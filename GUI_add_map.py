#!/usr/bin/env /home/marpauli/.cache/pypoetry/virtualenvs/syncsuite-HX8knUdy-py3.12/bin/python

from GUI_rsync_to_remote import get_map_keys, get_center, read_yaml
from subprocess import run, PIPE, STDOUT
from os import path, chdir
from pysimplegui import PySimpleGUI as sg
import yaml
import re

# define paths
script_root = path.dirname(path.realpath(__file__))
filemap_file = path.join(script_root, "file_map.yaml")
conf_file = path.join(script_root, "sync_conf.yaml")
icon_file = path.join(script_root, "icons/tmp/add_map.png")
find_path = "/"

# import configuration variables
config = read_yaml(conf_file)

# load variables
# create empty variables just for pyCharm not to raise undefined variable warning.
host = username = port = local_root_dir = rsync_options = ""
sg_theme = DEFTC = CHANGETC = ERRTC = ""
vars().update(config["rsync"])
vars().update(config["gui"])

# load file pair map
file_map = read_yaml(filemap_file)

map_keys = get_map_keys(file_map)

sg.theme(sg_theme)
input_text_fields = {
    "-HOST-": host,
    "-USER-": username,
    "-PORT-": port,
    "-FIND-PATH-": find_path,
}

layout = [
    [sg.Text("Remote settings:")],
    [
        sg.Text("host:"),
        sg.InputText(
            size=(20, 1),
            key="-HOST-",
            default_text=host,
            enable_events=True,
        ),
        sg.Text("  user:"),
        sg.InputText(
            size=(20, 1),
            key="-USER-",
            default_text=username,
            enable_events=True,
        ),
        sg.Text("   port:"),
        sg.InputText(
            size=(10, 1),
            key="-PORT-",
            default_text=port,
            enable_events=True,
        ),
        sg.Text("   find from dir:"),
        sg.InputText(
            size=(42, 1),
            key="-FIND-PATH-",
            default_text=find_path,
            enable_events=True,
        ),
    ],
    [sg.HSeparator(pad=((10, 10), (10, 20)), color="black")],
    [sg.Text("Source:")],
    [
        sg.InputText(size=(120, 1), key="-SOURCE-", enable_events=True),
        sg.FileBrowse(target="-SOURCE-"),
    ],
    [
        sg.Text("Target:"),
        sg.Push(),
        sg.Text(f"(Local root directory: {local_root_dir})"),
    ],
    [
        sg.InputText(size=(120, 1), key="-TARGET-", enable_events=True),
        sg.Button("Get target"),
    ],
    [sg.Listbox(values=[], enable_events=True, size=(131, 10), key="-FILE-LIST-")],
    [
        sg.Text("Add new project:"),
        sg.InputText(
            size=(20, 1), key="-NEW-PROJECT-", enable_events=True, default_text=""
        ),
        sg.Text("or select project:"),
        sg.Combo(
            content := list(file_map.keys()),
            default_value=content[-1],
            key="-PROJECT-",
            enable_events=True,
            size=15,
        ),
        sg.Push(),
        sg.Button("Add to project"),
        sg.Button("Exit"),
    ],
    [sg.HSeparator(pad=((10, 10), (10, 10)), color="black")],
    [sg.Text("", text_color=ERRTC, key="-ERROR-FIELD-")],
]


def get_remote_target(filepath, remote_host, user, ssh_port, find_dir) -> list:
    """Get path to remote target based on local name."""
    remote_files = (
        run(
            [
                "ssh",
                "-p",
                f"{ssh_port}",
                f"{user}@{remote_host}",
                "find",
                find_dir,
                "-name",
                f"{path.basename(filepath)}",
            ],
            text=True,
            stdout=PIPE,
            stderr=STDOUT,
        )
        .stdout.strip()
        .split("\n")
    )
    if len(remote_files) == 1 and remote_files[0] == "":
        return []
    else:
        return remote_files


def find_next_key(keys: list):
    """Find next free key for file map dictionary."""
    for i in range(1, len(keys) + 2):
        if i not in keys:
            return i


val_host, val_user, val_port = (host, username, port)


def validate_changes(vals, window):
    return_value = True
    if vals["-HOST-"] != host:
        global val_host
        if vals["-HOST-"] != "localhost":
            if len(host_ip := vals["-HOST-"].split(".")) != 4:
                window["-ERROR-FIELD-"].update("Invalid host!")
                return_value = False
            try:
                [int(add) for add in host_ip]
            except Exception as err:
                window["-ERROR-FIELD-"].update(
                    f"Invalid host! {type(err).__name__}: {err}"
                )
                return_value = False
        else:
            val_host = vals["-HOST-"]
    if vals["-USER-"] != username:
        global val_user
        pattern = re.compile(r"[a-zA-Z0-9]+")
        if not re.fullmatch(pattern, vals["-USER-"]):
            window["-ERROR-FIELD-"].update("Invalid username!")
            return_value = False
        else:
            val_user = vals["-USER-"]
    if vals["-PORT-"] != port:
        global val_port
        try:
            int(vals["-PORT-"])
            val_port = vals["-PORT-"]
        except Exception as err:
            window["-ERROR-FIELD-"].update(f"Invalid port! {type(err).__name__}: {err}")
            return_value = False

    return return_value


def update_yaml(project, src, trg):
    next_key = find_next_key(map_keys)
    if project not in list(file_map.keys()):
        file_map[project] = {next_key: [src, trg]}
    else:
        file_map[project][next_key] = [src, trg]
    with open(filemap_file, "w") as f:
        yaml.dump(file_map, f, sort_keys=False)


def main():
    if path.exists(local_root_dir):
        chdir(local_root_dir)
    else:
        chdir(script_root)
    window = sg.Window(
        "Set file paths for rsync_to_remote.py", layout, icon=icon_file, finalize=True
    )
    window.move((pos := get_center(window))[0], pos[1])
    window.bind("<Escape>", "-ESCAPE-")

    while True:
        event, values = window.read()
        if event in ("Exit", sg.WIN_CLOSED, "-ESCAPE-"):
            break
        if event in list(input_text_fields.keys()):
            if input_text_fields[event] != values[event]:
                window[event].update(text_color=CHANGETC)
            else:
                window[event].update(text_color=DEFTC)
        if event == "Get target":
            window["-ERROR-FIELD-"].update("")
            window.refresh()
            if (
                values["-HOST-"] != host
                or values["-USER-"] != username
                or values["-PORT-"] != port
            ) and not validate_changes(values, window):
                continue
            if path.exists(values["-SOURCE-"]):
                try:
                    file_list = get_remote_target(
                        values["-SOURCE-"],
                        val_host,
                        val_user,
                        val_port,
                        values["-FIND-PATH-"],
                    )
                except Exception as e:
                    print(f"{type(e).__name__}: {e}")
                    break

                if isinstance(file_list, list):
                    match len(file_list):
                        case 0:
                            window["-ERROR-FIELD-"].update("No target file found!")
                        case 1:
                            if file_list[0].startswith(("ssh:", "find:")):
                                window["-ERROR-FIELD-"].update(file_list[0])
                            else:
                                window["-FILE-LIST-"].update(file_list)
                                window["-TARGET-"].update(file_list[0])
                        case _:
                            window["-FILE-LIST-"].update(file_list)
            else:
                window["-ERROR-FIELD-"].update("Invalid source path!")
        if event == "-FILE-LIST-":
            window["-TARGET-"].update(values["-FILE-LIST-"][0])
        if event == "Add to project":
            window["-ERROR-FIELD-"].update("")
            if values["-NEW-PROJECT-"] != "":
                project = values["-NEW-PROJECT-"]
            else:
                project = values["-PROJECT-"]
            if validate_changes(values, window):
                if values["-SOURCE-"] == "":
                    window["-ERROR-FIELD-"].update("Empty source path!")
                elif not path.exists(values["-SOURCE-"]):
                    window["-ERROR-FIELD-"].update("Invalid source path!")
                elif values["-TARGET-"] == "":
                    window["-ERROR-FIELD-"].update("Empty target path!")
                else:
                    update_yaml(project, values["-SOURCE-"], values["-TARGET-"])
                    window["-ERROR-FIELD-"].update(
                        f"Added {values['-SOURCE-']} to project {project}!"
                    )
                    window["-SOURCE-"].update("")
                    window["-TARGET-"].update("")
                    window["-FILE-LIST-"].update([])

    window.close()


if __name__ == "__main__":
    main()
