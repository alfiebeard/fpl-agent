"""
Team Analysis Strategy

This strategy analyzes FPL teams and provides insights and recommendations.
"""

import logging
from typing import Dict, List, Any, Optional

from ..core.config import Config
from ..utils.validator import FPLValidator
from ..utils.prompt_formatter import PromptFormatter
from .base_strategy import BaseLLMStrategy

logger = logging.getLogger(__name__)


class TeamAnalysisStrategy(BaseLLMStrategy):
    """Strategy for analyzing FPL teams"""
    
    def __init__(self, config: Config):
        """
        Initialize the strategy.
        
        Args:
            config: FPL configuration object
        """

        super().__init__(config, model_name="lightweight")
        self.validator = FPLValidator("team_data")  # Use default data directory
    
    def get_strategy_name(self) -> str:
        """Return the name of this strategy."""

        return "TeamAnalysisStrategy"
    
    def get_team_hints_tips(self, team_name: str, team_players: List[Dict[str, Any]], current_gameweek: int, fixture_info: dict) -> Dict[str, str]:
        """
        Get hints, tips, and recommendations for players in a specific team.
        
        Args:
            team_name: Name of the team
            team_players: List of player data for the team
            current_gameweek: Current gameweek number
            fixture_info: Dictionary containing fixture information
            
        Returns:
            Dictionary mapping player names to hints and tips
        """
        logger.info(f"Getting hints and tips for {team_name}")
        
        try:
            # Create the prompt
            prompt = self._create_hints_tips_prompt(team_name, team_players, current_gameweek, fixture_info)
            
            # Debug: Log the prompt being sent
            logger.info(f"Prompt for hints/tips (length: {len(prompt)}): {prompt[:500]}...")
            
            # Get LLM response
            response = self.llm_engine.query(prompt)
            
            # Debug: Log the response received
            logger.info(f"LLM response received (length: {len(response)}): {repr(response[:200])}")
            
            # Parse the response to extract insights for each player
            self.validator.parse_llm_json_response(response, raise_on_error=False, expected_type="hints/tips")
            
        except Exception as e:
            logger.error(f"Failed to get hints and tips for {team_name}: {e}")
            # Return empty insights on failure
            return {}
    
    def get_team_injury_news(self, team_name: str, team_players: List[Dict[str, Any]], current_gameweek: int, fixture_info: dict) -> Dict[str, str]:
        """
        Get injury news and playing likelihood for players in a specific team.
        
        Args:
            team_name: Name of the team
            team_players: List of player data for the team
            current_gameweek: Current gameweek number
            fixture_info: Dictionary containing fixture information

        Returns:
            Dictionary mapping player names to injury news
        """
        logger.info(f"Getting injury news for {team_name}")
        
        try:            
            # Create the prompt
            prompt = self._create_injury_news_prompt(team_name, team_players, current_gameweek, fixture_info)
            
            # Debug: Log the prompt being sent
            logger.info(f"Prompt for injury news (length: {len(prompt)}): {prompt[:500]}...")
            
            # Get LLM response
            response = self.llm_engine.query(prompt)
            
            # Debug: Log the response received
            logger.info(f"LLM response received (length: {len(response)}): {repr(response[:200])}")
            
            # Parse the response to extract injury news for each player
            return self.validator.parse_llm_json_response(response, raise_on_error=False, expected_type="injury news")
            
        except Exception as e:
            logger.error(f"Failed to get injury news for {team_name}: {e}")
            # Return empty injury news on failure
            return {}
    
    def _create_hints_tips_prompt(self, team_name: str, team_players: Dict[str, Any], current_gameweek: int, fixture_info: dict) -> str:
        """Create the hints and tips prompt
        
        Args:
            team_name: Name of the team
            formatted_players: Formatted players for the prompt
            current_gameweek: Current gameweek number
            fixture_info: Dictionary containing fixture information

        Returns:
            The hints and tips prompt as a string
        """
        # Get fixture information
        fixture_str = fixture_info['fixture_str']
        is_double_gameweek = fixture_info['is_double_gameweek']
        fixture_difficulty = fixture_info['fixture_difficulty']
        
        # Create double gameweek text
        double_gameweek_text = "This is a double gameweek." if is_double_gameweek else ""
        
        return f"""You're job is to collate the latest fantasy premier league hints, tips and recommendations news on players in the {team_name} squad. The aim is to present the findings for use in an assessment of whether the players are great picks for the upcoming gameweek and will score big points. Research the latest hints, tips and recommendation for {team_name} players.

This is gameweek {current_gameweek} of the 2025/2026 season and {team_name} are facing {fixture_str}. {double_gameweek_text} The fixture difficulty for {team_name} is {fixture_difficulty}.

Current {team_name} squad:

{PromptFormatter.format_player_list(team_players, use_enrichments=False, use_ranking=False, show_header=False)}
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

Keep each player's information brief but informative.

IMPORTANT: You MUST respond with ONLY valid JSON. Do not include any markdown, explanations, or text outside the JSON structure."""
    
    def _create_injury_news_prompt(self, team_name: str, team_players: Dict[str, Any], current_gameweek: int, fixture_info: dict) -> str:
        """Create the injury news prompt
        
        Args:
            team_name: Name of the team
            team_players: List of player data for the team
            current_gameweek: Current gameweek number
            fixture_info: Dictionary containing fixture information

        Returns:
            The injury news prompt as a string
        """
        # Get fixture information
        fixture_str = fixture_info['fixture_str']
        is_double_gameweek = fixture_info['is_double_gameweek']
        fixture_difficulty = fixture_info['fixture_difficulty']
        
        # Create double gameweek text
        double_gameweek_text = "This is a double gameweek." if is_double_gameweek else ""
        
        return f"""You're job is to collate the latest injury news on players in the {team_name} squad. The aim is to present the findings for use in an assessment of whether the players will be fit for the upcoming gameweek and will play in the matchday squad. Research the latest injury news and playing likelihood for {team_name} players.

This is gameweek {current_gameweek} of the 2025/2026 season and {team_name} are {fixture_str}. {double_gameweek_text} The fixture difficulty for {team_name} is {fixture_difficulty}. 

Current {team_name} squad:

{PromptFormatter.format_player_list(team_players, use_enrichments=False, use_ranking=False, show_header=False)}
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

Keep each player's information brief but informative.

IMPORTANT: You MUST respond with ONLY valid JSON. Do not include any markdown, explanations, or text outside the JSON structure."""
