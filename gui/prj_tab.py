from nicegui import ui

# TODO:
# - implement functionality of <ADD> and <REMOVE> buttons


def save_project_config(cfg, footer):
    cfg.update_config(
        cfg.cfg_dir, cfg.cfg_file, cfg.filemap, cfg.synced_filemap
    )
    footer.text = cfg.get_config_footer()
    ui.notify("Configuration saved!")


def add_path(cfg_section: str):
    pass


def del_path(cgf_section: str, path: int):
    if path == 0:
        ui.notification("Cannot remove default empty selection!")
    else:
        ui.notification(f"{cgf_section}: {path}")


def prj_tab(cfg, footer):
    # UI
    with ui.grid(columns=2).classes("w-full gap-2"):
        ui.label("Configuration directory:")
        with ui.row().classes("gap-2 justify-end"):
            ui.button("Add").on("click", lambda: add_path("cfg_dir"))
            ui.button("Remove").on(
                "click", lambda: del_path("cfg_dir", cfg.cfg_dir)
            )
        ui.select(cfg.config_dirs, value=cfg.cfg_dir).classes(
            "col-span-full"
        ).bind_value(cfg, "cfg_dir").on(
            "update:model-value", lambda: save_project_config(cfg, footer)
        )

        ui.label("Configuration file:")
        with ui.row().classes("gap-2 justify-end"):
            ui.button("Add").on("click", lambda: add_path("cfg_file"))
            ui.button("Remove").on(
                "click", lambda: del_path("cfg_file", cfg.cfg_file)
            )
        ui.select(cfg.config_files, value=cfg.cfg_file).classes(
            "col-span-full"
        ).bind_value(cfg, "cfg_file").on(
            "update:model-value", lambda: save_project_config(cfg, footer)
        )

        ui.label("File map:")
        with ui.row().classes("gap-2 justify-end"):
            ui.button("Add").on("click", lambda: add_path("filemap"))
            ui.button("Remove").on(
                "click", lambda: del_path("filemap", cfg.filemap)
            )
        ui.select(cfg.filemaps, value=cfg.filemap).classes(
            "col-span-full"
        ).bind_value(cfg, "filemap").on(
            "update:model-value", lambda: save_project_config(cfg, footer)
        )

        ui.label("Synced file map:")
        with ui.row().classes("gap-2 justify-end"):
            ui.button("Add").on("click", lambda: add_path("synced_filemap"))
            ui.button("Remove").on(
                "click", lambda: del_path("synced_filemap", cfg.synced_filemap)
            )
        ui.select(cfg.synced_filemaps, value=cfg.synced_filemap).classes(
            "col-span-full"
        ).bind_value(cfg, "synced_filemap").on(
            "update:model-value", lambda: save_project_config(cfg, footer)
        )
