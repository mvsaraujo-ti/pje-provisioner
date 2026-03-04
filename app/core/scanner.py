from __future__ import annotations

import os
import subprocess

from app.modules.browser_detector_module import detect_browsers
from app.modules.token_detector_module import detect_token_hardware
from infra.pje_office_windows import PJeOfficeWindows
from app.utils.logger import get_logger


class SystemScanner:
    @staticmethod
    def _get_pje_office_version_from_path(exe_path: str) -> str | None:
        command = [
            "powershell",
            "-NoProfile",
            "-Command",
            f"(Get-Item '{exe_path}').VersionInfo.ProductVersion",
        ]
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=False,
        )
        version = (result.stdout or "").strip()
        return version or None

    def run_full_scan(self):
        logger = get_logger()
        results = {}

        token_info = detect_token_hardware()
        token_detected = bool(token_info.get("token_detected"))
        token_vendor = token_info.get("vendor")
        token_model = token_info.get("model")
        token_vid = token_info.get("usb_vid")
        token_pid = token_info.get("usb_pid")
        token_driver = token_info.get("driver_installed")
        token_driver_version = token_info.get("driver_version")
        token_reader = token_info.get("reader")
        token_provider = token_info.get("provider")

        if token_detected:
            model_text = token_reader or token_model or "Token detectado"
            vendor_text = token_provider or token_vendor or "Fabricante desconhecido"
            vid_text = token_vid or "N/A"
            pid_text = token_pid or "N/A"
            driver_text = token_driver or "Nao encontrado"
            version_text = token_driver_version or "N/A"
            token_message = (
                f"TOKEN HARDWARE - {model_text}; "
                f"VID/PID: {vid_text} / {pid_text}; "
                f"Provider: {vendor_text}; "
                f"TOKEN DRIVER - {driver_text} {version_text}"
            )
        else:
            token_message = "TOKEN HARDWARE - Nenhum token conectado"

        results["token"] = {
            "status": token_detected,
            "message": token_message,
            "details": token_info,
        }

        logger.info("driver_scan_started", extra={"event": "driver_scan_started"})
        driver_installed = bool(token_driver)
        if driver_installed and token_driver_version:
            driver_message = f"TOKEN DRIVER - {token_driver} {token_driver_version}"
        elif driver_installed:
            driver_message = f"TOKEN DRIVER - {token_driver} instalado"
        else:
            driver_message = "TOKEN DRIVER - Driver não encontrado"

        if driver_installed and not token_detected:
            if token_driver_version:
                driver_message = (
                    f"TOKEN DRIVER - {token_driver} {token_driver_version}"
                )
            else:
                driver_message = f"TOKEN DRIVER - {token_driver} instalado"

        results["driver"] = {
            "status": driver_installed,
            "message": driver_message,
            "details": token_info,
        }
        logger.info(
            "driver_scan_finished",
            extra={"event": "driver_scan_finished", "driver_installed": driver_installed},
        )

        logger.info("pjeoffice_scan_started", extra={"event": "pjeoffice_scan_started"})
        windows = PJeOfficeWindows()
        pje_version = windows.get_pje_office_version()
        if not pje_version:
            alt_path = r"C:\Program Files (x86)\PJeOffice Pro\pjeoffice-pro.exe"
            if os.path.exists(alt_path):
                pje_version = self._get_pje_office_version_from_path(alt_path)

        if pje_version:
            pje_status = True
            pje_message = f"PJE_OFFICE - PJeOffice Pro instalado (versão {pje_version})"
        else:
            pje_status = False
            pje_message = "PJE_OFFICE - Não instalado"

        results["pje_office"] = {
            "status": pje_status,
            "message": pje_message,
        }
        logger.info(
            "pjeoffice_scan_finished",
            extra={"event": "pjeoffice_scan_finished", "installed": pje_status},
        )

        logger.info("browser_scan_started", extra={"event": "browser_scan_started"})
        browser_info = detect_browsers()
        chrome_ok = browser_info.get("chrome")
        edge_ok = browser_info.get("edge")
        firefox_ok = browser_info.get("firefox")
        recommended = browser_info.get("recommended")
        chrome_path = browser_info.get("chrome_path")

        browser_message = (
            "Chrome: " + ("OK" if chrome_ok else "Not found") + "; "
            "Edge: " + ("OK" if edge_ok else "Not found") + "; "
            "Firefox: " + ("OK" if firefox_ok else "Not found") + "; "
            "Navegador recomendado: " + (str(recommended).capitalize() if recommended else "None")
        )
        if chrome_path:
            browser_message += f"; Chrome path: {chrome_path}"

        logger.info(
            "browser_scan_finished",
            extra={
                "event": "browser_scan_finished",
                "chrome": bool(chrome_ok),
                "edge": bool(edge_ok),
                "firefox": bool(firefox_ok),
                "recommended": recommended,
            },
        )

        results["browser"] = {
            "status": bool(chrome_ok or edge_ok or firefox_ok),
            "message": browser_message,
            "details": browser_info,
        }

        return results

    def run_simulated_fixes(self, scan_results):
        fixed_results = {}

        for component, data in scan_results.items():
            if data["status"]:
                fixed_results[component] = data
                continue

            fixed_results[component] = {
                "status": True,
                "message": f"{component.replace('_', ' ').title()} corrigido"
            }

        return fixed_results
