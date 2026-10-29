"""絵地図の下絵（2752x1536）：尾張＝夜、三河＝昼の塗り分けと、名所の位置の印。"""
import math, sys, json, pathlib
sys.argv = [sys.argv[0], "/tmp/aichi_map/frames"]
src = open("/tmp/scripts_map/map_frames.py").read()
exec(src.split("def frame(")[0])
from playwright.sync_api import sync_playwright
W3, H3 = 2752, 1536
clon, clat = 137.26, 34.99; ppk = H3 * 0.92 / 102.3
def P(lon, lat): return (W3 / 2 + (lon - clon) * KX * ppk, H3 / 2 - (lat - clat) * KY * ppk)
def pl(line): return " ".join(f"{P(*c)[0]:.1f},{P(*c)[1]:.1f}" for c in line)
def poly(feats, which=None):
    out = []
    for f in feats:
        if which and province(f["properties"]) != which: continue
        for ring in rings(f["geometry"]):
            out.append("M" + " L".join(f"{P(*c[:2])[0]:.1f},{P(*c[:2])[1]:.1f}" for c in ring) + "Z")
    return " ".join(out)
nfeat = [f for fs in neigh for f in fs]
MARK = {"red": ((136.8995, 35.1852), "#e02020"),        # 名古屋城
        "yellow": ((136.9083, 35.1700), "#f2c200"),     # 名古屋の中心街（栄・名古屋駅の一帯）
        "orange": ((137.1589, 34.9562), "#ff7a00"),     # 岡崎城
        "purple": ((137.1562, 35.0519), "#8a2be2")}     # 豊田の工場
marks = "".join(f'<circle cx="{P(*ll)[0]:.1f}" cy="{P(*ll)[1]:.1f}" r="16" fill="{col}" stroke="#fff" stroke-width="5"/>' for ll, col in MARK.values())
svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W3}" height="{H3}"><rect width="{W3}" height="{H3}" fill="#cfdde3"/>
<path d="{poly(nfeat)}" fill="#e6e1d6" stroke="#b9b3a6" stroke-width="1.5"/>
<path d="{poly(aichi, "owari")}" fill="#23284a"/><path d="{poly(aichi, "mikawa")}" fill="#f3ead2"/>
{"".join(f'<polyline points="{pl(l)}" fill="none" stroke="#111" stroke-width="3" stroke-linejoin="round"/>' for l in OUTLINE)}
{"".join(f'<polyline points="{pl(l)}" fill="none" stroke="#c9a03a" stroke-width="5" stroke-dasharray="16 8" stroke-linejoin="round"/>' for l in BORDER)}
{marks}</svg>'''
OUT = pathlib.Path("/tmp/aichi_map/ezu")
with sync_playwright() as p:
    b = p.chromium.launch(); pg = b.new_page(viewport={"width": W3, "height": H3})
    pg.set_content(f"<html><body style='margin:0'>{svg}</body></html>"); pg.screenshot(path=str(OUT / "guide.png")); b.close()
json.dump({k: P(*v[0]) for k, v in MARK.items()}, open(OUT / "marks.json", "w"))
print("ok")
