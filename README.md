# Gurbani Screen Display ✨

Streamlit app to turn a Gurbani JSON file into beautiful display images (PNG) with Punjabi + English titles.

## Features
- Upload JSON (supports: special `text` dictionary format or simple list).
- Upload Gurmukhi + Latin fonts (TTF).
- Themes: `royal`, `saffron`, `midnight`.
- Optional ornamental frame + watermark.
- Two modes: Batch image download as ZIP, or in-app slideshow preview.

## Quickstart (local)
```bash
pip install -r requirements.txt
streamlit run app.py
```
Then open the URL Streamlit prints.

## Deploy on Streamlit Cloud
1. Create a new GitHub repository, e.g. `gurbani-screen-display`.
2. Push these files.
3. Go to Streamlit Cloud, connect the repo, and set `app.py` as the entry point.
4. Add your fonts via the app’s **font upload** controls when you run it.

## JSON formats
### A) Special format (like your sample)
```json
{
  "originalTitle": "ਗੁਰੂ ਗ੍ਰੰਥ ਸਾਹਿਬ ਜੀ",
  "englishTitle": "Guru Granth Sahib",
  "text": {
    "0": "#100",
    "1": "ਰੇਨੁ ਸੰਤਨ ਕੀ ਮੇਰੈ ਮੁਖਿ ਲਾਗੀ ॥",
    "2": "ਦੁਰਮਤਿ ਬਿਨਸੀ ਕੁਬੁਧਿ ਅਭਾਗੀ ॥"
  }
}
```
The app will skip lines like `#100` and use both titles at the top.

### B) Simple list
```json
[
  {"title": "ਗੁਰੂ ਗ੍ਰੰਥ ਸਾਹਿਬ ਜੀ", "subtitle": "Guru Granth Sahib", "line": "...."},
  {"line": "...."}
]
```

## Fonts
You **must** upload a Gurmukhi font that supports Unicode Gurmukhi (e.g. Raavi, AnmolUni, GurbaniAkhar). For the Latin subtitle/watermark, upload a Latin font (e.g. Inter, Noto Sans).

## License
MIT
