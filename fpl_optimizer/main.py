"""
Main FPL Optimizer application - Enhanced with dual team creation methods
"""

import logging
import sys
import os
import json
from typing import Dict, List, Optional, Any
from datetime import datetime
import argparse
from pathlib import Path

# Handle imports for both direct execution and module execution
try:
    # When run as module (python -m fpl_optimizer.main)
    from .core.config import Config
    from .ingestion import get_test_data

    from .core.models import Player, Team, Position, FPLTeam
    from fpl_optimizer.strategies import ModelStrategy, LLMStrategy
    from fpl_optimizer.strategies.lightweight_llm_strategy import LightweightLLMStrategy
except ImportError:
    # When run directly (python fpl_optimizer/main.py)
    # Add the parent directory to the path
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from fpl_optimizer.core.config import Config
    from fpl_optimizer.ingestion import get_test_data

    from fpl_optimizer.core.models import Player, Team, Position, FPLTeam
    from fpl_optimizer.strategies import ModelStrategy, LLMStrategy
    from fpl_optimizer.strategies.lightweight_llm_strategy import LightweightLLMStrategy


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)


class FPLOptimizer:
    """Enhanced FPL Optimizer with dual team creation approaches"""
    
    def __init__(self, config_path: Optional[str] = None):
        """Initialize the FPL Optimizer"""
        self.config = Config(config_path)
        
        # Initialize model strategy (always needed)
        self.model_strategy = ModelStrategy(self.config)
        
        # LLM strategy will be initialized lazily when needed
        self._llm_strategy = None
        
    def fetch_data(self, sample_size: int = 50) -> Dict[str, Any]:
        """Fetch player data without optimization"""
        
        try:
            logger.info("Starting data fetch...")
            
            # Get test data
            logger.info("Fetching player data...")
            test_data = get_test_data(self.config, sample_size)
            players = test_data['players']
            teams = test_data['teams']
            
            logger.info(f"Fetched {len(players)} players and {len(teams)} teams")
            
            # Calculate expected points using model method
            logger.info("Calculating expected points...")
            player_xpts = self.model_strategy._calculate_comprehensive_xpts(players)
            
            logger.info("Data fetch completed successfully!")
            return {
                'players': players,
                'teams': teams,
                'player_xpts': player_xpts,
                'summary': test_data['summary']
            }
            
        except Exception as e:
            logger.error(f"Data fetch failed: {e}")
            raise
    
    @property
    def llm_strategy(self):
        """Lazy initialization of LLM strategy"""
        if self._llm_strategy is None:
            self._llm_strategy = LLMStrategy(self.config)
        return self._llm_strategy
    
    def fetch_fpl_players(self, limit: Optional[int] = None, enrich_with_llm: bool = False, force_refresh: bool = False) -> Dict[str, Any]:
        """Fetch real FPL player data from the API
        
        Args:
            limit: Optional limit on number of players to fetch
            enrich_with_llm: If True, fetch injury news and FPL hints for all players and cache them
        """
        
        try:
            logger.info("Starting FPL API data fetch...")
            
            # Import here to avoid circular imports
            from .ingestion.fetch_fpl import FPLDataFetcher
            from .utils.data_transformers import transform_fpl_data_to_teams
            from .core.models import Position
            
            # Initialize FPL fetcher
            fpl_fetcher = FPLDataFetcher(self.config)
            
            # Get bootstrap data
            logger.info("Fetching FPL bootstrap data...")
            bootstrap_data = fpl_fetcher.get_bootstrap_data()
            
            # Use data transformer to get rich player data
            logger.info("Transforming data with rich player information...")
            filters = {
                'exclude_injured': False,      # Include all players for display
                'exclude_unavailable': False,  # Include all players for display
                'min_chance_of_playing': 0,    # Include all players
                'min_minutes': 0,              # Include all players
                'max_price': float('inf'),     # No price limit
                'min_form': float('-inf'),     # No form minimum
                'positions': [Position.GK, Position.DEF, Position.MID, Position.FWD]
            }
            
            teams = transform_fpl_data_to_teams(bootstrap_data, filters)
            
            # Extract all players from teams
            all_players = []
            for team_summary in teams.values():
                all_players.extend(team_summary.players)
            
            # Apply limit if specified
            if limit and limit > 0:
                players = all_players[:limit]
                logger.info(f"Limited to {limit} players out of {len(all_players)} total")
            else:
                players = all_players
                logger.info(f"Using all {len(players)} players")
            
            # Create summary
            position_distribution = {}
            price_range_distribution = {}
            
            for player in players:
                # Position distribution
                pos = player.position.value
                position_distribution[pos] = position_distribution.get(pos, 0) + 1
                
                # Price range distribution
                if player.price <= 5.0:
                    price_range = "£0-5m"
                elif player.price <= 7.5:
                    price_range = "£5-7.5m"
                elif player.price <= 10.0:
                    price_range = "£7.5-10m"
                else:
                    price_range = "£10m+"
                price_range_distribution[price_range] = price_range_distribution.get(price_range, 0) + 1
            
            summary = {
                'total_players': len(players),
                'total_teams': len(teams),
                'position_distribution': position_distribution,
                'price_range_distribution': price_range_distribution,
                'data_source': 'FPL API (with rich data)',
                'fetched_at': datetime.now().isoformat()
            }
            
            logger.info("FPL data fetch completed successfully!")
            
            # Save basic player data to structured format
            try:
                # Create structured player data
                structured_data = {}
                for player in players:
                    # Get additional stats if available
                    additional_stats = player.custom_data if hasattr(player, 'custom_data') else {}
                    
                    player_data = {
                        "data": {
                            "name": player.name,
                            "team": player.team_name,
                            "position": player.position.value,
                            "price": player.price,
                            "chance_of_playing_next_round": player.chance_of_playing_next_round,
                            "chance_of_playing_this_round": player.chance_of_playing_this_round,
                            "ppg": additional_stats.get('ppg', player.points_per_game),
                            "form": additional_stats.get('form', player.form),
                            "minutes_played": additional_stats.get('minutes_played', player.minutes),
                            "fixture_difficulty": additional_stats.get('upcoming_fixture_difficulty', 3.0),
                            "ownership_percent": additional_stats.get('ownership_percent', float(player.selected_by_percent)),
                            "total_points": player.total_points,
                            "points_per_game": player.points_per_game,
                            "selected_by_pct": float(player.selected_by_percent),
                            "is_injured": player.is_injured,
                            "injury_type": player.news or "",
                            "price_change": player.price_change,
                            "team_id": player.team_id,
                            "team_short_name": player.team_short_name,
                            "xG": player.xG,
                            "xA": player.xA,
                            "xGC": player.xGC,
                            "xMins_pct": player.xMins_pct
                        }
                    }
                    structured_data[player.name] = player_data
                
                # Save to cache
                self.llm_strategy._save_player_data_cache(structured_data)
                logger.info(f"Saved basic player data for {len(structured_data)} players")
                
            except Exception as e:
                logger.error(f"Failed to save basic player data: {e}")
            
            # Enrich with LLM data if requested
            if enrich_with_llm:
                print("\n" + "="*80)
                print("ENRICHING PLAYER DATA WITH LLM ANALYSIS")
                print("="*80)
                print("This will fetch injury news and FPL hints for all teams...")
                print("This process may take 15-20 minutes.")
                print("="*80)
                
                try:
                    # Get enriched player data (respect force_refresh flag)
                    enriched_data = self.llm_strategy.get_enriched_player_data(force_refresh=force_refresh)
                    
                    if enriched_data:
                        print(f"✅ Successfully enriched and cached data for {len(enriched_data)} players")
                        summary['enriched_with_llm'] = True
                        summary['enriched_players_count'] = len(enriched_data)
                    else:
                        print("❌ Failed to enrich player data")
                        summary['enriched_with_llm'] = False
                        
                except Exception as e:
                    logger.error(f"Failed to enrich player data: {e}")
                    print(f"❌ Error enriching player data: {e}")
                    summary['enriched_with_llm'] = False
            
            return {
                'players': players,
                'teams': [team_summary.team for team_summary in teams.values()],
                'summary': summary
            }
            
        except Exception as e:
            logger.error(f"FPL data fetch failed: {e}")
            raise
    
    def create_team_model(self, budget: float = 100.0, sample_size: int = 500) -> Dict[str, Any]:
        """Create team using model-based statistical approach"""
        
        try:
            logger.info("Creating team using model-based statistical approach...")
            
            # Use model strategy
            result = self.model_strategy.create_team_from_scratch(budget)
            
            # Get additional data for display
            data = get_test_data(self.config, sample_size)
            
            logger.info("Model-based team creation completed successfully!")
            return {
                'method': 'Model-based Statistical Analysis',
                'optimization_result': result,
                'players': data['players'],
                'teams': data['teams'],
                'summary': data['summary']
            }
            
        except Exception as e:
            logger.error(f"Model-based team creation failed: {e}")
            raise
    
    def create_team_llm(self, budget: float = 100.0, gameweek: Optional[int] = None, use_semantic_filtering: bool = False, force_refresh: bool = False, use_embeddings: bool = False) -> Dict[str, Any]:
        """Create team using comprehensive LLM-based approach with FPL integration"""
        
        try:
            logger.info("Creating team using comprehensive LLM-based approach...")
            
            # Use LLM strategy
            result = self.llm_strategy.create_team(budget, gameweek or 1, use_semantic_filtering, force_refresh, use_embeddings)
            
            logger.info("Comprehensive LLM-based team creation completed successfully!")
            return {
                'method': 'Comprehensive LLM-based Team Creation',
                'team_data': result,
                'semantic_filtering': use_semantic_filtering,
                'force_refresh': force_refresh
            }
            
        except Exception as e:
            logger.error(f"Comprehensive LLM-based team creation failed: {e}")
            # If it's a ValueError with the LLM response, extract and show it
            if isinstance(e, ValueError) and "LLM failed to generate a valid team" in str(e):
                error_msg = str(e)
                llm_response = error_msg.split("Response: ", 1)[1] if "Response: " in error_msg else "No response available"
                print(f"\n" + "="*80)
                print("LLM RESPONSE (FAILED TO PARSE)")
                print("="*80)
                print(llm_response)
                print("="*80)
            raise
    
    def get_weekly_recommendations_model(self, current_team: FPLTeam, 
                                     free_transfers: int = 1) -> Dict[str, Any]:
        """Get weekly recommendations using model-based approach"""
        
        try:
            logger.info("Generating weekly recommendations using model-based approach...")
            
            # Get transfer suggestions
            transfer_result = self.model_strategy.suggest_weekly_transfers(
                current_team, free_transfers
            )
            
            # Get captain selections
            captain_id, vice_captain_id = self.model_strategy.select_captain_and_vice(current_team)
            
            # Get wildcard analysis
            wildcard_analysis = self.model_strategy.analyze_wildcard_usage(current_team)
            
            recommendations = {
                'method': 'Model-based Statistical Analysis',
                'transfers': {
                    'recommended_transfers': transfer_result.transfers,
                    'reasoning': transfer_result.reasoning,
                    'confidence': transfer_result.confidence
                },
                'captaincy': {
                    'captain_id': captain_id,
                    'vice_captain_id': vice_captain_id,
                    'captain_name': self._get_player_name_by_id(current_team, captain_id),
                    'vice_captain_name': self._get_player_name_by_id(current_team, vice_captain_id)
                },
                'wildcard': wildcard_analysis,
                'overall_confidence': transfer_result.confidence,
                'generated_at': datetime.now().isoformat()
            }
            
            logger.info("Model-based weekly recommendations completed successfully!")
            return recommendations
            
        except Exception as e:
            logger.error(f"API-based weekly recommendations failed: {e}")
            raise
    
    def get_weekly_recommendations_llm(self, current_team: FPLTeam, 
                                     free_transfers: int = 1,
                                     gameweek: Optional[int] = None) -> Dict[str, Any]:
        """Get weekly recommendations using LLM-based approach"""
        
        try:
            logger.info("Generating weekly recommendations using LLM-based approach...")
            
            # Use comprehensive team manager for weekly analysis
            recommendations = self.llm_strategy.update_team_weekly(gameweek)
            
            # Add method identifier
            recommendations['method'] = 'LLM-based Expert Insights'
            
            logger.info("LLM-based weekly recommendations completed successfully!")
            return recommendations
            
        except Exception as e:
            logger.error(f"LLM-based weekly recommendations failed: {e}")
            raise
    

    

    

    
    def update_team_weekly_comprehensive(self, gameweek: Optional[int] = None, use_semantic_filtering: bool = False, force_refresh: bool = False, use_embeddings: bool = False) -> Dict[str, Any]:
        """Update the current FPL team weekly using the comprehensive LLM team manager"""
        try:
            logger.info(f"Updating team weekly for gameweek {gameweek or 'current'}...")
            result = self.llm_strategy.update_team_weekly(gameweek, use_semantic_filtering, force_refresh, use_embeddings)
            logger.info("Weekly team update completed successfully!")
            return result
        except Exception as e:
            logger.error(f"Weekly team update failed: {e}")
            raise
    
    # Helper methods
    
    def _get_player_name_by_id(self, team: FPLTeam, player_id: Optional[int]) -> str:
        """Get player name by ID from team"""
        if player_id is None:
            return "Unknown"
        
        for player in team.players:
            if player.id == player_id:
                return player.name
        
        return f"Player {player_id}"
    
    def get_team_injury_news(self, team_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Get injury news and playing likelihood for players in a specific team or all teams.
        
        Args:
            team_name: Name of the team (None for all teams)
            
        Returns:
            Dictionary containing injury news for the team(s)
        """
        try:
            logger.info("Starting team injury news analysis...")
            
            # Initialize lightweight LLM engine
            lightweight_llm = LightweightLLMStrategy(self.config)
            
            # Fetch FPL data with additional stats
            from fpl_optimizer.ingestion.fetch_fpl import FPLDataFetcher
            fetcher = FPLDataFetcher(self.config)
            all_data = fetcher.get_all_data_with_additional_stats()
            players = all_data['players']
            
            if team_name:
                # Get specific team
                team_players = [p for p in players if p.team_name == team_name]
                if not team_players:
                    raise ValueError(f"No players found for team: {team_name}")
                
                logger.info(f"Getting injury news for {team_name} ({len(team_players)} players)")
                injury_news = lightweight_llm.get_team_injury_news(team_name, team_players)
                
                return {
                    'team_name': team_name,
                    'injury_news': injury_news,
                    'player_count': len(team_players)
                }
            else:
                # Get all teams
                teams = {}
                for player in players:
                    if player.team_name not in teams:
                        teams[player.team_name] = []
                    teams[player.team_name].append(player)
                
                results = {}
                for team_name, team_players in teams.items():
                    logger.info(f"Getting injury news for {team_name} ({len(team_players)} players)")
                    injury_news = lightweight_llm.get_team_injury_news(team_name, team_players)
                    results[team_name] = {
                        'injury_news': injury_news,
                        'player_count': len(team_players)
                    }
                
                return {
                    'all_teams': True,
                    'teams': results,
                    'total_teams': len(results)
                }
                
        except Exception as e:
            logger.error(f"Failed to get team injury news: {e}")
            raise
    
    def get_team_hints_tips(self, team_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Get hints, tips, and recommendations for players in a specific team or all teams.
        
        Args:
            team_name: Name of the team (None for all teams)
            
        Returns:
            Dictionary containing hints and tips for the team(s)
        """
        try:
            logger.info("Starting team hints and tips analysis...")
            
            # Initialize lightweight LLM engine
            lightweight_llm = LightweightLLMStrategy(self.config)
            
            # Fetch FPL data with additional stats
            from fpl_optimizer.ingestion.fetch_fpl import FPLDataFetcher
            fetcher = FPLDataFetcher(self.config)
            all_data = fetcher.get_all_data_with_additional_stats()
            players = all_data['players']
            
            if team_name:
                # Get specific team
                team_players = [p for p in players if p.team_name == team_name]
                if not team_players:
                    raise ValueError(f"No players found for team: {team_name}")
                
                logger.info(f"Getting hints and tips for {team_name} ({len(team_players)} players)")
                hints_tips = lightweight_llm.get_team_hints_tips(team_name, team_players)
                
                return {
                    'team_name': team_name,
                    'hints_tips': hints_tips,
                    'player_count': len(team_players)
                }
            else:
                # Get all teams
                teams = {}
                for player in players:
                    if player.team_name not in teams:
                        teams[player.team_name] = []
                    teams[player.team_name].append(player)
                
                results = {}
                for team_name, team_players in teams.items():
                    logger.info(f"Getting hints and tips for {team_name} ({len(team_players)} players)")
                    hints_tips = lightweight_llm.get_team_hints_tips(team_name, team_players)
                    results[team_name] = {
                        'hints_tips': hints_tips,
                        'player_count': len(team_players)
                    }
                
                return {
                    'all_teams': True,
                    'teams': results,
                    'total_teams': len(results)
                }
                
        except Exception as e:
            logger.error(f"Failed to get team hints and tips: {e}")
            raise
    
    def run_embedding_filtering(self, force_refresh: bool = False) -> Dict[str, Any]:
        """Run embedding filtering on cached player data with pre-filtering for viable players
        
        Args:
            force_refresh: If True, recompute embeddings even if cached
            
        Returns:
            Dict containing filtered players organized by position
        """
        try:
            logger.info("Running embedding filtering on viable players only...")
            
            # Import embedding filter
            from fpl_optimizer.strategies.embedding_filter import EmbeddingFilter
            
            # Initialize embedding filter
            embedding_filter = EmbeddingFilter(self.config)
            
            # Get structured enriched player data for filtering
            structured_data = self.llm_strategy.get_enriched_player_data(force_refresh=force_refresh)
            
            if not structured_data:
                raise ValueError("No enriched player data found. Please run 'fetch-fpl-players --enrich' first.")
            
            # Apply unified filtering to structured data
            viable_result = self.llm_strategy._get_viable_players_from_enriched(structured_data, for_embeddings=True)
            viable_players = {}
            
            # Convert the positions structure back to a flat dictionary
            for position_players in viable_result['positions'].values():
                for player_name, enriched_string in position_players:
                    viable_players[player_name] = enriched_string
            
            logger.info(f"Using {len(viable_players)} viable players for embedding filtering")
            
            # Apply embedding filtering on viable players only
            filtered_data = embedding_filter.filter_players_by_position(viable_players, force_refresh=force_refresh)
            
            # Group by position using structured data
            positions = {'GK': [], 'DEF': [], 'MID': [], 'FWD': []}
            
            # Get the structured data to access positions directly
            structured_data = self.llm_strategy.get_enriched_player_data(force_refresh=force_refresh)
            
            for player_name, enriched_string in filtered_data.items():
                # Get position from structured data
                if player_name in structured_data and isinstance(structured_data[player_name], dict) and "data" in structured_data[player_name]:
                    position = structured_data[player_name]["data"]["position"]
                    if position in positions:
                        positions[position].append((player_name, enriched_string))
                else:
                    # Fallback to string parsing if structured data not available
                    if ', GK,' in enriched_string:
                        positions['GK'].append((player_name, enriched_string))
                    elif ', DEF,' in enriched_string:
                        positions['DEF'].append((player_name, enriched_string))
                    elif ', MID,' in enriched_string:
                        positions['MID'].append((player_name, enriched_string))
                    elif ', FWD,' in enriched_string:
                        positions['FWD'].append((player_name, enriched_string))
            
            # Create result structure
            result = {
                'total_players_loaded': viable_result['total_players_loaded'],
                'viable_players': viable_result['total_players_filtered'],
                'pre_filtered_out': viable_result['filtered_out_count'],
                'total_players_filtered': len(filtered_data),
                'reduction_percentage': ((viable_result['total_players_loaded'] - len(filtered_data)) / viable_result['total_players_loaded'] * 100),
                'positions': positions,
                'timestamp': datetime.now().isoformat()
            }
            
            logger.info(f"Embedding filtering complete: {len(filtered_data)} players selected from {len(viable_players)} viable players")
            return result
            
        except Exception as e:
            logger.error(f"Failed to run embedding filtering: {e}")
            raise
    
    def enrich_players(self, force_refresh: bool = False) -> Dict[str, Any]:
        """
        Enrich existing player data with LLM insights.
        
        Args:
            force_refresh: If True, ignore cache and fetch fresh enrichment data
            
        Returns:
            Dict containing enrichment results
        """
        logger.info("Starting player data enrichment...")
        
        try:
            # Get enriched player data (this will load existing data and add enrichments)
            enriched_data = self.llm_strategy.get_enriched_player_data(force_refresh=force_refresh)
            
            if not enriched_data:
                return {
                    'error': 'No player data available to enrich',
                    'total_players': 0,
                    'enriched_players': 0
                }
            
            # Format the results for display
            formatted_players = []
            position_distribution = {'GK': 0, 'DEF': 0, 'MID': 0, 'FWD': 0}
            price_range_distribution = {'£0-5m': 0, '£5-7.5m': 0, '£7.5-10m': 0, '£10m+': 0}
            
            for player_name, player_data in enriched_data.items():
                if isinstance(player_data, dict) and "data" in player_data:
                    # Structured data format
                    prompt_text = self.llm_strategy._generate_prompt_text(player_data)
                    formatted_players.append(prompt_text)
                    
                    # Count positions
                    position = player_data["data"]["position"]
                    if position in position_distribution:
                        position_distribution[position] += 1
                    
                    # Count price ranges
                    price = player_data["data"]["price"]
                    if price <= 5.0:
                        price_range_distribution['£0-5m'] += 1
                    elif price <= 7.5:
                        price_range_distribution['£5-7.5m'] += 1
                    elif price <= 10.0:
                        price_range_distribution['£7.5-10m'] += 1
                    else:
                        price_range_distribution['£10m+'] += 1
                else:
                    # Legacy text format
                    formatted_players.append(player_data)
            
            return {
                'players': [],  # Empty list for compatibility with display function
                'teams': [],    # Empty list for compatibility with display function
                'summary': {
                    'total_players': len(enriched_data),
                    'total_teams': 20,  # Fixed number for FPL
                    'enriched_players': len(enriched_data),
                    'position_distribution': position_distribution,
                    'price_range_distribution': price_range_distribution,
                    'data_source': 'FPL API (enriched with LLM)',
                    'fetched_at': datetime.now().isoformat()
                },
                'formatted_players': formatted_players,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to enrich players: {e}")
            return {
                'error': f'Failed to enrich players: {e}',
                'total_players': 0,
                'enriched_players': 0
            }

    def filter_viable_players(self, force_refresh: bool = False) -> Dict[str, Any]:
        """Filter player data to only include viable FPL players
        
        Filters out players who are:
        - "Out" according to injury news
        - "Avoid" according to FPL suggestions
        
        Args:
            force_refresh: If True, ignore cache and fetch fresh data
            
        Returns:
            Dict containing filtered players organized by position
        """
        try:
            logger.info("Filtering player data for viable FPL players...")
            
            # Get enriched player data from cache
            enriched_data = self.llm_strategy.get_enriched_player_data(force_refresh=force_refresh)
            
            if not enriched_data:
                raise ValueError("No enriched player data found in cache. Please run 'fetch-fpl-players' first.")
            
            logger.info(f"Loaded {len(enriched_data)} players from cache")
            
            # Filter players based on injury status and FPL recommendations
            viable_players = {}
            filtered_out_count = 0
            
            # Get structured data for filtering
            structured_data = self.llm_strategy.get_enriched_player_data(force_refresh=force_refresh)
            
            for player_name, enriched_string in enriched_data.items():
                player_data = structured_data[player_name]
                data = player_data.get('data', {})
                injury_news = player_data.get('injury_news', '')
                hints_tips = player_data.get('hints_tips_news', '')
                
                # Check if player should be filtered out
                should_exclude = False
                exclusion_reason = ""
                
                # Check injury status
                if injury_news.startswith("Out"):
                    should_exclude = True
                    exclusion_reason = "Injured (Out)"
                
                # Check FPL recommendations
                if hints_tips.startswith("Avoid"):
                    should_exclude = True
                    exclusion_reason = "FPL Avoid"
                
                # Include player if they pass both filters
                if not should_exclude:
                    viable_players[player_name] = enriched_string
                else:
                    filtered_out_count += 1
            
            # Group by position
            positions = {'GK': [], 'DEF': [], 'MID': [], 'FWD': []}
            
            for player_name, enriched_string in viable_players.items():
                # Extract position from the enriched string
                if '(GK,' in enriched_string:
                    positions['GK'].append((player_name, enriched_string))
                elif '(DEF,' in enriched_string:
                    positions['DEF'].append((player_name, enriched_string))
                elif '(MID,' in enriched_string:
                    positions['MID'].append((player_name, enriched_string))
                elif '(FWD,' in enriched_string:
                    positions['FWD'].append((player_name, enriched_string))
            
            # Create result structure
            result = {
                'total_players_loaded': len(enriched_data),
                'total_players_filtered': len(viable_players),
                'filtered_out_count': filtered_out_count,
                'reduction_percentage': ((len(enriched_data) - len(viable_players)) / len(enriched_data) * 100),
                'positions': positions,
                'timestamp': datetime.now().isoformat()
            }
            
            logger.info(f"Viable player filtering complete: {len(viable_players)} players selected from {len(enriched_data)} total (filtered out {filtered_out_count})")
            return result
            
        except Exception as e:
            logger.error(f"Failed to filter viable players: {e}")
            raise


def main():
    """Main entry point with enhanced command options"""
    parser = argparse.ArgumentParser(description='FPL Optimizer with Dual Approaches')
    
    # Main command
    parser.add_argument('command', choices=[
        'fetch', 'fetch-fpl-players', 'enrich-players', 'create-model', 'create-team-llm', 'weekly-model', 'weekly-llm', 
        'update-team', 'load-team', 'list-teams', 'validate-team', 'team-injuries', 'team-hints', 'embedding-filter', 'filter-viable'
    ], help='Command to run')
    
    # Common arguments
    parser.add_argument('--sample-size', type=int, default=0, 
                       help='Number of players to sample/limit (default: 0 = all players, specify number to limit)')
    parser.add_argument('--config', type=str, help='Path to config file')
    parser.add_argument('--budget', type=float, default=100.0,
                       help='Team budget in millions (default: 100.0)')
    parser.add_argument('--gameweek', type=int, 
                       help='Current gameweek (for LLM context)')
    parser.add_argument('--free-transfers', type=int, default=1,
                       help='Number of free transfers available (default: 1)')
    
    # Team file for weekly commands
    parser.add_argument('--team-file', type=str,
                       help='Path to JSON file containing current team data')
    parser.add_argument('--latest-team', action='store_true',
                       help='Use the most recently created team file')
    
    # Team analysis arguments
    parser.add_argument('--team-name', type=str,
                       help='Specific team name for analysis (e.g., "Chelsea", "Arsenal")')
    

    
    # Save options
    parser.add_argument('--save-team', action='store_true',
                       help='Save the created team to a JSON file')
    parser.add_argument('--save-file', type=str,
                       help='Specific file path to save team (if not provided, auto-generates filename)')
    
    # Debug options
    parser.add_argument('--show-prompt', action='store_true',
                       help='Show the LLM prompt without executing (for debugging)')
    
    # Semantic filtering option
    parser.add_argument('--semantic-filtering', action='store_true',
                       help='Use enriched player data with injury news and FPL suggestions for semantic filtering')
    
    # Embedding filtering option
    parser.add_argument('--use-embeddings', action='store_true',
                       help='Use embedding-based filtering to select top players per position (requires --semantic-filtering)')
    
    # Force refresh option
    parser.add_argument('--force-refresh', action='store_true',
                       help='Force refresh of cached data (player data, embeddings, etc.)')
    
    # Enrichment option
    parser.add_argument('--enrich', action='store_true',
                       help='Enrich player data with injury news and FPL hints (requires LLM calls, takes 15-20 minutes)')
    
    args = parser.parse_args()
    
    try:
        optimizer = FPLOptimizer(args.config)
        
        if args.command == 'fetch':
            # Just fetch and display data
            result = optimizer.fetch_data(args.sample_size)
            display_player_data(result)
            
        elif args.command == 'fetch-fpl-players':
            # Fetch real FPL data from API
            result = optimizer.fetch_fpl_players(args.sample_size, args.enrich, args.force_refresh)
            display_player_data(result)
            
        elif args.command == 'enrich-players':
            # Enrich existing player data with LLM insights
            result = optimizer.enrich_players(args.force_refresh)
            display_player_data(result)
            
        elif args.command == 'create-model':
            # Create team using model approach
            result = optimizer.create_team_model(args.budget, args.sample_size)
            display_team_creation_result(result)
            
        elif args.command == 'create-team-llm':
            # Create team using comprehensive LLM approach
            if args.show_prompt:
                # Show the prompt without executing
                prompt = optimizer.llm_strategy._create_team_creation_prompt(args.budget, args.gameweek or 1, args.semantic_filtering, args.force_refresh, args.use_embeddings)
                print("\n" + "="*80)
                print("LLM TEAM CREATION PROMPT (DEBUG MODE)")
                print("="*80)
                print(prompt)
                print("="*80)
            else:
                # Execute normally
                result = optimizer.create_team_llm(args.budget, args.gameweek, args.semantic_filtering, args.force_refresh, args.use_embeddings)
                display_comprehensive_team_result(result)
                
                # Save team if requested
                if args.save_team:
                    try:
                        team_data = result['team_data']
                        saved_file = save_team_to_json(team_data, args.save_file)
                        print(f"\n" + "="*80)
                        print("TEAM SAVED")
                        print("="*80)
                        print(f"Team saved to: {saved_file}")
                        print("="*80)
                    except Exception as e:
                        logger.error(f"Failed to save team: {e}")
                        print(f"\nError saving team: {e}")
            
        elif args.command == 'update-team':
            # Update team weekly using comprehensive LLM team manager
            result = optimizer.update_team_weekly_comprehensive(args.gameweek, args.semantic_filtering, args.force_refresh, args.use_embeddings)
            display_comprehensive_team_result(result)
            
        elif args.command == 'weekly-model':
            # Weekly recommendations using model approach
            team_file = args.team_file
            if args.latest_team:
                team_file = get_latest_team_file()
                if team_file:
                    print(f"Using latest team: {os.path.basename(team_file)}")
            
            current_team = load_team_from_file(team_file) if team_file else create_sample_team()
            result = optimizer.get_weekly_recommendations_model(current_team, args.free_transfers)
            display_weekly_recommendations(result)
            
        elif args.command == 'weekly-llm':
            # Weekly recommendations using LLM approach
            team_file = args.team_file
            if args.latest_team:
                team_file = get_latest_team_file()
                if team_file:
                    print(f"Using latest team: {os.path.basename(team_file)}")
            
            current_team = load_team_from_file(team_file) if team_file else create_sample_team()
            result = optimizer.get_weekly_recommendations_llm(current_team, args.free_transfers, args.gameweek)
            display_weekly_recommendations(result)
            
        elif args.command == 'load-team':
            # Load and display a saved team
            team_file = args.team_file
            
            if args.latest_team:
                team_file = get_latest_team_file()
                if not team_file:
                    print("Error: No saved teams found")
                    sys.exit(1)
                print(f"Loading latest team: {os.path.basename(team_file)}")
            elif not args.team_file:
                print("Error: --team-file is required for load-team command (or use --latest-team)")
                sys.exit(1)
            
            try:
                saved_team_data = load_team_from_json(team_file)
                
                # Convert saved format back to the format expected by display function
                team_data = {
                    'captain': saved_team_data.get('team_info', {}).get('captain'),
                    'vice_captain': saved_team_data.get('team_info', {}).get('vice_captain'),
                    'total_cost': saved_team_data.get('team_info', {}).get('total_cost', 0.0),
                    'bank': saved_team_data.get('team_info', {}).get('bank', 0.0),
                    'expected_points': saved_team_data.get('team_info', {}).get('expected_points', 0.0),
                    'team': {
                        'starting': saved_team_data.get('squad', {}).get('starting_11', []),
                        'substitutes': saved_team_data.get('squad', {}).get('substitutes', [])
                    },
                    'raw_llm_response': saved_team_data.get('raw_llm_response', ''),
                    # Add reasoning fields
                    'captain_reason': saved_team_data.get('reasoning', {}).get('captain_reason', ''),
                    'vice_captain_reason': saved_team_data.get('reasoning', {}).get('vice_captain_reason', ''),
                    'chip_reason': saved_team_data.get('reasoning', {}).get('chip_reason', ''),
                    'transfers': saved_team_data.get('reasoning', {}).get('transfers', [])
                }
                
                display_comprehensive_team_result({'team_data': team_data})
            except Exception as e:
                logger.error(f"Failed to load team: {e}")
                sys.exit(1)
            
        elif args.command == 'list-teams':
            team_files = list_saved_teams()
            if not team_files:
                print("No saved teams found.")
            else:
                print("\n" + "="*80)
                print("SAVED TEAMS")
                print("="*80)
                for file_path in team_files:
                    print(f"- {os.path.basename(file_path)}")
                print("="*80)
        
        elif args.command == 'validate-team':
            # Validate existing team data
            try:
                from .utils.validator import FPLValidator
                from .core.team_manager import TeamManager
                
                print("\n" + "="*80)
                print("FPL TEAM VALIDATION")
                print("="*80)
                
                # Create validator and team manager
                validator = FPLValidator("team_data")
                team_manager = TeamManager("team_data")
                
                # Determine which gameweek to validate
                gameweek = args.gameweek
                if not gameweek:
                    # Try to find the latest gameweek
                    latest_gw = team_manager.get_latest_gameweek()
                    if latest_gw:
                        gameweek = latest_gw
                        print(f"Validating latest team (Gameweek {gameweek})")
                    else:
                        print("❌ No team files found in team_data directory")
                        sys.exit(1)
                else:
                    print(f"Validating team for Gameweek {gameweek}")
                
                # Check if team file exists
                team_file = Path(f"team_data/gw{gameweek:02d}.json")
                if not team_file.exists():
                    print(f"❌ Team file gw{gameweek:02d}.json not found")
                    sys.exit(1)
                
                # Load and validate team data
                print(f"\n1. Loading and validating gw{gameweek:02d}.json...")
                
                with open(team_file, 'r') as f:
                    team_data = json.load(f)
                
                print(f"✓ Loaded team data for Gameweek {team_data.get('gameweek', 'Unknown')}")
                
                # Validate team data
                validation_errors = validator.validate_team_data(team_data['team'], gameweek)
                
                if validation_errors:
                    print("❌ Team validation failed:")
                    for error in validation_errors:
                        print(f"  - {error}")
                    sys.exit(1)
                else:
                    print("✓ Team validation passed")
                
                # Display team summary
                print(f"\n2. Team Summary:")
                team = team_data['team']
                print(f"   Captain: {team.get('captain', 'Unknown')}")
                print(f"   Vice Captain: {team.get('vice_captain', 'Unknown')}")
                print(f"   Total Cost: £{team.get('total_cost', 0)}m")
                print(f"   Bank: £{team.get('bank', 0)}m")
                print(f"   Expected Points: {team.get('expected_points', 0)}")
                
                # Count players by position
                all_players = team.get('team', {}).get('starting', []) + team.get('team', {}).get('substitutes', [])
                position_counts = {'GK': 0, 'DEF': 0, 'MID': 0, 'FWD': 0}
                team_counts = {}
                
                for player in all_players:
                    position = player.get('position')
                    if position in position_counts:
                        position_counts[position] += 1
                    
                    team_name = player.get('team')
                    if team_name:
                        team_counts[team_name] = team_counts.get(team_name, 0) + 1
                
                print(f"   Squad: {position_counts['GK']} GK, {position_counts['DEF']} DEF, {position_counts['MID']} MID, {position_counts['FWD']} FWD")
                print(f"   Teams: {len(team_counts)} different teams")
                
                # Show formation
                starting = team.get('team', {}).get('starting', [])
                starting_positions = {'GK': 0, 'DEF': 0, 'MID': 0, 'FWD': 0}
                for player in starting:
                    position = player.get('position')
                    if position in starting_positions:
                        starting_positions[position] += 1
                
                formation = f"{starting_positions['DEF']}-{starting_positions['MID']}-{starting_positions['FWD']}"
                print(f"   Formation: {formation}")
                
                # Check meta.json
                print(f"\n3. Checking meta.json...")
                meta_file = Path("team_data/meta.json")
                if meta_file.exists():
                    with open(meta_file, 'r') as f:
                        meta_data = json.load(f)
                    
                    print("✓ meta.json found")
                    meta_current_gw = meta_data.get('current_gw', 'Unknown')
                    print(f"   Current GW: {meta_current_gw}")
                    print(f"   Last Team File: {meta_data.get('last_team_file', 'Unknown')}")
                    print(f"   Bank: £{meta_data.get('bank', 0)}m")
                    print(f"   Free Transfers: {meta_data.get('free_transfers', 0)}")
                    
                    # Check if meta.json is for a different gameweek
                    if meta_current_gw != 'Unknown' and meta_current_gw != gameweek:
                        print(f"\n⚠️  WARNING: meta.json is for Gameweek {meta_current_gw}, but you're validating Gameweek {gameweek}")
                        print(f"   This means you're validating a historical team, not the current team.")
                        print(f"   The meta.json reflects the current state after Gameweek {meta_current_gw}.")
                        
                        # Ask if they want to continue
                        print(f"\n   Do you want to continue validating the historical team? (y/N): ", end="")
                        try:
                            response = input().strip().lower()
                            if response not in ['y', 'yes']:
                                print("Validation cancelled.")
                                sys.exit(0)
                        except KeyboardInterrupt:
                            print("\nValidation cancelled.")
                            sys.exit(0)
                    
                    # Validate file consistency (only if meta.json matches the gameweek being validated)
                    if meta_current_gw == gameweek:
                        print(f"\n4. Validating file consistency...")
                        consistency_errors = validator.validate_files_consistency(gameweek)
                        
                        if consistency_errors:
                            print("❌ File consistency validation failed:")
                            for error in consistency_errors:
                                print(f"  - {error}")
                            sys.exit(1)
                        else:
                            print("✓ File consistency validation passed")
                    else:
                        print(f"\n4. Skipping file consistency validation (meta.json is for GW{meta_current_gw}, validating GW{gameweek})")
                        
                else:
                    print("⚠️  meta.json not found - creating it now...")
                    team_manager.initialize_meta(gameweek, team_data['team'])
                    print("✓ meta.json created successfully")
                    
                    # Now validate consistency since we just created meta.json
                    print(f"\n4. Validating file consistency...")
                    consistency_errors = validator.validate_files_consistency(gameweek)
                    
                    if consistency_errors:
                        print("❌ File consistency validation failed:")
                        for error in consistency_errors:
                            print(f"  - {error}")
                        sys.exit(1)
                    else:
                        print("✓ File consistency validation passed")
                
                print(f"\n🎉 All validations passed! Team data is ready for use.")
                print("="*80)
                
            except Exception as e:
                logger.error(f"Team validation failed: {e}")
                print(f"❌ Validation failed: {e}")
                sys.exit(1)
            
        elif args.command == 'team-injuries':
            # Get team injury news
            result = optimizer.get_team_injury_news(args.team_name)
            display_team_injury_news(result)
            
        elif args.command == 'team-hints':
            # Get team hints and tips
            result = optimizer.get_team_hints_tips(args.team_name)
            display_team_hints_tips(result)
            
        elif args.command == 'embedding-filter':
            # Run embedding filtering on cached player data
            result = optimizer.run_embedding_filtering(args.force_refresh)
            display_embedding_filtering_result(result)
            
        elif args.command == 'filter-viable':
            # Filter player data for viable FPL players only
            result = optimizer.filter_viable_players(args.force_refresh)
            display_viable_players_result(result)
            

            

        
    except Exception as e:
        logger.error(f"Command failed: {e}")
        sys.exit(1)


def display_player_data(result):
    """Display fetched player data"""
    print("\n" + "="*60)
    print("FPL PLAYER DATA FETCHED")
    print("="*60)
    
    # Print summary
    summary = result['summary']
    print(f"\nData Summary:")
    print(f"  Players: {summary['total_players']}")
    print(f"  Teams: {summary['total_teams']}")
    
    # Show data source if available
    if 'data_source' in summary:
        print(f"  Data Source: {summary['data_source']}")
    if 'fetched_at' in summary:
        print(f"  Fetched At: {summary['fetched_at']}")
    if 'enriched_with_llm' in summary:
        if summary['enriched_with_llm']:
            print(f"  ✅ Enriched with LLM data: {summary.get('enriched_players_count', 0)} players")
        else:
            print(f"  ❌ LLM enrichment failed or not requested")
    
    print(f"\nPosition Distribution:")
    for pos, count in summary['position_distribution'].items():
        print(f"  {pos}: {count}")
    
    print(f"\nPrice Range Distribution:")
    for price_range, count in summary['price_range_distribution'].items():
        print(f"  {price_range}: {count}")
    
    # Print detailed player table
    print(f"\n" + "="*120)
    print("DETAILED PLAYER DATA TABLE")
    print("="*120)
    
    # Header
    print(f"{'Name':<25} {'Team':<15} {'Pos':<4} {'Price':<6} {'Chance':<6} {'Form':<6} {'Total Pts':<10} {'Pts/Game':<8} {'Selected %':<10}")
    print("-" * 110)
    print("Note: 'Chance' shows likelihood of playing this gameweek (100% = Available during off-season)")
    print("-" * 110)
    
    # Sort players: club alphabetically, then position (GK, DEF, MID, FWD), then player name alphabetically
    position_order = {'GK': 0, 'DEF': 1, 'MID': 2, 'FWD': 3}
    sorted_players = sorted(result['players'], 
                          key=lambda p: (p.team_name, position_order[p.position.value], p.name))
    
    for player in sorted_players:
        # Get chance of playing from custom_data
        chance_of_playing = player.custom_data.get('chance_of_playing')
        if chance_of_playing is None:
            chance_str = "100%"  # Available (default during off-season)
        else:
            chance_str = f"{chance_of_playing}%"
        
        print(f"{player.name:<25} {player.team_name:<15} {player.position.value:<4} £{player.price:<5.1f} {chance_str:<6} {player.form:<6} {player.total_points:<10} {player.points_per_game:<8} {player.selected_by_percent:<10}")
    
    print(f"\nData fetch completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


def display_comprehensive_team_result(result):
    """Display comprehensive team creation/update results"""
    print("\n" + "="*80)
    print("FPL COMPREHENSIVE TEAM RESULT")
    print("="*80)
    
    # Check if this is a team_data result (from create-team-llm) or a direct result
    if isinstance(result, dict) and 'team_data' in result:
        # This is from create-team-llm, show the LLM response
        print(f"\n" + "="*80)
        print("LLM RESPONSE")
        print("="*80)
        print("Method: " + result.get('method', 'Unknown'))
        
        team_data = result['team_data']
        
        # Display basic team info
        print(f"\nCaptain: {team_data.get('captain', 'Not set')}")
        print(f"Vice Captain: {team_data.get('vice_captain', 'Not set')}")
        print(f"Total Cost: £{team_data.get('total_cost', 0):.1f}m")
        print(f"Bank: £{team_data.get('bank', 0):.1f}m")
        print(f"Expected Points: {team_data.get('expected_points', 0):.1f}")
        
        # Display team reasoning summary
        print(f"\n" + "="*80)
        print("TEAM SELECTION REASONING")
        print("="*80)
        
        # Show raw LLM response if available
        if 'raw_llm_response' in team_data:
            print(f"\n" + "="*80)
            print("RAW LLM RESPONSE")
            print("="*80)
            print(team_data['raw_llm_response'])
            print("="*80)
    else:
        # Direct result (from update-team)
        print(f"\nCaptain: {result.get('captain', 'Not set')}")
        print(f"Vice Captain: {result.get('vice_captain', 'Not set')}")
        print(f"Total Cost: £{result.get('total_cost', 0):.1f}m")
        print(f"Bank: £{result.get('bank', 0):.1f}m")
        print(f"Expected Points: {result.get('expected_points', 0):.1f}")
    
    # Display chip/wildcard usage if present
    if 'wildcard_or_chip' in result and result['wildcard_or_chip']:
        print(f"\n" + "="*80)
        print("CHIP/WILDCARD USAGE")
        print("="*80)
        print(f"Chip Used: {result['wildcard_or_chip']}")
        if 'chip_reason' in result:
            print(f"Reason: {result['chip_reason']}")
        print("="*80)
    
    # Display transfers if present
    if 'transfers' in result and result['transfers']:
        print(f"\n" + "="*80)
        print("TRANSFERS")
        print("="*80)
        for transfer in result['transfers']:
            print(f"OUT: {transfer.get('out', 'Unknown')}")
            print(f"IN:  {transfer.get('in', 'Unknown')}")
            if 'reason' in transfer:
                print(f"Reason: {transfer['reason']}")
            print("-" * 80)
    
    # Display captaincy reasoning if present
    if 'captain_reason' in result or 'vice_captain_reason' in result:
        print(f"\n" + "="*80)
        print("CAPTAINCY REASONING")
        print("="*80)
        if 'captain_reason' in result:
            print(f"Captain ({result.get('captain', 'Unknown')}): {result['captain_reason']}")
        if 'vice_captain_reason' in result:
            print(f"Vice Captain ({result.get('vice_captain', 'Unknown')}): {result['vice_captain_reason']}")
        print("="*80)
    
    # Get the correct team data structure
    team_data_to_display = None
    if isinstance(result, dict) and 'team_data' in result:
        team_data_to_display = result['team_data']
    else:
        team_data_to_display = result
    
    # Display starting 11
    if 'team' in team_data_to_display and 'starting' in team_data_to_display['team']:
        print(f"\n" + "="*80)
        print("STARTING 11")
        print("="*80)
        print(f"{'Name':<25} {'Team':<15} {'Pos':<4} {'Price':<6}")
        print("-" * 80)
        
        for player in team_data_to_display['team']['starting']:
            captain_marker = " (C)" if player.get('name') == team_data_to_display.get('captain') else ""
            vice_marker = " (VC)" if player.get('name') == team_data_to_display.get('vice_captain') else ""
            markers = captain_marker + vice_marker
            print(f"{player.get('name', 'Unknown') + markers:<25} {player.get('team', 'Unknown'):<15} {player.get('position', 'Unknown'):<4} £{player.get('price', 0):<5.1f}")
            
            # Display reasoning if available
            if 'reason' in player:
                print(f"  └─ {player['reason']}")
        
        print("-" * 80)
    
    # Display substitutes
    if 'team' in team_data_to_display and 'substitutes' in team_data_to_display['team']:
        print(f"\n" + "="*80)
        print("SUBSTITUTES")
        print("="*80)
        print(f"{'Name':<25} {'Team':<15} {'Pos':<4} {'Price':<6} {'Sub Order':<10}")
        print("-" * 80)
        
        for player in team_data_to_display['team']['substitutes']:
            sub_order = player.get('sub_order', 'GK')
            sub_order_str = str(sub_order) if sub_order is not None else 'GK'
            print(f"{player.get('name', 'Unknown'):<25} {player.get('team', 'Unknown'):<15} {player.get('position', 'Unknown'):<4} £{player.get('price', 0):<5.1f} {sub_order_str:<10}")
            
            # Display reasoning if available
            if 'reason' in player:
                print(f"  └─ {player['reason']}")
        
        print("-" * 80)
    
    print(f"\nComprehensive team operation completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


def display_team_creation_result(result):
    """Display team creation results"""
    print("\n" + "="*80)
    print(f"FPL TEAM CREATION COMPLETE - {result['method']}")
    print("="*80)
    
    opt_result = result['optimization_result']
    
    # Display selected team
    if hasattr(opt_result, 'selected_players') and opt_result.selected_players:
        print(f"\n" + "="*100)
        print("SELECTED TEAM")
        print("="*100)
        print(f"{'Name':<25} {'Team':<15} {'Pos':<4} {'Price':<6} {'Form':<6} {'Total Pts':<10} {'Captain':<8}")
        print("-" * 100)
        
        total_cost = 0
        for player in opt_result.selected_players:
            is_captain = "C" if hasattr(opt_result, 'captain_id') and opt_result.captain_id == player.id else ""
            is_vice = "VC" if hasattr(opt_result, 'vice_captain_id') and opt_result.vice_captain_id == player.id else ""
            captain_status = is_captain or is_vice
            
            print(f"{player.name:<25} {player.team_name:<15} {player.position.value:<4} £{player.price:<5.1f} {player.form:<6.1f} {player.total_points:<10} {captain_status:<8}")
            total_cost += player.price
        
        print(f"\nTeam Cost: £{total_cost:.1f}m")
        print(f"Expected Points: {opt_result.expected_points:.1f}")
        print(f"Confidence: {opt_result.confidence:.2f}")
    
    # Display reasoning
    if hasattr(opt_result, 'reasoning') and opt_result.reasoning:
        print(f"\n" + "="*80)
        print("REASONING")
        print("="*80)
        print(opt_result.reasoning)
    
    # Display LLM insights if available
    if hasattr(opt_result, 'llm_insights') and opt_result.llm_insights:
        print(f"\n" + "="*80)
        print("EXPERT INSIGHTS USED")
        print("="*80)
        print(opt_result.llm_insights)
    
    print(f"\nTeam creation completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


def display_weekly_recommendations(result):
    """Display weekly recommendations"""
    print("\n" + "="*80)
    print("FPL WEEKLY RECOMMENDATIONS")
    print("="*80)
    
    # Display basic info
    print(f"Method: {result.get('method', 'Unknown')}")
    print(f"Gameweek: {result.get('gameweek', 'Unknown')}")
    print(f"Free Transfers: {result.get('free_transfers', 'Unknown')}")
    
    # Display transfers if any
    transfers = result.get('transfers', [])
    if transfers:
        print(f"\nTransfers ({len(transfers)}):")
        for i, transfer in enumerate(transfers, 1):
            print(f"  {i}. {transfer.get('out', 'Unknown')} → {transfer.get('in', 'Unknown')}")
            if 'reason' in transfer:
                print(f"     Reason: {transfer['reason']}")
    else:
        print("\nNo transfers recommended")
    
    # Display team changes
    team_changes = result.get('team_changes', {})
    if team_changes:
        print(f"\nTeam Changes:")
        for change_type, details in team_changes.items():
            print(f"  {change_type}: {details}")
    
    # Display reasoning
    reasoning = result.get('reasoning', '')
    if reasoning:
        print(f"\nReasoning:")
        print(reasoning)
    
    print("="*80)


def display_team_injury_news(result):
    """Display team injury news results"""
    print("\n" + "="*80)
    print("FPL TEAM INJURY NEWS")
    print("="*80)
    
    if result.get('all_teams', False):
        # Display all teams
        print(f"Analyzed {result['total_teams']} teams")
        print()
        
        for team_name, team_data in result['teams'].items():
            print(f"{'='*60}")
            print(f"TEAM: {team_name.upper()}")
            print(f"Players: {team_data['player_count']}")
            print(f"{'='*60}")
            print(team_data['injury_news'])
            print()
    else:
        # Display single team
        print(f"Team: {result['team_name']}")
        print(f"Players: {result['player_count']}")
        print()
        print(result['injury_news'])
    
    print("="*80)


def display_team_hints_tips(result):
    """Display team hints and tips results"""
    print("\n" + "="*80)
    print("FPL TEAM HINTS & TIPS")
    print("="*80)
    
    if result.get('all_teams', False):
        # Display all teams
        print(f"Analyzed {result['total_teams']} teams")
        print()
        
        for team_name, team_data in result['teams'].items():
            print(f"{'='*60}")
            print(f"TEAM: {team_name.upper()}")
            print(f"Players: {team_data['player_count']}")
            print(f"{'='*60}")
            print(team_data['hints_tips'])
            print()
    else:
        # Display single team
        print(f"Team: {result['team_name']}")
        print(f"Players: {result['player_count']}")
        print()
        print(result['hints_tips'])
    
    print("="*80)


def _get_structured_player_data(player_name: str) -> Dict[str, Any]:
    """Helper function to get structured player data from cache"""
    # Cache the structured data to avoid repeated lookups
    if not hasattr(_get_structured_player_data, '_cached_data'):
        from fpl_optimizer.strategies.llm_strategy import LLMStrategy
        from fpl_optimizer.core.config import Config
        
        # Create a minimal config and strategy to access cached data
        config = Config()
        strategy = LLMStrategy(config)
        _get_structured_player_data._cached_data = strategy.get_enriched_player_data(force_refresh=False)
    
    cached_data = _get_structured_player_data._cached_data
    return cached_data[player_name]

def display_embedding_filtering_result(result):
    """Display embedding filtering results"""
    print("\n" + "="*80)
    print("EMBEDDING FILTERING RESULTS")
    print("="*80)
    
    # Summary
    print(f"Total players loaded: {result['total_players_loaded']}")
    if 'viable_players' in result:
        print(f"Viable players (after pre-filtering): {result['viable_players']}")
        print(f"Pre-filtered out: {result['pre_filtered_out']} (Injured 'Out' or FPL 'Avoid')")
    print(f"Final filtered players: {result['total_players_filtered']}")
    print(f"Total reduction: {result['reduction_percentage']:.1f}%")
    print(f"Timestamp: {result['timestamp']}")
    
    # Display by position
    positions = result['positions']
    
    for position, players in positions.items():
        print(f"\n{position} ({len(players)} players):")
        print("-" * 60)
        
        for i, (player_name, enriched_string) in enumerate(players, 1):
            # Try to get structured data for display
            player_data = _get_structured_player_data(player_name)
            
            if player_data:
                # Use structured data for display
                data = player_data["data"]
                
                stats_line = f"Stats: Chance of Playing - {data.get('chance_of_playing', 'N/A')}%, PPG - {data.get('ppg', 0):.1f}, Form - {data.get('form', 0):.1f}, Minutes - {data.get('minutes_played', 0)}, Fixture Difficulty - {data.get('fixture_difficulty', 'N/A')}, Ownership - {data.get('ownership_percent', 0):.1f}%."
                injury_line = f"Injury News: {player_data.get('injury_news', 'N/A')}"
                hints_line = f"FPL Suggestions: {player_data.get('hints_tips_news', 'N/A')}"
            else:
                # Fallback to string parsing for legacy data
                lines = enriched_string.split('\n')
                stats_line = lines[1] if len(lines) > 1 else ""
                injury_line = lines[2] if len(lines) > 2 else ""
                hints_line = lines[3] if len(lines) > 3 else ""
            
            print(f"{i:2d}. {player_name}")
            print(f"    {stats_line}")
            print(f"    {injury_line}")
            print(f"    {hints_line}")
            print()
    
    print("="*80)


def display_viable_players_result(result):
    """Display viable players filtering results"""
    print("\n" + "="*80)
    print("VIABLE PLAYERS FILTERING RESULTS")
    print("="*80)
    
    # Summary
    print(f"Total players loaded: {result['total_players_loaded']}")
    print(f"Viable players: {result['total_players_filtered']}")
    print(f"Filtered out: {result['filtered_out_count']} (Injured 'Out' or FPL 'Avoid')")
    print(f"Reduction: {result['reduction_percentage']:.1f}%")
    print(f"Timestamp: {result['timestamp']}")
    
    # Display by position
    positions = result['positions']
    
    for position, players in positions.items():
        print(f"\n{position} ({len(players)} players):")
        print("-" * 60)
        
        for i, (player_name, enriched_string) in enumerate(players, 1):
            # Try to get structured data for display
            player_data = _get_structured_player_data(player_name)
            
            if player_data:
                # Use structured data for display
                data = player_data["data"]
                
                stats_line = f"Stats: Chance of Playing - {data.get('chance_of_playing', 'N/A')}%, PPG - {data.get('ppg', 0):.1f}, Form - {data.get('form', 0):.1f}, Minutes - {data.get('minutes_played', 0)}, Fixture Difficulty - {data.get('fixture_difficulty', 'N/A')}, Ownership - {data.get('ownership_percent', 0):.1f}%."
                injury_line = f"Injury News: {player_data.get('injury_news', 'N/A')}"
                hints_line = f"FPL Suggestions: {player_data.get('hints_tips_news', 'N/A')}"
            else:
                # Fallback to string parsing for legacy data
                lines = enriched_string.split('\n')
                stats_line = lines[1] if len(lines) > 1 else ""
                injury_line = lines[2] if len(lines) > 2 else ""
                hints_line = lines[3] if len(lines) > 3 else ""
            
            print(f"{i:2d}. {player_name}")
            print(f"    {stats_line}")
            print(f"    {injury_line}")
            print(f"    {hints_line}")
            print()
    
    print("="*80)


def save_team_to_json(team_data: Dict[str, Any], file_path: Optional[str] = None) -> str:
    """
    Save team data to a JSON file aligned with FPL API structure.
    
    Args:
        team_data: Team data from LLM strategy
        file_path: Optional file path, if not provided will generate one
        
    Returns:
        Path to the saved file
    """
    if file_path is None:
        # Generate filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_path = f"fpl_team_{timestamp}.json"
    
    # Ensure output directory exists
    output_dir = "output/teams"
    os.makedirs(output_dir, exist_ok=True)
    
    # If only filename provided, prepend output directory
    if not os.path.dirname(file_path):
        file_path = os.path.join(output_dir, file_path)
    
    # Create FPL API-aligned structure
    fpl_team_data = {
        "team_info": {
            "captain": team_data.get('captain'),
            "vice_captain": team_data.get('vice_captain'),
            "total_cost": team_data.get('total_cost', 0.0),
            "bank": team_data.get('bank', 0.0),
            "expected_points": team_data.get('expected_points', 0.0),
            "created_at": datetime.now().isoformat(),
            "gameweek": 1  # Default to GW1 for new teams
        },
        "squad": {
            "starting_11": [],
            "substitutes": []
        },
        "formation": [3, 4, 3],  # Default formation
        "chips": {
            "wildcard_used": False,
            "free_hit_used": False,
            "triple_captain_used": False,
            "bench_boost_used": False
        },
        "transfers": {
            "free_transfers": 1,
            "transfer_hits": 0,
            "transfers_made": []
        },
        "reasoning": {
            "captain_reason": team_data.get('captain_reason', ''),
            "vice_captain_reason": team_data.get('vice_captain_reason', ''),
            "chip_reason": team_data.get('chip_reason', ''),
            "transfers": []
        }
    }
    
    # Process starting 11
    if 'team' in team_data and 'starting' in team_data['team']:
        for player in team_data['team']['starting']:
            fpl_player = {
                "name": player.get('name'),
                "position": player.get('position'),
                "team": player.get('team'),
                "price": player.get('price', 0.0),
                "is_captain": player.get('name') == team_data.get('captain'),
                "is_vice_captain": player.get('name') == team_data.get('vice_captain'),
                "is_starting": True,
                "reason": player.get('reason', '')
            }
            fpl_team_data["squad"]["starting_11"].append(fpl_player)
    
    # Process substitutes
    if 'team' in team_data and 'substitutes' in team_data['team']:
        for player in team_data['team']['substitutes']:
            fpl_player = {
                "name": player.get('name'),
                "position": player.get('position'),
                "team": player.get('team'),
                "price": player.get('price', 0.0),
                "sub_order": player.get('sub_order'),
                "is_starting": False,
                "reason": player.get('reason', '')
            }
            fpl_team_data["squad"]["substitutes"].append(fpl_player)
    
    # Process transfers with reasoning
    if 'transfers' in team_data and team_data['transfers']:
        for transfer in team_data['transfers']:
            transfer_data = {
                "out": transfer.get('out'),
                "in": transfer.get('in'),
                "reason": transfer.get('reason', '')
            }
            fpl_team_data["reasoning"]["transfers"].append(transfer_data)
            fpl_team_data["transfers"]["transfers_made"].append(transfer_data)
    
    # Add raw LLM response for reference
    if 'raw_llm_response' in team_data:
        fpl_team_data["raw_llm_response"] = team_data['raw_llm_response']
    
    # Save to file
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(fpl_team_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Team saved to: {file_path}")
        return file_path
        
    except Exception as e:
        logger.error(f"Failed to save team to {file_path}: {e}")
        raise

def load_team_from_json(file_path: str) -> Dict[str, Any]:
    """
    Load team data from a JSON file.
    
    Args:
        file_path: Path to the JSON file
        
    Returns:
        Team data dictionary
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            team_data = json.load(f)
        
        logger.info(f"Team loaded from: {file_path}")
        return team_data
        
    except Exception as e:
        logger.error(f"Failed to load team from {file_path}: {e}")
        raise


def load_team_from_file(file_path: str) -> FPLTeam:
    """Load team from JSON file"""
    try:
        # Load the JSON data
        team_data = load_team_from_json(file_path)
        
        # Convert to FPLTeam object
        from .models import Player, Position
        
        players = []
        
        # Process starting 11
        for player_data in team_data.get('squad', {}).get('starting_11', []):
            player = Player(
                id=len(players) + 1,  # Generate temporary ID
                name=player_data['name'],
                team_id=1,  # Will need to map team names to IDs
                position=Position[player_data['position']],
                price=player_data['price'],
                team_name=player_data['team']
            )
            players.append(player)
        
        # Process substitutes
        for player_data in team_data.get('squad', {}).get('substitutes', []):
            player = Player(
                id=len(players) + 1,  # Generate temporary ID
                name=player_data['name'],
                team_id=1,  # Will need to map team names to IDs
                position=Position[player_data['position']],
                price=player_data['price'],
                team_name=player_data['team']
            )
            players.append(player)
        
        # Get captain and vice captain IDs
        captain_id = None
        vice_captain_id = None
        for player in players:
            if player.name == team_data.get('team_info', {}).get('captain'):
                captain_id = player.id
            elif player.name == team_data.get('team_info', {}).get('vice_captain'):
                vice_captain_id = player.id
        
        return FPLTeam(
            team_id=1,  # Default team ID
            team_name="Loaded Team",
            manager_name="Manager",
            players=players,
            captain_id=captain_id,
            vice_captain_id=vice_captain_id,
            total_value=team_data.get('team_info', {}).get('total_cost', 100.0),
            bank=team_data.get('team_info', {}).get('bank', 0.0),
            free_transfers=team_data.get('transfers', {}).get('free_transfers', 1)
        )
        
    except Exception as e:
        logger.error(f"Failed to load team from {file_path}: {e}")
        logger.warning("Using sample team instead.")
        return create_sample_team()


def create_sample_team() -> FPLTeam:
    """Create a sample team for testing"""
    from .models import Player, Position
    
    sample_players = [
        Player(1, "Sample Goalkeeper", 1, Position.GK, 4.5, total_points=50, form=3.2, team_name="Team A"),
        Player(2, "Sample Defender 1", 2, Position.DEF, 5.0, total_points=60, form=4.1, team_name="Team B"),
        Player(3, "Sample Defender 2", 3, Position.DEF, 4.5, total_points=45, form=3.8, team_name="Team C"),
        Player(4, "Sample Midfielder 1", 4, Position.MID, 8.5, total_points=120, form=6.2, team_name="Team D"),
        Player(5, "Sample Midfielder 2", 5, Position.MID, 7.0, total_points=90, form=5.1, team_name="Team E"),
        Player(6, "Sample Forward", 6, Position.FWD, 9.5, total_points=140, form=7.3, team_name="Team F"),
    ]
    
    return FPLTeam(
        team_id=123,
        team_name="Sample Team",
        manager_name="Sample Manager",
        players=sample_players,
        total_value=95.0,
        bank=5.0
    )

def list_saved_teams() -> List[str]:
    """
    List all saved team files in the output directory.
    
    Returns:
        List of team file paths
    """
    output_dir = "output/teams"
    if not os.path.exists(output_dir):
        return []
    
    team_files = []
    for file in os.listdir(output_dir):
        if file.endswith('.json'):
            team_files.append(os.path.join(output_dir, file))
    
    # Sort by creation time (newest first)
    team_files.sort(key=lambda x: os.path.getctime(x), reverse=True)
    return team_files

def get_latest_team_file() -> Optional[str]:
    """
    Get the most recently created team file.
    
    Returns:
        Path to the latest team file, or None if no files exist
    """
    team_files = list_saved_teams()
    return team_files[0] if team_files else None


if __name__ == "__main__":
    main()
