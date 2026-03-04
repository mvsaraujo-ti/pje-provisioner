from __future__ import annotations

from app.infra.browser_windows import detect_browser
from app.modules.token_detector_module import detect_token_hardware
from infra.pje_office_windows import PJeOfficeWindows


class SystemScanner:
    def run_full_scan(self):
        results = {}

        token_info = detect_token_hardware()
        token_detected = bool(token_info.get("token_detected"))
        token_vendor = token_info.get("vendor")
        token_model = token_info.get("model")
        token_vid = token_info.get("usb_vid")
        token_pid = token_info.get("usb_pid")
        token_driver = token_info.get("driver_installed")
        token_driver_version = token_info.get("driver_version")

        if token_detected:
            vendor_text = token_vendor or "Fabricante desconhecido"
            model_text = token_model or "Modelo desconhecido"
            vid_text = token_vid or "N/A"
            pid_text = token_pid or "N/A"
            driver_text = token_driver or "Nao encontrado"
            version_text = token_driver_version or "N/A"
            token_message = (
                f"Hardware detectado: {vendor_text} {model_text}; "
                f"VID/PID: {vid_text} / {pid_text}; "
                f"Driver instalado: {driver_text}; "
                f"Versao: {version_text}"
            )
        else:
            token_message = "Token nao detectado"

        results["token"] = {
            "status": token_detected,
            "message": token_message,
        }

        driver_installed = bool(token_driver)
        driver_required = token_info.get("driver_required")
        if driver_installed and token_driver_version:
            if driver_required and driver_required.lower() not in token_driver.lower():
                driver_message = (
                    f"Driver instalado: {token_driver} (versao {token_driver_version}) "
                    f"- recomendado: {driver_required} - Status: DESATUALIZADO"
                )
            else:
                driver_message = (
                    f"Driver instalado: {token_driver} (versao {token_driver_version}) "
                    " - Status: OK"
                )
        elif driver_installed:
            driver_message = f"Driver instalado: {token_driver} - Status: OK"
        else:
            if driver_required:
                driver_message = (
                    f"Driver nao instalado - recomendado: {driver_required} - "
                    "Status: DESATUALIZADO"
                )
            else:
                driver_message = "Driver de token nao instalado - Status: DESATUALIZADO"

        results["driver"] = {
            "status": driver_installed,
            "message": driver_message,
        }

        windows = PJeOfficeWindows()
        pje_version = windows.get_pje_office_version()
        if pje_version:
            pje_status = True
            pje_message = f"PJe Office instalado (versao {pje_version})"
        else:
            pje_status = False
            pje_message = "PJe Office nao instalado"

        results["pje_office"] = {
            "status": pje_status,
            "message": pje_message,
        }

        browser_path = detect_browser()
        if browser_path:
            browser_message = f"Navegador detectado: {browser_path}"
        else:
            browser_message = "Nenhum navegador suportado detectado"

        results["browser"] = {
            "status": bool(browser_path),
            "message": browser_message,
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
