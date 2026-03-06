# -*- coding: utf-8 -*-
import ctypes
import os
import sys

from PySide6.QtWidgets import QApplication

from app.ui.main_window import MainWindow
from app.utils.logger import get_logger

os.environ.setdefault("PYTHONUTF8", "1")
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")


def main():
    logger = get_logger()
    logger.info("application_started", extra={"event": "application_started"})

    if sys.platform == "win32":
        elevated_flag = "--elevated"
        has_elevated_flag = elevated_flag in sys.argv
        is_admin = bool(ctypes.windll.shell32.IsUserAnAdmin())
        if not is_admin and not has_elevated_flag:
            logger.info(
                "application_elevation_requested",
                extra={"event": "application_elevation_requested"},
            )
            result = ctypes.windll.shell32.ShellExecuteW(
                None,
                "runas",
                sys.executable,
                "-m app.main --elevated",
                None,
                1,
            )
            if result <= 32:
                logger.error(
                    "application_elevation_failed",
                    extra={
                        "event": "application_elevation_failed",
                        "shell_execute_code": int(result),
                    },
                )
                sys.exit(1)
            sys.exit(0)

    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    exit_code = app.exec()
    logger.info(
        "application_finished",
        extra={"event": "application_finished", "exit_code": exit_code},
    )
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
