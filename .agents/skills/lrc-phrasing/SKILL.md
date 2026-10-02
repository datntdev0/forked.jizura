---
name: lrc-phrasing
description: Turn a word-timed LRC (one word per row, e.g. from tools/lrc/match_lyric.py) into a JIZURA-ready LRC whose rows are meaningful phrases. Use when the user has a word-level / too fine LRC, wants lyrics grouped into phrases for a lyric video, or wants an LRC made from an mp3 + lyric text for JIZURA.
---

# LRC phrasing for JIZURA

JIZURA shows one LRC row as one lyric line and cuts it into on-screen chunks itself. A row per word gives a cut per
word; a row per long sentence is too much text at once. The goal: rows that read as a unit and fit the singing.

Tools live in `tools/lrc/` (see its README). Work in the folder of the user's files; write new files next to the input.

## 1. Get the word-timed LRC

- Given a word-level `.lrc`: use it.
- Given only audio + lyric text: run `python tools/lrc/match_lyric.py song.mp3 song.lyrics.txt --language <code>`
  first (needs `pip install -r tools/lrc/requirements.txt` and ffmpeg; it is slow on CPU — tell the user).

## 2. Draft

```
python tools/lrc/phrase_lrc.py song.lrc --draft song.phrases.txt [--lyrics song.lyrics.txt]
```

Pass `--lyrics` when a lyric text exists (otherwise a capital letter is taken as a line start). The draft has one
lyric line per row, long lines cut at commas; it prints the long lines still left (`long (N words): ...`).

## 3. Choose the breaks (the real work)

Read the whole draft, then rewrite `song.phrases.txt`, one phrase per row. Rules:

- **Never change the words**: same words, spelling, punctuation and order; only move the row breaks.
  The build step refuses anything else.
- **Size**: about 2–7 words (Latin scripts) and 1–3.5 s of singing. Lines of 5 words or fewer stay whole.
- **Break by meaning**: between clauses, after a comma, subject | predicate. Keep together a noun and its
  modifiers, a verb and its object, a preposition and its noun, set expressions and names.
- **Don't strand function words** at a row end or start (vi: là, của, với, và, mà, thì; en: the, a, of, to, and),
  unless the singer clearly pauses there.
- **Follow the singing**: a large jump between word times is a breath — a good place to break. Times are word
  starts; a long gap can also be a held word, so do not break on gaps alone.
- **Repeated lines (chorus) break the same way every time.**
- **Don't make rows too short**: a 1–2 word row under ~0.8 s joins its neighbour, unless it is a hook/shout.
- Leave rows in other scripts (e.g. a Khmer or Japanese line) whole.
- JIZURA markup: `/` (manual chunk split), `*word*` (emphasis), a trailing `!` (impact), `|` (note). Lyrics that
  already contain these keep them; do not add them unless the user asks.

## 4. Build and check

```
python tools/lrc/phrase_lrc.py song.lrc --phrases song.phrases.txt -o song.phrased.lrc
```

- `Phrase does not match the words at ...`: fix that row of the phrase file (a word lost, changed or reordered), run again.
- `warning: ... all words within 0.12s`: the aligner had no real timing for that phrase. Estimate a start time
  between the rows around it, edit it in the output LRC, and tell the user it is a guess to check by ear.
- Also look at the next phrase after a squeezed one: its first words may be squeezed too (very small gaps).

## 5. Report

Tell the user, briefly: the output path, rows before → after, the breaks you chose for long or repeated lines
(one or two examples), and every time you estimated (marked as unverified). In JIZURA: 歌詞 → **LRC を読み込む**
(Load LRC / Mở LRC) replaces the lyrics with the file.
