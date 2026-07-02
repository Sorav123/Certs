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

class Extractor:

    @staticmethod
    def extract(zip_path: Path) -> Path:

        workdir = TEMP_DIR / zip_path.stem

        if workdir.exists():
            shutil.rmtree(workdir)

        workdir.mkdir(parents=True)

        with zipfile.ZipFile(zip_path) as archive:

            for member in archive.infolist():

                target = (workdir / member.filename).resolve()

                if not str(target).startswith(str(workdir.resolve())):
                    raise PackageValidationError(
                        f"Unsafe ZIP entry: {member.filename}"
                    )

                archive.extract(member, workdir)

        return workdir

    @staticmethod
    def discover(workdir: Path) -> Package:

        p12 = None
        mobile = None

        for file in workdir.rglob("*"):

            if not file.is_file():
                continue

            suffix = file.suffix.lower()

            if suffix == ".p12":

                if p12 is not None:
                    raise PackageValidationError(
                        "Multiple .p12 files found."
                    )

                p12 = file

            elif suffix == ".mobileprovision":

                if mobile is not None:
                    raise PackageValidationError(
                        "Multiple .mobileprovision files found."
                    )

                mobile = file

        if p12 is None:
            raise PackageValidationError(
                "Missing .p12"
            )

        if mobile is None:
            raise PackageValidationError(
                "Missing .mobileprovision"
            )

        return Package(
            workdir,
            p12,
            mobile,
        )

    @staticmethod
    def cleanup(workdir: Path):

        for file in workdir.rglob("*"):

            if not file.is_file():
                continue

            if file.suffix.lower() not in KEEP_EXTENSIONS:

                file.unlink()

    @staticmethod
    def remove_empty_dirs(workdir: Path):

        for folder in sorted(
            workdir.rglob("*"),
            reverse=True,
        ):

            if folder.is_dir():

                if not any(folder.iterdir()):

                    folder.rmdir()

    @staticmethod
    def build(package: Package, output_name: str) -> Path:

        output = OUTPUT_DIR / output_name

        if output.exists():
            output.unlink()

        with zipfile.ZipFile(
            output,
            "w",
            zipfile.ZIP_DEFLATED,
        ) as archive:

            archive.write(
                package.p12,
                package.p12.name,
            )

            archive.write(
                package.mobileprovision,
                package.mobileprovision.name,
            )

        return output


extractor = Extractor()
