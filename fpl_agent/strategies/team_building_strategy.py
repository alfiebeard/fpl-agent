"""
FPL team manager using LLM for comprehensive team management
"""

import logging
from typing import Dict, Optional, Any

from ..core.config import Config
from ..core.team_manager import TeamManager
from .base_strategy import BaseLLMStrategy
from ..utils.validator import FPLValidator
from ..utils.prompt_formatter import PromptFormatter

logger = logging.getLogger(__name__)


class TeamBuildingStrategy(BaseLLMStrategy):
    """
    LLM-based strategy for FPL team creation and weekly management.
    
    This class handles:
    - Team creation for Gameweek 1 using LLM analysis
    - Weekly team updates and transfers using LLM insights
    - Chip and wildcard management with LLM recommendations
    """
    
    def __init__(self, config: Config):
        super().__init__(config, model_name="main")
        self.team_manager = TeamManager()
    
    def get_strategy_name(self) -> str:
        """Return the name of this strategy."""
        return "Team Building Strategy"
    
    def create_team(self, budget: float = 100.0, gameweek: int = 1, use_semantic_filtering: bool = False, force_refresh: bool = False, use_embeddings: bool = False) -> Dict[str, Any]:
        """
        Create a new FPL team for Gameweek 1 using LLM analysis.
        
        Args:
            budget: Total budget in millions (default: 100.0)
            gameweek: Gameweek to create the team for (defaults to 1)
            use_semantic_filtering: If True, use enriched data with injury news and FPL suggestions
            force_refresh: If True, ignore cache and fetch fresh player data
        Returns:
            Dict containing the created team in the specified JSON format
        """
        logger.info(f"Creating new FPL team with budget £{budget}m for Gameweek {gameweek}")
        
        # Create the team creation prompt
        prompt = self._create_team_creation_prompt(budget, gameweek, use_semantic_filtering, force_refresh, use_embeddings)
        
        # Get LLM response
        logger.info("Querying LLM for team creation...")
        try:
            response = self.llm_engine.query(prompt, use_web_search=True)
            logger.info(f"LLM Response received (length: {len(response)})")
            logger.debug(f"LLM Response preview: {response[:500]}...")
        except Exception as e:
            logger.error(f"Failed to get LLM response: {e}")
            raise
        
        # Parse and validate the response
        logger.info("Parsing LLM response...")
        try:
            validator = FPLValidator()
            team_data = validator.parse_team_response(response)
        except Exception as e:
            logger.error(f"Failed to parse LLM response: {e}")
            logger.error(f"Full LLM response: {response}")
            raise ValueError(f"LLM failed to generate a valid team. Response: {response}")
        
        # Validate the team data
        logger.info("Validating team data...")
        validation_errors = validator.validate_team_data_comprehensive(team_data, self.config)
        
        if validation_errors:
            error_msg = "Team validation failed:\n" + "\n".join(f"- {error}" for error in validation_errors)
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        logger.info(f"Team created successfully with {len(team_data['team']['starting'])} starting players")
        
        # Save the team locally
        self.team_manager.save_team(gameweek, team_data)
        
        # Initialize meta.json with team status
        self.team_manager.initialize_meta(gameweek, team_data)
        
        # Add the raw LLM response to the result for debugging
        team_data['raw_llm_response'] = response
        return team_data
    
    def update_team_weekly(self, gameweek: Optional[int] = None, use_semantic_filtering: bool = False, force_refresh: bool = False, use_embeddings: bool = False) -> Dict[str, Any]:
        """
        Update the current FPL team for the specified gameweek.
        
        Args:
            gameweek: Gameweek to update for (defaults to current gameweek)
            use_semantic_filtering: If True, use enriched data with injury news and FPL suggestions
            force_refresh: If True, ignore cache and fetch fresh player data
            
        Returns:
            Dict containing the updated team in the specified JSON format
        """
        if gameweek is None:
            gameweek = self.data_service.fetcher.get_current_gameweek()
        
        logger.info(f"Updating team for Gameweek {gameweek}")
        
        # Get current meta data to track state
        current_meta = self.team_manager.get_meta()
        
        # Check if this is a free hit revert scenario and handle it first
        if self.team_manager.is_free_hit_revert_scenario(gameweek, current_meta):
            logger.info(f"Free hit revert scenario detected for Gameweek {gameweek}")
            # Handle the revert and get the reverted team
            reverted_team_data = self.team_manager.handle_free_hit_revert(gameweek, current_meta)
            # Get updated meta after revert
            current_meta = self.team_manager.get_meta()
            # Use the reverted team for the prompt
            current_team = reverted_team_data['team']
        else:
            # Check if previous team exists
            previous_team = self.team_manager.get_previous_team(gameweek)
            if not previous_team:
                raise ValueError(f"No team data found for Gameweek {gameweek - 1}. Cannot update team for Gameweek {gameweek}.")
            # Get current team data from local storage
            current_team = previous_team['team']
        
        try:
            # Get available chips and transfers from meta data
            chips_data = self.team_manager.get_available_chips_from_meta(current_meta)
            transfers_data = self.team_manager.get_available_transfers_from_meta(current_meta)
            
            # Create the weekly update prompt
            prompt = self._create_weekly_update_prompt(
                current_team, gameweek, chips_data, transfers_data, use_semantic_filtering, force_refresh, use_embeddings
            )
            
            # Get LLM response
            response = self.llm_engine.query(prompt, use_web_search=True)
            
            # Parse and validate the response
            validator = FPLValidator()
            team_data = validator.parse_team_response(response)
            
            # Check if wildcard or free hit is being used
            chip_used = team_data.get('wildcard_or_chip')
            if chip_used in ['wildcard', 'free_hit']:
                logger.info(f"{chip_used.title()} chip detected - creating new team from scratch")
                return self.team_manager.handle_chip_team_creation(gameweek, chip_used, team_data, self.create_team)
            
            # Validate the team data
            logger.info("Validating team data...")
            validation_errors = validator.validate_team_data_comprehensive(team_data, self.config)
            
            # Validate bank calculation if transfers were made
            if team_data.get('transfers'):
                # Get available players data for bank validation
                available_players = self.data_service.get_available_players_dict()
                
                bank_errors = validator.validate_bank_calculation(
                    team_data, gameweek, team_data.get('transfers', []), available_players
                )
                validation_errors.extend(bank_errors)
            
            if validation_errors:
                error_msg = "Team validation failed:\n" + "\n".join(f"- {error}" for error in validation_errors)
                logger.error(error_msg)
                raise ValueError(error_msg)
            
            # Save the updated team
            self.team_manager.save_team(gameweek, team_data)
            
            # Automatically update meta.json based on the response
            self.team_manager.update_meta_from_response(gameweek, team_data, current_meta)
            
            logger.info(f"Team updated successfully for Gameweek {gameweek}")
            return team_data
            
        except Exception as e:
            logger.error(f"Failed to update team for Gameweek {gameweek}: {e}")
            raise
    
    def _create_team_creation_prompt(self, budget: float, gameweek: int, use_semantic_filtering: bool = False, force_refresh: bool = False, use_embeddings: bool = False) -> str:
        """Create the team creation prompt"""
        
        # Get available players data using data service
        players_data = self.data_service.get_available_players_formatted(use_semantic_filtering, force_refresh, use_embeddings)
        
        # Get team constraints from prompt formatter
        team_constraints = PromptFormatter.get_team_constraints_prompt(self.config)
        
        return f"""You must research and analyse the top Fantasy Premier League (FPL) strategies, tips, and recommendations for the upcoming gameweeks. Use a wide range of sources, including expert predictions, blogs, community forums, news articles, fixture difficulty analysis, and pre-season form. Identify underpriced players, strong upcoming fixtures, expected starters, set-piece takers, and hidden value. Your goal is to build the best possible squad for Gameweek {gameweek} and beyond.

You must strictly follow all official FPL rules and constraints when building the team:
* The total budget must not exceed £{budget} million.
{team_constraints}
* A maximum of 3 players are allowed from any single Premier League club.
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

IMPORTANT: For each player selection, provide a clear, detailed reason explaining:
- Why this player was selected (form, fixtures, value, etc.)
- For starting players: Why they are in the starting 11
- For substitutes: Why they are on the bench and their sub order priority
- For captain: Why they are the best captain choice (fixtures, form, reliability)
- For vice-captain: Why they are the best vice-captain choice

Base your reasoning on the latest expert tips, community insights, and statistical analysis you've researched.

Return the team in the following JSON format:

{{
  "captain": "CAPTAIN NAME",
  "vice_captain": "VICE CAPTAIN NAME",
  "total_cost": {budget}.0,
  "bank": 0.0,
  "expected_points": 65.0,
  "team": {{
    "starting": [
      {{ 
        "name": "Player 1", 
        "position": "MID", 
        "price": 8.5, 
        "team": "Arsenal",
        "reason": "Detailed explanation of why this player was selected for the starting 11, including form, fixtures, value, and expert recommendations"
      }},
      ...
    ],
    "substitutes": [
      {{ 
        "name": "Sub 1", 
        "position": "DEF", 
        "price": 4.5, 
        "team": "Brentford", 
        "sub_order": 1,
        "reason": "Detailed explanation of why this player is on the bench, their sub order priority, and when they would be most useful"
      }},
      {{ 
        "name": "Sub 2", 
        "position": "MID", 
        "price": 5.0, 
        "team": "Burnley", 
        "sub_order": 2,
        "reason": "Detailed explanation of why this player is on the bench, their sub order priority, and when they would be most useful"
      }},
      {{ 
        "name": "Sub 3", 
        "position": "FWD", 
        "price": 5.5, 
        "team": "Wolves", 
        "sub_order": 3,
        "reason": "Detailed explanation of why this player is on the bench, their sub order priority, and when they would be most useful"
      }},
      {{ 
        "name": "Backup Goalkeeper", 
        "position": "GK", 
        "price": 4.0, 
        "team": "Sheffield Utd", 
        "sub_order": null,
        "reason": "Detailed explanation of why this goalkeeper was selected as backup"
      }}
    ]
  }}
}}

Ensure the team meets all FPL rules and constraints before returning the output. Each player must have a detailed, informative reason for their selection."""
    
    def _create_weekly_update_prompt(self, current_team: Dict, gameweek: int, 
                                   chips_data: Dict, transfers_data: Dict, use_semantic_filtering: bool = False, force_refresh: bool = False, use_embeddings: bool = False) -> str:
        """Create the weekly update prompt"""
        
        # Format current team for prompt using prompt formatter
        team_str = PromptFormatter.format_current_team_for_prompt(current_team)
        
        # Format available chips using prompt formatter
        chips_str = PromptFormatter.format_chips_for_prompt(chips_data)
        
        # Get available players data using data service
        players_data = self.data_service.get_available_players_formatted(use_semantic_filtering, force_refresh, use_embeddings)
        
        return f"""You are managing a Fantasy Premier League (FPL) team with the goal of maximizing points across the season. Your current squad is:
{team_str}

It is now Gameweek {gameweek}.

IMPORTANT: If you used a Free Hit chip in the previous gameweek, your team will automatically revert to the team you had before using the Free Hit. The system will handle this revert automatically, so you should proceed with normal transfer planning for this gameweek.

Evaluate your team using the latest information available. Consider:
* Recent player performance and form
* Upcoming fixture difficulty
* Likelihood of starting and playing 90 minutes
* Rotation risk
* Injury or suspension status
* Transfer rumours, international absences, or tactical shifts
* Insights from expert sources, fantasy blogs, forums, news sites, and tipsters

Use this information to identify the most effective transfers, substitutions, or chip usage for the current and upcoming gameweeks.

The list of teams, their available players, the players positions, their costs and their likelihood of playing are below. You must select the players to transfer in from this list and replace the players in your current team with these players. You cannot transfer in players that are already in your starting 11 or substitutes.
{players_data}

The price of the players in your current team may be different to the price of the players in the list of available players. This is because they could have increased or decreased in price since they were picked. When selling a player you must use the following formula to calculate the sale price:
Transfer Out Price = Available Price + floor((Available Price - Current Price In Team) / 2). Rounded down to the nearest £0.1m.
For example, if a player is currently £8.5m in your team and the available price is £9.0m, the sale price would be £8.7m.

This would get added to the bank and is then offset against the cost of the incoming player.

If a player is injured, suspended or has a low likelihood of playing, you must be careful to check the reasoning behind this and if they are not going to play not select them, since this will result in a loss of points.

Transfer rules:
* You have {transfers_data.get('free_transfers', 1)} free transfers this week.
* If unused, 1 transfer can be carried over (maximum 2).
* Additional transfers cost -4 points each, and should only be used if they are likely to generate greater value.
* To make a transfer you must select a player in the starting 11 or substitutes and replace them with a player from the list of available players (excluding players that are already in your starting 11 or substitutes).

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

IMPORTANT: For each decision, provide clear, detailed reasoning explaining:
- **Transfers**: Why each transfer is being made (form, fixtures, injuries, value, etc.)
- **Chip usage**: Why a chip should be used (or not used) this gameweek
- **Captain/Vice-captain**: Why they are the best choices for this gameweek
- **Starting 11**: Why each player is in the starting lineup
- **Substitutes**: Why each player is on the bench and their sub order priority
- **Formation**: Why this formation is optimal for the current fixtures

Base your reasoning on the latest expert tips, community insights, and statistical analysis you've researched.

Remember your team must be built from the current team with only transfers on top, unless you are using a wildcard or chip.

Return your updated squad in this JSON format:

{{
  "wildcard_or_chip": null,  // or "wildcard", "bench_boost", "free_hit", "triple_captain"
  "chip_reason": "Detailed explanation of why this chip is being used (or why no chip is needed)",
  "transfers": [
    {{
      "out": "Player Out Name",
      "in": "Player In Name",
      "reason": "Detailed explanation of why this transfer is being made, including form, fixtures, injuries, value, and expert recommendations"
    }}
    // Multiple allowed if using wildcard or taking points hit
  ],
  "captain": "CAPTAIN NAME",
  "vice_captain": "VICE CAPTAIN NAME",
  "captain_reason": "Detailed explanation of why this player is the best captain choice for this gameweek",
  "vice_captain_reason": "Detailed explanation of why this player is the best vice-captain choice for this gameweek",
  "total_cost": 99.9,
  "bank": 0.1,
  "expected_points": 66.7,
  "team": {{
    "starting": [
      {{ 
        "name": "Player 1", 
        "position": "DEF", 
        "price": 5.5, 
        "team": "Chelsea",
        "reason": "Detailed explanation of why this player is in the starting 11 for this gameweek, including form, fixtures, and tactical considerations"
      }},
      ...
    ],
    "substitutes": [
      {{ 
        "name": "Sub 1", 
        "position": "MID", 
        "price": 5.0, 
        "team": "Brentford", 
        "sub_order": 1,
        "reason": "Detailed explanation of why this player is on the bench, their sub order priority, and when they would be most useful"
      }},
      {{ 
        "name": "Sub 2", 
        "position": "DEF", 
        "price": 4.0, 
        "team": "Luton", 
        "sub_order": 2,
        "reason": "Detailed explanation of why this player is on the bench, their sub order priority, and when they would be most useful"
      }},
      {{ 
        "name": "Sub 3", 
        "position": "FWD", 
        "price": 5.5, 
        "team": "Crystal Palace", 
        "sub_order": 3,
        "reason": "Detailed explanation of why this player is on the bench, their sub order priority, and when they would be most useful"
      }},
      {{ 
        "name": "Backup Goalkeeper", 
        "position": "GK", 
        "price": 4.0, 
        "team": "Burnley", 
        "sub_order": null,
        "reason": "Detailed explanation of why this goalkeeper is the backup choice"
      }}
    ]
  }}
}}

Ensure the final team meets all FPL constraints before submitting:
* Total cost ≤ £100.0 million
* {self.config.get_team_config().get('squad_size', 15)} total players: {self.config.get_position_limits()['GK']} goalkeepers, {self.config.get_position_limits()['DEF']} defenders, {self.config.get_position_limits()['MID']} midfielders, {self.config.get_position_limits()['FWD']} forwards
* Max {self.config.get_team_config().get('max_players_per_team', 3)} players from any single club
* Valid formation for starting 11 (1GK, {self.config.get_formation_constraints()['DEF'][0]}–{self.config.get_formation_constraints()['DEF'][1]} DEF, {self.config.get_formation_constraints()['MID'][0]}–{self.config.get_formation_constraints()['MID'][1]} MID, {self.config.get_formation_constraints()['FWD'][0]}–{self.config.get_formation_constraints()['FWD'][1]} FWD)""" 