#!/usr/bin/env /home/marpauli/.cache/pypoetry/virtualenvs/syncsuite-HX8knUdy-py3.12/bin/python

"""
############################### !!! WARNING !!! ###############################
# This is a helper script! There is very little checks performed, so if       #
# something goes south, you'll see some quality Traceback in the terminal. :) #
###############################################################################

Generate local yaml file containing file pairs, that will be used to speed up
process of adding files to file map. 'file_map -a' checks the synced_file_map
first and if file is not found, then it will try finding it via ssh.
Result is written in target file if specified, or target dir as
'synced_file_map.yaml' file or in the script root if target is not specified.

The process is quite lengthy, so try to have a lunch while it is running... ;)
and repeat it once in a while. (~400 files takes around 6 minutes)
"""

from argparse import RawDescriptionHelpFormatter
from os import chdir
from pathlib import Path
from subprocess import PIPE, STDOUT, run
from time import sleep

from tqdm import tqdm

from common import (
    BLD,
    CB,
    I_LOGGER,
    RB,
    RST,
    CustomArgParser,
    get_configuration_file,
    ignored_extensions,
    ignored_files,
    ignored_folders,
    read_yaml,
    write_yaml,
)

DRY_RUN = False

script_root = Path(__file__).resolve().parent
config_filename = Path("sync_conf.yaml")
synced_filemap_filefilename = Path("synced_file_map.yaml")
tmp_filemap_file = script_root / "tmp_sync.yaml"

# setup arg parser
help_message = """
    Generate local file containing file pairs, that will be used to
    speed up process of adding files to file map.
    Configuration file is required and target will be overwritten
    without warning, if already exists!"""
cap = CustomArgParser(
    description=help_message,
    formatter_class=RawDescriptionHelpFormatter,
)

cap.add_argument(
    "-cd",
    "--config_dir",
    help="Source dir of config file and target for result",
)
cap.add_argument("-c", "--config", help="Configuration file name")
cap.add_argument("-t", "--target", help="Target file name")

args = cap.parse_args()

config_file = get_configuration_file(
    args.config_dir, args.config, config_filename, True
)


def get_target_file():
    if args.target:
        target_path = Path(args.target)
        if not target_path.suffix and target_path.is_dir():
            return target_path / synced_filemap_filefilename
        if (
            target_path.suffix in [".yaml", ".yml"]
            and target_path.parent.is_dir()
        ):
            return target_path
        print(f"{RB}Invalid target!{RST}")
        exit(1)
    elif args.config_dir:
        return Path(args.config_dir) / synced_filemap_filefilename
    else:
        print(
            f"{CB}{synced_filemap_filefilename} will be "
            f"saved in {script_root}!{RST}"
        )
        return script_root / synced_filemap_filefilename


synced_filemap_file = get_target_file()

sync_conf = read_yaml(config_file)

ssh_host = sync_conf["rsync"]["host"]
ssh_usr = sync_conf["rsync"]["username"]
ssh_port = sync_conf["rsync"]["port"]
root_dir = sync_conf["rsync"]["local_root_dir"]
remote_dir = sync_conf["script"]["default_browse_dir"]

file_map = {}
not_found_files = []
multiple_matches = []


def get_git_branch_name() -> str:
    """
    Get the current git branch name.
    """
    chdir(root_dir)
    res = run(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
        capture_output=True,
        text=True,
    )
    chdir(script_root)
    if res.returncode != 0:
        raise RuntimeError("Failed to get git branch name.")
    return res.stdout.strip()


def get_remote_hostname() -> str:
    """
    Get the remote hostname and open persistent SSH connection.
    """
    hostname = (
        run(
            [
                "ssh",
                "-M",
                "-S",
                "/tmp/pathsync_socket",
                "-o",
                "ControlPersist=20",
                "-p",
                str(ssh_port),
                f"{ssh_usr}@{ssh_host}",
                "hostname",
            ],
            stdout=PIPE,
        )
        .stdout.decode("utf-8")
        .strip()
    )
    return hostname


def get_top_level_dir(file: str | Path, levels=1) -> str:
    """
    Get the n top-level directories of a file path.

    :param file: The file path as a string or Path object.
    :param levels: Number of top-level directories to return.
    :return: The top-level directory as a string.
    """

    if isinstance(file, str):
        file = Path(file)
    path = "/".join(file.parts[-(levels + 1) :])
    return path


def print_and_log_results(files: list, not_found: list, multiple: list):
    print(
        f"\n{BLD}{len(files)} local files found.{RST} \
        {len(files) - len(not_found) - len(multiple)} "
        f"files matched on remote host.{RST}"
    )
    if not_found:
        print(
            f"{RB}{len(not_found)} files not found{RST} on remote host. "
            f"See dev log for details."
        )
        I_LOGGER.warning(not_found, "Files not found on remote host:")
    if multiple:
        print(
            f"{RB}{len(multiple)} files have multiple matches{RST} on remote "
            f"host. See dev log for details."
        )
        I_LOGGER.warning(
            multiple,
            "Multiple matches found for files on remote host:",
        )


def filter_results_by_top_level(
    results: list, local_path: str, levels: int
) -> list:
    """
    Filter results based on top-level directory match.

    :param results: List of file paths from the remote host.
    :param local_path: Local file path.
    :param levels: Number of top-level directories to match.
    :return: Filtered list of results.
    """
    local_top_level = get_top_level_dir(local_path, levels)
    return [
        path
        for path in results
        if local_top_level == get_top_level_dir(path, levels)
    ]


def find_match(file: Path):
    """
    Resolve the result of the SSH command to find the best match for the local
    file. If multiple matches are found, return the longest path match.
    If no matches are found, return None.
    """
    result = run(
        [
            "ssh",
            "-S",
            "/tmp/pathsync_socket",
            "-p",
            str(ssh_port),
            f"{ssh_usr}@{ssh_host}",
            "find",
            remote_dir,
            "-name",
            str(file.name),
            "2>/dev/null",
        ],
        stdout=PIPE,
        stderr=STDOUT,
        text=True,
    ).stdout.splitlines()

    if result:
        local_path = file.as_posix()
        relative_local_path = file.relative_to(root_dir).as_posix()

        match len(result):
            case n if n > 1:
                for levels in range(1, 4):
                    result = filter_results_by_top_level(
                        result, local_path, levels
                    )
                    if len(result) <= 1:
                        break
                match len(result):
                    case n if n > 1:
                        multiple_matches.append(relative_local_path)
                    case 1:
                        file_map[relative_local_path] = result[0]
                    case _:
                        not_found_files.append(relative_local_path)
            case 1:
                file_map[relative_local_path] = result[0]
            case _:
                not_found_files.append(relative_local_path)
    else:
        not_found_files.append(file.relative_to(root_dir).as_posix())


def main():
    # get all files in the root directory
    all_files = [
        file
        for file in Path(root_dir).rglob("*")
        if file.is_file()
        and not any(folder in file.parts for folder in ignored_folders)
        and not any(file.suffix == ext for ext in ignored_extensions)
        and not any(file.name == name for name in ignored_files)
    ]
    # Enable dry run to set ignored files, folders and extensions in common.py
    if DRY_RUN:
        print(*all_files)
        print(len(all_files))
        exit(0)

    branch = get_git_branch_name()
    host = get_remote_hostname()
    print(
        f"Syncing file paths from {CB}{root_dir}{RST} \n"
        f"against host {CB}{host}{RST} \n"
        f"to {CB}{synced_filemap_file.resolve()}{RST} \n"
        f"using branch {CB}{branch}{RST} as reference.\n"
    )

    # check if tmp_sync.yaml exists - indicating previously failed sync
    if tmp_filemap_file.exists():
        print(f"Temporary sync file found: {tmp_filemap_file}. Removing it.")
        tmp_filemap_file.unlink()

    with tqdm(
        total=len(all_files),
        desc="Finding matches",
        unit="file",
        ncols=80,
        bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}]",
    ) as pbar:
        sleep(0.05)
        for file in all_files:
            find_match(file)
            pbar.update(1)

    print_and_log_results(all_files, not_found_files, multiple_matches)

    try:
        write_yaml(tmp_filemap_file, file_map)
    except Exception as e:
        print(f"Error writing to temporary file map: {e}")
        exit(1)

    # If the temporary file map was created successfully,
    # move it to the synced file map
    if synced_filemap_file.exists():
        synced_filemap_file.unlink()
    tmp_filemap_file.rename(synced_filemap_file)
    print(f"\n{BLD}Synced file map saved!{RST}")


if __name__ == "__main__":
    main()
