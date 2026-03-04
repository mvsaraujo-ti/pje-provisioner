from __future__ import annotations

import json
import re
import subprocess
import winreg


DEVICE_KEYWORDS = [
    "smartcard",
    "token",
    "safenet",
    "aladdin",
    "watchdata",
    "feitian",
    "gd",
]

DRIVER_KEYWORDS = [
    "safenet",
    "safesign",
    "watchdata",
    "etoken",
    "gd",
    "starsign",
]


def _json_to_list(payload: str) -> list[dict]:
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


def _extract_vid_pid(pnp_device_id: str) -> tuple[str | None, str | None]:
    vid_match = re.search(r"VID_([0-9A-Fa-f]{4})", pnp_device_id or "")
    pid_match = re.search(r"PID_([0-9A-Fa-f]{4})", pnp_device_id or "")
    vid = vid_match.group(1).upper() if vid_match else None
    pid = pid_match.group(1).upper() if pid_match else None
    return vid, pid


def detect_usb_devices() -> list[dict]:
    """
    Detecta dispositivos USB relacionados a token/smartcard via Win32_PnPEntity.
    """
    pattern = "|".join(re.escape(word) for word in DEVICE_KEYWORDS)
    cmd = [
        "powershell",
        "-NoProfile",
        "-Command",
        (
            "$devices = Get-CimInstance Win32_PnPEntity | "
            "Where-Object { "
            "$_.Name -match '(?i)"
            + pattern
            + "' -or $_.Manufacturer -match '(?i)"
            + pattern
            + "' }; "
            "$devices | Select-Object Name, Manufacturer, PNPDeviceID | ConvertTo-Json -Compress"
        ),
    ]

    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        return []

    devices: list[dict] = []
    for item in _json_to_list((result.stdout or "").strip()):
        pnp_id = str(item.get("PNPDeviceID") or "").strip()
        vid, pid = _extract_vid_pid(pnp_id)
        devices.append(
            {
                "name": str(item.get("Name") or "").strip(),
                "manufacturer": str(item.get("Manufacturer") or "").strip(),
                "pnp_device_id": pnp_id,
                "usb_vid": vid,
                "usb_pid": pid,
            }
        )
    return devices


def detect_smartcard_readers() -> list[dict]:
    """
    Detecta leitores smartcard via Win32_PnPEntity.
    """
    cmd = [
        "powershell",
        "-NoProfile",
        "-Command",
        (
            "$devices = Get-CimInstance Win32_PnPEntity | "
            "Where-Object { $_.Name -match '(?i)smartcard|leitor' }; "
            "$devices | Select-Object Name, Manufacturer, PNPDeviceID | ConvertTo-Json -Compress"
        ),
    ]

    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        return []

    readers: list[dict] = []
    for item in _json_to_list((result.stdout or "").strip()):
        pnp_id = str(item.get("PNPDeviceID") or "").strip()
        vid, pid = _extract_vid_pid(pnp_id)
        readers.append(
            {
                "name": str(item.get("Name") or "").strip(),
                "manufacturer": str(item.get("Manufacturer") or "").strip(),
                "pnp_device_id": pnp_id,
                "usb_vid": vid,
                "usb_pid": pid,
            }
        )
    return readers


def _read_uninstall_entries(path: str, wow_flag: int) -> list[dict]:
    entries: list[dict] = []
    access = winreg.KEY_READ | wow_flag
    try:
        parent = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, path, 0, access)
    except OSError:
        return entries

    try:
        index = 0
        while True:
            try:
                subkey_name = winreg.EnumKey(parent, index)
            except OSError:
                break
            index += 1

            try:
                subkey = winreg.OpenKey(parent, subkey_name, 0, access)
            except OSError:
                continue

            try:
                display_name = str(winreg.QueryValueEx(subkey, "DisplayName")[0]).strip()
            except OSError:
                display_name = ""
            try:
                display_version = str(winreg.QueryValueEx(subkey, "DisplayVersion")[0]).strip()
            except OSError:
                display_version = ""
            try:
                publisher = str(winreg.QueryValueEx(subkey, "Publisher")[0]).strip()
            except OSError:
                publisher = ""

            haystack = f"{display_name} {publisher}".lower()
            if any(keyword in haystack for keyword in DRIVER_KEYWORDS):
                entries.append(
                    {
                        "display_name": display_name,
                        "display_version": display_version,
                        "publisher": publisher,
                        "registry_key": f"{path}\\{subkey_name}",
                    }
                )
    finally:
        winreg.CloseKey(parent)

    return entries


def detect_installed_token_drivers() -> list[dict]:
    """
    Detecta softwares/drivers de token instalados no registry.
    """
    uninstall_paths = [
        r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall",
        r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall",
    ]
    wow_flags = [winreg.KEY_WOW64_64KEY, winreg.KEY_WOW64_32KEY]

    seen: set[str] = set()
    drivers: list[dict] = []
    for path in uninstall_paths:
        for wow_flag in wow_flags:
            for item in _read_uninstall_entries(path, wow_flag):
                key = item["registry_key"].lower()
                if key in seen:
                    continue
                seen.add(key)
                drivers.append(item)
    return drivers


def get_driver_version(drivers: list[dict] | None = None) -> str | None:
    """
    Retorna DisplayVersion do primeiro driver identificado.
    """
    items = drivers if drivers is not None else detect_installed_token_drivers()
    for item in items:
        version = str(item.get("display_version") or "").strip()
        if version:
            return version
    return None

