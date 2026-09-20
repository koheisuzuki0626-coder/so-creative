# -*- coding: utf-8 -*-
"""架空商品「こがね餃子」のパッケージ意匠を、無地の袋の写真に刷り込む。

意匠は生成に描かせず、ここで組んでから袋の面に乗せる。文字が崩れないので、
商品名や内容量の差し替えは刷り直すだけで済む。

9/20 に4度作り直した。
 1稿 生成りの地に文字だけ → コーヒー豆や雑穀の袋に見えた
 2稿 白地・赤帯・写真の小窓 → まだ要素が少なく、売り場のものに見えない
 3稿 赤ベタ・断ち切り写真・白フチの極太名。袋を自立袋から平袋に
 4稿 市販の平袋に構成を寄せ、切り抜きの1個と金の枠罫を足す
 5稿 紙箱（カートン）に変えた → 売り場の冷凍餃子はやはり袋
 6稿（これ）袋に戻す。ただし枕型のふくらんだパウチではなく、中にトレーが
      入って板のように平たい袋。真上から撮った1枚に、弧を使わず透視だけで
      刷る。面が平らなので大きな文字も金の縁も歪まない。訴求のバッジは
      5稿のまま増やしてある

  冷凍餃子の容器を調べた結果（9/20）：
   - 専用の耐寒トレーが入る製品があり、袋はふくらまず板状になる（丸善）
   - 冷凍食品用の紙箱（耐水紙・コートボール）は一般的で、専門の印刷通販が
     冷凍食品向けカートンを扱っている（紙箱・化粧箱.NET、アート印刷所）
   - 通販・ギフトの餃子は化粧箱が主（宇都宮餃子会）
   どのメーカーがどの形、という対応表は見つからなかったので、
   トレーが入って平たくなる、という点だけを取って袋の形を決めている
"""
import math
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

FONTS = "/tmp/fonts"
GOTHIC = f"{FONTS}/NotoSansJP-Black.ttf"
ZEN = f"{FONTS}/ZenKakuNew-Black.ttf"

SS = 2
DW, DH = 1000, 585           # 意匠を組む座標（袋の刷り面の比に合わせた）
SW, SH = 1800, 1053          # 原稿の解像度。面（約1770px 幅）より大きく取る

# 袋の刷り面の四隅（2752x1536 の写真から実測）。左右の羽根の内側。時計回り
FRONT = [(520, 240), (2292, 240), (2292, 1284), (520, 1284)]
# 羽根まで含めた袋ぜんたい。ここは地色だけを流す（実物も色は端まで回る）
BAG = [(330, 180), (2425, 180), (2425, 1345), (330, 1345)]

# 金の斜め帯（面に対する割合）。左下の起点・右へ上がる量・太さ
BAND_X0, BAND_Y0, BAND_RISE, BAND_TH = 0.46, 0.800, 0.145, 0.200
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
    """刷り面の意匠を返す。photo は商品写真、hero は切り抜きの1個。"""
    W, H = SW * SS, SH * SS
    k = W / DW                      # 意匠の座標（DW×DH）から画素への倍率
    img = _ground(W, H)

    # 商品写真を面の左いっぱいに敷く。右だけ抜いて赤に渡す
    pw, ph = int(640 * k), H
    # 地が明るいぶん、写真を起こしすぎると白茶ける
    p = _lift(photo, gamma=0.80, sat=1.12)
    sw, sh = p.size
    ch = int(sh * PHOTO_FILL)
    cw = int(ch * pw / ph)
    cx0 = max(0, min(sw - cw, int(sw * 0.50 - cw / 2)))
    cy0 = max(0, min(sh - ch, int(sh * PHOTO_CY - ch / 2)))
    p = p.crop((cx0, cy0, cx0 + cw, cy0 + ch)).resize((pw, ph), Image.LANCZOS)
    xx = np.arange(pw)[None, :].astype(np.float32)
    ed = (np.linspace(520, 625, ph, dtype=np.float32) * k)[:, None]
    mk = np.clip((ed - xx) / (105 * k), 0, 1) ** 0.85
    img.paste(p, (0, 0), Image.fromarray((mk * 255).astype(np.uint8)))
    d = ImageDraw.Draw(img)

    f_logo_s = ImageFont.truetype(GOTHIC, int(12 * k))
    f_logo = ImageFont.truetype(GOTHIC, int(28 * k))
    f_n1 = ImageFont.truetype(GOTHIC, int(62 * k))
    f_n2 = ImageFont.truetype(GOTHIC, int(172 * k))
    f_rom = ImageFont.truetype(GOTHIC, int(36 * k))
    f_copy1 = ImageFont.truetype(GOTHIC, int(33 * k))
    f_copy2 = ImageFont.truetype(GOTHIC, int(36 * k))
    f_tiny = ImageFont.truetype(ZEN, int(11 * k))
    f_box = ImageFont.truetype(ZEN, int(18 * k))
    f_box_s = ImageFont.truetype(ZEN, int(12 * k))

    # 右下の金の斜め帯。上に細い罫を1本、そのうえにコピーを2行
    band = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    bd = ImageDraw.Draw(band)
    x0, x1 = BAND_X0 * DW, DW
    yt0, yt1 = BAND_Y0 * DH, (BAND_Y0 - BAND_RISE) * DH
    th = BAND_TH * DH
    bd.polygon([(x0 * k, yt0 * k), (x1 * k, yt1 * k),
                (x1 * k, (yt1 + th) * k), (x0 * k, (yt0 + th) * k)],
               fill=GOLD + (255,))
    bd.line([(x0 * k, (yt0 - 11) * k), (x1 * k, (yt1 - 11) * k)],
            fill=GOLD + (235,), width=int(4 * k))
    img.paste(band, (0, 0), band)
    d = ImageDraw.Draw(img)

    ang = math.degrees(math.atan2((yt0 - yt1) * k, (x1 - x0) * k))
    lines = [(COPY1, f_copy1), (COPY2, f_copy2)]
    tw = int(max(_tw(d, t, f, 2 * k) for t, f in lines)) + int(22 * k)
    cop = Image.new("RGBA", (tw, int(88 * k)), (0, 0, 0, 0))
    cd = ImageDraw.Draw(cop)
    yy = int(3 * k)
    for t, f in lines:
        _tt(cd, tw / 2, yy, t, f, 2 * k, RED_D + (255,))
        yy += int(41 * k)
    cop = cop.rotate(ang, expand=True, resample=Image.BICUBIC)
    mx = 0.735
    my = (yt0 - (yt0 - yt1) * (mx * DW - x0) / (x1 - x0) + th / 2) / DH
    img.paste(cop, (int(mx * W - cop.width / 2), int(my * H - cop.height / 2)),
              cop)

    # 右上に切り抜きの1個。同じCMの箸のカットから背景を抜いたもの
    if hero is not None:
        hw = int(340 * k)
        hh = int(hw * hero.height / hero.width)
        hz = hero.resize((hw, hh), Image.LANCZOS)
        sh_ = Image.new("RGBA", (hw, hh), (0, 0, 0, 0))
        sh_.paste((0, 0, 0, 95), (0, 0), hz.split()[3])
        sh_ = sh_.filter(ImageFilter.GaussianBlur(2.4 * k))
        img.paste(sh_, (int(654 * k), int(18 * k)), sh_)
        img.paste(hz, (int(650 * k), int(10 * k)), hz)
        d = ImageDraw.Draw(img)

    # 商品名。写真の上にまたがらせて、面の幅いっぱいに使う
    ncx = 470 * k
    sx, sy = int(6 * k), int(7 * k)
    _tt(d, ncx + sx, 132 * k + sy, "こがね", f_n1, 8 * k, (70, 10, 12),
        stroke=int(8 * k), stroke_fill=(70, 10, 12))
    _tt(d, ncx, 132 * k, "こがね", f_n1, 8 * k, WHITE,
        stroke=int(8 * k), stroke_fill=(46, 6, 8))
    _tt(d, ncx + sx, 192 * k + sy, "餃子", f_n2, 11 * k, (70, 10, 12),
        stroke=int(13 * k), stroke_fill=(70, 10, 12))
    _tt(d, ncx, 192 * k, "餃子", f_n2, 11 * k, WHITE,
        stroke=int(13 * k), stroke_fill=(46, 6, 8))
    _tt(d, ncx, 386 * k, "GYOZA", f_rom, 9 * k, GOLD,
        stroke=int(4 * k), stroke_fill=(70, 10, 12))

    # 左上：ブランドの白箱
    bx0, by0, bx1, by1 = 28 * k, 20 * k, 222 * k, 100 * k
    d.rounded_rectangle([bx0, by0, bx1, by1], radius=8 * k, fill=WHITE)
    d.text(((bx0 + bx1) / 2, by0 + 9 * k), "FRESH FROZEN", font=f_logo_s,
           fill=(120, 110, 104), anchor="mt")
    d.text(((bx0 + bx1) / 2, by0 + 29 * k), "こがね食品", font=f_logo,
           fill=RED, anchor="mt")

    # 左に訴求のバッジを縦に3つ。売り場の冷凍餃子はここが賑やか
    _badge(img, 88 * k, 192 * k, 52 * k, 52 * k,
           [("油・水", 25, WHITE), ("いらず", 25, WHITE)], k)
    _badge(img, 88 * k, 310 * k, 52 * k, 52 * k,
           [("フタも", 25, WHITE), ("不要", 25, WHITE)], k)
    _badge(img, 88 * k, 438 * k, 58 * k, 66 * k,
           [("元祖", 15, GOLD), ("羽根", 30, WHITE), ("つき", 30, WHITE)], k)
    # 右に金の星バッジ
    _star(img, 904 * k, 268 * k, 64 * k, 12, k, [("新", 26), ("発売", 26)])
    d = ImageDraw.Draw(img)

    d.text((156 * k, 490 * k), "（調理例）", font=f_tiny, fill=WHITE, anchor="lt",
           stroke_width=int(2 * k), stroke_fill=(30, 22, 18))

    # 下の情報。白い小箱を並べる
    bxs = [("要冷凍", None), ("12個入り", "(300g)"), ("フライパン", "ひとつで"),
           ("たれ付き", None)]
    x = 28 * k
    y0b, y1b = 512 * k, 556 * k
    for main, sub in bxs:
        w = int((84 if sub else 68) * k)
        d.rectangle([x, y0b, x + w, y1b], fill=WHITE)
        if sub:
            d.text((x + w / 2, y0b + 4 * k), main, font=f_box, fill=RED_D,
                   anchor="mt")
            d.text((x + w / 2, y0b + 24 * k), sub, font=f_box_s, fill=INK,
                   anchor="mt")
        else:
            d.text((x + w / 2, (y0b + y1b) / 2), main, font=f_box, fill=RED_D,
                   anchor="mm")
        x += w + int(8 * k)

    # 面のふちに金の枠。これで全体が締まる
    fr = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    fd = ImageDraw.Draw(fr)
    fd.rounded_rectangle([11 * k, 11 * k, W - 11 * k, H - 11 * k],
                         radius=10 * k, outline=GOLD + (255,), width=int(5 * k))
    fd.rounded_rectangle([23 * k, 23 * k, W - 23 * k, H - 23 * k],
                         radius=7 * k, outline=GOLD_D + (150,), width=int(2 * k))
    img.paste(fr, (0, 0), fr)

    return img.resize((SW, SH), Image.LANCZOS)


def _persp(dst, src):
    """dst の4点を src の4点へ写す係数。PIL の transform は出力→入力で引く。"""
    A, B = [], []
    for (x, y), (u, v) in zip(dst, src):
        A.append([x, y, 1, 0, 0, 0, -u * x, -u * y]); B.append(u)
        A.append([0, 0, 0, x, y, 1, -v * x, -v * y]); B.append(v)
    return np.linalg.solve(np.array(A, np.float64), np.array(B, np.float64))


def silhouette(base, quad, lo=115.0, hi=175.0, feather=1.4):
    """袋の輪郭でマスクを作る。地の木目は暗いので明るさだけで拾える。"""
    lum = np.asarray(base.convert("RGB")).astype(np.float32).mean(2)
    m = np.clip((lum - lo) / (hi - lo), 0, 1)
    box = Image.new("L", base.size, 0)
    ImageDraw.Draw(box).polygon([tuple(q) for q in quad], fill=255)
    m = m * (np.asarray(box).astype(np.float32) / 255.0)
    m = np.asarray(Image.fromarray((m * 255).astype(np.uint8)).filter(
        ImageFilter.GaussianBlur(feather))).astype(np.float32) / 255.0
    return m


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
    # 1回目は羽根まで含めて地色だけ。2回目に刷り面の意匠を重ねる
    faces = [(_ground(600, 340), BAG, silhouette(base, BAG)),
             (build_art(Image.open(photo_path).convert("RGB"), hero),
              FRONT, None)]
    for art, quad, msk in faces:
        rgb, al = place_on_quad(art, base.size, quad)
        if msk is not None:
            al = msk
        # 面ごとに明るさを測り、その面の陰影だけをインクに乗せる
        m = Image.new("L", base.size, 0)
        ImageDraw.Draw(m).polygon([tuple(q) for q in FRONT], fill=255)
        sel = np.asarray(m) > 200
        ref = float(np.median(lum[sel])) if sel.any() else 200.0
        shade = np.clip(lum / max(ref, 1e-6), 0.62, 1.16)[..., None]
        printed = np.clip(rgb * shade, 0, 255) + rng.normal(0, 1.3, rgb.shape)
        out = out * (1 - al[..., None]) + printed * al[..., None]
    Image.fromarray(np.clip(out, 0, 255).astype(np.uint8)).save(dst)
    return dst


FFMPEG = ("/usr/local/lib/python3.11/dist-packages/imageio_ffmpeg/binaries/"
          "ffmpeg-linux-x86_64-v7.0.2")


def cutout(src, dst, blank=None, pad=48, off=(18, 24), blur=22, dark=0.58):
    """刷った袋を地から抜いて、影をつけた PNG にする。食卓のカットに載せる用。

    輪郭は必ず無地の袋（blank）から取る。刷り終わった写真から明るさで拾うと、
    赤い地の明るさが低いぶん抜けが薄くなり、載せたとき半透明に見える。
    """
    base = Image.open(src).convert("RGB")
    m = silhouette(Image.open(blank).convert("RGB") if blank else base, BAG)
    al = Image.fromarray((np.clip(m, 0, 1) * 255).astype(np.uint8))
    rgba = base.convert("RGBA")
    rgba.putalpha(al)
    x0 = max(0, min(q[0] for q in BAG) - pad)
    y0 = max(0, min(q[1] for q in BAG) - pad)
    x1 = min(base.width, max(q[0] for q in BAG) + pad + off[0] + blur)
    y1 = min(base.height, max(q[1] for q in BAG) + pad + off[1] + blur)
    cut = rgba.crop((x0, y0, x1, y1))
    sh = Image.new("RGBA", cut.size, (0, 0, 0, 0))
    sh.paste((0, 0, 0, int(255 * dark)), off, cut.split()[3])
    sh = sh.filter(ImageFilter.GaussianBlur(blur))
    out = Image.alpha_composite(sh, cut)
    out.save(dst)
    return dst


def on_table(table, packpng, out, dur=5.0, tin=0.0, cw=1920, chh=1080,
             width=0.45, mr=0.030, mb=0.050, at=1.20, rise=0.42, grade=None):
    """食卓のカットにパッケージを載せる。CMの締めはこの1カットで持たせる。

    パッケージは画面の外（右）から滑り込ませ、少し行き過ぎてから収まる。
    フェードで薄く出すと商品が幽霊のように見えて締まらない。

    階調はここで当てる（build.py 側では素通し）。持ち上げをパッケージにまで
    かけると、刷った赤がピンクに飛ぶ。
    """
    import subprocess
    pw = int(cw * width)
    mrp, mbp = int(cw * mr), int(chh * mb)
    gf = f"{grade}," if grade else ""
    # 0 → 1 に進む量。行き過ぎて戻る（イーズアウト・バック）
    u = f"clip((t-{at})/{rise},0,1)"
    ez = f"(1+2.70158*pow({u}-1,3)+1.70158*pow({u}-1,2))"
    fc = (
        f"[0:v]trim={tin}:{tin + dur},setpts=PTS-STARTPTS,"
        f"crop='min(iw,ih*{cw}/{chh})':'min(ih,iw*{chh}/{cw})',"
        f"scale={cw}:{chh}:flags=lanczos,setsar=1,{gf}fps=24[bg];"
        f"[1:v]scale={pw}:-1,format=rgba,setpts=PTS-STARTPTS[pk];"
        f"[bg][pk]overlay=x='W-w-{mrp}+(w+{mrp})*(1-{ez})':"
        f"y=H-h-{mbp}:shortest=1[v]"
    )
    subprocess.run([FFMPEG, "-loglevel", "error", "-y", "-i", table,
                    "-loop", "1", "-i", packpng, "-filter_complex", fc,
                    "-map", "[v]", "-t", str(dur), "-an",
                    "-c:v", "libx264", "-crf", "16", "-preset", "slow",
                    "-pix_fmt", "yuv420p", out], check=True)
    return out


# --- パッケージ単体に寄るカット（いまは使っていない）------------------------


def clip(still, out, dur=3.4, cw=1920, chh=1080, fps=24, z0=2540, z1=2290):
    """刷ったパッケージ写真の、正面の中心にゆっくり寄る。

    寄りは 10% ほど。袋は高さ約1140px なので、これ以上寄せると 16:9 の枠に
    上下の羽根まで入らない。
    """
    import subprocess
    src = Image.open(still).convert("RGB")
    sw, sh = src.size
    cx = 1376.0 * sw / 2752.0          # 袋の中心（羽根を含む）
    cy = 762.0 * sh / 1536.0
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
