"""Settings persistence for DataReporter."""

from __future__ import annotations

import json
from pathlib import Path


_SETTINGS_DIR = Path.home() / ".datareporter"
_SETTINGS_FILE = _SETTINGS_DIR / "settings.json"


_DEFAULTS = {
    "last_input_dir": "",
    "last_output_dir": "",
    "scope": "sample",
    "formats": ["pdf", "obsidian", "csv"],
    "pdf_grid": "2x3",
    "pdf_metadata_summary": True,
    "obsidian_attachments": True,
    "obsidian_md_per_technique": False,
    "csv_delimiter": ",",
    # Output behavior
    "mirror": False,
    "add_to_source": False,
    # Multi-dataset graph setting
    "datasets_per_graph": 1,
}


def load_settings() -> dict:
    _SETTINGS_DIR.mkdir(parents=True, exist_ok=True)
    if _SETTINGS_FILE.exists():
        try:
            with _SETTINGS_FILE.open("r", encoding="utf-8") as f:
                data = json.load(f)
            return {**_DEFAULTS, **data}
        except Exception:
            return dict(_DEFAULTS)
    return dict(_DEFAULTS)


def save_settings(data: dict) -> None:
    _SETTINGS_DIR.mkdir(parents=True, exist_ok=True)
    with _SETTINGS_FILE.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
