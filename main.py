#!/usr/bin/env python3

import sys
import os

# Add the downloader package to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from downloader.manager import DownloadManager

def main():
    try:
        manager = DownloadManager()
        manager.run()
    except KeyboardInterrupt:
        print("Download interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()

