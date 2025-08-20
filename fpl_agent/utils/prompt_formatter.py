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
    def format_player(player_data: Dict[str, Any], 
                     format_type: str = "list",
                     include_rankings: bool = False,
                     include_scores: bool = False,
                     include_sale_prices: bool = False,
                     player_index: int = None) -> str:
        """
        Unified player formatter for all scenarios.
        
        Args:
            player_data: Dictionary containing the player's data
            format_type: "list" (player lists), "team" (team display), "detailed" (comprehensive)
            include_rankings: Whether to include ranking numbers
            include_scores: Whether to include embedding scores
            include_sale_prices: Whether to include sale/purchase prices (for team display)
            player_index: Player index for rankings (if include_rankings=True)
            
        Returns:
            Formatted player string with all information
        """
        if not player_data:
            return "Player data not available"
        
        # Build the player information
        player_name = player_data.get('name', player_data.get('full_name', 'Unknown'))
        team_name = player_data.get('team', player_data.get('team_name', 'Unknown'))
        
        # Build complete player string
        formatted_parts = []
        
        # First line: Player name, team, and price info
        if format_type == "team" and include_sale_prices:
            # For team display: include sale and purchase prices
            first_line = f"{player_name} ({team_name}, Transfer Out Price: £{player_data.get('sale_price', 0.0)}m, Purchase Price: £{player_data.get('purchase_price', 0.0)}m)"
        else:
            # For player lists: just current price
            current_price = player_data.get('current_price', player_data.get('now_cost', 0) / 10.0)
            first_line = f"{player_name} ({team_name}, Transfer In Price: £{current_price:.1f}m)"
        
        # Add ranking prefix if requested
        if include_rankings and player_index is not None:
            first_line = f"{player_index:2d}. {first_line}"
        elif include_rankings:
            first_line = f"• {first_line}"
        
        formatted_parts.append(first_line)
        
        # Second line: Stats section
        ppg = player_data.get('form', 0.0)
        form = player_data.get('form', 0.0)
        total_points = player_data.get('total_points', 0)
        minutes = player_data.get('minutes', 0)
        ownership = player_data.get('selected_by_percent', 0.0)
        chance = player_data.get('chance_of_playing', 100)
        
        stats_line = f"[STATS] PPG: {ppg}, Form: {form}, Total Points: {total_points}, Minutes: {minutes}, Ownership: {ownership}%, Chance: {chance}%"
        formatted_parts.append(stats_line)
        
        # Add score line (if requested and available)
        if include_scores and format_type == "detailed":
            embedding_score = player_data.get('embedding_score', 0.0)
            keyword_bonus = player_data.get('keyword_bonus', 0.0)
            hybrid_score = embedding_score + keyword_bonus
            
            score_line = f"[SCORE]: {hybrid_score:.3f} (Embedding: {embedding_score:.3f}, Bonus: {keyword_bonus:+.3f})"
            formatted_parts.append(score_line)
        
        # Add expert insights (if available)
        if player_data.get('expert_insights') and player_data['expert_insights'] != 'None':
            formatted_parts.append(f"[EXPERT INSIGHTS]: {player_data['expert_insights']}")
        
        # Add injury news (if available)
        if player_data.get('injury_news') and player_data['injury_news'] != 'None':
            formatted_parts.append(f"[INJURY NEWS]: {player_data['injury_news']}")
        
        return "\n".join(formatted_parts)
    
    @staticmethod
    def format_current_team_for_prompt(team: Dict, team_player_data: Dict) -> str:
        """Format current team data for the prompt with enhanced player information"""
        if not team:
            return "No current team data available"
        
        formatted = []
        
        captain = team.get('captain', 'Unknown')
        vice_captain = team.get('vice_captain', 'Unknown')
        
        # Add starting players section
        formatted.append("Starting 11")
        formatted.append("")  # Empty line for spacing
        if 'starting' in team:
            for player in team['starting']:
                player_name = player.get('name', 'Unknown')
                
                # Format player with enhanced data (include sale prices)
                if player_name in team_player_data:
                    player_info = PromptFormatter.format_player(
                        team_player_data[player_name], 
                        format_type="team",
                        include_sale_prices=True
                    )
                else:
                    player_info = f"{player_name} (Data not available)"
                
                # Add captain/vice captain indicators to the first line
                lines = player_info.split('\n')
                if player_name == captain:
                    lines[0] += " (Captain)"
                elif player_name == vice_captain:
                    lines[0] += " (Vice Captain)"
                player_info = '\n'.join(lines)
                
                formatted.append(player_info)
                formatted.append("")  # Add spacing between players
        
        # Add substitutes section
        formatted.append("Substitutes")
        formatted.append("")  # Empty line for spacing
        if 'substitutes' in team:
            sub_count = 1
            for player in team['substitutes']:
                player_name = player.get('name', 'Unknown')
                position = player.get('position', 'Unknown')
                
                # Format player with enhanced data (include sale prices)
                if player_name in team_player_data:
                    player_info = PromptFormatter.format_player(
                        team_player_data[player_name], 
                        format_type="team",
                        include_sale_prices=True
                    )
                else:
                    player_info = f"{player_name} (Data not available)"
                
                # Add sub order to first line
                lines = player_info.split('\n')
                if position == 'GK':
                    lines[0] = f"GK. {lines[0]}"
                else:
                    lines[0] = f"{sub_count}. {lines[0]}"
                player_info = '\n'.join(lines)
                
                formatted.append(player_info)
                formatted.append("")  # Add spacing between players
                
                if position != 'GK':
                    sub_count += 1
        

    
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
