"""
Data processor for transforming and enriching FPL API data.

This class consolidates all data processing logic from the existing
data_transformers.py and data_enrichment.py files.
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

from ..core.config import Config
from ..core.models import Position, Player, Team
from ..ingestion.fetch_fpl import FPLDataFetcher
from dataclasses import dataclass
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)


@dataclass
class TeamSummary:
    """Team summary with players and statistics"""
    team: Team
    players: List[Player]
    total_players: int
    total_value: float
    average_points: float


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
    
    def _process_form(self, form_str: str) -> float:
        """
        Process form string to float.
        
        Args:
            form_str: Form string from FPL API
            
        Returns:
            Form as float
        """
        try:
            return float(form_str)
        except (ValueError, TypeError):
            return 0.0
    
    def get_available_players(self, player_data: Dict[str, Dict[str, Any]], 
                            filters: Optional[Dict[str, Any]] = None) -> Dict[str, Dict[str, Any]]:
        """
        Filter players based on availability criteria.
        
        Args:
            player_data: Dictionary of processed player data
            filters: Optional filter criteria
            
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
            # Check if player meets filter criteria
            if self._player_meets_criteria(player, filters):
                available_players[player_id] = player
        
        logger.info(f"Filtered to {len(available_players)} available players from {len(player_data)} total")
        return available_players
    
    def _player_meets_criteria(self, player: Dict[str, Any], filters: Dict[str, Any]) -> bool:
        """Check if player meets filter criteria."""
        # Position filter
        if player.get('position') not in filters.get('positions', ['GK', 'DEF', 'MID', 'FWD']):
            return False
        
        # Injury filter
        if filters.get('exclude_injured', True) and player.get('is_injured', False):
            return False
        
        # Availability filter
        if filters.get('exclude_unavailable', True):
            chance = player.get('chance_of_playing', 100)
            if chance < filters.get('min_chance_of_playing', 25):
                return False
        
        # Minutes filter
        if player.get('minutes', 0) < filters.get('min_minutes', 0):
            return False
        
        # Price filter
        if player.get('now_cost', 0) > filters.get('max_price', float('inf')):
            return False
        
        # Form filter
        if player.get('form', 0) < filters.get('min_form', float('-inf')):
            return False
        
        return True
    
    def get_fixture_info(self, team_name: str, current_gameweek: int, fixtures_data: List[Dict[str, Any]], players_data: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """
        Get fixture information for a team in a specific gameweek.
        
        Args:
            team_name: Name of the team
            current_gameweek: Current gameweek number
            fixtures_data: List of fixtures from FPL API
            players_data: Dictionary of player data
            
        Returns:
            Dictionary containing fixture string, double gameweek status, and fixture difficulty
        """
        # Extract team data from players
        teams_data = []
        team_names = set()
        for player in players_data.values():
            team_name_from_player = player.get('team_name')
            if team_name_from_player and team_name_from_player not in team_names:
                team_names.add(team_name_from_player)
                teams_data.append({'name': team_name_from_player, 'id': len(teams_data) + 1})
        
        # Create team name to ID mapping with error handling
        team_id_map = {}
        try:
            logger.debug(f"Processing teams data for {team_name}: found {len(teams_data)} teams")
            for team in teams_data:
                if isinstance(team, dict) and 'name' in team and 'id' in team:
                    team_id_map[team['name']] = team['id']
                else:
                    logger.debug(f"Skipping invalid team data: {team}")
            logger.debug(f"Created team ID mapping with {len(team_id_map)} teams")
        except Exception as e:
            logger.error(f"Failed to create team ID mapping: {e}")
            logger.error(f"Teams data structure: {teams_data[:2] if teams_data else 'Empty'}")
            return {
                'fixture_str': "no fixture scheduled",
                'is_double_gameweek': False,
                'fixture_difficulty': 3.0
            }
        
        team_id = team_id_map.get(team_name)
        
        if not team_id:
            return {
                'fixture_str': "no fixture scheduled",
                'is_double_gameweek': False,
                'fixture_difficulty': 3.0
            }
        
        # Find opponents for this gameweek
        opponents = []
        fixture_difficulties = []
        
        for fixture_data in fixtures_data:
            if fixture_data.get('event') == current_gameweek:
                home_team_id = fixture_data.get('team_h')
                away_team_id = fixture_data.get('team_a')
                
                # Get fixture date and time
                kickoff_time = fixture_data.get('kickoff_time')
                if kickoff_time:
                    try:
                        # Parse the ISO format date from FPL API
                        fixture_date = datetime.fromisoformat(kickoff_time.replace('Z', '+00:00'))
                        # Format as "Sunday 22nd May 2025 at 14:00"
                        day = fixture_date.day
                        suffix = 'th' if 11 <= day <= 13 else {1: 'st', 2: 'nd', 3: 'rd'}.get(day % 10, 'th')
                        formatted_date = f"{fixture_date.strftime('%A')} {day}{suffix} {fixture_date.strftime('%B %Y')} at {fixture_date.strftime('%H:%M')}"
                    except:
                        formatted_date = "TBD"
                else:
                    formatted_date = "TBD"
                
                if home_team_id == team_id:
                    # Team is playing home
                    away_team_name = next((team['name'] for team in teams_data if isinstance(team, dict) and team.get('id') == away_team_id), 'Unknown')
                    opponents.append(f"home to {away_team_name} on {formatted_date}")
                    # Get home difficulty (for the home team)
                    fixture_difficulties.append(fixture_data.get('team_h_difficulty', 3))
                elif away_team_id == team_id:
                    # Team is playing away
                    home_team_name = next((team['name'] for team in teams_data if isinstance(team, dict) and team.get('id') == home_team_id), 'Unknown')
                    opponents.append(f"away to {home_team_name} on {formatted_date}")
                    # Get away difficulty (for the away team)
                    fixture_difficulties.append(fixture_data.get('team_a_difficulty', 3))
        
        # Calculate average fixture difficulty
        if fixture_difficulties:
            avg_difficulty = sum(fixture_difficulties) / len(fixture_difficulties)
        else:
            avg_difficulty = 3.0
        
        # Format opponent string
        is_double_gameweek = len(opponents) > 1
        
        if opponents:
            if len(opponents) == 1:
                fixture_str = opponents[0]
            else:
                # Double gameweek
                fixture_str = f"double gameweek: {' and '.join(opponents)}"
        else:
            fixture_str = "no fixture scheduled"
        
        return {
            'fixture_str': fixture_str,
            'is_double_gameweek': is_double_gameweek,
            'fixture_difficulty': round(avg_difficulty, 1)
        }
    
    def calculate_chance_of_playing(self, this_round: Optional[int], next_round: Optional[int]) -> int:
        """
        Calculate the effective chance of playing as the minimum of this round and next round.
        
        Args:
            this_round: Chance of playing this round (null = 100)
            next_round: Chance of playing next round (null = 100)
            
        Returns:
            Minimum of the two values, treating null as 100
        """
        # Handle null values as 100 (player can play)
        this_round_chance = 100 if this_round is None else this_round
        next_round_chance = 100 if next_round is None else next_round
        
        # Return the minimum (conservative approach)
        return min(this_round_chance, next_round_chance)
    
    def transform_fpl_data_to_teams(
        self,
        bootstrap_data: Dict[str, Any],
        filters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, TeamSummary]:
        """
        Transform FPL API data into a team-based structure with optional filtering.
        
        Args:
            bootstrap_data: Raw FPL API bootstrap data
            filters: Optional filters to apply to players
            
        Returns:
            Dictionary mapping team names to TeamSummary objects
        """
        # Default filters
        default_filters = {
            'min_chance_of_playing': 0,      # Include all players by default
            'exclude_injured': True,         # Exclude injured by default
            'exclude_unavailable': True,     # Exclude unavailable by default
            'min_minutes': 0,                # No minimum minutes by default
            'max_price': float('inf'),       # No price limit by default
            'min_form': float('-inf'),       # No form minimum by default
            'positions': ['GK', 'DEF', 'MID', 'FWD']  # All positions by default
        }
        
        # Merge with provided filters
        if filters:
            default_filters.update(filters)
        
        filters = default_filters
        
        # Create team mapping and Team objects
        team_mapping = {}
        teams = {}
        
        for team_data in bootstrap_data.get('teams', []):
            team = Team(
                id=team_data['id'],
                name=team_data['name'],
                short_name=team_data['short_name'],
                strength=int(team_data.get('strength', 0) or 0),
                form=float(team_data.get('form', 0) or 0)
            )
            team_mapping[team_data['id']] = team
            teams[team.name] = TeamSummary(
                team=team,
                players=[],
                total_players=0,
                total_value=0.0,
                average_points=0.0
            )
        
        # Process players and assign to teams
        for player_data in bootstrap_data.get('elements', []):
            try:
                # Apply filters
                if not self._player_meets_team_filters(player_data, filters):
                    continue
                
                # Create Player object
                player = self._create_player_from_data(player_data, team_mapping)
                
                # Add to team
                team_id = player_data['team']
                team_name = team_mapping.get(team_id, {}).name if team_id in team_mapping else 'Unknown'
                
                if team_name in teams:
                    teams[team_name].players.append(player)
                    teams[team_name].total_players += 1
                    teams[team_name].total_value += player.now_cost / 10.0
                    teams[team_name].average_points += player.total_points
            except Exception as e:
                logger.warning(f"Failed to process player {player_data.get('id', 'unknown')}: {e}")
                continue
        
        # Calculate averages
        for team_summary in teams.values():
            if team_summary.total_players > 0:
                team_summary.average_points /= team_summary.total_players
        
        return teams
    
    def _player_meets_team_filters(self, player_data: Dict[str, Any], filters: Dict[str, Any]) -> bool:
        """Check if player meets team filtering criteria."""
        # Chance of playing filter
        chance_this = player_data.get('chance_of_playing_this_round')
        chance_next = player_data.get('chance_of_playing_next_round')
        chance = self.calculate_chance_of_playing(chance_this, chance_next)
        
        if chance < filters.get('min_chance_of_playing', 0):
            return False
        
        # Injury filter
        if filters.get('exclude_injured', True) and player_data.get('is_injured', False):
            return False
        
        # Minutes filter
        if player_data.get('minutes', 0) < filters.get('min_minutes', 0):
            return False
        
        # Price filter
        if player_data.get('now_cost', 0) / 10.0 > filters.get('max_price', float('inf')):
            return False
        
        # Form filter
        form = float(player_data.get('form', '0.0'))
        if form < filters.get('min_form', float('-inf')):
            return False
        
        # Position filter
        position_map = {1: 'GK', 2: 'DEF', 3: 'MID', 4: 'FWD'}
        position = position_map.get(player_data.get('element_type'), 'UNK')
        if position not in filters.get('positions', ['GK', 'DEF', 'MID', 'FWD']):
            return False
        
        return True
    
    def _create_player_from_data(self, player_data: Dict[str, Any], team_mapping: Dict[int, Team]) -> Player:
        """Create a Player object from FPL API data."""
        # Map FPL position IDs to our Position enum
        position_map = {1: Position.GK, 2: Position.DEF, 3: Position.MID, 4: Position.FWD}
        position = position_map.get(player_data.get('element_type'), Position.GK)
        
        # Get team info
        team_id = player_data['team']
        team_info = team_mapping.get(team_id, {'name': 'Unknown Team', 'short_name': 'UNK'})
        
        return Player(
            id=player_data['id'],
            first_name=player_data['first_name'],
            second_name=player_data['second_name'],
            team_id=team_id,
            element_type=player_data['element_type'],
            now_cost=player_data['now_cost'],
            total_points=player_data['total_points'],
            form=float(player_data.get('form', '0.0')),
            points_per_game=player_data.get('points_per_game', '0.0'),
            minutes=player_data.get('minutes', 0),
            selected_by_percent=player_data.get('selected_by_percent', '0.0'),
            xG=player_data.get('xG', '0.00'),
            xA=player_data.get('xA', '0.00'),
            xGC=player_data.get('xGC', '0.00'),
            xMins_pct=player_data.get('xMins_pct', 1.0)
        )
