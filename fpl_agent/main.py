"""
Main FPL Optimizer application - Simplified with smart data handling
"""

import logging
import sys
import os
from typing import Dict, Optional, Any
from datetime import datetime
import argparse
from pathlib import Path

# Handle imports for both direct execution and module execution
try:
    # When run as module (python -m fpl_agent.main)
    from .core.config import Config
    from .core.models import FPLTeam
    from .data import DataService
    from .data.data_store import DataStore
    from .strategies import TeamBuildingStrategy
    from .utils.display import display_comprehensive_team_result

except ImportError:
    # When run directly (python fpl_agent/main.py)
    # Add the parent directory to the path
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from fpl_agent.core.config import Config
    from fpl_agent.core.models import FPLTeam
    from fpl_agent.data import DataService
    from fpl_agent.data.data_store import DataStore
    from fpl_agent.strategies import TeamBuildingStrategy
    from fpl_agent.utils.display import display_comprehensive_team_result


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)


class FPLAgent:
    """Enhanced FPL Agent with smart data handling"""
    
    def __init__(self, config: Optional[Config] = None):
        """Initialize the FPL Agent"""
        if config is None:
            config = Config()
        self.config = config
        
        # Initialize services
        self.data_service = DataService(config)
        self.data_store = DataStore()
        
        # Initialize team manager
        from .core.team_manager import TeamManager
        self.team_manager = TeamManager()
        
        # LLM strategy will be initialized lazily when needed
        self._llm_strategy = None
    
    @property
    def llm_strategy(self):
        """Lazy initialization of LLM strategy"""
        if self._llm_strategy is None:
            self._llm_strategy = TeamBuildingStrategy(self.config)
        return self._llm_strategy
    
    # ... existing code ...
    
    def should_fetch_data(self, force_fetch: bool, cached_only: bool, data_fresh: bool) -> bool:
        """Determine if we should fetch fresh FPL data"""
        if cached_only:
            return False
        if force_fetch:
            return True
        return not data_fresh
    
    def should_enrich_data(self, force_enrich: bool, cached_only: bool, enrich_fresh: bool) -> bool:
        """Determine if we should run LLM enrichment"""
        if cached_only:
            return False
        if force_enrich:
            return True
        return not enrich_fresh
    
    def fetch_fpl_data(self, force_refresh: bool = False) -> Dict[str, Any]:
        """Fetch both FPL player data and fixtures data"""
        try:
            logger.info("Fetching FPL data...")
            
            # Fetch players (existing logic)
            player_result = self.data_service.get_players(force_refresh=force_refresh)
            
            # Fetch fixtures (new logic)
            fixtures_result = self.data_service.get_fixtures(force_refresh=force_refresh)
            
            # Return both results
            return {
                'players': list(player_result.values()),
                'total_players': len(player_result),
                'fixtures': fixtures_result['fixtures'],
                'total_fixtures': fixtures_result['total_fixtures'],
                'fetched_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"FPL data fetch failed: {e}")
            raise
    
    def enrich_player_data(self, force_refresh: bool = False) -> Dict[str, Any]:
        """Enrich player data with LLM insights"""
        try:
            logger.info("Enriching player data with LLM insights...")
            
            if force_refresh:
                print("🔄 Forcing fresh enrichment (this will take 15-20 minutes)...")
            else:
                print("🧠 Enriching player data with LLM insights...")
                print("⏱️  This process takes 15-20 minutes but is cached for future use")
            
            # Load current player data
            players_data = self.data_store.get_players_data()
            if not players_data:
                raise ValueError("No player data available for enrichment")
            
            print(f"📊 Enriching {len(players_data)} players from {len(set(player.get('team_name') for player in players_data.values()))} teams...")
            
            # Use DataProcessor to enrich player data by teams
            from .data.data_processor import DataProcessor
            from .strategies.team_analysis_strategy import TeamAnalysisStrategy
            
            data_processor = DataProcessor(self.config)
            team_analysis_strategy = TeamAnalysisStrategy(self.config)
            
            # Enrich the player data
            enriched_players = data_processor.enrich_player_data_by_teams(players_data, team_analysis_strategy)
            
            # Add enrichment timestamp
            enriched_data = {
                'players': enriched_players,
                'enrichment_timestamp': datetime.now().isoformat(),
                'enrichment_status': 'completed',
                'total_players_enriched': len(enriched_players)
            }
            
            # Store enriched data back to data store
            self.data_store.save_player_data(enriched_data)
            
            print(f"✅ Successfully enriched {len(enriched_players)} players")
            
            return {
                'enriched_players': len(enriched_players),
                'status': 'success',
                'message': f'Successfully enriched {len(enriched_players)} players',
                'enriched_at': datetime.now().isoformat()
            }
                
        except Exception as e:
            logger.error(f"Failed to enrich player data: {e}")
            print(f"❌ Error enriching player data: {e}")
            return {
                'enriched_players': 0,
                'status': 'failed',
                'error': str(e)
            }
    
    def enrich(self, force_refresh: bool = False) -> Dict[str, Any]:
        """Simple enrich method for the enrich command"""
        return self.enrich_player_data(force_refresh=force_refresh)
    
    def gw_update(self, gameweek: Optional[int] = None, 
                  force_fetch: bool = False, force_enrich: bool = False,
                  force_all: bool = False, cached_only: bool = False, 
                  no_enrichments: bool = False, prompt_only: bool = False) -> Dict[str, Any]:
        """Complete weekly gameweek update workflow"""
        try:
            print("🔄 Starting weekly FPL update...")
            
            # Get processed players data using the common service
            formatted_players = self.data_service.get_processed_players(
                force_fetch=force_fetch,
                force_enrich=force_enrich,
                force_all=force_all,
                cached_only=cached_only,
                no_enrichments=no_enrichments
            )
            
            print(f"✅ Processed players data ready")
            
            # Update team using LLM strategy
            print(f"\n⚽ Updating team for gameweek {gameweek or 'current'}...")
            team_result = self.llm_strategy.update_team_weekly(
                gameweek=gameweek,
                use_semantic_filtering=True,
                force_refresh=False,
                use_embeddings=not no_enrichments,  # Opposite of no_enrichments
                available_players=formatted_players,
                prompt_only=prompt_only
            )
            
            if prompt_only:
                print("✅ Prompt generation complete!")
                return {
                    'prompt': team_result['prompt'],
                    'completed_at': datetime.now().isoformat()
                }
            
            print("✅ Weekly update complete!")
            
            return {
                'team_update': team_result,
                'completed_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Weekly update failed: {e}")
            print(f"❌ Weekly update failed: {e}")
            raise
    
    def build_team(self, budget: float = 100.0, gameweek: Optional[int] = None,
                   force_fetch: bool = False, force_enrich: bool = False,
                   force_all: bool = False, cached_only: bool = False, 
                   no_enrichments: bool = False, prompt_only: bool = False) -> Dict[str, Any]:
        """Build new team with smart data handling"""
        try:
            print("⚽ Building new FPL team...")
            
            # Get processed players data using the common service
            formatted_players = self.data_service.get_processed_players(
                force_fetch=force_fetch,
                force_enrich=force_enrich,
                force_all=force_all,
                cached_only=cached_only,
                no_enrichments=no_enrichments
            )
            
            print(f"✅ Processed players data ready")
            
            # Build team using LLM strategy
            print(f"\n⚽ Building team with £{budget}m budget...")
            team_result = self.llm_strategy.create_team(
                budget=budget,
                gameweek=gameweek or 1,
                use_semantic_filtering=True,
                force_refresh=False,
                use_embeddings=not no_enrichments,  # Opposite of no_enrichments
                available_players=formatted_players,
                prompt_only=prompt_only
            )
            
            if prompt_only:
                print("✅ Prompt generation complete!")
                return {
                    'prompt': team_result['prompt'],
                    'completed_at': datetime.now().isoformat()
                }
            
            print("✅ Team building complete!")
            
            return {
                'team_data': team_result,
                'completed_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Team building failed: {e}")
            print(f"❌ Team building failed: {e}")
            raise
    
    def show_data_status(self) -> Dict[str, Any]:
        """Display current data status"""
        try:
            print("📊 FPL Data Status")
            print("=" * 50)
            
            # Check data freshness using DataStore
            fpl_data = self.data_store.load_player_data()
            fpl_age_hours = None
            if fpl_data and 'cache_timestamp' in fpl_data:
                fpl_age_hours = self.data_store._calculate_data_age_hours(fpl_data)
            
            # Check embeddings freshness
            embeddings_file = Path("team_data/player_embeddings.json")
            embeddings_age_hours = None
            if embeddings_file.exists():
                file_stat = embeddings_file.stat()
                embeddings_age_hours = (datetime.now().timestamp() - file_stat.st_mtime) / 3600
            
            # Check enriched data freshness
            enriched_age_hours = None
            if fpl_data and 'enrichment_timestamp' in fpl_data:
                enriched_age_hours = self.data_store._calculate_data_age_hours(fpl_data, 'enrichment_timestamp')
            
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
    
    def show_players_status(self) -> Dict[str, Any]:
        """Display available players breakdown showing filtering process"""
        try:
            print("👥 FPL Players Status")
            print("=" * 50)
            
            # Load player data
            players_data = self.data_store.load_player_data()
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
            available_players = self.data_service.processor._filter_available_players(all_players)
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
                    formatted_output = self.data_service.processor.format_players_by_position_ranked(
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
                    formatted_output = self.data_service.processor.format_players_by_position_ranked(
                        position_data,
                        use_embeddings=True,  # Show injury news and expert insights if available
                        include_rankings=True,
                        include_scores=False
                    )
                    print(formatted_output)
            
            print(f"\n✅ Available Players: {len(available_players)}")
            print("-" * 30)
            
            # Check if embedding filtering is available and configured
            embeddings_config = self.config.get('embeddings', {})
            use_embeddings = embeddings_config.get('use_embeddings', False)
            
            if use_embeddings:
                print(f"🔍 Embedding filtering: ENABLED")
                
                # Check if embeddings cache exists
                embeddings_file = Path("team_data/player_embeddings.json")
                if embeddings_file.exists():
                    try:
                        # Apply embedding filtering
                        filtered_players = self.data_service.processor.filter_available_players(
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
                        formatted_top_players = self.data_service.processor.format_players_by_position_ranked(
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
                        formatted_filtered_out = self.data_service.processor.format_players_by_position_ranked(
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
        """Show summary of available players when no embedding filtering"""
        print(f"\n📋 Basic Players Summary:")
        print("-" * 30)
        
        # Use the common formatting method from DataProcessor
        formatted_output = self.data_service.processor.format_players_by_position_ranked(
            available_players, 
            use_embeddings=False, 
            include_rankings=True
        )
        print(formatted_output)
        
        # Note: These players would go into LLM prompts with basic stats only
        print(f"\n📝 Note: These players would go into LLM prompts with basic stats only (no expert insights or injury news)")


def main():
    """Main entry point with simplified command structure"""
    parser = argparse.ArgumentParser(description='FPL Agent - Smart Data Handling')
    
    # Main command
    parser.add_argument('command', choices=[
        'fetch', 'enrich', 'gw-update', 'build-team', 'show-data', 'show-players'
    ], help='Command to run')
    
    # Smart data flags
    parser.add_argument('--force-fetch', action='store_true',
                       help='Force fresh FPL data fetch')
    parser.add_argument('--force-enrich', action='store_true',
                       help='Force fresh LLM enrichment')
    parser.add_argument('--force-all', action='store_true',
                       help='Force both fresh fetch and enrichment')
    parser.add_argument('--cached-only', action='store_true',
                       help='Use ONLY cached data (no API calls or enrichment)')
    parser.add_argument('--no-enrichments', action='store_true',
                       help='Use only basic player data without expert insights or injury news')
    
    # Common options
    parser.add_argument('--budget', type=float, default=100.0,
                       help='Team budget in millions (default: 100.0)')
    parser.add_argument('--gameweek', type=int,
                       help='Current gameweek')
    parser.add_argument('--team-file', type=str,
                       help='Path to JSON file containing current team data')
    
    # Save options
    parser.add_argument('--save-team', action='store_true',
                       help='Save the created team to a JSON file')
    parser.add_argument('--save-file', type=str,
                       help='Specific file path to save team')
    parser.add_argument('--show-prompt', action='store_true',
                       help='Show the prompt that would be sent to the LLM (for debugging)')
    
    args = parser.parse_args()
    
    try:
        optimizer = FPLAgent()
        
        if args.command == 'fetch':
            # Fetch fresh FPL data
            result = optimizer.fetch_fpl_data(force_refresh=args.force_fetch)
            print(f"\n✅ Fetched {result['total_players']} players and {result['total_fixtures']} fixtures")
            print(f"📅 Data timestamp: {result['fetched_at']}")
            
        elif args.command == 'enrich':
            # Simple enrich command - just call the enrich method
            result = optimizer.enrich(force_refresh=args.force_enrich)
            if result['status'] == 'success':
                print(f"\n✅ Enriched {result['enriched_players']} players")
                print(f"📅 Enriched at: {result['enriched_at']}")
            elif result['status'] == 'not_implemented':
                print(f"\n⚠️  {result['message']}")
                print(f"📅 Status checked at: {result['enriched_at']}")
            else:
                print(f"\n❌ Enrichment failed: {result.get('error', 'Unknown error')}")
                sys.exit(1)
                
        elif args.command == 'gw-update':
            if args.show_prompt:
                # Show the prompt that would be sent to the LLM
                print("📝 FPL Gameweek Update Prompt")
                print("=" * 80)
                
                # Generate the prompt without executing
                try:
                    # Get real team data for prompt generation
                    gameweek = args.gameweek or 1
                    
                    # Try to get the latest available team for prompt generation
                    try:
                        # First try to get the previous team for the specified gameweek
                        previous_team = optimizer.team_manager.get_previous_team(gameweek)
                        if previous_team:
                            current_team = previous_team
                            print(f"📋 Using real team data from Gameweek {gameweek - 1}")
                        else:
                            # If no previous team for this gameweek, try to get the latest available team
                            latest_gw = optimizer.team_manager.get_latest_gameweek()
                            if latest_gw and latest_gw >= 1:
                                latest_team = optimizer.team_manager.load_team(latest_gw)
                                if latest_team:
                                    current_team = latest_team
                                    print(f"📋 Using real team data from latest available Gameweek {latest_gw}")
                                else:
                                    raise ValueError("Could not load latest team")
                            else:
                                raise ValueError("No teams available")
                        
                        # Ensure the team data has the correct structure for the prompt formatter
                        # The PromptFormatter expects either direct team data or team.team structure
                        if current_team and 'team' in current_team:
                            # If we have team.team structure, extract the inner team data
                            if 'team' in current_team['team']:
                                # Handle double-nested structure: team.team.team
                                current_team = {
                                    'starting': current_team['team']['team']['starting'],
                                    'substitutes': current_team['team']['team']['substitutes'],
                                    'captain': current_team['team'].get('captain'),
                                    'vice_captain': current_team['team'].get('vice_captain'),
                                    'total_cost': current_team['team'].get('total_cost'),
                                    'bank': current_team['team'].get('bank')
                                }
                            else:
                                # Handle single-nested structure: team.team
                                current_team = current_team['team']
                    except Exception as e:
                        logger.warning(f"Could not load real team data: {e}, using sample data")
                        # Fallback to sample data if no real team exists
                        current_team = {
                            "team": {
                                "starting": [
                                    {"name": "Sample Player 1", "position": "GK", "price": 5.0, "team": "Sample Team"},
                                    {"name": "Sample Player 2", "position": "DEF", "price": 5.5, "team": "Sample Team"}
                                ],
                                "substitutes": [
                                    {"name": "Sample Sub 1", "position": "MID", "price": 5.0, "team": "Sample Team"}
                                ]
                            }
                        }
                        print(f"⚠️  No real team data available, using sample data")
                    
                    # Get real chips and transfers data from meta
                    try:
                        meta_data = optimizer.team_manager.get_meta()
                        chips_data = optimizer.team_manager.get_available_chips_from_meta(meta_data)
                        transfers_data = optimizer.team_manager.get_available_transfers_from_meta(meta_data)
                        print(f"🎯 Using real chips and transfers data")
                    except Exception as e:
                        logger.warning(f"Could not load meta data: {e}, using sample data")
                        chips_data = {"wildcard": True, "bench_boost": True, "free_hit": True, "triple_captain": True}
                        transfers_data = {"free_transfers": 1}
                    
                    # Generate the prompt using the real method with prompt_only=True
                    result = optimizer.gw_update(
                        gameweek=gameweek,
                        force_fetch=args.force_fetch,
                        force_enrich=args.force_enrich,
                        force_all=args.force_all,
                        cached_only=args.cached_only,
                        no_enrichments=args.no_enrichments,
                        prompt_only=True
                    )
                    
                    prompt = result['prompt']
                    print(f"Prompt Length: {len(prompt)} characters")
                    print("=" * 80)
                    print(prompt)
                    print("=" * 80)
                    print("✅ Prompt generated successfully. Use --show-prompt to preview, remove flag to execute.")
                    
                except Exception as e:
                    logger.error(f"Failed to generate prompt: {e}")
                    print(f"❌ Error generating prompt: {e}")
                    sys.exit(1)
            else:
                # Complete weekly gameweek update
                result = optimizer.gw_update(
                    gameweek=args.gameweek,
                    force_fetch=args.force_fetch,
                    force_enrich=args.force_enrich,
                    force_all=args.force_all,
                    cached_only=args.cached_only,
                    no_enrichments=args.no_enrichments
                )
                
                # Display team update result
                display_comprehensive_team_result(result['team_update'])
                
                # Save team if requested
                if args.save_team:
                    try:
                        team_data = result['team_update']
                        # Use TeamManager to save the team
                        gameweek = args.gameweek or 1
                        optimizer.team_manager.save_team(gameweek, team_data)
                        print(f"\n💾 Team saved for Gameweek {gameweek}")
                    except Exception as e:
                        logger.error(f"Failed to save team: {e}")
                        print(f"\n❌ Error saving team: {e}")
            
        elif args.command == 'build-team':
            if args.show_prompt:
                # Show the prompt that would be sent to the LLM
                print("📝 FPL Team Building Prompt")
                print("=" * 80)
                
                # Generate the prompt without executing
                try:
                    # Call the real method with prompt_only=True to get the exact same prompt
                    result = optimizer.build_team(
                        budget=args.budget,
                        gameweek=args.gameweek,
                        force_fetch=args.force_fetch,
                        force_enrich=args.force_enrich,
                        force_all=args.force_all,
                        cached_only=args.cached_only,
                        no_enrichments=args.no_enrichments,
                        prompt_only=True
                    )
                    
                    prompt = result['prompt']
                    print(f"Prompt Length: {len(prompt)} characters")
                    print("=" * 80)
                    print(prompt)
                    print("=" * 80)
                    print("✅ Prompt generated successfully. Use --show-prompt to preview, remove flag to execute.")
                    
                except Exception as e:
                    logger.error(f"Failed to generate prompt: {e}")
                    print(f"❌ Error generating prompt: {e}")
                    sys.exit(1)
            else:
                # Build new team
                result = optimizer.build_team(
                    budget=args.budget,
                    gameweek=args.gameweek,
                    force_fetch=args.force_fetch,
                    force_enrich=args.force_enrich,
                    force_all=args.force_all,
                    cached_only=args.cached_only,
                    no_enrichments=args.no_enrichments
                )
                
                # Display team result
                display_comprehensive_team_result(result['team_data'])
                
                # Save team if requested
                if args.save_team:
                    try:
                        team_data = result['team_data']
                        # Use TeamManager to save the team
                        gameweek = args.gameweek or 1
                        optimizer.team_manager.save_team(gameweek, team_data)
                        print(f"\n💾 Team saved for Gameweek {gameweek}")
                    except Exception as e:
                        logger.error(f"Failed to save team: {e}")
                        print(f"\n❌ Error saving team: {e}")
            
        elif args.command == 'show-data':
            # Show current data status
            optimizer.show_data_status()
            
        elif args.command == 'show-players':
            # Show available players breakdown
            optimizer.show_players_status()
        
    except Exception as e:
        logger.error(f"Command failed: {e}")
        print(f"\n❌ Command failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
