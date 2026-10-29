"""愛知の陰陽図・仮説図を、A3・1:400,000 の図面（線画・寸法入り）として描く。
出力：zumen.pdf（ベクター）と zumen.png（確認用）。単位は mm（用紙上）と km（実寸）。"""
import json, math, sys, pathlib
from playwright.sync_api import sync_playwright
DATA = pathlib.Path("/tmp/aichi_map/data"); OUT = pathlib.Path(sys.argv[1])
TJ_ALL, EQ_ALL = "89.5", "89.6"

# ---------- 投影（正距円筒・基準緯度35°N）と尺度 ----------
RE = 6371.0; LATR = 35.0
LON0, LON1, LAT0, LAT1 = 136.64, 137.88, 34.53, 35.45
KX = RE * math.cos(math.radians(LATR)) * math.pi / 180; KY = RE * math.pi / 180   # km/度
SC = 2.5                      # 1:400,000 → 1km = 2.5mm
MX0, MY0 = 24.0, 14.0         # 地図枠の左上（mm）
MW = (LON1 - LON0) * KX * SC; MH = (LAT1 - LAT0) * KY * SC
def X(lon): return MX0 + (lon - LON0) * KX * SC
def Y(lat): return MY0 + (LAT1 - lat) * KY * SC
def P(lon, lat): return (X(lon), Y(lat))
def inv(x, y): return (LON0 + (x - MX0) / (KX * SC), LAT1 - (y - MY0) / (KY * SC))
def dms(v, pos, neg):
    h = pos if v >= 0 else neg; v = abs(v); d = int(v); m = int((v - d) * 60); s = (v - d - m / 60) * 3600
    return f"{h}{d}°{m:02d}′{s:04.1f}″"

# ---------- データ ----------
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
aichi = json.load(open(DATA / "pref_23.json"))["features"]
neigh = {c: json.load(open(DATA / f"pref_{c}.json"))["features"] for c in (21, 22, 24, 20)}

# ---------- 線の位相：外周・尾張と三河の境を、辺の共有から取り出す ----------
def key(c): return (round(c[0], 6), round(c[1], 6))
def edges_of(features, tagger):
    cnt = {}
    for f in features:
        t = tagger(f["properties"])
        for ring in rings(f["geometry"]):
            for i in range(len(ring) - 1):
                a, b = key(ring[i]), key(ring[i + 1])
                if a == b: continue
                e = (a, b) if a < b else (b, a)
                cnt.setdefault(e, []).append(t)
    return cnt
ae = edges_of(aichi, province)
outline_e = [e for e, ts in ae.items() if len(ts) == 1]
border_e = [e for e, ts in ae.items() if len(ts) == 2 and set(ts) == {"owari", "mikawa"}]
print("愛知の外周の辺", len(outline_e), " 尾張と三河の境の辺", len(border_e))
def chain(edges):
    adj = {}
    for a, b in edges:
        adj.setdefault(a, []).append(b); adj.setdefault(b, []).append(a)
    used = set(); lines = []
    def walk(start):
        line = [start]; cur = start
        while True:
            nxt = None
            for n in adj[cur]:
                e = (cur, n) if cur < n else (n, cur)
                if e not in used:
                    used.add(e); nxt = n; break
            if nxt is None: break
            line.append(nxt); cur = nxt
        return line
    for v in adj:
        if len(adj[v]) != 2:
            while any(((v, n) if v < n else (n, v)) not in used for n in adj[v]):
                lines.append(walk(v))
    for v in adj:
        while any(((v, n) if v < n else (n, v)) not in used for n in adj[v]):
            lines.append(walk(v))
    return lines
def pl(line): return " ".join(f"{X(lon):.2f},{Y(lat):.2f}" for lon, lat in line)
outline_l = chain(outline_e); border_l = chain(border_e)
neigh_l = []
for c, feats in neigh.items():
    ne = edges_of(feats, lambda p: 1)
    neigh_l += chain([e for e, ts in ne.items() if len(ts) == 1])
owari_d = []
for f in aichi:
    if province(f["properties"]) != "owari": continue
    for ring in rings(f["geometry"]):
        owari_d.append("M" + " L".join(f"{X(c[0]):.2f},{Y(c[1]):.2f}" for c in ring) + "Z")

# ---------- 太極図の幾何（mm） ----------
NAG = (136.89949, 35.18515); OKA = (137.15888, 34.95625)
P1 = P(*NAG); P2 = P(*OKA)
C = ((P1[0] + P2[0]) / 2, (P1[1] + P2[1]) / 2)
Rmm = math.dist(P1, P2); a = Rmm / 2; Rkm = Rmm / SC
th = math.atan2(P2[1] - C[1], P2[0] - C[0]); s = 1
u = (math.cos(th), math.sin(th)); v = (-u[1], u[0])
A = (C[0] + u[0] * Rmm, C[1] + u[1] * Rmm); B = (C[0] - u[0] * Rmm, C[1] - u[1] * Rmm)
def arc(c, r, t0, t1, n=240):
    return [(c[0] + r * math.cos(t0 + (t1 - t0) * i / n), c[1] + r * math.sin(t0 + (t1 - t0) * i / n)) for i in range(n + 1)]
S_curve = arc(P1, a, th + math.pi, th + math.pi + s * math.pi) + arc(P2, a, th + math.pi, th + math.pi - s * math.pi)
dot = Rmm / 9
bearing = (90 + math.degrees(th)) % 360          # 画面の角度 → 北から時計回り
lat1, lon1, lat2, lon2 = map(math.radians, (NAG[1], NAG[0], OKA[1], OKA[0]))
dkm = 2 * RE * math.asin(math.sqrt(math.sin((lat2 - lat1) / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2))
print(f"R(図上)={Rkm:.2f}km  球面距離={dkm:.2f}km  方位角={bearing:.1f}°")
def ptxt(pt): return " ".join(f"{x:.2f},{y:.2f}" for x, y in pt)
Cll = inv(*C); All = inv(*A); Bll = inv(*B)

# ---------- 寸法 ----------
def L(p, q, cls="thin", extra=""):
    return f'<line class="{cls}" x1="{p[0]:.2f}" y1="{p[1]:.2f}" x2="{q[0]:.2f}" y2="{q[1]:.2f}" {extra}/>'
def T(x, y, txt, size=2.5, anchor="start", rot=None, cls="t", halo=True, weight=None):
    tr = f' transform="rotate({rot:.2f} {x:.2f} {y:.2f})"' if rot is not None else ""
    w = f' font-weight="{weight}"' if weight else ""
    return f'<text class="{cls}{" h" if halo else ""}" x="{x:.2f}" y="{y:.2f}" font-size="{size}" text-anchor="{anchor}"{tr}{w}>{txt}</text>'
dims = []
# (1) 外円の半径：Cから東北東へ
ang = math.radians(-18)
e1 = (C[0] + Rmm * math.cos(ang), C[1] + Rmm * math.sin(ang))
dims.append(L(C, e1, "dim", 'marker-end="url(#ar)"'))
mid = (C[0] + 0.62 * Rmm * math.cos(ang), C[1] + 0.62 * Rmm * math.sin(ang))
dims.append(T(mid[0], mid[1] - 1.2, f"R{Rkm:.2f}", 2.5, "middle", math.degrees(ang)))
# (2) S字の半円の半径（それぞれの膨らみの頂点へ）
for cen, t in ((P1, th + math.pi + s * math.pi / 2), (P2, th + math.pi - s * math.pi / 2)):
    q = (cen[0] + a * math.cos(t), cen[1] + a * math.sin(t))
    st = (cen[0] + (dot + 0.8) * math.cos(t), cen[1] + (dot + 0.8) * math.sin(t))
    dims.append(L(st, q, "dim", 'marker-end="url(#ar)"'))
    m = (cen[0] + 0.66 * a * math.cos(t), cen[1] + 0.66 * a * math.sin(t))
    deg = math.degrees(t)
    if 90 < (deg % 360) < 270: deg += 180
    dims.append(T(m[0], m[1] - 1.0, f"R{Rkm / 2:.2f}", 2.5, "middle", deg))
# (3) 軸に沿った直列寸法 P1–C–P2（白の側へずらす）
off = -s * 9.0
def sh(p, d): return (p[0] + v[0] * d, p[1] + v[1] * d)
for p in (P1, C, P2):
    dims.append(L(sh(p, -s * (dot + 1.0) if p is not C else -s * 1.0), sh(p, off - s * 1.5), "dim"))
for p, q in ((P1, C), (C, P2)):
    dims.append(L(sh(p, off), sh(q, off), "dim", 'marker-start="url(#ar)" marker-end="url(#ar)"'))
    m = sh(((p[0] + q[0]) / 2, (p[1] + q[1]) / 2), off - s * 1.3)
    dims.append(T(m[0], m[1], f"{Rkm / 2:.2f}", 2.5, "middle", math.degrees(th)))
# (4) 方位角：Cを通る北の基準線から軸まで
nlen = Rmm + 5
dims.append(L(C, (C[0], C[1] - nlen), "thin"))
dims.append(T(C[0] + 1.0, C[1] - nlen + 0.5, "N（真北）", 2.2))
ra = 24.0
arcp = arc(C, ra, -math.pi / 2, th, 120)
dims.append(f'<polyline class="dim" points="{ptxt(arcp)}" fill="none" marker-start="url(#ar)" marker-end="url(#ar)"/>')
am = (-math.pi / 2 + th) / 2
dims.append(T(C[0] + (ra + 3.2) * math.cos(am), C[1] + (ra + 3.2) * math.sin(am), f"{bearing:.1f}°", 2.5, "middle"))
# (5) 目の直径
for cen, t, lab in ((P1, math.radians(200), "φ"), (P2, math.radians(-10), "φ")):
    st = (cen[0] + dot * math.cos(t), cen[1] + dot * math.sin(t))
    en = (cen[0] + (dot + 9) * math.cos(t), cen[1] + (dot + 9) * math.sin(t))
    dims.append(L(en, st, "dim", 'marker-end="url(#ar)"'))
    anchor = "end" if math.cos(t) < 0 else "start"
    dims.append(T(en[0] + (-0.8 if anchor == "end" else 0.8), en[1] + 0.9, f"φ{2 * dot / SC:.2f}", 2.5, anchor))

# ---------- 点の名前（引出線） ----------
def leader(pt, dx, dy, text, anchor, hl=14):
    q = (pt[0] + dx, pt[1] + dy); e = (q[0] + (-hl if anchor == "end" else hl), q[1])
    return L(pt, q, "thin") + L(q, e, "thin") + \
        T(e[0] + (-0.6 if anchor == "end" else 0.6), e[1] + 0.9, text, 3.0, anchor, weight=700)
marks = [leader((P1[0] - dot * 0.7, P1[1] + dot * 0.7), -3, 13, "P1 名古屋城（白の目）", "end", 4),
         leader((P2[0] + dot * 0.7, P2[1] + dot * 0.7), 8, 10, "P2 岡崎城（黒の目）", "start"),
         T(C[0] - 2.2, C[1] + 4.0, "C", 3.0, "end", weight=700),
         T(A[0] + 1.5, A[1] + 3.5, "A", 3.0, weight=700), T(B[0] - 1.5, B[1] - 1.5, "B", 3.0, "end", weight=700)]

# ---------- 経緯線 ----------
grat = []; gratt = []
for m in range(40, 60, 10):  # 136°40′, 136°50′
    pass
for lon10 in range(int(LON0 * 6) + 1, int(LON1 * 6) + 1):
    lon = lon10 / 6; x = X(lon)
    grat.append(f'<line class="grat" x1="{x:.2f}" y1="{MY0}" x2="{x:.2f}" y2="{MY0 + MH:.2f}"/>')
    d = int(lon); mnt = round((lon - d) * 60)
    gratt.append(T(x, MY0 + MH - 1.6, f"{d}°{mnt:02d}′E", 2.2, "middle"))
for lat10 in range(int(LAT0 * 6) + 1, int(LAT1 * 6) + 1):
    lat = lat10 / 6; y = Y(lat)
    grat.append(f'<line class="grat" x1="{MX0}" y1="{y:.2f}" x2="{MX0 + MW:.2f}" y2="{y:.2f}"/>')
    d = int(lat); mnt = round((lat - d) * 60)
    gratt.append(T(MX0 + 1.2, y - 0.8, f"{d}°{mnt:02d}′N", 2.2))

# ---------- 地名 ----------
def TL(lon, lat, txt, size, anchor="middle", cls="t", weight=None):
    x, y = P(lon, lat); return T(x, y, txt, size, anchor, cls=cls, weight=weight)
names = [TL(136.80, 35.03, "尾張（陰）", 5, weight=700), TL(137.56, 35.02, "三河（陽）", 5, weight=700),
         TL(136.745, 34.79, "伊勢湾", 3.5, cls="it"), TL(137.10, 34.748, "三河湾", 3.5, cls="it"),
         TL(137.45, 34.555, "太平洋", 3.5, cls="it"),
         TL(137.03, 35.435, "岐阜県", 3.0, cls="g"), TL(137.80, 34.80, "静岡県", 3.0, cls="g"),
         TL(136.668, 35.07, "三重県", 2.5, "start", cls="g"), TL(137.78, 35.43, "長野県", 3.0, cls="g")]

# ---------- 右の欄 ----------
PX0, PX1 = 312.0, 406.0; PW = PX1 - PX0
panel = []
def box(y0, h, title):
    panel.append(f'<rect class="frame35" x="{PX0}" y="{y0:.2f}" width="{PW}" height="{h:.2f}" fill="#fff"/>')
    panel.append(T(PX0 + 2.5, y0 + 5.2, title, 3.5, halo=False, weight=700))
y = 14.0
notes = ["1. 太極図の目（小円の中心）を、名古屋城天守（P1）と",
         "　 岡崎城天守（P2）の位置に置く。",
         f"2. 外円の半径 R は目と目の距離に等しい（R＝{Rkm:.2f}）。",
         "　 S字は P1・P2 を中心とする半径 R/2 の半円2つ。",
         "3. 黒の頭（P1 側）を尾張、白の頭（P2 側）を三河にあてる。",
         f"4. 目の直径は 2R/9（φ{2 * dot / SC:.2f}）とする（作図上の約束）。",
         "5. 等距離線（P1・P2 から等しい距離の直線）は、C を通る",
         "　 直交中心線と一致する。",
         "6. 検証：円内の陸地で、尾張・三河の塗り分けと一致した",
         f"　 割合は 太極図 {TJ_ALL}％／等距離線 {EQ_ALL}％。S字の優位はない。",
         "7. 境界は国土数値情報を簡略化した線で、細部は省く。"]
box(y, 8.5 + 4.6 * len(notes), "注記")
for i, ln in enumerate(notes):
    panel.append(T(PX0 + 2.5, y + 11.5 + i * 4.6, ln, 2.5, halo=False))
y += 8.5 + 4.6 * len(notes) + 4
rows = [("点", "名称", "緯度", "経度"),
        ("P1", "名古屋城天守", dms(NAG[1], "N", "S"), dms(NAG[0], "E", "W")),
        ("P2", "岡崎城天守", dms(OKA[1], "N", "S"), dms(OKA[0], "E", "W")),
        ("C", "太極図の中心", dms(Cll[1], "N", "S"), dms(Cll[0], "E", "W")),
        ("A", "軸の端（P2側）", dms(All[1], "N", "S"), dms(All[0], "E", "W")),
        ("B", "軸の端（P1側）", dms(Bll[1], "N", "S"), dms(Bll[0], "E", "W"))]
hgt = 8.5 + 4.8 * len(rows) + 1
box(y, hgt, "座標表（JGD2011）")
cx = [PX0 + 2.5, PX0 + 10, PX0 + 38, PX0 + 64]
for i, r in enumerate(rows):
    yy = y + 12 + i * 4.8
    for k, c in enumerate(r):
        panel.append(T(cx[k], yy, c, 2.4, halo=False, weight=700 if i == 0 else None))
    if i == 0:
        panel.append(L((PX0 + 2, yy + 1.4), (PX1 - 2, yy + 1.4), "thin"))
y += hgt + 4
dimrows = [("外円の半径 R", f"{Rkm:.2f} km"), ("S字の半円の半径 R/2", f"{Rkm / 2:.2f} km"),
           ("目の直径 2R/9", f"{2 * dot / SC:.2f} km"), ("軸の方位角（P1→P2）", f"{bearing:.1f}°"),
           ("P1–P2 の球面距離", f"{dkm:.2f} km")]
hgt = 8.5 + 4.8 * len(dimrows) + 1
box(y, hgt, "主要寸法")
for i, (k_, v_) in enumerate(dimrows):
    yy = y + 12 + i * 4.8
    panel.append(T(PX0 + 2.5, yy, k_, 2.5, halo=False)); panel.append(T(PX1 - 3, yy, v_, 2.5, "end", halo=False))
y += hgt + 4
legend = [("thick", "太い実線", "太極図の外形"), ("med", "中太の実線", "県境・海岸線"),
          ("bord", "太い一点鎖線", "尾張と三河の境"), ("cen", "細い一点鎖線", "中心線"),
          ("img", "細い二点鎖線", "作図用の円（想像線）"), ("hat", "細い斜線", "尾張の範囲")]
hgt = 8.5 + 5.2 * len(legend) + 1
box(y, hgt, "線の種類")
for i, (cls, nm, use) in enumerate(legend):
    yy = y + 12 + i * 5.2
    if cls == "hat":
        panel.append(f'<rect x="{PX0 + 3}" y="{yy - 2.6}" width="16" height="3.6" fill="url(#hatch)" stroke="#000" stroke-width="0.18"/>')
    else:
        panel.append(L((PX0 + 3, yy - 0.8), (PX0 + 19, yy - 0.8), cls))
    panel.append(T(PX0 + 22, yy, nm, 2.5, halo=False)); panel.append(T(PX0 + 50, yy, use, 2.5, halo=False))
y += hgt + 4
TB_Y = 287 - 56
assert y <= TB_Y + 0.1, f"右の欄がはみ出し {y:.1f} > {TB_Y}"
tb = [f'<rect class="frame50" x="{PX0}" y="{TB_Y}" width="{PW}" height="56" fill="#fff"/>']
def cell(x0, y0, w, h, lab, val, vsize=2.6):
    out = [f'<rect class="thin" x="{x0:.2f}" y="{y0:.2f}" width="{w:.2f}" height="{h:.2f}" fill="none"/>',
           T(x0 + 1.5, y0 + 3.3, lab, 2.0, halo=False)]
    out.append(T(x0 + 1.5, y0 + h - 2.2, val, vsize, halo=False))
    return out
tb += cell(PX0, TB_Y, PW, 14, "図名", "愛知の陰陽図　仮説図", 5.0)
tb += cell(PX0, TB_Y + 14, PW / 2, 10.5, "図番", "AY-001")
tb += cell(PX0 + PW / 2, TB_Y + 14, PW / 2, 10.5, "尺度", "1 : 400,000")
tb += cell(PX0, TB_Y + 24.5, PW, 10.5, "投影法", "正距円筒図法（基準緯度 35°N）")
tb += cell(PX0, TB_Y + 35, PW / 2, 10.5, "単位", "km（用紙上は mm）")
tb += cell(PX0 + PW / 2, TB_Y + 35, PW / 2, 10.5, "用紙", "A3")
tb += cell(PX0, TB_Y + 45.5, PW / 2, 10.5, "作成", "2026-10-29")
tb += cell(PX0 + PW / 2, TB_Y + 45.5, PW / 2, 10.5, "出典", "国土数値情報（行政区域）", 2.2)

# ---------- 縮尺・方位 ----------
sx, sy = MX0 + 6, MY0 + MH - 9
scale = [T(sx, sy - 4.5, "尺度 1:400,000", 2.5, weight=700)]
for i in range(3):
    scale.append(f'<rect x="{sx + i * 25:.2f}" y="{sy - 1.6:.2f}" width="25" height="1.6" fill="{"#000" if i % 2 == 0 else "#fff"}" stroke="#000" stroke-width="0.18"/>')
for i in range(4):
    scale.append(T(sx + i * 25, sy + 3.2, f"{i * 10}", 2.2, "middle"))
scale.append(T(sx + 75 + 3.5, sy + 3.2, "km", 2.2))
nx, ny = MX0 + 10, MY0 + 14
north = (f'<polygon points="{nx},{ny - 8} {nx + 2.6},{ny + 3} {nx},{ny + 1.2} {nx - 2.6},{ny + 3}" fill="#000"/>'
         + T(nx, ny - 9.5, "N", 3.5, "middle", weight=700))

# ---------- SVG ----------
ext = 6.0
axis = (C[0] - u[0] * (Rmm + ext), C[1] - u[1] * (Rmm + ext), C[0] + u[0] * (Rmm + ext), C[1] + u[1] * (Rmm + ext))
perp = (C[0] - v[0] * (Rmm + ext), C[1] - v[1] * (Rmm + ext), C[0] + v[0] * (Rmm + ext), C[1] + v[1] * (Rmm + ext))
def cross(p, r):
    return (f'<line class="cen" x1="{p[0] - r:.2f}" y1="{p[1]:.2f}" x2="{p[0] + r:.2f}" y2="{p[1]:.2f}"/>'
            f'<line class="cen" x1="{p[0]:.2f}" y1="{p[1] - r:.2f}" x2="{p[0]:.2f}" y2="{p[1] + r:.2f}"/>')
svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="420mm" height="297mm" viewBox="0 0 420 297">
<style>
 text{{font-family:'Hiragino Sans','Hiragino Kaku Gothic ProN',sans-serif;fill:#000}}
 .h{{paint-order:stroke;stroke:#fff;stroke-width:0.9;stroke-linejoin:round}}
 .it{{font-style:italic;fill:#333}} .g{{fill:#555;letter-spacing:.4}}
 .thin{{stroke:#000;stroke-width:0.18;fill:none}} .dim{{stroke:#000;stroke-width:0.18;fill:none}}
 .thick{{stroke:#000;stroke-width:0.5;fill:none;stroke-linecap:round;stroke-linejoin:round}}
 .med{{stroke:#000;stroke-width:0.35;fill:none;stroke-linejoin:round}}
 .nb{{stroke:#666;stroke-width:0.18;fill:none;stroke-linejoin:round}}
 .bord{{stroke:#000;stroke-width:0.5;fill:none;stroke-dasharray:6 1.2 0.6 1.2;stroke-linejoin:round}}
 .cen{{stroke:#000;stroke-width:0.18;fill:none;stroke-dasharray:8 1.2 1 1.2}}
 .img{{stroke:#000;stroke-width:0.18;fill:none;stroke-dasharray:8 1.2 1 1.2 1 1.2}}
 .grat{{stroke:#9a9a9a;stroke-width:0.1}}
 .frame35{{stroke:#000;stroke-width:0.35}} .frame50{{stroke:#000;stroke-width:0.5}}
</style>
<defs>
 <marker id="ar" viewBox="0 0 3 1.2" refX="3" refY="0.6" markerWidth="3" markerHeight="1.2" markerUnits="userSpaceOnUse" orient="auto-start-reverse"><path d="M0,0 L3,0.6 L0,1.2 z" fill="#000"/></marker>
 <pattern id="hatch" patternUnits="userSpaceOnUse" width="1.8" height="1.8" patternTransform="rotate(45)"><line x1="0" y1="0" x2="0" y2="1.8" stroke="#000" stroke-width="0.13"/></pattern>
 <clipPath id="mapc"><rect x="{MX0}" y="{MY0}" width="{MW:.2f}" height="{MH:.2f}"/></clipPath>
</defs>
<rect width="420" height="297" fill="#fff"/>
<g clip-path="url(#mapc)">
 {"".join(grat)}
 <path d="{" ".join(owari_d)}" fill="url(#hatch)" fill-rule="evenodd"/>
 {"".join(f'<polyline class="nb" points="{pl(l)}"/>' for l in neigh_l)}
 {"".join(f'<polyline points="{pl(l)}" fill="none" stroke="#fff" stroke-width="1.4" stroke-linejoin="round"/>' for l in outline_l)}
 {"".join(f'<polyline class="med" points="{pl(l)}"/>' for l in outline_l)}
 {"".join(f'<polyline class="bord" points="{pl(l)}"/>' for l in border_l)}
 <line class="cen" x1="{axis[0]:.2f}" y1="{axis[1]:.2f}" x2="{axis[2]:.2f}" y2="{axis[3]:.2f}"/>
 <line class="cen" x1="{perp[0]:.2f}" y1="{perp[1]:.2f}" x2="{perp[2]:.2f}" y2="{perp[3]:.2f}"/>
 <circle class="img" cx="{P1[0]:.2f}" cy="{P1[1]:.2f}" r="{a:.2f}"/>
 <circle class="img" cx="{P2[0]:.2f}" cy="{P2[1]:.2f}" r="{a:.2f}"/>
 <circle class="thick" cx="{C[0]:.2f}" cy="{C[1]:.2f}" r="{Rmm:.2f}"/>
 <polyline class="thick" points="{ptxt(S_curve)}"/>
 {"".join(dims)}
 <circle cx="{P1[0]:.2f}" cy="{P1[1]:.2f}" r="{dot:.2f}" fill="#fff" stroke="#000" stroke-width="0.5"/>
 <circle cx="{P2[0]:.2f}" cy="{P2[1]:.2f}" r="{dot:.2f}" fill="#000" stroke="#000" stroke-width="0.5"/>
 {cross(P1, dot + 2.5)}{cross(C, 2.5)}
 <line x1="{P2[0] - dot - 2.5:.2f}" y1="{P2[1]:.2f}" x2="{P2[0] + dot + 2.5:.2f}" y2="{P2[1]:.2f}" stroke="#fff" stroke-width="0.18" stroke-dasharray="8 1.2 1 1.2"/>
 <line x1="{P2[0]:.2f}" y1="{P2[1] - dot - 2.5:.2f}" x2="{P2[0]:.2f}" y2="{P2[1] + dot + 2.5:.2f}" stroke="#fff" stroke-width="0.18" stroke-dasharray="8 1.2 1 1.2"/>
 {"".join(marks)}{"".join(names)}{"".join(gratt)}{"".join(scale)}{north}
</g>
<rect class="frame35" x="{MX0}" y="{MY0}" width="{MW:.2f}" height="{MH:.2f}" fill="none"/>
{"".join(panel)}{"".join(tb)}
<rect x="20" y="10" width="390" height="277" fill="none" stroke="#000" stroke-width="0.7"/>
<line x1="210" y1="0" x2="210" y2="12" stroke="#000" stroke-width="0.7"/><line x1="210" y1="285" x2="210" y2="297" stroke="#000" stroke-width="0.7"/>
<line x1="0" y1="148.5" x2="22" y2="148.5" stroke="#000" stroke-width="0.7"/><line x1="408" y1="148.5" x2="420" y2="148.5" stroke="#000" stroke-width="0.7"/>
</svg>'''
(OUT / "zumen.svg").write_text(svg)
html = OUT / "zumen.html"
html.write_text(f"<html><head><meta charset='utf-8'><style>@page{{size:420mm 297mm;margin:0}}html,body{{margin:0}}svg{{display:block}}</style></head><body>{svg}</body></html>")
with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={"width": 1588, "height": 1123}, device_scale_factor=3)
    pg.goto(html.as_uri()); pg.wait_for_timeout(400)
    pg.screenshot(path=str(OUT / "zumen.png"), full_page=False)
    pg.pdf(path=str(OUT / "zumen.pdf"), width="420mm", height="297mm", print_background=True,
           margin={"top": "0", "right": "0", "bottom": "0", "left": "0"})
    b.close()
print("ok", f"地図 {MW:.1f}x{MH:.1f}mm")
