"""Cover image (9:16) and TikTok description for a JIZURA lyric video.

    python make_cover.py sheet video.mp4 [-n 12]
        frames spread over the video in one contact sheet with their times, to pick the cover frame
    python make_cover.py cover video.mp4 --time 1:23.5 --title "..." --artist "..." [--layout poster|overlay]
        poster (default): the title on a blurred copy of the frame, the frame itself below as a card
        overlay: the title straight on the frame (for frames with an empty area: --pos top|middle|bottom)
    python make_cover.py description --title "..." --artist "..."
        the description text (template in this script)

Needs ffmpeg / ffprobe on PATH and Pillow.
"""

import argparse
import json
import subprocess
import sys
import tempfile
import unicodedata
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

FONTS = Path(__file__).resolve().parent.parent / "assets" / "fonts"
TITLE_FONT, ARTIST_FONT = FONTS / "BeVietnamPro-Black.ttf", FONTS / "BeVietnamPro-SemiBold.ttf"

DESCRIPTION = """🎵 {title} – {artist}
🎬 Lyric video làm bằng 1 cú click với Jizura

{hashtags}"""
HASHTAGS = ["lyricvideo", "lyrics", "nhacviet"]

# TikTok shows a profile grid tile as the middle 3:4 of the cover (12.5% cut off above and below) and puts its
# buttons over the bottom and the right side: text starts at these heights (fractions of the cover height)
TEXT_TOP = {"top": 0.15, "middle": 0.40, "bottom": 0.60}
CARD_BOTTOM = 0.86  # poster card ends above the caption area


# ---------- video ----------

def parse_time(text: str) -> float:
    seconds = 0.0
    for part in text.split(":"):
        seconds = seconds * 60 + float(part)
    return seconds


def format_time(seconds: float) -> str:
    minutes, secs = divmod(seconds, 60)
    return f"{int(minutes)}:{secs:04.1f}"


def duration_of(video: Path) -> float:
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "json", str(video)],
                         capture_output=True, text=True, check=True).stdout
    return float(json.loads(out)["format"]["duration"])


def frame_at(video: Path, seconds: float) -> Image.Image:
    with tempfile.TemporaryDirectory() as tmp:
        png = Path(tmp) / "frame.png"
        subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{seconds:.3f}", "-i", str(video), "-frames:v", "1", str(png)],
                       check=True)
        return Image.open(png).convert("RGB")


def crop_to(image: Image.Image, ratio: float, focus: float = 0.5) -> Image.Image:
    """Crop to width/height = ratio; focus = where the crop sits vertically (0 top … 1 bottom)."""
    w, h = image.size
    cw, ch = (w, round(w / ratio)) if w / h <= ratio else (round(h * ratio), h)
    x, y = (w - cw) // 2, round((h - ch) * min(max(focus, 0.0), 1.0))
    return image.crop((x, y, x + cw, y + ch))


def crop_9_16(image: Image.Image) -> Image.Image:
    """Center-crop to 9:16, at least 1080x1920 (a 4K vertical video stays 2160x3840)."""
    image = crop_to(image, 9 / 16)
    width = max(image.width, 1080)
    return image.resize((width, width * 16 // 9), Image.LANCZOS) if width != image.width else image


# ---------- colors ----------

def luminance(rgb) -> float:
    r, g, b = (c / 255 for c in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def saturation(rgb) -> float:
    return (max(rgb) - min(rgb)) / 255


def mean_color(image: Image.Image) -> tuple:
    return tuple(int(c) for c in image.resize((1, 1), Image.BOX).getpixel((0, 0)))


def palette(image: Image.Image) -> list[tuple[int, int, int]]:
    """The frame's main colors (each at least 1% of the picture)."""
    small = image.resize((160, 284)).quantize(12)
    flat, total = small.getpalette(), 160 * 284
    return [tuple(flat[i * 3:i * 3 + 3]) for n, i in small.getcolors() if n / total > 0.01]


def ink_colors(frame: Image.Image, behind: Image.Image, bg: str) -> dict:
    """Text colors taken from the video's own colors: dark ink on a light background, white ink on a dark one."""
    if bg == "auto":
        bg = "light" if luminance(mean_color(behind)) > 0.55 else "dark"
    used = palette(frame)
    accent = max(used, key=lambda c: saturation(c) * (1 - abs(luminance(c) - 0.5)), default=(255, 213, 74))
    if bg == "light":
        darks = [c for c in used if luminance(c) < 0.3]
        title = max(darks, key=saturation) if darks else (34, 22, 36)
        return {"bg": bg, "title": title, "artist": accent if luminance(accent) < 0.55 else title,
                "veil": (255, 255, 255), "stroke": None}
    return {"bg": bg, "title": (255, 255, 255), "artist": accent if luminance(accent) > 0.45 else (255, 213, 74),
            "veil": (0, 0, 0), "stroke": (0, 0, 0)}


# ---------- text ----------

def wrap(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont, width: int) -> list[str]:
    lines, line = [], ""
    for word in text.split():
        trial = f"{line} {word}".strip()
        if line and draw.textlength(trial, font=font) > width:
            lines.append(line); line = word
        else:
            line = trial
    return lines + [line]


class TextBlock:
    """Title (largest size that wraps to max_lines inside width) and the artist line under it."""

    def __init__(self, image: Image.Image, title: str, artist: str, width: int, start_size: int, max_lines: int):
        draw = ImageDraw.Draw(image)
        size = start_size
        while True:
            self.font = ImageFont.truetype(str(TITLE_FONT), size)
            self.lines = wrap(draw, title, self.font, width)
            if (len(self.lines) <= max_lines and all(draw.textlength(l, font=self.font) <= width for l in self.lines)) \
                    or size < 40:
                break
            size = int(size * 0.92)
        self.artist = artist
        self.artist_font = ImageFont.truetype(str(ARTIST_FONT), max(28, int(size * 0.42)))
        self.line_h, self.gap = int(size * 1.12), int(size * 0.45)
        self.height = self.line_h * len(self.lines) + self.gap + self.artist_font.size

    def draw(self, image: Image.Image, top: int, ink: dict, accent: str | None):
        draw, x = ImageDraw.Draw(image), image.width // 2
        stroke = max(2, self.font.size // 22) if ink["stroke"] else 0
        y = top
        for line in self.lines:
            draw.text((x, y), line, font=self.font, fill=ink["title"], anchor="ma",
                      stroke_width=stroke, stroke_fill=ink["stroke"])
            y += self.line_h
        draw.text((x, y + self.gap), self.artist, font=self.artist_font, fill=accent or ink["artist"], anchor="ma",
                  stroke_width=stroke // 2, stroke_fill=ink["stroke"])


def veil_band(image: Image.Image, top: int, bottom: int, strength: float, color) -> Image.Image:
    """Cover a horizontal band with a color (fading out above and below) so the text reads on any frame."""
    w, h = image.size
    mask = Image.new("L", (1, h), 0)
    fade = max(1, (bottom - top) // 2)
    for y in range(h):
        d = 0 if top <= y <= bottom else min(abs(y - top), abs(y - bottom))
        mask.putpixel((0, y), int(255 * strength * max(0.0, 1 - d / fade)))
    return Image.composite(Image.new("RGB", (w, h), color), image, mask.resize((w, h)))


# ---------- layouts ----------

def overlay(frame: Image.Image, args) -> Image.Image:
    w, h = frame.size
    text = TextBlock(frame, args.title, args.artist, int(w * 0.84), int(w * 0.13), 3)
    top = int(h * TEXT_TOP[args.pos]) - (text.height // 2 if args.pos == "middle" else 0)
    pad = int(text.font.size * 0.6)
    band = (top - pad, top + text.height + pad)
    ink = ink_colors(frame, frame.crop((0, band[0], w, band[1])), args.bg)
    image = veil_band(frame, *band, args.dim if args.dim is not None else 0.55, ink["veil"])
    text.draw(image, top, ink, args.accent)
    return image


def poster(frame: Image.Image, args) -> Image.Image:
    w, h = frame.size
    background = frame.filter(ImageFilter.GaussianBlur(w * 0.06))
    ink = ink_colors(frame, background, args.bg)
    image = Image.blend(background, Image.new("RGB", (w, h), ink["veil"]), args.dim if args.dim is not None else 0.5)

    text = TextBlock(image, args.title, args.artist, int(w * 0.86), int(w * 0.11), 2)
    top = int(h * TEXT_TOP["top"])
    text.draw(image, top, ink, args.accent)

    card_top = top + text.height + int(h * 0.035)
    card_h = int(h * CARD_BOTTOM) - card_top
    card_w = min(int(w * 0.76), card_h * 4 // 5)
    card = crop_to(frame, card_w / card_h, args.focus).resize((card_w, card_h), Image.LANCZOS)
    radius, x = int(w * 0.03), (w - card_w) // 2
    mask = Image.new("L", card.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, card_w - 1, card_h - 1), radius, fill=255)

    shadow = Image.new("L", (w, h), 0)
    ImageDraw.Draw(shadow).rounded_rectangle((x, card_top + w // 80, x + card_w, card_top + card_h + w // 80), radius,
                                             fill=110)
    shadow = shadow.filter(ImageFilter.GaussianBlur(w * 0.015))
    image = Image.composite(Image.new("RGB", (w, h), (0, 0, 0)), image, shadow)
    image.paste(card, (x, card_top), mask)
    return image


def make_cover(args):
    frame = crop_9_16(frame_at(args.video, parse_time(args.time)))
    image = (poster if args.layout == "poster" else overlay)(frame, args)
    out = args.output or args.video.with_name(args.video.stem + ".cover.jpg")
    image.save(out, quality=95, subsampling=0)
    print(f"Wrote {out} ({image.width}x{image.height})")


# ---------- contact sheet ----------

def make_sheet(args):
    total = duration_of(args.video)
    times = [total * (i + 0.5) / args.n for i in range(args.n)]
    cols, thumb_w = 4, 400
    thumbs = [crop_9_16(frame_at(args.video, t)).resize((thumb_w, thumb_w * 16 // 9)) for t in times]
    rows = -(-len(thumbs) // cols)
    sheet = Image.new("RGB", (cols * thumb_w, rows * thumbs[0].height), "black")
    label = ImageFont.truetype(str(ARTIST_FONT), 36)
    for i, (t, thumb) in enumerate(zip(times, thumbs)):
        x, y = (i % cols) * thumb_w, (i // cols) * thumb.height
        sheet.paste(thumb, (x, y))
        ImageDraw.Draw(sheet).text((x + 12, y + 10), format_time(t), font=label, fill="yellow",
                                   stroke_width=3, stroke_fill="black")
    out = args.output or args.video.with_name(args.video.stem + ".sheet.jpg")
    sheet.save(out, quality=90)
    print(f"Wrote {out}: frames at " + ", ".join(format_time(t) for t in times))


# ---------- description ----------

def hashtag(text: str) -> str:
    """'Thiên Đường Với Người Thương' -> 'thienduongvoinguoithuong'"""
    plain = unicodedata.normalize("NFD", text.replace("đ", "d").replace("Đ", "D"))
    return "".join(c for c in plain if c.isascii() and c.isalnum()).lower()


def make_description(args):
    tags = " ".join("#" + t for t in [hashtag(args.title)] + HASHTAGS)
    text = DESCRIPTION.format(title=args.title, artist=args.artist, hashtags=tags)
    if args.output:
        args.output.write_text(text + "\n", encoding="utf-8", newline="\n")
        print(f"Wrote {args.output}")
    print(text)


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="Cover image and description for a lyric video.")
    sub = parser.add_subparsers(dest="command", required=True)

    sheet = sub.add_parser("sheet", help="contact sheet of frames to choose from")
    sheet.add_argument("video", type=Path)
    sheet.add_argument("-n", type=int, default=12, help="number of frames (default 12)")
    sheet.add_argument("-o", "--output", type=Path)

    cover = sub.add_parser("cover", help="9:16 cover image from one frame")
    cover.add_argument("video", type=Path)
    cover.add_argument("--time", required=True, help="frame time: seconds or m:ss.s")
    cover.add_argument("--title", required=True)
    cover.add_argument("--artist", required=True)
    cover.add_argument("--layout", choices=["poster", "overlay"], default="poster")
    cover.add_argument("--focus", type=float, default=0.5,
                       help="poster: which part of the frame the card shows, 0 top … 1 bottom (default 0.5)")
    cover.add_argument("--pos", choices=TEXT_TOP, default="top", help="overlay: where the title goes (default top)")
    cover.add_argument("--bg", choices=["auto", "light", "dark"], default="auto",
                       help="light: dark text on a light veil; dark: white text on a dark veil (default: by the frame)")
    cover.add_argument("--dim", type=float, help="strength of the veil, 0-1 (default 0.5 poster, 0.55 overlay)")
    cover.add_argument("--accent", help="artist text color, e.g. #FFD54A (default: the video's strongest color)")
    cover.add_argument("-o", "--output", type=Path, help="default: <video>.cover.jpg")

    desc = sub.add_parser("description", help="description text")
    desc.add_argument("--title", required=True)
    desc.add_argument("--artist", required=True)
    desc.add_argument("-o", "--output", type=Path)

    args = parser.parse_args()
    {"sheet": make_sheet, "cover": make_cover, "description": make_description}[args.command](args)


if __name__ == "__main__":
    main()
