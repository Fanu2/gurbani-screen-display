# app.py
import streamlit as st
from gurbani_renderer import render_batch, parse_items_from_json_bytes, THEMES
import zipfile, io, tempfile, os

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
    gur_font_file = st.file_uploader("Gurmukhi font (TTF, e.g., Raavi.ttf)", type=["ttf"])
    lat_font_file = st.file_uploader("Latin font (TTF, e.g., NotoSans-Regular.ttf)", type=["ttf"])

# ---------------- JSON upload ---------------- #
st.markdown("#### 1) Upload Gurbani JSON")
json_file = st.file_uploader("JSON file", type=["json"])

col1, col2 = st.columns([1, 2])
with col1:
    st.markdown("#### 2) Choose Mode")
    mode = st.radio("Generation Mode", ["Batch images (download)", "Slideshow preview in app"], index=0)

with col2:
    st.markdown("#### Tips")
    st.write("- Upload Raavi/AnmolUni/GurbaniAkhar for Gurmukhi; Inter/NotoSans for Latin.")
    st.write("- If no font is uploaded, system fallback will be used.")

# ---------------- Main rendering ---------------- #
if json_file is not None:
    items = parse_items_from_json_bytes(json_file.read())
    if not items:
        st.error("No lines found in JSON.")
    else:
        st.success(f"Loaded {len(items)} line(s).")

        # Canvas size
        W, H = map(int, size_choice.lower().split("x"))

        # --- Handle fonts with fallback --- #
        gur_font_path, lat_font_path = None, None

        if gur_font_file is not None:
            gur_tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".ttf")
            gur_tmp.write(gur_font_file.read())
            gur_tmp.flush()
            gur_font_path = gur_tmp.name
        else:
            # fallback
            gur_font_path = "/usr/share/fonts/truetype/noto/NotoSansGurmukhi-Regular.ttf"
            if not os.path.exists(gur_font_path):
                gur_font_path = "Raavi"  # Windows fallback

        if lat_font_file is not None:
            lat_tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".ttf")
            lat_tmp.write(lat_font_file.read())
            lat_tmp.flush()
            lat_font_path = lat_tmp.name
        else:
            # fallback
            lat_font_path = "/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf"
            if not os.path.exists(lat_font_path):
                lat_font_path = "Arial"  # Windows fallback

        # Config
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
            font_gurmukhi=gur_font_path,
            font_latin=lat_font_path,
        )

        if mode == "Slideshow preview in app":
            st.markdown("### Slideshow Preview")
            idx = st.slider("Line index", 1, min(len(items), 50), 1)
            from gurbani_renderer import render_image
            imgbuf = render_image(items[idx - 1], cfg)
            st.image(imgbuf, caption=f"Line {idx}/{len(items)}", use_column_width=True)

        else:
            st.markdown("### Generate Images")
            if st.button("Render All"):
                images = render_batch(items, cfg)
                if not images:
                    st.error("Rendering failed.")
                else:
                    zip_buf = io.BytesIO()
                    with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as zf:
                        for i, buf in enumerate(images, 1):
                            zf.writestr(f"gurbani_{i:04d}.png", buf.getvalue())
                    zip_buf.seek(0)
                    st.success(f"Generated {len(images)} images.")
                    st.download_button(
                        "Download ZIP",
                        data=zip_buf,
                        file_name="gurbani_images.zip",
                        mime="application/zip",
                    )

else:
    st.info("Upload JSON to proceed. Fonts optional (system fallback used if missing).")

# ---------------- Sample JSON ---------------- #
st.markdown("---")
st.markdown("Need an example? Download our sample JSON.")
with open("sample.json", "rb") as f:
    st.download_button("Download sample.json", f, file_name="sample.json", mime="application/json")
