"""
Centralized FPL data management, caching, and team/player lookups.
This consolidates FPL data fetching logic that was previously duplicated
between LLMStrategy and LightweightLLMStrategy.
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from pathlib import Path

from ..core.config import Config
from ..ingestion.fetch_fpl import FPLDataFetcher

logger = logging.getLogger(__name__)


class FPLDataManager:
    """
    Centralized manager for FPL data fetching, caching, and lookups.
    
    This consolidates FPL data management logic that was previously
    duplicated between different strategy classes.
    """
    
    def __init__(self, config: Config):
        """
        Initialize FPL data manager.
        
        Args:
            config: FPL configuration object
        """
        self.config = config
        self.fetcher = FPLDataFetcher(config)
        self._cache = {}
        self._cache_timestamps = {}
        self._cache_expiry_hours = 24  # Cache data for 24 hours
        
    def get_fpl_static_data(self, force_refresh: bool = False) -> Dict[str, Any]:
        """
        Get FPL static data (teams, players, etc.) with caching.
        
        Args:
            force_refresh: Whether to ignore cache and fetch fresh data
            
        Returns:
            Dictionary containing FPL static data
        """
        cache_key = "fpl_static_data"
        
        if not force_refresh and self._is_cache_valid(cache_key):
            logger.debug("Using cached FPL static data")
            return self._cache[cache_key]
        
        logger.info("Fetching fresh FPL static data...")
        try:
            data = self.fetcher.get_fpl_static_data()
            self._cache[cache_key] = data
            self._cache_timestamps[cache_key] = datetime.now()
            logger.info(f"FPL static data cached: {len(data.get('teams', []))} teams")
            return data
        except Exception as e:
            logger.error(f"Failed to fetch FPL static data: {e}")
            # Return cached data if available, even if expired
            if cache_key in self._cache:
                logger.warning("Returning expired cached data due to fetch failure")
                return self._cache[cache_key]
            raise
    
    def get_fixtures(self, force_refresh: bool = False) -> List[Dict[str, Any]]:
        """
        Get FPL fixtures data with caching.
        
        Args:
            force_refresh: Whether to ignore cache and fetch fresh data
            
        Returns:
            List of fixture dictionaries
        """
        cache_key = "fixtures"
        
        if not force_refresh and self._is_cache_valid(cache_key):
            logger.debug("Using cached fixtures data")
            return self._cache[cache_key]
        
        logger.info("Fetching fresh fixtures data...")
        try:
            data = self.fetcher.get_fixtures()
            self._cache[cache_key] = data
            self._cache_timestamps[cache_key] = datetime.now()
            logger.info(f"Fixtures data cached: {len(data)} fixtures")
            return data
        except Exception as e:
            logger.error(f"Failed to fetch fixtures data: {e}")
            if cache_key in self._cache:
                logger.warning("Returning expired cached data due to fetch failure")
                return self._cache[cache_key]
            raise
    
    def get_current_gameweek(self, force_refresh: bool = False) -> Optional[int]:
        """
        Get current FPL gameweek with caching.
        
        Args:
            force_refresh: Whether to ignore cache and fetch fresh data
            
        Returns:
            Current gameweek number or None if unavailable
        """
        cache_key = "current_gameweek"
        
        if not force_refresh and self._is_cache_valid(cache_key):
            logger.debug("Using cached current gameweek")
            return self._cache[cache_key]
        
        logger.info("Fetching fresh current gameweek...")
        try:
            gameweek = self.fetcher.get_current_gameweek()
            self._cache[cache_key] = gameweek
            self._cache_timestamps[cache_key] = datetime.now()
            logger.info(f"Current gameweek cached: GW{gameweek}")
            return gameweek
        except Exception as e:
            logger.error(f"Failed to fetch current gameweek: {e}")
            if cache_key in self._cache:
                logger.warning("Returning expired cached data due to fetch failure")
                return self._cache[cache_key]
            return None
    
    def get_teams_data(self, force_refresh: bool = False) -> List[Dict[str, Any]]:
        """
        Get teams data from FPL static data with caching.
        
        Args:
            force_refresh: Whether to ignore cache and fetch fresh data
            
        Returns:
            List of team dictionaries
        """
        static_data = self.get_fpl_static_data(force_refresh)
        return static_data.get('teams', [])
    
    def get_team_id_map(self, force_refresh: bool = False) -> Dict[str, int]:
        """
        Get mapping of team names to team IDs with caching.
        
        Args:
            force_refresh: Whether to ignore cache and fetch fresh data
            
        Returns:
            Dictionary mapping team names to team IDs
        """
        cache_key = "team_id_map"
        
        if not force_refresh and self._is_cache_valid(cache_key):
            logger.debug("Using cached team ID mapping")
            return self._cache[cache_key]
        
        logger.info("Building team ID mapping...")
        try:
            teams_data = self.get_teams_data(force_refresh)
            team_id_map = {}
            
            for team in teams_data:
                if isinstance(team, dict) and 'name' in team and 'id' in team:
                    team_id_map[team['name']] = team['id']
                else:
                    logger.debug(f"Skipping invalid team data: {team}")
            
            self._cache[cache_key] = team_id_map
            self._cache_timestamps[cache_key] = datetime.now()
            logger.info(f"Team ID mapping cached: {len(team_id_map)} teams")
            return team_id_map
            
        except Exception as e:
            logger.error(f"Failed to build team ID mapping: {e}")
            if cache_key in self._cache:
                logger.warning("Returning expired cached data due to mapping failure")
                return self._cache[cache_key]
            return {}
    
    def get_fixture_info(self, team_name: str, gameweek: int, force_refresh: bool = False) -> Dict[str, Any]:
        """
        Get fixture information for a team in a specific gameweek.
        
        Args:
            team_name: Name of the team
            gameweek: Gameweek number
            force_refresh: Whether to ignore cache and fetch fresh data
            
        Returns:
            Dictionary containing fixture string, double gameweek status, and fixture difficulty
        """
        try:
            fixtures_data = self.get_fixtures(force_refresh)
            team_id_map = self.get_team_id_map(force_refresh)
            
            team_id = team_id_map.get(team_name)
            if not team_id:
                logger.warning(f"Team '{team_name}' not found in team mapping")
                return {
                    'fixture_str': "no fixture scheduled",
                    'is_double_gameweek': False,
                    'fixture_difficulty': 3.0
                }
            
            # Find opponents for this gameweek
            opponents = []
            for fixture in fixtures_data:
                if fixture.get('event') == gameweek:
                    if fixture.get('team_h') == team_id:
                        opponents.append({
                            'team': fixture.get('team_a'),
                            'home_away': 'H',
                            'fixture': fixture
                        })
                    elif fixture.get('team_a') == team_id:
                        opponents.append({
                            'team': fixture.get('team_h'),
                            'home_away': 'A',
                            'fixture': fixture
                        })
            
            if not opponents:
                return {
                    'fixture_str': "no fixture scheduled",
                    'is_double_gameweek': False,
                    'fixture_difficulty': 3.0
                }
            
            # Check for double gameweek
            is_double_gameweek = len(opponents) > 1
            
            # Build fixture string
            fixture_parts = []
            for opp in opponents:
                opp_team_name = self._get_team_name_by_id(opp['team'])
                home_away = opp['home_away']
                fixture_parts.append(f"{opp_team_name} ({home_away})")
            
            fixture_str = " vs ".join(fixture_parts)
            
            # Calculate average fixture difficulty
            difficulties = []
            for opp in opponents:
                fixture = opp['fixture']
                # Extract difficulty from fixture data (this may need adjustment based on actual data structure)
                difficulty = fixture.get('difficulty', 3.0)
                difficulties.append(difficulty)
            
            avg_difficulty = sum(difficulties) / len(difficulties) if difficulties else 3.0
            
            return {
                'fixture_str': fixture_str,
                'is_double_gameweek': is_double_gameweek,
                'fixture_difficulty': avg_difficulty,
                'opponents': opponents
            }
            
        except Exception as e:
            logger.error(f"Failed to get fixture info for {team_name} GW{gameweek}: {e}")
            return {
                'fixture_str': "fixture info unavailable",
                'is_double_gameweek': False,
                'fixture_difficulty': 3.0
            }
    
    def get_team_players(self, team_name: str, force_refresh: bool = False) -> List[Dict[str, Any]]:
        """
        Get all players for a specific team with caching.
        
        Args:
            team_name: Name of the team
            force_refresh: Whether to ignore cache and fetch fresh data
            
        Returns:
            List of player dictionaries for the team
        """
        try:
            static_data = self.get_fpl_static_data(force_refresh)
            players_data = static_data.get('elements', [])
            team_id_map = self.get_team_id_map(force_refresh)
            
            team_id = team_id_map.get(team_name)
            if not team_id:
                logger.warning(f"Team '{team_name}' not found in team mapping")
                return []
            
            # Filter players by team
            team_players = [
                player for player in players_data 
                if player.get('team') == team_id
            ]
            
            logger.debug(f"Found {len(team_players)} players for {team_name}")
            return team_players
            
        except Exception as e:
            logger.error(f"Failed to get team players for {team_name}: {e}")
            return []
    
    def refresh_cache(self, force: bool = False) -> None:
        """
        Refresh all cached data.
        
        Args:
            force: Whether to force refresh even if cache is still valid
        """
        logger.info("Refreshing FPL data cache...")
        
        # Clear all cache timestamps to force refresh
        if force:
            self._cache_timestamps.clear()
        
        # Refresh key data
        self.get_fpl_static_data(force_refresh=True)
        self.get_fixtures(force_refresh=True)
        self.get_current_gameweek(force_refresh=True)
        
        logger.info("FPL data cache refresh completed")
    
    def get_cache_status(self) -> Dict[str, Any]:
        """
        Get status of cached data.
        
        Returns:
            Dictionary containing cache status information
        """
        status = {}
        now = datetime.now()
        
        for cache_key, timestamp in self._cache_timestamps.items():
            age_hours = (now - timestamp).total_seconds() / 3600
            is_valid = age_hours < self._cache_expiry_hours
            
            status[cache_key] = {
                'age_hours': round(age_hours, 1),
                'is_valid': is_valid,
                'expires_in_hours': max(0, self._cache_expiry_hours - age_hours)
            }
        
        return status
    
    def _is_cache_valid(self, cache_key: str) -> bool:
        """
        Check if cached data for a key is still valid.
        
        Args:
            cache_key: Cache key to check
            
        Returns:
            True if cache is valid, False otherwise
        """
        if cache_key not in self._cache or cache_key not in self._cache_timestamps:
            return False
        
        timestamp = self._cache_timestamps[cache_key]
        age_hours = (datetime.now() - timestamp).total_seconds() / 3600
        
        return age_hours < self._cache_expiry_hours
    
    def _get_team_name_by_id(self, team_id: int) -> str:
        """
        Get team name by team ID.
        
        Args:
            team_id: Team ID to look up
            
        Returns:
            Team name or "Unknown Team" if not found
        """
        try:
            team_id_map = self.get_team_id_map()
            # Reverse lookup
            for name, tid in team_id_map.items():
                if tid == team_id:
                    return name
            return f"Team_{team_id}"
        except Exception as e:
            logger.error(f"Failed to get team name for ID {team_id}: {e}")
            return f"Team_{team_id}"
