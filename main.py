#!/usr/bin/env /home/marpauli/.cache/pypoetry/virtualenvs/syncsuite-HX8knUdy-py3.12/bin/python
import multiprocessing

from nicegui import ui
from pathlib import Path
from gui.gui_common import CurrentConfig
from common import read_yaml

from gui.cfg_tab import cfg_tab
from gui.fmp_tab import fmp_tab
from gui.log_tab import log_tab
from gui.prj_tab import prj_tab
from gui.r2r_tab import r2r_tab

multiprocessing.set_start_method("spawn", force=True)

DEBUG = False
if DEBUG:
    try:
        import debugpy
    except ModuleNotFoundError:
        print("debugpy module not found!")
    else:
        debugpy.listen(5678)
        print("Remote debugging enabled. Waiting for client connection...")
        debugpy.wait_for_client()

gui_cfg_file = Path("gui/gui_cfg.yaml")
project_config = read_yaml(gui_cfg_file)
current_config = CurrentConfig(project_config)

# UI
ui.add_head_html("""
<style>
button {
    width: 120px !important;
}
</style>
""")
ui.html("<style>.multi-line-notification { white-space: pre-line; }</style>")
ui.dark_mode(True)

with ui.tabs().classes("w-full") as tabs:
    r2r = ui.tab("R2R", label="Rsync to Remote")
    fmp = ui.tab("FMP", label="Filemap")
    cfg = ui.tab("CFG", label="Config")
    log = ui.tab("LOG", label="Log")
    prj = ui.tab("PRJ", label="Project")

with ui.footer().classes():
    footer = ui.label(current_config.config_footer)

with ui.tab_panels(tabs, value=fmp).classes("w-full") as tab_panels:
    with ui.tab_panel(r2r) as r2r_panel:
        r2r_tab()
    with ui.tab_panel(fmp) as fmp_panel:
        fmp_panel.classes("gap-0")
        fmp_tab(current_config, fmp_panel)
    with ui.tab_panel(cfg) as cfg_panel:
        cfg_tab()
    with ui.tab_panel(log) as log_panel:
        log_tab()
    with ui.tab_panel(prj) as prj_panel:
        prj_tab(current_config, footer)


def reload_tab(tab_name):
    if tab_name == "R2R":
        r2r_panel.clear()
        with r2r_panel:
            r2r_tab()
    elif tab_name == "FMP":
        fmp_panel.clear()
        with fmp_panel:
            fmp_tab(current_config, fmp_panel)
    elif tab_name == "CFG":
        cfg_panel.clear()
        with cfg_panel:
            cfg_tab()
    elif tab_name == "LOG":
        log_panel.clear()
        with log_panel:
            log_tab()
    elif tab_name == "PRJ":
        prj_panel.clear()
        with prj_panel:
            prj_tab(current_config, footer)


tabs.on("update:model-value", lambda e: reload_tab(e.args))

ui.run(native=True, window_size=(960, 1200), title="Sync Suite")
