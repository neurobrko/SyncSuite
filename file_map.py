#!/usr/bin/env /home/marpauli/.cache/pypoetry/virtualenvs/syncsuite-HX8knUdy-py3.12/bin/python
"""
WIP
"""

from argparse import RawDescriptionHelpFormatter
from pathlib import Path
from subprocess import PIPE, STDOUT, run

from common import (
    RB,
    RST,
    CustomArgParser,
    dir_exists,
    file_exists,
    check_filemap,
    get_all_maps,
    read_yaml,
    write_yaml,
)

script_root = Path(__file__).resolve().parent
filemap_file = script_root / "file_map.yaml"

# setup arg parser
help_message = """
    View or add items to the file map."""
cap = CustomArgParser(
    description=help_message,
    formatter_class=RawDescriptionHelpFormatter,
)

cap.add_argument(
    "-v", "--view", help="list filepath in file_map file", action="store_true"
)
cap.add_argument(
    "-i",
    "--info",
    help="details about the file_map item",
)
cap.add_argument("-a", "--add", help="add a new file to the file_map")
cap.add_argument(
    "-m",
    "--map",
    help="path to file to be used as source or target (depending on action)",
)
cap.add_argument("-l", "--local_root_dir", help="local root directory for source files")
cap.add_argument(
    "-p",
    "--project",
    help="project name to which the file belongs (for adding new files)",
)
cap.add_argument("-c", "--config", help="Path to configuration file")
cap.add_argument("-r", "--remote", help="Remote host for synchronization")
cap.add_argument("-u", "--username", help="Remote username")
cap.add_argument("-s", "--ssh_port", help="SSH port")
cap.add_argument("-sm", "--synced_file_map", help="Path to synced_file_map.yaml")

args = cap.parse_args()


# check if file map is provided and valid
filemap_file = check_filemap(args.map, filemap_file, cap)
file_map = read_yaml(filemap_file)


def find_next_key(keys: list | set) -> int:
    """Find next free key for file map dictionary."""
    for i in range(1, len(keys) + 2):
        if i not in keys:
            return i


def get_project(project_name: str | None, file_map: dict) -> str:
    """
    Check if provided project name exists in file map and return it
    or return the last project name in the file map.
    :param project_name: name of the project to check
    :param file_map: file map dictionary
    :return: project name
    """
    if project_name and project_name in file_map:
        return project_name
    elif file_map:
        return list(file_map.keys())[-1]
    else:
        cap.error(
            f"{RB}No projects found in the file map! Provide a project name.{RST}"
        )
        cap.exit(1)


def update_file_map(project, src, trg):
    next_key = find_next_key(get_all_maps(file_map).keys())
    if project not in list(file_map.keys()):
        file_map[project] = {next_key: [src, trg]}
    else:
        file_map[project][next_key] = [src, trg]
    write_yaml(filemap_file, file_map)


if args.view:
    for project, paths in file_map.items():
        print(f"[{project}]:")
        for num, path in paths.items():
            if len(str(num)) == 1:
                num = f" {num}"
            print(f"    [{num}]: {Path(path[0]).name}")
    exit(0)

if args.info:
    num = int(args.info)
    if num not in (items := get_all_maps(file_map)):
        cap.error(f"Item '{num}' not found in file map!")
        cap.exit(1)

    project_name = next(
        (project for project, paths in file_map.items() if num in paths), None
    )

    print(f"Item '{num}' in project '{project_name}':")
    print(f"  Source: {items[num][0]}")
    print(f"  Target: {items[num][1]}")
    exit(0)

if args.add:
    # check if least required arguments are set
    if args.config:
        if not file_exists(args.config):
            cap.error(
                f"{RB}You must specify a valid configuration file using -c or --config!{RST}"
            )
            cap.exit(1)
        config = read_yaml(args.config)
    else:
        if not all([args.remote, args.username, args.ssh_port, args.local_root_dir]):
            cap.error(f"{RB}Insufficient arguments provided!{RST}")
            cap.exit(1)
        config = {}

    host = config.get("rsync", {}).get("host", args.remote)
    username = config.get("rsync", {}).get("username", args.username)
    ssh_port = config.get("rsync", {}).get("port", args.ssh_port)
    local_root_dir = Path(
        config.get("rsync", {}).get("local_root_dir", args.local_root_dir)
    )
    if not dir_exists(local_root_dir):
        cap.error(
            "You must specify a valid local root directory using -l or --local_root_dir!"
        )
        cap.exit(1)
    if not file_exists(local_root_dir / args.add):
        cap.error("You must specify a valid file to add using!")
        cap.exit(1)

    synced_file_map = (
        Path(args.synced_file_map)
        if args.synced_file_map
        else script_root / "synced_file_map.yaml"
    )
    if not file_exists(synced_file_map):
        cap.error(f"{RB}Sync file map '{synced_file_map}' does not exist!{RST}")
        cap.exit(1)
    synced_files = read_yaml(synced_file_map)

    project_name = get_project(args.project, file_map)
    target = synced_files.get(args.add, None)
    if target:
        # try to find the file in generated sync_file_map.yaml
        update_file_map(project_name, args.add, target)
    else:
        print(f"{RB}SSH search implementation is still WiP...{RST}")
        exit(1)
        # try ssh
        result = run(
            [
                "ssh",
                "-p",
                str(ssh_port),
                f"{username}@{host}",
                "find",
                "/",
                "-name",
                str(Path(args.add).name),
                "2>/dev/null",
            ],
            stdout=PIPE,
            stderr=STDOUT,
            text=True,
        ).stdout.splitlines()
        print(result)
        if not result:
            print(f"{RB}File '{args.add}' not found on remote host!{RST}")
            exit(1)
        elif len(result) > 1:
            print(f"{RB}Multiple files found with the same name!{RST}")
            for num, candidate in enumerate(result, start=1):
                print(f"[{num}]: {candidate}")
            choice = input("Select remote file to use: ")
            try:
                choice = int(choice)
                if choice < 1 or choice > len(result):
                    raise ValueError
                target = result[choice - 1]
            except ValueError:
                print(f"{RB}Invalid choice!{RST}")
                exit(1)
            update_file_map(project_name, args.add, target)
        else:
            target = result[0]
            update_file_map(project_name, args.add, target)
