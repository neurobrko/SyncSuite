# Sync Suite - Synchronize files to remote server

**author:** elvis (Marek Paulik)\
**mail:** [elvis@elvis.sk](mailto:elvis@elvis.sk)

### Set of tools to manage and perform synchronization of files to remote system using rsync. Script also outputs its action to console and logs them.

> **IMPORTANT**\
> Need to use passwordless ssh key on remote machine to work! [Quick Guide to setup SSH w/o password](https://www.linuxtrainingacademy.com/ssh-login-without-password/)

### Features
- Synchronize selected files, whole projects or all files to remote machine
- `-c` and `-m` flags allow you to use different configurations or filemaps
- Synchronization can run in ssh multiplex mode, with socket staying alive for 20 seconds after last command
- Run using script via CLI with options
- Restart service(s) on remote machine after sync
- Add files to path mapping dictionary with ability to find their counterparts on remote and group them in projects
- Script logs each days work in separate file.

### Components
**rsync_to_remote.py**\
Standalone CLI script to perform synchronization. Configuration can be loaded with `-c` flag, file map with `-m` flag.
All Settings can be altered by using number of arguments. For more details see `rsync_to_remote.py -h`

**file_map.py**\
Script to view and manage file map file. `-sm` search for remote counterparts in synced file map, before resorting to search
on remote via ssh. For more details see `file_map.py -h`

**create_path_sync.py**\
To speed up search for possible remote counterpart to local file, `file_map.py` script creates `synced_file_map.yaml`.\
This is pure helper script without any checks and very little verbosity! It talks to you through Traceback.\
It needs a `sync_conf.yaml` config file in same directory and result is saved also there. It is recommended to copy it elsewhere
to avoid overwriting in the future.

**log_cleanup.py**\
Run this script manually or create a cron job for it to periodically delete obsolete log files.

**sync_conf.yaml**\
Configuration file containing all settings to run the script. All settings in it can be overridden with CLI arguments.

**file_map.yaml**\
File contains local <-> remote filepaths pairs grouped into projects. Local paths are relative to working or repo direcory,
remote are full paths.

**synced_file_map.yaml**\
Result of `create_path_sync.py`

### Installation
```bash
mkdir /your/sync_suite/dir
cd /your/sync_suite/dir
git clone https://github.com/neurobrko/SyncSuite.git .
```
If using Poetry:
```bash
poetry init
poetry env info --path # copy output and use it later to alter .py scripts
```
If using python venv:
```bash
python3 -m venv .venv
source .venv/bin/python3
pip install -r requirements.txt
deactivate
cd .venv/bin
find "$PWD" -name python3 # copy output and use it later to alter .py scripts
```
(Optional) Create aliases

`~/.bash_aliases`
```sh
# SyncSuite rsync to remote
alias r2r='/your/sync_suite/dir/rsync_to_remote.py -c /your/conf_file/dir/sync_conf.yaml -m /your/file_map/dir/file_map.yaml'
# SyncSuite file map
alias rfm='/your/sync_suite/dir/file_map.py -c /your/conf_file/dir/sync_conf.yaml -m /your/file_map/dir/file_map.yaml -sm /your/file_map/dir/synced_file_map.yaml'
```
> **NOTE:** To see more *.bash_aliases magic* visit my DevTools repo.

### TODO
- Create GUI with NiceGUI or at least reuse PySimpleGUI implementation from previous version
- Add some checks and options to `create_path_sync.py`
- Cleanup, rafactor and add a bit of verbosity to `file_map.py`
