"""
Utility functions for extracting keyword-based status and bonuses from text fields.
Used by both DataProcessor and EmbeddingFilter to avoid code duplication.
"""

import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


def extract_keyword_status(player_name: str, structured_data: Dict, 
                          field_name: str, keyword_map: Dict[str, Any]) -> Any:
    """
    Extract keyword status from the first keyword before the dash.
    
    Args:
        player_name: Name of the player to extract data for
        structured_data: Dictionary containing player data
        field_name: Field name to extract from (e.g., 'injury_news', 'expert_insights')
        keyword_map: Mapping of keywords to return values
        
    Returns:
        The mapped value if keyword found, None otherwise
    """
    try:
        if player_name in structured_data:
            field_text = structured_data[player_name].get(field_name, '')
            if field_text and ' - ' in field_text:  # Look for space-dash-space
                # Split on first occurrence of " - " (space-dash-space)
                first_part = field_text.split(' - ', 1)[0].strip().lower()
                
                # Look for exact keyword match in the first part
                for keyword, value in keyword_map.items():
                    if first_part == keyword.lower():
                        return value
        
        return None  # Default if no keyword found
        
    except Exception as e:
        logger.warning(f"Failed to extract keyword status for {player_name}: {e}")
        return None


def extract_injury_status(player_name: str, structured_data: Dict) -> str:
    """
    Extract injury status from injury_news - only care about 'Out'.
    
    Args:
        player_name: Name of the player
        structured_data: Dictionary containing player data
        
    Returns:
        'out' if player is marked as out, None otherwise
    """
    status_map = {
        "out": "out"  # Only filter out "Out" players
    }
    return extract_keyword_status(player_name, structured_data, 'injury_news', status_map)


def extract_expert_bonus(player_name: str, structured_data: Dict) -> float:
    """
    Extract keyword bonus from expert_insights.
    
    Args:
        player_name: Name of the player
        structured_data: Dictionary containing player data
        
    Returns:
        Float bonus value based on expert keywords, 0.0 if no match
    """
    keyword_map = {
        "must-have": 0.5,
        "recommended": 0.3,
        "rotation risk": -0.2,
        "avoid": -0.5
    }
    result = extract_keyword_status(player_name, structured_data, 'expert_insights', keyword_map)
    return result if result is not None else 0.0
