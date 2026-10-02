---
name: lyric-video-cover
description: Make a high-quality 9:16 cover image and a TikTok description for a lyric video exported from JIZURA. Use when the user wants a cover / thumbnail / ảnh bìa, a caption / mô tả, or hashtags for a lyric video they are about to upload (TikTok, Reels, Shorts).
---

# Lyric video cover and description

One script does the work: `scripts/make_cover.py` (next to this file; needs ffmpeg/ffprobe on PATH and Pillow).
Below, `$S` is that script's path. Write the outputs next to the video unless the user says otherwise.

## 1. Inputs

- The exported video (`.mp4`).
- Song title and artist exactly as they should appear, with Vietnamese diacritics. Take them from the user, or from the
  JIZURA project file (`*.jizura.json`: `title`, `artist`); ask when neither has them. Do not guess the artist.

## 2. Pick the frame

```
python $S sheet video.mp4 -o video.sheet.jpg          # 12 frames with their times; -n for more
```

Open the sheet image and look at it. A good cover frame:
- shows a lyric line in full, ideally the hook / chorus line (with a word-timed or phrase LRC, its times tell you where
  the chorus is), and the lyric is complete, not in the middle of an animation;
- is not one of the empty frames (intro, interlude, outro: background only).

If no frame is right, make a sheet with more frames (`-n 24`), or try times near a good one (±0.5 s) in step 3.

## 3. Make the cover

```
python $S cover video.mp4 --time 2:13.6 --title "Thiên Đường Với Người Thương" --artist "Phương Mỹ Chi x DTAP" -o video.cover.jpg
```

- Default `--layout poster`: title and artist at the top on a blurred copy of the frame, the frame below as a rounded
  card. It never puts the title over the video's own lyric text, so use it unless the user wants something else.
- `--focus 0..1`: which part of the frame the card shows (0 top, 1 bottom) when the lyric is not in the middle.
- `--layout overlay --pos top|middle|bottom`: title straight on the frame, only for a frame with an empty area there.
- Colors come from the frame (`--bg auto`): dark text on light videos, white text on dark ones. Override with
  `--bg light|dark`, `--accent "#RRGGBB"` (artist line), `--dim 0..1` (veil strength).
- Size: 9:16, the video's resolution (2160x3840 for a 4K vertical export), never under 1080x1920.
- Text stays inside the middle 3:4 of the cover (TikTok's profile grid crop) and above the caption area.

**Always open the cover and check it** before reporting: title readable and not cut, diacritics right, the card shows a
complete lyric, nothing important hidden. Fix with the options above and render again.

## 4. Description

```
python $S description --title "..." --artist "..." -o video.tiktok.txt
```

Output (the template is `DESCRIPTION` in the script; the first hashtag is the title without diacritics):

```
🎵 Thiên Đường Với Người Thương – Phương Mỹ Chi x DTAP
🎬 Lyric video làm bằng 1 cú click với Jizura

#thienduongvoinguoithuong #lyricvideo #lyrics #nhacviet
```

Keep the template as it is. Add more hashtags (artist, song code) only when the user asks.

## 5. Report

Briefly: the cover path and size, which frame/time you used, the description text (ready to copy), and the contact
sheet's path (only a working file: the user can delete it). If the song's audio is under copyright, remind the user once that TikTok may mute it; using the
song's official TikTok sound is safer.
