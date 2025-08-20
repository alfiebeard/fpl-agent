"""
Prompt formatting utilities for FPL strategies
"""

import logging
from typing import Dict, List, Any

logger = logging.getLogger(__name__)


class PromptFormatter:
    """Utility class for formatting data into LLM prompts"""
    
    @staticmethod
    def format_players_for_llm(players: Dict[str, Dict[str, Any]]) -> str:
        """
        Format player data for LLM prompts.
        
        Args:
            players: Dictionary of player data from data service
            
        Returns:
            Formatted string for LLM prompts
        """
        try:
            # Group players by team
            teams = {}
            for player_id, player in players.items():
                team_name = player.get('team_name', 'Unknown')
                if team_name not in teams:
                    teams[team_name] = []
                teams[team_name].append(player)
            
            # Format the data
            formatted_data = []
            
            for team_name, team_players in sorted(teams.items()):
                formatted_data.append(team_name.upper())
                
                # Sort players by position (GK, DEF, MID, FWD) then by total points
                position_order = {'GK': 0, 'DEF': 1, 'MID': 2, 'FWD': 3}
                sorted_players = sorted(
                    team_players, 
                    key=lambda p: (position_order.get(p.get('position', 'UNK'), 4), -p.get('total_points', 0))
                )
                
                for player in sorted_players:
                    # Get player stats
                    name = player.get('full_name', 'Unknown')
                    position = player.get('position', 'UNK')
                    price = player.get('now_cost', 0) / 10.0  # Convert from FPL price format
                    chance = player.get('chance_of_playing', 100)
                    ppg = float(player.get('points_per_game', '0.0'))
                    form = float(player.get('form', '0.0'))
                    minutes = player.get('minutes', 0)
                    ownership = float(player.get('selected_by_percent', '0.0'))
                    
                    formatted_data.append(
                        f"{name}, {position}, £{price:.1f}, {chance}%, "
                        f"PPG: {ppg:.1f}, Form: {form:.1f}, Mins: {minutes}, "
                        f"Ownership: {ownership:.1f}%"
                    )
                
                formatted_data.append("")  # Empty line between teams
            
            return "\n".join(formatted_data)
            
        except Exception as e:
            logger.error(f"Failed to format players for LLM: {e}")
            return "Error: Could not format player data"
    
    @staticmethod
    def format_current_team_for_prompt(team: Dict) -> str:
        """Format current team data for the prompt"""
        if not team:
            return "No current team data available"
        
        formatted = []
        
        captain = team.get('captain', 'Unknown')
        vice_captain = team.get('vice_captain', 'Unknown')
        
        # Add starting players section
        formatted.append("Starting 11")
        if 'starting' in team:
            for player in team['starting']:
                player_name = player.get('name', 'Unknown')
                position = player.get('position', 'Unknown')
                price = player.get('price', 0.0)
                
                captain_str = ""
                if player_name == captain:
                    captain_str = ", Captain"
                elif player_name == vice_captain:
                    captain_str = ", Vice captain"
                
                formatted.append(f"{player_name}, {position}, £{price}{captain_str}")
        
        # Add substitutes section
        formatted.append("")
        formatted.append("Subs")
        if 'substitutes' in team:
            sub_count = 1
            for player in team['substitutes']:
                player_name = player.get('name', 'Unknown')
                position = player.get('position', 'Unknown')
                price = player.get('price', 0.0)
                sub_order = player.get('sub_order')
                
                if position == 'GK':
                    formatted.append(f"GK. {player_name}, {position}, £{price}")
                else:
                    formatted.append(f"{sub_count}. {player_name}, {position}, £{price}")
                    sub_count += 1
        
        return "\n".join(formatted)
    
    @staticmethod
    def format_chips_for_prompt(chips_data: Dict) -> str:
        """Format available chips for the prompt"""
        available_chips = []
        used_chips = chips_data.get('used', [])
        
        all_chips = ['wildcard', 'bench_boost', 'free_hit', 'triple_captain']
        for chip in all_chips:
            if chip not in [c.get('name') for c in used_chips]:
                available_chips.append(chip)
        
        return ", ".join(available_chips) if available_chips else "none"
    
    @staticmethod
    def get_team_constraints_prompt(config) -> str:
        """Generate team constraints prompt from config"""
        position_limits = config.get_position_limits()
        formation_constraints = config.get_formation_constraints()
        
        return f"""* The squad must include exactly 15 players:
    * {position_limits['GK']} goalkeepers
    * {position_limits['DEF']} defenders
    * {position_limits['MID']} midfielders
    * {position_limits['FWD']} forwards
* The starting 11 must follow valid FPL formations:
    * 1 goalkeeper
    * {formation_constraints['DEF'][0]} to {formation_constraints['DEF'][1]} defenders
    * {formation_constraints['MID'][0]} to {formation_constraints['MID'][1]} midfielders
    * {formation_constraints['FWD'][0]} to {formation_constraints['FWD'][1]} forwards"""
