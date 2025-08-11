import os
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from .config import load_config
from .downloader import FileDownloader

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)

class DownloadManager:
    def __init__(self):
        self.config = load_config()
        self.downloader = FileDownloader(self.config)

    def run(self):
        links = self._links()
        if not links:
            logger.error("No links found in list file")
            return

        # Process downloads sequentially (one at a time) to avoid server throttling
        for link in links:
            logger.info(f"Starting download: {link}")
            success = self.downloader.download(link, self.config.download_dir)
            if success:
                logger.info(f"Completed: {link}")
            else:
                logger.error(f"Failed: {link}")
                # Try one more time with single-threaded approach
                logger.info(f"Retrying {link} with single-threaded approach...")
                success = self._retry_single_threaded(link)
                if success:
                    logger.info(f"Retry successful: {link}")
                else:
                    logger.error(f"Retry also failed: {link}")

    def _retry_single_threaded(self, url):
        """Fallback method using single-threaded download with enhanced anti-throttling"""
        try:
            downloader = FileDownloader(self.config)
            return downloader._single_with_anti_throttling(url, self.config.download_dir)
        except Exception as e:
            logger.error(f"Retry failed: {e}")
            return False

    def _links(self):
        if not os.path.exists(self.config.links_file):
            with open(self.config.links_file, 'w') as f:
                f.write("# One URL per line")

            return []
        with open(self.config.links_file, 'r') as f:
            return [line.strip() for line in f if line.strip() and not line.startswith("#")]
