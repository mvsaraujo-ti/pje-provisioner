from __future__ import annotations

from app.infra.token_windows import (
    detect_installed_token_drivers,
    detect_smartcard_readers,
    detect_usb_devices,
    get_driver_version,
)
from app.infra.smartcard_windows import get_connected_smartcards


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


def _classify_from_smartcard_reader(readers: list[dict]) -> tuple[str | None, str | None]:
    for reader in readers:
        text = f"{reader.get('name', '')} {reader.get('manufacturer', '')}".lower()
        if "safenet" in text or "aladdin" in text or "gemalto" in text:
            return "SafeNet", "SafeNet eToken"
        if "watchdata" in text:
            return "Watchdata", "Watchdata Token"
        if "feitian" in text:
            return "Feitian", "Feitian ePass"
    return None, None


def _classify_driver_name(drivers: list[dict]) -> str | None:
    if not drivers:
        return None

    names = [
        str(item.get("display_name") or "").strip()
        for item in drivers
        if str(item.get("display_name") or "").strip()
    ]
    if not names:
        return None

    def is_safesign(name: str) -> bool:
        lower = name.lower()
        return (
            "safesign" in lower
            or "a.e.t. europe" in lower
        )

    def is_safenet(name: str) -> bool:
        lower = name.lower()
        return (
            "safenet authentication client" in lower
            or "safenet etoken" in lower
            or "safenet" in lower
            or "etoken" in lower
        )

    for name in names:
        if is_safesign(name):
            return name
    for name in names:
        if is_safenet(name):
            return name
    return names[0]


def detect_token_hardware() -> dict:
    """
    Detecta token USB e consolida informacoes de driver instalado.
    """
    usb_devices = detect_usb_devices()
    smartcard_readers = detect_smartcard_readers()
    smartcard_info = get_connected_smartcards()
    drivers = detect_installed_token_drivers()

    token_connected = bool(smartcard_info.get("token_connected"))
    if not token_connected and not drivers and not smartcard_readers and not usb_devices:
        return {"token_detected": False}

    first = usb_devices[0] if usb_devices else (smartcard_readers[0] if smartcard_readers else {})
    usb_vid = first.get("usb_vid")
    usb_pid = first.get("usb_pid")
    vendor = _detect_vendor(first)
    model = _detect_model(first)

    reader_vendor, reader_model = _classify_from_smartcard_reader(smartcard_readers)
    if reader_vendor:
        vendor = reader_vendor
    if reader_model:
        model = reader_model

    reader_name = smartcard_info.get("reader")
    card_name = smartcard_info.get("card")
    provider_name = smartcard_info.get("provider")
    if provider_name:
        vendor = provider_name
    if reader_name:
        model = reader_name

    installed_driver_name = _classify_driver_name(drivers)

    if token_connected:
        vendor_lower = str((vendor or "")).lower()
        if "gd" in vendor_lower or "safesign" in vendor_lower:
            hardware_label = "Token A3 GD conectado"
        elif "safenet" in vendor_lower or "aladdin" in vendor_lower or "gemalto" in vendor_lower:
            hardware_label = "Token A3 SafeNet conectado"
        else:
            hardware_label = f"Token detectado ({model or 'desconhecido'})"
    else:
        hardware_label = "Nenhum token conectado"

    if installed_driver_name:
        driver_label = f"{installed_driver_name} instalado"
    else:
        driver_label = "Driver não encontrado"

    return {
        "token_detected": token_connected,
        "token_connected": token_connected,
        "vendor": vendor,
        "model": model,
        "usb_vid": usb_vid,
        "usb_pid": usb_pid,
        "driver_required": VID_DRIVER_MAP.get(str(usb_vid or "").upper()),
        "driver_installed": installed_driver_name,
        "driver_version": get_driver_version(drivers),
        "reader": reader_name,
        "card": card_name,
        "provider": provider_name,
        "hardware_label": hardware_label,
        "driver_label": driver_label,
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
