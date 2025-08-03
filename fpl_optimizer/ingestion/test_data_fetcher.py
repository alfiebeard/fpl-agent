"""
Test data fetcher for FPL Optimizer
Fetches a sample of players for testing purposes - API-driven
"""

import logging
from typing import List, Dict, Any
from datetime import datetime
import random

from .fetch_fpl import FPLDataFetcher
from .fetch_understat import UnderstatDataFetcher
from .fetch_fbref import FBRefDataFetcher
from ..core.models import Player, Team, Position
from ..core.config import Config

logger = logging.getLogger(__name__)


class TestDataFetcher:
    """Fetches a sample of players for testing - API-driven"""
    
    def __init__(self, config: Config, sample_size: int = 50):
        self.config = config
        self.sample_size = sample_size
        self.fpl_fetcher = FPLDataFetcher(config)
        self.understat_fetcher = UnderstatDataFetcher(config)
        self.fbref_fetcher = FBRefDataFetcher(config)
    
    def get_test_players(self) -> List[Player]:
        """Fetch and return a sample of players for testing"""
        logger.info(f"Fetching test data for {self.sample_size} players...")
        
        try:
            # Step 1: Get FPL bootstrap data
            bootstrap_data = self.fpl_fetcher.get_bootstrap_data()
            all_players_data = bootstrap_data.get('elements', [])
            teams_data = bootstrap_data.get('teams', [])
            
            # Create team mapping
            team_mapping = {team['id']: team['name'] for team in teams_data}
            
            # Step 2: Sample players based on criteria
            sampled_players = self._sample_players(all_players_data, team_mapping)
            
            logger.info(f"Successfully sampled {len(sampled_players)} players")
            
            # Step 3: Add Understat data (xG/xA)
            logger.info("Adding Understat data...")
            enriched_players = self.understat_fetcher.update_players_with_xg_xa(sampled_players)
            
            # Step 4: Add FBRef data
            logger.info("Adding FBRef data...")
            enriched_players = self.fbref_fetcher.update_players_with_fbref_data(enriched_players)
            
            logger.info(f"Test data fetch complete: {len(enriched_players)} players")
            return enriched_players
            
        except Exception as e:
            logger.error(f"Error fetching test data: {e}")
            raise
    
    def _sample_players(self, all_players_data: List[Dict], team_mapping: Dict[int, str]) -> List[Player]:
        """Get all players or sample based on sample_size"""
        
        # If sample_size is very large, return all players
        if self.sample_size >= len(all_players_data):
            logger.info(f"Fetching all {len(all_players_data)} players...")
            all_players = []
            for player_data in all_players_data:
                position = self._get_position_from_fpl_data(player_data)
                if position:
                    team_name = team_mapping.get(player_data.get('team'), 'Unknown')
                    player = self._create_player_from_fpl_data(player_data, team_name, position)
                    all_players.append(player)
            return all_players
        
        # Otherwise, sample players based on position and price distribution
        # Group players by position
        players_by_position = {
            Position.FWD: [],
            Position.MID: [],
            Position.DEF: [],
            Position.GK: []
        }
        
        for player_data in all_players_data:
            position = self._get_position_from_fpl_data(player_data)
            if position:
                players_by_position[position].append(player_data)
        
        # Calculate target distribution (similar to real FPL teams)
        total_target = self.sample_size
        targets = {
            Position.FWD: max(1, int(total_target * 0.25)),  # 25% forwards, min 1
            Position.MID: max(1, int(total_target * 0.40)),  # 40% midfielders, min 1
            Position.DEF: max(1, int(total_target * 0.25)),  # 25% defenders, min 1
            Position.GK: max(1, int(total_target * 0.10)),   # 10% goalkeepers, min 1
        }
        
        # Adjust if total exceeds sample_size
        total_allocated = sum(targets.values())
        if total_allocated > total_target:
            # Reduce proportionally, but keep at least 1 per position
            excess = total_allocated - total_target
            positions = list(targets.keys())
            while excess > 0 and any(targets[pos] > 1 for pos in positions):
                for pos in positions:
                    if targets[pos] > 1 and excess > 0:
                        targets[pos] -= 1
                        excess -= 1
        
        sampled_players = []
        
        for position, target_count in targets.items():
            available_players = players_by_position[position]
            
            if len(available_players) <= target_count:
                # Take all available players for this position
                selected_players = available_players
            else:
                # Sample based on price distribution
                selected_players = self._sample_by_price_distribution(available_players, target_count)
            
            # Convert to Player objects
            for player_data in selected_players:
                team_name = team_mapping.get(player_data.get('team'), 'Unknown')
                player = self._create_player_from_fpl_data(player_data, team_name, position)
                sampled_players.append(player)
                logger.info(f"Sampled: {player.name} ({team_name}) - £{player.price:.1f}m")
        
        return sampled_players
    
    def _get_position_from_fpl_data(self, player_data: Dict) -> Position:
        """Convert FPL position code to Position enum"""
        position_code = player_data.get('element_type', 0)
        position_map = {
            1: Position.GK,
            2: Position.DEF, 
            3: Position.MID,
            4: Position.FWD
        }
        return position_map.get(position_code)
    
    def _sample_by_price_distribution(self, players: List[Dict], target_count: int) -> List[Dict]:
        """Sample players ensuring good price distribution"""
        
        if target_count <= 0:
            return []
        
        # Sort by price (descending)
        sorted_players = sorted(players, key=lambda p: p.get('now_cost', 0), reverse=True)
        
        # For very small samples, just take a mix of high and low priced players
        if target_count <= 2:
            if target_count == 1:
                # Take one from the middle
                mid_index = len(sorted_players) // 2
                return [sorted_players[mid_index]]
            else:  # target_count == 2
                # Take one premium, one budget
                return [sorted_players[0], sorted_players[-1]]
        
        # For larger samples, use price distribution
        total = len(sorted_players)
        premium_count = max(1, int(target_count * 0.3))
        budget_count = max(1, int(target_count * 0.3))
        mid_count = target_count - premium_count - budget_count
        
        selected = []
        
        # Add premium players
        selected.extend(sorted_players[:premium_count])
        
        # Add mid-range players
        if mid_count > 0:
            mid_start = total // 3
            mid_end = (total * 2) // 3
            mid_players = sorted_players[mid_start:mid_end]
            if len(mid_players) > 0:
                selected.extend(random.sample(mid_players, min(mid_count, len(mid_players))))
        
        # Add budget players
        if budget_count > 0:
            budget_players = sorted_players[-budget_count:]
            selected.extend(budget_players)
        
        # If we don't have enough, fill with random players
        if len(selected) < target_count:
            remaining = [p for p in players if p not in selected]
            additional_needed = target_count - len(selected)
            if len(remaining) > 0:
                selected.extend(random.sample(remaining, min(additional_needed, len(remaining))))
        
        return selected[:target_count]
    
    def _create_player_from_fpl_data(self, player_data: Dict, team_name: str, position: Position) -> Player:
        """Create Player object from FPL data"""
        
        # Determine price range
        price = player_data.get('now_cost', 0) / 10.0
        if price >= 8.0:
            price_range = "premium"
        elif price >= 5.5:
            price_range = "mid"
        else:
            price_range = "budget"
        
        return Player(
            id=player_data.get('id'),
            name=player_data.get('first_name', '') + ' ' + player_data.get('second_name', ''),
            team_id=player_data.get('team'),
            position=position,
            price=price,
            total_points=player_data.get('total_points', 0),
            form=float(player_data.get('form', 0)),
            points_per_game=float(player_data.get('points_per_game', 0)),
            minutes_played=player_data.get('minutes', 0),
            team_name=team_name,
            selected_by_pct=float(player_data.get('selected_by_percent', 0)),
            price_change=player_data.get('cost_change_event', 0) / 10.0,
            custom_data={
                'price_range': price_range,
                'fpl_id': player_data.get('id'),
                'web_name': player_data.get('web_name', ''),
                'status': player_data.get('status', ''),
                'news': player_data.get('news', ''),
                'expected_goals': float(player_data.get('expected_goals', 0)),
                'expected_assists': float(player_data.get('expected_assists', 0)),
                'influence': float(player_data.get('influence', 0)),
                'creativity': float(player_data.get('creativity', 0)),
                'threat': float(player_data.get('threat', 0)),
                'ict_index': float(player_data.get('ict_index', 0)),
            }
        )
    
    def get_test_teams(self) -> List[Team]:
        """Get teams for the sampled players"""
        logger.info("Fetching test teams...")
        
        try:
            bootstrap_data = self.fpl_fetcher.get_bootstrap_data()
            teams_data = bootstrap_data.get('teams', [])
            
            # Get unique teams from our sampled players
            players = self.get_test_players()
            test_team_ids = set(player.team_id for player in players)
            
            # Create Team objects for test teams
            test_teams = []
            for team_data in teams_data:
                if team_data['id'] in test_team_ids:
                    team = Team(
                        id=team_data.get('id'),
                        name=team_data.get('name'),
                        short_name=team_data.get('short_name'),
                        strength=team_data.get('strength', 0),
                        custom_data={
                            'fpl_id': team_data.get('id'),
                            'code': team_data.get('code'),
                            'strength_overall_home': team_data.get('strength_overall_home', 0),
                            'strength_overall_away': team_data.get('strength_overall_away', 0),
                        }
                    )
                    test_teams.append(team)
                    logger.info(f"Added test team: {team.name}")
            
            logger.info(f"Test teams fetch complete: {len(test_teams)} teams")
            return test_teams
            
        except Exception as e:
            logger.error(f"Error fetching test teams: {e}")
            raise
    
    def get_test_data_summary(self) -> Dict[str, Any]:
        """Get a summary of the test data"""
        players = self.get_test_players()
        teams = self.get_test_teams()
        
        # Group players by position and price range
        position_counts = {}
        price_range_counts = {}
        
        for player in players:
            # Position counts
            pos = player.position.value
            position_counts[pos] = position_counts.get(pos, 0) + 1
            
            # Price range counts
            price_range = player.custom_data.get('price_range', 'unknown')
            price_range_counts[price_range] = price_range_counts.get(price_range, 0) + 1
        
        return {
            'total_players': len(players),
            'total_teams': len(teams),
            'position_distribution': position_counts,
            'price_range_distribution': price_range_counts,
            'players': [p.name for p in players],
            'teams': [t.name for t in teams],
            'fetch_timestamp': datetime.now().isoformat()
        }


def get_test_data(config: Config = None, sample_size: int = 50) -> Dict[str, Any]:
    """Convenience function to get test data"""
    if config is None:
        config = Config()
    
    fetcher = TestDataFetcher(config, sample_size)
    return {
        'players': fetcher.get_test_players(),
        'teams': fetcher.get_test_teams(),
        'summary': fetcher.get_test_data_summary()
    } 