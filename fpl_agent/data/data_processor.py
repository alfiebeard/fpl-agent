"""
Data processor for transforming and enriching FPL API data.

This class consolidates all data processing logic from the existing
data_transformers.py and data_enrichment.py files.
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

from ..core.config import Config
from ..core.models import Position
from .fetch_fpl import FPLDataFetcher

logger = logging.getLogger(__name__)


class DataProcessor:
    """Processes and enriches FPL API data"""
    
    def __init__(self, config: Config):
        """
        Initialize data processor.
        
        Args:
            config: FPL configuration object
        """
        self.config = config
        self.fetcher = FPLDataFetcher(config)
    
    def process_fpl_data(self, bootstrap_data: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
        """
        Process raw FPL bootstrap data into structured player data.
        
        Args:
            bootstrap_data: Raw data from FPL bootstrap-static endpoint
            
        Returns:
            Dictionary of processed player data keyed by player ID
        """
        logger.info("Processing FPL bootstrap data...")
        
        # Create team ID to name mapping
        team_mapping = self._create_team_mapping(bootstrap_data)
        
        # Process players
        processed_players = {}
        for player_data in bootstrap_data.get('elements', []):
            try:
                player_id = str(player_data['id'])
                processed_players[player_id] = self._process_player(player_data, team_mapping)
            except Exception as e:
                logger.warning(f"Failed to process player {player_data.get('id', 'unknown')}: {e}")
                continue
        
        logger.info(f"Processed {len(processed_players)} players")
        return processed_players
    
    def _create_team_mapping(self, bootstrap_data: Dict[str, Any]) -> Dict[int, Dict[str, str]]:
        """Create mapping from team ID to team info."""
        team_mapping = {}
        for team_data in bootstrap_data.get('teams', []):
            team_mapping[team_data['id']] = {
                'name': team_data['name'],
                'short_name': team_data['short_name']
            }
        return team_mapping
    
    def _process_player(self, player_data: Dict[str, Any], team_mapping: Dict[int, Dict[str, str]]) -> Dict[str, Any]:
        """
        Process individual player data.
        
        Args:
            player_data: Raw player data from FPL API
            team_mapping: Team ID to team info mapping
            
        Returns:
            Processed player data dictionary
        """
        # Map FPL position IDs to our Position enum
        position_map = {1: 'GK', 2: 'DEF', 3: 'MID', 4: 'FWD'}
        position = position_map.get(player_data['element_type'], 'UNK')
        
        # Get team info
        team_id = player_data['team']
        team_info = team_mapping.get(team_id, {'name': 'Unknown Team', 'short_name': 'UNK'})
        
        # Calculate chance of playing
        chance_of_playing = self._calculate_chance_of_playing(
            player_data.get('chance_of_playing_this_round'),
            player_data.get('chance_of_playing_next_round')
        )
        
        # Process form data
        form = self._process_form(player_data.get('form', '0.0'))
        
        # Create processed player data
        processed_player = {
            'id': player_data['id'],
            'first_name': player_data['first_name'],
            'second_name': player_data['second_name'],
            'full_name': f"{player_data['first_name']} {player_data['second_name']}",
            'team_id': team_id,
            'team_name': team_info['name'],
            'team_short_name': team_info['short_name'],
            'position': position,
            'element_type': player_data['element_type'],
            'now_cost': player_data['now_cost'],
            'total_points': player_data['total_points'],
            'form': form,
            'points_per_game': player_data.get('points_per_game', '0.0'),
            'minutes': player_data.get('minutes', 0),
            'selected_by_percent': player_data.get('selected_by_percent', '0.0'),
            'chance_of_playing': chance_of_playing,
            'xG': player_data.get('xG', '0.00'),
            'xA': player_data.get('xA', '0.00'),
            'xGC': player_data.get('xGC', '0.00'),
            'xMins_pct': player_data.get('xMins_pct', 1.0),
            'is_injured': player_data.get('is_injured', False),
            'news': player_data.get('news', ''),
            'status': player_data.get('status', 'a'),
            'transfers_in': player_data.get('transfers_in', 0),
            'transfers_out': player_data.get('transfers_out', 0),
            'transfers_balance': player_data.get('transfers_balance', 0),
            'ict_index': player_data.get('ict_index', '0.0'),
            'influence': player_data.get('influence', '0.0'),
            'creativity': player_data.get('creativity', '0.0'),
            'threat': player_data.get('threat', '0.0'),
            'starts': player_data.get('starts', 0),
            'expected_goals': player_data.get('expected_goals', '0.00'),
            'expected_assists': player_data.get('expected_assists', '0.00'),
            'expected_goal_involvements': player_data.get('expected_goal_involvements', '0.00'),
            'expected_goals_conceded': player_data.get('expected_goals_conceded', '0.00'),
            'expected_clean_sheets': player_data.get('expected_clean_sheets', '0.00'),
            'expected_saves': player_data.get('expected_saves', '0.00'),
            'goals_scored': player_data.get('goals_scored', 0),
            'assists': player_data.get('assists', 0),
            'clean_sheets': player_data.get('clean_sheets', 0),
            'goals_conceded': player_data.get('goals_conceded', 0),
            'own_goals': player_data.get('own_goals', 0),
            'penalties_saved': player_data.get('penalties_saved', 0),
            'penalties_missed': player_data.get('penalties_missed', 0),
            'yellow_cards': player_data.get('yellow_cards', 0),
            'red_cards': player_data.get('red_cards', 0),
            'saves': player_data.get('saves', 0),
            'bonus': player_data.get('bonus', 0),
            'bps': player_data.get('bps', 0),
            'influence_rank': player_data.get('influence_rank', 0),
            'influence_rank_type': player_data.get('influence_rank_type', 0),
            'creativity_rank': player_data.get('creativity_rank', 0),
            'creativity_rank_type': player_data.get('creativity_rank_type', 0),
            'threat_rank': player_data.get('threat_rank', 0),
            'threat_rank_type': player_data.get('threat_rank_type', 0),
            'ict_index_rank': player_data.get('ict_index_rank', 0),
            'ict_index_rank_type': player_data.get('ict_index_rank_type', 0),
            'corners_and_indirect_freekicks_order': player_data.get('corners_and_indirect_freekicks_order', 0),
            'corners_and_indirect_freekicks_text': player_data.get('corners_and_indirect_freekicks_text', ''),
            'direct_freekicks_order': player_data.get('direct_freekicks_order', 0),
            'direct_freekicks_text': player_data.get('direct_freekicks_text', ''),
            'penalties_order': player_data.get('penalties_order', 0),
            'penalties_text': player_data.get('penalties_text', ''),
            'raw_data': player_data  # Keep original data for reference
        }
        
        return processed_player
    
    def _calculate_chance_of_playing(self, chance_this_round: Optional[int], chance_next_round: Optional[int]) -> int:
        """
        Calculate chance of playing as minimum of this round and next round.
        
        Args:
            chance_this_round: Chance of playing this round
            chance_next_round: Chance of playing next round
            
        Returns:
            Minimum chance of playing (0-100)
        """
        if chance_this_round is None and chance_next_round is None:
            return 100
        
        if chance_this_round is None:
            return chance_next_round or 100
        
        if chance_next_round is None:
            return chance_this_round or 100
        
        return min(chance_this_round, chance_next_round)
    
    def _process_form(self, form_data: Any) -> float:
        """
        Process form data to ensure it's a valid float.
        
        Args:
            form_data: Raw form data from FPL API
            
        Returns:
            Processed form as float
        """
        try:
            if form_data is None or form_data == '':
                return 0.0
            return float(form_data)
        except (ValueError, TypeError):
            return 0.0
    
    def get_available_players(self, player_data: Dict[str, Dict[str, Any]], filters: Optional[Dict[str, Any]] = None) -> Dict[str, Dict[str, Any]]:
        """
        Filter players based on availability criteria.
        
        Args:
            player_data: Dictionary of all player data
            filters: Optional filters to apply
            
        Returns:
            Filtered dictionary of available players
        """
        if filters is None:
            filters = {
                'exclude_injured': True,
                'exclude_unavailable': True,
                'min_chance_of_playing': 25,
                'min_minutes': 0,
                'max_price': float('inf'),
                'min_form': float('-inf'),
                'positions': ['GK', 'DEF', 'MID', 'FWD']
            }
        
        available_players = {}
        
        for player_id, player in player_data.items():
            try:
                # Apply filters
                if not self._player_meets_filters(player, filters):
                    continue
                
                available_players[player_id] = player
                
            except Exception as e:
                logger.warning(f"Failed to filter player {player_id}: {e}")
                continue
        
        logger.info(f"Filtered to {len(available_players)} available players from {len(player_data)} total")
        return available_players
    
    def _player_meets_filters(self, player: Dict[str, Any], filters: Dict[str, Any]) -> bool:
        """Check if player meets filtering criteria."""
        # Position filter
        if player.get('position') not in filters.get('positions', ['GK', 'DEF', 'MID', 'FWD']):
            return False
        
        # Injury filter
        if filters.get('exclude_injured', True) and player.get('is_injured', False):
            return False
        
        # Chance of playing filter
        chance = player.get('chance_of_playing', 100)
        if chance < filters.get('min_chance_of_playing', 25):
            return False
        
        # Minutes filter
        if player.get('minutes', 0) < filters.get('min_minutes', 0):
            return False
        
        # Price filter
        if player.get('now_cost', 0) / 10.0 > filters.get('max_price', float('inf')):
            return False
        
        # Form filter
        if player.get('form', 0) < filters.get('min_form', float('-inf')):
            return False
        
        return True
    
    def get_teams_data(self, player_data: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Extract team data from player data.
        
        Args:
            player_data: Dictionary of all player data
            
        Returns:
            List of team data dictionaries
        """
        team_names = set()
        teams_data = []
        
        # Extract team data from players
        for player in player_data.values():
            team_name_from_player = player.get('team_name')
            if team_name_from_player and team_name_from_player not in team_names:
                team_names.add(team_name_from_player)
                teams_data.append({'name': team_name_from_player, 'id': len(teams_data) + 1})
        
        return teams_data
    
    def get_fixture_info(self, team_name: str, current_gameweek: int, fixtures: List[Dict[str, Any]], players: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """
        Get fixture information for a team in a specific gameweek.
        
        Args:
            team_name: Name of the team
            current_gameweek: Current gameweek number
            fixtures: List of all fixtures
            players: Dictionary of all players
            
        Returns:
            Dictionary containing fixture string, double gameweek status, and fixture difficulty
        """
        # Find team's fixtures for the current gameweek
        team_fixtures = []
        for fixture in fixtures:
            if fixture.get('event') == current_gameweek:
                # Check if this team is playing
                home_team = fixture.get('team_h')
                away_team = fixture.get('team_a')
                
                # Get team names from players data
                home_team_name = None
                away_team_name = None
                
                for player in players.values():
                    if player.get('team_id') == home_team:
                        home_team_name = player.get('team_name')
                    elif player.get('team_id') == away_team:
                        away_team_name = player.get('team_name')
                    
                    if home_team_name and away_team_name:
                        break
                
                if home_team_name == team_name or away_team_name == team_name:
                    team_fixtures.append(fixture)
        
        if not team_fixtures:
            return {
                'fixture_str': 'not playing this gameweek',
                'is_double_gameweek': False,
                'fixture_difficulty': 3.0
            }
        
        # Check if it's a double gameweek
        is_double_gameweek = len(team_fixtures) > 1
        
        # Calculate fixture difficulty (simplified - could be enhanced)
        fixture_difficulty = 3.0  # Default medium difficulty
        
        # Create fixture string
        if is_double_gameweek:
            fixture_str = f"playing {len(team_fixtures)} matches this gameweek"
        else:
            fixture = team_fixtures[0]
            home_team = fixture.get('team_h')
            away_team = fixture.get('team_a')
            
            # Determine if team is home or away
            team_id = None
            for player in players.values():
                if player.get('team_name') == team_name:
                    team_id = player.get('team_id')
                    break
            
            if team_id == home_team:
                opponent_id = away_team
                fixture_str = f"at home vs {self._get_team_name_by_id(opponent_id, players)}"
            else:
                opponent_id = home_team
                fixture_str = f"away vs {self._get_team_name_by_id(opponent_id, players)}"
        
        return {
            'fixture_str': fixture_str,
            'is_double_gameweek': is_double_gameweek,
            'fixture_difficulty': fixture_difficulty
        }
    
    def _get_team_name_by_id(self, team_id: int, players: Dict[str, Dict[str, Any]]) -> str:
        """Get team name by team ID from players data."""
        for player in players.values():
            if player.get('team_id') == team_id:
                return player.get('team_name', 'Unknown Team')
        return 'Unknown Team'
