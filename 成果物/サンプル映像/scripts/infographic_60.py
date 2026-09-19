# -*- coding: utf-8 -*-
"""健診案内の60秒版。15秒版（infographic.py）の部品を使い回す。

ただ引き伸ばすと間延びするので、場面を4→8に増やした。
  0- 6  封筒（お知らせが届く）        ★新規
  6-14  目覚まし時計（30分）          15秒版を0.47倍速で再生
 14-22  検査項目（4つのタイル）       ★新規
 22-30  カレンダー（予約1分）         15秒版を0.47倍速
 30-38  ¥3,000→¥0（費用）            15秒版を0.47倍速
 38-46  期間バー（10/1→11/28）        ★新規
 46-54  結果（2週間でスマホに）       ★新規
 54-60  締め（健診、行こう。）        15秒版の間を60秒用に調整

運び役の連鎖も8場面ぶんに繋ぎ直した。
封筒の封 → 時計の頭のボタン → 検査タイル → カレンダーのマス →
取り消し線 → 期間バー → 結果のチェックバッジ → 締めの十字バッジ。

使い方: python3 infographic_60.py
"""
import numpy as np
import os
import subprocess
from PIL import Image, ImageDraw

import infographic as ig
from infographic import (W, H, SS, FPS, BG, INK, ACCENT, MUTED, DK, LT, SHX, SHY,
                         eo, a, text, text_sh, text_w, rrect, check_mark, sparkle,
                         title, halftone, bezier, TGT_X, TGT_Y, C_SZ)

DUR = 60.0
OUT = ig.OUT
FF = ig.FF

# 15秒版の場面を8秒の枠で使うときの倍速。旅立ち（ローカル3.5秒）が
# 枠の終わり0.5秒前（ローカル7.5秒）に来るように 3.5/7.5
K = 3.5 / 7.5

# 新しい場面の座標
TILE_Y = 640
TILE_XS = [960 - 345, 960 - 115, 960 + 115, 960 + 345]
TILE_W = 170
BAR_Y, BAR_W = 640, 760
DOC_X, DOC_Y = 620, 640
BADGE = (DOC_X + 150, DOC_Y - 200)   # 結果カードの角のチェックバッジ


def s_intro(d, t):
    """封筒からお知らせが持ち上がる"""
    title(d, t, "その封筒、あけましたか。")
    al = eo((t - 0.3) / 0.5)
    ex, ey, ew, eh = 960, 660, 470, 300
    # 中の紙。山吹の十字と2行の文字を持って、封筒の中から持ち上がる
    rise = 180 * eo((t - 1.0) / 1.0)
    py = ey + 20 - rise
    rrect(d, ex, py, ew - 90, 260, 14, INK, al * 0.95, shadow=True)
    pl = eo((t - 1.6) / 0.5)
    rrect(d, ex, py - 60, 44, 14, 6, ACCENT, pl)
    rrect(d, ex, py - 60, 14, 44, 6, ACCENT, pl)
    for k, wl in enumerate((150, 100)):
        rrect(d, ex, py + 10 + k * 34, wl, 10, 5, MUTED, al * 0.8)
    # 封筒の口（下半分）。紙より手前に置いて「入っている」ように見せる
    d.rounded_rectangle([(ex - ew / 2 + SHX) * SS, (ey - 30 + SHY) * SS,
                         (ex + ew / 2 + SHX) * SS, (ey + eh / 2 + SHY) * SS],
                        radius=20 * SS, fill=a(DK, al * 0.9))
    d.rounded_rectangle([(ex - ew / 2) * SS, (ey - 30) * SS,
                         (ex + ew / 2) * SS, (ey + eh / 2) * SS],
                        radius=20 * SS, fill=a(LT, al), outline=a(INK, 0.75 * al),
                        width=5 * SS)
    d.line([(ex - ew / 2) * SS, (ey - 26) * SS, ex * SS, (ey + 60) * SS],
           fill=a(INK, 0.45 * al), width=5 * SS)
    d.line([(ex + ew / 2) * SS, (ey - 26) * SS, ex * SS, (ey + 60) * SS],
           fill=a(INK, 0.45 * al), width=5 * SS)
    # 封。山吹の丸。旅立ち（5.55秒）で運び役に渡す
    gone = eo((t - 5.55) / 0.2)
    if gone < 1:
        r = 24
        d.ellipse([(ex - r) * SS, (ey + 60 - r) * SS, (ex + r) * SS, (ey + 60 + r) * SS],
                  fill=a(ACCENT, al * (1 - gone)))
    text(d, (960, 880), "あおば健保からのお知らせ", 36, MUTED, eo((t - 1.8) / 0.5),
         anchor="mm")


def s_items(d, t):
    """検査項目。4つのタイル"""
    title(d, t, "身長から血液まで、ひととおり。")
    labels = ("計測", "血圧", "血液", "視力")
    for i, cx in enumerate(TILE_XS):
        ai = eo((t - (0.45 + i * 0.18)) / 0.4)
        if ai <= 0:
            continue
        first = (i == 0)
        # タイル1は運び役が変形して着地したもの（14.45秒＝ローカル0.45）
        col = ACCENT if first else MUTED
        rrect(d, cx, TILE_Y, TILE_W * (0.7 + 0.3 * ai), TILE_W * (0.7 + 0.3 * ai),
              28, col, ai * (1.0 if first else 0.22), shadow=first)
        ic = BG if first else INK
        ia = ai * (1.0 if first else 0.85)
        if i == 0:      # 巻尺
            r = 40
            d.arc([(cx - r) * SS, (TILE_Y - r) * SS, (cx + r) * SS, (TILE_Y + r) * SS],
                  -40, 250, fill=a(ic, ia), width=9 * SS)
            d.line([(cx + r * 0.75) * SS, (TILE_Y + r * 0.6) * SS,
                    (cx + r * 1.35) * SS, (TILE_Y + r * 0.6) * SS],
                   fill=a(ic, ia), width=9 * SS)
        elif i == 1:    # 心拍の線
            pts = [(-58, 0), (-22, 0), (-10, -30), (6, 32), (18, 0), (58, 0)]
            d.line([((cx + x) * SS, (TILE_Y + y) * SS) for x, y in pts],
                   fill=a(ic, ia), width=9 * SS, joint="curve")
        elif i == 2:    # 試験管。中身がたまる
            d.rounded_rectangle([(cx - 22) * SS, (TILE_Y - 52) * SS,
                                 (cx + 22) * SS, (TILE_Y + 52) * SS],
                                radius=20 * SS, outline=a(ic, ia), width=8 * SS)
            fill_h = 60 * eo((t - 1.2) / 0.8)
            if fill_h > 6:
                d.rounded_rectangle([(cx - 13) * SS, (TILE_Y + 44 - fill_h) * SS,
                                     (cx + 13) * SS, (TILE_Y + 44) * SS],
                                    radius=10 * SS, fill=a(ic, ia))
        else:           # 目
            d.arc([(cx - 52) * SS, (TILE_Y - 52) * SS, (cx + 52) * SS, (TILE_Y + 52) * SS],
                  200, 340, fill=a(ic, ia), width=8 * SS)
            d.arc([(cx - 52) * SS, (TILE_Y - 52) * SS, (cx + 52) * SS, (TILE_Y + 52) * SS],
                  20, 160, fill=a(ic, ia), width=8 * SS)
            d.ellipse([(cx - 14) * SS, (TILE_Y - 14) * SS,
                       (cx + 14) * SS, (TILE_Y + 14) * SS], fill=a(ic, ia))
        text(d, (cx, TILE_Y + 130), labels[i], 36, MUTED, ai, anchor="mm")
    text(d, (960, 850), "基本の検査は約10項目。すべて当日に受けられます", 36, MUTED,
         eo((t - 1.6) / 0.5), anchor="mm")


def s_period(d, t):
    """期間バー。10/1 から 11/28 まで"""
    title(d, t, "期間は、2ヶ月たっぷり。")
    al = eo((t - 0.3) / 0.5)
    # 台座（運び役の取り消し線がこの姿に変形して着地している）
    rrect(d, 960, BAR_Y, BAR_W, 10, 5, MUTED, 0.35 * al, shadow=True)
    for sgn, lab in ((-1, "10/1"), (1, "11/28")):
        x = 960 + sgn * BAR_W / 2
        d.line([x * SS, (BAR_Y - 22) * SS, x * SS, (BAR_Y + 22) * SS],
               fill=a(INK, 0.5 * al), width=5 * SS)
        text_sh(d, (x, BAR_Y + 80), lab, 56, INK, al, anchor="mm")
    prog = eo((t - 0.6) / 1.8)
    fw = BAR_W * prog
    if fw > 8:
        rrect(d, 960 - BAR_W / 2 + fw / 2, BAR_Y, fw, 10, 5, ACCENT, al)
    # ピン。塗りの先頭に乗って走り、旅立ち（7.5秒）で運び役に渡す
    gone = eo((t - 7.5) / 0.2)
    if gone < 1:
        px = 960 - BAR_W / 2 + fw
        r = 20 + 4 * np.sin(2 * np.pi * t * 0.8)
        d.ellipse([(px - r + 4) * SS, (BAR_Y - r + 5) * SS,
                   (px + r + 4) * SS, (BAR_Y + r + 5) * SS], fill=a(DK, al * (1 - gone)))
        d.ellipse([(px - r) * SS, (BAR_Y - r) * SS, (px + r) * SS, (BAR_Y + r) * SS],
                  fill=a(ACCENT, al * (1 - gone)))
        d.ellipse([(px - 7) * SS, (BAR_Y - 7) * SS, (px + 7) * SS, (BAR_Y + 7) * SS],
                  fill=a(BG, al * (1 - gone)))
    text(d, (960, 850), "土日の受診もできます", 36, MUTED, eo((t - 1.4) / 0.5),
         anchor="mm")
    sparkle(d, 960 + BAR_W / 2, BAR_Y, t, 2.5)


def s_result(d, t):
    """結果はスマホに。レポートのカード"""
    title(d, t, "結果は、2週間でスマホに。")
    al = eo((t - 0.2) / 0.5)
    cw, chh = 330, 430
    d.rounded_rectangle([(DOC_X - cw / 2 + SHX) * SS, (DOC_Y - chh / 2 + SHY) * SS,
                         (DOC_X + cw / 2 + SHX) * SS, (DOC_Y + chh / 2 + SHY) * SS],
                        radius=18 * SS, fill=a(DK, 0.9 * al))
    d.rounded_rectangle([(DOC_X - cw / 2) * SS, (DOC_Y - chh / 2) * SS,
                         (DOC_X + cw / 2) * SS, (DOC_Y + chh / 2) * SS],
                        radius=18 * SS, fill=a(LT, al), outline=a(INK, 0.75 * al),
                        width=5 * SS)
    for k, wl in enumerate((190, 230, 150)):
        rrect(d, DOC_X - 10, DOC_Y - 120 + k * 44, wl * eo((t - (0.6 + k * 0.2)) / 0.5),
              12, 6, MUTED, al * 0.8)
    # カードの中の小さな棒グラフ
    for k, hh in enumerate((60, 96, 74)):
        bh = hh * eo((t - (1.2 + k * 0.15)) / 0.6)
        if bh > 4:
            rrect(d, DOC_X - 70 + k * 70, DOC_Y + 130 - bh / 2, 40, bh, 6,
                  ACCENT if k == 1 else MUTED, al * (1.0 if k == 1 else 0.6))
    # チェックバッジ。運び役が変形して着地したもの（46.5秒＝ローカル0.5）
    ba = eo((t - 0.5) / 0.3)
    if ba > 0:
        r = 34
        d.ellipse([(BADGE[0] - r + 4) * SS, (BADGE[1] - r + 5) * SS,
                   (BADGE[0] + r + 4) * SS, (BADGE[1] + r + 5) * SS], fill=a(DK, ba * 0.9))
        d.ellipse([(BADGE[0] - r) * SS, (BADGE[1] - r) * SS,
                   (BADGE[0] + r) * SS, (BADGE[1] + r) * SS], fill=a(ACCENT, ba))
        check_mark(d, BADGE[0], BADGE[1], 16, BG, eo((t - 0.7) / 0.3), w=6)
    sparkle(d, BADGE[0], BADGE[1], t, 0.85, r0=30)
    al2 = eo((t - 1.2) / 0.5)
    text(d, (1130, 560), "受診からおよそ", 44, MUTED, al2)
    text_sh(d, (1125, 780), "2週間", 150, INK, al2 * eo((t - 1.4) / 0.6), anchor="ls")
    text(d, (1130, 850), "紙の郵送も選べます", 36, MUTED, eo((t - 2.0) / 0.5))


def s_close(d, t):
    """締め。15秒版の scene4 と同じ組みで、運び役の到着（ローカル0.4）に合わせて遅らせる"""
    tt = eo((t - 0.2) / 0.6)
    bb = eo((t - 0.45) / 0.45)
    if bb > 0:
        br = 44 * (0.6 + 0.4 * bb)
        d.ellipse([(960 - br + SHX) * SS, (300 - br + SHY) * SS,
                   (960 + br + SHX) * SS, (300 + br + SHY) * SS],
                  outline=a(DK, bb * 0.9), width=6 * SS)
        d.ellipse([(960 - br) * SS, (300 - br) * SS, (960 + br) * SS, (300 + br) * SS],
                  outline=a(ACCENT, bb), width=6 * SS)
        rrect(d, 960, 300, br * 0.9, br * 0.3, br * 0.14, ACCENT, bb)
        rrect(d, 960, 300, br * 0.3, br * 0.9, br * 0.14, ACCENT, bb)
    text_sh(d, (960, 440 + 24 * (1 - tt)), "健診、行こう。", 104, INK, tt,
            anchor="mm", tracking=10)
    rl = 300 * eo((t - 0.6) / 0.5)
    if rl > 2:
        rrect(d, 960, 548, rl, 5, 2, ACCENT, eo((t - 0.6) / 0.4))
    a2 = eo((t - 0.9) / 0.5)
    text(d, (960, 630), "あおば健康保険組合", 46, MUTED, a2, anchor="mm")
    a3 = eo((t - 1.15) / 0.5)
    if a3 > 0:
        pw, ph, py = 460, 84, 740
        d.rounded_rectangle([(960 - pw / 2) * SS, py * SS,
                             (960 + pw / 2) * SS, (py + ph) * SS],
                            radius=ph / 2 * SS, outline=a(ACCENT, a3), width=3 * SS)
        text(d, (960, py + ph / 2 - 2), "受付は 10月1日 から", 40, INK, a3, anchor="mm")
    sparkle(d, 960 + 340, 420, t, 1.0, r0=24)
    sparkle(d, 960 - 360, 500, t, 1.2, r0=18)


def clock60(d, t):
    ig.scene1(d, t * K)


def cal60(d, t):
    ig.scene2(d, t * K)


def cost60(d, t):
    ig.scene3(d, t * K)


SCENES = [(0.0, 6.0, s_intro), (6.0, 14.0, clock60), (14.0, 22.0, s_items),
          (22.0, 30.0, cal60), (30.0, 38.0, cost60), (38.0, 46.0, s_period),
          (46.0, 54.0, s_result), (54.0, 60.0, s_close)]
BOUNDS = [st for st, _, _ in SCENES]
XFADE = 0.4


def bridges(d, gt):
    """運び役。15秒版と同じ作りで、8場面ぶんの連鎖にした"""
    lw = ig.S3_LW
    hops = (
        # 封筒の封 → 時計の頭のボタン
        (5.55, 6.55, (960, 720, 48, 48, 24), (960, 296, 26, 16, 6), -160),
        # 時計のリング → 検査タイル1
        (13.55, 14.45, (960, 620, 110, 110, 55), (TILE_XS[0], TILE_Y, TILE_W, TILE_W, 28), -140),
        # 検査タイル1 → カレンダーのマス
        (21.50, 22.63, (TILE_XS[0], TILE_Y, TILE_W, TILE_W, 28), (TGT_X, TGT_Y, C_SZ, C_SZ, 7), -150),
        # チェックの付いたマス → 取り消し線の左端
        (29.50, 30.85, (TGT_X, TGT_Y, C_SZ, C_SZ, 7), (960 - lw / 2 + 16, 400, 32, 8, 4), -110),
        # 取り消し線 → 期間バー
        (37.50, 38.50, (960, 400, lw, 8, 4), (960, BAR_Y, BAR_W, 10, 5), 60),
        # 期間バーのピン → 結果のチェックバッジ
        (45.50, 46.50, (960 + BAR_W / 2, BAR_Y, 40, 40, 20), (BADGE[0], BADGE[1], 68, 68, 34), -130),
        # チェックバッジ → 締めの十字バッジ
        (53.50, 54.45, (BADGE[0], BADGE[1], 68, 68, 34), (960, 300, 88, 88, 44), -90),
    )
    for (t0, t1, r_from, r_to, lift) in hops:
        if not (t0 <= gt <= t1):
            continue
        u = eo((gt - t0) / (t1 - t0))
        p0, p1 = (r_from[0], r_from[1]), (r_to[0], r_to[1])
        pm = ((p0[0] + p1[0]) / 2, (p0[1] + p1[1]) / 2 + lift)
        cx, cy = bezier(p0, pm, p1, u)
        w = r_from[2] + (r_to[2] - r_from[2]) * u
        h = r_from[3] + (r_to[3] - r_from[3]) * u
        rad = r_from[4] + (r_to[4] - r_from[4]) * u
        rrect(d, cx, cy, w, h, min(rad, h / 2, w / 2), ACCENT,
              min(1.0, eo((gt - t0) / 0.12)), shadow=True)


def chrome(d, gt):
    al = 0.55 * (1 - eo((gt - 54.0) / 0.4))
    if al > 0.01:
        text(d, (52, 46), "あおば健康保険組合", 28, MUTED, al)
    cur = max(i for i, b in enumerate(BOUNDS) if gt >= b)
    for i in range(8):
        x = W - 52 - (7 - i) * 30
        on = (i == cur)
        d.ellipse([(x - 7) * SS, (54 - 7) * SS, (x + 7) * SS, (54 + 7) * SS],
                  fill=a(ACCENT if on else INK, 0.9 if on else 0.22))
    text(d, (W - 48, H - 40), "※架空の健康保険組合のサンプル映像です。数字も架空です。",
         26, INK, 0.42, anchor="rs")


def draw_frame(gt):
    base = ig.PAPER.copy()
    dd = ImageDraw.Draw(base, "RGBA")
    ig.deco(dd, gt)
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
    out = base.resize((W, H), Image.LANCZOS)
    arr = np.asarray(out, dtype=np.int16)
    g = np.random.default_rng(int(round(gt * FPS))).integers(-5, 6, (H, W, 1), dtype=np.int16)
    return Image.fromarray(np.clip(arr + g, 0, 255).astype(np.uint8))


def main():
    ig.S3_LW = text_w(ig.S3_LABEL, 52) + 40
    ig.PAPER = ig.make_paper()
    os.makedirs(OUT, exist_ok=True)
    silent = f"{OUT}/08_infographic_60s_silent.mp4"
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
        if i % 300 == 0:
            print(f"  frame {i}/{n_frames}", flush=True)
    proc.stdin.close()
    assert proc.wait() == 0

    audio = f"{ig.HERE}/bgm_08_60.wav"
    mi, mtp, mlra, mth, off = ig.measure(audio)
    af = (f"loudnorm=I=-16:TP=-2.0:LRA=11:measured_I={mi}:measured_TP={mtp}:"
          f"measured_LRA={mlra}:measured_thresh={mth}:offset={off}:linear=true,"
          f"alimiter=limit=0.82:attack=1:release=40")
    master = f"{OUT}/08_infographic_60s_master.mp4"
    subprocess.run([FF, "-loglevel", "error", "-y", "-i", silent, "-i", audio,
                    "-map", "0:v:0", "-map", "1:a:0", "-c:v", "copy", "-af", af,
                    "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-shortest",
                    "-movflags", "+faststart", master], check=True)
    web = f"{OUT}/08_infographic_60s_web.mp4"
    subprocess.run([FF, "-loglevel", "error", "-y", "-i", master,
                    "-c:v", "libx264", "-crf", "26", "-maxrate", "2000k",
                    "-bufsize", "4000k", "-preset", "slow", "-pix_fmt", "yuv420p",
                    "-c:a", "aac", "-b:a", "128k", "-ar", "48000",
                    "-movflags", "+faststart", web], check=True)
    print(f"08(60s): {os.path.getsize(master)//1024}KB / web {os.path.getsize(web)//1024}KB")


if __name__ == "__main__":
    main()
