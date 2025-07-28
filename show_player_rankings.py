#!/usr/bin/env python3
"""
Show player rankings with comprehensive details
"""

from fpl_optimizer.utils.player_ranking import PlayerRanking
import pandas as pd

def main():
    """Main function to demonstrate player ranking utility"""
    
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
    
    # 4. Premium players (over £10.0M)
    print("\n" + "="*60)
    print("💎 PREMIUM PLAYERS (Over £10.0M)")
    print("="*60)
    
    premium_players = ranking.get_premium_players(price_min=10.0, limit=20)
    ranking.print_summary_table(premium_players)
    
    # 5. Midfielders only
    print("\n" + "="*60)
    print("⚽ TOP MIDFIELDERS")
    print("="*60)
    
    midfielders = ranking.generate_player_ranking_table(
        position_filter='MID',
        sort_by='total_xpts',
        ascending=False,
        limit=20
    )
    ranking.print_summary_table(midfielders)
    
    # 6. Forwards only
    print("\n" + "="*60)
    print("🎯 TOP FORWARDS")
    print("="*60)
    
    forwards = ranking.generate_player_ranking_table(
        position_filter='FWD',
        sort_by='total_xpts',
        ascending=False,
        limit=20
    )
    ranking.print_summary_table(forwards)
    
    # 7. Defenders only
    print("\n" + "="*60)
    print("🛡️ TOP DEFENDERS")
    print("="*60)
    
    defenders = ranking.generate_player_ranking_table(
        position_filter='DEF',
        sort_by='total_xpts',
        ascending=False,
        limit=20
    )
    ranking.print_summary_table(defenders)
    
    # 8. Goalkeepers only
    print("\n" + "="*60)
    print("🥅 TOP GOALKEEPERS")
    print("="*60)
    
    goalkeepers = ranking.generate_player_ranking_table(
        position_filter='GK',
        sort_by='total_xpts',
        ascending=False,
        limit=15
    )
    ranking.print_summary_table(goalkeepers)
    
    # 9. Players with high xG (potential goal scorers)
    print("\n" + "="*60)
    print("⚽ HIGH xG PLAYERS (Goal Scorers)")
    print("="*60)
    
    high_xg_players = ranking.generate_player_ranking_table(
        sort_by='real_xg_per_90',
        ascending=False,
        limit=20
    )
    ranking.print_summary_table(high_xg_players, show_columns=[
        'name', 'team', 'position', 'price', 'real_xg_per_90', 'real_xa_per_90', 'total_xpts'
    ])
    
    # 10. Players with high xA (potential assist providers)
    print("\n" + "="*60)
    print("🎯 HIGH xA PLAYERS (Assist Providers)")
    print("="*60)
    
    high_xa_players = ranking.generate_player_ranking_table(
        sort_by='real_xa_per_90',
        ascending=False,
        limit=20
    )
    ranking.print_summary_table(high_xa_players, show_columns=[
        'name', 'team', 'position', 'price', 'real_xg_per_90', 'real_xa_per_90', 'total_xpts'
    ])
    
    # 11. Export full ranking to CSV
    print("\n" + "="*60)
    print("💾 EXPORTING DATA")
    print("="*60)
    
    # Export top 100 players
    top_100 = ranking.generate_player_ranking_table(
        sort_by='total_xpts',
        ascending=False,
        limit=100
    )
    
    ranking.export_to_csv(top_100, 'top_100_players_by_xpts.csv')
    print("✅ Exported top 100 players to 'top_100_players_by_xpts.csv'")
    
    # Export all players by position
    for position in ['GK', 'DEF', 'MID', 'FWD']:
        pos_players = ranking.generate_player_ranking_table(
            position_filter=position,
            sort_by='total_xpts',
            ascending=False
        )
        ranking.export_to_csv(pos_players, f'top_{position.lower()}_players.csv')
        print(f"✅ Exported {position} players to 'top_{position.lower()}_players.csv'")
    
    print("\n🎉 Analysis complete! Check the CSV files for detailed data.")

def interactive_mode():
    """Interactive mode for custom queries"""
    
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

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--interactive":
        interactive_mode()
    else:
        main() 