#!/usr/bin/env python3
"""
Test data sources and merging functionality
"""

from fpl_optimizer.data.xg_xa_fetcher import XGXAFetcher
from fpl_optimizer.data.historical_data import HistoricalDataManager

def test_data_source_hierarchy():
    """Test how data sources are prioritized and used"""
    
    print("🔍 Testing Data Source Hierarchy")
    print("=" * 50)
    
    fetcher = XGXAFetcher()
    
    # Test players that exist in multiple sources
    test_players = [
        ("Mohamed Salah", "Liverpool"),
        ("Erling Haaland", "Man City"),
        ("Bukayo Saka", "Arsenal"),
    ]
    
    for player_name, team in test_players:
        print(f"\n📊 {player_name} ({team}):")
        
        # Test single source (default behavior - uses first available)
        single_data = fetcher.get_player_xg_xa(player_name, team)
        if single_data:
            print(f"  Single source ({single_data.source}):")
            print(f"    xG per 90: {single_data.xG_per_90:.4f}")
            print(f"    xA per 90: {single_data.xA_per_90:.4f}")
            print(f"    xCS per 90: {single_data.xCS_per_90:.4f}")
            print(f"    xMins %: {single_data.xMins_pct:.4f}")
        
        # Test merged sources
        merged_data = fetcher.get_player_xg_xa(player_name, team, merge_sources=True)
        if merged_data:
            print(f"  Merged sources ({merged_data.source}):")
            print(f"    xG per 90: {merged_data.xG_per_90:.4f}")
            print(f"    xA per 90: {merged_data.xA_per_90:.4f}")
            print(f"    xCS per 90: {merged_data.xCS_per_90:.4f}")
            print(f"    xMins %: {merged_data.xMins_pct:.4f}")

def test_source_comparison():
    """Compare data from different sources"""
    
    print(f"\n📊 Comparing Data Sources")
    print("=" * 50)
    
    fetcher = XGXAFetcher()
    
    # Test a few players across different sources
    test_players = ["Mohamed Salah", "Erling Haaland", "Bukayo Saka"]
    
    for player_name in test_players:
        print(f"\n🔍 {player_name}:")
        
        # Try different sources
        sources = ['fbref', 'understat', 'estimated']
        
        for source in sources:
            try:
                if source == 'fbref':
                    data = fetcher._fetch_from_fbref(player_name, "Unknown")
                elif source == 'understat':
                    data = fetcher._fetch_from_understat(player_name, "Unknown")
                else:
                    data = fetcher._get_estimated_xg_xa(player_name, "Unknown")
                
                if data:
                    print(f"  {source.upper():<10}: xG={data.xG_per_90:<6.4f} xA={data.xA_per_90:<6.4f} xCS={data.xCS_per_90:<6.4f} xMins={data.xMins_pct:<6.4f}")
                else:
                    print(f"  {source.upper():<10}: No data")
            except Exception as e:
                print(f"  {source.upper():<10}: Error - {e}")

def test_merging_algorithm():
    """Test the merging algorithm with different source combinations"""
    
    print(f"\n🔄 Testing Merging Algorithm")
    print("=" * 50)
    
    fetcher = XGXAFetcher()
    
    # Test players that exist in multiple sources
    test_players = ["Mohamed Salah", "Erling Haaland", "Bukayo Saka"]
    
    for player_name in test_players:
        print(f"\n🔍 {player_name}:")
        
        # Get data from individual sources
        fbref_data = fetcher._fetch_from_fbref(player_name, "Unknown")
        understat_data = fetcher._fetch_from_understat(player_name, "Unknown")
        
        if fbref_data and understat_data:
            print(f"  FBRef:     xG={fbref_data.xG_per_90:.4f} xA={fbref_data.xA_per_90:.4f} xCS={fbref_data.xCS_per_90:.4f} xMins={fbref_data.xMins_pct:.4f}")
            print(f"  Understat: xG={understat_data.xG_per_90:.4f} xA={understat_data.xA_per_90:.4f} xCS={understat_data.xCS_per_90:.4f} xMins={understat_data.xMins_pct:.4f}")
            
            # Calculate expected merged values (weighted average)
            # FBRef weight: 0.5, Understat weight: 0.3
            expected_xg = (fbref_data.xG_per_90 * 0.5 + understat_data.xG_per_90 * 0.3) / 0.8
            expected_xa = (fbref_data.xA_per_90 * 0.5 + understat_data.xA_per_90 * 0.3) / 0.8
            expected_xcs = (fbref_data.xCS_per_90 * 0.5 + understat_data.xCS_per_90 * 0.3) / 0.8
            expected_xmins = (fbref_data.xMins_pct * 0.5 + understat_data.xMins_pct * 0.3) / 0.8
            
            print(f"  Expected:  xG={expected_xg:.4f} xA={expected_xa:.4f} xCS={expected_xcs:.4f} xMins={expected_xmins:.4f}")
            
            # Get actual merged data
            merged_data = fetcher.get_player_xg_xa(player_name, "Unknown", merge_sources=True)
            if merged_data:
                print(f"  Merged:    xG={merged_data.xG_per_90:.4f} xA={merged_data.xA_per_90:.4f} xCS={merged_data.xCS_per_90:.4f} xMins={merged_data.xMins_pct:.4f}")
                print(f"  Match:     {'✅' if abs(merged_data.xG_per_90 - expected_xg) < 0.001 else '❌'}")

def test_xcs_and_xmins_data():
    """Test xCS and xMinsPct data specifically"""
    
    print(f"\n🎯 Testing xCS and xMinsPct Data")
    print("=" * 50)
    
    fetcher = XGXAFetcher()
    
    # Test players with different positions to see xCS differences
    test_players = [
        ("Mohamed Salah", "Liverpool", "MID"),
        ("Erling Haaland", "Man City", "FWD"),
        ("Virgil van Dijk", "Liverpool", "DEF"),
        ("Alisson", "Liverpool", "GK"),
    ]
    
    for player_name, team, position in test_players:
        print(f"\n🔍 {player_name} ({position}):")
        
        # Get data from different sources
        fbref_data = fetcher._fetch_from_fbref(player_name, team)
        estimated_data = fetcher._get_estimated_xg_xa(player_name, team, position)
        
        if fbref_data:
            print(f"  FBRef:     xCS={fbref_data.xCS_per_90:.4f} xMins={fbref_data.xMins_pct:.4f}")
        else:
            print(f"  FBRef:     No data")
        
        if estimated_data:
            print(f"  Estimated: xCS={estimated_data.xCS_per_90:.4f} xMins={estimated_data.xMins_pct:.4f}")
        
        # Show position-specific patterns
        if position == "DEF":
            print(f"  Note:      Defenders typically have higher xCS rates")
        elif position == "GK":
            print(f"  Note:      Goalkeepers have highest xCS rates and xMins")
        elif position == "FWD":
            print(f"  Note:      Forwards have lowest xCS rates")

def test_historical_data_with_enhanced_sources():
    """Test historical data manager with enhanced xG/xA/xCS/xMins data"""
    
    print(f"\n📈 Testing Historical Data with Enhanced Sources")
    print("=" * 60)
    
    historical_manager = HistoricalDataManager()
    
    # Test player historical stats
    test_players = ["Mohamed Salah", "Erling Haaland", "Bukayo Saka"]
    
    for player_name in test_players:
        print(f"\n🔍 Historical Data for {player_name}:")
        stats = historical_manager.get_player_historical_stats(player_name)
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

def explain_data_source_system():
    """Explain how the data source system works"""
    
    print(f"\n📚 Data Source System Explanation")
    print("=" * 60)
    
    print("""
🔍 How Data Sources Work:

1. PRIMARY SOURCE (FBRef):
   - Most reliable and comprehensive
   - Weight: 50% in merged calculations
   - Contains real xG/xA/xCS/xMins data

2. SECONDARY SOURCE (Understat):
   - Alternative data provider
   - Weight: 30% in merged calculations
   - Slightly different methodologies

3. TERTIARY SOURCE (FotMob):
   - Additional data source
   - Weight: 20% in merged calculations
   - Currently placeholder

4. FALLBACK (Estimated):
   - Used when no real data available
   - Weight: 10% in merged calculations
   - Based on position, price, team strength

🔄 Merging Process:
   - Collects data from all available sources
   - Applies weighted averages based on source reliability
   - Handles missing data gracefully
   - Returns single, consolidated dataset

📊 Data Components:
   - xG per 90: Expected goals per 90 minutes
   - xA per 90: Expected assists per 90 minutes  
   - xCS per 90: Expected clean sheets per 90 minutes
   - xMins %: Expected minutes percentage

🎯 Benefits:
   - Redundancy: Multiple sources ensure data availability
   - Accuracy: Weighted averages reduce single-source bias
   - Completeness: All xPts components covered
   - Reliability: Fallbacks for missing data
    """)

if __name__ == "__main__":
    test_data_source_hierarchy()
    test_source_comparison()
    test_merging_algorithm()
    test_xcs_and_xmins_data()
    test_historical_data_with_enhanced_sources()
    explain_data_source_system() 