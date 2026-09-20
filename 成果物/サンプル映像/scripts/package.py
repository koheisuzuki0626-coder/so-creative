# -*- coding: utf-8 -*-
"""架空商品「こがね餃子」のパッケージ意匠を、無地の袋の写真に刷り込む。

意匠は生成に描かせず、ここで組んでから袋の面に乗せる。文字が崩れないので、
商品名や内容量の差し替えは刷り直すだけで済む。

9/20 に2度作り直した。
 1稿 生成りの地に文字だけ → コーヒー豆や雑穀の袋に見えた
 2稿 白地・赤帯・写真の小窓 → まだ要素が少なく、売り場のものに見えない
 3稿（これ）売り場の冷凍餃子に寄せた。赤ベタの地、左に断ち切りの商品写真、
      白フチの極太名、金の斜め帯、丸バッジ、下に情報の小箱。袋も自立袋から
      平袋（上から見た置き）に差し替えている
"""
import math
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

FONTS = "/tmp/fonts"
GOTHIC = f"{FONTS}/NotoSansJP-Black.ttf"
ZEN = f"{FONTS}/ZenKakuNew-Black.ttf"

SS = 2
DW, DH = 1000, 700           # 意匠を組む座標
SW, SH = 1500, 1050          # 原稿の解像度。袋の面（約1514px 幅）より大きく取る

# 平袋の面（2752px の写真から実測）。(y, 見かけの半幅, 中心x)
PROF = [(250.0, 730.0, 1399.0), (770.0, 757.0, 1399.0), (1290.0, 730.0, 1399.0)]
Y0, Y1 = 250.0, 1290.0
FILL = 0.98
BULGE = 0.45                 # 枕型のふくらみ

# 金の斜め帯（面に対する割合）。左下の起点・右へ上がる量・太さ
BAND_X0, BAND_Y0, BAND_RISE, BAND_TH = 0.50, 0.795, 0.170, 0.190
PHOTO_FILL, PHOTO_CY = 1.0, 0.50   # 刷る写真の切り方

COPY1 = "羽根パリッ、"
COPY2 = "肉汁じゅわり！"

RED = (183, 27, 31)
RED_D = (126, 14, 18)
GOLD = (233, 189, 70)
GOLD_D = (168, 124, 26)
WHITE = (252, 250, 246)
INK = (36, 26, 24)


def geom(y):
    ys = [p[0] for p in PROF]
    return (float(np.interp(y, ys, [p[1] for p in PROF])) * FILL,
            float(np.interp(y, ys, [p[2] for p in PROF])))


def _tw(d, text, font, track):
    return sum(d.textlength(c, font=font) for c in text) + track * (len(text) - 1)


def _tt(d, cx, y, text, font, track, fill, stroke=0, stroke_fill=None):
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
    """袋に刷る写真だけ暗部を起こす。売り場で沈まないように。"""
    a = np.asarray(img).astype(np.float32) / 255.0
    a = np.clip(a, 0, 1) ** gamma
    g = a.mean(2, keepdims=True)
    a = np.clip(g + (a - g) * sat, 0, 1)
    return Image.fromarray((a * 255).astype(np.uint8))


def build_art(photo, hero=None):
    """袋の面いっぱいの意匠を返す。photo は商品写真、hero は切り抜きの1個。"""
    W, H = SW * SS, SH * SS
    k = W / DW                      # 意匠の座標（DW×DH）から画素への倍率

    # 地の赤。上下にグラデーションを入れる（ベタ1色は印刷に見えない）
    gr = np.linspace(0, 1, H)[:, None]
    base = np.zeros((H, W, 3), np.float32)
    for i in range(3):
        base[..., i] = RED[i] * (1.0 - 0.16 * gr) + RED_D[i] * (0.16 * gr)
    img = Image.fromarray(np.clip(base, 0, 255).astype(np.uint8))

    # 商品写真を面の左いっぱいに敷く。右だけ抜いて赤に渡す
    pw, ph = int(700 * k), H
    # 袋に刷る写真は、焼き上がりの俯瞰から鍋の内側だけを正方で切ったもの
    # （04_pack_photo.png）。皿のカットは台所の背景が入って左半分が沈んだ
    p = _lift(photo, gamma=0.62, sat=1.14)
    sw, sh = p.size
    ch = int(sh * PHOTO_FILL)
    cw = int(ch * pw / ph)
    cx0 = max(0, min(sw - cw, int(sw * 0.50 - cw / 2)))
    cy0 = max(0, min(sh - ch, int(sh * PHOTO_CY - ch / 2)))
    p = p.crop((cx0, cy0, cx0 + cw, cy0 + ch)).resize((pw, ph), Image.LANCZOS)
    xx = np.arange(pw)[None, :].astype(np.float32)
    ed = (np.linspace(575, 675, ph, dtype=np.float32) * k)[:, None]
    mk = np.clip((ed - xx) / (140 * k), 0, 1) ** 0.85
    img.paste(p, (0, 0), Image.fromarray((mk * 255).astype(np.uint8)))
    d = ImageDraw.Draw(img)

    f_logo_s = ImageFont.truetype(GOTHIC, int(13 * k))
    f_logo = ImageFont.truetype(GOTHIC, int(31 * k))
    f_n1 = ImageFont.truetype(GOTHIC, int(80 * k))
    f_n2 = ImageFont.truetype(GOTHIC, int(218 * k))
    f_rom = ImageFont.truetype(GOTHIC, int(46 * k))
    f_copy1 = ImageFont.truetype(GOTHIC, int(40 * k))
    f_copy2 = ImageFont.truetype(GOTHIC, int(44 * k))
    f_badge_s = ImageFont.truetype(GOTHIC, int(17 * k))
    f_badge = ImageFont.truetype(GOTHIC, int(37 * k))
    f_tiny = ImageFont.truetype(ZEN, int(12 * k))
    f_box = ImageFont.truetype(ZEN, int(21 * k))
    f_box_s = ImageFont.truetype(ZEN, int(14 * k))

    # 右下の金の斜め帯。上に細い罫を1本、そのうえにコピーを2行
    band = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    bd = ImageDraw.Draw(band)
    x0, x1 = BAND_X0 * DW, DW
    yt0, yt1 = BAND_Y0 * DH, (BAND_Y0 - BAND_RISE) * DH
    th = BAND_TH * DH
    bd.polygon([(x0 * k, yt0 * k), (x1 * k, yt1 * k),
                (x1 * k, (yt1 + th) * k), (x0 * k, (yt0 + th) * k)],
               fill=GOLD + (255,))
    bd.line([(x0 * k, (yt0 - 13) * k), (x1 * k, (yt1 - 13) * k)],
            fill=GOLD + (235,), width=int(4 * k))
    img.paste(band, (0, 0), band)
    d = ImageDraw.Draw(img)

    ang = math.degrees(math.atan2((yt0 - yt1) * k, (x1 - x0) * k))
    lines = [(COPY1, f_copy1), (COPY2, f_copy2)]
    tw = int(max(_tw(d, t, f, 2 * k) for t, f in lines)) + int(26 * k)
    cop = Image.new("RGBA", (tw, int(106 * k)), (0, 0, 0, 0))
    cd = ImageDraw.Draw(cop)
    yy = int(4 * k)
    for t, f in lines:
        _tt(cd, tw / 2, yy, t, f, 2 * k, RED_D + (255,))
        yy += int(49 * k)
    cop = cop.rotate(ang, expand=True, resample=Image.BICUBIC)
    mx = 0.76
    my = (yt0 - (yt0 - yt1) * (mx * DW - x0) / (x1 - x0) + th / 2) / DH
    img.paste(cop, (int(mx * W - cop.width / 2), int(my * H - cop.height / 2)),
              cop)

    # 右上に切り抜きの1個。参考と同じで、箸で持ち上げたところ
    if hero is not None:
        hw = int(392 * k)
        hh = int(hw * hero.height / hero.width)
        hz = hero.resize((hw, hh), Image.LANCZOS)
        sh_ = Image.new("RGBA", (hw, hh), (0, 0, 0, 0))
        sh_.paste((0, 0, 0, 95), (0, 0), hz.split()[3])
        sh_ = sh_.filter(ImageFilter.GaussianBlur(9 * k / 3))
        img.paste(sh_, (int(600 * k), int(28 * k)), sh_)
        img.paste(hz, (int(596 * k), int(20 * k)), hz)
        d = ImageDraw.Draw(img)

    # 商品名。写真の上にまたがらせて、面の幅いっぱいに使う
    ncx = 468 * k
    sx, sy = int(7 * k), int(9 * k)     # 影
    _tt(d, ncx + sx, 208 * k + sy, "こがね", f_n1, 10 * k, (70, 10, 12),
        stroke=int(9 * k), stroke_fill=(70, 10, 12))
    _tt(d, ncx, 208 * k, "こがね", f_n1, 10 * k, WHITE,
        stroke=int(9 * k), stroke_fill=(46, 6, 8))
    _tt(d, ncx + sx, 286 * k + sy, "餃子", f_n2, 14 * k, (70, 10, 12),
        stroke=int(17 * k), stroke_fill=(70, 10, 12))
    _tt(d, ncx, 286 * k, "餃子", f_n2, 14 * k, WHITE,
        stroke=int(17 * k), stroke_fill=(46, 6, 8))
    _tt(d, ncx, 528 * k, "GYOZA", f_rom, 11 * k, GOLD,
        stroke=int(5 * k), stroke_fill=(70, 10, 12))

    # 左上：ブランドの白箱
    bx0, by0, bx1, by1 = 30 * k, 26 * k, 254 * k, 118 * k
    d.rounded_rectangle([bx0, by0, bx1, by1], radius=9 * k, fill=WHITE)
    d.text(((bx0 + bx1) / 2, by0 + 11 * k), "FRESH FROZEN", font=f_logo_s,
           fill=(120, 110, 104), anchor="mt")
    d.text(((bx0 + bx1) / 2, by0 + 33 * k), "こがね食品", font=f_logo,
           fill=RED, anchor="mt")

    # 左下：縦長の楕円バッジ（参考の「元祖 油・水なし」の位置）
    ecx, ecy, ehw, ehh = 116 * k, 498 * k, 74 * k, 86 * k
    d.ellipse([ecx - ehw, ecy - ehh, ecx + ehw, ecy + ehh], fill=RED_D,
              outline=GOLD, width=int(4 * k))
    d.text((ecx, ecy - 68 * k), "元祖", font=f_badge_s, fill=GOLD, anchor="mt")
    d.text((ecx, ecy - 45 * k), "羽根", font=f_badge, fill=WHITE, anchor="mt")
    d.text((ecx, ecy + 0 * k), "つき", font=f_badge, fill=WHITE, anchor="mt")
    d.text((34 * k, 612 * k), "（調理例）", font=f_tiny, fill=WHITE, anchor="lt",
           stroke_width=int(2.2 * k), stroke_fill=(30, 22, 18))

    # 下の情報。白い小箱を並べて、最後は地に白文字
    bxs = [("要冷凍", None), ("12個入り", "(300g)"), ("フライパン", "ひとつで"),
           ("たれ付き", None)]
    x = 30 * k
    y0b, y1b = 640 * k, 684 * k
    for main, sub in bxs:
        w = int((96 if sub else 78) * k)
        d.rectangle([x, y0b, x + w, y1b], fill=WHITE)
        if sub:
            d.text((x + w / 2, y0b + 4 * k), main, font=f_box, fill=RED_D,
                   anchor="mt")
            d.text((x + w / 2, y0b + 26 * k), sub, font=f_box_s, fill=INK,
                   anchor="mt")
        else:
            d.text((x + w / 2, (y0b + y1b) / 2), main, font=f_box, fill=RED_D,
                   anchor="mm")
        x += w + int(9 * k)

    # 面のふちに金の枠。参考の袋はこれで全体が締まっている
    fr = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    fd = ImageDraw.Draw(fr)
    fd.rounded_rectangle([12 * k, 12 * k, W - 12 * k, H - 12 * k],
                         radius=14 * k, outline=GOLD + (255,), width=int(5 * k))
    fd.rounded_rectangle([24 * k, 24 * k, W - 24 * k, H - 24 * k],
                         radius=10 * k, outline=GOLD_D + (150,),
                         width=int(2 * k))
    img.paste(fr, (0, 0), fr)

    return img.resize((SW, SH), Image.LANCZOS)


def wrap_rgb(art, size):
    BW, BH = size
    src = np.asarray(art).astype(np.float32)
    out = np.zeros((BH, BW, 3), np.float32)
    al = np.zeros((BH, BW), np.float32)
    K = BULGE
    amax = math.asin(K)
    for y in range(int(Y0), int(Y1) + 1):
        v = (y - Y0) / (Y1 - Y0) * (SH - 1)
        v0 = int(v); v1 = min(v0 + 1, SH - 1); fv = v - v0
        row = src[v0] * (1 - fv) + src[v1] * fv
        hw, cx = geom(y)
        x0 = int(math.floor(cx - hw)); x1 = int(math.ceil(cx + hw))
        xs = np.arange(x0, x1 + 1)
        t = np.clip((xs - cx) / hw, -1.0, 1.0)
        s = np.arcsin(t * K) / amax
        u = (s + 1) / 2 * (SW - 1)
        u0 = np.clip(u.astype(int), 0, SW - 1)
        u1 = np.clip(u0 + 1, 0, SW - 1)
        fu = (u - u0)[:, None]
        out[y, x0:x1 + 1] = row[u0] * (1 - fu) + row[u1] * fu
        edge = np.clip((1 - np.abs(s)) / 0.030, 0, 1)
        al[y, x0:x1 + 1] = edge * edge * (3 - 2 * edge)
    # 上下の端もなだらかに
    for yy, k in ((int(Y0), 1), (int(Y1), -1)):
        for i in range(26):
            al[yy + k * i] *= i / 26.0
    return out, al


def print_on(src, dst, photo_path, hero_path=None, seed=4):
    base = Image.open(src).convert("RGB")
    hero = Image.open(hero_path).convert("RGBA") if hero_path else None
    art = build_art(Image.open(photo_path).convert("RGB"), hero)
    rgb, al = wrap_rgb(art, base.size)
    al = np.asarray(
        Image.fromarray((al * 255).astype(np.uint8)).filter(
            ImageFilter.GaussianBlur(1.2))
    ).astype(np.float32) / 255.0

    a = np.asarray(base).astype(np.float32)
    lum = a.mean(2)
    ref = float(np.median(lum[int(Y0):int(Y1), 700:2100]))
    shade = np.clip(lum / max(ref, 1e-6), 0.66, 1.14)[..., None]
    printed = np.clip(rgb * shade, 0, 255)
    rng = np.random.default_rng(seed)
    printed = printed + rng.normal(0, 1.4, printed.shape)
    out = a * (1 - al[..., None]) + printed * al[..., None]
    Image.fromarray(np.clip(out, 0, 255).astype(np.uint8)).save(dst)
    return dst


if __name__ == "__main__":
    import sys
    print(print_on(*sys.argv[1:5]))


# --- 締めのカット（パッケージに寄る3.4秒）を静止画から作る -------------------
FFMPEG = ("/usr/local/lib/python3.11/dist-packages/imageio_ffmpeg/binaries/"
          "ffmpeg-linux-x86_64-v7.0.2")


def clip(still, out, dur=3.4, cw=1920, chh=1080, fps=24, z0=2300, z1=2000):
    """刷ったパッケージ写真の面の中心に、ゆっくり寄る。"""
    import subprocess
    src = Image.open(still).convert("RGB")
    sw, sh = src.size
    cx = (PROF[0][2] + PROF[-1][2]) / 2 * sw / 2752.0
    cy = (Y0 + Y1) / 2 * sh / 1536.0
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
