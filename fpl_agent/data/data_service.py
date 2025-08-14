"""
Data service providing a single interface for all FPL data operations.

This class orchestrates the entire data pipeline:
fetch → process → store → retrieve
"""

import logging
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
            if cached_data and 'player_data' in cached_data:
                logger.info("Using cached player data")
                player_data = cached_data['player_data']
                
                # Apply filters if requested
                if filters:
                    player_data = self.processor.get_available_players(player_data, filters)
                
                return player_data
        
        # Fetch fresh data if no cache or force refresh
        logger.info("Fetching fresh player data from FPL API...")
        try:
            # Fetch raw data from FPL API
            bootstrap_data = self.fetcher.get_fpl_static_data()
            
            # Process the raw data
            player_data = self.processor.process_fpl_data(bootstrap_data)
            
            # Save to cache
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
            if cached_data and 'player_data' in cached_data:
                logger.warning("Returning cached data due to fetch failure")
                player_data = cached_data['player_data']
                
                if filters:
                    player_data = self.processor.get_available_players(player_data, filters)
                
                return player_data
            
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
            # Get available players
            players = self.get_available_players()
            
            # Import here to avoid circular imports
            from ..utils.prompt_formatter import PromptFormatter
            
            # Format the data for LLM prompts
            return PromptFormatter.format_players_for_llm(players)
            
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
