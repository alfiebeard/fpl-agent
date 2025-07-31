"""
Simplified LLM-based team creator using Gemini's web search
"""

import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime

from ..models import Player, FPLTeam, Position, OptimizationResult, Transfer
from ..config import Config
from ..ingestion import get_test_data
from .llm_analyzer import FPLLLMAnalyzer

logger = logging.getLogger(__name__)


class LLMTeamCreator:
    """
    Simplified LLM-powered team creator using Gemini's built-in web search.
    
    This approach focuses on:
    - Using Gemini's web search for current FPL insights
    - LLM analysis of expert opinions and recommendations
    - Human-like decision making based on community wisdom
    - Contextual understanding of FPL meta and trends
    """
    
    def __init__(self, config: Config):
        self.config = config
        self.llm_analyzer = FPLLLMAnalyzer(config)
    
    def create_team_from_scratch(self, budget: float = 100.0, 
                               gameweek: Optional[int] = None) -> OptimizationResult:
        """
        Create a completely new team from scratch using LLM analysis with web search.
        
        Args:
            budget: Available budget in millions
            gameweek: Current gameweek (for context)
            
        Returns:
            OptimizationResult with LLM-recommended team and insights
        """
        logger.info("Creating team from scratch using LLM-based approach...")
        
        try:
            # Get available players
            logger.info("Fetching available players...")
            data = get_test_data(self.config, sample_size=500)  # Get comprehensive player data
            available_players = data['players']
            
            # Use LLM analyzer with web search
            logger.info("Analyzing with LLM and web search...")
            llm_analysis = self.llm_analyzer.create_team(
                available_players, budget, gameweek or 1
            )
            
            # Convert to OptimizationResult
            result = self._convert_analysis_to_result(llm_analysis, available_players)
            
            logger.info("Team creation completed successfully using LLM approach")
            return result
            
        except Exception as e:
            logger.error(f"Failed to create team using LLM approach: {e}")
            return self._fallback_team_creation(available_players if 'available_players' in locals() else [], budget)
    
    def _convert_analysis_to_result(self, llm_analysis: Dict[str, Any], 
                                  available_players: List[Player]) -> OptimizationResult:
        """Convert LLM analysis to OptimizationResult"""
        
        # Create FPLTeam object
        selected_players = []
        team_data = llm_analysis.get('team', {})
        
        # Convert player names to Player objects
        for position, player_names in team_data.items():
            for player_name in player_names:
                player = self._find_player_by_name(player_name, available_players)
                if player:
                    selected_players.append(player)
        
        # Create FPLTeam
        fpl_team = FPLTeam(
            id=1,
            name="LLM Optimized Team",
            players=selected_players,
            captain_id=self._find_player_id_by_name(llm_analysis.get('captain', ''), selected_players),
            vice_captain_id=self._find_player_id_by_name(llm_analysis.get('vice_captain', ''), selected_players),
            formation=llm_analysis.get('formation', '4-4-2'),
            total_cost=llm_analysis.get('total_cost', 0.0)
        )
        
        # Create OptimizationResult
        result = OptimizationResult(
            team=fpl_team,
            expected_points=0.0,  # LLM doesn't provide this
            total_cost=fpl_team.total_cost,
            transfers=[],
            reasoning=llm_analysis.get('reasoning', ''),
            confidence=0.8,  # High confidence for LLM approach
            method="LLM with Web Search"
        )
        
        # Add LLM-specific metadata
        result.llm_insights = llm_analysis.get('web_insights', '')
        
        return result
    
    def _find_player_by_name(self, name: str, players: List[Player]) -> Optional[Player]:
        """Find a player by name (case-insensitive)"""
        name_lower = name.lower()
        for player in players:
            if player.name.lower() == name_lower:
                return player
        return None
    
    def _find_player_id_by_name(self, name: str, players: List[Player]) -> Optional[int]:
        """Find a player ID by name"""
        player = self._find_player_by_name(name, players)
        return player.id if player else None
    
    def _fallback_team_creation(self, players: List[Player], budget: float) -> OptimizationResult:
        """Fallback team creation without LLM"""
        logger.warning("Using fallback team creation")
        
        # Simple fallback: select top players by form within budget
        sorted_players = sorted(players, key=lambda p: p.form, reverse=True)
        
        selected_players = []
        total_cost = 0.0
        
        for player in sorted_players:
            if total_cost + player.price <= budget and len(selected_players) < 15:
                selected_players.append(player)
                total_cost += player.price
        
        # Create FPLTeam
        fpl_team = FPLTeam(
            id=1,
            name="Fallback Team",
            players=selected_players,
            captain_id=selected_players[0].id if selected_players else None,
            vice_captain_id=selected_players[1].id if len(selected_players) > 1 else None,
            formation="4-4-2",
            total_cost=total_cost
        )
        
        return OptimizationResult(
            team=fpl_team,
            expected_points=0.0,
            total_cost=total_cost,
            transfers=[],
            reasoning="Fallback team created using form-based selection",
            confidence=0.5,
            method="Fallback"
        )