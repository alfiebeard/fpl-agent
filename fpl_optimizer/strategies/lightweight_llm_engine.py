"""
Lightweight LLM engine for team-specific player information
"""

import logging
import json
from typing import Dict, List, Any, Optional

from google import genai
from google.genai import types

from ..core.config import Config
from ..core.models import Player

logger = logging.getLogger(__name__)


class LightweightLLMEngine:
    """
    Lightweight LLM engine for team-specific player information.
    
    This class handles:
    - Lightweight Gemini model (Flash-Lite) for cost-effective queries
    - Web search integration for current team news and tips
    - Team-specific player analysis (injuries, hints, tips)
    """
    
    def __init__(self, config: Config):
        self.config = config
        self.llm_config = config.get_lightweight_llm_config()
        self.model_name = self.llm_config.get('model', 'gemini-2.5-flash-lite')
        
        # Initialize Gemini client and search config
        self.model = self._initialize_gemini_model()

    def _initialize_gemini_model(self):
        """Initialize the Gemini client and search config"""
        api_key = self.config.get_env_var('GEMINI_API_KEY')
        
        try:
            client = genai.Client(api_key=api_key)

            # Define the grounding tool for web search
            grounding_tool = types.Tool(
                google_search=types.GoogleSearch()
            )

            # Configure generation settings for lightweight model
            generation_config = types.GenerateContentConfig(
                tools=[grounding_tool],
                temperature=self.llm_config.get('temperature', 0.2),
                max_output_tokens=self.llm_config.get('max_output_tokens', 8192),
                top_p=self.llm_config.get('top_p', 0.8),
                top_k=self.llm_config.get('top_k', 25)
            )
            
            # Store client and config for later use
            self.client = client
            self.generation_config = generation_config
            return True

        except Exception as e:
            logger.error(f"Failed to initialize lightweight Gemini model: {e}")
            return None
    
    def get_team_injury_news(self, team_name: str, players: List[Player]) -> str:
        """
        Get injury news and playing likelihood for players in a specific team.
        
        Args:
            team_name: Name of the team
            players: List of players in the team
            
        Returns:
            String containing injury news for each player
        """
        # Get current gameweek and opponent information
        from ..ingestion.fetch_fpl import FPLDataFetcher
        fetcher = FPLDataFetcher(self.config)
        
        # Get current gameweek
        current_gameweek = fetcher.get_current_gameweek()
        if current_gameweek is None:
            current_gameweek = 1  # Fallback to GW1 if not available
        
        # Get fixtures to find opponents for this gameweek
        fixtures_data = fetcher.get_fixtures()
        teams_data = fetcher.get_bootstrap_data().get('teams', [])
        
        # Create team name to ID mapping
        team_id_map = {team['name']: team['id'] for team in teams_data}
        team_id = team_id_map.get(team_name)
        
        # Find opponents for this gameweek
        opponents = []
        for fixture_data in fixtures_data:
            if fixture_data.get('event') == current_gameweek:
                home_team_id = fixture_data.get('team_h')
                away_team_id = fixture_data.get('team_a')
                
                # Get fixture date
                kickoff_time = fixture_data.get('kickoff_time')
                if kickoff_time:
                    try:
                        # Parse the ISO format date from FPL API
                        from datetime import datetime
                        fixture_date = datetime.fromisoformat(kickoff_time.replace('Z', '+00:00'))
                        # Format as "22nd May 2025"
                        day = fixture_date.day
                        suffix = 'th' if 11 <= day <= 13 else {1: 'st', 2: 'nd', 3: 'rd'}.get(day % 10, 'th')
                        formatted_date = f"{day}{suffix} {fixture_date.strftime('%B %Y')}"
                    except:
                        formatted_date = "TBD"
                else:
                    formatted_date = "TBD"
                
                if home_team_id == team_id:
                    # Team is playing away
                    away_team_name = next((team['name'] for team in teams_data if team['id'] == away_team_id), 'Unknown')
                    opponents.append(f"away to {away_team_name} on {formatted_date}")
                elif away_team_id == team_id:
                    # Team is playing home
                    home_team_name = next((team['name'] for team in teams_data if team['id'] == home_team_id), 'Unknown')
                    opponents.append(f"home to {home_team_name} on {formatted_date}")
        
        # Format opponent string
        if opponents:
            if len(opponents) == 1:
                opponent_str = opponents[0]
            else:
                # Double gameweek
                opponent_str = f"double gameweek: {' and '.join(opponents)}"
        else:
            opponent_str = "no fixture scheduled"
        
        # Format player list for the prompt
        player_list = self._format_players_for_prompt(players)
        
        prompt = f"""You're job is to collate the latest injury news on players in the {team_name} squad. The aim is to present the findings for use in an assessment of whether the players will be fit for the upcoming gameweek and will play in the matchday squad. Research the latest injury news and playing likelihood for {team_name} players.

This is gameweek {current_gameweek} and {team_name} are {opponent_str}.

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

        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=self.generation_config
            )
            return response.text
        except Exception as e:
            logger.error(f"Failed to get injury news for {team_name}: {e}")
            return f"Error: Could not fetch injury news for {team_name}"
    
    def get_team_hints_tips(self, team_name: str, players: List[Player]) -> str:
        """
        Get hints, tips, and recommendations for players in a specific team.
        
        Args:
            team_name: Name of the team
            players: List of players in the team
            
        Returns:
            String containing hints, tips, and recommendations for each player
        """
        # Get current gameweek and opponent information
        from ..ingestion.fetch_fpl import FPLDataFetcher
        fetcher = FPLDataFetcher(self.config)
        
        # Get current gameweek
        current_gameweek = fetcher.get_current_gameweek()
        if current_gameweek is None:
            current_gameweek = 1  # Fallback to GW1 if not available
        
        # Get fixtures to find opponents for this gameweek
        fixtures_data = fetcher.get_fixtures()
        teams_data = fetcher.get_bootstrap_data().get('teams', [])
        
        # Create team name to ID mapping
        team_id_map = {team['name']: team['id'] for team in teams_data}
        team_id = team_id_map.get(team_name)
        
        # Find opponents for this gameweek
        opponents = []
        for fixture_data in fixtures_data:
            if fixture_data.get('event') == current_gameweek:
                home_team_id = fixture_data.get('team_h')
                away_team_id = fixture_data.get('team_a')
                
                # Get fixture date
                kickoff_time = fixture_data.get('kickoff_time')
                if kickoff_time:
                    try:
                        # Parse the ISO format date from FPL API
                        from datetime import datetime
                        fixture_date = datetime.fromisoformat(kickoff_time.replace('Z', '+00:00'))
                        # Format as "22nd May 2025"
                        day = fixture_date.day
                        suffix = 'th' if 11 <= day <= 13 else {1: 'st', 2: 'nd', 3: 'rd'}.get(day % 10, 'th')
                        formatted_date = f"{day}{suffix} {fixture_date.strftime('%B %Y')}"
                    except:
                        formatted_date = "TBD"
                else:
                    formatted_date = "TBD"
                
                if home_team_id == team_id:
                    # Team is playing away
                    away_team_name = next((team['name'] for team in teams_data if team['id'] == away_team_id), 'Unknown')
                    opponents.append(f"away to {away_team_name} on {formatted_date}")
                elif away_team_id == team_id:
                    # Team is playing home
                    home_team_name = next((team['name'] for team in teams_data if team['id'] == home_team_id), 'Unknown')
                    opponents.append(f"home to {home_team_name} on {formatted_date}")
        
        # Format opponent string
        if opponents:
            if len(opponents) == 1:
                opponent_str = opponents[0]
            else:
                # Double gameweek
                opponent_str = f"double gameweek: {' and '.join(opponents)}"
        else:
            opponent_str = "no fixture scheduled"
        
        # Format player list for the prompt
        player_list = self._format_players_for_prompt(players)
        
        prompt = f"""You are a Fantasy Premier League expert. Research the latest hints, tips, and recommendations for {team_name} players.

This is gameweek {current_gameweek} and {team_name} are facing {opponent_str}.

Current {team_name} squad:
{player_list}

For each player, provide:
1. Recent form and performance insights
2. Expected role and playing time
3. Set-piece responsibilities (if any)
4. Upcoming fixture analysis (including the current gameweek fixture)
5. Transfer recommendations (buy/hold/sell)
6. Any tactical insights or team news that could affect FPL performance

Search for the most recent expert opinions, community insights, and statistical analysis from trusted FPL sources, blogs, and tipster websites.

Format your response as actionable FPL advice for each player, focusing on transfer decisions and captaincy considerations.

Keep each player's advice concise but comprehensive."""

        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=self.generation_config
            )
            return response.text
        except Exception as e:
            logger.error(f"Failed to get hints/tips for {team_name}: {e}")
            return f"Error: Could not fetch hints/tips for {team_name}"
    
    def _format_players_for_prompt(self, players: List[Player]) -> str:
        """Format player list for LLM prompts"""
        formatted_players = []
        
        for player in players:
            # Get additional stats if available
            ppg = player.custom_data.get('ppg', player.points_per_game)
            form = player.custom_data.get('form', player.form)
            fixture_difficulty = player.custom_data.get('upcoming_fixture_difficulty', 3.0)
            ownership = player.custom_data.get('ownership_percent', player.selected_by_pct)
            
            formatted_players.append(
                f"- {player.name} ({player.position.value}, £{player.price}m, "
                f"PPG: {ppg:.1f}, Form: {form:.1f}, "
                f"Fixture Diff: {fixture_difficulty}, Ownership: {ownership:.1f}%)"
            )
        
        return "\n".join(formatted_players)
    
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