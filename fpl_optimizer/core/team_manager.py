"""
Local team management system for FPL
Stores team data for each gameweek in JSON files
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class TeamManager:
    """Manages local FPL team data for each gameweek"""
    
    def __init__(self, data_dir: str = "team_data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
    
    def _get_team_file(self, gameweek: int) -> Path:
        """Get the file path for a specific gameweek's team data"""
        return self.data_dir / f"team_gw{gameweek}.json"
    
    def save_team(self, gameweek: int, team_data: Dict[str, Any]) -> None:
        """Save team data for a specific gameweek"""
        team_file = self._get_team_file(gameweek)
        
        # Add metadata
        team_data_with_meta = {
            "gameweek": gameweek,
            "saved_at": datetime.now().isoformat(),
            "team": team_data
        }
        
        with open(team_file, 'w') as f:
            json.dump(team_data_with_meta, f, indent=2)
        
        logger.info(f"Team data saved for Gameweek {gameweek}")
    
    def load_team(self, gameweek: int) -> Optional[Dict[str, Any]]:
        """Load team data for a specific gameweek"""
        team_file = self._get_team_file(gameweek)
        
        if not team_file.exists():
            return None
        
        try:
            with open(team_file, 'r') as f:
                data = json.load(f)
            logger.info(f"Team data loaded for Gameweek {gameweek}")
            return data
        except (json.JSONDecodeError, IOError) as e:
            logger.error(f"Failed to load team data for Gameweek {gameweek}: {e}")
            return None
    
    def team_exists(self, gameweek: int) -> bool:
        """Check if team data exists for a specific gameweek"""
        return self._get_team_file(gameweek).exists()
    
    def get_latest_team(self) -> Optional[Dict[str, Any]]:
        """Get the most recent team data"""
        team_files = list(self.data_dir.glob("team_gw*.json"))
        
        if not team_files:
            return None
        
        # Sort by gameweek number
        team_files.sort(key=lambda x: int(x.stem.split('gw')[1]))
        
        # Load the latest one
        latest_file = team_files[-1]
        gameweek = int(latest_file.stem.split('gw')[1])
        return self.load_team(gameweek)
    
    def get_latest_gameweek(self) -> Optional[int]:
        """Get the latest gameweek number"""
        team_files = list(self.data_dir.glob("team_gw*.json"))
        
        if not team_files:
            return None
        
        # Sort by gameweek number
        team_files.sort(key=lambda x: int(x.stem.split('gw')[1]))
        
        # Get the latest gameweek number
        latest_file = team_files[-1]
        return int(latest_file.stem.split('gw')[1])
    
    def list_teams(self) -> List[int]:
        """List all available gameweeks"""
        team_files = list(self.data_dir.glob("team_gw*.json"))
        gameweeks = []
        
        for file in team_files:
            try:
                gameweek = int(file.stem.split('gw')[1])
                gameweeks.append(gameweek)
            except (ValueError, IndexError):
                continue
        
        return sorted(gameweeks)
    
    def delete_team(self, gameweek: int) -> bool:
        """Delete team data for a specific gameweek"""
        team_file = self._get_team_file(gameweek)
        
        if team_file.exists():
            team_file.unlink()
            logger.info(f"Team data deleted for Gameweek {gameweek}")
            return True
        else:
            logger.warning(f"No team data found for Gameweek {gameweek}")
            return False
    
    def get_previous_team(self, gameweek: int) -> Optional[Dict[str, Any]]:
        """Get the team from the previous gameweek"""
        if gameweek <= 1:
            return None
        
        return self.load_team(gameweek - 1)
    
    def validate_team_data(self, team_data: Dict[str, Any]) -> bool:
        """Validate that team data has the required structure"""
        required_keys = ['captain', 'vice_captain', 'total_cost', 'bank', 'team']
        
        for key in required_keys:
            if key not in team_data:
                logger.error(f"Missing required key: {key}")
                return False
        
        team = team_data['team']
        if 'starting' not in team or 'substitutes' not in team:
            logger.error("Team must have 'starting' and 'substitutes' sections")
            return False
        
        # Check player counts
        if len(team['starting']) != 11:
            logger.error(f"Must have exactly 11 starting players, got {len(team['starting'])}")
            return False
        
        if len(team['substitutes']) != 4:
            logger.error(f"Must have exactly 4 substitutes, got {len(team['substitutes'])}")
            return False
        
        # Check budget
        if team_data['total_cost'] > 100.0:
            logger.error(f"Total cost £{team_data['total_cost']}m exceeds budget of £100.0m")
            return False
        
        return True
    
    def format_team_for_display(self, team_data: Dict[str, Any]) -> str:
        """Format team data for display"""
        if not team_data:
            return "No team data available"
        
        # Handle the nested structure
        if 'team' in team_data:
            team = team_data['team']
            gameweek = team_data.get('gameweek', 'Unknown')
        else:
            team = team_data
            gameweek = 'Unknown'
        
        result = []
        
        result.append(f"Gameweek {gameweek}")
        result.append(f"Captain: {team.get('captain', 'Unknown')}")
        result.append(f"Vice Captain: {team.get('vice_captain', 'Unknown')}")
        result.append(f"Total Cost: £{team.get('total_cost', 0)}m")
        result.append(f"Bank: £{team.get('bank', 0)}m")
        result.append("")
        
        if 'starting' in team:
            result.append("Starting XI:")
            for i, player in enumerate(team['starting'], 1):
                result.append(f"  {i:2d}. {player.get('name', 'Unknown')} ({player.get('position', 'Unknown')}) - {player.get('team', 'Unknown')} - £{player.get('price', 0)}m")
        
        if 'substitutes' in team:
            result.append("")
            result.append("Substitutes:")
            for i, player in enumerate(team['substitutes'], 1):
                sub_order = player.get('sub_order', 'N/A')
                result.append(f"  {i:2d}. {player.get('name', 'Unknown')} ({player.get('position', 'Unknown')}) - {player.get('team', 'Unknown')} - £{player.get('price', 0)}m (Sub {sub_order})")
        
        return "\n".join(result) 