"""ワードマーク（assets/logo-word.svg / logo-word-dark.svg）をつくり直す。

    pip3 install fonttools brotli
    # Inter の静的インスタンスを取る（URLは fonts.googleapis.com/css2?family=Inter:wght@300;500 から）
    curl -s "https://fonts.gstatic.com/.../Inter-300.ttf" -o inter300.ttf
    curl -s "https://fonts.gstatic.com/.../Inter-500.ttf" -o inter500.ttf
    python3 scripts/logo-word.py       # カレントに書き出す。assets/ へコピーする

ヘッダー（assets/site.css の .logo / .logo-dash / .logo-tail）と同じ組み方にしてある。
CSS 側の数値を変えたら、下の定数も合わせること。
文字はアウトライン化する。<text> にすると、フォントの無い環境で字形が変わる。
"""
from fontTools.ttLib import TTFont
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.misc.transform import Transform

def run(ttf, text, fs, tracking, x0, y0=0.0):
    """text を fs px で並べ、SVG の d 文字列と終端 x を返す。y は下向き。"""
    f = TTFont(ttf)
    upm = f['head'].unitsPerEm
    cmap = f.getBestCmap()
    gs = f.getGlyphSet()
    hmtx = f['hmtx']
    s = fs / upm
    ds, x = [], x0
    for ch in text:
        gn = cmap[ord(ch)]
        pen = SVGPathPen(gs)
        # 上向きのフォント座標を下向きの SVG 座標へ。ベースラインを y0 に置く
        gs[gn].draw(TransformPen(pen, Transform(s, 0, 0, -s, x, y0)))
        d = pen.getCommands()
        if d: ds.append(d)
        x += hmtx[gn][0] * s + tracking
    return ' '.join(ds), x

# ヘッダーと同じ組み方（assets/site.css）。1em = 100 で組んで、あとで viewBox に収める
EM = 100.0
MAIN_FS, MAIN_TRACK = EM, 0.01 * EM          # .logo font-weight 500 / letter-spacing .01em
TAIL_FS = 0.82 * EM                          # .logo-tail font-size .82em / weight 300
TAIL_TRACK = 0.005 * TAIL_FS                 # letter-spacing は自身の font-size 基準
TAIL_GAP = 0.04 * TAIL_FS                    # margin-left .04em（自身の font-size 基準）
DASH_W, DASH_H = 0.30 * EM, 0.075 * EM       # .logo-dash
DASH_MARGIN = 0.06 * EM
DASH_LIFT = 0.30 * EM                        # transform: translateY(-.30em)

INK, GOLD = '#1d1d1f', '#b08733'

def build(ink):
    d_so, x = run('inter500.ttf', 'so', MAIN_FS, MAIN_TRACK, 0.0)
    x -= MAIN_TRACK                          # 最後の字のあとに字間は付かない
    dash_x = x + DASH_MARGIN
    # 空の inline-flex 要素のベースラインは下マージン辺。そこから lift ぶん持ち上がる
    dash_y = -DASH_LIFT - DASH_H
    x = dash_x + DASH_W + DASH_MARGIN + TAIL_GAP
    d_tail, x = run('inter300.ttf', 'creative', TAIL_FS, TAIL_TRACK, x)
    x -= TAIL_TRACK
    # 上下は「so」の上端（Inter の cap height）から下端（o のオーバーシュート）まで見る
    f = TTFont('inter500.ttf'); upm = f['head'].unitsPerEm
    cap = f['OS/2'].sCapHeight / upm * MAIN_FS
    top = min(-cap, dash_y)
    bot = 0.0 + 0.012 * MAIN_FS              # o のオーバーシュートぶん
    pad = 0.5
    vb = f'{-pad:.2f} {top-pad:.2f} {x+pad*2:.2f} {bot-top+pad*2:.2f}'
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="{vb}" role="img" aria-label="so-creative">
  <title>so-creative</title>
  <!-- 社名のワードマーク（2026-09-24 に so. から作り直した）。
       ヘッダー（assets/site.css の .logo / .logo-dash / .logo-tail）と同じ組み方で、
       Inter 500 の「so」＋金色の区切り＋Inter 300 の「creative」。
       文字はアウトライン化してあるので、フォントが無くても同じ形で出る。
       作り直すときは、ヘッダー側の数値（.82em / .30em / .075em / .06em / .04em）と合わせること。 -->
  <path fill="{ink}" d="{d_so}"/>
  <rect x="{dash_x:.2f}" y="{dash_y:.2f}" width="{DASH_W:.2f}" height="{DASH_H:.2f}" rx="1" fill="{GOLD}"/>
  <path fill="{ink}" d="{d_tail}"/>
</svg>
'''

open('logo-word.svg','w',encoding='utf-8').write(build(INK))
open('logo-word-dark.svg','w',encoding='utf-8').write(build('#f5f5f7'))
print('できた')
