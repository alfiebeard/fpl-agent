"""
Data service providing a single interface for all FPL data operations.

This class orchestrates the entire data pipeline:
fetch → process → store → retrieve
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

from ..core.config import Config
from ..ingestion.fetch_fpl import FPLDataFetcher
from .data_store import DataStore
from .data_processor import DataProcessor

logger = logging.getLogger(__name__)


class DataService:
    """Single interface for all FPL data operations"""
    
    def __init__(self, config: Config):
        """
        Initialize data service.
        
        Args:
            config: FPL configuration object
        """
        self.config = config
        self.fetcher = FPLDataFetcher(config)
        self.store = DataStore()
        self.processor = DataProcessor(config)
    
    def get_players(self, force_refresh: bool = False, 
                   filters: Optional[Dict[str, Any]] = None) -> Dict[str, Dict[str, Any]]:
        """
        Get player data, either from cache or fresh from API.
        
        Args:
            force_refresh: If True, ignore cache and fetch fresh data
            filters: Optional filters for available players
            
        Returns:
            Dictionary of player data keyed by player ID
        """
        # Try to load from cache first (unless force refresh)
        if not force_refresh:
            cached_data = self.store.load_player_data()
            if cached_data and 'player_data' in cached_data:
                logger.info("Using cached player data")
                player_data = cached_data['player_data']
                
                # Apply filters if requested
                if filters:
                    player_data = self.processor.get_available_players(player_data, filters)
                
                return player_data
        
        # Fetch fresh data if no cache or force refresh
        logger.info("Fetching fresh player data from FPL API...")
        try:
            # Fetch raw data from FPL API
            bootstrap_data = self.fetcher.get_fpl_static_data()
            
            # Process the raw data
            player_data = self.processor.process_fpl_data(bootstrap_data)
            
            # Save to cache
            self.store.save_player_data(player_data)
            
            # Apply filters if requested
            if filters:
                player_data = self.processor.get_available_players(player_data, filters)
            
            logger.info(f"Successfully fetched and processed {len(player_data)} players")
            return player_data
            
        except Exception as e:
            logger.error(f"Failed to fetch fresh data: {e}")
            
            # Try to return cached data as fallback
            cached_data = self.store.load_player_data()
            if cached_data and 'player_data' in cached_data:
                logger.warning("Returning cached data due to fetch failure")
                player_data = cached_data['player_data']
                
                if filters:
                    player_data = self.processor.get_available_players(player_data, filters)
                
                return player_data
            
            raise
    
    def refresh_data(self) -> Dict[str, Dict[str, Any]]:
        """
        Force refresh of player data from FPL API.
        
        Returns:
            Fresh player data
        """
        return self.get_players(force_refresh=True)
    
    def get_available_players(self, filters: Optional[Dict[str, Any]] = None) -> Dict[str, Dict[str, Any]]:
        """
        Get only available players (filtered by availability criteria).
        
        Args:
            filters: Optional custom filters
            
        Returns:
            Dictionary of available players
        """
        if filters is None:
            filters = {
                'exclude_injured': True,
                'exclude_unavailable': True,
                'min_chance_of_playing': 25,
                'min_minutes': 0,
                'max_price': float('inf'),
                'min_form': float('-inf'),
                'positions': ['GK', 'DEF', 'MID', 'FWD']
            }
        
        return self.get_players(force_refresh=False, filters=filters)
    
    def get_players_by_position(self, position: str, force_refresh: bool = False) -> Dict[str, Dict[str, Any]]:
        """
        Get players filtered by position.
        
        Args:
            position: Position to filter by ('GK', 'DEF', 'MID', 'FWD')
            force_refresh: If True, ignore cache and fetch fresh data
            
        Returns:
            Dictionary of players in the specified position
        """
        filters = {
            'exclude_injured': True,
            'exclude_unavailable': True,
            'min_chance_of_playing': 25,
            'min_minutes': 0,
            'max_price': float('inf'),
            'min_form': float('-inf'),
            'positions': [position]
        }
        
        return self.get_players(force_refresh=force_refresh, filters=filters)
    
    def get_players_by_team(self, team_name: str, force_refresh: bool = False) -> Dict[str, Dict[str, Any]]:
        """
        Get players filtered by team.
        
        Args:
            team_name: Team name to filter by
            force_refresh: If True, ignore cache and fetch fresh data
            
        Returns:
            Dictionary of players in the specified team
        """
        all_players = self.get_players(force_refresh=force_refresh)
        
        team_players = {}
        for player_id, player in all_players.items():
            if player.get('team_name') == team_name:
                team_players[player_id] = player
        
        logger.info(f"Found {len(team_players)} players for team {team_name}")
        return team_players
    
    def get_player_by_id(self, player_id: str, force_refresh: bool = False) -> Optional[Dict[str, Any]]:
        """
        Get a specific player by ID.
        
        Args:
            player_id: Player ID to look up
            force_refresh: If True, ignore cache and fetch fresh data
            
        Returns:
            Player data dictionary or None if not found
        """
        all_players = self.get_players(force_refresh=force_refresh)
        return all_players.get(player_id)
    
    def get_player_by_name(self, player_name: str, force_refresh: bool = False) -> Optional[Dict[str, Any]]:
        """
        Get a specific player by name (full name or partial match).
        
        Args:
            player_name: Player name to search for
            force_refresh: If True, ignore cache and fetch fresh data
            
        Returns:
            Player data dictionary or None if not found
        """
        all_players = self.get_players(force_refresh=force_refresh)
        
        # Try exact match first
        for player in all_players.values():
            if player.get('full_name') == player_name:
                return player
        
        # Try partial match
        player_name_lower = player_name.lower()
        for player in all_players.values():
            full_name = player.get('full_name', '').lower()
            if player_name_lower in full_name:
                return player
        
        return None
    
    def get_data_age_hours(self) -> Optional[float]:
        """
        Get the age of cached data in hours.
        
        Returns:
            Age in hours or None if no cached data
        """
        return self.store.get_data_age_hours()
    
    def is_data_fresh(self, max_age_hours: float = 24.0) -> bool:
        """
        Check if cached data is fresh enough.
        
        Args:
            max_age_hours: Maximum age in hours to consider data fresh
            
        Returns:
            True if data is fresh, False otherwise
        """
        age = self.get_data_age_hours()
        if age is None:
            return False
        return age <= max_age_hours
    
    def get_cache_info(self) -> Dict[str, Any]:
        """
        Get information about the current cache status.
        
        Returns:
            Dictionary with cache information
        """
        age_hours = self.get_data_age_hours()
        data_exists = self.store.data_exists()
        
        info = {
            'cache_exists': data_exists,
            'age_hours': age_hours,
            'is_fresh': self.is_data_fresh() if age_hours is not None else False
        }
        
        if age_hours is not None:
            info['age_days'] = age_hours / 24.0
            from datetime import timedelta
            info['last_updated'] = (datetime.now() - timedelta(hours=age_hours)).isoformat()
        
        return info
    
    def get_fixture_info(self, team_name: str, current_gameweek: int) -> Dict[str, Any]:
        """
        Get fixture information for a team in a specific gameweek.
        
        Args:
            team_name: Name of the team
            current_gameweek: Current gameweek number
            
        Returns:
            Dictionary containing fixture string, double gameweek status, and fixture difficulty
        """
        fixtures = self.fetcher.get_fixtures()
        players = self.get_players(force_refresh=False)
        
        return self.processor.get_fixture_info(team_name, current_gameweek, fixtures, players)
