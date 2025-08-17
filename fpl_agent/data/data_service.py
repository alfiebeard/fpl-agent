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
