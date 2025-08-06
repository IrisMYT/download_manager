#!/usr/bin/env python3
"""
Multi-threaded Download Manager
Automatically optimizes download settings based on server capabilities
"""

import os
import sys
import time
import logging
from dataclasses import dataclass
from typing import List, Tuple, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urlparse, unquote
from pathlib import Path

import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)


@dataclass
class DownloadConfig:
    """Configuration for download settings"""
    max_concurrent_downloads: int = 3
    threads_per_download: int = 4
    chunk_size: int = 1024 * 1024  # 1MB
    timeout: int = 30
    retry_attempts: int = 3
    links_file: str = "download_links.txt"
    save_path: str = os.getcwd()


@dataclass
class ServerCapabilities:
    """Server test results"""
    max_threads: int
    speed_mbps: float
    supports_range: bool


@dataclass
class DownloadTask:
    """Represents a single download task"""
    url: str
    filename: str
    filepath: Path
    size: int
    threads: int


class NetworkTester:
    """Tests server capabilities and connection limits"""
    
    def __init__(self, config: DownloadConfig):
        self.config = config
        self.session = self._create_session()
    
    def _create_session(self) -> requests.Session:
        """Create a session with retry strategy"""
        session = requests.Session()
        retry = Retry(
            total=self.config.retry_attempts,
            backoff_factor=0.3,
            status_forcelist=[500, 502, 503, 504]
        )
        adapter = HTTPAdapter(max_retries=retry)
        session.mount('http://', adapter)
        session.mount('https://', adapter)
        return session
    
    def test_server(self, url: str) -> ServerCapabilities:
        """Run all server tests"""
        logger.info("Testing server capabilities...")
        
        supports_range = self._test_range_support(url)
        max_threads = self._test_thread_limit(url) if supports_range else 1
        speed_mbps = self._test_speed(url)
        
        return ServerCapabilities(
            max_threads=max_threads,
            speed_mbps=speed_mbps,
            supports_range=supports_range
        )
    
    def _test_range_support(self, url: str) -> bool:
        """Check if server supports partial content"""
        try:
            response = self.session.head(url, timeout=self.config.timeout)
            return response.headers.get('Accept-Ranges') == 'bytes'
        except Exception as e:
            logger.debug(f"Range support test failed: {e}")
            return False
    
    def _test_thread_limit(self, url: str, max_test: int = 10) -> int:
        """Test maximum concurrent connections"""
        logger.info("Testing concurrent connection limit...")
        
        def test_connection(thread_id: int) -> bool:
            try:
                headers = {'Range': f'bytes={thread_id*1024}-{(thread_id+1)*1024-1}'}
                response = self.session.get(
                    url, 
                    headers=headers, 
                    timeout=5, 
                    stream=True
                )
                return response.status_code in [200, 206]
            except:
                return False
        
        with ThreadPoolExecutor(max_workers=max_test) as executor:
            futures = [executor.submit(test_connection, i) for i in range(max_test)]
            results = [f.result() for f in as_completed(futures)]
        
        successful = sum(results)
        logger.info(f"Server allows {successful} concurrent connections")
        return successful
    
    def _test_speed(self, url: str, test_size: int = 3) -> float:
        """Test download speed"""
        logger.info("Testing download speed...")
        
        total_bytes = 0
        start_time = time.time()
        
        for i in range(test_size):
            try:
                headers = {
                    'Range': f'bytes={i*self.config.chunk_size}-{(i+1)*self.config.chunk_size-1}'
                }
                response = self.session.get(url, headers=headers, stream=True)
                total_bytes += len(response.content)
            except:
                break
        
        elapsed = time.time() - start_time
        speed_mbps = (total_bytes / elapsed) / (1024 * 1024) if elapsed > 0 else 0
        logger.info(f"Average speed: {speed_mbps:.2f} MB/s")
        
        return speed_mbps


class FileDownloader:
    """Handles individual file downloads"""
    
    def __init__(self, config: DownloadConfig):
        self.config = config
        self.session = self._create_session()
    
    def _create_session(self) -> requests.Session:
        """Create a session with retry strategy"""
        session = requests.Session()
        retry = Retry(
            total=self.config.retry_attempts,
            backoff_factor=0.3,
            status_forcelist=[500, 502, 503, 504]
        )
        adapter = HTTPAdapter(max_retries=retry)
        session.mount('http://', adapter)
        session.mount('https://', adapter)
        return session
    
    def download(self, task: DownloadTask) -> bool:
        """Download a file using optimal strategy"""
        try:
            if task.size > 0 and task.threads > 1:
                return self._multi_threaded_download(task)
            else:
                return self._single_threaded_download(task)
        except Exception as e:
            logger.error(f"Failed to download {task.filename}: {e}")
            return False
    
    def _single_threaded_download(self, task: DownloadTask) -> bool:
        """Simple single-threaded download"""
        logger.info(f"Downloading {task.filename} (single-threaded)...")
        
        try:
            response = self.session.get(task.url, stream=True, timeout=self.config.timeout)
            response.raise_for_status()
            
            with open(task.filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            
            logger.info(f"✓ Completed: {task.filename}")
            return True
            
        except Exception as e:
            logger.error(f"Download failed: {e}")
            return False
    
    def _multi_threaded_download(self, task: DownloadTask) -> bool:
        """Multi-threaded download with partial content"""
        logger.info(f"Downloading {task.filename} ({task.size / 1024 / 1024:.2f} MB) "
                   f"with {task.threads} threads...")
        
        chunks = self._calculate_chunks(task.size, task.threads)
        partial_files = []
        
        def download_chunk(chunk_info: Tuple[int, int, int]) -> Optional[str]:
            idx, start, end = chunk_info
            headers = {'Range': f'bytes={start}-{end}'}
            
            try:
                response = self.session.get(
                    task.url, 
                    headers=headers, 
                    stream=True,
                    timeout=self.config.timeout
                )
                response.raise_for_status()
                
                temp_file = f"{task.filepath}.part{idx}"
                with open(temp_file, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                
                return temp_file
                
            except Exception as e:
                logger.error(f"Chunk {idx} failed: {e}")
                return None
        
        with ThreadPoolExecutor(max_workers=task.threads) as executor:
            futures = [executor.submit(download_chunk, chunk) for chunk in chunks]
            partial_files = [f.result() for f in as_completed(futures)]
        
        # Check if all chunks downloaded
        if None in partial_files:
            logger.error(f"Some chunks failed for {task.filename}")
            self._cleanup_partial_files(partial_files)
            return False
        
        # Combine chunks
        self._combine_files(partial_files, task.filepath)
        logger.info(f"✓ Completed: {task.filename}")
        return True
    
    def _calculate_chunks(self, file_size: int, num_threads: int) -> List[Tuple[int, int, int]]:
        """Calculate byte ranges for each thread"""
        chunk_size = file_size // num_threads
        chunks = []
        
        for i in range(num_threads):
            start = i * chunk_size
            end = start + chunk_size - 1 if i < num_threads - 1 else file_size - 1
            chunks.append((i, start, end))
        
        return chunks
    
    def _combine_files(self, partial_files: List[str], output_path: Path) -> None:
        """Combine partial files into final file"""
        partial_files.sort()  # Ensure correct order
        
        with open(output_path, 'wb') as outfile:
            for partial in partial_files:
                if partial:
                    with open(partial, 'rb') as infile:
                        outfile.write(infile.read())
                    os.remove(partial)
    
    def _cleanup_partial_files(self, partial_files: List[Optional[str]]) -> None:
        """Remove partial files"""
        for partial in partial_files:
            if partial and os.path.exists(partial):
                os.remove(partial)
    
    def get_file_info(self, url: str) -> Tuple[str, int]:
        """Get filename and size from URL"""
        filename = self._extract_filename(url)
        
        try:
            response = self.session.head(url, timeout=self.config.timeout)
            size = int(response.headers.get('content-length', 0))
        except:
            size = 0
        
        return filename, size
    
    def _extract_filename(self, url: str) -> str:
        """Extract filename from URL"""
        parsed = urlparse(url)
        filename = os.path.basename(parsed.path)
        if not filename:
            filename = f"download_{int(time.time())}"
        return unquote(filename)


class DownloadManager:
    """Main download manager orchestrator"""
    
    def __init__(self, config: Optional[DownloadConfig] = None):
        self.config = config or DownloadConfig()
        self.tester = NetworkTester(self.config)
        self.downloader = FileDownloader(self.config)
    
    def run(self) -> None:
        """Main execution flow"""
        self._print_header()
        
        # Load links
        links = self._load_links()
        if not links:
            return
        
        # Get user configuration
        self._get_user_config()
        
        # Test server capabilities
        capabilities = self._test_server(links[0])
        
        # Optimize settings
        self._optimize_settings(capabilities)
        
        # Prepare download tasks
        tasks = self._prepare_tasks(links)
        
        # Execute downloads
        self._execute_downloads(tasks)
        
        logger.info("✓ All downloads completed!")
    
    def _print_header(self) -> None:
        """Print application header"""
        print("=" * 50)
        print("    MULTI-THREADED DOWNLOAD MANAGER")
        print("=" * 50)
    
    def _load_links(self) -> List[str]:
        """Load links from file"""
        if not os.path.exists(self.config.links_file):
            self._create_sample_file()
            logger.error(f"Please add your links to {self.config.links_file}")
            return []
        
        with open(self.config.links_file, 'r') as f:
            links = [line.strip() for line in f 
                    if line.strip() and not line.startswith('#')]
        
        logger.info(f"Loaded {len(links)} links from {self.config.links_file}")
        return links
    
    def _create_sample_file(self) -> None:
        """Create sample links file"""
        with open(self.config.links_file, 'w') as f:
            f.write("# Add your download links here, one per line
")
            f.write("# Lines starting with # are ignored
")
            f.write("# Example:
")
            f.write("# https://example.com/file.zip
")
        logger.info(f"Created {self.config.links_file}")
    
    def _get_user_config(self) -> None:
        """Get configuration from user"""
        try:
            concurrent = input("
Max concurrent downloads (default 3): ").strip()
            if concurrent:
                self.config.max_concurrent_downloads = int(concurrent)
            
            save_path = input("Save location (press Enter for current directory): ").strip()
            if save_path:
                self.config.save_path = save_path
                Path(save_path).mkdir(parents=True, exist_ok=True)
            
        except ValueError:
            logger.warning("Invalid input, using defaults")
    
    def _test_server(self, test_url: str) -> ServerCapabilities:
        """Test server capabilities using first link"""
        logger.info("
Analyzing server capabilities...")
        return self.tester.test_server(test_url)
    
    def _optimize_settings(self, capabilities: ServerCapabilities) -> None:
        """Optimize download settings based on test results"""
        if capabilities.supports_range:
            # Use tested limit but cap at 8 threads per file for stability
            self.config.threads_per_download = min(capabilities.max_threads, 8)
        else:
            self.config.threads_per_download = 1
        
        logger.info(f"
Optimized settings:")
        logger.info(f"  • Threads per download: {self.config.threads_per_download}")
        logger.info(f"  • Concurrent downloads: {self.config.max_concurrent_downloads}")
    
    def _prepare_tasks(self, links: List[str]) -> List[DownloadTask]:
        """Prepare download tasks"""
        tasks = []
        
        for url in links:
            filename, size = self.downloader.get_file_info(url)
            filepath = Path(self.config.save_path) / filename
            
            task = DownloadTask(
                url=url,
                filename=filename,
                filepath=filepath,
                size=size,
                threads=self.config.threads_per_download if size > 0 else 1
            )
            tasks.append(task)
        
        return tasks
    
    def _execute_downloads(self, tasks: List[DownloadTask]) -> None:
        """Execute download tasks"""
        logger.info(f"
Starting {len(tasks)} downloads...
")
        
        with ThreadPoolExecutor(max_workers=self.config.max_concurrent_downloads) as executor:
            futures = {executor.submit(self.downloader.download, task): task 
                      for task in tasks}
            
            completed = 0
            failed = []
            
            for future in as_completed(futures):
                completed += 1
                task = futures[future]
                
                try:
                    success = future.result()
                    if not success:
                        failed.append(task.filename)
                except Exception as e:
                    logger.error(f"Unexpected error for {task.filename}: {e}")
                    failed.append(task.filename)
                
                logger.info(f"Progress: {completed}/{len(tasks)} files")
        
        if failed:
            logger.warning(f"
Failed downloads: {', '.join(failed)}")


def main():
    """Entry point"""
    try:
        manager = DownloadManager()
        manager.run()
    except KeyboardInterrupt:
        logger.info("

Download cancelled by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
