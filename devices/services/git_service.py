import subprocess

from django.conf import settings


class GitService:

    @staticmethod
    def fetch():

        subprocess.run(
            ["git", "fetch", "origin"],
            cwd=settings.BASE_DIR,
            capture_output=True,
            text=True,
            check=True
        )

    @staticmethod
    def local_commit():

        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=settings.BASE_DIR,
            text=True
        ).strip()

    @staticmethod
    def remote_commit():

        return subprocess.check_output(
            ["git", "rev-parse", "--short", "origin/main"],
            cwd=settings.BASE_DIR,
            text=True
        ).strip()

    @staticmethod
    def local_branch():

        return subprocess.check_output(
            ["git", "branch", "--show-current"],
            cwd=settings.BASE_DIR,
            text=True
        ).strip()

    @staticmethod
    def last_commit_message():

        return subprocess.check_output(
            [
                "git",
                "log",
                "-1",
                "--pretty=%s",
            ],
            cwd=settings.BASE_DIR,
            text=True
        ).strip()

    @classmethod
    def get_status(cls):

        cls.fetch()

        local = cls.local_commit()
        remote = cls.remote_commit()

        return {
            "update_available": local != remote,
            "local_commit": local,
            "remote_commit": remote,
            "branch": cls.local_branch(),
            "last_commit": cls.last_commit_message(),
        }