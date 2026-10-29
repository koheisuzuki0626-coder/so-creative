"""金鯱×地図の動画用：土台（金鯱なし）と、上に重ねる線・文字の層（透過）を 1920x1080 で作る。変換の値も出す。"""
import json, math, sys, pathlib
sys.argv = [sys.argv[0], "/tmp/aichi_map/frames"]
src = open("/tmp/scripts_map/map_frames.py").read()
exec(src.split("def frame(")[0])
from playwright.sync_api import sync_playwright
OUT = pathlib.Path("/tmp/aichi_map/fanim"); W2, H2 = 1920, 1080
clon, clat = 137.26, 34.99; ppk = H2 * 0.92 / 102.3
def P(lon, lat): return (W2 / 2 + (lon - clon) * KX * ppk, H2 / 2 - (lat - clat) * KY * ppk)
def pl(line): return " ".join(f"{P(*c)[0]:.1f},{P(*c)[1]:.1f}" for c in line)
def poly_d(which):
    out = []
    for f in aichi:
        if province(f["properties"]) != which: continue
        for ring in rings(f["geometry"]):
            out.append("M" + " L".join(f"{P(*c[:2])[0]:.1f},{P(*c[:2])[1]:.1f}" for c in ring) + "Z")
    return " ".join(out)
P1, P2 = P(*NAG), P(*OKA)
g, b = (1192.74, 1369.80), (846.13, 681.28)            # 絵の中の金の玉・黒い玉（2048px の座標）
s = math.dist(P1, P2) / math.dist(g, b)
th = math.atan2(P2[1] - P1[1], P2[0] - P1[0]) - math.atan2(b[1] - g[1], b[0] - g[0])
SZ = round(2048 * s); WC = int(SZ * 2.2) // 2 * 2
params = {"P1": P1, "P2": P2, "s": s, "theta": th, "SZ": SZ, "WC": WC, "GX": g[0] * SZ / 2048, "GY": g[1] * SZ / 2048}
json.dump(params, open(OUT / "params.json", "w")); print(params)
TEX = '<filter id="paper"><feTurbulence type="fractalNoise" baseFrequency="0.8" numOctaves="3" seed="7"/><feColorMatrix values="0 0 0 0 0.45  0 0 0 0 0.40  0 0 0 0 0.32  0 0 0 0.10 0"/></filter>'
nb = "".join(f'<polyline points="{pl(l)}" fill="none" stroke="#bdb5a4" stroke-width="1.2"/>' for l in NEIGH)
ol = lambda col, w, op=1: "".join(f'<polyline points="{pl(l)}" fill="none" stroke="{col}" stroke-width="{w}" stroke-opacity="{op}" stroke-linejoin="round"/>' for l in OUTLINE)
bd = "".join(f'<polyline points="{pl(l)}" fill="none" stroke="{GOLD}" stroke-width="2.6" stroke-opacity="0.85" stroke-dasharray="11 5 2 5" stroke-linejoin="round"/>' for l in BORDER)
def label(p, t, dx, dy, anchor="start", size=24):
    return (f'<text x="{p[0]+dx:.1f}" y="{p[1]+dy:.1f}" text-anchor="{anchor}" font-family="Hiragino Sans" font-weight="700" font-size="{size}" fill="{INK}" '
            f'style="paint-order:stroke" stroke="{PAPER}" stroke-width="{size*0.28:.1f}" stroke-linejoin="round">{t}</text>')
title = (f'<text x="{W2-120}" y="110" style="writing-mode:vertical-rl" font-family="Hiragino Mincho ProN" font-weight="600" font-size="86" fill="{INK}" letter-spacing="12">ふたつの目</text>'
         f'<text x="{W2-225}" y="165" style="writing-mode:vertical-rl" font-family="Hiragino Mincho ProN" font-weight="600" font-size="40" fill="{GOLD}" letter-spacing="9">愛知の陰陽図</text>')
base = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W2}" height="{H2}"><defs>{TEX}</defs><rect width="{W2}" height="{H2}" fill="{PAPER}"/>{nb}'
        f'<path d="{poly_d("owari")}" fill="#dcd4c3"/><path d="{poly_d("mikawa")}" fill="#f6f1e6"/>{ol(INK, 2.0)}<rect width="{W2}" height="{H2}" filter="url(#paper)"/></svg>')
top = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W2}" height="{H2}">{ol(INK, 1.3, 0.55)}{bd}'
       f'{label(P1, "名古屋城", -34, 8, "end")}{label(P2, "岡崎城", 34, 8)}'
       f'{label(P(136.80, 35.31), "尾張", 0, 0, "middle", 30)}{label(P(137.62, 35.20), "三河", 0, 0, "middle", 30)}{title}</svg>')
with sync_playwright() as p:
    br = p.chromium.launch(); pg = br.new_page(viewport={"width": W2, "height": H2})
    pg.set_content(f"<html><body style='margin:0'>{base}</body></html>"); pg.wait_for_timeout(300); pg.screenshot(path=str(OUT / "base.png"))
    pg.set_content(f"<html><body style='margin:0;background:transparent'>{top}</body></html>"); pg.wait_for_timeout(300); pg.screenshot(path=str(OUT / "top.png"), omit_background=True)
    br.close()
print("ok")
