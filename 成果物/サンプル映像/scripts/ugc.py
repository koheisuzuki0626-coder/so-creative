# -*- coding: utf-8 -*-
"""架空商品「まもり葉」の UGC 風クリップを仕上げる。

生成した10秒（kling3_0 pro / 9:16）に、締めのカードと BGM を足す。
"""
import os
import subprocess
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

import product_label as PL

FFMPEG = "/usr/local/lib/python3.11/dist-packages/imageio_ffmpeg/binaries/ffmpeg-linux-x86_64-v7.0.2"
FONTS = "/tmp/fonts"
MINCHO_M = f"{FONTS}/NotoSerifJP-Medium.ttf"
GOTHIC_B = f"{FONTS}/NotoSansJP-Black.ttf"

W, H = 1080, 1920
PAPER = (238, 234, 223)     # 生成りの地
INK = (44, 68, 51)          # 濃緑。商品と同じ色
FAINT = (139, 152, 138)


def _track(d, cx, y, text, font, track, fill):
    total = sum(d.textlength(c, font=font) for c in text) + track * (len(text) - 1)
    x = cx - total / 2
    for ch in text:
        d.text((x, y), ch, font=font, fill=fill, anchor="lt")
        x += d.textlength(ch, font=font) + track


def end_card(path):
    """締めのカード。商品のラベルと同じ組みにして、ひと続きに見せる。"""
    ss = 2
    img = Image.new("RGB", (W * ss, H * ss), PAPER)
    d = ImageDraw.Draw(img)
    cx = W * ss / 2

    f_name = ImageFont.truetype(MINCHO_M, int(118 * ss))
    f_cat = ImageFont.truetype(GOTHIC_B, int(34 * ss))
    f_note = ImageFont.truetype(GOTHIC_B, int(24 * ss))

    # マークは商品ラベルと同じ関数で描く
    mark = Image.new("L", (400 * ss, 400 * ss), 0)
    PL.draw_mark(ImageDraw.Draw(mark), 200 * ss, 200 * ss, 190 * ss)
    tint = Image.new("RGB", mark.size, INK)
    img.paste(tint, (int(cx - 200 * ss), int(555 * ss)), mark)

    _track(d, cx, 1000 * ss, "まもり葉", f_name, 14 * ss, INK)

    rw = 150 * ss
    ry = 1185 * ss
    d.rectangle([cx - rw / 2, ry, cx + rw / 2, ry + 3 * ss], fill=INK)

    _track(d, cx, 1228 * ss, "ハンドクリーム", f_cat, 14 * ss, INK)
    _track(d, cx, 1740 * ss, "架空の商品です", f_note, 8 * ss, FAINT)

    img.resize((W, H), Image.LANCZOS).save(path)
    return path


def probe(path):
    """ffprobe が無いので ffmpeg の出力から尺を拾う。"""
    r = subprocess.run([FFMPEG, "-i", path], capture_output=True, text=True)
    for line in r.stderr.splitlines():
        if "Duration:" in line:
            hh, mm, ss = line.split("Duration:")[1].split(",")[0].strip().split(":")
            return int(hh) * 3600 + int(mm) * 60 + float(ss)
    raise RuntimeError("尺が読めない: " + path)


def run(src, out, bgm_wav, tail=2.2, fade=0.5):
    """本編 + 締めカード + BGM。"""
    here = os.path.dirname(os.path.abspath(__file__))
    card = end_card(os.path.join("/tmp", "_ugc_card.png"))

    # 本編を 1080x1920 に揃える
    body = "/tmp/_ugc_body.mp4"
    subprocess.run([
        FFMPEG, "-y", "-i", src,
        "-vf", f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},fps=30",
        "-an", "-c:v", "libx264", "-crf", "17", "-pix_fmt", "yuv420p", body,
    ], check=True, capture_output=True)

    # 締めカードを静止尺で
    tailmp4 = "/tmp/_ugc_tail.mp4"
    subprocess.run([
        FFMPEG, "-y", "-loop", "1", "-t", str(tail), "-i", card,
        "-vf", f"scale={W}:{H},fps=30", "-c:v", "libx264", "-crf", "17",
        "-pix_fmt", "yuv420p", tailmp4,
    ], check=True, capture_output=True)

    # 連結（本編の終わりから締めへ白フェード気味に繋ぐ）
    joined = "/tmp/_ugc_joined.mp4"
    lst = "/tmp/_ugc_list.txt"
    with open(lst, "w") as f:
        f.write(f"file '{body}'\nfile '{tailmp4}'\n")
    subprocess.run([FFMPEG, "-y", "-f", "concat", "-safe", "0", "-i", lst,
                    "-c", "copy", joined], check=True, capture_output=True)

    dur = probe(joined)
    subprocess.run([
        FFMPEG, "-y", "-i", joined, "-i", bgm_wav,
        "-filter_complex",
        f"[1:a]afade=t=out:st={max(dur - fade, 0.1)}:d={fade},"
        "loudnorm=I=-16:TP=-1.5:LRA=11,alimiter=limit=0.82[a]",
        "-map", "0:v", "-map", "[a]", "-shortest",
        "-c:v", "libx264", "-crf", "20", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "160k", "-ar", "48000",
        "-movflags", "+faststart", out,
    ], check=True, capture_output=True)
    return out


if __name__ == "__main__":
    import sys
    print(run(sys.argv[1], sys.argv[2], sys.argv[3]))


def run_talk(src, out, tail=2.4, fade=0.8):
    """人が喋るカット（生成音声あり）＋ 締めカード。BGM は足さない。"""
    card = end_card("/tmp/_ugc_card.png")
    dur = probe(src)

    body = "/tmp/_talk_body.mp4"
    subprocess.run([
        FFMPEG, "-y", "-i", src,
        "-vf", f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},fps=30",
        "-c:v", "libx264", "-crf", "18", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "160k", "-ar", "48000", body,
    ], check=True, capture_output=True)

    # 締めカードは無音で作り、本編の音を尻でフェードさせる
    tailmp4 = "/tmp/_talk_tail.mp4"
    subprocess.run([
        FFMPEG, "-y", "-loop", "1", "-t", str(tail), "-i", card,
        "-f", "lavfi", "-t", str(tail), "-i", "anullsrc=r=48000:cl=stereo",
        "-vf", f"scale={W}:{H},fps=30", "-c:v", "libx264", "-crf", "18",
        "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k", "-ar", "48000",
        "-shortest", tailmp4,
    ], check=True, capture_output=True)

    lst = "/tmp/_talk_list.txt"
    with open(lst, "w") as f:
        f.write(f"file '{body}'\nfile '{tailmp4}'\n")
    joined = "/tmp/_talk_joined.mp4"
    subprocess.run([FFMPEG, "-y", "-f", "concat", "-safe", "0", "-i", lst,
                    "-c", "copy", joined], check=True, capture_output=True)

    subprocess.run([
        FFMPEG, "-y", "-i", joined,
        "-af", f"afade=t=out:st={max(dur - fade, 0.1)}:d={fade},"
               "loudnorm=I=-16:TP=-1.5:LRA=11,alimiter=limit=0.9",
        "-c:v", "copy", "-c:a", "aac", "-b:a", "160k", "-ar", "48000",
        "-movflags", "+faststart", out,
    ], check=True, capture_output=True)
    return out
