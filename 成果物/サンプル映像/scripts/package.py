# -*- coding: utf-8 -*-
"""架空商品「こがね餃子」のパッケージ意匠を、無地の紙箱の写真に刷り込む。

意匠は生成に描かせず、ここで組んでから箱の面に乗せる。文字が崩れないので、
商品名や内容量の差し替えは刷り直すだけで済む。

9/20 に4度作り直した。
 1稿 生成りの地に文字だけ → コーヒー豆や雑穀の袋に見えた
 2稿 白地・赤帯・写真の小窓 → まだ要素が少なく、売り場のものに見えない
 3稿 赤ベタ・断ち切り写真・白フチの極太名。袋を自立袋から平袋に
 4稿 市販の平袋に構成を寄せ、切り抜きの1個と金の枠罫を足す
 5稿（これ）容器を紙箱（カートン）に変えた。パウチだと弧に沿って原稿を
      割り付けるので、大きな文字も金の縁も必ず歪む。紙箱の面は平らなので
      透視だけで乗り、そのぶん派手に振れる。訴求のバッジも増やした

  冷凍餃子の容器を調べた結果（9/20）：
   - 専用の耐寒トレーが入る製品があり、袋はふくらまず板状になる（丸善）
   - 冷凍食品用の紙箱（耐水紙・コートボール）は一般的で、専門の印刷通販が
     冷凍食品向けカートンを扱っている（紙箱・化粧箱.NET、アート印刷所）
   - 通販・ギフトの餃子は化粧箱が主（宇都宮餃子会）
   どのメーカーがどの形、という対応表は見つからなかったので、
   「面が平らで派手に振れる」ことを理由に紙箱を選んでいる
"""
import math
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

FONTS = "/tmp/fonts"
GOTHIC = f"{FONTS}/NotoSansJP-Black.ttf"
ZEN = f"{FONTS}/ZenKakuNew-Black.ttf"

SS = 2
DW, DH = 1000, 880           # 正面の意匠を組む座標（箱の面の比に合わせた）
SW, SH = 1600, 1408          # 原稿の解像度。面（約1410px 幅）より大きく取る
DWS, DHS = 170, 1180         # 側面の意匠を組む座標
SWS, SHS = 340, 2360

# 紙箱の面の四隅（2752x1536 の写真から実測）。時計回り
FRONT = [(633, 200), (2045, 104), (2045, 1455), (633, 1324)]
SIDE = [(2045, 104), (2220, 160), (2220, 1377), (2045, 1455)]

# 金の斜め帯（面に対する割合）。左下の起点・右へ上がる量・太さ
BAND_X0, BAND_Y0, BAND_RISE, BAND_TH = 0.47, 0.835, 0.135, 0.150
PHOTO_FILL, PHOTO_CY = 1.0, 0.50   # 刷る写真の切り方

COPY1 = "羽根パリッ、"
COPY2 = "肉汁じゅわり！"

RED = (183, 27, 31)
RED_D = (126, 14, 18)
GOLD = (233, 189, 70)
GOLD_D = (168, 124, 26)
WHITE = (252, 250, 246)
INK = (36, 26, 24)


def _tw(d, text, font, track):
    return sum(d.textlength(c, font=font) for c in text) + track * (len(text) - 1)


def _tt(d, cx, y, text, font, track, fill, stroke=0, stroke_fill=None):
    """字間を空けて中央に。字間ゼロの行はまとめて描く（約物が上に浮くため）。"""
    if track <= 0:
        d.text((cx, y), text, font=font, fill=fill, anchor="mt",
               stroke_width=stroke, stroke_fill=stroke_fill)
        return
    x = cx - _tw(d, text, font, track) / 2
    for ch in text:
        d.text((x, y), ch, font=font, fill=fill, anchor="lt",
               stroke_width=stroke, stroke_fill=stroke_fill)
        x += d.textlength(ch, font=font) + track


def _lift(img, gamma=0.60, sat=1.18):
    """箱に刷る写真だけ暗部を起こす。売り場で沈まないように。"""
    a = np.asarray(img).astype(np.float32) / 255.0
    a = np.clip(a, 0, 1) ** gamma
    g = a.mean(2, keepdims=True)
    a = np.clip(g + (a - g) * sat, 0, 1)
    return Image.fromarray((a * 255).astype(np.uint8))


def _ground(w, h):
    """赤の地。上下にグラデーションを入れる（ベタ1色は印刷に見えない）。"""
    gr = np.linspace(0, 1, h)[:, None]
    a = np.zeros((h, w, 3), np.float32)
    for i in range(3):
        a[..., i] = RED[i] * (1.0 - 0.16 * gr) + RED_D[i] * (0.16 * gr)
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))


def _badge(img, cx, cy, hw, hh, lines, k):
    """赤丸（縦楕円）のバッジ。lines は (文字, 級数, 色) の並び。"""
    d = ImageDraw.Draw(img)
    d.ellipse([cx - hw, cy - hh, cx + hw, cy + hh], fill=RED_D,
              outline=GOLD, width=int(4 * k))
    total = sum(sz for _, sz, _ in lines) + 4 * (len(lines) - 1)
    y = cy - total * k / 2 - 4 * k
    for text, sz, col in lines:
        f = ImageFont.truetype(GOTHIC, int(sz * k))
        d.text((cx, y), text, font=f, fill=col, anchor="mt")
        y += (sz + 4) * k


def _star(img, cx, cy, r, points, k, lines):
    """金の星型バッジ。売り場の「新発売」はだいたいこの形。"""
    d = ImageDraw.Draw(img)
    pts = []
    for i in range(points * 2):
        a = -math.pi / 2 + i * math.pi / points
        rr = r if i % 2 == 0 else r * 0.76
        pts.append((cx + rr * math.cos(a), cy + rr * math.sin(a)))
    d.polygon(pts, fill=GOLD, outline=GOLD_D)
    total = sum(sz for _, sz in lines) + 3 * (len(lines) - 1)
    y = cy - total * k / 2 - 3 * k
    for text, sz in lines:
        f = ImageFont.truetype(GOTHIC, int(sz * k))
        d.text((cx, y), text, font=f, fill=RED_D, anchor="mt")
        y += (sz + 3) * k


def build_art(photo, hero=None):
    """正面の意匠を返す。photo は商品写真、hero は切り抜きの1個。"""
    W, H = SW * SS, SH * SS
    k = W / DW                      # 意匠の座標（DW×DH）から画素への倍率
    img = _ground(W, H)

    # 商品写真を面の左いっぱいに敷く。右だけ抜いて赤に渡す
    pw, ph = int(700 * k), H
    # 紙箱は地が白くて明るいぶん、写真を起こしすぎると白茶けた
    p = _lift(photo, gamma=0.80, sat=1.12)
    sw, sh = p.size
    ch = int(sh * PHOTO_FILL)
    cw = int(ch * pw / ph)
    cx0 = max(0, min(sw - cw, int(sw * 0.50 - cw / 2)))
    cy0 = max(0, min(sh - ch, int(sh * PHOTO_CY - ch / 2)))
    p = p.crop((cx0, cy0, cx0 + cw, cy0 + ch)).resize((pw, ph), Image.LANCZOS)
    xx = np.arange(pw)[None, :].astype(np.float32)
    ed = (np.linspace(575, 690, ph, dtype=np.float32) * k)[:, None]
    mk = np.clip((ed - xx) / (130 * k), 0, 1) ** 0.85
    img.paste(p, (0, 0), Image.fromarray((mk * 255).astype(np.uint8)))
    d = ImageDraw.Draw(img)

    f_logo_s = ImageFont.truetype(GOTHIC, int(14 * k))
    f_logo = ImageFont.truetype(GOTHIC, int(33 * k))
    f_n1 = ImageFont.truetype(GOTHIC, int(88 * k))
    f_n2 = ImageFont.truetype(GOTHIC, int(238 * k))
    f_rom = ImageFont.truetype(GOTHIC, int(50 * k))
    f_copy1 = ImageFont.truetype(GOTHIC, int(42 * k))
    f_copy2 = ImageFont.truetype(GOTHIC, int(46 * k))
    f_tiny = ImageFont.truetype(ZEN, int(13 * k))
    f_box = ImageFont.truetype(ZEN, int(22 * k))
    f_box_s = ImageFont.truetype(ZEN, int(15 * k))

    # 右下の金の斜め帯。上に細い罫を1本、そのうえにコピーを2行
    band = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    bd = ImageDraw.Draw(band)
    x0, x1 = BAND_X0 * DW, DW
    yt0, yt1 = BAND_Y0 * DH, (BAND_Y0 - BAND_RISE) * DH
    th = BAND_TH * DH
    bd.polygon([(x0 * k, yt0 * k), (x1 * k, yt1 * k),
                (x1 * k, (yt1 + th) * k), (x0 * k, (yt0 + th) * k)],
               fill=GOLD + (255,))
    bd.line([(x0 * k, (yt0 - 14) * k), (x1 * k, (yt1 - 14) * k)],
            fill=GOLD + (235,), width=int(5 * k))
    img.paste(band, (0, 0), band)
    d = ImageDraw.Draw(img)

    ang = math.degrees(math.atan2((yt0 - yt1) * k, (x1 - x0) * k))
    lines = [(COPY1, f_copy1), (COPY2, f_copy2)]
    tw = int(max(_tw(d, t, f, 2 * k) for t, f in lines)) + int(26 * k)
    cop = Image.new("RGBA", (tw, int(110 * k)), (0, 0, 0, 0))
    cd = ImageDraw.Draw(cop)
    yy = int(4 * k)
    for t, f in lines:
        _tt(cd, tw / 2, yy, t, f, 2 * k, RED_D + (255,))
        yy += int(51 * k)
    cop = cop.rotate(ang, expand=True, resample=Image.BICUBIC)
    mx = 0.735
    my = (yt0 - (yt0 - yt1) * (mx * DW - x0) / (x1 - x0) + th / 2) / DH
    img.paste(cop, (int(mx * W - cop.width / 2), int(my * H - cop.height / 2)),
              cop)

    # 右上に切り抜きの1個。同じCMの箸のカットから背景を抜いたもの
    if hero is not None:
        hw = int(396 * k)
        hh = int(hw * hero.height / hero.width)
        hz = hero.resize((hw, hh), Image.LANCZOS)
        sh_ = Image.new("RGBA", (hw, hh), (0, 0, 0, 0))
        sh_.paste((0, 0, 0, 95), (0, 0), hz.split()[3])
        sh_ = sh_.filter(ImageFilter.GaussianBlur(3 * k))
        img.paste(sh_, (int(604 * k), int(34 * k)), sh_)
        img.paste(hz, (int(600 * k), int(26 * k)), hz)
        d = ImageDraw.Draw(img)

    # 商品名。写真の上にまたがらせて、面の幅いっぱいに使う
    ncx = 482 * k
    sx, sy = int(8 * k), int(10 * k)
    _tt(d, ncx + sx, 300 * k + sy, "こがね", f_n1, 11 * k, (70, 10, 12),
        stroke=int(10 * k), stroke_fill=(70, 10, 12))
    _tt(d, ncx, 300 * k, "こがね", f_n1, 11 * k, WHITE,
        stroke=int(10 * k), stroke_fill=(46, 6, 8))
    _tt(d, ncx + sx, 384 * k + sy, "餃子", f_n2, 15 * k, (70, 10, 12),
        stroke=int(18 * k), stroke_fill=(70, 10, 12))
    _tt(d, ncx, 384 * k, "餃子", f_n2, 15 * k, WHITE,
        stroke=int(18 * k), stroke_fill=(46, 6, 8))
    _tt(d, ncx, 652 * k, "GYOZA", f_rom, 12 * k, GOLD,
        stroke=int(5 * k), stroke_fill=(70, 10, 12))

    # 左上：ブランドの白箱
    bx0, by0, bx1, by1 = 34 * k, 30 * k, 266 * k, 126 * k
    d.rounded_rectangle([bx0, by0, bx1, by1], radius=10 * k, fill=WHITE)
    d.text(((bx0 + bx1) / 2, by0 + 12 * k), "FRESH FROZEN", font=f_logo_s,
           fill=(120, 110, 104), anchor="mt")
    d.text(((bx0 + bx1) / 2, by0 + 35 * k), "こがね食品", font=f_logo,
           fill=RED, anchor="mt")

    # 左に訴求のバッジを縦に3つ。売り場の冷凍餃子はここが賑やか
    _badge(img, 104 * k, 292 * k, 62 * k, 62 * k,
           [("油・水", 30, WHITE), ("いらず", 30, WHITE)], k)
    _badge(img, 104 * k, 434 * k, 62 * k, 62 * k,
           [("フタも", 30, WHITE), ("不要", 30, WHITE)], k)
    _badge(img, 104 * k, 600 * k, 70 * k, 84 * k,
           [("元祖", 19, GOLD), ("羽根", 38, WHITE), ("つき", 38, WHITE)], k)
    # 右に金の星バッジ
    _star(img, 886 * k, 452 * k, 82 * k, 12, k, [("新", 34), ("発売", 34)])
    d = ImageDraw.Draw(img)

    d.text((36 * k, 762 * k), "（調理例）", font=f_tiny, fill=WHITE, anchor="lt",
           stroke_width=int(2.4 * k), stroke_fill=(30, 22, 18))

    # 下の情報。白い小箱を並べる
    bxs = [("要冷凍", None), ("12個入り", "(300g)"), ("フライパン", "ひとつで"),
           ("たれ付き", None)]
    x = 34 * k
    y0b, y1b = 800 * k, 848 * k
    for main, sub in bxs:
        w = int((100 if sub else 82) * k)
        d.rectangle([x, y0b, x + w, y1b], fill=WHITE)
        if sub:
            d.text((x + w / 2, y0b + 5 * k), main, font=f_box, fill=RED_D,
                   anchor="mt")
            d.text((x + w / 2, y0b + 28 * k), sub, font=f_box_s, fill=INK,
                   anchor="mt")
        else:
            d.text((x + w / 2, (y0b + y1b) / 2), main, font=f_box, fill=RED_D,
                   anchor="mm")
        x += w + int(9 * k)

    # 面のふちに金の枠。紙箱はこれで全体が締まる
    fr = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    fd = ImageDraw.Draw(fr)
    fd.rounded_rectangle([14 * k, 14 * k, W - 14 * k, H - 14 * k],
                         radius=12 * k, outline=GOLD + (255,), width=int(6 * k))
    fd.rounded_rectangle([28 * k, 28 * k, W - 28 * k, H - 28 * k],
                         radius=8 * k, outline=GOLD_D + (150,), width=int(2 * k))
    img.paste(fr, (0, 0), fr)

    return img.resize((SW, SH), Image.LANCZOS)


def build_side():
    """側面の意匠。赤の地に商品名を縦組みで入れるだけ。"""
    W, H = SWS * SS, SHS * SS
    k = W / DWS
    img = _ground(W, H)
    d = ImageDraw.Draw(img)
    f = ImageFont.truetype(GOTHIC, int(62 * k))
    fs = ImageFont.truetype(ZEN, int(28 * k))
    y = 200 * k
    for ch in "こがね餃子":
        d.text((DWS * k / 2, y), ch, font=f, fill=WHITE, anchor="mt")
        y += 72 * k
    y += 44 * k
    for ch in "要冷凍":
        d.text((DWS * k / 2, y), ch, font=fs, fill=GOLD, anchor="mt")
        y += 34 * k
    fr = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(fr).rectangle([11 * k, 15 * k, W - 11 * k, H - 15 * k],
                                 outline=GOLD + (220,), width=int(5 * k))
    img.paste(fr, (0, 0), fr)
    return img.resize((SWS, SHS), Image.LANCZOS)


def _persp(dst, src):
    """dst の4点を src の4点へ写す係数。PIL の transform は出力→入力で引く。"""
    A, B = [], []
    for (x, y), (u, v) in zip(dst, src):
        A.append([x, y, 1, 0, 0, 0, -u * x, -u * y]); B.append(u)
        A.append([0, 0, 0, x, y, 1, -v * x, -v * y]); B.append(v)
    return np.linalg.solve(np.array(A, np.float64), np.array(B, np.float64))


def place_on_quad(art, size, quad, feather=1.1):
    """原稿を、写真の中の四角形（箱の面）に透視で貼る。rgb と alpha を返す。

    枕型の袋は弧に沿って割り付けていたので、大きな文字も金の縁も必ず歪んだ。
    紙箱の面は平らなので透視だけで乗る。
    """
    W, H = size
    a = art.convert("RGB")
    sw, sh = a.size
    co = _persp(quad, [(0, 0), (sw, 0), (sw, sh), (0, sh)])
    out = a.transform((W, H), Image.PERSPECTIVE, co, Image.BICUBIC)
    mask = Image.new("L", (W, H), 0)
    ImageDraw.Draw(mask).polygon([tuple(q) for q in quad], fill=255)
    mask = mask.filter(ImageFilter.GaussianBlur(feather))
    return (np.asarray(out).astype(np.float32),
            np.asarray(mask).astype(np.float32) / 255.0)


def print_on(src, dst, photo_path, hero_path=None, seed=4):
    base = Image.open(src).convert("RGB")
    hero = Image.open(hero_path).convert("RGBA") if hero_path else None
    a = np.asarray(base).astype(np.float32)
    lum = a.mean(2)
    out = a.copy()
    rng = np.random.default_rng(seed)
    faces = ((build_art(Image.open(photo_path).convert("RGB"), hero), FRONT),
             (build_side(), SIDE))
    for art, quad in faces:
        rgb, al = place_on_quad(art, base.size, quad)
        # 面ごとに明るさを測り、その面の陰影だけをインクに乗せる
        m = Image.new("L", base.size, 0)
        ImageDraw.Draw(m).polygon([tuple(q) for q in quad], fill=255)
        sel = np.asarray(m) > 200
        ref = float(np.median(lum[sel])) if sel.any() else 200.0
        shade = np.clip(lum / max(ref, 1e-6), 0.62, 1.16)[..., None]
        printed = np.clip(rgb * shade, 0, 255) + rng.normal(0, 1.3, rgb.shape)
        out = out * (1 - al[..., None]) + printed * al[..., None]
    Image.fromarray(np.clip(out, 0, 255).astype(np.uint8)).save(dst)
    return dst


# --- 締めのカット（パッケージに寄る3.4秒）を静止画から作る -------------------
FFMPEG = ("/usr/local/lib/python3.11/dist-packages/imageio_ffmpeg/binaries/"
          "ffmpeg-linux-x86_64-v7.0.2")


def clip(still, out, dur=3.4, cw=1920, chh=1080, fps=24, z0=2730, z1=2560):
    """刷ったパッケージ写真の、正面の中心にゆっくり寄る。

    寄りは 6% ほどに留める。箱は高さ約1350px あるので、これ以上寄せると
    16:9 の枠に下の情報の箱が入らない。
    """
    import subprocess
    src = Image.open(still).convert("RGB")
    sw, sh = src.size
    cx = sum(q[0] for q in FRONT) / 4 * sw / 2752.0
    cy = sum(q[1] for q in FRONT) / 4 * sh / 1536.0
    n = int(round(dur * fps))
    p = subprocess.Popen(
        [FFMPEG, "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
         "-s", f"{cw}x{chh}", "-r", str(fps), "-i", "-",
         "-c:v", "libx264", "-crf", "18", "-preset", "medium",
         "-pix_fmt", "yuv420p", out],
        stdin=subprocess.PIPE, stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL)
    for i in range(n):
        t = i / max(n - 1, 1)
        t = t * t * (3 - 2 * t)
        w = z0 + (z1 - z0) * t
        h = w * chh / cw
        x = min(max(cx - w / 2, 0), sw - w)
        y = min(max(cy - h / 2, 0), sh - h)
        fr = src.resize((cw, chh), Image.LANCZOS, box=(x, y, x + w, y + h))
        p.stdin.write(fr.tobytes())
    p.stdin.close()
    p.wait()
    return out


if __name__ == "__main__":
    import sys
    print(print_on(*sys.argv[1:5]))
