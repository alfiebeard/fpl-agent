"""
Base class for all LLM strategies.
This provides common functionality shared between different strategy implementations.
"""

import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

from ..core.config import Config
from .llm_engine import LLMEngine

logger = logging.getLogger(__name__)


class BaseLLMStrategy(ABC):
    """
    Abstract base class for all LLM strategies.
    
    This class provides common functionality that all LLM strategies share:
    - LLM engine initialization and management
    - Common prompt creation utilities
    - Shared response processing methods
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
        
        logger.info(f"Initialized {self.__class__.__name__} with model: {model_name}")
    
    @abstractmethod
    def get_strategy_name(self) -> str:
        """
        Return the name of this strategy.
        
        Returns:
            String identifier for the strategy
        """
        pass
    
    def _create_prompt(self, template: str, **kwargs) -> str:
        """
        Create a prompt by formatting a template with provided arguments.
        
        Args:
            template: Prompt template string with placeholders
            kwargs: Values to substitute into the template
            
        Returns:
            Formatted prompt string
        """
        try:
            return template.format(**kwargs)
        except KeyError as e:
            logger.error(f"Missing required prompt argument: {e}")
            logger.error(f"Template: {template}")
            logger.error(f"Provided kwargs: {kwargs}")
            raise ValueError(f"Prompt template missing required argument: {e}")
        except Exception as e:
            logger.error(f"Failed to create prompt: {e}")
            raise
    
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
                        import json
                        return json.loads(extracted)
                    except json.JSONDecodeError:
                        pass
            
            # Fallback to manual JSON extraction
            import json
            import re
            
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
    
    def _validate_llm_response(self, response: str, context: str = "LLM response") -> bool:
        """
        Validate that an LLM response is usable.
        
        Args:
            response: Response string from LLM
            context: Context for error messages
            
        Returns:
            True if response is valid, False otherwise
        """
        if not response:
            logger.warning(f"Empty {context}")
            return False
        
        if response.startswith("Error:"):
            logger.warning(f"LLM returned error in {context}: {response}")
            return False
        
        if len(response.strip()) < 10:
            logger.warning(f"Very short {context}: {response}")
            return False
        
        return True
    
    def _log_llm_interaction(self, prompt: str, response: str, context: str = "LLM query") -> None:
        """
        Log LLM interaction details for debugging.
        
        Args:
            prompt: Prompt sent to LLM
            response: Response received from LLM
            context: Context for the interaction
        """
        logger.debug(f"=== {context} ===")
        logger.debug(f"Prompt (length: {len(prompt)}): {prompt[:200]}...")
        logger.debug(f"Response (length: {len(response)}): {response[:200]}...")
        
        # Log response quality indicators
        if response.startswith("Error:"):
            logger.warning(f"LLM error in {context}: {response}")
        elif len(response.strip()) < 50:
            logger.warning(f"Very short response in {context}: {response}")
    
    def get_config_value(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value with fallback to default.
        
        Args:
            key: Configuration key (supports dot notation)
            default: Default value if key not found
            
        Returns:
            Configuration value or default
        """
        return self.config.get(key, default)
    
    def get_model_config(self) -> Dict[str, Any]:
        """
        Get the current model configuration.
        
        Returns:
            Dictionary containing model configuration
        """
        return self.config.get_llm_model_config(self.model_name)
    
    def refresh_model(self) -> None:
        """
        Refresh the LLM model configuration.
        
        This can be useful if model settings change during runtime.
        """
        logger.info(f"Refreshing LLM model configuration for {self.model_name}")
        
        # Reinitialize LLM engine with current config
        self.llm_engine = LLMEngine(self.config, self.model_name)
        
        logger.info(f"LLM model refreshed: {self.model_name}")
    
    def get_strategy_info(self) -> Dict[str, Any]:
        """
        Get information about this strategy instance.
        
        Returns:
            Dictionary containing strategy information
        """
        return {
            "strategy_name": self.get_strategy_name(),
            "model_name": self.model_name,
            "config_source": self.config.config_path,
            "llm_engine_type": self.llm_engine.__class__.__name__
        }
    
    def __str__(self) -> str:
        """String representation of the strategy."""
        return f"{self.__class__.__name__}(model={self.model_name})"
    
    def __repr__(self) -> str:
        """Detailed string representation of the strategy."""
        return f"{self.__class__.__name__}(config={self.config}, model_name='{self.model_name}')"
