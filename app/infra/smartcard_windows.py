from __future__ import annotations

import re
import subprocess

from app.utils.logger import get_logger


def _extract_field(output: str, field_name: str) -> str | None:
    pattern = rf"(?im)^\s*{re.escape(field_name)}\s*:\s*(.+?)\s*$"
    match = re.search(pattern, output or "")
    if not match:
        return None
    value = match.group(1).strip()
    return value or None


def _normalize_provider(provider: str | None) -> str | None:
    if not provider:
        return None
    text = provider.strip()
    lowered = text.lower()
    if "safenet" in lowered:
        return "SafeNet"
    if "safesign" in lowered:
        return "SafeSign"
    if "watchdata" in lowered:
        return "WatchData"
    if "feitian" in lowered:
        return "Feitian"
    if "gd" in lowered or "starsign" in lowered:
        return "GD StarSign"
    return text


def get_connected_smartcards() -> dict:
    """
    Consulta o subsistema SmartCard do Windows via `certutil -scinfo`.
    """
    logger = get_logger()
    logger.info("smartcard_scan_started", extra={"event": "smartcard_scan_started"})

    try:
        result = subprocess.run(
            ["certutil", "-scinfo"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="ignore",
            check=False,
        )
        output = f"{result.stdout or ''}\n{result.stderr or ''}"
        reader = _extract_field(output, "Reader")
        card = _extract_field(output, "Card")
        provider_raw = _extract_field(output, "Provider")
        provider = _normalize_provider(provider_raw)

        token_connected = bool(reader)
        payload = (
            {
                "token_connected": True,
                "reader": reader,
                "card": card,
                "provider": provider,
            }
            if token_connected
            else {"token_connected": False}
        )
    except Exception as exc:
        payload = {"token_connected": False, "error": str(exc)}

    logger.info(
        "smartcard_scan_finished",
        extra={
            "event": "smartcard_scan_finished",
            "token_connected": bool(payload.get("token_connected")),
        },
    )
    return payload

