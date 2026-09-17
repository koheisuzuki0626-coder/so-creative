# -*- coding: utf-8 -*-
"""素材カットをつないでテロップ・BGMを乗せ、3本を書き出す。

テロップは黒ブロックと文字を別PNGで重ね、どちらも overlay の y 時間式で
下から持ち上げる。文字だけフェードを遅らせて、ブロックが出たあとに文字が乗る。
drawbox は x/w に時間変数を持たないので使わない。
"""
import json
import os
import subprocess
import sys

FF = os.environ.get("SO_FFMPEG",
                    "/usr/local/lib/python3.11/dist-packages/imageio_ffmpeg/"
                    "binaries/ffmpeg-linux-x86_64-v7.0.2")
HERE = os.path.dirname(os.path.abspath(__file__))
TELOP = f"{HERE}/telop"
GEN = os.environ["SO_GEN"]      # 素材カットの置き場
OUT = os.environ.get("SO_OUT", f"{HERE}/out")
os.makedirs(OUT, exist_ok=True)

BOX = json.load(open(f"{TELOP}/boxes.json"))
COLOR = BOX["block_color"]
B = BOX["boxes"]

RISE = 190          # 下から持ち上げる量(px)。ブロックの高さぶん
RISE_D = 0.34       # 持ち上げにかける時間
BLK_IN = 0.16       # ブロックのフェードイン
TXT_LAG = 0.13      # 文字はブロックより遅れて出す
TXT_IN, TXT_OUT = 0.22, 0.24


def layer(idx, st, en, is_text):
    """ブロック／文字のレイヤー。どちらも同じ y 式で動かす。"""
    if is_text:
        fi, d_in = st + TXT_LAG, TXT_IN
    else:
        fi, d_in = st, BLK_IN
    fo = en - TXT_OUT
    return (f"[{idx}:v]format=rgba,"
            f"fade=t=in:st={fi}:d={d_in}:alpha=1,"
            f"fade=t=out:st={fo}:d={TXT_OUT}:alpha=1[t{idx}]")


def overlay_y(st):
    return f"'{RISE}*max(0,1-(t-{st})/{RISE_D})'"


def build(name, cuts, telops, dim, logo, logo_at, dim_at, bgm, measured):
    """cuts: [(file, in, dur)] / telops: [(key, st, en)]"""
    ins, fc = [], []
    for i, (f, tin, dur) in enumerate(cuts):
        ins += ["-i", f]
        fc.append(f"[{i}:v]trim={tin}:{tin + dur},setpts=PTS-STARTPTS,"
                  f"scale=1920:1080:flags=lanczos,fps=24[v{i}]")
    fc.append("".join(f"[v{i}]" for i in range(len(cuts)))
              + f"concat=n={len(cuts)}:v=1:a=0[cat]")

    fc.append("[cat]null[bg]")

    idx = len(cuts)
    tex = []
    for (k, st, en) in telops:
        for suffix, is_text in ((f"{k}_blk", False), (k, True)):
            ins += ["-loop", "1", "-t", "15", "-i", f"{TELOP}/{suffix}.png"]
            fc.append(layer(idx, st, en, is_text))
            tex.append((idx, st))
            idx += 1
    ins += ["-loop", "1", "-t", "15", "-i", f"{TELOP}/{dim}.png"]
    fc.append(f"[{idx}:v]format=rgba,fade=t=in:st={dim_at}:d=0.5:alpha=1[dim]")
    idx += 1
    ins += ["-loop", "1", "-t", "15", "-i", f"{TELOP}/{logo}.png"]
    fc.append(f"[{idx}:v]format=rgba,fade=t=in:st={logo_at}:d=0.5:alpha=1[lg]")

    cur = "[bg]"
    for n, (i, st) in enumerate(tex):
        nxt = f"[o{n}]"
        fc.append(f"{cur}[t{i}]overlay=0:y={overlay_y(st)}{nxt}")
        cur = nxt
    fc.append(f"{cur}[dim]overlay=0:0[od]")
    fc.append("[od][lg]overlay=0:0,format=yuv420p[vout]")

    silent = f"{OUT}/{name}_silent.mp4"
    cmd = [FF, "-loglevel", "error", "-y"] + ins + [
        "-filter_complex", ";".join(fc), "-map", "[vout]", "-t", "15", "-an",
        "-c:v", "libx264", "-crf", "16", "-preset", "slow",
        "-movflags", "+faststart", silent]
    subprocess.run(cmd, check=True)

    mi, mtp, mlra, mth, off = measured
    master = f"{OUT}/{name}_master.mp4"
    subprocess.run([
        FF, "-loglevel", "error", "-y", "-i", silent, "-i", bgm,
        "-map", "0:v:0", "-map", "1:a:0", "-c:v", "copy",
        "-af", (f"loudnorm=I=-16:TP=-2.0:LRA=11:measured_I={mi}:measured_TP={mtp}:"
                f"measured_LRA={mlra}:measured_thresh={mth}:offset={off}:linear=true,"
                "alimiter=limit=0.82:attack=1:release=40"),
        "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-shortest",
        "-movflags", "+faststart", master], check=True)

    web = f"{OUT}/{name}_web.mp4"
    subprocess.run([
        FF, "-loglevel", "error", "-y", "-i", master,
        "-c:v", "libx264", "-crf", "26", "-maxrate", "2000k", "-bufsize", "4000k",
        "-preset", "slow", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "128k", "-ar", "48000",
        "-movflags", "+faststart", web], check=True)
    print(f"{name}: {os.path.getsize(master)//1024}KB / web {os.path.getsize(web)//1024}KB")


if __name__ == "__main__":
    M02 = ("-12.90", "-1.16", "2.50", "-23.09", "-0.76")
    M04 = ("-13.06", "-0.27", "2.70", "-23.16", "-0.31")
    b02, b04 = f"{HERE}/bgm_02.wav", f"{HERE}/bgm_04.wav"

    build("02_service_15s",
          [(f"{GEN}/02_c1.mp4", 0.04, 5.0), (f"{GEN}/02_c2_v2.mp4", 0.04, 5.0),
           (f"{GEN}/02_c3.mp4", 0.04, 5.0)],
          [("02_1", 0.45, 4.70), ("02_2", 5.40, 9.70), ("02_3", 10.35, 12.50)],
          "dim34", "02_logo", 12.75, 12.45, b02, M02)

    build("04a_taste_15s",
          [(f"{HERE}/04_c1_slow.mp4", 0.0, 6.0), (f"{GEN}/04_c2.mp4", 0.04, 5.0),
           (f"{GEN}/04_c3_v2.mp4", 1.04, 4.0)],
          [("04a_1", 0.45, 5.70), ("04a_2", 6.35, 10.70)],
          "dim29", "04_logo", 11.4, 11.1, b04, M04)

    build("04b_time_15s",
          [(f"{GEN}/04_c3_v2.mp4", 0.04, 5.0), (f"{HERE}/04_c1_slow.mp4", 0.0, 6.0),
           (f"{GEN}/04_c2.mp4", 1.04, 4.0)],
          [("04b_1", 0.45, 4.65), ("04b_2", 5.40, 10.70)],
          "dim29", "04_logo_top", 11.4, 11.1, b04, M04)
