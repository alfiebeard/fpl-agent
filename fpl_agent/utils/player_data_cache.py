"""
Player data caching utilities.

This module handles caching of enriched player data to avoid repeated API calls.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class PlayerDataCache:
    """Handles caching of enriched player data"""
    
    def __init__(self):
        self.cache_dir = Path("team_data")
        self.cache_dir.mkdir(exist_ok=True)
        self.cache_file = self.cache_dir / "player_data.json"
    
    def get_cache_path(self) -> Path:
        """Get the path to the player data cache file"""
        return self.cache_file
    
    def load_cached_data(self) -> Optional[Dict[str, Any]]:
        """
        Load cached player data from JSON file.
        
        Returns:
            Cached player data or None if not available
        """
        if not self.cache_file.exists():
            logger.info("No cached player data found")
            return None
        
        try:
            with open(self.cache_file, 'r', encoding='utf-8') as f:
                cached_data = json.load(f)
            
            # Check if cache has timestamp for age calculation
            cache_timestamp = cached_data.get('cache_timestamp')
            if cache_timestamp:
                cache_time = datetime.fromisoformat(cache_timestamp)
                age_hours = (datetime.now() - cache_time).total_seconds() / 3600
                
                if age_hours > 24:
                    warning_msg = f"⚠️  Using cached player data that is {age_hours:.1f} hours old. Consider using --force-refresh for fresh data."
                    logger.warning(warning_msg)
                    print(f"\n{warning_msg}")
                else:
                    logger.info(f"Using cached player data ({age_hours:.1f} hours old)")
                
                return cached_data
            else:
                warning_msg = "⚠️  Using cached player data with unknown age. Consider using --force-refresh for fresh data."
                logger.warning(warning_msg)
                print(f"\n{warning_msg}")
                return cached_data
            
        except Exception as e:
            logger.error(f"Failed to load cached player data: {e}")
            return None
    
    def save_data(self, player_data: Dict[str, Dict[str, Any]]) -> None:
        """
        Save player data to cache file.
        
        Args:
            player_data: Dictionary of structured enriched player data
        """
        try:
            cache_data = {
                'cache_timestamp': datetime.now().isoformat(),
                'player_data': player_data,
                'total_players': len(player_data)
            }
            
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Saved player data cache with {len(player_data)} players to {self.cache_file}")
            
        except Exception as e:
            logger.error(f"Failed to save player data cache: {e}")
    
    def get_cached_enriched_data(self) -> Optional[Dict[str, Dict[str, Any]]]:
        """
        Get enriched player data from cache if available.
        
        Returns:
            Cached enriched player data or None if not available
        """
        cached_data = self.load_cached_data()
        
        if cached_data and 'player_data' in cached_data:
            return cached_data['player_data']
        
        return None
    
    def clear_cache(self) -> None:
        """Clear the player data cache"""
        try:
            if self.cache_file.exists():
                self.cache_file.unlink()
                logger.info("Player data cache cleared")
        except Exception as e:
            logger.error(f"Failed to clear player data cache: {e}")
    
    def get_cache_status(self) -> Dict[str, Any]:
        """Get status information about the cache"""
        if not self.cache_file.exists():
            return {
                "exists": False,
                "age_hours": None,
                "total_players": 0
            }
        
        try:
            with open(self.cache_file, 'r', encoding='utf-8') as f:
                cached_data = json.load(f)
            
            cache_timestamp = cached_data.get('cache_timestamp')
            age_hours = None
            if cache_timestamp:
                cache_time = datetime.fromisoformat(cache_timestamp)
                age_hours = (datetime.now() - cache_time).total_seconds() / 3600
            
            return {
                "exists": True,
                "age_hours": age_hours,
                "total_players": cached_data.get('total_players', 0),
                "cache_path": str(self.cache_file)
            }
        except Exception as e:
            logger.error(f"Failed to get cache status: {e}")
            return {
                "exists": False,
                "error": str(e)
            }
