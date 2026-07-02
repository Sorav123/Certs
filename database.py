from __future__ import annotations

import json
from pathlib import Path
from datetime import datetime


DB_DIR = Path(".certsync")
DB_DIR.mkdir(exist_ok=True)

DATABASE = DB_DIR / "database.json"


class Database:

    def __init__(self):

        if not DATABASE.exists():

            DATABASE.write_text(
                "{}",
                encoding="utf8",
            )

        self.reload()

    # -------------------------

    def reload(self):

        self.data = json.loads(
            DATABASE.read_text(
                encoding="utf8"
            )
        )

    # -------------------------

    def save(self):

        DATABASE.write_text(
            json.dumps(
                self.data,
                indent=4,
            ),
            encoding="utf8",
        )

    # -------------------------

    def already_processed(
        self,
        repository,
        filename,
        sha256,
    ):

        key = f"{repository}/{filename}"

        if key not in self.data:
            return False

        return (
            self.data[key]["sha256"]
            == sha256
        )

    # -------------------------

    def update(
        self,
        repository,
        filename,
        sha256,
    ):

        key = f"{repository}/{filename}"

        self.data[key] = {

            "sha256": sha256,

            "processed": datetime.utcnow().isoformat(),

            "status": "success",
        }

        self.save()


database = Database()
