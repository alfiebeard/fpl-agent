"""
Team Analysis Strategy

This strategy analyzes FPL teams and provides insights and recommendations.
"""

import logging
from typing import Dict, List, Any, Optional

from ..core.config import Config
from ..core.models import FPLTeam
from ..data.data_service import DataService
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
        self.validator = FPLValidator(config)
    
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