#!/usr/bin/env python3
"""
Debug what player data we're actually getting from the FPL API
"""

from fpl_optimizer.main import FPLOptimizer

def debug_player_data():
    """Debug what player data we're actually getting from the FPL API"""
    
    print("🔍 Debugging Player Data from FPL API")
    print("=" * 60)
    
    # Initialize optimizer
    optimizer = FPLOptimizer()
    
    # Fetch raw data
    print("Fetching raw FPL data...")
    data = optimizer._fetch_all_data()
    
    # Check what fields are available in the raw data
    if 'players' in data and data['players']:
        sample_player = data['players'][0]
        print(f"\n📋 Sample Player Raw Data Fields:")
        print("-" * 40)
        print(f"Name: {sample_player.name}")
        print(f"Team: {sample_player.team_name}")
        print(f"Position: {sample_player.position}")
        print(f"Price: {sample_player.price}")
        print(f"Form: {sample_player.form}")
        print(f"xG: {sample_player.xG}")
        print(f"xA: {sample_player.xA}")
        print(f"xMins_pct: {sample_player.xMins_pct}")
        print(f"Points per game: {sample_player.points_per_game}")
        print(f"Is injured: {sample_player.is_injured}")
        print(f"Custom data: {sample_player.custom_data}")
    
    # Check specific players we know should have data
    print(f"\n🔍 Checking Specific Players:")
    print("-" * 40)
    
    target_players = [
        "Mohamed Salah",
        "Erling Haaland", 
        "Bukayo Saka",
        "Alexander Isak"
    ]
    
    for target_name in target_players:
        found = False
        for player in data['players']:
            if target_name.lower() in player.name.lower():
                print(f"\n{player.name}:")
                print(f"  xG: {player.xG}")
                print(f"  xA: {player.xA}")
                print(f"  Form: {player.form}")
                print(f"  xMins_pct: {player.xMins_pct}")
                print(f"  Points per game: {player.points_per_game}")
                print(f"  Custom data: {player.custom_data}")
                found = True
                break
        
        if not found:
            print(f"\n{target_name}: Not found in data")
    
    # Check what fields are available for teams
    if 'teams' in data and data['teams']:
        sample_team = data['teams'][0]
        print(f"\n📋 Sample Team Raw Data Fields:")
        print("-" * 40)
        print(f"Name: {sample_team.name}")
        print(f"Short name: {sample_team.short_name}")
        print(f"Strength: {sample_team.strength}")
        print(f"Form: {sample_team.form}")
        print(f"xG: {sample_team.xG}")
        print(f"xGA: {sample_team.xGA}")

if __name__ == "__main__":
    debug_player_data() 