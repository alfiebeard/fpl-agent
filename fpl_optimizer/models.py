"""
Core data models for FPL Optimizer
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from enum import Enum
from datetime import datetime, timedelta


class Position(Enum):
    """Player positions"""
    GK = "GK"
    DEF = "DEF"
    MID = "MID"
    FWD = "FWD"


class ChipType(Enum):
    """FPL chip types"""
    WILDCARD = "wildcard"
    FREE_HIT = "free_hit"
    TRIPLE_CAPTAIN = "triple_captain"
    BENCH_BOOST = "bench_boost"


@dataclass
class Player:
    """Player model with all relevant FPL data"""
    
    # Basic info
    id: int
    name: str
    team_id: int
    position: Position
    price: float  # Current price in millions
    
    # Stats
    total_points: int = 0
    form: float = 0.0  # Form over last 5 gameweeks
    points_per_game: float = 0.0
    
    # Expected stats
    xG: float = 0.0
    xA: float = 0.0
    xGC: float = 0.0  # Expected goals conceded (for defenders/GKs)
    
    # Playing time
    minutes_played: int = 0
    xMins_pct: float = 1.0  # Expected playing time percentage
    
    # Injury status
    is_injured: bool = False
    injury_expected_return: Optional[datetime] = None
    injury_type: Optional[str] = None
    
    # Team info
    team_name: str = ""
    team_short_name: str = ""
    
    # Price changes
    price_change: float = 0.0
    selected_by_pct: float = 0.0
    
    # Custom fields
    custom_data: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Convert position string to enum if needed"""
        if isinstance(self.position, str):
            self.position = Position(self.position)
    
    @property
    def is_available(self) -> bool:
        """Check if player is available to play"""
        if not self.is_injured:
            return True
        
        if self.injury_expected_return is None:
            return False
        
        return datetime.now() >= self.injury_expected_return
    
    @property
    def value_for_money(self) -> float:
        """Calculate value for money (points per million)"""
        if self.price <= 0:
            return 0.0
        return self.points_per_game / self.price
    
    def get_expected_points(self, gameweek: int, config: 'Config') -> float:
        """Calculate expected points for a specific gameweek"""
        # This will be implemented in the xPts module
        # For now, return a placeholder
        return self.points_per_game


@dataclass
class Team:
    """Team model"""
    
    id: int
    name: str
    short_name: str
    strength: int = 0  # Team strength rating
    form: float = 0.0  # Recent form
    xG: float = 0.0  # Expected goals scored
    xGA: float = 0.0  # Expected goals conceded
    
    # Custom fields
    custom_data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Fixture:
    """Fixture model"""
    
    id: int
    gameweek: int
    home_team_id: int
    away_team_id: int
    home_team_name: str = ""
    away_team_name: str = ""
    
    # Fixture difficulty
    difficulty: int = 3  # 1-5 scale
    home_difficulty: int = 3
    away_difficulty: int = 3
    
    # Match details
    kickoff_time: Optional[datetime] = None
    is_finished: bool = False
    home_score: Optional[int] = None
    away_score: Optional[int] = None
    
    # Expected stats
    expected_goals: float = 2.5
    home_win_prob: float = 0.33
    draw_prob: float = 0.25
    away_win_prob: float = 0.42
    
    # Custom fields
    custom_data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Gameweek:
    """Gameweek model"""
    
    id: int
    name: str
    deadline_time: datetime
    is_finished: bool = False
    is_current: bool = False
    is_next: bool = False
    
    # Fixtures in this gameweek
    fixtures: List[Fixture] = field(default_factory=list)
    
    # Custom fields
    custom_data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class FPLTeam:
    """User's FPL team model"""
    
    # Team info
    team_id: int
    team_name: str
    manager_name: str
    
    # Current squad
    players: List[Player] = field(default_factory=list)
    captain_id: Optional[int] = None
    vice_captain_id: Optional[int] = None
    
    # Formation
    formation: List[int] = field(default_factory=lambda: [3, 4, 3])  # [def, mid, fwd]
    
    # Budget
    total_value: float = 100.0
    bank: float = 0.0
    
    # Chips
    chips_used: List[ChipType] = field(default_factory=list)
    chips_remaining: List[ChipType] = field(default_factory=list)
    
    # Transfers
    free_transfers: int = 1
    transfer_hits: int = 0
    
    # Performance
    total_points: int = 0
    overall_rank: Optional[int] = None
    
    # Custom fields
    custom_data: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Initialize chips if not set"""
        if not self.chips_remaining:
            self.chips_remaining = [
                ChipType.WILDCARD,
                ChipType.FREE_HIT,
                ChipType.TRIPLE_CAPTAIN,
                ChipType.BENCH_BOOST
            ]
    
    def get_players_by_position(self, position: Position) -> List[Player]:
        """Get all players of a specific position"""
        return [p for p in self.players if p.position == position]
    
    def get_starting_11(self) -> List[Player]:
        """Get the starting 11 based on current formation"""
        if len(self.formation) != 3:
            raise ValueError("Formation must have 3 elements [def, mid, fwd]")
        
        def_players = self.get_players_by_position(Position.DEF)
        mid_players = self.get_players_by_position(Position.MID)
        fwd_players = self.get_players_by_position(Position.FWD)
        
        # Sort by form/points and take top players for each position
        def_players.sort(key=lambda p: p.form, reverse=True)
        mid_players.sort(key=lambda p: p.form, reverse=True)
        fwd_players.sort(key=lambda p: p.form, reverse=True)
        
        starting_11 = []
        starting_11.extend(def_players[:self.formation[0]])
        starting_11.extend(mid_players[:self.formation[1]])
        starting_11.extend(fwd_players[:self.formation[2]])
        
        return starting_11
    
    def get_bench(self) -> List[Player]:
        """Get bench players"""
        starting_11 = self.get_starting_11()
        return [p for p in self.players if p not in starting_11]
    
    def get_captain(self) -> Optional[Player]:
        """Get captain player"""
        if self.captain_id is None:
            return None
        return next((p for p in self.players if p.id == self.captain_id), None)
    
    def get_vice_captain(self) -> Optional[Player]:
        """Get vice captain player"""
        if self.vice_captain_id is None:
            return None
        return next((p for p in self.players if p.id == self.vice_captain_id), None)


@dataclass
class Transfer:
    """Transfer model"""
    
    player_out: Player
    player_in: Player
    gameweek: int
    cost: int = 0  # Transfer hit cost
    reason: str = ""
    
    # Custom fields
    custom_data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class OptimizationResult:
    """Result of team optimization"""
    
    # Selected players
    selected_players: List[Player] = field(default_factory=list)
    
    # Team changes
    transfers: List[Transfer] = field(default_factory=list)
    captain_id: Optional[int] = None
    vice_captain_id: Optional[int] = None
    formation: List[int] = field(default_factory=lambda: [3, 4, 3])
    
    # Team financial info
    team_value: float = 100.0
    bank_balance: float = 0.0
    
    # Expected performance
    expected_points: float = 0.0
    expected_points_next_5: float = 0.0
    
    # Confidence
    confidence: float = 0.0  # 0-1 scale
    
    # Reasoning
    reasoning: str = ""
    llm_insights: str = ""
    
    # Custom fields
    custom_data: Dict[str, Any] = field(default_factory=dict) 