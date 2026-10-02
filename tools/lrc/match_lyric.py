"""Align a lyric text file to an audio file and write a timed LRC file.

Usage:
    python match_lyric.py song.mp3 lyric.txt
    python match_lyric.py song.mp3 lyric.txt -o song.lrc --model large-v3 --language vi

Output, one word per row ([interlude] marks long gaps without singing):
    [00:00.00][interlude]
    [00:10.76]First
    [00:11.20]lyric
    [00:11.60]line
"""

import argparse
from pathlib import Path

import stable_whisper
import torch
import whisper


def default_device() -> str:
    # torch.cuda.is_available() can be True for GPUs the installed build has no kernels for (e.g. old Pascal cards).
    if not torch.cuda.is_available():
        return "cpu"
    major, minor = torch.cuda.get_device_capability()
    return "cuda" if f"sm_{major}{minor}" in torch.cuda.get_arch_list() else "cpu"


def format_time(seconds: float) -> str:
    minutes, secs = divmod(max(seconds, 0.0), 60)
    return f"{int(minutes):02d}:{secs:05.2f}"


def read_lyric(path: Path) -> str:
    lines = [line.strip() for line in path.read_text(encoding="utf-8").splitlines()]
    return "\n".join(line for line in lines if line)


def align_lyric(audio, lyric: str, model_name: str, device: str, language: str | None, use_demucs: bool):
    model = stable_whisper.load_model(model_name, device=device)
    options = {"denoiser": "demucs"} if use_demucs else {}
    return model.align(audio, lyric, language=language, original_split=True, **options)


def to_lrc_lines(segment) -> list[str]:
    return [f"[{format_time(word.start)}]{word.word.strip()}" for word in segment.words if word.word.strip()]


def pull_back_late_words(segment, max_gap: float):
    # Alignment often pushes a line's last word across an instrumental break to just before the next line.
    # A word cannot pause that long inside one line, so move it right after the previous word.
    for previous, word in zip(segment.words, segment.words[1:]):
        if word.start - previous.end >= max_gap:
            duration = word.end - word.start
            word.start, word.end = previous.end, previous.end + duration


def build_lrc(segments, interlude_gap: float, audio_duration: float) -> list[str]:
    lrc_lines = []
    previous_end = 0.0

    def add_interlude_if_gap(next_start: float):
        if next_start - previous_end >= interlude_gap:
            lrc_lines.append(f"[{format_time(previous_end)}][interlude]")

    for segment in segments:
        pull_back_late_words(segment, interlude_gap)
        add_interlude_if_gap(segment.start)
        lrc_lines.extend(to_lrc_lines(segment))
        previous_end = segment.end
    add_interlude_if_gap(audio_duration)
    return lrc_lines


def main():
    parser = argparse.ArgumentParser(description="Create a timed LRC file from lyric text + audio.")
    parser.add_argument("audio", type=Path, help="Audio file (mp3, wav, ...)")
    parser.add_argument("lyric", type=Path, help="Lyric text file (UTF-8, one line per lyric line)")
    parser.add_argument("-o", "--output", type=Path, help="Output .lrc file (default: next to the audio file)")
    parser.add_argument("--model", default="medium", help="Whisper model: tiny, base, small, medium, large-v3, ...")
    parser.add_argument("--device", default=default_device(), help="cuda or cpu (default: cuda if supported)")
    parser.add_argument("--language", help="Lyric language code, e.g. vi, en (auto-detect if omitted)")
    parser.add_argument("--demucs", action="store_true", help="Isolate vocals with Demucs first (pip install demucs)")
    parser.add_argument("--interlude-gap", type=float, default=5.0,
                        help="Insert [interlude] when the gap between lines is at least this many seconds")
    args = parser.parse_args()

    audio = whisper.load_audio(str(args.audio))
    audio_duration = len(audio) / whisper.audio.SAMPLE_RATE
    lyric = read_lyric(args.lyric)
    result = align_lyric(audio, lyric, args.model, args.device, args.language, args.demucs)
    segments = [segment for segment in result.segments if segment.text.strip()]
    lrc_lines = build_lrc(segments, args.interlude_gap, audio_duration)

    output = args.output or args.audio.with_suffix(".lrc")
    output.write_text("\n".join(lrc_lines) + "\n", encoding="utf-8")
    print(f"Wrote {len(lrc_lines)} lines to {output}")


if __name__ == "__main__":
    main()
