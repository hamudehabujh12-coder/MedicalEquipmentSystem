import os
import subprocess

from django.conf import settings
from django.utils import timezone
from devices.models import SystemUpdate

class UpdateService:

    LOCK_FILE = os.path.join(
        settings.BASE_DIR,
        "update",
        "update.lock"
    )

    @classmethod
    def is_running(cls):
        return os.path.exists(cls.LOCK_FILE)

    @classmethod
    def create_lock(cls):

        with open(cls.LOCK_FILE, "w") as f:
            f.write("Updating...")

    @classmethod
    def remove_lock(cls):

        if os.path.exists(cls.LOCK_FILE):
            os.remove(cls.LOCK_FILE)

    @classmethod
    def run(cls, user):

        update = SystemUpdate.objects.create(
            version="GitHub",
            status="RUNNING",
            started_by=user,
            started_at=timezone.now(),
        )

        update_script = os.path.join(
            settings.BASE_DIR,
            "update",
            "scripts",
            "update.bat"
        )

        if not os.path.exists(update_script):

            update.status = "FAILED"
            update.error = "update.bat not found"
            update.finished_at = timezone.now()
            update.save()

            raise FileNotFoundError("update.bat not found.")

        subprocess.Popen(
            [
                "cmd",
                "/c",
                update_script
            ],
            cwd=settings.BASE_DIR,
            creationflags=subprocess.CREATE_NEW_CONSOLE
        )

        return update