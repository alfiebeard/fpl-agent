#!/usr/bin/env python3
"""
Quick demo of the player ranking utility
"""

from fpl_optimizer.utils.player_ranking import PlayerRanking

def main():
    """Quick demo of the ranking utility"""
    
    print("🏆 Quick Player Ranking Demo")
    print("=" * 50)
    
    # Initialize ranking utility
    ranking = PlayerRanking()
    
    # Load data
    print("Loading FPL data...")
    ranking.load_data()
    
    # Get top 20 players by xPts
    print("\n📊 Top 20 Players by xPts:")
    print("-" * 50)
    
    top_20 = ranking.generate_player_ranking_table(
        sort_by='total_xpts',
        ascending=False,
        limit=20
    )
    
    # Print a simple table
    for i, (_, row) in enumerate(top_20.iterrows(), 1):
        print(f"{i:2d}. {row['name']:<20} {row['team']:<15} {row['position']} £{row['price']:.1f}M {row['total_xpts']:.3f} xPts")
    
    # Get top 10 midfielders
    print("\n⚽ Top 10 Midfielders:")
    print("-" * 50)
    
    top_mids = ranking.generate_player_ranking_table(
        position_filter='MID',
        sort_by='total_xpts',
        ascending=False,
        limit=10
    )
    
    for i, (_, row) in enumerate(top_mids.iterrows(), 1):
        print(f"{i:2d}. {row['name']:<20} {row['team']:<15} £{row['price']:.1f}M {row['total_xpts']:.3f} xPts")
    
    # Get value players (under £6M)
    print("\n💰 Top 10 Value Players (Under £6M):")
    print("-" * 50)
    
    value_players = ranking.generate_player_ranking_table(
        price_max=6.0,
        sort_by='total_xpts',
        ascending=False,
        limit=10
    )
    
    for i, (_, row) in enumerate(value_players.iterrows(), 1):
        print(f"{i:2d}. {row['name']:<20} {row['team']:<15} {row['position']} £{row['price']:.1f}M {row['total_xpts']:.3f} xPts")
    
    print("\n✅ Demo complete! Use 'python show_player_rankings.py' for full analysis.")

if __name__ == "__main__":
    main() 