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

W, H = 1920, 1080          # 既定は16:9。縦型は set_canvas() で切り替える


def set_canvas(w, h):
    global W, H
    W, H = w, h
FONTS = os.environ.get("SO_FONTS", "/tmp/fonts")
ZEN = f"{FONTS}/ZenKakuNew-Black.ttf"
GOTHIC = f"{FONTS}/NotoSansJP-Black.ttf"
# 明朝は 05（縦型）だけで使う。ゴシックより「読ませる」より「効かせる」向き
MINCHO = f"{FONTS}/NotoSerifJP-Black.ttf"
# 締めの小さい文字。極太を小さく置くと潰れるので中細を使う
MINCHO_M = f"{FONTS}/NotoSerifJP-Medium.ttf"

ACCENT = (245, 181, 42)       # 山吹。04ブロックの縦バーに残す1色
NAVY = (15, 33, 64)           # 02の帯
LAMP = (238, 212, 168)        # 05の罫。夜のランドリーの灯りに寄せた暖色
EMO_ACCENT = (250, 196, 112)  # 05の差し色。山吹（04のバー）はポップに寄るので琥珀に
OUT = os.path.dirname(os.path.abspath(__file__)) + "/telop"
os.makedirs(OUT, exist_ok=True)

# 架空の名前（差し替え用）
SERVICE_NAME = "そのまま日報"
SERVICE_SUB = "現場の日報アプリ"
PRODUCT_NAME = "こがね餃子"
PRODUCT_SUB = "羽根つき 冷凍餃子"
SHOP_NAME = "きらら"
SHOP_SUB = "コインランドリー ／ 24時間・年中無休"

# 本文 / 色を差すキーワード / デザイン
# 02（業務ソフト）と04（食品CM）でテロップのデザインを作り分ける。
#   scrim … 文字は純白のまま、画面下部を黒のグラデーションで落とす（02・03）。
#           映画の字幕の作り。文字自体には影もフチも付けない
#   block … 黒ブロック＋白文字＋山吹の縦バー（04）。文字幅ぶんのブロック
#   emo   … 縦型（05）。明朝の極太＋字間広め＋文字の背後にやわらかい発光。
#           下敷きは角丸ブロックをやめ、ぼかした暗がりにして縁を出さない。
#           文字の上に細い暖色の罫を1本置く。夜の画に合わせた「効かせる」作り
#           （前身の sns は角丸ブロック＋ゴシックでポップに寄りすぎていた）
#   step  … 白帯＋黒文字＋左に大きなSTEP番号（07）。研修用なので可読性を最優先
#   white_band … 白帯＋黒文字（03の3分版の第4章）。STEP番号は無い。
#           数字を出すカットだけ本文と別扱いにして「事実」だと分かるようにする
# 02は帯 → 影 → グラデーションと3回変えた。影は黒フチと重ねぼかしが汚れて見えた。
TELOPS = {
    "02_1": ("現場で、その場で。", None, "scrim"),
    "02_2": ("事務所には、もう届いている。", None, "scrim"),
    "02_3": ("日報の転記を、なくす。", None, "scrim"),
    # 9/20 差し替え。黒ブロック（block）は画面の上に貼った板に見えていたので、
    # 画面下を落とすだけの cm に変えた。文言もCMの運びに合わせて組み直し
    "04a_1": ("凍ったまま、フライパンへ。", None, "cm"),
    "04a_2": ("羽根まで、ぱりっと。", None, "cm"),
    "04a_3": ("肉汁、そのまま。", None, "cm"),
    "04b_1": ("今日は、もう決まり。", None, "block"),
    "04b_2": ("フライパンひとつ、10分。", None, "block"),
    # 03 採用（16:9・scrim）
    "03_1": ("教える人が、すぐ隣にいる。", None, "scrim"),
    "03_2": ("3年目で、任される。", None, "scrim"),
    "03_3": ("見に来てください。", None, "scrim"),
    # 07 社内向け（16:9・step）。STEP番号は本文と別に持つ
    "07_1": ("入る前に、装備を確認。", "STEP 1", "step"),
    "07_2": ("通路では、必ず止まる。", "STEP 2", "step"),
    "07_3": ("声に出して、指で差す。", "STEP 3", "step"),
}

# 03 採用・3分版（16:9）。本文は scrim、第4章の数字だけ white_band にして
# 「事実」だと分かるようにする。インタビューは鍵カッコ付き（本人の発言だと示す）
TELOPS_3MIN = {
    "r3_03": ("朝は8時。朝礼は5分で終わる。", None, "scrim"),
    "r3_05": ("つくっているのは、機械の中に入る部品です。", None, "scrim"),
    "r3_08": ("1個あたり、数分。", None, "scrim"),
    "r3_10": ("図面の指示は 0.01mm 単位。", None, "scrim"),
    "r3_11": ("ここから検査に回ります。", None, "scrim"),
    "r3_13": ("記録は全部残します。", None, "scrim"),
    "r3_15": ("分からないことは、その場で聞けます。", None, "scrim"),
    "r3_17": ("「最初の半年は、\nずっと先輩の隣でした」", None, "scrim"),
    "r3_18": ("「3年目の今は、\n一人で段取りまでやります」", None, "scrim"),
    "r3_19": ("「教えるのは、手が空いた人。\n担当は決めていません」", None, "scrim"),
    "r3_22": ("「子どもの送りがあるので、\n始業を30分ずらしています」", None, "scrim"),
    "r3_24": ("教わった人が、教える側になる。", None, "scrim"),
    "r3_25": ("「1年目でも、機械は触らせてもらえます」", None, "scrim"),
    "r3_27": ("社員 24人。平均年齢 38歳。", None, "white_band"),
    "r3_28": ("設備は5年で3台入れ替えました。", None, "white_band"),
    "r3_29": ("検査室は空調完備。", None, "white_band"),
    "r3_30": ("作業着は会社支給。洗濯も会社で。", None, "white_band"),
    "r3_31": ("昼は40分。弁当の注文もできます。", None, "white_band"),
    "r3_32": ("残業は月平均 12時間。", None, "white_band"),
    "r3_34": ("「見学だけでも、\n来てもらえたら分かります」", None, "scrim"),
}

# 05 SNSショート（9:16・sns）。キャンバスが違うので別に持つ
TELOPS_V = {
    "05_1": ("夜11時。", "11時", "emo"),
    "05_2": ("まだ、空いてる。", "空いてる", "emo"),
    "05_3": ("乾燥、30分。", "30分", "emo"),
    "05_4": ("畳んで、帰る。", "帰る", "emo"),
    "05_5": ("待つ場所も、ある。", "ある", "emo"),
    "05_6": ("24時間・年中無休", "24時間", "emo"),
}

SIZE = 132
LEFT = 100
BOTTOM = 112
PAD_X, PAD_T, PAD_B = 30, 22, 26
TRACK = 11          # emo の字間(px)
# 約物のツメ。全角のまま置くと「音が、／ちがう。」の間が二字ぶん空いて見える。
# 値は「その文字の送り幅に対して引く割合」
TIGHTEN = {"、": 0.42, "。": 0.42, "，": 0.42, "．": 0.42,
           "・": 0.22, "：": 0.3, "；": 0.3}


def dim_alpha(img, k):
    """alpha だけ k 倍する。発光を重ねるときに濃さを決める。"""
    a = np.array(img)
    a[:, :, 3] = (a[:, :, 3] * k).astype(np.uint8)
    return Image.fromarray(a)


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
    # 長い引用は2行に割る（\n で区切る）。1行のまま縮めると
    # 下限の84pxでも画面に収まらず、右端で切れる
    lines = text.split("\n")
    rows = [split_accent(t, accent) if style != "step" else [(t, False)]
            for t in lines]
    parts = rows[0]
    # スタイルごとの文字サイズと置き場所
    #   scrim/block … 132px・左寄せ（16:9）
    #   sns         … 104px・中央寄せ（縦型は横幅が狭い）
    #   step        … 96px・左寄せ。左端のSTEP番号ブロック(268px)を避けて 330px から
    size = {"emo": 98, "step": 96, "white_band": 96}.get(style, SIZE)
    left = {"step": 330}.get(style, LEFT)
    bottom = {"emo": int(H * 0.32), "step": 118, "white_band": 118}.get(style, BOTTOM)
    # emo は字間を空ける。明朝を大きく置くと詰まって見えるのを開く
    track = TRACK if style == "emo" else 0
    face = MINCHO if style == "emo" else ZEN
    while size > 84:
        f = ImageFont.truetype(face, size)
        w = max(sum(f.getlength(t) for t, _ in r) + track * (len(lines[i]) - 1)
                for i, r in enumerate(rows)) + PAD_X * 2 + left - 70
        if w <= (W - 120 if style == "emo" else MAX_BLOCK_W):
            break
        size -= 4
    f = ImageFont.truetype(face, size)
    lead = int(size * 1.44)     # 行送り
    # 2行目以降は、1行目の「かぎ括弧のぶんだけ下げて、本文の1文字目に揃える。
    # 括弧の下に文字が来ると、引用の始まりがどこか読み取りにくい
    indent = (f.getlength(lines[0][0]) + track
              if len(lines) > 1 and lines[0][:1] in ("「", "『", "（", "\"") else 0)
    # 白帯に乗る step だけ黒文字。ほかは白
    body = (17, 17, 17) if style in ("step", "white_band") else (255, 255, 255)

    ac_col = EMO_ACCENT if style == "emo" else ACCENT

    def draw(d, ox, oy):
        # 1文字ずつ置く。約物を詰めるのと字間を空けるのに、まとめ描きだと足りない
        for i, row in enumerate(rows):
            x, y = ox + (indent if i else 0), oy + i * lead
            flat = [(ch, is_ac) for t, is_ac in row for ch in t]
            for j, (ch, is_ac) in enumerate(flat):
                d.text((x, y), ch, font=f, fill=(ac_col if is_ac else body) + (255,))
                x += d.textlength(ch, font=f) + track
                # 読点・句点は全角のまま置くと後ろが二字ぶん空いて見える。
                # 行末の1文字は下敷きの右端を決めるので詰めない
                if ch in TIGHTEN and j < len(flat) - 1:
                    x -= d.textlength(ch, font=f) * TIGHTEN[ch]

    txt = place(draw, left=left, bottom=bottom,
                center_x=(style == "emo"))
    bb = real_bbox(txt)
    img = blank()
    # block に発光を足していたが、ぼかしがブロックの外に40px以上はみ出して、
    # 暗い映像の上では黒ブロックの上に灰色の帯が乗ったように見えていた。
    # 209/255 の黒ブロックに白文字なら、それだけで十分に読める
    if style == "cm":
        # 黒ブロックをやめ、画面下の暗がりに乗せる（下敷きは build_set 側）。
        # 帯が無くなると味気ないので、本文の上に山吹の細い罫を1本だけ置く
        rw, rh, gap = 180, 4, 34
        ry = bb[1] - gap
        ramp = np.zeros((H, W), dtype=np.uint8)
        x0, x1 = bb[0], bb[0] + rw
        prof = np.clip(np.sin(np.linspace(0, np.pi, x1 - x0)) * 2.6, 0, 1) * 255
        ramp[ry:ry + rh, x0:x1] = prof.astype(np.uint8)
        rule = Image.composite(Image.new("RGBA", (W, H), ACCENT + (255,)),
                               blank(), Image.fromarray(ramp))
        img.alpha_composite(dim_alpha(rule.filter(ImageFilter.GaussianBlur(9)), 0.9))
        img.alpha_composite(rule)
        bb = (bb[0], ry, bb[2], bb[3])
    if style == "emo":
        # 文字そのものを光らせる。02で嫌われた「黒フチ＋重ねぼかし」とは別物で、
        # フチを作らず、広く薄いぼかしを2段重ねるだけ。夜の画で文字が浮く
        img.alpha_composite(dim_alpha(txt.filter(ImageFilter.GaussianBlur(34)), 0.62))
        img.alpha_composite(dim_alpha(txt.filter(ImageFilter.GaussianBlur(10)), 0.5))
        # 本文の上に細い暖色の線を1本。装飾はこれ1つに絞る。
        # 均一な棒だとハイフンに見えるので、両端を落として光の筋にする
        rw, rh, gap = 230, 4, 48
        cx = (bb[0] + bb[2]) // 2
        ry = bb[1] - gap
        ramp = np.zeros((H, W), dtype=np.uint8)
        x0, x1 = cx - rw // 2, cx + rw // 2
        # 中央は濃いまま、端の2割だけで落とす（全体を丸めると線が消える）
        prof = np.clip(np.sin(np.linspace(0, np.pi, x1 - x0)) * 2.6, 0, 1) * 255
        ramp[ry:ry + rh, x0:x1] = prof.astype(np.uint8)
        rule = Image.composite(Image.new("RGBA", (W, H), LAMP + (255,)),
                               blank(), Image.fromarray(ramp))
        img.alpha_composite(dim_alpha(rule.filter(ImageFilter.GaussianBlur(11)), 1.0))
        img.alpha_composite(rule)
        bb = (bb[0], ry, bb[2], bb[3])
    img.alpha_composite(txt)
    img.save(f"{OUT}/{key}.png")
    box = {"x": max(0, bb[0] - PAD_X), "y": bb[1] - PAD_T,
           "w": (bb[2] + PAD_X) - max(0, bb[0] - PAD_X),
           "h": (bb[3] + PAD_B) - (bb[1] - PAD_T)}
    return box


def _track_w(f, text, track):
    """字間を入れた実寸。締めの行を中央に置くのに使う。"""
    return sum(f.getlength(ch) for ch in text) + track * (len(text) - 1)


def _track_text(d, text, f, track, cx, cy, fill):
    """字間を空けて中央寄せで1行置く。PIL に letter-spacing が無いので1文字ずつ。"""
    x = cx - _track_w(f, text, track) / 2
    for ch in text:
        d.text((x, cy), ch, font=f, fill=fill, anchor="lm")
        x += f.getlength(ch) + track


def end_card_v(over, name, under, path, cy_ratio=0.42):
    """05（縦型）の締め。ロゴの組みに寄せた3段。

    上に業種、中央に明朝の社名、その下に暖色の光の線と営業時間。
    02/04 と同じ logo_card（極太ゴシックを中央に置くだけ）では、
    夜のコインランドリーの画に対して素っ気なかった。
    字間を大きく開け、線を1本だけ入れて「看板」に見せる。
    """
    n_size, s_size = 136, 40
    n_track, o_track, u_track = 24, 18, 14
    while n_size > 96:
        f_name = ImageFont.truetype(MINCHO, n_size)
        if _track_w(f_name, name, n_track) <= W - 200:
            break
        n_size -= 4
    f_name = ImageFont.truetype(MINCHO, n_size)
    f_over = ImageFont.truetype(MINCHO_M, s_size)
    f_under = ImageFont.truetype(MINCHO_M, s_size - 2)
    while s_size > 24:
        f_over = ImageFont.truetype(MINCHO_M, s_size)
        f_under = ImageFont.truetype(MINCHO_M, s_size - 2)
        if (max(_track_w(f_over, over, o_track),
                _track_w(f_under, under, u_track)) <= W - 160):
            break
        s_size -= 2

    # 段の高さは文字サイズで見る。行間は「効かせる」ために広く取る
    h_over, h_name, h_under, rh = s_size, n_size, s_size - 2, 3
    g1, g2, g3 = 52, 54, 46
    total = h_over + g1 + h_name + g2 + rh + g3 + h_under
    top = int(H * cy_ratio) - total // 2
    cx = W // 2
    y_over = top + h_over // 2
    y_name = top + h_over + g1 + h_name // 2
    y_rule = top + h_over + g1 + h_name + g2
    y_under = y_rule + rh + g3 + h_under // 2

    img = blank()
    d = ImageDraw.Draw(img)
    # 業種は白をわずかに温かく、社名は純白、営業時間は灯りの色。
    # 大きさの差だけでなく色の差でも段を作る
    _track_text(d, over, f_over, o_track, cx, y_over, (238, 231, 216, 228))
    _track_text(d, name, f_name, n_track, cx, y_name, (255, 255, 255, 255))
    _track_text(d, under, f_under, u_track, cx, y_under, LAMP + (236,))

    # 光の線。本編のテロップと同じ作り（両端を落として筋にする）
    rw = int(min(max(_track_w(f_name, name, n_track) * 0.62, 200), 420))
    ramp = np.zeros((H, W), dtype=np.uint8)
    x0, x1 = cx - rw // 2, cx + rw // 2
    prof = np.clip(np.sin(np.linspace(0, np.pi, x1 - x0)) * 2.6, 0, 1) * 255
    ramp[y_rule:y_rule + rh, x0:x1] = prof.astype(np.uint8)
    rule = Image.composite(Image.new("RGBA", (W, H), LAMP + (255,)),
                           blank(), Image.fromarray(ramp))

    # 文字の背後に黒のぼかしを敷く。夜の画でも建屋の白壁に文字が重なるので、
    # 影が無いと社名の輪郭が壁に溶ける
    sil = Image.composite(Image.new("RGBA", (W, H), (0, 0, 0, 255)),
                          blank(), img.split()[3])
    base = blank()
    # 締めの帯。ぼかした暗がりを1枚敷いて、店先の灯りを中央だけ落とす。
    # 敷かないと「24時間・年中無休」が入口の明かりに重なって読めなかった。
    # 縁が出ないので画は壊さず、路面の照り返しと空はそのまま残る
    band = blank()
    ImageDraw.Draw(band).rounded_rectangle(
        [int(W * 0.05), top - 130, int(W * 0.95),
         y_under + h_under // 2 + 130], radius=220, fill=(3, 6, 14, 140))
    base.alpha_composite(band.filter(ImageFilter.GaussianBlur(96)))
    for blur, k in ((40, 0.9), (14, 0.82), (5, 0.6)):
        base.alpha_composite(dim_alpha(sil.filter(ImageFilter.GaussianBlur(blur)), k))
    # 社名をやわらかく光らせる（本編の emo と同じ扱いにして1本の中で揃える）
    base.alpha_composite(dim_alpha(img.filter(ImageFilter.GaussianBlur(30)), 0.5))
    base.alpha_composite(dim_alpha(rule.filter(ImageFilter.GaussianBlur(11)), 1.0))
    base.alpha_composite(rule)
    base.alpha_composite(img)
    base.save(path)


def logo_card(name, sub, path, mark="check", tint=(255, 255, 255), cy_ratio=0.46):
    """締め。極太ゴシックで中央に。影で抜く。"""
    img = blank()
    shadow = blank()
    ds, d = ImageDraw.Draw(shadow), ImageDraw.Draw(img)
    # キャンバス幅に収まるまで縮める（縦型だと 104px では長い名前が切れる）
    n_size, s_size = 104, 40
    while n_size > 56:
        f_name = ImageFont.truetype(GOTHIC, n_size)
        mark_w = 0 if mark == "none" else 46 * 2 + 36
        if mark_w + f_name.getlength(name) <= W - 180:
            break
        n_size -= 4
    while s_size > 24:
        f_sub = ImageFont.truetype(ZEN, s_size)
        if f_sub.getlength(sub) <= W - 160:
            break
        s_size -= 2
    f_name = ImageFont.truetype(GOTHIC, n_size)
    f_sub = ImageFont.truetype(ZEN, s_size)
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


def build_set(table, label=""):
    """1つのキャンバスぶんのテロップと下敷きを書き、矩形の辞書を返す。"""
    boxes = {}
    for key, (text, accent, style) in table.items():
        boxes[key] = band_telop(key, text, accent, style)
        boxes[key]["style"] = style
    # 下敷きの天地は「同じ本の中」で揃える（カット替わりのチラつきを防ぐ）。
    # 本をまたいで揃えると、文字サイズと位置が違う本で帯が本文に合わなくなる
    # （07 の STEP 帯が本文を切ってしまう不具合の原因だった）
    def group_of(k):
        # 1本の中だけで揃える。rstrip("ab") で 04a と 04b をまとめていたので、
        # 取りやめた 04b の背の高い字（フ・1）がブロックの上端を決めてしまい、
        # 04a の上に使われない空きが出ていた。
        # スタイルも見る。3分版は1行の白帯と2行の引用が同じ "r3" なので、
        # まとめて揃えると白帯が2行ぶんの高さに広がってしまう
        return k.split("_")[0] + ":" + boxes[k]["style"]

    for g in {group_of(k) for k in boxes}:
        members = [k for k in boxes if group_of(k) == g]
        top = min(boxes[k]["y"] for k in members)
        bot = max(boxes[k]["y"] + boxes[k]["h"] for k in members)
        for k in members:
            boxes[k]["y"], boxes[k]["h"] = top, bot - top
    for key, b in boxes.items():
        b["underlay"] = True
        # グラデーションは動かさない（下から持ち上げると下端に隙間ができる）
        b["static_underlay"] = b["style"] in ("scrim", "cm")
        if b["style"] == "cm":
            # CM のテロップの動き。190px の持ち上げをやめて 44px を軽く上げ、
            # 文字は左から書き出す（wipe は build.py の geq で開けている）
            b["rise"], b["rise_d"] = 44, 0.42
            b["wipe"], b["wipe_edge"] = 0.62, 120
            b["txt_lag"], b["txt_in"] = 0.10, 0.20
        if b["style"] == "emo":
            # 下敷きはぼかした暗がりなので動かさない（動くと明るさが波打つ）。
            # 文字は 190px の持ち上げをやめ、28px をゆっくり浮かせる
            b["static_underlay"] = True
            b["rise"], b["rise_d"] = 28, 0.9
            b["blk_in"], b["txt_lag"] = 0.5, 0.18
            b["txt_in"], b["txt_out"] = 0.7, 0.5
        blk = blank()
        d = ImageDraw.Draw(blk)
        if b["style"] == "white_band":
            d.rectangle([0, b["y"], W, b["y"] + b["h"]], fill=(255, 255, 255, 249))
            d.rectangle([0, b["y"], 24, b["y"] + b["h"]], fill=NAVY + (255,))
        elif b["style"] == "emo":
            # 角丸ブロックをやめ、ぼかした暗がりを敷く。縁が出ないので
            # 夜の画に馴染み、それでいて明朝の白文字が沈まない
            pad_x, pad_y = 96, 88
            d.rounded_rectangle([b["x"] - pad_x, b["y"] - pad_y,
                                 b["x"] + b["w"] + pad_x,
                                 b["y"] + b["h"] + pad_y],
                                radius=180, fill=(3, 6, 14, 168))
            blk = blk.filter(ImageFilter.GaussianBlur(64))
        elif b["style"] == "step":
            d.rectangle([0, b["y"], W, b["y"] + b["h"]], fill=(255, 255, 255, 249))
            d.rectangle([0, b["y"], 268, b["y"] + b["h"]], fill=NAVY + (255,))
            fs = ImageFont.truetype(GOTHIC, 62)
            d.text((134, b["y"] + b["h"] // 2), table[key][1], font=fs,
                   fill=(255, 255, 255, 255), anchor="mm")
        elif b["style"] in ("scrim", "cm"):
            # 2行の引用は本文が上まで来るので、暗がりもその上から始める
            top_y = min(int(H * 0.574), b["y"] - 90)
            a = np.zeros((H, W), dtype=np.uint8)
            for y in range(top_y, H):
                a[y, :] = int(150 * (((y - top_y) / (H - top_y)) ** 1.5))
            blk = Image.composite(Image.new("RGBA", (W, H), (4, 8, 16, 255)),
                                  blank(), Image.fromarray(a))
        else:
            d.rectangle([b["x"], b["y"], b["x"] + b["w"], b["y"] + b["h"]],
                        fill=(0, 0, 0, 209))
            d.rectangle([b["x"], b["y"], b["x"] + 10, b["y"] + b["h"]],
                        fill=ACCENT + (255,))
        blk.save(f"{OUT}/{key}_blk.png")
    if label:
        print(f"[{label}] {W}x{H}: " + ", ".join(boxes))
    return boxes


if __name__ == "__main__":
    boxes = build_set(TELOPS, "16:9")
    logo_card(SERVICE_NAME, SERVICE_SUB, f"{OUT}/02_logo.png", mark="check")
    logo_card(PRODUCT_NAME, PRODUCT_SUB, f"{OUT}/04_logo.png", mark="none",
              tint=(255, 248, 232))
    # 訴求Bの締めは C2（箸の寄り）で中央に餃子が来るのでロゴを上に逃がす
    logo_card(PRODUCT_NAME, PRODUCT_SUB, f"{OUT}/04_logo_top.png", mark="none",
              tint=(255, 248, 232), cy_ratio=0.26)
    # 03 採用の締めは職種の提示（社名は出さない）
    logo_card("募集中", "機械加工 ／ 検査 ／ 出荷", f"{OUT}/03_logo.png", mark="none")
    for a, name in ((88, "dim34"), (74, "dim29")):
        Image.new("RGBA", (W, H), (0, 0, 0, a)).save(f"{OUT}/{name}.png")

    boxes_r3 = build_set(TELOPS_3MIN, "16:9 / 採用3分")
    logo_card("募集中", "機械加工 ／ 検査 ／ 出荷", f"{OUT}/r3_logo.png", mark="none")

    # 05 は縦型なのでキャンバスを切り替えて作り直す
    set_canvas(1080, 1920)
    boxes_v = build_set(TELOPS_V, "9:16")
    end_card_v("コインランドリー", SHOP_NAME, "24時間・年中無休",
               f"{OUT}/05_logo.png")
    Image.new("RGBA", (W, H), (0, 0, 0, 74)).save(f"{OUT}/dim29v.png")

    with open(f"{OUT}/boxes.json", "w") as fp:
        json.dump({"boxes": {**boxes, **boxes_r3, **boxes_v}}, fp,
                  ensure_ascii=False, indent=1)
