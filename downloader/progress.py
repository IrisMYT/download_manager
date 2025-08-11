from tqdm import tqdm

class DownloadProgress:
    def __init__(self, total_size, filename):
        self.pbar = tqdm(
            total=total_size,
            unit='B',
            unit_scale=True,
            unit_divisor=1024,
            desc=filename,
            ascii=True
        )

    def update(self, size):
        self.pbar.update(size)

    def close(self):
        self.pbar.close()
