"""
LLM engine for FPL team creation using Gemini's web search
"""

import logging
import json
import os
from typing import Dict, List, Optional, Any
from datetime import datetime

from google import genai
from google.genai import types


from ..models import Player, FPLTeam, Position
from ..config import Config

logger = logging.getLogger(__name__)


class LLMEngine:
    """
    Core LLM engine for FPL team creation using Gemini's web search.
    
    This class handles:
    - Gemini API initialization and configuration
    - Web search integration for current FPL insights
    - LLM response parsing and validation
    - Core LLM communication functionality
    """
    
    def __init__(self, config: Config):
        self.config = config
        self.llm_config = config.get_llm_config()
        self.model_name = self.llm_config.get('model', 'gemini-2.5-pro')

        # Initialize Gemini client and search config
        self.model = self._initialize_gemini_model()

    def _initialize_gemini_model(self):
        """Initialize the Gemini client and search config"""
        api_key = self.config.get_env_var('GEMINI_API_KEY')
        
        try:
            client = genai.Client(api_key=api_key)

            # Define the grounding tool
            grounding_tool = types.Tool(
                google_search=types.GoogleSearch()
            )

            # Configure generation settings
            generation_config = types.GenerateContentConfig(
                tools=[grounding_tool],
                generation_config=types.GenerationConfig(
                    temperature=self.llm_config.get('temperature'),
                    max_output_tokens=self.llm_config.get('max_output_tokens'),
                    top_p=self.llm_config.get('top_p'),
                    top_k=self.llm_config.get('top_k')
                )
            )
            
            # Return the model
            return client.GenerativeModel(
                model_name=self.model_name,
                generation_config=generation_config
            )

        except Exception as e:
            logger.error(f"Failed to initialize Gemini model: {e}")
            return None
    
    def create_team(self, available_players: List[Player], 
                   budget: float = 100.0, 
                   gameweek: int = 1) -> Dict[str, Any]:
        """
        Create an optimized FPL team using web search and current insights.
        
        Args:
            available_players: List of available players
            budget: Team budget in millions
            gameweek: Current gameweek
            
        Returns:
            Dictionary with team selection and reasoning
        """
        if not self.model:
            logger.error("Gemini client not available")
            return self._fallback_team_creation(available_players, budget)
        
        try:
            # Create comprehensive prompt with web search
            prompt = self._create_team_creation_prompt(available_players, budget, gameweek)
            
            # Use Gemini with web search
            response = self._query_gemini_with_search(prompt)
            
            # Parse the response
            result = self._parse_team_response(response, available_players)
            
            logger.info("Successfully created team using LLM analysis")
            return result
            
        except Exception as e:
            logger.error(f"Failed to create team with LLM: {e}")
            raise
    
    def _create_team_creation_prompt(self, players: List[Player], budget: float, gameweek: int) -> str:
        """Create a comprehensive prompt for team creation with web search"""
        
        # Group players by position
        players_by_position = {
            'Goalkeepers': [p for p in players if p.position == Position.GK],
            'Defenders': [p for p in players if p.position == Position.DEF],
            'Midfielders': [p for p in players if p.position == Position.MID],
            'Forwards': [p for p in players if p.position == Position.FWD]
        }
        
        # Format player data
        player_data = {}
        for position, pos_players in players_by_position.items():
            player_data[position] = []
            for player in pos_players:
                player_data[position].append({
                    'name': player.name,
                    'team': player.team,
                    'price': player.price,
                    'form': player.form,
                    'total_points': player.total_points,
                    'xG': getattr(player, 'xG', 0),
                    'xA': getattr(player, 'xA', 0)
                })
        
        prompt = f"""
You are an expert Fantasy Premier League (FPL) analyst. Create an optimized FPL team for Gameweek {gameweek} with a budget of £{budget}m.

IMPORTANT: Use web search to find the latest FPL insights, expert tips, injury news, and form analysis for the current gameweek. Consider:
- Recent form and fixtures
- Injury updates and team news
- Expert recommendations from FPL Scout, FPL Analytics, etc.
- Captain and vice-captain suggestions
- Budget distribution strategy

Available players by position:
{json.dumps(player_data, indent=2)}

FPL Rules:
- Must select exactly 15 players
- Maximum 3 players per team
- Formation: 1 GK, 3-5 DEF, 3-5 MID, 1-3 FWD
- Budget: £{budget}m total
- Captain gets 2x points, Vice-captain gets 2x points if captain doesn't play

Please provide your response in this exact JSON format:
{{
    "reasoning": "Detailed explanation of your strategy and web search findings",
    "team": {{
        "goalkeepers": ["Player1", "Player2"],
        "defenders": ["Player1", "Player2", "Player3", "Player4", "Player5"],
        "midfielders": ["Player1", "Player2", "Player3", "Player4", "Player5"],
        "forwards": ["Player1", "Player2", "Player3"]
    }},
    "captain": "Player Name",
    "vice_captain": "Player Name",
    "formation": "4-4-2",
    "total_cost": 100.0,
    "web_insights": "Summary of key insights found from web search"
}}

Base your recommendations on current web search results for the latest FPL insights and expert analysis.
"""
        return prompt
    
    def _query_gemini_with_search(self, prompt: str) -> str:
        """Query Gemini with web search enabled"""
        try:
            # Use Gemini's built-in web search (enabled at model level)
            response = self.model.generate_content(prompt)
            return response.text
        except Exception as e:
            logger.error(f"Failed to query Gemini: {e}")
            raise
    
    def _parse_team_response(self, response: str, available_players: List[Player]) -> Dict[str, Any]:
        """Parse the LLM response into structured data"""
        try:
            # Try to extract JSON from response
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            
            if json_start == -1 or json_end == 0:
                raise ValueError("No JSON found in response")
            
            json_str = response[json_start:json_end]
            parsed = json.loads(json_str)
            
            # Validate and convert to proper format
            result = {
                'success': True,
                'reasoning': parsed.get('reasoning', ''),
                'web_insights': parsed.get('web_insights', ''),
                'team': self._validate_team_selection(parsed.get('team', {}), available_players),
                'captain': parsed.get('captain', ''),
                'vice_captain': parsed.get('vice_captain', ''),
                'formation': parsed.get('formation', ''),
                'total_cost': parsed.get('total_cost', 0.0)
            }
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to parse LLM response: {e}")
            logger.error(f"Response: {response}")
            raise
    
    def _validate_team_selection(self, team_data: Dict, available_players: List[Player]) -> Dict[str, List[str]]:
        """Validate that selected players exist in available players"""
        validated_team = {
            'goalkeepers': [],
            'defenders': [],
            'midfielders': [],
            'forwards': []
        }
        
        available_names = {p.name.lower(): p.name for p in available_players}
        
        for position, players in team_data.items():
            if position in validated_team:
                for player_name in players:
                    # Try exact match first, then case-insensitive
                    if player_name in available_names:
                        validated_team[position].append(available_names[player_name])
                    elif player_name.lower() in available_names:
                        validated_team[position].append(available_names[player_name.lower()])
        
        return validated_team
    
