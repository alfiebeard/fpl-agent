#!/usr/bin/env python3
"""
Show detailed xPts table with breakdowns for all players
"""

from fpl_optimizer.main import FPLOptimizer
from fpl_optimizer.projection.xpts import ExpectedPointsCalculator
from fpl_optimizer.models import Position
import pandas as pd

def show_detailed_xpts_table():
    """Show detailed xPts table with breakdowns for all players"""
    
    print("📊 Detailed xPts Table with Breakdowns")
    print("=" * 80)
    
    # Initialize optimizer
    optimizer = FPLOptimizer()
    
    # Fetch data
    print("Fetching data and calculating xPts...")
    data = optimizer._fetch_all_data()
    processed_data = optimizer._process_data(data)
    
    # Initialize calculator
    calculator = ExpectedPointsCalculator(optimizer.config)
    
    # Calculate xPts for all players
    print("Calculating xPts for all players...")
    player_data = []
    
    for player in processed_data['players']:
        try:
            # Get player's fixtures
            team_fixtures = []
            for fixture in processed_data['fixtures']:
                if fixture.home_team_name == player.team_name or fixture.away_team_name == player.team_name:
                    team_fixtures.append(fixture)
            
            if not team_fixtures:
                continue
            
            # Calculate total xPts and breakdown for first 5 fixtures
            total_xpts = 0
            total_xg = 0
            total_xa = 0
            total_cs_points = 0
            total_bonus_points = 0
            total_yc_points = 0
            total_rc_points = 0
            total_base_points = 0
            fixture_count = 0
            
            for fixture in team_fixtures[:5]:  # First 5 fixtures for breakdown
                # Get teams for this fixture
                if fixture.home_team_name == player.team_name:
                    home_team = next((t for t in processed_data['teams'] if t.name == fixture.home_team_name), None)
                    away_team = next((t for t in processed_data['teams'] if t.name == fixture.away_team_name), None)
                else:
                    home_team = next((t for t in processed_data['teams'] if t.name == fixture.home_team_name), None)
                    away_team = next((t for t in processed_data['teams'] if t.name == fixture.away_team_name), None)
                
                if home_team and away_team:
                    # Calculate components
                    xg = calculator._calculate_expected_goals(player, fixture, home_team, away_team)
                    xa = calculator._calculate_expected_assists(player, fixture, home_team, away_team)
                    cs_prob = calculator._calculate_clean_sheet_probability(player, fixture, home_team, away_team)
                    bonus_prob = calculator._calculate_bonus_probability(player, xg, xa)
                    yc_prob = calculator._calculate_yellow_card_probability(player)
                    rc_prob = calculator._calculate_red_card_probability(player)
                    xmins = calculator._calculate_expected_minutes(player, fixture)
                    
                    # Get point values
                    goal_pts = calculator.points_config['goal'].get(player.position.value.lower(), 4)
                    assist_pts = calculator.points_config['assist']
                    cs_pts = calculator.points_config['clean_sheet'].get(player.position.value.lower(), 0)
                    bonus_pts = calculator.points_config['bonus']
                    yc_pts = calculator.points_config['yellow_card']
                    rc_pts = calculator.points_config['red_card']
                    
                    # Calculate points from each source
                    cs_points = cs_prob * cs_pts
                    bonus_points = bonus_prob * bonus_pts
                    yc_points = yc_prob * yc_pts
                    rc_points = rc_prob * rc_pts
                    base_points = 2.0 * xmins
                    
                    # Accumulate totals
                    total_xg += xg
                    total_xa += xa
                    total_cs_points += cs_points
                    total_bonus_points += bonus_points
                    total_yc_points += yc_points
                    total_rc_points += rc_points
                    total_base_points += base_points
                    fixture_count += 1
            
            # Calculate averages for 5 fixtures
            if fixture_count > 0:
                avg_xg = total_xg / fixture_count
                avg_xa = total_xa / fixture_count
                avg_cs_points = total_cs_points / fixture_count
                avg_bonus_points = total_bonus_points / fixture_count
                avg_yc_points = total_yc_points / fixture_count
                avg_rc_points = total_rc_points / fixture_count
                avg_base_points = total_base_points / fixture_count
            else:
                avg_xg = avg_xa = avg_cs_points = avg_bonus_points = avg_yc_points = avg_rc_points = avg_base_points = 0
            
            # Calculate total xPts for all fixtures
            total_xpts = 0
            for fixture in team_fixtures:
                if fixture.home_team_name == player.team_name:
                    home_team = next((t for t in processed_data['teams'] if t.name == fixture.home_team_name), None)
                    away_team = next((t for t in processed_data['teams'] if t.name == fixture.away_team_name), None)
                else:
                    home_team = next((t for t in processed_data['teams'] if t.name == fixture.home_team_name), None)
                    away_team = next((t for t in processed_data['teams'] if t.name == fixture.away_team_name), None)
                
                if home_team and away_team:
                    xpts = calculator.calculate_player_xpts(player, fixture, home_team, away_team)
                    total_xpts += xpts
            
            # Add player data
            player_data.append({
                'name': player.name,
                'team': player.team_name,
                'position': player.position.value,
                'price': player.price,
                'total_xpts': total_xpts,
                'avg_xpts_per_fixture': total_xpts / len(team_fixtures) if team_fixtures else 0,
                'avg_xg': avg_xg,
                'avg_xa': avg_xa,
                'avg_cs_points': avg_cs_points,
                'avg_bonus_points': avg_bonus_points,
                'avg_yc_points': avg_yc_points,
                'avg_rc_points': avg_rc_points,
                'avg_base_points': avg_base_points,
                'form': player.form,
                'xMins_pct': player.xMins_pct
            })
            
        except Exception as e:
            print(f"Error calculating xPts for {player.name}: {e}")
            continue
    
    # Convert to DataFrame and sort by total xPts
    df = pd.DataFrame(player_data)
    df = df.sort_values('total_xpts', ascending=False)
    
    # Display top 50 players with detailed breakdown
    print(f"\n🏆 Top 50 Players by Total xPts (All Fixtures):")
    print("=" * 120)
    
    # Format the table
    print(f"{'Rank':<4} {'Name':<20} {'Team':<15} {'Pos':<3} {'Price':<6} {'Total':<6} {'Per GW':<6} {'xG':<5} {'xA':<5} {'CS':<5} {'Bonus':<6} {'YC':<5} {'RC':<5} {'Base':<5} {'Form':<5}")
    print("-" * 120)
    
    for i, row in df.head(50).iterrows():
        print(f"{row.name+1:<4} {row['name']:<20} {row['team']:<15} {row['position']:<3} £{row['price']:<5.1f} {row['total_xpts']:<6.1f} {row['avg_xpts_per_fixture']:<6.2f} {row['avg_xg']:<5.3f} {row['avg_xa']:<5.3f} {row['avg_cs_points']:<5.2f} {row['avg_bonus_points']:<6.2f} {row['avg_yc_points']:<5.2f} {row['avg_rc_points']:<5.2f} {row['avg_base_points']:<5.2f} {row['form']:<5.1f}")
    
    # Show position breakdowns
    print(f"\n📈 Position Breakdowns (Top 10 each):")
    
    for position in ['GK', 'DEF', 'MID', 'FWD']:
        pos_df = df[df['position'] == position].head(10)
        if not pos_df.empty:
            print(f"\n{position} Players (Top 10):")
            print("-" * 120)
            print(f"{'Rank':<4} {'Name':<20} {'Team':<15} {'Price':<6} {'Total':<6} {'Per GW':<6} {'xG':<5} {'xA':<5} {'CS':<5} {'Bonus':<6} {'YC':<5} {'RC':<5} {'Base':<5}")
            print("-" * 120)
            
            for i, row in pos_df.iterrows():
                print(f"{i+1:<4} {row['name']:<20} {row['team']:<15} £{row['price']:<5.1f} {row['total_xpts']:<6.1f} {row['avg_xpts_per_fixture']:<6.2f} {row['avg_xg']:<5.3f} {row['avg_xa']:<5.3f} {row['avg_cs_points']:<5.2f} {row['avg_bonus_points']:<6.2f} {row['avg_yc_points']:<5.2f} {row['avg_rc_points']:<5.2f} {row['avg_base_points']:<5.2f}")
    
    # Show budget analysis
    print(f"\n💰 Budget Analysis:")
    print("-" * 50)
    
    budget_ranges = [
        ('Budget (£4.0-5.0M)', 4.0, 5.0),
        ('Mid-range (£5.1-7.0M)', 5.1, 7.0),
        ('Premium (£7.1-10.0M)', 7.1, 10.0),
        ('Ultra Premium (£10.1M+)', 10.1, 20.0)
    ]
    
    for label, min_price, max_price in budget_ranges:
        budget_df = df[(df['price'] >= min_price) & (df['price'] <= max_price)]
        if not budget_df.empty:
            best_player = budget_df.iloc[0]
            print(f"{label}: {best_player['name']} ({best_player['team']}) - £{best_player['price']:.1f}M - {best_player['total_xpts']:.1f} xPts")
    
    # Show statistics
    print(f"\n📊 Statistics:")
    print("-" * 30)
    print(f"Total Players: {len(df)}")
    print(f"Average xPts: {df['total_xpts'].mean():.1f}")
    print(f"Max xPts: {df['total_xpts'].max():.1f}")
    print(f"Min xPts: {df['total_xpts'].min():.1f}")
    
    # Save to CSV for further analysis
    csv_filename = "detailed_xpts_table.csv"
    df.to_csv(csv_filename, index=False)
    print(f"\n💾 Detailed data saved to: {csv_filename}")

if __name__ == "__main__":
    show_detailed_xpts_table() 