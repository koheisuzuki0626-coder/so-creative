# -*- coding: utf-8 -*-
"""架空ブランド「まもり葉」のラベルを、生成した無地チューブの写真に刷り込む。

ラベルは AI に描かせず、ここでベクター的に組んでから円筒に巻きつける。
ロゴやテキストを後から差し替えられることを示すための作り方。
"""
import math
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

FONTS = "/tmp/fonts"
MINCHO_M = f"{FONTS}/NotoSerifJP-Medium.ttf"
MINCHO_B = f"{FONTS}/NotoSerifJP-Black.ttf"
GOTHIC_B = f"{FONTS}/NotoSansJP-Black.ttf"

SS = 3                      # ラベル原稿のスーパーサンプル
SW, SH = 640, 1512          # ラベル原稿の寸法（等倍）
# SH は「刷り面の高さ ÷ 刷り面が回り込む弧の長さ」に合わせてある。
# ここがずれると、巻いたときに文字が縦長／横長に潰れる。

# チューブの輪郭（2048px の写真から実測）。rot はチューブを縦に起こす角度。
# prof は (y, 見かけの半径, 中心x) の実測列。間は線形で補う。
GEOM = {
    # 立っているカット
    "p1": dict(rot=0.0, y0=585.0, y1=1415.0, fill=0.80,
               prof=[(430.0, 236.0, 1017.0),
                     (1470.0, 151.0, 1029.0)]),
    # 寝かせたカット（チューブを縦に起こしてから刷る）
    "p2": dict(rot=-92.3, y0=753.0, y1=1407.0, fill=0.95,
               prof=[(660.0, 167.5, 1044.0),
                     (780.0, 147.5, 1044.0),
                     (900.0, 135.0, 1043.0),
                     (1020.0, 121.5, 1043.0),
                     (1140.0, 110.5, 1044.0),
                     (1260.0, 102.5, 1042.0),
                     (1380.0, 93.0, 1042.0),
                     (1500.0, 85.0, 1039.0)]),
}


# ---------------------------------------------------------------- 文字組み

def track_w(d, text, font, track):
    """字間を足したときの総幅。"""
    w = 0
    for ch in text:
        w += d.textlength(ch, font=font)
    return w + track * (len(text) - 1)


def track_text(d, cx, y, text, font, track, fill=255, anchor_y="mt"):
    """中央そろえで字間を空けて置く。"""
    total = track_w(d, text, font, track)
    x = cx - total / 2
    for ch in text:
        d.text((x, y), ch, font=font, fill=fill, anchor="l" + anchor_y[1])
        x += d.textlength(ch, font=font) + track


def thin(img, amount=1):
    """太いウェイトしか無いので、アルファを痩せさせて細く見せる。"""
    if amount <= 0:
        return img
    a = img.split()[-1]
    a = a.filter(ImageFilter.MinFilter(1 + 2 * amount))
    img.putalpha(a)
    return img


# ---------------------------------------------------------------- ロゴ

def leaf_path(cx, cy, w, h, tilt_deg=0.0):
    """先の尖った葉の輪郭。左右で膨らみを変えて葉らしくする。"""
    pts = []
    n = 90
    for i in range(n + 1):          # 右側を根元→先端
        t = i / n
        pts.append((+w / 2 * math.sin(math.pi * t) ** 1.35, -h / 2 + h * t))
    for i in range(n, -1, -1):      # 左側を先端→根元
        t = i / n
        pts.append((-w / 2 * math.sin(math.pi * t) ** 0.80, -h / 2 + h * t))
    c, s = math.cos(math.radians(tilt_deg)), math.sin(math.radians(tilt_deg))
    return [(cx + x * c - y * s, cy + x * s + y * c) for x, y in pts]


def vein_path(cx, cy, w, h, tilt_deg=0.0):
    """葉脈。根元から先端へ、わずかに右へ反る。"""
    pts = []
    n = 60
    for i in range(n + 1):
        t = i / n
        x = w * 0.085 * math.sin(math.pi * t) ** 0.9
        y = -h / 2 + h * t
        pts.append((x, y))
    c, s = math.cos(math.radians(tilt_deg)), math.sin(math.radians(tilt_deg))
    return [(cx + x * c - y * s, cy + x * s + y * c) for x, y in pts]


def draw_mark(d, cx, cy, h, tilt=-8.0):
    """葉のマーク。塗りの葉＋抜きの葉脈＋短い茎。"""
    w = h * 0.52
    d.polygon(leaf_path(cx, cy - h * 0.06, w, h, tilt), fill=255)
    # 葉脈は地の色で抜く
    vp = vein_path(cx, cy - h * 0.06, w, h * 0.94, tilt)
    d.line(vp, fill=0, width=max(2, int(h * 0.035)), joint="curve")
    # 茎
    c, s = math.cos(math.radians(tilt)), math.sin(math.radians(tilt))
    y0 = h * 0.44
    y1 = h * 0.70
    p0 = (cx - y0 * s, cy - h * 0.06 + y0 * c)
    p1 = (cx - y1 * s, cy - h * 0.06 + y1 * c)
    d.line([p0, p1], fill=255, width=max(2, int(h * 0.035)))


# ---------------------------------------------------------------- ラベル原稿

def _lerp3(g, y):
    pr = g["prof"]
    ys = [q[0] for q in pr]
    return (float(np.interp(y, ys, [q[1] for q in pr])),
            float(np.interp(y, ys, [q[2] for q in pr])))


def build_label():
    """白（=インクが乗る所）のマスクを作る。"""
    W, H = SW * SS, SH * SS
    img = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(img)
    cx = W / 2

    f_name = ImageFont.truetype(MINCHO_M, int(112 * SS))
    f_cat = ImageFont.truetype(GOTHIC_B, int(31 * SS))
    f_net = ImageFont.truetype(GOTHIC_B, int(25 * SS))
    f_sub = ImageFont.truetype(GOTHIC_B, int(25 * SS))

    draw_mark(d, cx, 252 * SS, 150 * SS)

    track_text(d, cx, 424 * SS, "まもり葉", f_name, 13 * SS)

    rw = 132 * SS
    ry = 596 * SS
    d.rectangle([cx - rw / 2, ry, cx + rw / 2, ry + max(1, int(2.4 * SS))], fill=255)

    track_text(d, cx, 630 * SS, "ハンドクリーム", f_cat, 13 * SS)

    # 中黒はフォントによって位置が揃わないので、点は自分で置く
    sub_y = 1130 * SS
    lw = track_w(d, "無香料", f_sub, 6 * SS)
    rw2 = track_w(d, "植物由来", f_sub, 6 * SS)
    gap = 26 * SS
    total = lw + gap + rw2
    track_text(d, cx - total / 2 + lw / 2, sub_y, "無香料", f_sub, 6 * SS)
    track_text(d, cx + total / 2 - rw2 / 2, sub_y, "植物由来", f_sub, 6 * SS)
    dr = 5.5 * SS
    dcy = sub_y + 25 * SS * 0.62
    d.ellipse([cx - dr, dcy - dr, cx + dr, dcy + dr], fill=255)
    track_text(d, cx, 1240 * SS, "NET 50g", f_net, 9 * SS)

    img = img.resize((SW, SH), Image.LANCZOS)
    return img


# ---------------------------------------------------------------- 円筒に巻く

def wrap(label, base_size, g):
    """ラベル原稿を、円筒の写り方に合わせて変形した alpha マップにする。"""
    BW, BH = base_size
    src = np.asarray(label).astype(np.float32) / 255.0
    out = np.zeros((BH, BW), np.float32)

    y0, y1 = g["y0"], g["y1"]
    ys = np.arange(int(y0), int(y1) + 1)
    K = g["fill"]
    amax = math.asin(K)

    for y in ys:
        v = (y - y0) / (y1 - y0) * (SH - 1)
        v0 = int(v)
        v1 = min(v0 + 1, SH - 1)
        fv = v - v0
        row = src[v0] * (1 - fv) + src[v1] * fv

        hw, cx = _lerp3(g, y)
        hwp = hw * K
        x0 = int(math.floor(cx - hwp))
        x1 = int(math.ceil(cx + hwp))
        xs = np.arange(x0, x1 + 1)
        t = np.clip((xs - cx) / hwp, -1.0, 1.0)
        # 円筒の見え方：面上の等間隔が、写真では中央ほど広く端ほど詰まる
        s = np.arcsin(t * K) / amax                     # -1..1 の展開座標
        u = (s + 1) / 2 * (SW - 1)
        u0 = np.clip(u.astype(int), 0, SW - 1)
        u1 = np.clip(u0 + 1, 0, SW - 1)
        fu = u - u0
        vals = row[u0] * (1 - fu) + row[u1] * fu
        # 端は回り込んで消える
        edge = np.clip((1 - np.abs(s)) / 0.14, 0, 1)
        edge = edge * edge * (3 - 2 * edge)
        out[y, x0:x1 + 1] = vals * edge

    return out


# ---------------------------------------------------------------- 刷る

def print_on(base_path, out_path, geom="p1", seed=7):
    g = GEOM[geom] if isinstance(geom, str) else geom
    base = Image.open(base_path).convert("RGB")
    label = build_label()
    alpha = wrap(label, base.size, g)

    amp = Image.fromarray((alpha * 255).astype(np.uint8)).filter(
        ImageFilter.GaussianBlur(0.8)
    )
    if g["rot"]:
        # 縦に起こした座標系で刷ってから、元の傾きへ戻す
        c = (base.size[0] / 2, base.size[1] / 2)
        amp = amp.rotate(-g["rot"], resample=Image.BICUBIC, center=c)
    alpha = np.asarray(amp).astype(np.float32) / 255.0

    a = np.asarray(base).astype(np.float32)

    # インクは下地に対する乗算。濃緑の一色刷り。
    MULT = np.array([0.32, 0.45, 0.35], np.float32)
    inked = a * MULT

    # 刷りムラ（版のかすれ）
    rng = np.random.default_rng(seed)
    noise = rng.normal(0.0, 1.0, (base.size[1] // 8, base.size[0] // 8)).astype(np.float32)
    noise = np.asarray(
        Image.fromarray(((noise * 40 + 128).clip(0, 255)).astype(np.uint8))
        .resize(base.size, Image.BICUBIC)
        .filter(ImageFilter.GaussianBlur(2.0))
    ).astype(np.float32) / 255.0
    dens = np.clip(0.94 + (noise - 0.5) * 0.24, 0.82, 1.0)

    amap = (alpha * dens)[..., None]
    out = a * (1 - amap) + inked * amap

    # 粒子をわずかに
    g = rng.normal(0, 1.6, out.shape).astype(np.float32) * (amap > 0.03)
    out = np.clip(out + g, 0, 255).astype(np.uint8)

    Image.fromarray(out).save(out_path)
    return out_path


# 無地のチューブ写真（Higgsfield / nano_banana_pro 生成）と、刷り上がりの置き場所。
MAT = "../素材"
JOBS = [
    ("p1", f"{MAT}/tube_p1.jpg", "../../../assets/works/ugc-mamoriha.jpg"),
    ("p2", f"{MAT}/tube_p2.jpg", "../../../assets/works/ugc-mamoriha-flat.jpg"),
]


def main(argv):
    if len(argv) >= 3:
        print(print_on(argv[1], argv[2], argv[3] if len(argv) > 3 else "p1"))
        return
    for geom, src, dst in JOBS:
        tmp = f"/tmp/_label_{geom}.png"
        print_on(src, tmp, geom)
        Image.open(tmp).convert("RGB").resize((1400, 1400), Image.LANCZOS).save(
            dst, quality=88, optimize=True
        )
        print(dst)


if __name__ == "__main__":
    import sys
    main(sys.argv)
