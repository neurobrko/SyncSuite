from nicegui import app, ui
from pathlib import Path
from common import read_yaml, write_yaml
from gui.gui_common import path_ellipsis


# set global variables
tasks_values = {}
task_cboxes = {}
files_values = {}
files_cboxes = {}
cfg_selected_keys = []


def task_callback(task, value, file_map):
    tasks_values[task] = value
    for num in file_map[task]:
        files_cboxes[num].value = value


def file_callback(num, value):
    files_values[num] = value


def use_keys():
    selected_keys = [
        key for key, value in files_values.items() if value if value
    ]

    if selected_keys:
        ui.notify(
            f"WIP:: SELECTED KEYS: {','.join([str(i) for i in selected_keys])}"
        )
    else:
        ui.notify("WIP:: No keys were selected!")


async def choose_file():
    new_file = await app.native.main_window.create_file_dialog(
        allow_multiple=False
    )
    ui.notify(f"Selected file: {new_file}")


async def add_file():
    await choose_file()


def delete_keys(fmp, fmp_file, cfg, cfg_file, selected_tasks, selected_keys):
    global cfg_selected_keys

    # Remove selected keys from the filemap and config
    for key in selected_keys:
        files_cboxes[key].delete()
        if key in cfg_selected_keys:
            try:
                cfg["sync"]["file_keys"].remove(key)
            except ValueError:
                pass

    # Update global selected keys and write config if changed
    if set(cfg_selected_keys) != set(cfg.get("sync").get("file_keys", [])):
        cfg_selected_keys = [k for k in cfg.get("sync").get("file_keys", [])]
        write_yaml(cfg_file, cfg)

    # Remove selected tasks and their keys
    for task in selected_tasks:
        task_cboxes[task].delete()
        task_keys = fmp.get(task, {})
        for key in task_keys:
            files_values.pop(key, None)
        selected_keys = [key for key in selected_keys if key not in task_keys]
        fmp.pop(task, None)
        tasks_values.pop(task)

    # Remove selected keys from remaining tasks and files_values
    for key in selected_keys:
        for task in fmp:
            fmp[task].pop(key, None)
        files_values.pop(key)

    write_yaml(fmp_file, fmp)
    ui.notify("Successfully deleted.")
    # NOTE: example of multiline notification
    # ui.notify(
    #     "Keys and/or \ntasks deleted.",
    #     multi_line=True,
    #     classes="multi-line-notification",
    # )


def delete_dialog(fmp, fmp_file, cfg, cfg_file):
    selected_tasks = [task for task, value in tasks_values.items() if value]
    selected_keys = [key for key, value in files_values.items() if value]

    if not any([selected_tasks, selected_keys]):
        ui.notify("No keys or tasks selected!")
        return

    with ui.dialog() as confirm_del, ui.card():
        ui.label(
            "Are you sure you want to delete selected tasks/keys?"
        ).classes("font-semibold")
        with ui.row().classes("w-full justify-end gap-2"):
            ui.button("Cancel").on("click", confirm_del.close)
            ui.button(
                "Delete",
                on_click=lambda: (
                    delete_keys(
                        fmp,
                        fmp_file,
                        cfg,
                        cfg_file,
                        selected_tasks,
                        selected_keys,
                    ),
                    confirm_del.close(),
                ),
            ).classes("bg-red")
    confirm_del.open()


def fmp_tab(cfg):
    filemap_file = cfg.filemap_file
    file_map = read_yaml(filemap_file)
    config_file = cfg.config_file
    config = read_yaml(config_file)
    global cfg_selected_keys
    cfg_selected_keys = [k for k in config.get("sync").get("file_keys", [])]

    ui.label(path_ellipsis(filemap_file, depth=1)).classes(
        "text-lg font-semibold"
    )

    for task, files in file_map.items():
        tasks_values[task] = False
        with ui.checkbox(
            task,
            on_change=lambda e, task=task: task_callback(
                task, e.value, file_map
            ),
        ) as cbox:
            task_cboxes[task] = cbox
            cbox.classes("font-semibold pt-4").props("dense")
        for num, files in sorted(
            files.items(), key=lambda item: Path(item[1][0]).name
        ):
            num_value = num in cfg_selected_keys
            files_values[num] = num_value
            with ui.checkbox(
                f"[{num:>2}] {Path(files[0]).name}",
                value=num_value,
                on_change=lambda e, num=num: file_callback(num, e.value),
            ) as cbox:
                files_cboxes[num] = cbox
                cbox.classes("pl-6 pt-1").props("dense")
                with ui.tooltip().classes("w-full"):
                    ui.html(
                        f"<b>src:</b> {files[0]}<br><b>trg:</b> {files[1]}"
                    ).classes("text-sm")

    with ui.dialog() as add_file_dialog, ui.card().classes("w-full"):
        ui.label("WIP - not implemented yet - WIP").classes(
            "text-lg font-semibold"
        ).style("color: yellow;")
        ui.label("Add file to filemap").classes("text-lg font-semibold")
        ui.input("Local file:").classes("w-full")
        ui.button("Cancel").on("click", add_file_dialog.close)

    with ui.grid(columns=2).classes("w-full pt-4"):
        ui.button("Use keys").on("click", use_keys)
        with ui.row().classes("w-full justify-end gap-2"):
            ui.button("Add file").classes("bg-green").on(
                "click", add_file_dialog.open
            )
            ui.button("Delete tasks/keys").on(
                "click",
                lambda: delete_dialog(
                    file_map, filemap_file, config, config_file
                ),
            ).classes("bg-red").style("width: 200px !important;")
