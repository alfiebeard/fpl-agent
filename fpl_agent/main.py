"""
Main FPL Optimizer application - Simplified with smart data handling
"""

import logging
import sys
import os
import json
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
        """Fetch FPL data with smart caching"""
        try:
            logger.info("Fetching FPL data...")
            result = self.data_service.get_players(force_refresh=force_refresh)
            
            # Return basic player data
            return {
                'players': list(result.values()),
                'total_players': len(result),
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
            
            # TODO: Implement actual enrichment functionality
            # For now, return a placeholder response
            print("⚠️  Enrichment functionality not yet implemented")
            print("   This is a placeholder for future development")
            
            return {
                'enriched_players': 0,
                'status': 'not_implemented',
                'message': 'Enrichment functionality not yet implemented',
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
    
    def gw_update(self, gameweek: Optional[int] = None, 
                  force_fetch: bool = False, force_enrich: bool = False,
                  force_all: bool = False, cached_only: bool = False) -> Dict[str, Any]:
        """Complete weekly gameweek update workflow"""
        try:
            print("🔄 Starting weekly FPL update...")
            
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
            
            data_status = {
                'fpl_data': {
                    'fresh': fpl_age_hours is not None and fpl_age_hours < 1.0,
                    'age_hours': fpl_age_hours,
                    'available': fpl_data is not None
                },
                'enriched_data': {
                    'fresh': False,
                    'age_hours': None,
                    'available': False
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
            
            # Determine what to do based on flags and data freshness
            should_fetch = self.should_fetch_data(
                force_fetch or force_all, 
                cached_only, 
                data_status['fpl_data']['fresh']
            )
            
            should_enrich = self.should_enrich_data(
                force_enrich or force_all, 
                cached_only, 
                data_status['enriched_data']['fresh']
            )
            
            # Show data status
            print(f"\n📊 Data Status:")
            fpl_age = data_status['fpl_data']['age_hours'] or 0
            enrich_age = data_status['enriched_data']['age_hours'] or 0
            print(f"   • FPL data: {fpl_age:.1f} hours old")
            print(f"   • Enriched data: {enrich_age:.1f} hours old")
            
            if cached_only:
                print("   • Using ONLY cached data (--cached-only flag)")
                should_fetch = False
                should_enrich = False
            
            # Step 1: Fetch FPL data if needed
            if should_fetch:
                print(f"\n🔄 Fetching fresh FPL data...")
                fetch_result = self.fetch_fpl_data(force_refresh=True)
                print(f"✅ Fetched {fetch_result['total_players']} players")
            else:
                print(f"\n📊 Using cached FPL data ({fpl_age:.1f} hours old)")
            
            # Step 2: Enrich data if needed
            if should_enrich:
                print(f"\n🧠 Enriching player data...")
                enrich_result = self.enrich_player_data(force_refresh=True)
                if enrich_result['status'] == 'success':
                    print(f"✅ Enriched {enrich_result['enriched_players']} players")
                else:
                    print(f"❌ Enrichment failed: {enrich_result.get('error', 'Unknown error')}")
            else:
                print(f"\n🧠 Using cached enriched data ({enrich_age:.1f} hours old)")
            
            # Step 3: Update team for gameweek
            print(f"\n⚽ Updating team for gameweek {gameweek or 'current'}...")
            team_result = self.llm_strategy.update_team_weekly(
                gameweek=gameweek,
                use_semantic_filtering=True,
                force_refresh=False,  # Use cached enriched data
                use_embeddings=False
            )
            
            print("✅ Weekly update complete!")
            
            return {
                'fetch_performed': should_fetch,
                'enrich_performed': should_enrich,
                'team_update': team_result,
                'data_status': data_status,
                'completed_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Weekly update failed: {e}")
            print(f"❌ Weekly update failed: {e}")
            raise
    
    def build_team(self, budget: float = 100.0, gameweek: Optional[int] = None,
                   force_fetch: bool = False, force_enrich: bool = False,
                   force_all: bool = False, cached_only: bool = False) -> Dict[str, Any]:
        """Build new team with smart data handling"""
        try:
            print("⚽ Building new FPL team...")
            
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
            
            data_status = {
                'fpl_data': {
                    'fresh': fpl_age_hours is not None and fpl_age_hours < 1.0,
                    'age_hours': fpl_age_hours,
                    'available': fpl_data is not None
                },
                'enriched_data': {
                    'fresh': False,
                    'age_hours': None,
                    'available': False
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
            
            # Determine what to do based on flags and data freshness
            should_fetch = self.should_fetch_data(
                force_fetch or force_all, 
                cached_only, 
                data_status['fpl_data']['fresh']
            )
            
            should_enrich = self.should_enrich_data(
                force_enrich or force_all, 
                cached_only, 
                data_status['enriched_data']['fresh']
            )
            
            # Show data status
            print(f"\n📊 Data Status:")
            fpl_age = data_status['fpl_data']['age_hours'] or 0
            enrich_age = data_status['enriched_data']['age_hours'] or 0
            print(f"   • FPL data: {fpl_age:.1f} hours old")
            print(f"   • Enriched data: {enrich_age:.1f} hours old")
            
            if cached_only:
                print("   • Using ONLY cached data (--cached-only flag)")
                should_fetch = False
                should_enrich = False
            
            # Step 1: Fetch FPL data if needed
            if should_fetch:
                print(f"\n🔄 Fetching fresh FPL data...")
                fetch_result = self.fetch_fpl_data(force_refresh=True)
                print(f"✅ Fetched {fetch_result['total_players']} players")
            else:
                print(f"\n📊 Using cached FPL data ({fpl_age:.1f} hours old)")
            
            # Step 2: Enrich data if needed
            if should_enrich:
                print(f"\n🧠 Enriching player data...")
                enrich_result = self.enrich_player_data(force_refresh=True)
                if enrich_result['status'] == 'success':
                    print(f"✅ Enriched {enrich_result['enriched_players']} players")
                else:
                    print(f"❌ Enrichment failed: {enrich_result.get('error', 'Unknown error')}")
            else:
                print(f"\n🧠 Using cached enriched data ({enrich_age:.1f} hours old)")
            
            # Step 3: Build team
            print(f"\n⚽ Building team with £{budget}m budget...")
            team_result = self.llm_strategy.create_team(
                budget=budget,
                gameweek=gameweek or 1,
                use_semantic_filtering=True,
                force_refresh=False,  # Use cached enriched data
                use_embeddings=False
            )
            
            print("✅ Team building complete!")
            
            return {
                'fetch_performed': should_fetch,
                'enrich_performed': should_enrich,
                'team_data': team_result,
                'data_status': data_status,
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
            
            data_status = {
                'fpl_data': {
                    'fresh': fpl_age_hours is not None and fpl_age_hours < 1.0,
                    'age_hours': fpl_age_hours,
                    'available': fpl_data is not None
                },
                'enriched_data': {
                    'fresh': False,
                    'age_hours': None,
                    'available': False
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


def main():
    """Main entry point with simplified command structure"""
    parser = argparse.ArgumentParser(description='FPL Agent - Smart Data Handling')
    
    # Main command
    parser.add_argument('command', choices=[
        'fetch', 'enrich', 'gw-update', 'build-team', 'show-data'
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
            print(f"\n✅ Fetched {result['total_players']} players")
            print(f"📅 Data timestamp: {result['fetched_at']}")
            
        elif args.command == 'enrich':
            # Enrich player data with LLM insights
            result = optimizer.enrich_player_data(force_refresh=args.force_enrich)
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
                    # Create minimal data for prompt generation
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
                    
                    chips_data = {"wildcard": True, "bench_boost": True, "free_hit": True, "triple_captain": True}
                    transfers_data = {"free_transfers": 1}
                    
                    # Generate the prompt
                    prompt = optimizer.llm_strategy._create_weekly_update_prompt(
                        current_team, args.gameweek or 1, chips_data, transfers_data
                    )
                    
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
                    cached_only=args.cached_only
                )
                
                # Display team update result
                display_comprehensive_team_result({'team_data': result['team_update']})
                
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
                    # Generate the prompt
                    prompt = optimizer.llm_strategy._create_team_creation_prompt(
                        args.budget, args.gameweek or 1
                    )
                    
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
                    cached_only=args.cached_only
                )
                
                # Display team result
                display_comprehensive_team_result({'team_data': result['team_data']})
                
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
        
    except Exception as e:
        logger.error(f"Command failed: {e}")
        print(f"\n❌ Command failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
