#!/usr/bin/env python3
"""
Test real API integration for xG/xA data
"""

from fpl_optimizer.data.xg_xa_fetcher import XGXAFetcher
from fpl_optimizer.data.historical_data import HistoricalDataManager
from fpl_optimizer.projection.historical_xpts import HistoricalExpectedPointsCalculator
from fpl_optimizer.main import FPLOptimizer

def test_xg_xa_fetcher():
    """Test the xG/xA fetcher with real data"""
    
    print("🔍 Testing xG/xA Fetcher with Real Data")
    print("=" * 50)
    
    fetcher = XGXAFetcher()
    
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
        
        data = fetcher.get_player_xg_xa(player_name, team)
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
        team_data = fetcher.get_team_xg_xga(team)
        if team_data:
            print(f"{team}: xG={team_data['xG_per_game']:.2f}, xGA={team_data['xGA_per_game']:.2f}")
        else:
            print(f"{team}: No data found")

def test_historical_data_with_real_apis():
    """Test historical data manager with real API integration"""
    
    print(f"\n📈 Testing Historical Data with Real APIs")
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
    
    # Test team historical stats
    print(f"\n🏆 Historical Team Data:")
    print("-" * 30)
    
    test_teams = ["Man City", "Arsenal", "Liverpool"]
    
    for team_name in test_teams:
        stats = historical_manager.get_team_historical_stats(team_name)
        if stats:
            print(f"{team_name}:")
            print(f"  xG per game: {stats['xg_per_game']:.4f}")
            print(f"  xGA per game: {stats['xga_per_game']:.4f}")
            print(f"  Clean sheet rate: {stats['clean_sheet_rate']:.4f}")
            print(f"  Total games: {stats['total_games']}")
        else:
            print(f"{team_name}: No data found")

def test_historical_xpts_with_real_data():
    """Test historical xPts calculator with real API data"""
    
    print(f"\n🧮 Testing Historical xPts with Real Data")
    print("=" * 60)
    
    # Initialize
    optimizer = FPLOptimizer()
    data = optimizer._fetch_all_data()
    processed_data = optimizer._process_data(data)
    
    # Create historical calculator
    calculator = HistoricalExpectedPointsCalculator(optimizer.config)
    
    # Test with a few players
    test_players = ["Mohamed Salah", "Erling Haaland", "Bukayo Saka"]
    
    for player_name in test_players:
        player = None
        for p in processed_data['players']:
            if player_name.lower() in p.name.lower():
                player = p
                break
        
        if player:
            print(f"\n🔍 {player.name} ({player.team_name}, {player.position.value}, £{player.price}M):")
            
            # Get first fixture
            team_fixtures = []
            for fixture in processed_data['fixtures']:
                if fixture.home_team_name == player.team_name or fixture.away_team_name == player.team_name:
                    team_fixtures.append(fixture)
            
            if team_fixtures:
                fixture = team_fixtures[0]
                
                # Get teams
                if fixture.home_team_name == player.team_name:
                    home_team = next((t for t in processed_data['teams'] if t.name == fixture.home_team_name), None)
                    away_team = next((t for t in processed_data['teams'] if t.name == fixture.away_team_name), None)
                else:
                    home_team = next((t for t in processed_data['teams'] if t.name == fixture.home_team_name), None)
                    away_team = next((t for t in processed_data['teams'] if t.name == fixture.away_team_name), None)
                
                if home_team and away_team:
                    # Get historical data
                    player_stats = calculator._get_player_historical_data(player)
                    home_stats = calculator._get_team_historical_data(home_team)
                    away_stats = calculator._get_team_historical_data(away_team)
                    
                    print(f"  Historical player data: {player_stats is not None}")
                    print(f"  Historical home team data: {home_stats is not None}")
                    print(f"  Historical away team data: {away_stats is not None}")
                    
                    if player_stats:
                        print(f"  Historical xG per 90: {player_stats['xg_per_90']:.4f}")
                        print(f"  Historical xA per 90: {player_stats['xa_per_90']:.4f}")
                        print(f"  Historical minutes %: {player_stats['minutes_pct']:.4f}")
                    
                    # Calculate components
                    xg = calculator._calculate_expected_goals(player, fixture, home_team, away_team)
                    xa = calculator._calculate_expected_assists(player, fixture, home_team, away_team)
                    cs_prob = calculator._calculate_clean_sheet_probability(player, fixture, home_team, away_team)
                    bonus_prob = calculator._calculate_bonus_probability(player, xg, xa)
                    yc_prob = calculator._calculate_yellow_card_probability(player)
                    rc_prob = calculator._calculate_red_card_probability(player)
                    xmins = calculator._calculate_expected_minutes(player, fixture)
                    
                    print(f"  Calculated xG: {xg:.4f}")
                    print(f"  Calculated xA: {xa:.4f}")
                    print(f"  CS prob: {cs_prob:.4f}")
                    print(f"  Bonus prob: {bonus_prob:.4f}")
                    print(f"  YC prob: {yc_prob:.4f}")
                    print(f"  RC prob: {rc_prob:.4f}")
                    print(f"  Minutes: {xmins:.4f}")
                    
                    # Calculate total xPts
                    total_xpts = calculator.calculate_player_xpts(player, fixture, home_team, away_team)
                    print(f"  Total xPts: {total_xpts:.4f}")

def compare_data_sources():
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
                    print(f"  {source.upper()}: xG={data.xG_per_90:.4f}, xA={data.xA_per_90:.4f}")
                else:
                    print(f"  {source.upper()}: No data")
            except Exception as e:
                print(f"  {source.upper()}: Error - {e}")

if __name__ == "__main__":
    test_xg_xa_fetcher()
    test_historical_data_with_real_apis()
    test_historical_xpts_with_real_data()
    compare_data_sources() 