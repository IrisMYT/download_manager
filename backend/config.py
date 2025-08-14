import json
import os
from typing import Dict, Any
from dataclasses import dataclass, asdict

@dataclass
class DownloadConfig:
    download_dir: str = "downloads"
    max_concurrent_downloads: int = 3
    timeout: int = 30
    retry_attempts: int = 3

@dataclass
class DownloadSettings:
    user_agent: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    proxy: str = None
    resume_on_startup: bool = False
    auto_start: bool = True
    min_split_size: int = 10 * 1024 * 1024  # 10MB
    global_chunk_number: int = 4
    global_chunk_size: int = 1024 * 1024  # 1MB
    max_speed_limit: int = 0  # KB/s, 0 = unlimited

class ConfigManager:
    def __init__(self):
        self.config_file = "config/config.json"
        self.settings_file = "config/settings.json"
        self.config = DownloadConfig()
        self.settings = DownloadSettings()
        self.load()

    def load(self):
        """Load configuration from files"""
        # Load config
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    data = json.load(f)
                    self.config = DownloadConfig(**data)
            except Exception as e:
                print(f"Error loading config: {e}")
                self.save()  # Save defaults
        else:
            self.save()  # Create with defaults

        # Load settings
        if os.path.exists(self.settings_file):
            try:
                with open(self.settings_file, 'r') as f:
                    data = json.load(f)
                    self.settings = DownloadSettings(**data)
            except Exception as e:
                print(f"Error loading settings: {e}")
                self.save()
        else:
            self.save()

        # Ensure download directory exists
        os.makedirs(self.config.download_dir, exist_ok=True)

    def save(self):
        """Save configuration to files"""
        os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
        
        with open(self.config_file, 'w') as f:
            json.dump(asdict(self.config), f, indent=2)
        
        with open(self.settings_file, 'w') as f:
            json.dump(asdict(self.settings), f, indent=2)

    def get_config(self) -> Dict[str, Any]:
        """Get config as dictionary"""
        return asdict(self.config)

    def get_settings(self) -> Dict[str, Any]:
        """Get settings as dictionary"""
        return asdict(self.settings)

    def update_config(self, updates: Dict[str, Any]):
        """Update config values"""
        for key, value in updates.items():
            if hasattr(self.config, key):
                setattr(self.config, key, value)
        self.save()

    def update_settings(self, updates: Dict[str, Any]):
        """Update settings values"""
        for key, value in updates.items():
            if hasattr(self.settings, key):
                setattr(self.settings, key, value)
        self.save()
