"""
Lightweight LLM Strategy for team-specific analysis
"""

import logging
from typing import Dict, List, Any, Optional
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
        
        # Create the prompt
        prompt = self._create_injury_news_prompt(team_name, players, current_gameweek, opponent_str)
        
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
        
        # Create the prompt
        prompt = self._create_hints_tips_prompt(team_name, players, current_gameweek, opponent_str)
        
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
                                 current_gameweek: int, opponent_str: str) -> str:
        """Create the injury news prompt"""
        # Format player list for the prompt
        player_list = self._format_players_for_prompt(players)
        
        return f"""You're job is to collate the latest injury news on players in the {team_name} squad. The aim is to present the findings for use in an assessment of whether the players will be fit for the upcoming gameweek and will play in the matchday squad. Research the latest injury news and playing likelihood for {team_name} players.

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
    
    def _create_hints_tips_prompt(self, team_name: str, players: List[Player], 
                                current_gameweek: int, opponent_str: str) -> str:
        """Create the hints and tips prompt"""
        # Format player list for the prompt
        player_list = self._format_players_for_prompt(players)
        
        return f"""You're job is to collate the latest fantasy premier league hints, tips and recommendations news on players in the {team_name} squad. The aim is to present the findings for use in an assessment of whether the players are great picks for the upcoming gameweek and will score big points. Research the latest hints, tips and recommendation for {team_name} players.

This is gameweek {current_gameweek} and {team_name} are facing {opponent_str}.

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
            fixture_difficulty = player.custom_data.get('upcoming_fixture_difficulty', 3.0)
            ownership = player.custom_data.get('ownership_percent', player.selected_by_pct)
            
            formatted_players.append(
                f"- {player.name} ({player.position.value}, £{player.price}m, "
                f"PPG: {ppg:.1f}, Form: {form:.1f}, Fixture Diff: {fixture_difficulty}, "
                f"Ownership: {ownership:.1f}%)"
            )
        
        return "\n".join(formatted_players) 