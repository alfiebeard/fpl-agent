"""
Core LLM engine for Gemini API communication with web search
"""

import logging
import json
from typing import Dict, List, Any

from google import genai
from google.genai import types


from ..models import Player, Position
from ..config import Config

logger = logging.getLogger(__name__)


class LLMEngine:
    """
    Core LLM engine for Gemini API communication with web search.
    
    This class handles:
    - Gemini API initialization and configuration
    - Web search integration for current insights
    - Core LLM communication functionality
    """
    
    def __init__(self, config: Config):
        self.config = config
        self.llm_config = config.get_llm_config()
        self.model_name = self.llm_config.get('model', 'gemini-2.5-pro')

        # Initialize Gemini client and search config
        self.model = self._initialize_gemini_model()

    def _initialize_gemini_model(self):
        """Initialize the Gemini client and search config"""
        api_key = self.config.get_env_var('GEMINI_API_KEY')
        
        try:
            client = genai.Client(api_key=api_key)

            # Define the grounding tool
            grounding_tool = types.Tool(
                google_search=types.GoogleSearch()
            )

            # Configure generation settings
            generation_config = types.GenerateContentConfig(
                tools=[grounding_tool],
                generation_config=types.GenerationConfig(
                    temperature=self.llm_config.get('temperature'),
                    max_output_tokens=self.llm_config.get('max_output_tokens'),
                    top_p=self.llm_config.get('top_p'),
                    top_k=self.llm_config.get('top_k')
                )
            )
            
            # Return the model
            return client.GenerativeModel(
                model_name=self.model_name,
                generation_config=generation_config
            )

        except Exception as e:
            logger.error(f"Failed to initialize Gemini model: {e}")
            return None
    

    
    def _query_gemini_with_search(self, prompt: str) -> str:
        """Query Gemini with web search enabled"""
        try:
            # Use Gemini's built-in web search (enabled at model level)
            response = self.model.generate_content(prompt)
            return response.text
        except Exception as e:
            logger.error(f"Failed to query Gemini: {e}")
            raise
    

    
