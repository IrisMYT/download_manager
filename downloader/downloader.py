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
            backoff_factor=1.0,  # Increased backoff
            status_forcelist=[429, 500, 502, 503, 504],
            raise_on_status=False
        )
        adapter = HTTPAdapter(
            max_retries=retry,
            pool_connections=20,  # Increased pool size
            pool_maxsize=20
        )
        s.mount('http://', adapter)
        s.mount('https://', adapter)
        return s

    def _get_name(self, url):
        parsed = urlparse(url)
        name = os.path.basename(parsed.path)
        return unquote(name) if name else f"file_{int(time.time())}"

    def get_info(self, url):
        session = self._create_session()
        filename = self._get_name(url)
        try:
            r = session.head(url, timeout=self.config.timeout, allow_redirects=True)
            size = int(r.headers.get('content-length', 0))
            range_ok = 'bytes' in r.headers.get('Accept-Ranges', '')
        except Exception as e:
            logger.warning(f"Failed to get file info: {e}")
            size, range_ok = 0, False
        finally:
            session.close()
        return filename, size, range_ok

    def _optimal_threads_chunk(self, size):
        if size < 500 * 1024 * 1024:
            return 4, 512 * 1024
        elif size < 2 * 1024 * 1024 * 1024:
            return 8, 1 * 1024 * 1024
        elif size < 5 * 1024 * 1024 * 1024:
            return 16, 2 * 1024 * 1024
        else:
            return 32, 4 * 1024 * 1024

    def download(self, url, dest_dir):
        filename, size, range_ok = self.get_info(url)
        filepath = os.path.join(dest_dir, filename)
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
            # Create a new session for each chunk to avoid connection pool issues
            session = self._create_session()
            headers = {'Range': f'bytes={start}-{end}'}
            try:
                with session.get(url, headers=headers, stream=True, timeout=self.config.timeout) as r:
                    r.raise_for_status()
                    with open(f"{filepath}.part{idx}", 'wb') as f:
                        for chunk in r.iter_content(chunk_size=chunk_size):
                            if chunk:
                                f.write(chunk)
                                # Update progress safely
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
            with ThreadPoolExecutor(max_workers=min(threads, 16)) as ex:
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
        except Exception as e:
            logger.error(f"Failed to merge file parts: {e}")
            raise
