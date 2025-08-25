# app.py
import streamlit as st
from gurbani_renderer import render_batch, parse_items_from_json_bytes, THEMES, render_image
import zipfile, io, base64, tempfile

st.set_page_config(page_title="Gurbani Screen Display", page_icon="✨", layout="wide")

st.title("✨ Gurbani Screen Display")
st.caption("Upload your Gurbani JSON to generate beautiful display images — with Punjabi + English titles.")

# ---------------- Sidebar ---------------- #
with st.sidebar:
    st.header("Settings")
    theme = st.selectbox("Theme", list(THEMES.keys()), index=0)
    size_choice = st.selectbox("Canvas Size", ["1920x1080", "2560x1440", "1080x1920"], index=0)
    padding = st.slider("Padding (px)", 40, 200, 100, 10)
    gurbani_size = st.slider("Gurbani Start Size", 60, 140, 96, 2)
    title_size = st.slider("Punjabi Title Size", 40, 90, 56, 2)
    subtitle_size = st.slider("English Title Size", 28, 70, 40, 2)
    frame = st.checkbox("Ornamental Frame", value=True)
    watermark = st.text_input("Watermark (optional)", value="")

    st.markdown("---")
    st.subheader("Fonts")
    gur_font_file = st.file_uploader("Gurmukhi font (TTF, e.g., Raavi.ttf or NotoSansGurmukhi.ttf)", type=["ttf"])
    lat_font_file = st.file_uploader("Latin font (TTF, e.g., NotoSans-Regular.ttf)", type=["ttf"])

# ---------------- File Upload ---------------- #
st.markdown("#### 1) Upload Gurbani JSON")
json_file = st.file_uploader("JSON file", type=["json"])

col1, col2 = st.columns([1, 2])
with col1:
    st.markdown("#### 2) Choose Mode")
    mode = st.radio("Generation Mode", ["Batch images (download)", "Slideshow preview in app"], index=0)

with col2:
    st.markdown("#### Tips")
    st.write("- Your JSON can be a simple list of objects with `line`, or the special format with a `text` dictionary.")
    st.write("- Use Raavi/AnmolUni/GurbaniAkhar for Gurmukhi; Inter/NotoSans for Latin.")
    st.write("- Fonts are now embedded with base64 → no missing font errors!")

# ---------------- Helper: Encode font ---------------- #
def font_to_base64_css(font_file, name):
    """Convert uploaded font to base64 CSS @font-face rule."""
    if font_file is None:
        return ""
    font_bytes = font_file.read()
    b64 = base64.b64encode(font_bytes).decode("utf-8")
    return f"""
    @font-face {{
        font-family: '{name}';
        src: url(data:font/ttf;base64,{b64}) format('truetype');
        font-weight: normal;
        font-style: normal;
    }}
    """

# ---------------- Main Logic ---------------- #
if json_file and gur_font_file and lat_font_file:
    # Load JSON items
    items = parse_items_from_json_bytes(json_file.read())
    if not items:
        st.error("No lines found in JSON.")
    else:
        st.success(f"Loaded {len(items)} line(s).")

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
        )

        # Embed fonts as CSS
        gur_font_css = font_to_base64_css(gur_font_file, "GurmukhiFont")
        lat_font_css = font_to_base64_css(lat_font_file, "LatinFont")
        cfg["font_css"] = gur_font_css + lat_font_css
        cfg["font_gurmukhi"] = "GurmukhiFont"
        cfg["font_latin"] = "LatinFont"

        if mode == "Slideshow preview in app":
            st.markdown("### Slideshow Preview")
            idx = st.slider("Line index", 1, min(len(items), 50), 1)
            imgbuf = render_image(items[idx - 1], cfg)
            st.image(imgbuf, caption=f"Line {idx}/{len(items)}", use_column_width=True)

        else:
            st.markdown("### Generate Images")
            if st.button("Render All"):
                images = render_batch(items, cfg)
                if not images:
                    st.error("Rendering failed.")
                else:
                    # zip them
                    zip_buf = io.BytesIO()
                    with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as zf:
                        for i, buf in enumerate(images, 1):
                            zf.writestr(f"gurbani_{i:04d}.png", buf.getvalue())
                    zip_buf.seek(0)
                    st.success(f"Generated {len(images)} images.")
                    st.download_button("Download ZIP", data=zip_buf,
                                       file_name="gurbani_images.zip", mime="application/zip")

else:
    st.info("Upload JSON + two fonts (TTF) to proceed.")

# ---------------- Footer ---------------- #
st.markdown("---")
st.markdown("Need an example? Download our sample JSON.")
with open("sample.json", "rb") as f:
    st.download_button("Download sample.json", f,
                       file_name="sample.json", mime="application/json")
