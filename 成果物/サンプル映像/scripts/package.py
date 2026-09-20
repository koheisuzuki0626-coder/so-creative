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

SS = 3
SW, SH = 1000, 700           # 袋の面の見かけの比に合わせた原稿

# 平袋の面（2752px の写真から実測）。(y, 見かけの半幅, 中心x)
PROF = [(250.0, 730.0, 1399.0), (770.0, 757.0, 1399.0), (1290.0, 730.0, 1399.0)]
Y0, Y1 = 250.0, 1290.0
FILL = 0.98
BULGE = 0.45                 # 枕型のふくらみ

# 金の斜め帯（面に対する割合）。左下の起点・右へ上がる量・太さ
BAND_X0, BAND_Y0, BAND_RISE, BAND_TH = 0.38, 0.86, 0.28, 0.155
COPY = "羽根パリッ、肉汁じゅわり！"

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


def build_art(photo):
    W, H = SW * SS, SH * SS
    img = Image.new("RGB", (W, H), RED)
    d = ImageDraw.Draw(img)

    # 地の赤に上下のグラデーション（ベタ1色は印刷に見えない）
    gr = np.linspace(0, 1, H)[:, None]
    base = np.zeros((H, W, 3), np.float32)
    for i in range(3):
        base[..., i] = RED[i] * (1.0 - 0.14 * gr) + RED_D[i] * (0.14 * gr)
    img = Image.fromarray(np.clip(base, 0, 255).astype(np.uint8))
    d = ImageDraw.Draw(img)

    # 左に商品写真を断ち切りで置く。右端だけ締めて抜く
    pw, ph = int(680 * SS), H
    p = _lift(photo, gamma=0.52, sat=1.22)
    sw, sh = p.size
    # 皿に寄せて切る（引きで撮っているので、そのままだと餃子が小さく天井が入る）
    ch = int(sh * 0.62)
    cw = int(ch * pw / ph)
    cx0 = int(sw * 0.50 - cw / 2)
    cy0 = int(sh * 0.76 - ch / 2)
    cx0 = max(0, min(sw - cw, cx0))
    cy0 = max(0, min(sh - ch, cy0))
    p = p.crop((cx0, cy0, cx0 + cw, cy0 + ch)).resize((pw, ph), Image.LANCZOS)
    # 抜きの境界は真っ直ぐ立てない。下に向かって少し広がる斜めにする
    fade = int(56 * SS)
    xx = np.arange(pw)[None, :].astype(np.float32)
    ed = (np.linspace(560, 660, ph, dtype=np.float32) * SS)[:, None]
    mk = np.clip((ed - xx) / fade, 0, 1) ** 0.75
    img.paste(p, (0, 0), Image.fromarray((mk * 255).astype(np.uint8)))
    # 境界に金の細い罫を通して、貼り込みに見えないようにする
    ru = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(ru).line([(560 * SS, 0), (660 * SS, H)],
                            fill=GOLD + (215,), width=int(3.5 * SS))
    img.paste(ru, (0, 0), ru)
    d = ImageDraw.Draw(img)

    # 金の斜め帯。左下から右へ緩く上がり、面の中で終わる
    band = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    bd = ImageDraw.Draw(band)
    bx = [(BAND_X0 * W, BAND_Y0 * H), (W, (BAND_Y0 - BAND_RISE) * H),
          (W, (BAND_Y0 - BAND_RISE + BAND_TH) * H),
          (BAND_X0 * W, (BAND_Y0 + BAND_TH) * H)]
    bd.polygon(bx, fill=GOLD + (255,))
    bd.line([bx[0], bx[1]], fill=GOLD_D + (255,), width=int(2 * SS))
    bd.line([bx[3], bx[2]], fill=GOLD_D + (255,), width=int(2 * SS))
    img.paste(band, (0, 0), band)
    d = ImageDraw.Draw(img)

    f_logo_s = ImageFont.truetype(GOTHIC, int(13 * SS))
    f_logo = ImageFont.truetype(GOTHIC, int(30 * SS))
    f_n1 = ImageFont.truetype(GOTHIC, int(104 * SS))
    f_n2 = ImageFont.truetype(GOTHIC, int(158 * SS))
    f_rom = ImageFont.truetype(GOTHIC, int(32 * SS))
    f_copy = ImageFont.truetype(GOTHIC, int(37 * SS))
    f_badge_s = ImageFont.truetype(GOTHIC, int(20 * SS))
    f_badge = ImageFont.truetype(GOTHIC, int(34 * SS))
    f_box = ImageFont.truetype(ZEN, int(22 * SS))
    f_box_s = ImageFont.truetype(ZEN, int(15 * SS))

    # 左上：ブランドの白箱（写真の上に乗せる）
    bx0, by0, bx1, by1 = 26 * SS, 24 * SS, 250 * SS, 112 * SS
    d.rounded_rectangle([bx0, by0, bx1, by1], radius=8 * SS, fill=WHITE)
    d.text(((bx0 + bx1) / 2, by0 + 10 * SS), "FRESH FROZEN", font=f_logo_s,
           fill=(120, 110, 104), anchor="mt")
    d.text(((bx0 + bx1) / 2, by0 + 32 * SS), "こがね食品", font=f_logo,
           fill=RED, anchor="mt")

    # 商品名。白抜きに濃い縁。2段に割って大きく見せる
    ncx = 748 * SS
    _tt(d, ncx, 150 * SS, "こがね", f_n1, 6 * SS, WHITE,
        stroke=int(11 * SS), stroke_fill=(52, 8, 10))
    _tt(d, ncx, 258 * SS, "餃子", f_n2, 10 * SS, WHITE,
        stroke=int(14 * SS), stroke_fill=(52, 8, 10))
    d.text((ncx, 438 * SS), "G Y O Z A", font=f_rom, fill=GOLD, anchor="mt")

    # 金帯の上にコピー。帯と同じ角度に倒して、帯の中心線に乗せる
    ang = math.degrees(math.atan2(BAND_RISE * H, (1 - BAND_X0) * W))
    tw = int(_tw(d, COPY, f_copy, 2 * SS)) + int(20 * SS)
    cop = Image.new("RGBA", (tw, int(64 * SS)), (0, 0, 0, 0))
    _tt(ImageDraw.Draw(cop), tw / 2, int(6 * SS), COPY, f_copy, 2 * SS,
        RED_D + (255,))
    cop = cop.rotate(ang, expand=True, resample=Image.BICUBIC)
    # 帯の中心線上の、コピーを乗せる点
    mx = 0.685
    my = BAND_Y0 - BAND_RISE * (mx - BAND_X0) / (1 - BAND_X0) + BAND_TH / 2
    img.paste(cop, (int(mx * W - cop.width / 2), int(my * H - cop.height / 2)),
              cop)

    # 赤丸バッジ
    r = 62 * SS
    cx2, cy2 = 492 * SS, 192 * SS
    d.ellipse([cx2 - r, cy2 - r, cx2 + r, cy2 + r], fill=RED_D,
              outline=GOLD, width=int(4 * SS))
    d.text((cx2, cy2 - 38 * SS), "元祖", font=f_badge_s, fill=GOLD, anchor="mt")
    d.text((cx2, cy2 - 8 * SS), "羽根", font=f_badge, fill=WHITE, anchor="mt")

    # 下の情報の小箱
    bxs = [("要冷凍", None), ("12個入り", "(300g)"), ("フライパン", "ひとつで")]
    x = 26 * SS
    for main, sub in bxs:
        w = int((100 if sub else 82) * SS)
        y0b, y1b = 612 * SS, 668 * SS
        d.rectangle([x, y0b, x + w, y1b], fill=WHITE)
        if sub:
            d.text((x + w / 2, y0b + 6 * SS), main, font=f_box, fill=RED_D, anchor="mt")
            d.text((x + w / 2, y0b + 31 * SS), sub, font=f_box_s, fill=INK, anchor="mt")
        else:
            d.text((x + w / 2, (y0b + y1b) / 2), main, font=f_box, fill=RED_D,
                   anchor="mm")
        x += w + int(10 * SS)

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


def print_on(src, dst, photo_path, seed=4):
    base = Image.open(src).convert("RGB")
    art = build_art(Image.open(photo_path).convert("RGB"))
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
    print(print_on(sys.argv[1], sys.argv[2], sys.argv[3]))


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
