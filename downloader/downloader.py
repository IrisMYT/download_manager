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
        self.session = self._session()

    def _session(self):
        s = requests.Session()
        retry = Retry(
            total=self.config.retry_attempts,
            backoff_factor=0.5,
            status_forcelist=[500, 502, 503, 504]
        )
        adapter = HTTPAdapter(max_retries=retry)
        s.mount('http://', adapter)
        s.mount('https://', adapter)
        return s

    def _get_name(self, url):
        parsed = urlparse(url)
        name = os.path.basename(parsed.path)
        return unquote(name) if name else f"file_{int(time.time())}"

    def get_info(self, url):
        filename = self._get_name(url)
        try:
            r = self.session.head(url, timeout=self.config.timeout, allow_redirects=True)
            size = int(r.headers.get('content-length', 0))
            range_ok = 'bytes' in r.headers.get('Accept-Ranges', '')
        except:
            size, range_ok = 0, False
        return filename, size, range_ok

    def _optimal_threads_chunk(self, size):
        if size < 500 * 1024 * 1024:        # < 500 MB
            return 4, 512 * 1024
        elif size < 2 * 1024 * 1024 * 1024: # < 2 GB
            return 8, 1 * 1024 * 1024
        elif size < 5 * 1024 * 1024 * 1024: # < 5 GB
            return 16, 2 * 1024 * 1024
        else:                               # >= 5 GB
            return 32, 4 * 1024 * 1024

    def download(self, url, dest_dir):
        filename, size, range_ok = self.get_info(url)
        filepath = os.path.join(dest_dir, filename)
        threads, chunk_size = self._optimal_threads_chunk(size)

        if size > 0 and range_ok:
            return self._multi(url, filepath, size, threads, chunk_size)
        else:
            return self._single(url, filepath)

    def _single(self, url, filepath):
        try:
            with self.session.get(url, stream=True, timeout=self.config.timeout) as r:
                r.raise_for_status()
                progress = DownloadProgress(int(r.headers.get('content-length', 0)), os.path.basename(filepath))
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

    def _multi(self, url, filepath, size, threads, chunk_size):
        parts = self._make_chunks(size, threads)

        def dl_chunk(idx, start, end):
            headers = {'Range': f'bytes={start}-{end}'}
            try:
                with self.session.get(url, headers=headers, stream=True, timeout=self.config.timeout) as r:
                    r.raise_for_status()
                    with open(f"{filepath}.part{idx}", 'wb') as f:
                        for chunk in r.iter_content(chunk_size=chunk_size):
                            if chunk:
                                f.write(chunk)
                                self.progress.update(len(chunk))
                return True
            except Exception as e:
                logger.warning(f"Chunk {idx} failed: {e}")
                return False

        self.progress = DownloadProgress(size, os.path.basename(filepath))
        with ThreadPoolExecutor(max_workers=threads) as ex:
            results = list(ex.map(lambda c: dl_chunk(*c), parts))
        self.progress.close()

        if all(results):
            self._merge(filepath, len(parts))
            return True
        return False

    def _make_chunks(self, size, threads):
        step = size // threads
        return [(i, i * step, (i + 1) * step - 1 if i < threads - 1 else size - 1) for i in range(threads)]

    def _merge(self, filepath, parts):
        with open(filepath, 'wb') as out:
            for i in range(parts):
                with open(f"{filepath}.part{i}", 'rb') as pf:
                    out.write(pf.read())
                os.remove(f"{filepath}.part{i}")
