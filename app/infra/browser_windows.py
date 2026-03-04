from __future__ import annotations

import os
import shutil
import subprocess

from app.utils.logger import get_logger


PJE_URL = "https://pje.tjma.jus.br"

CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
EDGE_PATH = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
FIREFOX_PATH = r"C:\Program Files\Mozilla Firefox\firefox.exe"


def detect_browser() -> str | None:
    """
    Detecta navegador instalado em ordem de prioridade:
    Chrome -> Edge -> Firefox.
    """
    for path in (CHROME_PATH, EDGE_PATH, FIREFOX_PATH):
        if os.path.exists(path):
            return path
    return None


def close_chrome() -> None:
    """
    Fecha processos do Chrome se estiverem em execucao.
    """
    subprocess.run(
        ["taskkill", "/F", "/IM", "chrome.exe"],
        capture_output=True,
        text=True,
        check=False,
    )


def clear_chrome_cache() -> None:
    """
    Remove cache padrao do perfil Default do Chrome.
    """
    cache_path = os.path.join(
        os.environ.get("LOCALAPPDATA", ""),
        "Google",
        "Chrome",
        "User Data",
        "Default",
        "Cache",
    )
    if os.path.isdir(cache_path):
        shutil.rmtree(cache_path, ignore_errors=True)


def open_browser(url: str) -> None:
    """
    Abre o navegador detectado diretamente na URL informada.
    """
    logger = get_logger()
    browser_path = detect_browser()

    if not browser_path:
        raise RuntimeError("Nenhum navegador suportado foi encontrado.")

    logger.info(
        "browser_opening",
        extra={"event": "browser_opening", "browser_path": browser_path, "url": url},
    )
    subprocess.Popen([browser_path, url])

