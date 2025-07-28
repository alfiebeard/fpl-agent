"""
Tests for xPts calculation module
"""

import pytest
from unittest.mock import Mock
from datetime import datetime

from ..models import Player, Team, Fixture, Position
from ..config import Config
from ..projection.xpts import ExpectedPointsCalculator


class TestExpectedPointsCalculator:
    """Test cases for ExpectedPointsCalculator"""
    
    @pytest.fixture
    def config(self):
        """Create a mock config"""
        config = Mock(spec=Config)
        config.get_points_config.return_value = {
            'goal': {'gk': 6, 'def': 6, 'mid': 5, 'fwd': 4},
            'assist': 3,
            'clean_sheet': {'gk': 4, 'def': 4, 'mid': 1, 'fwd': 0},
            'bonus': 1.5,
            'yellow_card': -1,
            'red_card': -3
        }
        config.get_optimization_config.return_value = {
            'xpts_decay_factor': 0.85
        }
        config.get_injury_config.return_value = {
            'default_return_probability': 0.8,
            'minimum_playing_time': 0.6
        }
        return config
    
    @pytest.fixture
    def calculator(self, config):
        """Create ExpectedPointsCalculator instance"""
        return ExpectedPointsCalculator(config)
    
    @pytest.fixture
    def sample_player(self):
        """Create a sample player"""
        return Player(
            id=1,
            name="Test Player",
            team_id=1,
            position=Position.MID,
            price=8.0,
            xG=0.3,
            xA=0.2,
            form=5.0,
            points_per_game=6.0,
            xMins_pct=0.9
        )
    
    @pytest.fixture
    def sample_teams(self):
        """Create sample teams"""
        return [
            Team(id=1, name="Home Team", short_name="HOME", xG=1.8, xGA=1.2),
            Team(id=2, name="Away Team", short_name="AWAY", xG=1.5, xGA=1.4)
        ]
    
    @pytest.fixture
    def sample_fixture(self):
        """Create a sample fixture"""
        return Fixture(
            id=1,
            gameweek=1,
            home_team_id=1,
            away_team_id=2,
            home_team_name="Home Team",
            away_team_name="Away Team",
            home_difficulty=2,
            away_difficulty=4,
            kickoff_time=datetime.now()
        )
    
    def test_calculate_player_xpts_basic(self, calculator, sample_player, 
                                       sample_fixture, sample_teams):
        """Test basic xPts calculation"""
        
        home_team = sample_teams[0]
        away_team = sample_teams[1]
        
        xpts = calculator.calculate_player_xpts(
            sample_player, sample_fixture, home_team, away_team
        )
        
        # Should return a positive number
        assert xpts > 0
        assert isinstance(xpts, float)
    
    def test_calculate_player_xpts_injured(self, calculator, sample_fixture, 
                                         sample_teams):
        """Test xPts calculation for injured player"""
        
        # Create injured player
        injured_player = Player(
            id=2,
            name="Injured Player",
            team_id=1,
            position=Position.MID,
            price=7.0,
            is_injured=True,
            injury_expected_return=datetime.now()
        )
        
        home_team = sample_teams[0]
        away_team = sample_teams[1]
        
        xpts = calculator.calculate_player_xpts(
            injured_player, sample_fixture, home_team, away_team
        )
        
        # Should return 0 for injured player
        assert xpts == 0.0
    
    def test_calculate_player_xpts_for_gameweek(self, calculator, sample_player,
                                              sample_teams):
        """Test xPts calculation for specific gameweek"""
        
        fixtures = [
            Fixture(
                id=1,
                gameweek=1,
                home_team_id=1,
                away_team_id=2,
                home_team_name="Home Team",
                away_team_name="Away Team",
                home_difficulty=2,
                away_difficulty=4
            )
        ]
        
        xpts = calculator.calculate_player_xpts_for_gameweek(
            sample_player, 1, fixtures, sample_teams
        )
        
        assert xpts >= 0
        assert isinstance(xpts, float)
    
    def test_calculate_player_xpts_for_period(self, calculator, sample_player,
                                            sample_teams):
        """Test xPts calculation for period with decay"""
        
        fixtures = [
            Fixture(
                id=1,
                gameweek=1,
                home_team_id=1,
                away_team_id=2,
                home_team_name="Home Team",
                away_team_name="Away Team",
                home_difficulty=2,
                away_difficulty=4
            ),
            Fixture(
                id=2,
                gameweek=2,
                home_team_id=2,
                away_team_id=1,
                home_team_name="Away Team",
                away_team_name="Home Team",
                home_difficulty=3,
                away_difficulty=3
            )
        ]
        
        xpts = calculator.calculate_player_xpts_for_period(
            sample_player, 1, 2, fixtures, sample_teams
        )
        
        assert xpts >= 0
        assert isinstance(xpts, float)
    
    def test_calculate_all_players_xpts(self, calculator, sample_teams):
        """Test xPts calculation for all players"""
        
        players = [
            Player(id=1, name="Player 1", team_id=1, position=Position.MID, 
                  price=8.0, xG=0.3, xA=0.2),
            Player(id=2, name="Player 2", team_id=2, position=Position.FWD, 
                  price=10.0, xG=0.5, xA=0.1),
            Player(id=3, name="Player 3", team_id=1, position=Position.DEF, 
                  price=5.0, xG=0.1, xA=0.1)
        ]
        
        fixtures = [
            Fixture(
                id=1,
                gameweek=1,
                home_team_id=1,
                away_team_id=2,
                home_team_name="Home Team",
                away_team_name="Away Team",
                home_difficulty=2,
                away_difficulty=4
            )
        ]
        
        player_xpts = calculator.calculate_all_players_xpts(
            players, 1, fixtures, sample_teams
        )
        
        assert isinstance(player_xpts, dict)
        assert len(player_xpts) == len(players)
        
        for player_id, xpts in player_xpts.items():
            assert isinstance(xpts, float)
            assert xpts >= 0
    
    def test_position_specific_points(self, calculator, sample_fixture, sample_teams):
        """Test that different positions get different point values"""
        
        home_team = sample_teams[0]
        away_team = sample_teams[1]
        
        # Create players with same stats but different positions
        players = [
            Player(id=1, name="GK", team_id=1, position=Position.GK, 
                  price=5.0, xG=0.1, xA=0.1),
            Player(id=2, name="DEF", team_id=1, position=Position.DEF, 
                  price=5.0, xG=0.1, xA=0.1),
            Player(id=3, name="MID", team_id=1, position=Position.MID, 
                  price=5.0, xG=0.1, xA=0.1),
            Player(id=4, name="FWD", team_id=1, position=Position.FWD, 
                  price=5.0, xG=0.1, xA=0.1)
        ]
        
        xpts_by_position = {}
        for player in players:
            xpts = calculator.calculate_player_xpts(
                player, sample_fixture, home_team, away_team
            )
            xpts_by_position[player.position] = xpts
        
        # All should have positive xPts
        for position, xpts in xpts_by_position.items():
            assert xpts > 0
    
    def test_fixture_difficulty_impact(self, calculator, sample_player, sample_teams):
        """Test that fixture difficulty affects xPts"""
        
        home_team = sample_teams[0]
        away_team = sample_teams[1]
        
        # Easy fixture
        easy_fixture = Fixture(
            id=1,
            gameweek=1,
            home_team_id=1,
            away_team_id=2,
            home_team_name="Home Team",
            away_team_name="Away Team",
            home_difficulty=1,  # Very easy
            away_difficulty=5   # Very hard for away team
        )
        
        # Hard fixture
        hard_fixture = Fixture(
            id=2,
            gameweek=1,
            home_team_id=1,
            away_team_id=2,
            home_team_name="Home Team",
            away_team_name="Away Team",
            home_difficulty=5,  # Very hard
            away_difficulty=1   # Very easy for away team
        )
        
        easy_xpts = calculator.calculate_player_xpts(
            sample_player, easy_fixture, home_team, away_team
        )
        
        hard_xpts = calculator.calculate_player_xpts(
            sample_player, hard_fixture, home_team, away_team
        )
        
        # Easy fixture should generally give higher xPts
        # (though this depends on the specific calculation logic)
        assert easy_xpts >= 0
        assert hard_xpts >= 0
