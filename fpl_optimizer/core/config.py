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
            config_path = Path(__file__).parent.parent / "config.yaml"
        
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
            'GEMINI_API_KEY': ('llm', 'api_key'),
            'FPL_TEAM_ID': ('fpl', 'team_id'),
        }
        
        for env_var, config_path in env_mappings.items():
            env_value = os.getenv(env_var)
            if env_value:
                # Navigate to nested config
                current = config
                for key in config_path[:-1]:
                    if key not in current:
                        current[key] = {}
                    current = current[key]
                current[config_path[-1]] = env_value
        
        return config
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value by key"""
        keys = key.split('.')
        current = self._config
        
        for k in keys:
            if isinstance(current, dict) and k in current:
                current = current[k]
            else:
                return default
        
        return current
    
    def get_env_var(self, var_name: str) -> Optional[str]:
        """Get environment variable"""
        return os.getenv(var_name)
    
    def get_fpl_config(self) -> Dict[str, Any]:
        """Get FPL API configuration"""
        return self._config.get('fpl', {})
    
    def get_data_sources_config(self) -> Dict[str, Any]:
        """Get data sources configuration"""
        return self._config.get('data_sources', {})
    
    def get_team_config(self) -> Dict[str, Any]:
        """Get team configuration"""
        return self._config.get('team', {})
    
    def get_optimization_config(self) -> Dict[str, Any]:
        """Get optimization configuration"""
        return self._config.get('optimization', {})
    
    def get_xpts_config(self) -> Dict[str, Any]:
        """Get expected points configuration"""
        return self._config.get('xpts', {})
    
    def get_llm_config(self) -> Dict[str, Any]:
        """Get LLM configuration"""
        return self._config.get('llm', {})
    
    def get_logging_config(self) -> Dict[str, Any]:
        """Get logging configuration"""
        return self._config.get('logging', {})
    
    def set(self, key: str, value: Any) -> None:
        """Set configuration value by key"""
        keys = key.split('.')
        current = self._config
        
        for k in keys[:-1]:
            if k not in current:
                current[k] = {}
            current = current[k]
        
        current[keys[-1]] = value
    
    def save(self, path: Optional[str] = None) -> None:
        """Save configuration to file"""
        save_path = Path(path) if path else self.config_path
        
        with open(save_path, 'w') as f:
            yaml.safe_dump(self._config, f, default_flow_style=False, indent=2)
    
    def reload(self) -> None:
        """Reload configuration from file"""
        self._config = self._load_config()
    
    def to_dict(self) -> Dict[str, Any]:
        """Return configuration as dictionary"""
        return self._config.copy()
    
    def __getitem__(self, key: str) -> Any:
        """Allow dictionary-style access"""
        return self.get(key)
    
    def __setitem__(self, key: str, value: Any) -> None:
        """Allow dictionary-style setting"""
        self.set(key, value)
    
    def __contains__(self, key: str) -> bool:
        """Check if key exists in configuration"""
        return self.get(key) is not None 