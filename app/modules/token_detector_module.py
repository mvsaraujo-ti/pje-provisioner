from __future__ import annotations

from app.infra.token_windows import (
    detect_installed_token_drivers,
    detect_smartcard_readers,
    detect_usb_devices,
    get_driver_version,
)


VID_DRIVER_MAP = {
    "0529": "SafeNet Authentication Client",
    "096E": "Feitian driver",
    "2CE3": "Watchdata driver",
    "0A89": "SafeSign",
}


def _detect_vendor(device: dict) -> str | None:
    text = f"{device.get('manufacturer', '')} {device.get('name', '')}".lower()
    if "safenet" in text or "aladdin" in text or "etoken" in text:
        return "SafeNet"
    if "safesign" in text:
        return "SafeSign"
    if "gd" in text or "starsign" in text:
        return "GD StarSign"
    if "feitian" in text:
        return "Feitian"
    if "watchdata" in text:
        return "WatchData"
    manufacturer = str(device.get("manufacturer") or "").strip()
    return manufacturer or None


def _detect_model(device: dict) -> str | None:
    name = str(device.get("name") or "").strip()
    return name or None


def detect_token_hardware() -> dict:
    """
    Detecta token USB e consolida informacoes de driver instalado.
    """
    usb_devices = detect_usb_devices()
    smartcard_readers = detect_smartcard_readers()
    drivers = detect_installed_token_drivers()

    devices = usb_devices if usb_devices else smartcard_readers
    if not devices:
        return {"token_detected": False}

    first = devices[0]
    usb_vid = first.get("usb_vid")
    usb_pid = first.get("usb_pid")
    vendor = _detect_vendor(first)
    model = _detect_model(first)

    installed_driver_name = None
    if drivers:
        installed_driver_name = str(drivers[0].get("display_name") or "").strip() or None

    return {
        "token_detected": True,
        "vendor": vendor,
        "model": model,
        "usb_vid": usb_vid,
        "usb_pid": usb_pid,
        "driver_required": VID_DRIVER_MAP.get(str(usb_vid or "").upper()),
        "driver_installed": installed_driver_name,
        "driver_version": get_driver_version(drivers),
    }


def detect_token() -> dict:
    """
    Compatibilidade com chamadas antigas.
    """
    data = detect_token_hardware()
    if not data.get("token_detected"):
        return {
            "token_detected": False,
            "token_vendor": None,
            "token_model": None,
            "driver_installed": False,
            "driver_version": None,
        }

    return {
        "token_detected": True,
        "token_vendor": data.get("vendor"),
        "token_model": data.get("model"),
        "driver_installed": bool(data.get("driver_installed")),
        "driver_version": data.get("driver_version"),
    }
