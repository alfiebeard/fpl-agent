#!/usr/bin/env python3
"""
Debug xPts calculation for a specific player
"""

from fpl_optimizer.main import FPLOptimizer
from fpl_optimizer.projection.xpts import ExpectedPointsCalculator
from fpl_optimizer.models import Position

def debug_player_xpts(player_name="El Hadji Malick Diouf"):
    """Debug xPts calculation for a specific player"""
    
    print(f"🔍 Debugging xPts for: {player_name}")
    print("=" * 50)
    
    # Initialize optimizer
    optimizer = FPLOptimizer()
    
    # Fetch data
    print("Fetching data...")
    data = optimizer._fetch_all_data()
    processed_data = optimizer._process_data(data)
    
    # Find the player
    player = None
    for p in processed_data['players']:
        if player_name.lower() in p.name.lower():
            player = p
            break
    
    if not player:
        print(f"❌ Player {player_name} not found")
        return
    
    print(f"✅ Found player: {player.name}")
    print(f"   Team: {player.team_name}")
    print(f"   Position: {player.position}")
    print(f"   Price: £{player.price}M")
    print(f"   Form: {player.form}")
    print(f"   xG: {player.xG}")
    print(f"   xA: {player.xA}")
    print(f"   xMins_pct: {player.xMins_pct}")
    
    # Get team
    team = None
    for t in processed_data['teams']:
        if t.name == player.team_name:
            team = t
            break
    
    if team:
        print(f"   Team strength: {team.strength}")
        print(f"   Team form: {team.form}")
    
    # Get fixtures for this team
    team_fixtures = []
    for fixture in processed_data['fixtures']:
        if fixture.home_team_name == player.team_name or fixture.away_team_name == player.team_name:
            team_fixtures.append(fixture)
    
    print(f"\n📅 Team fixtures (showing first 5):")
    for i, fixture in enumerate(team_fixtures[:5]):
        if fixture.home_team_name == player.team_name:
            opponent = fixture.away_team_name
            difficulty = fixture.home_difficulty
            is_home = True
        else:
            opponent = fixture.home_team_name
            difficulty = fixture.away_difficulty
            is_home = False
        
        print(f"   {i+1}. {'HOME' if is_home else 'AWAY'} vs {opponent} (Difficulty: {difficulty})")
    
    # Calculate xPts manually
    print(f"\n🧮 Manual xPts calculation:")
    calculator = ExpectedPointsCalculator(optimizer.config)
    
    total_xpts = 0
    for i, fixture in enumerate(team_fixtures[:5]):  # First 5 fixtures
        if fixture.home_team_name == player.team_name:
            home_team = team
            away_team = next((t for t in processed_data['teams'] if t.name == fixture.away_team_name), None)
            is_home = True
        else:
            home_team = next((t for t in processed_data['teams'] if t.name == fixture.home_team_name), None)
            away_team = team
            is_home = False
        
        if home_team and away_team:
            xpts = calculator.calculate_player_xpts(player, fixture, home_team, away_team)
            total_xpts += xpts
            
            print(f"   Fixture {i+1}: {xpts:.2f} xPts")
            
            # Break down the calculation
            xg = calculator._calculate_expected_goals(player, fixture, home_team, away_team)
            xa = calculator._calculate_expected_assists(player, fixture, home_team, away_team)
            xmins = calculator._calculate_expected_minutes(player, fixture)
            
            print(f"      xG: {xg:.3f}, xA: {xa:.3f}, xMins: {xmins:.1f}%")
    
    print(f"\n📊 Total xPts (first 5 fixtures): {total_xpts:.2f}")
    print(f"   Average per fixture: {total_xpts/5:.2f}")
    
    # Compare with the actual calculation
    actual_xpts = 0
    for fixture in team_fixtures:
        if fixture.home_team_name == player.team_name:
            home_team = team
            away_team = next((t for t in processed_data['teams'] if t.name == fixture.away_team_name), None)
        else:
            home_team = next((t for t in processed_data['teams'] if t.name == fixture.home_team_name), None)
            away_team = team
        
        if home_team and away_team:
            xpts = calculator.calculate_player_xpts(player, fixture, home_team, away_team)
            actual_xpts += xpts
    
    print(f"   Actual total xPts (all fixtures): {actual_xpts:.2f}")
    print(f"   Average per fixture: {actual_xpts/len(team_fixtures):.2f}")

if __name__ == "__main__":
    debug_player_xpts() 