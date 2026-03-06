from __future__ import annotations

import subprocess
from pathlib import Path

from app.utils.logger import get_logger
from app.utils.paths import resource_path


def _driver_path(filename: str) -> str:
    return str(resource_path("infra", "drivers", filename))


SAFE_SIGN_INSTALLER = _driver_path("safesign.exe")
SAFE_NET_INSTALLER = _driver_path("safenet.exe")


def _detect_target_driver(token_details: dict | None) -> str | None:
    details = token_details or {}
    text = " ".join(
        str(details.get(k) or "")
        for k in ("vendor", "provider", "hardware_label", "model", "driver_required")
    ).lower()
    if "gd" in text or "safesign" in text:
        return "safesign"
    if "safenet" in text or "etoken" in text or "aladdin" in text or "gemalto" in text:
        return "safenet"
    return None


def install_missing_token_driver(token_details: dict | None = None) -> dict:
    """
    Instala automaticamente driver do token quando ausente.
    """
    logger = get_logger()
    logger.info("driver_install_started", extra={"event": "driver_install_started"})

    target = _detect_target_driver(token_details)
    if target == "safesign":
        installer = SAFE_SIGN_INSTALLER
        cmd = [installer, "/s", '/v"/qn"']
        driver_name = "SafeSign"
    elif target == "safenet":
        installer = SAFE_NET_INSTALLER
        cmd = [installer, "/silent"]
        driver_name = "SafeNet Authentication Client"
    else:
        logger.warning(
            "driver_install_finished",
            extra={
                "event": "driver_install_finished",
                "success": False,
                "error": "driver target not identified",
            },
        )
        return {"status": "error", "message": "Nao foi possivel identificar driver do token."}

    installer_path = Path(installer)
    if not installer_path.exists():
        logger.error(
            "driver_install_finished",
            extra={
                "event": "driver_install_finished",
                "success": False,
                "error": f"installer not found: {installer}",
            },
        )
        return {"status": "error", "message": f"Instalador nao encontrado: {installer}"}

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        ok = result.returncode == 0
        logger.info(
            "driver_install_finished",
            extra={
                "event": "driver_install_finished",
                "success": ok,
                "driver": driver_name,
                "return_code": result.returncode,
            },
        )
        if ok:
            return {"status": "ok", "message": f"{driver_name} instalado com sucesso."}
        return {
            "status": "error",
            "message": f"Falha na instalacao do driver ({driver_name}). Codigo {result.returncode}",
        }
    except Exception as exc:
        logger.error(
            "driver_install_finished",
            extra={"event": "driver_install_finished", "success": False, "error": str(exc)},
        )
        return {"status": "error", "message": f"Falha na instalacao do driver: {exc}"}
