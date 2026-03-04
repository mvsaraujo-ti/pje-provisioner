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
from infra.pje_office_windows import PJeOfficeWindows
from app.utils.logger import get_logger


class PJeOfficeWorker(QThread):
    finished = Signal(dict)

    def run(self):
        print("ENTERED Worker.run")
        service = PJeOfficeService()
        try:
            print("CALLING REAL PJE SERVICE")
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
        self.setMinimumSize(700, 500)

        self.scanner = SystemScanner()
        self.last_results = {}
        self.logger = get_logger()
        self.fix_worker = None
        self.waiting_pje_office_install = False
        self.pje_office_progress_value = 0
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

        self.btn_scan = QPushButton("Modo Diagnóstico")
        self.btn_fix = QPushButton("Aplicar Correções")
        self.btn_scan.setIcon(
            self.style().standardIcon(QStyle.StandardPixmap.SP_FileDialogContentsView)
        )
        self.btn_fix.setIcon(
            self.style().standardIcon(QStyle.StandardPixmap.SP_BrowserReload)
        )

        layout.addWidget(self.btn_scan)
        layout.addWidget(self.btn_fix)

        self.checklist = QListWidget()
        layout.addWidget(self.checklist)

        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setFormat("Pronto")
        layout.addWidget(self.progress)

        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        self.log_area.setPlaceholderText("Logs aparecerão aqui...")
        layout.addWidget(self.log_area)

        layout.addStretch(1)

        footer = QLabel(
            "---------------------------------\n"
            "PJE Environment Provisioner\n\n"
            "Versão: 0.2.0\n\n"
            "Developer: Maxwell Araújo\n"
            "Contato: maxwellaraujoti@gmail.com\n"
            "---------------------------------"
        )
        footer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        footer.setStyleSheet("color: #666; font-size: 11px;")
        layout.addWidget(footer)

        # Eventos
        self.btn_scan.clicked.connect(self.run_scan)
        self.btn_fix.clicked.connect(self.run_fix)

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
            status = data["status"]
            message = data["message"]

            item_text = f"{component.upper()} → {message}"
            item = QListWidgetItem(item_text)

            if status:
                item.setForeground(QColor("green"))
                item.setIcon(
                    self.style().standardIcon(QStyle.StandardPixmap.SP_DialogApplyButton)
                )
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
                item.setForeground(QColor("red"))
                item.setIcon(
                    self.style().standardIcon(QStyle.StandardPixmap.SP_MessageBoxCritical)
                )
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

            self.checklist.addItem(item)

            progress_pct = int((index / total) * 100) if total else 100
            self.progress.setValue(progress_pct)
            QApplication.processEvents()

        self.log_area.append("\nVarredura concluída.\n")
        self.progress.setFormat("Varredura concluída")
        self.btn_scan.setEnabled(True)
        self.btn_fix.setEnabled(True)
        self.logger.info(
            "scan_finished",
            extra={
                "event": "scan_finished",
                "items_total": total,
            },
        )

    def run_fix(self):
        print("ENTERED run_fix")
        print("SIMULATION CHECK: no scanner.run_simulated_fixes call in run_fix")
        if not self.last_results:
            self.log_area.append("[ERRO] Execute a varredura antes de aplicar correções.\n")
            self.logger.error(
                "fix_blocked_without_scan",
                extra={"event": "fix_blocked_without_scan"},
            )
            return

        self.logger.info("fix_started", extra={"event": "fix_started"})
        self.btn_scan.setEnabled(False)
        self.btn_fix.setEnabled(False)
        self.progress.setRange(0, 0)
        self.progress.setFormat("Aplicando correções...")
        self.log_area.append("Iniciando correções reais...\n")

        needs_pje_office_fix = False
        for component, data in self.last_results.items():
            if component == "pje_office" and not data["status"]:
                needs_pje_office_fix = True
                break

        if needs_pje_office_fix:
            print("run_fix: calling REAL SERVICE in worker thread")
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

        print("run_fix: no real/simulated fix call needed, finalizing")
        self._finalize_fix(None)

    def _on_fix_finished(self, result):
        if self.fix_worker is not None:
            self.fix_worker.deleteLater()
            self.fix_worker = None

        if self.pje_office_timer.isActive():
            self.pje_office_timer.stop()

        if self.waiting_pje_office_install:
            install_ok = (
                result is not None
                and result.get("status") in ("installed", "updated", "up_to_date")
            )
            validated = os.path.exists(self.PJE_OFFICE_EXECUTABLE)

            if install_ok and validated:
                result = {
                    "status": "installed",
                    "message": "PJe Office instalado com sucesso.",
                }
                self.log_area.append("PJe Office instalado com sucesso.")
                self.progress.setRange(0, 100)
                self.progress.setValue(100)
                self.progress.setFormat("PJe Office instalado com sucesso.")
                try:
                    os.startfile(self.PJE_OFFICE_EXECUTABLE)
                except Exception as exc:
                    self.logger.warning(
                        "pje_office_auto_launch_failed",
                        extra={
                            "event": "pje_office_auto_launch_failed",
                            "error": str(exc),
                        },
                    )
            elif install_ok and not validated:
                result = {
                    "status": "error",
                    "message": "Falha ao validar instalacao do PJe Office.",
                }

        self.waiting_pje_office_install = False
        self._finalize_fix(result)

        if result is not None and result.get("status") in ("installed", "updated", "up_to_date"):
            self.progress.setRange(0, 100)
            self.progress.setValue(100)
            self.progress.setFormat("PJe Office instalado com sucesso.")

    def _check_pje_office_installation(self):
        if not self.waiting_pje_office_install:
            if self.pje_office_timer.isActive():
                self.pje_office_timer.stop()
            return

        install_pid = PJeOfficeWindows.get_current_install_pid()
        is_running = False
        if install_pid:
            is_running = psutil.pid_exists(install_pid)

        self.pje_office_progress_value += 5 if is_running else 1
        if self.pje_office_progress_value > 95:
            self.pje_office_progress_value = 5

        self.progress.setValue(self.pje_office_progress_value)
        self.progress.setFormat("Instalando PJe Office Pro... %p%")
        QApplication.processEvents()

    def _finalize_fix(self, worker_result):
        print("ENTERED _finalize_fix")
        if self.pje_office_timer.isActive():
            self.pje_office_timer.stop()
        self.waiting_pje_office_install = False
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setFormat("Aplicando correções... %p%")

        fixed_results = {}
        component_order = ["token", "driver", "pje_office", "browser"]
        ordered_components = [c for c in component_order if c in self.last_results]
        ordered_components.extend(
            [c for c in self.last_results.keys() if c not in ordered_components]
        )

        for component in ordered_components:
            data = self.last_results[component]
            status = data["status"]

            if component == "pje_office" and not status:
                print("_finalize_fix: using REAL SERVICE result for pje_office")
                result = worker_result or {
                    "status": "error",
                    "message": "Falha ao obter resultado da instalação.",
                }
                fixed_results[component] = {
                    "status": result["status"] in ("installed", "updated", "up_to_date"),
                    "message": result["message"],
                }
            elif component == "browser" and not status:
                self.logger.info(
                    "BROWSER_FIX_STARTED",
                    extra={"event": "BROWSER_FIX_STARTED"},
                )

                browser_ok = False
                try:
                    browser_result = run_browser_fix()
                    browser_ok = browser_result.get("status") == "ok"
                except Exception:
                    browser_ok = False

                self.logger.info(
                    "BROWSER_FIX_COMPLETED",
                    extra={
                        "event": "BROWSER_FIX_COMPLETED",
                        "success": browser_ok,
                    },
                )

                if browser_ok:
                    fixed_results[component] = {
                        "status": True,
                        "message": "Correções de navegador aplicadas",
                    }
                else:
                    fixed_results[component] = {
                        "status": False,
                        "message": "Falha ao corrigir navegador",
                    }
            else:
                fixed_results[component] = data
        total = len(fixed_results)

        self.checklist.clear()
        for index, (component, data) in enumerate(fixed_results.items(), start=1):
            status = data["status"]
            message = data["message"]
            item = QListWidgetItem(f"{component.upper()} → {message}")

            if status:
                item.setForeground(QColor("green"))
                item.setIcon(
                    self.style().standardIcon(QStyle.StandardPixmap.SP_DialogApplyButton)
                )
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
                item.setForeground(QColor("red"))
                item.setIcon(
                    self.style().standardIcon(QStyle.StandardPixmap.SP_MessageBoxCritical)
                )
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

            self.checklist.addItem(item)

            progress_pct = int((index / total) * 100) if total else 100
            self.progress.setValue(progress_pct)
            QApplication.processEvents()

        self.last_results = fixed_results
        self.log_area.append("\nCorreções concluídas.\n")
        self.progress.setFormat("Correções concluídas")
        self.btn_scan.setEnabled(True)
        self.btn_fix.setEnabled(True)
        self.logger.info(
            "fix_finished",
            extra={
                "event": "fix_finished",
                "items_total": total,
            },
        )
