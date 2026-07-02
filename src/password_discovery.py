from __future__ import annotations

import re
from pathlib import Path

MAX_FILE_SIZE = 100 * 1024

TEXT_EXTENSIONS = {
    ".txt",
    ".md",
    ".text",
    "",
}

PASSWORD_PATTERNS = [

    re.compile(
        r"password\s*[:=]\s*(.+)",
        re.IGNORECASE,
    ),

    re.compile(
        r"pass\s*[:=]\s*(.+)",
        re.IGNORECASE,
    ),

    re.compile(
        r"p12\s*password\s*[:=]\s*(.+)",
        re.IGNORECASE,
    ),

    re.compile(
        r"certificate\s*password\s*[:=]\s*(.+)",
        re.IGNORECASE,
    ),
]


class PasswordDiscovery:

    def discover(
        self,
        root: Path,
    ) -> list[str]:

        found = []

        for file in root.rglob("*"):

            if not file.is_file():
                continue

            if file.suffix.lower() not in TEXT_EXTENSIONS:
                continue

            if file.stat().st_size > MAX_FILE_SIZE:
                continue

            try:

                text = file.read_text(
                    encoding="utf8",
                    errors="ignore",
                )

            except Exception:
                continue

            found.extend(
                self.extract(text)
            )

        return self.unique(found)

    # -----------------------------------

    def extract(
        self,
        text: str,
    ) -> list[str]:

        passwords = []

        for pattern in PASSWORD_PATTERNS:

            for match in pattern.findall(text):

                password = match.strip()

                if password:

                    passwords.append(password)

        # Single line password

        lines = [
            line.strip()
            for line in text.splitlines()
        ]

        for line in lines:

            if (
                len(line) >= 3
                and len(line) <= 64
                and " " not in line
            ):

                if re.fullmatch(
                    r"[A-Za-z0-9._@#$%^&+=!-]+",
                    line,
                ):

                    passwords.append(line)

        return passwords

    # -----------------------------------

    @staticmethod
    def unique(values):

        seen = set()

        result = []

        for value in values:

            if value in seen:
                continue

            seen.add(value)

            result.append(value)

        return result


password_discovery = PasswordDiscovery()

