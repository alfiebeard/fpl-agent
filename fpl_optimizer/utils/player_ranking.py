#!/usr/bin/env python3
"""
Player ranking utility - generates comprehensive player tables sorted by xPts
"""

import pandas as pd
from typing import List, Dict, Optional, Tuple
from fpl_optimizer.main import FPLOptimizer
from fpl_optimizer.projection.historical_xpts import HistoricalExpectedPointsCalculator
from fpl_optimizer.data.xg_xa_fetcher import XGXAFetcher
import logging

logger = logging.getLogger(__name__)

class PlayerRanking:
    """Utility for ranking players by xPts with comprehensive details"""
    
    def __init__(self):
        self.optimizer = FPLOptimizer()
        self.xg_xa_fetcher = XGXAFetcher()
        self.calculator = None
        self.data = None
        
    def load_data(self):
        """Load and process all FPL data"""
        logger.info("Loading FPL data...")
        self.data = self.optimizer._fetch_all_data()
        processed_data = self.optimizer._process_data(self.data)
        self.calculator = HistoricalExpectedPointsCalculator(self.optimizer.config)
        return processed_data
    
    def get_player_xpts_breakdown(self, player, fixture, home_team, away_team) -> Dict:
        """Get detailed xPts breakdown for a player"""
        
        # Calculate all components
        xg = self.calculator._calculate_expected_goals(player, fixture, home_team, away_team)
        xa = self.calculator._calculate_expected_assists(player, fixture, home_team, away_team)
        cs_prob = self.calculator._calculate_clean_sheet_probability(player, fixture, home_team, away_team)
        bonus_prob = self.calculator._calculate_bonus_probability(player, xg, xa)
        yc_prob = self.calculator._calculate_yellow_card_probability(player)
        rc_prob = self.calculator._calculate_red_card_probability(player)
        xmins = self.calculator._calculate_expected_minutes(player, fixture)
        
        # Calculate total xPts
        total_xpts = self.calculator.calculate_player_xpts(player, fixture, home_team, away_team)
        
        # Get xG/xA data from real sources
        xg_xa_data = self.xg_xa_fetcher.get_player_xg_xa(player.name, player.team_name, merge_sources=True)
        
        return {
            'player_id': player.id,
            'name': player.name,
            'team': player.team_name,
            'position': player.position.value,
            'price': player.price,
            'form': player.form,
            'total_points': player.total_points,
            'points_per_game': player.points_per_game,
            'minutes_played': player.minutes_played,
            'xMins_pct': player.xMins_pct,
            'is_injured': player.is_injured,
            'injury_expected_return': player.injury_expected_return,
            'selected_by_pct': player.selected_by_pct,
            
            # xPts components
            'total_xpts': total_xpts,
            'xg': xg,
            'xa': xa,
            'cs_prob': cs_prob,
            'bonus_prob': bonus_prob,
            'yc_prob': yc_prob,
            'rc_prob': rc_prob,
            'xmins': xmins,
            
            # Real data sources
            'real_xg_per_90': xg_xa_data.xG_per_90 if xg_xa_data else None,
            'real_xa_per_90': xg_xa_data.xA_per_90 if xg_xa_data else None,
            'real_xcs_per_90': xg_xa_data.xCS_per_90 if xg_xa_data else None,
            'real_xmins_pct': xg_xa_data.xMins_pct if xg_xa_data else None,
            'data_source': xg_xa_data.source if xg_xa_data else 'estimated',
            
            # Fixture info
            'fixture_difficulty': fixture.home_difficulty if player.team_id == fixture.home_team_id else fixture.away_difficulty,
            'opponent': fixture.away_team_name if player.team_id == fixture.home_team_id else fixture.home_team_name,
            'is_home': player.team_id == fixture.home_team_id,
        }
    
    def generate_player_ranking_table(self, 
                                    position_filter: Optional[str] = None,
                                    price_min: Optional[float] = None,
                                    price_max: Optional[float] = None,
                                    team_filter: Optional[str] = None,
                                    min_games: int = 0,
                                    sort_by: str = 'total_xpts',
                                    ascending: bool = False,
                                    limit: Optional[int] = None) -> pd.DataFrame:
        """
        Generate comprehensive player ranking table
        
        Args:
            position_filter: Filter by position ('GK', 'DEF', 'MID', 'FWD')
            price_min: Minimum price filter
            price_max: Maximum price filter
            team_filter: Filter by team name
            min_games: Minimum games played
            sort_by: Column to sort by
            ascending: Sort order
            limit: Limit number of results
        """
        
        if not self.data:
            self.load_data()
        
        processed_data = self.optimizer._process_data(self.data)
        players = processed_data['players']
        fixtures = processed_data['fixtures']
        teams = processed_data['teams']
        
        logger.info(f"Calculating xPts for {len(players)} players...")
        
        player_data = []
        
        for player in players:
            # Apply filters
            if position_filter and player.position.value != position_filter:
                continue
            if price_min and player.price < price_min:
                continue
            if price_max and player.price > price_max:
                continue
            if team_filter and team_filter.lower() not in player.team_name.lower():
                continue
            if min_games > 0 and player.games_played < min_games:
                continue
            
            # Get player's next fixture
            player_fixtures = []
            for fixture in fixtures:
                if fixture.home_team_name == player.team_name or fixture.away_team_name == player.team_name:
                    player_fixtures.append(fixture)
            
            if not player_fixtures:
                continue
            
            fixture = player_fixtures[0]  # Next fixture
            
            # Get teams
            home_team = next((t for t in teams if t.name == fixture.home_team_name), None)
            away_team = next((t for t in teams if t.name == fixture.away_team_name), None)
            
            if not home_team or not away_team:
                continue
            
            # Get detailed breakdown
            breakdown = self.get_player_xpts_breakdown(player, fixture, home_team, away_team)
            player_data.append(breakdown)
        
        # Create DataFrame
        df = pd.DataFrame(player_data)
        
        if df.empty:
            logger.warning("No players match the specified filters")
            return df
        
        # Sort by specified column
        df = df.sort_values(by=sort_by, ascending=ascending)
        
        # Apply limit
        if limit:
            df = df.head(limit)
        
        return df
    
    def get_top_players_by_position(self, limit: int = 20) -> Dict[str, pd.DataFrame]:
        """Get top players for each position"""
        
        positions = ['GK', 'DEF', 'MID', 'FWD']
        results = {}
        
        for position in positions:
            logger.info(f"Getting top {position} players...")
            df = self.generate_player_ranking_table(
                position_filter=position,
                sort_by='total_xpts',
                ascending=False,
                limit=limit
            )
            results[position] = df
        
        return results
    
    def get_value_players(self, price_max: float = 6.0, limit: int = 20) -> pd.DataFrame:
        """Get best value players under a certain price"""
        
        return self.generate_player_ranking_table(
            price_max=price_max,
            sort_by='total_xpts',
            ascending=False,
            limit=limit
        )
    
    def get_premium_players(self, price_min: float = 10.0, limit: int = 20) -> pd.DataFrame:
        """Get premium players above a certain price"""
        
        return self.generate_player_ranking_table(
            price_min=price_min,
            sort_by='total_xpts',
            ascending=False,
            limit=limit
        )
    
    def export_to_csv(self, df: pd.DataFrame, filename: str):
        """Export ranking table to CSV"""
        df.to_csv(filename, index=False)
        logger.info(f"Exported {len(df)} players to {filename}")
    
    def print_summary_table(self, df: pd.DataFrame, show_columns: List[str] = None):
        """Print a formatted summary table"""
        
        if show_columns is None:
            show_columns = [
                'name', 'team', 'position', 'price', 'total_xpts', 
                'real_xg_per_90', 'real_xa_per_90', 'real_xcs_per_90', 'real_xmins_pct',
                'fixture_difficulty', 'opponent', 'is_home'
            ]
        
        # Filter columns that exist in the DataFrame
        available_columns = [col for col in show_columns if col in df.columns]
        
        if not available_columns:
            logger.warning("No valid columns to display")
            return
        
        # Select and format columns
        display_df = df[available_columns].copy()
        
        # Format numeric columns
        if 'price' in display_df.columns:
            display_df['price'] = display_df['price'].apply(lambda x: f"£{x:.1f}M")
        if 'total_xpts' in display_df.columns:
            display_df['total_xpts'] = display_df['total_xpts'].apply(lambda x: f"{x:.3f}")
        if 'real_xg_per_90' in display_df.columns:
            display_df['real_xg_per_90'] = display_df['real_xg_per_90'].apply(lambda x: f"{x:.3f}" if x is not None else "N/A")
        if 'real_xa_per_90' in display_df.columns:
            display_df['real_xa_per_90'] = display_df['real_xa_per_90'].apply(lambda x: f"{x:.3f}" if x is not None else "N/A")
        if 'real_xcs_per_90' in display_df.columns:
            display_df['real_xcs_per_90'] = display_df['real_xcs_per_90'].apply(lambda x: f"{x:.3f}" if x is not None else "N/A")
        if 'real_xmins_pct' in display_df.columns:
            display_df['real_xmins_pct'] = display_df['real_xmins_pct'].apply(lambda x: f"{x:.1%}" if x is not None else "N/A")
        if 'is_home' in display_df.columns:
            display_df['is_home'] = display_df['is_home'].apply(lambda x: "H" if x else "A")
        
        # Print table
        print(f"\n📊 Player Ranking Table ({len(df)} players)")
        print("=" * 100)
        print(display_df.to_string(index=False, max_colwidth=20))
        print("=" * 100)
        
        # Print summary stats
        print(f"\n📈 Summary Statistics:")
        print(f"  Total players: {len(df)}")
        print(f"  Average xPts: {df['total_xpts'].mean():.3f}")
        print(f"  Max xPts: {df['total_xpts'].max():.3f}")
        print(f"  Min xPts: {df['total_xpts'].min():.3f}")
        
        if 'price' in df.columns:
            print(f"  Average price: £{df['price'].mean():.1f}M")
            print(f"  Total value: £{df['price'].sum():.1f}M")
        
        if 'points_per_game' in df.columns:
            print(f"  Average PPG: {df['points_per_game'].mean():.2f}")
        
        # Position breakdown
        if 'position' in df.columns:
            print(f"\n🎯 Position Breakdown:")
            for pos in ['GK', 'DEF', 'MID', 'FWD']:
                pos_df = df[df['position'] == pos]
                if not pos_df.empty:
                    print(f"  {pos}: {len(pos_df)} players, avg xPts: {pos_df['total_xpts'].mean():.3f}")
        
        # Team breakdown
        if 'team' in df.columns:
            print(f"\n🏆 Top Teams by Average xPts:")
            team_stats = df.groupby('team')['total_xpts'].agg(['count', 'mean']).sort_values('mean', ascending=False)
            for team, stats in team_stats.head(5).iterrows():
                print(f"  {team}: {stats['count']} players, avg xPts: {stats['mean']:.3f}") 