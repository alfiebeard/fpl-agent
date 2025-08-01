"""
Main FPL Optimizer application - Enhanced with dual team creation methods
"""

import logging
import sys
import os
from typing import Dict, List, Optional, Any
from datetime import datetime
import argparse

# Handle imports for both direct execution and module execution
try:
    # When run as module (python -m fpl_optimizer.main)
    from .config import Config
    from .ingestion import get_test_data

    from .models import Player, Team, Position, FPLTeam
    from .strategies import ModelStrategy, LLMStrategy
except ImportError:
    # When run directly (python fpl_optimizer/main.py)
    # Add the parent directory to the path
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from fpl_optimizer.config import Config
    from fpl_optimizer.ingestion import get_test_data

    from fpl_optimizer.models import Player, Team, Position, FPLTeam
    from fpl_optimizer.strategies import ModelStrategy, LLMStrategy


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
    
    def fetch_fpl_players(self, limit: Optional[int] = None) -> Dict[str, Any]:
        """Fetch real FPL player data from the API"""
        
        try:
            logger.info("Starting FPL API data fetch...")
            
            # Import here to avoid circular imports
            from .ingestion.fetch_fpl import FPLDataFetcher
            
            # Initialize FPL fetcher
            fpl_fetcher = FPLDataFetcher(self.config)
            
            # Get bootstrap data
            logger.info("Fetching FPL bootstrap data...")
            bootstrap_data = fpl_fetcher.get_bootstrap_data()
            
            # Parse players
            logger.info("Parsing player data...")
            all_players = fpl_fetcher.parse_players(bootstrap_data)
            
            # Parse teams
            logger.info("Parsing team data...")
            teams = fpl_fetcher.parse_teams(bootstrap_data)
            
            # Apply limit if specified
            if limit and limit > 0:
                players = all_players[:limit]
                logger.info(f"Limited to {limit} players out of {len(all_players)} total")
            else:
                players = all_players
                logger.info(f"Using all {len(players)} players")
            
            # No xPts calculation needed for simple data fetch
            
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
                'data_source': 'FPL API',
                'fetched_at': datetime.now().isoformat()
            }
            
            logger.info("FPL data fetch completed successfully!")
            return {
                'players': players,
                'teams': teams,
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
    
    def create_team_llm(self, budget: float = 100.0, gameweek: Optional[int] = None) -> Dict[str, Any]:
        """Create team using comprehensive LLM-based approach with FPL integration"""
        
        try:
            logger.info("Creating team using comprehensive LLM-based approach...")
            
            # Use LLM strategy
            result = self.llm_strategy.create_team(budget, gameweek or 1)
            
            logger.info("Comprehensive LLM-based team creation completed successfully!")
            return {
                'method': 'Comprehensive LLM-based Team Creation',
                'team_data': result
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
            recommendations = self.team_manager.update_team_weekly(gameweek)
            
            # Add method identifier
            recommendations['method'] = 'LLM-based Expert Insights'
            
            logger.info("LLM-based weekly recommendations completed successfully!")
            return recommendations
            
        except Exception as e:
            logger.error(f"LLM-based weekly recommendations failed: {e}")
            raise
    

    

    

    
    def update_team_weekly_comprehensive(self, gameweek: Optional[int] = None) -> Dict[str, Any]:
        """Update the current FPL team weekly using the comprehensive LLM team manager"""
        try:
            logger.info(f"Updating team weekly for gameweek {gameweek or 'current'}...")
            result = self.llm_strategy.update_team_weekly(gameweek)
            logger.info("Weekly team update completed successfully!")
            return result
        except Exception as e:
            logger.error(f"Weekly team update failed: {e}")
            raise
    
    # Helper methods
    
    def _get_player_name_by_id(self, team: FPLTeam, player_id: Optional[int]) -> str:
        """Get player name by ID from team"""
        if not player_id:
            return "Unknown"
        
        for player in team.players:
            if player.id == player_id:
                return player.name
        
        return "Unknown"
    



def main():
    """Main entry point with enhanced command options"""
    parser = argparse.ArgumentParser(description='FPL Optimizer with Dual Approaches')
    
    # Main command
    parser.add_argument('command', choices=[
        'fetch', 'fetch-fpl-players', 'create-model', 'create-team-llm', 'weekly-model', 'weekly-llm', 
        'update-team'
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
    
    args = parser.parse_args()
    
    try:
        optimizer = FPLOptimizer(args.config)
        
        if args.command == 'fetch':
            # Just fetch and display data
            result = optimizer.fetch_data(args.sample_size)
            display_player_data(result)
            
        elif args.command == 'fetch-fpl-players':
            # Fetch real FPL data from API
            result = optimizer.fetch_fpl_players(args.sample_size)
            display_player_data(result)
            
        elif args.command == 'create-model':
            # Create team using model approach
            result = optimizer.create_team_model(args.budget, args.sample_size)
            display_team_creation_result(result)
            
        elif args.command == 'create-team-llm':
            # Create team using comprehensive LLM approach
            result = optimizer.create_team_llm(args.budget, args.gameweek)
            display_comprehensive_team_result(result)
            
        elif args.command == 'update-team':
            # Update team weekly using comprehensive LLM team manager
            result = optimizer.update_team_weekly_comprehensive(args.gameweek)
            display_comprehensive_team_result(result)
            
        elif args.command == 'weekly-model':
            # Weekly recommendations using model approach
            current_team = load_team_from_file(args.team_file) if args.team_file else create_sample_team()
            result = optimizer.get_weekly_recommendations_model(current_team, args.free_transfers)
            display_weekly_recommendations(result)
            
        elif args.command == 'weekly-llm':
            # Weekly recommendations using LLM approach
            current_team = load_team_from_file(args.team_file) if args.team_file else create_sample_team()
            result = optimizer.get_weekly_recommendations_llm(current_team, args.free_transfers, args.gameweek)
            display_weekly_recommendations(result)
            

            

        
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
    print(f"{'Name':<25} {'Team':<15} {'Pos':<4} {'Price':<6} {'Form':<6} {'Total Pts':<10} {'Pts/Game':<8} {'Selected %':<10}")
    print("-" * 100)
    
    # Sort players: club alphabetically, then position (GK, DEF, MID, FWD), then player name alphabetically
    position_order = {'GK': 0, 'DEF': 1, 'MID': 2, 'FWD': 3}
    sorted_players = sorted(result['players'], 
                          key=lambda p: (p.team_name, position_order[p.position.value], p.name))
    
    for player in sorted_players:
        print(f"{player.name:<25} {player.team_name:<15} {player.position.value:<4} £{player.price:<5.1f} {player.form:<6.1f} {player.total_points:<10} {player.points_per_game:<8.1f} {player.selected_by_pct:<10.1f}")
    
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
        print(f"Chip/Wildcard Used: {result['wildcard_or_chip']}")
    
    # Display transfers if present
    if 'transfers' in result and result['transfers']:
        print(f"\n" + "="*60)
        print("TRANSFERS")
        print("="*60)
        for transfer in result['transfers']:
            print(f"OUT: {transfer.get('out', 'Unknown')}")
            print(f"IN:  {transfer.get('in', 'Unknown')}")
            if 'reason' in transfer:
                print(f"Reason: {transfer['reason']}")
            print("-" * 40)
    
    # Display starting 11
    if 'team' in result and 'starting' in result['team']:
        print(f"\n" + "="*80)
        print("STARTING 11")
        print("="*80)
        print(f"{'Name':<25} {'Team':<15} {'Pos':<4} {'Price':<6}")
        print("-" * 80)
        
        for player in result['team']['starting']:
            print(f"{player.get('name', 'Unknown'):<25} {player.get('team', 'Unknown'):<15} {player.get('position', 'Unknown'):<4} £{player.get('price', 0):<5.1f}")
    
    # Display substitutes
    if 'team' in result and 'substitutes' in result['team']:
        print(f"\n" + "="*80)
        print("SUBSTITUTES")
        print("="*80)
        print(f"{'Name':<25} {'Team':<15} {'Pos':<4} {'Price':<6} {'Sub Order':<10}")
        print("-" * 80)
        
        for player in result['team']['substitutes']:
            sub_order = player.get('sub_order', 'GK')
            print(f"{player.get('name', 'Unknown'):<25} {player.get('team', 'Unknown'):<15} {player.get('position', 'Unknown'):<4} £{player.get('price', 0):<5.1f} {sub_order:<10}")
    
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
    print(f"WEEKLY FPL RECOMMENDATIONS - {result['method']}")
    print("="*80)
    
    # Display transfers
    transfers = result['transfers']['recommended_transfers']
    if transfers:
        print(f"\n" + "="*80)
        print("RECOMMENDED TRANSFERS")
        print("="*80)
        for i, transfer in enumerate(transfers, 1):
            if hasattr(transfer, 'player_out') and hasattr(transfer, 'player_in'):
                print(f"{i}. {transfer.player_out.name} → {transfer.player_in.name}")
                if hasattr(transfer, 'reason'):
                    print(f"   Reason: {transfer.reason}")
        print(f"\nTransfer Confidence: {result['transfers']['confidence']:.2f}")
    else:
        print("\nNo transfers recommended this week.")
    
    # Display captaincy
    print(f"\n" + "="*80)
    print("CAPTAINCY RECOMMENDATIONS")
    print("="*80)
    print(f"Captain: {result['captaincy']['captain_name']}")
    print(f"Vice Captain: {result['captaincy']['vice_captain_name']}")
    
    # Display wildcard analysis
    wildcard = result['wildcard']
    print(f"\n" + "="*80)
    print("WILDCARD ANALYSIS")
    print("="*80)
    print(f"Use Wildcard: {'YES' if wildcard['should_use_wildcard'] else 'NO'}")
    print(f"Confidence: {wildcard['confidence']:.2f}")
    print(f"Reasoning: {wildcard['reasoning']}")
    
    # Display insights summary if available
    if 'insights_summary' in result:
        insights = result['insights_summary']
        print(f"\n" + "="*80)
        print("EXPERT INSIGHTS SUMMARY")
        print("="*80)
        print(f"Total Insights: {insights['total_insights']}")
        print(f"Sources: {', '.join(insights['sources'])}")
        if insights['key_topics']:
            print(f"Key Topics: {', '.join(insights['key_topics'])}")
    
    print(f"\nOverall Confidence: {result['overall_confidence']:.2f}")
    print(f"Generated at: {result['generated_at']}")





def load_team_from_file(file_path: str) -> FPLTeam:
    """Load team from JSON file (placeholder implementation)"""
    # This would load a real team from a JSON file
    # For now, return a sample team
    logger.warning(f"Team file loading not implemented. Using sample team instead.")
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


if __name__ == "__main__":
    main()
