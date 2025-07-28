"""
LLM-based tips summarizer for FPL insights
"""

import openai
from typing import Dict, List, Optional, Any
import logging
import json
from datetime import datetime

from ..config import Config


logger = logging.getLogger(__name__)


class TipsSummarizer:
    """Uses LLM to summarize FPL tips and insights"""
    
    def __init__(self, config: Config):
        self.config = config
        self.llm_config = config.get_llm_config()
        
        # Initialize OpenAI client
        api_key = config.get('llm.api_key')
        if api_key:
            openai.api_key = api_key
        else:
            logger.warning("No OpenAI API key found. LLM features will be limited.")
    
    def get_weekly_tips(self, gameweek: int) -> Dict[str, Any]:
        """Get summarized tips for a specific gameweek"""
        
        logger.info(f"Fetching tips for gameweek {gameweek}")
        
        try:
            # Create prompt for LLM to gather tips
            prompt = self._create_tips_prompt(gameweek)
            
            # Get response from LLM
            response = self._call_llm(prompt)
            
            # Parse and structure the response
            tips = self._parse_tips_response(response)
            
            return tips
            
        except Exception as e:
            logger.error(f"Failed to get tips for gameweek {gameweek}: {e}")
            return self._get_mock_tips(gameweek)
    
    def get_player_insights(self, player_name: str, team_name: str) -> Dict[str, Any]:
        """Get specific insights about a player"""
        
        logger.info(f"Fetching insights for {player_name} ({team_name})")
        
        try:
            # Create prompt for player insights
            prompt = self._create_player_insights_prompt(player_name, team_name)
            
            # Get response from LLM
            response = self._call_llm(prompt)
            
            # Parse the response
            insights = self._parse_player_insights_response(response)
            
            return insights
            
        except Exception as e:
            logger.error(f"Failed to get insights for {player_name}: {e}")
            return self._get_mock_player_insights(player_name, team_name)
    
    def get_injury_news(self, team_name: str) -> List[Dict[str, Any]]:
        """Get injury news for a team"""
        
        logger.info(f"Fetching injury news for {team_name}")
        
        try:
            # Create prompt for injury news
            prompt = self._create_injury_prompt(team_name)
            
            # Get response from LLM
            response = self._call_llm(prompt)
            
            # Parse the response
            injuries = self._parse_injury_response(response)
            
            return injuries
            
        except Exception as e:
            logger.error(f"Failed to get injury news for {team_name}: {e}")
            return self._get_mock_injury_news(team_name)
    
    def get_fixture_analysis(self, home_team: str, away_team: str, gameweek: int) -> Dict[str, Any]:
        """Get analysis for a specific fixture"""
        
        logger.info(f"Fetching fixture analysis: {home_team} vs {away_team} (GW{gameweek})")
        
        try:
            # Create prompt for fixture analysis
            prompt = self._create_fixture_analysis_prompt(home_team, away_team, gameweek)
            
            # Get response from LLM
            response = self._call_llm(prompt)
            
            # Parse the response
            analysis = self._parse_fixture_analysis_response(response)
            
            return analysis
            
        except Exception as e:
            logger.error(f"Failed to get fixture analysis: {e}")
            return self._get_mock_fixture_analysis(home_team, away_team, gameweek)
    
    def _call_llm(self, prompt: str) -> str:
        """Call the LLM with a prompt"""
        
        try:
            if not openai.api_key:
                logger.warning("No API key available, returning mock response")
                return self._get_mock_llm_response(prompt)
            
            response = openai.ChatCompletion.create(
                model=self.llm_config.get('model', 'gpt-3.5-turbo'),
                messages=[
                    {"role": "system", "content": "You are an expert FPL analyst. Provide accurate, helpful insights based on current information."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=self.llm_config.get('max_tokens', 2000),
                temperature=self.llm_config.get('temperature', 0.1)
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            return self._get_mock_llm_response(prompt)
    
    def _create_tips_prompt(self, gameweek: int) -> str:
        """Create prompt for weekly tips"""
        
        return f"""
        As an expert FPL analyst, provide a comprehensive summary of the key tips and insights for Gameweek {gameweek}.
        
        Please gather information from:
        - Fantasy Football Scout
        - Reddit r/FantasyPL
        - FPL Twitter community
        - Official FPL Scout
        
        Focus on:
        1. Top captain picks and why
        2. Key transfer targets
        3. Players to avoid
        4. Injury news and updates
        5. Fixture analysis
        6. Differential picks
        7. Chip strategy advice
        
        Format your response as JSON with the following structure:
        {{
            "gameweek": {gameweek},
            "captain_picks": [
                {{"player": "name", "team": "team", "reason": "reason", "confidence": 0.8}}
            ],
            "transfer_targets": [
                {{"player": "name", "team": "team", "reason": "reason", "priority": "high/medium/low"}}
            ],
            "players_to_avoid": [
                {{"player": "name", "team": "team", "reason": "reason"}}
            ],
            "injury_updates": [
                {{"player": "name", "team": "team", "status": "status", "expected_return": "date"}}
            ],
            "differential_picks": [
                {{"player": "name", "team": "team", "ownership": "percentage", "reason": "reason"}}
            ],
            "chip_advice": "advice",
            "general_tips": "tips"
        }}
        """
    
    def _create_player_insights_prompt(self, player_name: str, team_name: str) -> str:
        """Create prompt for player insights"""
        
        return f"""
        Provide detailed insights about {player_name} ({team_name}) for FPL managers.
        
        Include:
        1. Recent form and performance
        2. Expected playing time
        3. Fixture difficulty analysis
        4. Injury status and concerns
        5. Historical performance against upcoming opponents
        6. Team tactics and role
        7. Price and value for money
        8. Risk factors
        
        Format as JSON:
        {{
            "player": "{player_name}",
            "team": "{team_name}",
            "form": "description",
            "playing_time": "expected minutes",
            "fixtures": "upcoming difficulty",
            "injury_status": "status",
            "historical_performance": "analysis",
            "team_role": "description",
            "value": "assessment",
            "risks": "risk factors",
            "recommendation": "buy/hold/sell",
            "confidence": 0.8
        }}
        """
    
    def _create_injury_prompt(self, team_name: str) -> str:
        """Create prompt for injury news"""
        
        return f"""
        Provide the latest injury news and updates for {team_name} players.
        
        Include:
        1. Confirmed injuries
        2. Expected return dates
        3. Doubtful players
        4. Suspensions
        5. International duty
        
        Format as JSON:
        {{
            "team": "{team_name}",
            "injuries": [
                {{"player": "name", "injury": "type", "expected_return": "date", "severity": "high/medium/low"}}
            ],
            "doubtful": [
                {{"player": "name", "issue": "description", "probability": "percentage"}}
            ],
            "suspended": [
                {{"player": "name", "reason": "reason", "return_date": "date"}}
            ],
            "international_duty": [
                {{"player": "name", "status": "status"}}
            ]
        }}
        """
    
    def _create_fixture_analysis_prompt(self, home_team: str, away_team: str, gameweek: int) -> str:
        """Create prompt for fixture analysis"""
        
        return f"""
        Provide detailed analysis for the {home_team} vs {away_team} fixture in Gameweek {gameweek}.
        
        Include:
        1. Head-to-head record
        2. Recent form comparison
        3. Key player matchups
        4. Tactical analysis
        5. Expected goals and clean sheet probability
        6. FPL implications
        
        Format as JSON:
        {{
            "fixture": "{home_team} vs {away_team}",
            "gameweek": {gameweek},
            "head_to_head": "record",
            "home_form": "recent performance",
            "away_form": "recent performance",
            "key_matchups": [
                {{"home_player": "name", "away_player": "name", "analysis": "description"}}
            ],
            "tactical_analysis": "description",
            "expected_goals": "prediction",
            "clean_sheet_probability": {{
                "home": 0.3,
                "away": 0.2
            }},
            "fpl_implications": "advice for managers"
        }}
        """
    
    def _parse_tips_response(self, response: str) -> Dict[str, Any]:
        """Parse LLM response for tips"""
        
        try:
            # Try to extract JSON from response
            if '{' in response and '}' in response:
                start = response.find('{')
                end = response.rfind('}') + 1
                json_str = response[start:end]
                return json.loads(json_str)
            else:
                return self._get_mock_tips(1)
        except Exception as e:
            logger.error(f"Failed to parse tips response: {e}")
            return self._get_mock_tips(1)
    
    def _parse_player_insights_response(self, response: str) -> Dict[str, Any]:
        """Parse LLM response for player insights"""
        
        try:
            if '{' in response and '}' in response:
                start = response.find('{')
                end = response.rfind('}') + 1
                json_str = response[start:end]
                return json.loads(json_str)
            else:
                return self._get_mock_player_insights("Unknown Player", "Unknown Team")
        except Exception as e:
            logger.error(f"Failed to parse player insights response: {e}")
            return self._get_mock_player_insights("Unknown Player", "Unknown Team")
    
    def _parse_injury_response(self, response: str) -> List[Dict[str, Any]]:
        """Parse LLM response for injury news"""
        
        try:
            if '{' in response and '}' in response:
                start = response.find('{')
                end = response.rfind('}') + 1
                json_str = response[start:end]
                data = json.loads(json_str)
                return data.get('injuries', [])
            else:
                return self._get_mock_injury_news("Unknown Team")
        except Exception as e:
            logger.error(f"Failed to parse injury response: {e}")
            return self._get_mock_injury_news("Unknown Team")
    
    def _parse_fixture_analysis_response(self, response: str) -> Dict[str, Any]:
        """Parse LLM response for fixture analysis"""
        
        try:
            if '{' in response and '}' in response:
                start = response.find('{')
                end = response.rfind('}') + 1
                json_str = response[start:end]
                return json.loads(json_str)
            else:
                return self._get_mock_fixture_analysis("Home Team", "Away Team", 1)
        except Exception as e:
            logger.error(f"Failed to parse fixture analysis response: {e}")
            return self._get_mock_fixture_analysis("Home Team", "Away Team", 1)
    
    def _get_mock_llm_response(self, prompt: str) -> str:
        """Get mock LLM response when API is not available"""
        
        if "tips" in prompt.lower():
            return json.dumps(self._get_mock_tips(1))
        elif "insights" in prompt.lower():
            return json.dumps(self._get_mock_player_insights("Mock Player", "Mock Team"))
        elif "injury" in prompt.lower():
            return json.dumps({"injuries": self._get_mock_injury_news("Mock Team")})
        elif "fixture" in prompt.lower():
            return json.dumps(self._get_mock_fixture_analysis("Home", "Away", 1))
        else:
            return '{"message": "Mock response"}'
    
    def _get_mock_tips(self, gameweek: int) -> Dict[str, Any]:
        """Get mock tips data"""
        
        return {
            "gameweek": gameweek,
            "captain_picks": [
                {"player": "Erling Haaland", "team": "Man City", "reason": "Home fixture vs weak defense", "confidence": 0.9},
                {"player": "Mohamed Salah", "team": "Liverpool", "reason": "Good form, favorable fixture", "confidence": 0.8}
            ],
            "transfer_targets": [
                {"player": "Bukayo Saka", "team": "Arsenal", "reason": "Consistent returns, good fixtures", "priority": "high"}
            ],
            "players_to_avoid": [
                {"player": "Injured Player", "team": "Team", "reason": "Confirmed injury"}
            ],
            "injury_updates": [
                {"player": "Kevin De Bruyne", "team": "Man City", "status": "Doubtful", "expected_return": "GW+2"}
            ],
            "differential_picks": [
                {"player": "Differential Player", "team": "Team", "ownership": "5%", "reason": "Good underlying stats"}
            ],
            "chip_advice": "Save chips for double gameweeks",
            "general_tips": "Focus on form over fixtures"
        }
    
    def _get_mock_player_insights(self, player_name: str, team_name: str) -> Dict[str, Any]:
        """Get mock player insights"""
        
        return {
            "player": player_name,
            "team": team_name,
            "form": "Good recent form with consistent returns",
            "playing_time": "Expected to start and play 90 minutes",
            "fixtures": "Favorable upcoming fixtures",
            "injury_status": "Fully fit",
            "historical_performance": "Good record against upcoming opponents",
            "team_role": "Key attacking player",
            "value": "Good value for money",
            "risks": "Rotation risk",
            "recommendation": "buy",
            "confidence": 0.8
        }
    
    def _get_mock_injury_news(self, team_name: str) -> List[Dict[str, Any]]:
        """Get mock injury news"""
        
        return [
            {"player": "Injured Player 1", "injury": "Hamstring", "expected_return": "GW+3", "severity": "medium"},
            {"player": "Injured Player 2", "injury": "Knee", "expected_return": "GW+6", "severity": "high"}
        ]
    
    def _get_mock_fixture_analysis(self, home_team: str, away_team: str, gameweek: int) -> Dict[str, Any]:
        """Get mock fixture analysis"""
        
        return {
            "fixture": f"{home_team} vs {away_team}",
            "gameweek": gameweek,
            "head_to_head": "Home team has good record",
            "home_form": "Good recent form",
            "away_form": "Mixed results",
            "key_matchups": [
                {"home_player": "Home Star", "away_player": "Away Star", "analysis": "Key battle"}
            ],
            "tactical_analysis": "Home team likely to dominate possession",
            "expected_goals": "2.5",
            "clean_sheet_probability": {
                "home": 0.4,
                "away": 0.2
            },
            "fpl_implications": "Good for home team attackers"
        }
