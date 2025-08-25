# Save uploaded fonts to temp files
import tempfile, os
from PIL import ImageFont

# Gurmukhi font handling
if gur_font_file is not None:
    gur_tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".ttf")
    gur_tmp.write(gur_font_file.read()); gur_tmp.flush()
    cfg["font_gurmukhi"] = gur_tmp.name
else:
    # fallback to bundled NotoSansGurmukhi if not uploaded
    gur_fallback = os.path.join("fonts", "NotoSansGurmukhi-Regular.ttf")
    if os.path.exists(gur_fallback):
        cfg["font_gurmukhi"] = gur_fallback
    else:
        st.error("⚠️ No Gurmukhi font provided, and NotoSansGurmukhi not found in fonts/.")
        st.stop()

# Latin font handling
if lat_font_file is not None:
    lat_tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".ttf")
    lat_tmp.write(lat_font_file.read()); lat_tmp.flush()
    cfg["font_latin"] = lat_tmp.name
else:
    lat_fallback = os.path.join("fonts", "NotoSans-Regular.ttf")
    if os.path.exists(lat_fallback):
        cfg["font_latin"] = lat_fallback
    else:
        st.error("⚠️ No Latin font provided, and NotoSans not found in fonts/.")
        st.stop()

# Validate fonts with PIL
try:
    _ = ImageFont.truetype(cfg["font_gurmukhi"], gurbani_size)
    _ = ImageFont.truetype(cfg["font_latin"], subtitle_size)
except Exception as e:
    st.error(f"Font loading failed: {e}")
    st.stop()
