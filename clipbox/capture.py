"""Captura de região, clipboard e OCR."""

from __future__ import annotations

from io import BytesIO

from PIL import Image
from PyQt6.QtCore import QBuffer, QIODevice, QMimeData
from PyQt6.QtGui import QGuiApplication, QImage, QPixmap
from PyQt6.QtWidgets import QApplication

from clipbox.language import normalize_text

_ocr = None


def qpixmap_to_pil(pixmap: QPixmap) -> Image.Image:
    qimage = pixmap.toImage().convertToFormat(QImage.Format.Format_RGBA8888)
    buffer = QBuffer()
    buffer.open(QIODevice.OpenModeFlag.WriteOnly)
    qimage.save(buffer, "PNG")
    return Image.open(BytesIO(bytes(buffer.data()))).convert("RGB")


def pil_to_qimage(image: Image.Image) -> QImage:
    rgb = image.convert("RGBA")
    data = rgb.tobytes("raw", "RGBA")
    qimage = QImage(data, rgb.width, rgb.height, QImage.Format.Format_RGBA8888)
    return qimage.copy()


def copy_image_and_text(image: Image.Image, text: str) -> None:
    clipboard = QApplication.clipboard()
    mime = QMimeData()
    mime.setImageData(pil_to_qimage(image))
    if text:
        mime.setText(text)
    clipboard.setMimeData(mime)


def copy_text(text: str) -> None:
    QApplication.clipboard().setText(text)


def grab_region(left: int, top: int, width: int, height: int) -> Image.Image:
    """Captura pixels reais da área virtual (multi-monitor)."""
    import mss

    if width < 2 or height < 2:
        raise ValueError("A região selecionada é pequena demais.")

    with mss.mss() as sct:
        raw = sct.grab({"left": left, "top": top, "width": width, "height": height})
        return Image.frombytes("RGB", raw.size, raw.bgra, "raw", "BGRX")


def virtual_desktop_rect() -> tuple[int, int, int, int]:
    geo = QGuiApplication.primaryScreen().virtualGeometry()
    return geo.x(), geo.y(), geo.width(), geo.height()


def get_ocr():
    global _ocr
    if _ocr is None:
        from rapidocr import RapidOCR

        _ocr = RapidOCR()
    return _ocr


def extract_text(image: Image.Image) -> str:
    engine = get_ocr()
    result = engine(image)
    if result is None:
        return ""

    text = getattr(result, "txts", None)
    if text:
        lines = [str(item).strip() for item in text if str(item).strip()]
        return normalize_text("\n".join(lines))

    if isinstance(result, (list, tuple)) and result:
        first = result[0]
        if isinstance(first, str):
            return normalize_text(first)
        lines: list[str] = []
        for item in first if isinstance(first, list) else result:
            if isinstance(item, str) and item.strip():
                lines.append(item.strip())
            elif isinstance(item, (list, tuple)) and len(item) >= 2:
                value = item[1]
                if isinstance(value, (list, tuple)):
                    value = value[0]
                if str(value).strip():
                    lines.append(str(value).strip())
        return normalize_text("\n".join(lines))
    return ""
