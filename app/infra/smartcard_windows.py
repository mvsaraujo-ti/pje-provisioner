from __future__ import annotations

import json
import re
import subprocess

from app.utils.logger import get_logger


def _extract_vid_pid(pnp_id: str) -> tuple[str | None, str | None]:
    vid_match = re.search(r"VID_([0-9A-Fa-f]{4})", pnp_id or "")
    pid_match = re.search(r"PID_([0-9A-Fa-f]{4})", pnp_id or "")
    vid = vid_match.group(1).upper() if vid_match else None
    pid = pid_match.group(1).upper() if pid_match else None
    return vid, pid


def _normalize_provider(text: str | None) -> str | None:
    if not text:
        return None
    lowered = text.lower()
    if any(k in lowered for k in ("safenet", "aladdin", "gemalto", "etoken")):
        return "SafeNet"
    if "watchdata" in lowered:
        return "WatchData"
    if "feitian" in lowered:
        return "Feitian"
    if "gd" in lowered or "starsign" in lowered or "safesign" in lowered:
        return "GD"
    return text.strip()


def _is_likely_real_token_card(card: dict) -> bool:
    name = str(card.get("name") or "").lower()
    manufacturer = str(card.get("manufacturer") or "").lower()
    combined = f"{name} {manufacturer}"

    generic_markers = [
        "microsoft",
        "driver de filtro",
        "smart card filter",
        "cartao inteligente",
        "cartão inteligente",
    ]
    if any(marker in combined for marker in generic_markers):
        return False

    vendor_markers = [
        "safenet",
        "aladdin",
        "gemalto",
        "etoken",
        "watchdata",
        "feitian",
        "gd",
    ]
    return any(marker in combined for marker in vendor_markers)


def _json_list(payload: str) -> list[dict]:
    if not payload:
        return []
    try:
        parsed = json.loads(payload)
    except json.JSONDecodeError:
        return []
    if isinstance(parsed, dict):
        parsed = [parsed]
    if not isinstance(parsed, list):
        return []
    return [item for item in parsed if isinstance(item, dict)]


def _collect_smartcard_pnp() -> tuple[list[dict], list[dict]]:
    cmd = [
        "powershell",
        "-NoProfile",
        "-Command",
        (
            "$all = Get-PnpDevice -PresentOnly | "
            "Where-Object { $_.FriendlyName -match '(?i)smartcard|token|safenet|aladdin|gemalto|watchdata|feitian|gd|etoken' "
            "-or $_.Class -match '(?i)smartcard|smartcardreader' }; "
            "$all | Select-Object FriendlyName,Class,Status,InstanceId,Manufacturer | ConvertTo-Json -Compress"
        ),
    ]
    res = subprocess.run(cmd, capture_output=True, text=True, check=False)
    devices = _json_list((res.stdout or "").strip()) if res.returncode == 0 else []

    readers: list[dict] = []
    cards: list[dict] = []
    for item in devices:
        name = str(item.get("FriendlyName") or "").strip()
        cls = str(item.get("Class") or "").strip().lower()
        status = str(item.get("Status") or "").strip().lower()
        instance_id = str(item.get("InstanceId") or "").strip()
        manufacturer = str(item.get("Manufacturer") or "").strip()
        vid, pid = _extract_vid_pid(instance_id)
        payload = {
            "name": name,
            "class": cls,
            "status": status,
            "instance_id": instance_id,
            "manufacturer": manufacturer,
            "usb_vid": vid,
            "usb_pid": pid,
        }
        if "reader" in cls:
            readers.append(payload)
        else:
            cards.append(payload)
    return readers, cards


def get_connected_smartcards() -> dict:
    """
    Detecta token conectado sem abrir popup/PIN.
    Usa apenas enumeração PnP/SmartCard do Windows.
    """
    logger = get_logger()
    logger.info("smartcard_scan_started", extra={"event": "smartcard_scan_started"})

    readers, cards = _collect_smartcard_pnp()

    connected_card = None
    for card in cards:
        if card.get("status") == "ok" and _is_likely_real_token_card(card):
            connected_card = card
            break

    token_connected = connected_card is not None
    if not token_connected:
        payload = {
            "token_connected": False,
            "readers": readers,
        }
    else:
        provider_text = (
            connected_card.get("manufacturer")
            or connected_card.get("name")
            or ""
        )
        payload = {
            "token_connected": True,
            "reader": connected_card.get("name"),
            "card": "ICP-Brasil A3",
            "provider": _normalize_provider(provider_text),
            "usb_vid": connected_card.get("usb_vid"),
            "usb_pid": connected_card.get("usb_pid"),
            "readers": readers,
        }

    logger.info(
        "smartcard_scan_finished",
        extra={
            "event": "smartcard_scan_finished",
            "token_connected": bool(payload.get("token_connected")),
            "reader_count": len(readers),
        },
    )
    return payload
