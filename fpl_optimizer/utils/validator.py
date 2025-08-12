"""
FPL Team Validator
Validates FPL teams against official rules and checks bank calculations
"""

import json
import logging
from typing import Dict, List, Any, Optional
from pathlib import Path
from enum import Enum

logger = logging.getLogger(__name__)


class Position(Enum):
    GK = "GK"
    DEF = "DEF"
    MID = "MID"
    FWD = "FWD"


class ValidationError(Exception):
    """Custom exception for validation errors"""
    pass


class FPLValidator:
    """
    Validates FPL teams against official rules and checks bank calculations
    """
    
    def __init__(self, data_dir: str = "team_data"):
        self.data_dir = Path(data_dir)
        self.meta_file = self.data_dir / "meta.json"
    
    def validate_team_data(self, team_data: Dict[str, Any], gameweek: int) -> List[str]:
        """
        Validate team data against FPL rules
        
        Args:
            team_data: Team data to validate
            gameweek: Current gameweek
            
        Returns:
            List of validation errors (empty if valid)
        """
        errors = []
        
        # Basic structure validation
        errors.extend(self._validate_basic_structure(team_data))
        
        # FPL rules validation
        errors.extend(self._validate_fpl_rules(team_data))
        
        # Formation validation
        errors.extend(self._validate_formation(team_data))
        
        # Captain validation
        errors.extend(self._validate_captain(team_data))
        
        # Substitute order validation
        errors.extend(self._validate_substitutes(team_data))
        
        return errors
    
    def validate_bank_calculation(self, team_data: Dict[str, Any], gameweek: int, 
                                transfers: List[Dict[str, str]], 
                                available_players: Dict[str, Dict[str, Any]]) -> List[str]:
        """
        Validate bank calculation based on transfers and price changes
        
        Args:
            team_data: New team data
            gameweek: Current gameweek
            transfers: List of transfers made
            available_players: Current available players with prices
            
        Returns:
            List of validation errors (empty if valid)
        """
        errors = []
        
        try:
            # Get previous team data
            previous_team = self._get_previous_team(gameweek)
            if not previous_team:
                errors.append(f"No previous team found for Gameweek {gameweek - 1}")
                return errors
            
            # Calculate expected bank
            expected_bank = self._calculate_expected_bank(
                previous_team, team_data, transfers, available_players
            )
            
            # Compare with actual bank
            actual_bank = team_data.get('bank', 0.0)
            
            if abs(expected_bank - actual_bank) > 0.05:  # Allow small rounding differences
                errors.append(
                    f"Bank calculation error: Expected £{expected_bank:.1f}m, "
                    f"got £{actual_bank:.1f}m (difference: £{abs(expected_bank - actual_bank):.1f}m)"
                )
            
        except Exception as e:
            errors.append(f"Bank calculation failed: {str(e)}")
        
        return errors
    
    def validate_files_consistency(self, gameweek: int) -> List[str]:
        """
        Validate consistency between team file, meta.json, and FPL rules
        
        Args:
            gameweek: Gameweek to validate
            
        Returns:
            List of validation errors (empty if valid)
        """
        errors = []
        
        # Check if files exist
        team_file = self.data_dir / f"gw{gameweek:02d}.json"
        if not team_file.exists():
            errors.append(f"Team file gw{gameweek:02d}.json not found")
            return errors
        
        if not self.meta_file.exists():
            errors.append("meta.json file not found")
            return errors
        
        # Load team data
        try:
            with open(team_file, 'r') as f:
                team_data = json.load(f)
        except Exception as e:
            errors.append(f"Failed to load team file: {str(e)}")
            return errors
        
        # Load meta data
        try:
            with open(self.meta_file, 'r') as f:
                meta_data = json.load(f)
        except Exception as e:
            errors.append(f"Failed to load meta.json: {str(e)}")
            return errors
        
        # Validate team data
        team_errors = self.validate_team_data(team_data['team'], gameweek)
        errors.extend(team_errors)
        
        # Check meta consistency
        meta_errors = self._validate_meta_consistency(meta_data, gameweek, team_data['team'])
        errors.extend(meta_errors)
        
        return errors
    
    def _validate_basic_structure(self, team_data: Dict[str, Any]) -> List[str]:
        """Validate basic team structure"""
        errors = []
        
        # Required keys
        required_keys = ['captain', 'vice_captain', 'total_cost', 'bank', 'team']
        for key in required_keys:
            if key not in team_data:
                errors.append(f"Missing required key: {key}")
        
        if 'team' in team_data:
            team = team_data['team']
            if 'starting' not in team or 'substitutes' not in team:
                errors.append("Team must have 'starting' and 'substitutes' sections")
            else:
                if len(team['starting']) != 11:
                    errors.append(f"Must have exactly 11 starting players, got {len(team['starting'])}")
                if len(team['substitutes']) != 4:
                    errors.append(f"Must have exactly 4 substitutes, got {len(team['substitutes'])}")
        
        return errors
    
    def _validate_fpl_rules(self, team_data: Dict[str, Any]) -> List[str]:
        """Validate FPL rules"""
        errors = []
        
        if 'team' not in team_data:
            return errors
        
        team = team_data['team']
        all_players = team.get('starting', []) + team.get('substitutes', [])
        
        # Get constraints from config
        position_limits = self.config.get_position_limits()
        squad_size = self.config.get_team_config().get('squad_size', 15)
        budget = self.config.get_team_config().get('budget', 100.0)
        max_players_per_team = self.config.get_team_config().get('max_players_per_team', 3)
        
        # Check squad size
        if len(all_players) != squad_size:
            errors.append(f"Must have exactly {squad_size} players, got {len(all_players)}")
            return errors
        
        # Check position distribution
        position_counts = {'GK': 0, 'DEF': 0, 'MID': 0, 'FWD': 0}
        team_counts = {}
        
        for player in all_players:
            # Count positions
            position = player.get('position')
            if position in position_counts:
                position_counts[position] += 1
            
            # Count teams
            team_name = player.get('team')
            if team_name:
                team_counts[team_name] = team_counts.get(team_name, 0) + 1
        
        # Validate position counts
        for pos, limit in position_limits.items():
            if position_counts.get(pos, 0) != limit:
                errors.append(f"Must have exactly {limit} {pos.lower()}s, got {position_counts.get(pos, 0)}")
        
        # Validate team limits
        for team_name, count in team_counts.items():
            if count > max_players_per_team:
                errors.append(f"Maximum {max_players_per_team} players allowed from {team_name}, got {count}")
        
        # Check total cost
        total_cost = team_data.get('total_cost', 0)
        if total_cost > budget:
            errors.append(f"Total cost £{total_cost}m exceeds budget of £{budget}m")
        
        return errors
    
    def _validate_formation(self, team_data: Dict[str, Any]) -> List[str]:
        """Validate formation is legal"""
        errors = []
        
        if 'team' not in team_data:
            return errors
        
        starting = team_data['team'].get('starting', [])
        if len(starting) != 11:
            return errors
        
        # Count positions in starting 11
        position_counts = {'GK': 0, 'DEF': 0, 'MID': 0, 'FWD': 0}
        for player in starting:
            position = player.get('position')
            if position in position_counts:
                position_counts[position] += 1
        
        # Get formation constraints from config
        formation_constraints = self.config.get_formation_constraints()
        
        # Validate formation
        if position_counts['GK'] != 1:
            errors.append(f"Must have exactly 1 goalkeeper in starting 11, got {position_counts['GK']}")
        
        for pos, (min_count, max_count) in formation_constraints.items():
            count = position_counts.get(pos, 0)
            if not (min_count <= count <= max_count):
                errors.append(f"Must have {min_count}-{max_count} {pos.lower()}s in starting 11, got {count}")
        
        return errors
    
    def _validate_captain(self, team_data: Dict[str, Any]) -> List[str]:
        """Validate captain and vice-captain"""
        errors = []
        
        captain = team_data.get('captain')
        vice_captain = team_data.get('vice_captain')
        
        if not captain:
            errors.append("Captain is required")
        if not vice_captain:
            errors.append("Vice-captain is required")
        
        if captain and vice_captain and captain == vice_captain:
            errors.append("Captain and vice-captain must be different players")
        
        # Check captain and vice-captain are in the team
        if 'team' in team_data:
            all_players = team_data['team'].get('starting', []) + team_data['team'].get('substitutes', [])
            player_names = [p.get('name') for p in all_players]
            
            if captain and captain not in player_names:
                errors.append(f"Captain '{captain}' is not in the team")
            if vice_captain and vice_captain not in player_names:
                errors.append(f"Vice-captain '{vice_captain}' is not in the team")
        
        return errors
    
    def _validate_substitutes(self, team_data: Dict[str, Any]) -> List[str]:
        """Validate substitute order"""
        errors = []
        
        if 'team' not in team_data:
            return errors
        
        substitutes = team_data['team'].get('substitutes', [])
        
        # Check for exactly one goalkeeper
        gk_count = sum(1 for p in substitutes if p.get('position') == 'GK')
        if gk_count != 1:
            errors.append(f"Must have exactly 1 goalkeeper on bench, got {gk_count}")
        
        # Check sub order for non-GK players
        sub_orders = []
        for player in substitutes:
            if player.get('position') != 'GK':
                sub_order = player.get('sub_order')
                if sub_order is None:
                    errors.append(f"Player '{player.get('name')}' missing sub_order")
                elif sub_order in sub_orders:
                    errors.append(f"Duplicate sub_order {sub_order}")
                else:
                    sub_orders.append(sub_order)
        
        # Check sub orders are 1, 2, 3
        expected_orders = [1, 2, 3]
        if sorted(sub_orders) != expected_orders:
            errors.append(f"Sub orders should be 1, 2, 3, got {sorted(sub_orders)}")
        
        return errors
    
    def _validate_meta_consistency(self, meta_data: Dict[str, Any], gameweek: int, 
                                 team_data: Dict[str, Any]) -> List[str]:
        """Validate meta.json consistency"""
        errors = []
        
        # Check current gameweek
        meta_gw = meta_data.get('current_gw')
        if meta_gw != gameweek:
            errors.append(f"Meta current_gw ({meta_gw}) doesn't match team gameweek ({gameweek})")
        
        # Check last team file
        expected_file = f"gw{gameweek:02d}.json"
        last_file = meta_data.get('last_team_file')
        if last_file != expected_file:
            errors.append(f"Meta last_team_file ({last_file}) doesn't match expected ({expected_file})")
        
        # Check bank matches team data
        meta_bank = meta_data.get('bank', 0.0)
        team_bank = team_data.get('bank', 0.0)
        if abs(meta_bank - team_bank) > 0.05:
            errors.append(f"Meta bank (£{meta_bank:.1f}m) doesn't match team bank (£{team_bank:.1f}m)")
        
        return errors
    
    def _get_previous_team(self, gameweek: int) -> Optional[Dict[str, Any]]:
        """Get previous team data"""
        if gameweek <= 1:
            return None
        
        prev_file = self.data_dir / f"gw{gameweek-1:02d}.json"
        if not prev_file.exists():
            return None
        
        try:
            with open(prev_file, 'r') as f:
                data = json.load(f)
            return data['team']
        except Exception:
            return None
    
    def _calculate_expected_bank(self, previous_team: Dict[str, Any], 
                               new_team: Dict[str, Any], 
                               transfers: List[Dict[str, str]], 
                               available_players: Dict[str, Dict[str, Any]]) -> float:
        """
        Calculate expected bank based on transfers and price changes
        
        Args:
            previous_team: Previous gameweek team data
            new_team: New team data
            transfers: List of transfers made
            available_players: Current available players with prices
            
        Returns:
            Expected bank value
        """
        # Start with previous bank
        previous_bank = previous_team.get('bank', 0.0)
        expected_bank = previous_bank
        
        # Process transfers
        for transfer in transfers:
            player_out = transfer.get('out')
            player_in = transfer.get('in')
            
            if not player_out or not player_in:
                continue
            
            # Get player prices
            out_price_available = self._get_player_price(player_out, available_players)
            in_price_available = self._get_player_price(player_in, available_players)
            out_price_team = self._get_player_price_in_team(player_out, previous_team)
            
            if out_price_available is None or in_price_available is None or out_price_team is None:
                continue
            
            # Calculate sell price using FPL rule
            sell_price = self._calculate_sell_price(out_price_available, out_price_team)
            
            # Update bank
            expected_bank += sell_price - in_price_available
        
        return expected_bank
    
    def _get_player_price(self, player_name: str, available_players: Dict[str, Dict[str, Any]]) -> Optional[float]:
        """Get player price from available players"""
        for player_data in available_players.values():
            if player_data.get('name') == player_name:
                return player_data.get('price')
        return None
    
    def _get_player_price_in_team(self, player_name: str, team_data: Dict[str, Any]) -> Optional[float]:
        """Get player price from team data"""
        all_players = team_data.get('team', {}).get('starting', []) + team_data.get('team', {}).get('substitutes', [])
        for player in all_players:
            if player.get('name') == player_name:
                return player.get('price')
        return None
    
    def _calculate_sell_price(self, available_price: float, team_price: float) -> float:
        """
        Calculate sell price using FPL rule:
        Transfer Out Price = Available Price + floor((Available Price - Current Price In Team) / 2)
        Rounded down to the nearest £0.1m
        """
        price_diff = available_price - team_price
        adjustment = (price_diff / 2) // 0.1 * 0.1  # Floor to nearest 0.1
        sell_price = available_price + adjustment
        return round(sell_price, 1)  # Round to 1 decimal place


def validate_llm_response(response: str, gameweek: int, available_players: Dict[str, Dict[str, Any]] = None) -> List[str]:
    """
    Validate LLM response for team creation/update
    
    Args:
        response: LLM response string
        gameweek: Current gameweek
        available_players: Available players data (for bank validation)
        
    Returns:
        List of validation errors (empty if valid)
    """
    errors = []
    
    try:
        # Extract JSON from response
        json_start = response.find('{')
        json_end = response.rfind('}') + 1
        
        if json_start == -1 or json_end == 0:
            errors.append("No JSON found in response")
            return errors
        
        json_str = response[json_start:json_end]
        team_data = json.loads(json_str)
        
        # Validate team data
        validator = FPLValidator()
        errors.extend(validator.validate_team_data(team_data, gameweek))
        
        # Validate bank if available players provided
        if available_players and 'transfers' in team_data:
            bank_errors = validator.validate_bank_calculation(
                team_data, gameweek, team_data.get('transfers', []), available_players
            )
            errors.extend(bank_errors)
        
    except json.JSONDecodeError as e:
        errors.append(f"Invalid JSON in response: {str(e)}")
    except Exception as e:
        errors.append(f"Validation failed: {str(e)}")
    
    return errors 