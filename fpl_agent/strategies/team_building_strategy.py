"""
FPL team manager using LLM for comprehensive team management
"""

import logging
import json
from typing import Dict, Optional, Any
from pathlib import Path
from datetime import datetime

from ..core.config import Config
from ..core.team_manager import TeamManager
from .base_strategy import BaseLLMStrategy
from .embedding_filter import EmbeddingFilter
from ..utils.data_transformers import transform_fpl_data_to_teams, calculate_chance_of_playing
from ..utils.validator import FPLValidator
from ..utils.player_factory import PlayerFactory
from ..utils.fpl_data_manager import FPLDataManager
from ..utils.data_enrichment import DataEnrichment
from ..core.models import Position

logger = logging.getLogger(__name__)


class TeamBuildingStrategy(BaseLLMStrategy):
    """
    LLM-based strategy for FPL team creation and weekly management.
    
    This class handles:
    - Team creation for Gameweek 1 using LLM analysis
    - Weekly team updates and transfers using LLM insights
    - Chip and wildcard management with LLM recommendations
    - Integration with FPL API for current team data
    """
    
    def __init__(self, config: Config):
        super().__init__(config, model_name="main")
        self.team_manager = TeamManager()
        self.embedding_filter = None  # Lazy initialization
        
        # Use our new utilities instead of direct FPL fetching
        self.player_factory = PlayerFactory()
        self.data_manager = FPLDataManager(config)
        self.data_enrichment = DataEnrichment(config)
    
    def get_strategy_name(self) -> str:
        """Return the name of this strategy."""
        return "Team Building Strategy"
    
    def _get_team_constraints_prompt(self) -> str:
        """Generate team constraints prompt from config"""
        position_limits = self.config.get_position_limits()
        formation_constraints = self.config.get_formation_constraints()
        
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
    
    def _save_player_data_cache(self, player_data: Dict[str, Dict[str, Any]]) -> None:
        """
        Save player data to cache file.
        
        Args:
            player_data: Dictionary of structured enriched player data
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
    
    def _get_cached_enriched_player_data(self) -> Optional[Dict[str, Dict[str, Any]]]:
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
            # Get FPL data using our data manager
            all_data = self.data_manager.get_fpl_static_data()
            players = all_data.get('elements', [])
            
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
                # Calculate chance of playing as minimum of this round and next round
                chance_of_playing = calculate_chance_of_playing(
                    player.chance_of_playing_this_round,
                    player.chance_of_playing_next_round
                )
                
                # Check if player meets filter criteria
                if (not player.is_injured and 
                    chance_of_playing >= filters['min_chance_of_playing'] and
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
                    # Calculate chance of playing as minimum of this round and next round
                    chance_of_playing = calculate_chance_of_playing(
                        player.chance_of_playing_this_round,
                        player.chance_of_playing_next_round
                    )
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
            response = self.llm_engine.query(prompt, use_web_search=True)
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
            gameweek = self.data_manager.get_current_gameweek()
        
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
            response = self.llm_engine.query(prompt, use_web_search=True)
            
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
                bootstrap_data = self.data_manager.get_fpl_static_data()
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
{self._get_team_constraints_prompt()}
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
* {self.config.get_team_config().get('squad_size', 15)} total players: {self.config.get_position_limits()['GK']} goalkeepers, {self.config.get_position_limits()['DEF']} defenders, {self.config.get_position_limits()['MID']} midfielders, {self.config.get_position_limits()['FWD']} forwards
* Max {self.config.get_team_config().get('max_players_per_team', 3)} players from any single club
* Valid formation for starting 11 (1GK, {self.config.get_formation_constraints()['DEF'][0]}–{self.config.get_formation_constraints()['DEF'][1]} DEF, {self.config.get_formation_constraints()['MID'][0]}–{self.config.get_formation_constraints()['MID'][1]} MID, {self.config.get_formation_constraints()['FWD'][0]}–{self.config.get_formation_constraints()['FWD'][1]} FWD)"""
    
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
        
        # Get constraints from config
        position_limits = self.config.get_position_limits()
        
        # Count positions
        gk_count = sum(1 for p in all_players if p.get('position') == 'GK')
        def_count = sum(1 for p in all_players if p.get('position') == 'DEF')
        mid_count = sum(1 for p in all_players if p.get('position') == 'MID')
        fwd_count = sum(1 for p in all_players if p.get('position') == 'FWD')
        
        # Validate against config
        if gk_count != position_limits['GK']:
            raise ValueError(f"Must have exactly {position_limits['GK']} goalkeepers, got {gk_count}")
        if def_count != position_limits['DEF']:
            raise ValueError(f"Must have exactly {position_limits['DEF']} defenders, got {def_count}")
        if mid_count != position_limits['MID']:
            raise ValueError(f"Must have exactly {position_limits['MID']} midfielders, got {mid_count}")
        if fwd_count != position_limits['FWD']:
            raise ValueError(f"Must have exactly {position_limits['FWD']} forwards, got {fwd_count}")
        
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
    
    def get_enriched_player_data(self, force_refresh: bool = False) -> Dict[str, Dict[str, Any]]:
        """
        Get enriched player data for all players with injury news and FPL suggestions.
        Uses caching to avoid expensive LLM calls.
        
        Args:
            force_refresh: If True, ignore cache and fetch fresh data
            
        Returns:
            Dictionary mapping player names to structured player data
        """
        # Try to load from cache first (unless force refresh is requested)
        if not force_refresh:
            cached_data = self._load_cached_player_data()
            if cached_data:
                player_data = cached_data.get('player_data', {})
                
                # Check if data already has enrichments
                has_enrichments = False
                if player_data:
                    # Check first player to see if enrichments exist
                    first_player = next(iter(player_data.values()), None)
                    if first_player and isinstance(first_player, dict):
                        has_enrichments = 'injury_news' in first_player and 'hints_tips_news' in first_player
                
                # If enrichments exist, return the data
                if has_enrichments:
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
                                    warning_msg = f"⚠️  Using cached enriched player data that is {age_hours:.1f} hours old. Consider using --force-refresh for fresh data."
                                    logger.warning(warning_msg)
                                    print(f"\n{warning_msg}")
                                else:
                                    logger.info(f"Using cached enriched player data for {len(player_data)} players ({age_hours:.1f} hours old)")
                            else:
                                warning_msg = "⚠️  Using cached enriched player data with unknown age. Consider using --force-refresh for fresh data."
                                logger.warning(warning_msg)
                                print(f"\n{warning_msg}")
                                logger.info(f"Using cached enriched player data for {len(player_data)} players")
                        except Exception:
                            logger.info(f"Using cached enriched player data for {len(player_data)} players")
                    else:
                        logger.info(f"Using cached enriched player data for {len(player_data)} players")
                    return player_data
                
                # If basic data exists but no enrichments, we'll add enrichments below
                if player_data:
                    logger.info(f"Found basic player data for {len(player_data)} players, adding enrichments...")
                else:
                    logger.info("No cached player data found")
                    return {}
            else:
                logger.info("No cached player data found")
                return {}
        
        # At this point, we either need to fetch fresh data or add enrichments to existing data
        try:
            # Check if we have existing basic data
            cached_data = self._load_cached_player_data()
            existing_player_data = cached_data.get('player_data', {}) if cached_data else {}
            
            if existing_player_data and not force_refresh:
                # We have basic data, just need to add enrichments
                logger.info("Adding enrichments to existing basic player data...")
                enriched_data = self._add_enrichments_to_existing_data(existing_player_data)
            else:
                # Need to fetch fresh data and add enrichments
                logger.info("Fetching fresh enriched player data for all players...")
                enriched_data = self._fetch_fresh_enriched_data()
            
            return enriched_data
            
        except Exception as e:
            logger.error(f"Failed to get enriched player data: {e}")
            return {}
    
    def _fetch_fresh_enriched_data(self) -> Dict[str, Dict[str, Any]]:
        """Fetch fresh enriched data using our new utility"""
        try:
            logger.info("Using DataEnrichment utility to fetch fresh enriched data...")
            
            # Get basic FPL data from our data manager
            all_data = self.data_manager.get_fpl_static_data()
            players = all_data.get('elements', [])
            
            # Use our DataEnrichment utility instead of duplicating logic
            
            # Group players by team
            players_by_team = {}
            for player in players:
                team_name = player.team_name
                if team_name not in players_by_team:
                    players_by_team[team_name] = []
                players_by_team[team_name].append(player)
            
            # Use our data manager for gameweek and fixture info
            current_gameweek = self.data_manager.get_current_gameweek()
            if current_gameweek is None:
                current_gameweek = 1  # Fallback to GW1 if not available
            
            logger.info(f"Using Gameweek {current_gameweek} for enrichment")
            
            # Use our DataEnrichment utility instead of duplicating logic
            
            # Convert FPL data to our expected format and enrich
            player_data_dict = {}
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
                    
                    # Get additional stats from custom_data (calculated fields)
                    ppg = player.custom_data.get('ppg', float(player.points_per_game))
                    form = player.custom_data.get('form', float(player.form))
                    fixture_difficulty = player.custom_data.get('upcoming_fixture_difficulty', 3.0)
                    ownership = player.custom_data.get('ownership_percent', float(player.selected_by_percent))
                    
                    # Create structured player data using exact FPL API field names
                    player_data = {
                        "data": {
                            # Basic info
                            "id": player.id,
                            "first_name": player.first_name,
                            "second_name": player.second_name,
                            "name": player.name,
                            "team_id": player.team_id,
                            "team": player.team_name,
                            "team_short_name": player.team_short_name,
                            "element_type": player.element_type,
                            "position": player.position.value,
                            
                            # Price info
                            "now_cost": player.now_cost,
                            "price": player.price,
                            "cost_change_start": player.cost_change_start,
                            "cost_change_event": player.cost_change_event,
                            "price_change": player.price_change,
                            
                            # Stats
                            "total_points": player.total_points,
                            "points_per_game": player.points_per_game,
                            "form": player.form,
                            "minutes": player.minutes,
                            "selected_by_percent": player.selected_by_percent,
                            
                            # Expected stats
                            "xG": player.xG,
                            "xA": player.xA,
                            "xGC": player.xGC,
                            "xMins_pct": player.xMins_pct,
                            
                            # Injury status
                            "status": player.status,
                            "news": player.news,
                            "news_added": player.news_added,
                            "chance_of_playing_next_round": player.chance_of_playing_next_round,
                            "chance_of_playing_this_round": player.chance_of_playing_this_round,
                            "is_injured": player.is_injured,
                            
                            # Calculated fields (for display)
                            "ppg": ppg,
                            "form_float": form,
                            "minutes_played": player.minutes,
                            "fixture_difficulty": fixture_difficulty,
                            "ownership_percent": ownership
                        },
                        "injury_news": player_injury,
                        "hints_tips_news": player_hints
                    }
                    
                    enriched_data[player.name] = player_data
                    
                except Exception as e:
                    logger.error(f"Failed to create enriched data for {player.name}: {e}")
                    # Create fallback enriched data
                    enriched_data[player.name] = {
                        "data": {
                            # Basic info
                            "id": player.id,
                            "first_name": player.first_name,
                            "second_name": player.second_name,
                            "name": player.name,
                            "team_id": player.team_id,
                            "team": player.team_name,
                            "team_short_name": player.team_short_name,
                            "element_type": player.element_type,
                            "position": player.position.value,
                            
                            # Price info
                            "now_cost": player.now_cost,
                            "price": player.price,
                            "cost_change_start": player.cost_change_start,
                            "cost_change_event": player.cost_change_event,
                            "price_change": player.price_change,
                            
                            # Stats
                            "total_points": player.total_points,
                            "points_per_game": player.points_per_game,
                            "form": player.form,
                            "minutes": player.minutes,
                            "selected_by_percent": player.selected_by_percent,
                            
                            # Expected stats
                            "xG": player.xG,
                            "xA": player.xA,
                            "xGC": player.xGC,
                            "xMins_pct": player.xMins_pct,
                            
                            # Injury status
                            "status": player.status,
                            "news": player.news,
                            "news_added": player.news_added,
                            "chance_of_playing_next_round": player.chance_of_playing_next_round,
                            "chance_of_playing_this_round": player.chance_of_playing_this_round,
                            "is_injured": player.is_injured,
                            
                            # Calculated fields (for display)
                            "ppg": float(player.points_per_game),
                            "form_float": float(player.form),
                            "minutes_played": player.minutes,
                            "fixture_difficulty": 3.0,
                            "ownership_percent": float(player.selected_by_percent)
                        },
                        "injury_news": "Fit - No recent injury news suggests he is available for selection.",
                        "hints_tips_news": "Recommended - Player shows good potential for the upcoming gameweek."
                    }
            
            # Save to cache
            self._save_player_data_cache(enriched_data)
            
            logger.info(f"Created enriched data for {len(enriched_data)} players")
            return enriched_data
            
        except Exception as e:
            logger.error(f"Failed to fetch fresh enriched data: {e}")
            return {}
    
    def _add_enrichments_to_existing_data(self, existing_player_data: Dict[str, Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        """Add enrichments to existing basic player data using our new utility"""
        try:
            logger.info("Using DataEnrichment utility to add enrichments...")
            
            # Use our new DataEnrichment utility instead of the massive inline implementation
            enriched_data = self.data_enrichment.enrich_player_data(existing_player_data)
            
            # Save to cache
            self._save_player_data_cache(enriched_data)
            
            logger.info(f"Added enrichments to {len(enriched_data)} players using utility")
            return enriched_data
            
        except Exception as e:
            logger.error(f"Failed to add enrichments to existing data: {e}")
            return existing_player_data

    def _generate_embedding_text(self, player_data: Dict[str, Any]) -> str:
        """
        Generate text for embeddings (without stats line).
        
        Args:
            player_data: Structured player data dictionary
            
        Returns:
            Text string formatted for embeddings
        """
        data = player_data["data"]
        return f"{data['name']} ({data['team']}, {data['position']}, £{data['price']})\n" \
               f"Injury News: {player_data['injury_news']}\n" \
               f"FPL Suggestions: {player_data['hints_tips_news']}"

    def _generate_prompt_text(self, player_data: Dict[str, Any]) -> str:
        """
        Generate text for LLM prompts (with stats line).
        
        Args:
            player_data: Structured player data dictionary
            
        Returns:
            Text string formatted for LLM prompts
        """
        data = player_data["data"]
        return f"{data['name']} ({data['team']}, {data['position']}, £{data['price']})\n" \
               f"Stats: Chance of Playing - {data['chance_of_playing']}%, PPG - {data['ppg']:.1f}, " \
               f"Form - {data['form']:.1f}, Minutes - {data['minutes_played']}, " \
               f"Fixture Difficulty - {data['fixture_difficulty']}, Ownership - {data['ownership_percent']:.1f}%.\n" \
               f"Injury News: {player_data['injury_news']}\n" \
               f"FPL Suggestions: {player_data['hints_tips_news']}"

    def get_enriched_player_data_for_embeddings(self, force_refresh: bool = False) -> Dict[str, str]:
        """
        Get enriched player data formatted for embeddings (without stats line).
        
        Args:
            force_refresh: If True, ignore cache and fetch fresh data
            
        Returns:
            Dictionary mapping player names to embedding-friendly enriched data strings
        """
        logger.info("Getting enriched player data for embeddings...")
        
        try:
            # Get structured enriched player data
            structured_data = self.get_enriched_player_data(force_refresh=force_refresh)
            
            if not structured_data:
                return {}
            
            # Create embedding-friendly versions (without stats line)
            embedding_data = {}
            
            for player_name, player_data in structured_data.items():
                embedding_text = self._generate_embedding_text(player_data)
                embedding_data[player_name] = embedding_text
            
            logger.info(f"Created embedding-friendly data for {len(embedding_data)} players")
            return embedding_data
            
        except Exception as e:
            logger.error(f"Failed to get enriched player data for embeddings: {e}")
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
            structured_data = self.get_enriched_player_data(force_refresh=force_refresh)
            
            if not structured_data:
                return "Error: Could not fetch enriched player data"
            
            # Format for prompt (all players for now)
            formatted_data = []
            
            for player_name, player_data in structured_data.items():
                prompt_text = self._generate_prompt_text(player_data)
                formatted_data.append(prompt_text)
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
            
            # Use the unified filtering method
            viable_result = self._get_viable_players_from_enriched(enriched_data, for_embeddings=False)
            
            # Format the viable players data
            formatted_data = []
            
            for position_players in viable_result['positions'].values():
                for player_name, prompt_text in position_players:
                    formatted_data.append(prompt_text)
                    formatted_data.append("")  # Empty line between players
            
            return "\n".join(formatted_data)
            
        except Exception as e:
            logger.error(f"Failed to get enriched available players data: {e}")
            return "Error: Could not fetch enriched player data"
    
    def _get_viable_players_from_enriched(self, enriched_data: Dict[str, Dict[str, Any]], for_embeddings: bool = False) -> Dict[str, Any]:
        """
        Get viable players from enriched data using unified filtering.
        
        This method combines:
        1. Basic availability filters (chance of playing, injured, etc.)
        2. Rule-based filters (Out/Avoid players)
        
        Args:
            enriched_data: Dictionary mapping player names to structured player data
            for_embeddings: If True, return embedding-friendly text format
            
        Returns:
            Dict containing filtered players organized by position
        """
        logger.info("Applying unified filtering to enriched player data...")
        
        try:
            # Apply unified filtering
            viable_players = {}
            filtered_out_count = 0
            
            for player_name, player_data in enriched_data.items():
                data = player_data["data"]
                
                # Basic availability filters using structured data
                # Calculate chance of playing as minimum of this_round and next_round
                chance_of_playing = calculate_chance_of_playing(
                    data.get('chance_of_playing_this_round'),
                    data.get('chance_of_playing_next_round')
                )
                if chance_of_playing < 25:  # Manual filter: chance of playing
                    filtered_out_count += 1
                    continue
                
                if data.get('is_injured', False):  # Manual filter: injured players
                    filtered_out_count += 1
                    continue
                
                position = data.get('position')
                if position not in ['GK', 'DEF', 'MID', 'FWD']:  # Manual filter: valid positions
                    filtered_out_count += 1
                    continue
                
                # Rule-based filters (Out/Avoid)
                injury_news = player_data.get('injury_news', '')
                hints_tips = player_data.get('hints_tips_news', '')
                
                # Check injury status
                if injury_news.startswith("Out"):
                    filtered_out_count += 1
                    continue
                
                # Check FPL recommendations
                if hints_tips.startswith("Avoid"):
                    filtered_out_count += 1
                    continue
                
                # Player passes all filters
                viable_players[player_name] = player_data
            
            # Group by position
            positions = {'GK': [], 'DEF': [], 'MID': [], 'FWD': []}
            
            for player_name, player_data in viable_players.items():
                position_key = player_data["data"]["position"]
                if position_key in positions:
                    if for_embeddings:
                        # Generate embedding-friendly text
                        embedding_text = self._generate_embedding_text(player_data)
                        positions[position_key].append((player_name, embedding_text))
                    else:
                        # Generate prompt-friendly text
                        prompt_text = self._generate_prompt_text(player_data)
                        positions[position_key].append((player_name, prompt_text))
            
            # Create result structure
            result = {
                'total_players_loaded': len(enriched_data),
                'total_players_filtered': len(viable_players),
                'filtered_out_count': filtered_out_count,
                'reduction_percentage': ((len(enriched_data) - len(viable_players)) / len(enriched_data) * 100),
                'positions': positions,
                'timestamp': datetime.now().isoformat()
            }
            
            logger.info(f"Unified filtering complete: {len(viable_players)} players selected from {len(enriched_data)} total (filtered out {filtered_out_count})")
            return result
            
        except Exception as e:
            logger.error(f"Failed to apply unified filtering: {e}")
            raise

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
            # Get structured enriched player data
            structured_data = self.get_enriched_player_data(force_refresh=force_refresh)
            
            if not structured_data:
                return "Error: Could not fetch structured player data"
            
            # Use the unified filtering method first
            viable_result = self._get_viable_players_from_enriched(structured_data, for_embeddings=True)
            viable_players = {}
            
            # Convert the positions structure back to a flat dictionary
            for position_players in viable_result['positions'].values():
                for player_name, embedding_text in position_players:
                    viable_players[player_name] = embedding_text
            
            # Initialize embedding filter if needed
            if self.embedding_filter is None:
                try:
                    self.embedding_filter = EmbeddingFilter(self.config)
                except Exception as e:
                    logger.error(f"Failed to initialize embedding filter: {e}")
                    logger.info("Falling back to unfiltered enriched data")
                    return self._get_available_players_data_enriched(force_refresh)
            
            # Apply embedding filtering on viable players only
            try:
                filtered_data = self.embedding_filter.filter_players_by_position(viable_players, force_refresh)
                
                if not filtered_data:
                    logger.warning("Embedding filtering returned no players, falling back to unfiltered data")
                    return self._get_available_players_data_enriched(force_refresh)
                
                # Format the filtered data for prompt - need to get full structured data for prompt text
                formatted_data = []
                full_structured_data = self.get_enriched_player_data(force_refresh=force_refresh)
                
                for player_name, embedding_text in filtered_data.items():
                    if player_name in full_structured_data:
                        prompt_text = self._generate_prompt_text(full_structured_data[player_name])
                        formatted_data.append(prompt_text)
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
 