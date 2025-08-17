"""
Data processor for transforming and enriching FPL API data.
"""

import logging
from typing import Dict, List, Any, Optional

from ..core.config import Config
from .fetch_fpl import FPLDataFetcher
from .embedding_filter import EmbeddingFilter

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
            Dictionary of processed player data keyed by full name
        """
        logger.info("Processing FPL bootstrap data...")
        
        # Create team ID to name mapping
        team_mapping = self._create_team_mapping(bootstrap_data)
        
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
        return processed_players

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
                    'finished': fixture.get('finished', False)
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
    
    def _calculate_chance_of_playing(self, this_round: Optional[Any], next_round: Optional[Any]) -> float:
        """
        Calculate chance of playing based on FPL data.
        
        Args:
            this_round: Chance of playing this round
            next_round: Chance of playing next round
            
        Returns:
            Chance of playing as a percentage (0-100)
        """
        # Use this round if available, otherwise next round, otherwise 100%
        if this_round is not None and this_round != '':
            return float(this_round)
        elif next_round is not None and next_round != '':
            return float(next_round)
        else:
            return 100.0
    
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
    
    def get_available_players(self, players_data: Dict[str, Dict[str, Any]], 
                            min_minutes: int = 0, 
                            max_price: Optional[float] = None,
                            positions: Optional[List[str]] = None) -> Dict[str, Dict[str, Any]]:
        """
        Get available players based on criteria.
        
        Args:
            players_data: Dictionary of player data
            min_minutes: Minimum minutes played
            max_price: Maximum price in millions
            positions: List of positions to include
            
        Returns:
            Filtered dictionary of available players
        """
        available_players = {}
        
        for player_name, player_data in players_data.items():
            # Check minutes
            if player_data.get('minutes', 0) < min_minutes:
                continue
            
            # Check price
            if max_price is not None:
                player_price = player_data.get('now_cost', 0) / 10.0  # Convert to millions
                if player_price > max_price:
                    continue
            
            # Check position
            if positions and player_data.get('position') not in positions:
                continue
            
            available_players[player_name] = player_data
        
        return available_players
    
    def enrich_player_data_by_teams(self, players_data: Dict[str, Dict[str, Any]], team_analysis_strategy=None) -> Dict[str, Dict[str, Any]]:
        """
        Enrich player data using team_analysis_strategy per-team approach.
        
        Args:
            players_data: Dictionary of player data keyed by full name
            team_analysis_strategy: TeamAnalysisStrategy instance for LLM queries
            
        Returns:
            Enriched player data with expert_insights and injury_news attributes
        """
        if not team_analysis_strategy:
            raise ValueError("team_analysis_strategy is required for enrichment")
            
        logger.info("Starting team-based player enrichment...")
        
        # Group players by team
        team_players = self._group_players_by_team(players_data)
        
        # Get list of Premier League teams
        premier_league_teams = list(team_players.keys())
        total_teams = len(premier_league_teams)
        
        logger.info(f"Processing {total_teams} Premier League teams for enrichment")
        
        # Get current gameweek
        current_gameweek = self.fetcher.get_current_gameweek()
        if current_gameweek is None:
            current_gameweek = 1  # Fallback to GW1
        
        # Process each team sequentially
        for i, team_name in enumerate(premier_league_teams, 1):
            try:
                logger.info(f"Processing team {i}/{total_teams}: {team_name}")
                print(f"🔄 Processing {team_name}... ({i}/{total_teams} teams)")
                
                # Get players for this team
                team_player_list = team_players[team_name]
                
                # Get fixture information for this team
                fixture_info = self._get_fixture_info(team_name, current_gameweek)
                
                # Format players for prompts
                formatted_players = self._format_players_for_prompt(team_player_list)
                
                # Get expert insights from strategy (LLM logic)
                try:
                    expert_insights = team_analysis_strategy.get_team_hints_tips(team_name, formatted_players, current_gameweek, fixture_info)
                    print(f"   ✅ Expert insights added for {team_name}")
                except Exception as e:
                    logger.error(f"Failed to get expert insights for {team_name}: {e}")
                    print(f"   ❌ Expert insights failed for {team_name}: {e}")
                    expert_insights = {player['full_name']: "No expert insights available" for player in team_player_list}
                
                # Get injury news from strategy (LLM logic)
                try:
                    injury_news = team_analysis_strategy.get_team_injury_news(team_name, formatted_players, current_gameweek, fixture_info)
                    print(f"   ✅ Injury news added for {team_name}")
                except Exception as e:
                    logger.error(f"Failed to get injury news for {team_name}: {e}")
                    print(f"   ❌ Injury news failed for {team_name}: {e}")
                    injury_news = {player['full_name']: "No injury news available" for player in team_player_list}
                
                # Apply enriched data to players (Data processing logic)
                try:
                    self._apply_enriched_data_to_players(players_data, team_player_list, expert_insights, injury_news)
                    print(f"   ✅ Team data enriched for {team_name}")
                except Exception as e:
                    logger.error(f"Failed to apply enriched data for {team_name}: {e}")
                    print(f"   ❌ Data application failed for {team_name}: {e}")
                
            except Exception as e:
                logger.error(f"Failed to process team {team_name}: {e}")
                print(f"   ❌ Team processing failed for {team_name}: {e}")
                continue
        
        logger.info("Team-based player enrichment completed")
        return players_data
    
    def _group_players_by_team(self, players_data: Dict[str, Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """Group players by team name."""
        team_players = {}
        
        for player_name, player_data in players_data.items():
            team_name = player_data.get('team_name', 'Unknown Team')
            if team_name not in team_players:
                team_players[team_name] = []
            team_players[team_name].append(player_data)
        
        return team_players
    
    def _apply_enriched_data_to_players(self, players_data: Dict[str, Dict[str, Any]], 
                                      team_players: List[Dict[str, Any]], 
                                      expert_insights: Dict[str, str],
                                      injury_news: Dict[str, str]) -> None:
        """
        Apply enriched data (expert insights and injury news) to player data.
        
        Args:
            players_data: Dictionary of all player data
            team_players: List of players for this team
            expert_insights: Dictionary mapping player names to expert insights
            injury_news: Dictionary mapping player names to injury news
        """
        for player in team_players:
            player_name = player['full_name']
            if player_name in players_data:
                # Add expert insights
                players_data[player_name]['expert_insights'] = expert_insights.get(
                    player_name, "No expert insights available"
                )
                # Add injury news
                players_data[player_name]['injury_news'] = injury_news.get(
                    player_name, "No injury news available"
                )
    
    def _get_fixture_info(self, team_name: str, current_gameweek: int) -> dict:
        """
        Get fixture information for a team in a specific gameweek.
        
        Args:
            team_name: Name of the team
            current_gameweek: Current gameweek number
            
        Returns:
            Dictionary containing fixture string, double gameweek status, and fixture difficulty
        """
        # Get fixtures data from the fetcher
        fixtures_data = self.fetcher.get_fixtures()
        teams_data = self.fetcher.get_fpl_static_data().get('teams', [])
        
        # Create team name to ID mapping
        team_id_map = {}
        for team in teams_data:
            if isinstance(team, dict) and 'name' in team and 'id' in team:
                team_id_map[team['name']] = team['id']
        
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
                        from datetime import datetime
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
    
    def format_fixtures_for_prompt(self, fixtures: List[Dict[str, Any]], gameweek: int) -> str:
        """
        Format fixtures into a clean, organized string for prompts.
        
        Args:
            fixtures: List of fixtures for the gameweek
            gameweek: Gameweek number
            
        Returns:
            Formatted string of fixtures grouped by date
        """
        if not fixtures:
            return f"No fixtures scheduled for Gameweek {gameweek}."
        
        def get_ordinal_suffix(day):
            """Get the correct ordinal suffix for a day number"""
            if 10 <= day % 100 <= 20:
                suffix = 'th'
            else:
                suffix = {1: 'st', 2: 'nd', 3: 'rd'}.get(day % 10, 'th')
            return suffix
        
        # Group fixtures by date
        fixtures_by_date = {}
        for fixture in fixtures:
            try:
                from datetime import datetime
                kickoff_time = fixture['kickoff_time']
                if kickoff_time:
                    # Parse the ISO format date from FPL API
                    fixture_date = datetime.fromisoformat(kickoff_time.replace('Z', '+00:00'))
                    day = fixture_date.day
                    suffix = get_ordinal_suffix(day)
                    date_key = fixture_date.strftime(f'%A %d{suffix} %B %Y')
                    
                    if date_key not in fixtures_by_date:
                        fixtures_by_date[date_key] = []
                    
                    fixtures_by_date[date_key].append(fixture)
            except:
                # Fallback if date parsing fails
                if 'Unknown Date' not in fixtures_by_date:
                    fixtures_by_date['Unknown Date'] = []
                fixtures_by_date['Unknown Date'].append(fixture)
        
        # Format the output
        output = [f"GAMEWEEK {gameweek} FIXTURES:", "=" * 30, ""]
        
        for date, date_fixtures in fixtures_by_date.items():
            output.append(f"{date}:")
            for fixture in date_fixtures:
                # team_h and team_a are already strings!
                output.append(f"• {fixture['team_h']} vs {fixture['team_a']}")
            output.append("")
        
        return "\n".join(output)
    
    def _format_players_for_prompt(self, team_players: List[Dict[str, Any]]) -> str:
        """Format player list for LLM prompts"""
        formatted_players = []
        
        for player in team_players:
            # Get player stats
            ppg = player.get('points_per_game', 0)
            form = player.get('form', 0)
            ownership = player.get('selected_by_percent', 0)
            price = player.get('now_cost', 0) / 10.0  # Convert to millions
            
            # Convert to float for formatting, handling string values
            try:
                ppg_float = float(ppg) if ppg is not None else 0.0
            except (ValueError, TypeError):
                ppg_float = 0.0
            
            try:
                form_float = float(form) if form is not None else 0.0
            except (ValueError, TypeError):
                form_float = 0.0
            
            try:
                ownership_float = float(ownership) if ownership is not None else 0.0
            except (ValueError, TypeError):
                ownership_float = 0.0
            
            formatted_players.append(
                f"- {player['full_name']} ({player['position']}, £{price:.1f}m, "
                f"PPG: {ppg_float:.1f}, Form: {form_float:.1f}, "
                f"Ownership: {ownership_float:.1f}%)"
            )
        
        return "\n".join(formatted_players)
    
    def filter_available_players(self, players_data: Dict[str, Dict[str, Any]], 
                               use_embeddings: bool = False) -> Dict[str, Dict[str, Any]]:
        """
        Filter players for availability and optionally embeddings.
        Used for both team building and gameweek updates.
        
        Args:
            players_data: Dictionary of player data
            use_embeddings: Whether to use embedding-based filtering
            
        Returns:
            Filtered player data
        """
        logger.info("Starting player filtering for team building...")
        
        # Step 1: Basic filtering - remove players who can't play
        available_players = self._filter_available_players(players_data)
        logger.info(f"Basic filtering: {len(available_players)} players available from {len(players_data)} total")
        
        # Step 2: Injury news filtering (only if enrichments available)
        if self._has_enrichments(available_players):
            available_players = self._filter_by_injury_news(available_players)
            logger.info(f"Injury news filtering: {len(available_players)} players available after injury filtering")
        
        if not use_embeddings:
            logger.info("Embedding filtering disabled, returning all available players")
            return available_players
        
        # Step 3: Check if enrichments exist
        enriched_players = self._get_enriched_players(available_players)
        if not enriched_players:
            logger.info("No enrichments found, returning all available players")
            return available_players
        
        # Step 3: Apply embedding filtering
        try:
            embedding_filter = EmbeddingFilter(self.config)
            filtered_players = embedding_filter.filter_players_by_position(enriched_players, available_players)
            
            # Get the filtered player names and return their full data
            filtered_player_names = list(filtered_players.keys())
            final_filtered_data = {
                name: available_players[name] 
                for name in filtered_player_names 
                if name in available_players
            }
            
            logger.info(f"Embedding filtering: {len(final_filtered_data)} players selected from {len(available_players)} available")
            return final_filtered_data
            
        except Exception as e:
            logger.error(f"Embedding filtering failed: {e}")
            logger.info("Falling back to all available players")
            return available_players
    
    def _filter_available_players(self, players_data: Dict[str, Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        """Filter out players who can't play (injured, suspended)"""
        available_players = {}
        
        for player_name, player_data in players_data.items():
            # Check chance of playing (25% threshold)
            chance_of_playing = player_data.get('chance_of_playing', 100)
            if chance_of_playing is not None and chance_of_playing < 25:
                continue
            
            # Note: We don't filter by minutes=0 as new signings/backup players
            # might not have played yet but could still be viable FPL options
            
            available_players[player_name] = player_data
        
        return available_players
    
    def _get_enriched_players(self, players_data: Dict[str, Dict[str, Any]]) -> Dict[str, str]:
        """Extract enriched data for embedding filtering"""
        enriched_data = {}
        
        for player_name, player_data in players_data.items():
            # Combine expert insights and injury news
            expert_insights = player_data.get('expert_insights', '')
            injury_news = player_data.get('injury_news', '')
            
            if expert_insights or injury_news:
                enriched_text = f"{expert_insights} {injury_news}".strip()
                enriched_data[player_name] = enriched_text
        
        return enriched_data
    
    def _has_enrichments(self, players_data: Dict[str, Dict[str, Any]]) -> bool:
        """Check if players have enriched data (expert insights or injury news)"""
        for player_data in players_data.values():
            if player_data.get('expert_insights') or player_data.get('injury_news'):
                return True
        return False
    
    def _filter_by_injury_news(self, players_data: Dict[str, Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        """Filter out players marked as 'Out' in injury news"""
        available_players = {}
        
        for player_name, player_data in players_data.items():
            # Use the existing keyword extraction system
            injury_status = self._extract_injury_status(player_name, {player_name: player_data})
            
            # If we can't determine status or player is NOT "out", include them
            if not injury_status or injury_status != "out":
                available_players[player_name] = player_data
            # If marked as "out", filter them out
        
        return available_players
    
    def _extract_injury_status(self, player_name: str, structured_data: Dict) -> str:
        """Extract injury status from injury_news - only care about 'Out'"""
        status_map = {
            "out": "out"  # Only filter out "Out" players
        }
        return self._extract_keyword_status(player_name, structured_data, 'injury_news', status_map)
    
    def _extract_keyword_status(self, player_name: str, structured_data: Dict, 
                               field_name: str, keyword_map: Dict[str, Any]) -> Any:
        """Extract keyword status from the first keyword before the dash"""
        try:
            if player_name in structured_data:
                field_text = structured_data[player_name].get(field_name, '')
                if field_text and ' - ' in field_text:  # Look for space-dash-space
                    # Split on first occurrence of " - " (space-dash-space)
                    first_part = field_text.split(' - ', 1)[0].strip().lower()
                    
                    # Look for exact keyword match in the first part
                    for keyword, value in keyword_map.items():
                        if first_part == keyword.lower():
                            return value
            
            return None  # Default if no keyword found
            
        except Exception as e:
            logger.warning(f"Failed to extract keyword status for {player_name}: {e}")
            return None
    
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
                    price = float(data.get('now_cost', 0) or 0) / 10.0
                    ppg = float(data.get('pp90', 0) or 0)
                    form = float(data.get('form', 0) or 0)
                    ownership = float(data.get('selected_by_percent', 0) or 0)
                    team_name = data.get('team_name', 'Unknown')
                    
                    # Format the ranking prefix
                    if include_rankings:
                        prefix = f"{i:2d}. "
                    else:
                        prefix = "• "
                    
                    # Player line (exactly like show-players)
                    # Add chance of playing after ownership
                    chance = data.get('chance_of_playing', 100)
                    if chance is None or chance == '':
                        chance = 100
                    else:
                        try:
                            chance = float(chance)
                        except (ValueError, TypeError):
                            chance = 100
                    
                    player_line = f"{prefix}{name} ({team_name}, £{price:.1f}m, PPG: {ppg:.1f}, Form: {form:.1f}, Ownership: {ownership:.1f}%, Chance: {chance:.0f}%)"
                    formatted_lines.append(player_line)
                    
                    # Score line (if using embeddings and scores requested)
                    if include_scores and use_embeddings:
                        # Try to get embedding scores if available
                        embedding_score = data.get('embedding_score', 0.0)
                        keyword_bonus = data.get('keyword_bonus', 0.0)
                        hybrid_score = embedding_score + keyword_bonus
                        
                        score_line = f"         Score: {hybrid_score:.3f} (Embedding: {embedding_score:.3f}, Bonus: {keyword_bonus:+.3f})"
                        formatted_lines.append(score_line)
                    
                    # Expert insights line (if available and using embeddings)
                    if use_embeddings and data.get('expert_insights'):
                        expert_line = f"         Expert Insights: {data['expert_insights']}"
                        formatted_lines.append(expert_line)
                    
                    # Injury news line (if available and using embeddings)
                    if use_embeddings and data.get('injury_news'):
                        injury_line = f"         Injury News: {data['injury_news']}"
                        formatted_lines.append(injury_line)
                    
                    # Add empty line between players for better readability
                    formatted_lines.append("")
        
        return "\n".join(formatted_lines)
    
    def format_players_for_llm_prompt(self, players_data: Dict[str, Dict[str, Any]], 
                                    use_embeddings: bool = False) -> str:
        """
        Format players for LLM prompts with position grouping and rankings.
        
        Args:
            players_data: Dictionary of player data
            use_embeddings: Whether embedding filtering was used
            
        Returns:
            Formatted string for LLM prompt
        """
        # Use the common formatting method with config default for rankings and scores when using embeddings
        return self.format_players_by_position_ranked(
            players_data, 
            use_embeddings=use_embeddings, 
            include_rankings=None,  # Use config default
            include_scores=use_embeddings  # Include scores when using embeddings (same as show-players)
        )
