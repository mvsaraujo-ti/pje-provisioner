from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QLabel,
    QPushButton,
    QListWidget,
    QListWidgetItem,
    QTextEdit,
    QProgressBar,
    QStyle,
)
from PySide6.QtCore import Qt, QThread, Signal, QTimer
from PySide6.QtGui import QColor
import os
import psutil

from app.core.scanner import SystemScanner
from app.core.pje_office_service import PJeOfficeService
from app.modules.browser_module import run_browser_fix
from app.modules.token_driver_installer import install_missing_token_driver
from infra.pje_office_windows import PJeOfficeWindows
from app.utils.logger import get_logger


class PJeOfficeWorker(QThread):
    finished = Signal(dict)

    def run(self):
        service = PJeOfficeService()
        try:
            result = service.ensure_installed()
        except Exception as exc:
            result = {
                "status": "error",
                "message": f"Falha ao instalar PJe Office: {exc}",
            }
        self.finished.emit(result)


class MainWindow(QMainWindow):
    PJE_OFFICE_EXECUTABLE = r"C:\Program Files\PJeOffice Pro\pjeoffice-pro.exe"

    def __init__(self):
        super().__init__()

        self.setWindowTitle("PJE Provisioner")
        self.setMinimumSize(980, 760)
        self.setStyleSheet(
            "QMainWindow { background-color: #f7f9fc; }"
            "QListWidget { background-color: #ffffff; border: 1px solid #dce3ee; }"
            "QTextEdit { background-color: #ffffff; border: 1px solid #dce3ee; }"
            "QPushButton { background-color: #e8eef8; border: 1px solid #c8d6ea; padding: 6px; }"
            "QPushButton:hover { background-color: #dfe8f7; }"
        )

        self.scanner = SystemScanner()
        self.last_results = {}
        self.logger = get_logger()
        self.fix_worker = None
        self.waiting_pje_office_install = False
        self.pje_office_progress_value = 0
        self.browser_opened_after_fix = False

        self.pje_office_timer = QTimer(self)
        self.pje_office_timer.setInterval(1000)
        self.pje_office_timer.timeout.connect(self._check_pje_office_installation)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        layout = QVBoxLayout()
        central_widget.setLayout(layout)

        title = QLabel("PJE Environment Provisioner")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-size: 20px; font-weight: bold;")
        layout.addWidget(title)

        self.btn_scan = QPushButton("Modo Diagnostico")
        self.btn_fix = QPushButton("Aplicar Correcoes")
        self.btn_scan.setIcon(
            self.style().standardIcon(QStyle.StandardPixmap.SP_FileDialogContentsView)
        )
        self.btn_fix.setIcon(
            self.style().standardIcon(QStyle.StandardPixmap.SP_BrowserReload)
        )

        top_label = QLabel("Acoes")
        top_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #234;")
        layout.addWidget(top_label)
        layout.addWidget(self.btn_scan)
        layout.addWidget(self.btn_fix)

        center_label = QLabel("Diagnostico do ambiente")
        center_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #234;")
        layout.addWidget(center_label)

        self.checklist = QListWidget()
        self.checklist.setMinimumHeight(260)
        layout.addWidget(self.checklist, 2)

        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setFormat("Pronto")
        layout.addWidget(self.progress)

        base_label = QLabel("Logs da execucao")
        base_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #234;")
        layout.addWidget(base_label)

        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        self.log_area.setPlaceholderText("Logs aparecerao aqui...")
        self.log_area.setMinimumHeight(280)
        layout.addWidget(self.log_area, 3)

        footer = QLabel(
            "---------------------------------\n"
            "PJE Environment Provisioner\n\n"
            "Versao: 0.4.0\n\n"
            "Developer: Maxwell Araujo\n"
            "Contato: maxwellaraujoti@gmail.com\n"
            "---------------------------------"
        )
        footer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        footer.setStyleSheet("color: #666; font-size: 11px;")
        layout.addWidget(footer)

        self.btn_scan.clicked.connect(self.run_scan)
        self.btn_fix.clicked.connect(self.run_fix)

    def _decorate_item(self, component: str, status: bool, message: str) -> QListWidgetItem:
        warning = (
            "DESATUALIZADO" in message.upper()
            or "NENHUM TOKEN CONECTADO" in message.upper()
            or "NAO INSTALADO" in message.upper()
        )
        symbol = "✔" if status else ("⚠" if warning else "✖")
        color = "#1f8f4c" if status else ("#c99700" if warning else "#c63d3d")

        item = QListWidgetItem(f"{symbol} {component.upper()}\n{message}")
        item.setForeground(QColor(color))
        if status:
            icon = QStyle.StandardPixmap.SP_DialogApplyButton
        elif warning:
            icon = QStyle.StandardPixmap.SP_MessageBoxWarning
        else:
            icon = QStyle.StandardPixmap.SP_MessageBoxCritical
        item.setIcon(self.style().standardIcon(icon))
        return item

    def _scan_message_for_component(self, component: str, data: dict) -> str:
        message = str(data.get("message") or "")

        if component == "token" and isinstance(data.get("details"), dict):
            details = data["details"]
            hw = details.get("hardware_label") or "Nenhum token conectado"
            drv = details.get("driver_installed") or "Driver nao encontrado"
            ver = details.get("driver_version") or ""
            if ver:
                drv = f"{drv} {ver}"
            return f"TOKEN HARDWARE - {hw}; TOKEN DRIVER - {drv}"

        if component == "driver" and isinstance(data.get("details"), dict):
            details = data["details"]
            drv = details.get("driver_installed") or "Driver nao encontrado"
            ver = details.get("driver_version") or ""
            if ver:
                drv = f"{drv} {ver}"
            return f"TOKEN DRIVER - {drv}"

        if component == "browser" and isinstance(data.get("details"), dict):
            bd = data["details"]
            chrome = "OK" if bd.get("chrome") else "Not found"
            edge = "OK" if bd.get("edge") else "Not found"
            firefox = "OK" if bd.get("firefox") else "Not found"
            rec = str(bd.get("recommended") or "None").capitalize()
            text = f"Chrome: {chrome} | Edge: {edge} | Firefox: {firefox} | Navegador recomendado: {rec}"
            chrome_path = bd.get("chrome_path")
            if chrome_path:
                text += f" | Chrome path: {chrome_path}"
            return text

        return message

    def run_scan(self):
        self.logger.info("scan_started", extra={"event": "scan_started"})
        self.btn_scan.setEnabled(False)
        self.btn_fix.setEnabled(False)
        self.progress.setValue(0)
        self.progress.setFormat("Varredura em andamento... %p%")
        self.log_area.append("Iniciando varredura...\n")

        self.last_results = self.scanner.run_full_scan()

        self.checklist.clear()
        total = len(self.last_results)

        for index, (component, data) in enumerate(self.last_results.items(), start=1):
            status = bool(data.get("status"))
            message = self._scan_message_for_component(component, data)

            item = self._decorate_item(component, status, message)
            self.checklist.addItem(item)

            if status:
                self.log_area.append(f"[OK] {message}")
                self.logger.info(
                    "scan_component_ok",
                    extra={
                        "event": "scan_component_ok",
                        "component": component,
                        "status": status,
                        "detail": message,
                    },
                )
            else:
                self.log_area.append(f"[ERRO] {message}")
                self.logger.warning(
                    "scan_component_error",
                    extra={
                        "event": "scan_component_error",
                        "component": component,
                        "status": status,
                        "detail": message,
                    },
                )

            progress_pct = int((index / total) * 100) if total else 100
            self.progress.setValue(progress_pct)
            QApplication.processEvents()

        self.log_area.append("\nVarredura concluida.\n")
        self.progress.setFormat("Varredura concluida")
        self.btn_scan.setEnabled(True)
        self.btn_fix.setEnabled(True)
        self.logger.info(
            "scan_finished",
            extra={"event": "scan_finished", "items_total": total},
        )

    def run_fix(self):
        self.browser_opened_after_fix = False
        if not self.last_results:
            self.log_area.append("[ERRO] Execute a varredura antes de aplicar correcoes.\n")
            self.logger.error("fix_blocked_without_scan", extra={"event": "fix_blocked_without_scan"})
            return

        self.logger.info("fix_started", extra={"event": "fix_started"})
        self.btn_scan.setEnabled(False)
        self.btn_fix.setEnabled(False)
        self.progress.setRange(0, 0)
        self.progress.setFormat("Aplicando correcoes...")
        self.log_area.append("Iniciando correcoes reais...\n")

        needs_pje_office_fix = any(
            comp == "pje_office" and not bool(data.get("status"))
            for comp, data in self.last_results.items()
        )

        if needs_pje_office_fix:
            self.waiting_pje_office_install = True
            self.pje_office_progress_value = 0
            self.progress.setRange(0, 100)
            self.progress.setValue(0)
            self.progress.setFormat("Instalando PJe Office Pro... %p%")
            self.log_area.append("Instalando PJe Office Pro...")
            self.pje_office_timer.start()
            self.fix_worker = PJeOfficeWorker()
            self.fix_worker.finished.connect(self._on_fix_finished)
            self.fix_worker.start()
            return

        self._finalize_fix(None)

    def _on_fix_finished(self, result):
        if self.fix_worker is not None:
            self.fix_worker.deleteLater()
            self.fix_worker = None

        if self.pje_office_timer.isActive():
            self.pje_office_timer.stop()

        if self.waiting_pje_office_install:
            install_ok = result is not None and result.get("status") in ("installed", "updated", "up_to_date")
            validated = os.path.exists(self.PJE_OFFICE_EXECUTABLE)

            if install_ok and validated:
                result = {"status": "installed", "message": "PJe Office instalado com sucesso."}
                self.log_area.append("PJe Office instalado com sucesso.")
                self.progress.setRange(0, 100)
                self.progress.setValue(100)
                self.progress.setFormat("PJe Office instalado com sucesso.")
                try:
                    os.startfile(self.PJE_OFFICE_EXECUTABLE)
                except Exception as exc:
                    self.logger.warning(
                        "pje_office_auto_launch_failed",
                        extra={"event": "pje_office_auto_launch_failed", "error": str(exc)},
                    )
            elif install_ok and not validated:
                result = {"status": "error", "message": "Falha ao validar instalacao do PJe Office."}

        self.waiting_pje_office_install = False
        self._finalize_fix(result)

    def _check_pje_office_installation(self):
        if not self.waiting_pje_office_install:
            if self.pje_office_timer.isActive():
                self.pje_office_timer.stop()
            return

        install_pid = PJeOfficeWindows.get_current_install_pid()
        is_running = bool(install_pid and psutil.pid_exists(install_pid))

        self.pje_office_progress_value += 5 if is_running else 1
        if self.pje_office_progress_value > 95:
            self.pje_office_progress_value = 5

        self.progress.setValue(self.pje_office_progress_value)
        self.progress.setFormat("Instalando PJe Office Pro... %p%")
        QApplication.processEvents()

    def _finalize_fix(self, worker_result):
        if self.pje_office_timer.isActive():
            self.pje_office_timer.stop()
        self.waiting_pje_office_install = False

        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setFormat("Aplicando correcoes... %p%")

        fixed_results = {}
        component_order = ["token", "driver", "pje_office", "browser"]
        ordered_components = [c for c in component_order if c in self.last_results]
        ordered_components.extend([c for c in self.last_results if c not in ordered_components])

        for component in ordered_components:
            data = self.last_results[component]
            status = bool(data.get("status"))

            if component == "pje_office" and not status:
                result = worker_result or {
                    "status": "error",
                    "message": "Falha ao obter resultado da instalacao.",
                }
                fixed_results[component] = {
                    "status": result.get("status") in ("installed", "updated", "up_to_date"),
                    "message": result.get("message"),
                }

            elif component == "driver" and not status:
                self.log_area.append("Instalando driver do token...")
                token_details = self.last_results.get("token", {}).get("details", {})
                install_result = install_missing_token_driver(token_details)
                if install_result.get("status") == "ok":
                    self.log_area.append("[OK] Driver do token instalado. Reexecutando diagnostico...")
                    rescanned = self.scanner.run_full_scan()
                    fixed_results["token"] = rescanned.get("token", self.last_results.get("token", {}))
                    fixed_results["driver"] = rescanned.get("driver", data)
                else:
                    fixed_results[component] = {
                        "status": False,
                        "message": install_result.get("message", "Falha ao instalar driver do token"),
                    }

            elif component == "browser" and not status:
                self.logger.info("BROWSER_FIX_STARTED", extra={"event": "BROWSER_FIX_STARTED"})
                browser_result = run_browser_fix()
                browser_ok = browser_result.get("status") == "ok"
                if browser_ok:
                    self.browser_opened_after_fix = True
                self.logger.info(
                    "BROWSER_FIX_COMPLETED",
                    extra={"event": "BROWSER_FIX_COMPLETED", "success": browser_ok},
                )
                fixed_results[component] = {
                    "status": browser_ok,
                    "message": "Correcoes de navegador aplicadas" if browser_ok else "Falha ao corrigir navegador",
                }

            else:
                fixed_results[component] = data

        self.checklist.clear()
        total = len(fixed_results)
        for index, (component, data) in enumerate(fixed_results.items(), start=1):
            status = bool(data.get("status"))
            message = self._scan_message_for_component(component, data)
            item = self._decorate_item(component, status, message)
            self.checklist.addItem(item)

            if status:
                self.log_area.append(f"[OK] {message}")
                self.logger.info(
                    "fix_component_ok",
                    extra={
                        "event": "fix_component_ok",
                        "component": component,
                        "status": status,
                        "detail": message,
                    },
                )
            else:
                self.log_area.append(f"[ERRO] {message}")
                self.logger.warning(
                    "fix_component_error",
                    extra={
                        "event": "fix_component_error",
                        "component": component,
                        "status": status,
                        "detail": message,
                    },
                )

            progress_pct = int((index / total) * 100) if total else 100
            self.progress.setValue(progress_pct)
            QApplication.processEvents()

        self.last_results = fixed_results
        self.log_area.append("\nCorrecoes concluidas.\n")
        self.progress.setFormat("Correcoes concluidas")
        self.btn_scan.setEnabled(True)
        self.btn_fix.setEnabled(True)
        self.logger.info("fix_finished", extra={"event": "fix_finished", "items_total": total})

        all_ok = all(bool(item.get("status")) for item in fixed_results.values()) if fixed_results else False
        if all_ok and not self.browser_opened_after_fix:
            browser_result = run_browser_fix()
            if browser_result.get("status") == "ok":
                self.browser_opened_after_fix = True
                self.log_area.append("[OK] Chrome aberto na pagina inicial do PJe.")
