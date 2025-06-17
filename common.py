#!/usr/bin/env python3
import inspect
import logging
from pathlib import Path
from time import strftime

import yaml


# Common exceptions for the rsync_to_remote script
class RepeatingKeyError(Exception):
    pass


class BadFileSyncDefinition(Exception):
    pass


def read_yaml(file: str | Path) -> dict:
    """
    Reads a YAML file and returns its content.

    :param file: Path to the YAML file.
    :return: Content of the YAML file.
    """
    with open(file, "r") as f:
        return yaml.safe_load(f)


script_root = Path(__file__).resolve().parent
date_format = read_yaml("sync_conf.yaml")["script"]["date_format"]

# Setup logging
LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(logging.DEBUG)
LOGGER.propagate = False

log_filename = f"r2r-{strftime('%y%m%d')}.log"
dev_filename = f"r2r-dev-{strftime('%y%m%d')}.log"
log_path = script_root / "log"
if not log_path.exists():
    log_path.mkdir(parents=True)
# Create a handler for the main log file to log only INFO messages
info_handler = logging.FileHandler(log_path / log_filename)
info_handler.addFilter(lambda record: record.levelno == logging.INFO)
info_formatter = logging.Formatter("%(message)s", datefmt=date_format)
info_handler.setFormatter(info_formatter)
# Create a handler for the dev log file to everything but INFO messages
dev_handler = logging.FileHandler(log_path / dev_filename)
dev_handler.addFilter(lambda record: record.levelno != logging.INFO)
dev_formatter = logging.Formatter(
    "%(asctime)s | %(levelname)s [%(filename)s:%(lineno)d]: %(message)s",
    datefmt="%H:%M:%S",
)
dev_handler.setFormatter(dev_formatter)
# Add handlers to the logger
LOGGER.addHandler(info_handler)
LOGGER.addHandler(dev_handler)


class IndentedLogger:
    def __init__(self, logger):
        self.logger = logger
        self.log_prefix = "HH:MM:SS |"

    @staticmethod
    def _get_caller_info():
        caller_frame = inspect.currentframe().f_back
        filename = Path(caller_frame.f_code.co_filename).name
        return filename, caller_frame.f_lineno

    def _format_message(self, msg: list, prefix: str, level: str) -> str:
        print(level)
        if level == "INFO":
            log_prefix = ""
        else:
            filename, lineno = self._get_caller_info()
            log_prefix = f"{self.log_prefix} {level.upper()} [{filename}:{lineno}]: "
        if prefix:
            log_prefix += prefix
            indented_message = f"{prefix} " + ("\n" + " " * (len(log_prefix) + 1)).join(
                msg
            )
        else:
            indented_message = ("\n" + " " * (len(log_prefix))).join(msg)
        return indented_message

    def log(self, level: str, msg: list, m_prefix: str | None = None):
        indented_message = self._format_message(msg, m_prefix, level)
        log_method = getattr(self.logger, level.lower(), None)
        if log_method:
            log_method(indented_message)

    def debug(self, msg: list, m_prefix: str | None = None):
        self.log("DEBUG", msg, m_prefix)

    def info(self, msg: list, m_prefix: str | None = None):
        self.log("INFO", msg, m_prefix)

    def warning(self, msg: list, m_prefix: str | None = None):
        self.log("WARNING", msg, m_prefix)

    def error(self, msg: list, m_prefix: str | None = None):
        self.log("ERROR", msg, m_prefix)

    def critical(self, msg: list, m_prefix: str | None = None):
        self.log("CRITICAL", msg, m_prefix)


# Create an instance of IndentedLogger
I_LOGGER = IndentedLogger(LOGGER)
