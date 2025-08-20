"""
Data service providing a single interface for all FPL data operations.

This class orchestrates the entire data pipeline:
fetch → process → store → retrieve
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List

from ..core.config import Config
from .fetch_fpl import FPLDataFetcher
from .data_store import DataStore
from .data_processor import DataProcessor
from ..utils.fpl_calculations import calculate_fpl_sale_price

logger = logging.getLogger(__name__)


class DataService:
    """Single interface for all FPL data operations"""
    
    # Default filters for available players
    _DEFAULT_FILTERS = {
        'exclude_injured': True,
        'exclude_unavailable': True,
        'min_chance_of_playing': 25,
        'min_minutes': 0,
        'max_price': float('inf'),
        'min_form': float('-inf'),
        'positions': ['GK', 'DEF', 'MID', 'FWD']
    }
    
    def __init__(self, config: Config):
        """
        Initialize data service.
        
        Args:
            config: FPL configuration object
        """
        self.config = config
        self.fetcher = FPLDataFetcher(config)
        self.store = DataStore()
        self.processor = DataProcessor(config)
    
    def get_players(self, force_refresh: bool = False, 
                   filters: Optional[Dict[str, Any]] = None) -> Dict[str, Dict[str, Any]]:
        """
        Get player data, either from cache or fresh from API.
        
        Args:
            force_refresh: If True, ignore cache and fetch fresh data
            filters: Optional filters for available players
            
        Returns:
            Dictionary of player data keyed by player ID
        """
        # Try to load from cache first (unless force refresh)
        if not force_refresh:
            cached_data = self.store.load_player_data()
            if cached_data:
                # Handle both old and new data formats
                if 'players' in cached_data:
                    logger.info("Using cached enriched player data")
                    player_data = cached_data['players']
                elif 'player_data' in cached_data:
                    logger.info("Using cached legacy player data")
                    player_data = cached_data['player_data']
                else:
                    logger.info("Using cached player data")
                    player_data = cached_data
                
                # Apply filters if requested
                if filters:
                    player_data = self.processor.get_available_players(player_data, filters)
                
                return player_data
        else:
            logger.info("Force refresh requested, will fetch fresh data")
        
        # Fetch fresh data if no cache or force refresh
        logger.info("Fetching fresh player data from FPL API...")
        try:
            # Fetch raw data from FPL API
            bootstrap_data = self.fetcher.get_fpl_static_data()
            
            # Process the raw data
            player_data = self.processor.process_fpl_data(bootstrap_data)
            
            # Check if we have existing enriched data to preserve
            existing_data = self.store.load_player_data()
            if existing_data and 'expert_insights' in existing_data:
                # Preserve enriched data by merging with fresh FPL data
                logger.info("Preserving existing enriched data while updating FPL data")
                enriched_data = {
                    'cache_timestamp': datetime.now().isoformat(),
                    'players': player_data,
                    'total_players': len(player_data),
                    'expert_insights': existing_data.get('expert_insights', {}),
                    'injury_news': existing_data.get('injury_news', {}),
                    'enrichment_timestamp': existing_data.get('enrichment_timestamp')
                }
                self.store.save_player_data(enriched_data)
            else:
                # No existing enriched data, save normally
                logger.info("No existing enriched data found, saving raw player data")
                self.store.save_player_data(player_data)
            
            # Apply filters if requested
            if filters:
                player_data = self.processor.get_available_players(player_data, filters)
            
            logger.info(f"Successfully fetched and processed {len(player_data)} players")
            return player_data
            
        except Exception as e:
            logger.error(f"Failed to fetch fresh data: {e}")
            
            # Try to return cached data as fallback
            cached_data = self.store.load_player_data()
            if cached_data:
                logger.warning("Returning cached data due to fetch failure")
                # Handle both old and new data formats
                if 'players' in cached_data:
                    player_data = cached_data['players']
                elif 'player_data' in cached_data:
                    player_data = cached_data['player_data']
                else:
                    player_data = cached_data
                
                if filters:
                    player_data = self.processor.get_available_players(player_data, filters)
                
                return player_data
            
            raise
    
    def get_fixtures(self, force_refresh: bool = False) -> Dict[str, Any]:
        """
        Get fixtures data, either from cache or fresh from API.
        
        Args:
            force_refresh: If True, ignore cache and fetch fresh data
            
        Returns:
            Dictionary containing fixtures data and metadata
        """
        # Try to load from cache first (unless force refresh)
        if not force_refresh:
            cached_data = self.store.load_fixtures_data()
            if cached_data:
                logger.info("Using cached fixtures data")
                return cached_data
        
        # Fetch fresh fixtures data
        logger.info("Fetching fresh fixtures data from FPL API...")
        try:
            # Fetch raw fixtures from FPL API
            raw_fixtures = self.fetcher.get_fixtures()
            
            # Get teams data for team name resolution
            bootstrap_data = self.fetcher.get_fpl_static_data()
            teams_data = bootstrap_data.get('teams', [])
            
            # Process the raw fixtures data
            processed_fixtures = self.processor.process_fixtures_data(raw_fixtures, teams_data)
            
            # Save to cache
            self.store.save_fixtures_data(processed_fixtures)
            
            logger.info(f"Successfully fetched and processed {len(processed_fixtures)} fixtures")
            
            return {
                'cache_timestamp': datetime.now().isoformat(),
                'fixtures': processed_fixtures,
                'total_fixtures': len(processed_fixtures)
            }
            
        except Exception as e:
            logger.error(f"Failed to fetch fresh fixtures data: {e}")
            
            # Try to return cached data as fallback
            cached_data = self.store.load_fixtures_data()
            if cached_data:
                logger.warning("Returning cached fixtures data due to fetch failure")
                return cached_data
            
            raise
    
    def get_available_players(self, filters: Optional[Dict[str, Any]] = None) -> Dict[str, Dict[str, Any]]:
        """
        Get only available players (filtered by availability criteria).
        
        Args:
            filters: Optional custom filters
            
        Returns:
            Dictionary of available players
        """
        if filters is None:
            filters = self._DEFAULT_FILTERS.copy()
        
        return self.get_players(force_refresh=False, filters=filters)
    
    def get_fixture_info(self, team_name: str, current_gameweek: int) -> Dict[str, Any]:
        """
        Get fixture information for a team in a specific gameweek.
        
        Args:
            team_name: Name of the team
            current_gameweek: Current gameweek number
            
        Returns:
            Dictionary containing fixture string, double gameweek status, and fixture difficulty
        """
        fixtures = self.fetcher.get_fixtures()
        players = self.get_players(force_refresh=False)
        
        return self.processor.get_fixture_info(team_name, current_gameweek, fixtures, players)
    
    def get_available_players_formatted(self, use_semantic_filtering: bool = False, force_refresh: bool = False, use_embeddings: bool = False) -> str:
        """
        Get available players data formatted for LLM prompts.
        
        Args:
            use_semantic_filtering: If True, use enriched data with injury news and FPL suggestions
            force_refresh: If True, ignore cache and fetch fresh data
            use_embeddings: If True, use embedding filtering (placeholder for future implementation)
            
        Returns:
            String containing all available players organized by team
        """
        logger.info("Fetching and formatting available players data...")
        
        try:
            # Get available players using the new filtering system
            players_data = self.get_players(force_refresh=force_refresh)
            
            # Use the new filtering system from DataProcessor
            filtered_players = self.processor.filter_available_players(
                players_data, use_embeddings=use_embeddings
            )
            
            # Format using the new formatting method
            return self.processor.format_players_for_llm_prompt(
                filtered_players, use_embeddings=use_embeddings
            )
            
        except Exception as e:
            logger.error(f"Failed to get available players data: {e}")
            return "Error: Could not fetch player data"
    
    def get_available_players_dict(self) -> Dict[str, Dict[str, Any]]:
        """
        Get available players data as a dictionary for validation.
        
        Returns:
            Dictionary of players with their data
        """
        try:
            # Get available players
            players = self.get_available_players()
            
            # Convert to the expected format
            players_dict = {}
            for player_id, player in players.items():
                players_dict[player.get('full_name', 'Unknown')] = {
                    'name': player.get('full_name', 'Unknown'),
                    'position': player.get('position', 'UNK'),
                    'price': player.get('now_cost', 0) / 10.0,  # Convert from FPL price format
                    'team': player.get('team_name', 'Unknown')
                }
            
            return players_dict
            
        except Exception as e:
            logger.error(f"Failed to get available players dict: {e}")
            return {}
    
    def get_processed_players(self, force_fetch: bool = False, force_enrich: bool = False,
                             force_all: bool = False, cached_only: bool = False,
                             no_enrichments: bool = False) -> str:
        """
        Get processed players data with smart caching and enrichment handling.
        This method handles all the complex data processing logic that was duplicated in main.py.
        
        Args:
            force_fetch: If True, force fresh FPL data fetch
            force_enrich: If True, force fresh enrichment
            force_all: If True, force both fresh fetch and enrichment
            cached_only: If True, use only cached data
            no_enrichments: If True, disable embedding filtering and enrichments
            
        Returns:
            Formatted string of available players for LLM prompts
        """
        logger.info("Getting processed players data...")
        
        # Check data freshness using DataStore
        fpl_data = self.store.load_player_data()
        fpl_age_hours = None
        if fpl_data and 'cache_timestamp' in fpl_data:
            fpl_age_hours = self.store._calculate_data_age_hours(fpl_data)
        
        # Check embeddings freshness
        embeddings_file = Path("team_data/player_embeddings.json")
        embeddings_age_hours = None
        if embeddings_file.exists():
            file_stat = embeddings_file.stat()
            embeddings_age_hours = (datetime.now().timestamp() - file_stat.st_mtime) / 3600
        
        # Check enriched data freshness
        enriched_age_hours = None
        if fpl_data and 'enrichment_timestamp' in fpl_data:
            enriched_age_hours = self.store._calculate_data_age_hours(fpl_data, 'enrichment_timestamp')
        
        # Determine what to do based on flags and data freshness
        should_fetch = self._should_fetch_data(
            force_fetch or force_all, 
            cached_only, 
            fpl_age_hours is not None and fpl_age_hours < 1.0
        )
        
        should_enrich = self._should_enrich_data(
            force_enrich or force_all, 
            cached_only, 
            enriched_age_hours is not None and enriched_age_hours < 1.0
        )
        
        # Step 1: Fetch FPL data if needed
        if should_fetch:
            logger.info("Fetching fresh FPL data...")
            # Fetch fresh data from API
            bootstrap_data = self.fetcher.get_fpl_static_data()
            # Process the raw data
            fresh_player_data = self.processor.process_fpl_data(bootstrap_data)
            # Save the fresh data to the store
            self.store.save_player_data(fresh_player_data)
            logger.info("Fresh FPL data fetched and saved to store")
        
        # Step 2: Enrich data if needed
        if should_enrich:
            logger.info("Enriching player data...")
            try:
                # Load current player data for enrichment
                current_players_data = self.store.load_player_data()
                if not current_players_data or 'players' not in current_players_data:
                    logger.warning("No player data available for enrichment")
                else:
                    # Import here to avoid circular imports
                    from ..strategies.team_analysis_strategy import TeamAnalysisStrategy
                    
                    # Initialize the team analysis strategy for enrichment
                    team_analysis_strategy = TeamAnalysisStrategy(self.config)
                    
                    # Enrich the player data using the processor
                    enriched_players = self.processor.enrich_player_data_by_teams(
                        current_players_data['players'], 
                        team_analysis_strategy
                    )
                    
                    # Save the enriched data back to the store
                    enriched_data = {
                        'players': enriched_players,
                        'enrichment_timestamp': datetime.now().isoformat(),
                        'enrichment_status': 'completed',
                        'total_players_enriched': len(enriched_players)
                    }
                    
                    # Preserve the cache timestamp if it exists
                    if 'cache_timestamp' in current_players_data:
                        enriched_data['cache_timestamp'] = current_players_data['cache_timestamp']
                    
                    self.store.save_player_data(enriched_data)
                    logger.info(f"Successfully enriched {len(enriched_players)} players")
                    
            except Exception as e:
                logger.error(f"Failed to enrich player data: {e}")
                logger.warning("Continuing with unenriched data")
        
        # Step 3: Load player data for processing
        players_data = self.store.load_player_data()
        if not players_data:
            raise ValueError("No player data available. Run 'fetch' command first.")
        
        # Extract just the players data
        if 'players' in players_data:
            players_data = players_data['players']
        elif 'player_data' in players_data:
            players_data = players_data['player_data']
        
        # Step 4: Determine embedding usage
        if no_enrichments:
            use_embeddings = False
            logger.info("Embedding filtering disabled due to --no-enrichments flag")
        else:
            use_embeddings = self.config.get_embeddings_config().get('use_embeddings', False)
        
        # Step 5: Filter players using DataProcessor
        filtered_players = self.processor.filter_available_players(
            players_data, use_embeddings=use_embeddings
        )
        
        # Step 6: Calculate and inject embedding scores if using embeddings
        if use_embeddings:
            try:
                # Import here to avoid circular imports
                from .embedding_filter import EmbeddingFilter
                
                # Get the embedding filter to calculate scores
                embedding_filter = EmbeddingFilter(self.config)
                enriched_data = self.processor._get_enriched_players(filtered_players)
                
                # Get similarities and hybrid scores
                player_embeddings = embedding_filter._load_cached_embeddings()
                if player_embeddings and 'embeddings' in player_embeddings:
                    # Convert string representations back to numpy arrays
                    converted_embeddings = {}
                    for player_name, embedding_str in player_embeddings['embeddings'].items():
                        try:
                            import numpy as np
                            import json
                            embedding_array = np.array(json.loads(embedding_str))
                            converted_embeddings[player_name] = embedding_array
                        except Exception:
                            continue
                    
                    # TODO: Can this not just be one function in embedding_filter, that runs all this? Would be cleaner.

                    # Get query embeddings and calculate similarities
                    query_embeddings = embedding_filter._encode_queries()
                    player_positions = embedding_filter._get_player_positions(enriched_data, filtered_players)
                    similarities = embedding_filter._calculate_similarities(converted_embeddings, query_embeddings, player_positions)
                    
                    # Get hybrid scores for ranking
                    structured_data = embedding_filter._get_structured_data_for_hybrid_scoring(enriched_data, filtered_players)
                    hybrid_scores = embedding_filter._calculate_hybrid_scores(similarities, structured_data)
                    
                    # Inject scores into player data
                    for position, ranked_players in hybrid_scores.items():
                        for player_name, hybrid_score, embedding_score, keyword_bonus in ranked_players:
                            if player_name in filtered_players:
                                filtered_players[player_name]['embedding_score'] = embedding_score
                                filtered_players[player_name]['keyword_bonus'] = keyword_bonus
                                filtered_players[player_name]['hybrid_score'] = hybrid_score
                    
                    logger.info(f"Injected embedding scores for {len(filtered_players)} players")
                else:
                    logger.warning("No embeddings cache available, scores will be 0.0")
            except Exception as e:
                logger.warning(f"Failed to calculate embedding scores: {e}, scores will be 0.0")
        
        # Step 7: Format players for LLM prompt
        formatted_players = self.processor.format_players_for_llm_prompt(
            filtered_players, use_embeddings=use_embeddings
        )
        
        logger.info(f"Processed {len(filtered_players)} players for LLM prompt")
        return formatted_players
    
    def get_gameweek_fixtures_formatted(self, gameweek: int) -> str:
        """
        Get formatted fixtures for a specific gameweek for use in prompts.
        
        Args:
            gameweek: Gameweek number
            
        Returns:
            Formatted string of fixtures for the gameweek
        """
        try:
            # Get fixtures data (from cache if available)
            fixtures_data = self.get_fixtures(force_refresh=False)
            
            if not fixtures_data or 'fixtures' not in fixtures_data:
                return f"Error loading fixtures for Gameweek {gameweek}."
            
            # Get fixtures for the specific gameweek
            gameweek_fixtures = self.processor.get_gameweek_fixtures(gameweek, fixtures_data['fixtures'])
            
            # Format fixtures for prompt
            return self.processor.format_fixtures_for_prompt(gameweek_fixtures, gameweek)
            
        except Exception as e:
            logger.error(f"Failed to get formatted fixtures for gameweek {gameweek}: {e}")
            return f"Error loading fixtures for Gameweek {gameweek}."
    
    def _should_fetch_data(self, force_fetch: bool, cached_only: bool, data_fresh: bool) -> bool:
        """Determine if we should fetch fresh FPL data"""
        if cached_only:
            return False
        if force_fetch:
            return True
        return not data_fresh
    
    def _should_enrich_data(self, force_enrich: bool, cached_only: bool, enrich_fresh: bool) -> bool:
        """Determine if we should run LLM enrichment"""
        if cached_only:
            return False
        if force_enrich:
            return True
        return not enrich_fresh
    
    def get_all_gameweek_data(self, gameweek: int, force_fetch: bool = False, 
                             use_enrichments: bool = True, 
                             cached_only: bool = False) -> Dict[str, Any]:
        """
        Get all data needed for a gameweek in one call.
        Returns: players, fixtures
        """
        players = self.get_processed_players(
            force_fetch=force_fetch,
            force_enrich=use_enrichments,
            force_all=False,
            cached_only=cached_only,
            no_enrichments=not use_enrichments
        )
        fixtures = self.get_gameweek_fixtures_formatted(gameweek)
        
        return {
            'players': players,
            'fixtures': fixtures
        }

    def show_data_status(self, data_store: DataStore) -> Dict[str, Any]:
        """
        Display current data status.
        Moved from main.py to consolidate data status operations.
        
        Args:
            data_store: DataStore instance for loading player data
            
        Returns:
            Dictionary containing data status information
        """
        try:
            print("📊 FPL Data Status")
            print("=" * 50)
            
            # Check data freshness using DataStore
            fpl_data = data_store.load_player_data()
            fpl_age_hours = None
            if fpl_data and 'cache_timestamp' in fpl_data:
                fpl_age_hours = data_store._calculate_data_age_hours(fpl_data)
            
            # Check embeddings freshness
            embeddings_file = Path("team_data/player_embeddings.json")
            embeddings_age_hours = None
            if embeddings_file.exists():
                file_stat = embeddings_file.stat()
                embeddings_age_hours = (datetime.now().timestamp() - file_stat.st_mtime) / 3600
            
            # Check enriched data freshness
            enriched_age_hours = None
            if fpl_data and 'enrichment_timestamp' in fpl_data:
                enriched_age_hours = data_store._calculate_data_age_hours(fpl_data, 'enrichment_timestamp')
            
            data_status = {
                'fpl_data': {
                    'fresh': fpl_age_hours is not None and fpl_age_hours < 1.0,
                    'age_hours': fpl_age_hours,
                    'available': fpl_data is not None
                },
                'enriched_data': {
                    'fresh': enriched_age_hours is not None and enriched_age_hours < 1.0,
                    'age_hours': enriched_age_hours,
                    'available': enriched_age_hours is not None
                },
                'embeddings': {
                    'fresh': embeddings_age_hours is not None and embeddings_age_hours < 1.0,
                    'age_hours': embeddings_age_hours,
                    'available': embeddings_age_hours is not None
                },
                'overall_status': 'unknown'
            }
            
            # Determine overall status
            if data_status['fpl_data']['available'] and data_status['enriched_data']['available']:
                if data_status['fpl_data']['fresh'] and data_status['enriched_data']['fresh']:
                    data_status['overall_status'] = 'fresh'
                elif data_status['fpl_data']['available'] and data_status['enriched_data']['available']:
                    data_status['overall_status'] = 'partial'
                else:
                    data_status['overall_status'] = 'stale'
            elif data_status['fpl_data']['available']:
                data_status['overall_status'] = 'fpl_only'
            else:
                data_status['overall_status'] = 'none'
            
            # FPL Data Status
            print(f"\n🔄 FPL Data:")
            if data_status['fpl_data']['available']:
                age = data_status['fpl_data']['age_hours']
                status = "✅ Fresh" if data_status['fpl_data']['fresh'] else "⚠️  Stale"
                print(f"   • Status: {status}")
                print(f"   • Age: {age:.1f} hours")
                print(f"   • Last updated: {datetime.now().timestamp() - (age * 3600):.0f} seconds ago")
            else:
                print("   • Status: ❌ Not available")
                print("   • Action: Run 'fetch' command")
            
            # Enriched Data Status
            print(f"\n🧠 Enriched Data:")
            if data_status['enriched_data']['available']:
                age = data_status['enriched_data']['age_hours']
                status = "✅ Fresh" if data_status['enriched_data']['fresh'] else "⚠️  Stale"
                print(f"   • Status: {status}")
                print(f"   • Age: {age:.1f} hours")
                print(f"   • Last updated: {datetime.now().timestamp() - (age * 3600):.0f} seconds ago")
            else:
                print("   • Status: ❌ Not available")
                print("   • Action: Run 'enrich' command")
            
            # Embeddings Status
            print(f"\n🔍 Embeddings:")
            if data_status['embeddings']['available']:
                age = data_status['embeddings']['age_hours']
                status = "✅ Fresh" if data_status['embeddings']['fresh'] else "⚠️  Stale"
                print(f"   • Status: {status}")
                print(f"   • Age: {age:.1f} hours")
            else:
                print("   • Status: ❌ Not available")
            
            # Overall Status
            print(f"\n📋 Overall Status:")
            overall = data_status['overall_status']
            if overall == 'fresh':
                print("   • Status: ✅ All data is fresh and ready")
                print("   • Action: Ready for team building/updates")
            elif overall == 'stale':
                print("   • Status: ⚠️  Data is available but stale")
                print("   • Action: Consider running 'gw-update' or 'build-team' with --force-all")
            elif overall == 'partial':
                print("   • Status: ⚠️  Partial data available")
                print("   • Action: Run 'enrich' to complete data preparation")
            elif overall == 'fpl_only':
                print("   • Status: ⚠️  Only FPL data available")
                print("   • Action: Run 'enrich' to add LLM insights")
            else:
                print("   • Status: ❌ No data available")
                print("   • Action: Run 'fetch' to get started")
            
            # Recommendations
            print(f"\n💡 Recommendations:")
            if data_status['overall_status'] == 'fresh':
                print("   • All data is fresh - ready for team operations")
            elif data_status['overall_status'] in ['stale', 'partial']:
                print("   • Run 'gw-update' for complete weekly refresh")
                print("   • Or run 'build-team' with --force-all for fresh team")
            else:
                print("   • Start with 'fetch' to get FPL data")
                print("   • Then 'enrich' to add insights")
                print("   • Finally 'build-team' or 'gw-update'")
            
            return data_status
            
        except Exception as e:
            logger.error(f"Failed to show data status: {e}")
            print(f"❌ Error showing data status: {e}")
            raise

    def show_players_status(self, data_store: DataStore, config: Config) -> Dict[str, Any]:
        """
        Display available players breakdown showing filtering process.
        Moved from main.py to consolidate player status operations.
        
        Args:
            data_store: DataStore instance for loading player data
            config: Config instance for embeddings configuration
            
        Returns:
            Dictionary containing player status information
        """
        try:
            print("👥 FPL Players Status")
            print("=" * 50)
            
            # Load player data
            players_data = data_store.load_player_data()
            if not players_data:
                print("❌ No player data available. Run 'fetch' command first.")
                return {}
            
            # Extract player data
            if 'players' in players_data:
                all_players = players_data['players']
            elif 'player_data' in players_data:
                all_players = players_data['player_data']
            else:
                all_players = players_data
            
            total_players = len(all_players)
            print(f"📊 Total players in data: {total_players}")
            
            # Apply basic filtering to separate available vs unavailable
            available_players = self.processor._filter_available_players(all_players)
            unavailable_players = {
                name: data for name, data in all_players.items() 
                if name not in available_players
            }
            
            print(f"\n🚫 Not Available Players: {len(unavailable_players)}")
            print("-" * 30)
            print("   (Filtered out by: chance_of_playing < 25% OR marked as 'Out' in injury news)")
            print()
            
            # Debug: Check if we have any unavailable players
            if len(unavailable_players) == 0:
                print("   No unavailable players found")
            else:
                print(f"   Found {len(unavailable_players)} unavailable players")
                # Show first few names as debug
                first_names = list(unavailable_players.keys())[:5]
                print(f"   First few: {first_names}")
            
            # Group by position for better organization
            position_groups = {}
            for name, data in unavailable_players.items():
                position = data.get('element_type', 'Unknown')
                
                # Handle different possible element_type formats
                if position == 1 or position == '1' or position == 'GK':
                    position = 'GK'
                elif position == 2 or position == '2' or position == 'DEF':
                    position = 'DEF'
                elif position == 3 or position == '3' or position == 'MID':
                    position = 'MID'
                elif position == 4 or position == '4' or position == 'FWD':
                    position = 'FWD'
                else:
                    # If we can't determine position, try to infer from other data
                    # Check if player has any position-related fields
                    if 'element_type' in data and data['element_type'] not in ['Unknown', None, '']:
                        position = 'Unknown'  # Keep as unknown if we have some data
                    else:
                        # Try to infer from team or other fields, default to 'Unknown'
                        position = 'Unknown'
                
                if position not in position_groups:
                    position_groups[position] = []
                position_groups[position].append((name, data))
            
            print(f"   Position groups: {list(position_groups.keys())}")
            
            # Format using the common method for consistency
            # First try the standard positions
            for position in ['GK', 'DEF', 'MID', 'FWD']:
                if position in position_groups:
                    players = position_groups[position]
                    print(f"   {position} ({len(players)} players):")
                    
                    # Use the common formatting method to ensure chance of playing is included
                    position_data = dict(players)
                    formatted_output = self.processor.format_players_by_position_ranked(
                        position_data,
                        use_embeddings=True,  # Show injury news and expert insights if available
                        include_rankings=True,
                        include_scores=False
                    )
                    print(formatted_output)
                else:
                    print(f"   No {position} players found")
            
            # Handle any remaining players (including 'Unknown' position)
            for position in position_groups.keys():
                if position not in ['GK', 'DEF', 'MID', 'FWD']:
                    players = position_groups[position]
                    print(f"   {position} ({len(players)} players):")
                    
                    # Use the common formatting method to ensure chance of playing is included
                    position_data = dict(players)
                    formatted_output = self.processor.format_players_by_position_ranked(
                        position_data,
                        use_embeddings=True,  # Show injury news and expert insights if available
                        include_rankings=True,
                        include_scores=False
                    )
                    print(formatted_output)
            
            print(f"\n✅ Available Players: {len(available_players)}")
            print("-" * 30)
            
            # Check if embedding filtering is available and configured
            embeddings_config = config.get_embeddings_config()
            use_embeddings = embeddings_config.get('use_embeddings', False)
            
            if use_embeddings:
                print(f"🔍 Embedding filtering: ENABLED")
                
                # Check if embeddings cache exists
                embeddings_file = Path("team_data/player_embeddings.json")
                if embeddings_file.exists():
                    try:
                        # Apply embedding filtering
                        filtered_players = self.processor.filter_available_players(
                            all_players, use_embeddings=True
                        )
                        
                        # Get the processed player data that includes chance of playing and other fields
                        # This ensures both sections have consistent data
                        processed_players_data = {}
                        for name, data in all_players.items():
                            if name in filtered_players:
                                # For top players, use the filtered data
                                processed_players_data[name] = filtered_players[name]
                            elif name in available_players:
                                # For filtered out players, ensure they have the same fields
                                processed_data = data.copy()
                                # Ensure chance_of_playing is properly set
                                if 'chance_of_playing' not in processed_data or processed_data['chance_of_playing'] is None:
                                    processed_data['chance_of_playing'] = 100
                                processed_players_data[name] = processed_data
                        
                        # Calculate players filtered out by embeddings
                        embedding_filtered_out = {
                            name: processed_players_data[name] for name in available_players.keys() 
                            if name not in filtered_players
                        }
                        
                        print(f"\n🎯 Top Players (Embedding Selected): {len(filtered_players)}")
                        print("-" * 40)
                        print("   (Selected by embedding similarity + keyword bonuses)")
                        print()
                        
                        # Use the common formatting method for top players with scores
                        formatted_top_players = self.processor.format_players_by_position_ranked(
                            filtered_players, 
                            use_embeddings=True, 
                            include_rankings=True,
                            include_scores=True
                        )
                        print(formatted_top_players)
                        
                        print(f"\n🚫 Filtered Out by Embedding: {len(embedding_filtered_out)}")
                        print("-" * 40)
                        print("   (Available but didn't make top N per position)")
                        print()
                        
                        # Use the common formatting method for filtered out players with scores
                        formatted_filtered_out = self.processor.format_players_by_position_ranked(
                            embedding_filtered_out, 
                            use_embeddings=True, 
                            include_rankings=True,
                            include_scores=True
                        )
                        print(formatted_filtered_out)
                        
                    except Exception as e:
                        print(f"   ❌ Embedding filtering failed: {e}")
                        print(f"   📋 Falling back to basic players summary...")
                        self._show_basic_players_summary(available_players)
                else:
                    print(f"   📁 No embeddings cache found. Run 'enrich' command first.")
                    print(f"   📋 Falling back to basic players summary...")
                    self._show_basic_players_summary(available_players)
            else:
                print(f"🔍 Embedding filtering: DISABLED")
                self._show_basic_players_summary(available_players)
            
            return {
                'total_players': total_players if 'total_players' in locals() else 0,
                'available_players': len(available_players) if 'available_players' in locals() else 0,
                'unavailable_players': len(unavailable_players) if 'unavailable_players' in locals() else 0,
                'use_embeddings': use_embeddings,
                'completed_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to show players status: {e}")
            print(f"❌ Error showing players status: {e}")
            raise

    def _show_basic_players_summary(self, available_players: Dict[str, Dict[str, Any]]):
        """
        Show summary of available players when no embedding filtering.
        Moved from main.py to consolidate player display operations.
        
        Args:
            available_players: Dictionary of available players
        """
        print(f"\n📋 Basic Players Summary:")
        print("-" * 30)
        
        # Use the common formatting method from DataProcessor
        formatted_output = self.processor.format_players_by_position_ranked(
            available_players, 
            use_embeddings=False, 
            include_rankings=True
        )
        print(formatted_output)
        
        # Note: These players would go into LLM prompts with basic stats only
        print(f"\n📝 Note: These players would go into LLM prompts with basic stats only (no expert insights or injury news)")
    
    def get_current_team_player_data(self, current_team: Dict[str, Any], 
                                    use_enrichments: bool = False,
                                    force_refresh: bool = False) -> Dict[str, Dict[str, Any]]:
        """
        Get comprehensive data for all players in the current team.
        
        Args:
            current_team: Current team data from gwNN.json
            use_enrichments: Whether to include expert insights and injury news
            force_refresh: Whether to force fresh data fetch
            
        Returns:
            Dictionary of player data indexed by full name, including:
            - Current market price (from player_data.json)
            - Purchase price (from gwNN.json)
            - Expert insights (if enrichments available)
            - Injury news (if enrichments available)
            - All other player attributes
            
        Raises:
            ValueError: If any player in current team is not found in market data
        """
        try:
            # 1. Get all player names from current team
            team_players = current_team['starting'] + current_team['substitutes']
            player_names = [player['name'] for player in team_players]
            
            # 2. Get current market data for these specific players
            all_players_data = self.get_players(force_refresh=force_refresh)
            current_market_data = {
                name: all_players_data[name] 
                for name in player_names 
                if name in all_players_data
            }
            
            # 3. Validate all players found
            missing_players = [name for name in player_names if name not in current_market_data]
            if missing_players:
                raise ValueError(
                    f"Players not found in current market data: {', '.join(missing_players)}. "
                    f"This indicates a data inconsistency that must be resolved."
                )
            
            # 4. Get enriched data if requested
            enriched_data = {}
            if use_enrichments:
                enriched_data = self._get_team_enrichments(player_names, force_refresh)
            
            # 5. Merge all data sources
            final_player_data = {}
            for player_name in player_names:
                # Get team data (purchase price, position, etc.)
                team_player = next(p for p in team_players if p['name'] == player_name)
                
                # Get market data (current price, etc.)
                market_player = current_market_data[player_name]
                
                # Get enriched data if available
                player_enrichments = enriched_data.get(player_name, {})
                
                # Calculate sale price using FPL formula
                current_price = market_player.get('now_cost', 0) / 10.0
                purchase_price = team_player['price']
                sale_price = calculate_fpl_sale_price(current_price, purchase_price)
                
                # Merge all data
                final_player_data[player_name] = {
                    # From team data
                    'name': team_player['name'],
                    'position': team_player['position'],
                    'team': team_player['team'],
                    'purchase_price': purchase_price,
                    
                    # From market data
                    'current_price': current_price,
                    'form': market_player.get('form', ''),
                    'total_points': market_player.get('total_points', 0),
                    'minutes': market_player.get('minutes', 0),
                    
                    # Calculated sale price
                    'sale_price': sale_price,
                    
                    # From enrichments (if available)
                    'expert_insights': player_enrichments.get('expert_insights', 'None'),
                    'injury_news': player_enrichments.get('injury_news', 'None'),
                    
                    # Additional market data
                    'selected_by_percent': market_player.get('selected_by_percent', 0),
                    'transfers_in': market_player.get('transfers_in', 0),
                    'transfers_out': market_player.get('transfers_out', 0),
                }
            
            logger.info(f"Successfully loaded data for {len(final_player_data)} team players")
            return final_player_data
            
        except Exception as e:
            logger.error(f"Failed to get current team player data: {e}")
            raise
    
    def _get_team_enrichments(self, player_names: List[str], force_refresh: bool) -> Dict[str, Dict[str, Any]]:
        """
        Get enriched data (expert insights and injury news) for specific players.
        
        Args:
            player_names: List of player names to enrich
            force_refresh: Whether to force fresh enrichment
            
        Returns:
            Dictionary of enriched data indexed by player name
        """
        try:
            # Load existing enriched data from cache
            cached_data = self.store.load_player_data()
            if not cached_data or force_refresh:
                logger.info("No enriched data available or force refresh requested")
                return {}
            
            # Extract enrichments for the specific players
            enriched_data = {}
            for player_name in player_names:
                player_enrichments = {}
                
                # Get expert insights if available
                if 'expert_insights' in cached_data and player_name in cached_data['expert_insights']:
                    player_enrichments['expert_insights'] = cached_data['expert_insights'][player_name]
                
                # Get injury news if available
                if 'injury_news' in cached_data and player_name in cached_data['injury_news']:
                    player_enrichments['injury_news'] = cached_data['injury_news'][player_name]
                
                if player_enrichments:
                    enriched_data[player_name] = player_enrichments
            
            logger.info(f"Loaded enrichments for {len(enriched_data)} out of {len(player_names)} players")
            return enriched_data
            
        except Exception as e:
            logger.warning(f"Failed to load team enrichments: {e}")
            return {}
