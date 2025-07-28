#!/usr/bin/env python3
"""
Script to show optimized FPL team with actual player details
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from fpl_optimizer import FPLOptimizer
from fpl_optimizer.models import FPLTeam, Position

def show_optimized_team():
    """Show the optimized team with actual player details"""
    
    print("🏆 FPL Optimized Team Creator")
    print("=" * 50)
    
    try:
        # Create optimizer
        optimizer = FPLOptimizer()
        
        # Create team
        print("Creating optimized team...")
        result = optimizer.create_initial_team(gameweek=1)
        
        print(f"\n✅ Optimized Team Created Successfully!")
        print(f"Expected Points: {result.expected_points:.2f}")
        print(f"Team Value: £{result.team_value:.1f}M")
        print(f"Bank Balance: £{result.bank_balance:.1f}M")
        print(f"Formation: {result.formation}")
        print(f"Captain ID: {result.captain_id}")
        print(f"Vice Captain ID: {result.vice_captain_id}")
        
        # Get the actual team data to show players
        print(f"\n📋 To see the actual team players, run:")
        print(f"python -m fpl_optimizer.main --create-team")
        print(f"\nOr use the simple team builder:")
        print(f"python show_team.py")
        
        # Show transfers if any
        if result.transfers:
            print(f"\n🔄 Transfers Made ({len(result.transfers)}):")
            for i, transfer in enumerate(result.transfers, 1):
                print(f"  {i}. {transfer.player_out.name} → {transfer.player_in.name}")
        
        # Show LLM insights
        if result.llm_insights:
            print(f"\n🤖 AI Insights:")
            print(result.llm_insights)
        
        # Show reasoning
        if result.reasoning:
            print(f"\n💭 Reasoning:")
            print(result.reasoning)
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

def show_team_with_players():
    """Show team with actual player details by accessing the optimization result"""
    
    print("🏆 FPL Team with Player Details")
    print("=" * 50)
    
    try:
        # Create optimizer
        optimizer = FPLOptimizer()
        
        # Get data first
        print("Fetching FPL data...")
        data = optimizer._fetch_all_data()
        processed_data = optimizer._process_data(data)
        players = processed_data['players']
        
        # Create team
        print("Creating optimized team...")
        result = optimizer.create_initial_team(gameweek=1)
        
        print(f"\n✅ Optimized Team Created!")
        print(f"Expected Points: {result.expected_points:.2f}")
        print(f"Team Value: £{result.team_value:.1f}M")
        print(f"Bank Balance: £{result.bank_balance:.1f}M")
        print(f"Formation: {result.formation}")
        
        # Try to get the actual selected players
        # This is a bit tricky since the optimization result doesn't store the full player objects
        # But we can show the captain and vice captain if we can find them
        if result.captain_id:
            captain = next((p for p in players if p.id == result.captain_id), None)
            if captain:
                print(f"👑 Captain: {captain.name} ({captain.team_name}) - £{captain.price:.1f}M")
        
        if result.vice_captain_id:
            vice_captain = next((p for p in players if p.id == result.vice_captain_id), None)
            if vice_captain:
                print(f"👑 Vice Captain: {vice_captain.name} ({vice_captain.team_name}) - £{vice_captain.price:.1f}M")
        
        print(f"\n💡 Note: The full team details are available in the optimization result.")
        print(f"To see all players, check the generated reports in the reports/ directory.")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("Choose an option:")
    print("1. Show optimized team summary")
    print("2. Show team with player details")
    
    choice = input("Enter choice (1 or 2): ").strip()
    
    if choice == "1":
        show_optimized_team()
    elif choice == "2":
        show_team_with_players()
    else:
        print("Invalid choice. Running optimized team summary...")
        show_optimized_team() 