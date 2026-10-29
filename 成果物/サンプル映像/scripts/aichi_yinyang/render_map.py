"""愛知県の地図（国土数値情報の行政区域・簡略版）の上に太極図を重ねる。
太極図の2つの点を、名古屋城（尾張）と岡崎城（三河）に合わせる。"""
import json, math, sys, pathlib
from playwright.sync_api import sync_playwright

DATA = pathlib.Path("/tmp/aichi_map/data"); OUT = pathlib.Path(sys.argv[1])
LON0, LON1, LAT0, LAT1 = 136.60, 137.92, 34.50, 35.47
K = math.cos(math.radians(35.0)); S = 2200 / ((LON1 - LON0) * K)
W = round((LON1 - LON0) * K * S); H = round((LAT1 - LAT0) * S)
def P(lon, lat): return ((lon - LON0) * K * S, (LAT1 - lat) * S)

MIKAWA_CITY = {"豊橋市","岡崎市","豊川市","豊田市","安城市","西尾市","蒲郡市","刈谷市",
               "碧南市","知立市","高浜市","新城市","田原市","みよし市"}
MIKAWA_GUN = {"額田郡","北設楽郡"}
def province(p):
    return "mikawa" if (p.get("N03_004") in MIKAWA_CITY or p.get("N03_003") in MIKAWA_GUN) else "owari"

def rings(geom):
    polys = [geom["coordinates"]] if geom["type"] == "Polygon" else geom["coordinates"]
    for poly in polys:
        for ring in poly:
            yield ring
def path_d(geom):
    out = []
    for ring in rings(geom):
        pts = [P(*c[:2]) for c in ring]
        out.append("M" + " L".join(f"{x:.1f},{y:.1f}" for x, y in pts) + " Z")
    return " ".join(out)

aichi = json.load(open(DATA / "pref_23.json"))["features"]
neigh = []
for code in (21, 22, 24, 20):
    neigh += json.load(open(DATA / f"pref_{code}.json"))["features"]

# ---- 太極図の幾何 ----
NAGOYA = P(136.89949, 35.18515); OKAZAKI = P(137.15888, 34.95625)
C = ((NAGOYA[0] + OKAZAKI[0]) / 2, (NAGOYA[1] + OKAZAKI[1]) / 2)
R = math.dist(NAGOYA, OKAZAKI); a = R / 2
th = math.atan2(OKAZAKI[1] - C[1], OKAZAKI[0] - C[0])     # 岡崎の向き
def arc(cx, cy, r, t0, t1, n=90):
    return [(cx + r * math.cos(t0 + (t1 - t0) * i / n), cy + r * math.sin(t0 + (t1 - t0) * i / n)) for i in range(n + 1)]
def taiji(s):
    """s=±1：黒い半円をどちら側に置くか。名古屋＝黒の頭（白い点）、岡崎＝白の頭（黒い点）。"""
    dark = (arc(C[0], C[1], R, th, th + s * math.pi)
            + arc(NAGOYA[0], NAGOYA[1], a, th + math.pi, th + math.pi + s * math.pi)
            + arc(OKAZAKI[0], OKAZAKI[1], a, th + math.pi, th + math.pi - s * math.pi))
    white = (arc(C[0], C[1], R, th + math.pi, th + math.pi + s * math.pi)
             + arc(OKAZAKI[0], OKAZAKI[1], a, th, th + s * math.pi)
             + arc(NAGOYA[0], NAGOYA[1], a, th, th - s * math.pi))
    return dark, white

def pip(pt, poly):
    x, y = pt; inside = False
    for i in range(len(poly)):
        x1, y1 = poly[i]; x2, y2 = poly[i - 1]
        if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1) + x1:
            inside = not inside
    return inside
# 市町村ごとの外周（投影後）と外接矩形
muni = []
for f in aichi:
    for ring in rings(f["geometry"]):
        pts = [P(*c[:2]) for c in ring]
        xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
        muni.append((province(f["properties"]), pts, (min(xs), min(ys), max(xs), max(ys))))
def prov_at(pt):
    for pv, pts, (x0, y0, x1, y1) in muni:
        if x0 <= pt[0] <= x1 and y0 <= pt[1] <= y1 and pip(pt, pts):
            return pv
    return None
# どちら向きに置くと「尾張が黒・三河が白」に多く重なるか
best = None
for s in (1, -1):
    dark, white = taiji(s); score = n = 0
    for i in range(-30, 31):
        for j in range(-30, 31):
            pt = (C[0] + R * i / 30, C[1] + R * j / 30)
            if math.dist(pt, C) > R: continue
            pv = prov_at(pt)
            if pv is None: continue
            n += 1
            in_dark = pip(pt, dark)
            score += (pv == "owari") == in_dark
    print(f"s={s}: 一致 {score}/{n}")
    if best is None or score > best[0]: best = (score, s)
dark, white = taiji(best[1])
poly = lambda pts: " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)

# ---- SVG ----
land_n = "".join(f'<path d="{path_d(f["geometry"])}"/>' for f in neigh)
land_a = "".join(
    f'<path class="{province(f["properties"])}" d="{path_d(f["geometry"])}"/>' for f in aichi)
dot_r = R / 9
muni_lines = "".join(f'<path d="{path_d(f["geometry"])}"/>' for f in aichi)
owari_fill = "".join(f'<path d="{path_d(f["geometry"])}"/>' for f in aichi if province(f["properties"]) == "owari")
aichi_fill = muni_lines
def label(x, y, text, cls): return f'<text class="{cls}" x="{x:.0f}" y="{y:.0f}">{text}</text>'
lx, ly = P(136.66, 35.06); mx, my = P(137.56, 35.02)
ib = P(136.735, 34.78); mb = P(137.10, 34.745); pc = P(137.43, 34.555)
svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">
<style>
 .sea{{fill:#dfe8ec}} .nb path{{fill:#ecebe6;stroke:#d9d7cf;stroke-width:1}}
 .owari{{fill:#f3e9d2}} .mikawa{{fill:#e4ecd6}} .ai path{{stroke:#ffffff;stroke-width:1.6;stroke-linejoin:round}}
 .pref{{fill:none;stroke:#8f8a7c;stroke-width:3}}
 text{{font-family:'Hiragino Sans','Hiragino Kaku Gothic ProN',sans-serif;paint-order:stroke;stroke-linejoin:round}}
 .prov{{font-family:'Hiragino Mincho ProN',serif;font-weight:600;font-size:92px;fill:#3a332a;stroke:#fffaf0;stroke-width:12px;letter-spacing:.2em}}
 .prov.inv{{fill:#fffaf0;stroke:#1a1a1a}}
 .muni path{{fill:none;stroke:#7d7d7d;stroke-opacity:.5;stroke-width:1.3;stroke-linejoin:round}}
 .outline path{{fill:none;stroke-linejoin:round}}
 .castle{{font-weight:700;font-size:40px;fill:#1c1c1c;stroke:#ffffff;stroke-width:9px}}
 .bay{{font-style:italic;font-size:38px;fill:#6f8c99;stroke:#dfe8ec;stroke-width:6px;letter-spacing:.15em}}
 .title{{font-family:'Hiragino Mincho ProN',serif;font-weight:600;font-size:84px;fill:#2a2520;stroke:#dfe8ec;stroke-width:10px;letter-spacing:.12em}}
 .cap{{font-size:32px;fill:#4a4540;stroke:#dfe8ec;stroke-width:6px}}
 .src{{font-size:22px;fill:#7a7a7a;stroke:#dfe8ec;stroke-width:4px}}
</style>
<rect class="sea" width="{W}" height="{H}"/>
<g class="nb">{land_n}</g>
<g class="ai">{land_a}</g>
<polygon points="{poly(white)}" fill="#ffffff" fill-opacity="0.62"/>
<polygon points="{poly(dark)}" fill="#111111" fill-opacity="0.68"/>
<g class="muni">{muni_lines}</g>
<defs>
 <mask id="outO" maskUnits="userSpaceOnUse"><rect width="{W}" height="{H}" fill="#fff"/><g fill="#000">{owari_fill}</g></mask>
 <mask id="outA" maskUnits="userSpaceOnUse"><rect width="{W}" height="{H}" fill="#fff"/><g fill="#000">{aichi_fill}</g></mask>
</defs>
<g class="outline" mask="url(#outO)" stroke="#b0412c" stroke-width="8">{owari_fill}</g>
<g class="outline" mask="url(#outA)" stroke="#5b554a" stroke-width="7">{aichi_fill}</g>
<circle cx="{C[0]:.1f}" cy="{C[1]:.1f}" r="{R:.1f}" fill="none" stroke="#141414" stroke-width="6"/>
<circle cx="{NAGOYA[0]:.1f}" cy="{NAGOYA[1]:.1f}" r="{dot_r:.1f}" fill="#ffffff" stroke="#141414" stroke-width="3"/>
<circle cx="{OKAZAKI[0]:.1f}" cy="{OKAZAKI[1]:.1f}" r="{dot_r:.1f}" fill="#141414" stroke="#ffffff" stroke-width="3"/>
{label(NAGOYA[0] - dot_r - 18, NAGOYA[1] - dot_r - 14, "名古屋城", "castle")}
{label(OKAZAKI[0] + dot_r + 18, OKAZAKI[1] + dot_r + 44, "岡崎城", "castle")}
{label(lx, ly, "尾張", "prov inv")}{label(mx, my, "三河", "prov")}
{label(ib[0], ib[1], "伊勢湾", "bay")}{label(mb[0], mb[1], "三河湾", "bay")}{label(pc[0], pc[1], "太平洋", "bay")}
{label(60, H - 150, "愛知の陰陽図", "title")}
{label(64, H - 90, "白い点＝名古屋城（尾張）　黒い点＝岡崎城（三河）　赤い線＝尾張と三河の境", "cap")}
<text class="src" text-anchor="end" x="{W - 30}" y="{H - 28}">出典：国土数値情報（行政区域データ・2021年）国土交通省 を加工して作成</text>
</svg>'''
# 名古屋城・岡崎城のラベル位置は text-anchor で調整
svg = svg.replace('class="castle" x="%.0f"' % (NAGOYA[0] - dot_r - 18), 'class="castle" text-anchor="end" x="%.0f"' % (NAGOYA[0] - dot_r - 18))
(OUT / "aichi_taiji.svg").write_text(svg)
html = OUT / "aichi_taiji.html"
html.write_text(f"<html><head><meta charset='utf-8'><style>html,body{{margin:0}}</style></head><body>{svg}</body></html>")
with sync_playwright() as p:
    b = p.chromium.launch(); pg = b.new_page(viewport={"width": W, "height": H})
    pg.goto(html.as_uri()); pg.wait_for_timeout(300)
    pg.screenshot(path=str(OUT / "aichi_taiji.png")); b.close()
print(f"{W}x{H} R={R:.0f}px center={C} side={best[1]}")
