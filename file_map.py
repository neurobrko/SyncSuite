#!/usr/bin/env /home/marpauli/.cache/pypoetry/virtualenvs/syncsuite-HX8knUdy-py3.12/bin/python
"""
WIP
"""

from argparse import RawDescriptionHelpFormatter
from pathlib import Path

from common import CB, RB, RST, CustomArgParser, get_all_maps, read_yaml

script_root = Path(__file__).resolve().parent

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

if not args.map or not Path(args.map).exists() or not Path(args.map).is_file():
    cap.error("You must specify a valid file map using -m or --map!")
    cap.exit(1)

file_map = read_yaml(args.map)

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
    if not args.config:
        print(f"{CB}Configuration file was not specified! Using CLI arguments.{RST}")
        if not all([args.remote, args.username, args.ssh_port, args.local_root_dir]):
            cap.error(f"{RB}Insufficient arguments provided!{RST}")
            cap.exit(1)
    if args.config and not Path(args.config).exists():
        cap.error(f"{RB}Configuration file '{args.config}' does not exist!{RST}")
        cap.exit(1)
    else:
        config = read_yaml(args.config)
        host = config.get("rsync", {}).get("host", args.remote)
        username = config.get("rsync", {}).get("username", args.username)
        ssh_port = config.get("rsync", {}).get("port", args.ssh_port)
        local_root_dir = Path(
            config.get("rsync", {}).get("local_root_dir", args.local_root_dir)
        )
    if not local_root_dir.exists() or not local_root_dir.is_dir():
        cap.error(
            "You must specify a valid local root directory using -l or --local_root_dir!"
        )
        cap.exit(1)
    if (
        not (local_root_dir / args.add).exists()
        or not Path(local_root_dir / args.add).is_file()
    ):
        print(local_root_dir / args.add)
        print(type(local_root_dir / args.add))
        cap.error("You must specify a valid file to add using -a or --add!")
        cap.exit(1)

    # try to find the file in generated sync_file_map.yaml
    synced_file_map = (
        Path(args.synced_file_map)
        if args.synced_file_map
        else script_root / "synced_file_map.yaml"
    )
    if synced_file_map.exists() and synced_file_map.is_file():
        synced_files = read_yaml(synced_file_map)
        target = synced_files.get(args.add, None)
        if target:
            # add to file map
            print(f"{CB}File '{args.add}' exists in the sync file map!{RST}")

        else:
            # try ssh
            print(f"{CB}File '{args.add}' does not exist in the sync file map!{RST}")
    else:
        print(f"{CB}Sync file map '{synced_file_map}' does not exist!{RST}")
