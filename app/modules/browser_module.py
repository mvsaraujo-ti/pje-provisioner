from __future__ import annotations

import os
import subprocess

from app.infra import browser_windows
from app.utils.logger import get_logger

CHROME_CANDIDATES = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
]
PJE_URL = "https://pje.tjma.jus.br"


def _detect_chrome_path() -> str | None:
    for path in CHROME_CANDIDATES:
        if os.path.exists(path):
            return path
    return None


def open_chrome(url: str = PJE_URL) -> dict:
    logger = get_logger()
    chrome_path = _detect_chrome_path()
    if not chrome_path:
        logger.error("chrome_not_found", extra={"event": "chrome_not_found"})
        return {"status": "error", "message": "Chrome nao encontrado."}

    try:
        subprocess.Popen([chrome_path, url])
        logger.info(
            "chrome_opened",
            extra={"event": "chrome_opened", "browser_path": chrome_path, "url": url},
        )
        return {
            "status": "ok",
            "message": "Chrome aberto com sucesso.",
            "browser_path": chrome_path,
            "url": url,
        }
    except Exception as exc:
        logger.error(
            "chrome_open_failed",
            extra={"event": "chrome_open_failed", "error": str(exc)},
        )
        return {"status": "error", "message": f"Falha ao abrir Chrome: {exc}"}


def run_browser_fix(launch_browser: bool = True) -> dict:
    logger = get_logger()

    try:
        browser_path = _detect_chrome_path()
        if not browser_path:
            logger.error(
                "browser_fix_failed_no_browser",
                extra={"event": "browser_fix_failed_no_browser"},
            )
            return {"status": "error", "message": "Chrome nao encontrado no sistema."}

        logger.info(
            "browser_detected",
            extra={"event": "browser_detected", "browser_path": browser_path},
        )

        browser_windows.close_chrome()
        browser_windows.clear_chrome_cache()

        if launch_browser:
            open_result = open_chrome(PJE_URL)
            if open_result.get("status") != "ok":
                return open_result

        return {
            "status": "ok",
            "message": "Correcoes de navegador aplicadas com sucesso.",
            "browser_path": browser_path,
            "url": PJE_URL,
        }
    except Exception as exc:
        logger.error(
            "browser_fix_failed",
            extra={"event": "browser_fix_failed", "error": str(exc)},
        )
        return {"status": "error", "message": "Falha ao corrigir navegador"}
