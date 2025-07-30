"""
LLM-based team creator using web search insights and AI analysis
"""

import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime

from ..models import Player, FPLTeam, Position, OptimizationResult, Transfer
from ..config import Config
from ..ingestion import get_test_data
from .web_search import FPLWebSearcher
from .llm_analyzer import FPLLLMAnalyzer

logger = logging.getLogger(__name__)


class LLMTeamCreator:
    """
    LLM-powered team creator using expert insights and AI analysis.
    
    This approach focuses on:
    - Web search for expert FPL insights and tips
    - LLM analysis of expert opinions and recommendations
    - Human-like decision making based on community wisdom
    - Contextual understanding of FPL meta and trends
    - Expert-driven captain and transfer selections
    - Wildcard timing based on expert consensus
    """
    
    def __init__(self, config: Config):
        self.config = config
        self.web_searcher = FPLWebSearcher(config)
        self.llm_analyzer = FPLLLMAnalyzer(config)
        self.analysis_config = config.get_llm_config().get('analysis', {})
        self.gather_timeout = self.analysis_config.get('gather_insights_timeout', 180)
        self.min_sources = self.analysis_config.get('min_sources', 5)
        self.confidence_threshold = self.analysis_config.get('confidence_threshold', 0.6)
    
    def create_team_from_scratch(self, budget: float = 100.0, 
                               gameweek: Optional[int] = None) -> OptimizationResult:
        """
        Create a completely new team from scratch using expert insights and LLM analysis.
        
        This method is suitable for:
        - Start of season team creation
        - Wildcard team creation
        - Complete team overhaul
        
        Args:
            budget: Available budget in millions
            gameweek: Current gameweek (for context)
            
        Returns:
            OptimizationResult with LLM-recommended team and insights
        """
        logger.info("Creating team from scratch using LLM-based approach...")
        
        try:
            # Step 1: Gather expert insights
            logger.info("Step 1: Gathering expert insights from web sources...")
            insights = self._gather_team_creation_insights(gameweek)
            
            if len(insights) < self.min_sources:
                logger.warning(f"Only found {len(insights)} insights, below minimum of {self.min_sources}")
            
            # Step 2: Get available players
            logger.info("Step 2: Fetching available players...")
            data = get_test_data(self.config, sample_size=500)  # Get comprehensive player data
            available_players = data['players']
            
            # Step 3: LLM analysis for team creation
            logger.info("Step 3: Analyzing insights with LLM for team creation...")
            llm_analysis = self.llm_analyzer.analyze_team_creation(
                insights, available_players, budget
            )
            
            # Step 4: Convert LLM analysis to OptimizationResult
            result = self._convert_team_analysis_to_result(
                llm_analysis, available_players, insights
            )
            
            # Step 5: Add LLM-specific metadata
            result.llm_insights = self._format_insights_summary(insights)
            result.reasoning = f"LLM Analysis: {llm_analysis.get('reasoning', '')}"
            result.confidence = llm_analysis.get('confidence', 0.5)
            
            logger.info("Team creation from scratch completed successfully using LLM approach")
            return result
            
        except Exception as e:
            logger.error(f"Failed to create team using LLM approach: {e}")
            return self._fallback_team_creation(available_players if 'available_players' in locals() else [], budget)
    
    def suggest_weekly_transfers(self, current_team: FPLTeam, 
                               free_transfers: int = 1,
                               gameweek: Optional[int] = None) -> OptimizationResult:
        """
        Suggest weekly transfers based on expert insights and LLM analysis.
        
        This method analyzes:
        - Current expert transfer recommendations
        - Player form and fixture analysis from experts
        - Injury updates and team news
        - Price change predictions
        - Community sentiment and ownership trends
        
        Args:
            current_team: Current FPL team
            free_transfers: Number of free transfers available
            gameweek: Current gameweek
            
        Returns:
            OptimizationResult with transfer recommendations
        """
        logger.info("Generating weekly transfer suggestions using LLM-based approach...")
        
        try:
            # Step 1: Gather transfer-specific insights
            logger.info("Step 1: Gathering transfer insights from expert sources...")
            insights = self._gather_transfer_insights(gameweek)
            
            # Step 2: Get available players for transfers
            logger.info("Step 2: Fetching available players for transfer analysis...")
            data = get_test_data(self.config, sample_size=500)
            available_players = data['players']
            
            # Step 3: LLM analysis for transfers
            logger.info("Step 3: Analyzing transfer options with LLM...")
            llm_analysis = self.llm_analyzer.analyze_weekly_transfers(
                insights, current_team, available_players, free_transfers
            )
            
            # Step 4: Convert to OptimizationResult
            result = self._convert_transfer_analysis_to_result(
                llm_analysis, current_team, available_players, insights
            )
            
            logger.info(f"Generated {len(result.transfers)} transfer suggestions using LLM approach")
            return result
            
        except Exception as e:
            logger.error(f"Failed to generate transfer suggestions using LLM approach: {e}")
            return self._fallback_transfer_suggestions(current_team)
    
    def select_captain_and_vice(self, team: FPLTeam, 
                              gameweek: Optional[int] = None) -> Tuple[int, int]:
        """
        Select captain and vice-captain based on expert insights and LLM analysis.
        
        This method considers:
        - Expert captain picks and recommendations
        - Fixture analysis from expert sources
        - Form and momentum insights
        - Penalty takers and set piece specialists
        - Differential vs template captain choices
        
        Args:
            team: Current FPL team
            gameweek: Current gameweek
            
        Returns:
            Tuple of (captain_id, vice_captain_id)
        """
        logger.info("Selecting captain and vice-captain using expert insights...")
        
        try:
            # Step 1: Gather captaincy insights
            logger.info("Step 1: Gathering captaincy insights from experts...")
            insights = self._gather_captaincy_insights(gameweek)
            
            # Step 2: LLM analysis for captaincy
            logger.info("Step 2: Analyzing captaincy options with LLM...")
            llm_analysis = self.llm_analyzer.analyze_captaincy(insights, team)
            
            # Step 3: Convert to player IDs
            captain_id, vice_captain_id = self._convert_captaincy_analysis(
                llm_analysis, team
            )
            
            logger.info(f"Selected captain and vice-captain using LLM analysis")
            return captain_id, vice_captain_id
            
        except Exception as e:
            logger.error(f"Failed to select captains using LLM approach: {e}")
            return self._fallback_captain_selection(team)
    
    def analyze_wildcard_usage(self, current_team: FPLTeam,
                             gameweek: Optional[int] = None) -> Dict[str, Any]:
        """
        Analyze whether wildcard should be used based on expert insights and LLM analysis.
        
        This method evaluates:
        - Expert wildcard timing advice
        - Template team shifts mentioned by experts
        - Fixture swing analysis from expert sources
        - Player price changes and trends
        - Injury crisis or player availability issues
        
        Args:
            current_team: Current FPL team
            gameweek: Current gameweek
            
        Returns:
            Analysis of wildcard usage recommendation
        """
        logger.info("Analyzing wildcard usage using expert insights...")
        
        try:
            # Step 1: Gather wildcard insights
            logger.info("Step 1: Gathering wildcard insights from experts...")
            insights = self._gather_wildcard_insights(gameweek)
            
            # Step 2: Get available players for wildcard analysis
            data = get_test_data(self.config, sample_size=500)
            available_players = data['players']
            
            # Step 3: LLM analysis for wildcard usage
            logger.info("Step 3: Analyzing wildcard timing with LLM...")
            llm_analysis = self.llm_analyzer.analyze_wildcard_usage(
                insights, current_team, available_players
            )
            
            # Step 4: Enhance analysis with insights metadata
            recommendation = {
                'should_use_wildcard': llm_analysis.get('use_wildcard', False),
                'reasoning': llm_analysis.get('reasoning', ''),
                'confidence': llm_analysis.get('confidence', 0.5),
                'optimal_timing': llm_analysis.get('optimal_timing', 'later'),
                'expert_insights_used': len(insights),
                'key_factors': llm_analysis.get('key_factors', []),
                'template_changes': llm_analysis.get('template_changes', []),
                'insights_summary': self._format_insights_summary(insights)
            }
            
            logger.info(f"Wildcard analysis complete using LLM approach. Recommendation: {recommendation['should_use_wildcard']}")
            return recommendation
            
        except Exception as e:
            logger.error(f"Failed to analyze wildcard usage using LLM approach: {e}")
            return self._fallback_wildcard_analysis(current_team)
    
    def get_weekly_recommendations(self, current_team: FPLTeam,
                                 free_transfers: int = 1,
                                 gameweek: Optional[int] = None) -> Dict[str, Any]:
        """
        Get comprehensive weekly recommendations including transfers, captaincy, and wildcard analysis.
        
        This is the main weekly method that provides all FPL decisions for the gameweek.
        
        Args:
            current_team: Current FPL team
            free_transfers: Number of free transfers available
            gameweek: Current gameweek
            
        Returns:
            Comprehensive weekly recommendations
        """
        logger.info("Generating comprehensive weekly recommendations using LLM approach...")
        
        try:
            # Gather all insights in parallel for efficiency
            logger.info("Gathering comprehensive insights for weekly analysis...")
            
            # Get gameweek-specific insights
            gameweek_insights = self.web_searcher.search_gameweek_specific(gameweek) if gameweek else []
            transfer_insights = self.web_searcher.search_transfer_insights()
            captain_insights = self.web_searcher.search_captain_insights()
            wildcard_insights = self.web_searcher.search_wildcard_insights()
            
            # Combine all insights
            all_insights = gameweek_insights + transfer_insights + captain_insights + wildcard_insights
            
            logger.info(f"Gathered {len(all_insights)} total insights from {len(set(i.get('source', 'Unknown') for i in all_insights))} sources")
            
            # Get transfer recommendations
            transfer_result = self.suggest_weekly_transfers(current_team, free_transfers, gameweek)
            
            # Get captain recommendations
            captain_id, vice_captain_id = self.select_captain_and_vice(current_team, gameweek)
            
            # Get wildcard analysis
            wildcard_analysis = self.analyze_wildcard_usage(current_team, gameweek)
            
            # Compile comprehensive recommendations
            recommendations = {
                'gameweek': gameweek,
                'transfers': {
                    'recommended_transfers': transfer_result.transfers,
                    'reasoning': transfer_result.reasoning,
                    'confidence': transfer_result.confidence
                },
                'captaincy': {
                    'captain_id': captain_id,
                    'vice_captain_id': vice_captain_id,
                    'captain_name': self._get_player_name_by_id(current_team, captain_id),
                    'vice_captain_name': self._get_player_name_by_id(current_team, vice_captain_id)
                },
                'wildcard': wildcard_analysis,
                'insights_summary': {
                    'total_insights': len(all_insights),
                    'sources': list(set(i.get('source', 'Unknown') for i in all_insights)),
                    'key_topics': self._extract_key_topics(all_insights)
                },
                'overall_confidence': self._calculate_overall_confidence([
                    transfer_result.confidence,
                    wildcard_analysis.get('confidence', 0.5)
                ]),
                'generated_at': datetime.now().isoformat()
            }
            
            logger.info("Comprehensive weekly recommendations generated successfully")
            return recommendations
            
        except Exception as e:
            logger.error(f"Failed to generate weekly recommendations: {e}")
            return self._fallback_weekly_recommendations(current_team, free_transfers, gameweek)
    
    # Private helper methods
    
    def _gather_team_creation_insights(self, gameweek: Optional[int]) -> List[Dict[str, Any]]:
        """Gather insights specific to team creation"""
        insights = []
        
        # General FPL insights
        general_insights = self.web_searcher.search_fpl_insights()
        insights.extend(general_insights)
        
        # Wildcard insights (relevant for team creation)
        wildcard_insights = self.web_searcher.search_wildcard_insights()
        insights.extend(wildcard_insights)
        
        # Gameweek-specific insights if available
        if gameweek:
            gameweek_insights = self.web_searcher.search_gameweek_specific(gameweek)
            insights.extend(gameweek_insights)
        
        return insights
    
    def _gather_transfer_insights(self, gameweek: Optional[int]) -> List[Dict[str, Any]]:
        """Gather insights specific to transfers"""
        insights = []
        
        # Transfer-specific insights
        transfer_insights = self.web_searcher.search_transfer_insights()
        insights.extend(transfer_insights)
        
        # Gameweek-specific insights
        if gameweek:
            gameweek_insights = self.web_searcher.search_gameweek_specific(gameweek)
            insights.extend(gameweek_insights)
        
        return insights
    
    def _gather_captaincy_insights(self, gameweek: Optional[int]) -> List[Dict[str, Any]]:
        """Gather insights specific to captaincy"""
        insights = []
        
        # Captain-specific insights
        captain_insights = self.web_searcher.search_captain_insights()
        insights.extend(captain_insights)
        
        # Gameweek-specific insights
        if gameweek:
            gameweek_insights = self.web_searcher.search_gameweek_specific(gameweek)
            insights.extend(gameweek_insights)
        
        return insights
    
    def _gather_wildcard_insights(self, gameweek: Optional[int]) -> List[Dict[str, Any]]:
        """Gather insights specific to wildcard usage"""
        insights = []
        
        # Wildcard-specific insights
        wildcard_insights = self.web_searcher.search_wildcard_insights()
        insights.extend(wildcard_insights)
        
        # General FPL insights for context
        general_insights = self.web_searcher.search_fpl_insights()
        insights.extend(general_insights[:5])  # Just top 5 for context
        
        return insights
    
    def _convert_team_analysis_to_result(self, llm_analysis: Dict[str, Any],
                                       available_players: List[Player],
                                       insights: List[Dict[str, Any]]) -> OptimizationResult:
        """Convert LLM team analysis to OptimizationResult"""
        
        # Extract recommended team from LLM analysis
        recommended_team = llm_analysis.get('recommended_team', {})
        
        # Find actual player objects
        selected_players = []
        player_name_to_obj = {p.name: p for p in available_players}
        
        for position, player_names in recommended_team.items():
            for name in player_names:
                if name in player_name_to_obj:
                    selected_players.append(player_name_to_obj[name])
                else:
                    # Find best match if exact name not found
                    best_match = self._find_best_player_match(name, available_players, position)
                    if best_match:
                        selected_players.append(best_match)
        
        # Get captain and vice-captain IDs
        captain_name = llm_analysis.get('captain', '')
        vice_captain_name = llm_analysis.get('vice_captain', '')
        
        captain_id = None
        vice_captain_id = None
        
        for player in selected_players:
            if player.name == captain_name:
                captain_id = player.id
            elif player.name == vice_captain_name:
                vice_captain_id = player.id
        
        # Calculate expected points (simplified)
        expected_points = sum(p.points_per_game for p in selected_players)
        
        return OptimizationResult(
            selected_players=selected_players,
            captain_id=captain_id,
            vice_captain_id=vice_captain_id,
            expected_points=expected_points,
            confidence=llm_analysis.get('confidence', 0.5),
            reasoning=llm_analysis.get('reasoning', ''),
            llm_insights=self._format_insights_summary(insights)
        )
    
    def _convert_transfer_analysis_to_result(self, llm_analysis: Dict[str, Any],
                                           current_team: FPLTeam,
                                           available_players: List[Player],
                                           insights: List[Dict[str, Any]]) -> OptimizationResult:
        """Convert LLM transfer analysis to OptimizationResult"""
        
        # Extract transfers from LLM analysis
        recommended_transfers = llm_analysis.get('recommended_transfers', [])
        
        transfers = []
        player_name_to_obj = {p.name: p for p in available_players + current_team.players}
        
        for transfer_data in recommended_transfers:
            player_out_name = transfer_data.get('player_out', '')
            player_in_name = transfer_data.get('player_in', '')
            reason = transfer_data.get('reason', '')
            
            player_out = player_name_to_obj.get(player_out_name)
            player_in = player_name_to_obj.get(player_in_name)
            
            if player_out and player_in:
                transfer = Transfer(
                    player_out=player_out,
                    player_in=player_in,
                    gameweek=1,  # Would be current gameweek in real implementation
                    reason=reason
                )
                transfers.append(transfer)
        
        # Get captain and vice-captain
        captain_name = llm_analysis.get('captain', '')
        vice_captain_name = llm_analysis.get('vice_captain', '')
        
        captain_id = None
        vice_captain_id = None
        
        for player in current_team.players:
            if player.name == captain_name:
                captain_id = player.id
            elif player.name == vice_captain_name:
                vice_captain_id = player.id
        
        return OptimizationResult(
            selected_players=current_team.players,
            transfers=transfers,
            captain_id=captain_id,
            vice_captain_id=vice_captain_id,
            confidence=llm_analysis.get('confidence', 0.5),
            reasoning=llm_analysis.get('reasoning', ''),
            llm_insights=self._format_insights_summary(insights)
        )
    
    def _convert_captaincy_analysis(self, llm_analysis: Dict[str, Any],
                                  team: FPLTeam) -> Tuple[int, int]:
        """Convert LLM captaincy analysis to player IDs"""
        captain_name = llm_analysis.get('captain', '')
        vice_captain_name = llm_analysis.get('vice_captain', '')
        
        captain_id = None
        vice_captain_id = None
        
        for player in team.players:
            if player.name == captain_name:
                captain_id = player.id
            elif player.name == vice_captain_name:
                vice_captain_id = player.id
        
        # Fallback to first two players if names don't match
        if not captain_id and team.players:
            captain_id = team.players[0].id
        if not vice_captain_id and len(team.players) > 1:
            vice_captain_id = team.players[1].id
        elif not vice_captain_id:
            vice_captain_id = captain_id
        
        return captain_id, vice_captain_id
    
    def _find_best_player_match(self, name: str, players: List[Player], 
                              position: str) -> Optional[Player]:
        """Find best matching player by name and position"""
        position_enum = Position(position) if position in ['GK', 'DEF', 'MID', 'FWD'] else None
        
        # Filter by position if valid
        candidates = players
        if position_enum:
            candidates = [p for p in players if p.position == position_enum]
        
        # Simple name matching (could be improved with fuzzy matching)
        name_lower = name.lower()
        for player in candidates:
            if name_lower in player.name.lower() or player.name.lower() in name_lower:
                return player
        
        # Return first player of position if no match found
        return candidates[0] if candidates else None
    
    def _format_insights_summary(self, insights: List[Dict[str, Any]]) -> str:
        """Format insights into a readable summary"""
        if not insights:
            return "No expert insights available."
        
        summary_parts = []
        summary_parts.append(f"Expert insights from {len(insights)} sources:")
        
        # Group by source
        sources = {}
        for insight in insights:
            source = insight.get('source', 'Unknown')
            if source not in sources:
                sources[source] = []
            sources[source].append(insight)
        
        for source, source_insights in sources.items():
            summary_parts.append(f"\n{source} ({len(source_insights)} insights):")
            for insight in source_insights[:2]:  # Top 2 per source
                title = insight.get('title', '')[:100] + '...' if len(insight.get('title', '')) > 100 else insight.get('title', '')
                if title:
                    summary_parts.append(f"  - {title}")
        
        return '\n'.join(summary_parts)
    
    def _get_player_name_by_id(self, team: FPLTeam, player_id: Optional[int]) -> str:
        """Get player name by ID from team"""
        if not player_id:
            return "Unknown"
        
        for player in team.players:
            if player.id == player_id:
                return player.name
        
        return "Unknown"
    
    def _extract_key_topics(self, insights: List[Dict[str, Any]]) -> List[str]:
        """Extract key topics from insights"""
        all_content = ' '.join(insight.get('content', '') for insight in insights)
        
        # Simple keyword extraction
        fpl_keywords = [
            'captain', 'transfer', 'wildcard', 'bench boost', 'triple captain',
            'differential', 'template', 'rotation', 'fixtures', 'form', 'injury'
        ]
        
        found_topics = []
        content_lower = all_content.lower()
        
        for keyword in fpl_keywords:
            if keyword in content_lower:
                found_topics.append(keyword.title())
        
        return found_topics[:10]  # Return top 10 topics
    
    def _calculate_overall_confidence(self, confidences: List[float]) -> float:
        """Calculate overall confidence from multiple confidence scores"""
        if not confidences:
            return 0.5
        
        # Average confidence with slight penalty for multiple decisions
        avg_confidence = sum(confidences) / len(confidences)
        penalty = 0.05 * (len(confidences) - 1)  # Small penalty for complexity
        
        return max(0.1, avg_confidence - penalty)
    
    # Fallback methods
    
    def _fallback_team_creation(self, players: List[Player], budget: float) -> OptimizationResult:
        """Fallback team creation when LLM approach fails"""
        logger.warning("Using fallback team creation method")
        
        # Simple fallback: select top players by form
        players_by_position = {
            Position.GK: [p for p in players if p.position == Position.GK],
            Position.DEF: [p for p in players if p.position == Position.DEF],
            Position.MID: [p for p in players if p.position == Position.MID],
            Position.FWD: [p for p in players if p.position == Position.FWD]
        }
        
        selected_players = []
        
        # Select players by position
        for position, count in [(Position.GK, 2), (Position.DEF, 5), (Position.MID, 5), (Position.FWD, 3)]:
            position_players = sorted(players_by_position.get(position, []), 
                                    key=lambda p: p.form + p.points_per_game, reverse=True)
            selected_players.extend(position_players[:count])
        
        return OptimizationResult(
            selected_players=selected_players,
            captain_id=selected_players[0].id if selected_players else None,
            vice_captain_id=selected_players[1].id if len(selected_players) > 1 else None,
            confidence=0.3,
            reasoning="Fallback team creation due to LLM unavailability"
        )
    
    def _fallback_transfer_suggestions(self, current_team: FPLTeam) -> OptimizationResult:
        """Fallback transfer suggestions when LLM approach fails"""
        logger.warning("Using fallback transfer suggestion method")
        
        return OptimizationResult(
            selected_players=current_team.players,
            transfers=[],
            captain_id=current_team.players[0].id if current_team.players else None,
            vice_captain_id=current_team.players[1].id if len(current_team.players) > 1 else None,
            confidence=0.3,
            reasoning="Fallback - no transfers recommended due to LLM unavailability"
        )
    
    def _fallback_captain_selection(self, team: FPLTeam) -> Tuple[int, int]:
        """Fallback captain selection when LLM approach fails"""
        logger.warning("Using fallback captain selection method")
        
        if not team.players:
            return None, None
        
        # Sort by form and select top 2
        sorted_players = sorted(team.players, key=lambda p: p.form + p.points_per_game, reverse=True)
        
        captain_id = sorted_players[0].id
        vice_captain_id = sorted_players[1].id if len(sorted_players) > 1 else captain_id
        
        return captain_id, vice_captain_id
    
    def _fallback_wildcard_analysis(self, current_team: FPLTeam) -> Dict[str, Any]:
        """Fallback wildcard analysis when LLM approach fails"""
        logger.warning("Using fallback wildcard analysis method")
        
        return {
            'should_use_wildcard': False,
            'reasoning': 'Conservative approach - LLM analysis unavailable',
            'confidence': 0.3,
            'optimal_timing': 'later',
            'expert_insights_used': 0,
            'key_factors': ['LLM unavailable'],
            'template_changes': []
        }
    
    def _fallback_weekly_recommendations(self, current_team: FPLTeam,
                                       free_transfers: int,
                                       gameweek: Optional[int]) -> Dict[str, Any]:
        """Fallback weekly recommendations when LLM approach fails"""
        logger.warning("Using fallback weekly recommendations method")
        
        captain_id, vice_captain_id = self._fallback_captain_selection(current_team)
        
        return {
            'gameweek': gameweek,
            'transfers': {
                'recommended_transfers': [],
                'reasoning': 'No transfers recommended - LLM analysis unavailable',
                'confidence': 0.3
            },
            'captaincy': {
                'captain_id': captain_id,
                'vice_captain_id': vice_captain_id,
                'captain_name': self._get_player_name_by_id(current_team, captain_id),
                'vice_captain_name': self._get_player_name_by_id(current_team, vice_captain_id)
            },
            'wildcard': self._fallback_wildcard_analysis(current_team),
            'insights_summary': {
                'total_insights': 0,
                'sources': [],
                'key_topics': []
            },
            'overall_confidence': 0.3,
            'generated_at': datetime.now().isoformat()
        }