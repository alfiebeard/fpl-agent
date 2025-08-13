"""
Factory for creating Player objects from different data sources.
This consolidates player creation logic that was previously scattered throughout the codebase.
"""

import logging
from typing import Dict, Any
from ..core.models import Player, Position

logger = logging.getLogger(__name__)


class PlayerFactory:
    """
    Factory class for creating Player objects from various data sources.
    
    This consolidates player creation logic that was previously duplicated
    and fixes the issue of class definitions inside methods.
    """
    
    @staticmethod
    def from_enriched_data(data: Dict[str, Any]) -> Player:
        """
        Create a Player object from enriched FPL data.
        
        Args:
            data: Dictionary containing enriched player data
            
        Returns:
            Player object with all attributes populated
        """
        try:
            # Extract basic info
            player_id = data["data"].get("id", 0)
            first_name = data["data"].get("first_name", "")
            second_name = data["data"].get("second_name", "")
            name = data["data"].get("name", "")
            team_id = data["data"].get("team_id", 0)
            team_name = data["data"].get("team", "")
            team_short_name = data["data"].get("team_short_name", "")
            element_type = data["data"].get("element_type", 0)
            
            # Create position object
            position_value = data["data"].get("position", "")
            position = Position(value=position_value)
            
            # Extract price info
            now_cost = data["data"].get("now_cost", 0)
            price = data["data"].get("price", 0.0)
            cost_change_start = data["data"].get("cost_change_start", 0)
            cost_change_event = data["data"].get("cost_change_event", 0)
            price_change = data["data"].get("price_change", 0.0)
            
            # Extract stats
            total_points = data["data"].get("total_points", 0)
            points_per_game = data["data"].get("points_per_game", 0.0)
            form = data["data"].get("form", 0.0)
            minutes = data["data"].get("minutes", 0)
            selected_by_percent = data["data"].get("selected_by_percent", 0.0)
            
            # Extract expected stats
            xG = data["data"].get("xG", 0.0)
            xA = data["data"].get("xA", 0.0)
            xGC = data["data"].get("xGC", 0.0)
            xMins_pct = data["data"].get("xMins_pct", 0.0)
            
            # Extract injury status
            status = data["data"].get("status", "")
            news = data["data"].get("news", "")
            news_added = data["data"].get("news_added", "")
            chance_of_playing_next_round = data["data"].get("chance_of_playing_next_round", None)
            chance_of_playing_this_round = data["data"].get("chance_of_playing_this_round", None)
            is_injured = data["data"].get("is_injured", False)
            
            # Extract calculated fields
            ppg = data["data"].get("ppg", 0.0)
            form_float = data["data"].get("form_float", 0.0)
            minutes_played = data["data"].get("minutes_played", 0)
            fixture_difficulty = data["data"].get("fixture_difficulty", 3.0)
            ownership_percent = data["data"].get("ownership_percent", 0.0)
            
            # Create custom_data for additional stats
            custom_data = {
                'chance_of_playing': chance_of_playing_this_round,
                'ppg': ppg,
                'form': form_float,
                'minutes_played': minutes_played,
                'upcoming_fixture_difficulty': fixture_difficulty,
                'ownership_percent': ownership_percent
            }
            
            # Create and return Player object
            player = Player(
                id=player_id,
                first_name=first_name,
                second_name=second_name,
                name=name,
                team_id=team_id,
                team_name=team_name,
                team_short_name=team_short_name,
                element_type=element_type,
                position=position,
                now_cost=now_cost,
                price=price,
                cost_change_start=cost_change_start,
                cost_change_event=cost_change_event,
                price_change=price_change,
                total_points=total_points,
                points_per_game=points_per_game,
                form=form,
                minutes=minutes,
                selected_by_percent=selected_by_percent,
                xG=xG,
                xA=xA,
                xGC=xGC,
                xMins_pct=xMins_pct,
                status=status,
                news=news,
                news_added=news_added,
                chance_of_playing_next_round=chance_of_playing_next_round,
                chance_of_playing_this_round=chance_of_playing_this_round,
                is_injured=is_injured,
                ppg=ppg,
                form_float=form_float,
                minutes_played=minutes_played,
                fixture_difficulty=fixture_difficulty,
                ownership_percent=ownership_percent,
                custom_data=custom_data
            )
            
            # Add legacy compatibility attributes
            player.selected_by_pct = selected_by_percent
            player.injury_type = news
            
            return player
            
        except Exception as e:
            logger.error(f"Failed to create Player from enriched data: {e}")
            logger.error(f"Data structure: {data}")
            raise
    
    @staticmethod
    def create_simple_player(data: Dict[str, Any]) -> Player:
        """
        Create a lightweight Player object for analysis purposes.
        
        This replaces the SimplePlayer class that was previously defined
        inside a method (which was terrible design).
        
        Args:
            data: Dictionary containing basic player data
            
        Returns:
            Player object with essential attributes for analysis
        """
        try:
            # Extract essential info for analysis
            player_id = data["data"].get("id", 0)
            name = data["data"].get("name", "")
            team_name = data["data"].get("team", "")
            position_value = data["data"].get("position", "")
            position = Position(value=position_value)
            
            # Basic stats needed for analysis
            total_points = data["data"].get("total_points", 0)
            points_per_game = data["data"].get("points_per_game", 0.0)
            form = data["data"].get("form", 0.0)
            minutes = data["data"].get("minutes", 0)
            selected_by_percent = data["data"].get("selected_by_percent", 0.0)
            
            # Injury and availability info
            status = data["data"].get("status", "")
            news = data["data"].get("news", "")
            chance_of_playing_this_round = data["data"].get("chance_of_playing_this_round", None)
            is_injured = data["data"].get("is_injured", False)
            
            # Create minimal Player object for analysis
            player = Player(
                id=player_id,
                name=name,
                team_name=team_name,
                position=position,
                total_points=total_points,
                points_per_game=points_per_game,
                form=form,
                minutes=minutes,
                selected_by_percent=selected_by_percent,
                status=status,
                news=news,
                chance_of_playing_this_round=chance_of_playing_this_round,
                is_injured=is_injured
            )
            
            return player
            
        except Exception as e:
            logger.error(f"Failed to create simple Player for analysis: {e}")
            logger.error(f"Data structure: {data}")
            raise
    
    @staticmethod
    def from_basic_fpl_data(data: Dict[str, Any]) -> Player:
        """
        Create a Player object from basic FPL API data.
        
        Args:
            data: Dictionary containing basic FPL player data
            
        Returns:
            Player object with basic attributes populated
        """
        try:
            # Extract basic FPL data
            player_id = data.get("id", 0)
            first_name = data.get("first_name", "")
            second_name = data.get("second_name", "")
            name = data.get("name", "")
            team_id = data.get("team", 0)
            element_type = data.get("element_type", 0)
            
            # Get team name from team ID (would need team mapping)
            team_name = f"Team_{team_id}"  # Placeholder
            
            # Create position from element type
            position_map = {1: "GK", 2: "DEF", 3: "MID", 4: "FWD"}
            position_value = position_map.get(element_type, "UNK")
            position = Position(value=position_value)
            
            # Basic stats
            now_cost = data.get("now_cost", 0)
            total_points = data.get("total_points", 0)
            points_per_game = data.get("points_per_game", 0.0)
            form = data.get("form", 0.0)
            minutes = data.get("minutes", 0)
            selected_by_percent = data.get("selected_by_percent", 0.0)
            
            # Create Player object
            player = Player(
                id=player_id,
                first_name=first_name,
                second_name=second_name,
                name=name,
                team_id=team_id,
                team_name=team_name,
                element_type=element_type,
                position=position,
                now_cost=now_cost,
                total_points=total_points,
                points_per_game=points_per_game,
                form=form,
                minutes=minutes,
                selected_by_percent=selected_by_percent
            )
            
            return player
            
        except Exception as e:
            logger.error(f"Failed to create Player from basic FPL data: {e}")
            logger.error(f"Data structure: {data}")
            raise
