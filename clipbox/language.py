"""Detecção de idioma, tradução e leitura em voz."""

from __future__ import annotations

import re

from langdetect import DetectorFactory, detect, lang_detect_exception
from deep_translator import GoogleTranslator, MyMemoryTranslator

DetectorFactory.seed = 0

LANGUAGE_CHOICES: list[tuple[str, str]] = [
    ("pt", "Português"),
    ("en", "Inglês"),
    ("es", "Espanhol"),
    ("fr", "Francês"),
    ("de", "Alemão"),
    ("it", "Italiano"),
    ("ja", "Japonês"),
    ("ko", "Coreano"),
    ("zh-CN", "Chinês (simplificado)"),
    ("ru", "Russo"),
]

CODE_TO_LABEL = {code: label for code, label in LANGUAGE_CHOICES}

LANGDETECT_MAP = {
    "pt": "pt",
    "en": "en",
    "es": "es",
    "fr": "fr",
    "de": "de",
    "it": "it",
    "ja": "ja",
    "ko": "ko",
    "zh-cn": "zh-CN",
    "zh": "zh-CN",
    "ru": "ru",
}


GOOGLE_CHUNK = 4500
MYMEMORY_CHUNK = 450


def normalize_text(text: str) -> str:
    cleaned = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = [re.sub(r"\s+", " ", line).strip() for line in cleaned.split("\n")]
    return "\n".join(line for line in lines if line)


def detect_language(text: str) -> tuple[str, str]:
    sample = " ".join(normalize_text(text).split())
    if len(sample) < 8:
        return "und", "Indeterminado"
    try:
        code = detect(sample)
    except lang_detect_exception.LangDetectException:
        return "und", "Indeterminado"
    mapped = LANGDETECT_MAP.get(code.lower(), code)
    return mapped, CODE_TO_LABEL.get(mapped, mapped)


MYMEMORY_NAMES = {
    "en": "english",
    "pt": "portuguese brazil",
    "es": "spanish",
    "fr": "french",
    "de": "german",
    "it": "italian",
    "ja": "japanese",
    "ko": "korean",
    "zh-CN": "chinese simplified",
    "ru": "russian",
}


def translate_text(text: str, source: str, target: str) -> str:
    cleaned = normalize_text(text)
    if not cleaned:
        return ""
    src = "auto" if source in {"und", "", "auto"} else source
    if src == target:
        return cleaned
    translated: list[str] = []
    last_error = ""
    for piece in _batch_chunks(cleaned, GOOGLE_CHUNK):
        try:
            translated.append(_translate_google(piece, src, target))
            continue
        except Exception as exc:  # noqa: BLE001
            last_error = _short_error(exc)
        try:
            parts = [
                _translate_mymemory(small, src, target)
                for small in _batch_chunks(piece, MYMEMORY_CHUNK)
            ]
            translated.append("\n".join(part for part in parts if part.strip()))
        except Exception as exc:  # noqa: BLE001
            raise RuntimeError(
                "Falha ao traduzir o texto (Google e MyMemory). "
                + _short_error(exc)
                + (f" | Google: {last_error}" if last_error else "")
            ) from exc
    return "\n".join(translated)


def _translate_google(piece: str, src: str, target: str) -> str:
    return GoogleTranslator(source=src, target=target).translate(piece)


def _translate_mymemory(piece: str, src: str, target: str) -> str:
    mm_src = MYMEMORY_NAMES.get(src, "english") if src != "auto" else "english"
    mm_tgt = MYMEMORY_NAMES.get(target, target)
    return MyMemoryTranslator(source=mm_src, target=mm_tgt).translate(piece)


def _batch_chunks(text: str, limit: int) -> list[str]:
    blocks: list[str] = []
    current = ""
    for line in normalize_text(text).split("\n"):
        candidate = line if not current else f"{current}\n{line}"
        if len(candidate) <= limit:
            current = candidate
            continue
        if current:
            blocks.append(current)
            current = ""
        if len(line) <= limit:
            current = line
        else:
            blocks.extend(_split_long(line, limit))
    if current:
        blocks.append(current)
    return [block for block in blocks if block.strip()]


def _split_long(text: str, limit: int) -> list[str]:
    parts: list[str] = []
    remaining = text
    while remaining:
        if len(remaining) <= limit:
            parts.append(remaining)
            break
        window = remaining[:limit]
        cut = max(window.rfind(". "), window.rfind("! "), window.rfind("? "), window.rfind(" "))
        if cut < limit // 3:
            cut = limit
        else:
            cut += 1
        parts.append(remaining[:cut].strip())
        remaining = remaining[cut:].strip()
    return [part for part in parts if part]


def _short_error(exc: Exception) -> str:
    message = str(exc).replace("\n", " ").strip()
    if len(message) > 180:
        message = message[:177] + "…"
    return message or type(exc).__name__


def speak_text(text: str, language_code: str | None = None) -> None:
    if not text.strip():
        return
    import pyttsx3

    engine = pyttsx3.init()
    voices = engine.getProperty("voices") or []
    chosen = _pick_voice(voices, language_code)
    if chosen is not None:
        engine.setProperty("voice", chosen)
    engine.setProperty("rate", 175)
    engine.say(text)
    engine.runAndWait()
    engine.stop()


def _pick_voice(voices, language_code: str | None):
    if not voices:
        return None
    needles = _voice_needles(language_code)
    for voice in voices:
        blob = " ".join(
            [
                str(getattr(voice, "id", "")),
                str(getattr(voice, "name", "")),
                " ".join(getattr(voice, "languages", []) or []),
            ]
        ).lower()
        if any(needle in blob for needle in needles):
            return voice.id
    return voices[0].id


def _voice_needles(language_code: str | None) -> list[str]:
    code = (language_code or "").lower()
    mapping = {
        "pt": ["pt-br", "portuguese", "helena", "daniel", "pt_br"],
        "en": ["en-us", "english", "zira", "david"],
        "es": ["spanish", "es-es", "sabina"],
        "fr": ["french", "hortense"],
        "de": ["german", "hedda"],
        "it": ["italian"],
        "ja": ["japanese", "haruka"],
        "ko": ["korean", "heami"],
        "zh-cn": ["chinese", "huihui", "zh-cn"],
        "ru": ["russian", "irina"],
    }
    return mapping.get(code, [code] if code else ["pt-br", "portuguese"])
