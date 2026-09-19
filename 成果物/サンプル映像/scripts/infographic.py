# -*- coding: utf-8 -*-
"""08 モーショングラフィックス「あおば健康保険組合 健診受診案内」を全部コードで描く。

初稿は「数字で見る、想工業。」（採用インフォグラフィック）で作ったが、
健診案内のほうがいいとの指摘で題材を戻した（9/19）。想工業版は
git 履歴（44c7d75）にあるので、要るときはそこから復活できる。

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


def check_mark(d, cx, cy, r, col, alpha, w=None):
    """チェックマーク。左下がりの短い線＋右上がりの長い線"""
    w = w or max(4, int(r * 0.28))
    pts = [(cx - r * 0.55, cy + r * 0.05), (cx - r * 0.12, cy + r * 0.48),
           (cx + r * 0.62, cy - r * 0.42)]
    d.line([(x * SS, y * SS) for x, y in pts], fill=a(col, alpha),
           width=w * SS, joint="curve")


def scene1(d, t):
    """時計の円弧が一周して「30分」が数え上がる"""
    tt = eo((t - 0.1) / 0.6)
    text(d, (W / 2, 150 + 26 * (1 - tt)), "年に1回の、30分。", 72, INK, tt,
         anchor="mm", tracking=6)

    cx, cy, r, wd = W / 2, 620, 250, 44
    al = eo((t - 0.35) / 0.4)
    box = [(cx - r) * SS, (cy - r) * SS, (cx + r) * SS, (cy + r) * SS]
    # 文字盤の目盛り12本
    for k in range(12):
        ang = np.pi * 2 * k / 12 - np.pi / 2
        r0, r1 = r + wd / 2 + 18, r + wd / 2 + 38
        d.line([(cx + np.cos(ang) * r0) * SS, (cy + np.sin(ang) * r0) * SS,
                (cx + np.cos(ang) * r1) * SS, (cy + np.sin(ang) * r1) * SS],
               fill=a(INK, 0.25 * al), width=4 * SS)
    d.arc(box, 0, 360, fill=a(MUTED, 0.4 * al), width=wd * SS)
    frac = eo((t - 0.55) / 1.7)
    if frac > 0:
        d.arc(box, -90, -90 + 360 * frac, fill=a(ACCENT, al), width=wd * SS)
    v = int(round(30 * eo((t - 0.55) / 1.7)))
    text(d, (cx, cy - 14), str(v), 150, INK, al, anchor="mm")
    text(d, (cx, cy + 96), "分で終わります", 40, MUTED, al, anchor="mm")


def scene2(d, t):
    """スマホの中でカレンダーが組み上がり、1日にチェックが付く"""
    tt = eo((t - 0.1) / 0.5)
    text(d, (W / 2, 150 + 26 * (1 - tt)), "予約は、スマホで1分。", 72, INK, tt,
         anchor="mm", tracking=6)

    # 左：スマホの輪郭
    al = eo((t - 0.3) / 0.5)
    px, py, pw, ph = 470, 320, 330, 580
    d.rounded_rectangle([px * SS, py * SS, (px + pw) * SS, (py + ph) * SS],
                        radius=42 * SS, outline=a(INK, 0.75 * al), width=6 * SS)
    d.line([(px + pw / 2 - 40) * SS, (py + 40) * SS,
            (px + pw / 2 + 40) * SS, (py + 40) * SS],
           fill=a(INK, 0.4 * al), width=5 * SS)
    # カレンダー。7列×4段のマスが順に出て、19日目にチェック
    cols, rows = 7, 4
    cw, ch_, gap = 34, 34, 6
    gx = px + (pw - cols * cw - (cols - 1) * gap) / 2
    gy = py + 110
    target = 18                       # 0はじまりで19日目
    for i in range(cols * rows):
        ai = eo((t - (0.7 + i * 0.028)) / 0.3)
        if ai <= 0:
            continue
        r_, c = divmod(i, cols)
        x = gx + c * (cw + gap)
        y = gy + r_ * (ch_ + gap)
        col = ACCENT if (i == target and t > 2.0) else MUTED
        alpha = ai * (1.0 if (i == target and t > 2.0) else 0.5)
        d.rounded_rectangle([x * SS, y * SS, (x + cw) * SS, (y + ch_) * SS],
                            radius=7 * SS, fill=a(col, alpha))
        if i == target and t > 2.15:
            check_mark(d, x + cw / 2, y + ch_ / 2, 13, BG,
                       eo((t - 2.15) / 0.3), w=5)

    # 右：所要時間のカウンター
    al2 = eo((t - 1.0) / 0.5)
    text(d, (1130, 470), "予約にかかる時間", 44, MUTED, al2)
    v = max(1, int(round(1 * eo((t - 1.1) / 0.8) * 1)))
    text(d, (1125, 700), "1", 210, INK, al2 * eo((t - 1.1) / 0.6), anchor="ls")
    text(d, (1125 + text_w("1", 210) + 16, 700), "分", 60, INK,
         al2 * eo((t - 1.3) / 0.6), anchor="ls")
    check_mark(d, 1210 + text_w("1", 210), 610, 40, ACCENT, eo((t - 1.9) / 0.4))


def scene3(d, t):
    """¥3,000 に取り消し線が走り、0円へ数え下がる"""
    tt = eo((t - 0.1) / 0.5)
    text(d, (W / 2, 150 + 26 * (1 - tt)), "費用は、0円。", 72, INK, tt,
         anchor="mm", tracking=6)

    # 上：もとの金額。山吹の取り消し線が走る
    al = eo((t - 0.4) / 0.5)
    label = "通常 ¥3,000 のところ"
    text(d, (W / 2, 400), label, 52, MUTED, al, anchor="mm")
    lw = text_w(label, 52) + 40
    strike = lw * eo((t - 0.9) / 0.5)
    if strike > 4:
        y = 400
        d.rounded_rectangle([(W / 2 - lw / 2) * SS, (y - 4) * SS,
                             (W / 2 - lw / 2 + strike) * SS, (y + 4) * SS],
                            radius=4 * SS, fill=a(ACCENT, 0.95))

    # 中央：カウントダウン。3,000 → 0
    al2 = eo((t - 0.7) / 0.5)
    v = int(round(3000 * (1 - eo((t - 1.1) / 1.4))))
    v = (v // 10) * 10                 # 端数が暴れないよう10円刻みで落とす
    txt = f"¥{v:,}"
    text(d, (W / 2, 730), txt, 230, INK, al2, anchor="ms")
    a3 = eo((t - 2.7) / 0.4)
    text(d, (W / 2, 830), "組合が全額負担します", 44, MUTED, a3, anchor="mm")


def scene4(d, t):
    """締め。健診、行こう。"""
    tt = eo((t - 0.15) / 0.6)
    text(d, (W / 2, 440 + 24 * (1 - tt)), "健診、行こう。", 104, INK, tt,
         anchor="mm", tracking=10)
    rl = 300 * eo((t - 0.5) / 0.5)
    if rl > 2:
        d.rounded_rectangle([(W / 2 - rl / 2) * SS, 546 * SS,
                             (W / 2 + rl / 2) * SS, (546 + 5) * SS],
                            radius=2 * SS, fill=a(ACCENT, eo((t - 0.5) / 0.4)))
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


SCENES = [(0.0, 4.0, scene1), (4.0, 8.0, scene2), (8.0, 12.0, scene3), (12.0, 15.0, scene4)]
XFADE = 0.4     # 場面の頭でフェードイン（前の場面は尻でフェードアウト）


def draw_frame(gt):
    base = Image.new("RGB", (W * SS, H * SS), BG)
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
    text(dn, (W - 48, H - 40), "※架空の健康保険組合のサンプル映像です。数字も架空です。",
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
