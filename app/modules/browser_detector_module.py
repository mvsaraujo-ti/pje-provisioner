from __future__ import annotations

import os


CHROME_PATHS = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
]

EDGE_PATHS = [
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
]

FIREFOX_PATHS = [
    r"C:\Program Files\Mozilla Firefox\firefox.exe",
]


def _find_first(paths: list[str]) -> str | None:
    for path in paths:
        if os.path.exists(path):
            return path
    return None


def detect_browsers() -> dict:
    chrome_path = _find_first(CHROME_PATHS)
    edge_path = _find_first(EDGE_PATHS)
    firefox_path = _find_first(FIREFOX_PATHS)

    recommended = None
    if chrome_path:
        recommended = "chrome"
    elif edge_path:
        recommended = "edge"
    elif firefox_path:
        recommended = "firefox"

    return {
        "chrome": bool(chrome_path),
        "edge": bool(edge_path),
        "firefox": bool(firefox_path),
        "recommended": recommended,
        "chrome_path": chrome_path,
        "edge_path": edge_path,
        "firefox_path": firefox_path,
    }

