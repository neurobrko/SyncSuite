#!/usr/bin/env /home/marpauli/.cache/pypoetry/virtualenvs/syncsuite-HX8knUdy-py3.12/bin/python

from pysimplegui import PySimpleGUI as sg
from os import path
from subprocess import run
from GUI_rsync_to_remote import get_center, read_yaml
from platform import system

script_root = path.dirname(path.realpath(__file__))
conf_file = path.join(script_root, "sync_conf.yaml")
conf = read_yaml(conf_file)
text_editor = conf["gui"]["text_editor"]
terminal_app = conf["gui"]["terminal_app"]
sg.theme(conf["gui"]["sg_theme"])
FONT = "Ubuntu"

layout = [
    [
        sg.Text(
            "Sync Suite",
            font=(FONT, 36, "bold"),
            text_color="grey24",
            pad=((0, 0), (0, 10)),
        )
    ],
    [
        sg.Column(
            [
                [
                    sg.Image(
                        filename=path.join(script_root, "icons", "sync.png"),
                        enable_events=True,
                        key="-SYNC-",
                    ),
                ],
                [
                    sg.Text(
                        "Instant sync",
                        pad=((0, 0), (5, 25)),
                        font=(FONT, 12, "bold"),
                        enable_events=True,
                        key="-T-SYNC-",
                    )
                ],
                [
                    sg.Image(
                        filename=path.join(script_root, "icons", "map.png"),
                        enable_events=True,
                        key="-MAP-",
                    ),
                ],
                [
                    sg.Text(
                        "Show file map",
                        pad=((0, 0), (5, 25)),
                        font=(FONT, 12, "bold"),
                        enable_events=True,
                        key="-T-MAP-",
                    )
                ],
            ],
            element_justification="center",
            pad=((50, 25), (0, 0)),
        ),
        sg.Column(
            [
                [
                    sg.Image(
                        filename=path.join(script_root, "icons", "settings.png"),
                        enable_events=True,
                        key="-SETT-",
                    ),
                ],
                [
                    sg.Text(
                        "Sync options",
                        pad=((0, 0), (5, 25)),
                        font=(FONT, 12, "bold"),
                        enable_events=True,
                        key="-T-SETT-",
                    )
                ],
                [
                    sg.Image(
                        filename=path.join(script_root, "icons", "config.png"),
                        enable_events=True,
                        key="-CONF-",
                    ),
                ],
                [
                    sg.Text(
                        "Show config",
                        pad=((0, 0), (5, 25)),
                        font=(FONT, 12, "bold"),
                        enable_events=True,
                        key="-T-CONF-",
                    )
                ],
            ],
            element_justification="center",
            pad=((50, 25), (0, 0)),
        ),
        sg.Column(
            [
                [
                    sg.Image(
                        filename=path.join(script_root, "icons", "add.png"),
                        enable_events=True,
                        key="-ADD-",
                    ),
                ],
                [
                    sg.Text(
                        "Add files to sync",
                        pad=((0, 0), (5, 25)),
                        font=(FONT, 12, "bold"),
                        enable_events=True,
                        key="-T-ADD-",
                    )
                ],
                [
                    sg.Image(
                        filename=path.join(script_root, "icons", "log.png"),
                        enable_events=True,
                        key="-LOG-",
                    ),
                ],
                [
                    sg.Text(
                        "Show last log",
                        pad=((0, 0), (5, 25)),
                        font=(FONT, 12, "bold"),
                        enable_events=True,
                        key="-T-LOG-",
                    )
                ],
            ],
            element_justification="center",
            pad=((50, 25), (0, 0)),
        ),
    ],
]


window = sg.Window(
    "Run and manage your synchronization",
    layout,
    finalize=True,
    icon=path.join(script_root, "icons/tmp/rsync.png"),
    grab_anywhere=True,
)
window.move((pos := get_center(window))[0], pos[1])
terminal_run = [
    terminal_app,
    "--",
    "bash",
    "-c",
]

system = system().lower()

while True:
    event, values = window.read()
    if event in ("-SYNC-", "-T-SYNC-"):
        cmd = [path.join(script_root, "rsync_to_remote.py")]
        if "linux" in system:
            cmd = terminal_run + cmd
        run(cmd)
    if event in ("-SETT-", "-T-SETT-"):
        run(path.join(script_root, "GUI_rsync_to_remote.py"))
    if event in ("-ADD-", "-T-ADD-"):
        run(path.join(script_root, "GUI_add_map.py"))
    if event in ("-MAP-", "-T-MAP-"):
        run([text_editor, path.join(script_root, "file_map.yaml")])
    if event in ("-CONF-", "-T-CONF-"):
        run([text_editor, path.join(script_root, "sync_conf.yaml")])
    if event in ("-LOG-", "-T-LOG-"):
        run(path.join(script_root, "GUI_show_log.py"))
    if event == sg.WIN_CLOSED:
        break

window.close()
