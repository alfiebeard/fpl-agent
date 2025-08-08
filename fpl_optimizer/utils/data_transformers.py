"""
Data transformation utilities for FPL data
"""

import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

from ..core.models import Player, Team, Position

logger = logging.getLogger(__name__)


@dataclass
class TeamSummary:
    """Team summary with players and statistics"""
    team: Team
    players: List[Player]
    total_players: int
    total_value: float
    average_points: float


def transform_fpl_data_to_teams(
    bootstrap_data: Dict[str, Any],
    filters: Optional[Dict[str, Any]] = None
) -> Dict[str, TeamSummary]:
    """
    Transform FPL API data into a team-based structure with optional filtering.
    
    Args:
        bootstrap_data: Raw FPL API bootstrap data
        filters: Optional filters to apply to players
        
    Returns:
        Dictionary mapping team names to TeamSummary objects
        
    Example filters:
        filters = {
            'min_chance_of_playing': 50,      # Only players with >50% chance of playing
            'exclude_injured': True,          # Exclude injured players
            'exclude_unavailable': True,      # Exclude unavailable players
            'min_minutes': 90,                # Only players with at least 90 minutes
            'max_price': 15.0,                # Only players under £15.0m
            'min_form': 0.0,                  # Only players with positive form
            'positions': [Position.GK, Position.DEF, Position.MID, Position.FWD]  # Only specific positions
        }
    """
    
    # Default filters
    default_filters = {
        'min_chance_of_playing': 0,      # Include all players by default
        'exclude_injured': True,         # Exclude injured by default
        'exclude_unavailable': True,     # Exclude unavailable by default
        'min_minutes': 0,                # No minimum minutes by default
        'max_price': float('inf'),       # No price limit by default
        'min_form': float('-inf'),       # No form minimum by default
        'positions': [Position.GK, Position.DEF, Position.MID, Position.FWD]  # All positions by default
    }
    
    # Merge with provided filters
    if filters:
        default_filters.update(filters)
    
    filters = default_filters
    
    # Create team mapping and Team objects
    team_mapping = {}
    teams = {}
    
    for team_data in bootstrap_data.get('teams', []):
        team = Team(
            id=team_data['id'],
            name=team_data['name'],
            short_name=team_data['short_name'],
            strength=int(team_data.get('strength', 0) or 0),
            form=float(team_data.get('form', 0) or 0)
        )
        team_mapping[team_data['id']] = team
        teams[team.name] = TeamSummary(
            team=team,
            players=[],
            total_players=0,
            total_value=0.0,
            average_points=0.0
        )
    
    # Position mapping
    position_map = {1: Position.GK, 2: Position.DEF, 3: Position.MID, 4: Position.FWD}
    
    # Process players
    for player_data in bootstrap_data.get('elements', []):
        try:
            # Basic player info
            player_id = player_data['id']
            first_name = player_data['first_name']
            second_name = player_data['second_name']
            name = f"{first_name} {second_name}"
            
            # Position
            element_type = player_data['element_type']
            position = position_map.get(element_type)
            if position is None:
                logger.warning(f"Unknown position type {element_type} for player {player_id}")
                continue
            
            # Team info
            team_id = player_data['team']
            team = team_mapping.get(team_id)
            if team is None:
                logger.warning(f"Unknown team ID {team_id} for player {player_id}")
                continue
            
            # Pricing
            price = player_data['now_cost'] / 10.0  # Convert from tenths
            
            # Performance stats
            total_points = player_data['total_points']
            form = float(player_data.get('form', 0))
            minutes = player_data.get('minutes', 0)
            selected_by_percent = float(player_data.get('selected_by_percent', 0))
            
            # Status and availability
            status = player_data.get('status', 'a')
            is_injured = status == 'i'
            chance_of_playing = player_data.get('chance_of_playing_next_round')
            
            # Expected stats
            expected_goals = player_data.get('expected_goals', 0.0)
            expected_assists = player_data.get('expected_assists', 0.0)
            expected_goals_conceded = player_data.get('expected_goals_conceded', 0.0)
            
            # Additional stats
            goals_scored = player_data.get('goals_scored', 0)
            assists = player_data.get('assists', 0)
            clean_sheets = player_data.get('clean_sheets', 0)
            saves = player_data.get('saves', 0)
            bonus = player_data.get('bonus', 0)
            expected_points_next = player_data.get('ep_next')
            
            # Apply filters
            if not _passes_filters(
                position, status, chance_of_playing, minutes, 
                price, form, filters
            ):
                continue
            
            # Create player using the updated Player model with FPL API field names
            player = Player(
                id=player_id,
                first_name=first_name,
                second_name=second_name,
                team_id=team_id,
                element_type=element_type,
                now_cost=player_data['now_cost'],
                total_points=total_points,
                form=player_data.get('form', '0.0'),
                points_per_game=player_data.get('points_per_game', '0.0'),
                minutes=minutes,
                selected_by_percent=player_data.get('selected_by_percent', '0.0'),
                xG=player_data.get('xG', '0.00'),
                xA=player_data.get('xA', '0.00'),
                xGC=player_data.get('xGC', '0.00'),
                xMins_pct=player_data.get('xMins_pct', 1.0),
                status=status,
                news=player_data.get('news', ''),
                news_added=player_data.get('news_added'),
                chance_of_playing_next_round=player_data.get('chance_of_playing_next_round'),
                chance_of_playing_this_round=player_data.get('chance_of_playing_this_round'),
                cost_change_start=player_data.get('cost_change_start', 0),
                cost_change_event=player_data.get('cost_change_event', 0),
                team_name=team.name,
                team_short_name=team.short_name
            )
            
            # Add additional data to custom_data
            player.custom_data.update({
                'status': status,
                'chance_of_playing': chance_of_playing,
                'expected_points_next': expected_points_next,
                'goals_scored': goals_scored,
                'assists': assists,
                'clean_sheets': clean_sheets,
                'saves': saves,
                'bonus': bonus,
                'bps': player_data.get('bps', 0),
                'ict_index': player_data.get('ict_index', 0.0),
                'influence': player_data.get('influence', 0.0),
                'creativity': player_data.get('creativity', 0.0),
                'threat': player_data.get('threat', 0.0)
            })
            
            # Add to team
            teams[team.name].players.append(player)
            
        except Exception as e:
            logger.warning(f"Failed to process player {player_data.get('id')}: {e}")
            continue
    
    # Calculate team statistics
    for team_summary in teams.values():
        team_summary.total_players = len(team_summary.players)
        team_summary.total_value = sum(p.price for p in team_summary.players)
        team_summary.average_points = sum(p.total_points for p in team_summary.players) / max(team_summary.total_players, 1)
        
        # Sort players by position (GK, DEF, MID, FWD) then by total points
        position_order = {Position.GK: 0, Position.DEF: 1, Position.MID: 2, Position.FWD: 3}
        team_summary.players.sort(key=lambda p: (position_order.get(p.position, 4), -p.total_points))
    
    logger.info(f"Transformed data for {len(teams)} teams with {sum(len(t.players) for t in teams.values())} players")
    
    return teams


def _passes_filters(
    position: Position,
    status: str,
    chance_of_playing: Optional[int],
    minutes: int,
    price: float,
    form: float,
    filters: Dict[str, Any]
) -> bool:
    """Check if a player passes all filters"""
    
    # Position filter
    if position not in filters['positions']:
        return False
    
    # Status filters
    if filters['exclude_injured'] and status == 'i':
        return False
    
    if filters['exclude_unavailable'] and status in ['n', 'u']:
        return False
    
    # Chance of playing filter
    if chance_of_playing is not None and chance_of_playing < filters['min_chance_of_playing']:
        return False
    
    # Minutes filter
    if minutes < filters['min_minutes']:
        return False
    
    # Price filter
    if price > filters['max_price']:
        return False
    
    # Form filter
    if form < filters['min_form']:
        return False
    
    return True


def print_teams_summary(teams: Dict[str, TeamSummary], max_players_per_team: int = 5) -> None:
    """
    Print a summary of teams and their top players.
    
    Args:
        teams: Dictionary of teams from transform_fpl_data_to_teams
        max_players_per_team: Maximum number of players to show per team
    """
    
    print(f"\n{'='*80}")
    print(f"TEAMS SUMMARY ({len(teams)} teams)")
    print(f"{'='*80}")
    
    for team_name, team_summary in sorted(teams.items()):
        team = team_summary.team
        print(f"\n{team.name} ({team.short_name})")
        print(f"  Players: {team_summary.total_players} | Total Value: £{team_summary.total_value:.1f}m | Avg Points: {team_summary.average_points:.1f}")
        print(f"  {'-'*60}")
        
        # Show top players by total points
        top_players = sorted(team_summary.players, key=lambda p: p.total_points, reverse=True)[:max_players_per_team]
        
        for player in top_players:
            status_indicator = ""
            status = player.custom_data.get('status', 'a')
            chance_of_playing = player.custom_data.get('chance_of_playing')
            
            if status == 'i':
                status_indicator = " [INJ]"
            elif status == 'n':
                status_indicator = " [UNAV]"
            elif chance_of_playing and chance_of_playing < 75:
                status_indicator = f" [{chance_of_playing}%]"
            
            print(f"  {player.name:<25} {player.position.value:<4} £{player.price:<5.1f} {player.total_points:>3}pts "
                  f"{player.form:>5.1f}form {player.selected_by_pct:>5.1f}%{status_indicator}")


def get_team_by_name(teams: Dict[str, TeamSummary], team_name: str) -> Optional[TeamSummary]:
    """Get a specific team by name (case-insensitive)"""
    for name, team_summary in teams.items():
        if name.lower() == team_name.lower():
            return team_summary
    return None


def get_players_by_position(teams: Dict[str, TeamSummary], position: Position) -> List[Player]:
    """Get all players of a specific position across all teams"""
    players = []
    for team_summary in teams.values():
        players.extend([p for p in team_summary.players if p.position == position])
    return sorted(players, key=lambda p: p.total_points, reverse=True)


def get_top_players(teams: Dict[str, TeamSummary], position: Position = None, limit: int = 10) -> List[Player]:
    """Get top players by total points, optionally filtered by position"""
    all_players = []
    for team_summary in teams.values():
        if position:
            all_players.extend([p for p in team_summary.players if p.position == position])
        else:
            all_players.extend(team_summary.players)
    
    return sorted(all_players, key=lambda p: p.total_points, reverse=True)[:limit]