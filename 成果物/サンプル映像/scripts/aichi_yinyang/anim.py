"""地図カットのアニメーション（24fps・1920x1080）。SVGを1枚読み込み、JSでコマごとに状態を変えて書き出す。"""
import json, math, sys, pathlib, subprocess
sys.argv = [sys.argv[0], "/tmp/aichi_map/frames"]
src = open("/tmp/scripts_map/map_frames.py").read()
exec(src.split("def frame(")[0])                       # データ・境界の取り出しまで
from playwright.sync_api import sync_playwright
OUT = pathlib.Path("/tmp/aichi_map/anim")
clon, clat, ppk = 137.26, 34.99, 9.38
def P(lon, lat): return (W / 2 + (lon - clon) * KX * ppk, H / 2 - (lat - clat) * KY * ppk)
def pl(line): return " ".join(f"{P(*c)[0]:.1f},{P(*c)[1]:.1f}" for c in line)
def poly_d(which):
    out = []
    for f in aichi:
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
u = (math.cos(th), math.sin(th)); v = (-u[1], u[0])
ga = math.radians(-20); ge = (C[0] + R * math.cos(ga), C[1] + R * math.sin(ga)); gm = (C[0] + 0.55 * R * math.cos(ga), C[1] + 0.55 * R * math.sin(ga))
NS = 'vector-effect="non-scaling-stroke"'
def vt(x, y, big, num):
    return (f'<text class="v" x="{x}" y="{y}" font-size="54" fill="{GOLD}">{num}</text>'
            f'<text class="v" x="{x}" y="{y + 90}" font-size="64" fill="{INK}" letter-spacing="10">{big}</text>')
svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">
<style>
 .m{{font-family:'Hiragino Mincho ProN',serif;font-weight:600}}
 .s{{font-family:'Hiragino Sans',sans-serif;font-weight:700;fill:{INK};paint-order:stroke;stroke:{PAPER};stroke-width:7px;stroke-linejoin:round}}
 .v{{writing-mode:vertical-rl;font-family:'Hiragino Mincho ProN',serif;font-weight:600}}
</style>
<defs>
 <filter id="paper"><feTurbulence type="fractalNoise" baseFrequency="0.8" numOctaves="3" seed="7"/><feColorMatrix values="0 0 0 0 0.45  0 0 0 0 0.40  0 0 0 0 0.32  0 0 0 0.10 0"/></filter>
 <filter id="glow" x="-20%" y="-20%" width="140%" height="140%"><feGaussianBlur stdDeviation="7"/></filter>
 <filter id="soft"><feGaussianBlur stdDeviation="30"/></filter>
 <mask id="inkm" maskUnits="userSpaceOnUse" x="-2000" y="-2000" width="6000" height="6000"><rect x="-2000" y="-2000" width="6000" height="6000" fill="#000"/><circle id="inkc" cx="{P1[0]:.1f}" cy="{P1[1]:.1f}" r="3000" fill="#fff" filter="url(#soft)"/></mask>
 <marker id="ar" viewBox="0 0 10 10" refX="10" refY="5" markerWidth="9" markerHeight="9" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="{GOLD}"/></marker>
</defs>
<rect width="{W}" height="{H}" fill="{PAPER}"/>
<g id="world">
 <g id="nb">{"".join(f'<polyline points="{pl(l)}" fill="none" stroke="#bdb5a4" stroke-width="1.3" {NS}/>' for l in NEIGH)}</g>
 <path id="mkf" d="{poly_d("mikawa")}" fill="{WHITE}"/>
 <path id="owf" d="{poly_d("owari")}" fill="{INK}" fill-opacity="0.94" mask="url(#inkm)"/>
 <g id="ol">{"".join(f'<polyline class="olp" points="{pl(l)}" fill="none" stroke="{INK}" stroke-width="2.4" stroke-linejoin="round" {NS}/>' for l in OUTLINE)}</g>
 <g id="bg" filter="url(#glow)">{"".join(f'<polyline points="{pl(l)}" fill="none" stroke="{GOLD}" stroke-width="9" stroke-linecap="round" stroke-linejoin="round"/>' for l in BORDER)}</g>
 <g id="bl">{"".join(f'<polyline points="{pl(l)}" fill="none" stroke="#f6d77a" stroke-width="3" stroke-linejoin="round" {NS}/>' for l in BORDER)}</g>
 <circle id="gc" cx="{C[0]:.1f}" cy="{C[1]:.1f}" r="{R:.1f}" fill="none" stroke="{GOLD}" stroke-width="4" {NS}/>
 <line id="gr" x1="{C[0]:.1f}" y1="{C[1]:.1f}" x2="{ge[0]:.1f}" y2="{ge[1]:.1f}" stroke="{GOLD}" stroke-width="2.5"/>
 <path id="gra" d="M0,-9 L18,0 L0,9 z" fill="{GOLD}" transform="translate({ge[0]:.1f} {ge[1]:.1f}) rotate(-20) translate(-18 0)"/>
 <text id="grl" class="m" x="{gm[0]:.1f}" y="{gm[1] - 14:.1f}" font-size="34" fill="{GOLD}" text-anchor="middle" transform="rotate(-20 {gm[0]:.1f} {gm[1]:.1f})">R 34.7km</text>
 <path id="gx" d="M{C[0]-10:.1f},{C[1]:.1f} h20 M{C[0]:.1f},{C[1]-10:.1f} v20" stroke="{GOLD}" stroke-width="2.5"/>
 <circle id="p1" cx="{P1[0]:.1f}" cy="{P1[1]:.1f}" r="7" fill="{INK}"/><circle id="p2" cx="{P2[0]:.1f}" cy="{P2[1]:.1f}" r="7" fill="{INK}"/>
 <circle id="ic" cx="{C[0]:.1f}" cy="{C[1]:.1f}" r="{R:.1f}" fill="none" stroke="{INK}" stroke-width="3.5" {NS}/>
 <polyline id="sh" points="{sp}" fill="none" stroke="{WHITE}" stroke-width="9" stroke-linecap="round" {NS}/>
 <polyline id="si" points="{sp}" fill="none" stroke="{INK}" stroke-width="3.5" stroke-linecap="round" {NS}/>
 <polyline id="sg" points="{sp}" fill="none" stroke="{GOLD}" stroke-width="6" stroke-linecap="round" {NS}/>
 <line id="eq" x1="{C[0] - v[0] * R:.1f}" y1="{C[1] - v[1] * R:.1f}" x2="{C[0] + v[0] * R:.1f}" y2="{C[1] + v[1] * R:.1f}" stroke="#7d7d7d" stroke-width="4" stroke-dasharray="4 12" stroke-linecap="round"/>
 <g id="e1" transform-origin="{P1[0]:.1f} {P1[1]:.1f}"><circle cx="{P1[0]:.1f}" cy="{P1[1]:.1f}" r="{dot:.1f}" fill="{WHITE}" stroke="{INK}" stroke-width="3.5" {NS}/></g>
 <g id="e2" transform-origin="{P2[0]:.1f} {P2[1]:.1f}"><circle cx="{P2[0]:.1f}" cy="{P2[1]:.1f}" r="{dot:.1f}" fill="{INK}" stroke="{INK}" stroke-width="3.5" {NS}/></g>
 <circle id="q1a" cx="{P1[0]:.1f}" cy="{P1[1]:.1f}" r="{dot:.1f}" fill="none" stroke="{GOLD}" stroke-width="4" {NS}/><circle id="q1b" cx="{P1[0]:.1f}" cy="{P1[1]:.1f}" r="{dot:.1f}" fill="none" stroke="{GOLD}" stroke-width="4" {NS}/>
 <circle id="q2a" cx="{P2[0]:.1f}" cy="{P2[1]:.1f}" r="{dot:.1f}" fill="none" stroke="{GOLD}" stroke-width="4" {NS}/><circle id="q2b" cx="{P2[0]:.1f}" cy="{P2[1]:.1f}" r="{dot:.1f}" fill="none" stroke="{GOLD}" stroke-width="4" {NS}/>
 <g id="lb"><text class="s" x="{P1[0] - dot - 14:.1f}" y="{P1[1] - dot - 6:.1f}" text-anchor="end" font-size="26">名古屋城</text><text class="s" x="{P2[0] + dot + 14:.1f}" y="{P2[1] + dot + 30:.1f}" font-size="26">岡崎城</text></g>
</g>
<g id="tt"><text class="v" x="1760" y="170" font-size="96" fill="{INK}" letter-spacing="14">ふたつの目</text><text class="v" x="1650" y="230" font-size="44" fill="{GOLD}" letter-spacing="10">愛知の陰陽図</text></g>
<g id="ch1">{vt(1760, 150, "白の中の黒", "一")}</g><g id="ch2">{vt(1760, 150, "境の川", "二")}</g>
<g id="ch3">{vt(1760, 150, "黒の中の白", "三")}</g><g id="ch4">{vt(1760, 150, "三百年後", "四")}</g>
<g id="nm"><g id="nmS"><text class="m" x="1560" y="430" font-size="44" fill="{GOLD}">S字</text><text class="m" x="1560" y="500" font-size="76" fill="{INK}">89.5%</text></g>
<g id="nmL"><text class="m" x="1560" y="620" font-size="44" fill="#6f6f6f">直線</text><text class="m" x="1560" y="690" font-size="76" fill="{INK}">89.6%</text></g></g>
<rect width="{W}" height="{H}" filter="url(#paper)" pointer-events="none"/>
</svg>'''
JS = """
const $ = id => document.getElementById(id);
const P1 = %s, P2 = %s, CW = %d, CH = %d, DOT = %f;
const ease = t => t < .5 ? 4*t*t*t : 1 - Math.pow(-2*t+2, 3)/2;
const seg = (t, a, b) => Math.min(1, Math.max(0, (t - a) / (b - a)));
const pop = p => p <= 0 ? 0 : (p >= 1 ? 1 : 1 + 2.70158*Math.pow(p-1,3) + 1.70158*Math.pow(p-1,2));
function op(id, o){ $(id).style.opacity = o; }
function draw(el, p){ const l = el.getTotalLength(); el.style.strokeDasharray = l + ' ' + l; el.style.strokeDashoffset = l * (1 - p); }
function undraw(el){ el.style.strokeDasharray = ''; el.style.strokeDashoffset = ''; }
function zoom(k, cx, cy, e){ const kk = Math.exp(Math.log(k) * e); const x = CW/2 + (cx - CW/2) * e, y = CH/2 + (cy - CH/2) * e;
  $('world').setAttribute('transform', `translate(${CW/2} ${CH/2}) scale(${kk}) translate(${-x} ${-y})`); }
function pulse(a, b, t, t0, t1, t2, t3){ for (const [id, s, e] of [[a, t0, t1], [b, t2, t3]]) { const p = seg(t, s, e); const c = $(id); c.setAttribute('r', DOT * (1 + 2.6 * ease(p))); c.style.opacity = (p > 0 && p < 1) ? 0.9 * (1 - p) : 0; } }
const ALL = ['mkf','owf','bg','bl','gc','gr','gra','grl','gx','p1','p2','ic','sh','si','sg','eq','e1','e2','q1a','q1b','q2a','q2b','lb','tt','ch1','ch2','ch3','ch4','nm','nmS','nmL'];
function reset(){
  ALL.forEach(id => op(id, 0)); op('nb', 1); op('ol', 1);
  document.querySelectorAll('.olp').forEach(undraw); ['gc','gr','si','sh','sg','eq'].forEach(id => undraw($(id)));
  $('inkc').setAttribute('r', 3000); $('world').setAttribute('transform', '');
  $('e1').style.transform = 'scale(1)'; $('e2').style.transform = 'scale(1)'; op('nmS', 1); op('nmL', 1); op('owf', 1); op('mkf', 1);
  $('owf').setAttribute('fill-opacity', 0.94); $('ol').querySelectorAll('polyline').forEach(e => e.setAttribute('stroke', '%s'));
}
function yin(){ ['mkf','owf','ic','sh','si','e1','e2'].forEach(id => op(id, 1)); }
function setFrame(cut, t){
  reset();
  if (cut === 'C01') { op('nb', seg(t, 0, 1.5)); const p = ease(seg(t, 0.2, 4.4)); document.querySelectorAll('.olp').forEach(e => draw(e, p)); op('mkf', 0); op('owf', 0); }
  if (cut === 'C02') { op('mkf', 0); op('owf', 0); op('p1', seg(t, .2, .6)); op('p2', seg(t, .5, .9)); op('lb', seg(t, .4, 1.2));
    op('gc', 1); draw($('gc'), ease(seg(t, 1.0, 3.6))); op('gx', seg(t, 1.0, 1.4)); op('gr', seg(t, 3.4, 3.45)); draw($('gr'), ease(seg(t, 3.4, 4.4))); op('gra', seg(t, 4.3, 4.5)); op('grl', seg(t, 4.0, 4.8)); }
  if (cut === 'C03') { op('lb', 1); op('gc', 1 - seg(t, 0, .6)); op('gx', 1 - seg(t, 0, .6)); op('ic', seg(t, 0, .6));
    op('si', 1); op('sh', 1); const ps = ease(seg(t, .3, 2.2)); draw($('si'), ps); draw($('sh'), ps);
    $('inkc').setAttribute('r', 1300 * ease(seg(t, 1.8, 4.6))); op('mkf', seg(t, 2.4, 4.2));
    const a = pop(seg(t, 5.3, 5.8)), b = pop(seg(t, 5.5, 6.0)); op('e1', a > 0 ? 1 : 0); op('e2', b > 0 ? 1 : 0);
    $('e1').style.transform = `scale(${a})`; $('e2').style.transform = `scale(${b})`;
    op('p1', 1 - seg(t, 5.3, 5.6)); op('p2', 1 - seg(t, 5.5, 5.8)); op('tt', seg(t, 6.2, 7.2)); }
  if (cut === 'C04') { yin(); zoom(2.0, P2[0], P2[1], ease(seg(t, 0, 1.6))); op('ch1', seg(t, .5, 1.4)); }
  if (cut === 'C07') { yin(); pulse('q2a', 'q2b', t, .4, 2.4, 1.0, 3.0); }
  if (cut === 'C08') { yin(); op('bg', ease(seg(t, 0, 1))); op('bl', ease(seg(t, 0, 1))); op('ch2', seg(t, .4, 1.3)); }
  if (cut === 'C12') { yin(); zoom(2.0, P1[0], P1[1], ease(seg(t, 0, 1.6))); op('ch3', seg(t, .5, 1.4)); }
  if (cut === 'C15') { yin(); pulse('q1a', 'q1b', t, .3, 2.0, .8, 2.6); }
  if (cut === 'C16') { yin(); zoom(0.78, CW/2, CH/2, ease(seg(t, 0, 1.5))); op('ch4', seg(t, .4, 1.3)); }
  if (cut === 'C19') { yin(); op('si', 0); op('sh', 0); op('sg', 1); draw($('sg'), ease(seg(t, .2, 1.8))); op('eq', 1); draw($('eq'), ease(seg(t, 1.8, 3.2)));
    op('nm', 1); op('nmS', seg(t, 2.6, 3.4)); op('nmL', seg(t, 3.2, 4.0)); }
  if (cut === 'C20') { yin(); op('si', 0); op('sh', 0); const f = ease(seg(t, .3, 3.0));
    op('sg', 1 - seg(t, 0, 1.2)); op('eq', 1 - seg(t, 0, 1.2)); op('nm', 1 - seg(t, 0, 1.2));
    $('owf').setAttribute('fill-opacity', 0.94 * (1 - f) + 0.11 * f); op('mkf', 1 - 0.88 * f);
    $('ol').querySelectorAll('polyline').forEach(e => e.setAttribute('stroke', f > .5 ? '#9a9286' : '%s')); op('ol', 1 - 0.35 * f);
    pulse('q1a', 'q2a', t, 4.0, 5.8, 4.0, 5.8); }
  if (cut === 'C21') { yin(); const f = ease(seg(t, 0, 1.2)); $('owf').setAttribute('fill-opacity', 0.11 + 0.83 * f); op('mkf', 0.12 + 0.88 * f);
    op('si', seg(t, .2, 1.2)); op('sh', seg(t, .2, 1.2)); op('tt', seg(t, .8, 2.0)); }
}
""" % (json.dumps(P1), json.dumps(P2), W, H, dot, INK, INK)
TL = dict(json.load(open("/tmp/aichi_map/timeline.json")))
DUR = {k: TL[k] for k in ("C01","C02","C03","C04","C07","C08","C12","C15","C16","C19","C20","C21")}
html = OUT / "anim.html"
html.write_text(f"<html><head><meta charset='utf-8'><style>html,body{{margin:0;overflow:hidden}}</style></head><body>{svg}<script>{JS}</script></body></html>")
only = sys.argv[1:] if False else None
with sync_playwright() as p:
    b = p.chromium.launch(); pg = b.new_page(viewport={"width": W, "height": H})
    pg.goto(html.as_uri()); pg.wait_for_timeout(500)
    import os
    pick = os.environ.get('CUTS', '').split()
    for cut, d in DUR.items():
        if pick and cut not in pick: continue
        fd = OUT / cut; fd.mkdir(exist_ok=True)
        for f in range(round(d * 24)):
            pg.evaluate(f"setFrame('{cut}', {f / 24:.5f})")
            pg.screenshot(path=str(fd / f"f{f:04d}.jpg"), type="jpeg", quality=94)
        subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-framerate", "24", "-i", str(fd / "f%04d.jpg"),
                        "-c:v", "libx264", "-crf", "14", "-preset", "medium", "-pix_fmt", "yuv420p", str(OUT / f"{cut}.mp4")], check=True)
        print(cut, "done", flush=True)
    b.close()
