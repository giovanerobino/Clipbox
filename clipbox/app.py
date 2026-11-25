"""Aplicativo Clipbox: atalho Ctrl+T, bandeja e janela de resultado."""

from __future__ import annotations

import sys
from threading import Thread

from PIL import Image
from pynput import keyboard
from PyQt6.QtCore import QObject, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QAction, QColor, QIcon, QPainter, QPixmap
from PyQt6.QtWidgets import QApplication, QMenu, QSystemTrayIcon

from clipbox.capture import grab_region
from clipbox.overlay import SnipOverlay
from clipbox.window import ResultWindow


class HotkeyBridge(QObject):
    triggered = pyqtSignal()


def make_icon() -> QIcon:
    pixmap = QPixmap(64, 64)
    pixmap.fill(QColor("#111318"))
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setBrush(QColor("#3d5afe"))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawRoundedRect(8, 8, 48, 48, 12, 12)
    painter.setPen(QColor("#ffffff"))
    painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, "Cb")
    painter.end()
    return QIcon(pixmap)


class ClipboxApp:
    def __init__(self) -> None:
        self.qt = QApplication.instance() or QApplication(sys.argv)
        self.qt.setQuitOnLastWindowClosed(False)
        self.qt.setApplicationName("Clipbox")
        self.window = ResultWindow()
        self.overlay = SnipOverlay()
        self.overlay.captured.connect(self._on_region)
        self.overlay.cancelled.connect(lambda: self.window.statusBar().showMessage("Captura cancelada"))
        self.bridge = HotkeyBridge()
        self.bridge.triggered.connect(self.start_snip)
        self._hotkey_listener = None
        self._setup_tray()
        self._setup_hotkey()

    def _setup_tray(self) -> None:
        self.tray = QSystemTrayIcon(make_icon())
        menu = QMenu()
        show = QAction("Abrir Clipbox")
        show.triggered.connect(self.window.show)
        snip = QAction("Nova box (Ctrl+T)")
        snip.triggered.connect(self.start_snip)
        quit_act = QAction("Sair")
        quit_act.triggered.connect(self.qt.quit)
        menu.addAction(show)
        menu.addAction(snip)
        menu.addSeparator()
        menu.addAction(quit_act)
        self.tray.setContextMenu(menu)
        self.tray.setToolTip("Clipbox — Ctrl+T para recortar")
        self.tray.show()
        self.tray.showMessage(
            "Clipbox",
            "Pressione Ctrl+T para criar uma box na tela.",
            QSystemTrayIcon.MessageIcon.Information,
            3500,
        )

    def _setup_hotkey(self) -> None:
        def listen() -> None:
            with keyboard.GlobalHotKeys({"<ctrl>+t": self.bridge.triggered.emit}) as listener:
                self._hotkey_listener = listener
                listener.join()

        Thread(target=listen, daemon=True).start()

    def start_snip(self) -> None:
        self.window.statusBar().showMessage("Selecione a região…")
        self.overlay.show()
        self.overlay.raise_()
        self.overlay.activateWindow()

    def _on_region(self, left: int, top: int, width: int, height: int) -> None:
        QTimer.singleShot(80, lambda: self._grab(left, top, width, height))

    def _grab(self, left: int, top: int, width: int, height: int) -> None:
        try:
            image: Image.Image = grab_region(left, top, width, height)
        except Exception as exc:  # noqa: BLE001
            self.window.show()
            self.window.statusBar().showMessage(f"Falha ao capturar: {exc}")
            return
        self.window.show()
        self.window.raise_()
        self.window.activateWindow()
        self.window.load_capture(image)

    def run(self) -> int:
        self.window.show()
        return self.qt.exec()


def main() -> None:
    sys.exit(ClipboxApp().run())


if __name__ == "__main__":
    main()
