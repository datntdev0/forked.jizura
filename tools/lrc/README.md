# LRC tools

Make a timed LRC for JIZURA (歌詞 → LRC を読み込む) from a song and its lyrics.
The lyrics can be plain text (one lyric line per row) or an `.srt` (only its text is used).

1. **Word times** — `match_lyric.py` aligns the lyrics to the audio (Whisper via stable-ts) and writes one word per row:

   ```
   pip install -r requirements.txt        # needs ffmpeg on PATH; --demucs also needs: pip install demucs
   python match_lyric.py song.mp3 song.srt --language vi -o song.lrc
   ```

2. **Phrases** — one word per row is too fine for a lyric video. `phrase_lrc.py` groups the words into phrase rows:

   ```
   python phrase_lrc.py song.lrc --draft song.phrases.txt --lyrics song.srt
   # edit song.phrases.txt: one phrase per row, same words in the same order
   python phrase_lrc.py song.lrc --phrases song.phrases.txt -o song.phrase.lrc
   ```

   Each phrase row starts at its first word; `[interlude]` rows are kept. Warnings list rows on screen under 1 s,
   rows sung for 2.5 s or more, rows over 6 words (`--min-secs`, `--max-secs`, `--max-words`), and phrases whose
   words the aligner squeezed together (no real timing: check their start time by ear).

The Codex skill `preprocess` (`.agents/skills/preprocess/`) runs both steps for a folder with an mp3 and an srt,
with the agent choosing the phrase breaks.
