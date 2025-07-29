"""
Main FPL Optimizer application - Streamlined
"""

import logging
import sys
from typing import Dict, List, Optional, Any
from datetime import datetime
import argparse

from .config import Config
from .ingestion import get_test_data
from .optimizer import ILPSolver
from .models import Player, Team, Position


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)


class FPLOptimizer:
    """Streamlined FPL Optimizer application"""
    
    def __init__(self, config_path: Optional[str] = None):
        """Initialize the FPL Optimizer"""
        self.config = Config(config_path)
        self.ilp_solver = ILPSolver(self.config)
    
    def fetch_data(self, sample_size: int = 50) -> Dict[str, Any]:
        """Fetch player data without optimization"""
        
        try:
            logger.info("Starting data fetch...")
            
            # Get test data
            logger.info("Fetching player data...")
            test_data = get_test_data(self.config, sample_size)
            players = test_data['players']
            teams = test_data['teams']
            
            logger.info(f"Fetched {len(players)} players and {len(teams)} teams")
            
            # Calculate expected points
            logger.info("Calculating expected points...")
            player_xpts = self._calculate_expected_points(players)
            
            logger.info("Data fetch completed successfully!")
            return {
                'players': players,
                'teams': teams,
                'player_xpts': player_xpts,
                'summary': test_data['summary']
            }
            
        except Exception as e:
            logger.error(f"Data fetch failed: {e}")
            raise
    
    def optimize_team(self, sample_size: int = 50) -> Dict[str, Any]:
        """Optimize a team using sampled data"""
        
        try:
            logger.info("Starting team optimization...")
            
            # Step 1: Get test data
            logger.info("Step 1: Fetching test data...")
            test_data = get_test_data(self.config, sample_size)
            players = test_data['players']
            teams = test_data['teams']
            
            logger.info(f"Fetched {len(players)} players and {len(teams)} teams")
            
            # Step 2: Calculate expected points (simplified)
            logger.info("Step 2: Calculating expected points...")
            player_xpts = self._calculate_expected_points(players)
            
            # Step 3: Optimize team
            logger.info("Step 3: Optimizing team...")
            # Create an empty team for optimization
            from .models import FPLTeam
            empty_team = FPLTeam(team_id=1, team_name="New Team", manager_name="Manager", players=[])
            optimization_result = self.ilp_solver.optimize_team(players, empty_team, player_xpts)
            
            logger.info("Team optimization completed successfully!")
            return {
                'optimization_result': optimization_result,
                'players': players,
                'teams': teams,
                'player_xpts': player_xpts,
                'summary': test_data['summary']
            }
            
        except Exception as e:
            logger.error(f"Team optimization failed: {e}")
            raise
    
    def _calculate_expected_points(self, players: List[Player]) -> Dict[int, float]:
        """Calculate expected points for players (simplified)"""
        xpts = {}
        
        for player in players:
            # Simple expected points calculation based on form and price
            base_xpts = player.form * 0.5  # Form factor
            price_factor = player.price * 0.1  # Price factor
            points_factor = player.total_points * 0.01  # Historical points factor
            
            # Add xG/xA if available
            xg_factor = getattr(player, 'xG', 0) * 4  # xG to points conversion
            xa_factor = getattr(player, 'xA', 0) * 3  # xA to points conversion
            
            total_xpts = base_xpts + price_factor + points_factor + xg_factor + xa_factor
            
            # Position bonuses
            if player.position == Position.GK:
                total_xpts *= 0.8  # Goalkeepers get fewer points
            elif player.position == Position.DEF:
                total_xpts *= 0.9  # Defenders get slightly fewer points
            
            xpts[player.id] = max(0, total_xpts)
        
        return xpts


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='FPL Optimizer')
    parser.add_argument('command', choices=['fetch', 'optimize'], 
                       help='Command to run: fetch (get player data) or optimize (create team)')
    parser.add_argument('--sample-size', type=int, default=50, 
                       help='Number of players to sample (default: 50)')
    parser.add_argument('--config', type=str, help='Path to config file')
    
    args = parser.parse_args()
    
    try:
        optimizer = FPLOptimizer(args.config)
        
        if args.command == 'fetch':
            # Just fetch and display data
            result = optimizer.fetch_data(args.sample_size)
            display_player_data(result)
        elif args.command == 'optimize':
            # Fetch data and optimize team
            result = optimizer.optimize_team(args.sample_size)
            display_optimization_result(result)
        
    except Exception as e:
        logger.error(f"Command failed: {e}")
        sys.exit(1)


def display_player_data(result):
    """Display fetched player data"""
    print("\n" + "="*60)
    print("FPL PLAYER DATA FETCHED")
    print("="*60)
    
    # Print summary
    summary = result['summary']
    print(f"\nData Summary:")
    print(f"  Players: {summary['total_players']}")
    print(f"  Teams: {summary['total_teams']}")
    
    print(f"\nPosition Distribution:")
    for pos, count in summary['position_distribution'].items():
        print(f"  {pos}: {count}")
    
    print(f"\nPrice Range Distribution:")
    for price_range, count in summary['price_range_distribution'].items():
        print(f"  {price_range}: {count}")
    
    # Print detailed player table
    print(f"\n" + "="*120)
    print("DETAILED PLAYER DATA TABLE")
    print("="*120)
    
    # Header
    print(f"{'Name':<25} {'Team':<15} {'Pos':<4} {'Price':<6} {'Form':<6} {'Total Pts':<10} {'xPts':<6} {'xG':<6} {'xA':<6}")
    print("-" * 120)
    
    # Sort players by expected points
    sorted_players = sorted(result['players'], key=lambda p: result['player_xpts'].get(p.id, 0), reverse=True)
    
    for player in sorted_players:
        xpts = result['player_xpts'].get(player.id, 0)
        xg = getattr(player, 'xG', 0)
        xa = getattr(player, 'xA', 0)
        
        print(f"{player.name:<25} {player.team_name:<15} {player.position.value:<4} £{player.price:<5.1f} {player.form:<6.1f} {player.total_points:<10} {xpts:<6.1f} {xg:<6.3f} {xa:<6.3f}")
    
    print(f"\nData fetch completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


def display_optimization_result(result):
    """Display optimization results"""
    print("\n" + "="*60)
    print("FPL OPTIMIZATION COMPLETE")
    print("="*60)
    
    # Print summary
    summary = result['summary']
    print(f"\nData Summary:")
    print(f"  Players: {summary['total_players']}")
    print(f"  Teams: {summary['total_teams']}")
    
    print(f"\nPosition Distribution:")
    for pos, count in summary['position_distribution'].items():
        print(f"  {pos}: {count}")
    
    print(f"\nPrice Range Distribution:")
    for price_range, count in summary['price_range_distribution'].items():
        print(f"  {price_range}: {count}")
    
    # Print detailed player table
    print(f"\n" + "="*120)
    print("DETAILED PLAYER DATA TABLE")
    print("="*120)
    
    # Header
    print(f"{'Name':<25} {'Team':<15} {'Pos':<4} {'Price':<6} {'Form':<6} {'Total Pts':<10} {'xPts':<6} {'xG':<6} {'xA':<6} {'Selected':<10}")
    print("-" * 120)
    
    # Sort players by expected points
    sorted_players = sorted(result['players'], key=lambda p: result['player_xpts'].get(p.id, 0), reverse=True)
    
    for player in sorted_players:
        xpts = result['player_xpts'].get(player.id, 0)
        xg = getattr(player, 'xG', 0)
        xa = getattr(player, 'xA', 0)
        
        # Check if player is in selected team
        is_selected = "✓" if hasattr(result['optimization_result'], 'selected_players') and player in result['optimization_result'].selected_players else ""
        
        print(f"{player.name:<25} {player.team_name:<15} {player.position.value:<4} £{player.price:<5.1f} {player.form:<6.1f} {player.total_points:<10} {xpts:<6.1f} {xg:<6.3f} {xa:<6.3f} {is_selected:<10}")
    
    # Print optimization result
    opt_result = result['optimization_result']
    if hasattr(opt_result, 'selected_players'):
        print(f"\n" + "="*80)
        print("OPTIMIZED TEAM SELECTION")
        print("="*80)
        print(f"{'Name':<25} {'Team':<15} {'Pos':<4} {'Price':<6} {'xPts':<6} {'Captain':<8}")
        print("-" * 80)
        
        for player in opt_result.selected_players:
            xpts = result['player_xpts'].get(player.id, 0)
            is_captain = "✓" if hasattr(opt_result, 'captain_id') and opt_result.captain_id == player.id else ""
            is_vice = "VC" if hasattr(opt_result, 'vice_captain_id') and opt_result.vice_captain_id == player.id else ""
            captain_status = is_captain or is_vice
            
            print(f"{player.name:<25} {player.team_name:<15} {player.position.value:<4} £{player.price:<5.1f} {xpts:<6.1f} {captain_status:<8}")
    
    print(f"\nOptimization completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


if __name__ == "__main__":
    main()
