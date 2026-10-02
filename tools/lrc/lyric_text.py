"""Lyric lines from a lyric file: plain text (one lyric line per row) or SRT subtitles (the cue text, times dropped)."""

import re
import unicodedata
from pathlib import Path

SRT_TIME = re.compile(r"^\d+:\d+:\d+[,.]\d+\s*-->")
MARKUP = re.compile(r"<[^>]+>|\{[^}]*\}")  # <i>, <font ...>, {\an8}
NOT_LYRIC = re.compile(r"^[\s♪♫#*]*(\[[^\]]*\])?[\s♪♫#*]*$")  # ♪ or [Music] alone on a row; (backing vocals) stay


def read_lyric_lines(path: Path) -> list[str]:
    rows = path.read_text(encoding="utf-8-sig").splitlines()
    if path.suffix.lower() == ".srt":
        rows = [MARKUP.sub("", r) for r in rows if not r.strip().isdigit() and not SRT_TIME.match(r.strip())]
        rows = [r.strip(" ♪♫") for r in rows if not NOT_LYRIC.match(r)]
    return [unicodedata.normalize("NFC", r.strip()) for r in rows if r.strip()]
