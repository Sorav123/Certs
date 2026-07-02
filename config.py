"""
Configuration Loader

Loads:
- repos.yaml
- passwords.yaml
- settings.yaml

This module is the single source of truth for configuration.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


ROOT_DIR = Path(__file__).resolve().parent.parent
CONFIG_DIR = ROOT_DIR / "config"


def _load_yaml(filename: str) -> dict[str, Any]:
    path = CONFIG_DIR / filename

    if not path.exists():
        raise FileNotFoundError(f"Missing configuration file: {path}")

    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    if data is None:
        data = {}

    return data


@dataclass(slots=True)
class Repository:

    name: str
    url: str
    enabled: bool = True


class Config:

    def __init__(self):

        self._repos = _load_yaml("repos.yaml")
        self._passwords = _load_yaml("passwords.yaml")
        self._settings = _load_yaml("settings.yaml")

    @property
    def repositories(self) -> list[Repository]:

        repos: list[Repository] = []

        for item in self._repos.get("repos", []):

            repos.append(
                Repository(
                    name=item["name"],
                    url=item["url"],
                    enabled=item.get("enabled", True),
                )
            )

        return repos

    @property
    def passwords(self) -> list[str]:

        return [
            str(password)
            for password in self._passwords.get("passwords", [])
        ]

    @property
    def destination_repo(self) -> str:

        return self._settings["destination_repo"]

    @property
    def branch(self) -> str:

        return self._settings.get("branch", "main")

    @property
    def workers(self) -> int:

        return int(self._settings.get("workers", 4))

    @property
    def new_password(self) -> str:

        return self._settings["new_password"]

    @property
    def dry_run(self) -> bool:

        return bool(self._settings.get("dry_run", False))

    @property
    def overwrite_if_changed(self) -> bool:

        return bool(
            self._settings.get(
                "overwrite_if_changed",
                True,
            )
        )

    @property
    def remove_extra_files(self) -> bool:

        return bool(
            self._settings.get(
                "delete_extra_files",
                True,
            )
        )

    @property
    def keep_original_names(self) -> bool:

        return bool(
            self._settings.get(
                "keep_original_filename",
                True,
            )
        )

    @property
    def scan_interval_hours(self) -> int:

        return int(
            self._settings.get(
                "scan_interval_hours",
                6,
            )
        )


config = Config()
