#!/usr/bin/env python3
import argparse
from subprocess import run, PIPE
from time import sleep, strftime

from pytimedinput import timedKey

from common import LOGGER, read_yaml, RepeatingKeyError, BadFileSyncDefinition
from pathlib import Path

# define paths
script_root = Path(__file__).resolve().parent
conf_file = script_root / "sync_conf.yaml"
filemap_file = script_root / "file_map.yaml"

# import configuration variables and remove GUI variables
config = read_yaml(conf_file)
config.pop("gui", None)

# set empty variables and populate them with config values
# Just for the sake of PyCharm's static analysis
host = username = port = local_root_dir = ""
rsync_options = []
VM_check_timeout = result_timeout = default_dir = date_format = ""
project = file_keys = ""
sync_all = False
restart_services = False
services = ""
GN = GB = RN = RB = CN = CB = WU = BLD = UND = RST = ""

for vals in config.values():
    globals().update(vals)

# setup arg parser
ap = argparse.ArgumentParser()
ap.add_argument("-r", "--remote", help="Remote host for synchronization")
ap.add_argument("-u", "--username", help="Remote username")
ap.add_argument("-s", "--ssh_port", help="SSH port")
ap.add_argument("-l", "--local_root_dir", help="Root directory for source files")
ap.add_argument("-vt", "--vm_timeout", help="Timeout to check VM info")
ap.add_argument("-rt", "--result_timeout", help="Timeout to check script output")
ap.add_argument("-d", "--date_format", help="Timestamp format for logging")
ap.add_argument(
    "-a", "--sync_all", help="Sync all files from all projects", action="store_true"
)
ap.add_argument("-p", "--project", help="Sync all files from project")
ap.add_argument(
    "-f", "--files", help="Sync selected files. No spaces, comma as separator."
)
ap.add_argument(
    "-sr",
    "--services_restart",
    help="Restart services on remote machine.",
    action="store_true",
)
ap.add_argument(
    "-sn",
    "--services_names",
    help="Name(s) of service(s) to restart. No spaces, comma as separator.",
)

args = ap.parse_args()

# override settings, if set from cli
if args.remote:
    host = args.remote
if args.username:
    username = args.username
if args.ssh_port:
    port = args.ssh_port
    # if port is specified in CLI, alter rsync_options!
    for n, item in enumerate(rsync_options):
        if item.startswith("ssh -p"):
            rsync_options[n] = f"ssh -p {port}"
            break
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

# store content fo file_map.yaml
file_map = read_yaml(filemap_file)


def get_project_maps(filemap: dict, project_name: str) -> dict:
    return filemap[project_name]


def run_rsync(filepaths: list, counter: int):
    print(f"{GN}[{counter}]{RST}")
    print(f"{CB}local file: {RST}{WU}{filepaths[0]}{RST}")
    print(f"{CB}remote file: {RST}{WU}{filepaths[1]}{RST}")
    to_log = f"\n*_* [{counter}] *_*\nsource: {filepaths[0]}\ntarget: {filepaths[1]}\nrsync output:"
    try:
        result = run(
            ["rsync"]
            + rsync_options
            + [
                (Path(local_root_dir) / filepaths[0]).as_posix(),
                f"{username}@{host}:{filepaths[1]}",
            ],
            stdout=PIPE,
            stderr=PIPE,
            text=True,
        )
        to_log = "\n".join([to_log, result.stdout])
        LOGGER.info(to_log)
        counter += 1
        if result.stderr:
            print(f"{RB}{result.stderr}{RST}")
            LOGGER.info(f"\n!!! {result.stderr} !!!")
            counter -= 1
        return counter
    except Exception as err:
        print(f"{RB}Something went wrong! {err}{RST}")
    LOGGER.info(to_log)


def get_all_maps(filemap: dict) -> dict:
    all_maps = {}
    for project_name, maps in filemap.items():
        for key, value in maps.items():
            if key in all_maps:
                raise RepeatingKeyError(f"Repeating keys in project '{project_name}'")
            all_maps[key] = value
    return all_maps


def synchronize_files(all_maps):
    # decide what to sync based on settings
    if sync_all:
        i = 1
        for paths in all_maps.values():
            i = run_rsync(paths, i)
        return i
    elif project:
        file_maps = get_project_maps(file_map, project)
        i = 1
        for paths in file_maps.values():
            # print(paths)
            i = run_rsync(paths, i)
        return i
    elif len(file_keys) > 0:
        i = 1
        for k in file_keys:
            i = run_rsync(all_maps[k], i)
        return i
    else:
        raise BadFileSyncDefinition


def _restart_services():
    if not restart_services:
        return
    print(f"{BLD}Restarting service(s) {' '.join(services)} on remote...{RST}")
    cmd = [
        "ssh",
        "-p",
        f"{port}",
        f"{username}@{host}",
        "systemctl",
        "restart",
    ] + services
    run(
        cmd,
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

    # display info about VM
    print(f"{BLD}ssh: {RB}{username}@{host}:{port}{RST}")
    LOGGER.info(f"ssh: {username}@{host}:{port}")
    print("Fetching remote hostname...")
    hostname = run(
        ["ssh", "-p", f"{port}", f"{username}@{host}", "echo", "$HOSTNAME"],
        stdout=PIPE,
    ).stdout.decode("utf-8")
    print(f"{BLD}remote hostname: {RB}{hostname}{RST}")
    LOGGER.info(f"remote hostname: {hostname.strip()}")

    # give user few seconds to check VM settings
    # TODO: add countdown
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

    if i - 1 == 0:
        print(f"{RB}\nSynced file(s) count: {i - 1}{RST}\n")
    else:
        print(f"{BLD}\nSynced file(s) count: {RST}{CB}{i - 1}{RST}\n")
    LOGGER.info(f"\nSynced file(s) count: {i - 1}")
    LOGGER.info("".join(["> SYNC END <".center(50, "="), "\n\n"]))

    _restart_services()

    _display_result_with_timeout()

    print(f"{GB}GoodBye!{RST}", " " * 70)
    sleep(1)
    exit()


if __name__ == "__main__":
    main()
    print(f"{GB}SUCCESS!{RST}")
