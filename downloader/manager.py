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

        logger.info(f"Starting download of {len(links)} files with {self.config.max_concurrent_downloads} concurrent downloads")
        
        # Process downloads sequentially to avoid server throttling
        for i, link in enumerate(links):
            logger.info(f"Downloading file {i+1}/{len(links)}: {link}")
            try:
                result = self.downloader.download(link, self.config.download_dir)
                if result:
                    logger.info(f"Successfully downloaded: {link}")
                else:
                    logger.error(f"Failed to download: {link}")
            except Exception as e:
                logger.error(f"Exception downloading {link}: {e}")

    def _links(self):
        if not os.path.exists(self.config.links_file):
            with open(self.config.links_file, 'w') as f:
                f.write("# One URL per line")
            logger.info(f"Created empty links file: {self.config.links_file}")
            return []
        
        with open(self.config.links_file, 'r') as f:
            links = [line.strip() for line in f if line.strip() and not line.startswith("#")]
        logger.info(f"Loaded {len(links)} links from {self.config.links_file}")
        return links
