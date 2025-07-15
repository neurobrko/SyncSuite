#!/usr/bin/env python3

from pathlib import Path
import time

from common import I_LOGGER, LOGGER

"""
To perform log cleanup, run this script manually or create a cron job to run it periodically.
You can also run it with every GUI start. Usually, GUI is started once a day or less often,
than main script, so it is a good place to run this script.
"""

INFO_LOG_PERSISTENCE = 5  # Number of days to keep runtime log files
DEV_LOG_PERSISTENCE = 30  # Number of days to keep dev log files


def log_cleanup():
    log_dir = Path(__file__).resolve().parent / "log"

    if not log_dir.exists():
        LOGGER.warning(f"Log directory does not exist: {log_dir}")
        exit(1)

    now = time.time()

    deleted = []
    for file in log_dir.iterdir():
        if file.is_file():
            persistence = (
                DEV_LOG_PERSISTENCE
                if "r2r-dev" in file.name
                else INFO_LOG_PERSISTENCE
            )
            if now - file.stat().st_mtime > persistence * 86400:
                file.unlink()
                deleted.append(file)
    if deleted:
        plural = "s" if len(deleted) > 1 else ""
        I_LOGGER.warning(deleted, f"Deleted {len(deleted)} log file{plural}:")
    else:
        LOGGER.warning("No logs were deleted.")


if __name__ == "__main__":
    log_cleanup()
