import os
import time
import logging
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlparse, unquote
import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
from .progress import DownloadProgress

logger = logging.getLogger(__name__)

class FileDownloader:
    def __init__(self, config):
        self.config = config

    def _create_session(self):
        s = requests.Session()
        retry = Retry(
            total=self.config.retry_attempts,
            backoff_factor=2.0,
            status_forcelist=[429, 500, 502, 503, 504],
            raise_on_status=False
        )
        adapter = HTTPAdapter(
            max_retries=retry,
            pool_connections=32,
            pool_maxsize=32
        )
        s.mount('http://', adapter)
        s.mount('https://', adapter)
        return s

    def _get_filename_from_headers(self, headers, url):
        """Extract filename from Content-Disposition header or URL"""
        content_disposition = headers.get('content-disposition', '')
        if 'filename=' in content_disposition:
            filename_start = content_disposition.find('filename=')
            if filename_start != -1:
                filename = content_disposition[filename_start + 9:]
                if filename.startswith('"') and filename.endswith('"'):
                    filename = filename[1:-1]
                return unquote(filename)
        
        parsed = urlparse(url)
        name = os.path.basename(parsed.path)
        return unquote(name) if name else f"file_{int(time.time())}"

    def get_info(self, url):
        session = self._create_session()
        try:
            r = session.head(url, timeout=self.config.timeout, allow_redirects=True)
            r.raise_for_status()
            filename = self._get_filename_from_headers(r.headers, url)
            size = int(r.headers.get('content-length', 0))
            range_ok = 'bytes' in r.headers.get('Accept-Ranges', '')
            logger.info(f"File info - Name: {filename}, Size: {size}, Range support: {range_ok}")
        except Exception as e:
            logger.warning(f"Failed to get file info with HEAD: {e}")
            try:
                r = session.get(url, timeout=self.config.timeout, stream=True)
                r.raise_for_status()
                filename = self._get_filename_from_headers(r.headers, url)
                size = int(r.headers.get('content-length', 0))
                range_ok = 'bytes' in r.headers.get('Accept-Ranges', '')
            except Exception as e2:
                logger.error(f"Failed to get file info with GET request: {e2}")
                filename, size, range_ok = f"file_{int(time.time())}", 0, False
        finally:
            session.close()
        return filename, size, range_ok

    def download(self, url, dest_dir):
        filename, size, range_ok = self.get_info(url)
        filepath = os.path.join(dest_dir, filename)
        
        # Handle filename conflicts
        counter = 1
        original_filepath = filepath
        while os.path.exists(filepath):
            name, ext = os.path.splitext(original_filepath)
            filepath = f"{name}_{counter}{ext}"
            counter += 1

        # Use 32 chunks for all files (except very small ones)
        if size > 0 and range_ok and size > 10*1024*1024:  # > 10MB
            return self._multi(url, filepath, size, 32, 1024*1024)  # 32 chunks, 1MB each
        else:
            return self._single_with_anti_throttling(url, filepath)

    def _single_with_anti_throttling(self, url, filepath):
        session = self._create_session()
        try:
            with session.get(url, stream=True, timeout=self.config.timeout) as r:
                r.raise_for_status()
                total_size = int(r.headers.get('content-length', 0))
                progress = DownloadProgress(total_size, os.path.basename(filepath))
                
                downloaded = 0
                last_downloaded = 0
                last_time = time.time()
                speed_history = []
                throttle_detected = False
                throttle_pause_done = False
                
                with open(filepath, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=64*1024):  # 64KB chunks
                        if chunk:
                            f.write(chunk)
                            downloaded += len(chunk)
                            progress.update(len(chunk))
                            
                            # Real-time speed monitoring
                            current_time = time.time()
                            if current_time - last_time >= 1.0:  # Check every second
                                speed = (downloaded - last_downloaded) / (current_time - last_time)
                                speed_history.append(speed)
                                
                                # Keep only last 5 speed measurements
                                if len(speed_history) > 5:
                                    speed_history.pop(0)
                                
                                # Detect throttling (speed dropped significantly)
                                if len(speed_history) >= 3:
                                    avg_speed = sum(speed_history[:-1]) / (len(speed_history) - 1)
                                    if speed < avg_speed * 0.3 and speed < 1024 * 1024:  # Less than 30% of avg and < 1MB/s
                                        if not throttle_detected:
                                            logger.info(f"Throttling detected! Current speed: {speed/1024/1024:.2f} MB/s, Average: {avg_speed/1024/1024:.2f} MB/s")
                                            throttle_detected = True
                                
                                last_downloaded = downloaded
                                last_time = current_time
                            
                            # Specific percentage-based pause (anti-throttling)
                            if total_size > 0:
                                percentage = downloaded / total_size
                                if percentage >= 0.92 and percentage < 0.94 and not throttle_pause_done:
                                    logger.info(f"Anti-throttling: Strategic pause at {percentage:.1%}")
                                    progress.close()
                                    time.sleep(5)
                                    # Create new progress bar after pause
                                    progress = DownloadProgress(total_size, os.path.basename(filepath))
                                    progress.update(downloaded)
                                    logger.info("Resuming after strategic pause")
                                    throttle_pause_done = True
                                    # Reset speed monitoring after pause
                                    speed_history = []
                                    last_downloaded = downloaded
                                    last_time = time.time()
                
                progress.close()
            logger.info(f"✓ {filepath}")
            return True
        except Exception as e:
            logger.error(f"Failed {filepath}: {e}")
            return False
        finally:
            session.close()

    def _multi(self, url, filepath, size, threads, chunk_size):
        parts = self._make_chunks(size, threads)
        completed_parts = [False] * len(parts)
        part_progress = [0] * len(parts)

        def dl_chunk(idx, start, end):
            # Create a new session for each chunk
            session = self._create_session()
            headers = {'Range': f'bytes={start}-{end}'}
            temp_filepath = f"{filepath}.part{idx}"
            
            try:
                with session.get(url, headers=headers, stream=True, timeout=self.config.timeout) as r:
                    r.raise_for_status()
                    downloaded = 0
                    last_downloaded = 0
                    last_time = time.time()
                    speed_history = []
                    throttle_detected = False
                    throttle_pause_done = False
                    
                    with open(temp_filepath, 'wb') as f:
                        for chunk in r.iter_content(chunk_size=64*1024):  # 64KB chunks
                            if chunk:
                                f.write(chunk)
                                downloaded += len(chunk)
                                part_progress[idx] = downloaded
                                
                                try:
                                    self.progress.update(len(chunk))
                                except:
                                    pass
                                
                                # Real-time speed monitoring for chunks too
                                current_time = time.time()
                                if current_time - last_time >= 1.0:
                                    speed = (downloaded - last_downloaded) / (current_time - last_time)
                                    speed_history.append(speed)
                                    
                                    if len(speed_history) > 5:
                                        speed_history.pop(0)
                                    
                                    if len(speed_history) >= 3:
                                        avg_speed = sum(speed_history[:-1]) / (len(speed_history) - 1)
                                        if speed < avg_speed * 0.3 and speed < 512 * 1024:  # Throttling detection
                                            if not throttle_detected:
                                                logger.info(f"Chunk {idx} throttling detected! Speed: {speed/1024:.0f} KB/s")
                                                throttle_detected = True
                                    
                                    last_downloaded = downloaded
                                    last_time = current_time
                                
                                # Anti-throttling pause for chunks at 92-94%
                                chunk_size_bytes = end - start + 1
                                if chunk_size_bytes > 0:
                                    percentage = downloaded / chunk_size_bytes
                                    if percentage >= 0.92 and percentage < 0.94 and not throttle_pause_done:
                                        logger.info(f"Chunk {idx}: Anti-throttling pause at {percentage:.1%}")
                                        time.sleep(3)
                                        throttle_pause_done = True
                    
                    completed_parts[idx] = True
                    return True
            except Exception as e:
                logger.warning(f"Chunk {idx} failed: {e}")
                return False
            finally:
                session.close()

        # Create progress bar with custom format that shows real-time speed
        self.progress = DownloadProgress(size, os.path.basename(filepath))
        
        try:
            with ThreadPoolExecutor(max_workers=min(threads, 16)) as ex:  # Cap at 16 concurrent workers