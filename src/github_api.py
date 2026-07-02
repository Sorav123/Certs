from github import Github
from github.ContentFile import ContentFile
import requests
from pathlib import Path

from config import (
    SOURCE_REPO,
    TEMP,
)


class GitHub:

    def __init__(self):

        self.github = Github()

        self.repo = self.github.get_repo(
            "royilkom-alt/AppleJr"
        )

    def get_zip_files(self):

        results = []

        self.walk(
            "",
            results,
        )

        return results

    def walk(
        self,
        folder,
        results,
    ):

        contents = self.repo.get_contents(folder)

        if not isinstance(contents, list):
            contents = [contents]

        while contents:

            item = contents.pop()

            if item.type == "dir":

                children = self.repo.get_contents(
                    item.path
                )

                if not isinstance(
                    children,
                    list,
                ):
                    children = [children]

                contents.extend(children)

                continue

            if item.name.endswith(".zip"):

                results.append(item)

    def download(self, item):

        destination = TEMP / item.name

        r = requests.get(item.download_url)

        destination.write_bytes(r.content)

        return destination

    def upload(
        self,
        zip_file,
        filename,
    ):

        print(
            f"UPLOAD: {filename}"
        )
