# -*- coding: utf-8 -*-
"""08 インフォグラフィック「数字で見る、想工業。」を全部コードで描く。

Higgsfield を使わない初めてのサンプル。モーショングラフィックス／
インフォグラフィックは文字と図形が主役で、生成AIは画面内の文字を
正しく描けない（03の名札で実証済み）ため、この題材ではコードで描くのが正しい。
クレジット消費は 0。

構成は 構成案_インフォグラフィック15秒.md のとおり。
場面は 0-4 / 4-8 / 8-12 / 12-15 秒で、BGM（bgm_08）の小節頭に切り替えが乗る。

フレームを PIL で1枚ずつ描き、rawvideo で ffmpeg に流す。
円やグラフの縁を滑らかにするため2倍で描いて縮小する。

使い方: python3 infographic.py
"""
from PIL import Image, ImageDraw, ImageFont
import numpy as np
import os
import subprocess

W, H = 1920, 1080
SS = 2                      # スーパーサンプル倍率
FPS = 30
DUR = 15.0
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.environ.get("SO_OUT", f"{HERE}/out")
FONTS = os.environ.get("SO_FONTS", "/tmp/fonts")
ZEN = f"{FONTS}/ZenKakuNew-Black.ttf"
FF = ("/usr/local/lib/python3.11/dist-packages/imageio_ffmpeg/binaries/"
      "ffmpeg-linux-x86_64-v7.0.2")

# 色。スレートは #46597B だと紺地とのコントラストが 2.27:1 で足りず、
# #5D7398 に上げて 3:1 を通した（dataviz の検証スクリプトで確認）
NAVY = (15, 33, 64)
INK = (238, 231, 214)
ACCENT = (245, 181, 42)
SLATE = (93, 115, 152)


def F(size):
    return ImageFont.truetype(ZEN, size * SS)


def clamp01(x):
    return max(0.0, min(1.0, x))


def eo(x):
    """ease-out cubic。数える・伸びる・並ぶの全部に使う"""
    x = clamp01(x)
    return 1 - (1 - x) ** 3


def a(col, alpha):
    return col + (int(255 * alpha),)


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


def person(d, cx, cy, h, col, alpha):
    """人型アイコン。丸い頭＋角丸の胴体"""
    s = SS
    head_r = h * 0.19
    d.ellipse([(cx - head_r) * s, (cy - h * 0.5) * s,
               (cx + head_r) * s, (cy - h * 0.5 + head_r * 2) * s], fill=a(col, alpha))
    bw = h * 0.46
    d.rounded_rectangle([(cx - bw / 2) * s, (cy - h * 0.5 + head_r * 2.25) * s,
                         (cx + bw / 2) * s, (cy + h * 0.5) * s],
                        radius=bw / 2 * s, fill=a(col, alpha))


def scene1(d, t):
    """創業47年のカウンター＋社員62人の人型が並ぶ"""
    tt = eo((t - 0.1) / 0.6)
    text(d, (W / 2, 150 + 26 * (1 - tt)), "数字で見る、想工業。", 76, INK, tt,
         anchor="mm", tracking=6)

    # 左：創業カウンター。中央寄せだと桁が増えるたび揺れるので左端を固定する
    al = eo((t - 0.45) / 0.5)
    v = int(round(47 * eo((t - 0.55) / 1.3)))
    text(d, (330, 430), "創業", 44, SLATE, al)
    text(d, (325, 750), str(v), 250, INK, al, anchor="ls")
    text(d, (325 + text_w("47", 250) + 18, 750), "年", 64, INK, al * 0.9, anchor="ls")

    # 右：人型アイコン 62人（13列×5段の頭から62個）
    cols, size_, gx, gy = 13, 46, 57, 76
    x0, y0 = 1010, 400
    shown = 0
    for i in range(62):
        ai = eo((t - (0.8 + i * 0.026)) / 0.3)
        if ai <= 0:
            continue
        shown += 1
        r, c = divmod(i, cols)
        person(d, x0 + c * gx, y0 + r * gy, size_ * (0.6 + 0.4 * ai), SLATE, ai * 0.95)
    al2 = eo((t - 0.9) / 0.5)
    text(d, (1010 - 28, 820), f"社員 {shown}人", 52, INK, al2, anchor="ls")


def scene2(d, t):
    """有給82%のドーナツ＋平均残業12hのカウンター"""
    tt = eo((t - 0.1) / 0.5)
    text(d, (W / 2, 150 + 26 * (1 - tt)), "休める町工場です。", 72, INK, tt,
         anchor="mm", tracking=6)

    # 左：ドーナツ。台座の全周スレート＋実測ぶんだけ山吹が伸びる
    cx, cy, r, wd = 620, 620, 240, 60
    al = eo((t - 0.3) / 0.4)
    box = [(cx - r) * SS, (cy - r) * SS, (cx + r) * SS, (cy + r) * SS]
    d.arc(box, 0, 360, fill=a(SLATE, 0.45 * al), width=wd * SS)
    frac = 0.82 * eo((t - 0.5) / 1.5)
    if frac > 0:
        d.arc(box, -90, -90 + 360 * frac, fill=a(ACCENT, al), width=wd * SS)
    v = int(round(82 * eo((t - 0.5) / 1.5)))
    text(d, (cx, cy - 8), f"{v}%", 110, INK, al, anchor="mm")
    text(d, (cx, cy + 330), "有給取得率", 44, SLATE, al, anchor="mm")

    # 右：残業カウンター
    al2 = eo((t - 1.0) / 0.5)
    v2 = int(round(12 * eo((t - 1.1) / 1.2)))
    text(d, (1180, 500), "平均残業", 44, SLATE, al2)
    text(d, (1175, 720), str(v2), 190, INK, al2, anchor="ls")
    text(d, (1175 + text_w("12", 190) + 16, 720), "時間/月", 56, INK, al2 * 0.9, anchor="ls")


BARS = [("20代", 24, ACCENT), ("30代", 21, SLATE), ("40代〜", 17, SLATE)]


def scene3(d, t):
    """年代別の棒グラフ。20代がいちばん高く、山吹で点灯"""
    tt = eo((t - 0.1) / 0.5)
    text(d, (W / 2, 150 + 26 * (1 - tt)), "20代が、いちばん多い。", 72, INK, tt,
         anchor="mm", tracking=6)

    base_y, max_h, bw, gap = 850, 430, 190, 130
    x0 = (W - (bw * 3 + gap * 2)) / 2
    al = eo((t - 0.3) / 0.4)
    d.line([(x0 - 60) * SS, base_y * SS, (x0 + bw * 3 + gap * 2 + 60) * SS, base_y * SS],
           fill=a(INK, 0.28 * al), width=2 * SS)
    for i, (label, v, col) in enumerate(BARS):
        x = x0 + i * (bw + gap)
        hgt = (v / 24) * max_h * eo((t - (0.4 + i * 0.22)) / 0.9)
        ab = eo((t - (0.4 + i * 0.22)) / 0.4)
        if hgt > 8:
            # 上だけ角丸、根元はベースラインに直づけ（浮かせない）
            d.rounded_rectangle([x * SS, (base_y - hgt) * SS,
                                 (x + bw) * SS, (base_y + 8) * SS],
                                radius=8 * SS, fill=a(col, ab))
        text(d, (x + bw / 2, base_y - hgt - 44), f"{v}人", 44, INK,
             eo((t - (0.9 + i * 0.22)) / 0.4), anchor="mm")
        text(d, (x + bw / 2, base_y + 48), label, 42, SLATE, ab, anchor="mm")


def scene4(d, t):
    """締め。ロゴカードに収束"""
    tt = eo((t - 0.15) / 0.6)
    text(d, (W / 2, 460 + 24 * (1 - tt)), "想工業株式会社", 104, INK, tt,
         anchor="mm", tracking=10)
    # 細い山吹の罫
    rl = 300 * eo((t - 0.5) / 0.5)
    if rl > 2:
        d.rounded_rectangle([(W / 2 - rl / 2) * SS, 566 * SS,
                             (W / 2 + rl / 2) * SS, (566 + 5) * SS],
                            radius=2 * SS, fill=a(ACCENT, eo((t - 0.5) / 0.4)))
    a2 = eo((t - 0.7) / 0.5)
    text(d, (W / 2, 650), "機械加工 ／ 検査 ／ 出荷", 44, SLATE, a2, anchor="mm")
    # 採用強化中のピル（山吹の縁取り＋生成りの文字）
    a3 = eo((t - 0.95) / 0.5)
    if a3 > 0:
        pw, ph, py = 340, 84, 760
        d.rounded_rectangle([(W / 2 - pw / 2) * SS, py * SS,
                             (W / 2 + pw / 2) * SS, (py + ph) * SS],
                            radius=ph / 2 * SS, outline=a(ACCENT, a3), width=3 * SS)
        text(d, (W / 2, py + ph / 2 - 2), "採用強化中", 42, INK, a3, anchor="mm")


SCENES = [(0.0, 4.0, scene1), (4.0, 8.0, scene2), (8.0, 12.0, scene3), (12.0, 15.0, scene4)]
XFADE = 0.4     # 場面の頭でフェードイン（前の場面は尻でフェードアウト）


def draw_frame(gt):
    base = Image.new("RGB", (W * SS, H * SS), NAVY)
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
    # 注記は場面に関係なく常に出す（数字が架空であることを画面内で断る）
    note = Image.new("RGBA", (W * SS, H * SS), (0, 0, 0, 0))
    dn = ImageDraw.Draw(note)
    text(dn, (W - 48, H - 40), "※架空の会社のサンプル映像です。数字も架空です。",
         26, INK, 0.42, anchor="rs")
    base.paste(note, (0, 0), note)
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
