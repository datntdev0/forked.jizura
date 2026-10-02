---
name: preprocess
description: Prepare a song for JIZURA from a folder with its audio (.mp3) and correct lyrics (.srt) - word-timed LRC by aligning the lyrics to the audio, then a .phrase.lrc whose rows are meaningful phrases for a lyric video. Use when the user gives a song folder / mp3 + srt and wants an LRC (timed lyrics) for JIZURA, or asks to preprocess / chuẩn bị / tạo LRC cho một bài hát.
---

# Preprocess a song for JIZURA

mp3 + correct lyrics (.srt) → `<song>.lrc` (one word per row, timed) → `<song>.phrase.lrc` (one phrase per row).
The tools are in `tools/lrc/` of this repo (see its README). All outputs go into the song folder.

## 1. The folder

- The user names the folder; ask when they have not.
- It needs one `.mp3` and one `.srt` with the **correct lyric text** (the SRT's times are not used, only its text).
  Several of each: pair them by file name, ask when that is unclear. Missing one: stop and say which.
- `<song>` below = the mp3 file name without `.mp3`. If `<song>.lrc` or `<song>.phrase.lrc` exists already, ask
  before overwriting it.
- Read the SRT text. If it looks machine-made (misheard words, ads like "subscribe", lines that make no sense), tell
  the user: alignment keeps the text exactly as written, so wrong words stay wrong.

## 2. Word-timed LRC

Check first: `ffmpeg -version` and `python -c "import stable_whisper, torch; print(torch.cuda.is_available())"`.
When the import fails, ask before installing `pip install -r tools/lrc/requirements.txt` (torch is large).

```
python tools/lrc/match_lyric.py "<folder>/<song>.mp3" "<folder>/<song>.srt" --language <code> -o "<folder>/<song>.lrc"
```

- `--language`: the lyrics' language (`vi` for Vietnamese, `en`, `ja`, `ko`, ...). Mixed lyrics: the main language.
- Default model `medium`. `--model large-v3` aligns better but is slower; `--demucs` (needs `pip install demucs`)
  isolates the vocals first, which helps with loud backing tracks.
- Time: about 2-3 min for a 4-min song on a GPU, much longer on CPU (tell the user when CUDA is False). Let it run
  in one call with a long timeout; do not start it twice.
- Check the result: one row per lyric word, `[interlude]` rows on long instrumental breaks.

## 3. Phrase LRC

```
python tools/lrc/phrase_lrc.py "<folder>/<song>.lrc" --draft "<folder>/<song>.phrases.txt" --lyrics "<folder>/<song>.srt"
```

The draft has one lyric line per row, long lines cut at commas; it prints the long lines still left
(`long (N words): ...`). Then read the whole draft and rewrite `<song>.phrases.txt`, one phrase per row.

JIZURA shows one LRC row as one lyric line and cuts it into on-screen chunks itself: a row per word gives a cut per
word, a long sentence is too much text at once. Rules:

- **Never change the words**: same words, spelling, punctuation and order; only move the row breaks.
  The build step refuses anything else.
- **Size**: at most 6 words per row (Latin scripts), usually 2-6, and 1-3.5 s of singing. A lyric line of 6 words
  or fewer stays whole; a longer one is split into rows of 6 words or fewer.
- **Break by meaning**: between clauses, after a comma, subject | predicate. Keep together a noun and its modifiers,
  a verb and its object, a preposition and its noun, set expressions and names.
- **Don't strand function words** at a row end or start (vi: là, của, với, và, mà, thì; en: the, a, of, to, and),
  unless the singer clearly pauses there.
- **Follow the singing**: a large jump between word times is a breath, a good place to break. Times are word
  starts; a long gap can also be a held word, so do not break on gaps alone.
- **Repeated lines (chorus) break the same way every time.**
- **No tiny rows**: a 1-2 word row under ~0.8 s joins its neighbour, unless it is a hook or a shout.
- Rows in another script (e.g. a Khmer or Japanese line) stay whole.
- JIZURA markup: `/` (manual chunk split), `*word*` (emphasis), a trailing `!` (impact), `|` (note). Lyrics that
  already contain these keep them; do not add any unless the user asks.

Build:

```
python tools/lrc/phrase_lrc.py "<folder>/<song>.lrc" --phrases "<folder>/<song>.phrases.txt" -o "<folder>/<song>.phrase.lrc"
```

- `Phrase does not match the words at ...`: fix that row of the phrase file (a word lost, changed or moved), build again.
- `warning: ... (N words: more than 6)`: split that row by the rules above and build again (a row in another
  script may stay whole).
- `warning: ... all words within 0.12s`: the aligner had no real timing there. Estimate a start time between the rows
  around it, edit it in `<song>.phrase.lrc`, and tell the user it is a guess to check by ear. Also look at the row
  after it: its first words may be squeezed too (gaps of a few hundredths of a second).

## 4. Report

Briefly: the files written (`<song>.lrc`, `<song>.phrases.txt`, `<song>.phrase.lrc`), words → phrase rows, one or two
of the breaks you chose for long or repeated lines, and every start time you estimated (marked unverified).
In JIZURA: 歌詞 → **LRC を読み込む** (Load LRC / Mở LRC) with `<song>.phrase.lrc`.
