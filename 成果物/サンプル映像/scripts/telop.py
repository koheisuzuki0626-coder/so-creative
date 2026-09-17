# -*- coding: utf-8 -*-
"""テロップとロゴの素材を作る（B案：黒ブロック＋色差し）。

ffmpeg に drawtext が無いので、文字は透過PNGに焼いて overlay する。
ブロックと文字を別のPNGに分ける。ffmpeg の drawbox は x/w に時間変数 t を持たない
（一度しか評価されない）ので、動きは overlay の y 時間式で付ける。
ブロックと文字を同じ y 式で動かし、文字だけ遅れてフェードインさせる。

フォントは Google Fonts の Zen Kaku Gothic New 900 / Noto Sans JP 900。
IPAGothic には太字が無く、細くて弱いので使わない。
"""
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import numpy as np
import json
import os

W, H = 1920, 1080
FONTS = os.environ.get("SO_FONTS", "/tmp/fonts")
ZEN = f"{FONTS}/ZenKakuNew-Black.ttf"
GOTHIC = f"{FONTS}/NotoSansJP-Black.ttf"

ACCENT = (245, 181, 42)       # 山吹。04ブロックの縦バーに残す1色
NAVY = (15, 33, 64)           # 02の帯
OUT = os.path.dirname(os.path.abspath(__file__)) + "/telop"
os.makedirs(OUT, exist_ok=True)

# 架空の名前（差し替え用）
SERVICE_NAME = "そのまま日報"
SERVICE_SUB = "現場の日報アプリ"
PRODUCT_NAME = "こがね餃子"
PRODUCT_SUB = "羽根つき 冷凍餃子"

# 本文 / 色を差すキーワード / デザイン
# 02（業務ソフト）と04（食品CM）でテロップのデザインを作り分ける。
#   navy  … 紺帯＋白文字＋白の縦帯（02）。帯は画面全幅
#   block … 黒ブロック＋白文字＋山吹の縦バー（04）。文字幅ぶんのブロック
# 文字はどちらも白。第2稿では02を黒文字、04はキーワードを山吹にしていたが、
# 「テロップは白字の方がいい」との指摘で白に統一した。色は帯とバーだけで差をつける。
TELOPS = {
    "02_1": ("現場で、その場で。", None, "navy"),
    "02_2": ("事務所には、もう届いている。", None, "navy"),
    "02_3": ("日報の転記を、なくす。", None, "navy"),
    "04a_1": ("音が、ちがう。", None, "block"),
    "04a_2": ("肉汁、そのまま。", None, "block"),
    "04b_1": ("今日は、もう決まり。", None, "block"),
    "04b_2": ("フライパンひとつ、10分。", None, "block"),
}

SIZE = 132
LEFT = 100
BOTTOM = 112
PAD_X, PAD_T, PAD_B = 30, 22, 26


def blank():
    return Image.new("RGBA", (W, H), (0, 0, 0, 0))


def real_bbox(img):
    """実際に描かれた範囲を alpha から測る。極太フォントは getbbox が当てにならない。"""
    a = np.array(img)[:, :, 3]
    ys, xs = np.nonzero(a > 8)
    if len(xs) == 0:
        return None
    return int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())


def place(draw_fn, left=None, bottom=None, center_x=False):
    """一度描いて実寸を測り、目標位置に合わせて描き直す。"""
    probe = blank()
    draw_fn(ImageDraw.Draw(probe), 0, 0)
    bb = real_bbox(probe)
    if bb is None:
        return probe
    x0, y0, x1, y1 = bb
    tx = ((W - (x1 - x0)) // 2 - x0) if center_x else (left - x0)
    ty = (H - bottom - (y1 - y0)) - y0
    out = blank()
    draw_fn(ImageDraw.Draw(out), tx, ty)
    return out


def split_accent(text, accent):
    parts, rest = [], text
    while rest:
        if accent and rest.startswith(accent):
            parts.append((accent, True))
            rest = rest[len(accent):]
        else:
            i = rest.find(accent) if accent else -1
            if i < 0:
                parts.append((rest, False))
                rest = ""
            else:
                parts.append((rest[:i], False))
                rest = rest[i:]
    return parts


MAX_BLOCK_W = 1700


def band_telop(key, text, accent, style):
    """文字だけのPNGを書き、下敷き（ブロック／帯）の矩形を返す。

    長い行は下敷きが画面幅を超えるので、収まるまで文字を小さくする。
    """
    parts = split_accent(text, accent)
    size = SIZE
    while size > 92:
        f = ImageFont.truetype(ZEN, size)
        w = sum(f.getlength(t) for t, _ in parts) + PAD_X * 2 + LEFT - 70
        if w <= MAX_BLOCK_W:
            break
        size -= 4
    f = ImageFont.truetype(ZEN, size)

    def draw(d, ox, oy):
        x = ox
        for t, is_ac in parts:
            # 文字は常に白。色差しは使わない（accent を渡せば山吹に戻せる）
            col = ACCENT if is_ac else (255, 255, 255)
            d.text((x, oy), t, font=f, fill=col + (255,))
            x += d.textlength(t, font=f)

    txt = place(draw, left=LEFT, bottom=BOTTOM)
    bb = real_bbox(txt)
    img = blank()
    # 下敷きから浮かせるための軽い影
    img.alpha_composite(txt.filter(ImageFilter.GaussianBlur(12)))
    img.alpha_composite(txt)
    img.save(f"{OUT}/{key}.png")
    box = {"x": max(0, bb[0] - PAD_X), "y": bb[1] - PAD_T,
           "w": (bb[2] + PAD_X) - max(0, bb[0] - PAD_X),
           "h": (bb[3] + PAD_B) - (bb[1] - PAD_T)}
    return box


def logo_card(name, sub, path, mark="check", tint=(255, 255, 255), cy_ratio=0.46):
    """締め。極太ゴシックで中央に。影で抜く。"""
    img = blank()
    shadow = blank()
    ds, d = ImageDraw.Draw(shadow), ImageDraw.Draw(img)
    f_name = ImageFont.truetype(GOTHIC, 104)
    f_sub = ImageFont.truetype(ZEN, 40)
    nb = f_name.getbbox(name)
    name_w = nb[2] - nb[0]
    mark_r = 0 if mark == "none" else 46
    gap = 0 if mark == "none" else 36
    total_w = mark_r * 2 + gap + name_w
    x0 = (W - total_w) // 2
    cy = int(H * cy_ratio)

    if mark == "check":
        mx, my = x0 + mark_r, cy
        for dr in (ds, d):
            dr.ellipse([mx - mark_r, my - mark_r, mx + mark_r, my + mark_r],
                       outline=tint + (255,), width=8)
            dr.line([(mx - 21, my + 2), (mx - 6, my + 18), (mx + 23, my - 19)],
                    fill=tint + (255,), width=10, joint="curve")

    nx = x0 + mark_r * 2 + gap
    # サブは画面中央ではなく「名前の中心」に合わせる（マークがあると中央だとずれる）
    sub_cx = nx + name_w // 2
    for dr in (ds, d):
        dr.text((nx, cy), name, font=f_name, fill=tint + (255,), anchor="lm")
        dr.text((sub_cx, cy + 92), sub, font=f_sub, fill=tint + (225,), anchor="mm")

    shadow = shadow.filter(ImageFilter.GaussianBlur(28))
    base = blank()
    base.alpha_composite(shadow)
    base.alpha_composite(shadow)
    base.alpha_composite(img)
    base.save(path)


if __name__ == "__main__":
    boxes = {}
    for key, (text, accent, style) in TELOPS.items():
        boxes[key] = band_telop(key, text, accent, style)
        boxes[key]["style"] = style
    # 下敷きの天地は全カットで揃える（行ごとに違うとカット替わりでチラつく）
    top = min(b["y"] for b in boxes.values())
    bot = max(b["y"] + b["h"] for b in boxes.values())
    for key, b in boxes.items():
        b["y"], b["h"] = top, bot - top
        blk = blank()
        d = ImageDraw.Draw(blk)
        if b["style"] == "navy":
            # 紺帯は画面全幅。左端に白の縦帯
            d.rectangle([0, b["y"], W, b["y"] + b["h"]], fill=NAVY + (224,))
            d.rectangle([0, b["y"], 28, b["y"] + b["h"]], fill=(255, 255, 255, 255))
        else:
            d.rectangle([b["x"], b["y"], b["x"] + b["w"], b["y"] + b["h"]],
                        fill=(0, 0, 0, 209))
            # 左端に山吹の縦バー。ブロックの端を締める
            d.rectangle([b["x"], b["y"], b["x"] + 10, b["y"] + b["h"]],
                        fill=ACCENT + (255,))
        blk.save(f"{OUT}/{key}_blk.png")
    logo_card(SERVICE_NAME, SERVICE_SUB, f"{OUT}/02_logo.png", mark="check")
    logo_card(PRODUCT_NAME, PRODUCT_SUB, f"{OUT}/04_logo.png", mark="none",
              tint=(255, 248, 232))
    # 訴求Bの締めは C2（箸の寄り）で中央に餃子が来るのでロゴを上に逃がす
    logo_card(PRODUCT_NAME, PRODUCT_SUB, f"{OUT}/04_logo_top.png", mark="none",
              tint=(255, 248, 232), cy_ratio=0.26)
    for a, name in ((88, "dim34"), (74, "dim29")):
        Image.new("RGBA", (W, H), (0, 0, 0, a)).save(f"{OUT}/{name}.png")
    with open(f"{OUT}/boxes.json", "w") as fp:
        json.dump({"boxes": boxes}, fp, ensure_ascii=False, indent=1)
    print(json.dumps(boxes, ensure_ascii=False, indent=1))
