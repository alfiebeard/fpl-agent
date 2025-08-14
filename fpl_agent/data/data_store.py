"""
Data store for managing player_data.json file persistence.

This class handles file I/O operations and provides age-based warnings
without forcing data refresh.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class DataStore:
    """Manages persistence of player data to/from JSON file"""
    
    def __init__(self, data_dir: str = "team_data"):
        """
        Initialize data store.
        
        Args:
            data_dir: Directory to store data files
        """
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        self.player_data_file = self.data_dir / "player_data.json"
    
    def load_player_data(self) -> Optional[Dict[str, Any]]:
        """
        Load player data from JSON file.
        
        Returns:
            Player data dictionary or None if file doesn't exist
        """
        if not self.player_data_file.exists():
            logger.info("No player data file found")
            return None
        
        try:
            with open(self.player_data_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Check data age and provide warnings
            self._check_data_age(data)
            return data
            
        except Exception as e:
            logger.error(f"Failed to load player data: {e}")
            return None
    
    def save_player_data(self, player_data: Dict[str, Any]) -> None:
        """
        Save player data to JSON file.
        
        Args:
            player_data: Player data to save
        """
        try:
            # Add timestamp for age tracking
            data_to_save = {
                'cache_timestamp': datetime.now().isoformat(),
                'player_data': player_data,
                'total_players': len(player_data)
            }
            
            with open(self.player_data_file, 'w', encoding='utf-8') as f:
                json.dump(data_to_save, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Saved player data with {len(player_data)} players to {self.player_data_file}")
            
        except Exception as e:
            logger.error(f"Failed to save player data: {e}")
            raise
    
    def _check_data_age(self, data: Dict[str, Any]) -> None:
        """
        Check data age and provide appropriate warnings.
        
        Args:
            data: Loaded data dictionary
        """
        age_hours = self._calculate_data_age_hours(data)
        if age_hours is None:
            warning_msg = "⚠️  Using player data with unknown age. Consider refreshing for fresh data."
            logger.warning(warning_msg)
            print(f"\n{warning_msg}")
            return
        
        # Age thresholds
        CRITICAL_AGE_HOURS = 168  # 7 days
        WARNING_AGE_HOURS = 24    # 1 day
        
        if age_hours > CRITICAL_AGE_HOURS:
            warning_msg = f"⚠️  CRITICAL: Using player data that is {age_hours:.1f} hours old ({age_hours/24:.1f} days). Data is very outdated!"
            logger.warning(warning_msg)
            print(f"\n{warning_msg}")
        elif age_hours > WARNING_AGE_HOURS:
            warning_msg = f"⚠️  Using player data that is {age_hours:.1f} hours old. Consider refreshing for fresh data."
            logger.warning(warning_msg)
            print(f"\n{warning_msg}")
        else:
            logger.info(f"Using player data ({age_hours:.1f} hours old)")
    
    def _calculate_data_age_hours(self, data: Dict[str, Any]) -> Optional[float]:
        """
        Calculate the age of stored data in hours.
        
        Args:
            data: Loaded data dictionary
            
        Returns:
            Age in hours or None if no data or timestamp
        """
        cache_timestamp = data.get('cache_timestamp')
        if not cache_timestamp:
            return None
        
        try:
            cache_time = datetime.fromisoformat(cache_timestamp)
            return (datetime.now() - cache_time).total_seconds() / 3600
        except Exception:
            return None