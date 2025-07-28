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
        yc_prob = self._calculate_yellow_card_probability(player)
        rc_prob = self._calculate_red_card_probability(player)
        
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
        """Calculate expected goals for a player"""
        
        # Use player's xG if available, otherwise estimate from position and price
        if player.xG > 0:
            base_xg = player.xG
        else:
            # Estimate xG based on position and price (more realistic for pre-season)
            if player.position == Position.FWD:
                # Forwards: higher price = higher xG expectation
                base_xg = 0.15 + (player.price - 4.5) * 0.05  # 0.15-0.35 range
            elif player.position == Position.MID:
                # Midfielders: moderate xG expectation
                base_xg = 0.08 + (player.price - 4.5) * 0.03  # 0.08-0.20 range
            elif player.position == Position.DEF:
                # Defenders: low xG expectation
                base_xg = 0.02 + (player.price - 4.0) * 0.01  # 0.02-0.08 range
            else:  # GK
                base_xg = 0.0  # Goalkeepers don't score goals
        
        # Adjust based on fixture difficulty
        if player.team_id == fixture.home_team_id:
            # Player is playing at home
            difficulty_factor = (6 - fixture.home_difficulty) / 5.0  # 1-5 scale inverted
        else:
            # Player is playing away
            difficulty_factor = (6 - fixture.away_difficulty) / 5.0
        
        # Adjust based on player form (if available)
        if player.form > 0:
            form_factor = 1.0 + (player.form / 100.0)
        else:
            # For pre-season, use a neutral factor
            form_factor = 1.0
        
        # Calculate final xG
        xg = base_xg * difficulty_factor * form_factor
        
        return max(0.0, xg)
    
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
    
    def _calculate_yellow_card_probability(self, player: Player) -> float:
        """Calculate yellow card probability"""
        
        # Base yellow card probability
        base_yc_prob = 0.15  # ~15% chance per game
        
        # Adjust based on position (defenders/midfielders more likely)
        if player.position == Position.DEF:
            position_factor = 1.3
        elif player.position == Position.MID:
            position_factor = 1.1
        else:
            position_factor = 0.8
        
        # Adjust based on player's historical cards (if available)
        historical_cards = player.custom_data.get('yellow_cards', 3)
        historical_factor = 1.0 + (historical_cards - 3) * 0.1
        
        yc_prob = base_yc_prob * position_factor * historical_factor
        
        return max(0.0, min(1.0, yc_prob))
    
    def _calculate_red_card_probability(self, player: Player) -> float:
        """Calculate red card probability"""
        
        # Base red card probability (much lower than yellow)
        base_rc_prob = 0.02  # ~2% chance per game
        
        # Adjust based on player's historical cards (if available)
        historical_cards = player.custom_data.get('red_cards', 0)
        historical_factor = 1.0 + historical_cards * 0.5
        
        rc_prob = base_rc_prob * historical_factor
        
        return max(0.0, min(1.0, rc_prob))
    
    def _calculate_expected_minutes(self, player: Player, fixture: Fixture) -> float:
        """Calculate expected playing time percentage"""
        
        # Start with player's base expected minutes
        base_minutes = player.xMins_pct
        
        # If no xMins_pct data, estimate based on position and form
        if base_minutes <= 0:
            if player.position == Position.GK:
                base_minutes = 0.9  # Goalkeepers usually play full matches
            elif player.position == Position.DEF:
                base_minutes = 0.8  # Defenders usually play most of the match
            elif player.position == Position.MID:
                base_minutes = 0.7  # Midfielders may be rotated more
            else:  # FWD
                base_minutes = 0.6  # Forwards may be subbed more often
        
        # Adjust based on injury status
        if player.is_injured:
            if player.injury_expected_return and fixture.kickoff_time and player.injury_expected_return > fixture.kickoff_time:
                return 0.0  # Won't be available
            else:
                base_minutes *= 0.5  # Doubtful
        
        # Adjust based on player form (better form = more minutes)
        form_factor = 1.0 + (player.form / 100.0)
        
        # Adjust based on fixture difficulty (easier fixtures = more attacking minutes)
        if fixture.difficulty <= 2:  # Easy fixture
            difficulty_factor = 1.1
        elif fixture.difficulty >= 4:  # Hard fixture
            difficulty_factor = 0.9
        else:
            difficulty_factor = 1.0
        
        minutes = base_minutes * form_factor * difficulty_factor
        
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
