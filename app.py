import streamlit as st
import json
import unicodedata
from PIL import Image, ImageDraw, ImageFont
import os
import io
import zipfile
import tempfile

# -------------------------------
# Unicode Normalizer for Gurbani
# -------------------------------
def normalize_gurbani_text(text: str) -> str:
    return unicodedata.normalize("NFC", text)

# -------------------------------
# Load Fonts (default + uploaded)
# -------------------------------
def load_font(font_file, size):
    try:
        return ImageFont.truetype(font_file, size)
    except Exception:
        return ImageFont.load_default()

def get_available_fonts(uploaded_files, font_size):
    fonts = []
    for file in uploaded_files:
        fonts.append(load_font(file, font_size))

    # Fallbacks
    fallback_paths = ["./fonts/AnmolUni.ttf", "./fonts/NotoSans-Regular.ttf"]
    for path in fallback_paths:
        if os.path.exists(path):
            fonts.append(load_font(path, font_size))

    # Always include default
    fonts.append(ImageFont.load_default())
    return fonts

# -------------------------------
# Render Gurbani Line into Image
# -------------------------------
def render_gurbani_line(line, font, theme, add_frame, watermark_text):
    W, H = 800, 400
    bg_colors = {"Light": "white", "Dark": "black", "Blue": "#1e3d59", "Cream": "#f5f5dc"}
    fg_colors = {"Light": "black", "Dark": "white", "Blue": "white", "Cream": "black"}

    img = Image.new("RGB", (W, H), color=bg_colors.get(theme, "white"))
    draw = ImageDraw.Draw(img)

    # Wrap text
    max_width = W - 80
    words, lines, line_buf = line.split(), [], ""
    for word in words:
        test_line = line_buf + " " + word if line_buf else word
        if draw.textlength(test_line, font=font) <= max_width:
            line_buf = test_line
        else:
            lines.append(line_buf)
            line_buf = word
    if line_buf:
        lines.append(line_buf)

    total_h = sum([font.getbbox(l)[3] - font.getbbox(l)[1] + 10 for l in lines])
    y = (H - total_h) // 2

    for l in lines:
        w = draw.textlength(l, font=font)
        draw.text(((W - w) // 2, y), l, font=font, fill=fg_colors.get(theme, "black"))
        y += font.getbbox(l)[3] - font.getbbox(l)[1] + 10

    if add_frame:
        draw.rectangle([5, 5, W - 5, H - 5], outline=fg_colors.get(theme, "black"), width=4)

    if watermark_text:
        wm = f"© {watermark_text}"
        wm_w = draw.textlength(wm, font=font)
        draw.text((W - wm_w - 10, H - 40), wm, font=font, fill=fg_colors.get(theme, "black"))

    return img

# -------------------------------
# Streamlit UI
# -------------------------------
st.title("📖 Gurbani Screen Display App")
st.write("Upload a Gurbani JSON file and optional fonts (TTF). Generates beautiful posters or slideshows.")

uploaded_json = st.file_uploader("Upload Gurbani JSON", type=["json"])
uploaded_fonts = st.file_uploader("Upload Fonts (optional, TTF)", type=["ttf"], accept_multiple_files=True)

theme = st.selectbox("Select Theme", ["Light", "Dark", "Blue", "Cream"])
font_size = st.slider("Font Size", 24, 72, 48)
add_frame = st.checkbox("Add Border Frame", value=True)
watermark = st.text_input("Watermark Text (optional)", "Gurbani")

if uploaded_json:
    # -------------------------------
    # Load and Normalize JSON
    # -------------------------------
    try:
        gurbani_json = json.load(uploaded_json)
        # Normalize every line
        gurbani_texts = [normalize_gurbani_text(v) for k, v in gurbani_json["text"].items()]
    except Exception as e:
        st.error(f"Error loading JSON: {e}")
        gurbani_texts = []

    if gurbani_texts:
        fonts = get_available_fonts(uploaded_fonts, font_size)

        st.subheader("Preview Slideshow")
        index = st.slider("Line Index", 0, len(gurbani_texts) - 1, 0)
        selected_font = fonts[0]  # pick first available
        img = render_gurbani_line(gurbani_texts[index], selected_font, theme, add_frame, watermark)
        st.image(img)

        # -------------------------------
        # Download Options
        # -------------------------------
        col1, col2 = st.columns(2)

        with col1:
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            st.download_button("⬇️ Download Current Poster", buf.getvalue(), "gurbani_poster.png", "image/png")

        with col2:
            if st.button("⬇️ Download All as ZIP"):
                with tempfile.TemporaryDirectory() as tmpdir:
                    zip_path = os.path.join(tmpdir, "gurbani_posters.zip")
                    with zipfile.ZipFile(zip_path, "w") as zipf:
                        for i, line in enumerate(gurbani_texts):
                            im = render_gurbani_line(line, selected_font, theme, add_frame, watermark)
                            fpath = os.path.join(tmpdir, f"gurbani_{i+1}.png")
                            im.save(fpath)
                            zipf.write(fpath, os.path.basename(fpath))
                    with open(zip_path, "rb") as f:
                        st.download_button("Download ZIP", f.read(), "gurbani_posters.zip", "application/zip")
