#!/usr/bin/env python3
"""
Test data sources and merging functionality
"""

import unittest
from fpl_optimizer.data.xg_xa_fetcher import XGXAFetcher
from fpl_optimizer.data.historical_data import HistoricalDataManager

class TestDataSources(unittest.TestCase):
    """Test data source functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.fetcher = XGXAFetcher()
        self.historical_manager = HistoricalDataManager()
    
    def test_data_source_hierarchy(self):
        """Test how data sources are prioritized and used"""
        
        print("🔍 Testing Data Source Hierarchy")
        print("=" * 50)
        
        # Test players that exist in multiple sources
        test_players = [
            ("Mohamed Salah", "Liverpool"),
            ("Erling Haaland", "Man City"),
            ("Bukayo Saka", "Arsenal"),
        ]
        
        for player_name, team in test_players:
            print(f"\n📊 {player_name} ({team}):")
            
            # Test single source (default behavior - uses first available)
            single_data = self.fetcher.get_player_xg_xa(player_name, team)
            if single_data:
                print(f"  Single source ({single_data.source}):")
                print(f"    xG per 90: {single_data.xG_per_90:.4f}")
                print(f"    xA per 90: {single_data.xA_per_90:.4f}")
                print(f"    xCS per 90: {single_data.xCS_per_90:.4f}")
                print(f"    xMins %: {single_data.xMins_pct:.4f}")
            
            # Test merged sources
            merged_data = self.fetcher.get_player_xg_xa(player_name, team, merge_sources=True)
            if merged_data:
                print(f"  Merged sources ({merged_data.source}):")
                print(f"    xG per 90: {merged_data.xG_per_90:.4f}")
                print(f"    xA per 90: {merged_data.xA_per_90:.4f}")
                print(f"    xCS per 90: {merged_data.xCS_per_90:.4f}")
                print(f"    xMins %: {merged_data.xMins_pct:.4f}")
    
    def test_source_comparison(self):
        """Compare data from different sources"""
        
        print(f"\n📊 Comparing Data Sources")
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
                        print(f"  {source.upper():<10}: xG={data.xG_per_90:<6.4f} xA={data.xA_per_90:<6.4f} xCS={data.xCS_per_90:<6.4f} xMins={data.xMins_pct:<6.4f}")
                    else:
                        print(f"  {source.upper():<10}: No data")
                except Exception as e:
                    print(f"  {source.upper():<10}: Error - {e}")
    
    def test_merging_algorithm(self):
        """Test the merging algorithm with different source combinations"""
        
        print(f"\n🔄 Testing Merging Algorithm")
        print("=" * 50)
        
        # Test players that exist in multiple sources
        test_players = ["Mohamed Salah", "Erling Haaland", "Bukayo Saka"]
        
        for player_name in test_players:
            print(f"\n🔍 {player_name}:")
            
            # Get data from individual sources
            fbref_data = self.fetcher._fetch_from_fbref(player_name, "Unknown")
            understat_data = self.fetcher._fetch_from_understat(player_name, "Unknown")
            
            if fbref_data and understat_data:
                print(f"  FBRef:     xG={fbref_data.xG_per_90:.4f} xA={fbref_data.xA_per_90:.4f} xCS={fbref_data.xCS_per_90:.4f} xMins={fbref_data.xMins_pct:.4f}")
                print(f"  Understat: xG={understat_data.xG_per_90:.4f} xA={understat_data.xA_per_90:.4f} xCS={understat_data.xCS_per_90:.4f} xMins={understat_data.xMins_pct:.4f}")
                
                # Calculate expected merged values (weighted average)
                expected_xg = (fbref_data.xG_per_90 * 0.6 + understat_data.xG_per_90 * 0.4)
                expected_xa = (fbref_data.xA_per_90 * 0.6 + understat_data.xA_per_90 * 0.4)
                expected_xcs = (fbref_data.xCS_per_90 * 0.6 + understat_data.xCS_per_90 * 0.4)
                expected_xmins = (fbref_data.xMins_pct * 0.6 + understat_data.xMins_pct * 0.4)
                
                print(f"  Expected:  xG={expected_xg:.4f} xA={expected_xa:.4f} xCS={expected_xcs:.4f} xMins={expected_xmins:.4f}")
                
                # Get actual merged data
                merged_data = self.fetcher.get_player_xg_xa(player_name, "Unknown", merge_sources=True)
                if merged_data:
                    print(f"  Actual:    xG={merged_data.xG_per_90:.4f} xA={merged_data.xA_per_90:.4f} xCS={merged_data.xCS_per_90:.4f} xMins={merged_data.xMins_pct:.4f}")
                    
                    # Check if merged data is reasonable
                    xg_diff = abs(merged_data.xG_per_90 - expected_xg)
                    xa_diff = abs(merged_data.xA_per_90 - expected_xa)
                    
                    if xg_diff < 0.1 and xa_diff < 0.1:
                        print(f"  ✅ Merging algorithm working correctly")
                    else:
                        print(f"  ⚠️ Merging algorithm may need adjustment")

def run_data_source_tests():
    """Run the data source tests"""
    print("🧪 Running Data Source Tests")
    print("=" * 60)
    
    test_suite = unittest.TestLoader().loadTestsFromTestCase(TestDataSources)
    runner = unittest.TextTestRunner(verbosity=2)
    runner.run(test_suite)

if __name__ == "__main__":
    run_data_source_tests() 