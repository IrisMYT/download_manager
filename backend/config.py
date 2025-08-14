import os
import json
from dataclasses import dataclass, asdict
from typing import Dict, Any
import threading

CONFIG_DIR = "config"
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")
SETTINGS_FILE = os.path.join(CONFIG_DIR, "settings.json")

@dataclass
class DownloadConfig:
    links_file: str
    download_dir: str
    max_concurrent_downloads: int
    timeout: int
    retry_attempts: int
    
@dataclass
class GlobalSettings:
    global_chunk_size: int
    global_chunk_number: int
    max_speed_limit: int  # in KB/s, 0 for unlimited
    auto_start: bool
    resume_on_startup: bool
    min_split_size: int  # minimum file size to split
    user_agent: str
    proxy: str
    
class ConfigManager:
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not hasattr(self, 'initialized'):
            self.initialized = True
            os.makedirs(CONFIG_DIR, exist_ok=True)
            self.config = self.load_config()
            self.settings = self.load_settings()
    
    def load_config(self) -> DownloadConfig:
        defaults = {
            "links_file": "downloads/queue.txt",
            "download_dir": "downloads",
            "max_concurrent_downloads": 3,
            "timeout": 300,
            "retry_attempts": 5
        }
        
        if not os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, "w") as f:
                json.dump(defaults, f, indent=4)
        
        try:
            with open(CONFIG_FILE, 'r') as f:
                cfg = json.load(f)
            cfg = {**defaults, **cfg}
        except:
            cfg = defaults
        
        os.makedirs(cfg["download_dir"], exist_ok=True)
        return DownloadConfig(**cfg)
    
    def load_settings(self) -> GlobalSettings:
        defaults = {
            "global_chunk_size": 1048576,  # 1MB
            "global_chunk_number": 8,
            "max_speed_limit": 0,
            "auto_start": True,
            "resume_on_startup": True,
            "min_split_size": 10485760,  # 10MB
            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "proxy": ""
        }
        
        if not os.path.exists(SETTINGS_FILE):
            with open(SETTINGS_FILE, "w") as f:
                json.dump(defaults, f, indent=4)
        
        try:
            with open(SETTINGS_FILE, 'r') as f:
                settings = json.load(f)
            settings = {**defaults, **settings}
        except:
            settings = defaults
            
        return GlobalSettings(**settings)
    
    def save_config(self, config_dict: Dict[str, Any]):
        with self._lock:
            with open(CONFIG_FILE, 'w') as f:
                json.dump(config_dict, f, indent=4)
            self.config = DownloadConfig(**config_dict)
    
    def save_settings(self, settings_dict: Dict[str, Any]):
        with self._lock:
            with open(SETTINGS_FILE, 'w') as f:
                json.dump(settings_dict, f, indent=4)
            self.settings = GlobalSettings(**settings_dict)
    
    def get_config_dict(self) -> Dict[str, Any]:
        return asdict(self.config)
    
    def get_settings_dict(self) -> Dict[str, Any]:
        return asdict(self.settings)
