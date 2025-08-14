import os
import time
import logging
import hashlib
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urlparse, unquote
from dataclasses import dataclass
from typing import Optional, Tuple, Callable
import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

logger = logging.getLogger(__name__)

@dataclass
class DownloadTask:
    id: str
    url: str
    filename: str
    filepath: str
    total_size: int
    downloaded_size: int
    status: str  # 'pending', 'downloading', 'paused', 'completed', 'failed'
    speed: float
    progress: float
    error: Optional[str] = None
    supports_resume: bool = True
    start_time: Optional[float] = None
    eta: Optional[int] = None

class FileDownloader:
    def __init__(self, config_manager):
        self.config_manager = config_manager
        self.active_downloads = {}
        self.download_lock = threading.Lock()
        self.pause_events = {}
        self.cancel_events = {}
        
    def _create_session(self):
        s = requests.Session()
        retry = Retry(
            total=self.config_manager.config.retry_attempts,
            backoff_factor=2.0,
            status_forcelist=[429, 500, 502, 503, 504],
            raise_on_status=False
        )
        adapter = HTTPAdapter(
            max_retries=retry,
            pool_connections=30,
            pool_maxsize=30
        )
        s.mount('http://', adapter)
        s.mount('https://', adapter)
        
        # Set user agent
        s.headers.update({
            'User-Agent': self.config_manager.settings.user_agent
        })
        
        # Set proxy if configured
        if self.config_manager.settings.proxy:
            s.proxies = {
                'http': self.config_manager.settings.proxy,
                'https': self.config_manager.settings.proxy
            }
        
        return s
    
    def generate_task_id(self, url: str) -> str:
        return hashlib.md5(f"{url}_{time.time()}".encode()).hexdigest()[:12]
    
    def _get_filename_from_url(self, url: str, headers: dict) -> str:
        """Extract filename from headers or URL"""
        content_disposition = headers.get('content-disposition', '')
        if 'filename=' in content_disposition:
            parts = content_disposition.split('filename=')
            if len(parts) > 1:
                filename = parts[1].strip('"'')
                return unquote(filename)
        
        parsed = urlparse(url)
        filename = os.path.basename(parsed.path)
        return unquote(filename) if filename else f"download_{int(time.time())}"
    
    def get_file_info(self, url: str) -> Tuple[str, int, bool]:
        """Get file information from URL"""
        session = self._create_session()
        try:
            # Try HEAD request first
            r = session.head(url, timeout=self.config_manager.config.timeout, allow_redirects=True)
            
            if r.status_code >= 400:
                # Fallback to GET with stream
                r = session.get(url, timeout=self.config_manager.config.timeout, stream=True)
            
            r.raise_for_status()
            
            filename = self._get_filename_from_url(url, r.headers)
            size = int(r.headers.get('content-length', 0))
            supports_range = 'bytes' in r.headers.get('accept-ranges', '').lower()
            
            return filename, size, supports_range
            
        except Exception as e:
            logger.error(f"Failed to get file info: {e}")
            return f"download_{int(time.time())}", 0, False
        finally:
            session.close()
    
    def create_download_task(self, url: str) -> DownloadTask:
        """Create a new download task"""
        task_id = self.generate_task_id(url)
        filename, size, supports_resume = self.get_file_info(url)
        
        # Handle filename conflicts
        filepath = os.path.join(self.config_manager.config.download_dir, filename)
        counter = 1
        base_filepath = filepath
        while os.path.exists(filepath):
            name, ext = os.path.splitext(base_filepath)
            filepath = f"{name}_{counter}{ext}"
            counter += 1
        
        task = DownloadTask(
            id=task_id,
            url=url,
            filename=os.path.basename(filepath),
            filepath=filepath,
            total_size=size,
            downloaded_size=0,
            status='pending',
            speed=0.0,
            progress=0.0,
            supports_resume=supports_resume
        )
        
        with self.download_lock:
            self.active_downloads[task_id] = task
            self.pause_events[task_id] = threading.Event()
            self.pause_events[task_id].set()  # Not paused by default
            self.cancel_events[task_id] = threading.Event()
        
        return task
    
    def download(self, task_id: str, progress_callback: Optional[Callable] = None):
        """Start downloading a task"""
        task = self.active_downloads.get(task_id)
        if not task:
            return False
        
        task.status = 'downloading'
        task.start_time = time.time()
        
        try:
            settings = self.config_manager.settings
            
            # Determine if we should use multi-threaded download
            if (task.total_size > settings.min_split_size and 
                task.supports_resume and 
                settings.global_chunk_number > 1):
                
                success = self._multi_threaded_download(
                    task, 
                    settings.global_chunk_number,
                    settings.global_chunk_size,
                    progress_callback
                )
            else:
                success = self._single_threaded_download(task, progress_callback)
            
            if success:
                task.status = 'completed'
                task.progress = 100.0
            else:
                task.status = 'failed'
                
            return success
            
        except Exception as e:
            logger.error(f"Download error for {task_id}: {e}")
            task.status = 'failed'
            task.error = str(e)
            return False
    
    def _single_threaded_download(self, task: DownloadTask, progress_callback: Optional[Callable]) -> bool:
        """Download file in a single thread"""
        session = self._create_session()
        
        try:
            # Check for existing partial download
            headers = {}
            mode = 'wb'
            
            if os.path.exists(task.filepath):
                existing_size = os.path.getsize(task.filepath)
                if existing_size < task.total_size and task.supports_resume:
                    headers['Range'] = f'bytes={existing_size}-'
                    mode = 'ab'
                    task.downloaded_size = existing_size
            
            with session.get(task.url, headers=headers, stream=True, timeout=self.config_manager.config.timeout) as r:
                r.raise_for_status()
                
                with open(task.filepath, mode) as f:
                    chunk_size = self.config_manager.settings.global_chunk_size
                    last_update = time.time()
                    bytes_since_last_update = 0
                    
                    for chunk in r.iter_content(chunk_size=chunk_size):
                        # Check for pause
                        self.pause_events[task.id].wait()
                        
                        # Check for cancel
                        if self.cancel_events[task.id].is_set():
                            return False
                        
                        if chunk:
                            f.write(chunk)
                            chunk_len = len(chunk)
                            task.downloaded_size += chunk_len
                            bytes_since_last_update += chunk_len
                            
                            # Update progress
                            current_time = time.time()
                            if current_time - last_update >= 0.5:  # Update every 0.5 seconds
                                elapsed = current_time - last_update
                                task.speed = bytes_since_last_update / elapsed
                                task.progress = (task.downloaded_size / task.total_size * 100) if task.total_size > 0 else 0
                                
                                # Calculate ETA
                                if task.speed > 0:
                                    remaining_bytes = task.total_size - task.downloaded_size
                                    task.eta = int(remaining_bytes / task.speed)
                                
                                if progress_callback:
                                    progress_callback(task)
                                
                                last_update = current_time
                                bytes_since_last_update = 0
                                
                                # Apply speed limit if set
                                if self.config_manager.settings.max_speed_limit > 0:
                                    if task.speed > self.config_manager.settings.max_speed_limit * 1024:
                                        sleep_time = (chunk_len / (self.config_manager.settings.max_speed_limit * 1024)) - elapsed
                                        if sleep_time > 0:
                                            time.sleep(sleep_time)
            
            return True
            
        except Exception as e:
            logger.error(f"Single-threaded download failed: {e}")
            task.error = str(e)
            return False
        finally:
            session.close()
    
    def _multi_threaded_download(self, task: DownloadTask, num_threads: int, chunk_size: int, progress_callback: Optional[Callable]) -> bool:
        """Download file using multiple threads"""
        chunks = self._calculate_chunks(task.total_size, num_threads)
        chunk_progress = {i: 0 for i in range(len(chunks))}
        chunk_lock = threading.Lock()
        
        def download_chunk(chunk_info):
            idx, start, end = chunk_info
            session = self._create_session()
            headers = {'Range': f'bytes={start}-{end}'}
            temp_filepath = f"{task.filepath}.part{idx}"
            
            try:
                # Check if chunk already exists
                if os.path.exists(temp_filepath):
                    existing_size = os.path.getsize(temp_filepath)
                    if existing_size == (end - start + 1):
                        with chunk_lock:
                            chunk_progress[idx] = existing_size
                        return True
                    elif existing_size > 0:
                        headers['Range'] = f'bytes={start + existing_size}-{end}'
                        with chunk_lock:
                            chunk_progress[idx] = existing_size
                
                mode = 'ab' if os.path.exists(temp_filepath) else 'wb'
                
                with session.get(task.url, headers=headers, stream=True, timeout=self.config_manager.config.timeout) as r:
                    r.raise_for_status()
                    
                    with open(temp_filepath, mode) as f:
                        for chunk in r.iter_content(chunk_size=chunk_size):
                            # Check for pause
                            self.pause_events[task.id].wait()
                            
                            # Check for cancel
                            if self.cancel_events[task.id].is_set():
                                return False
                            
                            if chunk:
                                f.write(chunk)
                                with chunk_lock:
                                    chunk_progress[idx] += len(chunk)
                
                return True
                
            except Exception as e:
                logger.error(f"Chunk {idx} download failed: {e}")
                return False
            finally:
                session.close()
        
        # Progress monitoring thread
        def monitor_progress():
            last_total = 0
            last_time = time.time()
            
            while task.status == 'downloading':
                time.sleep(0.5)
                
                with chunk_lock:
                    total_downloaded = sum(chunk_progress.values())
                
                current_time = time.time()
                elapsed = current_time - last_time
                
                if elapsed > 0:
                    bytes_diff = total_downloaded - last_total
                    task.speed = bytes_diff / elapsed
                    task.downloaded_size = total_downloaded
                    task.progress = (total_downloaded / task.total_size * 100) if task.total_size > 0 else 0
                    
                    if task.speed > 0:
                        remaining = task.total_size - total_downloaded
                        task.eta = int(remaining / task.speed)
                    
                    if progress_callback:
                        progress_callback(task)
                    
                    last_total = total_downloaded
                    last_time = current_time
        
        # Start progress monitoring
        monitor_thread = threading.Thread(target=monitor_progress)
        monitor_thread.daemon = True
        monitor_thread.start()
        
        # Download chunks
        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(download_chunk, chunk) for chunk in chunks]
            results = [f.result() for f in as_completed(futures)]
        
        if all(results):
            # Merge chunks
            return self._merge_chunks(task.filepath, len(chunks))
        
        return False
    
    def _calculate_chunks(self, total_size: int, num_threads: int) -> list:
        """Calculate chunk ranges for multi-threaded download"""
        chunk_size = total_size // num_threads
        chunks = []
        
        for i in range(num_threads):
            start = i * chunk_size
            end = start + chunk_size - 1 if i < num_threads - 1 else total_size - 1
            chunks.append((i, start, end))
        
        return chunks
    
    def _merge_chunks(self, filepath: str, num_chunks: int) -> bool:
        """Merge downloaded chunks into final file"""
        try:
            with open(filepath, 'wb') as outfile:
                for i in range(num_chunks):
                    chunk_file = f"{filepath}.part{i}"
                    if os.path.exists(chunk_file):
                        with open(chunk_file, 'rb') as infile:
                            outfile.write(infile.read())
                        os.remove(chunk_file)
                    else:
                        logger.error(f"Missing chunk file: {chunk_file}")
                        return False
            
            logger.info(f"Successfully merged {num_chunks} chunks into {filepath}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to merge chunks: {e}")
            return False
    
    def pause_download(self, task_id: str):
        """Pause a download"""
        if task_id in self.pause_events:
            self.pause_events[task_id].clear()
            if task_id in self.active_downloads:
                self.active_downloads[task_id].status = 'paused'
    
    def resume_download(self, task_id: str):
        """Resume a paused download"""
        if task_id in self.pause_events:
            self.pause_events[task_id].set()
            if task_id in self.active_downloads:
                self.active_downloads[task_id].status = 'downloading'
    
    def cancel_download(self, task_id: str):
        """Cancel a download"""
        if task_id in self.cancel_events:
            self.cancel_events[task_id].set()
        if task_id in self.active_downloads:
            self.active_downloads[task_id].status = 'cancelled'
    
    def get_task_status(self, task_id: str) -> Optional[DownloadTask]:
        """Get current status of a download task"""
        return self.active_downloads.get(task_id)
