#!/usr/bin/env python3
from pathlib import Path
from common import write_yaml


def path_ellipsis(path: str | Path, ellipsis="...", path_sep="/", depth=2):
    path = Path(path)
    if path.is_dir():
        return ellipsis + path_sep + path_sep.join(path.parts[-depth:])
    if path.is_file():
        return ellipsis + path_sep + path_sep.join(path.parts[-depth - 1 :])
    return "Invalid path!"


class CurrentConfig:
    def __init__(self, project_config):
        self.project_config = project_config
        self.config_dirs = project_config.get("cfg_dir", [])
        self.config_files = project_config.get("cfg_file", [])
        self.filemaps = project_config.get("filemap", [])
        self.synced_filemaps = project_config.get("synced_filemap", [])
        self.current_project = project_config.get(
            "current",
            {"cfg_dir": 0, "cfg_file": 0, "filemap": 0, "synced_filemap": 0},
        )
        self._cfg_dir = self.current_project["cfg_dir"]
        self._cfg_file = self.current_project["cfg_file"]
        self._filemap = self.current_project["filemap"]
        self._synced_filemap = self.current_project["synced_filemap"]

        self.config_footer = self.get_config_footer()

    @property
    def cfg_dir(self):
        return self._cfg_dir

    @cfg_dir.setter
    def cfg_dir(self, value):
        self._cfg_dir = value

    @property
    def cfg_file(self):
        return self._cfg_file

    @cfg_file.setter
    def cfg_file(self, value):
        self._cfg_file = value

    @property
    def filemap(self):
        return self._filemap

    @filemap.setter
    def filemap(self, value):
        self._filemap = value

    @property
    def synced_filemap(self):
        return self._synced_filemap

    @synced_filemap.setter
    def synced_filemap(self, value):
        self._synced_filemap = value

    def as_dict(self):
        return {
            "cfg_dir": self.cfg_dir,
            "cfg_file": self.cfg_file,
            "filemap": self.filemap,
            "synced_filemap": self.synced_filemap,
        }

    @property
    def is_full_override(self):
        return all([self.cfg_file, self.filemap, self.synced_filemap])

    @property
    def filemap_file(self) -> str | Path | None:
        if not self.cfg_dir and not self.filemap:
            return
        elif self.filemap:
            return self.filemaps[self.filemap]
        return Path(self.config_dirs[self.cfg_dir]) / "file_map.yaml"

    @property
    def config_file(self) -> str | Path | None:
        if not self.cfg_dir and not self.cfg_file:
            return
        elif self.cfg_file:
            return self.config_files[self.cfg_file]
        return Path(self.config_dirs[self.cfg_dir]) / "sync_conf.yaml"

    def update_config(self, cfg_d, cfg_f, fmp, s_fmp):
        self.cfg_dir = cfg_d
        self.cfg_file = cfg_f
        self.filemap = fmp
        self.synced_filemap = s_fmp

        self.project_config["current"]["cfg_dir"] = cfg_d
        self.project_config["current"]["cfg_file"] = cfg_f
        self.project_config["current"]["filemap"] = fmp
        self.project_config["current"]["synced_filemap"] = s_fmp

        write_yaml("gui/gui_cfg.yaml", self.project_config)

        self.config_footer = self.get_config_footer()

    def get_config_footer(self):
        if not any(self.current_project.values()):
            return "No project selected!"
        if self.is_full_override:
            return (
                f"CF: {path_ellipsis(self.config_files[self.cfg_file])} ",
                f": : FM: {path_ellipsis(self.filemaps[self.filemap])} ",
                f": : SF: {
                    path_ellipsis(self.synced_filemaps[self.synced_filemap])
                }",
            )
        cc_paths = f"CD: {path_ellipsis(self.config_dirs[self.cfg_dir])}"
        if self.cfg_file:
            cc_paths += (
                f" : : CF: {path_ellipsis(self.config_files[self.cfg_file])}"
            )
        if self.filemap:
            cc_paths += (
                f" : : FM: {path_ellipsis(self.filemaps[self.filemap])}"
            )
        if self.synced_filemap:
            cc_paths += f" : : SF: {
                path_ellipsis(self.synced_filemaps[self.synced_filemap])
            }"
        return cc_paths
