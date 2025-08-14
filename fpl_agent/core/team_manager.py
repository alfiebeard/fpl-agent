"""
Local team management system for FPL
Stores team data for each gameweek in JSON files
"""

import json
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
        self.meta_file = self.data_dir / "meta.json"
    
    def _get_team_file(self, gameweek: int) -> Path:
        """Get the file path for a specific gameweek's team data"""
        return self.data_dir / f"gw{gameweek:02d}.json"
    
    def _load_meta(self) -> Dict[str, Any]:
        """Load the meta.json file"""
        if not self.meta_file.exists():
            return {}
        
        try:
            with open(self.meta_file, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            logger.error(f"Failed to load meta.json: {e}")
            return {}
    
    def _save_meta(self, meta_data: Dict[str, Any]) -> None:
        """Save the meta.json file"""
        try:
            with open(self.meta_file, 'w') as f:
                json.dump(meta_data, f, indent=2)
            logger.info("Meta data saved successfully")
        except IOError as e:
            logger.error(f"Failed to save meta.json: {e}")
    
    def initialize_meta(self, gameweek: int, team_data: Dict[str, Any]) -> None:
        """Initialize the meta.json file with default values for a new team"""
        meta_data = {
            "current_gw": gameweek,
            "last_team_file": f"gw{gameweek:02d}.json",
            "bank": team_data.get('bank', 0.0),
            "free_transfers": 1,
            "chips_used": {
                "wildcard": False,
                "bench_boost": False,
                "free_hit": False,
                "triple_captain": False
            }
        }
        
        self._save_meta(meta_data)
        logger.info(f"Meta data initialized for Gameweek {gameweek}")
    
    def update_meta(self, gameweek: int, team_data: Dict[str, Any], 
                   chips_used: Optional[Dict[str, bool]] = None,
                   free_transfers: Optional[int] = None) -> None:
        """Update the meta.json file with new team status"""
        meta_data = self._load_meta()
        
        # Update basic info
        meta_data["current_gw"] = gameweek
        meta_data["last_team_file"] = f"gw{gameweek:02d}.json"
        meta_data["bank"] = team_data.get('bank', meta_data.get('bank', 0.0))
        
        # Update free transfers if provided
        if free_transfers is not None:
            meta_data["free_transfers"] = free_transfers
        
        # Update chips used if provided
        if chips_used is not None:
            if "chips_used" not in meta_data:
                meta_data["chips_used"] = {}
            meta_data["chips_used"].update(chips_used)
        
        self._save_meta(meta_data)
        logger.info(f"Meta data updated for Gameweek {gameweek}")
    
    def get_meta(self) -> Dict[str, Any]:
        """Get the current meta data"""
        return self._load_meta()
    
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
        team_files = list(self.data_dir.glob("gw*.json"))
        
        if not team_files:
            return None
        
        # Sort by gameweek number
        team_files.sort(key=lambda x: int(x.stem[2:]))  # Remove 'gw' prefix
        
        # Load the latest one
        latest_file = team_files[-1]
        gameweek = int(latest_file.stem[2:])
        return self.load_team(gameweek)
    
    def get_latest_gameweek(self) -> Optional[int]:
        """Get the latest gameweek number"""
        team_files = list(self.data_dir.glob("gw*.json"))
        
        if not team_files:
            return None
        
        # Sort by gameweek number
        team_files.sort(key=lambda x: int(x.stem[2:]))  # Remove 'gw' prefix
        
        # Get the latest gameweek number
        latest_file = team_files[-1]
        return int(latest_file.stem[2:])
    
    def list_teams(self) -> List[int]:
        """List all available gameweeks"""
        team_files = list(self.data_dir.glob("gw*.json"))
        gameweeks = []
        
        for file in team_files:
            try:
                gameweek = int(file.stem[2:])  # Remove 'gw' prefix
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
    
    def is_free_hit_revert_scenario(self, gameweek: int, current_meta: Dict[str, Any]) -> bool:
        """
        Check if this is a free hit revert scenario (next gameweek after free hit was used)
        
        Args:
            gameweek: Current gameweek
            current_meta: Current meta data
            
        Returns:
            True if this is a free hit revert scenario
        """
        # Check if free hit was used in the previous gameweek
        chips_used = current_meta.get('chips_used', {})
        if chips_used.get('free_hit', False):
            # Check if we have a team from before the free hit
            pre_free_hit_gw = gameweek - 2  # The gameweek before the free hit
            if pre_free_hit_gw >= 1:
                pre_free_hit_team = self.load_team(pre_free_hit_gw)
                if pre_free_hit_team:
                    return True
        return False
    
    def handle_free_hit_revert(self, gameweek: int, current_meta: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle free hit revert scenario - revert to team before free hit was used
        
        Args:
            gameweek: Current gameweek
            current_meta: Current meta data
            
        Returns:
            Reverted team data
        """
        # Find the team from before the free hit
        pre_free_hit_gw = gameweek - 2
        pre_free_hit_team_data = self.load_team(pre_free_hit_gw)
        
        if not pre_free_hit_team_data:
            raise ValueError(f"No team found from Gameweek {pre_free_hit_gw} to revert to after free hit")
        
        # Get the team data from before free hit
        pre_free_hit_team = pre_free_hit_team_data['team']
        
        # Create a new team entry for current gameweek with the reverted team
        reverted_team = {
            'captain': pre_free_hit_team.get('captain'),
            'vice_captain': pre_free_hit_team.get('vice_captain'),
            'total_cost': pre_free_hit_team.get('total_cost'),
            'bank': pre_free_hit_team.get('bank'),
            'expected_points': pre_free_hit_team.get('expected_points'),
            'wildcard_or_chip': None,
            'transfers': [],
            'team': pre_free_hit_team['team']
        }
        
        # Save the reverted team
        self.save_team(gameweek, reverted_team)
        
        # Update meta.json to reflect the revert
        # Bank should revert to pre-free-hit bank
        # Free transfers should be 1 (normal weekly allocation)
        # Free hit should remain marked as used
        self.update_meta(
            gameweek=gameweek,
            team_data=reverted_team,
            free_transfers=1  # Normal weekly allocation after revert
        )
        
        logger.info(f"Team reverted to pre-free-hit state for Gameweek {gameweek}")
        return reverted_team
    
    def handle_chip_team_creation(self, gameweek: int, chip_type: str, team_data: Dict[str, Any], create_team_func) -> Dict[str, Any]:
        """
        Handle wildcard or free hit team creation from scratch
        
        Args:
            gameweek: Current gameweek
            chip_type: 'wildcard' or 'free_hit'
            team_data: Initial team data from LLM response
            create_team_func: Function to create a new team
            
        Returns:
            Created team data
        """
        logger.info(f"Creating new team from scratch using {chip_type}")
        
        # Create a new team from scratch using the provided function
        new_team_data = create_team_func(budget=100.0, gameweek=gameweek)
        
        # Override with chip information
        new_team_data['wildcard_or_chip'] = chip_type
        new_team_data['chip_reason'] = team_data.get('chip_reason', f'{chip_type.title()} chip used')
        
        # Save the new team
        self.save_team(gameweek, new_team_data)
        
        # Update meta.json
        current_meta = self.get_meta()
        self.update_meta_from_response(gameweek, new_team_data, current_meta)
        
        logger.info(f"New team created successfully using {chip_type} for Gameweek {gameweek}")
        return new_team_data
    
    def update_meta_from_response(self, gameweek: int, team_data: Dict[str, Any], current_meta: Dict[str, Any]) -> None:
        """Update meta.json based on the LLM response"""
        
        # Check if a chip was used
        chip_used = team_data.get('wildcard_or_chip')
        
        # Check for consecutive free hit usage (not allowed in FPL)
        if chip_used == 'free_hit':
            chips_used = current_meta.get('chips_used', {})
            if chips_used.get('free_hit', False):
                logger.warning("Free hit cannot be used in consecutive gameweeks")
                # Don't mark free hit as used again
                chip_used = None
        
        # Calculate new free transfers
        current_transfers = current_meta.get('free_transfers', 1)
        transfers_made = len(team_data.get('transfers', []))
        
        if chip_used == 'wildcard':
            # Wildcard doesn't affect transfers - they remain unchanged
            new_transfers = current_transfers
        elif chip_used == 'free_hit':
            # Free hit doesn't affect transfers
            new_transfers = current_transfers
        else:
            # Normal transfers
            if transfers_made == 0:
                # No transfers made, carry over 1 (max 2)
                new_transfers = min(current_transfers + 1, 2)
            else:
                # Transfers made, calculate remaining
                new_transfers = max(0, current_transfers - transfers_made)
        
        # Handle chip usage and reset on Gameweek 20
        chips_used = None
        if chip_used and chip_used != 'null':
            chips_used = {chip_used: True}
        
        # Reset all chips on Gameweek 20 (second half of season)
        if gameweek == 20:
            chips_used = {
                "wildcard": False,
                "bench_boost": False,
                "free_hit": False,
                "triple_captain": False
            }
            logger.info("Gameweek 20: All chips reset for second half of season")
        
        # Update meta.json
        self.update_meta(
            gameweek=gameweek,
            team_data=team_data,
            chips_used=chips_used,
            free_transfers=new_transfers
        )
        
        logger.info(f"Meta updated: transfers={new_transfers}, chip_used={chips_used}")
    
    def get_available_chips_from_meta(self, meta_data: Dict[str, Any]) -> Dict[str, Any]:
        """Get available chips information from meta data"""
        chips_used = meta_data.get('chips_used', {})
        available_chips = []
        used_chips = []
        
        all_chips = ['wildcard', 'bench_boost', 'free_hit', 'triple_captain']
        for chip in all_chips:
            if chips_used.get(chip, False):
                used_chips.append({'name': chip})
            else:
                # Special case: Free hit cannot be used in consecutive gameweeks
                if chip == 'free_hit' and chips_used.get('free_hit', False):
                    # Free hit was used, so it's not available
                    used_chips.append({'name': chip})
                else:
                    available_chips.append(chip)
        
        return {
            'used': used_chips,
            'available': available_chips
        }
    
    def get_available_transfers_from_meta(self, meta_data: Dict[str, Any]) -> Dict[str, Any]:
        """Get available transfers information from meta data"""
        return {
            'free_transfers': meta_data.get('free_transfers', 1),
            'bank': meta_data.get('bank', 0.0)
        } 