"""
Lightweight LLM Strategy for team-specific analysis
"""

import logging
from typing import Dict, List
from datetime import datetime

from ..core.config import Config
from ..core.models import Player
from ..strategies.lightweight_llm_engine import LightweightLLMEngine

logger = logging.getLogger(__name__)


class LightweightLLMStrategy:
    """
    Lightweight LLM strategy for team-specific analysis.
    
    This class handles:
    - Team injury news analysis using lightweight LLM
    - Team hints and tips analysis using lightweight LLM
    - Prompt creation and orchestration
    """
    
    def __init__(self, config: Config):
        self.config = config
        self.llm_engine = LightweightLLMEngine(config)
        
        # Cache for FPL data to avoid repeated API calls
        self._cached_bootstrap_data = None
        self._cached_fixtures_data = None
        self._cached_current_gameweek = None
    
    def initialize_fpl_data(self):
        """Initialize FPL data cache to avoid repeated API calls during team processing"""
        if self._cached_bootstrap_data is None:
            logger.info("Initializing FPL data cache for lightweight LLM strategy...")
            from ..ingestion.fetch_fpl import FPLDataFetcher
            fetcher = FPLDataFetcher(self.config)
            
            self._cached_bootstrap_data = fetcher.get_fpl_static_data()
            self._cached_fixtures_data = fetcher.get_fixtures()
            self._cached_current_gameweek = fetcher.get_current_gameweek()
            
            if self._cached_current_gameweek is None:
                self._cached_current_gameweek = 1  # Fallback to GW1
                
            logger.info(f"FPL data cache initialized: GW{self._cached_current_gameweek}, "
                       f"{len(self._cached_fixtures_data)} fixtures, "
                       f"{len(self._cached_bootstrap_data.get('teams', []))} teams")
    
    def _get_fixture_info(self, team_name: str, current_gameweek: int) -> dict:
        """
        Get fixture information for a team in a specific gameweek.
        
        Args:
            team_name: Name of the team
            current_gameweek: Current gameweek number
            
        Returns:
            Dictionary containing fixture string, double gameweek status, and fixture difficulty
        """
        # Ensure FPL data is cached
        self.initialize_fpl_data()
        
        # Use cached data instead of making API calls
        fixtures_data = self._cached_fixtures_data
        teams_data = self._cached_bootstrap_data.get('teams', [])
        
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
    
    def get_team_injury_news(self, team_name: str, players: List[Player]) -> str:
        """
        Get injury news and playing likelihood for players in a specific team.
        
        Args:
            team_name: Name of the team
            players: List of players in the team
            
        Returns:
            String containing injury news for each player
        """
        # Ensure FPL data is cached
        self.initialize_fpl_data()
        
        # Use cached current gameweek
        current_gameweek = self._cached_current_gameweek
        
        # Get fixture information
        fixture_info = self._get_fixture_info(team_name, current_gameweek)
        
        # Create the prompt
        prompt = self._create_injury_news_prompt(team_name, players, current_gameweek, fixture_info)
        
        # Get LLM response
        return self.llm_engine.query_llm(prompt)
    
    def get_team_hints_tips(self, team_name: str, players: List[Player]) -> str:
        """
        Get hints, tips, and recommendations for players in a specific team.
        
        Args:
            team_name: Name of the team
            players: List of players in the team
            
        Returns:
            String containing hints, tips, and recommendations for each player
        """
        # Ensure FPL data is cached
        self.initialize_fpl_data()
        
        # Use cached current gameweek
        current_gameweek = self._cached_current_gameweek
        
        # Get fixture information
        fixture_info = self._get_fixture_info(team_name, current_gameweek)
        
        # Create the prompt
        prompt = self._create_hints_tips_prompt(team_name, players, current_gameweek, fixture_info)
        
        # Get LLM response
        return self.llm_engine.query_llm(prompt)
    
    def get_team_summary(self, team_name: str, players: List[Player]) -> Dict[str, str]:
        """
        Get both injury news and hints/tips for a team.
        
        Args:
            team_name: Name of the team
            players: List of players in the team
            
        Returns:
            Dictionary containing both injury news and hints/tips
        """
        logger.info(f"Getting team summary for {team_name}...")
        
        # Get both types of information
        injury_news = self.get_team_injury_news(team_name, players)
        hints_tips = self.get_team_hints_tips(team_name, players)
        
        return {
            'team_name': team_name,
            'injury_news': injury_news,
            'hints_tips': hints_tips,
            'player_count': len(players)
        }
    
    def _create_injury_news_prompt(self, team_name: str, players: List[Player], 
                                 current_gameweek: int, fixture_info: dict) -> str:
        """Create the injury news prompt"""
        # Format player list for the prompt
        player_list = self._format_players_for_prompt(players)
        
        # Get fixture information
        fixture_str = fixture_info['fixture_str']
        is_double_gameweek = fixture_info['is_double_gameweek']
        fixture_difficulty = fixture_info['fixture_difficulty']
        
        # Create double gameweek text
        double_gameweek_text = "This is a double gameweek." if is_double_gameweek else ""
        
        return f"""You're job is to collate the latest injury news on players in the {team_name} squad. The aim is to present the findings for use in an assessment of whether the players will be fit for the upcoming gameweek and will play in the matchday squad. Research the latest injury news and playing likelihood for {team_name} players.

This is gameweek {current_gameweek} of the 2025/2026 season and {team_name} are {fixture_str}. {double_gameweek_text} The fixture difficulty for {team_name} is {fixture_difficulty}. 

Current {team_name} squad:
{player_list}

For each player, provide a short sentence summarising the injury news and playing likelihood.

The short sentence should be of the format: INSERT_PLAYING_LIKELIHOOD - a short summary of the reason for the decision INSERT_PLAYING_LIKELIHOOD based on your research on the players availability for the gameweek.
For INSERT_PLAYING_LIKELIHOOD either Fit, Minor doubt, Major doubt, Out.

To make your decision, you should consider the following:
1. Current availability of the player as of gameweek {current_gameweek}. E.g., currently injured, currently suspended, currently on international duty, etc.
2. Current injury status of the player. E.g., minor injury, major injury, long term injury, etc.
3. Likelihood of playing in the next gameweek (percentage).
4. Expected return date.
5. Any relevant news or updates.
6. Any reasons for whether the player could be rested for the this gameweek.
7. Any reason the player is currently out of the squad and not included, e.g., long term suspension, banned,injury or personal issues.

Search for the most recent and reliable information from official sources, team announcements, and trusted football news outlets.

Format your response as a concise sentence for every player in the squad above, with the ouput formatted as a JSON object with the following structure:

{{
    "Player Name 1": "INSERT_PLAYING_LIKELIHOOD - a short summary of the reason for the decision INSERT_PLAYING_LIKELIHOOD based on your research on the players availability for the gameweek.",
    "Player Name 2": "INSERT_PLAYING_LIKELIHOOD - a short summary of the reason for the decision INSERT_PLAYING_LIKELIHOOD based on your research on the players availability for the gameweek.",
    ...
}}

Keep each player's information brief but informative."""
    
    def _create_hints_tips_prompt(self, team_name: str, players: List[Player], 
                                current_gameweek: int, fixture_info: dict) -> str:
        """Create the hints and tips prompt"""
        # Format player list for the prompt
        player_list = self._format_players_for_prompt(players)
        
        # Get fixture information
        fixture_str = fixture_info['fixture_str']
        is_double_gameweek = fixture_info['is_double_gameweek']
        fixture_difficulty = fixture_info['fixture_difficulty']
        
        # Create double gameweek text
        double_gameweek_text = "This is a double gameweek." if is_double_gameweek else ""
        
        return f"""You're job is to collate the latest fantasy premier league hints, tips and recommendations news on players in the {team_name} squad. The aim is to present the findings for use in an assessment of whether the players are great picks for the upcoming gameweek and will score big points. Research the latest hints, tips and recommendation for {team_name} players.

This is gameweek {current_gameweek} of the 2025/2026 season and {team_name} are facing {fixture_str}. {double_gameweek_text} The fixture difficulty for {team_name} is {fixture_difficulty}.

Current {team_name} squad:
{player_list}

For each player, provide a short sentence summarising the hints, tips and recommendations.

The short sentence should be of the format: INSERT_PLAYER_TIP_STATUS - a short summary of the reason for the decision INSERT_PLAYER_TIP_STATUS based on your research on the players hints, tips and recommendations for the gameweek.
For INSERT_PLAYER_TIP_STATUS either Must-have, Recommended, Avoid, Rotation risk.

To make your decision, you should consider the following:
1. Recent form and performance insights.
2. Expected role and playing time.
3. Set-piece responsibilities (if any).
4. Upcoming fixture analysis (including the current gameweek fixture).
5. Transfer recommendations (buy/hold/sell).
6. Any tactical insights or team news that could affect the player's FPL performance.

Search for the most recent and reliable information from official sources, team announcements, and trusted football news outlets.

Use hints, tips and recommendations you discover first and foremost, but if you think the stats help support the decision, then use them.

Format your response as a concise sentence for every player in the squad above, with the ouput formatted as a JSON object with the following structure:

{{
    "Player Name 1": "INSERT_PLAYER_TIP_STATUS - a short summary of the reason for the decision INSERT_PLAYER_TIP_STATUS based on your research on the players hints, tips and recommendations for the gameweek.",
    "Player Name 2": "INSERT_PLAYER_TIP_STATUS - a short summary of the reason for the decision INSERT_PLAYER_TIP_STATUS based on your research on the players hints, tips and recommendations for the gameweek.",
    ...
}}

Keep each player's information brief but informative."""
    
    def _format_players_for_prompt(self, players: List[Player]) -> str:
        """Format player list for LLM prompts"""
        formatted_players = []
        
        for player in players:
            # Get additional stats if available
            ppg = player.custom_data.get('ppg', player.points_per_game)
            form = player.custom_data.get('form', player.form)
            ownership = player.custom_data.get('ownership_percent', player.selected_by_percent)
            
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
                f"- {player.name} ({player.position.value}, £{player.price}m, "
                f"PPG: {ppg_float:.1f}, Form: {form_float:.1f}, "
                f"Ownership: {ownership_float:.1f}%)"
            )
        
        return "\n".join(formatted_players) 