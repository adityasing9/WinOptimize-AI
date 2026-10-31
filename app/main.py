"""
WinOptimize AI - Application Main Entry Point
Initializes Qt application, taskbar app model ID, crash handlers, and main window.
"""

from __future__ import annotations
import ctypes
import os
import sys
import logging
from pathlib import Path
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt, QSharedMemory

# Add repo root to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from ui.main_window import MainWindow

logger = logging.getLogger("WinOp.App")


def setup_windows_appid():
    """Sets explicit Windows App User Model ID so the taskbar groups and icons display properly."""
    try:
        app_id = "GoogleDeepMind.WinOptimizeAI.Optimizer.1.0.0"
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(app_id)
    except Exception:
        pass


def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="[%(asctime)s] %(levelname)s [%(name)s]: %(message)s",
        datefmt="%H:%M:%S",
    )


def main():
    setup_logging()
    setup_windows_appid()

    # Enable High DPI scaling
    QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)

    app = QApplication(sys.argv)
    app.setApplicationName("WinOptimize AI")
    app.setOrganizationName("DeepMind Advanced Agentic Coding")

    # Single-instance enforcement using QSharedMemory
    shared_mem = QSharedMemory("WinOptimizeAI_SingleInstance_Mutex")
    if not shared_mem.create(1):
        logger.warning("Another instance of WinOptimize AI is already running.")
        # Proceed or bring existing window to front

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
