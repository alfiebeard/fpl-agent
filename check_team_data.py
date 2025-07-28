#!/usr/bin/env python3
"""
Check team data to understand xPts calculation issues
"""

from fpl_optimizer.main import FPLOptimizer

def check_team_data():
    """Check team data to understand xPts calculation issues"""
    
    print("🔍 Checking Team Data")
    print("=" * 50)
    
    # Initialize optimizer
    optimizer = FPLOptimizer()
    
    # Fetch data
    print("Fetching data...")
    data = optimizer._fetch_all_data()
    processed_data = optimizer._process_data(data)
    
    # Check teams
    print(f"\n📋 Team Data:")
    print("-" * 80)
    print(f"{'Team':<20} {'Strength':<10} {'Form':<8} {'xG':<8} {'xGA':<8}")
    print("-" * 80)
    
    for team in processed_data['teams']:
        print(f"{team.name:<20} {team.strength:<10} {team.form:<8.2f} {team.xG:<8.2f} {team.xGA:<8.2f}")
    
    # Check specific teams for the fixture
    print(f"\n🔍 Specific Teams for West Ham vs Sunderland:")
    west_ham = None
    sunderland = None
    
    for team in processed_data['teams']:
        if team.name == "West Ham":
            west_ham = team
        elif team.name == "Sunderland":
            sunderland = team
    
    if west_ham:
        print(f"West Ham:")
        print(f"   Strength: {west_ham.strength}")
        print(f"   Form: {west_ham.form}")
        print(f"   xG: {west_ham.xG}")
        print(f"   xGA: {west_ham.xGA}")
    
    if sunderland:
        print(f"Sunderland:")
        print(f"   Strength: {sunderland.strength}")
        print(f"   Form: {sunderland.form}")
        print(f"   xG: {sunderland.xG}")
        print(f"   xGA: {sunderland.xGA}")
    
    # Calculate clean sheet probability manually
    if west_ham and sunderland:
        print(f"\n🧮 Manual Clean Sheet Calculation:")
        print(f"West Ham (away) vs Sunderland (home)")
        
        # West Ham defense vs Sunderland attack
        team_defense = west_ham.xGA
        opponent_attack = sunderland.xG
        
        print(f"   West Ham xGA (defense): {team_defense}")
        print(f"   Sunderland xG (attack): {opponent_attack}")
        
        # Base clean sheet probability
        base_cs_prob = max(0.0, 0.4 - (team_defense * 0.1) - (opponent_attack * 0.1))
        print(f"   Base CS probability: 0.4 - ({team_defense} * 0.1) - ({opponent_attack} * 0.1) = {base_cs_prob:.4f}")
        
        # Difficulty factor (away fixture, difficulty 2)
        difficulty_factor = (6 - 2) / 5.0  # Away difficulty = 2
        print(f"   Difficulty factor: (6 - 2) / 5 = {difficulty_factor:.4f}")
        
        # Final probability
        cs_prob = base_cs_prob * difficulty_factor
        print(f"   Final CS probability: {base_cs_prob:.4f} * {difficulty_factor:.4f} = {cs_prob:.4f}")
        
        # Points from clean sheet
        cs_points = cs_prob * 4  # 4 points for defender clean sheet
        print(f"   CS points: {cs_prob:.4f} * 4 = {cs_points:.4f} pts")

if __name__ == "__main__":
    check_team_data() 