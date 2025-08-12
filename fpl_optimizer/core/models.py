"""
Core data models for FPL Optimizer
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from enum import Enum


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
    """Player model with all relevant FPL data - aligned with FPL API structure"""
    
    # Basic info (FPL API fields)
    id: int
    first_name: str
    second_name: str
    team_id: int
    element_type: int  # 1=GK, 2=DEF, 3=MID, 4=FWD
    now_cost: int  # Price in tenths (e.g., 55 = £5.5m)
    
    # Stats (FPL API fields)
    total_points: int = 0
    form: str = "0.0"  # Form over last 5 gameweeks
    points_per_game: str = "0.0"
    minutes: int = 0
    selected_by_percent: str = "0.0"
    
    # Expected stats (FPL API fields)
    xG: str = "0.00"
    xA: str = "0.00"
    xGC: str = "0.00"  # Expected goals conceded (for defenders/GKs)
    xMins_pct: float = 1.0  # Expected playing time percentage
    
    # Injury status (FPL API fields)
    status: str = "a"  # a=available, i=injured, s=suspended, u=unavailable
    news: str = ""  # Injury/news information
    news_added: Optional[str] = None  # When news was last updated
    chance_of_playing_next_round: Optional[int] = None  # Chance of playing next gameweek (%)
    chance_of_playing_this_round: Optional[int] = None  # Chance of playing this gameweek (%)
    
    # Price changes (FPL API fields)
    cost_change_start: int = 0  # Price change since start of season (in tenths)
    cost_change_event: int = 0  # Price change this gameweek (in tenths)
    
    # Team info (derived from team_id)
    team_name: str = ""
    team_short_name: str = ""
    
    # Position enum (derived from element_type)
    position: Optional[Position] = None
    
    # Custom fields for additional data
    custom_data: Dict[str, Any] = field(default_factory=dict)
    
    # Computed properties
    @property
    def name(self) -> str:
        """Full player name"""
        return f"{self.first_name} {self.second_name}"
    
    @property
    def price(self) -> float:
        """Current price in millions"""
        return self.now_cost / 10.0
    
    @property
    def price_change(self) -> float:
        """Price change since start of season in millions"""
        return self.cost_change_start / 10.0
    
    @property
    def is_injured(self) -> bool:
        """Check if player is injured"""
        return self.status == 'i'
    
    @property
    def is_available(self) -> bool:
        """Check if player is available to play"""
        return self.status == 'a'
    
    @property
    def value_for_money(self) -> float:
        """Calculate value for money (points per million)"""
        if self.price <= 0:
            return 0.0
        return float(self.points_per_game) / self.price

    def __post_init__(self):
        """Set derived fields after initialization"""
        # Set position enum from element_type
        position_map = {1: Position.GK, 2: Position.DEF, 3: Position.MID, 4: Position.FWD}
        self.position = position_map.get(self.element_type, Position.MID)


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