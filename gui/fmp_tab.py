from nicegui import ui
from pathlib import Path
from common import read_yaml
from gui.gui_common import path_ellipsis


tasks_values = {}
files_values = {}
files_cboxes = {}


def task_callback(task, value, file_map):
    tasks_values[task] = value
    for num in file_map[task]:
        files_cboxes[num].value = value
    ui.notify(tasks_values)


def file_callback(num, value):
    files_values[num] = value
    ui.notify(files_values)


def fmp_tab(cfg):
    filemap_file = cfg.filemap_file
    file_map = read_yaml(filemap_file)
    config_file = cfg.config_file
    config = read_yaml(config_file)
    file_keys = config.get("sync").get("file_keys", [])

    ui.label(path_ellipsis(filemap_file, depth=1)).classes(
        "text-lg font-semibold"
    )

    for task, files in file_map.items():
        tasks_values[task] = False
        ui.checkbox(
            task,
            on_change=lambda e, task=task: task_callback(
                task, e.value, file_map
            ),
        ).classes("text-s font-semibold")
        for num, files in files.items():
            num_value = num in file_keys
            files_values[num] = num_value
            with ui.checkbox(
                f"[{num:>2}] {Path(files[0]).name}",
                value=num_value,
                on_change=lambda e, num=num: file_callback(num, e.value),
            ) as cbox:
                files_cboxes[num] = cbox
                cbox.classes("pl-8")
                with ui.tooltip().classes("w-10/12"):
                    ui.html(
                        f"<b>src:</b> {files[0]}<br><b>trg:</b> {files[1]}"
                    ).classes("text-sm")

    with ui.grid(columns=2).classes("w-full"):
        ui.button("Use keys")
        with ui.row().classes("w-full justify-end gap-2"):
            ui.button("Add file").classes("bg-green")
            ui.button("Delete tasks/keys").classes("bg-red").style(
                "width: 200px !important;"
            )
