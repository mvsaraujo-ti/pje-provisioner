from __future__ import annotations

from app.modules.browser_detector_module import detect_browsers
from app.modules.token_detector_module import detect_token_hardware
from infra.pje_office_windows import PJeOfficeWindows
from app.utils.logger import get_logger


class SystemScanner:
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
            driver_message = f"TOKEN DRIVER - {token_driver} instalado - Status: OK"
        else:
            if driver_required:
                driver_message = (
                    "TOKEN DRIVER - NAO INSTALADO - "
                    f"recomendado: {driver_required} - Status: ERRO"
                )
            else:
                driver_message = "TOKEN DRIVER - NAO INSTALADO - Status: ERRO"

        if driver_installed and not token_detected:
            if token_driver_version:
                driver_message = (
                    f"TOKEN DRIVER - {token_driver} instalado (versao {token_driver_version})"
                )
            else:
                driver_message = f"TOKEN DRIVER - {token_driver} instalado"

        results["driver"] = {
            "status": driver_installed,
            "message": driver_message,
            "details": token_info,
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
