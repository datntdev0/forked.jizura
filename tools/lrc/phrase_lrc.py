"""Group a word-timed LRC (one word per row, e.g. from match_lyric.py) into phrase rows for JIZURA.

Two steps, so a person (or an agent) can decide where the phrases break:

    python phrase_lrc.py song.lrc --draft song.phrases.txt [--lyrics song.srt]
        writes a first guess, one phrase per row: lyric lines (from --lyrics: text or .srt, else a capital letter starts a line),
        lines longer than --max-words split at a comma; long lines left without one are listed for the editor

    (edit song.phrases.txt: move the breaks, but keep every word in the same order)

    python phrase_lrc.py song.lrc --phrases song.phrases.txt -o song.phrase.lrc
        each phrase row starts at the time of its first word; [interlude] rows are kept;
        stops when the phrases do not match the words, and warns about phrases the aligner squeezed together
"""

import argparse
import re
import sys
import unicodedata
from pathlib import Path

from lyric_text import read_lyric_lines

TIME_ROW = re.compile(r"^\[(\d+):(\d+(?:\.\d+)?)\](.*)$")
INTERLUDE = re.compile(r"^\[[^\]]*\]$")  # [interlude], [間奏 8], ... — no lyric text
SQUEEZED = 0.1  # seconds per word: below this the aligner had no real timing for the phrase


def nfc(text: str) -> str:
    return unicodedata.normalize("NFC", text)


def format_time(seconds: float) -> str:
    minutes, secs = divmod(max(seconds, 0.0), 60)
    return f"[{int(minutes):02d}:{secs:05.2f}]"


def read_words(path: Path) -> list[tuple[float, str]]:
    """(time, word) rows; an interlude row keeps its tag text, e.g. '[interlude]'."""
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        m = TIME_ROW.match(line.strip())
        if m and m[3].strip():
            rows.append((int(m[1]) * 60 + float(m[2]), nfc(m[3].strip())))
    return rows


def is_interlude(word: str) -> bool:
    return bool(INTERLUDE.match(word))


# ---------- draft ----------

def split_long(words: list[tuple[float, str]], max_words: int) -> list[list[tuple[float, str]]]:
    """Split a line longer than max_words after the comma nearest its middle, until no part has a comma left to cut.
    A long line without a comma stays whole: where it breaks depends on the meaning, which the editor decides."""
    if len(words) <= max_words:
        return [words]
    commas = [i for i in range(2, len(words) - 1) if words[i - 1][1].endswith((",", ";", ":"))]
    if not commas:
        return [words]
    cut = min(commas, key=lambda i: abs(i - len(words) / 2))
    return split_long(words[:cut], max_words) + split_long(words[cut:], max_words)


def lyric_lines(words: list[tuple[float, str]], lyrics: list[str] | None) -> list[list[tuple[float, str]]]:
    """The words cut into lyric lines: by the lyric file when given, else before every capitalized word."""
    lines, current = [], []
    sizes = iter(len(row.split()) for row in lyrics) if lyrics else None
    want = next(sizes, None) if sizes else None
    for word in words:
        if is_interlude(word[1]):
            continue
        if sizes is None and current and word[1][:1].isupper():
            lines.append(current); current = []
        current.append(word)
        if sizes is not None and len(current) == want:
            lines.append(current); current = []
            want = next(sizes, None)
    if current:
        lines.append(current)
    return lines


def write_rows(path: Path, rows: list[str]):
    path.write_text("\n".join(rows) + "\n", encoding="utf-8", newline="\n")


def write_draft(words, lyrics, max_words: int, output: Path):
    phrases = [part for line in lyric_lines(words, lyrics) for part in split_long(line, max_words)]
    write_rows(output, [" ".join(w for _, w in p) for p in phrases])
    print(f"Wrote {len(phrases)} phrases to {output}")
    for p in phrases:
        if len(p) > max_words:
            print(f"long ({len(p)} words): {format_time(p[0][0])}{' '.join(w for _, w in p)}")


# ---------- phrases -> LRC ----------

def build_lrc(words, phrases: list[str]) -> tuple[list[str], list[str]]:
    rows, warnings, i = [], [], 0
    for phrase in phrases:
        while i < len(words) and is_interlude(words[i][1]):
            rows.append(format_time(words[i][0]) + words[i][1]); i += 1
        tokens = phrase.split()
        got = [w for _, w in words[i:i + len(tokens)]]
        if got != tokens:
            at = format_time(words[i][0]) if i < len(words) else "the end"
            sys.exit(f"Phrase does not match the words at {at}:\n  phrase: {' '.join(tokens)}\n  words:  {' '.join(got)}")
        start, last = words[i][0], words[i + len(tokens) - 1][0]
        if len(tokens) > 1 and (last - start) / (len(tokens) - 1) < SQUEEZED:
            warnings.append(f"{format_time(start)}{phrase}  (all words within {last - start:.2f}s: check the start time)")
        rows.append(format_time(start) + phrase)
        i += len(tokens)
    rest = words[i:]
    if any(not is_interlude(w) for _, w in rest):
        sys.exit(f"Words left after the last phrase, from {format_time(rest[0][0])}: "
                 + " ".join([w for _, w in rest if not is_interlude(w)][:12]) + " ...")
    rows += [format_time(t) + w for t, w in rest]
    return rows, warnings


def main():
    parser = argparse.ArgumentParser(description="Group a word-timed LRC into phrase rows for JIZURA.")
    parser.add_argument("lrc", type=Path, help="Word-timed LRC (one word per row)")
    parser.add_argument("--draft", type=Path, help="Write a first phrase guess (one phrase per row) to this file")
    parser.add_argument("--lyrics", type=Path, help="Lyrics (text with one lyric line per row, or .srt), for the draft's line breaks")
    parser.add_argument("--max-words", type=int, default=7, help="Draft: split lines longer than this (default 7)")
    parser.add_argument("--phrases", type=Path, help="Phrase file (one phrase per row) to turn into the LRC")
    parser.add_argument("-o", "--output", type=Path, help="Output LRC (default: <lrc>.phrase.lrc)")
    args = parser.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

    words = read_words(args.lrc)
    if args.draft:
        write_draft(words, read_lyric_lines(args.lyrics) if args.lyrics else None, args.max_words, args.draft)
    if args.phrases:
        rows, warnings = build_lrc(words, read_lyric_lines(args.phrases))
        output = args.output or args.lrc.with_suffix(".phrase.lrc")
        write_rows(output, rows)
        print(f"Wrote {len(rows)} rows to {output}")
        for w in warnings:
            print("warning:", w)
    if not args.draft and not args.phrases:
        parser.error("give --draft and/or --phrases")


if __name__ == "__main__":
    main()
