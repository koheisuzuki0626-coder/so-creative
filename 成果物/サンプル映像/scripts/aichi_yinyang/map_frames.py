"""絵コンテ用：地図のカット（1920x1080）を描く。黒・白・金の3色、和紙の地。"""
import json, math, sys, pathlib
from playwright.sync_api import sync_playwright
DATA = pathlib.Path("/tmp/aichi_map/data"); OUT = pathlib.Path(sys.argv[1])
W, H = 1920, 1080
RE = 6371.0; KX = RE * math.cos(math.radians(35.0)) * math.pi / 180; KY = RE * math.pi / 180
INK, PAPER, WHITE, GOLD = "#161616", "#efe8da", "#fbf8f1", "#b8892d"
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
neigh = [json.load(open(DATA / f"pref_{c}.json"))["features"] for c in (21, 22, 24, 20)]
def key(c): return (round(c[0], 6), round(c[1], 6))
def edges_of(features, tagger):
    cnt = {}
    for f in features:
        t = tagger(f["properties"])
        for ring in rings(f["geometry"]):
            for i in range(len(ring) - 1):
                a, b = key(ring[i]), key(ring[i + 1])
                if a == b: continue
                cnt.setdefault((a, b) if a < b else (b, a), []).append(t)
    return cnt
def chain(edges):
    adj = {}
    for a, b in edges:
        adj.setdefault(a, []).append(b); adj.setdefault(b, []).append(a)
    used = set(); lines = []
    def ek(x, y): return (x, y) if x < y else (y, x)
    def walk(st):
        line = [st]; cur = st
        while True:
            nxt = next((n for n in adj[cur] if ek(cur, n) not in used), None)
            if nxt is None: return line
            used.add(ek(cur, nxt)); line.append(nxt); cur = nxt
    for order in (lambda v: len(adj[v]) != 2, lambda v: True):
        for v in adj:
            if order(v):
                while any(ek(v, n) not in used for n in adj[v]):
                    lines.append(walk(v))
    return lines
ae = edges_of(aichi, province)
OUTLINE = chain([e for e, t in ae.items() if len(t) == 1])
BORDER = chain([e for e, t in ae.items() if len(t) == 2 and set(t) == {"owari", "mikawa"}])
NEIGH = []
for feats in neigh:
    ne = edges_of(feats, lambda p: 1)
    NEIGH += chain([e for e, t in ne.items() if len(t) == 1])
NAG = (136.89949, 35.18515); OKA = (137.15888, 34.95625)

def frame(name, view, layers, extra=""):
    clon, clat, ppk = view
    def P(lon, lat): return (W / 2 + (lon - clon) * KX * ppk, H / 2 - (lat - clat) * KY * ppk)
    def pl(line): return " ".join(f"{P(*c)[0]:.1f},{P(*c)[1]:.1f}" for c in line)
    def poly_d(feats, which):
        out = []
        for f in feats:
            if province(f["properties"]) != which: continue
            for ring in rings(f["geometry"]):
                out.append("M" + " L".join(f"{P(*c[:2])[0]:.1f},{P(*c[:2])[1]:.1f}" for c in ring) + "Z")
        return " ".join(out)
    P1, P2 = P(*NAG), P(*OKA)
    C = ((P1[0] + P2[0]) / 2, (P1[1] + P2[1]) / 2); R = math.dist(P1, P2); a = R / 2
    th = math.atan2(P2[1] - C[1], P2[0] - C[0])
    def arc(c, r, t0, t1, n=200):
        return [(c[0] + r * math.cos(t0 + (t1 - t0) * i / n), c[1] + r * math.sin(t0 + (t1 - t0) * i / n)) for i in range(n + 1)]
    S = arc(P1, a, th + math.pi, th + 2 * math.pi) + arc(P2, a, th + math.pi, th)
    sp = " ".join(f"{x:.1f},{y:.1f}" for x, y in S)
    dot = R / 9
    g = []
    L = set(layers)
    fill_op = 0.12 if "faded" in L else 1.0
    if "fills" in L:
        g.append(f'<path d="{poly_d(aichi, "mikawa")}" fill="{WHITE}" fill-opacity="{fill_op}"/>')
        g.append(f'<path d="{poly_d(aichi, "owari")}" fill="{INK}" fill-opacity="{0.9 * fill_op if "faded" in L else 0.94}"/>')
    g.append("".join(f'<polyline points="{pl(l)}" fill="none" stroke="#bdb5a4" stroke-width="1.3"/>' for l in NEIGH))
    oc = "#9a9286" if "faded" in L else INK
    g.append("".join(f'<polyline points="{pl(l)}" fill="none" stroke="{oc}" stroke-width="2.4" stroke-linejoin="round"/>' for l in OUTLINE))
    if "borderglow" in L:
        g.append(f'<g filter="url(#glow)">' + "".join(f'<polyline points="{pl(l)}" fill="none" stroke="{GOLD}" stroke-width="9" stroke-linecap="round" stroke-linejoin="round"/>' for l in BORDER) + "</g>")
        g.append("".join(f'<polyline points="{pl(l)}" fill="none" stroke="#f6d77a" stroke-width="3" stroke-linejoin="round"/>' for l in BORDER))
    if "pts" in L:
        for p in (P1, P2):
            g.append(f'<circle cx="{p[0]:.1f}" cy="{p[1]:.1f}" r="7" fill="{INK}"/>')
    if "gcircle" in L:
        g.append(f'<circle cx="{C[0]:.1f}" cy="{C[1]:.1f}" r="{R:.1f}" fill="none" stroke="{GOLD}" stroke-width="4"/>')
        e = (C[0] + R * math.cos(math.radians(-20)), C[1] + R * math.sin(math.radians(-20)))
        g.append(f'<line x1="{C[0]:.1f}" y1="{C[1]:.1f}" x2="{e[0]:.1f}" y2="{e[1]:.1f}" stroke="{GOLD}" stroke-width="2.5" marker-end="url(#ar)"/>')
        m = (C[0] + 0.55 * R * math.cos(math.radians(-20)), C[1] + 0.55 * R * math.sin(math.radians(-20)))
        g.append(f'<text x="{m[0]:.1f}" y="{m[1] - 14:.1f}" class="m" font-size="34" fill="{GOLD}" text-anchor="middle" transform="rotate(-20 {m[0]:.1f} {m[1]:.1f})">R 34.7km</text>')
        g.append(f'<path d="M{C[0]-10:.1f},{C[1]:.1f} h20 M{C[0]:.1f},{C[1]-10:.1f} v20" stroke="{GOLD}" stroke-width="2.5"/>')
    if "circle" in L:
        cw = 2 if "faded" in L else 3.5
        g.append(f'<circle cx="{C[0]:.1f}" cy="{C[1]:.1f}" r="{R:.1f}" fill="none" stroke="{INK}" stroke-width="{cw}"/>')
    if "scurve" in L:
        g.append(f'<polyline points="{sp}" fill="none" stroke="{WHITE}" stroke-width="9" stroke-linecap="round"/>')
        g.append(f'<polyline points="{sp}" fill="none" stroke="{INK}" stroke-width="3.5" stroke-linecap="round"/>')
    if "scurvegold" in L:
        g.append(f'<polyline points="{sp}" fill="none" stroke="{GOLD}" stroke-width="6" stroke-linecap="round"/>')
        u = (math.cos(th), math.sin(th)); v = (-u[1], u[0])
        g.append(f'<line x1="{C[0] - v[0] * R:.1f}" y1="{C[1] - v[1] * R:.1f}" x2="{C[0] + v[0] * R:.1f}" y2="{C[1] + v[1] * R:.1f}" stroke="#7d7d7d" stroke-width="4" stroke-dasharray="4 12" stroke-linecap="round"/>')
    if "eyes" in L:
        g.append(f'<circle cx="{P1[0]:.1f}" cy="{P1[1]:.1f}" r="{dot:.1f}" fill="{WHITE}" stroke="{INK}" stroke-width="3.5"/>')
        g.append(f'<circle cx="{P2[0]:.1f}" cy="{P2[1]:.1f}" r="{dot:.1f}" fill="{INK}" stroke="{INK}" stroke-width="3.5"/>')
    for tag, p in (("pulse1", P1), ("pulse2", P2)):
        if tag in L:
            for k, op in ((1.6, .9), (2.3, .55), (3.1, .28)):
                g.append(f'<circle cx="{p[0]:.1f}" cy="{p[1]:.1f}" r="{dot * k:.1f}" fill="none" stroke="{GOLD}" stroke-width="4" stroke-opacity="{op}"/>')
    if "labels" in L:
        g.append(f'<text class="s h" x="{P1[0] - dot - 14:.1f}" y="{P1[1] - dot - 6:.1f}" text-anchor="end" font-size="26">名古屋城</text>')
        g.append(f'<text class="s h" x="{P2[0] + dot + 14:.1f}" y="{P2[1] + dot + 30:.1f}" font-size="26">岡崎城</text>')
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">
<style>
 .m{{font-family:'Hiragino Mincho ProN',serif;font-weight:600}}
 .s{{font-family:'Hiragino Sans',sans-serif;font-weight:700;fill:{INK}}}
 .h{{paint-order:stroke;stroke:{PAPER};stroke-width:7px;stroke-linejoin:round}}
 .v{{writing-mode:vertical-rl;font-family:'Hiragino Mincho ProN',serif;font-weight:600}}
</style>
<defs>
 <filter id="paper"><feTurbulence type="fractalNoise" baseFrequency="0.8" numOctaves="3" seed="7"/><feColorMatrix values="0 0 0 0 0.45  0 0 0 0 0.40  0 0 0 0 0.32  0 0 0 0.10 0"/></filter>
 <filter id="glow" x="-20%" y="-20%" width="140%" height="140%"><feGaussianBlur stdDeviation="7"/></filter>
 <marker id="ar" viewBox="0 0 10 10" refX="10" refY="5" markerWidth="9" markerHeight="9" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="{GOLD}"/></marker>
</defs>
<rect width="{W}" height="{H}" fill="{PAPER}"/>
{"".join(g)}
{extra}
<rect width="{W}" height="{H}" filter="url(#paper)"/>
</svg>'''
    html = OUT / f"{name}.html"
    html.write_text(f"<html><head><meta charset='utf-8'><style>html,body{{margin:0}}</style></head><body>{svg}</body></html>")
    return html

def vtitle(x, y, big, small=None, num=None):
    s = ""
    if num:
        s += f'<text class="v" x="{x}" y="{y}" font-size="54" fill="{GOLD}">{num}</text>'
        y += 90
    s += f'<text class="v" x="{x}" y="{y}" font-size="64" fill="{INK}" letter-spacing="10">{big}</text>'
    if small:
        s += f'<text class="v" x="{x - 92}" y="{y + 40}" font-size="36" fill="{GOLD}" letter-spacing="8">{small}</text>'
    return s
BASE = (137.26, 34.99, 9.38)
YIN = ["fills", "circle", "scurve", "eyes"]
specs = {
 "C01": (BASE, []),
 "C02": (BASE, ["pts", "gcircle", "labels"]),
 "C03": (BASE, YIN + ["labels"], f'<text class="v" x="1760" y="170" font-size="96" fill="{INK}" letter-spacing="14">ふたつの目</text><text class="v" x="1650" y="230" font-size="44" fill="{GOLD}" letter-spacing="10">愛知の陰陽図</text>'),
 "C04": ((OKA[0], OKA[1], 9.38 * 2.0), YIN, vtitle(1760, 150, "白の中の黒", None, "一")),
 "C07": (BASE, YIN + ["pulse2"]),
 "C08": (BASE, YIN + ["borderglow"], vtitle(1760, 150, "境の川", None, "二")),
 "C12": ((NAG[0], NAG[1], 9.38 * 2.0), YIN, vtitle(1760, 150, "黒の中の白", None, "三")),
 "C15": (BASE, YIN + ["pulse1"]),
 "C16": ((137.26, 34.99, 9.38 * 0.78), YIN, vtitle(1760, 150, "三百年後", None, "四")),
 "C19": (BASE, ["fills", "circle", "scurvegold", "eyes"],
         f'<text class="m" x="1560" y="430" font-size="44" fill="{GOLD}">S字</text><text class="m" x="1560" y="500" font-size="76" fill="{INK}">89.5%</text>'
         f'<text class="m" x="1560" y="620" font-size="44" fill="#6f6f6f">直線</text><text class="m" x="1560" y="690" font-size="76" fill="{INK}">89.6%</text>'),
 "C20": (BASE, ["fills", "faded", "circle", "eyes"]),
 "C21": (BASE, YIN, f'<text class="v" x="1760" y="170" font-size="96" fill="{INK}" letter-spacing="14">ふたつの目</text><text class="v" x="1650" y="230" font-size="44" fill="{GOLD}" letter-spacing="10">愛知の陰陽図</text>'),
}
pages = [(n,) + ((s + ("",)) if len(s) == 2 else s) for n, s in specs.items()]
with sync_playwright() as p:
    b = p.chromium.launch(); pg = b.new_page(viewport={"width": W, "height": H})
    for n, view, layers, extra in pages:
        h = frame(n, view, layers, extra)
        pg.goto(h.as_uri()); pg.wait_for_timeout(250)
        pg.screenshot(path=str(OUT / f"{n}.png"))
    b.close()
print("ok", len(pages))
