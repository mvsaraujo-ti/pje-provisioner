# -*- coding: utf-8 -*-
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout


class StatusCard(QFrame):
    OK = "ok"
    WARN = "warn"
    ERROR = "error"

    _STYLES = {
        OK: {"symbol": "✔", "color": "#3fb950"},
        WARN: {"symbol": "⚠", "color": "#d29922"},
        ERROR: {"symbol": "✖", "color": "#f85149"},
    }

    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        self._title_base = title
        self.setObjectName("statusCard")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(4)

        header_row = QHBoxLayout()
        header_row.setContentsMargins(0, 0, 0, 0)
        header_row.setSpacing(8)

        self.icon_label = QLabel("⚠")
        self.icon_label.setFixedWidth(18)
        self.icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.title_label = QLabel(title)
        self.title_label.setStyleSheet("font-size: 13px; font-weight: 700;")

        header_row.addWidget(self.icon_label)
        header_row.addWidget(self.title_label, 1)

        self.status_label = QLabel("Status: Aguardando diagnóstico...")
        self.status_label.setWordWrap(True)
        self.status_label.setStyleSheet("font-size: 12px;")

        layout.addLayout(header_row)
        layout.addWidget(self.status_label)

        self.set_state(self.WARN, "Aguardando diagnóstico...")

    def set_state(self, state: str, text: str) -> None:
        style = self._STYLES.get(state, self._STYLES[self.ERROR])
        symbol = style["symbol"]
        color = style["color"]

        self.icon_label.setText(symbol)
        self.title_label.setText(self._title_base)
        self.title_label.setStyleSheet(
            f"font-size: 13px; font-weight: 700; color: {color};"
        )
        self.status_label.setText(f"Status: {text}")
        self.status_label.setStyleSheet("font-size: 12px; color: #e8e8e8;")
        self.setStyleSheet(
            "QFrame#statusCard {"
            "background-color: #2b2b2b;"
            f"border: 1px solid {color};"
            "border-radius: 8px;"
            "}"
        )
