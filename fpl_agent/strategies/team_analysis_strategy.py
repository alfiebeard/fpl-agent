"""
Lightweight LLM Strategy for team-specific analysis
"""

import logging
from typing import Dict, List
from datetime import datetime

from ..core.config import Config
from ..core.models import Player
from .base_strategy import BaseLLMStrategy

logger = logging.getLogger(__name__)


class TeamAnalysisStrategy(BaseLLMStrategy):
    """
    Lightweight LLM strategy for team-specific analysis.
    
    This class handles:
    - Team injury news analysis using lightweight LLM
    - Team hints and tips analysis using lightweight LLM
    - Prompt creation and orchestration
    """
    
    def __init__(self, config: Config):
        super().__init__(config, model_name="lightweight")
            
    def get_strategy_name(self) -> str:
        """Return the name of this strategy."""
        return "Team Analysis Strategy"
    
    def get_team_injury_news(self, team_name: str, players: List[Player]) -> str:
        """
        Get injury news and playing likelihood for players in a specific team.
        
        Args:
            team_name: Name of the team
            players: List of players in the team
            
        Returns:
            String containing injury news for each player
        """
        # Get current gameweek from our data pipeline
        current_gameweek = self.get_current_gameweek()
        
        # Get fixture information
        fixture_info = self.get_fixture_info(team_name, current_gameweek)
        
        # Create the prompt
        prompt = self._create_injury_news_prompt(team_name, players, current_gameweek, fixture_info)
        
        # Get LLM response
        response = self.llm_engine.query(prompt, use_web_search=False, extract_json=True)
        
        # Use base class JSON extraction for better error handling
        return self._extract_json_response(response, f"injury news for {team_name}")
    
    def get_team_hints_tips(self, team_name: str, players: List[Player]) -> str:
        """
        Get hints, tips, and recommendations for players in a specific team.
        
        Args:
            team_name: Name of the team
            players: List of players in the team
            
        Returns:
            String containing hints, tips, and recommendations for each player
        """
        # Get current gameweek from our data pipeline
        current_gameweek = self.get_current_gameweek()
        
        # Get fixture information
        fixture_info = self.get_fixture_info(team_name, current_gameweek)
        
        # Create the prompt
        prompt = self._create_hints_tips_prompt(team_name, players, current_gameweek, fixture_info)
        
        # Get LLM response
        response = self.llm_engine.query(prompt, use_web_search=False, extract_json=True)
        
        # Use base class JSON extraction for better error handling
        return self._extract_json_response(response, f"hints/tips for {team_name}")
    
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