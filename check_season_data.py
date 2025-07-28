#!/usr/bin/env python3
"""
Script to check what season this data is for
"""

import requests
import json

def check_season_data():
    """Check what season this data is for"""
    
    print("🔍 Checking Season Data")
    print("=" * 50)
    
    try:
        # Get bootstrap data
        response = requests.get('https://fantasy.premierleague.com/api/bootstrap-static/')
        data = response.json()
        
        # Check all teams
        teams = data.get('teams', [])
        print(f"📋 All Teams ({len(teams)}):")
        for team in teams:
            print(f"  {team['id']}: {team['name']} (Short: {team['short_name']})")
        
        # Check if this looks like current Premier League
        premier_league_teams = [
            'Arsenal', 'Aston Villa', 'Bournemouth', 'Brentford', 'Brighton', 
            'Burnley', 'Chelsea', 'Crystal Palace', 'Everton', 'Fulham',
            'Liverpool', 'Luton', 'Manchester City', 'Manchester United', 
            'Newcastle', 'Nottingham Forest', 'Sheffield United', 'Spurs', 
            'West Ham', 'Wolves'
        ]
        
        current_teams = [t['name'] for t in teams]
        missing_teams = [t for t in premier_league_teams if t not in current_teams]
        extra_teams = [t for t in current_teams if t not in premier_league_teams]
        
        print(f"\n🔍 Team Analysis:")
        print(f"  Expected PL teams: {len(premier_league_teams)}")
        print(f"  Teams in data: {len(current_teams)}")
        print(f"  Missing teams: {missing_teams}")
        print(f"  Extra teams: {extra_teams}")
        
        # Check events (gameweeks)
        events = data.get('events', [])
        print(f"\n📅 Gameweek Information:")
        for event in events[:5]:  # Show first 5
            print(f"  {event['id']}: {event['name']} - Current: {event.get('is_current', False)} - Finished: {event.get('finished', False)}")
        
        # Check if this is 2025-26 season
        print(f"\n🎯 Season Analysis:")
        if 'Sunderland' in current_teams:
            print(f"  ⚠️ Sunderland is in the data - this might be 2024-25 season data")
        else:
            print(f"  ✅ No Sunderland - this might be 2025-26 season data")
        
        # Check fixture dates
        fixtures_response = requests.get('https://fantasy.premierleague.com/api/fixtures/')
        fixtures_data = fixtures_response.json()
        
        if fixtures_data:
            first_fixture = fixtures_data[0]
            last_fixture = fixtures_data[-1]
            print(f"\n📅 Fixture Dates:")
            print(f"  First fixture: {first_fixture.get('kickoff_time', 'Unknown')}")
            print(f"  Last fixture: {last_fixture.get('kickoff_time', 'Unknown')}")
        
        # Check if this is pre-season data
        print(f"\n🔍 Data Status:")
        players = data.get('elements', [])
        players_with_form = [p for p in players if p.get('form') and p.get('form') != '0.0']
        print(f"  Players with form data: {len(players_with_form)}/{len(players)}")
        
        if len(players_with_form) == 0:
            print(f"  ⚠️ This appears to be pre-season data (no form data available)")
            print(f"  💡 xPts calculation should be based on historical data or estimates")
        else:
            print(f"  ✅ This appears to be in-season data")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_season_data() 