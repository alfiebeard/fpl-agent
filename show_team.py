#!/usr/bin/env python3
"""
Simple script to show FPL team results
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from fpl_optimizer import FPLOptimizer
from fpl_optimizer.models import FPLTeam, Position

def show_team_details():
    """Show team creation results in detail"""
    
    print("🏆 FPL Team Creator")
    print("=" * 50)
    
    try:
        # Create optimizer
        optimizer = FPLOptimizer()
        
        # Create team
        print("Creating optimal team...")
        result = optimizer.create_initial_team(gameweek=1)
        
        print(f"\n✅ Team Created Successfully!")
        print(f"Expected Points: {result.expected_points:.2f}")
        print(f"Team Value: £{result.team_value:.1f}M")
        print(f"Bank Balance: £{result.bank_balance:.1f}M")
        print(f"Formation: {result.formation}")
        print(f"Captain ID: {result.captain_id}")
        print(f"Vice Captain ID: {result.vice_captain_id}")
        
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

def show_optimized_team():
    """Show the optimized team with actual selected players"""
    
    print("🏆 FPL Optimized Team")
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
        
        # Show selected players
        if result.selected_players:
            print(f"\n📋 Selected Players ({len(result.selected_players)}):")
            
            # Group by position
            gk_players = [p for p in result.selected_players if p.position == Position.GK]
            def_players = [p for p in result.selected_players if p.position == Position.DEF]
            mid_players = [p for p in result.selected_players if p.position == Position.MID]
            fwd_players = [p for p in result.selected_players if p.position == Position.FWD]
            
            print(f"\nGoalkeepers ({len(gk_players)}):")
            for player in gk_players:
                captain_star = " 👑" if player.id == result.captain_id else " 👑" if player.id == result.vice_captain_id else ""
                print(f"  - {player.name} ({player.team_name}) - £{player.price:.1f}M - Form: {player.form:.1f}{captain_star}")
            
            print(f"\nDefenders ({len(def_players)}):")
            for player in def_players:
                captain_star = " 👑" if player.id == result.captain_id else " 👑" if player.id == result.vice_captain_id else ""
                print(f"  - {player.name} ({player.team_name}) - £{player.price:.1f}M - Form: {player.form:.1f}{captain_star}")
            
            print(f"\nMidfielders ({len(mid_players)}):")
            for player in mid_players:
                captain_star = " 👑" if player.id == result.captain_id else " 👑" if player.id == result.vice_captain_id else ""
                print(f"  - {player.name} ({player.team_name}) - £{player.price:.1f}M - Form: {player.form:.1f}{captain_star}")
            
            print(f"\nForwards ({len(fwd_players)}):")
            for player in fwd_players:
                captain_star = " 👑" if player.id == result.captain_id else " 👑" if player.id == result.vice_captain_id else ""
                print(f"  - {player.name} ({player.team_name}) - £{player.price:.1f}M - Form: {player.form:.1f}{captain_star}")
        else:
            print(f"\n⚠️ No selected players found in result")
        
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

def show_simple_team():
    """Show a simple team creation without complex optimization"""
    
    print("🏆 Simple FPL Team Creator")
    print("=" * 50)
    
    try:
        # Create optimizer
        optimizer = FPLOptimizer()
        
        # Get data
        print("Fetching FPL data...")
        data = optimizer._fetch_all_data()
        processed_data = optimizer._process_data(data)
        
        # Get some top players by position
        players = processed_data['players']
        
        # Filter by position and sort by form
        gk_players = [p for p in players if p.position.value == "GK"]
        def_players = [p for p in players if p.position.value == "DEF"]
        mid_players = [p for p in players if p.position.value == "MID"]
        fwd_players = [p for p in players if p.position.value == "FWD"]
        
        # Sort by form (descending)
        gk_players.sort(key=lambda p: p.form, reverse=True)
        def_players.sort(key=lambda p: p.form, reverse=True)
        mid_players.sort(key=lambda p: p.form, reverse=True)
        fwd_players.sort(key=lambda p: p.form, reverse=True)
        
        print(f"\n📊 Top Players by Position:")
        print(f"Goalkeepers (top 5):")
        for i, player in enumerate(gk_players[:5], 1):
            print(f"  {i}. {player.name} ({player.team_name}) - £{player.price:.1f}M - Form: {player.form:.1f}")
        
        print(f"\nDefenders (top 5):")
        for i, player in enumerate(def_players[:5], 1):
            print(f"  {i}. {player.name} ({player.team_name}) - £{player.price:.1f}M - Form: {player.form:.1f}")
        
        print(f"\nMidfielders (top 5):")
        for i, player in enumerate(mid_players[:5], 1):
            print(f"  {i}. {player.name} ({player.team_name}) - £{player.price:.1f}M - Form: {player.form:.1f}")
        
        print(f"\nForwards (top 5):")
        for i, player in enumerate(fwd_players[:5], 1):
            print(f"  {i}. {player.name} ({player.team_name}) - £{player.price:.1f}M - Form: {player.form:.1f}")
        
        # Create a simple team within budget
        print(f"\n🏗️ Building Simple Team (Budget: £100M)...")
        team_players = []
        total_value = 0.0
        budget = 100.0
        
        # Add 2 goalkeepers (cheapest first)
        gk_players.sort(key=lambda p: p.price)  # Sort by price ascending
        for gk in gk_players[:2]:
            if total_value + gk.price <= budget:
                team_players.append(gk)
                total_value += gk.price
        
        # Add defenders (cheapest first)
        def_players.sort(key=lambda p: p.price)
        def_count = 0
        for defender in def_players:
            if def_count >= 5:
                break
            if total_value + defender.price <= budget:
                team_players.append(defender)
                total_value += defender.price
                def_count += 1
        
        # Add midfielders (cheapest first)
        mid_players.sort(key=lambda p: p.price)
        mid_count = 0
        for midfielder in mid_players:
            if mid_count >= 5:
                break
            if total_value + midfielder.price <= budget:
                team_players.append(midfielder)
                total_value += midfielder.price
                mid_count += 1
        
        # Add forwards (cheapest first)
        fwd_players.sort(key=lambda p: p.price)
        fwd_count = 0
        for forward in fwd_players:
            if fwd_count >= 3:
                break
            if total_value + forward.price <= budget:
                team_players.append(forward)
                total_value += forward.price
                fwd_count += 1
        
        print(f"\n✅ Simple Team Created!")
        print(f"Total Players: {len(team_players)}")
        print(f"Total Value: £{total_value:.1f}M")
        print(f"Bank Balance: £{100.0 - total_value:.1f}M")
        
        print(f"\n📋 Team Squad:")
        print(f"Goalkeepers:")
        for player in team_players[:2]:
            print(f"  - {player.name} ({player.team_name}) - £{player.price:.1f}M")
        
        print(f"\nDefenders:")
        for player in team_players[2:7]:
            print(f"  - {player.name} ({player.team_name}) - £{player.price:.1f}M")
        
        print(f"\nMidfielders:")
        for player in team_players[7:12]:
            print(f"  - {player.name} ({player.team_name}) - £{player.price:.1f}M")
        
        print(f"\nForwards:")
        for player in team_players[12:15]:
            print(f"  - {player.name} ({player.team_name}) - £{player.price:.1f}M")
        
        # Suggest captain and vice captain
        captain = max(team_players, key=lambda p: p.form)
        vice_captain = max([p for p in team_players if p != captain], key=lambda p: p.form)
        
        print(f"\n👑 Captain: {captain.name} (Form: {captain.form:.1f})")
        print(f"👑 Vice Captain: {vice_captain.name} (Form: {vice_captain.form:.1f})")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("Choose an option:")
    print("1. Show detailed team creation results")
    print("2. Show simple team with top players")
    print("3. Show optimized team with selected players")
    
    choice = input("Enter choice (1, 2, or 3): ").strip()
    
    if choice == "1":
        show_team_details()
    elif choice == "2":
        show_simple_team()
    elif choice == "3":
        show_optimized_team()
    else:
        print("Invalid choice. Running optimized team...")
        show_optimized_team() 