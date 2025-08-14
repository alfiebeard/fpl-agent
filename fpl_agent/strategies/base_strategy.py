"""
Base class for all LLM strategies.
This provides common functionality shared between different strategy implementations.
"""

import json
import logging
import re
from abc import ABC, abstractmethod
from typing import Dict, Any

from ..core.config import Config
from .llm_engine import LLMEngine
from ..data import DataService


logger = logging.getLogger(__name__)


class BaseLLMStrategy(ABC):
    """
    Abstract base class for all LLM strategies.
    
    This class provides common functionality that all LLM strategies share:
    - LLM engine initialization and management
    - Data service access
    - Common response processing methods
    - Configuration management
    """
    
    def __init__(self, config: Config, model_name: str):
        """
        Initialize base strategy with common components.
        
        Args:
            config: FPL configuration object
            model_name: Name of the LLM model to use (e.g., "main", "lightweight")
        """
        self.config = config
        self.model_name = model_name
        
        # Initialize LLM engine with specified model
        self.llm_engine = LLMEngine(config, model_name)
        
        # Initialize data service for all strategies
        self.data_service = DataService(config)
        
        logger.info(f"Initialized {self.__class__.__name__} with model: {model_name}")
    
    def _extract_json_response(self, response: str, context: str = "LLM response") -> Dict[str, Any]:
        """
        Extract and parse JSON from LLM response with error handling.
        
        Args:
            response: Raw response string from LLM
            context: Context for error messages
            
        Returns:
            Parsed JSON dictionary or empty dict if parsing fails
        """
        if not response:
            logger.warning(f"Empty {context}")
            return {}
        
        try:
            # Use the LLM engine's JSON extraction if available
            if hasattr(self.llm_engine, '_extract_json_from_response'):
                extracted = self.llm_engine._extract_json_from_response(response)
                if extracted != response:  # JSON was extracted
                    try:
                        return json.loads(extracted)
                    except json.JSONDecodeError:
                        pass
                        
            # Look for JSON object in the response
            json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', response, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                # Clean up common issues
                json_str = json_str.replace('\n', ' ').replace('\r', ' ')
                return json.loads(json_str)
            
            # Try simpler extraction
            start = response.find('{')
            end = response.rfind('}')
            if start != -1 and end != -1 and end > start:
                json_str = response[start:end+1]
                return json.loads(json_str)
            
            logger.warning(f"No JSON found in {context}")
            return {}
            
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse JSON from {context}: {e}")
            logger.debug(f"Response content: {response[:200]}...")
            return {}
        except Exception as e:
            logger.error(f"Unexpected error extracting JSON from {context}: {e}")
            return {}
    
    def get_current_gameweek(self) -> int:
        """
        Get current gameweek from data pipeline with fallback.
        
        Returns:
            Current gameweek number or 1 as fallback
        """
        return self.data_service.fetcher.get_current_gameweek() or 1
    
    def get_fixture_info(self, team_name: str, current_gameweek: int) -> Dict[str, Any]:
        """
        Get fixture information for a team in a specific gameweek.
        
        Args:
            team_name: Name of the team
            current_gameweek: Current gameweek number
            
        Returns:
            Dictionary containing fixture string, double gameweek status, and fixture difficulty
        """
        return self.data_service.get_fixture_info(team_name, current_gameweek)
    
    def __str__(self) -> str:
        """String representation of the strategy."""
        return f"{self.__class__.__name__}(model={self.model_name})"
    
    def __repr__(self) -> str:
        """Detailed string representation of the strategy."""
        return f"{self.__class__.__name__}(config={self.config}, model_name='{self.model_name}')"
