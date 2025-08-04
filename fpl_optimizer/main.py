"""
Main FPL Optimizer application - Enhanced with dual team creation methods
"""

import logging
import sys
import os
import json
from typing import Dict, List, Optional, Any
from datetime import datetime
import argparse
from pathlib import Path

# Handle imports for both direct execution and module execution
try:
    # When run as module (python -m fpl_optimizer.main)
    from .core.config import Config
    from .ingestion import get_test_data

    from .core.models import Player, Team, Position, FPLTeam
    from .strategies import ModelStrategy, LLMStrategy
except ImportError:
    # When run directly (python fpl_optimizer/main.py)
    # Add the parent directory to the path
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from fpl_optimizer.core.config import Config
    from fpl_optimizer.ingestion import get_test_data

    from fpl_optimizer.core.models import Player, Team, Position, FPLTeam
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
            from .utils.data_transformers import transform_fpl_data_to_teams
            from .core.models import Position
            
            # Initialize FPL fetcher
            fpl_fetcher = FPLDataFetcher(self.config)
            
            # Get bootstrap data
            logger.info("Fetching FPL bootstrap data...")
            bootstrap_data = fpl_fetcher.get_bootstrap_data()
            
            # Use data transformer to get rich player data
            logger.info("Transforming data with rich player information...")
            filters = {
                'exclude_injured': False,      # Include all players for display
                'exclude_unavailable': False,  # Include all players for display
                'min_chance_of_playing': 0,    # Include all players
                'min_minutes': 0,              # Include all players
                'max_price': float('inf'),     # No price limit
                'min_form': float('-inf'),     # No form minimum
                'positions': [Position.GK, Position.DEF, Position.MID, Position.FWD]
            }
            
            teams = transform_fpl_data_to_teams(bootstrap_data, filters)
            
            # Extract all players from teams
            all_players = []
            for team_summary in teams.values():
                all_players.extend(team_summary.players)
            
            # Apply limit if specified
            if limit and limit > 0:
                players = all_players[:limit]
                logger.info(f"Limited to {limit} players out of {len(all_players)} total")
            else:
                players = all_players
                logger.info(f"Using all {len(players)} players")
            
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
                'data_source': 'FPL API (with rich data)',
                'fetched_at': datetime.now().isoformat()
            }
            
            logger.info("FPL data fetch completed successfully!")
            return {
                'players': players,
                'teams': [team_summary.team for team_summary in teams.values()],
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
            recommendations = self.llm_strategy.update_team_weekly(gameweek)
            
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
        'update-team', 'load-team', 'list-teams', 'validate-team'
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
    parser.add_argument('--latest-team', action='store_true',
                       help='Use the most recently created team file')
    
    # Save options
    parser.add_argument('--save-team', action='store_true',
                       help='Save the created team to a JSON file')
    parser.add_argument('--save-file', type=str,
                       help='Specific file path to save team (if not provided, auto-generates filename)')
    
    # Debug options
    parser.add_argument('--show-prompt', action='store_true',
                       help='Show the LLM prompt without executing (for debugging)')
    
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
            if args.show_prompt:
                # Show the prompt without executing
                prompt = optimizer.llm_strategy._create_team_creation_prompt(args.budget, args.gameweek or 1)
                print("\n" + "="*80)
                print("LLM TEAM CREATION PROMPT (DEBUG MODE)")
                print("="*80)
                print(prompt)
                print("="*80)
            else:
                # Execute normally
                result = optimizer.create_team_llm(args.budget, args.gameweek)
                display_comprehensive_team_result(result)
                
                # Save team if requested
                if args.save_team:
                    try:
                        team_data = result['team_data']
                        saved_file = save_team_to_json(team_data, args.save_file)
                        print(f"\n" + "="*80)
                        print("TEAM SAVED")
                        print("="*80)
                        print(f"Team saved to: {saved_file}")
                        print("="*80)
                    except Exception as e:
                        logger.error(f"Failed to save team: {e}")
                        print(f"\nError saving team: {e}")
            
        elif args.command == 'update-team':
            # Update team weekly using comprehensive LLM team manager
            result = optimizer.update_team_weekly_comprehensive(args.gameweek)
            display_comprehensive_team_result(result)
            
        elif args.command == 'weekly-model':
            # Weekly recommendations using model approach
            team_file = args.team_file
            if args.latest_team:
                team_file = get_latest_team_file()
                if team_file:
                    print(f"Using latest team: {os.path.basename(team_file)}")
            
            current_team = load_team_from_file(team_file) if team_file else create_sample_team()
            result = optimizer.get_weekly_recommendations_model(current_team, args.free_transfers)
            display_weekly_recommendations(result)
            
        elif args.command == 'weekly-llm':
            # Weekly recommendations using LLM approach
            team_file = args.team_file
            if args.latest_team:
                team_file = get_latest_team_file()
                if team_file:
                    print(f"Using latest team: {os.path.basename(team_file)}")
            
            current_team = load_team_from_file(team_file) if team_file else create_sample_team()
            result = optimizer.get_weekly_recommendations_llm(current_team, args.free_transfers, args.gameweek)
            display_weekly_recommendations(result)
            
        elif args.command == 'load-team':
            # Load and display a saved team
            team_file = args.team_file
            
            if args.latest_team:
                team_file = get_latest_team_file()
                if not team_file:
                    print("Error: No saved teams found")
                    sys.exit(1)
                print(f"Loading latest team: {os.path.basename(team_file)}")
            elif not args.team_file:
                print("Error: --team-file is required for load-team command (or use --latest-team)")
                sys.exit(1)
            
            try:
                saved_team_data = load_team_from_json(team_file)
                
                # Convert saved format back to the format expected by display function
                team_data = {
                    'captain': saved_team_data.get('team_info', {}).get('captain'),
                    'vice_captain': saved_team_data.get('team_info', {}).get('vice_captain'),
                    'total_cost': saved_team_data.get('team_info', {}).get('total_cost', 0.0),
                    'bank': saved_team_data.get('team_info', {}).get('bank', 0.0),
                    'expected_points': saved_team_data.get('team_info', {}).get('expected_points', 0.0),
                    'team': {
                        'starting': saved_team_data.get('squad', {}).get('starting_11', []),
                        'substitutes': saved_team_data.get('squad', {}).get('substitutes', [])
                    },
                    'raw_llm_response': saved_team_data.get('raw_llm_response', ''),
                    # Add reasoning fields
                    'captain_reason': saved_team_data.get('reasoning', {}).get('captain_reason', ''),
                    'vice_captain_reason': saved_team_data.get('reasoning', {}).get('vice_captain_reason', ''),
                    'chip_reason': saved_team_data.get('reasoning', {}).get('chip_reason', ''),
                    'transfers': saved_team_data.get('reasoning', {}).get('transfers', [])
                }
                
                display_comprehensive_team_result({'team_data': team_data})
            except Exception as e:
                logger.error(f"Failed to load team: {e}")
                sys.exit(1)
            
        elif args.command == 'list-teams':
            team_files = list_saved_teams()
            if not team_files:
                print("No saved teams found.")
            else:
                print("\n" + "="*80)
                print("SAVED TEAMS")
                print("="*80)
                for file_path in team_files:
                    print(f"- {os.path.basename(file_path)}")
                print("="*80)
        
        elif args.command == 'validate-team':
            # Validate existing team data
            try:
                from .utils.validator import FPLValidator
                from .core.team_manager import TeamManager
                
                print("\n" + "="*80)
                print("FPL TEAM VALIDATION")
                print("="*80)
                
                # Create validator and team manager
                validator = FPLValidator("team_data")
                team_manager = TeamManager("team_data")
                
                # Determine which gameweek to validate
                gameweek = args.gameweek
                if not gameweek:
                    # Try to find the latest gameweek
                    latest_gw = team_manager.get_latest_gameweek()
                    if latest_gw:
                        gameweek = latest_gw
                        print(f"Validating latest team (Gameweek {gameweek})")
                    else:
                        print("❌ No team files found in team_data directory")
                        sys.exit(1)
                else:
                    print(f"Validating team for Gameweek {gameweek}")
                
                # Check if team file exists
                team_file = Path(f"team_data/gw{gameweek:02d}.json")
                if not team_file.exists():
                    print(f"❌ Team file gw{gameweek:02d}.json not found")
                    sys.exit(1)
                
                # Load and validate team data
                print(f"\n1. Loading and validating gw{gameweek:02d}.json...")
                
                with open(team_file, 'r') as f:
                    team_data = json.load(f)
                
                print(f"✓ Loaded team data for Gameweek {team_data.get('gameweek', 'Unknown')}")
                
                # Validate team data
                validation_errors = validator.validate_team_data(team_data['team'], gameweek)
                
                if validation_errors:
                    print("❌ Team validation failed:")
                    for error in validation_errors:
                        print(f"  - {error}")
                    sys.exit(1)
                else:
                    print("✓ Team validation passed")
                
                # Display team summary
                print(f"\n2. Team Summary:")
                team = team_data['team']
                print(f"   Captain: {team.get('captain', 'Unknown')}")
                print(f"   Vice Captain: {team.get('vice_captain', 'Unknown')}")
                print(f"   Total Cost: £{team.get('total_cost', 0)}m")
                print(f"   Bank: £{team.get('bank', 0)}m")
                print(f"   Expected Points: {team.get('expected_points', 0)}")
                
                # Count players by position
                all_players = team.get('team', {}).get('starting', []) + team.get('team', {}).get('substitutes', [])
                position_counts = {'GK': 0, 'DEF': 0, 'MID': 0, 'FWD': 0}
                team_counts = {}
                
                for player in all_players:
                    position = player.get('position')
                    if position in position_counts:
                        position_counts[position] += 1
                    
                    team_name = player.get('team')
                    if team_name:
                        team_counts[team_name] = team_counts.get(team_name, 0) + 1
                
                print(f"   Squad: {position_counts['GK']} GK, {position_counts['DEF']} DEF, {position_counts['MID']} MID, {position_counts['FWD']} FWD")
                print(f"   Teams: {len(team_counts)} different teams")
                
                # Show formation
                starting = team.get('team', {}).get('starting', [])
                starting_positions = {'GK': 0, 'DEF': 0, 'MID': 0, 'FWD': 0}
                for player in starting:
                    position = player.get('position')
                    if position in starting_positions:
                        starting_positions[position] += 1
                
                formation = f"{starting_positions['DEF']}-{starting_positions['MID']}-{starting_positions['FWD']}"
                print(f"   Formation: {formation}")
                
                # Check meta.json
                print(f"\n3. Checking meta.json...")
                meta_file = Path("team_data/meta.json")
                if meta_file.exists():
                    with open(meta_file, 'r') as f:
                        meta_data = json.load(f)
                    
                    print("✓ meta.json found")
                    meta_current_gw = meta_data.get('current_gw', 'Unknown')
                    print(f"   Current GW: {meta_current_gw}")
                    print(f"   Last Team File: {meta_data.get('last_team_file', 'Unknown')}")
                    print(f"   Bank: £{meta_data.get('bank', 0)}m")
                    print(f"   Free Transfers: {meta_data.get('free_transfers', 0)}")
                    
                    # Check if meta.json is for a different gameweek
                    if meta_current_gw != 'Unknown' and meta_current_gw != gameweek:
                        print(f"\n⚠️  WARNING: meta.json is for Gameweek {meta_current_gw}, but you're validating Gameweek {gameweek}")
                        print(f"   This means you're validating a historical team, not the current team.")
                        print(f"   The meta.json reflects the current state after Gameweek {meta_current_gw}.")
                        
                        # Ask if they want to continue
                        print(f"\n   Do you want to continue validating the historical team? (y/N): ", end="")
                        try:
                            response = input().strip().lower()
                            if response not in ['y', 'yes']:
                                print("Validation cancelled.")
                                sys.exit(0)
                        except KeyboardInterrupt:
                            print("\nValidation cancelled.")
                            sys.exit(0)
                    
                    # Validate file consistency (only if meta.json matches the gameweek being validated)
                    if meta_current_gw == gameweek:
                        print(f"\n4. Validating file consistency...")
                        consistency_errors = validator.validate_files_consistency(gameweek)
                        
                        if consistency_errors:
                            print("❌ File consistency validation failed:")
                            for error in consistency_errors:
                                print(f"  - {error}")
                            sys.exit(1)
                        else:
                            print("✓ File consistency validation passed")
                    else:
                        print(f"\n4. Skipping file consistency validation (meta.json is for GW{meta_current_gw}, validating GW{gameweek})")
                        
                else:
                    print("⚠️  meta.json not found - creating it now...")
                    team_manager.initialize_meta(gameweek, team_data['team'])
                    print("✓ meta.json created successfully")
                    
                    # Now validate consistency since we just created meta.json
                    print(f"\n4. Validating file consistency...")
                    consistency_errors = validator.validate_files_consistency(gameweek)
                    
                    if consistency_errors:
                        print("❌ File consistency validation failed:")
                        for error in consistency_errors:
                            print(f"  - {error}")
                        sys.exit(1)
                    else:
                        print("✓ File consistency validation passed")
                
                print(f"\n🎉 All validations passed! Team data is ready for use.")
                print("="*80)
                
            except Exception as e:
                logger.error(f"Team validation failed: {e}")
                print(f"❌ Validation failed: {e}")
                sys.exit(1)
            

            

        
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
    print(f"{'Name':<25} {'Team':<15} {'Pos':<4} {'Price':<6} {'Chance':<6} {'Form':<6} {'Total Pts':<10} {'Pts/Game':<8} {'Selected %':<10}")
    print("-" * 110)
    print("Note: 'Chance' shows likelihood of playing this gameweek (100% = Available during off-season)")
    print("-" * 110)
    
    # Sort players: club alphabetically, then position (GK, DEF, MID, FWD), then player name alphabetically
    position_order = {'GK': 0, 'DEF': 1, 'MID': 2, 'FWD': 3}
    sorted_players = sorted(result['players'], 
                          key=lambda p: (p.team_name, position_order[p.position.value], p.name))
    
    for player in sorted_players:
        # Get chance of playing from custom_data
        chance_of_playing = player.custom_data.get('chance_of_playing')
        if chance_of_playing is None:
            chance_str = "100%"  # Available (default during off-season)
        else:
            chance_str = f"{chance_of_playing}%"
        
        print(f"{player.name:<25} {player.team_name:<15} {player.position.value:<4} £{player.price:<5.1f} {chance_str:<6} {player.form:<6.1f} {player.total_points:<10} {player.points_per_game:<8.1f} {player.selected_by_pct:<10.1f}")
    
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
        
        # Display team reasoning summary
        print(f"\n" + "="*80)
        print("TEAM SELECTION REASONING")
        print("="*80)
        
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
        print(f"\n" + "="*80)
        print("CHIP/WILDCARD USAGE")
        print("="*80)
        print(f"Chip Used: {result['wildcard_or_chip']}")
        if 'chip_reason' in result:
            print(f"Reason: {result['chip_reason']}")
        print("="*80)
    
    # Display transfers if present
    if 'transfers' in result and result['transfers']:
        print(f"\n" + "="*80)
        print("TRANSFERS")
        print("="*80)
        for transfer in result['transfers']:
            print(f"OUT: {transfer.get('out', 'Unknown')}")
            print(f"IN:  {transfer.get('in', 'Unknown')}")
            if 'reason' in transfer:
                print(f"Reason: {transfer['reason']}")
            print("-" * 80)
    
    # Display captaincy reasoning if present
    if 'captain_reason' in result or 'vice_captain_reason' in result:
        print(f"\n" + "="*80)
        print("CAPTAINCY REASONING")
        print("="*80)
        if 'captain_reason' in result:
            print(f"Captain ({result.get('captain', 'Unknown')}): {result['captain_reason']}")
        if 'vice_captain_reason' in result:
            print(f"Vice Captain ({result.get('vice_captain', 'Unknown')}): {result['vice_captain_reason']}")
        print("="*80)
    
    # Get the correct team data structure
    team_data_to_display = None
    if isinstance(result, dict) and 'team_data' in result:
        team_data_to_display = result['team_data']
    else:
        team_data_to_display = result
    
    # Display starting 11
    if 'team' in team_data_to_display and 'starting' in team_data_to_display['team']:
        print(f"\n" + "="*80)
        print("STARTING 11")
        print("="*80)
        print(f"{'Name':<25} {'Team':<15} {'Pos':<4} {'Price':<6}")
        print("-" * 80)
        
        for player in team_data_to_display['team']['starting']:
            captain_marker = " (C)" if player.get('name') == team_data_to_display.get('captain') else ""
            vice_marker = " (VC)" if player.get('name') == team_data_to_display.get('vice_captain') else ""
            markers = captain_marker + vice_marker
            print(f"{player.get('name', 'Unknown') + markers:<25} {player.get('team', 'Unknown'):<15} {player.get('position', 'Unknown'):<4} £{player.get('price', 0):<5.1f}")
            
            # Display reasoning if available
            if 'reason' in player:
                print(f"  └─ {player['reason']}")
        
        print("-" * 80)
    
    # Display substitutes
    if 'team' in team_data_to_display and 'substitutes' in team_data_to_display['team']:
        print(f"\n" + "="*80)
        print("SUBSTITUTES")
        print("="*80)
        print(f"{'Name':<25} {'Team':<15} {'Pos':<4} {'Price':<6} {'Sub Order':<10}")
        print("-" * 80)
        
        for player in team_data_to_display['team']['substitutes']:
            sub_order = player.get('sub_order', 'GK')
            sub_order_str = str(sub_order) if sub_order is not None else 'GK'
            print(f"{player.get('name', 'Unknown'):<25} {player.get('team', 'Unknown'):<15} {player.get('position', 'Unknown'):<4} £{player.get('price', 0):<5.1f} {sub_order_str:<10}")
            
            # Display reasoning if available
            if 'reason' in player:
                print(f"  └─ {player['reason']}")
        
        print("-" * 80)
    
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


def save_team_to_json(team_data: Dict[str, Any], file_path: Optional[str] = None) -> str:
    """
    Save team data to a JSON file aligned with FPL API structure.
    
    Args:
        team_data: Team data from LLM strategy
        file_path: Optional file path, if not provided will generate one
        
    Returns:
        Path to the saved file
    """
    if file_path is None:
        # Generate filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_path = f"fpl_team_{timestamp}.json"
    
    # Ensure output directory exists
    output_dir = "output/teams"
    os.makedirs(output_dir, exist_ok=True)
    
    # If only filename provided, prepend output directory
    if not os.path.dirname(file_path):
        file_path = os.path.join(output_dir, file_path)
    
    # Create FPL API-aligned structure
    fpl_team_data = {
        "team_info": {
            "captain": team_data.get('captain'),
            "vice_captain": team_data.get('vice_captain'),
            "total_cost": team_data.get('total_cost', 0.0),
            "bank": team_data.get('bank', 0.0),
            "expected_points": team_data.get('expected_points', 0.0),
            "created_at": datetime.now().isoformat(),
            "gameweek": 1  # Default to GW1 for new teams
        },
        "squad": {
            "starting_11": [],
            "substitutes": []
        },
        "formation": [3, 4, 3],  # Default formation
        "chips": {
            "wildcard_used": False,
            "free_hit_used": False,
            "triple_captain_used": False,
            "bench_boost_used": False
        },
        "transfers": {
            "free_transfers": 1,
            "transfer_hits": 0,
            "transfers_made": []
        },
        "reasoning": {
            "captain_reason": team_data.get('captain_reason', ''),
            "vice_captain_reason": team_data.get('vice_captain_reason', ''),
            "chip_reason": team_data.get('chip_reason', ''),
            "transfers": []
        }
    }
    
    # Process starting 11
    if 'team' in team_data and 'starting' in team_data['team']:
        for player in team_data['team']['starting']:
            fpl_player = {
                "name": player.get('name'),
                "position": player.get('position'),
                "team": player.get('team'),
                "price": player.get('price', 0.0),
                "is_captain": player.get('name') == team_data.get('captain'),
                "is_vice_captain": player.get('name') == team_data.get('vice_captain'),
                "is_starting": True,
                "reason": player.get('reason', '')
            }
            fpl_team_data["squad"]["starting_11"].append(fpl_player)
    
    # Process substitutes
    if 'team' in team_data and 'substitutes' in team_data['team']:
        for player in team_data['team']['substitutes']:
            fpl_player = {
                "name": player.get('name'),
                "position": player.get('position'),
                "team": player.get('team'),
                "price": player.get('price', 0.0),
                "sub_order": player.get('sub_order'),
                "is_starting": False,
                "reason": player.get('reason', '')
            }
            fpl_team_data["squad"]["substitutes"].append(fpl_player)
    
    # Process transfers with reasoning
    if 'transfers' in team_data and team_data['transfers']:
        for transfer in team_data['transfers']:
            transfer_data = {
                "out": transfer.get('out'),
                "in": transfer.get('in'),
                "reason": transfer.get('reason', '')
            }
            fpl_team_data["reasoning"]["transfers"].append(transfer_data)
            fpl_team_data["transfers"]["transfers_made"].append(transfer_data)
    
    # Add raw LLM response for reference
    if 'raw_llm_response' in team_data:
        fpl_team_data["raw_llm_response"] = team_data['raw_llm_response']
    
    # Save to file
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(fpl_team_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Team saved to: {file_path}")
        return file_path
        
    except Exception as e:
        logger.error(f"Failed to save team to {file_path}: {e}")
        raise

def load_team_from_json(file_path: str) -> Dict[str, Any]:
    """
    Load team data from a JSON file.
    
    Args:
        file_path: Path to the JSON file
        
    Returns:
        Team data dictionary
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            team_data = json.load(f)
        
        logger.info(f"Team loaded from: {file_path}")
        return team_data
        
    except Exception as e:
        logger.error(f"Failed to load team from {file_path}: {e}")
        raise


def load_team_from_file(file_path: str) -> FPLTeam:
    """Load team from JSON file"""
    try:
        # Load the JSON data
        team_data = load_team_from_json(file_path)
        
        # Convert to FPLTeam object
        from .models import Player, Position
        
        players = []
        
        # Process starting 11
        for player_data in team_data.get('squad', {}).get('starting_11', []):
            player = Player(
                id=len(players) + 1,  # Generate temporary ID
                name=player_data['name'],
                team_id=1,  # Will need to map team names to IDs
                position=Position[player_data['position']],
                price=player_data['price'],
                team_name=player_data['team']
            )
            players.append(player)
        
        # Process substitutes
        for player_data in team_data.get('squad', {}).get('substitutes', []):
            player = Player(
                id=len(players) + 1,  # Generate temporary ID
                name=player_data['name'],
                team_id=1,  # Will need to map team names to IDs
                position=Position[player_data['position']],
                price=player_data['price'],
                team_name=player_data['team']
            )
            players.append(player)
        
        # Get captain and vice captain IDs
        captain_id = None
        vice_captain_id = None
        for player in players:
            if player.name == team_data.get('team_info', {}).get('captain'):
                captain_id = player.id
            elif player.name == team_data.get('team_info', {}).get('vice_captain'):
                vice_captain_id = player.id
        
        return FPLTeam(
            team_id=1,  # Default team ID
            team_name="Loaded Team",
            manager_name="Manager",
            players=players,
            captain_id=captain_id,
            vice_captain_id=vice_captain_id,
            total_value=team_data.get('team_info', {}).get('total_cost', 100.0),
            bank=team_data.get('team_info', {}).get('bank', 0.0),
            free_transfers=team_data.get('transfers', {}).get('free_transfers', 1)
        )
        
    except Exception as e:
        logger.error(f"Failed to load team from {file_path}: {e}")
        logger.warning("Using sample team instead.")
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

def list_saved_teams() -> List[str]:
    """
    List all saved team files in the output directory.
    
    Returns:
        List of team file paths
    """
    output_dir = "output/teams"
    if not os.path.exists(output_dir):
        return []
    
    team_files = []
    for file in os.listdir(output_dir):
        if file.endswith('.json'):
            team_files.append(os.path.join(output_dir, file))
    
    # Sort by creation time (newest first)
    team_files.sort(key=lambda x: os.path.getctime(x), reverse=True)
    return team_files

def get_latest_team_file() -> Optional[str]:
    """
    Get the most recently created team file.
    
    Returns:
        Path to the latest team file, or None if no files exist
    """
    team_files = list_saved_teams()
    return team_files[0] if team_files else None


if __name__ == "__main__":
    main()
