"""
Expected Points (xPts) calculation module
"""

import numpy as np
from typing import Dict, List, Optional, Any
import logging
from datetime import datetime, timedelta

from ..models import Player, Team, Fixture, Gameweek, Position
from ..config import Config


logger = logging.getLogger(__name__)


class ExpectedPointsCalculator:
    """Calculates expected points for players across multiple gameweeks"""
    
    def __init__(self, config: Config):
        self.config = config
        self.points_config = config.get_points_config()
        self.optimization_config = config.get_optimization_config()
        self.injury_config = config.get_injury_config()
        
        # Historical data for better estimates
        self.historical_data = {
            'yellow_cards_per_90': {
                'DEF': 0.25,  # Average yellow cards per 90 mins for defenders
                'MID': 0.20,  # Average yellow cards per 90 mins for midfielders
                'FWD': 0.15,  # Average yellow cards per 90 mins for forwards
                'GK': 0.05,   # Average yellow cards per 90 mins for goalkeepers
            },
            'red_cards_per_90': {
                'DEF': 0.02,
                'MID': 0.015,
                'FWD': 0.01,
                'GK': 0.005,
            },
            'bonus_points_per_90': {
                'DEF': 0.15,
                'MID': 0.25,
                'FWD': 0.30,
                'GK': 0.10,
            },
            'minutes_per_game': {
                'GK': 0.95,   # Goalkeepers play most games
                'DEF': 0.85,  # Defenders play most games
                'MID': 0.75,  # Midfielders get rotated more
                'FWD': 0.70,  # Forwards get subbed more
            }
        }
        
        # Team-specific data for better estimates
        self.team_rotation_risk = {
            'Man City': 0.8,    # High rotation risk
            'Arsenal': 0.7,     # Medium-high rotation risk
            'Liverpool': 0.7,   # Medium-high rotation risk
            'Chelsea': 0.8,     # High rotation risk
            'Spurs': 0.6,       # Medium rotation risk
            'Man Utd': 0.7,     # Medium-high rotation risk
            'Newcastle': 0.6,   # Medium rotation risk
            'Aston Villa': 0.5, # Lower rotation risk
            'Brighton': 0.7,    # Medium-high rotation risk
            'Brentford': 0.5,   # Lower rotation risk
            'West Ham': 0.5,    # Lower rotation risk
            'Crystal Palace': 0.5,
            'Fulham': 0.5,
            'Wolves': 0.5,
            'Everton': 0.5,
            'Bournemouth': 0.5,
            'Burnley': 0.5,
            'Nott\'m Forest': 0.5,
            'Sunderland': 0.6,  # Newly promoted - might rotate
            'Leeds': 0.6,       # Newly promoted - might rotate
        }
        
    def calculate_player_xpts(self, player: Player, fixture: Fixture, 
                            home_team: Team, away_team: Team) -> float:
        """Calculate expected points for a player in a specific fixture"""
        
        # Check if player is available
        if not player.is_available:
            return 0.0
        
        # Get position-specific point values
        goal_pts = self.points_config['goal'].get(player.position.value.lower(), 4)
        assist_pts = self.points_config['assist']
        cs_pts = self.points_config['clean_sheet'].get(player.position.value.lower(), 0)
        bonus_pts = self.points_config['bonus']
        yc_pts = self.points_config['yellow_card']
        rc_pts = self.points_config['red_card']
        
        # Calculate expected goals and assists
        xG_pred = self._calculate_expected_goals(player, fixture, home_team, away_team)
        xA_pred = self._calculate_expected_assists(player, fixture, home_team, away_team)
        
        # Calculate clean sheet probability
        xCS_prob = self._calculate_clean_sheet_probability(player, fixture, home_team, away_team)
        
        # Calculate bonus probability
        bonus_prob = self._calculate_bonus_probability(player, xG_pred, xA_pred)
        
        # Calculate card probabilities
        yc_prob = self._calculate_yellow_card_probability(player, fixture)
        rc_prob = self._calculate_red_card_probability(player, fixture)
        
        # Calculate expected minutes
        xMins_pct = self._calculate_expected_minutes(player, fixture)
        
        # Apply xPts formula
        xPts = (
            (xG_pred * goal_pts) +
            (xA_pred * assist_pts) +
            (xCS_prob * cs_pts) +
            (bonus_prob * bonus_pts) +
            (yc_prob * yc_pts) +
            (rc_prob * rc_pts)
        ) * xMins_pct
        
        # Add base points for playing (2 points for playing 60+ minutes)
        base_points = 2.0 * xMins_pct
        
        total_xpts = xPts + base_points
        
        return max(0.0, total_xpts)  # Ensure non-negative
    
    def calculate_player_xpts_for_gameweek(self, player: Player, gameweek: int,
                                         fixtures: List[Fixture], teams: List[Team]) -> float:
        """Calculate expected points for a player in a specific gameweek"""
        
        # Find player's fixture in this gameweek
        player_fixture = self._find_player_fixture(player, gameweek, fixtures)
        if not player_fixture:
            return 0.0
        
        # Get teams
        home_team = self._find_team_by_name(player_fixture.home_team_name, teams)
        away_team = self._find_team_by_name(player_fixture.away_team_name, teams)
        
        if not home_team or not away_team:
            return 0.0
        
        return self.calculate_player_xpts(player, player_fixture, home_team, away_team)
    
    def calculate_player_xpts_for_period(self, player: Player, start_gameweek: int,
                                       end_gameweek: int, fixtures: List[Fixture],
                                       teams: List[Team]) -> float:
        """Calculate expected points for a player over a period of gameweeks with decay"""
        
        total_xpts = 0.0
        decay_factor = self.optimization_config.get('xpts_decay_factor', 0.85)
        
        for gw in range(start_gameweek, end_gameweek + 1):
            # Calculate base xPts for this gameweek
            gw_xpts = self.calculate_player_xpts_for_gameweek(player, gw, fixtures, teams)
            
            # Apply decay based on distance from current gameweek
            weeks_ahead = gw - start_gameweek
            decayed_xpts = gw_xpts * (decay_factor ** weeks_ahead)
            
            total_xpts += decayed_xpts
        
        return total_xpts
    
    def calculate_all_players_xpts(self, players: List[Player], current_gameweek: int,
                                 fixtures: List[Fixture], teams: List[Team]) -> Dict[int, float]:
        """Calculate expected points for all players over the planning window"""
        
        planning_window = self.optimization_config.get('planning_window', 5)
        end_gameweek = current_gameweek + planning_window - 1
        
        player_xpts = {}
        
        for player in players:
            try:
                xpts = self.calculate_player_xpts_for_period(
                    player, current_gameweek, end_gameweek, fixtures, teams
                )
                player_xpts[player.id] = xpts
            except Exception as e:
                logger.warning(f"Failed to calculate xPts for {player.name}: {e}")
                player_xpts[player.id] = 0.0
        
        return player_xpts
    
    def _calculate_expected_goals(self, player: Player, fixture: Fixture,
                                home_team: Team, away_team: Team) -> float:
        """Calculate expected goals for a player with improved logic"""
        
        # Use player's xG if available, otherwise estimate from position and price
        if player.xG > 0:
            base_xg = player.xG
        else:
            # Improved estimation based on position, price, and historical performance
            if player.position == Position.FWD:
                # Forwards: use price and points per game as indicators
                price_factor = (player.price - 4.5) / 10.0  # 0-1 scale
                ppg_factor = min(player.points_per_game / 10.0, 1.0)  # 0-1 scale
                base_xg = 0.10 + (price_factor * 0.20) + (ppg_factor * 0.15)  # 0.10-0.45 range
            elif player.position == Position.MID:
                # Midfielders: consider attacking vs defensive midfielders
                price_factor = (player.price - 4.5) / 10.0
                ppg_factor = min(player.points_per_game / 10.0, 1.0)
                base_xg = 0.05 + (price_factor * 0.12) + (ppg_factor * 0.10)  # 0.05-0.27 range
            elif player.position == Position.DEF:
                # Defenders: mostly attacking full-backs
                price_factor = (player.price - 4.0) / 6.0
                ppg_factor = min(player.points_per_game / 8.0, 1.0)
                base_xg = 0.01 + (price_factor * 0.04) + (ppg_factor * 0.03)  # 0.01-0.08 range
            else:  # GK
                base_xg = 0.0
        
        # Adjust based on fixture difficulty (opposition consideration)
        if player.team_id == fixture.home_team_id:
            difficulty_factor = (6 - fixture.home_difficulty) / 5.0
        else:
            difficulty_factor = (6 - fixture.away_difficulty) / 5.0
        
        # Adjust based on team strength
        if player.team_id == fixture.home_team_id:
            team_strength = home_team.strength / 1000.0  # Normalize to 0-1
            opponent_strength = away_team.strength / 1000.0
        else:
            team_strength = away_team.strength / 1000.0
            opponent_strength = home_team.strength / 1000.0
        
        # Home advantage
        home_advantage = 1.1 if player.team_id == fixture.home_team_id else 0.9
        
        # Calculate final xG
        final_xg = base_xg * difficulty_factor * team_strength * home_advantage
        
        return max(0.0, final_xg)
    
    def _calculate_expected_assists(self, player: Player, fixture: Fixture,
                                 home_team: Team, away_team: Team) -> float:
        """Calculate expected assists for a player"""
        
        # Use player's xA if available, otherwise estimate from position and price
        if player.xA > 0:
            base_xa = player.xA
        else:
            # Estimate xA based on position and price (more realistic for pre-season)
            if player.position == Position.MID:
                # Midfielders: higher price = higher xA expectation
                base_xa = 0.12 + (player.price - 4.5) * 0.04  # 0.12-0.28 range
            elif player.position == Position.FWD:
                # Forwards: moderate xA expectation
                base_xa = 0.08 + (player.price - 4.5) * 0.02  # 0.08-0.16 range
            elif player.position == Position.DEF:
                # Defenders: low xA expectation
                base_xa = 0.03 + (player.price - 4.0) * 0.01  # 0.03-0.08 range
            else:  # GK
                base_xa = 0.0  # Goalkeepers rarely assist
        
        # Adjust based on fixture difficulty
        if player.team_id == fixture.home_team_id:
            difficulty_factor = (6 - fixture.home_difficulty) / 5.0
        else:
            difficulty_factor = (6 - fixture.away_difficulty) / 5.0
        
        # Adjust based on player form (if available)
        if player.form > 0:
            form_factor = 1.0 + (player.form / 100.0)
        else:
            # For pre-season, use a neutral factor
            form_factor = 1.0
        
        # Calculate final xA
        xa = base_xa * difficulty_factor * form_factor
        
        return max(0.0, xa)
    
    def _calculate_clean_sheet_probability(self, player: Player, fixture: Fixture,
                                         home_team: Team, away_team: Team) -> float:
        """Calculate clean sheet probability for a player"""
        
        # Only defenders and goalkeepers can get clean sheet points
        if player.position not in [Position.DEF, Position.GK]:
            return 0.0
        
        # Base clean sheet probability from team defense
        if player.team_id == fixture.home_team_id:
            team_defense = home_team.xGA if home_team else 1.5
            opponent_attack = away_team.xG if away_team else 1.5
        else:
            team_defense = away_team.xGA if away_team else 1.5
            opponent_attack = home_team.xG if home_team else 1.5
        
        # Calculate clean sheet probability
        # Lower xGA and lower opponent xG = higher clean sheet probability
        base_cs_prob = max(0.0, 0.4 - (team_defense * 0.1) - (opponent_attack * 0.1))
        
        # Adjust based on fixture difficulty
        if player.team_id == fixture.home_team_id:
            difficulty_factor = (6 - fixture.home_difficulty) / 5.0
        else:
            difficulty_factor = (6 - fixture.away_difficulty) / 5.0
        
        cs_prob = base_cs_prob * difficulty_factor
        
        return max(0.0, min(1.0, cs_prob))
    
    def _calculate_bonus_probability(self, player: Player, xG_pred: float, xA_pred: float) -> float:
        """Calculate bonus points probability"""
        
        # Bonus points are typically awarded for attacking contributions
        attacking_contribution = xG_pred + xA_pred
        
        # Base bonus probability based on attacking contribution
        base_bonus_prob = min(0.3, attacking_contribution * 0.2)
        
        # Adjust based on player's historical bonus performance
        # This would ideally use historical bonus data
        historical_bonus_factor = 1.0
        
        bonus_prob = base_bonus_prob * historical_bonus_factor
        
        return max(0.0, min(1.0, bonus_prob))
    
    def _calculate_yellow_card_probability(self, player: Player, fixture: Fixture) -> float:
        """Calculate yellow card probability with improved logic"""
        
        # Base probability from historical data
        base_prob = self.historical_data['yellow_cards_per_90'].get(player.position.value, 0.20)
        
        # Adjust based on opponent team (some teams get more cards against them)
        opponent_team = fixture.away_team_name if player.team_id == fixture.home_team_id else fixture.home_team_name
        opponent_factor = self._get_opponent_card_factor(opponent_team)
        
        # Adjust based on fixture difficulty (harder games = more cards)
        if player.team_id == fixture.home_team_id:
            difficulty_factor = 1.0 + (fixture.home_difficulty - 3) * 0.1
        else:
            difficulty_factor = 1.0 + (fixture.away_difficulty - 3) * 0.1
        
        # Adjust based on player's disciplinary history (if available)
        if hasattr(player, 'yellow_cards') and player.yellow_cards > 0:
            history_factor = 1.0 + (player.yellow_cards / 10.0)
        else:
            history_factor = 1.0
        
        final_prob = base_prob * opponent_factor * difficulty_factor * history_factor
        
        return min(0.5, max(0.01, final_prob))  # Keep within reasonable bounds

    def _calculate_red_card_probability(self, player: Player, fixture: Fixture) -> float:
        """Calculate red card probability with improved logic"""
        
        # Base probability from historical data
        base_prob = self.historical_data['red_cards_per_90'].get(player.position.value, 0.01)
        
        # Adjust based on opponent team
        opponent_team = fixture.away_team_name if player.team_id == fixture.home_team_id else fixture.home_team_name
        opponent_factor = self._get_opponent_card_factor(opponent_team)
        
        # Adjust based on fixture difficulty (harder games = more cards)
        if player.team_id == fixture.home_team_id:
            difficulty_factor = 1.0 + (fixture.home_difficulty - 3) * 0.15
        else:
            difficulty_factor = 1.0 + (fixture.away_difficulty - 3) * 0.15
        
        # Adjust based on player's disciplinary history (if available)
        if hasattr(player, 'red_cards') and player.red_cards > 0:
            history_factor = 1.0 + (player.red_cards * 0.5)
        else:
            history_factor = 1.0
        
        final_prob = base_prob * opponent_factor * difficulty_factor * history_factor
        
        return min(0.1, max(0.001, final_prob))  # Keep within reasonable bounds

    def _get_opponent_card_factor(self, opponent_team: str) -> float:
        """Get card factor based on opponent team"""
        # Some teams historically get more cards against them
        high_card_teams = {
            'Man City': 1.2,    # Teams that dominate possession
            'Arsenal': 1.1,     # Teams that play attacking football
            'Liverpool': 1.1,
            'Spurs': 1.1,
            'Chelsea': 1.1,
            'Man Utd': 1.1,
        }
        
        return high_card_teams.get(opponent_team, 1.0)
    
    def _calculate_expected_minutes(self, player: Player, fixture: Fixture) -> float:
        """Calculate expected minutes as a percentage (0.0-1.0) with improved logic"""
        
        # Base minutes based on position
        base_minutes = self.historical_data['minutes_per_game'].get(player.position.value, 0.75)
        
        # Adjust based on price (more expensive players play more)
        price_factor = min(1.0, 0.7 + (player.price - 4.5) * 0.06)  # 0.7-1.0 range
        
        # Adjust based on team rotation risk
        team_rotation = self.team_rotation_risk.get(player.team_name, 0.6)
        rotation_factor = 1.0 - (team_rotation * 0.2)  # Higher rotation risk = lower minutes
        
        # Adjust based on fixture difficulty (easier games = more rotation)
        if player.team_id == fixture.home_team_id:
            difficulty_factor = 1.0 + (3 - fixture.home_difficulty) * 0.05
        else:
            difficulty_factor = 1.0 + (3 - fixture.away_difficulty) * 0.05
        
        # Adjust based on injury status
        if player.is_injured:
            if (hasattr(player, 'injury_expected_return') and player.injury_expected_return and 
                fixture.kickoff_time and hasattr(player.injury_expected_return, 'replace')):
                try:
                    # Handle timezone-aware datetime comparison
                    if player.injury_expected_return > fixture.kickoff_time:
                        return 0.0  # Won't be available
                except (TypeError, ValueError):
                    # If datetime comparison fails, assume doubtful
                    pass
            base_minutes *= 0.5  # Doubtful
        
        # Calculate final minutes
        minutes = base_minutes * price_factor * rotation_factor * difficulty_factor
        
        return max(0.0, min(1.0, minutes))
    
    def _find_player_fixture(self, player: Player, gameweek: int, fixtures: List[Fixture]) -> Optional[Fixture]:
        """Find the fixture for a player in a specific gameweek"""
        
        for fixture in fixtures:
            if fixture.gameweek == gameweek:
                if (player.team_id == fixture.home_team_id or 
                    player.team_id == fixture.away_team_id):
                    return fixture
        
        return None
    
    def _find_team_by_name(self, team_name: str, teams: List[Team]) -> Optional[Team]:
        """Find team by name"""
        
        for team in teams:
            if team.name == team_name:
                return team
        
        return None
