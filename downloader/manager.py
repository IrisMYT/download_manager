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

        with ThreadPoolExecutor(max_workers=self.config.max_concurrent_downloads) as pool:
            futures = [pool.submit(self.downloader.download, link, self.config.download_dir) for link in links]
            for f in as_completed(futures):
                f.result()

    def _links(self):
        if not os.path.exists(self.config.links_file):
            with open(self.config.links_file, 'w') as f:
                f.write("# One URL per line")
                
            return []
        with open(self.config.links_file, 'r') as f:
            return [line.strip() for line in f if line.strip() and not line.startswith("#")]
