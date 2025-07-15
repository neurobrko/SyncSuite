from nicegui import ui


def cfg_tab():
    ui.label(
        "Configuration functionality will be implemented here.\n"
        "selecting config dir, config file, filemap file\n"
        "- editing ssh config"
    ).style("white-space: pre-wrap")
