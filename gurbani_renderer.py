# gurbani_renderer.py
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageOps
import io, json, datetime, textwrap

THEMES = {
    "royal": {
        "gradient": ((255, 250, 235), (224, 233, 255)),
        "accent": (212,175,55),
        "gurbani_color": (20,20,20),
        "latin_color": (30,30,30),
    },
    "saffron": {
        "gradient": ((255, 248, 231), (255, 223, 164)),
        "accent": (230, 140, 0),
        "gurbani_color": (25,20,15),
        "latin_color": (40,35,30),
    },
    "midnight": {
        "gradient": ((20,24,44), (5,6,14)),
        "accent": (230, 220, 200),
        "gurbani_color": (245,245,245),
        "latin_color": (230,230,230),
    }
}

def lerp(a,b,t): return a + (b-a)*t

def make_vertical_gradient(size, top_rgb, bottom_rgb):
    w, h = size
    grad = Image.new("RGB", (w, h))
    for y in range(h):
        t = y / max(1, h-1)
        r = int(lerp(top_rgb[0], bottom_rgb[0], t))
        g = int(lerp(top_rgb[1], bottom_rgb[1], t))
        b = int(lerp(top_rgb[2], bottom_rgb[2], t))
        grad.paste((r,g,b), (0,y,w,y+1))
    return grad

def add_soft_vignette(img, strength=0.28):
    w, h = img.size
    mask = Image.new("L", (w, h), 0)
    draw = ImageDraw.Draw(mask)
    margin = int(min(w,h)*0.08)
    draw.ellipse([margin, margin, w-margin, h-margin], fill=int(255*strength))
    blurred = mask.filter(ImageFilter.GaussianBlur(radius=int(min(w,h)*0.08)))
    overlay = Image.new("RGBA", (w, h), (0,0,0,int(255*strength)))
    img = Image.alpha_composite(img.convert("RGBA"), Image.composite(overlay, Image.new("RGBA",(w,h),(0,0,0,0)), blurred))
    return img.convert("RGB")

def ornamental_frame(img, line_color=(212,175,55), thickness=10):
    framed = ImageOps.expand(img, border=thickness, fill=line_color)
    framed = ImageOps.expand(framed, border=2, fill=(255,255,255))
    framed = ImageOps.expand(framed, border=thickness//2, fill=line_color)
    return framed

def fit_text(draw, text, font_path, max_width, max_height, start_size, min_size=24, line_spacing=1.15):
    size = start_size
    while size >= min_size:
        font = ImageFont.truetype(font_path, size)
        avg_char_w = font.getlength("ਅਆਇਈਉਊਏਐਔਕਖਗਘਂਓਸ਼ਸਹMNpq") / 18.0
        chars_per_line = max(8, int(max_width / max(1, avg_char_w)))
        wrapped = textwrap.wrap(text, width=chars_per_line)
        total_h, max_w = 0, 0
        for line in wrapped:
            w = draw.textlength(line, font=font)
            max_w = max(max_w, w)
            total_h += font.size * line_spacing
        if max_w <= max_width and total_h <= max_height:
            return font, wrapped, int(total_h)
        size -= 2
    font = ImageFont.truetype(font_path, min_size)
    wrapped = textwrap.wrap(text, width=50)
    total_h = sum(font.size * line_spacing for _ in wrapped)
    return font, wrapped, int(total_h)

def draw_text_block(draw, lines, font, x_center, y_top, color=(20,20,20), shadow=True):
    line_h = font.size
    y = y_top
    for line in lines:
        w = draw.textlength(line, font=font)
        x = x_center - w/2
        if shadow:
            for dx, dy in [(-1,0),(1,0),(0,-1),(0,1)]:
                draw.text((x+dx, y+dy), line, font=font, fill=(0,0,0))
        draw.text((x, y), line, font=font, fill=color)
        y += int(line_h*1.15)

def parse_items_from_json_bytes(json_bytes):
    data = json.loads(json_bytes.decode("utf-8"))
    # Special handling for "text" dict
    if isinstance(data, dict) and "text" in data and isinstance(data["text"], dict):
        items = []
        punjabi_title = data.get("originalTitle", "")
        english_title = data.get("englishTitle", "")
        for k, v in data["text"].items():
            if not v or not str(v).strip() or str(v).strip().startswith("#"):
                continue
            items.append({"line": v, "title": punjabi_title, "subtitle": english_title})
        return items
    # Generic lists
    if isinstance(data, list):
        return data
    # Other dict styles
    for k in ["items","data","shabads","lines"]:
        if isinstance(data, dict) and k in data and isinstance(data[k], list):
            return data[k]
    return []

def render_image(item, cfg):
    W, H = cfg["size"]
    pad = cfg["padding"]
    theme = THEMES[cfg["theme"]]
    bg = make_vertical_gradient((W,H), theme["gradient"][0], theme["gradient"][1])
    bg = add_soft_vignette(bg, strength=0.28)
    img = bg
    draw = ImageDraw.Draw(img)

    # Titles
    title_text = (item.get("title") or "").strip()
    subtitle = (item.get("subtitle") or "").strip()

    y = pad*0.4
    if title_text:
        title_font = ImageFont.truetype(cfg["font_gurmukhi"], size=int(cfg["title_size"]))
        tw = draw.textlength(title_text, font=title_font)
        draw.text(((W - tw)/2, y), title_text, font=title_font, fill=theme["gurbani_color"])
        y += title_font.size*1.2
    if subtitle:
        sub_font = ImageFont.truetype(cfg["font_latin"], size=int(cfg["subtitle_size"]))
        tw = draw.textlength(subtitle, font=sub_font)
        draw.text(((W - tw)/2, y), subtitle, font=sub_font, fill=theme["latin_color"])
        y += sub_font.size*1.2

    gurbani = (item.get("line") or "").strip()
    if not gurbani:
        return None
    area_top = int(y + pad*0.5)
    area_h = int(H*0.55)
    area_w = W - 2*pad

    gur_font, gur_lines, gur_h = fit_text(draw, gurbani, cfg["font_gurmukhi"], area_w, area_h, start_size=cfg["gurbani_size"])
    gur_top = area_top + (area_h - gur_h)//2
    draw_text_block(draw, gur_lines, gur_font, x_center=W/2, y_top=gur_top, color=theme["gurbani_color"], shadow=True)

    if cfg["watermark"]:
        wm_font = ImageFont.truetype(cfg["font_latin"], size=int(cfg["watermark_size"]))
        wm = cfg["watermark"]
        wm_w = draw.textlength(wm, font=wm_font)
        wm_x = W - wm_w - pad*0.6
        wm_y = H - wm_font.size - pad*0.6
        draw.text((wm_x+1, wm_y+1), wm, font=wm_font, fill=(0,0,0))
        draw.text((wm_x, wm_y), wm, font=wm_font, fill=theme["latin_color"])

    if cfg["frame"]:
        img = ornamental_frame(img, line_color=theme["accent"], thickness=int(min(W,H)*0.01))

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf

def render_batch(items, cfg):
    images = []
    for idx, it in enumerate(items, 1):
        imgbuf = render_image(it, cfg)
        if imgbuf:
            images.append(imgbuf)
    return images
