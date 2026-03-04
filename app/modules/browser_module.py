from __future__ import annotations

from app.infra import browser_windows
from app.utils.logger import get_logger


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
        browser_path = browser_windows.detect_browser()
        if not browser_path:
            logger.error(
                "browser_fix_failed_no_browser",
                extra={"event": "browser_fix_failed_no_browser"},
            )
            return {
                "status": "error",
                "message": "Nenhum navegador suportado foi encontrado.",
            }

        logger.info(
            "browser_detected",
            extra={"event": "browser_detected", "browser_path": browser_path},
        )

        browser_windows.close_chrome()
        browser_windows.clear_chrome_cache()
        browser_windows.open_browser(browser_windows.PJE_URL)

        return {
            "status": "ok",
            "message": "Correcao de navegador executada com sucesso.",
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
