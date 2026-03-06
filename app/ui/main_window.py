# -*- coding: utf-8 -*-
from __future__ import annotations

import psutil
from PySide6.QtCore import QThread, QTimer, Qt, Signal
from PySide6.QtGui import QTextCursor
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QProgressBar,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.core.pje_office_service import PJeOfficeService
from app.core.scanner import SystemScanner
from app.infra.pje_office_windows import PJeOfficeWindows
from app.modules.browser_module import open_chrome, run_browser_fix
from app.modules.token_driver_installer import install_missing_token_driver
from app.ui.components import StatusCard
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


class ScanWorker(QThread):
    log_signal = Signal(str)
    progress_signal = Signal(str, dict, int, str)
    finished_signal = Signal(dict)

    def __init__(self, scanner: SystemScanner, parent=None):
        super().__init__(parent)
        self.scanner = scanner

    def run(self):
        try:
            self.log_signal.emit("Iniciando varredura...")
            order = ["token", "driver", "pje_office", "browser"]

            def on_progress(component: str, message: str, data: dict | None):
                self.log_signal.emit(message)
                if data is None:
                    return
                try:
                    index = order.index(component) + 1
                except ValueError:
                    return
                progress = int((index / len(order)) * 100)
                self.progress_signal.emit(component, data, progress, message)

            results = self.scanner.run_full_scan(progress_callback=on_progress)
            self.finished_signal.emit(results)
        except Exception as exc:
            self.log_signal.emit(f"[ERRO] Falha durante varredura: {exc}")
            self.finished_signal.emit({})


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("PJE Environment Provisioner (Beta)")
        self.resize(900, 650)

        self.scanner = SystemScanner()
        self.last_results: dict[str, dict] = {}
        self.logger = get_logger()
        self.fix_worker = None
        self.scan_worker = None
        self.waiting_pje_office_install = False
        self.pje_office_progress_value = 0
        self._wait_cursor_active = False

        self.pje_office_timer = QTimer(self)
        self.pje_office_timer.setInterval(1000)
        self.pje_office_timer.timeout.connect(self._check_pje_office_installation)

        self._build_ui()
        self._apply_global_stylesheet()

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)

        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(14, 14, 14, 12)
        main_layout.setSpacing(8)
        main_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        header = QLabel("PJE Environment Provisioner (Beta)")
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header.setStyleSheet("font-size: 22px; font-weight: 700;")
        main_layout.addWidget(header)

        actions_label = QLabel("AÇÕES")
        actions_label.setStyleSheet("font-size: 13px; font-weight: 600;")
        main_layout.addWidget(actions_label)

        actions_row = QHBoxLayout()
        actions_row.setSpacing(8)
        actions_row.addStretch(1)
        self.btn_scan = QPushButton("Modo Diagnóstico")
        self.btn_fix = QPushButton("Aplicar Correções")
        self.btn_scan.setMinimumWidth(180)
        self.btn_fix.setMinimumWidth(180)
        actions_row.addWidget(self.btn_scan)
        actions_row.addWidget(self.btn_fix)
        actions_row.addStretch(1)
        main_layout.addLayout(actions_row)

        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setFormat("Pronto")
        main_layout.addWidget(self.progress)

        diagnosis_label = QLabel("DIAGNÓSTICO")
        diagnosis_label.setStyleSheet("font-size: 13px; font-weight: 600;")
        main_layout.addWidget(diagnosis_label)

        self.cards = {
            "token": StatusCard("TOKEN HARDWARE"),
            "driver": StatusCard("TOKEN DRIVER"),
            "pje_office": StatusCard("PJE OFFICE"),
            "browser": StatusCard("BROWSERS"),
        }

        for card in self.cards.values():
            main_layout.addWidget(card)

        logs_label = QLabel("LOGS")
        logs_label.setStyleSheet("font-size: 13px; font-weight: 600;")
        main_layout.addWidget(logs_label)

        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        self.log_area.setMinimumHeight(150)
        self.log_area.setPlaceholderText("Logs da execução...")
        main_layout.addWidget(self.log_area, 1)

        footer = QLabel("Versão 0.5.0\nDeveloper: Maxwell Araújo")
        footer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        footer.setStyleSheet("font-size: 11px; color: #cfcfcf; padding-top: 2px;")
        main_layout.addWidget(footer)

        self.btn_scan.clicked.connect(self.run_scan)
        self.btn_fix.clicked.connect(self.run_fix)

    def _apply_global_stylesheet(self):
        self.setStyleSheet(
            "QMainWindow { background-color: #1e1e1e; }"
            "QWidget { color: #e8e8e8; }"
            "QPushButton { background-color: #2b2b2b; color: #ffffff; border: 1px solid #3a3a3a; border-radius: 8px; padding: 8px 12px; font-size: 13px; font-weight: 600; }"
            "QPushButton:hover { background-color: #343434; }"
            "QPushButton:disabled { background-color: #444444; color: #aaaaaa; }"
            "QProgressBar { border: 1px solid #3a3a3a; border-radius: 6px; text-align: center; background-color: #151515; color: #e8e8e8; }"
            "QProgressBar::chunk { background-color: #3fb950; border-radius: 6px; }"
            "QTextEdit { background-color: #111111; border: 1px solid #3a3a3a; border-radius: 8px; color: #e8e8e8; font-family: 'Consolas', 'Courier New', monospace; font-size: 12px; }"
        )

    def _append_log(self, message: str):
        self.log_area.append(message)
        self.log_area.moveCursor(QTextCursor.MoveOperation.End)
        self.log_area.ensureCursorVisible()

    def _status_from_message(self, ok: bool, message: str) -> str:
        upper = message.upper()
        warning = any(text in upper for text in ["NÃO", "NAO", "NOT FOUND", "NENHUM"])
        if ok:
            return StatusCard.OK
        if warning:
            return StatusCard.WARN
        return StatusCard.ERROR

    def _extract_display_message(self, component: str, data: dict) -> str:
        details = data.get("details") if isinstance(data, dict) else None

        if component == "token" and isinstance(details, dict):
            return details.get("hardware_label") or data.get("message") or "Nenhum token conectado"

        if component == "driver" and isinstance(details, dict):
            name = details.get("driver_installed")
            version = details.get("driver_version")
            if name and version:
                return f"{name} {version}"
            if name:
                return f"{name} instalado"
            return "Driver não encontrado"

        if component == "browser" and isinstance(details, dict):
            chrome = "OK" if details.get("chrome") else "Not found"
            edge = "OK" if details.get("edge") else "Not found"
            firefox = "OK" if details.get("firefox") else "Not found"
            recommended = str(details.get("recommended") or "None").capitalize()
            lines = [
                f"Chrome {chrome}",
                f"Edge {edge}",
                f"Firefox {firefox}",
                f"Navegador recomendado: {recommended}",
            ]
            return "\n".join(lines)

        return str(data.get("message") or "Sem detalhes")

    def _render_cards(self, results: dict[str, dict]):
        for component in ["token", "driver", "pje_office", "browser"]:
            data = results.get(component, {"status": False, "message": "Componente nao encontrado"})
            self._render_component_card(component, data)

    def _render_component_card(self, component: str, data: dict):
        ok = bool(data.get("status"))
        text = self._extract_display_message(component, data)
        state = self._status_from_message(ok, text)
        self.cards[component].set_state(state, text)

    def _set_busy_ui(self, busy: bool):
        self.btn_scan.setEnabled(not busy)
        self.btn_fix.setEnabled(not busy)
        if busy and not self._wait_cursor_active:
            QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
            self._wait_cursor_active = True
        elif not busy and self._wait_cursor_active:
            QApplication.restoreOverrideCursor()
            self._wait_cursor_active = False

    def run_scan(self):
        if self.scan_worker is not None and self.scan_worker.isRunning():
            return

        self.last_results = {}
        self._set_busy_ui(True)
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setFormat("Varredura em andamento... %p%")
        self.log_area.clear()

        self.scan_worker = ScanWorker(self.scanner, self)
        self.scan_worker.log_signal.connect(self._append_log)
        self.scan_worker.progress_signal.connect(self._on_scan_progress)
        self.scan_worker.finished_signal.connect(self._on_scan_finished)
        self.scan_worker.start()

    def _on_scan_progress(self, component: str, data: dict, progress: int, _message: str):
        if component not in self.cards:
            return
        self.last_results[component] = data
        self._render_component_card(component, data)
        self.progress.setValue(progress)
        self.progress.setFormat("Varredura em andamento... %p%")

    def _on_scan_finished(self, results: dict):
        self.last_results = results or {}
        self._render_cards(self.last_results)
        self.progress.setValue(100)
        self._append_log("Varredura concluída.")
        self.progress.setFormat("Varredura concluída")
        self._set_busy_ui(False)

        if self.scan_worker is not None:
            self.scan_worker.deleteLater()
            self.scan_worker = None

    def run_fix(self):
        if not self.last_results:
            self._append_log("[ERRO] Execute a varredura antes de aplicar correções.")
            return

        self._set_busy_ui(True)
        self.progress.setRange(0, 0)
        self.progress.setFormat("Aplicando correções...")
        self._append_log("Iniciando correções reais...")

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
            self._append_log("Instalando PJe Office Pro...")
            self.fix_worker = PJeOfficeWorker()
            self.fix_worker.finished.connect(self._on_fix_finished)
            self.fix_worker.start()
            self.pje_office_timer.start()
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
            validated = PJeOfficeWindows().is_installed()

            if install_ok and validated:
                result = {"status": "installed", "message": "PJe Office instalado com sucesso."}
                self._append_log("PJe Office instalado com sucesso.")
                self.progress.setRange(0, 100)
                self.progress.setValue(100)
                self.progress.setFormat("PJe Office instalado com sucesso.")
            elif install_ok and not validated:
                result = {"status": "error", "message": "Falha ao validar instalação do PJe Office."}

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

    def _finalize_fix(self, worker_result: dict | None):
        if self.pje_office_timer.isActive():
            self.pje_office_timer.stop()
        self.waiting_pje_office_install = False

        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setFormat("Aplicando correções... %p%")

        fixed_results = {}
        order = ["token", "driver", "pje_office", "browser"]

        for component in order:
            data = self.last_results.get(component, {"status": False, "message": "Componente nao encontrado"})
            status = bool(data.get("status"))

            if component == "pje_office" and not status:
                result = worker_result or {
                    "status": "error",
                    "message": "Falha ao obter resultado da instalação.",
                }
                fixed_results[component] = {
                    "status": result.get("status") in ("installed", "updated", "up_to_date"),
                    "message": result.get("message"),
                }
                continue

            if component == "driver" and not status:
                self._append_log("Instalando driver do token...")
                token_details = self.last_results.get("token", {}).get("details", {})
                install_result = install_missing_token_driver(token_details)
                if install_result.get("status") == "ok":
                    self._append_log("[OK] Driver do token instalado. Reexecutando diagnóstico...")
                    rescanned = self.scanner.run_full_scan()
                    fixed_results["token"] = rescanned.get("token", self.last_results.get("token", {}))
                    fixed_results["driver"] = rescanned.get("driver", data)
                else:
                    fixed_results[component] = {
                        "status": False,
                        "message": install_result.get("message", "Falha ao instalar driver do token"),
                    }
                continue

            if component == "browser" and not status:
                self.logger.info("BROWSER_FIX_STARTED", extra={"event": "BROWSER_FIX_STARTED"})
                browser_result = run_browser_fix(launch_browser=False)
                browser_ok = browser_result.get("status") == "ok"
                self.logger.info(
                    "BROWSER_FIX_COMPLETED",
                    extra={"event": "BROWSER_FIX_COMPLETED", "success": browser_ok},
                )
                fixed_results[component] = {
                    "status": browser_ok,
                    "message": "Correções de navegador aplicadas" if browser_ok else "Falha ao corrigir navegador",
                }
                continue

            fixed_results[component] = data

        self.last_results = fixed_results
        self._render_cards(fixed_results)

        for index, component in enumerate(order, start=1):
            data = fixed_results.get(component, {"status": False, "message": "Componente nao encontrado"})
            msg = self._extract_display_message(component, data)
            ok = bool(data.get("status"))
            prefix = "[OK]" if ok else "[ERRO]"
            color = "#3fb950" if ok else "#f85149"
            self._append_log(f'<span style="color:{color}">{prefix} {component.upper()} - {msg}</span>')
            self.progress.setValue(int((index / len(order)) * 100))
            QApplication.processEvents()

        self._append_log("Correções concluídas.")
        self.progress.setFormat("Correções concluídas")
        self._set_busy_ui(False)

        pje_status = bool(fixed_results.get("pje_office", {}).get("status"))
        if not pje_status:
            self._append_log("[ERRO] PJeOffice não está instalado. Chrome não será aberto.")
            return

        self._append_log("[INFO] Iniciando PJeOffice Pro...")
        windows = PJeOfficeWindows()
        if windows.start_if_needed(wait_seconds=3):
            self._append_log("[OK] PJeOffice iniciado.")
            open_result = open_chrome()
            if open_result.get("status") == "ok":
                self._append_log("[OK] Chrome aberto na página inicial do PJe.")
            else:
                self._append_log(f"[ERRO] {open_result.get('message')}")
            return

        self._append_log("[ERRO] Não foi possível iniciar o PJeOffice. Chrome não será aberto.")
