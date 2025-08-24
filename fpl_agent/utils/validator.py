"""
FPL Team Validator
Validates FPL teams against official rules and checks bank calculations
"""

import json
import logging
from typing import Dict, List, Any, Optional
from ..core.config import Config

logger = logging.getLogger(__name__)

class Validator:
    """
    Validates FPL teams against official rules and checks bank calculations

    Args:
        config: Configuration
    """
    
    def __init__(self, config: Config):
        self.config = config
    
    def validate_team_data(self, team_data: Dict[str, Any], budget: float) -> List[str]:
        """
        Validate team data against FPL rules
        
        Args:
            team_data: Team data to validate
            budget: Current budget, team sale value + bank value
            
        Returns:
            List of validation errors (empty if valid)
        """
        errors = []
        
        # Basic structure validation
        errors.extend(self._validate_basic_structure(team_data))
        
        # FPL rules validation
        errors.extend(self._validate_fpl_rules(team_data, budget))
        
        # Formation validation
        errors.extend(self._validate_formation(team_data))
        
        # Captain validation
        errors.extend(self._validate_captain(team_data))
        
        # Substitute order validation
        errors.extend(self._validate_substitutes(team_data))
        
        return errors
    
    def _validate_basic_structure(self, team_data: Dict[str, Any]) -> List[str]:
        """Validate basic team structure
        
        Args:
            team_data: Team data to validate
            
        Returns:
            List of validation errors (empty if valid)
        """
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
    
    def _validate_fpl_rules(self, team_data: Dict[str, Any], budget: float) -> List[str]:
        """Validate FPL rules
        
        Args:
            team_data: Team data to validate
            
        Returns:
            List of validation errors (empty if valid)
        """
        errors = []
        
        if 'team' not in team_data:
            return errors
        
        team = team_data['team']
        all_players = team.get('starting', []) + team.get('substitutes', [])
        
        # Get constraints from config
        position_limits = self.config.get_position_limits()
        squad_size = self.config.get_team_config().get('squad_size', 15)
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

        if total_cost + team_data.get('bank', 0) == budget:
            errors.append(f"Total cost £{total_cost}m exceeds budget of £{budget}m")
        
        return errors
    
    def _validate_formation(self, team_data: Dict[str, Any]) -> List[str]:
        """Validate formation is legal
        
        Args:
            team_data: Team data to validate
            
        Returns:
            List of validation errors (empty if valid)
        """
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
        """Validate captain and vice-captain
        
        Args:
            team_data: Team data to validate
            
        Returns:
            List of validation errors (empty if valid)
        """
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
        """Validate substitute order
        
        Args:
            team_data: Team data to validate
            
        Returns:
            List of validation errors (empty if valid)
        """
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
        """Validate meta.json consistency
        
        Args:
            meta_data: Meta data to validate
            gameweek: Current gameweek
            team_data: Team data to validate
            
        Returns:
            List of validation errors (empty if valid)
        """
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
    
    def validate_bank_calculation(self, team_data: Dict[str, Any], gameweek: int, 
                                transfers: List[Dict[str, str]], previous_team: Dict[str, Any],
                                available_players: Dict[str, Dict[str, Any]]) -> List[str]:
        """
        Validate bank calculation based on transfers and price changes
        
        Args:
            team_data: New team data
            gameweek: Current gameweek
            transfers: List of transfers made
            previous_team: Previous team data
            available_players: Current available players with prices
            
        Returns:
            List of validation errors (empty if valid)
        """
        errors = []
        
        try:
            # Get previous team data
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
        """Get player price from available players
        
        Args:
            player_name: Name of the player
            available_players: Current available players with prices
            
        Returns:
            Player price
        """
        for player_data in available_players.values():
            if player_data.get('name') == player_name:
                return player_data.get('price')
        return None
    
    def _get_player_price_in_team(self, player_name: str, team_data: Dict[str, Any]) -> Optional[float]:
        """Get player price from team data
        
        Args:
            player_name: Name of the player
            team_data: Team data
            
        Returns:
            Player price
        """
        all_players = team_data.get('team', {}).get('starting', []) + team_data.get('team', {}).get('substitutes', [])
        for player in all_players:
            if player.get('name') == player_name:
                return player.get('price')
        return None
    
    def _calculate_sell_price(self, current_price: float, purchase_price: float) -> float:
        """
        Calculate sell price using FPL rule:
        If Current Price > Purchase Price: Transfer Out Price = Purchase Price + floor((Current Price - Purchase Price) / 2)
        Rounded down to the nearest £0.1m
        If Current Price <= Purchase Price: Transfer Out Price = Current Price
        
        Args:
            current_price: Current price of the player
            purchase_price: Purchase price of the player
            
        Returns:
            Sell price
        """
        if current_price > purchase_price:
            price_diff = current_price - purchase_price
            adjustment = (price_diff / 2) // 0.1 * 0.1  # Floor to nearest 0.1
            sell_price = current_price + adjustment
        else:
            sell_price = current_price
        return round(sell_price, 1)  # Round to 1 decimal place
    
    def parse_llm_json_response(self, response: str, raise_on_error: bool = True, 
                               expected_type: str = "any") -> Dict[str, Any]:
        """Parse LLM response to extract JSON data with robust error handling
        
        Args:
            response: The LLM response as a string
            raise_on_error: Whether to raise exceptions on failure (True) or return empty dict (False)
            expected_type: Description of expected response type for logging

        Returns:
            Dictionary with the parsed JSON data
            
        Raises:
            ValueError: If raise_on_error is True and parsing fails
            Exception: If an error occurs during parsing
        """
        try:
            # Debug: Log the raw response
            logger.info(f"Raw LLM response for {expected_type} (length: {len(response)}): {repr(response[:500])}")
            
            # Check if response is an error message
            if response.startswith('Error:'):
                error_msg = f"LLM returned error: {response}"
                logger.error(error_msg)
                if raise_on_error:
                    raise ValueError(error_msg)
                return {}
            
            # Try to extract JSON from the response
            response_text = response.strip()
            
            # Handle markdown code blocks
            if response_text.startswith('```json'):
                response_text = response_text[7:]
            if response_text.endswith('```'):
                response_text = response_text[:-3]
            
            # Extract JSON content between braces (fallback method)
            if not response_text or response_text.find('{') == -1:
                # Try to find JSON content in the response
                json_start = response.find('{')
                json_end = response.rfind('}') + 1
                
                if json_start == -1 or json_end == 0:
                    error_msg = f"No JSON found in response for {expected_type}"
                    logger.error(f"{error_msg}. Response: {response}")
                    if raise_on_error:
                        raise ValueError(error_msg)
                    return {}
                
                response_text = response[json_start:json_end]
            
            # Debug: Log the cleaned response
            logger.info(f"Cleaned response text for {expected_type} (length: {len(response_text)}): {repr(response_text[:500])}")
            
            # Check if response is empty
            if not response_text:
                error_msg = f"Response is empty after cleaning for {expected_type}"
                logger.error(error_msg)
                if raise_on_error:
                    raise ValueError(error_msg)
                return {}
            
            parsed = json.loads(response_text)
            logger.debug(f"Successfully parsed {expected_type} response: {parsed}")
            
            return parsed
            
        except json.JSONDecodeError as e:
            error_msg = f"Failed to parse JSON response for {expected_type}: {e}"
            logger.error(error_msg)
            logger.error(f"JSON string: {response_text if 'response_text' in locals() else 'Not available'}")
            if raise_on_error:
                raise ValueError(error_msg)
            return {}
        except Exception as e:
            error_msg = f"Failed to parse {expected_type} response: {e}"
            logger.error(error_msg)
            logger.error(f"Response that failed to parse: {repr(response)}")
            if raise_on_error:
                raise
            return {} 