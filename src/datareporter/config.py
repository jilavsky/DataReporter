"""Report configuration and settings persistence."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Optional

from datareporter.core.grouping import OutputMode, Scope

__all__ = ["ReportConfig", "load_settings", "save_settings", "SETTINGS_PATH"]

#: Where GUI settings are persisted between sessions.
SETTINGS_PATH = Path.home() / ".datareporter.json"

#: Formats a report can be produced in.
FORMATS = ("pdf", "md", "ascii")


@dataclass
class ReportConfig:
    """All knobs for one report-generation run."""

    scope: Scope = "sample"                  #: dataset | technique | sample | user
    mode: OutputMode = "source"              #: source | mirror | flat
    output_dir: Optional[Path] = None        #: required for mirror/flat modes
    formats: list[str] = field(default_factory=lambda: ["pdf"])
    per_graph: int = 1                       #: datasets overlaid per graph (1-10)
    pdf_grid: tuple[int, int] = (2, 3)       #: images per PDF page (rows, cols)
    pdf_summary: bool = True                 #: leading metadata/summary PDF page
    md_metadata: bool = True                 #: metadata bullets in Markdown
    workers: Optional[int] = None            #: parallel processes (None = auto)

    def validate(self) -> None:
        if self.scope not in ("dataset", "technique", "sample", "user"):
            raise ValueError(f"Unknown scope: {self.scope}")
        if self.mode not in ("source", "mirror", "flat"):
            raise ValueError(f"Unknown output mode: {self.mode}")
        if self.mode in ("mirror", "flat") and not self.output_dir:
            raise ValueError(f"Output mode '{self.mode}' requires output_dir")
        bad = [f for f in self.formats if f not in FORMATS]
        if bad:
            raise ValueError(f"Unknown format(s): {bad}; valid: {FORMATS}")
        if not self.formats:
            raise ValueError("At least one output format is required")
        if not 1 <= int(self.per_graph) <= 10:
            raise ValueError("per_graph must be between 1 and 10")


def load_settings(path: Path = SETTINGS_PATH) -> dict:
    """Load persisted GUI settings; returns {} when missing/corrupt."""
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def save_settings(settings: dict, path: Path = SETTINGS_PATH) -> None:
    """Persist GUI settings as JSON (best effort)."""
    try:
        Path(path).write_text(json.dumps(settings, indent=2, default=str),
                              encoding="utf-8")
    except OSError:
        pass
