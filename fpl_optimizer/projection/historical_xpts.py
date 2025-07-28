#!/usr/bin/env python3
"""
Historical data-based xPts calculator
"""

from fpl_optimizer.projection.xpts import ExpectedPointsCalculator
from fpl_optimizer.models import Player, Fixture, Team, Position
from fpl_optimizer.data.historical_data import HistoricalDataManager
from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)

class HistoricalExpectedPointsCalculator(ExpectedPointsCalculator):
    """xPts calculator that uses historical data with weighted recent performance"""
    
    def __init__(self, config):
        super().__init__(config)
        self.historical_manager = HistoricalDataManager()
        
        # Fallback data for players without historical data
        self.fallback_data = {
            'new_signings': {
                'xg_per_90': 0.15,  # Conservative estimate for new players
                'xa_per_90': 0.10,
                'minutes_pct': 0.70,
                'yellow_cards_per_90': 0.15,
                'red_cards_per_90': 0.01,
                'bonus_per_90': 0.20,
                'clean_sheet_rate': 0.15,
            }
        }
    
    def _get_player_historical_data(self, player: Player) -> Optional[Dict]:
        """Get historical data for a player, with fallbacks"""
        
        # Try to get historical data
        historical_stats = self.historical_manager.get_player_historical_stats(player.name)
        
        if historical_stats:
            logger.debug(f"Found historical data for {player.name}: {historical_stats}")
            return historical_stats
        
        # Check if player has previous club data (for new signings)
        previous_club_stats = self._get_previous_club_data(player)
        if previous_club_stats:
            logger.debug(f"Using previous club data for {player.name}: {previous_club_stats}")
            return previous_club_stats
        
        # Use fallback data based on position and price
        fallback_stats = self._get_fallback_data(player)
        logger.debug(f"Using fallback data for {player.name}: {fallback_stats}")
        return fallback_stats
    
    def _get_previous_club_data(self, player: Player) -> Optional[Dict]:
        """Get data from player's previous club (for new signings)"""
        
        # This would integrate with external APIs to get previous club performance
        # For now, we'll use a simplified approach based on player price and position
        
        if player.price >= 10.0:
            # Premium signing - likely to perform well
            return {
                'xg_per_90': 0.25 + (player.price - 10.0) * 0.05,
                'xa_per_90': 0.15 + (player.price - 10.0) * 0.03,
                'minutes_pct': 0.80,
                'yellow_cards_per_90': 0.12,
                'red_cards_per_90': 0.008,
                'bonus_per_90': 0.30,
                'clean_sheet_rate': 0.20,
            }
        elif player.price >= 7.0:
            # Mid-range signing
            return {
                'xg_per_90': 0.15 + (player.price - 7.0) * 0.03,
                'xa_per_90': 0.12 + (player.price - 7.0) * 0.02,
                'minutes_pct': 0.75,
                'yellow_cards_per_90': 0.15,
                'red_cards_per_90': 0.01,
                'bonus_per_90': 0.25,
                'clean_sheet_rate': 0.18,
            }
        else:
            # Budget signing - use conservative estimates
            return self.fallback_data['new_signings']
    
    def _get_fallback_data(self, player: Player) -> Dict:
        """Get fallback data based on position and price"""
        
        base_data = self.fallback_data['new_signings'].copy()
        
        # Adjust based on position
        if player.position == Position.FWD:
            base_data['xg_per_90'] = 0.20 + (player.price - 4.5) * 0.03
            base_data['xa_per_90'] = 0.08 + (player.price - 4.5) * 0.02
            base_data['minutes_pct'] = 0.65 + (player.price - 4.5) * 0.02
        elif player.position == Position.MID:
            base_data['xg_per_90'] = 0.12 + (player.price - 4.5) * 0.02
            base_data['xa_per_90'] = 0.15 + (player.price - 4.5) * 0.03
            base_data['minutes_pct'] = 0.70 + (player.price - 4.5) * 0.02
        elif player.position == Position.DEF:
            base_data['xg_per_90'] = 0.03 + (player.price - 4.0) * 0.01
            base_data['xa_per_90'] = 0.05 + (player.price - 4.0) * 0.01
            base_data['minutes_pct'] = 0.80 + (player.price - 4.0) * 0.02
            base_data['clean_sheet_rate'] = 0.25 + (player.price - 4.0) * 0.02
        else:  # GK
            base_data['xg_per_90'] = 0.0
            base_data['xa_per_90'] = 0.0
            base_data['minutes_pct'] = 0.90
            base_data['clean_sheet_rate'] = 0.30 + (player.price - 4.0) * 0.02
        
        return base_data
    
    def _get_team_historical_data(self, team: Team) -> Optional[Dict]:
        """Get historical data for a team"""
        
        team_stats = self.historical_manager.get_team_historical_stats(team.name)
        
        if team_stats:
            logger.debug(f"Found historical data for {team.name}: {team_stats}")
            return team_stats
        
        # Use fallback team data based on team strength
        return self._get_fallback_team_data(team)
    
    def _get_fallback_team_data(self, team: Team) -> Dict:
        """Get fallback team data based on team strength"""
        
        # Base team performance on team strength
        strength_factor = team.strength / 5.0  # Normalize to 0-1
        
        return {
            'xg_per_game': 1.0 + strength_factor * 1.0,  # 1.0-2.0 range
            'xga_per_game': 1.5 - strength_factor * 0.5,  # 1.0-1.5 range
            'clean_sheet_rate': 0.15 + strength_factor * 0.20,  # 0.15-0.35 range
            'total_games': 0  # No historical games
        }
    
    def _calculate_expected_goals(self, player: Player, fixture: Fixture,
                                home_team: Team, away_team: Team) -> float:
        """Calculate expected goals using historical data"""
        
        # Get player's historical data
        player_stats = self._get_player_historical_data(player)
        if not player_stats:
            return 0.0
        
        # Base xG from historical performance
        base_xg = player_stats['xg_per_90']
        
        # Adjust based on fixture difficulty
        if player.team_id == fixture.home_team_id:
            difficulty_factor = (6 - fixture.home_difficulty) / 5.0
        else:
            difficulty_factor = (6 - fixture.away_difficulty) / 5.0
        
        # Adjust based on team vs opponent strength
        home_stats = self._get_team_historical_data(home_team)
        away_stats = self._get_team_historical_data(away_team)
        
        if home_stats and away_stats:
            # Team attacking strength vs opponent defense
            if player.team_id == fixture.home_team_id:
                team_attack = home_stats['xg_per_game']
                opponent_defense = away_stats['xga_per_game']
            else:
                team_attack = away_stats['xg_per_game']
                opponent_defense = home_stats['xga_per_game']
            
            # Team factor based on relative strength
            team_factor = (team_attack / opponent_defense) * 0.8 + 0.2
        else:
            team_factor = 1.0
        
        # Calculate final xG
        xg = base_xg * difficulty_factor * team_factor
        
        return max(0.0, xg)
    
    def _calculate_expected_assists(self, player: Player, fixture: Fixture,
                                 home_team: Team, away_team: Team) -> float:
        """Calculate expected assists using historical data"""
        
        # Get player's historical data
        player_stats = self._get_player_historical_data(player)
        if not player_stats:
            return 0.0
        
        # Base xA from historical performance
        base_xa = player_stats['xa_per_90']
        
        # Apply same difficulty and team factors as xG
        if player.team_id == fixture.home_team_id:
            difficulty_factor = (6 - fixture.home_difficulty) / 5.0
        else:
            difficulty_factor = (6 - fixture.away_difficulty) / 5.0
        
        home_stats = self._get_team_historical_data(home_team)
        away_stats = self._get_team_historical_data(away_team)
        
        if home_stats and away_stats:
            if player.team_id == fixture.home_team_id:
                team_attack = home_stats['xg_per_game']
                opponent_defense = away_stats['xga_per_game']
            else:
                team_attack = away_stats['xg_per_game']
                opponent_defense = home_stats['xga_per_game']
            
            team_factor = (team_attack / opponent_defense) * 0.8 + 0.2
        else:
            team_factor = 1.0
        
        xa = base_xa * difficulty_factor * team_factor
        
        return max(0.0, xa)
    
    def _calculate_clean_sheet_probability(self, player: Player, fixture: Fixture,
                                         home_team: Team, away_team: Team) -> float:
        """Calculate clean sheet probability using historical data"""
        
        # Only defenders and goalkeepers can get clean sheet points
        if player.position not in [Position.DEF, Position.GK]:
            return 0.0
        
        # Get team historical data
        home_stats = self._get_team_historical_data(home_team)
        away_stats = self._get_team_historical_data(away_team)
        
        if not home_stats or not away_stats:
            return 0.0
        
        # Base clean sheet probability from team defense vs opponent attack
        if player.team_id == fixture.home_team_id:
            team_defense = home_stats['xga_per_game']
            opponent_attack = away_stats['xg_per_game']
        else:
            team_defense = away_stats['xga_per_game']
            opponent_attack = home_stats['xg_per_game']
        
        # Calculate base clean sheet probability
        base_cs_prob = max(0.0, 0.4 - (team_defense * 0.1) - (opponent_attack * 0.1))
        
        # Adjust based on fixture difficulty
        if player.team_id == fixture.home_team_id:
            difficulty_factor = (6 - fixture.home_difficulty) / 5.0
        else:
            difficulty_factor = (6 - fixture.away_difficulty) / 5.0
        
        # Player-specific adjustments based on position and role
        if player.position == Position.GK:
            player_factor = 1.0  # Goalkeepers get full CS probability
        elif player.position == Position.DEF:
            # Defenders get CS probability based on their role
            if player.price >= 6.0:
                player_factor = 0.8  # Attacking full-backs
            elif player.price >= 5.0:
                player_factor = 0.9  # Regular defenders
            else:
                player_factor = 1.0  # Cheap defenders (more defensive)
        
        cs_prob = base_cs_prob * difficulty_factor * player_factor
        
        return max(0.0, min(1.0, cs_prob))
    
    def _calculate_bonus_probability(self, player: Player, xG_pred: float, xA_pred: float) -> float:
        """Calculate bonus points probability using historical data"""
        
        # Get player's historical data
        player_stats = self._get_player_historical_data(player)
        if not player_stats:
            return 0.0
        
        # Base bonus probability from historical performance
        base_bonus_prob = player_stats['bonus_per_90'] * 0.9  # Convert to per-game
        
        # Add attacking contribution factor
        attacking_contribution = xG_pred + xA_pred
        attacking_factor = min(1.5, 1.0 + attacking_contribution * 0.5)
        
        bonus_prob = base_bonus_prob * attacking_factor
        
        return max(0.0, min(1.0, bonus_prob))
    
    def _calculate_yellow_card_probability(self, player: Player) -> float:
        """Calculate yellow card probability using historical data"""
        
        # Get player's historical data
        player_stats = self._get_player_historical_data(player)
        if not player_stats:
            return 0.15  # Default fallback
        
        # Base yellow card probability from historical data
        base_yc_prob = player_stats['yellow_cards_per_90'] * 0.9  # Convert to per-game
        
        # For now, use base probability without fixture-specific adjustments
        # In a full implementation, we'd need to pass fixture context differently
        
        return max(0.0, min(1.0, base_yc_prob))
    
    def _calculate_red_card_probability(self, player: Player) -> float:
        """Calculate red card probability using historical data"""
        
        # Get player's historical data
        player_stats = self._get_player_historical_data(player)
        if not player_stats:
            return 0.01  # Default fallback
        
        # Base red card probability from historical data
        base_rc_prob = player_stats['red_cards_per_90'] * 0.9  # Convert to per-game
        
        return max(0.0, min(1.0, base_rc_prob))
    
    def _calculate_expected_minutes(self, player: Player, fixture: Fixture) -> float:
        """Calculate expected playing time using historical data"""
        
        # Get player's historical data
        player_stats = self._get_player_historical_data(player)
        if not player_stats:
            return 0.8  # Default fallback
        
        # Base minutes from historical data
        base_minutes = player_stats['minutes_pct']
        
        # Adjust based on injury status
        if player.is_injured:
            if player.injury_expected_return and fixture.kickoff_time and player.injury_expected_return > fixture.kickoff_time:
                return 0.0  # Won't be available
            else:
                base_minutes *= 0.5  # Doubtful
        
        # Adjust based on fixture difficulty (easier games = more rotation)
        if player.team_id == fixture.home_team_id:
            difficulty_factor = 1.0 + (3 - fixture.home_difficulty) * 0.05
        else:
            difficulty_factor = 1.0 + (3 - fixture.away_difficulty) * 0.05
        
        # Team rotation risk (would be enhanced with actual team data)
        team_rotation = self._get_team_rotation_risk(player.team_name)
        rotation_factor = 1.0 - (team_rotation * 0.2)
        
        minutes = base_minutes * difficulty_factor * rotation_factor
        
        return max(0.0, min(1.0, minutes))
    
    def _get_team_rotation_risk(self, team_name: str) -> float:
        """Get team rotation risk factor"""
        high_rotation_teams = {
            'Man City': 0.8,
            'Arsenal': 0.7,
            'Liverpool': 0.7,
            'Chelsea': 0.8,
            'Spurs': 0.6,
            'Man Utd': 0.7,
            'Newcastle': 0.6,
            'Brighton': 0.7,
        }
        
        return high_rotation_teams.get(team_name, 0.5)
    
    def _get_opponent_card_factor(self, opponent_team: str) -> float:
        """Get card factor based on opponent team"""
        high_card_teams = {
            'Man City': 1.2,    # Teams that dominate possession
            'Arsenal': 1.1,     # Teams that play attacking football
            'Liverpool': 1.1,
            'Spurs': 1.1,
            'Chelsea': 1.1,
            'Man Utd': 1.1,
        }
        
        return high_card_teams.get(opponent_team, 1.0) 