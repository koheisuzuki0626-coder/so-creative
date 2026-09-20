# -*- coding: utf-8 -*-
"""架空商品「こがね餃子」のパッケージ意匠を、無地の袋の写真に刷り込む。

意匠は生成に描かせず、ここで組んでから袋の面に乗せる。文字が崩れないので、
商品名や内容量の差し替えが効く。

9/20 に作り直した。最初は生成りの地に文字だけを置いていたが、それでは
コーヒー豆や雑穀の袋に見えた。売り場の冷凍餃子は白地・赤の帯・商品写真が
基本なので、袋の面を全面塗りにして、皿のカットをそのまま商品写真に使う。
"""
import math
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

FONTS = "/tmp/fonts"
GOTHIC = f"{FONTS}/NotoSansJP-Black.ttf"
ZEN = f"{FONTS}/ZenKakuNew-Black.ttf"

SS = 3
SW, SH = 620, 914            # 袋の面の見かけの比に合わせた原稿

# 袋の輪郭（2752px の写真から実測）。(y, 見かけの半径, 中心x)
PROF = [(250.0, 367.0, 1376.0), (700.0, 375.0, 1375.0), (1250.0, 330.0, 1375.0)]
Y0, Y1 = 212.0, 1284.0       # 袋の上端〜下端。面を全部塗る
FILL = 0.975
BULGE = 0.35                 # 面のふくらみ。円筒よりずっと浅い

WHITE = (250, 248, 243)
RED = (181, 38, 40)
INK = (38, 31, 27)
GOLD = (176, 135, 51)
SUB = (92, 82, 74)


def geom(y):
    ys = [p[0] for p in PROF]
    return (float(np.interp(y, ys, [p[1] for p in PROF])) * FILL,
            float(np.interp(y, ys, [p[2] for p in PROF])))


def _tw(d, text, font, track):
    return sum(d.textlength(c, font=font) for c in text) + track * (len(text) - 1)


def _tt(d, cx, y, text, font, track, fill):
    """字間を空けて中央に。字間ゼロの行はまとめて描く（約物が上に浮くため）。"""
    if track <= 0:
        d.text((cx, y), text, font=font, fill=fill, anchor="mt")
        return
    x = cx - _tw(d, text, font, track) / 2
    for ch in text:
        d.text((x, y), ch, font=font, fill=fill, anchor="lt")
        x += d.textlength(ch, font=font) + track


def build_art(photo):
    """袋の面いっぱいの意匠を RGB で返す。photo は商品写真。"""
    W, H = SW * SS, SH * SS
    img = Image.new("RGB", (W, H), WHITE)
    d = ImageDraw.Draw(img)
    cx = W / 2
    M = 30 * SS                                   # 左右の余白

    f_band = ImageFont.truetype(GOTHIC, int(46 * SS))
    f_cold = ImageFont.truetype(GOTHIC, int(22 * SS))
    f_name = ImageFont.truetype(GOTHIC, int(100 * SS))
    f_copy = ImageFont.truetype(ZEN, int(21 * SS))
    f_cnt = ImageFont.truetype(GOTHIC, int(40 * SS))
    f_net = ImageFont.truetype(GOTHIC, int(26 * SS))
    f_fine = ImageFont.truetype(ZEN, int(17 * SS))

    # 上の赤帯。売り場でいちばん目に入る場所に特徴を出す
    d.rectangle([0, 0, W, 152 * SS], fill=RED)
    _tt(d, cx, 46 * SS, "羽根つき", f_band, 16 * SS, WHITE)
    # 左に「冷凍」の白抜き
    bw, bh = 86 * SS, 40 * SS
    d.rounded_rectangle([M, 56 * SS, M + bw, 56 * SS + bh], radius=8 * SS, fill=WHITE)
    d.text((M + bw / 2, 56 * SS + bh / 2), "冷凍", font=f_cold, fill=RED, anchor="mm")

    # 商品名
    _tt(d, cx, 188 * SS, "こがね餃子", f_name, 6 * SS, INK)
    _tt(d, cx, 318 * SS, "フライパンひとつで、パリッと羽根つき。", f_copy, 0, SUB)

    # 金の細い罫
    d.rectangle([M, 358 * SS, W - M, 358 * SS + 3 * SS], fill=GOLD)

    # 商品写真。皿のカットをそのまま使う
    pw, ph = W - M * 2, 300 * SS
    ph_img = photo.copy()
    sw, sh = ph_img.size
    want = pw / ph
    if sw / sh > want:                            # 横長すぎるので左右を切る
        nw = int(sh * want)
        ph_img = ph_img.crop(((sw - nw) // 2, 0, (sw + nw) // 2, sh))
    else:
        nh = int(sw / want)
        ph_img = ph_img.crop((0, (sh - nh) // 2, sw, (sh + nh) // 2))
    ph_img = ph_img.resize((pw, ph), Image.LANCZOS)
    # 袋に刷る写真は、台所の暗さのままだと売り場で沈む。暗部を起こして
    # 彩度を少し上げる（映像側の絵は変えない。袋の中の1枚だけ）
    pa = np.asarray(ph_img).astype(np.float32) / 255.0
    pa = np.clip(pa, 0, 1) ** 0.62                     # 中間〜暗部を持ち上げ
    g = pa.mean(2, keepdims=True)
    pa = np.clip(g + (pa - g) * 1.14, 0, 1)            # 彩度
    ph_img = Image.fromarray((pa * 255).astype(np.uint8))
    mask = Image.new("L", (pw, ph), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, pw - 1, ph - 1],
                                           radius=14 * SS, fill=255)
    img.paste(ph_img, (M, 392 * SS), mask)
    d.rounded_rectangle([M, 392 * SS, W - M, 392 * SS + ph], radius=14 * SS,
                        outline=(214, 208, 198), width=2 * SS)
    d.text((cx, 392 * SS + ph - 34 * SS), "＊調理例", font=f_fine,
           fill=(255, 255, 255), anchor="mt")

    # 下：個数と内容量
    r = 60 * SS
    bx, by = M + r, 772 * SS
    d.ellipse([bx - r, by - r, bx + r, by + r], fill=RED)
    d.text((bx, by - 12 * SS), "12", font=f_cnt, fill=WHITE, anchor="mm")
    d.text((bx, by + 24 * SS), "個入", font=f_fine, fill=WHITE, anchor="mm")
    d.text((W - M, by - 16 * SS), "300g", font=f_net, fill=INK, anchor="rm")
    d.text((W - M, by + 20 * SS), "冷凍食品（加熱してお召し上がりください）",
           font=f_fine, fill=SUB, anchor="rm")

    return img.resize((SW, SH), Image.LANCZOS)


def wrap_rgb(art, size):
    """原稿を袋の面に合わせて変形する。RGB と、乗せる濃さを返す。"""
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
        edge = np.clip((1 - np.abs(s)) / 0.035, 0, 1)
        al[y, x0:x1 + 1] = edge * edge * (3 - 2 * edge)
    return out, al


def print_on(src, dst, photo_path, seed=4):
    base = Image.open(src).convert("RGB")
    photo = Image.open(photo_path).convert("RGB")
    art = build_art(photo)
    rgb, al = wrap_rgb(art, base.size)

    al = np.asarray(
        Image.fromarray((al * 255).astype(np.uint8)).filter(
            ImageFilter.GaussianBlur(1.1))
    ).astype(np.float32) / 255.0

    a = np.asarray(base).astype(np.float32)
    # 袋の陰影と皺をそのまま残す。面の明るさを基準に、刷った絵を明暗させる
    lum = a.mean(2)
    ref = float(np.median(lum[int(Y0):int(Y1), 1100:1650]))
    shade = np.clip(lum / max(ref, 1e-6), 0.62, 1.16)[..., None]
    printed = np.clip(rgb * shade, 0, 255)

    rng = np.random.default_rng(seed)
    printed = printed + rng.normal(0, 1.4, printed.shape)
    out = a * (1 - al[..., None]) + printed * al[..., None]
    Image.fromarray(np.clip(out, 0, 255).astype(np.uint8)).save(dst)
    return dst


if __name__ == "__main__":
    import sys
    print(print_on(sys.argv[1], sys.argv[2], sys.argv[3]))
