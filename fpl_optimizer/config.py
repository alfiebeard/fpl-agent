"""
Configuration management for FPL Optimizer
"""

import os
import yaml
from typing import Dict, Any, Optional
from pathlib import Path
from dotenv import load_dotenv


class Config:
    """Configuration manager for FPL Optimizer"""
    
    def __init__(self, config_path: Optional[str] = None):
        """Initialize configuration from YAML file and environment variables"""
        load_dotenv()  # Load environment variables from .env file
        
        if config_path is None:
            config_path = Path(__file__).parent / "config.yaml"
        
        self.config_path = Path(config_path)
        self._config = self._load_config()
        
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from YAML file"""
        if not self.config_path.exists():
            raise FileNotFoundError(f"Config file not found: {self.config_path}")
        
        with open(self.config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        # Override with environment variables
        config = self._override_with_env(config)
        
        return config
    
    def _override_with_env(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Override config values with environment variables"""
        env_mappings = {
            'OPENAI_API_KEY': ('llm', 'api_key'),
            'FPL_LEAGUE_ID': ('fpl', 'league_id'),
            'FPL_TEAM_ID': ('fpl', 'team_id'),
            'FPL_EMAIL': ('fpl', 'email'),
            'FPL_PASSWORD': ('fpl', 'password'),
        }
        
        for env_var, config_path in env_mappings.items():
            env_value = os.getenv(env_var)
            if env_value:
                self._set_nested_value(config, config_path, env_value)
        
        return config
    
    def _set_nested_value(self, config: Dict[str, Any], path: tuple, value: Any):
        """Set a nested value in the config dictionary"""
        current = config
        for key in path[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]
        current[path[-1]] = value
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value by dot notation (e.g., 'llm.model')"""
        keys = key.split('.')
        value = self._config
        
        try:
            for k in keys:
                value = value[k]
            return value
        except (KeyError, TypeError):
            return default
    
    def get_llm_config(self) -> Dict[str, Any]:
        """Get LLM configuration"""
        return self._config.get('llm', {})
    
    def get_optimization_config(self) -> Dict[str, Any]:
        """Get optimization configuration"""
        return self._config.get('optimization', {})
    
    def get_team_config(self) -> Dict[str, Any]:
        """Get team configuration"""
        return self._config.get('team', {})
    
    def get_points_config(self) -> Dict[str, Any]:
        """Get points configuration"""
        return self._config.get('points', {})
    
    def get_injury_config(self) -> Dict[str, Any]:
        """Get injury configuration"""
        return self._config.get('injury', {})
    
    def get_scheduler_config(self) -> Dict[str, Any]:
        """Get scheduler configuration"""
        return self._config.get('scheduler', {})
    
    def get_output_config(self) -> Dict[str, Any]:
        """Get output configuration"""
        return self._config.get('output', {})
    
    def get_testing_config(self) -> Dict[str, Any]:
        """Get testing configuration"""
        return self._config.get('testing', {})
    
    def is_test_mode(self) -> bool:
        """Check if running in test mode"""
        return self.get('testing.test_mode', False)
    
    def use_mock_data(self) -> bool:
        """Check if should use mock data - always returns False as mock data is not allowed"""
        return False 