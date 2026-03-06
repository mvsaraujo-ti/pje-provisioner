from __future__ import annotations

import json
import re
import subprocess

from app.utils.logger import get_logger

NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)


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
    if "safesign" in lowered:
        return "SafeSign"
    if "gd" in lowered or "starsign" in lowered:
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

    # Qualquer smartcard "ok" que nao seja filtro/generica deve ser tratada como token.
    return bool(name.strip())


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
    res = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        check=False,
        creationflags=NO_WINDOW,
    )
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


def _collect_certutil_scinfo() -> dict:
    cmd = ["certutil", "-scinfo"]
    res = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        check=False,
        creationflags=NO_WINDOW,
    )
    text = f"{res.stdout or ''}\n{res.stderr or ''}"
    lowered = text.lower()

    # Indicadores comuns quando nao existe cartao/token no leitor.
    no_card_markers = [
        "no card",
        "nenhum cart",
        "cannot find a smart card",
    ]
    has_no_card = any(marker in lowered for marker in no_card_markers)

    reader = None
    card = None
    provider = None
    reader_match = re.search(r"(?im)^\s*Reader(?:\[\d+\])?\s*:\s*(.+)$", text)
    if reader_match:
        reader = reader_match.group(1).strip()
    card_match = re.search(r"(?im)^\s*Card(?:\[\d+\])?\s*:\s*(.+)$", text)
    if card_match:
        card = card_match.group(1).strip()
    provider_match = re.search(r"(?im)^\s*Provider(?:\[\d+\])?\s*:\s*(.+)$", text)
    if provider_match:
        provider = provider_match.group(1).strip()

    token_connected = bool(card and not has_no_card)
    return {
        "token_connected": token_connected,
        "reader": reader,
        "card": card,
        "provider": _normalize_provider(provider),
    }


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

    certutil_info = _collect_certutil_scinfo()
    token_connected = connected_card is not None or bool(certutil_info.get("token_connected"))
    if not token_connected:
        payload = {
            "token_connected": False,
            "readers": readers,
        }
    else:
        provider_text = (
            (connected_card or {}).get("manufacturer")
            or (connected_card or {}).get("name")
            or certutil_info.get("provider")
            or certutil_info.get("card")
            or ""
        )
        payload = {
            "token_connected": True,
            "reader": (connected_card or {}).get("name") or certutil_info.get("reader"),
            "card": (connected_card or {}).get("name") or certutil_info.get("card") or "ICP-Brasil A3",
            "provider": _normalize_provider(provider_text),
            "usb_vid": (connected_card or {}).get("usb_vid"),
            "usb_pid": (connected_card or {}).get("usb_pid"),
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
