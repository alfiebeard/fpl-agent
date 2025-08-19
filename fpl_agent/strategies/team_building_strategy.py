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
    
    def create_team(self, budget: float, gameweek: int, 
                    all_gameweek_data: Dict[str, Any], 
                    team_context: Optional[Dict[str, Any]] = None,
                    use_enrichments: bool = False,
                    prompt_only: bool = False) -> Dict[str, Any]:
        """
        Create new team using consolidated data from main.py
        Returns team data (does NOT save)
        """
        try:
            # Extract data from consolidated parameters
            players_data = all_gameweek_data['players']
            fixtures_info = all_gameweek_data['fixtures']
            
            # Create the team creation prompt
            prompt = self._create_team_creation_prompt(
                budget, gameweek, players_data, fixtures_info, team_context, use_enrichments
            )
            
            if prompt_only:
                return {'prompt': prompt}
            
            # Send to LLM
            response = self.llm_engine.query(prompt)
            
            # Parse and validate LLM response
            validator = FPLValidator()
            team_data = validator.parse_team_response(response)
            
            # Validate ONLY team structure (not business logic)
            logger.info("Validating team structure...")
            validation_errors = validator.validate_team_data_comprehensive(team_data, self.config)
            
            if validation_errors:
                error_msg = "Team validation failed:\n" + "\n".join(f"- {error}" for error in validation_errors)
                logger.error(error_msg)
                raise ValueError(error_msg)
            
            # Return team data (NO SAVING)
            return team_data
            
        except Exception as e:
            logger.error(f"Failed to create team: {e}")
            raise
    
    def update_team_weekly(self, team_context: Dict[str, Any], 
                           all_gameweek_data: Dict[str, Any], 
                           use_enrichments: bool = False,
                           prompt_only: bool = False) -> Dict[str, Any]:
        """
        Update team using consolidated data from main.py
        Returns team data (does NOT save or handle business logic)
        """
        try:
            # Extract data from consolidated parameters
            gameweek = team_context['gameweek']
            current_team = team_context['team']
            chips_data = team_context['chips']
            transfers_data = team_context['transfers']
            players_data = all_gameweek_data['players']
            fixtures_info = all_gameweek_data['fixtures']
            
            # Create the weekly update prompt
            prompt = self._create_weekly_update_prompt(
                current_team, gameweek, chips_data, transfers_data, 
                players_data, fixtures_info, use_enrichments
            )
            
            if prompt_only:
                return {'prompt': prompt}
            
            # Send to LLM
            response = self.llm_engine.query(prompt)
            
            # Parse and validate LLM response
            validator = FPLValidator()
            team_data = validator.parse_team_response(response)
            
            # Validate ONLY team structure (not business logic)
            logger.info("Validating team structure...")
            validation_errors = validator.validate_team_data_comprehensive(team_data, self.config)
            
            if validation_errors:
                error_msg = "Team validation failed:\n" + "\n".join(f"- {error}" for error in validation_errors)
                logger.error(error_msg)
                raise ValueError(error_msg)
            
            # Return team data with chip usage info (NO SAVING, NO BUSINESS LOGIC)
            return team_data
            
        except Exception as e:
            logger.error(f"Failed to update team: {e}")
            raise
    
    def _create_team_creation_prompt(self, budget: float, gameweek: int, 
                                    players_data: str, fixtures_info: str,
                                    team_context: Optional[Dict[str, Any]] = None,
                                    use_enrichments: bool = False) -> str:
        """Create the team creation prompt using consolidated data"""
        
        # Get prompt intro based on enrichments flag (not detected from data)
        prompt_intro = self._get_prompt_intro(use_enrichments)
        
        # Get team constraints from prompt formatter
        team_constraints = PromptFormatter.get_team_constraints_prompt(self.config)
        
        return f"""You are a Fantasy Premier League (FPL) team building expert. Your task is to create the optimal FPL team for Gameweek {gameweek}.

CRITICAL INSTRUCTION: You MUST respond with ONLY valid JSON. Do not include any markdown, explanations, or text outside the JSON structure. Your entire response must be a single, valid JSON object.

You must research and analyse the top Fantasy Premier League (FPL) strategies, tips, and recommendations for the upcoming gameweeks. Use a wide range of sources, including expert predictions, blogs, community forums, news articles, fixture difficulty analysis, and pre-season form. Identify underpriced players, strong upcoming fixtures, expected starters, set-piece takers, and hidden value. Your goal is to build the best possible squad for Gameweek {gameweek} and beyond.

You must strictly follow all official FPL rules and constraints when building the team:
* The total budget must not exceed £{budget} million.
{team_constraints}
* A maximum of 3 players are allowed from any single Premier League club.
* Favour players with strong upcoming fixtures and minimal rotation risk.
* Consider potential international absences in the upcoming gameweeks(e.g., AFCON), injury risks, or likely minutes played.

The fixtures this gameweek are:
{fixtures_info}

{prompt_intro}
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

FINAL INSTRUCTION: You MUST respond with ONLY the following JSON format. No other text, no markdown, no explanations outside the JSON:

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

Ensure the final team meets all FPL constraints before submitting:
* Total cost ≤ £{budget}.0 million
* {self.config.get_team_config().get('squad_size', 15)} total players: {self.config.get_position_limits()['GK']} goalkeepers, {self.config.get_position_limits()['DEF']} defenders, {self.config.get_position_limits()['MID']} midfielders, {self.config.get_position_limits()['FWD']} forwards
* Max {self.config.get_position_limits().get('max_players_per_team', 3)} players from any single club
* Valid formation for starting 11 (1GK, {self.config.get_formation_constraints()['DEF'][0]}–{self.config.get_formation_constraints()['DEF'][1]} DEF, {self.config.get_formation_constraints()['MID'][0]}–{self.config.get_formation_constraints()['MID'][1]} MID, {self.config.get_formation_constraints()['FWD'][0]}–{self.config.get_formation_constraints()['FWD'][1]} FWD)

Each player must have a detailed, informative reason for their selection.

REMEMBER: Your response must be ONLY valid JSON. No markdown, no explanations, no text outside the JSON structure."""
    
    def _get_prompt_intro(self, has_enrichments: bool, is_weekly_update: bool = False) -> str:
        """Get the appropriate prompt introduction based on available data"""
        if has_enrichments:
            base_text = """The list of available players by each position, their costs, basic stats, preliminary score, expert insights and injury news are below. You should use this information to make your decisions, but use this as a starting point for wider research and don't only use this. The players are ranked based on a loose scoring system, which takes their expert insights into account using embeddings, you may use this as a starting point if you find it helpful, but don't only use this."""
        else:
            base_text = """The list of available players by each position, their costs and basic stats are below. You should use this information to make your decisions, but use this as a starting point for wider research and don't only use this."""
        
        if is_weekly_update:
            return f"{base_text} You must select the players to transfer in from this list and replace the players in your current team with these players. You cannot transfer in players that are already in your starting 11 or substitutes."
        else:
            return f"{base_text} You must select the players from this list:"
    
    def _create_weekly_update_prompt(self, current_team: Dict, gameweek: int, 
                                   chips_data: Dict, transfers_data: Dict, 
                                   players_data: str, fixtures_info: str,
                                   use_enrichments: bool = False) -> str:
        """Create the weekly update prompt using consolidated data"""
        
        # Format current team for prompt using prompt formatter
        team_str = PromptFormatter.format_current_team_for_prompt(current_team)
        
        # Format available chips using prompt formatter
        chips_str = PromptFormatter.format_chips_for_prompt(chips_data)
        
        # Get prompt intro based on enrichments flag (not detected from data)
        prompt_intro = self._get_prompt_intro(use_enrichments, is_weekly_update=True)
        
        # Get fixtures for the gameweek
        fixtures_info = fixtures_info
        
        return f"""You are managing a Fantasy Premier League (FPL) team with the goal of maximizing points across the season. Your current squad is:
{team_str}

It is now Gameweek {gameweek}.

CRITICAL INSTRUCTION: You MUST respond with ONLY valid JSON. Do not include any markdown, explanations, or text outside the JSON structure. Your entire response must be a single, valid JSON object.

IMPORTANT: If you used a Free Hit chip in the previous gameweek, your team will automatically revert to the team you had before using the Free Hit. The system will handle this revert automatically, so you should proceed with normal transfer planning for this gameweek.

Evaluate your team using the latest information available. Consider:
* Recent player performance and form
* Upcoming fixture difficulty
* Likelihood of starting and playing 90 minutes
* Rotation risk
* Injury or suspension status
* Transfer rumours, international absences, or tactical shifts
* Insights from expert sources, fantasy blogs, forums, news sites, and tipsters

You must research and analyse the top Fantasy Premier League (FPL) strategies, tips, and recommendations for the upcoming gameweeks. Use a wide range of sources, including expert predictions, blogs, community forums, news articles, fixture difficulty analysis, and pre-season form. Identify underpriced players, strong upcoming fixtures, expected starters, set-piece takers, and hidden value. Your goal is to build the best possible squad for Gameweek {gameweek} and beyond.

Use this information to identify the most effective transfers, substitutions, or chip usage for the current and upcoming gameweeks.

The fixtures this gameweek are:
{fixtures_info}

{prompt_intro}
{players_data}

The price of the players in your current team may be different to the price of the players in the list of available players. This is because they could have increased or decreased in price since they were picked. When selling a player you must use the following formula to calculate the sale price:
If Current Price > Purchase Price: Transfer Out Price = Purchase Price + floor((Current Price - Purchase Price) / 2). Rounded down to the nearest £0.1m.
For example, if a player was purchased at £8.0m and the available price is £9.0m, the sale price would be £8.5m.
However, if Current Price <= Purchase Price: Transfer Out Price = Current Price
If a player was purchased at £8.0m but the available price is £7.0m, the sale price would be £7.0m (full loss).

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

FINAL INSTRUCTION: You MUST respond with ONLY the following JSON format. No other text, no markdown, no explanations outside the JSON:

{{
  "chip": null,  // or "wildcard", "bench_boost", "free_hit", "triple_captain"
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
        "team": "Burnley", 
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
* Valid formation for starting 11 (1GK, {self.config.get_formation_constraints()['DEF'][0]}–{self.config.get_formation_constraints()['DEF'][1]} DEF, {self.config.get_formation_constraints()['MID'][0]}–{self.config.get_formation_constraints()['MID'][1]} MID, {self.config.get_formation_constraints()['FWD'][0]}–{self.config.get_formation_constraints()['FWD'][1]} FWD)

Each player must have a detailed, informative reason for their selection.

REMEMBER: Your response must be ONLY valid JSON. No markdown, no explanations, no text outside the JSON structure.""" 