# -*- coding: utf-8 -*-
from __future__ import annotations

import subprocess
from typing import Callable

from app.infra.pje_office_windows import PJeOfficeWindows
from app.modules.browser_detector_module import detect_browsers
from app.modules.token_detector_module import detect_token_hardware
from app.utils.logger import get_logger

NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)


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
            creationflags=NO_WINDOW,
        )
        version = (result.stdout or "").strip()
        return version or None

    def run_full_scan(
        self,
        progress_callback: Callable[[str, str, dict | None], None] | None = None,
    ) -> dict:
        logger = get_logger()
        logger.info("scan_started", extra={"event": "scan_started"})

        results: dict[str, dict] = {}

        logger.info("smartcard_scan", extra={"event": "smartcard_scan"})
        if progress_callback:
            progress_callback("token", "Detectando token...", None)
        token_info = detect_token_hardware()
        token_detected = bool(token_info.get("token_detected"))
        token_label = token_info.get("hardware_label") or "Nenhum token conectado"

        results["token"] = {
            "status": token_detected,
            "message": token_label,
            "details": token_info,
        }
        if progress_callback:
            progress_callback("token", f"Token: {token_label}", results["token"])

        logger.info("driver_scan", extra={"event": "driver_scan"})
        if progress_callback:
            progress_callback("driver", "Detectando drivers...", None)
        driver_name = token_info.get("driver_installed")
        driver_version = token_info.get("driver_version")
        driver_installed = bool(driver_name)
        if driver_installed and driver_version:
            driver_message = f"{driver_name} {driver_version}"
        elif driver_installed:
            driver_message = f"{driver_name} instalado"
        else:
            driver_message = "Driver não encontrado"

        results["driver"] = {
            "status": driver_installed,
            "message": driver_message,
            "details": token_info,
        }
        if progress_callback:
            progress_callback("driver", f"Drivers: {driver_message}", results["driver"])

        logger.info("pjeoffice_scan", extra={"event": "pjeoffice_scan"})
        if progress_callback:
            progress_callback("pje_office", "Detectando PJeOffice...", None)
        windows = PJeOfficeWindows()
        pje_version = windows.get_pje_office_version()

        if pje_version:
            pje_status = True
            pje_message = f"PJeOffice Pro instalado (versão {pje_version})"
        else:
            pje_status = False
            pje_message = "Não instalado"

        results["pje_office"] = {
            "status": pje_status,
            "message": pje_message,
        }
        if progress_callback:
            progress_callback("pje_office", f"PJeOffice: {pje_message}", results["pje_office"])

        logger.info("browser_scan", extra={"event": "browser_scan"})
        if progress_callback:
            progress_callback("browser", "Detectando navegadores...", None)
        browser_info = detect_browsers()
        chrome_ok = bool(browser_info.get("chrome"))
        edge_ok = bool(browser_info.get("edge"))
        firefox_ok = bool(browser_info.get("firefox"))
        recommended = browser_info.get("recommended")

        browser_lines = [
            f"Chrome {'OK' if chrome_ok else 'Not found'}",
            f"Edge {'OK' if edge_ok else 'Not found'}",
            f"Firefox {'OK' if firefox_ok else 'Not found'}",
            f"Navegador recomendado: {(str(recommended).capitalize() if recommended else 'None')}",
        ]
        if browser_info.get("chrome_path"):
            browser_lines.append(f"Caminho do Chrome: {browser_info['chrome_path']}")

        results["browser"] = {
            "status": bool(chrome_ok or edge_ok or firefox_ok),
            "message": "\n".join(browser_lines),
            "details": browser_info,
        }
        if progress_callback:
            progress_callback("browser", "Deteccao de navegadores concluida.", results["browser"])

        logger.info("scan_finished", extra={"event": "scan_finished"})
        return results

    def run_simulated_fixes(self, scan_results: dict) -> dict:
        fixed_results = {}

        for component, data in scan_results.items():
            if data["status"]:
                fixed_results[component] = data
                continue

            fixed_results[component] = {
                "status": True,
                "message": f"{component.replace('_', ' ').title()} corrigido",
            }

        return fixed_results
