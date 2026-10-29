"""陰陽図の絵を、正確な愛知県の地図と融合させる（2400x1350）。"""
import json, math, sys, pathlib
sys.argv = [sys.argv[0], "/tmp/aichi_map/frames"]
src = open("/tmp/scripts_map/map_frames.py").read()
exec(src.split("def frame(")[0])            # データ・境界（OUTLINE / BORDER / NEIGH）・province など
from playwright.sync_api import sync_playwright
OUT = pathlib.Path("/tmp/aichi_map/fusion"); D = pathlib.Path.home() / "Desktop/絵画_2026-10-27"
W2, H2 = 2400, 1350
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
P1, P2 = P(*NAG), P(*OKA); C = ((P1[0] + P2[0]) / 2, (P1[1] + P2[1]) / 2); R = math.dist(P1, P2)
def sim(src1, src2, dst1, dst2):
    """2点の対応から、回転・拡大・平行移動を作る（SVG の transform 文字列）。"""
    vs = (src2[0] - src1[0], src2[1] - src1[1]); vd = (dst2[0] - dst1[0], dst2[1] - dst1[1])
    s = math.hypot(*vd) / math.hypot(*vs); th = math.degrees(math.atan2(vd[1], vd[0]) - math.atan2(vs[1], vs[0]))
    return f"translate({dst1[0]:.2f} {dst1[1]:.2f}) rotate({th:.3f}) scale({s:.5f}) translate({-src1[0]:.2f} {-src1[1]:.2f})", s, th
TEX = '<filter id="paper"><feTurbulence type="fractalNoise" baseFrequency="0.8" numOctaves="3" seed="7"/><feColorMatrix values="0 0 0 0 0.45  0 0 0 0 0.40  0 0 0 0 0.32  0 0 0 0.10 0"/></filter>'
nb = "".join(f'<polyline points="{pl(l)}" fill="none" stroke="#bdb5a4" stroke-width="1.4"/>' for l in NEIGH)
ol = lambda col, w, op=1: "".join(f'<polyline points="{pl(l)}" fill="none" stroke="{col}" stroke-width="{w}" stroke-opacity="{op}" stroke-linejoin="round"/>' for l in OUTLINE)
bd = lambda col, w, op=1: "".join(f'<polyline points="{pl(l)}" fill="none" stroke="{col}" stroke-width="{w}" stroke-opacity="{op}" stroke-dasharray="14 6 3 6" stroke-linejoin="round"/>' for l in BORDER)
TITLE = (f'<text x="{W2 - 150}" y="150" style="writing-mode:vertical-rl;font-family:\'Hiragino Mincho ProN\',serif;font-weight:600" font-size="110" fill="{INK}" letter-spacing="16">ふたつの目</text>'
         f'<text x="{W2 - 285}" y="220" style="writing-mode:vertical-rl;font-family:\'Hiragino Mincho ProN\',serif;font-weight:600" font-size="50" fill="{GOLD}" letter-spacing="12">愛知の陰陽図</text>')
def label(p, txt, dx, dy, anchor="start", col=INK, halo=PAPER):
    return (f'<text x="{p[0] + dx:.1f}" y="{p[1] + dy:.1f}" text-anchor="{anchor}" font-family="Hiragino Sans" font-weight="700" font-size="30" '
            f'fill="{col}" style="paint-order:stroke" stroke="{halo}" stroke-width="8" stroke-linejoin="round">{txt}</text>')
def render(name, body):
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="{W2}" height="{H2}"><defs>{TEX}'
           f'<filter id="soft"><feGaussianBlur stdDeviation="18"/></filter></defs><rect width="{W2}" height="{H2}" fill="{PAPER}"/>{body}'
           f'<rect width="{W2}" height="{H2}" filter="url(#paper)"/></svg>')
    html = OUT / f"{name}.html"; html.write_text(f"<html><body style='margin:0'>{svg}</body></html>")
    return html

# ---- 1) 金鯱 × 地図：金の玉＝名古屋城、黒い玉＝岡崎城 ----
kin = (D / "陰陽_案1_金鯱_本物の形.png").as_uri()
tf, s1, th1 = sim((1192.74, 1369.80), (846.13, 681.28), P1, P2)
body1 = (f'{nb}<path d="{poly_d("owari")}" fill="#dcd4c3"/><path d="{poly_d("mikawa")}" fill="#f6f1e6"/>{ol(INK, 2.4)}'
         f'<defs><radialGradient id="fade"><stop offset="0.80" stop-color="#fff"/><stop offset="1" stop-color="#000"/></radialGradient>'
         f'<mask id="kmask" maskUnits="userSpaceOnUse" x="0" y="0" width="2048" height="2048"><circle cx="1024" cy="1024" r="1000" fill="url(#fade)"/></mask></defs>'
         f'<g transform="{tf}" style="mix-blend-mode:multiply"><image href="{kin}" width="2048" height="2048" mask="url(#kmask)"/></g>'
         f'{ol(INK, 1.6, 0.55)}{bd(GOLD, 3, 0.85)}'
         f'{label(P1, "名古屋城", -48, 10, "end")}{label(P2, "岡崎城", 48, 10)}{label(P(136.80, 35.31), "尾張", 0, 0, "middle")}{label(P(137.62, 35.20), "三河", 0, 0, "middle")}{TITLE}')
# ---- 2) 尾張と三河 × 地図：太陽＝名古屋城、月＝岡崎城。夜は尾張の形に、昼は三河の形に ----
yin = (D / "陰陽_案2_尾張と三河_v2.png").as_uri()
c0, Rt, at, dt = 1024, 2048 * 0.42, 2048 * 0.21, 2048 * 0.42 / 9
def tarc(cx, cy, r, t0, t1, n=160):
    return " ".join(f"{cx + r*math.cos(t0+(t1-t0)*i/n):.1f},{cy + r*math.sin(t0+(t1-t0)*i/n):.1f}" for i in range(n + 1))
dark = tarc(c0, c0, Rt * 0.95, -math.pi/2, -3*math.pi/2) + " " + tarc(c0, c0 + at, at, math.pi/2, -math.pi/2) + " " + tarc(c0, c0 - at, at, math.pi/2, 3*math.pi/2)
light = tarc(c0, c0, Rt * 0.95, -math.pi/2, math.pi/2) + " " + tarc(c0, c0 + at, at, math.pi/2, -math.pi/2) + " " + tarc(c0, c0 - at, at, math.pi/2, 3*math.pi/2)
S2 = 1.15   # 絵の拡大率（尾張・三河をそれぞれ覆う大きさ）
tf_n = f"translate({P1[0]:.1f} {P1[1]:.1f}) scale({S2}) translate({-1027.09:.2f} {-1457.21:.2f})"   # 太陽→名古屋城
tf_d = f"translate({P2[0]:.1f} {P2[1]:.1f}) scale({S2}) translate({-1028.95:.2f} {-598.70:.2f})"    # 月→岡崎城
body2 = (f'{nb}<defs><clipPath id="cow"><path d="{poly_d("owari")}"/></clipPath><clipPath id="cmk"><path d="{poly_d("mikawa")}"/></clipPath>'
         f'<mask id="mdark" maskUnits="userSpaceOnUse" x="-400" y="-400" width="2848" height="2848"><polygon points="{dark}" fill="#fff" filter="url(#soft)"/></mask>'
         f'<mask id="mlight" maskUnits="userSpaceOnUse" x="-400" y="-400" width="2848" height="2848"><polygon points="{light}" fill="#fff" filter="url(#soft)"/></mask></defs>'
         f'<g clip-path="url(#cow)"><rect width="{W2}" height="{H2}" fill="#1d2140"/><g transform="{tf_n}"><image href="{yin}" width="2048" height="2048" mask="url(#mdark)"/></g></g>'
         f'<g clip-path="url(#cmk)"><rect width="{W2}" height="{H2}" fill="#dfe6e8"/><g transform="{tf_d}"><image href="{yin}" width="2048" height="2048" mask="url(#mlight)"/></g></g>'
         f'{ol(INK, 2.6)}{bd(GOLD, 4, 0.95)}'
         f'<circle cx="{C[0]:.1f}" cy="{C[1]:.1f}" r="{R:.1f}" fill="none" stroke="{GOLD}" stroke-width="3" stroke-opacity="0.9"/>'
         f'{label(P1, "名古屋城", -60, -40, "end", "#fff", "#1d2140")}{label(P2, "岡崎城", 60, 12)}'
         f'{label(P(136.80, 35.31), "尾張（夜）", 0, 0, "middle")}{label(P(137.62, 35.20), "三河（昼）", 0, 0, "middle")}{TITLE}')
with sync_playwright() as p:
    b = p.chromium.launch(); pg = b.new_page(viewport={"width": W2, "height": H2})
    for name, body in (("fusion_kinshachi", body1), ("fusion_owari_mikawa", body2)):
        pg.goto(render(name, body).as_uri()); pg.wait_for_timeout(1500)
        pg.screenshot(path=str(OUT / f"{name}.png"))
    b.close()
print(f"金鯱: 拡大 {s1:.3f}・回転 {th1:.1f}°")
