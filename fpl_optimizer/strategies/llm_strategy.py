"""
FPL team manager using LLM for comprehensive team management
"""

import logging
import json
import os
from typing import Dict, Optional, Any, List
from pathlib import Path
from datetime import datetime, timedelta

from ..core.config import Config
from ..ingestion.fetch_fpl import FPLDataFetcher
from ..core.team_manager import TeamManager
from .llm_engine import LLMEngine
from .lightweight_llm_strategy import LightweightLLMStrategy
from .embedding_filter import EmbeddingFilter
from ..utils.data_transformers import transform_fpl_data_to_teams
from ..utils.validator import FPLValidator, validate_llm_response
from ..core.models import Position

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
        self.team_manager = TeamManager()
        self.llm_engine = LLMEngine(config)
        self.embedding_filter = None  # Lazy initialization
    
    def _get_player_data_cache_path(self) -> Path:
        """Get the path to the player data cache file"""
        cache_dir = Path("team_data")
        cache_dir.mkdir(exist_ok=True)
        return cache_dir / "player_data.json"
    
    def _load_cached_player_data(self) -> Optional[Dict[str, Any]]:
        """
        Load cached player data from JSON file.
        
        Returns:
            Cached player data or None if not available
        """
        cache_path = self._get_player_data_cache_path()
        
        if not cache_path.exists():
            logger.info("No cached player data found")
            return None
        
        try:
            with open(cache_path, 'r', encoding='utf-8') as f:
                cached_data = json.load(f)
            
            # Check if cache has timestamp for age calculation
            cache_timestamp = cached_data.get('cache_timestamp')
            if cache_timestamp:
                cache_time = datetime.fromisoformat(cache_timestamp)
                age_hours = (datetime.now() - cache_time).total_seconds() / 3600
                
                if age_hours > 24:
                    warning_msg = f"⚠️  Using cached player data that is {age_hours:.1f} hours old. Consider using --force-refresh for fresh data."
                    logger.warning(warning_msg)
                    print(f"\n{warning_msg}")
                else:
                    logger.info(f"Using cached player data ({age_hours:.1f} hours old)")
                
                return cached_data
            else:
                warning_msg = "⚠️  Using cached player data with unknown age. Consider using --force-refresh for fresh data."
                logger.warning(warning_msg)
                print(f"\n{warning_msg}")
                return cached_data
            
        except Exception as e:
            logger.error(f"Failed to load cached player data: {e}")
            return None
    
    def _save_player_data_cache(self, player_data: Dict[str, str]) -> None:
        """
        Save player data to cache file.
        
        Args:
            player_data: Dictionary of enriched player data
        """
        cache_path = self._get_player_data_cache_path()
        
        try:
            cache_data = {
                'cache_timestamp': datetime.now().isoformat(),
                'player_data': player_data,
                'total_players': len(player_data)
            }
            
            with open(cache_path, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Saved player data cache with {len(player_data)} players to {cache_path}")
            
        except Exception as e:
            logger.error(f"Failed to save player data cache: {e}")
    
    def _get_cached_enriched_player_data(self) -> Optional[Dict[str, str]]:
        """
        Get enriched player data from cache if available.
        
        Returns:
            Cached enriched player data or None if not available
        """
        cached_data = self._load_cached_player_data()
        if cached_data:
            return cached_data.get('player_data', {})
        return None

    def _get_available_players_data(self, use_semantic_filtering: bool = False, force_refresh: bool = False, use_embeddings: bool = False) -> str:
        """
        Get available players data formatted for LLM prompts.
        
        Args:
            use_semantic_filtering: If True, use enriched data with injury news and FPL suggestions
            force_refresh: If True, ignore cache and fetch fresh data (only applies when use_semantic_filtering=True)
            
        Returns:
            String containing all available players organized by team
        """
        logger.info("Fetching and formatting available players data...")
        
        if use_semantic_filtering:
            if use_embeddings:
                logger.info("Using semantic filtering with enriched player data AND embedding filtering")
                return self._get_available_players_data_enriched_filtered(force_refresh=force_refresh)
            else:
                logger.info("Using semantic filtering with enriched player data (no embedding filtering)")
                return self._get_available_players_data_enriched(force_refresh=force_refresh)
        
        try:
            # Fetch FPL data with additional stats
            all_data = self.fpl_fetcher.get_all_data_with_additional_stats()
            players = all_data['players']
            
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
            
            # Filter players based on criteria
            available_players = []
            for player in players:
                # Check if player meets filter criteria
                if (not player.is_injured and 
                    player.custom_data.get('chance_of_playing', 100) >= filters['min_chance_of_playing'] and
                    player.position in filters['positions'] and
                    player.price <= filters['max_price'] and
                    player.form >= filters['min_form']):
                    available_players.append(player)
            
            # Group players by team
            teams = {}
            for player in available_players:
                team_name = player.team_name
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
                    key=lambda p: (position_order.get(p.position.value, 4), -p.total_points)
                )
                
                for player in sorted_players:
                    # Get chance of playing as raw percentage (or "100%" if missing during off-season)
                    chance_of_playing = player.custom_data.get('chance_of_playing')
                    if chance_of_playing is None:
                        chance_str = "100%"  # Available (default during off-season)
                    else:
                        chance_str = f"{chance_of_playing}%"
                    
                    # Get additional stats
                    ppg = player.custom_data.get('ppg', player.points_per_game)
                    form = player.custom_data.get('form', player.form)
                    minutes = player.custom_data.get('minutes_played', player.minutes_played)
                    fixture_difficulty = player.custom_data.get('upcoming_fixture_difficulty', 3.0)
                    ownership = player.custom_data.get('ownership_percent', player.selected_by_pct)
                    
                    formatted_data.append(
                        f"{player.name}, {player.position.value}, £{player.price}, {chance_str}, "
                        f"PPG: {ppg:.1f}, Form: {form:.1f}, Mins: {minutes}, "
                        f"Fixture Diff: {fixture_difficulty}, Ownership: {ownership:.1f}%"
                    )
                
                formatted_data.append("")  # Empty line between teams
            
            return "\n".join(formatted_data)
            
        except Exception as e:
            logger.error(f"Failed to get available players data: {e}")
            return "Error: Could not fetch player data"
    
    def _get_available_players_dict(self, bootstrap_data: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
        """
        Get available players data as a dictionary for validation.
        
        Args:
            bootstrap_data: Raw FPL bootstrap data
            
        Returns:
            Dictionary of players with their data
        """
        try:
            # Apply filters for available players only
            filters = {
                'exclude_injured': True,
                'exclude_unavailable': True,
                'min_chance_of_playing': 25,
                'min_minutes': 0,
                'max_price': float('inf'),
                'min_form': float('-inf'),
                'positions': [Position.GK, Position.DEF, Position.MID, Position.FWD]
            }
            
            # Transform data
            teams = transform_fpl_data_to_teams(bootstrap_data, filters)
            
            # Convert to dictionary format
            players_dict = {}
            for team_name, team_summary in teams.items():
                for player in team_summary.players:
                    players_dict[player.name] = {
                        'name': player.name,
                        'position': player.position.value,
                        'price': player.price,
                        'team': team_name
                    }
            
            return players_dict
            
        except Exception as e:
            logger.error(f"Failed to get available players dict: {e}")
            return {}
    
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
        
        # Validate the team data
        logger.info("Validating team data...")
        validator = FPLValidator()
        validation_errors = validator.validate_team_data(team_data, gameweek)
        
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
            gameweek = self.fpl_fetcher.get_current_gameweek()
        
        logger.info(f"Updating team for Gameweek {gameweek}")
        
        # Get current meta data to track state
        current_meta = self.team_manager.get_meta()
        
        # Check if this is a free hit revert scenario and handle it first
        if self._is_free_hit_revert_scenario(gameweek, current_meta):
            logger.info(f"Free hit revert scenario detected for Gameweek {gameweek}")
            # Handle the revert and get the reverted team
            reverted_team_data = self._handle_free_hit_revert(gameweek, current_meta)
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
            chips_data = self._get_available_chips_from_meta(current_meta)
            transfers_data = self._get_available_transfers_from_meta(current_meta)
            
            # Create the weekly update prompt
            prompt = self._create_weekly_update_prompt(
                current_team, gameweek, chips_data, transfers_data, use_semantic_filtering, force_refresh, use_embeddings
            )
            
            # Get LLM response
            response = self.llm_engine._query_gemini_with_search(prompt)
            
            # Parse and validate the response
            team_data = self._parse_team_response(response)
            
            # Check if wildcard or free hit is being used
            chip_used = team_data.get('wildcard_or_chip')
            if chip_used in ['wildcard', 'free_hit']:
                logger.info(f"{chip_used.title()} chip detected - creating new team from scratch")
                return self._handle_chip_team_creation(gameweek, chip_used, team_data)
            
            # Validate the team data
            logger.info("Validating team data...")
            validator = FPLValidator()
            validation_errors = validator.validate_team_data(team_data, gameweek)
            
            # Validate bank calculation if transfers were made
            if team_data.get('transfers'):
                # Get available players data for bank validation
                bootstrap_data = self.fpl_fetcher.get_bootstrap_data()
                available_players = self._get_available_players_dict(bootstrap_data)
                
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
            self._update_meta_from_response(gameweek, team_data, current_meta)
            
            logger.info(f"Team updated successfully for Gameweek {gameweek}")
            return team_data
            
        except Exception as e:
            logger.error(f"Failed to update team for Gameweek {gameweek}: {e}")
            raise
    
    def _create_team_creation_prompt(self, budget: float, gameweek: int, use_semantic_filtering: bool = False, force_refresh: bool = False, use_embeddings: bool = False) -> str:
        """Create the team creation prompt"""
        
        # Get available players data
        players_data = self._get_available_players_data(use_semantic_filtering, force_refresh, use_embeddings)
        
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
        
        # Format current team for prompt
        team_str = self._format_current_team_for_prompt(current_team)
        
        # Format available chips
        chips_str = self._format_chips_for_prompt(chips_data)
        
        # Get available players data
        players_data = self._get_available_players_data(use_semantic_filtering, force_refresh, use_embeddings)
        
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
* 15 total players: 2 goalkeepers, 5 defenders, 5 midfielders, 3 forwards
* Max 3 players from any single club
* Valid formation for starting 11 (1GK, 3–5 DEF, 2–5 MID, 1–3 FWD)"""
    
    def _format_current_team_for_prompt(self, team_data: Dict) -> str:
        """Format current team data for the prompt"""
        if not team_data:
            return "No current team data available"
        
        formatted = []
        
        # Handle the actual team data structure from saved teams
        if 'team' in team_data:
            team = team_data['team']
            # Captain and vice-captain are at the top level of the team data
            captain = team_data.get('captain', 'Unknown')
            vice_captain = team_data.get('vice_captain', 'Unknown')
        else:
            team = team_data
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
    

    
    def _get_available_chips_from_meta(self, meta_data: Dict[str, Any]) -> Dict[str, Any]:
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
    
    def _get_available_transfers_from_meta(self, meta_data: Dict[str, Any]) -> Dict[str, Any]:
        """Get available transfers information from meta data"""
        return {
            'free_transfers': meta_data.get('free_transfers', 1),
            'bank': meta_data.get('bank', 0.0)
        }
    
    def _update_meta_from_response(self, gameweek: int, team_data: Dict[str, Any], 
                                 current_meta: Dict[str, Any]) -> None:
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
        self.team_manager.update_meta(
            gameweek=gameweek,
            team_data=team_data,
            chips_used=chips_used,
            free_transfers=new_transfers
        )
        
        logger.info(f"Meta updated: transfers={new_transfers}, chip_used={chip_used}")
    
    def _get_available_chips_local(self, previous_team: Dict[str, Any]) -> Dict[str, Any]:
        """Get available chips information from local team data"""
        # For now, assume all chips are available
        # In a more sophisticated implementation, you could track chip usage
        return {
            'used': [],
            'available': ['wildcard', 'bench_boost', 'free_hit', 'triple_captain']
        }
    
    def _get_available_transfers_local(self, previous_team: Dict[str, Any]) -> Dict[str, Any]:
        """Get available transfers information from local team data"""
        # For now, assume 1 free transfer per week
        # In a more sophisticated implementation, you could track transfer usage
        return {
            'free_transfers': 1,
            'bank': previous_team['team'].get('bank', 0.0)
        }
    
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
    
    def _is_free_hit_revert_scenario(self, gameweek: int, current_meta: Dict[str, Any]) -> bool:
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
                pre_free_hit_team = self.team_manager.load_team(pre_free_hit_gw)
                if pre_free_hit_team:
                    return True
        return False
    
    def _handle_free_hit_revert(self, gameweek: int, current_meta: Dict[str, Any]) -> Dict[str, Any]:
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
        pre_free_hit_team_data = self.team_manager.load_team(pre_free_hit_gw)
        
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
        self.team_manager.save_team(gameweek, reverted_team)
        
        # Update meta.json to reflect the revert
        # Bank should revert to pre-free-hit bank
        # Free transfers should be 1 (normal weekly allocation)
        # Free hit should remain marked as used
        self.team_manager.update_meta(
            gameweek=gameweek,
            team_data=reverted_team,
            free_transfers=1  # Normal weekly allocation after revert
        )
        
        logger.info(f"Team reverted to pre-free-hit state for Gameweek {gameweek}")
        return reverted_team
    
    def _handle_chip_team_creation(self, gameweek: int, chip_type: str, team_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle wildcard or free hit team creation from scratch
        
        Args:
            gameweek: Current gameweek
            chip_type: 'wildcard' or 'free_hit'
            team_data: Initial team data from LLM response
            
        Returns:
            Created team data
        """
        logger.info(f"Creating new team from scratch using {chip_type}")
        
        # TODO: Calculate actual budget based on current player values and money in bank
        # For wildcard: Should use current team's total value + bank balance
        # For free hit: Should use the team from before free hit's total value + bank balance
        # This ensures budget reflects price changes (could be more or less than 100.0)
        # Create a new team from scratch using the LLM
        new_team_data = self.create_team(budget=100.0, gameweek=gameweek)
        
        # Override with chip information
        new_team_data['wildcard_or_chip'] = chip_type
        new_team_data['chip_reason'] = team_data.get('chip_reason', f'{chip_type.title()} chip used')
        
        # Save the new team
        self.team_manager.save_team(gameweek, new_team_data)
        
        # Update meta.json
        current_meta = self.team_manager.get_meta()
        self._update_meta_from_response(gameweek, new_team_data, current_meta)
        
        logger.info(f"New team created successfully using {chip_type} for Gameweek {gameweek}")
        return new_team_data
    
    def get_enriched_player_data(self, force_refresh: bool = False) -> Dict[str, str]:
        """
        Get enriched player data for all players with injury news and FPL suggestions.
        Uses caching to avoid expensive LLM calls.
        
        Args:
            force_refresh: If True, ignore cache and fetch fresh data
            
        Returns:
            Dictionary mapping player names to enriched data strings
        """
        # Try to load from cache first (unless force refresh is requested)
        if not force_refresh:
            cached_data = self._get_cached_enriched_player_data()
            if cached_data:
                # Get cache age for warning
                cache_path = self._get_player_data_cache_path()
                if cache_path.exists():
                    try:
                        with open(cache_path, 'r', encoding='utf-8') as f:
                            cache_info = json.load(f)
                        cache_timestamp = cache_info.get('cache_timestamp')
                        if cache_timestamp:
                            cache_time = datetime.fromisoformat(cache_timestamp)
                            age_hours = (datetime.now() - cache_time).total_seconds() / 3600
                            if age_hours > 24:
                                warning_msg = f"⚠️  Using cached player data that is {age_hours:.1f} hours old. Consider using --force-refresh for fresh data."
                                logger.warning(warning_msg)
                                print(f"\n{warning_msg}")
                            else:
                                logger.info(f"Using cached enriched player data for {len(cached_data)} players ({age_hours:.1f} hours old)")
                        else:
                            warning_msg = "⚠️  Using cached player data with unknown age. Consider using --force-refresh for fresh data."
                            logger.warning(warning_msg)
                            print(f"\n{warning_msg}")
                            logger.info(f"Using cached enriched player data for {len(cached_data)} players")
                    except Exception:
                        logger.info(f"Using cached enriched player data for {len(cached_data)} players")
                else:
                    logger.info(f"Using cached enriched player data for {len(cached_data)} players")
                return cached_data
        
        logger.info("Fetching fresh enriched player data for all players...")
        
        try:
            # Fetch FPL data with additional stats
            all_data = self.fpl_fetcher.get_all_data_with_additional_stats()
            players = all_data['players']
            teams = all_data['teams']
            
            # Initialize lightweight LLM strategy for team analysis
            lightweight_llm = LightweightLLMStrategy(self.config)
            
            # Group players by team
            players_by_team = {}
            for player in players:
                team_name = player.team_name
                if team_name not in players_by_team:
                    players_by_team[team_name] = []
                players_by_team[team_name].append(player)
            
            # Pre-fetch FPL data once to avoid multiple API calls
            logger.info("Pre-fetching FPL data for all teams...")
            from ..ingestion.fetch_fpl import FPLDataFetcher
            fpl_fetcher = FPLDataFetcher(self.config)
            
            # Get current gameweek
            current_gameweek = fpl_fetcher.get_current_gameweek()
            if current_gameweek is None:
                current_gameweek = 1  # Fallback to GW1 if not available
            
            # Get fixtures and teams data once
            fixtures_data = fpl_fetcher.get_fixtures()
            teams_data = fpl_fetcher.get_bootstrap_data().get('teams', [])
            
            logger.info(f"Using Gameweek {current_gameweek} with {len(fixtures_data)} fixtures")
            
            # Get injury news and hints for all teams
            logger.info("Getting injury news for all teams...")
            all_injury_news = {}
            all_hints_tips = {}
            
            for team_name, team_players in players_by_team.items():
                try:
                    # Get injury news for this team (passing pre-fetched data)
                    injury_news = lightweight_llm.get_team_injury_news(team_name, team_players)
                    all_injury_news[team_name] = injury_news
                    
                    # Get hints and tips for this team (passing pre-fetched data)
                    hints_tips = lightweight_llm.get_team_hints_tips(team_name, team_players)
                    all_hints_tips[team_name] = hints_tips
                    
                    logger.info(f"Processed {team_name}: {len(team_players)} players")
                except Exception as e:
                    logger.error(f"Failed to process {team_name}: {e}")
                    # Continue with other teams
                    continue
            
            # Create enriched data for each player
            enriched_data = {}
            
            for player in players:
                try:
                    # Get player's team injury news and hints
                    team_name = player.team_name
                    injury_news = all_injury_news.get(team_name, "{}")
                    hints_tips = all_hints_tips.get(team_name, "{}")
                    
                    # Parse JSON responses
                    injury_dict = {}
                    hints_dict = {}
                    
                    try:
                        injury_dict = json.loads(injury_news) if injury_news else {}
                    except json.JSONDecodeError as e:
                        logger.warning(f"Failed to parse injury news for {team_name}: {e}")
                        injury_dict = {}
                    
                    try:
                        hints_dict = json.loads(hints_tips) if hints_tips else {}
                    except json.JSONDecodeError as e:
                        logger.warning(f"Failed to parse hints for {team_name}: {e}")
                        hints_dict = {}
                    
                    # Get player-specific data
                    player_injury = injury_dict.get(player.name, "Fit - No recent injury news suggests he is available for selection.")
                    player_hints = hints_dict.get(player.name, "Recommended - Player shows good potential for the upcoming gameweek.")
                    
                    # Get additional stats
                    chance_of_playing = player.custom_data.get('chance_of_playing', 100)
                    ppg = player.custom_data.get('ppg', player.points_per_game)
                    form = player.custom_data.get('form', player.form)
                    minutes = player.custom_data.get('minutes_played', player.minutes_played)
                    fixture_difficulty = player.custom_data.get('upcoming_fixture_difficulty', 3.0)
                    ownership = player.custom_data.get('ownership_percent', player.selected_by_pct)
                    
                    # Create enriched data string
                    enriched_string = (
                        f"{player.name} ({player.position.value}, £{player.price})\n"
                        f"Stats: Chance of Playing - {chance_of_playing}%, PPG - {ppg:.1f}, "
                        f"Form - {form:.1f}, Minutes - {minutes}, "
                        f"Fixture Difficulty - {fixture_difficulty}, Ownership - {ownership:.1f}%.\n"
                        f"Injury News: {player_injury}\n"
                        f"FPL Suggestions: {player_hints}"
                    )
                    
                    enriched_data[player.name] = enriched_string
                    
                except Exception as e:
                    logger.error(f"Failed to create enriched data for {player.name}: {e}")
                    # Create fallback enriched data
                    enriched_data[player.name] = (
                        f"{player.name} ({player.position.value}, £{player.price})\n"
                        f"Stats: Chance of Playing - 100%, PPG - {player.points_per_game:.1f}, "
                        f"Form - {player.form:.1f}, Minutes - {player.minutes_played}, "
                        f"Fixture Difficulty - 3.0, Ownership - {player.selected_by_pct:.1f}%.\n"
                        f"Injury News: Fit - No recent injury news suggests he is available for selection.\n"
                        f"FPL Suggestions: Recommended - Player shows good potential for the upcoming gameweek."
                    )
            
            # Save to cache
            self._save_player_data_cache(enriched_data)
            
            logger.info(f"Created enriched data for {len(enriched_data)} players")
            return enriched_data
            
        except Exception as e:
            logger.error(f"Failed to get enriched player data: {e}")
            return {}
    
    def get_enriched_player_data_for_prompt(self, force_refresh: bool = False) -> str:
        """
        Get enriched player data formatted for LLM prompt.
        Currently returns all players (placeholder for future filtering).
        
        Args:
            force_refresh: If True, ignore cache and fetch fresh data
            
        Returns:
            String containing enriched player data for LLM prompt
        """
        logger.info("Getting enriched player data for prompt...")
        
        try:
            enriched_data = self.get_enriched_player_data(force_refresh=force_refresh)
            
            if not enriched_data:
                return "Error: Could not fetch enriched player data"
            
            # Format for prompt (all players for now)
            formatted_data = []
            
            for player_name, enriched_string in enriched_data.items():
                formatted_data.append(enriched_string)
                formatted_data.append("")  # Empty line between players
            
            return "\n".join(formatted_data)
            
        except Exception as e:
            logger.error(f"Failed to get enriched player data for prompt: {e}")
            return "Error: Could not format enriched player data"
    
    def _get_available_players_data_enriched(self, force_refresh: bool = False) -> str:
        """
        Get enriched available players data for semantic filtering.
        
        Args:
            force_refresh: If True, ignore cache and fetch fresh data
            
        Returns:
            String containing enriched player data for LLM prompts
        """
        logger.info("Fetching enriched available players data...")
        
        try:
            # Get enriched player data
            enriched_data = self.get_enriched_player_data(force_refresh=force_refresh)
            
            if not enriched_data:
                return "Error: Could not fetch enriched player data"
            
            # Apply basic filters for available players only
            all_data = self.fpl_fetcher.get_all_data_with_additional_stats()
            players = all_data['players']
            
            filters = {
                'exclude_injured': True,
                'exclude_unavailable': True,
                'min_chance_of_playing': 25,
                'min_minutes': 0,
                'max_price': float('inf'),
                'min_form': float('-inf'),
                'positions': [Position.GK, Position.DEF, Position.MID, Position.FWD]
            }
            
            # Filter players based on criteria
            available_players = []
            for player in players:
                if (not player.is_injured and 
                    player.custom_data.get('chance_of_playing', 100) >= filters['min_chance_of_playing'] and
                    player.position in filters['positions'] and
                    player.price <= filters['max_price'] and
                    player.form >= filters['min_form']):
                    available_players.append(player)
            
            # Format the enriched data for available players only
            formatted_data = []
            
            for player in available_players:
                if player.name in enriched_data:
                    formatted_data.append(enriched_data[player.name])
                    formatted_data.append("")  # Empty line between players
            
            return "\n".join(formatted_data)
            
        except Exception as e:
            logger.error(f"Failed to get enriched available players data: {e}")
            return "Error: Could not fetch enriched player data"
    
    def _get_available_players_data_enriched_filtered(self, force_refresh: bool = False) -> str:
        """
        Get enriched available players data with embedding-based filtering.
        
        Args:
            force_refresh: If True, ignore cache and fetch fresh data
            
        Returns:
            String containing filtered enriched player data for LLM prompts
        """
        logger.info("Fetching enriched available players data with embedding filtering...")
        
        try:
            # Get enriched player data
            enriched_data = self.get_enriched_player_data(force_refresh=force_refresh)
            
            if not enriched_data:
                return "Error: Could not fetch enriched player data"
            
            # Initialize embedding filter if needed
            if self.embedding_filter is None:
                try:
                    self.embedding_filter = EmbeddingFilter(self.config)
                except Exception as e:
                    logger.error(f"Failed to initialize embedding filter: {e}")
                    logger.info("Falling back to unfiltered enriched data")
                    return self._get_available_players_data_enriched(force_refresh)
            
            # Apply embedding filtering
            try:
                filtered_data = self.embedding_filter.filter_players_by_position(enriched_data, force_refresh)
                
                if not filtered_data:
                    logger.warning("Embedding filtering returned no players, falling back to unfiltered data")
                    return self._get_available_players_data_enriched(force_refresh)
                
                # Format the filtered data for prompt
                formatted_data = []
                
                for player_name, enriched_string in filtered_data.items():
                    formatted_data.append(enriched_string)
                    formatted_data.append("")  # Empty line between players
                
                logger.info(f"Successfully filtered to {len(filtered_data)} players using embeddings")
                return "\n".join(formatted_data)
                
            except Exception as e:
                logger.error(f"Embedding filtering failed: {e}")
                logger.info("Falling back to unfiltered enriched data")
                return self._get_available_players_data_enriched(force_refresh)
            
        except Exception as e:
            logger.error(f"Failed to get filtered enriched available players data: {e}")
            return "Error: Could not fetch filtered enriched player data"
 