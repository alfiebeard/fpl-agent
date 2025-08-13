"""
Player data service utilities.

This module handles all player data operations including fetching, enriching, and formatting.
"""

import json
import logging
from typing import Dict, Any, List, Optional
from .player_data_cache import PlayerDataCache
from .fpl_data_manager import FPLDataManager
from .data_enrichment import DataEnrichment

logger = logging.getLogger(__name__)


class PlayerDataService:
    """Handles all player data operations"""
    
    def __init__(self, config):
        self.config = config
        self.cache = PlayerDataCache()
        self.data_manager = FPLDataManager(config)
        self.data_enrichment = DataEnrichment(config)
    
    def get_available_players_data(self, use_semantic_filtering: bool = False, force_refresh: bool = False, use_embeddings: bool = False) -> str:
        """
        Get available players data as formatted string.
        
        Args:
            use_semantic_filtering: If True, use semantic filtering
            force_refresh: If True, ignore cache and fetch fresh data
            use_embeddings: If True, use embeddings for filtering
            
        Returns:
            Formatted string of available players
        """
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
                'positions': ['GK', 'DEF', 'MID', 'FWD']  # All positions
            }
            
            # Filter players based on criteria
            available_players = []
            for player in players:
                # Calculate chance of playing as minimum of this round and next round
                chance_of_playing = self._calculate_chance_of_playing(
                    player.get('chance_of_playing_this_round'),
                    player.get('chance_of_playing_next_round')
                )
                
                # Check if player meets filter criteria
                if (not player.get('is_injured', False) and 
                    chance_of_playing >= filters['min_chance_of_playing'] and
                    player.get('element_type') in filters['positions'] and
                    player.get('now_cost', 0) <= filters['max_price'] and
                    player.get('form', 0) >= filters['min_form']):
                    available_players.append(player)
            
            # Group players by team
            teams = {}
            for player in available_players:
                team_name = player.get('team', 'Unknown')
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
                    key=lambda p: (position_order.get(p.get('element_type', ''), 4), -p.get('total_points', 0))
                )
                
                for player in sorted_players:
                    # Calculate chance of playing as minimum of this round and next round
                    chance_of_playing = self._calculate_chance_of_playing(
                        player.get('chance_of_playing_this_round'),
                        player.get('chance_of_playing_next_round')
                    )
                    chance_str = f"{chance_of_playing}%"
                    
                    # Get additional stats
                    ppg = player.get('points_per_game', 0)
                    form = player.get('form', 0)
                    minutes = player.get('minutes', 0)
                    fixture_difficulty = 3.0  # Default value
                    ownership = player.get('selected_by_percent', 0)
                    
                    formatted_data.append(
                        f"{player.get('name', 'Unknown')}, {player.get('element_type', 'Unknown')}, "
                        f"£{player.get('now_cost', 0)/10:.1f}, {chance_str}, "
                        f"PPG: {ppg:.1f}, Form: {form:.1f}, Mins: {minutes}, "
                        f"Fixture Diff: {fixture_difficulty}, Ownership: {ownership:.1f}%"
                    )
                
                formatted_data.append("")  # Empty line between teams
            
            return "\n".join(formatted_data)
            
        except Exception as e:
            logger.error(f"Failed to get available players data: {e}")
            return "Error: Could not fetch player data"
    
    def get_available_players_dict(self, bootstrap_data: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
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
                'positions': ['GK', 'DEF', 'MID', 'FWD']
            }
            
            # Transform data
            from .data_transformers import transform_fpl_data_to_teams
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
    
    def get_enriched_player_data(self, force_refresh: bool = False) -> Dict[str, Dict[str, Any]]:
        """
        Get enriched player data with injury news and hints.
        
        Args:
            force_refresh: If True, ignore cache and fetch fresh data
            
        Returns:
            Dictionary of enriched player data
        """
        try:
            # Try to get from cache first (unless force refresh)
            if not force_refresh:
                cached_data = self.cache.get_cached_enriched_data()
                if cached_data:
                    logger.info("Using cached enriched player data")
                    return cached_data
            
            # Fetch fresh enriched data
            logger.info("Fetching fresh enriched player data...")
            enriched_data = self._fetch_fresh_enriched_data()
            
            if enriched_data:
                # Save to cache
                self.cache.save_data(enriched_data)
                return enriched_data
            else:
                logger.warning("Failed to fetch fresh enriched data, returning empty dict")
                return {}
                
        except Exception as e:
            logger.error(f"Failed to get enriched player data: {e}")
            return {}
    
    def _fetch_fresh_enriched_data(self) -> Dict[str, Dict[str, Any]]:
        """Fetch fresh enriched data using our DataEnrichment utility"""
        try:
            logger.info("Using DataEnrichment utility to fetch fresh enriched data...")
            
            # Get basic FPL data from our data manager
            all_data = self.data_manager.get_fpl_static_data()
            players = all_data.get('elements', [])
            
            # Convert FPL data to our expected format and enrich
            player_data_dict = {}
            for player in players:
                # Convert player data to our expected format
                player_data = {
                    "data": {
                        "id": player.get("id", 0),
                        "name": player.get("name", ""),
                        "team": player.get("team", ""),
                        "position": player.get("element_type", ""),
                        # Add other required fields as needed
                    }
                }
                player_data_dict[player.get("name", "")] = player_data
            
            # Use our DataEnrichment utility
            enriched_data = self.data_enrichment.enrich_player_data(player_data_dict)
            
            logger.info(f"Created enriched data for {len(enriched_data)} players using utility")
            return enriched_data
            
        except Exception as e:
            logger.error(f"Failed to fetch fresh enriched data: {e}")
            return {}
    
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
            Formatted string of enriched player data for LLM prompts
        """
        logger.info("Getting enriched player data for LLM prompt...")
        
        try:
            # Get structured enriched player data
            structured_data = self.get_enriched_player_data(force_refresh=force_refresh)
            
            if not structured_data:
                return "No enriched player data available"
            
            # Create prompt-friendly versions (with stats line)
            prompt_data = []
            
            for player_name, player_data in structured_data.items():
                prompt_text = self._generate_prompt_text(player_data)
                prompt_data.append(prompt_text)
            
            result = "\n\n".join(prompt_data)
            logger.info(f"Created prompt-friendly data for {len(prompt_data)} players")
            return result
            
        except Exception as e:
            logger.error(f"Failed to get enriched player data for prompt: {e}")
            return "Error: Could not format player data for prompt"
    
    def _generate_embedding_text(self, player_data: Dict[str, Any]) -> str:
        """
        Generate text for embeddings (without stats line).
        
        Args:
            player_data: Structured player data dictionary
            
        Returns:
            Text string formatted for embeddings
        """
        data = player_data["data"]
        return f"{data['name']} ({data['team']}, {data['position']}, £{data.get('price', 0)})\n" \
               f"Injury News: {player_data.get('injury_news', 'No news')}\n" \
               f"FPL Suggestions: {player_data.get('hints_tips_news', 'No suggestions')}"
    
    def _generate_prompt_text(self, player_data: Dict[str, Any]) -> str:
        """
        Generate text for LLM prompts (with stats line).
        
        Args:
            player_data: Structured player data dictionary
            
        Returns:
            Text string formatted for LLM prompts
        """
        data = player_data["data"]
        return f"{data['name']} ({data['team']}, {data['position']}, £{data.get('price', 0)})\n" \
               f"Stats: Chance of Playing - {data.get('chance_of_playing', 100)}%, " \
               f"PPG - {data.get('ppg', 0):.1f}, Form - {data.get('form', 0):.1f}, " \
               f"Minutes - {data.get('minutes', 0)}, " \
               f"Fixture Difficulty - {data.get('fixture_difficulty', 3)}, " \
               f"Ownership - {data.get('ownership_percent', 0):.1f}%.\n" \
               f"Injury News: {player_data.get('injury_news', 'No news')}\n" \
               f"FPL Suggestions: {player_data.get('hints_tips_news', 'No suggestions')}"
    
    def _calculate_chance_of_playing(self, chance_this_round: Optional[int], chance_next_round: Optional[int]) -> int:
        """
        Calculate chance of playing as minimum of this round and next round.
        
        Args:
            chance_this_round: Chance of playing this round (0-100)
            chance_next_round: Chance of playing next round (0-100)
            
        Returns:
            Minimum chance of playing (0-100)
        """
        if chance_this_round is None and chance_next_round is None:
            return 100  # Default to 100% if no data
        
        chances = []
        if chance_this_round is not None:
            chances.append(chance_this_round)
        if chance_next_round is not None:
            chances.append(chance_next_round)
        
        return min(chances) if chances else 100
    
    def get_cache_status(self) -> Dict[str, Any]:
        """Get status of all data sources"""
        return {
            "player_cache": self.cache.get_cache_status(),
            "fpl_data": self.data_manager.get_cache_status(),
            "enrichment": self.data_enrichment.get_enrichment_status()
        }
    
    def refresh_data(self, force: bool = False) -> None:
        """Refresh all data sources"""
        logger.info("Refreshing all player data sources...")
        
        # Refresh FPL data
        self.data_manager.refresh_cache(force=force)
        
        # Refresh enrichment data
        self.data_enrichment.refresh_data(force=force)
        
        # Clear player cache if forcing refresh
        if force:
            self.cache.clear_cache()
        
        logger.info("Player data refresh completed")
