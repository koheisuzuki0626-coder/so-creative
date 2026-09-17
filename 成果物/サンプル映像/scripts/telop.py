# -*- coding: utf-8 -*-
"""テロップ・ロゴの PNG を作る。ffmpeg に drawtext が無いので overlay 用の素材を焼く。"""
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import os

W, H = 1920, 1080
FONT = "/usr/share/fonts/opentype/ipafont-gothic/ipagp.ttf"
NAVY = (15, 33, 64)          # #0f2140
BAND_ALPHA = 217             # 85%
OUT = os.path.dirname(os.path.abspath(__file__)) + "/telop"
os.makedirs(OUT, exist_ok=True)

# 差し替え用の架空名
SERVICE_NAME = "現場ノート"
SERVICE_SUB  = "日報アプリ"
PRODUCT_NAME = "こがね餃子"
PRODUCT_SUB  = "羽根つき 冷凍餃子"


def band_telop(text, path, size=76):
    """下1/4にネイビーの帯を敷き、左に白の縦バー、本文は左寄せ。"""
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    band_h = 250
    y0 = H - band_h
    d.rectangle([0, y0, W, H], fill=NAVY + (BAND_ALPHA,))
    f = ImageFont.truetype(FONT, size)
    bbox = f.getbbox(text)
    tx, ty = 170, y0 + (band_h - (bbox[3] - bbox[1])) // 2 - bbox[1]
    # 白の縦バー（本文の天地に合わせる）
    bar_h = bbox[3] - bbox[1] + 16
    bar_y = y0 + (band_h - bar_h) // 2
    d.rectangle([120, bar_y, 126, bar_y + bar_h], fill=(255, 255, 255, 255))
    d.text((tx, ty), text, font=f, fill=(255, 255, 255, 255), stroke_width=1,
           stroke_fill=(255, 255, 255, 255))
    img.save(path)


def logo_card(name, sub, path, mark="check", tint=(255, 255, 255), cy_ratio=0.46):
    """締め用。帯を使わず中央寄せ、影で抜く。マークは図形で描く。"""
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    shadow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ds = ImageDraw.Draw(shadow)
    d = ImageDraw.Draw(img)

    f_name = ImageFont.truetype(FONT, 96)
    f_sub = ImageFont.truetype(FONT, 40)
    nb = f_name.getbbox(name)
    sb = f_sub.getbbox(sub)
    name_w, name_h = nb[2] - nb[0], nb[3] - nb[1]
    mark_r = 0 if mark == "none" else 44
    gap = 0 if mark == "none" else 34
    total_w = mark_r * 2 + gap + name_w
    x0 = (W - total_w) // 2
    cy = int(H * cy_ratio)

    # マーク
    mx, my = x0 + mark_r, cy
    if mark == "check":
        for dr in (ds, d):
            dr.ellipse([mx - mark_r, my - mark_r, mx + mark_r, my + mark_r],
                       outline=tint + (255,), width=6)
    if mark == "none":
        pass
    elif mark == "check":
        pts = [(mx - 20, my + 2), (mx - 6, my + 17), (mx + 22, my - 18)]
        for dr in (ds, d):
            dr.line(pts, fill=tint + (255,), width=8, joint="curve")
    else:
        # 餃子のシルエット。円の輪郭は使わず、塗りの半月＋ひだ3本
        for dr in (ds, d):
            dr.ellipse([mx - mark_r, my - mark_r, mx + mark_r, my + mark_r],
                       fill=(0, 0, 0, 0), outline=(0, 0, 0, 0), width=0)
            dr.pieslice([mx - 34, my - 30, mx + 34, my + 38], start=180, end=360,
                        fill=tint + (255,))
            dr.line([(mx - 34, my + 4), (mx + 34, my + 4)], fill=tint + (255,), width=6)
            for ox in (-17, 0, 17):
                dr.line([(mx + ox, my - 2), (mx + ox, my - 22)],
                        fill=(0, 0, 0, 120), width=5)

    # 名前とサブ
    nx = x0 + mark_r * 2 + gap
    ny = cy - name_h // 2 - nb[1]
    for dr in (ds, d):
        dr.text((nx, ny), name, font=f_name, fill=tint + (255,),
                stroke_width=1, stroke_fill=tint + (255,))
    sx = (W - (sb[2] - sb[0])) // 2
    sy = cy + 86
    for dr in (ds, d):
        dr.text((sx, sy), sub, font=f_sub, fill=tint + (230,))

    shadow = shadow.filter(ImageFilter.GaussianBlur(26))
    base = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    base.alpha_composite(shadow)
    base.alpha_composite(shadow)
    base.alpha_composite(img)
    base.save(path)


if __name__ == "__main__":
    band_telop("現場で、その場で。", f"{OUT}/02_1.png")
    band_telop("事務所には、もう届いている。", f"{OUT}/02_2.png")
    band_telop("日報の転記を、なくす。", f"{OUT}/02_3.png")
    logo_card(SERVICE_NAME, SERVICE_SUB, f"{OUT}/02_logo.png", mark="check")

    band_telop("音が、ちがう。", f"{OUT}/04a_1.png")
    band_telop("肉汁、そのまま。", f"{OUT}/04a_2.png")
    band_telop("今日は、もう決まり。", f"{OUT}/04b_1.png")
    band_telop("フライパンひとつ、10分。", f"{OUT}/04b_2.png")
    logo_card(PRODUCT_NAME, PRODUCT_SUB, f"{OUT}/04_logo.png", mark="none",
              tint=(255, 248, 232))
    # 訴求Bの締めは C2（箸の寄り）で、中央に餃子が来る。ロゴは上に逃がす
    logo_card(PRODUCT_NAME, PRODUCT_SUB, f"{OUT}/04_logo_top.png", mark="none",
              tint=(255, 248, 232), cy_ratio=0.26)
    print("done")
