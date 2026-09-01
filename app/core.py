#!/usr/bin/env python3
"""Presentation logic shared by the Flask server (app.py) and the static
site builder (../build.py).

Nothing in here imports Flask, so the serverless build needs only Jinja2.
"""
import html
import json
import os
import re

from markupsafe import Markup

HERE = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(HERE, "data", "collections.json")
VERSION = "1.1.0"


def read_data(path=DATA_PATH):
    with open(path) as f:
        return json.load(f)


LANG_NAMES = {
    "en": "English", "es": "Spanish", "ru": "Russian", "fr": "French", "de": "German",
    "zh": "Chinese", "pt": "Portuguese", "it": "Italian", "ja": "Japanese", "ar": "Arabic",
    "fa": "Persian", "ps": "Pashto", "tr": "Turkish", "nl": "Dutch", "pl": "Polish",
    "uk": "Ukrainian", "be": "Belarusian", "ko": "Korean", "id": "Indonesian", "vi": "Vietnamese",
    "th": "Thai", "hi": "Hindi", "he": "Hebrew", "sv": "Swedish", "da": "Danish", "no": "Norwegian",
    "fi": "Finnish", "cs": "Czech", "el": "Greek", "ro": "Romanian", "hu": "Hungarian",
    "bg": "Bulgarian", "ca": "Catalan", "la": "Latin", "tl": "Tagalog", "af": "Afrikaans",
    "lo": "Lao", "km": "Khmer", "ur": "Urdu", "sr": "Serbian", "hr": "Croatian", "sk": "Slovak",
    "sl": "Slovenian", "lt": "Lithuanian", "lv": "Latvian", "et": "Estonian", "my": "Burmese",
    "ne": "Nepali", "si": "Sinhala", "ta": "Tamil", "bn": "Bengali", "ml": "Malayalam",
    "mk": "Macedonian", "sq": "Albanian", "hy": "Armenian", "ka": "Georgian", "az": "Azerbaijani",
    "kk": "Kazakh", "uz": "Uzbek", "mn": "Mongolian", "sw": "Swahili", "am": "Amharic",
    "is": "Icelandic", "ga": "Irish", "cy": "Welsh", "eu": "Basque", "gl": "Galician",
    "eo": "Esperanto", "yi": "Yiddish", "so": "Somali", "ms": "Malay", "jv": "Javanese",
    "qu": "Quechua", "ku": "Kurdish", "tg": "Tajik", "ky": "Kyrgyz", "tk": "Turkmen",
    "bs": "Bosnian", "gu": "Gujarati", "pa": "Punjabi", "mr": "Marathi", "te": "Telugu",
    "kn": "Kannada", "or": "Odia", "as": "Assamese", "dv": "Dhivehi", "bo": "Tibetan",
    "ug": "Uyghur", "ha": "Hausa", "yo": "Yoruba", "ig": "Igbo", "zu": "Zulu",
    "mg": "Malagasy", "ny": "Chichewa", "rw": "Kinyarwanda", "sn": "Shona", "st": "Sotho",
    "br": "Breton", "gd": "Scottish Gaelic", "fy": "Frisian", "lb": "Luxembourgish",
    "mt": "Maltese", "fo": "Faroese", "hz": "Herero", "nn": "Norwegian Nynorsk",
}


def commas(n):
    try:
        return f"{int(n):,}"
    except (TypeError, ValueError):
        return "—"


def compact(n):
    """1729093664 -> '1.73 billion' — for prose, never instead of the exact figure."""
    try:
        n = int(n)
    except (TypeError, ValueError):
        return "—"
    for div, word in ((1_000_000_000, "billion"), (1_000_000, "million"), (1_000, "thousand")):
        if n >= div:
            v = n / div
            return f"{v:.2f} {word}" if v < 10 else f"{v:.1f} {word}"
    return f"{n:,}"


def lang(code):
    return LANG_NAMES.get(code, code)


WB = "https://web.archive.org"

_A_OPEN = re.compile(r"&lt;a href=&quot;([^&]+)&quot;&gt;")
_A_CLOSE = "&lt;/a&gt;"


def api_html(text):
    """Render the Wayback API's own `description`, which arrives as raw HTML.

    Everything is escaped first and only plain <a href="..."> is allowed back in,
    so a change upstream can never inject markup here. The API writes its links
    root-relative (`/web/*/example.com`), which only resolves on web.archive.org,
    so those are rewritten absolute.
    """
    if not text:
        return Markup("")
    esc = html.escape(str(text), quote=True)

    def anchor(m):
        href = html.unescape(m.group(1))
        if href.startswith("/"):
            href = WB + href
        elif not href.startswith(("http://", "https://")):
            return m.group(0)
        return f'<a href="{html.escape(href, quote=True)}" rel="noopener">'

    return Markup(_A_OPEN.sub(anchor, esc).replace(_A_CLOSE, "</a>"))


FILTERS = {"commas": commas, "compact": compact, "lang": lang, "api_html": api_html}


def age_phrase(days):
    if days is None:
        return "date unknown"
    if days <= 0:
        return "today"
    if days == 1:
        return "yesterday"
    if days < 60:
        return f"{days} days ago"
    if days < 730:
        m = round(days / 30.44)
        return f"{m} month{'' if m == 1 else 's'} ago"
    y = days / 365.25
    return f"{y:.1f} years ago"


def enrich(data):
    """Attach the few derived fields the templates need."""
    cats = data["categories"]
    biggest = max((c["count"] for c in data["collections"]), default=1)
    for c in data["collections"]:
        c["category_label"] = cats.get(c["category"], {}).get("label", c["category"])
        c["bar"] = (c["count"] / biggest) if biggest else 0
        age = c.get("index_age_days")
        c["age_phrase"] = age_phrase(age)
        if age is None:
            c["freshness"] = ("unknown", "Unknown", "Index rebuild date unknown")
        elif age <= 45:
            c["freshness"] = ("current", "Live", "Rebuilt within the last 45 days")
        elif age <= 400:
            c["freshness"] = ("aging", "Aging", "Last rebuilt over a month ago")
        else:
            c["freshness"] = ("frozen", "Frozen", "No index rebuild in over a year")
    return data
