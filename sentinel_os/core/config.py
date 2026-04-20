"""
Configuration management system for SentinelOS
Supports YAML, JSON, and environment variable overrides
"""
import os
import json
from pathlib import Path
from typing import Dict, Any, Optional


class Config:
    """Central configuration management"""
    
    # Default configuration
    DEFAULT_CONFIG = {
        "simulation": {
            "max_time": 500,
            "enable_ai": True,
            "seed": None,
            "debug_mode": False,
        },
        "scheduler": {
            "policy": "hybrid",  # hybrid, edf, priority, round_robin
            "ai_advisor_enabled": True,
        },
        "resources": {
            "initial_memory": 1000,
            "initial_energy": 10000,
            "memory_threshold": 200,
            "energy_threshold": 2000,
        },
        "faults": {
            "deadline_miss_probability": 0.3,
            "resource_failure_probability": 0.2,
            "sensor_failure_probability": 0.1,
        },
        "tasks": {
            "generation_rate": 0.3,  # new tasks per time step
            "min_priority": 1,
            "max_priority": 10,
            "min_deadline": 5,
            "max_deadline": 20,
        },
        "events": {
            "io_interrupt_probability": 0.1,
            "timer_interrupt_probability": 0.15,
        },
        "logging": {
            "level": "INFO",  # DEBUG, INFO, WARNING, ERROR, CRITICAL
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            "file": None,  # None = stdout only
            "file_mode": "a",  # a = append, w = overwrite
        },
        "metrics": {
            "track_detailed": True,
            "export_interval": 50,  # steps between exports
            "export_formats": ["json", "csv"],  # json, csv, sqlite
        },
        "ai_advisor": {
            "model_path": "sentinel_os/ai/auv_ai_advisor.pkl",
            "confidence_threshold": 0.6,
            "retrain_frequency": 100,
        },
    }
    
    def __init__(self, config_file: Optional[str] = None):
        """
        Initialize configuration
        
        Args:
            config_file: Path to config file (YAML or JSON)
        """
        self.config = self.DEFAULT_CONFIG.copy()
        
        if config_file and os.path.exists(config_file):
            self._load_file(config_file)
        
        # Override with environment variables (SOS_* prefix)
        self._load_env_vars()
    
    def _load_file(self, config_file: str) -> None:
        """Load configuration from file"""
        try:
            if config_file.endswith('.json'):
                with open(config_file, 'r') as f:
                    file_config = json.load(f)
            elif config_file.endswith(('.yaml', '.yml')):
                try:
                    import yaml
                    with open(config_file, 'r') as f:
                        file_config = yaml.safe_load(f)
                except ImportError:
                    print("Warning: PyYAML not installed, skipping YAML config")
                    return
            else:
                raise ValueError(f"Unsupported config format: {config_file}")
            
            self._deep_merge(self.config, file_config)
            print(f"✓ Loaded config from {config_file}")
        except Exception as e:
            print(f"⚠ Warning: Failed to load config file: {e}")
    
    def _load_env_vars(self) -> None:
        """Load configuration from environment variables (SOS_* prefix)"""
        # Example: SOS_SIMULATION_MAX_TIME=1000
        for key, value in os.environ.items():
            if key.startswith("SOS_"):
                parts = key[4:].lower().split("_")
                if len(parts) >= 2:
                    section = parts[0]
                    setting = "_".join(parts[1:])
                    if section in self.config:
                        self.config[section][setting] = self._parse_value(value)
                        print(f"✓ Env override: {section}.{setting} = {value}")
    
    def _deep_merge(self, base: Dict, override: Dict) -> None:
        """Recursively merge override config into base"""
        for key, value in override.items():
            if isinstance(value, dict) and key in base:
                self._deep_merge(base[key], value)
            else:
                base[key] = value
    
    @staticmethod
    def _parse_value(value: str) -> Any:
        """Parse environment variable value to appropriate type"""
        if value.lower() == "true":
            return True
        elif value.lower() == "false":
            return False
        elif value.lower() == "none":
            return None
        else:
            try:
                return int(value)
            except ValueError:
                try:
                    return float(value)
                except ValueError:
                    return value
    
    def get(self, section: str, key: str, default: Any = None) -> Any:
        """
        Get configuration value
        
        Args:
            section: Configuration section (e.g., 'simulation')
            key: Configuration key (e.g., 'max_time')
            default: Default value if not found
        
        Returns:
            Configuration value
        """
        return self.config.get(section, {}).get(key, default)
    
    def set(self, section: str, key: str, value: Any) -> None:
        """Set configuration value"""
        if section not in self.config:
            self.config[section] = {}
        self.config[section][key] = value
    
    def to_dict(self) -> Dict:
        """Get entire configuration as dictionary"""
        return self.config.copy()
    
    def to_json(self) -> str:
        """Serialize configuration to JSON"""
        return json.dumps(self.config, indent=2)
    
    def save(self, filepath: str) -> None:
        """Save configuration to file"""
        os.makedirs(os.path.dirname(filepath) or ".", exist_ok=True)
        with open(filepath, 'w') as f:
            if filepath.endswith('.json'):
                json.dump(self.config, f, indent=2)
            elif filepath.endswith(('.yaml', '.yml')):
                try:
                    import yaml
                    yaml.dump(self.config, f, default_flow_style=False)
                except ImportError:
                    print("Warning: PyYAML not installed, saving as JSON instead")
                    json.dump(self.config, f, indent=2)
        print(f"✓ Saved config to {filepath}")


# Global configuration instance
_global_config: Optional[Config] = None


def get_config(config_file: Optional[str] = None) -> Config:
    """Get global configuration instance"""
    global _global_config
    if _global_config is None:
        _global_config = Config(config_file)
    return _global_config


def reset_config() -> None:
    """Reset global configuration (useful for testing)"""
    global _global_config
    _global_config = None
