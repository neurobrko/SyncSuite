#!/usr/bin/env /home/marpauli/.cache/pypoetry/virtualenvs/syncsuite-HX8knUdy-py3.12/bin/python

"""
WORK IN PROGRESS
Script is working.
But corner cases were not properly tested
and still needs some cleanup and refactoring.
Also some more verbosity would be nice.
"""

from argparse import RawDescriptionHelpFormatter
from pathlib import Path
from subprocess import PIPE, STDOUT, run

from common import (
    CB,
    GB,
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
    View file map, add new files to it or delete existing ones.
    When adding, use -c to specify configuration file or use CLI
    arguments. Least required arguments are: -r, -u, -s and -l.
    """
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
cap.add_argument("-d", "--delete", help="delete an item from the file_map")
cap.add_argument(
    "-m",
    "--map",
    help="path to file to be used as source or target (depending on action)",
)
cap.add_argument(
    "-l", "--local_root_dir", help="local root directory for source files"
)
cap.add_argument(
    "-p",
    "--project",
    help="project name to which the file belongs (for adding new files)",
)
cap.add_argument("-c", "--config", help="Path to configuration file")
cap.add_argument("-r", "--remote", help="Remote host for synchronization")
cap.add_argument("-u", "--username", help="Remote username")
cap.add_argument("-s", "--ssh_port", help="SSH port")
cap.add_argument(
    "-sm", "--synced_file_map", help="Path to synced_file_map.yaml"
)

args = cap.parse_args()


# check if file map is provided and valid
filemap_file = check_filemap(args.map, filemap_file, cap)
file_map = read_yaml(filemap_file)


def find_next_key(keys: list[int] | set[int]) -> int:
    """Find next free key for file map dictionary."""
    keys_set = set(keys)
    i = 1
    while i in keys_set:
        i += 1
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
            f"{RB}No projects found in the file map! \
            Provide a project name.{RST}"
        )


def update_file_map(project, src, trg):
    next_key = find_next_key(list(get_all_maps(file_map).keys()))
    if project not in list(file_map.keys()):
        file_map[project] = {next_key: [src, trg]}
    else:
        file_map[project][next_key] = [src, trg]
    write_yaml(filemap_file, file_map)


if args.view:
    for project, paths in file_map.items():
        print(f"[{project}]:")
        for num, path in paths.items():
            num_str = f"{num:2}"
            print(f"    [{num_str}]: {Path(path[0]).name}")
    exit(0)

if args.info:
    try:
        num = int(args.info)
    except ValueError:
        cap.error(f"Item '{args.info}' is not a valid number!")
    items = get_all_maps(file_map)
    if num not in items:
        cap.error(f"Item '{num}' not found in file map!")

    project_name = next(
        (project for project, paths in file_map.items() if num in paths), None
    )

    print(f"Item '{num}' in project '{project_name}':")
    print(f"  Source: {items[num][0]}")
    print(f"  Target: {items[num][1]}")
    exit(0)


def validate_config_and_args(args):
    """
    Validate configuration file and artguments.
    """
    if args.config:
        if not file_exists(args.config):
            cap.error(
                f"{RB}You must specify a valid \
            configuration file using -c or --config!{RST}"
            )
        return read_yaml(args.config)
    else:
        required_args = [
            args.remote,
            args.username,
            args.ssh_port,
            args.local_root_dir,
        ]
        if not all(required_args):
            cap.error(f"{RB}Insufficient arguments provided!{RST}")
        return {}


def validate_local_files(local_root_dir, source):
    """
    Validate local root directory and source file.
    """
    if not dir_exists(local_root_dir):
        cap.error(
            f"{RB}You must specify a valid local root directory using \
            -l or --local_root_dir!{RST}"
        )
    if not file_exists(local_root_dir / source):
        cap.error(f"{RB}You must specify a valid file to add using!{RST}")


def find_remote_file(source, ssh_port, username, host) -> str | None:
    """
    Search for the target file on remote system.
    """
    result = run(
        [
            "ssh",
            "-p",
            str(ssh_port),
            f"{username}@{host}",
            "find",
            "/",
            "-name",
            str(source.name),
            "2>/dev/null",
        ],
        stdout=PIPE,
        stderr=STDOUT,
        text=True,
    ).stdout.splitlines()

    if not result:
        print(f"{RB}File '{source.as_posix()}' not found on remote host!{RST}")
        exit(1)
    elif len(result) > 1:
        print(
            f"{CB}Multiple files found with the same name! \n\
            Possible candidate(s) highlighted. \n\
            Hit '0' if none is suitable.{RST}"
        )
        for num, candidate in enumerate(result, start=1):
            highlight = (
                f"{GB}[{num:2}]: {candidate}{RST}"
                if Path(candidate).parts[-2] == source.parts[-2]
                else f"[{num:2}]: {candidate}"
            )
            print(highlight)
        choice = input("Select remote file to use: ")
        try:
            choice = int(choice)
            if choice < 1 or choice > len(result):
                raise ValueError
            return result[choice - 1]
        except ValueError:
            print(f"{RB}Invalid choice!{RST}")
            exit(1)
    return result[0]


if args.add:
    source = Path(args.add)
    config = validate_config_and_args(args)

    host = config.get("rsync", {}).get("host", args.remote)
    username = config.get("rsync", {}).get("username", args.username)
    ssh_port = config.get("rsync", {}).get("port", args.ssh_port)
    local_root_dir = Path(
        config.get("rsync", {}).get("local_root_dir", args.local_root_dir)
    )

    validate_local_files(local_root_dir, source)

    synced_file_map = (
        Path(args.synced_file_map)
        if args.synced_file_map
        else script_root / "synced_file_map.yaml"
    )
    if not file_exists(synced_file_map):
        cap.error(
            f"{RB}Sync file map '{synced_file_map}' does not exist!{RST}"
        )
    synced_files = read_yaml(synced_file_map)

    project_name = get_project(args.project, file_map)
    target = synced_files.get(args.add, None)

    if not target:
        target = find_remote_file(source, ssh_port, username, host)

    update_file_map(project_name, args.add, target)
    exit(0)

if args.delete:
    try:
        num = int(args.delete)
    except ValueError:
        cap.error(f"{RB}Invalid item number '{args.delete}'!{RST}")
    if num not in (get_all_maps(file_map)):
        cap.error(f"Item '{num}' not found in file map!")
    # delete the item from the file map
    project = ""
    for proj, items in file_map.items():
        if num in items:
            project = proj
            del file_map[proj][num]
    # if project is empty after adding, delete it too
    if len(file_map[project]) == 0:
        del file_map[project]

    write_yaml(filemap_file, file_map)
    exit(0)

print(f"{CB}Please specify at least one arguments!{RST}")
cap.print_usage()
