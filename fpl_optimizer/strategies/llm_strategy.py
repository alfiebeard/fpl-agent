"""
FPL team manager using LLM for comprehensive team management
"""

import logging
import json
from typing import Dict, Optional, Any

from ..config import Config
from ..ingestion.fetch_fpl import FPLDataFetcher
from .llm_engine import LLMEngine
from ..utils.data_transformers import transform_fpl_data_to_teams
from ..models import Position

logger = logging.getLogger(__name__)


class LLMStrategy:
    """
    LLM-based strategy for FPL team creation and weekly management.
    
    This class handles:
    - Team creation for Gameweek 1 using LLM analysis
    - Weekly team updates and transfers using LLM insights
    - Chip and wildcard management with LLM recommendations
    - Integration with FPL API for current team data
    """
    
    def __init__(self, config: Config):
        self.config = config
        self.fpl_fetcher = FPLDataFetcher(config)
        self.llm_engine = LLMEngine(config)
        self.team_id = config.get('fpl.team_id')
        
        if not self.team_id:
            logger.warning("No FPL team ID configured. Weekly updates will not work.")
    
    def _get_available_players_data(self) -> str:
        """
        Get available players data formatted for LLM prompts.
        
        Returns:
            String containing all available players organized by team
        """
        logger.info("Fetching and formatting available players data...")
        
        try:
            # Fetch FPL data
            bootstrap_data = self.fpl_fetcher.get_bootstrap_data()
            
            # Apply filters for available players only
            filters = {
                'exclude_injured': True,      # Exclude injured players
                'exclude_unavailable': True,  # Exclude unavailable players
                'min_chance_of_playing': 25,  # Only players with >25% chance of playing
                'min_minutes': 0,             # Include all players regardless of minutes
                'max_price': float('inf'),    # No price limit
                'min_form': float('-inf'),    # No form minimum
                'positions': [Position.GK, Position.DEF, Position.MID, Position.FWD]  # All positions
            }
            
            # Transform data
            teams = transform_fpl_data_to_teams(bootstrap_data, filters)
            
            # Format the data
            formatted_data = []
            
            for team_name, team_summary in sorted(teams.items()):
                formatted_data.append(team_name.upper())
                
                # Sort players by position (GK, DEF, MID, FWD) then by total points
                position_order = {'GK': 0, 'DEF': 1, 'MID': 2, 'FWD': 3}
                sorted_players = sorted(
                    team_summary.players, 
                    key=lambda p: (position_order.get(p.position.value, 4), -p.total_points)
                )
                
                for player in sorted_players:
                    # Get chance of playing as raw percentage (or "100%" if missing during off-season)
                    chance_of_playing = player.custom_data.get('chance_of_playing')
                    if chance_of_playing is None:
                        chance_str = "100%"  # Available (default during off-season)
                    else:
                        chance_str = f"{chance_of_playing}%"
                    
                    formatted_data.append(
                        f"{player.name}, {player.position.value}, £{player.price}, {chance_str}"
                    )
                
                formatted_data.append("")  # Empty line between teams
            
            return "\n".join(formatted_data)
            
        except Exception as e:
            logger.error(f"Failed to get available players data: {e}")
            return "Error: Could not fetch player data"
    
    def create_team(self, budget: float = 100.0, gameweek: int = 1) -> Dict[str, Any]:
        """
        Create a new FPL team for Gameweek 1 using LLM analysis.
        
        Args:
            budget: Total budget in millions (default: 100.0)
            gameweek: Gameweek to create the team for (defaults to 1)
        Returns:
            Dict containing the created team in the specified JSON format
        """
        logger.info(f"Creating new FPL team with budget £{budget}m for Gameweek {gameweek}")
        
        # Create the team creation prompt
        prompt = self._create_team_creation_prompt(budget, gameweek)
        
        # Get LLM response
        logger.info("Querying LLM for team creation...")
        try:
            response = self.llm_engine._query_gemini_with_search(prompt)
            logger.info(f"LLM Response received (length: {len(response)})")
            logger.debug(f"LLM Response preview: {response[:500]}...")
        except Exception as e:
            logger.error(f"Failed to get LLM response: {e}")
            raise
        
        # Parse and validate the response
        logger.info("Parsing LLM response...")
        try:
            team_data = self._parse_team_response(response)
        except Exception as e:
            logger.error(f"Failed to parse LLM response: {e}")
            logger.error(f"Full LLM response: {response}")
            raise ValueError(f"LLM failed to generate a valid team. Response: {response}")
        
        logger.info(f"Team created successfully with {len(team_data['team']['starting'])} starting players")
        
        # Add the raw LLM response to the result for debugging
        team_data['raw_llm_response'] = response
        return team_data
    
    def update_team_weekly(self, gameweek: Optional[int] = None) -> Dict[str, Any]:
        """
        Update the current FPL team for the specified gameweek.
        
        Args:
            gameweek: Gameweek to update for (defaults to current gameweek)
            
        Returns:
            Dict containing the updated team in the specified JSON format
        """
        if not self.team_id:
            raise ValueError("FPL team ID not configured. Cannot update team.")
        
        if gameweek is None:
            gameweek = self.fpl_fetcher.get_current_gameweek()
        
        logger.info(f"Updating team for Gameweek {gameweek}")
        
        # Get current team data
        current_team = self._get_current_team_data(gameweek)
        
        # Get available chips and transfers
        chips_data = self._get_available_chips()
        transfers_data = self._get_available_transfers()
        
        # Create the weekly update prompt
        prompt = self._create_weekly_update_prompt(
            current_team, gameweek, chips_data, transfers_data
        )
        
        # Get LLM response
        response = self.llm_engine._query_gemini_with_search(prompt)
        
        # Parse and validate the response
        team_data = self._parse_team_response(response)
        
        logger.info(f"Team updated successfully for Gameweek {gameweek}")
        return team_data
    
    def _create_team_creation_prompt(self, budget: float, gameweek: int) -> str:
        """Create the team creation prompt"""
        
        # Get available players data
        players_data = self._get_available_players_data()
        
        return f"""You must research and analyse the top Fantasy Premier League (FPL) strategies, tips, and recommendations for the upcoming gameweeks. Use a wide range of sources, including expert predictions, blogs, community forums, news articles, fixture difficulty analysis, and pre-season form. Identify underpriced players, strong upcoming fixtures, expected starters, set-piece takers, and hidden value. Your goal is to build the best possible squad for Gameweek {gameweek} and beyond.

You must strictly follow all official FPL rules and constraints when building the team:
* The total budget must not exceed £{budget} million.
* The squad must include exactly 15 players:
    * 2 goalkeepers
    * 5 defenders
    * 5 midfielders
    * 3 forwards
* A maximum of 3 players are allowed from any single Premier League club.
* The starting 11 must follow valid FPL formations:
    * 1 goalkeeper
    * 3 to 5 defenders
    * 2 to 5 midfielders
    * 1 to 3 forwards
* Favour players with strong upcoming fixtures and minimal rotation risk.
* Consider potential international absences in the upcoming gameweeks(e.g., AFCON), injury risks, or likely minutes played.

The list of teams, their available players, the players positions, their costs and their likelihood of playing are below. You must select the players from this list:
{players_data}

If a player is injured, suspended or has a low likelihood of playing, you must be careful to check the reasoning behind this and if they are not going to play not select them, since this will result in a loss of points.

Once the squad is selected:
1. Choose a starting 11 based on expected Gameweek {gameweek} performance and the upcoming gameweeks.
2. Rank the 4 substitutes in expected points order: Sub 1 (highest priority), Sub 2, Sub 3, and the backup goalkeeper.
3. Select a captain with the highest expected points and a strong fixture.
4. Select a vice-captain who is a reliable starter with good expected value.

Return the team in the following JSON format:

{{
  "captain": "CAPTAIN NAME",
  "vice_captain": "VICE CAPTAIN NAME",
  "total_cost": {budget}.0,
  "bank": 0.0,
  "expected_points": 65.0,
  "team": {{
    "starting": [
      {{ "name": "Player 1", "position": "MID", "price": 8.5, "team": "Arsenal" }},
      ...
    ],
    "substitutes": [
      {{ "name": "Sub 1", "position": "DEF", "price": 4.5, "team": "Brentford", "sub_order": 1 }},
      {{ "name": "Sub 2", "position": "MID", "price": 5.0, "team": "Burnley", "sub_order": 2 }},
      {{ "name": "Sub 3", "position": "FWD", "price": 5.5, "team": "Wolves", "sub_order": 3 }},
      {{ "name": "Backup Goalkeeper", "position": "GK", "price": 4.0, "team": "Sheffield Utd", "sub_order": null }}
    ]
  }}
}}

Ensure the team meets all FPL rules and constraints before returning the output."""
    
    def _create_weekly_update_prompt(self, current_team: Dict, gameweek: int, 
                                   chips_data: Dict, transfers_data: Dict) -> str:
        """Create the weekly update prompt"""
        
        # Format current team for prompt
        team_str = self._format_current_team_for_prompt(current_team)
        
        # Format available chips
        chips_str = self._format_chips_for_prompt(chips_data)
        
        # Get available players data
        players_data = self._get_available_players_data()
        
        return f"""You are managing a Fantasy Premier League (FPL) team with the goal of maximizing points across the season. Your current squad is:
{team_str}

It is now Gameweek {gameweek}.

Evaluate your team using the latest information available. Consider:
* Recent player performance and form
* Upcoming fixture difficulty
* Likelihood of starting and playing 90 minutes
* Rotation risk
* Injury or suspension status
* Transfer rumours, international absences, or tactical shifts
* Insights from expert sources, fantasy blogs, forums, news sites, and tipsters

Use this information to identify the most effective transfers, substitutions, or chip usage for the current and upcoming gameweeks.

The list of teams, their available players, the players positions, their costs and their likelihood of playing are below. You must select the players from this list:
{players_data}

If a player is injured, suspended or has a low likelihood of playing, you must be careful to check the reasoning behind this and if they are not going to play not select them, since this will result in a loss of points.

Transfer rules:
* You have {transfers_data.get('free_transfers', 1)} free transfers this week.
* If unused, 1 transfer can be carried over (maximum 2).
* Additional transfers cost -4 points each, and should only be used if they are likely to generate greater value.

You also have access to the following chips and wildcards: {chips_str}

Chip and wildcard rules:
* You can use one chip or wildcard per gameweek.
* First half of season (GW1–19): 1 wildcard + 1 of each chip (Triple Captain, Bench Boost, Free Hit)
* Second half (GW20+): another wildcard + reset of each chip
* Chips:
    * Wildcard: unlimited free transfers for the current week (permanent team change)
    * Free Hit: unlimited free transfers this gameweek only (team reverts next week)
    * Bench Boost: all 15 players score points
    * Triple Captain: captain's points are tripled instead of doubled

If you plan to use a chip or wildcard this week, clearly state which one. If using Wildcard or Free Hit, you may omit transfers (since they are handled via chip activation).

After completing your analysis:
1. Decide whether to use a wildcard or chip
2. List transfers (if any)
3. Return the final team:
    * Valid formation
    * Bench ordered by expected points
    * Captain and vice-captain optimised for expected value

Return your updated squad in this JSON format:

{{
  "wildcard_or_chip": null,  // or "wildcard", "bench_boost", "free_hit", "triple_captain"
  "transfers": [
    {{
      "out": "Player Out Name",
      "in": "Player In Name",
      "reason": "Optional short explanation for the transfer"
    }}
    // Multiple allowed if using wildcard or taking points hit
  ],
  "captain": "CAPTAIN NAME",
  "vice_captain": "VICE CAPTAIN NAME",
  "total_cost": 99.9,
  "bank": 0.1,
  "expected_points": 66.7,
  "team": {{
    "starting": [
      {{ "name": "Player 1", "position": "DEF", "price": 5.5, "team": "Chelsea" }},
      ...
    ],
    "substitutes": [
      {{ "name": "Sub 1", "position": "MID", "price": 5.0, "team": "Brentford", "sub_order": 1 }},
      {{ "name": "Sub 2", "position": "DEF", "price": 4.0, "team": "Luton", "sub_order": 2 }},
      {{ "name": "Sub 3", "position": "FWD", "price": 5.5, "team": "Crystal Palace", "sub_order": 3 }},
      {{ "name": "Backup Goalkeeper", "position": "GK", "price": 4.0, "team": "Burnley", "sub_order": null }}
    ]
  }}
}}

Ensure the final team meets all FPL constraints before submitting:
* Total cost ≤ £100.0 million
* 15 total players: 2 goalkeepers, 5 defenders, 5 midfielders, 3 forwards
* Max 3 players from any single club
* Valid formation for starting 11 (1GK, 3–5 DEF, 2–5 MID, 1–3 FWD)"""
    

    
    def _format_current_team_for_prompt(self, team_data: Dict) -> str:
        """Format current team data for the prompt"""
        if not team_data:
            return "No current team data available"
        
        formatted = []
        for pick in team_data.get('picks', []):
            player_name = pick.get('element', 'Unknown')
            position = pick.get('position', 'Unknown')
            is_captain = pick.get('is_captain', False)
            is_vice_captain = pick.get('is_vice_captain', False)
            
            captain_str = ""
            if is_captain:
                captain_str = " (C)"
            elif is_vice_captain:
                captain_str = " (VC)"
            
            formatted.append(f"{player_name} - {position}{captain_str}")
        
        return "\n".join(formatted)
    
    def _format_chips_for_prompt(self, chips_data: Dict) -> str:
        """Format available chips for the prompt"""
        available_chips = []
        used_chips = chips_data.get('used', [])
        
        all_chips = ['wildcard', 'bench_boost', 'free_hit', 'triple_captain']
        for chip in all_chips:
            if chip not in [c.get('name') for c in used_chips]:
                available_chips.append(chip)
        
        return ", ".join(available_chips) if available_chips else "none"
    
    def _format_transfers_for_prompt(self, transfers_data: Dict) -> str:
        """Format available transfers for the prompt"""
        free_transfers = transfers_data.get('free_transfers', 1)
        return f"{free_transfers} free transfer{'s' if free_transfers != 1 else ''}"
    

    
    def _get_current_team_data(self, gameweek: int) -> Dict[str, Any]:
        """Get current team data for the specified gameweek"""
        try:
            return self.fpl_fetcher.get_user_team_picks(self.team_id, gameweek)
        except Exception as e:
            logger.error(f"Failed to get current team data: {e}")
            return {}
    
    def _get_available_chips(self) -> Dict[str, Any]:
        """Get available chips information"""
        try:
            chips = self.fpl_fetcher.get_user_chips(self.team_id)
            return {
                'used': chips,
                'available': ['wildcard', 'bench_boost', 'free_hit', 'triple_captain']
            }
        except Exception as e:
            logger.error(f"Failed to get chips data: {e}")
            return {'used': [], 'available': []}
    
    def _get_available_transfers(self) -> Dict[str, Any]:
        """Get available transfers information"""
        try:
            team_data = self.fpl_fetcher.get_team_data(self.team_id)
            return {
                'free_transfers': team_data.get('transfers', 1),
                'bank': team_data.get('summary_event_points', 0)
            }
        except Exception as e:
            logger.error(f"Failed to get transfers data: {e}")
            return {'free_transfers': 1, 'bank': 0}
    
    def _parse_team_response(self, response: str) -> Dict[str, Any]:
        """Parse the LLM response into team data"""
        try:
            # Extract JSON from the response
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            
            if json_start == -1 or json_end == 0:
                logger.error(f"No JSON found in response. Response: {response}")
                raise ValueError("No JSON found in response")
            
            json_str = response[json_start:json_end]
            logger.debug(f"Extracted JSON: {json_str}")
            
            team_data = json.loads(json_str)
            logger.debug(f"Parsed team data: {team_data}")
            
            # Validate the team data
            self._validate_team_data(team_data)
            
            return team_data
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            logger.error(f"JSON string: {json_str if 'json_str' in locals() else 'Not available'}")
            raise ValueError(f"Invalid JSON response: {e}")
        except Exception as e:
            logger.error(f"Failed to parse team response: {e}")
            logger.error(f"Response: {response}")
            raise
    
    def _validate_team_data(self, team_data: Dict[str, Any]) -> None:
        """Validate that the team data meets FPL constraints"""
        # Basic structure validation
        required_keys = ['captain', 'vice_captain', 'total_cost', 'bank', 'team']
        for key in required_keys:
            if key not in team_data:
                raise ValueError(f"Missing required key: {key}")
        
        team = team_data['team']
        if 'starting' not in team or 'substitutes' not in team:
            raise ValueError("Team must have 'starting' and 'substitutes' sections")
        
        # Count players
        starting = team['starting']
        substitutes = team['substitutes']
        
        if len(starting) != 11:
            raise ValueError(f"Must have exactly 11 starting players, got {len(starting)}")
        
        if len(substitutes) != 4:
            raise ValueError(f"Must have exactly 4 substitutes, got {len(substitutes)}")
        
        # Check budget
        total_cost = team_data['total_cost']
        if total_cost > 100.0:
            raise ValueError(f"Total cost £{total_cost}m exceeds budget of £100.0m")
        
        # Check team composition (basic validation)
        all_players = starting + substitutes
        gk_count = sum(1 for p in all_players if p.get('position') == 'GK')
        def_count = sum(1 for p in all_players if p.get('position') == 'DEF')
        mid_count = sum(1 for p in all_players if p.get('position') == 'MID')
        fwd_count = sum(1 for p in all_players if p.get('position') == 'FWD')
        
        if gk_count != 2:
            raise ValueError(f"Must have exactly 2 goalkeepers, got {gk_count}")
        if def_count != 5:
            raise ValueError(f"Must have exactly 5 defenders, got {def_count}")
        if mid_count != 5:
            raise ValueError(f"Must have exactly 5 midfielders, got {mid_count}")
        if fwd_count != 3:
            raise ValueError(f"Must have exactly 3 forwards, got {fwd_count}")
        
        logger.info("Team data validation passed")
    
 