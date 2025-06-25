#!/usr/bin/env python3
import argparse
import inspect
import logging
from pathlib import Path
from time import strftime

import yaml


def read_yaml(file: str | Path) -> dict:
    """
    Reads a YAML file and returns its content.

    :param file: Path to the YAML file.
    :return: Content of the YAML file.
    """
    with open(file, "r") as f:
        return yaml.safe_load(f)


script_root = Path(__file__).resolve().parent
conf_file = script_root / "sync_conf.yaml"
date_format = read_yaml(conf_file)["script"]["date_format"]

ignored_folders = [".idea", ".git", "__pycache__", ".ruff_cache"]
ignored_extensions = [".log"]
ignored_files = [".gitignore", "README.md", "LICENSE", ".pre-commit-config.yaml"]

# terminal colors
GN = "\033[0;32m"
GB = "\033[1;32m"
RN = "\033[0;31m"
RB = "\033[1;31m"
CN = "\033[0;36m"
CB = "\033[1;36m"
WU = "\033[4;37m"
BLD = "\033[1m"
UND = "\033[4m"
RST = "\033[0m"

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
    """
    A logger output that indents messages for better readability.
    (It's more of a proof-of-concept, because, while the output is more
    readable, it is not very good for copying the logs later on.)
    """

    def __init__(self, logger):
        self.logger = logger
        self.log_prefix = "HH:MM:SS |"

    @staticmethod
    def _get_caller_info():
        caller_frame = inspect.currentframe().f_back
        filename = Path(caller_frame.f_code.co_filename).name
        return filename, caller_frame.f_lineno

    def _format_message(self, msg: list, prefix: str, level: str) -> str:
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


# Common exceptions for the rsync_to_remote script
class RepeatingKeyError(Exception):
    pass


class BadFileSyncDefinition(Exception):
    pass


class CustomArgParser(argparse.ArgumentParser):
    """
    Custom argument parser to customize displayed help message.
    """

    def format_help(self):
        formatter = self._get_formatter()

        # description
        formatter.add_text(self.description)

        # positionals, optionals and user-defined groups
        for action_group in self._action_groups:
            formatter.start_section(action_group.title)
            formatter.add_text(action_group.description)
            formatter.add_arguments(action_group._group_actions)
            formatter.end_section()

        # epilog
        formatter.add_text(self.epilog)

        # determine help from format above
        return formatter.format_help()


# Helper functions
def write_yaml(file: str | Path, data: dict):
    """
    Writes a dictionary to a YAML file.

    :param file: Path to the YAML file.
    :param data: Data to write to the YAML file.
    """
    with open(file, "w") as f:
        yaml.safe_dump(
            data, f, default_flow_style=False, allow_unicode=True, sort_keys=False
        )


def modify_ssh_options(options: list, ssh_options: str) -> list:
    """
    Modify rsync options to include custom SSH options.
    :param options: List of rsync options.
    :param ssh_options: Custom SSH options to include.
    :return: Modified list of rsync options.
    """
    for n, item in enumerate(options):
        if item.startswith("ssh -p"):
            options[n] = f"ssh {ssh_options}"
            break
    return options


def file_exists(file_path: str | Path) -> bool:
    """
    Check if a file exists at the given path.

    :param file_path: Path to the file.
    :return: True if the file exists, False otherwise.
    """
    return Path(file_path).exists() and Path(file_path).is_file()


def dir_exists(dir_path: str | Path) -> bool:
    """
    Check if a directory exists at the given path.

    :param dir_path: Path to the directory.
    :return: True if the directory exists, False otherwise.
    """
    return Path(dir_path).exists() and Path(dir_path).is_dir()


def check_filemap(
    args_path: str | Path, default_path: str | Path, cap: CustomArgParser
) -> str | Path:
    if args_path:
        filemap_file = Path(args_path)
        if not file_exists(filemap_file):
            cap.error(f"{RB}You must specify a valid file map using -m or --map!{RST}")
            cap.exit(1)
        return filemap_file
    if not file_exists(default_path):
        cap.error(
            f"{RB}Filemap file not found! Please create {default_path.name} in the same directory.{RST}"
        )
        cap.exit(1)
    return default_path


def get_all_maps(filemap: dict) -> dict:
    all_maps = {}
    for project_name, maps in filemap.items():
        for key, value in maps.items():
            if key in all_maps:
                raise RepeatingKeyError(f"Repeating keys in project '{project_name}'")
            all_maps[key] = value
    return all_maps


def compose_ssh_command(
    persistent: bool = True,
    remote_cmd: list | None = None,
    conf_file: str | Path = conf_file,
) -> list:
    """
    Compose an SSH command to use persistent connection.

    :param persistent: whether to use a persistent SSH connection, True by default
    :param remote_cmd: optional command to run on the remote host
    :return: composed ssh command
    """
    conf = read_yaml(conf_file)
    sync_suite_socket = Path("/tmp/syncsuite_socket")
    ssh_cmd = ["ssh"]
    ssh_creds = [
        "-p",
        str(conf["rsync"]["port"]),
        f"{conf['rsync']['username']}@{conf['rsync']['host']}",
    ]
    if persistent:
        if sync_suite_socket.exists():
            ssh_cmd += ["-S", str(sync_suite_socket)]
        else:
            ssh_cmd += [
                "-M",
                "-S",
                str(sync_suite_socket),
                "-o",
                "ControlPersist=20",
            ]
    ssh_cmd += ssh_creds
    if remote_cmd:
        ssh_cmd += remote_cmd
    return ssh_cmd
