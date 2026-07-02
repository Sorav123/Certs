"""
Downloader

Responsibilities
----------------
- Download ZIP files
- Calculate SHA256
- Save into temp folder
- Retry failed downloads
"""

from __future__ import annotations

import hashlib
import shutil
import time
from pathlib import Path

import requests


TEMP_DIR = Path("temp")
TEMP_DIR.mkdir(exist_ok=True)

CHUNK_SIZE = 1024 * 1024
TIMEOUT = 120
MAX_RETRIES = 3


class DownloadError(Exception):
    pass


class DownloadResult:

    def __init__(
        self,
        file_path: Path,
        sha256: str,
        size: int,
    ):
        self.file_path = file_path
        self.sha256 = sha256
        self.size = size


class Downloader:

    def __init__(self):

        self.session = requests.Session()

        self.session.headers.update(
            {
                "User-Agent": "CertSync/1.0"
            }
        )

    # ----------------------------------------

    def download(
        self,
        url: str,
        filename: str,
    ) -> DownloadResult:

        destination = TEMP_DIR / filename

        if destination.exists():
            destination.unlink()

        last_error = None

        for retry in range(MAX_RETRIES):

            try:

                return self._download_once(
                    url,
                    destination,
                )

            except Exception as exc:

                last_error = exc

                if destination.exists():
                    destination.unlink()

                time.sleep(2 * (retry + 1))

        raise DownloadError(str(last_error))

    # ----------------------------------------

    def _download_once(
        self,
        url,
        destination,
    ) -> DownloadResult:

        sha = hashlib.sha256()

        total = 0

        with self.session.get(
            url,
            stream=True,
            timeout=TIMEOUT,
        ) as response:

            response.raise_for_status()

            with open(destination, "wb") as fp:

                for chunk in response.iter_content(
                    chunk_size=CHUNK_SIZE
                ):

                    if not chunk:
                        continue

                    fp.write(chunk)

                    sha.update(chunk)

                    total += len(chunk)

        return DownloadResult(
            destination,
            sha.hexdigest(),
            total,
        )

    # ----------------------------------------

    @staticmethod
    def remove(path: Path):

        if path.exists():

            if path.is_file():
                path.unlink()

            else:
                shutil.rmtree(path)


downloader = Downloader()
