"""
Transfer optimization functionality for FPL Optimizer
"""

from typing import Dict, List, Optional, Any, Tuple
import pandas as pd
from ..models import Player, Transfer, FPLTeam


class TransferOptimizer:
    """Optimizes transfer decisions"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.max_transfers = config.get("max_transfers", 2)
        self.transfer_cost = config.get("transfer_cost", 4)
    
    def optimize_transfers(self, current_team: FPLTeam, available_players: List[Player],
                         player_xpts: Dict[int, float], free_transfers: int = 1,
                         bank_balance: float = 0.0) -> List[Transfer]:
        """Optimize transfers for the current gameweek"""
        if free_transfers == 0:
            return []
        
        # Calculate current team expected points
        current_xpts = sum(player_xpts.get(p.id, 0) for p in current_team.players)
        
        # Find potential improvements
        potential_transfers = []
        
        for current_player in current_team.players:
            current_player_xpts = player_xpts.get(current_player.id, 0)
            
            for new_player in available_players:
                if new_player.id == current_player.id:
                    continue
                
                # Check if we can afford the transfer
                price_diff = new_player.price - current_player.price
                if price_diff > bank_balance:
                    continue
                
                new_player_xpts = player_xpts.get(new_player.id, 0)
                improvement = new_player_xpts - current_player_xpts
                
                if improvement > 0:
                    potential_transfers.append({
                        "out_player": current_player,
                        "in_player": new_player,
                        "improvement": improvement,
                        "cost": price_diff
                    })
        
        # Sort by improvement per transfer cost
        potential_transfers.sort(key=lambda x: x["improvement"] / max(1, x["cost"]), reverse=True)
        
        # Select best transfers within constraints
        selected_transfers = []
        remaining_transfers = min(free_transfers, self.max_transfers)
        remaining_budget = bank_balance
        
        for transfer in potential_transfers:
            if remaining_transfers <= 0:
                break
            
            if transfer["cost"] <= remaining_budget:
                selected_transfers.append(Transfer(
                    player_out_id=transfer["out_player"].id,
                    player_in_id=transfer["in_player"].id,
                    gameweek=current_team.gameweek + 1,
                    cost=transfer["cost"]
                ))
                remaining_transfers -= 1
                remaining_budget -= transfer["cost"]
        
        return selected_transfers
    
    def calculate_transfer_impact(self, current_team: FPLTeam, transfers: List[Transfer],
                                player_xpts: Dict[int, float]) -> float:
        """Calculate the expected points impact of transfers"""
        if not transfers:
            return 0.0
        
        current_xpts = sum(player_xpts.get(p.id, 0) for p in current_team.players)
        
        # Simulate transfers
        new_team_players = current_team.players.copy()
        for transfer in transfers:
            # Remove out player
            new_team_players = [p for p in new_team_players if p.id != transfer.player_out_id]
            # Add in player (simplified - would need to fetch actual player data)
            # For now, just estimate the improvement
        
        # This is a simplified calculation
        transfer_improvement = sum(t.cost * 0.1 for t in transfers)  # Rough estimate
        
        return transfer_improvement
