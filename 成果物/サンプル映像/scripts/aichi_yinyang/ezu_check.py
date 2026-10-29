import math, sys, pathlib
sys.argv = [sys.argv[0], "/tmp/aichi_map/frames"]
src = open("/tmp/scripts_map/map_frames.py").read()
exec(src.split("def frame(")[0])
from playwright.sync_api import sync_playwright
W3, H3 = 2752, 1536; clon, clat = 137.26, 34.99; ppk = H3 * 0.92 / 102.3
def P(lon, lat): return (W3 / 2 + (lon - clon) * KX * ppk, H3 / 2 - (lat - clat) * KY * ppk)
def pl(line): return " ".join(f"{P(*c)[0]:.1f},{P(*c)[1]:.1f}" for c in line)
img = pathlib.Path(sys.argv[-1] if len(sys.argv) > 1 else "/tmp/aichi_map/ezu/ezu_raw.png")
img = pathlib.Path("/tmp/aichi_map/ezu/ezu_clean.png")
svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W3}" height="{H3}"><image href="{img.as_uri()}" width="{W3}" height="{H3}"/>'
       + "".join(f'<polyline points="{pl(l)}" fill="none" stroke="#ff2020" stroke-width="3"/>' for l in OUTLINE + BORDER) + "</svg>")
with sync_playwright() as p:
    b = p.chromium.launch(); pg = b.new_page(viewport={"width": W3, "height": H3})
    h = pathlib.Path("/tmp/aichi_map/ezu/align.html"); h.write_text(f"<html><body style='margin:0'>{svg}</body></html>")
    pg.goto(h.as_uri()); pg.wait_for_timeout(800)
    pg.screenshot(path="/tmp/aichi_map/ezu/align.png"); b.close()
print("ok")
