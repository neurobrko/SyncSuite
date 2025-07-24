#!/usr/bin/env /home/marpauli/.cache/pypoetry/virtualenvs/syncsuite-HX8knUdy-py3.12/bin/python

from argparse import RawDescriptionHelpFormatter
from pathlib import Path
from subprocess import run

from common import (
    CB,
    GB,
    RB,
    RST,
    CustomArgParser,
    config_editor,
    config_filename,
    get_remote_files,
    dir_exists,
    file_exists,
    filemap_filename,
    get_all_maps,
    get_configuration_file,
    read_yaml,
    synced_filemap_filename,
    update_file_map,
    write_yaml,
)

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
    metavar="NUM | STR | null",
    help="Delete an item or task from the file_map",
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
    "-t",
    "--task",
    metavar="NAME",
    help="Task name to add file to or to be deleted",
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
cap.add_argument(
    "-g",
    "--gui",
    action="store_true",
    help="Suppress some output to use with GUI",
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


def get_task(file_map: dict, task_name: str | None = None) -> str:
    """
    Check if task name was provided and return it
    or return the last task name in the file map.
    :param task_name: name of the task to check
    :param file_map: file map dictionary
    :return: task name
    """
    if task_name:
        return task_name
    elif file_map:
        return list(file_map.keys())[-1]
    else:
        cap.error(
            f"{RB}No task found in the file map! Provide a task name.{RST}"
        )


if args.view:
    for task, paths in file_map.items():
        print(f"[{task}]:")
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

    task_name = next(
        (task for task, paths in file_map.items() if num in paths), None
    )

    print(f"Item '{num}' in task '{task_name}':")
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
        cap.error(f"{RB}You must specify a valid file to add!{RST}")


def find_remote_file(
    source, ssh_port, username, host, remote_dir
) -> str | None:
    result = get_remote_files(source, ssh_port, username, host, remote_dir)
    if not result:
        print(f"{RB}File '{source.as_posix()}' not found on remote host!{RST}")
        exit(1)
    if len(result) > 1:
        print(
            f"{CB}Multiple files found with the same name!{RST}"
            f" (Possible candidate(s) highlighted.) \n"
            f"{CB}Type '0' if none is suitable.{RST}"
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
            if choice == 0:
                print(f"{CB}No candidate selected.{RST}")
                exit(0)
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
    remote_browse_dir = config.get("script", {}).get("default_browse_dir", "/")

    validate_local_files(local_root_dir, source)

    synced_file_map = get_configuration_file(
        args.config_dir, args.synced_file_map, synced_filemap_filename
    )
    target = None
    if synced_file_map:
        synced_files = read_yaml(synced_file_map)
        target = synced_files.get(args.add)

    if not target:
        print(
            f"{CB}File not found in Synced filemap. Performing ssh search...{RST}"
        )
        target = find_remote_file(
            source, ssh_port, username, host, remote_browse_dir
        )

    task_name = get_task(file_map, args.task)

    update_file_map(task_name, args.add, target, file_map, filemap_file)

    print(f"{CB}Added '{source}' to task: '{task_name}'!{RST}")
    exit(0)

if args.delete:
    if isinstance(args.delete, bool):
        if args.task:
            if args.task in file_map:
                file_map.pop(args.task)
                print(f"{CB}Deleted task '{args.task}'!{RST}")
            else:
                cap.error(f"{RB}Task '{args.task}' not found!{RST}")
        else:
            cap.error(f"{RB}Please specify file or task to delete!{RST}")
    else:
        try:
            num = int(args.delete)
        except ValueError:
            cap.error(f"{RB}Invalid item number '{args.delete}'!{RST}")
        if num not in (get_all_maps(file_map)):
            cap.error(f"Item '{num}' not found in file map!")
        # delete the item from the file map
        task = ""
        source_file = ""
        for tsk, items in file_map.items():
            if num in items:
                task = tsk
                source_file = file_map[tsk][num][0]
                del file_map[tsk][num]
                break
        # if task is empty after adding, delete it too
        if len(file_map[tsk]) == 0:
            del file_map[tsk]

        print(
            f"{CB}Deleted '[{num}]: {source_file}' from task: '{task}'!{RST}"
        )

    write_yaml(filemap_file, file_map)
    exit(0)

cap.error(f"{CB}Please specify at least one arguments!{RST}")
