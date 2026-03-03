import sys
from PySide6.QtWidgets import QApplication
from app.ui.main_window import MainWindow
from app.utils.logger import get_logger


def main():
    logger = get_logger()
    logger.info("application_started", extra={"event": "application_started"})
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
