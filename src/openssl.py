from __future__ import annotations

import os
import subprocess
from pathlib import Path


OPENSSL_BIN = os.getenv(
    "OPENSSL_BIN",
    "openssl",
)


class OpenSSLException(Exception):
    pass


class OpenSSL:

    @staticmethod
    def run(
        args: list[str],
        timeout: int = 120,
    ) -> subprocess.CompletedProcess:

        command = [OPENSSL_BIN] + args

        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=timeout,
        )

        if result.returncode != 0:

            raise OpenSSLException(

                result.stderr.strip()

            )

        return result

    # ----------------------------------

    @staticmethod
    def verify_password(
        p12: Path,
        password: str,
    ) -> bool:

        try:

            OpenSSL.run(

                [

                    "pkcs12",

                    "-info",

                    "-in",

                    str(p12),

                    "-passin",

                    f"pass:{password}",

                    "-noout",

                ]

            )

            return True

        except OpenSSLException:

            return False

    # ----------------------------------

    @staticmethod
    def export_pem(

        p12: Path,

        password: str,

        output: Path,

    ):

        OpenSSL.run(

            [

                "pkcs12",

                "-in",

                str(p12),

                "-passin",

                f"pass:{password}",

                "-nodes",

                "-out",

                str(output),

            ]

        )

    # ----------------------------------

    @staticmethod
    def create_p12(

        pem: Path,

        output: Path,

        password: str,

    ):

        OpenSSL.run(

            [

                "pkcs12",

                "-export",

                "-in",

                str(pem),

                "-out",

                str(output),

                "-passout",

                f"pass:{password}",

            ]

        )

    # ----------------------------------

    @staticmethod
    def fingerprint_sha1(

        p12: Path,

        password: str,

    ) -> str:

        result = OpenSSL.run(

            [

                "pkcs12",

                "-in",

                str(p12),

                "-passin",

                f"pass:{password}",

                "-clcerts",

                "-nokeys",

            ]

        )

        certificate = result.stdout

        process = subprocess.run(

            [

                OPENSSL_BIN,

                "x509",

                "-fingerprint",

                "-sha1",

                "-noout",

            ],

            input=certificate,

            text=True,

            capture_output=True,

        )

        if process.returncode != 0:

            raise OpenSSLException(

                process.stderr

            )

        return (

            process.stdout

            .split("=")[-1]

            .strip()

        )

    # ----------------------------------

    @staticmethod
    def fingerprint_sha256(

        p12: Path,

        password: str,

    ) -> str:

        result = OpenSSL.run(

            [

                "pkcs12",

                "-in",

                str(p12),

                "-passin",

                f"pass:{password}",

                "-clcerts",

                "-nokeys",

            ]

        )

        certificate = result.stdout

        process = subprocess.run(

            [

                OPENSSL_BIN,

                "x509",

                "-fingerprint",

                "-sha256",

                "-noout",

            ],

            input=certificate,

            text=True,

            capture_output=True,

        )

        if process.returncode != 0:

            raise OpenSSLException(

                process.stderr

            )

        return (

            process.stdout

            .split("=")[-1]

            .strip()

        )


openssl = OpenSSL()
