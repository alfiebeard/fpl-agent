"""
Main FPL Agent application
"""

import logging
import sys
from typing import Dict, Optional, Any, List
from datetime import datetime
import argparse

from .core.config import Config
from .core.team_manager import TeamManager
from .data import DataService
from .data.data_store import DataStore
from .utils.team_utils import group_players_by_team, get_team_fixture_info
from .strategies.team_analysis_strategy import TeamAnalysisStrategy
from .strategies import TeamBuildingStrategy
from .utils.display import display_comprehensive_team_result, display_fetch_results, display_data_status, display_detailed_players_status
from .data.embedding_filter import EmbeddingFilter
from .utils.prompt_formatter import PromptFormatter


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
    
    def fetch_fpl_data(self, use_cached: bool = False, use_enrichments: bool = False, gameweek: Optional[int] = None, filter_unavailable_players: Optional[bool] = False) -> None:
        """Fetch both FPL player data and fixtures data"""
        try:
            if use_cached:
                logger.info("Loading cached FPL data...")
            else:
                logger.info("Fetching fresh FPL data...")

            if gameweek is None:
                gameweek = self.data_service.fetcher.get_current_gameweek() or 1

            if filter_unavailable_players:
                if use_enrichments:
                    filter_unavailable_players_mode = "fpl_data_and_enrichments"
                else:
                    filter_unavailable_players_mode = "fpl_data_only"
            else:
                filter_unavailable_players_mode = "no_filter"

            # For fetch command, don't filter players - show all data
            all_gameweek_data = self.data_service.get_all_gameweek_data(
                gameweek=gameweek,
                use_cached=use_cached,
                filter_unavailable_players_mode=filter_unavailable_players_mode
            )

            if not use_cached and use_enrichments:
                # If using enrichments, gets ranking by default too.
                self.enrich(all_gameweek_data, gameweek)
            
            display_fetch_results({
                'total_players': len(all_gameweek_data['players']),
                'total_fixtures': len(all_gameweek_data['fixtures']),
                'fetched_at': datetime.now().isoformat()
            }, use_cached)

            return all_gameweek_data
            
        except Exception as e:
            logger.error(f"FPL data fetch failed: {e}")
            raise
    
    def enrich(self, all_gameweek_data: Optional[Dict[str, Any]] = None, gameweek: Optional[int] = None, rank_players: Optional[bool] = True, prompt_only: bool = False) -> Dict[str, Any]:
        """Enrich player data with LLM insights including expert insights and injury news"""
        try:
            logger.info("Enriching player data with LLM insights...")

            if gameweek is None:
                gameweek = self.data_service.fetcher.get_current_gameweek() or 1

            if all_gameweek_data is None:
                # Fetch all gameweek data in one call - when enriching used cached data - the flow should be fetch then enrich or use fetch with --use-enrichments for all.
                # For team building, filter players to only show available ones
                all_gameweek_data = self.fetch_fpl_data(
                    use_cached=True, 
                    use_enrichments=False, 
                    gameweek=gameweek, 
                    filter_unavailable_players=False
                )

            # Group players by team
            team_players = group_players_by_team(all_gameweek_data['players'])

            # Get enrichments by team
            print(f"📊 Enriching {len(all_gameweek_data['players'])} players from {len(team_players)} teams...")

            team_analysis_strategy = TeamAnalysisStrategy(self.config)
            
            # Handle prompt-only mode for first team
            if prompt_only:
                # Get the first team for prompt display
                first_team_players = team_players[0]
                first_team_name = list(first_team_players.values())[0].get('team_name')
                first_team_fixtures = get_team_fixture_info(first_team_name, all_gameweek_data['fixtures'], gameweek)
                
                print(f"📝 Showing prompts for first team: {first_team_name}")
                print("\n" + "="*50)
                print("🔍 HINTS & TIPS PROMPT:")
                print("="*50)
                
                # Get and display hints & tips prompt
                hints_prompt = team_analysis_strategy._create_hints_tips_prompt(
                    first_team_name, 
                    first_team_players,
                    gameweek, 
                    first_team_fixtures
                )
                print(hints_prompt)
                
                print("\n" + "="*50)
                print("🏥 INJURY NEWS PROMPT:")
                print("="*50)
                
                # Get and display injury news prompt
                injury_prompt = team_analysis_strategy._create_injury_news_prompt(
                    first_team_name, 
                    first_team_players,
                    gameweek, 
                    first_team_fixtures
                )
                print(injury_prompt)
                
                print("\n" + "="*50)
                print("✅ Prompt display complete!")
                return {"prompt_only": True, "team_name": first_team_name}
            
            logger.info(f"Processing {len(team_players)} Premier League teams for enrichment")
            
            # Process each team sequentially
            for team_player_list in [team_players[0]]:
                try:
                    team_name = list(team_player_list.values())[0].get('team_name')
                    logger.info(f"Processing team {team_name}")
                    print(f"🔄 Processing {team_name}...")
                    
                    # Get fixture information for this team
                    fixture_info = get_team_fixture_info(team_name, all_gameweek_data['fixtures'], gameweek)
                    
                    # Get expert insights from LLM strategy
                    expert_insights = team_analysis_strategy.get_team_hints_tips(team_name, team_player_list, gameweek, fixture_info)
                    
                    # Get injury news from LLM strategy
                    injury_news = team_analysis_strategy.get_team_injury_news(team_name, team_player_list, gameweek, fixture_info)
                    
                    # Convert team_player_list to list of player dictionaries
                    team_players_list = list(team_player_list.values())
                    
                    # Apply enriched data to players
                    self._add_enrichments_to_players(all_gameweek_data['players'], team_players_list, expert_insights, injury_news)
                    
                    print(f"   ✅ Team data enriched for {team_name}")
                    
                except Exception as e:
                    logger.error(f"Failed to process team {team_name}: {e}")
                    print(f"   ❌ Team processing failed for {team_name}: {e}")
                    continue
            
            logger.info("Player enrichment completed")

            if rank_players:
                # Calculate embedding scores using EmbeddingFilter
                embedding_filter = EmbeddingFilter(self.config)
                player_embeddings = embedding_filter.calculate_player_embeddings(all_gameweek_data['players'], use_cached=False)
                player_embedding_scores = embedding_filter.calculate_player_embedding_scores(player_embeddings, all_gameweek_data['players'])
                
                # Add embedding scores to players
                if player_embeddings:
                    self._add_embedding_scores_to_players(all_gameweek_data['players'], player_embedding_scores)
                    print(f"✅ Added embedding scores for {len(player_embedding_scores)} players")
                else:
                    print("⚠️  No embedding scores calculated")
            
            # Save enriched data
            enriched_data = {
                'players': all_gameweek_data['players'],
                'enrichment_timestamp': datetime.now().isoformat()
            }
            
            self.data_service.store.save_player_data(enriched_data)
            print(f"✅ Successfully enriched player data for {len(all_gameweek_data['players'])} teams")
                
        except Exception as e:
            logger.error(f"Failed to enrich player data: {e}")
            print(f"❌ Error enriching player data: {e}")
        
    def _add_enrichments_to_players(self, players_data: Dict[str, Dict[str, Any]], 
                                      team_players: List[Dict[str, Any]], 
                                      expert_insights: Dict[str, str],
                                      injury_news: Dict[str, str]) -> None:
        """Apply enriched data to player records."""
        for player in team_players:
            player_name = player['full_name']
            if player_name in players_data:
                players_data[player_name]['expert_insights'] = expert_insights.get(
                    player_name, "No expert insights available"
                )
                players_data[player_name]['injury_news'] = injury_news.get(
                    player_name, "No injury news available"
                )
    
    def _add_embedding_scores_to_players(self, players_data: Dict[str, Dict[str, Any]], 
                                        embedding_scores: Dict[str, Dict[str, Any]]) -> None:
        """Add embedding scores to players."""
        for player_name, scores in embedding_scores.items():
            if player_name in players_data:
                players_data[player_name].update(scores)
    
    def build_team(self, budget: float = 100.0, gameweek: Optional[int] = None,
                   cached_only: bool = False, rag_mode: str = "ranked_enrichments", prompt_only: bool = False,
                   save_team: bool = False) -> None:
        """Build new team using LLM strategy
        
        Args:
            budget: Team budget (£)
            gameweek: Gameweek number (Default: current gameweek)
            cached_only: Use cached data only (Default: False)
            rag_mode: RAG strategy to use for team building (Default: "ranked_enrichments")
                - "none": No enrichments, no ranking
                - "enrichments": Use enrichments, no ranking
                - "ranked_enrichments": Enrichments + ranking
            prompt_only: Show the prompt that would be sent to the LLM (for debugging) (Default: False)
            save_team: Save the created team to a JSON file (Default: False)
        """
        try:
            print("⚽ Building new FPL team...")
            print(f"🔄 Using RAG mode: {rag_mode}")

            if rag_mode == "none":
                use_enrichments = False
                use_ranking = False
            elif rag_mode == "enrichments":
                use_enrichments = True
                use_ranking = False
            elif rag_mode == "ranked_enrichments":
                use_enrichments = True
                use_ranking = True
            else:
                raise ValueError(f"Invalid rag_mode: {rag_mode}")
            
            # Fetch all gameweek data in one call
            # For team building, filter players to only show available ones
            all_gameweek_data = self.fetch_fpl_data(
                use_cached=cached_only, 
                use_enrichments=use_enrichments, 
                gameweek=gameweek, 
                filter_unavailable_players=True
            )

            print(f"✅ Gameweek data loaded")
            
            # Build team using LLM strategy
            print(f"\n⚽ Building team with £{budget}m budget...")
            team_result = self.llm_strategy.create_team(
                budget=budget,
                gameweek=gameweek,
                all_gameweek_data=all_gameweek_data,
                use_enrichments=use_enrichments,
                use_ranking=use_ranking,
                prompt_only=prompt_only
            )
            
            if prompt_only:
                print("✅ Prompt generation complete!")
                print("\n" + "="*50)
                print("📝 GENERATED PROMPT:")
                print("="*50)
                print(team_result['prompt'])
                return team_result
            
            # Save team if requested
            if save_team:
                self.team_manager.save_new_team(team_result, gameweek)
                print("✅ Team saved successfully!")
            else:
                print("✅ Team building complete (not saved)")
            
            # Display team results
            display_comprehensive_team_result(team_result)
            
        except Exception as e:
            logger.error(f"Team building failed: {e}")
            print(f"❌ Team building failed: {e}")
            raise

    def gw_update(self, gameweek: Optional[int] = None, cached_only: bool = False, 
                  rag_mode: str = "ranked_enrichments", prompt_only: bool = False,
                  save_team: bool = False) -> None:
        """Complete weekly gameweek update using LLM strategy
        
        Args:
            gameweek: Gameweek number (Default: current gameweek)
            cached_only: Use cached data only (Default: False)
            rag_mode: RAG strategy to use for team building (Default: "ranked_enrichments")
                - "none": No enrichments, no ranking
                - "enrichments": Use enrichments, no ranking
                - "ranked_enrichments": Enrichments + ranking
            prompt_only: Show the prompt that would be sent to the LLM (for debugging) (Default: False)
            save_team: Save the created team to a JSON file (Default: False)
        """
        
        try:
            print("🔄 Starting weekly FPL update...")
            print(f"🔄 Using RAG mode: {rag_mode}")
            
            if rag_mode == "none":
                use_enrichments = False
                use_ranking = False
            elif rag_mode == "enrichments":
                use_enrichments = True
                use_ranking = False
            elif rag_mode == "ranked_enrichments":
                use_enrichments = True
                use_ranking = True
            else:
                raise ValueError(f"Invalid rag_mode: {rag_mode}")
            
            # Get all team context in one call (includes automatic free hit revert)
            team_context = self.team_manager.get_team_context(gameweek or 1)
            print(f"✅ Team context loaded for gameweek {team_context['gameweek']}")
            
            # Fetch all gameweek data in one call
            # For team building, filter players to only show available ones
            all_gameweek_data = self.fetch_fpl_data(
                use_cached=cached_only, 
                use_enrichments=use_enrichments, 
                gameweek=gameweek, 
                filter_unavailable_players=True
            )

            print(f"✅ Gameweek data loaded")
            
            # Get data for current team players
            current_team_player_data = self.data_service.get_current_team_player_data(
                current_team=team_context['team'],
                use_enrichments=use_enrichments,
                use_cached=cached_only
            )
            print(f"✅ Current team player data loaded")

            # Add current team player data to team context
            team_context['current_team_player_data'] = current_team_player_data
            
            # Update team using LLM strategy (no persistence, no business logic)
            print(f"\n⚽ Updating team for gameweek {gameweek or 'current'}...")
            team_result = self.llm_strategy.update_team_weekly(
                team_context=team_context,
                all_gameweek_data=all_gameweek_data,
                use_enrichments=use_enrichments,
                use_ranking=use_ranking,
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
            
            # Validate chip availability before using it
            available_chips = team_context['chips']['available']
            if chip_type not in available_chips:
                print(f"❌ {chip_type.title()} chip is not available!")
                print(f"Available chips: {', '.join(available_chips) if available_chips else 'None'}")
                print(f"Used chips: {', '.join(chip['name'] for chip in team_context['chips']['used'])}")
                raise ValueError(f"{chip_type.title()} chip is not available for use")
            
            if chip_type in ['wildcard', 'free_hit']:
                print(f"✅ {chip_type.title()} chip is available - proceeding with team rebuild...")
                
                # Get budget from current team
                available_budget = self.team_manager.calculate_team_budget(
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
                print(f"✅ {chip_type.title()} chip is available - proceeding...")
                print("🔄 Bench Boost applied - all 15 players will score")
                updated_team['chip'] = 'bench_boost'
                
            elif chip_type == 'triple_captain':
                print(f"✅ {chip_type.title()} chip is available - proceeding...")
                print("🔄 Triple Captain applied - captain points tripled")
                updated_team['chip'] = 'triple_captain'
            
            # Preserve the LLM's chip_reason
            updated_team['chip_reason'] = team_result['chip_reason']
        
        return updated_team

    def show_data(self):
        """Show current data status"""
        return display_data_status(self.data_service.get_data_status(self.data_store))

    def show_players(self):
        """Show available players breakdown"""
        players_status = self.data_service.get_players_status(self.data_store, self.config)

        if 'error' in players_status:
            print(f"❌ {players_status['error']}")
        else:
            display_detailed_players_status(
                total_players=players_status['total_players'],
                available_players=players_status['available_players'],
                unavailable_players=players_status['unavailable_players'],
                filtered_players=players_status.get('filtered_players'),
                embedding_filtered_out=players_status.get('embedding_filtered_out'),
                use_embeddings=players_status['use_embeddings']
            )

def main():
    """Main entry point with simplified command structure"""
    parser = argparse.ArgumentParser(description='FPL Agent')
    
    # Main command
    parser.add_argument('command', choices=[
        'fetch', 'enrich', 'gw-update', 'build-team', 'show-data', 'show-players'
    ], help='Command to run')
    
    # Smart data flags
    parser.add_argument('--cached-only', action='store_true',
                       help='Use ONLY cached data (no API calls or enrichment). For fetch command: use stored data instead of fresh fetch.')
    parser.add_argument('--use-enrichments', action='store_true',
                       help='Use enrichments with expert insights or injury news, just basic data (default: False)')
    parser.add_argument('--rag-mode', choices=['none', 'enrichments', 'ranked_enrichments'], default='ranked_enrichments',
                       help='RAG mode to use for team building and weekly updates (default: ranked_enrichments)')
    parser.add_argument('--filter-unavailable-players', action='store_true',
                       help='Filter out unavailable players from the data (default: False)')
    
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
    parser.add_argument('--show-prompt', action='store_true',
                       help='Show the prompt that would be sent to the LLM (for debugging)')
    
    args = parser.parse_args()
    
    try:
        fpl_agent = FPLAgent()
        
        if args.command == 'fetch':
            # Fetch fresh FPL data (always fresh unless --cached flag)
            fpl_agent.fetch_fpl_data(
                use_cached=args.cached_only, 
                use_enrichments=args.use_enrichments,
                gameweek=args.gameweek,
                filter_unavailable_players=args.filter_unavailable_players
            )
            
        elif args.command == 'enrich':
            fpl_agent.enrich(
                gameweek=args.gameweek,
                prompt_only=args.show_prompt
            )

        elif args.command == 'build-team':
            # Build new team
            fpl_agent.build_team(
                budget=args.budget,
                gameweek=args.gameweek,
                cached_only=args.cached_only,
                rag_mode=args.rag_mode,
                prompt_only=args.show_prompt
            )
            
            if not args.show_prompt:
                print("✅ Team building complete!")
                
        elif args.command == 'gw-update':
            # Complete weekly gameweek update
            fpl_agent.gw_update(
                gameweek=args.gameweek or 1,
                cached_only=args.cached_only,
                rag_mode=args.rag_mode,
                prompt_only=args.show_prompt
            )
            
            if not args.show_prompt:
                print("✅ Weekly update complete!")
            
        elif args.command == 'show-data':
            fpl_agent.show_data()
            
        elif args.command == 'show-players':
            fpl_agent.show_players()
        
    except Exception as e:
        logger.error(f"Command failed: {e}")
        print(f"\n❌ Command failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
