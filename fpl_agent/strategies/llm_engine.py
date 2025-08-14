"""
Unified LLM Engine for Gemini API communication
"""

import logging
import json
import re

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
            api_key = self.config.get_env_var('GEMINI_API_KEY')
            
            client = genai.Client(api_key=api_key)

            # Define the grounding tool for web search
            grounding_tool = types.Tool(
                google_search=types.GoogleSearch()
            )

            # Configure generation settings from model config
            generation_config = types.GenerateContentConfig(
                tools=[grounding_tool],
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
    
    def query(self, prompt: str, extract_json: bool = False) -> str:
        """
        Query the LLM with a given prompt.
        
        Args:
            prompt: The prompt to send to the LLM
            extract_json: Whether to extract and clean JSON from response
            
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
            
            # Check if response has text content
            if not hasattr(response, 'candidates') or not response.candidates:
                logger.warning(f"LLM response has no candidates. Response type: {type(response)}")
                return "Error: Empty response from LLM"
            
            # Extract text from the first candidate
            candidate = response.candidates[0]
            if not hasattr(candidate, 'content') or not candidate.content:
                logger.warning(f"LLM response candidate has no content. Candidate: {candidate}")
                return "Error: Empty response content from LLM"
            
            # Extract text from content parts
            content_parts = candidate.content.parts
            if not content_parts:
                logger.warning(f"LLM response content has no parts. Content: {candidate.content}")
                return "Error: Empty response parts from LLM"
            
            # Get text from the first part
            first_part = content_parts[0]
            if not hasattr(first_part, 'text'):
                logger.warning(f"LLM response part has no text. Part: {first_part}")
                return "Error: No text in response part"
            
            response_text = first_part.text.strip()
            
            if not response_text:
                logger.warning("LLM response text is empty")
                return "Error: Empty response text from LLM"
            
            # Extract JSON if requested
            if extract_json:
                return self._extract_json_from_response(response_text)
            
            return response_text
                
        except Exception as e:
            logger.error(f"Failed to query LLM: {e}")
            return f"Error: Could not get LLM response: {e}"
    
    def _extract_json_from_response(self, response_text: str) -> str:
        """Extract and clean JSON from LLM response"""
        try:
            # Look for JSON object in the response (robust pattern)
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
                    # Try simpler extraction
                    try:
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
            logger.error(f"Failed to extract JSON from response: {e}")
            return response_text
    

    
