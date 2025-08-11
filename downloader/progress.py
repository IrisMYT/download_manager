from tqdm import tqdm
import time

class DownloadProgress:
    def __init__(self, total_size, filename):
        self.start_time = time.time()
        self.pbar = tqdm(
            total=total_size,
            unit='B',
            unit_scale=True,
            unit_divisor=1024,
            desc=filename,
            ascii=True,
            bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}, {rate_fmt}]"
        )

    def update(self, size):
        self.pbar.update(size)

    def close(self):
        self.pbar.close()
