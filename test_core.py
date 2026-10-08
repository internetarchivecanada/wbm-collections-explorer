#!/usr/bin/env python3
"""Guard core.api_html, which renders the Wayback API's own `description`.

That field arrives as raw HTML from upstream. Everything must be escaped except
plain <a href> links and <br> line breaks, which four collections use to
separate paragraphs. Run: python3 test_core.py
"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "app"))

from core import api_html  # noqa: E402

DATA = os.path.join(HERE, "app", "data", "collections.json")


def main():
    # <br> in its common spellings becomes a real line break
    for tag in ("<br>", "<BR>", "<br/>", "<br />"):
        assert str(api_html(f"one{tag}two")) == "one<br>two", (tag, str(api_html(f"one{tag}two")))

    # a <br> carrying anything else stays escaped text, never markup
    for tag in ('<br onclick="x()">', "<br class=x>", "<brx>"):
        out = str(api_html(tag))
        assert "<br" not in out and "&lt;br" in out, (tag, out)

    # text that merely looks like an escaped tag stays text
    assert str(api_html("a &lt;br&gt; b")) == "a &amp;lt;br&amp;gt; b"
    # a line break beside a rejected link: break rendered, link left as text
    out = str(api_html('<a href="javascript:x()">x</a><br>y'))
    assert "<a" not in out and out.endswith("<br>y"), out

    # links: root-relative made absolute, absolute kept, other schemes left escaped
    assert str(api_html('<a href="/web/*/x.com">x</a>')) == \
        '<a href="https://web.archive.org/web/*/x.com" rel="noopener">x</a>'
    assert str(api_html('<a href="https://pen.org/">PEN</a>')) == \
        '<a href="https://pen.org/" rel="noopener">PEN</a>'
    assert "<a" not in str(api_html('<a href="javascript:alert(1)">x</a>'))

    # every other tag is escaped
    for raw in ("<script>alert(1)</script>", '<img src=x onerror="alert(1)">', "<b>bold</b>"):
        out = str(api_html(raw))
        assert "<" not in out, (raw, out)

    assert str(api_html("")) == "" and str(api_html(None)) == ""

    # real data: no raw "&lt;br" survives, and only <a>/<br> markup is emitted
    data = json.load(open(DATA))
    for c in data["collections"]:
        out = str(api_html(c.get("api_description")))
        assert "&lt;br" not in out, f"{c['id']} still shows a literal <br>"
        tags = set(re.findall(r"</?([a-z]+)", out))
        assert tags <= {"a", "br"}, f"{c['id']} emitted {tags}"

    print("ok — descriptions keep links and line breaks, everything else is escaped")


if __name__ == "__main__":
    main()
