import os
import requests
import threading
import time
from typing import Optional, Dict, List, Callable
from urllib.parse import urlparse, unquote

class Downloader:
    def __init__(self, url: str, output_path: str, config: Dict):
        self.url = url
        self.output_path = output_path
        self.config = config
        self.filename = ""
        self.total_size = 0
        self.downloaded_size = 0
        self.chunks: List[Dict] = []
        self.active_chunks = 0
        self.paused = False
        self.cancelled = False
        self.error: Optional[str] = None
        self.progress_callback: Optional[Callable] = None
        self.start_time = time.time()
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': config.user_agent or 'Mozilla/5.0'
        })
        
        if config.proxy:
            self.session.proxies = {
                'http': config.proxy,
                'https': config.proxy
            }

    def download(self) -> bool:
        """Main download method"""
        try:
            # Get file info
            response = self.session.head(self.url, allow_redirects=True, timeout=30)
            
            # Handle redirects
            if response.status_code in [301, 302, 303, 307, 308]:
                self.url = response.headers.get('Location', self.url)
                response = self.session.head(self.url, allow_redirects=True, timeout=30)
            
            if response.status_code != 200:
                # Try GET request instead
                response = self.session.get(self.url, stream=True, timeout=30)
                if response.status_code != 200:
                    self.error = f"HTTP {response.status_code}"
                    return False
            
            # Get filename
            self.filename = self._get_filename(response)
            
            # Get file size
            self.total_size = int(response.headers.get('Content-Length', 0))
            
            # Check if server supports range requests
            supports_range = response.headers.get('Accept-Ranges') == 'bytes'
            
            # Determine download method
            if supports_range and self.total_size > self.config.min_split_size:
                return self._multi_part_download()
            else:
                return self._single_part_download()
                
        except requests.exceptions.RequestException as e:
            self.error = f"Network error: {str(e)}"
            return False
        except Exception as e:
            self.error = f"Download error: {str(e)}"
            return False

    def _get_filename(self, response) -> str:
        """Extract filename from response or URL"""
        # Try Content-Disposition header
        cd = response.headers.get('Content-Disposition')
        if cd:
            parts = cd.split('filename=')
            if len(parts) > 1:
                filename = parts[1].strip('"\'')
                if filename:
                    return filename
        
        # Extract from URL
        parsed = urlparse(self.url)
        filename = os.path.basename(unquote(parsed.path))
        
        if not filename or '.' not in filename:
            filename = f"download_{int(time.time())}"
        
        return filename

    def _single_part_download(self) -> bool:
        """Download file in a single part"""
        try:
            filepath = os.path.join(self.output_path, self.filename)
            
            response = self.session.get(self.url, stream=True, timeout=self.config.timeout)
            
            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if self.cancelled:
                        return False
                    
                    while self.paused:
                        time.sleep(0.1)
                        if self.cancelled:
                            return False
                    
                    if chunk:
                        f.write(chunk)
                        self.downloaded_size += len(chunk)
                        
                        if self.progress_callback:
                            speed = self._calculate_speed()
                            self.progress_callback(
                                self.downloaded_size,
                                self.total_size,
                                speed
                            )
            
            return True
            
        except Exception as e:
            self.error = str(e)
            return False

    def _multi_part_download(self) -> bool:
        """Download file in multiple parts"""
        try:
            filepath = os.path.join(self.output_path, self.filename)
            
            # Calculate chunk size and count
            chunk_count = min(self.config.global_chunk_number, 
                             max(1, self.total_size // self.config.min_split_size))
            chunk_size = self.total_size // chunk_count
            
            # Create chunks
            self.chunks = []
            for i in range(chunk_count):
                start = i * chunk_size
                end = start + chunk_size - 1 if i < chunk_count - 1 else self.total_size - 1
                
                self.chunks.append({
                    'id': i,
                    'start': start,
                    'end': end,
                    'downloaded': 0,
                    'status': 'pending'
                })
            
            # Create temporary file
            with open(filepath + '.tmp', 'wb') as f:
                f.seek(self.total_size - 1)
                f.write(b'\0')
            
            # Download chunks in parallel
            threads = []
            for chunk in self.chunks:
                thread = threading.Thread(
                    target=self._download_chunk,
                    args=(chunk, filepath + '.tmp')
                )
                thread.start()
                threads.append(thread)
            
            # Wait for all threads
            for thread in threads:
                thread.join()
            
            # Check if all chunks completed
            if self.cancelled:
                os.remove(filepath + '.tmp')
                return False
            
            if all(chunk['status'] == 'completed' for chunk in self.chunks):
                os.rename(filepath + '.tmp', filepath)
                return True
            else:
                self.error = "Some chunks failed to download"
                return False
                
        except Exception as e:
            self.error = str(e)
            return False

    def _download_chunk(self, chunk: Dict, filepath: str):
        """Download a single chunk"""
        try:
            headers = {
                'Range': f"bytes={chunk['start']}-{chunk['end']}"
            }
            
            response = self.session.get(
                self.url,
                headers=headers,
                stream=True,
                timeout=self.config.timeout
            )
            
            if response.status_code not in [200, 206]:
                chunk['status'] = 'failed'
                return
            
            chunk['status'] = 'downloading'
            
            with open(filepath, 'r+b') as f:
                f.seek(chunk['start'])
                
                for data in response.iter_content(chunk_size=8192):
                    if self.cancelled:
                        chunk['status'] = 'cancelled'
                        return
                    
                    while self.paused:
                        time.sleep(0.1)
                        if self.cancelled:
                            chunk['status'] = 'cancelled'
                            return
                    
                    if data:
                        f.write(data)
                        chunk['downloaded'] += len(data)
                        self.downloaded_size += len(data)
                        
                        if self.progress_callback:
                            speed = self._calculate_speed()
                            self.progress_callback(
                                self.downloaded_size,
                                self.total_size,
                                speed
                            )
            
            chunk['status'] = 'completed'
            
        except Exception as e:
            chunk['status'] = 'failed'
            chunk['error'] = str(e)

    def _calculate_speed(self) -> float:
        """Calculate download speed in bytes per second"""
        elapsed = time.time() - self.start_time
        if elapsed > 0:
            return self.downloaded_size / elapsed
        return 0

    def pause(self):
        """Pause the download"""
        self.paused = True

    def resume(self):
        """Resume the download"""
        self.paused = False

    def cancel(self):
        """Cancel the download"""
        self.cancelled = True
