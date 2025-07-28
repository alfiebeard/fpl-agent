#!/usr/bin/env python3
"""
Test real API integration for xG/xA data
"""

import unittest
from fpl_optimizer.data.xg_xa_fetcher import XGXAFetcher
from fpl_optimizer.data.historical_data import HistoricalDataManager
from fpl_optimizer.projection.historical_xpts import HistoricalExpectedPointsCalculator
from fpl_optimizer.main import FPLOptimizer

class TestRealAPIs(unittest.TestCase):
    """Test real API integration"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.fetcher = XGXAFetcher()
        self.historical_manager = HistoricalDataManager()
        self.optimizer = FPLOptimizer()
    
    def test_xg_xa_fetcher(self):
        """Test the xG/xA fetcher with real data"""
        
        print("🔍 Testing xG/xA Fetcher with Real Data")
        print("=" * 50)
        
        # Test known players
        test_players = [
            ("Mohamed Salah", "Liverpool"),
            ("Erling Haaland", "Man City"),
            ("Bukayo Saka", "Arsenal"),
            ("Kevin De Bruyne", "Man City"),
            ("Alexander Isak", "Newcastle"),
            ("Unknown Player", "Unknown Team")
        ]
        
        for player_name, team in test_players:
            print(f"\n📊 {player_name} ({team}):")
            
            data = self.fetcher.get_player_xg_xa(player_name, team)
            if data:
                print(f"  Source: {data.source}")
                print(f"  Position: {data.position}")
                print(f"  xG per 90: {data.xG_per_90:.4f}")
                print(f"  xA per 90: {data.xA_per_90:.4f}")
                print(f"  Minutes played: {data.minutes_played}")
                print(f"  Games played: {data.games_played}")
                print(f"  Season: {data.season}")
            else:
                print(f"  No data found")
        
        # Test team data
        print(f"\n🏆 Team xG/xGA Data:")
        print("-" * 30)
        
        test_teams = ["Man City", "Arsenal", "Liverpool", "Unknown Team"]
        
        for team in test_teams:
            team_data = self.fetcher.get_team_xg_xga(team)
            if team_data:
                print(f"{team}: xG={team_data['xG_per_game']:.2f}, xGA={team_data['xGA_per_game']:.2f}")
            else:
                print(f"{team}: No data found")
    
    def test_historical_data_with_real_apis(self):
        """Test historical data manager with real API integration"""
        
        print(f"\n📈 Testing Historical Data with Real APIs")
        print("=" * 60)
        
        # Test player historical stats
        test_players = ["Mohamed Salah", "Erling Haaland", "Bukayo Saka"]
        
        for player_name in test_players:
            print(f"\n🔍 Historical Data for {player_name}:")
            stats = self.historical_manager.get_player_historical_stats(player_name)
            if stats:
                print(f"  xG per 90: {stats['xg_per_90']:.4f}")
                print(f"  xA per 90: {stats['xa_per_90']:.4f}")
                print(f"  Minutes %: {stats['minutes_pct']:.4f}")
                print(f"  Yellow cards per 90: {stats['yellow_cards_per_90']:.4f}")
                print(f"  Red cards per 90: {stats['red_cards_per_90']:.4f}")
                print(f"  Bonus per 90: {stats['bonus_per_90']:.4f}")
                print(f"  Clean sheet rate: {stats['clean_sheet_rate']:.4f}")
                print(f"  Total games: {stats['total_games']}")
            else:
                print(f"  No historical data found")
        
        # Test team historical stats
        print(f"\n🏆 Historical Team Data:")
        print("-" * 30)
        
        test_teams = ["Man City", "Arsenal", "Liverpool"]
        
        for team_name in test_teams:
            stats = self.historical_manager.get_team_historical_stats(team_name)
            if stats:
                print(f"{team_name}:")
                print(f"  xG per game: {stats['xg_per_game']:.4f}")
                print(f"  xGA per game: {stats['xga_per_game']:.4f}")
                print(f"  Clean sheet rate: {stats['clean_sheet_rate']:.4f}")
                print(f"  Total games: {stats['total_games']}")
            else:
                print(f"{team_name}: No data found")
    
    def test_historical_xpts_with_real_data(self):
        """Test historical xPts calculation with real data"""
        
        print(f"\n📊 Testing Historical xPts with Real Data")
        print("=" * 60)
        
        calculator = HistoricalExpectedPointsCalculator(self.optimizer.config)
        
        # Test with real players
        test_players = ["Mohamed Salah", "Erling Haaland", "Bukayo Saka"]
        
        for player_name in test_players:
            print(f"\n🔍 Historical xPts for {player_name}:")
            
            # Get historical xPts
            historical_xpts = calculator.get_player_historical_xpts(player_name)
            if historical_xpts:
                print(f"  Average xPts per game: {historical_xpts['avg_xpts_per_game']:.3f}")
                print(f"  Total games: {historical_xpts['total_games']}")
                print(f"  Consistency score: {historical_xpts['consistency_score']:.3f}")
                print(f"  Form trend: {historical_xpts['form_trend']}")
            else:
                print(f"  No historical xPts data found")
    
    def test_data_source_comparison(self):
        """Compare data from different sources"""
        
        print(f"\n🔄 Comparing Data Sources")
        print("=" * 50)
        
        # Test a few players across different sources
        test_players = ["Mohamed Salah", "Erling Haaland", "Bukayo Saka"]
        
        for player_name in test_players:
            print(f"\n🔍 {player_name}:")
            
            # Try different sources
            sources = ['fbref', 'understat', 'estimated']
            
            for source in sources:
                try:
                    if source == 'fbref':
                        data = self.fetcher._fetch_from_fbref(player_name, "Unknown")
                    elif source == 'understat':
                        data = self.fetcher._fetch_from_understat(player_name, "Unknown")
                    else:
                        data = self.fetcher._get_estimated_xg_xa(player_name, "Unknown")
                    
                    if data:
                        print(f"  {source.upper():<10}: xG={data.xG_per_90:<6.4f} xA={data.xA_per_90:<6.4f}")
                    else:
                        print(f"  {source.upper():<10}: No data")
                except Exception as e:
                    print(f"  {source.upper():<10}: Error - {e}")

def run_real_api_tests():
    """Run the real API tests"""
    print("🧪 Running Real API Tests")
    print("=" * 60)
    
    test_suite = unittest.TestLoader().loadTestsFromTestCase(TestRealAPIs)
    runner = unittest.TextTestRunner(verbosity=2)
    runner.run(test_suite)

if __name__ == "__main__":
    run_real_api_tests() 