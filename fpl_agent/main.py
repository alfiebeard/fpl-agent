"""
Main FPL Agent application
"""

import logging
import sys
from typing import Dict, Optional, Any
from datetime import datetime
import argparse

from .core.config import Config
from .core.team_manager import TeamManager
from .data import DataService
from .data.data_store import DataStore
from .strategies import TeamBuildingStrategy
from .utils.display import display_comprehensive_team_result
from .utils.validator import FPLValidator


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
        self.team_manager = TeamManager()
        
        # LLM strategy will be initialized lazily when needed
        self._llm_strategy = None
    
    @property
    def llm_strategy(self):
        """Lazy initialization of LLM strategy"""
        if self._llm_strategy is None:
            self._llm_strategy = TeamBuildingStrategy(self.config)
        return self._llm_strategy
    
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
    
    def enrich(self, force_refresh: bool = False) -> Dict[str, Any]:
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
    
    def build_team(self, budget: float = 100.0, gameweek: Optional[int] = None,
                   force_fetch: bool = False, force_enrich: bool = False,
                   force_all: bool = False, cached_only: bool = False, 
                   no_enrichments: bool = False, prompt_only: bool = False,
                   save_team: bool = False) -> None:
        """Build new team using LLM strategy"""
        try:
            print("⚽ Building new FPL team...")
            
            # Get all gameweek data in one call
            all_gameweek_data = self.data_service.get_all_gameweek_data(
                gameweek=gameweek or 1,
                force_fetch=force_fetch,
                use_enrichments=not no_enrichments,
                cached_only=cached_only
            )
            print(f"✅ Gameweek data loaded")
            
            # Build team using LLM strategy (no persistence, no business logic)
            print(f"\n⚽ Building team with £{budget}m budget...")
            team_result = self.llm_strategy.create_team(
                budget=budget,
                gameweek=gameweek or 1,
                all_gameweek_data=all_gameweek_data,
                use_enrichments=not no_enrichments,
                prompt_only=prompt_only
            )
            
            if prompt_only:
                print("✅ Prompt generation complete!")
                print("\n" + "="*50)
                print("📝 GENERATED PROMPT:")
                print("="*50)
                print(team_result['prompt'])
                return team_result
            
            # Handle persistence if requested
            if save_team:
                self.team_manager.save_new_team(team_result, gameweek or 1)
                print("✅ Team saved successfully!")
            else:
                print("✅ Team building complete (not saved)")
            
            # Display results
            display_comprehensive_team_result(team_result)
            
        except Exception as e:
            logger.error(f"Team building failed: {e}")
            print(f"❌ Team building failed: {e}")
            raise

    def gw_update(self, gameweek: Optional[int] = None, 
                  force_fetch: bool = False, force_enrich: bool = False,
                  force_all: bool = False, cached_only: bool = False, 
                  no_enrichments: bool = False, prompt_only: bool = False,
                  save_team: bool = False) -> None:
        """Complete weekly gameweek update using LLM strategy"""
        try:
            print("🔄 Starting weekly FPL update...")
            
            # Get all team context in one call (includes automatic free hit revert)
            team_context = self.team_manager.get_team_context(gameweek or 1)
            print(f"✅ Team context loaded for gameweek {team_context['gameweek']}")
            
            # Get all gameweek data in one call
            all_gameweek_data = self.data_service.get_all_gameweek_data(
                gameweek=gameweek or 1,
                force_fetch=force_fetch,
                use_enrichments=not no_enrichments,
                cached_only=cached_only
            )
            print(f"✅ Gameweek data loaded")
            
            # Update team using LLM strategy (no persistence, no business logic)
            print(f"\n⚽ Updating team for gameweek {gameweek or 'current'}...")
            team_result = self.llm_strategy.update_team_weekly(
                team_context=team_context,
                all_gameweek_data=all_gameweek_data,
                use_enrichments=not no_enrichments,
                prompt_only=prompt_only
            )
            
            if prompt_only:
                print("✅ Prompt generation complete!")
                print("\n" + "="*50)
                print("📝 GENERATED PROMPT:")
                print("="*50)
                print(team_result['prompt'])
                return team_result
            
            # Process team update and get final team
            final_team_result = self._handle_chip_usage(team_result, team_context)
            
            # Handle persistence if requested
            if save_team:
                self.team_manager.save_weekly_update(final_team_result, team_context)
                print("✅ Team saved successfully!")
            else:
                print("✅ Team update complete (not saved)")
            
            # Display results
            display_comprehensive_team_result(final_team_result)
            
        except Exception as e:
            logger.error(f"Weekly update failed: {e}")
            print(f"❌ Weekly update failed: {e}")
            raise
    
    def _handle_chip_usage(self, team_result: Dict[str, Any], team_context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle chip usage"""
        
        # Start with the original team
        updated_team = team_result.copy()
        
        # Handle chip usage - this might return a completely new team
        if team_result.get('chip'):
            chip_type = team_result['chip']
            
            if chip_type in ['wildcard', 'free_hit']:
                # Get budget from current team
                available_budget = self.team_manager.calculate_team_value(
                    team_context['team'], 
                    self.data_service.get_players(force_refresh=False)
                )
                print(f"🔄 {chip_type.title()} applied - building new team with £{available_budget}m budget...")
                
                # Build new team using existing build_team method
                new_team_result = self.build_team(
                    budget=available_budget,
                    gameweek=team_context['gameweek'],
                    save_team=False
                )
                
                # Add chip information to the new team
                new_team_result['chip'] = chip_type
                
                # Replace with the new team
                updated_team = new_team_result
            
            elif chip_type == 'bench_boost':
                print("🔄 Bench Boost applied - all 15 players will score")
                updated_team['chip'] = 'bench_boost'
                
            elif chip_type == 'triple_captain':
                print("🔄 Triple Captain applied - captain points tripled")
                updated_team['chip'] = 'triple_captain'
            
            # Preserve the LLM's chip_reason
            updated_team['chip_reason'] = team_result['chip_reason']
        
        # Validate transfers and bank
        self._validate_transfers_and_bank(updated_team, team_context)
        
        return updated_team

    def _validate_transfers_and_bank(self, team_result: Dict[str, Any], team_context: Dict[str, Any]) -> None:
        """Validate transfers and bank using FPLValidator workflow"""
        
        validator = FPLValidator()
        current_players = self.data_service.get_players(force_refresh=False)
        
        # Use the comprehensive validation workflow
        validator.validate_transfers_and_bank_workflow(
            team_result,
            team_context['gameweek'],
            team_context,
            current_players
        )

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
        fpl_agent = FPLAgent()
        
        if args.command == 'fetch':
            # Fetch fresh FPL data
            fpl_agent.fetch_fpl_data(force_refresh=args.force_fetch)
            
        elif args.command == 'enrich':
            # Simple enrich command - just call the enrich method
            fpl_agent.enrich(force_refresh=args.force_enrich)
                
        elif args.command == 'gw-update':
            # Complete weekly gameweek update
            fpl_agent.gw_update(
                gameweek=args.gameweek or 1,
                force_fetch=args.force_fetch,
                force_enrich=args.force_enrich,
                force_all=args.force_all,
                cached_only=args.cached_only,
                no_enrichments=args.no_enrichments,
                prompt_only=args.show_prompt
            )
            
            if not args.show_prompt:
                print("✅ Weekly update complete!")
            
        elif args.command == 'build-team':
            # Build new team
            fpl_agent.build_team(
                budget=args.budget,
                gameweek=args.gameweek,
                force_fetch=args.force_fetch,
                force_enrich=args.force_enrich,
                force_all=args.force_all,
                cached_only=args.cached_only,
                no_enrichments=args.no_enrichments,
                prompt_only=args.show_prompt
            )
            
            if not args.show_prompt:
                print("✅ Team building complete!")
            
        elif args.command == 'show-data':
            # Show current data status
            fpl_agent.data_service.show_data_status(fpl_agent.data_store)
            
        elif args.command == 'show-players':
            # Show available players breakdown
            fpl_agent.data_service.show_players_status(fpl_agent.data_store, fpl_agent.config)
        
    except Exception as e:
        logger.error(f"Command failed: {e}")
        print(f"\n❌ Command failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
