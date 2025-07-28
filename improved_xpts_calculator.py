#!/usr/bin/env python3
"""
Improved xPts calculator that addresses the identified issues
"""

from fpl_optimizer.main import FPLOptimizer
from fpl_optimizer.projection.xpts import ExpectedPointsCalculator
from fpl_optimizer.models import Position, Player, Fixture, Team
import pandas as pd

class ImprovedExpectedPointsCalculator(ExpectedPointsCalculator):
    """Improved xPts calculator with better data handling"""
    
    def __init__(self, config):
        super().__init__(config)
        
        # Historical data for better estimates (would come from previous seasons)
        self.historical_data = {
            'yellow_cards_per_90': {
                'DEF': 0.25,  # Average yellow cards per 90 mins for defenders
                'MID': 0.20,  # Average yellow cards per 90 mins for midfielders
                'FWD': 0.15,  # Average yellow cards per 90 mins for forwards
                'GK': 0.05,   # Average yellow cards per 90 mins for goalkeepers
            },
            'red_cards_per_90': {
                'DEF': 0.02,
                'MID': 0.015,
                'FWD': 0.01,
                'GK': 0.005,
            },
            'bonus_points_per_90': {
                'DEF': 0.15,
                'MID': 0.25,
                'FWD': 0.30,
                'GK': 0.10,
            },
            'minutes_per_game': {
                'GK': 0.95,   # Goalkeepers play most games
                'DEF': 0.85,  # Defenders play most games
                'MID': 0.75,  # Midfielders get rotated more
                'FWD': 0.70,  # Forwards get subbed more
            }
        }
        
        # Team-specific data for better estimates
        self.team_rotation_risk = {
            'Man City': 0.8,    # High rotation risk
            'Arsenal': 0.7,     # Medium-high rotation risk
            'Liverpool': 0.7,   # Medium-high rotation risk
            'Chelsea': 0.8,     # High rotation risk
            'Spurs': 0.6,       # Medium rotation risk
            'Man Utd': 0.7,     # Medium-high rotation risk
            'Newcastle': 0.6,   # Medium rotation risk
            'Aston Villa': 0.5, # Lower rotation risk
            'Brighton': 0.7,    # Medium-high rotation risk
            'Brentford': 0.5,   # Lower rotation risk
            'West Ham': 0.5,    # Lower rotation risk
            'Crystal Palace': 0.5,
            'Fulham': 0.5,
            'Wolves': 0.5,
            'Everton': 0.5,
            'Bournemouth': 0.5,
            'Burnley': 0.5,
            'Nott\'m Forest': 0.5,
            'Sunderland': 0.6,  # Newly promoted - might rotate
            'Leeds': 0.6,       # Newly promoted - might rotate
        }
    
    def _calculate_expected_goals(self, player: Player, fixture: Fixture,
                                home_team: Team, away_team: Team) -> float:
        """Calculate expected goals for a player with improved logic"""
        
        # Use player's xG if available, otherwise estimate from position and price
        if player.xG > 0:
            base_xg = player.xG
        else:
            # Improved estimation based on position, price, and historical performance
            if player.position == Position.FWD:
                # Forwards: use price and points per game as indicators
                price_factor = (player.price - 4.5) / 10.0  # 0-1 scale
                ppg_factor = min(player.points_per_game / 10.0, 1.0)  # 0-1 scale
                base_xg = 0.10 + (price_factor * 0.20) + (ppg_factor * 0.15)  # 0.10-0.45 range
            elif player.position == Position.MID:
                # Midfielders: consider attacking vs defensive midfielders
                price_factor = (player.price - 4.5) / 10.0
                ppg_factor = min(player.points_per_game / 10.0, 1.0)
                base_xg = 0.05 + (price_factor * 0.12) + (ppg_factor * 0.10)  # 0.05-0.27 range
            elif player.position == Position.DEF:
                # Defenders: mostly attacking full-backs
                price_factor = (player.price - 4.0) / 6.0
                ppg_factor = min(player.points_per_game / 8.0, 1.0)
                base_xg = 0.01 + (price_factor * 0.04) + (ppg_factor * 0.03)  # 0.01-0.08 range
            else:  # GK
                base_xg = 0.0
        
        # Adjust based on fixture difficulty (opposition consideration)
        if player.team_id == fixture.home_team_id:
            difficulty_factor = (6 - fixture.home_difficulty) / 5.0
        else:
            difficulty_factor = (6 - fixture.away_difficulty) / 5.0
        
        # Adjust based on team attacking strength vs opponent defense
        if player.team_id == fixture.home_team_id:
            team_attack = home_team.xG if home_team else 1.0
            opponent_defense = away_team.xGA if away_team else 1.4
        else:
            team_attack = away_team.xG if away_team else 1.0
            opponent_defense = home_team.xGA if home_team else 1.4
        
        # Team vs opponent factor
        team_factor = (team_attack / opponent_defense) * 0.8 + 0.2  # 0.2-1.8 range
        
        # Calculate final xG
        xg = base_xg * difficulty_factor * team_factor
        
        return max(0.0, xg)
    
    def _calculate_expected_assists(self, player: Player, fixture: Fixture,
                                 home_team: Team, away_team: Team) -> float:
        """Calculate expected assists for a player with improved logic"""
        
        # Use player's xA if available, otherwise estimate
        if player.xA > 0:
            base_xa = player.xA
        else:
            # Improved estimation
            if player.position == Position.MID:
                price_factor = (player.price - 4.5) / 10.0
                ppg_factor = min(player.points_per_game / 10.0, 1.0)
                base_xa = 0.08 + (price_factor * 0.15) + (ppg_factor * 0.12)  # 0.08-0.35 range
            elif player.position == Position.FWD:
                price_factor = (player.price - 4.5) / 10.0
                ppg_factor = min(player.points_per_game / 10.0, 1.0)
                base_xa = 0.05 + (price_factor * 0.08) + (ppg_factor * 0.06)  # 0.05-0.19 range
            elif player.position == Position.DEF:
                price_factor = (player.price - 4.0) / 6.0
                ppg_factor = min(player.points_per_game / 8.0, 1.0)
                base_xa = 0.02 + (price_factor * 0.04) + (ppg_factor * 0.03)  # 0.02-0.09 range
            else:  # GK
                base_xa = 0.0
        
        # Apply same difficulty and team factors as xG
        if player.team_id == fixture.home_team_id:
            difficulty_factor = (6 - fixture.home_difficulty) / 5.0
        else:
            difficulty_factor = (6 - fixture.away_difficulty) / 5.0
        
        if player.team_id == fixture.home_team_id:
            team_attack = home_team.xG if home_team else 1.0
            opponent_defense = away_team.xGA if away_team else 1.4
        else:
            team_attack = away_team.xG if away_team else 1.0
            opponent_defense = home_team.xGA if home_team else 1.4
        
        team_factor = (team_attack / opponent_defense) * 0.8 + 0.2
        
        xa = base_xa * difficulty_factor * team_factor
        
        return max(0.0, xa)
    
    def _calculate_clean_sheet_probability(self, player: Player, fixture: Fixture,
                                         home_team: Team, away_team: Team) -> float:
        """Calculate clean sheet probability with player-specific adjustments"""
        
        # Only defenders and goalkeepers can get clean sheet points
        if player.position not in [Position.DEF, Position.GK]:
            return 0.0
        
        # Base clean sheet probability from team defense vs opponent attack
        if player.team_id == fixture.home_team_id:
            team_defense = home_team.xGA if home_team else 1.5
            opponent_attack = away_team.xG if away_team else 1.5
        else:
            team_defense = away_team.xGA if away_team else 1.5
            opponent_attack = home_team.xG if home_team else 1.5
        
        # Calculate base clean sheet probability
        base_cs_prob = max(0.0, 0.4 - (team_defense * 0.1) - (opponent_attack * 0.1))
        
        # Adjust based on fixture difficulty
        if player.team_id == fixture.home_team_id:
            difficulty_factor = (6 - fixture.home_difficulty) / 5.0
        else:
            difficulty_factor = (6 - fixture.away_difficulty) / 5.0
        
        # Player-specific adjustments based on position and role
        if player.position == Position.GK:
            # Goalkeepers get full CS probability
            player_factor = 1.0
        elif player.position == Position.DEF:
            # Defenders get CS probability based on their role
            # Higher price usually means more attacking, less defensive focus
            if player.price >= 6.0:
                player_factor = 0.8  # Attacking full-backs
            elif player.price >= 5.0:
                player_factor = 0.9  # Regular defenders
            else:
                player_factor = 1.0  # Cheap defenders (more defensive)
        
        cs_prob = base_cs_prob * difficulty_factor * player_factor
        
        return max(0.0, min(1.0, cs_prob))
    
    def _calculate_bonus_probability(self, player: Player, xG_pred: float, xA_pred: float) -> float:
        """Calculate bonus points probability with improved logic"""
        
        # Base bonus probability from attacking contribution
        attacking_contribution = xG_pred + xA_pred
        base_bonus_prob = min(0.3, attacking_contribution * 0.2)
        
        # Add position-specific bonus probability
        position_bonus = self.historical_data['bonus_points_per_90'].get(player.position.value, 0.2)
        position_factor = position_bonus / 0.25  # Normalize to 0.25 baseline
        
        # Add player-specific factor based on points per game
        ppg_factor = min(player.points_per_game / 8.0, 1.5)  # Players with high PPG get more bonus
        
        bonus_prob = base_bonus_prob * position_factor * ppg_factor
        
        return max(0.0, min(1.0, bonus_prob))
    
    def _calculate_yellow_card_probability(self, player: Player, fixture: Fixture) -> float:
        """Calculate yellow card probability with opponent consideration"""
        
        # Base yellow card probability from historical data
        base_yc_prob = self.historical_data['yellow_cards_per_90'].get(player.position.value, 0.15)
        
        # Convert per-90 to per-game probability
        base_yc_prob = base_yc_prob * 0.9  # Assume 90% of games played
        
        # Adjust based on player's historical cards (if available)
        historical_cards = player.custom_data.get('yellow_cards', 3)
        historical_factor = 1.0 + (historical_cards - 3) * 0.1
        
        # Adjust based on fixture difficulty (harder games = more cards)
        if player.team_id == fixture.home_team_id:
            difficulty_factor = 1.0 + (fixture.home_difficulty - 3) * 0.1
        else:
            difficulty_factor = 1.0 + (fixture.away_difficulty - 3) * 0.1
        
        # Opponent-specific adjustment (some teams get more cards against them)
        opponent_team = fixture.away_team_name if player.team_id == fixture.home_team_id else fixture.home_team_name
        opponent_factor = self._get_opponent_card_factor(opponent_team)
        
        yc_prob = base_yc_prob * historical_factor * difficulty_factor * opponent_factor
        
        return max(0.0, min(1.0, yc_prob))
    
    def _calculate_red_card_probability(self, player: Player, fixture: Fixture) -> float:
        """Calculate red card probability with opponent consideration"""
        
        # Base red card probability
        base_rc_prob = self.historical_data['red_cards_per_90'].get(player.position.value, 0.02)
        base_rc_prob = base_rc_prob * 0.9  # Convert to per-game
        
        # Adjust based on player's historical cards
        historical_cards = player.custom_data.get('red_cards', 0)
        historical_factor = 1.0 + historical_cards * 0.5
        
        # Adjust based on fixture difficulty
        if player.team_id == fixture.home_team_id:
            difficulty_factor = 1.0 + (fixture.home_difficulty - 3) * 0.1
        else:
            difficulty_factor = 1.0 + (fixture.away_difficulty - 3) * 0.1
        
        # Opponent-specific adjustment
        opponent_team = fixture.away_team_name if player.team_id == fixture.home_team_id else fixture.home_team_name
        opponent_factor = self._get_opponent_card_factor(opponent_team)
        
        rc_prob = base_rc_prob * historical_factor * difficulty_factor * opponent_factor
        
        return max(0.0, min(1.0, rc_prob))
    
    def _calculate_expected_minutes(self, player: Player, fixture: Fixture) -> float:
        """Calculate expected playing time with improved logic"""
        
        # Start with position-based base minutes
        base_minutes = self.historical_data['minutes_per_game'].get(player.position.value, 0.8)
        
        # Adjust based on player price (more expensive = more likely to play)
        price_factor = min(player.price / 8.0, 1.2)  # Cap at 1.2x
        
        # Adjust based on team rotation risk
        team_rotation = self.team_rotation_risk.get(player.team_name, 0.6)
        rotation_factor = 1.0 - (team_rotation * 0.2)  # Higher rotation risk = lower minutes
        
        # Adjust based on fixture difficulty (easier games = more rotation)
        if player.team_id == fixture.home_team_id:
            difficulty_factor = 1.0 + (3 - fixture.home_difficulty) * 0.05
        else:
            difficulty_factor = 1.0 + (3 - fixture.away_difficulty) * 0.05
        
        # Adjust based on injury status
        if player.is_injured:
            if player.injury_expected_return and fixture.kickoff_time and player.injury_expected_return > fixture.kickoff_time:
                return 0.0  # Won't be available
            else:
                base_minutes *= 0.5  # Doubtful
        
        # Calculate final minutes
        minutes = base_minutes * price_factor * rotation_factor * difficulty_factor
        
        return max(0.0, min(1.0, minutes))
    
    def _get_opponent_card_factor(self, opponent_team: str) -> float:
        """Get card factor based on opponent team"""
        # Some teams historically get more cards against them
        high_card_teams = {
            'Man City': 1.2,    # Teams that dominate possession
            'Arsenal': 1.1,     # Teams that play attacking football
            'Liverpool': 1.1,
            'Spurs': 1.1,
            'Chelsea': 1.1,
            'Man Utd': 1.1,
        }
        
        return high_card_teams.get(opponent_team, 1.0)

def test_improved_calculator():
    """Test the improved calculator"""
    
    print("🧪 Testing Improved xPts Calculator")
    print("=" * 50)
    
    # Initialize
    optimizer = FPLOptimizer()
    data = optimizer._fetch_all_data()
    processed_data = optimizer._process_data(data)
    
    # Create improved calculator
    calculator = ImprovedExpectedPointsCalculator(optimizer.config)
    
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
                    # Calculate components
                    xg = calculator._calculate_expected_goals(player, fixture, home_team, away_team)
                    xa = calculator._calculate_expected_assists(player, fixture, home_team, away_team)
                    cs_prob = calculator._calculate_clean_sheet_probability(player, fixture, home_team, away_team)
                    bonus_prob = calculator._calculate_bonus_probability(player, xg, xa)
                    yc_prob = calculator._calculate_yellow_card_probability(player, fixture)
                    rc_prob = calculator._calculate_red_card_probability(player, fixture)
                    xmins = calculator._calculate_expected_minutes(player, fixture)
                    
                    print(f"  xG: {xg:.4f}")
                    print(f"  xA: {xa:.4f}")
                    print(f"  CS prob: {cs_prob:.4f}")
                    print(f"  Bonus prob: {bonus_prob:.4f}")
                    print(f"  YC prob: {yc_prob:.4f}")
                    print(f"  RC prob: {rc_prob:.4f}")
                    print(f"  Minutes: {xmins:.4f}")

if __name__ == "__main__":
    test_improved_calculator() 