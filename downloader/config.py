import os
import json
from dataclasses import dataclass

CONFIG_FILE = "config.json"

@dataclass
class DownloadConfig:
    links_file: str
    download_dir: str
    max_concurrent_downloads: int
    timeout: int
    retry_attempts: int

def load_config() -> DownloadConfig:
    defaults = {
        "links_file": "/mnt/6tb/MYT/Anime/Download/list.txt",  # Updated to your path
        "download_dir": "/mnt/6tb/MYT/Anime/Download",  # Updated to your path
        "max_concurrent_downloads": 1,  # Reduced to prevent server throttling
        "timeout": 120,  # Increased timeout
        "retry_attempts": 3  # Reduced but with better backoff
    }

    if not os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "w") as f:
            json.dump(defaults, f, indent=4)
        print(f"Created default {CONFIG_FILE}")

    try:
        with open(CONFIG_FILE, 'r') as f:
            cfg = json.load(f)
        cfg = {**defaults, **cfg}
    except:
        cfg = defaults

    os.makedirs(cfg["download_dir"], exist_ok=True)
    return DownloadConfig(**cfg)
