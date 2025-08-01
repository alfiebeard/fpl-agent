"""
Model-based team creator using statistical analysis and xPts calculations
"""

import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime

from ..models import Player, FPLTeam, Position, OptimizationResult, Transfer
from ..config import Config
from ..optimizer import ILPSolver
from ..ingestion import get_test_data

logger = logging.getLogger(__name__)


class ModelStrategy:
    """
    Model-driven team creator using statistical analysis, xPts, and optimization algorithms.
    
    This approach focuses on:
    - Real-time FPL API data
    - Expected points (xPts) calculations
    - Statistical analysis of player performance
    - Mathematical optimization using ILP
    - Fixture difficulty analysis
    - Form and momentum metrics
    """
    
    def __init__(self, config: Config):
        self.config = config
        self.ilp_solver = ILPSolver(config)
        self.team_config = config.get_team_config()
        self.optimization_config = config.get_optimization_config()
        self.xpts_config = config.get_xpts_config()
    
    def create_team_from_scratch(self, budget: float = 100.0) -> OptimizationResult:
        """
        Create a completely new team from scratch using model data and statistical analysis.
        
        Args:
            budget: Available budget in millions
            
        Returns:
            OptimizationResult with selected team and analysis
        """
        logger.info("Creating team from scratch using model-based approach...")
        
        try:
            # Fetch all available players
            data = get_test_data(self.config, sample_size=500)  # Get more players for full team creation
            players = data['players']
            
            logger.info(f"Analyzing {len(players)} players for team creation")
            
            # Calculate comprehensive expected points
            player_xpts = self._calculate_comprehensive_xpts(players)
            
            # Create empty team for optimization
            empty_team = FPLTeam(
                team_id=1, 
                team_name="New Team", 
                manager_name="Manager", 
                players=[],
                total_value=budget
            )
            
            # Optimize team selection
            result = self.ilp_solver.optimize_team(players, empty_team, player_xpts)
            
            # Add API-specific analysis
            result.reasoning = self._generate_api_reasoning(result, players, player_xpts)
            result.confidence = self._calculate_confidence(result, players, player_xpts)
            
            logger.info("Team creation from scratch completed successfully")
            return result
            
        except Exception as e:
            logger.error(f"Failed to create team from scratch: {e}")
            raise
    
    def suggest_weekly_transfers(self, current_team: FPLTeam, 
                               free_transfers: int = 1,
                               max_hits: int = 1) -> OptimizationResult:
        """
        Suggest weekly transfers based on statistical analysis and xPts projections.
        
        Args:
            current_team: Current FPL team
            free_transfers: Number of free transfers available
            max_hits: Maximum transfer hits willing to take
            
        Returns:
            OptimizationResult with suggested transfers
        """
        logger.info("Generating weekly transfer suggestions using model-based approach...")
        
        try:
            # Fetch latest player data
            data = get_test_data(self.config, sample_size=500)
            all_players = data['players']
            
            # Calculate expected points for next gameweek
            player_xpts = self._calculate_gameweek_xpts(all_players)
            
            # Analyze current team performance
            current_performance = self._analyze_current_team(current_team, player_xpts)
            
            # Find optimal transfers
            transfers = self._find_optimal_transfers(
                current_team, all_players, player_xpts, 
                free_transfers, max_hits
            )
            
            # Select captain and vice-captain
            captain_id, vice_captain_id = self._select_captains_statistical(
                current_team, player_xpts
            )
            
            # Create result
            result = OptimizationResult(
                selected_players=current_team.players,
                transfers=transfers,
                captain_id=captain_id,
                vice_captain_id=vice_captain_id,
                expected_points=sum(player_xpts.get(p.id, 0) for p in current_team.players),
                confidence=self._calculate_transfer_confidence(transfers, player_xpts),
                reasoning=self._generate_transfer_reasoning(transfers, current_performance)
            )
            
            logger.info(f"Generated {len(transfers)} transfer suggestions")
            return result
            
        except Exception as e:
            logger.error(f"Failed to generate transfer suggestions: {e}")
            raise
    
    def select_captain_and_vice(self, team: FPLTeam) -> Tuple[int, int]:
        """
        Select captain and vice-captain based on statistical analysis.
        
        Args:
            team: Current FPL team
            
        Returns:
            Tuple of (captain_id, vice_captain_id)
        """
        logger.info("Selecting captain and vice-captain using statistical analysis...")
        
        try:
            # Get latest data for captain selection
            data = get_test_data(self.config, sample_size=100)
            all_players = data['players']
            
            # Calculate gameweek-specific xPts
            player_xpts = self._calculate_gameweek_xpts(all_players)
            
            return self._select_captains_statistical(team, player_xpts)
            
        except Exception as e:
            logger.error(f"Failed to select captains: {e}")
            raise
    
    def analyze_wildcard_usage(self, current_team: FPLTeam) -> Dict[str, Any]:
        """
        Analyze whether wildcard should be used based on statistical projections.
        
        Args:
            current_team: Current FPL team
            
        Returns:
            Analysis of wildcard usage recommendation
        """
        logger.info("Analyzing wildcard usage using statistical projections...")
        
        try:
            # Get comprehensive data
            data = get_test_data(self.config, sample_size=500)
            all_players = data['players']
            
            # Calculate long-term xPts (next 5-10 gameweeks)
            long_term_xpts = self._calculate_long_term_xpts(all_players)
            
            # Analyze current team vs optimal team
            current_value = sum(long_term_xpts.get(p.id, 0) for p in current_team.players)
            
            # Create optimal team
            optimal_result = self.create_team_from_scratch(current_team.total_value)
            optimal_value = optimal_result.expected_points_next_5
            
            improvement = optimal_value - current_value
            wildcard_threshold = self.optimization_config.get('wildcard_threshold', 20)
            
            recommendation = {
                'should_use_wildcard': improvement > wildcard_threshold,
                'expected_improvement': improvement,
                'current_team_value': current_value,
                'optimal_team_value': optimal_value,
                'confidence': min(improvement / wildcard_threshold, 1.0) if improvement > 0 else 0,
                'reasoning': self._generate_wildcard_reasoning(improvement, wildcard_threshold)
            }
            
            logger.info(f"Wildcard analysis complete. Recommendation: {recommendation['should_use_wildcard']}")
            return recommendation
            
        except Exception as e:
            logger.error(f"Failed to analyze wildcard usage: {e}")
            raise
    
    def _calculate_comprehensive_xpts(self, players: List[Player]) -> Dict[int, float]:
        """Calculate comprehensive expected points using multiple factors"""
        xpts = {}
        weights = self.xpts_config.get('weights', {})
        
        for player in players:
            # Base calculation from form and historical performance
            form_xpts = player.form * weights.get('form', 0.3)
            
            # Expected goals and assists
            xg_xa_xpts = (getattr(player, 'xG', 0) * 4 + getattr(player, 'xA', 0) * 3) * weights.get('xg_xa', 0.4)
            
            # Playing time adjustment
            minutes_factor = (player.minutes_played / 90) if player.minutes_played > 0 else player.xMins_pct
            minutes_xpts = minutes_factor * weights.get('minutes', 0.1)
            
            # Fixture difficulty (simplified)
            fixture_xpts = self._calculate_fixture_difficulty_xpts(player) * weights.get('fixtures', 0.2)
            
            # Position-specific adjustments
            position_multiplier = self._get_position_multiplier(player.position)
            
            total_xpts = (form_xpts + xg_xa_xpts + fixture_xpts) * position_multiplier + minutes_xpts
            
            # Injury adjustment
            if player.is_injured:
                total_xpts *= 0.1  # Heavily penalize injured players
            elif not player.is_available:
                total_xpts *= 0.3
            
            xpts[player.id] = max(0, total_xpts)
        
        return xpts
    
    def _calculate_gameweek_xpts(self, players: List[Player]) -> Dict[int, float]:
        """Calculate expected points for the next gameweek specifically"""
        # Similar to comprehensive but with focus on immediate fixtures
        return self._calculate_comprehensive_xpts(players)
    
    def _calculate_long_term_xpts(self, players: List[Player]) -> Dict[int, float]:
        """Calculate expected points over next 5-10 gameweeks"""
        base_xpts = self._calculate_comprehensive_xpts(players)
        
        # Apply decay factor for future gameweeks
        decay_factor = self.optimization_config.get('xpts_decay_factor', 0.85)
        
        long_term_xpts = {}
        for player_id, xpts in base_xpts.items():
            # Project over 5 gameweeks with decay
            total_xpts = sum(xpts * (decay_factor ** i) for i in range(5))
            long_term_xpts[player_id] = total_xpts
        
        return long_term_xpts
    
    def _calculate_fixture_difficulty_xpts(self, player: Player) -> float:
        """Calculate expected points based on fixture difficulty"""
        # Simplified fixture analysis - in real implementation, 
        # this would analyze upcoming fixtures
        base_difficulty = 3  # Neutral difficulty
        team_strength = getattr(player, 'team_strength', 50)  # Team strength out of 100
        
        # Better teams get more points against average opposition
        difficulty_adjustment = (team_strength - 50) / 100
        return 2.0 + difficulty_adjustment  # Base 2 points with adjustment
    
    def _get_position_multiplier(self, position: Position) -> float:
        """Get position-specific multiplier for expected points"""
        multipliers = {
            Position.GK: 0.8,
            Position.DEF: 0.9,
            Position.MID: 1.0,
            Position.FWD: 1.1
        }
        return multipliers.get(position, 1.0)
    
    def _analyze_current_team(self, team: FPLTeam, player_xpts: Dict[int, float]) -> Dict[str, Any]:
        """Analyze current team performance and identify weaknesses"""
        analysis = {
            'total_xpts': sum(player_xpts.get(p.id, 0) for p in team.players),
            'weak_positions': [],
            'underperforming_players': [],
            'injury_concerns': []
        }
        
        # Analyze by position
        for position in Position:
            position_players = team.get_players_by_position(position)
            if position_players:
                avg_xpts = sum(player_xpts.get(p.id, 0) for p in position_players) / len(position_players)
                if avg_xpts < 2.0:  # Threshold for underperformance
                    analysis['weak_positions'].append(position.value)
        
        # Find underperforming players
        for player in team.players:
            xpts = player_xpts.get(player.id, 0)
            if xpts < 1.5:  # Low expected points threshold
                analysis['underperforming_players'].append(player)
        
        # Check injury concerns
        for player in team.players:
            if player.is_injured or not player.is_available:
                analysis['injury_concerns'].append(player)
        
        return analysis
    
    def _find_optimal_transfers(self, current_team: FPLTeam, all_players: List[Player],
                              player_xpts: Dict[int, float], free_transfers: int,
                              max_hits: int) -> List[Transfer]:
        """Find optimal transfers using statistical analysis"""
        transfers = []
        available_transfers = free_transfers + max_hits
        
        if available_transfers == 0:
            return transfers
        
        # Get players not in current team
        current_player_ids = {p.id for p in current_team.players}
        available_players = [p for p in all_players if p.id not in current_player_ids]
        
        # Find best transfer opportunities
        transfer_opportunities = []
        
        for current_player in current_team.players:
            current_xpts = player_xpts.get(current_player.id, 0)
            
            # Find better replacements in same position
            same_position_players = [p for p in available_players if p.position == current_player.position]
            
            for replacement in same_position_players:
                replacement_xpts = player_xpts.get(replacement.id, 0)
                price_diff = replacement.price - current_player.price
                
                # Check if transfer is financially viable
                if current_team.bank + price_diff >= 0:
                    xpts_improvement = replacement_xpts - current_xpts
                    
                    # Only consider if significant improvement
                    if xpts_improvement > 1.0:  # Minimum improvement threshold
                        transfer_opportunities.append({
                            'player_out': current_player,
                            'player_in': replacement,
                            'xpts_improvement': xpts_improvement,
                            'price_diff': price_diff
                        })
        
        # Sort by expected points improvement
        transfer_opportunities.sort(key=lambda x: x['xpts_improvement'], reverse=True)
        
        # Select top transfers within available transfer limit
        for i, opportunity in enumerate(transfer_opportunities[:available_transfers]):
            cost = 4 if i >= free_transfers else 0  # Transfer hit cost
            
            transfer = Transfer(
                player_out=opportunity['player_out'],
                player_in=opportunity['player_in'],
                gameweek=1,  # Would be current gameweek in real implementation
                cost=cost,
                reason=f"Expected points improvement: {opportunity['xpts_improvement']:.1f}"
            )
            transfers.append(transfer)
        
        return transfers
    
    def _select_captains_statistical(self, team: FPLTeam, 
                                   player_xpts: Dict[int, float]) -> Tuple[int, int]:
        """Select captain and vice-captain based on expected points"""
        # Sort team players by expected points
        team_players_with_xpts = [
            (p, player_xpts.get(p.id, 0)) for p in team.players
        ]
        team_players_with_xpts.sort(key=lambda x: x[1], reverse=True)
        
        if len(team_players_with_xpts) >= 2:
            captain_id = team_players_with_xpts[0][0].id
            vice_captain_id = team_players_with_xpts[1][0].id
        elif len(team_players_with_xpts) == 1:
            captain_id = team_players_with_xpts[0][0].id
            vice_captain_id = captain_id
        else:
            # Fallback
            captain_id = team.players[0].id if team.players else None
            vice_captain_id = captain_id
        
        return captain_id, vice_captain_id
    
    def _calculate_confidence(self, result: OptimizationResult, 
                            players: List[Player], 
                            player_xpts: Dict[int, float]) -> float:
        """Calculate confidence score for the optimization result"""
        if not result.selected_players:
            return 0.0
        
        # Base confidence on expected points distribution
        selected_xpts = [player_xpts.get(p.id, 0) for p in result.selected_players]
        avg_xpts = sum(selected_xpts) / len(selected_xpts)
        
        # Higher average xPts = higher confidence
        confidence = min(avg_xpts / 5.0, 1.0)  # Normalize to 0-1 scale
        
        return confidence
    
    def _calculate_transfer_confidence(self, transfers: List[Transfer], 
                                     player_xpts: Dict[int, float]) -> float:
        """Calculate confidence score for transfer suggestions"""
        if not transfers:
            return 1.0  # High confidence in no transfers if none suggested
        
        # Base confidence on expected improvement
        total_improvement = sum(
            player_xpts.get(t.player_in.id, 0) - player_xpts.get(t.player_out.id, 0)
            for t in transfers
        )
        
        # Normalize confidence based on improvement
        confidence = min(total_improvement / 10.0, 1.0)  # 10 points improvement = full confidence
        
        return max(confidence, 0.1)  # Minimum confidence
    
    def _generate_api_reasoning(self, result: OptimizationResult, 
                               players: List[Player], 
                               player_xpts: Dict[int, float]) -> str:
        """Generate reasoning for API-based team selection"""
        reasoning_parts = [
            "Team created using statistical analysis and API data:",
            f"- Analyzed {len(players)} players using expected points calculations",
            f"- Selected team has {len(result.selected_players)} players",
            f"- Total expected points: {result.expected_points:.1f}",
            "- Selection based on form, xG/xA, fixture difficulty, and playing time",
            "- Optimized using Integer Linear Programming for maximum points"
        ]
        
        return "\n".join(reasoning_parts)
    
    def _generate_transfer_reasoning(self, transfers: List[Transfer], 
                                   current_analysis: Dict[str, Any]) -> str:
        """Generate reasoning for transfer suggestions"""
        if not transfers:
            return "No transfers recommended based on current statistical analysis."
        
        reasoning_parts = [
            f"Recommended {len(transfers)} transfers based on statistical analysis:",
        ]
        
        for i, transfer in enumerate(transfers, 1):
            reasoning_parts.append(
                f"{i}. {transfer.player_out.name} → {transfer.player_in.name}: {transfer.reason}"
            )
        
        if current_analysis['weak_positions']:
            reasoning_parts.append(f"Addressing weak positions: {', '.join(current_analysis['weak_positions'])}")
        
        return "\n".join(reasoning_parts)
    
    def _generate_wildcard_reasoning(self, improvement: float, threshold: float) -> str:
        """Generate reasoning for wildcard recommendation"""
        if improvement > threshold:
            return (f"Wildcard recommended: Expected improvement of {improvement:.1f} points "
                   f"exceeds threshold of {threshold} points. Statistical analysis shows "
                   f"significant potential gains from team restructuring.")
        else:
            return (f"Wildcard not recommended: Expected improvement of {improvement:.1f} points "
                   f"is below threshold of {threshold} points. Current team structure is "
                   f"statistically sound for upcoming fixtures.")