"""
Insights extraction functionality for FPL Optimizer
"""

from typing import Dict, List, Optional, Any
import json
import re
from ..models import Player


class InsightsExtractor:
    """Extracts actionable insights from LLM responses"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
    
    def extract_player_insights(self, llm_response: str) -> Dict[str, Any]:
        """Extract player-specific insights from LLM response"""
        insights = {
            "player_recommendations": [],
            "injury_updates": [],
            "form_insights": [],
            "fixture_insights": []
        }
        
        try:
            # Try to parse as JSON first
            data = json.loads(llm_response)
            if isinstance(data, dict):
                insights.update(data)
        except json.JSONDecodeError:
            # Fall back to text parsing
            insights = self._parse_text_insights(llm_response)
        
        return insights
    
    def extract_team_insights(self, llm_response: str) -> Dict[str, Any]:
        """Extract team-specific insights from LLM response"""
        insights = {
            "team_recommendations": [],
            "formation_insights": [],
            "tactical_insights": []
        }
        
        try:
            data = json.loads(llm_response)
            if isinstance(data, dict):
                insights.update(data)
        except json.JSONDecodeError:
            insights = self._parse_text_insights(llm_response)
        
        return insights
    
    def extract_fixture_insights(self, llm_response: str) -> Dict[str, Any]:
        """Extract fixture-specific insights from LLM response"""
        insights = {
            "fixture_recommendations": [],
            "difficulty_adjustments": [],
            "weather_insights": []
        }
        
        try:
            data = json.loads(llm_response)
            if isinstance(data, dict):
                insights.update(data)
        except json.JSONDecodeError:
            insights = self._parse_text_insights(llm_response)
        
        return insights
    
    def _parse_text_insights(self, text: str) -> Dict[str, Any]:
        """Parse insights from unstructured text"""
        insights = {
            "player_recommendations": [],
            "injury_updates": [],
            "form_insights": [],
            "fixture_insights": []
        }
        
        # Simple keyword-based parsing
        lines = text.split('\n')
        for line in lines:
            line = line.strip().lower()
            
            if 'recommend' in line or 'pick' in line:
                insights["player_recommendations"].append(line)
            elif 'injury' in line or 'out' in line or 'doubt' in line:
                insights["injury_updates"].append(line)
            elif 'form' in line or 'playing' in line or 'minutes' in line:
                insights["form_insights"].append(line)
            elif 'fixture' in line or 'difficulty' in line:
                insights["fixture_insights"].append(line)
        
        return insights
    
    def apply_insights_to_xpts(self, player_xpts: Dict[int, float], 
                             insights: Dict[str, Any]) -> Dict[int, float]:
        """Apply insights to adjust expected points"""
        adjusted_xpts = player_xpts.copy()
        
        # Apply injury adjustments
        for injury_update in insights.get("injury_updates", []):
            # This would need more sophisticated parsing in a real implementation
            # For now, just a placeholder
            pass
        
        # Apply form adjustments
        for form_insight in insights.get("form_insights", []):
            # This would need more sophisticated parsing in a real implementation
            # For now, just a placeholder
            pass
        
        return adjusted_xpts
    
    def validate_insights(self, insights: Dict[str, Any]) -> bool:
        """Validate that insights are reasonable"""
        # Check for reasonable structure
        required_keys = ["player_recommendations", "injury_updates", "form_insights"]
        
        for key in required_keys:
            if key not in insights:
                return False
            
            if not isinstance(insights[key], list):
                return False
        
        return True
