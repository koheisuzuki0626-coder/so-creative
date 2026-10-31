"""動く絵地図の上に重ねる層（線・城の点・地名・題字・出典）を、透過の 1920x1080 で作る。
絵は ezu_clean.png(2752x1536) を scale=1936:1080,crop=1920:1080:8:0 した位置にある（10-31 実測）。"""
import math, sys, pathlib
sys.argv = [sys.argv[0], "/tmp/aichi_map/frames"]
src = open("/tmp/scripts_map/map_frames.py").read()
exec(src.split("def frame(")[0])
from playwright.sync_api import sync_playwright
W3, H3 = 2752, 1536; clon, clat = 137.26, 34.99; ppk = H3 * 0.92 / 102.3
SX, SY, OX = 1936 / W3, 1080 / H3, 8
def P(lon, lat): return (W3 / 2 + (lon - clon) * KX * ppk, H3 / 2 - (lat - clat) * KY * ppk)
def pl(line): return " ".join(f"{P(*c)[0]:.1f},{P(*c)[1]:.1f}" for c in line)
LAB = {"尾張": (136.80, 35.31), "三河": (137.52, 35.13)}
P1, P2 = P(*NAG), P(*OKA); C = ((P1[0] + P2[0]) / 2, (P1[1] + P2[1]) / 2); R = math.dist(P1, P2)
def txt(x, y, t, size, col, halo, anchor="start", font="Hiragino Sans", weight=700, extra=""):
    return (f'<text x="{x:.1f}" y="{y:.1f}" text-anchor="{anchor}" font-family="{font}" font-weight="{weight}" font-size="{size}" fill="{col}" '
            f'style="paint-order:stroke" stroke="{halo}" stroke-width="{size*0.28:.1f}" stroke-linejoin="round" {extra}>{t}</text>')
pin = lambda p, fill, ring: f'<circle cx="{p[0]:.1f}" cy="{p[1]:.1f}" r="11" fill="{fill}" stroke="{ring}" stroke-width="4"/>'
lo, lm = P(*LAB["尾張"]), P(*LAB["三河"])
RX = W3 - OX / SX * 2  # 切り落とされる右端の手前に揃える
svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="1920" height="1080" viewBox="{OX / SX:.3f} 0 {1920 / SX:.3f} {H3}" preserveAspectRatio="none">
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
{txt(RX - 40, H3 - 56, "地図：国土数値情報（行政区域データ・2021年）国土交通省 を加工して作成", 22, "#5a5348", "#efe7d6", "end", weight=400)}
{txt(RX - 40, H3 - 24, "金の点＝城の本当の位置　名所の絵＝生成AI（Nano Banana Pro）", 22, "#5a5348", "#efe7d6", "end", weight=400)}
</svg>'''
out = pathlib.Path("/tmp/aichi_map/ezanim"); h = out / "layer.html"
h.write_text(f"<html><body style='margin:0;background:transparent'>{svg}</body></html>", encoding="utf-8")
with sync_playwright() as p:
    b = p.chromium.launch(); pg = b.new_page(viewport={"width": 1920, "height": 1080})
    pg.goto(h.as_uri()); pg.wait_for_timeout(1000); pg.screenshot(path=str(out / "layer.png"), omit_background=True); b.close()
vp = lambda q: (q[0] * SX - OX, q[1] * SY)
print("名古屋城", [round(v, 1) for v in vp(P1)], "岡崎城", [round(v, 1) for v in vp(P2)])
