from __future__ import annotations

import os
import subprocess

from app.infra import browser_windows
from app.utils.logger import get_logger

CHROME_CANDIDATES = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
]


def _detect_chrome_path() -> str | None:
    for path in CHROME_CANDIDATES:
        if os.path.exists(path):
            return path
    return None


def run_browser_fix() -> dict:
    """
    Executa correcao de navegador:
    1) detecta navegador
    2) fecha chrome
    3) limpa cache do chrome
    4) abre navegador no PJe
    """
    logger = get_logger()

    try:
        browser_path = _detect_chrome_path()
        if not browser_path:
            logger.error(
                "browser_fix_failed_no_browser",
                extra={"event": "browser_fix_failed_no_browser"},
            )
            return {
                "status": "error",
                "message": "Chrome não encontrado no sistema.",
            }

        logger.info(
            "browser_detected",
            extra={"event": "browser_detected", "browser_path": browser_path},
        )

        browser_windows.close_chrome()
        browser_windows.clear_chrome_cache()
        subprocess.Popen([browser_path, browser_windows.PJE_URL])

        return {
            "status": "ok",
            "message": "Chrome aberto com sucesso na página do PJe.",
            "browser_path": browser_path,
            "url": browser_windows.PJE_URL,
        }
    except Exception as exc:
        logger.error(
            "browser_fix_failed",
            extra={"event": "browser_fix_failed", "error": str(exc)},
        )
        return {
            "status": "error",
            "message": "Falha ao corrigir navegador",
        }
