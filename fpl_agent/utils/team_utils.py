"""
Team utility functions for FPL data processing.
"""

from typing import Dict, List, Any
from datetime import datetime
from zoneinfo import ZoneInfo


def group_players_by_team(players_data: Dict[str, Dict[str, Any]]) -> List[Dict[str, Dict[str, Any]]]:
    """
    Group players by team name.
    
    Args:
        players_data: Dictionary of player data keyed by player name
        
    Returns:
        List of dictionaries, where each dictionary contains players for one team
    """
    team_players = {}
    
    # First, group players by team
    for player_name, player_data in players_data.items():
        team_name = player_data.get('team_name', 'Unknown Team')
        if team_name not in team_players:
            team_players[team_name] = {}
        team_players[team_name][player_name] = player_data
    
    # Convert to list of team dicts
    return list(team_players.values())


def get_team_fixture_info(team_name: str, fixtures_data: List[Dict[str, Any]], 
                          current_gameweek: int) -> Dict[str, Any]:
    """
    Get fixture information for a specific team in a gameweek.
    
    Args:
        team_name: Name of the team
        fixtures_data: List of all fixtures (with team names as strings)
        current_gameweek: Current gameweek number
        
    Returns:
        Dictionary containing fixture string, double gameweek status, and fixture difficulty
    """
    # Find opponents for this gameweek
    opponents = []
    fixture_difficulties = []
    
    for fixture_data in fixtures_data:
        if fixture_data.get('event') == current_gameweek:
            home_team = fixture_data.get('team_h')
            away_team = fixture_data.get('team_a')
            
            # Get fixture date and time
            kickoff_time = fixture_data.get('kickoff_time')
            if kickoff_time:
                try:
                    # Parse the ISO format date from FPL API
                    fixture_date = datetime.fromisoformat(kickoff_time.replace('Z', '+00:00'))
                    # Convert UTC to BST (British Summer Time)
                    utc_tz = ZoneInfo('UTC')
                    bst_tz = ZoneInfo('Europe/London')
                    fixture_date = fixture_date.replace(tzinfo=utc_tz).astimezone(bst_tz)
                    # Format as "Sunday 22nd May 2025 at 14:00"
                    day = fixture_date.day
                    suffix = 'th' if 11 <= day <= 13 else {1: 'st', 2: 'nd', 3: 'rd'}.get(day % 10, 'th')
                    formatted_date = f"{fixture_date.strftime('%A')} {day}{suffix} {fixture_date.strftime('%B %Y')} at {fixture_date.strftime('%H:%M')}"
                except:
                    formatted_date = "TBD"
            else:
                formatted_date = "TBD"
            
            if home_team == team_name:
                # Team is playing home
                opponents.append(f"home to {away_team} on {formatted_date}")
                # Get home difficulty (for the home team)
                fixture_difficulties.append(fixture_data.get('team_h_difficulty', 3))
            elif away_team == team_name:
                # Team is playing away
                opponents.append(f"away to {home_team} on {formatted_date}")
                # Get away difficulty (for the away team)
                fixture_difficulties.append(fixture_data.get('team_a_difficulty', 3))
    
    # Calculate average fixture difficulty
    if fixture_difficulties:
        avg_difficulty = sum(fixture_difficulties) / len(fixture_difficulties)
    else:
        avg_difficulty = 3.0
    
    # Format opponent string
    is_double_gameweek = len(opponents) > 1
    
    if opponents:
        if len(opponents) == 1:
            fixture_str = opponents[0]
        else:
            # Double gameweek
            fixture_str = f"double gameweek: {' and '.join(opponents)}"
    else:
        fixture_str = "no fixture scheduled"
    
    return {
        'fixture_str': fixture_str,
        'is_double_gameweek': is_double_gameweek,
        'fixture_difficulty': avg_difficulty
    }
