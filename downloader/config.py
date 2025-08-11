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
        "links_file": "list.txt",
        "download_dir": "downloads",
        "max_concurrent_downloads": 3,  # Reduced to prevent overwhelming server
        "timeout": 120,  # Increased timeout
        "retry_attempts": 3  # Reduced retries to prevent hanging
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
