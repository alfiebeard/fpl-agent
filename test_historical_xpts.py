#!/usr/bin/env python3
"""
Test the historical data-based xPts calculator
"""

from fpl_optimizer.main import FPLOptimizer
from fpl_optimizer.projection.historical_xpts import HistoricalExpectedPointsCalculator
from fpl_optimizer.data.historical_data import HistoricalDataManager
from fpl_optimizer.models import Position

def test_historical_data_system():
    """Test the historical data system"""
    
    print("🧪 Testing Historical Data System")
    print("=" * 50)
    
    # Initialize historical data manager
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
    test_teams = ["Man City", "Arsenal", "Liverpool"]
    
    for team_name in test_teams:
        print(f"\n🏆 Historical Data for {team_name}:")
        stats = historical_manager.get_team_historical_stats(team_name)
        if stats:
            print(f"  xG per game: {stats['xg_per_game']:.4f}")
            print(f"  xGA per game: {stats['xga_per_game']:.4f}")
            print(f"  Clean sheet rate: {stats['clean_sheet_rate']:.4f}")
            print(f"  Total games: {stats['total_games']}")
        else:
            print(f"  No historical data found")

def test_historical_xpts_calculator():
    """Test the historical xPts calculator"""
    
    print("\n🧮 Testing Historical xPts Calculator")
    print("=" * 50)
    
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
                    
                    # Calculate components
                    xg = calculator._calculate_expected_goals(player, fixture, home_team, away_team)
                    xa = calculator._calculate_expected_assists(player, fixture, home_team, away_team)
                    cs_prob = calculator._calculate_clean_sheet_probability(player, fixture, home_team, away_team)
                    bonus_prob = calculator._calculate_bonus_probability(player, xg, xa)
                    yc_prob = calculator._calculate_yellow_card_probability(player)
                    rc_prob = calculator._calculate_red_card_probability(player)
                    xmins = calculator._calculate_expected_minutes(player, fixture)
                    
                    print(f"  xG: {xg:.4f}")
                    print(f"  xA: {xa:.4f}")
                    print(f"  CS prob: {cs_prob:.4f}")
                    print(f"  Bonus prob: {bonus_prob:.4f}")
                    print(f"  YC prob: {yc_prob:.4f}")
                    print(f"  RC prob: {rc_prob:.4f}")
                    print(f"  Minutes: {xmins:.4f}")
                    
                    # Calculate total xPts
                    total_xpts = calculator.calculate_player_xpts(player, fixture, home_team, away_team)
                    print(f"  Total xPts: {total_xpts:.4f}")

def compare_calculators():
    """Compare historical vs improved calculator"""
    
    print("\n📊 Comparing Historical vs Improved Calculator")
    print("=" * 60)
    
    # Initialize
    optimizer = FPLOptimizer()
    data = optimizer._fetch_all_data()
    processed_data = optimizer._process_data(data)
    
    # Create both calculators
    from improved_xpts_calculator import ImprovedExpectedPointsCalculator
    historical_calc = HistoricalExpectedPointsCalculator(optimizer.config)
    improved_calc = ImprovedExpectedPointsCalculator(optimizer.config)
    
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
                    # Calculate with both calculators
                    hist_xg = historical_calc._calculate_expected_goals(player, fixture, home_team, away_team)
                    hist_xa = historical_calc._calculate_expected_assists(player, fixture, home_team, away_team)
                    hist_xmins = historical_calc._calculate_expected_minutes(player, fixture)
                    hist_xpts = historical_calc.calculate_player_xpts(player, fixture, home_team, away_team)
                    
                    imp_xg = improved_calc._calculate_expected_goals(player, fixture, home_team, away_team)
                    imp_xa = improved_calc._calculate_expected_assists(player, fixture, home_team, away_team)
                    imp_xmins = improved_calc._calculate_expected_minutes(player, fixture)
                    imp_xpts = improved_calc.calculate_player_xpts(player, fixture, home_team, away_team)
                    
                    print(f"  {'Metric':<15} {'Historical':<12} {'Improved':<12} {'Diff':<10}")
                    print(f"  {'-'*15} {'-'*12} {'-'*12} {'-'*10}")
                    print(f"  {'xG':<15} {hist_xg:<12.4f} {imp_xg:<12.4f} {hist_xg-imp_xg:<10.4f}")
                    print(f"  {'xA':<15} {hist_xa:<12.4f} {imp_xa:<12.4f} {hist_xa-imp_xa:<10.4f}")
                    print(f"  {'Minutes':<15} {hist_xmins:<12.4f} {imp_xmins:<12.4f} {hist_xmins-imp_xmins:<10.4f}")
                    print(f"  {'Total xPts':<15} {hist_xpts:<12.4f} {imp_xpts:<12.4f} {hist_xpts-imp_xpts:<10.4f}")

if __name__ == "__main__":
    test_historical_data_system()
    test_historical_xpts_calculator()
    compare_calculators() 