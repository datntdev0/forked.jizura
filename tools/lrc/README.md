# LRC tools

Make a timed LRC for JIZURA (歌詞 → LRC を読み込む) from a song and its lyrics.

1. **Word times** — `match_lyric.py` aligns the lyric text to the audio (Whisper via stable-ts) and writes one word per row:

   ```
   pip install -r requirements.txt        # needs ffmpeg on PATH; --demucs also needs: pip install demucs
   python match_lyric.py song.mp3 song.lyrics.txt --language vi --model large-v3
   ```

2. **Phrases** — one word per row is too fine for a lyric video. `phrase_lrc.py` groups the words into phrase rows:

   ```
   python phrase_lrc.py song.lrc --draft song.phrases.txt --lyrics song.lyrics.txt
   # edit song.phrases.txt: one phrase per row, same words in the same order
   python phrase_lrc.py song.lrc --phrases song.phrases.txt -o song.phrased.lrc
   ```

   Each phrase row starts at its first word; `[interlude]` rows are kept. A warning lists phrases whose words the
   aligner squeezed together (no real timing): check their start time by ear.

The `lrc-phrasing` skill (`.claude/skills/`, `.agents/skills/`) runs step 2 with an agent choosing the breaks.
