import math, sys, pathlib, json
sys.argv = [sys.argv[0], "/tmp/aichi_map/frames"]
src = open("/tmp/scripts_map/map_frames.py").read()
exec(src.split("def frame(")[0])
from playwright.sync_api import sync_playwright
W3, H3 = 2752, 1536; clon, clat = 137.26, 34.99; ppk = H3 * 0.92 / 102.3
def P(lon, lat): return (W3 / 2 + (lon - clon) * KX * ppk, H3 / 2 - (lat - clat) * KY * ppk)
def pl(line): return " ".join(f"{P(*c)[0]:.1f},{P(*c)[1]:.1f}" for c in line)
def inside(lon, lat):
    for f in aichi:
        for ring in rings(f["geometry"]):
            ins = False
            for i in range(len(ring)):
                x1, y1 = ring[i][:2]; x2, y2 = ring[i - 1][:2]
                if (y1 > lat) != (y2 > lat) and lon < (x2 - x1) * (lat - y1) / (y2 - y1) + x1: ins = not ins
            if ins: return province(f["properties"])
    return None
LAB = {"尾張": (136.80, 35.31), "三河": (137.52, 35.13)}
for k, (lon, lat) in LAB.items():
    assert inside(lon, lat) == {"尾張": "owari", "三河": "mikawa"}[k], f"{k} の文字が県の外"
P1, P2 = P(*NAG), P(*OKA); C = ((P1[0] + P2[0]) / 2, (P1[1] + P2[1]) / 2); R = math.dist(P1, P2)
img = pathlib.Path("/tmp/aichi_map/ezu/ezu_clean.png").as_uri()
def txt(x, y, t, size, col, halo, anchor="start", font="Hiragino Sans", weight=700, extra=""):
    return (f'<text x="{x:.1f}" y="{y:.1f}" text-anchor="{anchor}" font-family="{font}" font-weight="{weight}" font-size="{size}" fill="{col}" '
            f'style="paint-order:stroke" stroke="{halo}" stroke-width="{size*0.28:.1f}" stroke-linejoin="round" {extra}>{t}</text>')
pin = lambda p, fill, ring: f'<circle cx="{p[0]:.1f}" cy="{p[1]:.1f}" r="11" fill="{fill}" stroke="{ring}" stroke-width="4"/>'
lo, lm = P(*LAB["尾張"]), P(*LAB["三河"])
svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W3}" height="{H3}"><image href="{img}" width="{W3}" height="{H3}"/>
{"".join(f'<polyline points="{pl(l)}" fill="none" stroke="#2a2520" stroke-width="2.4" stroke-opacity="0.55" stroke-linejoin="round"/>' for l in OUTLINE)}
{"".join(f'<polyline points="{pl(l)}" fill="none" stroke="#d8b25a" stroke-width="4" stroke-dasharray="16 8" stroke-linejoin="round"/>' for l in BORDER)}
<circle cx="{C[0]:.1f}" cy="{C[1]:.1f}" r="{R:.1f}" fill="none" stroke="#d8b25a" stroke-width="3" stroke-opacity="0.75"/>
{pin(P1, "#f3d27a", "#1b1b1b")}{pin(P2, "#1b1b1b", "#f3d27a")}
{txt(P1[0] - 22, P1[1] + 10, "名古屋城", 34, "#fff8e6", "#1d2140", "end")}
{txt(P2[0] - 22, P2[1] + 46, "岡崎城", 34, "#1b1b1b", "#f6f1e6", "end")}
{txt(lo[0], lo[1], "尾張", 64, "#fff8e6", "#1d2140", "middle", "Hiragino Mincho ProN", 600, 'letter-spacing="10"')}
{txt(lm[0], lm[1], "三河", 64, "#1b1b1b", "#f6f1e6", "middle", "Hiragino Mincho ProN", 600, 'letter-spacing="10"')}
<text x="{W3 - 170}" y="160" style="writing-mode:vertical-rl" font-family="Hiragino Mincho ProN" font-weight="600" font-size="124" fill="#1b1b1b" letter-spacing="18">ふたつの目</text>
<text x="{W3 - 320}" y="240" style="writing-mode:vertical-rl" font-family="Hiragino Mincho ProN" font-weight="600" font-size="56" fill="#b8892d" letter-spacing="12">愛知の陰陽図</text>
{txt(W3 - 40, H3 - 56, "地図：国土数値情報（行政区域データ・2021年）国土交通省 を加工して作成", 22, "#5a5348", "#efe7d6", "end", weight=400)}
{txt(W3 - 40, H3 - 24, "金の点＝城の本当の位置　名所の絵＝生成AI（Nano Banana Pro）", 22, "#5a5348", "#efe7d6", "end", weight=400)}
</svg>'''
h = pathlib.Path("/tmp/aichi_map/ezu/finish.html"); h.write_text(f"<html><body style='margin:0'>{svg}</body></html>")
with sync_playwright() as p:
    b = p.chromium.launch(); pg = b.new_page(viewport={"width": W3, "height": H3})
    pg.goto(h.as_uri()); pg.wait_for_timeout(1200); pg.screenshot(path="/tmp/aichi_map/ezu/ezu_final.png"); b.close()
print("ok")
