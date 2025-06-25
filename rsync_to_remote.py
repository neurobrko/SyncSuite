#!/usr/bin/env /home/marpauli/.cache/pypoetry/virtualenvs/syncsuite-HX8knUdy-py3.12/bin/python
from argparse import RawDescriptionHelpFormatter
from subprocess import run, PIPE
from time import sleep, strftime, time

from pytimedinput import timedKey

from common import (
    BLD,
    CB,
    GB,
    GN,
    RB,
    RST,
    WU,
    check_filemap,
    compose_ssh_command,
    CustomArgParser,
    file_exists,
    get_all_maps,
    LOGGER,
    modify_ssh_options,
    read_yaml,
    RepeatingKeyError,
    BadFileSyncDefinition,
)
from pathlib import Path

# define paths
script_root = Path(__file__).resolve().parent
filemap_file = script_root / "file_map.yaml"

# setup arg parser
help_message = """
    Synchronize files to remote VM using rsync.
    Use -c to specify configuration file or use CLI arguments.
    Least required arguments are: -r, -u and one of -f, -p or -a.
    You can override settings from config file using CLI arguments."""
cap = CustomArgParser(
    description=help_message,
    formatter_class=RawDescriptionHelpFormatter,
)

cap.add_argument("-c", "--config", help="Path to configuration file")
cap.add_argument("-m", "--map", help="Path to filemap file")
cap.add_argument("-r", "--remote", help="Remote host for synchronization")
cap.add_argument("-u", "--username", help="Remote username")
cap.add_argument("-s", "--ssh_port", help="SSH port")
cap.add_argument("-l", "--local_root_dir", help="Root directory for source files")
cap.add_argument("-vt", "--vm_timeout", help="Timeout to check VM info")
cap.add_argument("-rt", "--result_timeout", help="Timeout to check script output")
cap.add_argument("-d", "--date_format", help="Timestamp format for logging")
cap.add_argument(
    "-a", "--sync_all", help="Sync all files from all projects", action="store_true"
)
cap.add_argument("-p", "--project", help="Sync all files from project")
cap.add_argument(
    "-f", "--files", help="Sync selected files. No spaces, comma as separator."
)
cap.add_argument(
    "-sr",
    "--services_restart",
    help="Restart services on remote machine.",
    action="store_true",
)
cap.add_argument(
    "-sn",
    "--services_names",
    help="Name(s) of service(s) to restart. No spaces, comma as separator.",
)
cap.add_argument(
    "-ps", "--persistent_ssh", help="Use persistent SSH connection", action="store_true"
)

args = cap.parse_args()

# check if least required arguments are set
if not args.config:
    print(
        f"{CB}Configuration file was not specified! Using defaults and CLI arguments.{RST}"
    )
    if not all(
        [
            args.remote,
            args.username,
            any([args.files, args.project, args.sync_all]),
        ]
    ):
        cap.error(f"{RB}Insufficient arguments provided!{RST}")
        cap.exit(1)

# set variables and populate them with defaults or empty values
# Just for the sake of PyCharm's static analysis
local_root_dir = default_dir = script_root
port = 22
rsync_options = ["-rtvz", "--progress", "-e", "ssh -p 22"]
date_format = "%Y-%m-%d %H:%M:%S"
VM_check_timeout = result_timeout = 0
sync_all = restart_services = persistent_ssh = False
host = username = project = file_keys = services = ""

if args.config:
    conf_file = Path(args.config)
    if not file_exists(conf_file):
        cap.error(f"{RB}Configuration file {conf_file} not found!{RST}")
        cap.exit(1)
    # import configuration variables and remove GUI variables
    config = read_yaml(conf_file)
    config.pop("gui", None)
    print(f"{CB}Using configuration file: {conf_file}{RST}")
    # update globals with config values
    for vals in config.values():
        globals().update(vals)


# check if filemap is valid
filemap_file = check_filemap(args.map, filemap_file, cap)

# store content of file_map.yaml
file_map = read_yaml(filemap_file)

# override settings, if set from cli
if args.remote:
    host = args.remote
if args.username:
    username = args.username
if args.ssh_port:
    port = args.ssh_port
    # if port is specified in CLI, alter rsync_options!
    rsync_options = modify_ssh_options(rsync_options, f"-p {port}")
if args.local_root_dir:
    local_root_dir = args.local_root_dir
if args.vm_timeout:
    VM_check_timeout = int(args.vm_timeout)
if args.result_timeout:
    result_timeout = int(args.result_timeout)
if args.date_format:
    date_format = args.date_format
if args.sync_all:
    sync_all = True
if args.project:
    project = args.project
if args.files:
    file_keys = [int(file) for file in args.files.split(",")]
if args.services_restart:
    restart_services = args.services_restart
if args.services_names:
    services = args.services_names.split(",")
if args.persistent_ssh:
    persistent_ssh = args.persistent_ssh


def get_project_maps(filemap: dict, project_name: str) -> dict:
    return filemap[project_name]


def run_rsync(filepaths: list, counter: int, persistent: bool = False) -> int:
    print(f"{GN}[{counter}]{RST}")
    print(f"{CB}local file: {RST}{WU}{filepaths[0]}{RST}")
    print(f"{CB}remote file: {RST}{WU}{filepaths[1]}{RST}")
    to_log = f"\n*_* [{counter}] *_*\nsource: {filepaths[0]}\ntarget: {filepaths[1]}\nrsync output:"
    options = rsync_options[:]
    sync_suite_socket = Path("/tmp/syncsuite_socket")
    # persistent SSH connection should be open, but check it and fall back to non-persistent, if not
    if persistent and sync_suite_socket.exists():
        options = modify_ssh_options(options, f"-S {str(sync_suite_socket)} -p {port}")
    try:
        result = run(
            ["rsync"]
            + options
            + [
                (Path(local_root_dir) / filepaths[0]).as_posix(),
                f"{username}@{host}:{filepaths[1]}",
            ],
            stdout=PIPE,
            stderr=PIPE,
            text=True,
        )
    except Exception as err:
        print(f"{RB}Something went wrong! {err}{RST}")
        LOGGER.error(f"Error during rsync: {err}")
    else:
        to_log = "\n".join([to_log, result.stdout])
        LOGGER.info(to_log)
        counter += 1
        if result.stderr:
            print(f"{RB}{result.stderr}{RST}")
            LOGGER.info(f"\n!!! {result.stderr} !!!")
            counter -= 1
        return counter


def synchronize_files(all_maps):
    # TODO: Add checks for keys and projects
    # decide what to sync based on settings
    if sync_all:
        i = 1
        for paths in all_maps.values():
            i = run_rsync(paths, i, persistent_ssh)
        return i
    elif project:
        file_maps = get_project_maps(file_map, project)
        i = 1
        for paths in file_maps.values():
            # print(paths)
            i = run_rsync(paths, i, persistent_ssh)
        return i
    elif len(file_keys) > 0:
        i = 1
        for k in file_keys:
            i = run_rsync(all_maps[k], i, persistent_ssh)
        return i
    else:
        raise BadFileSyncDefinition


def _restart_services():
    if not restart_services:
        return
    print(f"{BLD}Restarting service(s) {' '.join(services)} on remote...{RST}")
    run(
        compose_ssh_command(
            remote_cmd=(["systemctl", "restart"] + services), conf_file=conf_file
        ),
        stdout=PIPE,
    )
    print(
        f"{BLD}Services restarted.{RST} (Check journalctl if restart was successfull.)\n"
    )
    LOGGER.info(f"Restarted services: {' '.join(services)}")


def _display_result_with_timeout():
    if result_timeout:
        for x in range(result_timeout):
            print(
                f"{RB}Press Ctrl+C to exit or script will exit in: {(result_timeout - x)} s...{RST}",
                end=" \r",
            )
            sleep(1)


def main():
    start_time = time()
    print("".join([BLD, "> Sync files to remote VM <".center(80, "="), RST]))
    LOGGER.info("> SYNC START <".center(50, "="))
    LOGGER.info(f"timestamp: {strftime(date_format)}")
    # Check for repeating keys in file map projects
    try:
        all_maps = get_all_maps(file_map)
        LOGGER.info("File map keys OK!")
    except RepeatingKeyError as err:
        print(f"{RB}{err}{RST}")
        LOGGER.info(f"!!! {err} !!!")
        exit(1)

    # display info about VM and open persistent SSH connection
    print(f"{BLD}ssh: {RB}{username}@{host}:{port}{RST}")
    LOGGER.info(f"ssh: {username}@{host}:{port}")
    print("Fetching remote hostname...")
    hostname = run(
        compose_ssh_command(remote_cmd=["hostname"], conf_file=conf_file),
        stdout=PIPE,
    ).stdout.decode("utf-8")
    print(f"{BLD}remote hostname: {RB}{hostname}{RST}")
    LOGGER.info(f"remote hostname: {hostname.strip()}")

    # give user few seconds to check VM settings
    if VM_check_timeout:
        user_text, timed_out = timedKey(
            f"Correct VM? (Waiting for {VM_check_timeout} s.) [y/n]: ",
            timeout=VM_check_timeout,
            allowCharacters="yYnN",
        )
        if timed_out:
            print("Continue synchronization!")
            LOGGER.info("VM check: OK! (w/o user interaction)")
            i = synchronize_files(all_maps)
        else:
            if user_text in ["y", "Y"]:
                LOGGER.info("VM check: OK!")
                i = synchronize_files(all_maps)
            else:
                print("Synchronization canceled. Check WM info.")
                LOGGER.info("VM check: Synchronization canceled by user.")
                LOGGER.info("".join(["> SYNC END <".center(50, "="), "\n\n"]))
                exit(1)
    else:
        i = synchronize_files(all_maps)

    end_time = time()
    if i == 1:
        print(f"{RB}\nSynced {i - 1} file!{RST}\n")
    else:
        plural = "s" if i > 2 else ""
        print(
            f"{BLD}\nSynced {CB}{i - 1}{RST}{BLD} file{plural} in {CB}{(end_time - start_time):.2f} seconds{RST}{BLD}.{RST}\n"
        )
    LOGGER.info(f"\nSynced file(s) count: {i - 1}")
    LOGGER.info("".join(["> SYNC END <".center(50, "="), "\n\n"]))

    _restart_services()

    _display_result_with_timeout()

    print(f"{GB}GoodBye!{RST}", " " * 70)
    sleep(1)
    exit(0)


if __name__ == "__main__":
    main()
