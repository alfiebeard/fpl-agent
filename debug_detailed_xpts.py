#!/usr/bin/env python3
"""
Detailed debug of xPts calculation
"""

from fpl_optimizer.main import FPLOptimizer
from fpl_optimizer.projection.xpts import ExpectedPointsCalculator
from fpl_optimizer.models import Position

def debug_detailed_xpts(player_name="El Hadji Malick Diouf"):
    """Debug detailed xPts calculation for a specific player"""
    
    print(f"🔍 Detailed xPts Debug for: {player_name}")
    print("=" * 60)
    
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
    
    # Get first fixture for detailed breakdown
    team_fixtures = []
    for fixture in processed_data['fixtures']:
        if fixture.home_team_name == player.team_name or fixture.away_team_name == player.team_name:
            team_fixtures.append(fixture)
    
    if not team_fixtures:
        print("❌ No fixtures found for this team")
        return
    
    fixture = team_fixtures[0]  # First fixture
    print(f"\n📅 Analyzing first fixture: {fixture.home_team_name} vs {fixture.away_team_name}")
    print(f"   Gameweek: {fixture.gameweek}")
    print(f"   Home difficulty: {fixture.home_difficulty}")
    print(f"   Away difficulty: {fixture.away_difficulty}")
    
    # Get teams for this fixture
    if fixture.home_team_name == player.team_name:
        home_team = team
        away_team = next((t for t in processed_data['teams'] if t.name == fixture.away_team_name), None)
        is_home = True
    else:
        home_team = next((t for t in processed_data['teams'] if t.name == fixture.home_team_name), None)
        away_team = team
        is_home = False
    
    if not home_team or not away_team:
        print("❌ Could not find teams for fixture")
        return
    
    print(f"   Playing: {'HOME' if is_home else 'AWAY'}")
    print(f"   Home team: {home_team.name} (strength: {home_team.strength})")
    print(f"   Away team: {away_team.name} (strength: {away_team.strength})")
    
    # Calculate xPts with detailed breakdown
    calculator = ExpectedPointsCalculator(optimizer.config)
    
    print(f"\n🧮 Detailed xPts Breakdown:")
    print("-" * 40)
    
    # Get position-specific point values
    goal_pts = calculator.points_config['goal'].get(player.position.value.lower(), 4)
    assist_pts = calculator.points_config['assist']
    cs_pts = calculator.points_config['clean_sheet'].get(player.position.value.lower(), 0)
    bonus_pts = calculator.points_config['bonus']
    yc_pts = calculator.points_config['yellow_card']
    rc_pts = calculator.points_config['red_card']
    
    print(f"Point values for {player.position.value}:")
    print(f"   Goal: {goal_pts} pts")
    print(f"   Assist: {assist_pts} pts")
    print(f"   Clean sheet: {cs_pts} pts")
    print(f"   Bonus: {bonus_pts} pts")
    print(f"   Yellow card: {yc_pts} pts")
    print(f"   Red card: {rc_pts} pts")
    
    # Calculate each component
    xG_pred = calculator._calculate_expected_goals(player, fixture, home_team, away_team)
    xA_pred = calculator._calculate_expected_assists(player, fixture, home_team, away_team)
    xCS_prob = calculator._calculate_clean_sheet_probability(player, fixture, home_team, away_team)
    bonus_prob = calculator._calculate_bonus_probability(player, xG_pred, xA_pred)
    yc_prob = calculator._calculate_yellow_card_probability(player)
    rc_prob = calculator._calculate_red_card_probability(player)
    xMins_pct = calculator._calculate_expected_minutes(player, fixture)
    
    print(f"\nExpected values:")
    print(f"   xG: {xG_pred:.4f}")
    print(f"   xA: {xA_pred:.4f}")
    print(f"   Clean sheet probability: {xCS_prob:.4f}")
    print(f"   Bonus probability: {bonus_prob:.4f}")
    print(f"   Yellow card probability: {yc_prob:.4f}")
    print(f"   Red card probability: {rc_prob:.4f}")
    print(f"   Minutes percentage: {xMins_pct:.4f}")
    
    # Calculate points from each source
    goal_points = xG_pred * goal_pts
    assist_points = xA_pred * assist_pts
    cs_points = xCS_prob * cs_pts
    bonus_points = bonus_prob * bonus_pts
    yc_points = yc_prob * yc_pts
    rc_points = rc_prob * rc_pts
    
    print(f"\nPoints from each source:")
    print(f"   Goals: {goal_points:.4f} pts")
    print(f"   Assists: {assist_points:.4f} pts")
    print(f"   Clean sheets: {cs_points:.4f} pts")
    print(f"   Bonus: {bonus_points:.4f} pts")
    print(f"   Yellow cards: {yc_points:.4f} pts")
    print(f"   Red cards: {rc_points:.4f} pts")
    
    # Calculate total attacking points
    attacking_points = goal_points + assist_points + cs_points + bonus_points + yc_points + rc_points
    print(f"   Total attacking points: {attacking_points:.4f} pts")
    
    # Apply minutes factor
    minutes_adjusted_points = attacking_points * xMins_pct
    print(f"   Minutes adjusted points: {minutes_adjusted_points:.4f} pts")
    
    # Add base points
    base_points = 2.0 * xMins_pct
    print(f"   Base points for playing: {base_points:.4f} pts")
    
    # Final total
    total_xpts = minutes_adjusted_points + base_points
    print(f"   TOTAL xPts: {total_xpts:.4f} pts")
    
    # Compare with actual calculation
    actual_xpts = calculator.calculate_player_xpts(player, fixture, home_team, away_team)
    print(f"\n✅ Verification: Actual calculation = {actual_xpts:.4f} pts")
    
    if abs(total_xpts - actual_xpts) < 0.01:
        print("✅ Calculations match!")
    else:
        print(f"❌ Calculations don't match! Difference: {abs(total_xpts - actual_xpts):.4f}")

if __name__ == "__main__":
    debug_detailed_xpts() 