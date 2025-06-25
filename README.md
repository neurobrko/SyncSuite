# Sync Suite - Synchronize files to remote server

**author:** elvis (Marek Paulik)\
**mail:** [elvis@elvis.sk](mailto:elvis@elvis.sk)

### Set of tools to manage and perform synchronization of files to remote system using rsync. Script also outputs its action to console and logs them.

> **IMPORTANT:**\
> You need to use passwordless ssh key on remote machine to work! [Quick Guide to setup SSH w/o password](https://www.linuxtrainingacademy.com/ssh-login-without-password/)

## Features
- Synchronize selected files, whole projects or all files to remote machine
- `-c` and `-m` flags allow you to use different configurations or filemaps
- Synchronization can run in ssh multiplex mode, with socket staying alive for 20 seconds after last command
- Run using script via CLI with options
- Restart service(s) on remote machine after sync
- Add files to path mapping dictionary with ability to find their counterparts on remote and group them in projects
- Script logs each days work in separate file.

## Components
### rsync_to_remote.py
Standalone CLI script to perform synchronization. Configuration can be loaded with `-c` flag, file map with `-m` flag.
All Settings can be altered by using number of arguments. For more details see `rsync_to_remote.py -h`

### file_map.py
Script to view and manage file map file. `-sm` search for remote counterparts in synced file map, before resorting to search
on remote via ssh. For more details see `file_map.py -h`

### create_path_sync.py
To speed up search for possible remote counterpart to local file, `file_map.py` script creates `synced_file_map.yaml`.\
This is pure helper script without any checks and very little verbosity! It talks to you through Traceback.\
It needs a `sync_conf.yaml` config file in same directory and result is saved also there. It is recommended to copy it elsewhere
to avoid overwriting in the future.

### log_cleanup.py
Run this script manually or create a cron job for it to periodically delete obsolete log files.

### sync_conf.yaml
Configuration file containing all settings to run the script. All settings in it can be overridden with CLI arguments.

**format:** {category: {var1: val1, var2: val2}}
- **ALWAYS** make backup before editing by hand!

**RSYNC SETTINGS**
- when editing port, always edit rsync option accordingly!
- *local_root_dir* should ALWAYS contain valid path, BUT if empty, must be "" (same goes for default_dir)

**SCRIPT SETTINGS**
- set timeouts to 0 to skip check
- (future option for GUI) set *default_dir* to specify dir to start browsing from *local_root_dir* (LRD) is used if empty, if LRD empty script parent dir is used

**SYNC SETTINGS**
> **INFO:**\
Override hierarchy: sync_all > project > file_keys
- *sync_all*: sync all files in file_map.yaml; value: true/false
- *project*: sync all files from specified project, null for None
- *file_keys*: list of file pairs to sync WARNING: Must be list even with zero or single item! hint: empty_list: []

**SERVICES SETTINGS**
- *restart_services*: defaults to False. It is recommended to never save this option as True to avoid unnecessary service restarting.
- *services*: same as file_keys, must allways be a list. services must allways be duffixed with '.service' or '.target'.

### file_map.yaml
File contains local <-> remote filepaths pairs grouped into projects. Local paths are relative to working or repo direcory,
remote are full paths. You should **NEVER** edit it by hand!\
**format:** {project: [source/path, target/path]}

### synced_file_map.yaml
Result of `create_path_sync.py`

## Installation
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
> **IMPORTANT:**\
> To run the scripts from anywhere without activating virtual environment, edit shebang in all .py files!
```python
#!/usr/bin/env /absolute/path/to/env/pyton/executable/copied/before
```

(Optional) Create aliases

`~/.bash_aliases`
```sh
# SyncSuite rsync to remote
alias r2r='/your/sync_suite/dir/rsync_to_remote.py -c /your/conf_file/dir/sync_conf.yaml -m /your/file_map/dir/file_map.yaml'
# SyncSuite file map
alias rfm='/your/sync_suite/dir/file_map.py -c /your/conf_file/dir/sync_conf.yaml -m /your/file_map/dir/file_map.yaml -sm /your/file_map/dir/synced_file_map.yaml'
```
> **NOTE:**\
> To see more *.bash_aliases magic* visit my [DevTools repo](https://github.com/neurobrko/DevTools).

## TODO
- Create GUI with NiceGUI or at least reuse PySimpleGUI implementation from previous version
- Add some checks and options to `create_path_sync.py`
- Cleanup, rafactor and add a bit of verbosity to `file_map.py`
