"""
GitHub API Engine

Responsibilities
----------------
- Connect to GitHub
- Read public repositories
- Scan recursively
- Return ZIP files only
- Retry transient failures
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass
from typing import List
from urllib.parse import urlparse

from github import Github
from github.ContentFile import ContentFile
from github.GithubException import GithubException


MAX_RETRIES = 3
RETRY_DELAY = (2, 5, 10)


@dataclass(slots=True)
class ZipFile:

    repository: str
    repository_url: str

    name: str
    path: str

    download_url: str

    sha: str
    size: int


class GitHubAPI:

    def __init__(self):

        token = os.getenv("GITHUB_TOKEN")

        # Public repos bhi token ke bina readable hote hain,
        # lekin token rate limit kaafi improve karta hai.

        self.client = Github(token if token else None)

    # -------------------------------------------------

    @staticmethod
    def split_repo_url(url: str) -> tuple[str, str]:

        parsed = urlparse(url)

        path = parsed.path.strip("/")

        owner, repo = path.split("/")[:2]

        if repo.endswith(".git"):
            repo = repo[:-4]

        return owner, repo

    # -------------------------------------------------

    def open_repository(self, url: str):

        owner, repo = self.split_repo_url(url)

        return self.client.get_repo(f"{owner}/{repo}")

    # -------------------------------------------------

    def latest_commit_sha(self, url: str) -> str:

        repo = self.open_repository(url)

        return repo.get_branch(repo.default_branch).commit.sha

    # -------------------------------------------------

    def recursive_zip_scan(
        self,
        url: str,
    ) -> List[ZipFile]:

        repo = self.open_repository(url)

        results: List[ZipFile] = []

        self._walk(
            repo,
            "",
            results,
            url,
        )

        return results

    # -------------------------------------------------

    def _walk(
        self,
        repo,
        folder,
        results,
        repo_url,
    ):

        contents = self._retry(
            lambda: repo.get_contents(folder)
        )

        if not isinstance(contents, list):
            contents = [contents]

        while contents:

            item = contents.pop(0)

            if item.type == "dir":

                children = self._retry(
                    lambda p=item.path: repo.get_contents(p)
                )

                if not isinstance(children, list):
                    children = [children]

                contents.extend(children)

                continue

            if not item.name.lower().endswith(".zip"):
                continue

            results.append(
                ZipFile(
                    repository=repo.full_name,
                    repository_url=repo_url,

                    name=item.name,
                    path=item.path,

                    download_url=item.download_url,

                    sha=item.sha,

                    size=item.size,
                )
            )

    # -------------------------------------------------

    def _retry(self, func):

        last_error = None

        for attempt in range(MAX_RETRIES):

            try:

                return func()

            except GithubException as exc:

                last_error = exc

                if attempt == MAX_RETRIES - 1:
                    break

                time.sleep(RETRY_DELAY[attempt])

        raise last_error


github_api = GitHubAPI()
