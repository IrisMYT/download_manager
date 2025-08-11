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
            backoff_factor=1.5,  # Increased backoff
            status_forcelist=[429, 500, 502, 503, 504],
            raise_on_status=False
        )
        adapter = HTTPAdapter(
            max_retries=retry,
            pool_connections=20,
            pool_maxsize=20
        )
        s.mount('http://', adapter)
        s.mount('https://', adapter)
        return s

    def _get_filename_from_headers(self, headers, url):
        """Extract filename from Content-Disposition header or URL"""
        content_disposition = headers.get('content-disposition', '')
        if 'filename=' in content_disposition:
            # Extract filename from Content-Disposition header
            filename_start = content_disposition.find('filename=')
            if filename_start != -1:
                filename = content_disposition[filename_start + 9:]
                # Handle quoted filenames
                if filename.startswith('"') and filename.endswith('"'):
                    filename = filename[1:-1]
                return unquote(filename)
        
        # Fallback to URL-based extraction
        parsed = urlparse(url)
        name = os.path.basename(parsed.path)
        return unquote(name) if name else f"file_{int(time.time())}"

    def get_info(self, url):
        session = self._create_session()
        try:
            r = session.head(url, timeout=self.config.timeout, allow_redirects=True)
            r.raise_for_status()
            
            # Get filename from headers or URL
            filename = self._get_filename_from_headers(r.headers, url)
            
            size = int(r.headers.get('content-length', 0))
            range_ok = 'bytes' in r.headers.get('Accept-Ranges', '')
            
            logger.info(f"File info - Name: {filename}, Size: {size}, Range support: {range_ok}")
        except Exception as e:
            logger.warning(f"Failed to get file info: {e}")
            # Try GET request as fallback
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

    def _optimal_threads_chunk(self, size):
        if size < 500 * 1024 * 1024:  # < 500MB
            return 4, 512 * 1024
        elif size < 2 * 1024 * 1024 * 1024:  # < 2GB
            return 8, 1 * 1024 * 1024
        elif size < 5 * 1024 * 1024 * 1024:  # < 5GB
            return 12, 2 * 1024 * 1024
        else:  # >= 5GB
            return 16, 4 * 1024 * 1024

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
        
        threads, chunk_size = self._optimal_threads_chunk(size)

        if size > 0 and range_ok and threads > 1:
            return self._multi(url, filepath, size, threads, chunk_size)
        else:
            return self._single(url, filepath)

    def _single(self, url, filepath):
        session = self._create_session()
        try:
            with session.get(url, stream=True, timeout=self.config.timeout) as r:
                r.raise_for_status()
                total_size = int(r.headers.get('content-length', 0))
                progress = DownloadProgress(total_size, os.path.basename(filepath))
                with open(filepath, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                            progress.update(len(chunk))
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

        def dl_chunk(idx, start, end):
            # Create a new session for each chunk to avoid connection issues
            session = self._create_session()
            headers = {'Range': f'bytes={start}-{end}'}
            temp_filepath = f"{filepath}.part{idx}"
            
            try:
                # Check if part already exists and is complete
                if os.path.exists(temp_filepath):
                    existing_size = os.path.getsize(temp_filepath)
                    if existing_size == (end - start + 1):
                        logger.info(f"Chunk {idx} already downloaded")
                        # Update progress for existing chunk
                        try:
                            self.progress.update(existing_size)
                        except:
                            pass
                        session.close()
                        return True
                    elif existing_size > 0:
                        # Resume from where it left off
                        headers['Range'] = f'bytes={start + existing_size}-{end}'
                
                with session.get(url, headers=headers, stream=True, timeout=self.config.timeout) as r:
                    r.raise_for_status()
                    mode = 'ab' if os.path.exists(temp_filepath) else 'wb'
                    with open(temp_filepath, mode) as f:
                        for chunk in r.iter_content(chunk_size=64*1024):  # Larger chunk size for better throughput
                            if chunk:
                                f.write(chunk)
                                try:
                                    self.progress.update(len(chunk))
                                except:
                                    pass
                return True
            except Exception as e:
                logger.warning(f"Chunk {idx} failed: {e}")
                return False
            finally:
                session.close()

        self.progress = DownloadProgress(size, os.path.basename(filepath))
        try:
            with ThreadPoolExecutor(max_workers=min(threads, 8)) as ex:  # Reduced max workers
                results = list(ex.map(lambda c: dl_chunk(*c), parts))
        finally:
            self.progress.close()

        if all(results):
            self._merge(filepath, len(parts))
            return True
        return False

    def _make_chunks(self, size, threads):
        step = size // threads
        return [(i, i * step, (i + 1) * step - 1 if i < threads - 1 else size - 1) for i in range(threads)]

    def _merge(self, filepath, parts):
        try:
            with open(filepath, 'wb') as out:
                for i in range(parts):
                    part_file = f"{filepath}.part{i}"
                    if os.path.exists(part_file):
                        with open(part_file, 'rb') as pf:
                            out.write(pf.read())
                        os.remove(part_file)
            logger.info(f"Merged {parts} parts into {filepath}")
        except Exception as e:
            logger.error(f"Failed to merge file parts: {e}")
            raise
