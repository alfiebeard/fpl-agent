"""
Data processor for transforming and enriching FPL API data.
"""

import logging
from typing import Dict, List, Any, Optional

from ..core.config import Config
from .fetch_fpl import FPLDataFetcher
from ..utils.prompt_formatter import PromptFormatter

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
    
    def process_fpl_data(self, bootstrap_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process raw FPL bootstrap data into structured player data.
        
        Args:
            bootstrap_data: Raw data from FPL bootstrap-static endpoint
            
        Returns:
            Dict with:
              - players: processed player data keyed by full name
              - fpl_current_gameweek / fpl_next_gameweek: event IDs from bootstrap
                (used later to resolve chance_of_playing for a CLI --gameweek)
        """
        logger.info("Processing FPL bootstrap data...")
        
        # Create team ID to name mapping
        team_mapping = self._create_team_mapping(bootstrap_data)
        availability_context = self.get_availability_context(bootstrap_data)
        
        # Process players
        processed_players = {}
        for player_data in bootstrap_data.get('elements', []):
            try:
                full_name = f"{player_data['first_name']} {player_data['second_name']}"
                processed_players[full_name] = self._process_player(player_data, team_mapping)
            except Exception as e:
                logger.warning(f"Failed to process player {player_data.get('id', 'unknown')}: {e}")
                continue
        
        logger.info(f"Processed {len(processed_players)} players")
        return {
            'players': processed_players,
            'fpl_current_gameweek': availability_context['fpl_current_gameweek'],
            'fpl_next_gameweek': availability_context['fpl_next_gameweek'],
        }

    @staticmethod
    def get_availability_context(bootstrap_data: Dict[str, Any]) -> Dict[str, Optional[int]]:
        """Extract FPL current/next gameweek IDs from bootstrap events."""
        current_gw = None
        next_gw = None
        for event in bootstrap_data.get('events', []):
            if event.get('is_current'):
                current_gw = event.get('id')
            if event.get('is_next'):
                next_gw = event.get('id')
        return {
            'fpl_current_gameweek': current_gw,
            'fpl_next_gameweek': next_gw,
        }

    @staticmethod
    def normalize_chance_value(value: Optional[Any]) -> Optional[float]:
        """Normalize an FPL chance_of_playing_* field to float or None."""
        if value is None or value == '':
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    def resolve_chance_of_playing(
        self,
        this_round: Optional[Any],
        next_round: Optional[Any],
        gameweek: Optional[int] = None,
        fpl_current_gameweek: Optional[int] = None,
        fpl_next_gameweek: Optional[int] = None,
        fallback_chance: Optional[Any] = None,
    ) -> float:
        """
        Resolve a single chance_of_playing % for a target gameweek.

        FPL only exposes this_round / next_round. We map the CLI --gameweek onto
        those fields using the bootstrap current/next event IDs captured at fetch.
        """
        this_val = self.normalize_chance_value(this_round)
        next_val = self.normalize_chance_value(next_round)
        fallback_val = self.normalize_chance_value(fallback_chance)

        if gameweek is not None and fpl_current_gameweek is not None and gameweek == fpl_current_gameweek:
            preferred, secondary = this_val, next_val
        elif gameweek is not None and fpl_next_gameweek is not None and gameweek == fpl_next_gameweek:
            preferred, secondary = next_val, this_val
        elif gameweek is not None and fpl_next_gameweek is not None and gameweek > fpl_next_gameweek:
            # Best forward-looking estimate FPL gives us
            preferred, secondary = next_val, this_val
        elif gameweek is not None and fpl_current_gameweek is not None and gameweek < fpl_current_gameweek:
            preferred, secondary = this_val, next_val
        else:
            # No usable mapping (old cache / missing context): prefer next for planning
            preferred, secondary = next_val, this_val

        for value in (preferred, secondary, fallback_val):
            if value is not None:
                return value
        return 100.0

    def apply_chance_of_playing_for_gameweek(
        self,
        players_data: Dict[str, Dict[str, Any]],
        gameweek: Optional[int],
        fpl_current_gameweek: Optional[int] = None,
        fpl_next_gameweek: Optional[int] = None,
    ) -> Dict[str, Dict[str, Any]]:
        """Set chance_of_playing on each player for the given gameweek (in place)."""
        for player_data in players_data.values():
            player_data['chance_of_playing'] = self.resolve_chance_of_playing(
                this_round=player_data.get('chance_of_playing_this_round'),
                next_round=player_data.get('chance_of_playing_next_round'),
                gameweek=gameweek,
                fpl_current_gameweek=fpl_current_gameweek,
                fpl_next_gameweek=fpl_next_gameweek,
                fallback_chance=player_data.get('chance_of_playing'),
            )
        return players_data

    def process_fixtures_data(self, raw_fixtures: List[Dict[str, Any]], teams_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Process raw fixtures data, converting team IDs to team names.
        
        Args:
            raw_fixtures: Raw fixtures data from FPL API
            teams_data: Teams data from FPL API
            
        Returns:
            List of processed fixtures with team names as strings
        """
        logger.info("Processing FPL fixtures data...")
        
        # Create team ID to name mapping
        team_id_map = {}
        for team in teams_data:
            if isinstance(team, dict) and 'id' in team and 'name' in team:
                team_id_map[team['id']] = team['name']
        
        processed_fixtures = []
        for fixture in raw_fixtures:
            try:
                processed_fixtures.append({
                    'event': fixture.get('event'),
                    'team_h': team_id_map.get(fixture.get('team_h'), 'Unknown'),
                    'team_a': team_id_map.get(fixture.get('team_a'), 'Unknown'),
                    'kickoff_time': fixture.get('kickoff_time'),
                    'finished': fixture.get('finished', False),
                    'team_h_difficulty': fixture.get('team_h_difficulty', 3),
                    'team_a_difficulty': fixture.get('team_a_difficulty', 3)
                })
            except Exception as e:
                logger.warning(f"Failed to process fixture {fixture.get('id', 'unknown')}: {e}")
                continue
        
        logger.info(f"Processed {len(processed_fixtures)} fixtures")
        return processed_fixtures
    
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
        
        # Store both FPL chance fields; resolve to a single chance_of_playing later
        # once we know which --gameweek the caller is planning for.
        chance_this = self.normalize_chance_value(
            player_data.get('chance_of_playing_this_round')
        )
        chance_next = self.normalize_chance_value(
            player_data.get('chance_of_playing_next_round')
        )
        # Provisional value until apply_chance_of_playing_for_gameweek runs
        chance_of_playing = self.resolve_chance_of_playing(
            this_round=chance_this,
            next_round=chance_next,
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
            'now_cost': player_data['now_cost'],
            'total_points': player_data['total_points'],
            'points_per_game': player_data['points_per_game'],
            'form': form,
            'minutes': player_data['minutes'],
            'goals_scored': player_data['goals_scored'],
            'assists': player_data['assists'],
            'clean_sheets': player_data['clean_sheets'],
            'goals_conceded': player_data['goals_conceded'],
            'own_goals': player_data['own_goals'],
            'penalties_saved': player_data['penalties_saved'],
            'penalties_missed': player_data['penalties_missed'],
            'yellow_cards': player_data['yellow_cards'],
            'red_cards': player_data['red_cards'],
            'saves': player_data['saves'],
            'bonus': player_data['bonus'],
            'bps': player_data['bps'],
            'influence': player_data['influence'],
            'creativity': player_data['creativity'],
            'threat': player_data['threat'],
            'ict_index': player_data['ict_index'],
            'status': player_data['status'],
            'chance_of_playing_this_round': chance_this,
            'chance_of_playing_next_round': chance_next,
            'chance_of_playing': chance_of_playing,
            'news': player_data.get('news', ''),
            'transfers_in': player_data['transfers_in'],
            'transfers_out': player_data['transfers_out'],
            'transfers_in_event': player_data['transfers_in_event'],
            'transfers_out_event': player_data['transfers_out_event'],
            'value_form': player_data['value_form'],
            'value_season': player_data['value_season'],
            'selected_by_percent': player_data['selected_by_percent']
        }
        
        return processed_player
    
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
    
    def get_gameweek_fixtures(self, gameweek: int, fixtures_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Get all fixtures for a specific gameweek from cached fixtures data.
        
        Args:
            gameweek: Gameweek number
            fixtures_data: Cached fixtures data
            
        Returns:
            List of fixtures for the specified gameweek
        """
        if not fixtures_data:
            return []
        
        # Filter fixtures for the specific gameweek
        gameweek_fixtures = []
        for fixture in fixtures_data:
            if fixture.get('event') == gameweek:
                gameweek_fixtures.append(fixture)
        
        return gameweek_fixtures
    
    def format_players_by_position_ranked(self, players_data: Dict[str, Dict[str, Any]], 
                                         use_embeddings: bool = False, 
                                         include_rankings: bool = None,
                                         include_scores: bool = False) -> str:
        """
        Format players grouped by position with rankings - used by both show-players and LLM prompts.
        This method produces the EXACT same format as show-players.
        
        Args:
            players_data: Dictionary of player data
            use_embeddings: Whether embedding filtering was used
            include_rankings: Whether to include ranking numbers (None=use config default, True/False=override)
            include_scores: Whether to include embedding scores (for show-players with embeddings)
            
        Returns:
            Formatted string with players grouped by position and ranked
        """
        # Get default from config if not specified
        if include_rankings is None:
            include_rankings = self.config.get_display_config().get('include_rankings_in_prompts', True)
        
        formatted_lines = []
        
        # Group by position
        position_groups = {}
        for name, data in players_data.items():
            position = data.get('position', 'UNK')
            if position not in position_groups:
                position_groups[position] = []
            position_groups[position].append((name, data))
        
        # Sort positions in standard order
        position_order = ['GK', 'DEF', 'MID', 'FWD']
        
        for position in position_order:
            if position in position_groups:
                players = position_groups[position]
                
                # Sort players by the appropriate metric
                if include_scores and use_embeddings:
                    # When showing embedding scores, sort by hybrid score for consistency
                    def hybrid_sort_key(player_tuple):
                        name, data = player_tuple
                        try:
                            hybrid_score = float(data.get('hybrid_score', 0) or 0)
                            return hybrid_score
                        except (ValueError, TypeError):
                            return 0.0
                    
                    players.sort(key=hybrid_sort_key, reverse=True)
                else:
                    # Default sorting by PPG + Form (same as show-players)
                    def safe_sort_key(player_tuple):
                        name, data = player_tuple
                        try:
                            ppg = float(data.get('pp90', 0) or 0)
                            form = float(data.get('form', 0) or 0)
                            cost = float(data.get('now_cost', 0) or 0)
                            return (ppg + form / 10, cost)
                        except (ValueError, TypeError):
                            # Fallback to safe values if conversion fails
                            return (0.0, 0.0)
                    
                    players.sort(key=safe_sort_key, reverse=True)
                
                formatted_lines.append(f"\n{position} ({len(players)} players):")
                
                for i, (name, data) in enumerate(players, 1):
                    # Use unified player formatter
                    player_info = PromptFormatter.format_player(
                        data,
                        format_type="detailed",
                        include_rankings=include_rankings,
                        include_scores=include_scores and use_embeddings,
                        player_index=i if include_rankings else None
                    )
                    formatted_lines.append(player_info)
                    
                    # Add empty line between players for better readability
                    formatted_lines.append("")
        
        return "\n".join(formatted_lines)
