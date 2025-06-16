#!/usr/bin/env python3

from pathlib import Path
import time

from common import LOGGER

"""
To perform log cleanup, run this script manually or create a cron job to run it periodically.
You can also run it with every GUI start. Usually, GUI is started once a day or less often,
than main script, so it is a good place to run this script.
"""


def log_cleanup():
    log_dir = Path(__file__).resolve().parent / "log"

    if not log_dir.exists():
        LOGGER.warning(f"Log directory does not exist: {log_dir}")
        exit(1)

    info_log_persistence = 5  # Number of days to keep runtime log files
    dev_log_persistence = 30  # Number of days to keep dev log files
    now = time.time()

    deleted = 0
    for file in log_dir.iterdir():
        if file.is_file():
            persistence = (
                dev_log_persistence if "r2r-dev" in file.name else info_log_persistence
            )
            if now - file.stat().st_mtime > persistence * 86400:
                file.unlink()
                deleted += 1
                LOGGER.warning(f"Deleted: {file.name}")
    if not deleted:
        LOGGER.warning("No logs were deleted.")


if __name__ == "__main__":
    log_cleanup()
