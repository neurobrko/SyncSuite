#!/usr/bin/env /home/marpauli/.cache/pypoetry/virtualenvs/syncsuite-HX8knUdy-py3.12/bin/python

from argparse import RawDescriptionHelpFormatter
from pathlib import Path
from subprocess import PIPE, STDOUT, run

from common import (
    CB,
    GB,
    RB,
    RST,
    CustomArgParser,
    config_editor,
    config_filename,
    dir_exists,
    file_exists,
    filemap_filename,
    get_all_maps,
    get_configuration_file,
    read_yaml,
    synced_filemap_filename,
    write_yaml,
)
# import debugpy
#
# debugpy.listen(5678)
# print(f"{CB}Waiting for debugger to attach...{RST}")
# debugpy.wait_for_client()

script_root = Path(__file__).resolve().parent

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
    "-v", "--view", help="List filepath in file_map file", action="store_true"
)
cap.add_argument(
    "-i",
    "--info",
    metavar="NUM",
    help="details about the file_map item",
)
cap.add_argument(
    "-a", "--add", metavar="FILE", help="Add a new file to the file_map"
)
cap.add_argument(
    "-d",
    "--delete",
    nargs="?",
    const=True,
    default=None,
    metavar="NUM | null",
    help="Delete an item or project from the file_map",
)
cap.add_argument(
    "-m",
    "--map",
    metavar="FILE",
    help="Path to file to be used as source or target (depending on action)",
)
cap.add_argument(
    "-l",
    "--local_root_dir",
    metavar="DIR",
    help="Local root directory for source files",
)
cap.add_argument(
    "-p",
    "--project",
    metavar="NAME",
    help="Project name to add file to or to be deleted",
)
cap.add_argument(
    "-cd",
    "--config_dir",
    metavar="DIR",
    help="Path to dir containing config file",
)
cap.add_argument(
    "-c", "--config", metavar="FILE", help="Path to configuration file"
)
cap.add_argument(
    "-r", "--remote", metavar="HOST", help="Remote host for synchronization"
)
cap.add_argument("-u", "--username", metavar="USER", help="Remote username")
cap.add_argument("-s", "--ssh_port", metavar="NUM", help="SSH port")
cap.add_argument(
    "-sm",
    "--synced_file_map",
    metavar="FILE",
    help="Path to synced_file_map.yaml",
)
cap.add_argument(
    "-e",
    "--edit",
    help="Edit file map by hand. NOT RECOMMENDED!",
    action="store_true",
)

args = cap.parse_args()

filemap_file = get_configuration_file(
    args.config_dir, args.map, filemap_filename, return_only_path=True
)

# If editing by hand was selected, override everything else
if args.edit:
    run([config_editor, filemap_file])
    exit(0)

file_map = read_yaml(filemap_file)


def find_next_key(keys: list[int] | set[int]) -> int:
    """Find next free key for file map dictionary."""
    keys_set = set(keys)
    i = 1
    while i in keys_set:
        i += 1
    return i


def get_project(file_map: dict, project_name: str | None = None) -> str:
    """
    Check if project name was provided and return it
    or return the last project name in the file map.
    :param project_name: name of the project to check
    :param file_map: file map dictionary
    :return: project name
    """
    if project_name:
        return project_name
    elif file_map:
        return list(file_map.keys())[-1]
    else:
        cap.error(
            f"{RB}No projects found in the file map! Provide a project name.{RST}"
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


def validate_config_and_args(config_file: Path | None, args: dict) -> dict:
    """
    Validate configuration file and artguments.
    """
    if config_file:
        return read_yaml(config_file)
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
            f"{RB}You must specify a valid local root directory using "
            f"-l or --local_root_dir!{RST}"
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
            f"{CB}Multiple files found with the same name! \n"
            f"Possible candidate(s) highlighted. \n"
            f"check_filemapt '0' if none is suitable.{RST}"
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
    config_file = get_configuration_file(
        args.config_dir, args.config, config_filename
    )
    source = Path(args.add)
    config = validate_config_and_args(config_file, args)

    host = config.get("rsync", {}).get("host", args.remote)
    username = config.get("rsync", {}).get("username", args.username)
    ssh_port = config.get("rsync", {}).get("port", args.ssh_port)
    local_root_dir = Path(
        config.get("rsync", {}).get("local_root_dir", args.local_root_dir)
    )

    validate_local_files(local_root_dir, source)

    synced_file_map = get_configuration_file(
        args.config_dir, args.synced_file_map, synced_filemap_filename
    )
    target = None
    if synced_file_map:
        synced_files = read_yaml(synced_file_map)
        target = synced_files.get(args.add)

    if not target:
        target = find_remote_file(source, ssh_port, username, host)

    project_name = get_project(file_map, args.project)

    update_file_map(project_name, args.add, target)

    print(f"{CB}Added '{source}' to project: '{project_name}'!{RST}")
    exit(0)

if args.delete:
    if isinstance(args.delete, bool):
        if args.project:
            if args.project in file_map:
                file_map.pop(args.project)
                print(f"{CB}Deleted project '{args.project}'!{RST}")
            else:
                cap.error(f"{RB}Project '{args.project}' not found!{RST}")
        else:
            cap.error(f"{RB}Please specify file or project to delete!{RST}")
    else:
        try:
            num = int(args.delete)
        except ValueError:
            cap.error(f"{RB}Invalid item number '{args.delete}'!{RST}")
        if num not in (get_all_maps(file_map)):
            cap.error(f"Item '{num}' not found in file map!")
        # delete the item from the file map
        project = ""
        source_file = ""
        for proj, items in file_map.items():
            if num in items:
                project = proj
                source_file = file_map[proj][num][0]
                del file_map[proj][num]
                break
        # if project is empty after adding, delete it too
        if len(file_map[project]) == 0:
            del file_map[project]

        print(
            f"{CB}Deleted '[{num}]: {source_file}' from project: '{project}'!"
            f"{RST}"
        )

    write_yaml(filemap_file, file_map)
    exit(0)

cap.error(f"{CB}Please specify at least one arguments!{RST}")
