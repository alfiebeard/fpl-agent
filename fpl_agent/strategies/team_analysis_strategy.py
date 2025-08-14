"""
Team Analysis Strategy

This strategy analyzes FPL teams and provides insights and recommendations.
"""

import logging
from typing import Dict, List, Any, Optional

from ..core.config import Config
from ..core.models import FPLTeam
from ..utils.validator import FPLValidator
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
        super().__init__(config, model_name="main")
        self.validator = FPLValidator("team_data")  # Use default data directory
    
    def get_strategy_name(self) -> str:
        """Return the name of this strategy."""
        return "TeamAnalysisStrategy"
    
    def get_team_hints_tips(self, team_name: str, formatted_players: str, current_gameweek: int, fixture_info: dict) -> Dict[str, str]:
        """
        Get hints, tips, and recommendations for players in a specific team.
        
        Args:
            team_name: Name of the team
            formatted_players: Formatted string of players for the prompt
            current_gameweek: Current gameweek number
            fixture_info: Dictionary containing fixture information
            
        Returns:
            Dictionary mapping player names to hints and tips
        """
        logger.info(f"Getting hints and tips for {team_name}")
        
        try:
            # Create the prompt
            prompt = self._create_hints_tips_prompt(team_name, formatted_players, current_gameweek, fixture_info)
            
            # Get LLM response
            response = self.llm_engine.query(prompt)
            
            # Parse the response to extract insights for each player
            return self._parse_hints_tips_response(response, formatted_players)
            
        except Exception as e:
            logger.error(f"Failed to get hints and tips for {team_name}: {e}")
            # Return empty insights on failure
            return {}
    
    def get_team_injury_news(self, team_name: str, formatted_players: str, current_gameweek: int, fixture_info: dict) -> Dict[str, str]:
        """
        Get injury news and playing likelihood for players in a specific team.
        
        Args:
            team_name: Name of the team
            formatted_players: Formatted string of players for the prompt
            current_gameweek: Current gameweek number
            fixture_info: Dictionary containing fixture information
            
        Returns:
            Dictionary mapping player names to injury news
        """
        logger.info(f"Getting injury news for {team_name}")
        
        try:
            # Create the prompt
            prompt = self._create_injury_news_prompt(team_name, formatted_players, current_gameweek, fixture_info)
            
            # Get LLM response
            response = self.llm_engine.query(prompt)
            
            # Parse the response to extract injury news for each player
            return self._parse_injury_news_response(response, formatted_players)
            
        except Exception as e:
            logger.error(f"Failed to get injury news for {team_name}: {e}")
            # Return empty injury news on failure
            return {}
    

    
    def _create_hints_tips_prompt(self, team_name: str, formatted_players: str, current_gameweek: int, fixture_info: dict) -> str:
        """Create the hints and tips prompt"""
        # Get fixture information
        fixture_str = fixture_info['fixture_str']
        is_double_gameweek = fixture_info['is_double_gameweek']
        fixture_difficulty = fixture_info['fixture_difficulty']
        
        # Create double gameweek text
        double_gameweek_text = "This is a double gameweek." if is_double_gameweek else ""
        
        return f"""You're job is to collate the latest fantasy premier league hints, tips and recommendations news on players in the {team_name} squad. The aim is to present the findings for use in an assessment of whether the players are great picks for the upcoming gameweek and will score big points. Research the latest hints, tips and recommendation for {team_name} players.

This is gameweek {current_gameweek} of the 2025/2026 season and {team_name} are facing {fixture_str}. {double_gameweek_text} The fixture difficulty for {team_name} is {fixture_difficulty}.

Current {team_name} squad:
{formatted_players}

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
    
    def _create_injury_news_prompt(self, team_name: str, formatted_players: str, current_gameweek: int, fixture_info: dict) -> str:
        """Create the injury news prompt"""
        # Get fixture information
        fixture_str = fixture_info['fixture_str']
        is_double_gameweek = fixture_info['is_double_gameweek']
        fixture_difficulty = fixture_info['fixture_difficulty']
        
        # Create double gameweek text
        double_gameweek_text = "This is a double gameweek." if is_double_gameweek else ""
        
        return f"""You're job is to collate the latest injury news on players in the {team_name} squad. The aim is to present the findings for use in an assessment of whether the players will be fit for the upcoming gameweek and will play in the matchday squad. Research the latest injury news and playing likelihood for {team_name} players.

This is gameweek {current_gameweek} of the 2025/2026 season and {team_name} are {fixture_str}. {double_gameweek_text} The fixture difficulty for {team_name} is {fixture_difficulty}. 

Current {team_name} squad:
{formatted_players}

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
    
    def _parse_hints_tips_response(self, response: str, formatted_players: str) -> Dict[str, str]:
        """Parse LLM response to extract hints and tips for each player."""
        try:
            import json
            # Try to extract JSON from the response
            response_text = response.strip()
            if response_text.startswith('```json'):
                response_text = response_text[7:]
            if response_text.endswith('```'):
                response_text = response_text[:-3]
            
            parsed = json.loads(response_text)
            
            # The response should be a direct mapping of player names to insights
            # No need for 'player_insights' wrapper since your prompts don't use it
            return parsed
            
        except Exception as e:
            logger.error(f"Failed to parse hints and tips response: {e}")
            # Return empty dict on parsing failure
            return {}
    
    def _parse_injury_news_response(self, response: str, formatted_players: str) -> Dict[str, str]:
        """Parse LLM response to extract injury news for each player."""
        try:
            import json
            # Try to extract JSON from the response
            response_text = response.strip()
            if response_text.startswith('```json'):
                response_text = response_text[7:]
            if response_text.endswith('```'):
                response_text = response_text[:-3]
            
            parsed = json.loads(response_text)
            
            # The response should be a direct mapping of player names to injury news
            # No need for 'player_injuries' wrapper since your prompts don't use it
            return parsed
            
        except Exception as e:
            logger.error(f"Failed to parse injury news response: {e}")
            # Return empty dict on parsing failure
            return {}
    
    def analyze_team(self, team: FPLTeam) -> Dict[str, Any]:
        """
        Analyze an FPL team and provide insights.
        
        Args:
            team: FPL team to analyze
            
        Returns:
            Dictionary containing analysis results
        """
        logger.info(f"Analyzing team: {team.team_name}")
        
        try:
            # Get current FPL data for context
            current_data = self.data_service.get_current_data()
            if not current_data:
                raise ValueError("Failed to get current FPL data")
            
            # Create analysis prompt
            prompt = self._create_analysis_prompt(team, current_data)
            
            # Get LLM analysis
            analysis_response = self.llm_engine.query(prompt)
            
            # Parse and validate response
            analysis_data = self._parse_analysis_response(analysis_response)
            
            # Validate analysis data
            validation_errors = self.validator.validate_analysis_data(analysis_data)
            if validation_errors:
                logger.warning(f"Analysis validation errors: {validation_errors}")
            
            return {
                'team_id': team.team_id,
                'team_name': team.team_name,
                'analysis': analysis_data,
                'validation_errors': validation_errors,
                'timestamp': current_data.get('timestamp', 'unknown')
            }
            
        except Exception as e:
            logger.error(f"Failed to analyze team {team.team_name}: {e}")
            raise
    
    def analyze_team_performance(self, team: FPLTeam, gameweek: Optional[int] = None) -> Dict[str, Any]:
        """
        Analyze team performance for a specific gameweek or overall.
        
        Args:
            team: FPL team to analyze
            gameweek: Specific gameweek to analyze (None for overall)
            
        Returns:
            Dictionary containing performance analysis
        """
        logger.info(f"Analyzing team performance for {team.team_name} - Gameweek: {gameweek or 'Overall'}")
        
        try:
            # Get performance data
            if gameweek:
                performance_data = self.data_service.get_gameweek_performance(team.team_id, gameweek)
            else:
                performance_data = self.data_service.get_overall_performance(team.team_id)
            
            if not performance_data:
                raise ValueError(f"Failed to get performance data for gameweek {gameweek}")
            
            # Create performance analysis prompt
            prompt = self._create_performance_analysis_prompt(team, performance_data, gameweek)
            
            # Get LLM analysis
            analysis_response = self.llm_engine.query(prompt)
            
            # Parse response
            analysis_data = self._parse_performance_analysis_response(analysis_response)
            
            return {
                'team_id': team.team_id,
                'team_name': team.team_name,
                'gameweek': gameweek,
                'performance_data': performance_data,
                'analysis': analysis_data,
                'timestamp': performance_data.get('timestamp', 'unknown')
            }
            
        except Exception as e:
            logger.error(f"Failed to analyze team performance: {e}")
            raise
    
    def get_team_recommendations(self, team: FPLTeam, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Get recommendations for improving the team.
        
        Args:
            team: FPL team to analyze
            context: Additional context (e.g., upcoming fixtures, budget constraints)
            
        Returns:
            Dictionary containing recommendations
        """
        logger.info(f"Getting recommendations for team: {team.team_name}")
        
        try:
            # Get current FPL data and context
            current_data = self.data_service.get_current_data()
            if not current_data:
                raise ValueError("Failed to get current FPL data")
            
            # Create recommendations prompt
            prompt = self._create_recommendations_prompt(team, current_data, context)
            
            # Get LLM recommendations
            recommendations_response = self.llm_engine.query(prompt)
            
            # Parse response
            recommendations_data = self._parse_recommendations_response(recommendations_response)
            
            return {
                'team_id': team.team_id,
                'team_name': team.team_name,
                'recommendations': recommendations_data,
                'context': context,
                'timestamp': current_data.get('timestamp', 'unknown')
            }
            
        except Exception as e:
            logger.error(f"Failed to get team recommendations: {e}")
            raise
    
    def _create_analysis_prompt(self, team: FPLTeam, current_data: Dict[str, Any]) -> str:
        """Create prompt for team analysis."""
        team_summary = team.get_team_summary()
        
        prompt = f"""
        Analyze this FPL team and provide insights:

        Team: {team_summary['team_name']}
        Manager: {team_summary['manager_name']}
        Formation: {team_summary['formation']}
        Total Value: £{team_summary['total_value']:.1f}m
        Bank: £{team_summary['bank']:.1f}m
        Total Points: {team_summary['total_points']}
        Overall Rank: {team_summary['overall_rank'] or 'Unknown'}

        Players:
        {self._format_players_for_analysis(team.players)}

        Current Gameweek: {current_data.get('current_gameweek', 'Unknown')}
        Next Deadline: {current_data.get('next_deadline', 'Unknown')}

        Please provide:
        1. Team strengths and weaknesses
        2. Player performance analysis
        3. Formation effectiveness
        4. Budget utilization
        5. Areas for improvement
        6. Risk assessment

        Format your response as a structured analysis with clear sections.
        """
        
        return prompt
    
    def _create_performance_analysis_prompt(self, team: FPLTeam, performance_data: Dict[str, Any], gameweek: Optional[int]) -> str:
        """Create prompt for performance analysis."""
        team_summary = team.get_team_summary()
        
        prompt = f"""
        Analyze the performance of this FPL team:

        Team: {team_summary['team_name']}
        Gameweek: {gameweek or 'Overall Season'}
        Total Points: {team_summary['total_points']}
        Overall Rank: {team_summary['overall_rank'] or 'Unknown'}

        Performance Data:
        {self._format_performance_data(performance_data)}

        Please provide:
        1. Performance summary
        2. Key contributors
        3. Areas of concern
        4. Trends and patterns
        5. Comparison to previous periods
        6. Recommendations for improvement

        Format your response as a structured analysis.
        """
        
        return prompt
    
    def _create_recommendations_prompt(self, team: FPLTeam, current_data: Dict[str, Any], context: Optional[Dict[str, Any]]) -> str:
        """Create prompt for team recommendations."""
        team_summary = team.get_team_summary()
        
        prompt = f"""
        Provide recommendations for improving this FPL team:

        Team: {team_summary['team_name']}
        Current Formation: {team_summary['formation']}
        Total Value: £{team_summary['total_value']:.1f}m
        Bank: £{team_summary['bank']:.1f}m
        Free Transfers: {team_summary['free_transfers']}

        Current Squad:
        {self._format_players_for_recommendations(team.players)}

        Context:
        {self._format_context_for_recommendations(context) if context else 'No additional context provided'}

        Please provide:
        1. Transfer recommendations
        2. Formation suggestions
        3. Captain choices
        4. Chip usage strategy
        5. Budget allocation
        6. Risk management

        Format your response as actionable recommendations with reasoning.
        """
        
        return prompt
    
    def _format_players_for_analysis(self, players: List[Dict[str, Any]]) -> str:
        """Format players for analysis prompt."""
        if not players:
            return "No players in squad"
        
        formatted = []
        for player in players:
            position = player.get('position', 'UNK')
            name = player.get('full_name', 'Unknown')
            price = player.get('now_cost', 0) / 10.0
            points = player.get('total_points', 0)
            form = player.get('form', 0)
            status = player.get('status', 'a')
            
            status_text = "🟢" if status == 'a' else "🔴" if status == 'i' else "🟡"
            
            formatted.append(f"{status_text} {position}: {name} (£{price:.1f}m, {points}pts, form: {form})")
        
        return "\n".join(formatted)
    
    def _format_players_for_recommendations(self, players: List[Dict[str, Any]]) -> str:
        """Format players for recommendations prompt."""
        if not players:
            return "No players in squad"
        
        # Group by position
        positions = {'GK': [], 'DEF': [], 'MID': [], 'FWD': []}
        
        for player in players:
            position = player.get('position', 'UNK')
            if position in positions:
                name = player.get('full_name', 'Unknown')
                price = player.get('now_cost', 0) / 10.0
                points = player.get('total_points', 0)
                form = player.get('form', 0)
                positions[position].append(f"{name} (£{price:.1f}m, {points}pts, form: {form})")
        
        formatted = []
        for pos, players_list in positions.items():
            if players_list:
                formatted.append(f"{pos}: {', '.join(players_list)}")
        
        return "\n".join(formatted)
    
    def _format_performance_data(self, performance_data: Dict[str, Any]) -> str:
        """Format performance data for prompt."""
        if not performance_data:
            return "No performance data available"
        
        formatted = []
        for key, value in performance_data.items():
            if key != 'timestamp':
                formatted.append(f"{key}: {value}")
        
        return "\n".join(formatted)
    
    def _format_context_for_recommendations(self, context: Dict[str, Any]) -> str:
        """Format context for recommendations prompt."""
        formatted = []
        for key, value in context.items():
            formatted.append(f"{key}: {value}")
        
        return "\n".join(formatted)
    
    def _parse_analysis_response(self, response: str) -> Dict[str, Any]:
        """Parse LLM analysis response."""
        # Simple parsing - could be enhanced with more structured output
        return {
            'raw_response': response,
            'summary': response[:200] + "..." if len(response) > 200 else response
        }
    
    def _parse_performance_analysis_response(self, response: str) -> Dict[str, Any]:
        """Parse LLM performance analysis response."""
        return {
            'raw_response': response,
            'summary': response[:200] + "..." if len(response) > 200 else response
        }
    
    def _parse_recommendations_response(self, response: str) -> Dict[str, Any]:
        """Parse LLM recommendations response."""
        return {
            'raw_response': response,
            'summary': response[:200] + "..." if len(response) > 200 else response
        } 