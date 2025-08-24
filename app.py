# -*- coding: utf-8 -*-
"""
Gurbani Screen Display — Single‑file Streamlit App
-------------------------------------------------
Features:
- Upload Gurbani JSON (supports your `text` dict format and simple lists)
- UTF‑8 safe parsing (no mojibake for Gurmukhi)
- Upload fonts OR auto‑load bundled fonts from ./fonts (AnmolUni + NotoSans)
- Themes (royal, saffron, midnight), optional frame, watermark
- Slideshow preview or batch render (ZIP download)

Run:
    streamlit run gurbani_streamlit_app_single_file.py

Optional repo layout if you want bundled fonts:
    fonts/
      ├─ AnmolUni.ttf
      └─ NotoSans-Regular.ttf
"""
import io
import json
import os
import tempfile
import zipfile
from typing import List, Dict, Any, Tuple

import streamlit as st
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageOps

# ------------------------- App Config -------------------------
st.set_page_config(page_title="Gurbani Screen Display", page_icon="✨", layout="wide")

# ------------------------- Themes ----------------------------
THEMES: Dict[str, Dict[str, Tuple[int, int, int]]] = {
    "royal": {
        "gradient_top": (255, 250, 235),
        "gradient_bottom": (224, 233, 255),
        "accent": (212, 175, 55),
        "gurbani_color": (20, 20, 20),
        "latin_color": (30, 30, 30),
    },
    "saffron": {
        "gradient_top": (255, 248, 231),
        "gradient_bottom": (255, 223, 164),
        "accent": (230, 140, 0),
        "gurbani_color": (25, 20, 15),
        "latin_color": (40, 35, 30),
    },
    "midnight": {
        "gradient_top": (20, 24, 44),
        "gradient_bottom": (5, 6, 14),
        "accent": (230, 220, 200),
        "gurbani_color": (245, 245, 245),
        "latin_color": (230, 230, 230),
    },
}

# ------------------------- Utilities -------------------------

def lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def make_vertical_gradient(size: Tuple[int, int], top_rgb, bottom_rgb) -> Image.Image:
    w, h = size
    grad = Image.new("RGB", (w, h))
    for y in range(h):
        t = y / max(1, h - 1)
        r = int(lerp(top_rgb[0], bottom_rgb[0], t))
        g = int(lerp(top_rgb[1], bottom_rgb[1], t))
        b = int(lerp(top_rgb[2], bottom_rgb[2], t))
        grad.paste((r, g, b), (0, y, w, y + 1))
    return grad


def add_soft_vignette(img: Image.Image, strength: float = 0.28) -> Image.Image:
    w, h = img.size
    mask = Image.new("L", (w, h), 0)
    draw = ImageDraw.Draw(mask)
    margin = int(min(w, h) * 0.08)
    draw.ellipse([margin, margin, w - margin, h - margin], fill=int(255 * strength))
    blurred = mask.filter(ImageFilter.GaussianBlur(radius=int(min(w, h) * 0.08)))
    overlay = Image.new("RGBA", (w, h), (0, 0, 0, int(255 * strength)))
    out = Image.alpha_composite(img.convert("RGBA"), Image.composite(overlay, Image.new("RGBA", (w, h), (0, 0, 0, 0)), blurred))
    return out.convert("RGB")


def ornamental_frame(img: Image.Image, line_color=(212, 175, 55), thickness: int = 10) -> Image.Image:
    framed = ImageOps.expand(img, border=thickness, fill=line_color)
    framed = ImageOps.expand(framed, border=2, fill=(255, 255, 255))
    framed = ImageOps.expand(framed, border=thickness // 2, fill=line_color)
    return framed


def fit_text(draw: ImageDraw.ImageDraw, text: str, font_path: str, max_width: int, max_height: int,
             start_size: int, min_size: int = 24, line_spacing: float = 1.15):
    """Auto-wrap + auto-size to fit a box."""
    size = start_size
    while size >= min_size:
        font = ImageFont.truetype(font_path, size)
        # Estimate chars per line by average glyph width
        avg_char_w = font.getlength("ਅਆਇਈਉਊਏਐਔਕਖਗਘਂਓਸ਼ਸਹMNpq") / 18.0
        chars_per_line = max(8, int(max_width / max(1, avg_char_w)))
        lines = wrap_text(draw, text, font, chars_per_line)
        total_h, max_w = 0, 0
        for ln in lines:
            w = draw.textlength(ln, font=font)
            max_w = max(max_w, w)
            total_h += int(font.size * line_spacing)
        if max_w <= max_width and total_h <= max_height:
            return font, lines, int(total_h)
        size -= 2
    font = ImageFont.truetype(font_path, min_size)
    lines = wrap_text(draw, text, font, 50)
    total_h = sum(int(font.size * line_spacing) for _ in lines)
    return font, lines, int(total_h)


def wrap_text(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont, limit: int) -> List[str]:
    # Simple word wrap that respects Unicode spaces/punctuation
    import textwrap
    return textwrap.wrap(text, width=limit)


def draw_text_block(draw: ImageDraw.ImageDraw, lines: List[str], font: ImageFont.FreeTypeFont,
                    x_center: float, y_top: int, color=(20, 20, 20), shadow=True):
    y = y_top
    for line in lines:
        w = draw.textlength(line, font=font)
        x = x_center - w / 2
        if shadow:
            for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                draw.text((x + dx, y + dy), line, font=font, fill=(0, 0, 0))
        draw.text((x, y), line, font=font, fill=color)
        y += int(font.size * 1.15)


# -------------------- JSON Parsing (UTF‑8 safe) --------------------

def parse_items_from_json_bytes(json_bytes: bytes) -> List[Dict[str, Any]]:
    """Accepts bytes from Streamlit uploader, returns a list of items.
    Special-cases the {"text": {"1": "..."}} structure, attaching titles if present.
    """
    data = json.loads(json_bytes.decode("utf-8"))

    # Case A: your special format
    if isinstance(data, dict) and isinstance(data.get("text"), dict):
        items = []
        punjabi_title = data.get("originalTitle", "")
        english_title = data.get("englishTitle", "")
        # Keep numeric order by sorting keys numerically when possible
        def key_sort(k):
            try:
                return int(k)
            except Exception:
                return k
        for k in sorted(data["text"].keys(), key=key_sort):
            v = str(data["text"][k]).strip()
            if not v or v.startswith("#"):
                continue
            items.append({"line": v, "title": punjabi_title, "subtitle": english_title})
        return items

    # Case B: list of objects already
    if isinstance(data, list):
        return data

    # Case C: nested lists under well-known keys
    if isinstance(data, dict):
        for k in ["items", "data", "shabads", "lines"]:
            if isinstance(data.get(k), list):
                return data[k]

    return []


# -------------------- Rendering --------------------

def render_image(item: Dict[str, Any], cfg: Dict[str, Any]) -> io.BytesIO:
    W, H = cfg["size"]
    pad = cfg["padding"]
    theme = THEMES[cfg["theme"]]

    bg = make_vertical_gradient((W, H), theme["gradient_top"], theme["gradient_bottom"])
    bg = add_soft_vignette(bg, strength=0.28)
    draw = ImageDraw.Draw(bg)

    # Titles
    y = int(pad * 0.4)
    title_text = (item.get("title") or "").strip()
    subtitle = (item.get("subtitle") or "").strip()

    if title_text:
        title_font = ImageFont.truetype(cfg["font_gurmukhi"], size=int(cfg["title_size"]))
        tw = draw.textlength(title_text, font=title_font)
        draw.text(((W - tw) / 2, y), title_text, font=title_font, fill=theme["gurbani_color"])
        y += int(title_font.size * 1.25)

    if subtitle:
        sub_font = ImageFont.truetype(cfg["font_latin"], size=int(cfg["subtitle_size"]))
        tw = draw.textlength(subtitle, font=sub_font)
        draw.text(((W - tw) / 2, y), subtitle, font=sub_font, fill=theme["latin_color"])
        y += int(sub_font.size * 1.25)

    # Gurbani line (centered block)
    gurbani = (item.get("line") or "").strip()
    if not gurbani:
        return None

    area_top = int(y + pad * 0.5)
    area_h = int(H * 0.55)
    area_w = W - 2 * pad

    gur_font, gur_lines, gur_h = fit_text(draw, gurbani, cfg["font_gurmukhi"], area_w, area_h, start_size=cfg["gurbani_size"])
    gur_top = area_top + (area_h - gur_h) // 2
    draw_text_block(draw, gur_lines, gur_font, x_center=W / 2, y_top=gur_top, color=theme["gurbani_color"], shadow=True)

    # Watermark
    if cfg.get("watermark"):
        wm_font = ImageFont.truetype(cfg["font_latin"], size=int(cfg["watermark_size"]))
        wm = cfg["watermark"]
        wm_w = draw.textlength(wm, font=wm_font)
        wm_x = W - wm_w - int(pad * 0.6)
        wm_y = H - wm_font.size - int(pad * 0.6)
        # subtle shadow
        draw.text((wm_x + 1, wm_y + 1), wm, font=wm_font, fill=(0, 0, 0))
        draw.text((wm_x, wm_y), wm, font=wm_font, fill=theme["latin_color"])

    # Optional frame
    if cfg.get("frame"):
        bg = ornamental_frame(bg, line_color=theme["accent"], thickness=int(min(W, H) * 0.01))

    buf = io.BytesIO()
    bg.save(buf, format="PNG")
    buf.seek(0)
    return buf


def render_batch(items: List[Dict[str, Any]], cfg: Dict[str, Any]) -> List[io.BytesIO]:
    images = []
    for it in items:
        imgbuf = render_image(it, cfg)
        if imgbuf:
            images.append(imgbuf)
    return images


# ----------------------- UI: Sidebar -------------------------
st.title("✨ Gurbani Screen Display")
st.caption("UTF‑8 safe, font‑aware Gurbani renderer for screens.")

with st.sidebar:
    st.header("Settings")
    theme = st.selectbox("Theme", list(THEMES.keys()), index=0)
    size_choice = st.selectbox("Canvas Size", ["1920x1080", "2560x1440", "1080x1920"], index=0)
    padding = st.slider("Padding (px)", 40, 240, 100, 10)
    gurbani_size = st.slider("Gurbani Start Size", 60, 160, 96, 2)
    title_size = st.slider("Punjabi Title Size", 40, 100, 56, 2)
    subtitle_size = st.slider("English Title Size", 28, 80, 40, 2)
    frame = st.checkbox("Ornamental Frame", value=True)
    watermark = st.text_input("Watermark (optional)", value="")

    st.markdown("---")
    st.subheader("Fonts")
    st.write("Upload TTFs or rely on bundled ./fonts (AnmolUni + NotoSans).")
    gur_font_file = st.file_uploader("Gurmukhi font (TTF)", type=["ttf"], key="gfont")
    lat_font_file = st.file_uploader("Latin font (TTF)", type=["ttf"], key="lfont")

# ----------------------- UI: Inputs ---------------------------
st.markdown("#### 1) Upload Gurbani JSON")
json_file = st.file_uploader("JSON file", type=["json"], key="json")

col1, col2 = st.columns([1, 2])
with col1:
    st.markdown("#### 2) Mode")
    mode = st.radio("Generation Mode", ["Batch images (download)", "Slideshow preview in app"], index=0)
with col2:
    st.markdown("#### Tips")
    st.write("- Supports your special `{ 'text': { '1': '...' } }` format and simple lists.")
    st.write("- For best results, use AnmolUni/Raavi for Gurmukhi and Noto Sans for English.")

# ---------------------- Font Resolution ----------------------

def resolve_font_paths(gur_upload, lat_upload) -> Tuple[str, str]:
    """Return filesystem paths to the chosen fonts.
    Preference: uploaded -> bundled ./fonts -> error.
    """
    # If user uploaded, save to temp files
    if gur_upload is not None and lat_upload is not None:
        gtmp = tempfile.NamedTemporaryFile(delete=False, suffix=".ttf")
        gtmp.write(gur_upload.read()); gtmp.flush()
        ltmp = tempfile.NamedTemporaryFile(delete=False, suffix=".ttf")
        ltmp.write(lat_upload.read()); ltmp.flush()
        return gtmp.name, ltmp.name

    # Else attempt bundled fonts
    app_dir = os.path.dirname(os.path.abspath(__file__))
    bundled_g = os.path.join(app_dir, "fonts", "AnmolUni.ttf")
    bundled_l = os.path.join(app_dir, "fonts", "NotoSans-Regular.ttf")
    if os.path.exists(bundled_g) and os.path.exists(bundled_l):
        return bundled_g, bundled_l

    return None, None

# ---------------------- Main Logic ---------------------------
if json_file is not None:
    try:
        items = parse_items_from_json_bytes(json_file.read())
    except Exception as e:
        st.error(f"Failed to read JSON as UTF‑8: {e}")
        items = []

    if not items:
        st.error("No lines found in JSON.")
    else:
        st.success(f"Loaded {len(items)} line(s).")

        # Resolve fonts
        g_path, l_path = resolve_font_paths(gur_font_file, lat_font_file)
        if not g_path or not l_path:
            st.error("No fonts available. Upload two TTFs or place AnmolUni.ttf and NotoSans-Regular.ttf under ./fonts.")
        else:
            # Prepare config
            W, H = map(int, size_choice.lower().split("x"))
            cfg = dict(
                size=(W, H),
                padding=padding,
                gurbani_size=gurbani_size,
                title_size=title_size,
                subtitle_size=subtitle_size,
                watermark_size=28,
                theme=theme,
                frame=frame,
                watermark=watermark,
                font_gurmukhi=g_path,
                font_latin=l_path,
            )

            if mode == "Slideshow preview in app":
                st.markdown("### Slideshow Preview")
                idx = st.slider("Line index", 1, len(items), 1)
                buf = render_image(items[idx - 1], cfg)
                if buf:
                    st.image(buf, caption=f"Line {idx}/{len(items)}", use_column_width=True)
            else:
                st.markdown("### Generate Images")
                if st.button("Render All"):
                    images = render_batch(items, cfg)
                    if not images:
                        st.error("Rendering failed.")
                    else:
                        zip_buf = io.BytesIO()
                        with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as zf:
                            for i, b in enumerate(images, 1):
                                zf.writestr(f"gurbani_{i:04d}.png", b.getvalue())
                        zip_buf.seek(0)
                        st.success(f"Generated {len(images)} images.")
                        st.download_button("Download ZIP", data=zip_buf, file_name="gurbani_images.zip", mime="application/zip")
else:
    st.info("Upload JSON to begin. Optionally upload fonts, or place them under ./fonts for auto‑loading.")

# ---------------------- Sample Download ----------------------
st.markdown("---")
st.markdown("Need an example? Download a sample JSON.")
sample = {
    "originalTitle": "ਗੁਰੂ ਗ੍ਰੰਥ ਸਾਹਿਬ ਜੀ",
    "englishTitle": "Guru Granth Sahib",
    "text": {
        "0": "#100",
        "1": "ਰੇਨੁ ਸੰਤਨ ਕੀ ਮੇਰੈ ਮੁਖਿ ਲਾਗੀ ॥",
        "2": "ਦੁਰਮਤਿ ਬਿਨਸੀ ਕੁਬੁਧਿ ਅਭਾਗੀ ॥",
        "3": "ਸਚ ਘਰਿ ਬੈਸਿ ਰਹੇ ਗੁਣ ਗਾਏ ਨਾਨਕ ਬਿਨਸੇ ਕੂਰਾ ਜੀਉ ॥੪॥੧੧॥੧੮॥",
        "4": "ਮਾਝ ਮਹਲਾ ੫ ॥"
    }
}
sample_bytes = json.dumps(sample, ensure_ascii=False, indent=2).encode("utf-8")
st.download_button("Download sample.json", data=sample_bytes, file_name="sample.json", mime="application/json")
