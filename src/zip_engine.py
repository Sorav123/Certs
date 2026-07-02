from __future__ import annotations

import shutil
import zipfile
from pathlib import Path


KEEP_EXTENSIONS = {
    ".p12",
    ".mobileprovision",
}


class ZipEngineError(Exception):
    pass


class ZipEngine:

    def extract(self, zip_path: Path, workdir: Path) -> Path:

        if workdir.exists():
            shutil.rmtree(workdir)

        workdir.mkdir(parents=True)

        with zipfile.ZipFile(zip_path, "r") as archive:

            for member in archive.infolist():

                target = (workdir / member.filename).resolve()

                if not str(target).startswith(str(workdir.resolve())):
                    raise ZipEngineError(
                        f"Unsafe ZIP entry: {member.filename}"
                    )

                archive.extract(member, workdir)

        return workdir

    # -----------------------------------------

    def locate(self, workdir: Path):

        p12 = None
        mobile = None

        for file in workdir.rglob("*"):

            if not file.is_file():
                continue

            name = file.name

            if name.startswith("._"):
                file.unlink()
                continue

            if "__MACOSX" in file.parts:
                continue

            ext = file.suffix.lower()

            if ext == ".p12":

                if p12:
                    raise ZipEngineError(
                        "Multiple .p12 files found."
                    )

                p12 = file

            elif ext == ".mobileprovision":

                if mobile:
                    raise ZipEngineError(
                        "Multiple .mobileprovision files found."
                    )

                mobile = file

        if not p12:
            raise ZipEngineError("Missing .p12")

        if not mobile:
            raise ZipEngineError(
                "Missing .mobileprovision"
            )

        return p12, mobile

    # -----------------------------------------

    def cleanup(self, workdir: Path):

        for file in workdir.rglob("*"):

            if not file.is_file():
                continue

            if file.suffix.lower() not in KEEP_EXTENSIONS:
                file.unlink()

        self._remove_empty_dirs(workdir)

    # -----------------------------------------

    def flatten(
        self,
        workdir: Path,
        p12: Path,
        mobile: Path,
    ):

        new_p12 = workdir / p12.name
        new_mobile = workdir / mobile.name

        if p12 != new_p12:
            shutil.move(str(p12), str(new_p12))

        if mobile != new_mobile:
            shutil.move(str(mobile), str(new_mobile))

        self._remove_empty_dirs(workdir)

        return new_p12, new_mobile

    # -----------------------------------------

    def build(
        self,
        workdir: Path,
        output_zip: Path,
    ):

        if output_zip.exists():
            output_zip.unlink()

        with zipfile.ZipFile(
            output_zip,
            "w",
            compression=zipfile.ZIP_DEFLATED,
        ) as archive:

            for file in sorted(workdir.iterdir()):

                if file.is_file():

                    archive.write(
                        file,
                        arcname=file.name,
                    )

        return output_zip

    # -----------------------------------------

    def process(
        self,
        source_zip: Path,
        output_zip: Path,
    ):

        workdir = output_zip.parent / source_zip.stem

        self.extract(source_zip, workdir)

        p12, mobile = self.locate(workdir)

        self.cleanup(workdir)

        self.flatten(
            workdir,
            p12,
            mobile,
        )

        self.build(
            workdir,
            output_zip,
        )

        shutil.rmtree(workdir)

        return output_zip

    # -----------------------------------------

    @staticmethod
    def _remove_empty_dirs(root: Path):

        for folder in sorted(
            root.rglob("*"),
            reverse=True,
        ):

            if folder.is_dir():

                if not any(folder.iterdir()):

                    folder.rmdir()
