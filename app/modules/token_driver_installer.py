from __future__ import annotations

import os
import subprocess

from app.utils.logger import get_logger


SAFE_SIGN_INSTALLER = r"c:\Workspace\pje-provisioner\infra\drivers\safesign.exe"
SAFE_NET_INSTALLER = r"c:\Workspace\pje-provisioner\infra\drivers\safenet.exe"


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
        return {"status": "error", "message": "Não foi possível identificar driver do token."}

    if not os.path.exists(installer):
        logger.error(
            "driver_install_finished",
            extra={
                "event": "driver_install_finished",
                "success": False,
                "error": f"installer not found: {installer}",
            },
        )
        return {"status": "error", "message": f"Instalador não encontrado: {installer}"}

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
            "message": f"Falha na instalação do driver ({driver_name}). Código {result.returncode}",
        }
    except Exception as exc:
        logger.error(
            "driver_install_finished",
            extra={"event": "driver_install_finished", "success": False, "error": str(exc)},
        )
        return {"status": "error", "message": f"Falha na instalação do driver: {exc}"}

