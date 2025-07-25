from nicegui import app, ui
from pathlib import Path
from common import (
    get_remote_files,
    read_yaml,
    update_file_map,
    write_yaml,
)
from gui.gui_common import path_ellipsis

# TODO: switch automatically to R2R tab after hitting use keys button
#        NOTE: After implementing R2R tab!
#
# TODO: when deleting task, there should be either separate tab,
#       or the tab should be "switched" to delete mode to prevent accidental
#       deletion of selected file keys from config_file.
#        NOTE: Temporary solution: Use <ALL>, <NONE>, <RESET> buttons

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


def use_keys(config, config_file):
    selected_keys = [
        key for key, value in files_values.items() if value if value
    ]
    config["sync"]["file_keys"] = selected_keys
    write_yaml(config_file, config)
    ui.notify("Keys updated.")


async def choose_file(local_root_dir=None):
    new_file = await app.native.main_window.create_file_dialog(
        allow_multiple=False, directory=local_root_dir
    )
    new_file = Path(new_file[0]).relative_to(local_root_dir)
    return new_file.as_posix()


async def get_local_file(local_file, config):
    local_file.value = await choose_file(config["rsync"]["local_root_dir"])
    local_file.update()


def _set_remote_file(remote_file, value):
    remote_file.value = value
    remote_file.update()


def find_remote_file(
    remote_file, local_file, synced_file, config, multi_result
):
    multi_result.set_visibility(False)
    if not local_file.value:
        ui.notify("Please select a local file first!")
        return
    if synced_file:
        _set_remote_file(remote_file, synced_file)
        ui.notify("Remote file found in synced filemap.")
        return
    result = get_remote_files(
        Path(local_file.value),
        config["rsync"]["port"],
        config["rsync"]["username"],
        config["rsync"]["host"],
        config["script"]["default_browse_dir"],
    )
    if not result:
        ui.notify("Nothing found!")
        return
    if len(result) > 1:
        multi_result.clear()
        multi_result.set_visibility(True)
        with multi_result:
            ui.label("Multiple remote files found via ssh:").classes(
                "text-md font-semibold"
            )
            with ui.list().props("dense"):
                for item in result:
                    ui.item(
                        Path(item)
                        .relative_to(
                            Path(config["script"]["default_browse_dir"])
                        )
                        .as_posix(),
                        on_click=lambda item=item: (
                            _set_remote_file(remote_file, item),
                            multi_result.set_visibility(False),
                        ),
                    )
        return
    _set_remote_file(remote_file, result[0])
    ui.notify("Remote file found via ssh.")


def _reload_panel(cfg, panel):
    panel.clear()
    with panel:
        fmp_tab(cfg, panel)


def add_file(
    local_file,
    remote_file,
    file_map,
    filemap_file,
    to_task,
    new_task,
    cfg,
    panel,
    dialog,
):
    if not local_file.value:
        ui.notify("Please select a local file first!")
        return
    if not remote_file.value:
        ui.notify("No remote file specified!")
        return
    use_task = new_task if new_task else to_task
    update_file_map(
        use_task, local_file.value, remote_file.value, file_map, filemap_file
    )
    _reload_panel(cfg, panel)
    dialog.close()
    ui.notify("File added to filemap.")


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
    empty_tasks = []
    for key in selected_keys:
        for task in fmp:
            fmp[task].pop(key, None)
            if len(fmp[task]) == 0:
                empty_tasks.append(task)
        files_values.pop(key)
    # if task is emty after key deletion, remove task
    for task in empty_tasks:
        task_cboxes[task].delete()
        fmp.pop(task)
        tasks_values.pop(task)

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


def _selection_toggle(value):
    for task in task_cboxes.values():
        task.value = value
    for file in files_cboxes.values():
        file.value = value


def fmp_tab(cfg, panel=None):
    filemap_file = cfg.filemap_file
    file_map = read_yaml(filemap_file)
    tasks = [k for k in file_map.keys()]
    config_file = cfg.config_file
    config = read_yaml(config_file)
    synced_filemap = read_yaml(cfg.synced_filemap_file)
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
                with ui.tooltip().classes("w-10/12").props("delay=650"):
                    ui.html(
                        f"<b>src:</b> {files[0]}<br><b>trg:</b> {files[1]}"
                    ).classes("text-sm")

    with ui.dialog() as add_file_dialog, ui.card().classes("w-full"):
        ui.label("WIP - not implemented yet - WIP").classes(
            "text-lg font-semibold"
        ).style("color: yellow;")
        ui.label("Add file to filemap").classes("text-lg font-semibold")
        local_file = ui.input("Local file:").classes("w-full")
        with ui.row().classes("w-full justify-end"):
            ui.button("Choose Local File").on(
                "click",
                lambda local_file=local_file, config=config: get_local_file(
                    local_file, config
                ),
            ).style("width: 200px !important;")
        remote_file = ui.input("Remote file").classes("w-full")
        with ui.column().classes("w-full") as multi_result:
            multi_result.set_visibility(False)
        with ui.row().classes("w-full justify-end"):
            ui.button("Find Remote File").on(
                "click",
                lambda remote_file=remote_file,
                local_file=local_file,
                synced_filemap=synced_filemap,
                multi_result=multi_result: find_remote_file(
                    remote_file,
                    local_file,
                    synced_filemap.get(local_file.value),
                    config,
                    multi_result,
                ),
            ).classes("bg-orange").style("width: 200px !important;")
        with ui.grid(columns=2).classes("w-full gap-4"):
            ui.label("Put in task:").classes("text-md font-semibold")
            ui.label("Create new task:").classes("text-md font-semibold")
            to_task = ui.select(tasks, value=tasks[-1]).classes("w-full")
            new_task = ui.input()
        with ui.row().classes("w-full justify-end gap-2"):
            ui.button("Add").on(
                "click",
                lambda: add_file(
                    local_file,
                    remote_file,
                    file_map,
                    filemap_file,
                    to_task.value,
                    new_task.value,
                    cfg,
                    panel,
                    add_file_dialog,
                ),
            ).classes("bg-green")
            ui.button("Cancel").on(
                "click",
                lambda: (add_file_dialog.close, _reload_panel(cfg, panel)),
            )

    with ui.grid(columns=2).classes("w-full pt-4"):
        with ui.row().classes("w-full gap-2"):
            ui.button("Use keys").on(
                "click", lambda: use_keys(config, config_file)
            )
            ui.button("All").on(
                "click", lambda: _selection_toggle(True)
            ).classes("cbox-sel")
            ui.button("None").on(
                "click", lambda: _selection_toggle(False)
            ).classes("cbox-sel")
            ui.button("Reset").on(
                "click", lambda: _reload_panel(cfg, panel)
            ).classes("cbox-sel")
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
