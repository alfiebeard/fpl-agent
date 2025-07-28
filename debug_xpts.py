#!/usr/bin/env python3
"""
Debug script to check xPts calculation
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from fpl_optimizer import FPLOptimizer
from fpl_optimizer.models import Position

def debug_xpts():
    """Debug the xPts calculation"""
    
    print("🔍 Debugging xPts Calculation")
    print("=" * 50)
    
    try:
        # Create optimizer
        optimizer = FPLOptimizer()
        
        # Get data
        print("Fetching FPL data...")
        data = optimizer._fetch_all_data()
        processed_data = optimizer._process_data(data)
        
        players = processed_data['players']
        fixtures = processed_data['fixtures']
        teams = processed_data['teams']
        
        print(f"Players: {len(players)}")
        print(f"Fixtures: {len(fixtures)}")
        print(f"Teams: {len(teams)}")
        
        # Check a few players
        print(f"\n📊 Sample Players:")
        for i, player in enumerate(players[:5]):
            print(f"  {i+1}. {player.name} ({player.team_name}) - {player.position.value} - £{player.price:.1f}M - Form: {player.form:.1f}")
        
        # Check fixtures for gameweek 1
        gw1_fixtures = [f for f in fixtures if f.gameweek == 1]
        print(f"\n📅 Gameweek 1 Fixtures: {len(gw1_fixtures)}")
        for fixture in gw1_fixtures[:3]:
            print(f"  {fixture.home_team_name} vs {fixture.away_team_name} (Difficulty: {fixture.difficulty})")
        
        # Calculate xPts for a few players
        print(f"\n🎯 Calculating xPts for sample players...")
        from fpl_optimizer.projection.xpts import ExpectedPointsCalculator
        from fpl_optimizer.config import Config
        
        config = Config()
        xpts_calc = ExpectedPointsCalculator(config)
        
        # Calculate xPts for all players
        player_xpts = xpts_calc.calculate_all_players_xpts(players, 1, fixtures, teams)
        
        # Show top 10 players by xPts
        sorted_players = sorted(players, key=lambda p: player_xpts.get(p.id, 0), reverse=True)
        print(f"\n🏆 Top 10 Players by Expected Points:")
        for i, player in enumerate(sorted_players[:10]):
            xpts = player_xpts.get(player.id, 0)
            print(f"  {i+1}. {player.name} ({player.team_name}) - {player.position.value} - £{player.price:.1f}M - xPts: {xpts:.2f}")
        
        # Check if any players have non-zero xPts
        non_zero_count = sum(1 for xpts in player_xpts.values() if xpts > 0)
        print(f"\n📈 Players with non-zero xPts: {non_zero_count}/{len(players)}")
        
        if non_zero_count == 0:
            print("❌ All players have 0 xPts - this is the problem!")
            
            # Debug a specific player
            test_player = players[0]
            print(f"\n🔍 Debugging xPts for {test_player.name}:")
            
            # Find their fixture
            player_fixture = None
            for fixture in fixtures:
                if fixture.gameweek == 1 and (test_player.team_id == fixture.home_team_id or test_player.team_id == fixture.away_team_id):
                    player_fixture = fixture
                    break
            
            if player_fixture:
                print(f"  Found fixture: {player_fixture.home_team_name} vs {player_fixture.away_team_name}")
                
                # Get teams
                home_team = next((t for t in teams if t.name == player_fixture.home_team_name), None)
                away_team = next((t for t in teams if t.name == player_fixture.away_team_name), None)
                
                if home_team and away_team:
                    print(f"  Home team: {home_team.name}")
                    print(f"  Away team: {away_team.name}")
                    
                    # Calculate xPts manually
                    xpts = xpts_calc.calculate_player_xpts(test_player, player_fixture, home_team, away_team)
                    print(f"  Manual xPts calculation: {xpts:.2f}")
                else:
                    print(f"  Could not find teams")
            else:
                print(f"  No fixture found for gameweek 1")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_xpts() 