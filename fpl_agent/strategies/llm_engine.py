"""
Unified LLM Engine for Gemini API communication
"""

import logging

from google import genai
from google.genai import types

from ..core.config import Config

logger = logging.getLogger(__name__)


class LLMEngine:
    """
    Unified LLM engine that works with any Gemini model configuration.
    
    This class handles:
    - Gemini API initialization and configuration
    - Web search integration when enabled
    - Response processing and JSON extraction
    - Error handling for LLM operations
    """
    
    def __init__(self, config: Config, model_name: str):
        """
        Initialize LLM engine.
        
        Args:
            config: Main FPL configuration
            model_name: Name of the model config to use (e.g., "main", "lightweight")
        """
        self.config = config
        
        # Get the model config dynamically from the config file
        self.llm_config = config.get_llm_model_config(model_name)
        self.model_name = self.llm_config.get('model')
        
        # Initialize Gemini client and model
        self._initialize_gemini_model()
    
    def _initialize_gemini_model(self):
        """Initialize the Gemini client and model configuration"""
        try:
            api_key = self.llm_config.get('api_key')
            
            client = genai.Client(api_key=api_key)

            # Define the grounding tool for web search
            grounding_tool = types.Tool(
                google_search=types.GoogleSearch()
            )

            # Configure generation settings from model config
            generation_config = types.GenerateContentConfig(
                tools=[grounding_tool],  # Re-enabled web search grounding
                temperature=self.llm_config.get('temperature', 0.3),
                max_output_tokens=self.llm_config.get('max_output_tokens', 8192),
                top_p=self.llm_config.get('top_p', 0.8),
                top_k=self.llm_config.get('top_k', 25)
            )
            
            # Store client and config for later use
            self.client = client
            self.generation_config = generation_config
            
            logger.info(f"Initialized LLM engine with model: {self.model_name}")
            
        except Exception as e:
            logger.error(f"Failed to initialize Gemini model: {e}")
            raise
    
    def query(self, prompt: str) -> str:
        """
        Query the LLM with a given prompt.
        
        Args:
            prompt: The prompt to send to the LLM
            
        Returns:
            String containing the LLM response
        """
        try:
            # Initialize the model if not already done
            if not hasattr(self, 'client'):
                self._initialize_gemini_model()
                
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=self.generation_config
            )
            
            # Simple text extraction - LLM should return json
            if hasattr(response, 'candidates') and response.candidates:
                candidate = response.candidates[0]
                if hasattr(candidate, 'content') and candidate.content.parts:
                    return candidate.content.parts[0].text.strip()
            
            return "Error: Invalid response format from LLM"
                
        except Exception as e:
            logger.error(f"LLM query failed: {e}")
            return f"Error: {e}"