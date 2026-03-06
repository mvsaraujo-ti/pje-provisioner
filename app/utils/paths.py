from __future__ import annotations

import os
import sys
from pathlib import Path

if getattr(sys, "frozen", False):
    BASE_PATH = Path(getattr(sys, "_MEIPASS"))
else:
    BASE_PATH = Path(__file__).resolve().parents[2]


def resource_path(*parts: str) -> Path:
    return BASE_PATH.joinpath(*parts)


def resource_path_str(*parts: str) -> str:
    return os.fspath(resource_path(*parts))
