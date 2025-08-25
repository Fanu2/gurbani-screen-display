from PIL import Image, ImageDraw, ImageFont
import io, json
from functools import lru_cache
import math

# Try to import HarfBuzz + FreeType
try:
    import uharfbuzz as hb
    import freetype
    _HB_AVAILABLE = True
except Exception:
    _HB_AVAILABLE = False


# ---------------- THEME DEFINITIONS ----------------
THEMES = {
    "Light": {"bg": (255, 255, 255), "fg": (0, 0, 0)},
    "Dark": {"bg": (0, 0, 0), "fg": (255, 255, 255)},
    "Sepia": {"bg": (245, 230, 200), "fg": (50, 30, 10)},
}


# ---------------- JSON PARSER ----------------
def parse_items_from_json_bytes(data: bytes):
    try:
        raw = json.loads(data.decode("utf-8"))
    except Exception:
        return []

    items = []
    if isinstance(raw, list):
        for obj in raw:
            if isinstance(obj, dict) and "line" in obj:
                items.append(obj)
            elif isinstance(obj, dict) and "text" in obj:
                items.append(obj["text"])
            elif isinstance(obj, str):
                items.append({"line": obj})
    return items


# ---------------- FONT HELPERS ----------------
@lru_cache(maxsize=8)
def _load_fontdata(font_path: str) -> bytes:
    with open(font_path, "rb") as f:
        return f.read()

@lru_cache(maxsize=8)
def _load_ft_face(font_path: str):
    face = freetype.Face(font_path)
    return face

def _ft_set_size(face, size_px: int):
    face.set_char_size(size_px * 64)

def _hb_shape(text: str, font_bytes: bytes):
    buf = hb.Buffer()
    buf.add_str(text)
    buf.guess_segment_properties()
    font = hb.Font(hb.Face(font_bytes))
    hb.shape(font, buf, {})
    return buf.glyph_infos, buf.glyph_positions


# ---------------- TEXT RENDERING ----------------
def hb_measure(text: str, font_path: str, size_px: int):
    """Returns (width, height, ascent, descent) in px for shaped text."""
    if not _HB_AVAILABLE:
        pil_font = ImageFont.truetype(font_path, size_px)
        w, h = pil_font.getbbox(text)[2:]
        ascent, descent = pil_font.getmetrics()
        return w, h, ascent, descent

    font_bytes = _load_fontdata(font_path)
    infos, pos = _hb_shape(text, font_bytes)

    adv_x = sum(p.x_advance for p in pos) / 64.0

    face = _load_ft_face(font_path)
    _ft_set_size(face, size_px)
    ascent = face.size.ascender / 64.0 if hasattr(face.size, "ascender") else size_px * 0.8
    descent = -face.size.descender / 64.0 if hasattr(face.size, "descender") else size_px * 0.2
    height = ascent + descent

    return int(math.ceil(adv_x)), int(math.ceil(height)), int(ascent), int(descent)


def hb_render(img: Image.Image, text: str, font_path: str, size_px: int, fill, xy):
    """Draw shaped text onto img at (x,y baseline)."""
    if not _HB_AVAILABLE:
        draw = ImageDraw.Draw(img)
        pil_font = ImageFont.truetype(font_path, size_px)
        draw.text(xy, text, font=pil_font, fill=fill, anchor="ls")
        w, h = draw.textbbox(xy, text, font=pil_font)[2:]
        return w, h

    x0, y0 = xy
    font_bytes = _load_fontdata(font_path)
    face = _load_ft_face(font_path)
    _ft_set_size(face, size_px)
    infos, positions = _hb_shape(text, font_bytes)

    pen_x, pen_y = float(x0), float(y0)
    max_y = y0
    min_y = y0

    for info, pos in zip(infos, positions):
        gid = info.codepoint
        dx = pos.x_offset / 64.0
        dy = -pos.y_offset / 64.0

        face.load_glyph(gid, freetype.FT_LOAD_RENDER)
        slot = face.glyph
        bmp = slot.bitmap
        w, h = bmp.width, bmp.rows
        top = slot.bitmap_top
        left = slot.bitmap_left

        if w > 0 and h > 0:
            glyph_img = Image.frombytes("L", (w, h), bytes(bmp.buffer))
            gx = int(pen_x + dx + left)
            gy = int(pen_y + dy - top)
            img.paste(Image.new("RGBA", (w, h), fill), (gx, gy), glyph_img)

            max_y = max(max_y, gy + h)
            min_y = min(min_y, gy)

        pen_x += pos.x_advance / 64.0
        pen_y -= pos.y_advance / 64.0

    return int(pen_x - x0), max_y - min_y


def shape_wrap(text: str, font_path: str, size_px: int, max_width: int):
    words = text.split()
    if not words:
        return [""]

    lines, cur = [], words[0]
    for w in words[1:]:
        probe = cur + " " + w
        w_px, *_ = hb_measure(probe, font_path, size_px)
        if w_px <= max_width:
            cur = probe
        else:
            lines.append(cur)
            cur = w
    lines.append(cur)
    return lines


def draw_gurmukhi_centered(img: Image.Image, text: str, font_path: str, size_px: int,
                           fill, center_x: int, y: int, max_width: int, line_gap: int = 10):
    lines = shape_wrap(text, font_path, size_px, max_width)
    total_h = 0
    for line in lines:
        w_px, h_px, asc, desc = hb_measure(line, font_path, size_px)
        x = int(center_x - w_px / 2)
        baseline_y = int(y + asc)
        hb_render(img, line, font_path, size_px, fill, (x, baseline_y))
        y += int(h_px + line_gap)
        total_h += int(h_px + line_gap)
    return total_h


# ---------------- MAIN RENDERER ----------------
def render_image(item, cfg):
    W, H = cfg["size"]
    theme = THEMES[cfg["theme"]]
    img = Image.new("RGBA", (W, H), theme["bg"])

    # Draw Gurbani line
    gurmukhi_text = item.get("line") if isinstance(item, dict) else str(item)
    y = cfg["padding"]

    line_gap = max(8, cfg["gurbani_size"] // 6)
    draw_gurmukhi_centered(
        img=img,
        text=gurmukhi_text,
        font_path=cfg["font_gurmukhi"],
        size_px=cfg["gurbani_size"],
        fill=theme["fg"],
        center_x=W // 2,
        y=y,
        max_width=W - 2 * cfg["padding"],
        line_gap=line_gap,
    )

    # Punjabi Title
    if "title" in item:
        draw = ImageDraw.Draw(img)
        font = ImageFont.truetype(cfg["font_gurmukhi"], cfg["title_size"])
        text = item["title"]
        w = draw.textlength(text, font=font)
        draw.text(((W - w) // 2, H - cfg["padding"]*2),
                  text, font=font, fill=theme["fg"])

    # English Subtitle
    if "subtitle" in item:
        draw = ImageDraw.Draw(img)
        font = ImageFont.truetype(cfg["font_latin"], cfg["subtitle_size"])
        text = item["subtitle"]
        w = draw.textlength(text, font=font)
        draw.text(((W - w) // 2, H - cfg["padding"]),
                  text, font=font, fill=theme["fg"])

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf


def render_batch(items, cfg):
    return [render_image(it, cfg) for it in items]
