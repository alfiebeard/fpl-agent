"""
OpenRouter Engine for API communication
"""

import logging
import requests
from typing import Optional, Dict, Any

from ..core.config import Config

logger = logging.getLogger(__name__)


class OpenRouterEngine:
    """
    OpenRouter engine that works with any OpenRouter model configuration.
    
    This class handles:
    - OpenRouter API initialization and configuration
    - Web search integration when enabled (via :online suffix)
    - Response processing and JSON extraction
    - Error handling for LLM operations
    """
    
    def __init__(self, config: Config, model_name: str):
        """
        Initialize OpenRouter engine.
        
        Args:
            config: Main FPL configuration
            model_name: Name of the model config to use (e.g., "openrouter_gpt5")
        """
        self.config = config
        
        # Get the model config dynamically from the config file
        self.llm_config = config.get_llm_model_config(model_name)
        self.model_name = self.llm_config.get('model')
        
        # Enable web search by appending :online if configured
        if self.llm_config.get('web_search', False):
            self.model_name = f"{self.model_name}:online"
        
        # Get API key from config
        self.api_key = config._config.get('llm', {}).get('openrouter_api_key')
        if not self.api_key:
            raise ValueError("OpenRouter API key not found. Set OPENROUTER_API_KEY environment variable.")
        
        # OpenRouter API endpoint
        self.api_url = "https://openrouter.ai/api/alpha/responses"
        
        logger.info(f"Initialized OpenRouter engine with model: {self.model_name}")
    
    def query(self, prompt: str, response_schema: Optional[dict] = None, max_retries: Optional[int] = None) -> str:
        """
        Query the OpenRouter API with a given prompt and automatic retry on failure.
        
        Args:
            prompt: The prompt to send to the LLM
            response_schema: Optional response schema (not used for OpenRouter)
            max_retries: Maximum number of retry attempts (defaults to config value if None)

        Returns:
            String containing the LLM response
        """
        # Use config value if max_retries not specified
        if max_retries is None:
            max_retries = self.llm_config.get('max_retries', 1)
        
        for attempt in range(max_retries + 1):
            try:
                # Prepare the request payload
                payload = {
                    "model": self.model_name,
                    "input": prompt,
                    "max_tokens": self.llm_config.get('max_output_tokens', 8192),
                    "temperature": self.llm_config.get('temperature', 0.3),
                    "top_p": self.llm_config.get('top_p', 0.8),
                    "top_k": self.llm_config.get('top_k', 25),
                }
                
                # Debug logging - let's see what we're sending
                logger.debug(f"OpenRouter API request payload: {payload}")
                
                # Prepare headers
                headers = {
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                }
                
                # Make the API request
                response = requests.post(
                    self.api_url,
                    json=payload,
                    headers=headers,
                    timeout=600  # 10 minute timeout
                )
                
                # Check for HTTP errors
                response.raise_for_status()
                
                # Parse the response
                response_data = response.json()
                
                # Debug logging - let's see what we're getting
                logger.debug(f"OpenRouter API response status: {response.status_code}")
                logger.debug(f"OpenRouter API response data: {response_data}")
                
                # Extract the response text
                text_response = self._extract_text_response(response_data)
                
                # Check if extraction failed
                if text_response.startswith("Error:"):
                    if attempt < max_retries:
                        logger.warning(f"OpenRouter response extraction failed (attempt {attempt + 1}/{max_retries + 1}), retrying...")
                        logger.warning(f"Error: {text_response}")
                        continue  # Try again
                    else:
                        logger.error(f"OpenRouter response extraction failed after {max_retries + 1} attempts")
                        return text_response
                
                # Success!
                if attempt > 0:
                    logger.info(f"OpenRouter query succeeded on retry attempt {attempt + 1}")
                return text_response
                
            except requests.exceptions.RequestException as e:
                if attempt < max_retries:
                    logger.warning(f"OpenRouter query failed (attempt {attempt + 1}/{max_retries + 1}), retrying... Error: {e}")
                    continue
                else:
                    logger.error(f"OpenRouter query failed after {max_retries + 1} attempts: {e}")
                    return f"Error: {e}"
            except Exception as e:
                if attempt < max_retries:
                    logger.warning(f"OpenRouter query failed (attempt {attempt + 1}/{max_retries + 1}), retrying... Error: {e}")
                    continue
                else:
                    logger.error(f"OpenRouter query failed after {max_retries + 1} attempts: {e}")
                    return f"Error: {e}"
        
        # This should never be reached, but just in case
        return "Error: Unexpected retry loop exit"
        
    def _extract_text_response(self, response_data: Dict[str, Any]) -> str:
        """
        Extracts the textual response from an OpenRouter API response in a consistent way,
        handling reasoning-enabled models, encrypted reasoning, and structured outputs.
        
        Args:
            response_data: Raw JSON response from OpenRouter API.
        
        Returns:
            Extracted text as a single string, or an error message if no text found.
        """
        try:
            text_pieces = []

            # Prefer iterating over the 'output' array
            for item in response_data.get("output", []):
                # Messages from assistant
                if item.get("type") == "message":
                    for content in item.get("content", []):
                        if content.get("type") == "output_text" and content.get("text"):
                            text_pieces.append(content["text"])

                # Reasoning outputs (optional, encrypted_content ignored unless needed)
                elif item.get("type") == "reasoning":
                    # Some models put summary arrays here; skip or handle as needed
                    if "summary" in item and item["summary"]:
                        text_pieces.extend(item["summary"])
                    # You can optionally decode 'encrypted_content' if required

            # Fallback for legacy 'choices'
            if not text_pieces and "choices" in response_data:
                for choice in response_data.get("choices", []):
                    message = choice.get("message", {})
                    content = message.get("content")
                    if isinstance(content, str) and content.strip():
                        text_pieces.append(content.strip())
            
            if not text_pieces:
                return "Error: No text found in model response"

            # Concatenate all pieces and return
            return "\n".join(text_pieces).strip()

        except Exception as e:
            return f"Error: Failed to extract text - {e}"
