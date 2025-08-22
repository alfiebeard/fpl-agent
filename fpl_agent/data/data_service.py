"""
Data service providing a single interface for all FPL data operations.

This class orchestrates the entire data pipeline:
fetch → process → store → retrieve
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List

from ..core.config import Config
from .fetch_fpl import FPLDataFetcher
from .data_store import DataStore
from .data_processor import DataProcessor
from ..utils.fpl_calculations import calculate_fpl_sale_price
from ..utils.keyword_extractor import extract_injury_status

logger = logging.getLogger(__name__)


class DataService:
    """Single interface for all FPL data operations"""
    
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

    def get_all_gameweek_data(self, gameweek: int, use_cached: bool = False, 
                             filter_unavailable_players_mode: str = "no_filter") -> Dict[str, Any]:
        """
        Get all fpl and fixture data needed for a gameweek in one call.
        
        Args:
            gameweek: Gameweek number
            use_cached: If True, return cached data. If False, fetch fresh data.
            filter_unavailable_players_mode: If "fpl_data_and_enrichments", apply availability filters using both FPL data and enrichments. If "fpl_data_only", apply availability filters using FPL data only. If "no_filter", return all players.
            
        Returns:
            Dictionary containing players and fixtures data
        """
        players = self.get_players(
            use_cached=use_cached,      # Use cache when use_cached is True
            filter_unavailable_players_mode=filter_unavailable_players_mode  # Pass through filtering preference
        )
        
        # Get raw fixtures data for the gameweek
        fixtures = self.get_fixtures(use_cached=use_cached)
        if fixtures and 'fixtures' in fixtures:
            gameweek_fixtures = self.processor.get_gameweek_fixtures(gameweek, fixtures['fixtures'])
        else:
            gameweek_fixtures = []
        
        return {
            'players': players,
            'fixtures': gameweek_fixtures  # Raw fixture data for processing
        }
    
    def get_players(self, use_cached: bool = False, filter_unavailable_players_mode: str = "no_filter") -> Dict[str, Dict[str, Any]]:
        """
        Get players data with smart caching.
        
        Args:
            use_cached: If True, use only cached data. If False, fetch fresh data.
            filter_unavailable_players_mode: If "fpl_data_and_enrichments", apply availability filters using both FPL data and enrichments. If "fpl_data_only", apply availability filters using FPL data only. If "no_filter", return all players.
            
        Returns:
            Dictionary of processed player data keyed by player name
        """
        
        # Step 1: Fetch FPL data if needed
        if not use_cached:
            try:
                logger.info("Fetching fresh FPL data...")
                # Fetch fresh data from API
                bootstrap_data = self.fetcher.get_fpl_static_data()
                # Process the raw data
                fresh_player_data = self.processor.process_fpl_data(bootstrap_data)
                # Save the fresh data to the store
                self.store.save_player_data(fresh_player_data)
                logger.info("Fresh FPL data fetched and saved to store")
            except Exception as e:
                logger.error(f"Failed to fetch fresh FPL data: {e}")
                raise
        else:
            logger.warning("Returning cached FPL data due to use_cached flag")
        
        # Step 2: Load player data for processing
        players_data = self.store.load_player_data()
        if not players_data:
            raise ValueError("No player data available. Run 'fetch' command first.")
        
        players_data = players_data['players']

        # Step 3: Filter players if requested
        filtered_players = self._filter_out_unavailable_players(players_data, filter_unavailable_players_mode)
        
        return filtered_players
    
    def get_fixtures(self, use_cached: bool = False) -> Dict[str, Any]:
        """
        Get fixtures data, either from cache or fresh from API.
        
        Args:
            use_cached: If True, use cached data. If False, fetch fresh data.
            
        Returns:
            Dictionary containing fixtures data and metadata
        """
        
        # Step 1: Fetch fresh fixtures data
        if not use_cached:
            try:
                logger.info("Fetching fresh fixtures data...")
                # Fetch raw fixtures from FPL API
                fixtures_data = self.fetcher.get_fixtures()
                # Get teams data for team name resolution
                bootstrap_data = self.fetcher.get_fpl_static_data()
                teams_data = bootstrap_data.get('teams', [])
                # Process the raw fixtures data
                processed_fixtures = self.processor.process_fixtures_data(fixtures_data, teams_data)
                # Save to cache
                self.store.save_fixtures_data(processed_fixtures)    
                logger.info(f"Successfully fetched and processed {len(processed_fixtures)} fixtures")
            except Exception as e:
                logger.error(f"Failed to fetch fresh fixtures data: {e}")
                raise
        else:
            logger.warning("Returning cached fixtures data due to use_cached flag")

        # Step 2: Load cached fixtures data
        fixtures_data = self.store.load_fixtures_data()
        if not fixtures_data:
            raise ValueError("No fixtures data available. Run 'fetch' command first.")
        
        return fixtures_data
    
    def _filter_out_unavailable_players(self, players_data: Dict[str, Dict[str, Any]], filter_unavailable_players_mode: str = "no_filter") -> Dict[str, Dict[str, Any]]:
        """
        Filter players based on the filter_unavailable_players_mode.

        Args:
            players_data: Dictionary of processed player data
            filter_unavailable_players_mode: If "fpl_data_and_enrichments", apply availability filters using both FPL data and enrichments. If "fpl_data_only", apply availability filters using FPL data only. If "no_filter", return all players.

        Returns:
            Dictionary of filtered player data
        """

        # TODO: Add a filter using default filters - manual, then an approach using enrichment results.

        if filter_unavailable_players_mode == "no_filter":
            return players_data
        
        if filter_unavailable_players_mode != "fpl_data_only" and filter_unavailable_players_mode != "fpl_data_and_enrichments":
            raise ValueError(f"Invalid filter_unavailable_players_mode: {filter_unavailable_players_mode}")
        
        # Basic filtering - remove players who can't play according to FPL data
        available_players = self._filter_available_players_by_chance_of_playing(players_data)

        if filter_unavailable_players_mode == "fpl_data_only":
            logger.info(f"Basic filtering: {len(available_players)} players available from {len(players_data)} total")
            return available_players
        
        # Enrichments filtering - remove players who can't play according to enrichments
        available_players = self._filter_by_injury_news(available_players)
        logger.info(f"Enrichments filtering: {len(available_players)} players available from {len(players_data)} total")

        return available_players
    
    def _filter_available_players_by_chance_of_playing(self, players_data: Dict[str, Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        """Filter out players who can't play (e.g., injured, suspended, etc.) according to FPL data
        Args:
            players_data: Dictionary of processed player data

        Returns:
            Dictionary of filtered player data
        """
        available_players = {}
        
        for player_name, player_data in players_data.items():
            # Check chance of playing (25% threshold)
            chance_of_playing = player_data.get('chance_of_playing', 100)
            if chance_of_playing is not None and chance_of_playing < 25:
                continue
            
            available_players[player_name] = player_data
        
        return available_players
    
    def _filter_by_injury_news(self, players_data: Dict[str, Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        """Filter out players marked as 'Out' in injury news

        Args:
            players_data: Dictionary of processed player data

        Returns:
            Dictionary of filtered player data
        """
        available_players = {}
        
        for player_name, player_data in players_data.items():
            # Use the shared keyword extraction utility
            injury_status = extract_injury_status(player_name, {player_name: player_data})
            
            # Filter out players marked as "out"
            if not injury_status or injury_status != "out":
                available_players[player_name] = player_data
        
        return available_players
        
    def show_data_status(self, data_store: DataStore) -> Dict[str, Any]:
        """
        Display current data status.
        
        Args:
            data_store: DataStore instance for loading player data
            
        Returns:
            Dictionary containing data status information
        """
        try:            
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

        # TODO: sort this mess out - common too long, move some to display. Work out what it's trying to do.
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
                        filtered_players = self._filter_out_unavailable_players(all_players, "fpl_data_and_enrichments")
                        
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
                                    use_cached: bool = False) -> Dict[str, Dict[str, Any]]:
        """
        Get comprehensive data for all players in the current team.
        
        Args:
            current_team: Current team data from gwNN.json
            use_enrichments: Whether to include expert insights and injury news
            use_cached: Whether to use cached data only
            
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
            all_players_data = self.get_players(use_cached=use_cached)
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
                enriched_data = self._get_team_enrichments(player_names, use_cached)
            
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
    
    def _get_team_enrichments(self, player_names: List[str], use_cached: bool) -> Dict[str, Dict[str, Any]]:
        """
        Get enriched data (expert insights and injury news) for specific players.
        
        Args:
            player_names: List of player names to enrich
            use_cached: Whether to use cached data only
            
        Returns:
            Dictionary of enriched data indexed by player name
        """
        try:
            # Load existing enriched data from cache
            cached_data = self.store.load_player_data()
            if not cached_data or use_cached:
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
