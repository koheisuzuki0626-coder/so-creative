import math, sys
from playwright.sync_api import sync_playwright
S = 2048; c = S / 2; R = S * 0.42; a = R / 2; d = R / 9
def arc(cx, cy, r, t0, t1, n=200):
    return " ".join(f"{cx + r*math.cos(t0+(t1-t0)*i/n):.1f},{cy + r*math.sin(t0+(t1-t0)*i/n):.1f}" for i in range(n+1))
# 縦の軸。白＝右半分＋上の頭、黒＝左半分＋下の頭
dark = arc(c, c, R, -math.pi/2, -3*math.pi/2) + " " + arc(c, c + a, a, math.pi/2, -math.pi/2) + " " + arc(c, c - a, a, math.pi/2, 3*math.pi/2)
svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{S}" height="{S}"><rect width="{S}" height="{S}" fill="#9a9a9a"/>
<circle cx="{c}" cy="{c}" r="{R}" fill="#ffffff"/><polygon points="{dark}" fill="#111111"/>
<circle cx="{c}" cy="{c - a}" r="{d}" fill="#111111"/><circle cx="{c}" cy="{c + a}" r="{d}" fill="#ffffff"/>
<circle cx="{c}" cy="{c}" r="{R}" fill="none" stroke="#111111" stroke-width="6"/></svg>'''
with sync_playwright() as p:
    b = p.chromium.launch(); pg = b.new_page(viewport={"width": S, "height": S})
    pg.set_content(f"<html><body style='margin:0'>{svg}</body></html>"); pg.screenshot(path=sys.argv[1]); b.close()
print("ok")
