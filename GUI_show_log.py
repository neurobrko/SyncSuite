#!/usr/bin/env /home/marpauli/.cache/pypoetry/virtualenvs/syncsuite-HX8knUdy-py3.12/bin/python

from pysimplegui import PySimpleGUI as sg
from os import path
from time import strftime
from subprocess import run
from GUI_rsync_to_remote import get_center, read_yaml

script_root = path.dirname(path.realpath(__file__))
conf_file = path.join(script_root, "sync_conf.yaml")
log_filename = f"r2r-{strftime('%y%m%d')}.log"
log_file = path.join(script_root, "log", log_filename)

conf = read_yaml(conf_file)
sg.theme(conf["gui"]["sg_theme"])
ERRTC = conf["gui"]["ERRTC"]
log_viewer = conf["gui"]["text_editor"]

if not path.exists(log_file):
    layout_warn = [
        [
            sg.Text(
                "Today's log file does not exist!",
                text_color=ERRTC,
                justification="center",
            )
        ],
        [sg.Push(), sg.Button("Exit"), sg.Push()],
    ]
    window_warn = sg.Window(
        "Error!", layout_warn, finalize=True, icon="icons/view_log.png"
    )
    window_warn.move((pos := get_center(window_warn))[0], pos[1])
    window_warn.bind("<Escape>", "-ESCAPE-")
    while True:
        event = window_warn.read()[0]
        if event in ("Exit", sg.WIN_CLOSED, "-ESCAPE-"):
            break
    window_warn.close()
    exit()

with open(log_file, "r") as f:
    log_content = f.readlines()

last_log = []

for line in log_content[-3::-1]:
    last_log.insert(0, line)
    if "=> SYNC START <=" in line:
        break

layout = [
    [sg.Listbox(values=last_log, size=(100, len(last_log)), font="Helvetica")],
    [sg.Button("View complete log", key="-VIEW-LOG-"), sg.Push(), sg.Button("Exit")],
]


window = sg.Window("Last log", layout, finalize=True, icon="icons/view_log.png")
window.move((pos := get_center(window))[0], pos[1])
window.bind("<Escape>", "-ESCAPE-")
while True:
    event = window.read()[0]
    if event in ("Exit", sg.WIN_CLOSED, "-ESCAPE-"):
        break
    if event == "-VIEW-LOG-":
        run(
            [log_viewer, log_file],
        )
        break

    window.close()
