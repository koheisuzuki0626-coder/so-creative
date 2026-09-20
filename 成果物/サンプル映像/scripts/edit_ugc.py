# -*- coding: utf-8 -*-
"""まもりば（まもり葉）の人物ありUGCを編集する。

生成そのままの並びから、カットの入れ替え・削除・差し替えをして繋ぎ直す。
"""
import subprocess
import numpy as np
from PIL import Image

FFMPEG = "/usr/local/lib/python3.11/dist-packages/imageio_ffmpeg/binaries/ffmpeg-linux-x86_64-v7.0.2"
W, H, FPS = 720, 1280, 30


def push_in(still, out, dur, audio=None, z0=1.00, z1=1.11):
    """静止画にゆっくり寄る。生成カットの差し替え用。"""
    src = Image.open(still).convert("RGB")
    sw, sh = src.size
    n = int(round(dur * FPS))
    p = subprocess.Popen(
        [FFMPEG, "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
         "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
         "-c:v", "libx264", "-crf", "20", "-preset", "medium",
         "-pix_fmt", "yuv420p", out],
        stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for i in range(n):
        t = i / max(n - 1, 1)
        t = t * t * (3 - 2 * t)                 # 出だしと終わりをなだらかに
        z = z0 + (z1 - z0) * t
        cw, ch = sw / z, sh / z
        x, y = (sw - cw) / 2, (sh - ch) / 2
        fr = src.resize((W, H), Image.LANCZOS, box=(x, y, x + cw, y + ch))
        p.stdin.write(np.asarray(fr).tobytes())
    p.stdin.close()
    p.wait()
    if audio:
        tmp = out.replace(".mp4", "_a.mp4")
        subprocess.run([FFMPEG, "-y", "-i", out, "-i", audio,
                        "-c:v", "copy", "-c:a", "aac", "-b:a", "128k",
                        "-ar", "48000", "-shortest", tmp],
                       check=True, capture_output=True)
        subprocess.run(["mv", tmp, out], check=True)
    return out


def move(still, out, dur, box0, box1, audio=None):
    """静止画の中を、box0 から box1 へゆっくり動く。box は (x, y, w, h)。"""
    src = Image.open(still).convert("RGB")
    n = int(round(dur * FPS))
    p = subprocess.Popen(
        [FFMPEG, "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
         "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
         "-c:v", "libx264", "-crf", "20", "-preset", "medium",
         "-pix_fmt", "yuv420p", out],
        stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for i in range(n):
        t = i / max(n - 1, 1)
        t = t * t * (3 - 2 * t)
        x, y, w, h = [a + (b - a) * t for a, b in zip(box0, box1)]
        fr = src.resize((W, H), Image.LANCZOS, box=(x, y, x + w, y + h))
        p.stdin.write(np.asarray(fr).tobytes())
    p.stdin.close()
    p.wait()
    if audio:
        tmp = out.replace(".mp4", "_a.mp4")
        subprocess.run([FFMPEG, "-y", "-i", out, "-i", audio,
                        "-c:v", "copy", "-c:a", "aac", "-b:a", "128k",
                        "-ar", "48000", "-shortest", tmp],
                       check=True, capture_output=True)
        subprocess.run(["mv", tmp, out], check=True)
    return out


def slice_audio(src, out, start, dur):
    subprocess.run([FFMPEG, "-y", "-ss", f"{start:.2f}", "-i", src,
                    "-t", f"{dur:.2f}", "-vn", "-ac", "2", "-ar", "48000",
                    "-c:a", "aac", "-b:a", "128k", out],
                   check=True, capture_output=True)
    return out


def norm(src, out, start=None, dur=None):
    """繋ぐ前に、全部のカットを同じ形式に揃える。"""
    cmd = [FFMPEG, "-y"]
    if start is not None:
        cmd += ["-ss", f"{start:.2f}"]
    cmd += ["-i", src]
    if dur is not None:
        cmd += ["-t", f"{dur:.2f}"]
    cmd += ["-vf", f"scale={W}:{H},fps={FPS}",
            "-c:v", "libx264", "-crf", "20", "-preset", "medium",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "128k", "-ar", "48000", "-ac", "2", out]
    subprocess.run(cmd, check=True, capture_output=True)
    return out


def join(parts, out):
    lst = "/tmp/_edit_list.txt"
    with open(lst, "w") as f:
        for p in parts:
            f.write(f"file '{p}'\n")
    subprocess.run([FFMPEG, "-y", "-f", "concat", "-safe", "0", "-i", lst,
                    "-c", "copy", "-movflags", "+faststart", out],
                   check=True, capture_output=True)
    return out


def probe(path):
    """ffprobe が無いので ffmpeg の出力から尺を拾う。"""
    r = subprocess.run([FFMPEG, "-i", path], capture_output=True, text=True)
    for line in r.stderr.splitlines():
        if "Duration:" in line:
            hh, mm, ss = line.split("Duration:")[1].split(",")[0].strip().split(":")
            return int(hh) * 3600 + int(mm) * 60 + float(ss)
    raise RuntimeError("尺が読めない: " + path)


def concat_video_only(parts, out):
    """映像だけを繋ぐ（音は別で作る）。"""
    lst = "/tmp/_vonly_list.txt"
    with open(lst, "w") as f:
        for p in parts:
            f.write(f"file '{p}'\n")
    subprocess.run([FFMPEG, "-y", "-f", "concat", "-safe", "0", "-i", lst,
                    "-an", "-c", "copy", out], check=True, capture_output=True)
    return out


def xfade_join(chunks, sr, ms=25):
    """音の断片を、継ぎ目だけ短く重ねて繋ぐ。段差も無音の穴も作らない。"""
    n = int(sr * ms / 1000)
    out = chunks[0].astype(np.float32).copy()
    for c in chunks[1:]:
        c = c.astype(np.float32)
        m = min(n, len(out), len(c))
        if m > 0:
            r = np.linspace(0, 1, m)
            out[-m:] = out[-m:] * (1 - r) + c[:m] * r
            out = np.concatenate([out, c[m:]])
        else:
            out = np.concatenate([out, c])
    return out
