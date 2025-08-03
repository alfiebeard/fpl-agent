"""
Integer Linear Programming solver for FPL team optimization
"""

import pulp
import numpy as np
from typing import Dict, List, Optional, Any, Tuple
import logging

from ..core.models import Player, FPLTeam, Position, OptimizationResult
from ..core.config import Config


logger = logging.getLogger(__name__)


class ILPSolver:
    """Integer Linear Programming solver for FPL team optimization"""
    
    def __init__(self, config: Config):
        self.config = config
        self.team_config = config.get_team_config()
        self.optimization_config = config.get_optimization_config()
        
    def optimize_team(self, players: List[Player], current_team: FPLTeam,
                     player_xpts: Dict[int, float]) -> OptimizationResult:
        """Optimize team selection using ILP"""
        
        logger.info("Starting ILP team optimization...")
        
        try:
            # Create the optimization problem
            prob = pulp.LpProblem("FPL_Team_Optimization", pulp.LpMaximize)
            
            # Decision variables: 1 if player is selected, 0 otherwise
            player_vars = {}
            for player in players:
                player_vars[player.id] = pulp.LpVariable(
                    f"player_{player.id}", 
                    cat=pulp.LpBinary
                )
            
            # Objective function: maximize expected points
            objective = pulp.lpSum([
                player_xpts.get(player.id, 0) * player_vars[player.id]
                for player in players
            ])
            prob += objective
            
            # Constraints
            self._add_budget_constraint(prob, players, player_vars)
            self._add_formation_constraints(prob, players, player_vars)
            self._add_team_constraints(prob, players, player_vars)
            self._add_squad_size_constraint(prob, players, player_vars)
            
            # Solve the problem
            prob.solve(pulp.PULP_CBC_CMD(msg=False))
            
            if prob.status == pulp.LpStatusOptimal:
                return self._extract_solution(prob, players, player_vars, player_xpts)
            else:
                logger.error(f"ILP optimization failed with status: {prob.status}")
                return self._create_fallback_solution(current_team, player_xpts)
                
        except Exception as e:
            logger.error(f"Error in ILP optimization: {e}")
            return self._create_fallback_solution(current_team, player_xpts)
    
    def optimize_with_transfers(self, players: List[Player], current_team: FPLTeam,
                              player_xpts: Dict[int, float], 
                              max_transfers: int = 2) -> OptimizationResult:
        """Optimize team with transfer constraints"""
        
        logger.info(f"Starting ILP optimization with max {max_transfers} transfers...")
        
        try:
            # Create the optimization problem
            prob = pulp.LpProblem("FPL_Team_Optimization_With_Transfers", pulp.LpMaximize)
            
            # Decision variables
            player_vars = {}
            transfer_vars = {}
            
            for player in players:
                player_vars[player.id] = pulp.LpVariable(
                    f"player_{player.id}", 
                    cat=pulp.LpBinary
                )
                
                # Transfer variable: 1 if we transfer this player in/out
                is_current_player = any(p.id == player.id for p in current_team.players)
                if is_current_player:
                    transfer_vars[player.id] = pulp.LpVariable(
                        f"transfer_out_{player.id}",
                        cat=pulp.LpBinary
                    )
                else:
                    transfer_vars[player.id] = pulp.LpVariable(
                        f"transfer_in_{player.id}",
                        cat=pulp.LpBinary
                    )
            
            # Objective function: maximize expected points minus transfer costs
            transfer_cost = 4  # Points cost per transfer
            objective = pulp.lpSum([
                player_xpts.get(player.id, 0) * player_vars[player.id]
                for player in players
            ]) - transfer_cost * pulp.lpSum([
                transfer_vars[player.id]
                for player in players
            ])
            prob += objective
            
            # Constraints
            self._add_budget_constraint(prob, players, player_vars)
            self._add_formation_constraints(prob, players, player_vars)
            self._add_team_constraints(prob, players, player_vars)
            self._add_squad_size_constraint(prob, players, player_vars)
            self._add_transfer_constraints(prob, players, player_vars, transfer_vars, 
                                         current_team, max_transfers)
            
            # Solve the problem
            prob.solve(pulp.PULP_CBC_CMD(msg=False))
            
            if prob.status == pulp.LpStatusOptimal:
                return self._extract_solution_with_transfers(
                    prob, players, player_vars, transfer_vars, player_xpts, current_team
                )
            else:
                logger.error(f"ILP optimization with transfers failed with status: {prob.status}")
                return self._create_fallback_solution(current_team, player_xpts)
                
        except Exception as e:
            logger.error(f"Error in ILP optimization with transfers: {e}")
            return self._create_fallback_solution(current_team, player_xpts)
    
    def _add_budget_constraint(self, prob: pulp.LpProblem, players: List[Player], 
                             player_vars: Dict[int, pulp.LpVariable]):
        """Add budget constraint"""
        budget = self.team_config.get('budget', 100.0)
        prob += pulp.lpSum([
            player.price * player_vars[player.id]
            for player in players
        ]) <= budget, "Budget_Constraint"
    
    def _add_formation_constraints(self, prob: pulp.LpProblem, players: List[Player],
                                 player_vars: Dict[int, pulp.LpVariable]):
        """Add formation constraints"""
        
        # Count players by position
        gk_players = [p for p in players if p.position == Position.GK]
        def_players = [p for p in players if p.position == Position.DEF]
        mid_players = [p for p in players if p.position == Position.MID]
        fwd_players = [p for p in players if p.position == Position.FWD]
        
        # FPL Formation Rules:
        # 1. Must have exactly 2 goalkeepers
        prob += pulp.lpSum([
            player_vars[p.id] for p in gk_players
        ]) == 2, "Exact_Goalkeepers"
        
        # 2. Must have exactly 5 defenders
        prob += pulp.lpSum([
            player_vars[p.id] for p in def_players
        ]) == 5, "Exact_Defenders"
        
        # 3. Must have exactly 5 midfielders
        prob += pulp.lpSum([
            player_vars[p.id] for p in mid_players
        ]) == 5, "Exact_Midfielders"
        
        # 4. Must have exactly 3 forwards
        prob += pulp.lpSum([
            player_vars[p.id] for p in fwd_players
        ]) == 3, "Exact_Forwards"
        
        # 5. Total squad size must be exactly 15
        prob += pulp.lpSum([
            player_vars[p.id] for p in players
        ]) == 15, "Exact_Squad_Size"
    
    def _add_team_constraints(self, prob: pulp.LpProblem, players: List[Player],
                            player_vars: Dict[int, pulp.LpVariable]):
        """Add maximum players per team constraint"""
        max_players_per_team = self.team_config.get('max_players_per_team', 3)
        
        # Group players by team
        team_players = {}
        for player in players:
            if player.team_id not in team_players:
                team_players[player.team_id] = []
            team_players[player.team_id].append(player)
        
        # Add constraint for each team
        for team_id, team_player_list in team_players.items():
            prob += pulp.lpSum([
                player_vars[p.id] for p in team_player_list
            ]) <= max_players_per_team, f"Team_Limit_{team_id}"
    
    def _add_squad_size_constraint(self, prob: pulp.LpProblem, players: List[Player],
                                 player_vars: Dict[int, pulp.LpVariable]):
        """Add squad size constraint (15 players) - now handled in formation constraints"""
        # This is now handled in _add_formation_constraints
        pass
    
    def _add_transfer_constraints(self, prob: pulp.LpProblem, players: List[Player],
                                player_vars: Dict[int, pulp.LpVariable],
                                transfer_vars: Dict[int, pulp.LpVariable],
                                current_team: FPLTeam, max_transfers: int):
        """Add transfer constraints"""
        
        # Limit total transfers
        prob += pulp.lpSum([
            transfer_vars[player.id] for player in players
        ]) <= max_transfers, "Max_Transfers"
        
        # Link transfer variables to player selection
        current_player_ids = {p.id for p in current_team.players}
        
        for player in players:
            if player.id in current_player_ids:
                # Current player: transfer_out = 1 if not selected
                prob += transfer_vars[player.id] == (1 - player_vars[player.id]), f"Transfer_Out_{player.id}"
            else:
                # New player: transfer_in = 1 if selected
                prob += transfer_vars[player.id] == player_vars[player.id], f"Transfer_In_{player.id}"
    
    def _extract_solution(self, prob: pulp.LpProblem, players: List[Player],
                         player_vars: Dict[int, pulp.LpVariable],
                         player_xpts: Dict[int, float]) -> OptimizationResult:
        """Extract solution from solved ILP problem"""
        
        # Get selected players
        selected_players = []
        for player in players:
            if player_vars[player.id].value() == 1:
                selected_players.append(player)
        
        # Calculate expected points
        expected_points = sum(player_xpts.get(p.id, 0) for p in selected_players)
        
        # Determine formation
        def_count = len([p for p in selected_players if p.position == Position.DEF])
        mid_count = len([p for p in selected_players if p.position == Position.MID])
        fwd_count = len([p for p in selected_players if p.position == Position.FWD])
        formation = [def_count, mid_count, fwd_count]
        
        # Select captain and vice captain
        captain_id, vice_captain_id = self._select_captains(selected_players, player_xpts)
        
        # Calculate team value and bank balance
        team_value = sum(p.price for p in selected_players)
        bank_balance = 100.0 - team_value
        
        return OptimizationResult(
            selected_players=selected_players,
            transfers=[],  # No transfers in basic optimization
            captain_id=captain_id,
            vice_captain_id=vice_captain_id,
            formation=formation,
            expected_points=expected_points,
            team_value=team_value,
            bank_balance=bank_balance,
            confidence=0.8,
            reasoning="ILP optimization completed successfully"
        )
    
    def _extract_solution_with_transfers(self, prob: pulp.LpProblem, players: List[Player],
                                       player_vars: Dict[int, pulp.LpVariable],
                                       transfer_vars: Dict[int, pulp.LpVariable],
                                       player_xpts: Dict[int, float],
                                       current_team: FPLTeam) -> OptimizationResult:
        """Extract solution with transfers from solved ILP problem"""
        
        from ..core.models import Transfer
        
        # Get selected players
        selected_players = []
        for player in players:
            if player_vars[player.id].value() == 1:
                selected_players.append(player)
        
        # Calculate transfers
        transfers = []
        current_player_ids = {p.id for p in current_team.players}
        
        for player in players:
            if transfer_vars[player.id].value() == 1:
                if player.id in current_player_ids:
                    # Player transferred out
                    player_out = next(p for p in current_team.players if p.id == player.id)
                    transfers.append(Transfer(
                        player_out=player_out,
                        player_in=player,
                        gameweek=1,  # Would need actual gameweek
                        cost=4,
                        reason="Optimization transfer"
                    ))
                else:
                    # Player transferred in
                    # Find which current player was transferred out
                    # This is simplified - would need more complex logic
                    pass
        
        # Calculate expected points
        expected_points = sum(player_xpts.get(p.id, 0) for p in selected_players)
        
        # Determine formation
        def_count = len([p for p in selected_players if p.position == Position.DEF])
        mid_count = len([p for p in selected_players if p.position == Position.MID])
        fwd_count = len([p for p in selected_players if p.position == Position.FWD])
        formation = [def_count, mid_count, fwd_count]
        
        # Select captain and vice captain
        captain_id, vice_captain_id = self._select_captains(selected_players, player_xpts)
        
        # Calculate team value and bank balance
        team_value = sum(p.price for p in selected_players)
        bank_balance = 100.0 - team_value
        
        return OptimizationResult(
            selected_players=selected_players,
            transfers=transfers,
            captain_id=captain_id,
            vice_captain_id=vice_captain_id,
            formation=formation,
            expected_points=expected_points,
            team_value=team_value,
            bank_balance=bank_balance,
            confidence=0.8,
            reasoning="ILP optimization with transfers completed successfully"
        )
    
    def _select_captains(self, players: List[Player], 
                        player_xpts: Dict[int, float]) -> Tuple[Optional[int], Optional[int]]:
        """Select captain and vice captain based on expected points"""
        
        # Sort players by expected points
        sorted_players = sorted(players, key=lambda p: player_xpts.get(p.id, 0), reverse=True)
        
        if len(sorted_players) >= 2:
            return sorted_players[0].id, sorted_players[1].id
        elif len(sorted_players) == 1:
            return sorted_players[0].id, None
        else:
            return None, None
    
    def _create_fallback_solution(self, current_team: FPLTeam,
                                player_xpts: Dict[int, float]) -> OptimizationResult:
        """Create a fallback solution when optimization fails"""
        
        logger.warning("Creating fallback solution due to optimization failure")
        
        # If current team is empty, create a simple team
        if not current_team.players:
            # Get all players from the optimization context
            # This is a simplified approach - in practice we'd need to pass players here
            return OptimizationResult(
                transfers=[],
                captain_id=None,
                vice_captain_id=None,
                formation=[3, 4, 3],
                expected_points=0.0,
                team_value=100.0,
                bank_balance=0.0,
                confidence=0.1,
                reasoning="Fallback solution - no players available"
            )
        
        # Use current team
        selected_players = current_team.players
        
        # Calculate expected points
        expected_points = sum(player_xpts.get(p.id, 0) for p in selected_players)
        
        # Use current formation
        formation = current_team.formation
        
        # Use current captain and vice captain
        captain_id = current_team.captain_id
        vice_captain_id = current_team.vice_captain_id
        
        # Calculate team value
        team_value = sum(p.price for p in selected_players)
        bank_balance = 100.0 - team_value
        
        return OptimizationResult(
            transfers=[],
            captain_id=captain_id,
            vice_captain_id=vice_captain_id,
            formation=formation,
            expected_points=expected_points,
            team_value=team_value,
            bank_balance=bank_balance,
            confidence=0.3,
            reasoning="Fallback solution due to optimization failure"
        )
