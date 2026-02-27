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
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor

from core.scanner import SystemScanner
from utils.logger import get_logger


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("PJE Provisioner")
        self.setMinimumSize(700, 500)

        self.scanner = SystemScanner()
        self.last_results = {}
        self.logger = get_logger()

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
        self.progress.setValue(0)
        self.progress.setFormat("Aplicando correções... %p%")
        self.log_area.append("Iniciando correções simuladas...\n")

        fixed_results = self.scanner.run_simulated_fixes(self.last_results)
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
        self.log_area.append("\nCorreções simuladas concluídas.\n")
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
