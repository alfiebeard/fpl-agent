"""
Main FPL Optimizer application
"""

import logging
import sys
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import argparse
import requests # Added for _check_fpl_data

from .config import Config
from .ingestion import FPLDataFetcher, UnderstatDataFetcher, FBRefDataFetcher
from .processing import DataNormalizer
from .projection import ExpectedPointsCalculator
from .optimizer import ILPSolver
from .llm_layer import TipsSummarizer
from .output import ReportGenerator
from .models import FPLTeam, OptimizationResult


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('fpl_optimizer.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)


class FPLOptimizer:
    """Main FPL Optimizer application"""
    
    def __init__(self, config_path: Optional[str] = None):
        """Initialize the FPL Optimizer"""
        self.config = Config(config_path)
        self.fpl_fetcher = FPLDataFetcher(self.config)
        self.understat_fetcher = UnderstatDataFetcher(self.config)
        self.fbref_fetcher = FBRefDataFetcher(self.config)
        self.normalizer = DataNormalizer(self.config)
        self.xpts_calculator = ExpectedPointsCalculator(self.config)
        self.ilp_solver = ILPSolver(self.config)
        self.tips_summarizer = TipsSummarizer(self.config)
        self.report_generator = ReportGenerator(self.config)
        
    def create_initial_team(self, gameweek: Optional[int] = None) -> OptimizationResult:
        """Create an initial FPL team from scratch"""
        
        try:
            logger.info("Starting initial team creation...")
            
            # Step 1: Fetch all data
            logger.info("Step 1: Fetching data...")
            data = self._fetch_all_data()
            
            # Step 2: Process and normalize data
            logger.info("Step 2: Processing data...")
            processed_data = self._process_data(data)
            
            # Step 3: Calculate expected points
            logger.info("Step 3: Calculating expected points...")
            player_xpts = self._calculate_expected_points(processed_data, gameweek)
            
            # Step 4: Get LLM insights
            logger.info("Step 4: Getting LLM insights...")
            current_gw = gameweek or processed_data.get('current_gameweek', 1)
            llm_insights = self._get_llm_insights(current_gw)
            
            # Step 5: Create empty team and optimize from scratch
            logger.info("Step 5: Creating optimal team from scratch...")
            from .models import FPLTeam
            empty_team = FPLTeam(team_id=1, team_name="New FPL Team", manager_name="FPL Manager", players=[])  # Empty team
            optimization_result = self._create_optimal_team(
                processed_data['players'], empty_team, player_xpts, llm_insights
            )
            
            # Step 6: Generate report
            logger.info("Step 6: Generating report...")
            self._generate_report(optimization_result, processed_data, llm_insights)
            
            logger.info("Initial team creation completed successfully!")
            return optimization_result
            
        except Exception as e:
            logger.error(f"Initial team creation failed: {e}")
            raise
    
    def optimize_transfers(self, current_team: FPLTeam, gameweek: Optional[int] = None,
                          max_transfers: int = 2) -> OptimizationResult:
        """Optimize transfers for an existing team"""
        
        try:
            logger.info(f"Starting transfer optimization with max {max_transfers} transfers...")
            
            # Step 1: Fetch all data
            logger.info("Step 1: Fetching data...")
            data = self._fetch_all_data()
            
            # Step 2: Process and normalize data
            logger.info("Step 2: Processing data...")
            processed_data = self._process_data(data)
            
            # Step 3: Calculate expected points
            logger.info("Step 3: Calculating expected points...")
            player_xpts = self._calculate_expected_points(processed_data, gameweek)
            
            # Step 4: Get LLM insights
            logger.info("Step 4: Getting LLM insights...")
            current_gw = gameweek or processed_data.get('current_gameweek', 1)
            llm_insights = self._get_llm_insights(current_gw)
            
            # Step 5: Optimize with transfer constraints
            logger.info("Step 5: Optimizing transfers...")
            optimization_result = self._optimize_with_transfers(
                processed_data['players'], current_team, player_xpts, llm_insights, max_transfers
            )
            
            # Step 6: Generate report
            logger.info("Step 6: Generating report...")
            self._generate_report(optimization_result, processed_data, llm_insights)
            
            logger.info("Transfer optimization completed successfully!")
            return optimization_result
            
        except Exception as e:
            logger.error(f"Transfer optimization failed: {e}")
            raise
    
    def run_optimization(self, gameweek: Optional[int] = None, 
                        team_id: Optional[int] = None) -> OptimizationResult:
        """Run the complete optimization process"""
        
        logger.info("Starting FPL optimization process...")
        
        try:
            # Step 1: Fetch data
            logger.info("Step 1: Fetching data...")
            data = self._fetch_all_data()
            
            # Step 2: Process and normalize data
            logger.info("Step 2: Processing and normalizing data...")
            processed_data = self._process_data(data)
            
            # Step 3: Calculate expected points
            logger.info("Step 3: Calculating expected points...")
            player_xpts = self._calculate_expected_points(processed_data, gameweek)
            
            # Step 4: Get LLM insights
            logger.info("Step 4: Getting LLM insights...")
            llm_insights = self._get_llm_insights(gameweek or 1)
            
            # Step 5: Optimize team
            logger.info("Step 5: Optimizing team...")
            current_team = self._get_current_team(team_id, processed_data['players'])
            optimization_result = self._optimize_team(
                processed_data['players'], current_team, player_xpts, llm_insights
            )
            
            # Step 6: Generate report
            logger.info("Step 6: Generating report...")
            self._generate_report(optimization_result, processed_data, llm_insights)
            
            logger.info("Optimization process completed successfully!")
            return optimization_result
            
        except Exception as e:
            logger.error(f"Optimization process failed: {e}")
            raise
    
    def _fetch_all_data(self) -> Dict[str, Any]:
        """Fetch all required data from various sources"""
        
        # Fetch FPL data
        fpl_data = self.fpl_fetcher.get_all_data()
        
        # Fetch Understat data (xG/xA)
        if not self.config.use_mock_data():
            fpl_data['players'] = self.understat_fetcher.update_players_with_xg_xa(
                fpl_data['players']
            )
        
        # Fetch FBRef data (additional stats)
        if not self.config.use_mock_data():
            fpl_data['players'] = self.fbref_fetcher.update_players_with_fbref_data(
                fpl_data['players']
            )
            fpl_data['teams'] = self.fbref_fetcher.update_teams_with_fbref_data(
                fpl_data['teams']
            )
        
        return fpl_data
    
    def _process_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Process and normalize all data"""
        
        processed_data = {}
        
        # Normalize players
        processed_data['players'] = self.normalizer.normalize_players(data['players'])
        
        # Normalize teams
        processed_data['teams'] = self.normalizer.normalize_teams(data['teams'])
        
        # Normalize fixtures
        processed_data['fixtures'] = self.normalizer.normalize_fixtures(data['fixtures'])
        
        # Normalize gameweeks
        processed_data['gameweeks'] = data['gameweeks']
        
        # Add current gameweek info
        processed_data['current_gameweek'] = data.get('current_gameweek', 1)
        processed_data['next_deadline'] = data.get('next_deadline')
        
        return processed_data
    
    def _calculate_expected_points(self, processed_data: Dict[str, Any], 
                                 gameweek: Optional[int] = None) -> Dict[int, float]:
        """Calculate expected points for all players"""
        
        current_gw = gameweek or processed_data.get('current_gameweek', 1)
        
        return self.xpts_calculator.calculate_all_players_xpts(
            processed_data['players'],
            current_gw,
            processed_data['fixtures'],
            processed_data['teams']
        )
    
    def _get_llm_insights(self, gameweek: int) -> Dict[str, Any]:
        """Get LLM insights and tips"""
        
        # Get weekly tips
        weekly_tips = self.tips_summarizer.get_weekly_tips(gameweek)
        
        # Get injury news for all teams
        injury_news = {}
        for team in ['Arsenal', 'Man City', 'Liverpool', 'Chelsea', 'Man Utd']:
            injury_news[team] = self.tips_summarizer.get_injury_news(team)
        
        return {
            'weekly_tips': weekly_tips,
            'injury_news': injury_news,
            'gameweek': gameweek
        }
    
    def _get_current_team(self, team_id: Optional[int], 
                          players: List) -> 'FPLTeam':
        """Get current FPL team (mock for now)"""
        
        # For now, create a mock team
        # In production, this would fetch from FPL API
        from .models import FPLTeam, Position
        
        mock_players = []
        for i, player in enumerate(players[:15]):  # Take first 15 players
            mock_players.append(player)
        
        return FPLTeam(
            team_id=team_id or 1,
            team_name="My FPL Team",
            manager_name="FPL Manager",
            players=mock_players,
            captain_id=mock_players[0].id if mock_players else None,
            vice_captain_id=mock_players[1].id if len(mock_players) > 1 else None,
            formation=[3, 4, 3],
            total_value=100.0,
            bank=0.0
        )
    
    def _optimize_team(self, players: List, current_team: FPLTeam,
                      player_xpts: Dict[int, float], 
                      llm_insights: Dict[str, Any]) -> OptimizationResult:
        """Optimize team selection"""
        
        # Adjust xPts based on LLM insights
        adjusted_xpts = self._adjust_xpts_with_llm_insights(player_xpts, llm_insights)
        
        # Run ILP optimization
        optimization_result = self.ilp_solver.optimize_with_transfers(
            players, current_team, adjusted_xpts, max_transfers=2
        )
        
        # Add LLM insights to result
        optimization_result.llm_insights = self._format_llm_insights(llm_insights)
        
        return optimization_result
    
    def _create_optimal_team(self, players: List, empty_team: FPLTeam,
                           player_xpts: Dict[int, float], 
                           llm_insights: Dict[str, Any]) -> OptimizationResult:
        """Create optimal team from scratch (no transfer constraints)"""
        
        # Adjust xPts based on LLM insights
        adjusted_xpts = self._adjust_xpts_with_llm_insights(player_xpts, llm_insights)
        
        # Run ILP optimization for team creation (no transfer constraints)
        optimization_result = self.ilp_solver.optimize_team(
            players, empty_team, adjusted_xpts
        )
        
        # Add LLM insights to result
        optimization_result.llm_insights = self._format_llm_insights(llm_insights)
        
        return optimization_result
    
    def _optimize_with_transfers(self, players: List, current_team: FPLTeam,
                               player_xpts: Dict[int, float], 
                               llm_insights: Dict[str, Any],
                               max_transfers: int) -> OptimizationResult:
        """Optimize team with transfer constraints"""
        
        # Adjust xPts based on LLM insights
        adjusted_xpts = self._adjust_xpts_with_llm_insights(player_xpts, llm_insights)
        
        # Run ILP optimization with transfer constraints
        optimization_result = self.ilp_solver.optimize_with_transfers(
            players, current_team, adjusted_xpts, max_transfers=max_transfers
        )
        
        # Add LLM insights to result
        optimization_result.llm_insights = self._format_llm_insights(llm_insights)
        
        return optimization_result
    
    def _adjust_xpts_with_llm_insights(self, player_xpts: Dict[int, float],
                                      llm_insights: Dict[str, Any]) -> Dict[int, float]:
        """Adjust expected points based on LLM insights"""
        
        adjusted_xpts = player_xpts.copy()
        
        # Get weekly tips
        weekly_tips = llm_insights.get('weekly_tips', {})
        
        # Boost players recommended by LLM
        transfer_targets = weekly_tips.get('transfer_targets', [])
        for target in transfer_targets:
            player_name = target.get('player', '')
            priority = target.get('priority', 'medium')
            
            # Find player by name (simplified)
            for player_id, xpts in adjusted_xpts.items():
                # This is simplified - would need proper player lookup
                if priority == 'high':
                    adjusted_xpts[player_id] = xpts * 1.1  # 10% boost
                elif priority == 'medium':
                    adjusted_xpts[player_id] = xpts * 1.05  # 5% boost
        
        # Penalize players to avoid
        players_to_avoid = weekly_tips.get('players_to_avoid', [])
        for avoid in players_to_avoid:
            player_name = avoid.get('player', '')
            
            # Find player by name (simplified)
            for player_id, xpts in adjusted_xpts.items():
                # This is simplified - would need proper player lookup
                adjusted_xpts[player_id] = xpts * 0.9  # 10% penalty
        
        return adjusted_xpts
    
    def _format_llm_insights(self, llm_insights: Dict[str, Any]) -> str:
        """Format LLM insights for output"""
        
        weekly_tips = llm_insights.get('weekly_tips', {})
        
        insights = []
        
        # Add captain picks
        captain_picks = weekly_tips.get('captain_picks', [])
        if captain_picks:
            insights.append("Captain Picks:")
            for pick in captain_picks[:3]:  # Top 3
                insights.append(f"- {pick.get('player', '')} ({pick.get('team', '')}): {pick.get('reason', '')}")
        
        # Add transfer targets
        transfer_targets = weekly_tips.get('transfer_targets', [])
        if transfer_targets:
            insights.append("\nTransfer Targets:")
            for target in transfer_targets[:3]:  # Top 3
                insights.append(f"- {target.get('player', '')} ({target.get('team', '')}): {target.get('reason', '')}")
        
        # Add general tips
        general_tips = weekly_tips.get('general_tips', '')
        if general_tips:
            insights.append(f"\nGeneral Tips: {general_tips}")
        
        return "\n".join(insights)
    
    def _generate_report(self, optimization_result: OptimizationResult,
                        processed_data: Dict[str, Any],
                        llm_insights: Dict[str, Any]):
        """Generate optimization report"""
        
        report_data = {
            'optimization_result': optimization_result,
            'processed_data': processed_data,
            'llm_insights': llm_insights,
            'timestamp': datetime.now().isoformat()
        }
        
        # Generate report
        self.report_generator.generate_report(report_data)
    
    def run_scheduled_optimization(self):
        """Run optimization on schedule (30 mins before deadline)"""
        
        logger.info("Running scheduled optimization...")
        
        try:
            # Get next deadline
            next_deadline = self.fpl_fetcher.get_next_deadline()
            
            if next_deadline:
                # Calculate time until deadline
                time_until_deadline = next_deadline - datetime.now()
                
                if time_until_deadline.total_seconds() > 0:
                    logger.info(f"Next deadline: {next_deadline}")
                    logger.info(f"Time until deadline: {time_until_deadline}")
                    
                    # Run optimization
                    result = self.run_optimization()
                    
                    # TODO: Implement human approval step
                    # For now, just log the result
                    logger.info(f"Optimization completed. Expected points: {result.expected_points}")
                    
                else:
                    logger.info("Deadline has passed")
            else:
                logger.warning("Could not determine next deadline")
                
        except Exception as e:
            logger.error(f"Scheduled optimization failed: {e}")

    def _check_fpl_data(self):
        """Check FPL API data quality and availability"""
        print("🔍 Checking FPL API Data")
        print("=" * 50)
        
        try:
            # Get bootstrap data
            print("Fetching bootstrap data...")
            response = requests.get('https://fantasy.premierleague.com/api/bootstrap-static/')
            data = response.json()
            
            print(f"✅ Successfully fetched data")
            print(f"Total elements (players): {len(data.get('elements', []))}")
            print(f"Total teams: {len(data.get('teams', []))}")
            print(f"Total events (gameweeks): {len(data.get('events', []))}")
            
            # Check teams
            print(f"\n📋 Teams in the data:")
            teams = data.get('teams', [])
            for team in teams[:10]:  # Show first 10
                print(f"  {team['id']}: {team['name']} (Short: {team['short_name']})")
            
            # Check players
            print(f"\n👥 Sample Players:")
            players = data.get('elements', [])
            for i, player in enumerate(players[:5]):
                team_name = next((t['name'] for t in teams if t['id'] == player['team']), 'Unknown')
                print(f"  {i+1}. {player['first_name']} {player['second_name']} ({team_name}) - £{player['now_cost']/10:.1f}M - Form: {player.get('form', 'N/A')}")
            
            # Check current season info
            print(f"\n📅 Season Information:")
            events = data.get('events', [])
            if events:
                current_event = next((e for e in events if e.get('is_current', False)), None)
                if current_event:
                    print(f"  Current gameweek: {current_event['name']} (ID: {current_event['id']})")
                else:
                    print(f"  No current gameweek marked")
                    print(f"  First gameweek: {events[0]['name']} (ID: {events[0]['id']})")
            
            # Check data quality
            print(f"\n🔍 Data Quality Check:")
            players_with_form = [p for p in players if p.get('form') and p.get('form') != '0.0']
            print(f"  Players with non-zero form: {len(players_with_form)}/{len(players)}")
            
            if len(players_with_form) == 0:
                print(f"  ⚠️ All players have zero form - this might be pre-season data")
            else:
                print(f"  ✅ Found players with actual form data")
            
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()

    def _debug_player_data(self):
        """Debug player data and show sample players"""
        print("🔍 Debugging Player Data from FPL API")
        print("=" * 60)
        
        # Fetch raw data
        print("Fetching raw FPL data...")
        data = self._fetch_all_data()
        
        # Check what fields are available in the raw data
        if 'players' in data and data['players']:
            sample_player = data['players'][0]
            print(f"\n📋 Sample Player Raw Data Fields:")
            print("-" * 40)
            print(f"Name: {sample_player.name}")
            print(f"Team: {sample_player.team_name}")
            print(f"Position: {sample_player.position}")
            print(f"Price: {sample_player.price}")
            print(f"Form: {sample_player.form}")
            print(f"xG: {sample_player.xG}")
            print(f"xA: {sample_player.xA}")
            print(f"xMins_pct: {sample_player.xMins_pct}")
            print(f"Points per game: {sample_player.points_per_game}")
            print(f"Is injured: {sample_player.is_injured}")
            print(f"Custom data: {sample_player.custom_data}")
        
        # Check specific players we know should have data
        print(f"\n🔍 Checking Specific Players:")
        print("-" * 40)
        
        target_players = [
            "Mohamed Salah",
            "Erling Haaland", 
            "Bukayo Saka",
            "Alexander Isak"
        ]
        
        for target_name in target_players:
            found = False
            for player in data['players']:
                if target_name.lower() in player.name.lower():
                    print(f"\n{player.name}:")
                    print(f"  xG: {player.xG}")
                    print(f"  xA: {player.xA}")
                    print(f"  Form: {player.form}")
                    print(f"  xMins_pct: {player.xMins_pct}")
                    print(f"  Points per game: {player.points_per_game}")
                    print(f"  Custom data: {player.custom_data}")
                    found = True
                    break
            
            if not found:
                print(f"\n{target_name}: Not found in data")

    def _show_player_rankings(self):
        """Show player rankings by expected points"""
        from .utils.player_ranking import PlayerRanking
        
        print("🏆 FPL Player Rankings - Comprehensive Analysis")
        print("=" * 60)
        
        # Initialize ranking utility
        ranking = PlayerRanking()
        
        # Load data (this will take a moment)
        print("Loading FPL data...")
        ranking.load_data()
        
        # 1. Top 50 players overall by xPts
        print("\n" + "="*60)
        print("📊 TOP 50 PLAYERS BY xPTS")
        print("="*60)
        
        top_players = ranking.generate_player_ranking_table(
            sort_by='total_xpts',
            ascending=False,
            limit=50
        )
        
        ranking.print_summary_table(top_players)
        
        # 2. Top players by position
        print("\n" + "="*60)
        print("🎯 TOP PLAYERS BY POSITION")
        print("="*60)
        
        position_rankings = ranking.get_top_players_by_position(limit=10)
        
        for position, df in position_rankings.items():
            print(f"\n{position} - Top 10:")
            ranking.print_summary_table(df)
        
        # 3. Value players (under £6.0M)
        print("\n" + "="*60)
        print("💰 BEST VALUE PLAYERS (Under £6.0M)")
        print("="*60)
        
        value_players = ranking.get_value_players(price_max=6.0, limit=20)
        ranking.print_summary_table(value_players)

    def _show_team_structure(self):
        """Show current team structure"""
        print("🏟️ Current Team Structure")
        print("=" * 50)
        
        # This would typically load the user's current team
        # For now, show a sample team structure
        print("Sample FPL Team Structure:")
        print("-" * 30)
        print("Goalkeepers: 2 players")
        print("Defenders: 5 players") 
        print("Midfielders: 5 players")
        print("Forwards: 3 players")
        print("\nTotal: 15 players")
        print("Budget: £100.0M")
        print("Formation: 4-4-2, 3-5-2, 4-3-3, etc.")

    def _show_detailed_xpts(self):
        """Show detailed expected points calculations"""
        print("📊 Detailed Expected Points Analysis")
        print("=" * 50)
        
        # Fetch and process data
        data = self._fetch_all_data()
        processed_data = self._process_data(data)
        player_xpts = self._calculate_expected_points(processed_data)
        
        # Show top 20 players with detailed breakdown
        sorted_players = sorted(player_xpts.items(), key=lambda x: x[1], reverse=True)
        
        print("\nTop 20 Players by Expected Points:")
        print("-" * 80)
        print(f"{'Rank':<4} {'Player':<20} {'Team':<15} {'Position':<4} {'xPts':<8} {'Price':<8}")
        print("-" * 80)
        
        for i, (player_id, xpts) in enumerate(sorted_players[:20], 1):
            player = next((p for p in processed_data['players'] if p.id == player_id), None)
            if player:
                print(f"{i:<4} {player.name:<20} {player.team_name:<15} {player.position:<4} {xpts:<8.2f} £{player.price:<7.1f}M")

    def _show_xpts_table(self):
        """Show comprehensive xPts table with detailed breakdowns"""
        print("📊 Comprehensive xPts Table - All Players")
        print("=" * 120)
        
        # Fetch and process data
        print("Fetching and processing data...")
        data = self._fetch_all_data()
        processed_data = self._process_data(data)
        
        # Get current gameweek
        current_gw = processed_data.get('current_gameweek', 1)
        print(f"Current Gameweek: {current_gw}")
        
        # Calculate xPts for all players
        print("Calculating expected points...")
        player_xpts = self._calculate_expected_points(processed_data, current_gw)
        
        # Create detailed breakdown for each player
        print("Generating detailed breakdowns...")
        player_details = []
        
        for player in processed_data['players']:
            if player.id in player_xpts:
                xpts = player_xpts[player.id]
                
                # Get player's next fixture for detailed calculation
                player_fixture = None
                for fixture in processed_data['fixtures']:
                    if (fixture.home_team_name == player.team_name or 
                        fixture.away_team_name == player.team_name) and fixture.gameweek == current_gw:
                        player_fixture = fixture
                        break
                
                if player_fixture:
                    # Get teams for detailed calculation
                    home_team = next((t for t in processed_data['teams'] if t.name == player_fixture.home_team_name), None)
                    away_team = next((t for t in processed_data['teams'] if t.name == player_fixture.away_team_name), None)
                    
                    if home_team and away_team:
                        # Calculate detailed components
                        xg = self.xpts_calculator._calculate_expected_goals(player, player_fixture, home_team, away_team)
                        xa = self.xpts_calculator._calculate_expected_assists(player, player_fixture, home_team, away_team)
                        cs_prob = self.xpts_calculator._calculate_clean_sheet_probability(player, player_fixture, home_team, away_team)
                        bonus_prob = self.xpts_calculator._calculate_bonus_probability(player, xg, xa)
                        yc_prob = self.xpts_calculator._calculate_yellow_card_probability(player, player_fixture)
                        rc_prob = self.xpts_calculator._calculate_red_card_probability(player, player_fixture)
                        xmins = self.xpts_calculator._calculate_expected_minutes(player, player_fixture)
                        
                        # Calculate points from each component
                        goal_pts = self.xpts_calculator.points_config['goal'].get(player.position.value.lower(), 4)
                        assist_pts = self.xpts_calculator.points_config['assist']
                        cs_pts = self.xpts_calculator.points_config['clean_sheet'].get(player.position.value.lower(), 0)
                        bonus_pts = self.xpts_calculator.points_config['bonus']
                        yc_pts = self.xpts_calculator.points_config['yellow_card']
                        rc_pts = self.xpts_calculator.points_config['red_card']
                        
                        xg_points = xg * goal_pts * xmins
                        xa_points = xa * assist_pts * xmins
                        cs_points = cs_prob * cs_pts * xmins
                        bonus_points = bonus_prob * bonus_pts * xmins
                        yc_points = yc_prob * yc_pts * xmins
                        rc_points = rc_prob * rc_pts * xmins
                        base_points = 2.0 * xmins  # Base points for playing
                        
                        # Get opponent
                        if player.team_id == player_fixture.home_team_id:
                            opponent = player_fixture.away_team_name
                            is_home = True
                        else:
                            opponent = player_fixture.home_team_name
                            is_home = False
                        
                        player_details.append({
                            'name': player.name,
                            'team': player.team_name,
                            'position': player.position.value,
                            'price': player.price,
                            'form': player.form,
                            'opponent': opponent,
                            'is_home': is_home,
                            'xPts': xpts,
                            'xG': xg,
                            'xA': xa,
                            'CS_prob': cs_prob,
                            'Bonus_prob': bonus_prob,
                            'YC_prob': yc_prob,
                            'RC_prob': rc_prob,
                            'Minutes': xmins,
                            'xG_points': xg_points,
                            'xA_points': xa_points,
                            'CS_points': cs_points,
                            'Bonus_points': bonus_points,
                            'YC_points': yc_points,
                            'RC_points': rc_points,
                            'Base_points': base_points,
                            'fixture_difficulty': player_fixture.home_difficulty if is_home else player_fixture.away_difficulty
                        })
        
        # Sort by xPts
        player_details.sort(key=lambda x: x['xPts'], reverse=True)
        
        # Display table
        print(f"\n📋 Top 50 Players by xPts (Gameweek {current_gw})")
        print("=" * 140)
        print(f"{'Rank':<4} {'Player':<18} {'Team':<12} {'Pos':<3} {'Price':<6} {'xPts':<6} {'xG':<5} {'xA':<5} {'CS%':<5} {'Min%':<5} {'Opponent':<12} {'H/A':<3} {'Form':<5}")
        print("-" * 140)
        
        for i, player in enumerate(player_details[:50], 1):
            home_away = "H" if player['is_home'] else "A"
            print(f"{i:<4} {player['name']:<18} {player['team']:<12} {player['position']:<3} £{player['price']:<5.1f}M {player['xPts']:<6.2f} {player['xG']:<5.3f} {player['xA']:<5.3f} {player['CS_prob']:<5.1%} {player['Minutes']:<5.1%} {player['opponent']:<12} {home_away:<3} {player['form']:<5.1f}")
        
        # Show detailed breakdown for top 10
        print(f"\n🔍 Detailed Breakdown - Top 10 Players")
        print("=" * 160)
        print(f"{'Rank':<4} {'Player':<18} {'Team':<12} {'Pos':<3} {'xPts':<6} {'xG_pts':<7} {'xA_pts':<7} {'CS_pts':<7} {'Bonus_pts':<8} {'YC_pts':<7} {'RC_pts':<7} {'Base_pts':<8} {'Fixture':<8}")
        print("-" * 160)
        
        for i, player in enumerate(player_details[:10], 1):
            fixture_diff = player['fixture_difficulty']
            fixture_str = f"FDR{fixture_diff}"
            print(f"{i:<4} {player['name']:<18} {player['team']:<12} {player['position']:<3} {player['xPts']:<6.2f} {player['xG_points']:<7.2f} {player['xA_points']:<7.2f} {player['CS_points']:<7.2f} {player['Bonus_points']:<8.2f} {player['YC_points']:<7.2f} {player['RC_points']:<7.2f} {player['Base_points']:<8.2f} {fixture_str:<8}")
        
        # Position breakdowns
        positions = ['GK', 'DEF', 'MID', 'FWD']
        for pos in positions:
            pos_players = [p for p in player_details if p['position'] == pos]
            if pos_players:
                print(f"\n🎯 Top 10 {pos} Players")
                print("-" * 80)
                print(f"{'Rank':<4} {'Player':<18} {'Team':<12} {'xPts':<6} {'xG':<5} {'xA':<5} {'CS%':<5} {'Price':<6}")
                print("-" * 80)
                for i, player in enumerate(pos_players[:10], 1):
                    print(f"{i:<4} {player['name']:<18} {player['team']:<12} {player['xPts']:<6.2f} {player['xG']:<5.3f} {player['xA']:<5.3f} {player['CS_prob']:<5.1%} £{player['price']:<5.1f}M")
        
        # Value analysis (xPts per million)
        print(f"\n💰 Best Value Players (xPts per £M)")
        print("-" * 80)
        print(f"{'Rank':<4} {'Player':<18} {'Team':<12} {'Pos':<3} {'xPts':<6} {'Price':<6} {'xPts/£M':<8}")
        print("-" * 80)
        
        value_players = [(p, p['xPts'] / p['price']) for p in player_details if p['price'] > 0]
        value_players.sort(key=lambda x: x[1], reverse=True)
        
        for i, (player, value) in enumerate(value_players[:20], 1):
            print(f"{i:<4} {player['name']:<18} {player['team']:<12} {player['position']:<3} {player['xPts']:<6.2f} £{player['price']:<5.1f}M {value:<8.3f}")
        
        # Export option
        print(f"\n💾 Export Options:")
        print("  - Use 'python fpl_optimizer.py --export-rankings filename.csv' to export rankings")
        print("  - Use 'python fpl_optimizer.py --show-rankings' for more ranking options")
        
        return player_details

    def _export_rankings(self, filename: str):
        """Export player rankings to CSV file"""
        from .utils.player_ranking import PlayerRanking
        
        print(f"💾 Exporting player rankings to {filename}")
        
        ranking = PlayerRanking()
        ranking.load_data()
        
        # Export top 100 players
        top_100 = ranking.generate_player_ranking_table(
            sort_by='total_xpts',
            ascending=False,
            limit=100
        )
        
        ranking.export_to_csv(top_100, filename)
        print(f"✅ Exported top 100 players to '{filename}'")

    def _run_interactive_mode(self):
        """Run in interactive mode"""
        from .utils.player_ranking import PlayerRanking
        
        print("🔍 INTERACTIVE PLAYER RANKING")
        print("=" * 50)
        
        ranking = PlayerRanking()
        ranking.load_data()
        
        while True:
            print("\nOptions:")
            print("1. Top players by xPts")
            print("2. Filter by position")
            print("3. Filter by price range")
            print("4. Filter by team")
            print("5. Sort by different criteria")
            print("6. Export to CSV")
            print("0. Exit")
            
            choice = input("\nEnter your choice (0-6): ").strip()
            
            if choice == '0':
                break
            elif choice == '1':
                limit = int(input("How many players? (default 20): ") or 20)
                df = ranking.generate_player_ranking_table(limit=limit)
                ranking.print_summary_table(df)
            elif choice == '2':
                position = input("Position (GK/DEF/MID/FWD): ").strip().upper()
                limit = int(input("How many players? (default 20): ") or 20)
                df = ranking.generate_player_ranking_table(position_filter=position, limit=limit)
                ranking.print_summary_table(df)
            elif choice == '3':
                min_price = float(input("Min price (default 0): ") or 0)
                max_price = float(input("Max price (default 15): ") or 15)
                limit = int(input("How many players? (default 20): ") or 20)
                df = ranking.generate_player_ranking_table(price_min=min_price, price_max=max_price, limit=limit)
                ranking.print_summary_table(df)
            elif choice == '4':
                team = input("Team name (partial match): ").strip()
                limit = int(input("How many players? (default 20): ") or 20)
                df = ranking.generate_player_ranking_table(team_filter=team, limit=limit)
                ranking.print_summary_table(df)
            elif choice == '5':
                print("Sort by: total_xpts, price, real_xg_per_90, real_xa_per_90, form, total_points")
                sort_by = input("Sort by: ").strip()
                limit = int(input("How many players? (default 20): ") or 20)
                df = ranking.generate_player_ranking_table(sort_by=sort_by, limit=limit)
                ranking.print_summary_table(df)
            elif choice == '6':
                filename = input("CSV filename (default: player_rankings.csv): ").strip() or "player_rankings.csv"
                df = ranking.generate_player_ranking_table(limit=100)
                ranking.export_to_csv(df, filename)
                print(f"✅ Exported to {filename}")
            else:
                print("Invalid choice. Please try again.")

    def _export_xpts_table(self, filename: str):
        """Export detailed xPts table to CSV file"""
        import pandas as pd
        
        print(f"💾 Exporting detailed xPts table to {filename}")
        
        # Get the detailed xPts data
        player_details = self._show_xpts_table()
        
        if player_details:
            # Convert to DataFrame
            df = pd.DataFrame(player_details)
            
            # Reorder columns for better readability
            column_order = [
                'name', 'team', 'position', 'price', 'form', 'xPts',
                'xG', 'xA', 'CS_prob', 'Bonus_prob', 'YC_prob', 'RC_prob', 'Minutes',
                'xG_points', 'xA_points', 'CS_points', 'Bonus_points', 'YC_points', 'RC_points', 'Base_points',
                'opponent', 'is_home', 'fixture_difficulty'
            ]
            
            # Only include columns that exist
            existing_columns = [col for col in column_order if col in df.columns]
            df = df[existing_columns]
            
            # Export to CSV
            df.to_csv(filename, index=False)
            print(f"✅ Exported {len(df)} players to '{filename}'")
            
            # Show summary
            print(f"\n📊 Export Summary:")
            print(f"  Total players: {len(df)}")
            print(f"  Top xPts: {df['xPts'].max():.2f} ({df.loc[df['xPts'].idxmax(), 'name']})")
            print(f"  Average xPts: {df['xPts'].mean():.2f}")
            print(f"  Position breakdown:")
            for pos in ['GK', 'DEF', 'MID', 'FWD']:
                pos_df = df[df['position'] == pos]
                if len(pos_df) > 0:
                    print(f"    {pos}: {len(pos_df)} players, avg xPts: {pos_df['xPts'].mean():.2f}")
            
            return df
        else:
            print("❌ No player data available for export")
            return None


def main():
    """Main entry point"""
    
    parser = argparse.ArgumentParser(description='FPL Optimizer')
    parser.add_argument('--config', help='Path to config file')
    parser.add_argument('--gameweek', type=int, help='Gameweek to optimize for')
    parser.add_argument('--team-id', type=int, help='FPL team ID')
    parser.add_argument('--scheduled', action='store_true', help='Run scheduled optimization')
    parser.add_argument('--create-team', action='store_true', help='Create initial team from scratch')
    parser.add_argument('--optimize-transfers', action='store_true', help='Optimize transfers for existing team')
    parser.add_argument('--max-transfers', type=int, default=2, help='Maximum number of transfers (default: 2)')
    
    # New debugging and utility commands
    parser.add_argument('--check-data', action='store_true', help='Check FPL API data quality and availability')
    parser.add_argument('--debug-players', action='store_true', help='Debug player data and show sample players')
    parser.add_argument('--show-rankings', action='store_true', help='Show player rankings by expected points')
    parser.add_argument('--show-team', action='store_true', help='Show current team structure')
    parser.add_argument('--show-xpts', action='store_true', help='Show detailed expected points calculations')
    parser.add_argument('--show-xpts-table', action='store_true', help='Show comprehensive xPts table with breakdowns')
    parser.add_argument('--export-xpts-table', type=str, help='Export detailed xPts table to CSV file')
    parser.add_argument('--export-rankings', type=str, help='Export player rankings to CSV file')
    parser.add_argument('--interactive', action='store_true', help='Run in interactive mode')
    
    args = parser.parse_args()
    
    try:
        optimizer = FPLOptimizer(args.config)
        
        if args.scheduled:
            optimizer.run_scheduled_optimization()
        elif args.create_team:
            print("Creating initial team from scratch...")
            result = optimizer.create_initial_team(args.gameweek)
            print(f"✅ Initial team creation completed successfully!")
            print(f"Expected points: {result.expected_points:.2f}")
            print(f"Team value: {result.team_value:.1f}")
            print(f"Bank balance: {result.bank_balance:.1f}")
            print(f"Captain: {result.captain_id}")
            print(f"Vice Captain: {result.vice_captain_id}")
            if result.transfers:
                print(f"Transfers: {len(result.transfers)}")
                for transfer in result.transfers:
                    print(f"  {transfer.player_out} → {transfer.player_in}")
        elif args.optimize_transfers:
            print("Optimizing transfers for existing team...")
            # For now, create a mock current team
            from .models import FPLTeam
            mock_team = FPLTeam(team_id=args.team_id or 1, team_name="Mock Team", manager_name="Mock Manager", players=[])
            result = optimizer.optimize_transfers(mock_team, args.gameweek, args.max_transfers)
            print(f"✅ Transfer optimization completed successfully!")
            print(f"Expected points: {result.expected_points:.2f}")
            print(f"Transfers made: {len(result.transfers)}")
            for transfer in result.transfers:
                print(f"  {transfer.player_out} → {transfer.player_in}")
        elif args.check_data:
            optimizer._check_fpl_data()
        elif args.debug_players:
            optimizer._debug_player_data()
        elif args.show_rankings:
            optimizer._show_player_rankings()
        elif args.show_team:
            optimizer._show_team_structure()
        elif args.show_xpts:
            optimizer._show_detailed_xpts()
        elif args.show_xpts_table:
            optimizer._show_xpts_table()
        elif args.export_xpts_table:
            optimizer._export_xpts_table(args.export_xpts_table)
        elif args.export_rankings:
            optimizer._export_rankings(args.export_rankings)
        elif args.interactive:
            optimizer._run_interactive_mode()
        else:
            # Legacy mode - run full optimization
            result = optimizer.run_optimization(args.gameweek, args.team_id)
            print(f"✅ Optimization completed successfully!")
            print(f"Expected points: {result.expected_points:.2f}")
            print(f"Confidence: {result.confidence}")
            print(f"Reasoning: {result.reasoning}")
            
    except Exception as e:
        logger.error(f"Application failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
