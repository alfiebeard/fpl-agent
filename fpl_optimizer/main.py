"""
Main FPL Optimizer application
"""

import logging
import sys
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import argparse

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
