"""
ZIP Extraction Engine

Features
--------
- Secure extraction (Zip Slip protection)
- Recursive file discovery
- Cleanup
- Empty folder removal
- ZIP rebuild
"""

from __future__ import annotations

import shutil
import zipfile
from pathlib import Path


TEMP_DIR = Path("temp")
OUTPUT_DIR = Path("output")

TEMP_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)


KEEP_EXTENSIONS = {
    ".p12",
    ".mobileprovision",
}


class PackageValidationError(Exception):
    pass


class Package:

    def __init__(
        self,
        root: Path,
        p12: Path,
        mobileprovision: Path,
    ):

        self.root = root
        self.p12 = p12
        self.mobileprovision = mobileprovision
