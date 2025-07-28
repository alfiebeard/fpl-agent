#!/usr/bin/env python3
"""
Script to check what data we're actually getting from the FPL API
"""

import requests
import json

def check_fpl_data():
    """Check the actual FPL API data"""
    
    print("🔍 Checking FPL API Data")
    print("=" * 50)
    
    try:
        # Get bootstrap data
        print("Fetching bootstrap data...")
        response = requests.get('https://fantasy.premierleague.com/api/bootstrap-static/')
        data = response.json()
        
        print(f"✅ Successfully fetched data")
        print(f"Total elements (players): {len(data.get('elements', []))}")
        print(f"Total teams: {len(data.get('teams', []))}")
        print(f"Total events (gameweeks): {len(data.get('events', []))}")
        
        # Check teams
        print(f"\n📋 Teams in the data:")
        teams = data.get('teams', [])
        for team in teams[:10]:  # Show first 10
            print(f"  {team['id']}: {team['name']} (Short: {team['short_name']})")
        
        # Check if Sunderland is in the data
        sunderland_teams = [t for t in teams if 'sunderland' in t['name'].lower()]
        if sunderland_teams:
            print(f"\n⚠️ Found Sunderland teams: {[t['name'] for t in sunderland_teams]}")
        else:
            print(f"\n✅ No Sunderland teams found")
        
        # Check players
        print(f"\n👥 Sample Players:")
        players = data.get('elements', [])
        for i, player in enumerate(players[:5]):
            team_name = next((t['name'] for t in teams if t['id'] == player['team']), 'Unknown')
            print(f"  {i+1}. {player['first_name']} {player['second_name']} ({team_name}) - £{player['now_cost']/10:.1f}M - Form: {player.get('form', 'N/A')}")
        
        # Check if there are any Sunderland players
        sunderland_players = []
        for player in players:
            team_name = next((t['name'] for t in teams if t['id'] == player['team']), 'Unknown')
            if 'sunderland' in team_name.lower():
                sunderland_players.append(player)
        
        if sunderland_players:
            print(f"\n⚠️ Found {len(sunderland_players)} Sunderland players:")
            for player in sunderland_players[:5]:
                print(f"  - {player['first_name']} {player['second_name']} (Form: {player.get('form', 'N/A')})")
        else:
            print(f"\n✅ No Sunderland players found")
        
        # Check current season info
        print(f"\n📅 Season Information:")
        events = data.get('events', [])
        if events:
            current_event = next((e for e in events if e.get('is_current', False)), None)
            if current_event:
                print(f"  Current gameweek: {current_event['name']} (ID: {current_event['id']})")
            else:
                print(f"  No current gameweek marked")
                print(f"  First gameweek: {events[0]['name']} (ID: {events[0]['id']})")
        
        # Check if this is current season data
        print(f"\n🔍 Data Quality Check:")
        players_with_form = [p for p in players if p.get('form') and p.get('form') != '0.0']
        print(f"  Players with non-zero form: {len(players_with_form)}/{len(players)}")
        
        if len(players_with_form) == 0:
            print(f"  ⚠️ All players have zero form - this might be pre-season data")
        else:
            print(f"  ✅ Found players with actual form data")
        
        # Check fixture data
        print(f"\n📅 Fixture Data:")
        fixtures_response = requests.get('https://fantasy.premierleague.com/api/fixtures/')
        fixtures_data = fixtures_response.json()
        print(f"  Total fixtures: {len(fixtures_data)}")
        
        if fixtures_data:
            sample_fixture = fixtures_data[0]
            print(f"  Sample fixture: {sample_fixture}")
            
            # Check if fixtures have proper team names
            home_team = next((t['name'] for t in teams if t['id'] == sample_fixture['team_h']), 'Unknown')
            away_team = next((t['name'] for t in teams if t['id'] == sample_fixture['team_a']), 'Unknown')
            print(f"  Sample fixture teams: {home_team} vs {away_team}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_fpl_data() 