# -*- coding: utf-8 -*-
"""08 モーショングラフィックス「あおば健康保険組合 健診受診案内」を全部コードで描く。

初稿は「数字で見る、想工業。」（採用インフォグラフィック）で作ったが、
健診案内のほうがいいとの指摘で題材を戻した（9/19）。想工業版は
git 履歴（44c7d75）にあるので、要るときはそこから復活できる。

2稿（9/19）:
- 場面の切り替えを「山吹の運び役」で繋いだ。時計のリングが縮んで
  カレンダーのマスに飛び、そのマスが取り消し線の起点に伸び、
  取り消し線が締めの罫に変わる。単純なクロスフェードをやめた
- 画面が寂しいとの指摘で装飾を足した。薄い十字マーク（医療モチーフ）、
  大きな円の輪郭、左上の組合名、右上の進行ドット、数字が確定した
  瞬間のスパークル、見出し下の短い罫

クレジット消費は 0。フレームを PIL で描いて rawvideo で ffmpeg に流す。
円やグラフの縁を滑らかにするため2倍で描いて縮小する。

使い方: python3 infographic.py
"""
from PIL import Image, ImageDraw, ImageFont
import numpy as np
import os
import subprocess

W, H = 1920, 1080
SS = 2
FPS = 30
DUR = 15.0
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.environ.get("SO_OUT", f"{HERE}/out")
FONTS = os.environ.get("SO_FONTS", "/tmp/fonts")
ZEN = f"{FONTS}/ZenKakuNew-Black.ttf"
FF = ("/usr/local/lib/python3.11/dist-packages/imageio_ffmpeg/binaries/"
      "ffmpeg-linux-x86_64-v7.0.2")

# 色。深緑の地に生成りの文字、山吹のアクセント。くすんだ緑がかった
# グレーを台座に使う。#6E8B7D は深緑地とのコントラスト 3:1 を通してある
BG = (16, 51, 40)
INK = (238, 231, 214)
ACCENT = (245, 181, 42)
MUTED = (110, 139, 125)


def F(size):
    return ImageFont.truetype(ZEN, size * SS)


def clamp01(x):
    return max(0.0, min(1.0, x))


def eo(x):
    """ease-out cubic。数える・伸びる・並ぶの全部に使う"""
    x = clamp01(x)
    return 1 - (1 - x) ** 3


def a(col, alpha):
    return col + (int(255 * clamp01(alpha)),)


def text(d, xy, s, size, col, alpha=1.0, anchor="la", tracking=0):
    f = F(size)
    if tracking:
        # 1文字ずつ置くので、まず全体の幅を測って起点を出す。
        # anchor の x 成分（l/m/r）はここで消化し、文字は左詰めで置いていく
        total = sum(f.getlength(ch) for ch in s) / SS + tracking * (len(s) - 1)
        x, y = xy
        if anchor[0] == "m":
            x -= total / 2
        elif anchor[0] == "r":
            x -= total
        ch_anchor = "l" + (anchor[1] if len(anchor) > 1 else "a")
        for ch in s:
            d.text((x * SS, y * SS), ch, font=f, fill=a(col, alpha), anchor=ch_anchor)
            x += (f.getlength(ch) / SS) + tracking
        return
    d.text((xy[0] * SS, xy[1] * SS), s, font=f, fill=a(col, alpha), anchor=anchor)


def text_w(s, size):
    return F(size).getlength(s) / SS


def rrect(d, cx, cy, w, h, rad, col, alpha):
    d.rounded_rectangle([(cx - w / 2) * SS, (cy - h / 2) * SS,
                         (cx + w / 2) * SS, (cy + h / 2) * SS],
                        radius=rad * SS, fill=a(col, alpha))


def check_mark(d, cx, cy, r, col, alpha, w=None):
    """チェックマーク。左下がりの短い線＋右上がりの長い線"""
    w = w or max(4, int(r * 0.28))
    pts = [(cx - r * 0.55, cy + r * 0.05), (cx - r * 0.12, cy + r * 0.48),
           (cx + r * 0.62, cy - r * 0.42)]
    d.line([(x * SS, y * SS) for x, y in pts], fill=a(col, alpha),
           width=w * SS, joint="curve")


def sparkle(d, cx, cy, t, t0, col=ACCENT, n=8, r0=20):
    """数字が確定した瞬間の光。短い線が8方向へ散って消える"""
    u = (t - t0) / 0.45
    if not (0 < u < 1):
        return
    ue = eo(u)
    for k in range(n):
        ang = np.pi * 2 * k / n + 0.3
        ra = r0 + 46 * ue
        rb = ra + 20 * (1 - ue)
        d.line([(cx + np.cos(ang) * ra) * SS, (cy + np.sin(ang) * ra) * SS,
                (cx + np.cos(ang) * rb) * SS, (cy + np.sin(ang) * rb) * SS],
               fill=a(col, (1 - u) * 0.9), width=5 * SS)


def title(d, t, s):
    tt = eo((t - 0.1) / 0.6)
    text(d, (W / 2, 150 + 26 * (1 - tt)), s, 72, INK, tt, anchor="mm", tracking=6)
    # 見出し下の短い罫。装飾はこの太さで統一する
    rrect(d, W / 2, 212, 56 * tt, 5, 2, ACCENT, tt * 0.9)
    return tt


# ---------------------------------------------------------------- 背景の装飾

_rng = np.random.default_rng(11)
PLUS = [(float(_rng.uniform(80, W - 80)), float(_rng.uniform(240, H - 120)),
         float(_rng.uniform(10, 22)), float(_rng.uniform(0, 1)),
         bool(_rng.uniform() < 0.2)) for _ in range(14)]


def deco(d, gt):
    """全場面の下に敷く装飾。薄い十字（医療モチーフ）と大きな円の輪郭。
    動きはごくゆっくり。主役の数字より前に出ない濃さに抑える"""
    for (cx, cy, r, wd, al) in ((150, H - 60, 380, 3, 0.06),
                                (W - 130, 110, 260, 3, 0.06)):
        d.arc([(cx - r) * SS, (cy - r) * SS, (cx + r) * SS, (cy + r) * SS],
              0, 360, fill=a(INK, al), width=wd * SS)
    for (px, py, sz, ph, is_ac) in PLUS:
        drift = 8 * np.sin(2 * np.pi * (gt * 0.045 + ph))
        al = 0.05 + 0.04 * (0.5 + 0.5 * np.sin(2 * np.pi * (gt * 0.08 + ph * 3)))
        col = ACCENT if is_ac else MUTED
        y = py + drift
        rrect(d, px, y, sz, sz * 0.3, sz * 0.15, col, al * (1.6 if is_ac else 1.0))
        rrect(d, px, y, sz * 0.3, sz, sz * 0.15, col, al * (1.6 if is_ac else 1.0))


def chrome(d, gt):
    """全場面の上に載せる枠まわり。左上の組合名と右上の進行ドット"""
    # 締めでは中央に大きく名前が出るので、左上のは引っ込める
    al = 0.55 * (1 - eo((gt - 12.0) / 0.4))
    if al > 0.01:
        text(d, (52, 46), "あおば健康保険組合", 28, MUTED, al)
    cur = min(3, int(gt // 4))
    for i in range(4):
        x = W - 52 - (3 - i) * 30
        on = (i == cur)
        d.ellipse([(x - 7) * SS, (54 - 7) * SS, (x + 7) * SS, (54 + 7) * SS],
                  fill=a(ACCENT if on else INK, 0.9 if on else 0.22))
    text(d, (W - 48, H - 40), "※架空の健康保険組合のサンプル映像です。数字も架空です。",
         26, INK, 0.42, anchor="rs")


# ---------------------------------------------------------------- 場面

# 場面2のカレンダーの寸法。運び役の着地点の計算にも使うので外に出す
P_X, P_Y, P_W, P_H = 470, 320, 330, 580
C_COLS, C_ROWS, C_SZ, C_GAP = 7, 4, 34, 6
G_X = P_X + (P_W - C_COLS * C_SZ - (C_COLS - 1) * C_GAP) / 2
G_Y = P_Y + 110
TARGET = 18
TGT_X = G_X + (TARGET % C_COLS) * (C_SZ + C_GAP) + C_SZ / 2
TGT_Y = G_Y + (TARGET // C_COLS) * (C_SZ + C_GAP) + C_SZ / 2

S3_LABEL = "通常 ¥3,000 のところ"
S3_LW = None    # フォント読み込み後に測る


def scene1(d, t):
    """時計の円弧が一周して「30分」が数え上がる"""
    title(d, t, "年に1回の、30分。")
    cx, cy, r, wd = W / 2, 620, 250, 44
    al = eo((t - 0.35) / 0.4)
    # 運び役が縮み始めたらリングごと畳む（3.5秒から半径が縮んで中央へ）
    shrink = eo((t - 3.5) / 0.55)
    r = r * (1 - shrink)
    wd = max(4, wd * (1 - shrink * 0.5))
    box = [(cx - r) * SS, (cy - r) * SS, (cx + r) * SS, (cy + r) * SS]
    for k in range(12):
        ang = np.pi * 2 * k / 12 - np.pi / 2
        r0, r1 = r + wd / 2 + 18, r + wd / 2 + 38
        d.line([(cx + np.cos(ang) * r0) * SS, (cy + np.sin(ang) * r0) * SS,
                (cx + np.cos(ang) * r1) * SS, (cy + np.sin(ang) * r1) * SS],
               fill=a(INK, 0.25 * al * (1 - shrink)), width=4 * SS)
    if r > 20:
        d.arc(box, 0, 360, fill=a(MUTED, 0.4 * al * (1 - shrink)), width=int(wd) * SS)
        frac = eo((t - 0.55) / 1.7)
        if frac > 0:
            d.arc(box, -90, -90 + 360 * frac, fill=a(ACCENT, al), width=int(wd) * SS)
    fade_txt = 1 - shrink
    v = int(round(30 * eo((t - 0.55) / 1.7)))
    text(d, (cx, cy - 14), str(v), 150, INK, al * fade_txt, anchor="mm")
    text(d, (cx, cy + 96), "分で終わります", 40, MUTED, al * fade_txt, anchor="mm")
    sparkle(d, cx, cy - 250, t, 2.3)


def scene2(d, t):
    """スマホの中でカレンダーが組み上がり、1日にチェックが付く"""
    title(d, t, "予約は、スマホで1分。")
    al = eo((t - 0.15) / 0.5)
    d.rounded_rectangle([P_X * SS, P_Y * SS, (P_X + P_W) * SS, (P_Y + P_H) * SS],
                        radius=42 * SS, outline=a(INK, 0.75 * al), width=6 * SS)
    d.line([(P_X + P_W / 2 - 40) * SS, (P_Y + 40) * SS,
            (P_X + P_W / 2 + 40) * SS, (P_Y + 40) * SS],
           fill=a(INK, 0.4 * al), width=5 * SS)
    for i in range(C_COLS * C_ROWS):
        r_, c = divmod(i, C_COLS)
        x = G_X + c * (C_SZ + C_GAP)
        y = G_Y + r_ * (C_SZ + C_GAP)
        if i == TARGET:
            # 運び役がここに着地する（グローバル4.3秒＝ローカル0.3秒）。
            # 着地後はこの場面が描き継ぎ、離陸（ローカル3.55秒）で手放す。
            # 残したままだと飛んでいる運び役と二重に見える
            gone = eo((t - 3.55) / 0.2)
            if t < 0.30 or gone >= 1:
                continue
            rrect(d, TGT_X, TGT_Y, C_SZ, C_SZ, 7, ACCENT, 1.0 - gone)
            if t > 2.0:
                check_mark(d, TGT_X, TGT_Y, 13, BG, eo((t - 2.0) / 0.3) * (1 - gone), w=5)
            sparkle(d, TGT_X, TGT_Y, t, 2.05, r0=26)
            continue
        ai = eo((t - (0.5 + i * 0.028)) / 0.3)
        if ai <= 0:
            continue
        rrect(d, x + C_SZ / 2, y + C_SZ / 2, C_SZ, C_SZ, 7, MUTED, ai * 0.5)
    al2 = eo((t - 1.0) / 0.5)
    text(d, (1130, 470), "予約にかかる時間", 44, MUTED, al2)
    text(d, (1125, 700), "1", 210, INK, al2 * eo((t - 1.1) / 0.6), anchor="ls")
    text(d, (1125 + text_w("1", 210) + 16, 700), "分", 60, INK,
         al2 * eo((t - 1.3) / 0.6), anchor="ls")
    check_mark(d, 1210 + text_w("1", 210), 610, 40, ACCENT, eo((t - 1.9) / 0.4))


def scene3(d, t):
    """¥3,000 に取り消し線が走り、0円へ数え下がる"""
    title(d, t, "費用は、0円。")
    al = eo((t - 0.2) / 0.4)
    text(d, (W / 2, 400), S3_LABEL, 52, MUTED, al, anchor="mm")
    # 取り消し線。運び役が左端に着地（ローカル0.35）してから右へ走る
    strike = S3_LW * eo((t - 0.4) / 0.5)
    gone = eo((t - 3.55) / 0.2)
    if strike > 4 and gone < 1:
        rrect(d, W / 2 - S3_LW / 2 + strike / 2, 400, strike, 8, 4, ACCENT,
              0.95 * (1 - gone))
    al2 = eo((t - 0.5) / 0.5)
    v = int(round(3000 * (1 - eo((t - 0.9) / 1.4))))
    v = (v // 10) * 10
    text(d, (W / 2, 730), f"¥{v:,}", 230, INK, al2, anchor="ms")
    sparkle(d, W / 2 + text_w("¥0", 230) / 2 + 60, 640, t, 2.4, r0=30)
    a3 = eo((t - 2.5) / 0.4)
    text(d, (W / 2, 830), "組合が全額負担します", 44, MUTED, a3, anchor="mm")


def scene4(d, t):
    """締め。健診、行こう。"""
    tt = eo((t - 0.15) / 0.6)
    text(d, (W / 2, 440 + 24 * (1 - tt)), "健診、行こう。", 104, INK, tt,
         anchor="mm", tracking=10)
    # 罫は運び役（取り消し線の名残）が着地してから伸びる
    rl = 300 * eo((t - 0.3) / 0.5)
    if rl > 2:
        rrect(d, W / 2, 548, rl, 5, 2, ACCENT, eo((t - 0.3) / 0.4))
    a2 = eo((t - 0.7) / 0.5)
    text(d, (W / 2, 630), "あおば健康保険組合", 46, MUTED, a2, anchor="mm")
    a3 = eo((t - 0.95) / 0.5)
    if a3 > 0:
        pw, ph, py = 460, 84, 740
        d.rounded_rectangle([(W / 2 - pw / 2) * SS, py * SS,
                             (W / 2 + pw / 2) * SS, (py + ph) * SS],
                            radius=ph / 2 * SS, outline=a(ACCENT, a3), width=3 * SS)
        text(d, (W / 2, py + ph / 2 - 2), "受付は 10月1日 から", 40, INK, a3,
             anchor="mm")
    sparkle(d, W / 2 + 340, 420, t, 0.8, r0=24)
    sparkle(d, W / 2 - 360, 500, t, 1.0, r0=18)


SCENES = [(0.0, 4.0, scene1), (4.0, 8.0, scene2), (8.0, 12.0, scene3), (12.0, 15.0, scene4)]
XFADE = 0.4


# ---------------------------------------------------------------- 運び役

def bezier(p0, pm, p1, u):
    x = (1 - u) ** 2 * p0[0] + 2 * u * (1 - u) * pm[0] + u ** 2 * p1[0]
    y = (1 - u) ** 2 * p0[1] + 2 * u * (1 - u) * pm[1] + u ** 2 * p1[1]
    return x, y


def bridges(d, gt):
    """山吹の運び役。前の場面の主役が縮んで飛び、次の場面の主役に変形する。
    着地する矩形は次の場面の要素と同寸なので、継ぎ目は見えない"""
    global S3_LW
    for (t0, t1, r_from, r_to, lift) in (
            # 時計のリング → カレンダーのマス
            (3.55, 4.30, (W / 2, 620, 110, 110, 55), (TGT_X, TGT_Y, C_SZ, C_SZ, 7), -140),
            # チェックの付いたマス → 取り消し線の左端
            (7.55, 8.40, (TGT_X, TGT_Y, C_SZ, C_SZ, 7),
             (W / 2 - S3_LW / 2 + 16, 400, 32, 8, 4), -110),
            # 取り消し線 → 締めの罫
            (11.55, 12.30, (W / 2, 400, S3_LW, 8, 4), (W / 2, 548, 44, 5, 2), 70)):
        if not (t0 <= gt <= t1):
            continue
        u = eo((gt - t0) / (t1 - t0))
        p0, p1 = (r_from[0], r_from[1]), (r_to[0], r_to[1])
        pm = ((p0[0] + p1[0]) / 2, (p0[1] + p1[1]) / 2 + lift)
        cx, cy = bezier(p0, pm, p1, u)
        w = r_from[2] + (r_to[2] - r_from[2]) * u
        h = r_from[3] + (r_to[3] - r_from[3]) * u
        rad = r_from[4] + (r_to[4] - r_from[4]) * u
        rrect(d, cx, cy, w, h, min(rad, h / 2, w / 2), ACCENT, min(1.0, eo((gt - t0) / 0.12)))


def draw_frame(gt):
    base = Image.new("RGB", (W * SS, H * SS), BG)
    dd = ImageDraw.Draw(base, "RGBA")
    deco(dd, gt)
    for (st, en, fn) in SCENES:
        if not (st - 0.001 <= gt < en + 0.001):
            continue
        layer = Image.new("RGBA", (W * SS, H * SS), (0, 0, 0, 0))
        d = ImageDraw.Draw(layer)
        fn(d, gt - st)
        fade = 1.0
        if st > 0:
            fade = min(fade, eo((gt - st) / XFADE))
        if en < DUR:
            fade = min(fade, eo((en - gt) / XFADE))
        if fade < 1.0:
            alpha = layer.getchannel("A").point(lambda p: int(p * fade))
            layer.putalpha(alpha)
        base.paste(layer, (0, 0), layer)
    top = Image.new("RGBA", (W * SS, H * SS), (0, 0, 0, 0))
    dt = ImageDraw.Draw(top)
    bridges(dt, gt)
    chrome(dt, gt)
    base.paste(top, (0, 0), top)
    return base.resize((W, H), Image.LANCZOS)


def measure(path, tp=-2.0):
    out = subprocess.run(
        [FF, "-hide_banner", "-i", path, "-af",
         f"loudnorm=I=-16:TP={tp}:print_format=json", "-f", "null", "-"],
        capture_output=True, text=True).stderr
    keys = ("input_i", "input_tp", "input_lra", "input_thresh", "target_offset")
    vals = {}
    for line in out.splitlines():
        for k in keys:
            if f'"{k}"' in line:
                vals[k] = line.split(":")[1].strip().strip('",')
    return tuple(vals[k] for k in keys)


def main():
    global S3_LW
    S3_LW = text_w(S3_LABEL, 52) + 40
    os.makedirs(OUT, exist_ok=True)
    silent = f"{OUT}/08_infographic_15s_silent.mp4"
    n_frames = int(DUR * FPS)
    proc = subprocess.Popen(
        [FF, "-loglevel", "error", "-y",
         "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
         "-i", "-",
         "-c:v", "libx264", "-crf", "18", "-preset", "medium",
         "-pix_fmt", "yuv420p", "-movflags", "+faststart", silent],
        stdin=subprocess.PIPE)
    for i in range(n_frames):
        frame = draw_frame(i / FPS)
        proc.stdin.write(np.asarray(frame, dtype=np.uint8).tobytes())
        if i % 90 == 0:
            print(f"  frame {i}/{n_frames}", flush=True)
    proc.stdin.close()
    assert proc.wait() == 0

    audio = f"{HERE}/bgm_08.wav"
    mi, mtp, mlra, mth, off = measure(audio)
    af = (f"loudnorm=I=-16:TP=-2.0:LRA=11:measured_I={mi}:measured_TP={mtp}:"
          f"measured_LRA={mlra}:measured_thresh={mth}:offset={off}:linear=true,"
          f"alimiter=limit=0.82:attack=1:release=40")
    master = f"{OUT}/08_infographic_15s_master.mp4"
    subprocess.run([FF, "-loglevel", "error", "-y", "-i", silent, "-i", audio,
                    "-map", "0:v:0", "-map", "1:a:0", "-c:v", "copy", "-af", af,
                    "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-shortest",
                    "-movflags", "+faststart", master], check=True)
    web = f"{OUT}/08_infographic_15s_web.mp4"
    subprocess.run([FF, "-loglevel", "error", "-y", "-i", master,
                    "-c:v", "libx264", "-crf", "26", "-maxrate", "2000k",
                    "-bufsize", "4000k", "-preset", "slow", "-pix_fmt", "yuv420p",
                    "-c:a", "aac", "-b:a", "128k", "-ar", "48000",
                    "-movflags", "+faststart", web], check=True)
    print(f"08: {os.path.getsize(master)//1024}KB / web {os.path.getsize(web)//1024}KB")


if __name__ == "__main__":
    main()
