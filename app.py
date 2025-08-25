import os
import random
import tempfile
import streamlit as st
from PIL import Image, ImageDraw, ImageFont

# -------------------------------
# Font setup
# -------------------------------
FONTS_DIR = "fonts"
cfg = {
    "font_gurmukhi": os.path.join(FONTS_DIR, "NotoSansGurmukhi-Regular.ttf"),
    "font_shahmukhi": os.path.join(FONTS_DIR, "NotoNastaliqUrdu-Regular.ttf"),
    "font_hindi": os.path.join(FONTS_DIR, "NotoSansDevanagari-Regular.ttf"),
    "font_assamese": os.path.join(FONTS_DIR, "NotoSansAssamese-Regular.ttf"),
}

# -------------------------------
# Sample texts
# -------------------------------
SAMPLE_TEXTS = {
    "Gurmukhi": "ਸਤਿ ਨਾਮੁ ਕਰਤਾ ਪੁਰਖੁ",
    "Shahmukhi": "ست نام کرتا پرکھ",
    "Hindi": "सत नाम करता पुरख",
    "Assamese": "সৎ নাম কৰ্তা পুৰখ"
}

# -------------------------------
# Streamlit UI
# -------------------------------
st.set_page_config(page_title="✨ Gurbani Screen Display", page_icon="✨")

st.title("✨ Gurbani Screen Display")

language = st.selectbox("Select Language", list(SAMPLE_TEXTS.keys()))

text_input = st.text_area(
    "Enter your text",
    SAMPLE_TEXTS[language],
    height=100
)

font_size = st.slider("Font Size", 20, 150, 60)

# Color options
default_colors = ["white", "yellow", "orange", "pink", "lightblue", "lightgreen"]
text_color = st.color_picker("Pick Text Color", "#ffffff")
shuffle_colors = st.checkbox("Shuffle Colors (each line random)")

# Background options
bg_color = st.color_picker("Pick Background Color", "#000000")

# -------------------------------
# Rendering logic
# -------------------------------
def render_text(text, font_path, font_size, color, bg_color, shuffle=False):
    lines = text.split("\n")
    font = ImageFont.truetype(font_path, font_size)

    # Estimate image size
    dummy_img = Image.new("RGB", (100, 100))
    draw = ImageDraw.Draw(dummy_img)
    max_width = 0
    total_height = 0
    line_heights = []

    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
        max_width = max(max_width, w)
        total_height += h + 10
        line_heights.append(h)

    img = Image.new("RGB", (max_width + 40, total_height + 40), bg_color)
    draw = ImageDraw.Draw(img)

    y = 20
    for i, line in enumerate(lines):
        line_color = random.choice(default_colors) if shuffle else color
        draw.text((20, y), line, font=font, fill=line_color)
        y += line_heights[i] + 10

    return img


# -------------------------------
# Buttons
# -------------------------------
col1, col2, col3 = st.columns(3)

with col1:
    if st.button("Preview Sample Text"):
        font_path = cfg[f"font_{language.lower()}"]
        img = render_text(
            SAMPLE_TEXTS[language],
            font_path,
            font_size,
            text_color,
            bg_color,
            shuffle_colors
        )
        st.image(img, caption=f"Preview ({language})", use_container_width=True)

with col2:
    if st.button("Preview All Languages"):
        for lang, sample in SAMPLE_TEXTS.items():
            st.markdown(f"### {lang}")

            font_path = cfg[f"font_{lang.lower()}"]

            # Render sample
            img_sample = render_text(
                sample,
                font_path,
                font_size,
                text_color,
                bg_color,
                shuffle_colors
            )

            # Render user input
            img_custom = render_text(
                text_input,
                font_path,
                font_size,
                text_color,
                bg_color,
                shuffle_colors
            )

            cols = st.columns(2)
            with cols[0]:
                st.image(img_sample, caption=f"{lang} (Sample)", use_container_width=True)
            with cols[1]:
                st.image(img_custom, caption=f"{lang} (Your Text)", use_container_width=True)

with col3:
    if st.button("Generate"):
        font_path = cfg[f"font_{language.lower()}"]
        img = render_text(
            text_input,
            font_path,
            font_size,
            text_color,
            bg_color,
            shuffle_colors
        )

        st.image(img, caption="Rendered Text", use_container_width=True)

        # Save to download
        tmp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
        img.save(tmp_file.name, "PNG")

        with open(tmp_file.name, "rb") as f:
            st.download_button(
                "Download Image",
                f,
                file_name=f"{language}_text.png",
                mime="image/png"
            )
