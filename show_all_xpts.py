#!/usr/bin/env python3
"""
Script to show all players sorted by expected points
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from fpl_optimizer import FPLOptimizer
from fpl_optimizer.models import Position

def show_all_xpts():
    """Show all players sorted by expected points"""
    
    print("📊 All Players by Expected Points")
    print("=" * 60)
    
    try:
        # Create optimizer
        optimizer = FPLOptimizer()
        
        # Get data
        print("Fetching FPL data and calculating expected points...")
        data = optimizer._fetch_all_data()
        processed_data = optimizer._process_data(data)
        
        players = processed_data['players']
        fixtures = processed_data['fixtures']
        teams = processed_data['teams']
        
        # Calculate xPts
        from fpl_optimizer.projection.xpts import ExpectedPointsCalculator
        from fpl_optimizer.config import Config
        
        config = Config()
        xpts_calc = ExpectedPointsCalculator(config)
        player_xpts = xpts_calc.calculate_all_players_xpts(players, 1, fixtures, teams)
        
        # Sort players by xPts
        sorted_players = sorted(players, key=lambda p: player_xpts.get(p.id, 0), reverse=True)
        
        print(f"\n🏆 Top 50 Players by Expected Points:")
        print("-" * 60)
        print(f"{'Rank':<4} {'Name':<25} {'Team':<15} {'Pos':<3} {'Price':<6} {'xPts':<6}")
        print("-" * 60)
        
        for i, player in enumerate(sorted_players[:50], 1):
            xpts = player_xpts.get(player.id, 0)
            print(f"{i:<4} {player.name:<25} {player.team_name:<15} {player.position.value:<3} £{player.price:<5.1f} {xpts:<6.2f}")
        
        # Show breakdown by position
        print(f"\n📈 Position Breakdown (Top 10 each):")
        
        for position in [Position.GK, Position.DEF, Position.MID, Position.FWD]:
            pos_players = [p for p in sorted_players if p.position == position]
            print(f"\n{position.value} Players (Top 10):")
            print("-" * 50)
            print(f"{'Rank':<4} {'Name':<25} {'Team':<15} {'Price':<6} {'xPts':<6}")
            print("-" * 50)
            
            for i, player in enumerate(pos_players[:10], 1):
                xpts = player_xpts.get(player.id, 0)
                print(f"{i:<4} {player.name:<25} {player.team_name:<15} £{player.price:<5.1f} {xpts:<6.2f}")
        
        # Show some statistics
        print(f"\n📊 Statistics:")
        print(f"Total Players: {len(players)}")
        print(f"Players with xPts > 0: {sum(1 for xpts in player_xpts.values() if xpts > 0)}")
        print(f"Average xPts: {sum(player_xpts.values()) / len(player_xpts):.2f}")
        print(f"Max xPts: {max(player_xpts.values()):.2f}")
        print(f"Min xPts: {min(player_xpts.values()):.2f}")
        
        # Show budget analysis
        print(f"\n💰 Budget Analysis:")
        budget_ranges = [
            (0, 4.5, "Budget (£0-4.5M)"),
            (4.6, 6.0, "Mid-range (£4.6-6.0M)"),
            (6.1, 8.0, "Premium (£6.1-8.0M)"),
            (8.1, 15.0, "Ultra Premium (£8.1M+)")
        ]
        
        for min_price, max_price, label in budget_ranges:
            budget_players = [p for p in sorted_players if min_price <= p.price <= max_price]
            if budget_players:
                top_player = budget_players[0]
                top_xpts = player_xpts.get(top_player.id, 0)
                print(f"{label}: {top_player.name} ({top_player.team_name}) - £{top_player.price:.1f}M - {top_xpts:.2f} xPts")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

def show_xpts_by_position(position_name):
    """Show players by specific position"""
    
    try:
        position_map = {
            'gk': Position.GK,
            'def': Position.DEF,
            'mid': Position.MID,
            'fwd': Position.FWD
        }
        
        position = position_map.get(position_name.lower())
        if not position:
            print(f"Invalid position: {position_name}. Use: gk, def, mid, fwd")
            return
        
        # Create optimizer
        optimizer = FPLOptimizer()
        
        # Get data
        print(f"Fetching {position.value} players...")
        data = optimizer._fetch_all_data()
        processed_data = optimizer._process_data(data)
        
        players = processed_data['players']
        fixtures = processed_data['fixtures']
        teams = processed_data['teams']
        
        # Filter by position
        pos_players = [p for p in players if p.position == position]
        
        # Calculate xPts
        from fpl_optimizer.projection.xpts import ExpectedPointsCalculator
        from fpl_optimizer.config import Config
        
        config = Config()
        xpts_calc = ExpectedPointsCalculator(config)
        player_xpts = xpts_calc.calculate_all_players_xpts(pos_players, 1, fixtures, teams)
        
        # Sort by xPts
        sorted_players = sorted(pos_players, key=lambda p: player_xpts.get(p.id, 0), reverse=True)
        
        print(f"\n🏆 Top {position.value} Players by Expected Points:")
        print("-" * 60)
        print(f"{'Rank':<4} {'Name':<25} {'Team':<15} {'Price':<6} {'xPts':<6}")
        print("-" * 60)
        
        for i, player in enumerate(sorted_players[:20], 1):
            xpts = player_xpts.get(player.id, 0)
            print(f"{i:<4} {player.name:<25} {player.team_name:<15} £{player.price:<5.1f} {xpts:<6.2f}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        position = sys.argv[1]
        show_xpts_by_position(position)
    else:
        show_all_xpts() 