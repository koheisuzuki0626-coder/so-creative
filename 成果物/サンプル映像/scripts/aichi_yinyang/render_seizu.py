"""仮説図：尾張と三河の境は、名古屋城と岡崎城を目とする太極図のS字に沿うか。
製図の体裁（図枠・表題欄・凡例・縮尺・方位）で描き、検証の数字も載せる。"""
import math, sys, pathlib
OUTDIR = pathlib.Path(sys.argv[1]); TJ_ALL, TJ_O, TJ_M, EQ_ALL, EQ_O, EQ_M = sys.argv[2:8]
sys.argv = [sys.argv[0], str(OUTDIR)]
src = open("/tmp/scripts_map/render_map.py").read()
exec(src.split("# どちら向きに置くと")[0])          # データ・投影・太極図の幾何
from playwright.sync_api import sync_playwright
s_side = 1
dark, white = taiji(s_side)
MX = MY = 80; PANEL = 860; CW, CH = W + 2 * MX + PANEL, H + 2 * MY
PX0 = MX + W + 40; PW = CW - MX - PX0
def Q(pt): return (pt[0] + MX, pt[1] + MY)            # 地図座標 → 用紙座標
def pts(seq): return " ".join(f"{x + MX:.1f},{y + MY:.1f}" for x, y in seq)
def dpath(geom):
    out = []
    for ring in rings(geom):
        out.append("M" + " L".join(f"{P(*c[:2])[0] + MX:.1f},{P(*c[:2])[1] + MY:.1f}" for c in ring) + " Z")
    return " ".join(out)
km = S / 110.95                                       # 1km あたりのpx

# ---- 太極図の作図線 ----
u = ((OKAZAKI[0] - C[0]) / a, (OKAZAKI[1] - C[1]) / a); v = (-u[1], u[0])
A_ = (C[0] + u[0] * R, C[1] + u[1] * R); B_ = (C[0] - u[0] * R, C[1] - u[1] * R)
s_curve = (arc(NAGOYA[0], NAGOYA[1], a, th + math.pi, th + math.pi + s_side * math.pi)
           + arc(OKAZAKI[0], OKAZAKI[1], a, th + math.pi, th + math.pi - s_side * math.pi))
ext = 1.12 * R
axis = (Q((C[0] - u[0] * ext, C[1] - u[1] * ext)), Q((C[0] + u[0] * ext, C[1] + u[1] * ext)))
perp = (Q((C[0] - v[0] * R, C[1] - v[1] * R)), Q((C[0] + v[0] * R, C[1] + v[1] * R)))
n0 = Q(NAGOYA); o0 = Q(OKAZAKI); cc = Q(C); dot_r = R / 9
re = (cc[0] + R, cc[1])

TBW, TBH = PW, 520
TBX, TBY = PX0, CH - MY - TBH
rows = [("図　名", ["愛知の陰陽図（仮説図）"], True),
        ("仮　説", ["尾張と三河の境は、名古屋城と", "岡崎城を目とする太極図のS字に沿う"], False),
        ("作　図", ["外円の半径＝城と城の距離（34.7km）", "黒の頭に名古屋城、白の頭に岡崎城"], False),
        ("検　証", [f"一致：太極図 {TJ_ALL}％／直線 {EQ_ALL}％"], False),
        ("所　見", ["S字は直線より境に沿ってはいない", "一致は2つの城が別の国にあることから"], False),
        ("出　典", ["国土数値情報（行政区域・2021年）", "国土交通省 を加工して作成"], False),
        ("作　成", ["2026-10-29"], False)]
tb = [f'<rect x="{TBX}" y="{TBY}" width="{TBW}" height="{TBH}" fill="#ffffff" stroke="#111" stroke-width="4"/>']
y = TBY; LW = 130
heights = [70 if r[2] else (40 * len(r[1]) + 22) for r in rows]
scale = TBH / sum(heights); heights = [h * scale for h in heights]
for (lab, lines, big), h in zip(rows, heights):
    tb.append(f'<line x1="{TBX}" y1="{y:.1f}" x2="{TBX + TBW}" y2="{y:.1f}" stroke="#111" stroke-width="1.5"/>')
    tb.append(f'<text class="tbl" x="{TBX + LW / 2}" y="{y + h / 2 + 10:.1f}" text-anchor="middle">{lab}</text>')
    if big:
        tb.append(f'<text class="tbt" x="{TBX + LW + 24}" y="{y + h / 2 + 15:.1f}">{lines[0]}</text>')
    else:
        y0 = y + h / 2 - (len(lines) - 1) * 19 + 9
        for k, ln in enumerate(lines):
            tb.append(f'<text class="tbv" x="{TBX + LW + 24}" y="{y0 + k * 38:.1f}">{ln}</text>')
    y += h
tb.append(f'<line x1="{TBX + LW}" y1="{TBY}" x2="{TBX + LW}" y2="{TBY + TBH}" stroke="#111" stroke-width="1.5"/>')

# ---- 凡例・縮尺 ----
LX, LY, LWID, LHT = PX0, MY, PW, 420
def leg_row(i, sym, text):
    yy = LY + 62 + i * 50
    return sym(LX + 30, yy) + f'<text class="leg" x="{LX + 130}" y="{yy + 10}">{text}</text>'
box = lambda fill, stroke: (lambda x, y: f'<rect x="{x}" y="{y - 14}" width="70" height="28" fill="{fill}" stroke="{stroke}" stroke-width="2"/>')
line = lambda color, dash, w: (lambda x, y: f'<line x1="{x}" y1="{y}" x2="{x + 70}" y2="{y}" stroke="{color}" stroke-width="{w}" stroke-dasharray="{dash}"/>')
legend = [f'<rect x="{LX}" y="{LY}" width="{LWID}" height="{LHT}" fill="#ffffff" stroke="#111" stroke-width="2"/>',
          f'<text class="legh" x="{LX + 24}" y="{LY + 38}">凡　例</text>',
          leg_row(0, box("#1b1b1b", "#1b1b1b"), "尾張（陰）"),
          leg_row(1, box("#ffffff", "#111"), "三河（陽）"),
          leg_row(2, line("#c8381e", "none", 5), "太極図のS字（仮説の境）"),
          leg_row(3, line("#c8381e", "16 10", 3), "太極図の外円"),
          leg_row(4, line("#2f6fb3", "3 9", 4), "等距離線（比較用の直線）"),
          leg_row(5, line("#555", "26 8 4 8", 2), "中心線")]
sb_x, sb_y = LX + 30, LY + LHT - 40
sb = [f'<rect x="{sb_x + i * 10 * km:.1f}" y="{sb_y - 12}" width="{10 * km:.1f}" height="12" fill="{"#111" if i % 2 == 0 else "#fff"}" stroke="#111" stroke-width="1.5"/>' for i in range(3)]
sb += [f'<text class="sbt" x="{sb_x + i * 10 * km:.1f}" y="{sb_y + 26}" text-anchor="middle">{i * 10}</text>' for i in range(4)]
sb.append(f'<text class="sbt" x="{sb_x + 30 * km + 22:.1f}" y="{sb_y + 26}">km</text>')
VX, VY, VW = PX0, MY + 420 + 40, PW
VH = TBY - 40 - VY
vt = [f'<rect x="{VX}" y="{VY}" width="{VW}" height="{VH}" fill="#ffffff" stroke="#111" stroke-width="2"/>',
      f'<text class="legh" x="{VX + 24}" y="{VY + 44}">検証の方法</text>']
for k, ln in enumerate(["円の内側の陸地に、格子状に約2万の点を置く",
                        "各点が尾張か三河かを、行政区域で判定する",
                        "太極図・等距離線の塗り分けと突き合わせる",
                        "（格子の間隔は約0.4km）"]):
    vt.append(f'<text class="leg" x="{VX + 24}" y="{VY + 100 + k * 46}">・{ln}</text>')
cols = [VX + 24, VX + 330, VX + 500, VX + 660]
ty = VY + 340
for k, h in enumerate(["", "全体", "尾張", "三河"]):
    vt.append(f'<text class="legh" x="{cols[k]}" y="{ty}">{h}</text>')
vt.append(f'<line x1="{VX + 20}" y1="{ty + 16}" x2="{VX + VW - 20}" y2="{ty + 16}" stroke="#111" stroke-width="1.5"/>')
for r, (name, vals, col) in enumerate([("太極図のS字", (TJ_ALL, TJ_O, TJ_M), "#c8381e"), ("等距離線", (EQ_ALL, EQ_O, EQ_M), "#2f6fb3")]):
    yy = ty + 66 + r * 56
    vt.append(f'<text class="leg" x="{cols[0]}" y="{yy}" fill="{col}" style="fill:{col};font-weight:700">{name}</text>')
    for k, val in enumerate(vals):
        vt.append(f'<text class="leg" x="{cols[k + 1]}" y="{yy}">{val}%</text>')
for k, ln in enumerate(["→ 差は0.1ポイントで、無いに等しい。", "　 S字の形が境に沿っている証拠にはならない"]):
    vt.append(f'<text class="leg" x="{VX + 24}" y="{ty + 210 + k * 44}" style="font-weight:700">{ln}</text>')
# 方位記号
nx, ny = MX + 110, MY + 150
north = (f'<polygon points="{nx},{ny - 70} {nx + 24},{ny + 30} {nx},{ny + 12} {nx - 24},{ny + 30}" fill="#111"/>'
         f'<text class="nth" x="{nx}" y="{ny - 84}" text-anchor="middle">N</text>')

def T(lon, lat, text, cls, anchor="start"):
    x, y = Q(P(lon, lat)); return f'<text class="{cls}" text-anchor="{anchor}" x="{x:.0f}" y="{y:.0f}">{text}</text>'
neigh_d = "".join(f'<path d="{dpath(f["geometry"])}"/>' for f in neigh)
ow_d = "".join(f'<path d="{dpath(f["geometry"])}"/>' for f in aichi if province(f["properties"]) == "owari")
mk_d = "".join(f'<path d="{dpath(f["geometry"])}"/>' for f in aichi if province(f["properties"]) == "mikawa")
all_d = ow_d + mk_d
svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{CW}" height="{CH}" viewBox="0 0 {CW} {CH}">
<style>
 text{{font-family:'Hiragino Sans','Hiragino Kaku Gothic ProN',sans-serif;paint-order:stroke;stroke-linejoin:round}}
 .nb path{{fill:#f7f7f5;stroke:#c9c9c4;stroke-width:1.2}}
 .ow path{{fill:#1b1b1b;stroke:#4d4d4d;stroke-width:1.2}} .mk path{{fill:#ffffff;stroke:#cfcfcf;stroke-width:1.2}}
 .ol path{{fill:none;stroke:#111;stroke-width:6;stroke-linejoin:round}}
 .prov{{font-weight:700;font-size:64px;letter-spacing:.15em}}
 .castle{{font-weight:700;font-size:34px}}
 .bay{{font-size:32px;fill:#7b8e98;letter-spacing:.2em;font-style:italic}}
 .pref{{font-size:30px;fill:#9a9a94;letter-spacing:.2em}}
 .dim{{font-size:32px;font-weight:700;fill:#c8381e;stroke:#fff;stroke-width:8px}}
 .note{{font-size:26px;fill:#c8381e;stroke:#fff;stroke-width:7px}}
 .tbl{{font-size:26px;font-weight:700;fill:#111}} .tbv{{font-size:27px;fill:#111}}
 .tbt{{font-family:'Hiragino Mincho ProN',serif;font-size:44px;font-weight:600;fill:#111;letter-spacing:.06em}}
 .leg{{font-size:28px;fill:#111}} .legh{{font-size:28px;font-weight:700;fill:#111}}
 .sbt{{font-size:24px;fill:#111}} .nth{{font-size:40px;font-weight:700;fill:#111}}
 .src{{font-size:21px;fill:#777}}
</style>
<defs>
 <clipPath id="mapc"><rect x="{MX}" y="{MY}" width="{W}" height="{H}"/></clipPath>
 <clipPath id="circ"><circle cx="{cc[0]:.1f}" cy="{cc[1]:.1f}" r="{R:.1f}"/></clipPath>
 <mask id="outA" maskUnits="userSpaceOnUse"><rect width="{CW}" height="{CH}" fill="#fff"/><g fill="#000">{all_d}</g></mask>
 <marker id="arr" viewBox="0 0 10 10" refX="10" refY="5" markerWidth="9" markerHeight="9" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="#c8381e"/></marker>
</defs>
<rect width="{CW}" height="{CH}" fill="#ffffff"/>
<g clip-path="url(#mapc)">
 <rect x="{MX}" y="{MY}" width="{W}" height="{H}" fill="#eef2f4"/>
 <g class="nb">{neigh_d}</g>
 <g class="ow">{ow_d}</g><g class="mk">{mk_d}</g>
 <g class="ol" mask="url(#outA)">{all_d}</g>
 <line x1="{perp[0][0]:.1f}" y1="{perp[0][1]:.1f}" x2="{perp[1][0]:.1f}" y2="{perp[1][1]:.1f}" stroke="#2f6fb3" stroke-width="4" stroke-dasharray="3 9" stroke-linecap="round"/>
 <line x1="{axis[0][0]:.1f}" y1="{axis[0][1]:.1f}" x2="{axis[1][0]:.1f}" y2="{axis[1][1]:.1f}" stroke="#777" stroke-width="2" stroke-dasharray="26 8 4 8"/>
 <circle cx="{cc[0]:.1f}" cy="{cc[1]:.1f}" r="{R:.1f}" fill="none" stroke="#c8381e" stroke-width="3" stroke-dasharray="16 10"/>
 <polyline points="{pts(s_curve)}" fill="none" stroke="#ffffff" stroke-width="11" stroke-linecap="round"/>
 <polyline points="{pts(s_curve)}" fill="none" stroke="#c8381e" stroke-width="5" stroke-linecap="round"/>
 <path d="M{cc[0] - 14:.1f},{cc[1]:.1f} h28 M{cc[0]:.1f},{cc[1] - 14:.1f} v28" stroke="#c8381e" stroke-width="3"/>
 <circle cx="{n0[0]:.1f}" cy="{n0[1]:.1f}" r="{dot_r:.1f}" fill="#ffffff" stroke="#c8381e" stroke-width="3"/>
 <circle cx="{o0[0]:.1f}" cy="{o0[1]:.1f}" r="{dot_r:.1f}" fill="#111111" stroke="#c8381e" stroke-width="3"/>
 <line x1="{cc[0]:.1f}" y1="{cc[1]:.1f}" x2="{re[0]:.1f}" y2="{re[1]:.1f}" stroke="#c8381e" stroke-width="2.5" marker-end="url(#arr)"/>
 <text class="dim" text-anchor="middle" x="{cc[0] + R / 2:.0f}" y="{cc[1] - 18:.0f}">R＝34.7 km</text>
 <text class="note" text-anchor="middle" x="{cc[0] + R / 2:.0f}" y="{cc[1] + 40:.0f}">＝名古屋城〜岡崎城の距離</text>
 <text class="castle" text-anchor="end" x="{n0[0] - dot_r - 16:.0f}" y="{n0[1] - dot_r - 10:.0f}" fill="#fff" stroke="#111" stroke-width="7">名古屋城</text>
 <text class="castle" x="{o0[0] + dot_r + 16:.0f}" y="{o0[1] + dot_r + 40:.0f}" fill="#111" stroke="#fff" stroke-width="7">岡崎城</text>
 {T(136.66, 35.06, "尾張（陰）", "prov").replace('class="prov"', 'class="prov" fill="#fff" stroke="#111" stroke-width="10"')}
 {T(137.52, 35.02, "三河（陽）", "prov").replace('class="prov"', 'class="prov" fill="#111" stroke="#fff" stroke-width="10"')}
 {T(136.735, 34.78, "伊勢湾", "bay")}{T(137.10, 34.745, "三河湾", "bay")}{T(137.43, 34.555, "太平洋", "bay")}
 {T(137.02, 35.445, "岐阜県", "pref")}{T(137.80, 34.80, "静岡県", "pref")}
</g>
{"".join(tb)}{"".join(legend)}{"".join(vt)}{"".join(sb)}{north}
<rect x="{MX}" y="{MY}" width="{W}" height="{H}" fill="none" stroke="#111" stroke-width="2"/>
<rect x="30" y="30" width="{CW - 60}" height="{CH - 60}" fill="none" stroke="#111" stroke-width="6"/>
</svg>'''
(OUTDIR / "seizu.svg").write_text(svg)
html = OUTDIR / "seizu.html"
html.write_text(f"<html><head><meta charset='utf-8'><style>html,body{{margin:0}}</style></head><body>{svg}</body></html>")
with sync_playwright() as p:
    b = p.chromium.launch(); pg = b.new_page(viewport={"width": CW, "height": CH})
    pg.goto(html.as_uri()); pg.wait_for_timeout(300)
    pg.screenshot(path=str(OUTDIR / "seizu.png")); b.close()
print(f"{CW}x{CH}")
