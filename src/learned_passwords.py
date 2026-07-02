from __future__ import annotations

import json
from pathlib import Path
from typing import Dict


DB_DIR = Path(".certsync")
DB_DIR.mkdir(exist_ok=True)

DATABASE = DB_DIR / "learned_passwords.json"


class LearnedPasswords:

    def __init__(self):

        if not DATABASE.exists():

            DATABASE.write_text(
                "{}",
                encoding="utf8",
            )

        self.reload()

    # ----------------------------------

    def reload(self):

        self.data: Dict = json.loads(
            DATABASE.read_text(
                encoding="utf8",
            )
        )

    # ----------------------------------

    def save(self):

        DATABASE.write_text(
            json.dumps(
                self.data,
                indent=4,
                ensure_ascii=False,
            ),
            encoding="utf8",
        )

    # ----------------------------------

    def add(
        self,
        repository: str,
        password: str,
    ):

        password = password.strip()

        if not password:
            return

        if password not in self.data:

            self.data[password] = {
                "success": 0,
                "repositories": [],
            }

        self.data[password]["success"] += 1

        if repository not in self.data[password]["repositories"]:

            self.data[password]["repositories"].append(
                repository
            )

        self.save()

    # ----------------------------------

    def exists(
        self,
        password: str,
    ) -> bool:

        return password in self.data

    # ----------------------------------

    def all(self) -> list[str]:

        passwords = sorted(

            self.data.items(),

            key=lambda item: item[1]["success"],

            reverse=True,

        )

        return [

            password

            for password, _ in passwords

        ]

    # ----------------------------------

    def repository_passwords(
        self,
        repository: str,
    ) -> list[str]:

        results = []

        for password, info in self.data.items():

            if repository in info["repositories"]:

                results.append(

                    (

                        password,

                        info["success"],

                    )

                )

        results.sort(

            key=lambda x: x[1],

            reverse=True,

        )

        return [

            password

            for password, _ in results

        ]

    # ----------------------------------

    def build_password_list(

        self,

        repository: str,

        discovered: list[str],

        config_passwords: list[str],

    ) -> list[str]:

        final = []

        seen = set()

        groups = [

            discovered,

            self.repository_passwords(

                repository

            ),

            self.all(),

            config_passwords,

        ]

        for group in groups:

            for password in group:

                password = password.strip()

                if not password:

                    continue

                if password in seen:

                    continue

                seen.add(password)

                final.append(password)

        return final


learned_passwords = LearnedPasswords()
