"""Overlay de recorte em tela cheia (Ctrl+T)."""

from __future__ import annotations

from PyQt6.QtCore import QPoint, QRect, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QGuiApplication, QPainter, QPen
from PyQt6.QtWidgets import QWidget


class SnipOverlay(QWidget):
    captured = pyqtSignal(int, int, int, int)
    cancelled = pyqtSignal()

    def __init__(self) -> None:
        super().__init__(None)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setCursor(Qt.CursorShape.CrossCursor)
        self._origin: QPoint | None = None
        self._current: QPoint | None = None
        geo = QGuiApplication.primaryScreen().virtualGeometry()
        self.setGeometry(geo)

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self.grabKeyboard()

    def hideEvent(self, event) -> None:
        self.releaseKeyboard()
        super().hideEvent(event)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._origin = event.globalPosition().toPoint()
            self._current = self._origin
            self.update()

    def mouseMoveEvent(self, event) -> None:
        if self._origin is not None:
            self._current = event.globalPosition().toPoint()
            self.update()

    def mouseReleaseEvent(self, event) -> None:
        if event.button() != Qt.MouseButton.LeftButton or self._origin is None:
            return
        self._current = event.globalPosition().toPoint()
        rect = QRect(self._origin, self._current).normalized()
        self._origin = None
        self._current = None
        self.hide()
        if rect.width() < 4 or rect.height() < 4:
            self.cancelled.emit()
            return
        dpr = QGuiApplication.primaryScreen().devicePixelRatio()
        left = int(rect.x() * dpr)
        top = int(rect.y() * dpr)
        width = max(1, int(rect.width() * dpr))
        height = max(1, int(rect.height() * dpr))
        self.captured.emit(left, top, width, height)

    def keyPressEvent(self, event) -> None:
        if event.key() == Qt.Key.Key_Escape:
            self.hide()
            self.cancelled.emit()

    def paintEvent(self, _event) -> None:
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(8, 10, 14, 120))
        if self._origin is None or self._current is None:
            painter.setPen(QColor("#e8eaed"))
            painter.drawText(
                self.rect().adjusted(24, 24, -24, -24),
                Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft,
                "Arraste para criar a box  •  Esc cancela  •  Clipbox",
            )
            return

        local_origin = self.mapFromGlobal(self._origin)
        local_current = self.mapFromGlobal(self._current)
        box = QRect(local_origin, local_current).normalized()
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Clear)
        painter.fillRect(box, Qt.GlobalColor.transparent)
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
        painter.setPen(QPen(QColor("#5b8cff"), 2))
        painter.drawRect(box.adjusted(0, 0, -1, -1))
        painter.setPen(QColor("#e8eaed"))
        painter.drawText(
            box.left(),
            max(18, box.top() - 8),
            f"{box.width()} × {box.height()}",
        )
