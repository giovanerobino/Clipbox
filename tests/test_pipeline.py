"""Testes do pipeline OCR / idioma / tradução sem UI."""

from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image, ImageDraw, ImageFont

from clipbox.capture import extract_text, pil_to_qimage, qpixmap_to_pil
from clipbox.language import detect_language, normalize_text, translate_text, _batch_chunks, MYMEMORY_CHUNK


def _font(size: int = 42):
    for name in ("arial.ttf", "segoeui.ttf", "C:\\Windows\\Fonts\\arial.ttf"):
        path = Path(name)
        if path.exists():
            return ImageFont.truetype(str(path), size)
    return ImageFont.load_default()


def make_text_image(text: str, size=(720, 160)) -> Image.Image:
    image = Image.new("RGB", size, "#ffffff")
    draw = ImageDraw.Draw(image)
    draw.text((24, 40), text, fill="#111111", font=_font())
    return image


def test_ocr_reads_generated_english():
    image = make_text_image("HELLO CLIPBOX")
    text = extract_text(image).upper()
    assert "HELLO" in text
    assert "CLIPBOX" in text


def test_detect_english():
    code, label = detect_language("This screenshot contains readable English words.")
    assert code == "en"
    assert "Inglês" in label


def test_detect_portuguese():
    code, label = detect_language("Este texto em portugues deve ser identificado corretamente agora.")
    assert code == "pt"
    assert "Português" in label


def test_translate_en_to_pt():
    translated = translate_text("hello world", "en", "pt").lower()
    normalized = translated.replace("á", "a").replace("-", " ")
    assert "ola" in normalized or "mundo" in normalized


def test_normalize_drops_empty_lines():
    cleaned = normalize_text("hello\n\n\nworld\n  \nnext")
    assert cleaned == "hello\nworld\nnext"


def test_long_text_is_split_for_mymemory(monkeypatch):
    lore = (
        "Do you, too, seek the power of the deep? It has been many eons since I first wove "
        "the theory of enchantments, an art still practiced to this day. And now, it seems "
        "you are next in line to walk this path. May your fate be better than the Nitwits "
        "who failed to control the deep and turned this realm to stone.\n\n"
        "To claim your World Engine Upgrade, you must follow my instructions carefully, "
        "lest the deep consume you. Begin by delving into the depths of the world, where "
        "a dark and ancient power lingers. Within its lair, you may uncover Echo Shards "
        "that carry the essence of the deep.\n\n"
        "Alternatively, you may encounter a certain explorer who has returned with Echo "
        "Shards of his own. Completing the Wayfinder's task should persuade him to trade "
        "some, if you, like many others, prefer to avoid the dangers of the deep."
    )
    chunks = _batch_chunks(lore, MYMEMORY_CHUNK)
    assert all(len(chunk) <= MYMEMORY_CHUNK for chunk in chunks)
    assert len(chunks) >= 2

    def fail_google(*_args, **_kwargs):
        raise RuntimeError("quota")

    monkeypatch.setattr("clipbox.language._translate_google", fail_google)
    translated = translate_text(lore, "en", "pt").lower()
    assert any(word in translated for word in ("profundo", "poder", "mundo", "eco", "profundezas"))


def test_pil_qimage_roundtrip():
    from PyQt6.QtGui import QPixmap
    from PyQt6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication([])
    image = Image.new("RGB", (12, 8), "#336699")
    qimage = pil_to_qimage(image)
    pixmap = QPixmap.fromImage(qimage)
    back = qpixmap_to_pil(pixmap)
    assert back.size == (12, 8)
    del app
