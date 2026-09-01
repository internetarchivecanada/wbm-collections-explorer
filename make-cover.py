#!/usr/bin/env python3
"""Landing-page cover: all 49 collection names as a flowed word wall, sized in three
tiers by document count. Counts span four orders of magnitude, so a treemap or bar
length would be unreadable; type size carries only a coarse tier, and the tier legend
says so. Reads as texture at thumbnail size, as a contents page at full size."""
import json, html

W, H = 1200, 630
data = json.load(open('/Users/markgraham/Documents/collections-explorer/app/data/collections.json'))
cols = sorted(data['collections'], key=lambda c: -c['count'])

# three coarse tiers; type size is ordinal, never read as a proportional length
def tier(n):
    if n >= 100_000_000: return 0
    if n >= 5_000_000:   return 1
    return 2
TIERS = [
    dict(fs=33, weight=680, fill='#184f95', lead=46, gap=30),
    dict(fs=23, weight=620, fill='#2a78d6', lead=34, gap=26),
    dict(fs=16, weight=560, fill='#5598e7', lead=25, gap=20),
]
CHAR_W = 0.575  # advance width for this face; deliberately generous so nothing collides

x0, x1 = 40, W - 40
y = 168
parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">',
         f'<rect width="{W}" height="{H}" fill="#fcfcfb"/>',
         "<g font-family=\"system-ui, -apple-system, 'Segoe UI', sans-serif\">",
         '<text x="40" y="52" font-size="15" font-weight="600" letter-spacing="2.2" fill="#898781">'
         'INTERNET ARCHIVE &#183; WAYBACK MACHINE</text>',
         '<text x="40" y="94" font-size="34" font-weight="700" letter-spacing="-0.7" fill="#0b0b0b">'
         'Collection Search</text>',
         '<text x="40" y="120" font-size="15" fill="#52514e">'
         '49 full-text collections &#183; 8,143,819,348 indexed documents &#183; '
         'type size groups them by order of magnitude</text>']

x = x0
cur = tier(cols[0]['count'])
for c in cols:
    t = tier(c['count'])
    if t != cur:                      # start each tier on a fresh line
        y += TIERS[cur]['lead']
        x = x0
        cur = t
    s = TIERS[t]
    label = c['title']
    wpx = len(label) * s['fs'] * CHAR_W
    if x != x0 and x + wpx > x1:
        y += s['lead']
        x = x0
    parts.append(f'<text x="{x:.1f}" y="{y:.1f}" font-size="{s["fs"]}" font-weight="{s["weight"]}" '
                 f'fill="{s["fill"]}">{html.escape(label, quote=True)}</text>')
    x += wpx + s['gap']

parts.append(f'<text x="40" y="{H-26}" font-size="13" fill="#898781">'
             'wayback-labs.sf.archive.org/collections/</text>')
parts.append('</g></svg>')
open('cover.svg', 'w').write('\n'.join(parts))
print('last baseline y =', round(y), '(must be <', H - 60, ')')
