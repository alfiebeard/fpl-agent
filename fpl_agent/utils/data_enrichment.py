"""
Utility functions for enriching player data with analysis, news, and insights.
This extracts data enrichment logic that was previously mixed into LLMStrategy.
"""

import logging
import json
from typing import Dict, List, Any
from datetime import datetime

from ..core.config import Config
from ..core.models import Player
from .player_factory import PlayerFactory
from .fpl_data_manager import FPLDataManager
from ..strategies.team_analysis_strategy import TeamAnalysisStrategy

logger = logging.getLogger(__name__)


class DataEnrichment:
    """
    Utility class for enriching player data with analysis and insights.
    
    This consolidates data enrichment logic that was previously scattered
    throughout the LLMStrategy class.
    """
    
    def __init__(self, config: Config):
        """
        Initialize data enrichment utility.
        
        Args:
            config: FPL configuration object
        """
        self.config = config
        self.player_factory = PlayerFactory()
        self.data_manager = FPLDataManager(config)
        self.team_analysis = TeamAnalysisStrategy(config)
        
        # Initialize FPL data cache once to avoid repeated API calls
        self.team_analysis.initialize_fpl_data()
    
    def enrich_player_data(self, existing_player_data: Dict[str, Dict[str, Any]], 
                          force_refresh: bool = False) -> Dict[str, Dict[str, Any]]:
        """
        Add enrichments to existing basic player data.
        
        This method enriches player data with:
        - Team injury news and analysis
        - Team hints and tips
        - Fixture information
        - Player availability insights
        
        Args:
            existing_player_data: Dictionary of existing player data
            force_refresh: Whether to force refresh of FPL data
            
        Returns:
            Dictionary of enriched player data
        """
        try:
            logger.info("Starting player data enrichment process...")
            
            # Group players by team for efficient analysis
            players_by_team = self._group_players_by_team(existing_player_data)
            
            # Get current gameweek for fixture analysis
            current_gameweek = self.data_manager.get_current_gameweek(force_refresh)
            if current_gameweek is None:
                current_gameweek = 1  # Fallback to GW1 if not available
            
            logger.info(f"Using Gameweek {current_gameweek} for enrichment")
            
            # Get injury news and hints for all teams
            all_injury_news, all_hints_tips = self._get_team_analysis(players_by_team, current_gameweek)
            
            # Enrich individual player data
            enriched_data = self._enrich_individual_players(
                existing_player_data, all_injury_news, all_hints_tips
            )
            
            logger.info(f"Data enrichment completed for {len(enriched_data)} players")
            return enriched_data
            
        except Exception as e:
            logger.error(f"Failed to enrich player data: {e}")
            # Return original data if enrichment fails
            return existing_player_data
    
    def _group_players_by_team(self, player_data: Dict[str, Dict[str, Any]]) -> Dict[str, List[tuple]]:
        """
        Group players by team for efficient analysis.
        
        Args:
            player_data: Dictionary of player data
            
        Returns:
            Dictionary mapping team names to lists of (player_name, player_data) tuples
        """
        players_by_team = {}
        
        for player_name, player_data_item in player_data.items():
            try:
                team_name = player_data_item["data"]["team"]
                if team_name not in players_by_team:
                    players_by_team[team_name] = []
                players_by_team[team_name].append((player_name, player_data_item))
            except KeyError as e:
                logger.warning(f"Missing team data for player {player_name}: {e}")
                continue
        
        logger.info(f"Grouped {len(player_data)} players into {len(players_by_team)} teams")
        return players_by_team
    
    def _get_team_analysis(self, players_by_team: Dict[str, List[tuple]], 
                           current_gameweek: int) -> tuple[Dict[str, str], Dict[str, str]]:
        """
        Get injury news and hints/tips for all teams.
        
        Args:
            players_by_team: Dictionary mapping team names to player lists
            current_gameweek: Current gameweek number
            
        Returns:
            Tuple of (injury_news_dict, hints_tips_dict)
        """
        logger.info("Getting team analysis for all teams...")
        
        all_injury_news = {}
        all_hints_tips = {}
        
        for team_name, team_players in players_by_team.items():
            try:
                # Convert to player objects for LLM strategy
                player_objects = []
                for player_name, player_data in team_players:
                    # Use PlayerFactory instead of the old SimplePlayer class
                    player = self.player_factory.create_simple_player(player_data)
                    player_objects.append(player)
                
                # Get injury news for this team
                injury_news = self.team_analysis.get_team_injury_news(team_name, player_objects)
                all_injury_news[team_name] = injury_news
                
                # Get hints and tips for this team
                hints_tips = self.team_analysis.get_team_hints_tips(team_name, player_objects)
                all_hints_tips[team_name] = hints_tips
                
                logger.info(f"Processed {team_name}: {len(team_players)} players")
                
            except Exception as e:
                logger.error(f"Failed to process {team_name}: {e}")
                # Continue with other teams
                continue
        
        return all_injury_news, all_hints_tips
    
    def _enrich_individual_players(self, existing_player_data: Dict[str, Dict[str, Any]],
                                  all_injury_news: Dict[str, str],
                                  all_hints_tips: Dict[str, str]) -> Dict[str, Dict[str, Any]]:
        """
        Enrich individual player data with team analysis.
        
        Args:
            existing_player_data: Original player data
            all_injury_news: Injury news by team
            all_hints_tips: Hints/tips by team
            
        Returns:
            Dictionary of enriched player data
        """
        enriched_data = {}
        
        for player_name, player_data in existing_player_data.items():
            try:
                # Get player's team injury news and hints
                team_name = player_data["data"]["team"]
                injury_news = all_injury_news.get(team_name, "{}")
                hints_tips = all_hints_tips.get(team_name, "{}")
                
                # Parse JSON responses
                injury_dict = self._parse_json_response(injury_news, f"injury news for {team_name}")
                hints_dict = self._parse_json_response(hints_tips, f"hints/tips for {team_name}")
                
                # Create enriched player data
                enriched_player_data = player_data.copy()
                
                # Add team analysis to player data
                if "enrichments" not in enriched_player_data:
                    enriched_player_data["enrichments"] = {}
                
                enriched_player_data["enrichments"].update({
                    "team_injury_news": injury_dict,
                    "team_hints_tips": hints_dict,
                    "enrichment_timestamp": datetime.now().isoformat()
                })
                
                enriched_data[player_name] = enriched_player_data
                
            except Exception as e:
                logger.error(f"Failed to enrich player {player_name}: {e}")
                # Keep original data if enrichment fails
                enriched_data[player_name] = player_data
        
        return enriched_data
    
    def _parse_json_response(self, response: str, context: str) -> Dict[str, Any]:
        """
        Parse JSON response from LLM with error handling.
        
        Args:
            response: JSON string response from LLM
            context: Context for error messages
            
        Returns:
            Parsed dictionary or empty dict if parsing fails
        """
        if not response:
            return {}
        
        try:
            return json.loads(response)
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse {context}: {e}")
            logger.debug(f"Response content: {response[:200]}...")
            return {}
    
    def get_team_summary(self, team_name: str, players: List[Player]) -> Dict[str, str]:
        """
        Get comprehensive team summary including injury news and hints.
        
        Args:
            team_name: Name of the team
            players: List of Player objects for the team
            
        Returns:
            Dictionary containing team summary information
        """
        try:
            # Get current gameweek for fixture analysis
            current_gameweek = self.data_manager.get_current_gameweek()
            if current_gameweek is None:
                current_gameweek = 1
            
            # Get fixture information
            fixture_info = self.data_manager.get_fixture_info(team_name, current_gameweek)
            
            # Get team analysis
            injury_news = self.team_analysis.get_team_injury_news(team_name, players)
            hints_tips = self.team_analysis.get_team_hints_tips(team_name, players)
            
            # Parse responses
            injury_dict = self._parse_json_response(injury_news, f"injury news for {team_name}")
            hints_dict = self._parse_json_response(hints_tips, f"hints/tips for {team_name}")
            
            return {
                "team_name": team_name,
                "gameweek": current_gameweek,
                "fixture_info": fixture_info,
                "injury_news": injury_dict,
                "hints_tips": hints_dict,
                "summary_timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to get team summary for {team_name}: {e}")
            return {
                "team_name": team_name,
                "error": f"Failed to generate summary: {e}"
            }
    
    def refresh_data(self, force: bool = False) -> None:
        """
        Refresh all data used for enrichment.
        
        Args:
            force: Whether to force refresh even if cache is still valid
        """
        logger.info("Refreshing data for enrichment...")
        
        # Refresh FPL data cache
        self.data_manager.refresh_cache(force=force)
        
        # Reinitialize lightweight LLM strategy data
        self.team_analysis.initialize_fpl_data()
        
        logger.info("Data refresh completed")
    
    def get_enrichment_status(self) -> Dict[str, Any]:
        """
        Get status of enrichment data sources.
        
        Returns:
            Dictionary containing enrichment status information
        """
        return {
            "fpl_data_cache": self.data_manager.get_cache_status(),
            "team_analysis_initialized": hasattr(self.team_analysis, '_cached_bootstrap_data'),
            "enrichment_timestamp": datetime.now().isoformat()
        }
