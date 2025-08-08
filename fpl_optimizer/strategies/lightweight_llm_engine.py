"""
Lightweight LLM Engine for team-specific analysis
"""

import logging
from typing import Dict, Any

from google import genai
from google.genai import types

from ..core.config import Config

logger = logging.getLogger(__name__)


class LightweightLLMEngine:
    """
    Lightweight LLM engine for team-specific analysis.
    
    This class handles:
    - LLM calls using Gemini 2.5 Flash-Lite
    - Response processing and JSON extraction
    - Error handling for LLM operations
    """
    
    def __init__(self, config: Config):
        self.config = config
        self.llm_config = config.get_lightweight_llm_config()
        self.model_name = self.llm_config.get('model', 'gemini-2.5-flash-lite')
        self.model = self._initialize_gemini_model()
    
    def _initialize_gemini_model(self):
        """Initialize the Gemini model with web search capabilities"""
        try:
            api_key = self.config.get_env_var('GEMINI_API_KEY')
            
            client = genai.Client(api_key=api_key)

            # Define the grounding tool for web search
            grounding_tool = types.Tool(
                google_search=types.GoogleSearch()
            )

            # Configure generation settings for lightweight model
            generation_config = types.GenerateContentConfig(
                tools=[grounding_tool],
                temperature=self.llm_config.get('temperature', 0.2),
                max_output_tokens=self.llm_config.get('max_output_tokens', 8192),
                top_p=self.llm_config.get('top_p', 0.8),
                top_k=self.llm_config.get('top_k', 25)
            )
            
            # Store client and config for later use
            self.client = client
            self.generation_config = generation_config
            
            logger.info(f"Initialized lightweight LLM engine with model: {self.model_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize Gemini model: {e}")
            raise
    
    def query_llm(self, prompt: str) -> str:
        """
        Query the LLM with a given prompt and return the response.
        
        Args:
            prompt: The prompt to send to the LLM
            
        Returns:
            String containing the LLM response (cleaned JSON if available)
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
            
            # Check if response has text content
            if not hasattr(response, 'text') or response.text is None:
                logger.warning(f"LLM response has no text content. Response type: {type(response)}")
                logger.warning(f"Response attributes: {dir(response) if response else 'None'}")
                return "Error: Empty response from LLM"
            
            # Clean up the response to extract only the JSON part
            response_text = response.text.strip()
            
            # Try to extract JSON from the response
            import json
            import re
            
            # Look for JSON object in the response (more robust pattern)
            json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', response_text, re.DOTALL)
            if json_match:
                try:
                    # Validate that it's proper JSON
                    json_str = json_match.group(0)
                    # Clean up common issues
                    json_str = json_str.replace('\n', ' ').replace('\r', ' ')
                    json.loads(json_str)  # Test if it's valid JSON
                    return json_str
                except json.JSONDecodeError:
                    # Try a simpler extraction
                    try:
                        # Look for the first { and last }
                        start = response_text.find('{')
                        end = response_text.rfind('}')
                        if start != -1 and end != -1 and end > start:
                            json_str = response_text[start:end+1]
                            json.loads(json_str)  # Test if it's valid JSON
                            return json_str
                    except json.JSONDecodeError:
                        pass
                    # If JSON extraction fails, return the full response
                    return response_text
            else:
                # If no JSON found, return the full response
                return response_text
                
        except Exception as e:
            logger.error(f"Failed to query LLM: {e}")
            return f"Error: Could not get LLM response" 