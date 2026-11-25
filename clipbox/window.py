"""Janela de resultado: texto, idioma, tradução e TTS."""

from __future__ import annotations

from pathlib import Path

from PIL import Image
from PyQt6.QtCore import QObject, QRunnable, QSize, Qt, QThreadPool, pyqtSignal
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from clipbox.capture import copy_image_and_text, copy_text, extract_text, pil_to_qimage
from clipbox.language import LANGUAGE_CHOICES, detect_language, normalize_text, speak_text, translate_text
from clipbox.styles import APP_QSS


class WorkerSignals(QObject):
    done = pyqtSignal(object)
    failed = pyqtSignal(str)


class Worker(QRunnable):
    def __init__(self, fn, *args):
        super().__init__()
        self.fn = fn
        self.args = args
        self.signals = WorkerSignals()

    def run(self) -> None:
        try:
            self.signals.done.emit(self.fn(*self.args))
        except Exception as exc:  # noqa: BLE001
            self.signals.failed.emit(str(exc))


class ResultWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Clipbox")
        self.resize(920, 720)
        self.setStyleSheet(APP_QSS)
        self.image: Image.Image | None = None
        self.source_lang = "und"
        self.pool = QThreadPool.globalInstance()

        root = QWidget()
        layout = QVBoxLayout(root)
        layout.setContentsMargins(18, 18, 18, 12)
        layout.setSpacing(12)

        title = QLabel("Clipbox")
        title.setObjectName("title")
        hint = QLabel("Ctrl+T recorta a tela. A imagem e o texto vão para o clipboard.")
        hint.setObjectName("hint")
        layout.addWidget(title)
        layout.addWidget(hint)

        self.preview = QLabel("Nenhuma captura ainda")
        self.preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview.setMinimumHeight(180)
        self.preview.setStyleSheet(
            "background:#0e1014; border:1px solid #2c313c; border-radius:12px; color:#9aa0a6;"
        )
        layout.addWidget(self.preview)

        card = QFrame()
        card.setObjectName("card")
        card_layout = QVBoxLayout(card)
        self.meta = QLabel("Idioma: —")
        self.meta.setObjectName("meta")
        card_layout.addWidget(self.meta)
        self.raw_edit = QPlainTextEdit()
        self.raw_edit.setPlaceholderText("Texto extraído da captura…")
        card_layout.addWidget(self.raw_edit)
        layout.addWidget(card, 1)

        row = QHBoxLayout()
        row.addWidget(QLabel("Traduzir para"))
        self.target = QComboBox()
        for code, label in LANGUAGE_CHOICES:
            self.target.addItem(label, code)
        self.target.setCurrentIndex(0)
        row.addWidget(self.target, 1)
        self.translate_btn = QPushButton("Traduzir")
        self.translate_btn.setObjectName("primary")
        self.translate_btn.clicked.connect(self.translate_current)
        row.addWidget(self.translate_btn)
        layout.addLayout(row)

        self.translated_edit = QPlainTextEdit()
        self.translated_edit.setPlaceholderText("Texto traduzido…")
        layout.addWidget(self.translated_edit, 1)

        actions = QHBoxLayout()
        self.speak_raw_btn = QPushButton("Ler texto bruto")
        self.speak_tr_btn = QPushButton("Ler tradução")
        self.copy_raw_btn = QPushButton("Copiar texto")
        self.copy_tr_btn = QPushButton("Copiar tradução")
        self.save_btn = QPushButton("Salvar .txt")
        self.speak_raw_btn.clicked.connect(lambda: self._speak(self.raw_edit.toPlainText(), self.source_lang))
        self.speak_tr_btn.clicked.connect(
            lambda: self._speak(self.translated_edit.toPlainText(), self.target.currentData())
        )
        self.copy_raw_btn.clicked.connect(lambda: self._copy_field(self.raw_edit.toPlainText(), "Texto copiado"))
        self.copy_tr_btn.clicked.connect(
            lambda: self._copy_field(self.translated_edit.toPlainText(), "Tradução copiada")
        )
        self.save_btn.clicked.connect(self.save_txt)
        for btn in (
            self.speak_raw_btn,
            self.speak_tr_btn,
            self.copy_raw_btn,
            self.copy_tr_btn,
            self.save_btn,
        ):
            actions.addWidget(btn)
        layout.addLayout(actions)

        self.setCentralWidget(root)
        bar = QStatusBar()
        self.setStatusBar(bar)
        bar.showMessage("Aguardando Ctrl+T")

    def load_capture(self, image: Image.Image) -> None:
        self.image = image
        pixmap = QPixmap.fromImage(pil_to_qimage(image)).scaled(
            QSize(860, 220),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self.preview.setPixmap(pixmap)
        self.raw_edit.setPlainText("Lendo texto da captura…")
        self.translated_edit.clear()
        self.statusBar().showMessage("Imagem no clipboard. Extraindo texto…")
        copy_image_and_text(image, "")
        worker = Worker(self._ocr_and_detect, image)
        worker.signals.done.connect(self._on_ocr)
        worker.signals.failed.connect(self._on_fail)
        self.pool.start(worker)

    def _ocr_and_detect(self, image: Image.Image) -> dict:
        text = extract_text(image)
        code, label = detect_language(text)
        return {"text": text, "code": code, "label": label}

    def _on_ocr(self, payload: object) -> None:
        data = payload if isinstance(payload, dict) else {}
        text = normalize_text(str(data.get("text") or ""))
        self.source_lang = str(data.get("code") or "und")
        label = str(data.get("label") or "Indeterminado")
        self.raw_edit.setPlainText(text)
        self.meta.setText(f"Idioma detectado: {label} ({self.source_lang})")
        if self.image is not None:
            copy_image_and_text(self.image, text)
        if text:
            self.statusBar().showMessage("Imagem e texto no clipboard — prontos para colar no .txt")
        else:
            self.statusBar().showMessage("Imagem no clipboard. Nenhum texto reconhecido.")

    def translate_current(self) -> None:
        text = normalize_text(self.raw_edit.toPlainText())
        if not text:
            QMessageBox.information(self, "Clipbox", "Não há texto para traduzir.")
            return
        self.raw_edit.setPlainText(text)
        target = self.target.currentData()
        self.translate_btn.setEnabled(False)
        self.statusBar().showMessage("Traduzindo…")
        worker = Worker(translate_text, text, self.source_lang, target)
        worker.signals.done.connect(self._on_translated)
        worker.signals.failed.connect(self._on_fail)
        self.pool.start(worker)

    def _on_translated(self, payload: object) -> None:
        self.translate_btn.setEnabled(True)
        self.translated_edit.setPlainText(str(payload or ""))
        self.statusBar().showMessage("Tradução pronta")

    def _speak(self, text: str, lang: str | None) -> None:
        if not text.strip():
            QMessageBox.information(self, "Clipbox", "Não há texto para ler.")
            return
        self.statusBar().showMessage("Lendo texto…")
        worker = Worker(speak_text, text, lang)
        worker.signals.done.connect(lambda _=None: self.statusBar().showMessage("Leitura concluída"))
        worker.signals.failed.connect(self._on_fail)
        self.pool.start(worker)

    def _copy_field(self, text: str, ok_message: str) -> None:
        copy_text(text)
        self.statusBar().showMessage(ok_message)

    def save_txt(self) -> None:
        raw = self.raw_edit.toPlainText().strip()
        translated = self.translated_edit.toPlainText().strip()
        if not raw and not translated:
            QMessageBox.information(self, "Clipbox", "Não há texto para salvar.")
            return
        path, _ = QFileDialog.getSaveFileName(self, "Salvar texto", "clipbox.txt", "Texto (*.txt)")
        if not path:
            return
        parts = ["=== Texto bruto ===", raw]
        if translated:
            parts.extend(["", "=== Tradução ===", translated])
        Path(path).write_text("\n".join(parts), encoding="utf-8")
        self.statusBar().showMessage(f"Salvo em {path}")

    def _on_fail(self, message: str) -> None:
        self.translate_btn.setEnabled(True)
        self.statusBar().showMessage("Erro")
        QMessageBox.warning(self, "Clipbox", message[:600])
