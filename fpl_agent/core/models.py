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
class FPLTeam:
    """User's FPL team model"""
    
    # Team info
    team_id: int
    team_name: str
    manager_name: str
    
    # Current squad
    players: List[Dict[str, Any]] = field(default_factory=list)
    captain_id: Optional[int] = None
    vice_captain_id: Optional[int] = None
    
    # Formation
    formation: List[int] = field(default_factory=lambda: FPLTeam.get_default_formation())  # [def, mid, fwd]
    
    # Budget
    total_value: float = field(default_factory=lambda: FPLTeam.get_default_budget())
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
    
    def get_players_by_position(self, position: str) -> List[Dict[str, Any]]:
        """Get all players of a specific position"""
        return [p for p in self.players if p.get('position') == position]
    
    def get_starting_11(self) -> List[Dict[str, Any]]:
        """Get the starting 11 based on current formation"""
        if len(self.formation) != 3:
            raise ValueError("Formation must have 3 elements [def, mid, fwd]")
        
        def_players = self.get_players_by_position('DEF')
        mid_players = self.get_players_by_position('MID')
        fwd_players = self.get_players_by_position('FWD')
        
        # Sort by form/points and take top players for each position
        def_players.sort(key=lambda p: float(p.get('form', 0)), reverse=True)
        mid_players.sort(key=lambda p: float(p.get('form', 0)), reverse=True)
        fwd_players.sort(key=lambda p: float(p.get('form', 0)), reverse=True)
        
        starting_11 = []
        starting_11.extend(def_players[:self.formation[0]])
        starting_11.extend(mid_players[:self.formation[1]])
        starting_11.extend(fwd_players[:self.formation[2]])
        
        return starting_11
    
    def get_bench(self) -> List[Dict[str, Any]]:
        """Get bench players (all players not in starting 11)"""
        starting_11 = self.get_starting_11()
        starting_ids = {p.get('id') for p in starting_11}
        return [p for p in self.players if p.get('id') not in starting_ids]
    
    def get_captain(self) -> Optional[Dict[str, Any]]:
        """Get the captain player"""
        if self.captain_id is None:
            return None
        return next((p for p in self.players if p.get('id') == self.captain_id), None)
    
    def get_vice_captain(self) -> Optional[Dict[str, Any]]:
        """Get the vice captain player"""
        if self.vice_captain_id is None:
            return None
        return next((p for p in self.players if p.get('id') == self.vice_captain_id), None)
    
    def add_player(self, player: Dict[str, Any]) -> None:
        """Add a player to the team"""
        self.players.append(player)
    
    def get_total_cost(self) -> float:
        """Calculate total team cost"""
        return sum(float(p.get('price', 0)) for p in self.players)
    
    def get_team_summary(self) -> Dict[str, Any]:
        """Get a summary of the team"""
        return {
            'team_id': self.team_id,
            'team_name': self.team_name,
            'manager_name': self.manager_name,
            'total_players': len(self.players),
            'total_value': self.get_total_cost(),
            'bank': self.bank,
            'formation': self.formation,
            'captain': self.get_captain(),
            'vice_captain': self.get_vice_captain(),
            'chips_used': [chip.value for chip in self.chips_used],
            'chips_remaining': [chip.value for chip in self.chips_remaining],
            'free_transfers': self.free_transfers,
            'total_points': self.total_points,
            'overall_rank': self.overall_rank
        }
    
    @staticmethod
    def get_default_formation() -> List[int]:
        """Get default formation [def, mid, fwd]"""
        return [4, 4, 2]
    
    @staticmethod
    def get_default_budget() -> float:
        """Get default budget"""
        return 100.0 