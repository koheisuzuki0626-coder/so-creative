# -*- coding: utf-8 -*-
"""架空商品「こがね餃子」のパッケージ意匠を、無地の袋の写真に刷り込む。

まもりばのラベルと同じ考え方。意匠は生成に描かせず、ここで組んでから
袋の面に乗せる。文字が崩れないので、商品名や内容量の差し替えが効く。
"""
import math
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

FONTS = "/tmp/fonts"
GOTHIC = f"{FONTS}/NotoSansJP-Black.ttf"
ZEN = f"{FONTS}/ZenKakuNew-Black.ttf"

SS = 3
SW, SH = 620, 843            # 刷り面の原稿。袋の面の見かけの比に合わせてある

# 袋の輪郭（2752px の写真から実測）。(y, 見かけの半径, 中心x)
PROF = [(250.0, 367.0, 1376.0), (700.0, 375.0, 1375.0), (1250.0, 330.0, 1375.0)]
Y0, Y1 = 380.0, 1190.0       # 刷り面の上下
FILL = 0.80                  # 袋の幅のうち刷る割合
BULGE = 0.35                 # 面のふくらみ。円筒(0.8前後)よりずっと浅い

INK = np.array([0.30, 0.27, 0.27], np.float32)    # 濃い墨。地に対する乗算
GOLD = np.array([0.97, 0.80, 0.30], np.float32)   # 山吹


def geom(y):
    ys = [p[0] for p in PROF]
    hw = float(np.interp(y, ys, [p[1] for p in PROF]))
    cx = float(np.interp(y, ys, [p[2] for p in PROF]))
    return hw * FILL, cx


def _track_w(d, text, font, track):
    return sum(d.textlength(c, font=font) for c in text) + track * (len(text) - 1)


def _track(d, cx, y, text, font, track, fill=255):
    """字間を空けて中央に置く。

    1文字ずつ anchor="lt" で置くと、読点・句点が上に浮く（小さい字面が
    em の左上に寄るため）。字間を空けない行は、まとめて描く。
    """
    if track <= 0:
        d.text((cx, y), text, font=font, fill=fill, anchor="mt")
        return
    x = cx - _track_w(d, text, font, track) / 2
    for ch in text:
        d.text((x, y), ch, font=font, fill=fill, anchor="lt")
        x += d.textlength(ch, font=font) + track


def build_art():
    """墨の版と山吹の版を、それぞれ濃度マスクとして返す。"""
    W, H = SW * SS, SH * SS
    ink = Image.new("L", (W, H), 0)
    gold = Image.new("L", (W, H), 0)
    di, dg = ImageDraw.Draw(ink), ImageDraw.Draw(gold)
    cx = W / 2

    f_top = ImageFont.truetype(GOTHIC, int(30 * SS))
    f_name = ImageFont.truetype(GOTHIC, int(120 * SS))
    f_sub = ImageFont.truetype(GOTHIC, int(36 * SS))
    f_copy = ImageFont.truetype(ZEN, int(24 * SS))
    f_net = ImageFont.truetype(GOTHIC, int(26 * SS))

    _track(dg, cx, 50 * SS, "羽根つき", f_top, 14 * SS)
    dg.rectangle([cx - 100 * SS, 118 * SS, cx + 100 * SS, 118 * SS + 3 * SS], fill=255)

    _track(di, cx, 190 * SS, "こがね餃子", f_name, 10 * SS)

    di.rectangle([cx - 75 * SS, 372 * SS, cx + 75 * SS, 372 * SS + 2 * SS], fill=255)
    _track(di, cx, 408 * SS, "冷凍餃子", f_sub, 16 * SS)

    _track(di, cx, 600 * SS, "フライパンひとつで、パリッと羽根つき。", f_copy, 0)
    _track(di, cx, 740 * SS, "12個入 300g", f_net, 8 * SS)

    return (ink.resize((SW, SH), Image.LANCZOS),
            gold.resize((SW, SH), Image.LANCZOS))


def wrap(art, size):
    """原稿を袋の面に合わせて変形する。"""
    BW, BH = size
    src = np.asarray(art).astype(np.float32) / 255.0
    out = np.zeros((BH, BW), np.float32)
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
        fu = u - u0
        vals = row[u0] * (1 - fu) + row[u1] * fu
        edge = np.clip((1 - np.abs(s)) / 0.06, 0, 1)
        out[y, x0:x1 + 1] = vals * (edge * edge * (3 - 2 * edge))
    return out


def print_on(src, dst, seed=4):
    base = Image.open(src).convert("RGB")
    ink_a, gold_a = build_art()
    a = np.asarray(base).astype(np.float32)
    rng = np.random.default_rng(seed)

    for art, mult in ((ink_a, INK), (gold_a, GOLD)):
        al = wrap(art, base.size)
        al = np.asarray(
            Image.fromarray((al * 255).astype(np.uint8)).filter(
                ImageFilter.GaussianBlur(0.9))
        ).astype(np.float32) / 255.0
        al = al * 0.97                       # 刷りムラぶん、わずかに薄く
        a = a * (1 - al[..., None]) + (a * mult) * al[..., None]
        g = rng.normal(0, 1.5, a.shape).astype(np.float32) * (al[..., None] > 0.04)
        a = a + g

    Image.fromarray(np.clip(a, 0, 255).astype(np.uint8)).save(dst)
    return dst


if __name__ == "__main__":
    import sys
    print(print_on(sys.argv[1], sys.argv[2]))
