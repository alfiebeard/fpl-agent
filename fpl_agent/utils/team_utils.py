"""
Utility functions for team management and analysis.
"""

from pathlib import Path
from typing import List, Dict, Any


def get_all_teams() -> List[str]:
    """
    Get list of all team names from team_data directory.
    
    Returns:
        List of team names (directory names)
    """
    team_data_dir = Path("team_data")
    if not team_data_dir.exists():
        return []
    
    teams = []
    for item in team_data_dir.iterdir():
        if item.is_dir() and item.name != "shared":
            teams.append(item.name)
    
    return sorted(teams)


def group_players_by_team(players: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    """
    Group players by their team.
    
    Args:
        players: List of player dictionaries
        
    Returns:
        Dictionary mapping team names to lists of players
    """
    grouped = {}
    for player in players:
        team = player.get('team', 'Unknown')
        if team not in grouped:
            grouped[team] = []
        grouped[team].append(player)
    
    return grouped


def get_team_fixture_info(team_name: str, fixtures: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Get fixture information for a specific team.
    
    Args:
        team_name: Name of the team
        fixtures: List of all fixtures
        
    Returns:
        List of fixtures involving the specified team
    """
    team_fixtures = []
    for fixture in fixtures:
        if (fixture.get('team_h') == team_name or 
            fixture.get('team_a') == team_name):
            team_fixtures.append(fixture)
    
    return team_fixtures
