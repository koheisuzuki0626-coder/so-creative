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

B = BOX["boxes"]

RISE = 190          # 下から持ち上げる量(px)。ブロックの高さぶん
RISE_D = 0.34       # 持ち上げにかける時間
BLK_IN = 0.16       # ブロックのフェードイン
TXT_LAG = 0.13      # 文字はブロックより遅れて出す
TXT_IN, TXT_OUT = 0.22, 0.24


def layer(idx, st, en, is_text):
    """下敷き／文字のレイヤー。基本はどちらも同じ y 式で動かす。"""
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


def measure(path):
    """loudnorm の1パス目。2パスにしないと AAC 変換でピークが 0dB に張り付く。"""
    out = subprocess.run(
        [FF, "-hide_banner", "-i", path, "-af",
         "loudnorm=I=-16:TP=-2.0:print_format=json", "-f", "null", "-"],
        capture_output=True, text=True).stderr
    keys = ("input_i", "input_tp", "input_lra", "input_thresh", "target_offset")
    vals = {}
    for line in out.splitlines():
        for k in keys:
            if f'"{k}"' in line:
                vals[k] = line.split(":")[1].strip().strip('",')
    return tuple(vals[k] for k in keys)


def build(name, cuts, telops, dim, logo, logo_at, dim_at, audio,
          canvas=(1920, 1080)):
    """cuts: [(file, in, dur)] / telops: [(key, st, en)]"""
    cw, ch = canvas
    ar = f"{cw}/{ch}"
    ins, fc = [], []
    for i, (f, tin, dur) in enumerate(cuts):
        ins += ["-i", f]
        # 素材のアスペクト比が出力と違うことがある（kling は 1928x1076 を返す）。
        # 出力比でセンタークロップしてから合わせる
        fc.append(f"[{i}:v]trim={tin}:{tin + dur},setpts=PTS-STARTPTS,"
                  f"crop='min(iw,ih*{ar})':'min(ih,iw*{ch}/{cw})',"
                  f"scale={cw}:{ch}:flags=lanczos,setsar=1,fps=24[v{i}]")
    fc.append("".join(f"[v{i}]" for i in range(len(cuts)))
              + f"concat=n={len(cuts)}:v=1:a=0[cat]")

    fc.append("[cat]null[bg]")

    idx = len(cuts)
    tex = []
    for (k, st, en) in telops:
        layers = [(k, True, False)]
        if B[k].get("underlay", True):
            # グラデーションの下敷きは動かさない（下端に隙間ができる）
            layers.insert(0, (f"{k}_blk", False, B[k].get("static_underlay", False)))
        for suffix, is_text, static in layers:
            ins += ["-loop", "1", "-t", "15", "-i", f"{TELOP}/{suffix}.png"]
            fc.append(layer(idx, st, en, is_text))
            tex.append((idx, None if static else st))
            idx += 1
    # 締め（暗転＋ロゴ）は本によって無い（07 研修は STEP 3 で終わる）
    ending = []
    if dim:
        ins += ["-loop", "1", "-t", "15", "-i", f"{TELOP}/{dim}.png"]
        fc.append(f"[{idx}:v]format=rgba,fade=t=in:st={dim_at}:d=0.5:alpha=1[dim]")
        ending.append("dim")
        idx += 1
    if logo:
        ins += ["-loop", "1", "-t", "15", "-i", f"{TELOP}/{logo}.png"]
        fc.append(f"[{idx}:v]format=rgba,fade=t=in:st={logo_at}:d=0.5:alpha=1[lg]")
        ending.append("lg")

    cur = "[bg]"
    for n, (i, st) in enumerate(tex):
        nxt = f"[o{n}]"
        pos = "0:0" if st is None else f"0:y={overlay_y(st)}"
        fc.append(f"{cur}[t{i}]overlay={pos}{nxt}")
        cur = nxt
    for n, lab in enumerate(ending):
        nxt = f"[e{n}]"
        fc.append(f"{cur}[{lab}]overlay=0:0{nxt}")
        cur = nxt
    fc.append(f"{cur}null,format=yuv420p[vout]")

    silent = f"{OUT}/{name}_silent.mp4"
    cmd = [FF, "-loglevel", "error", "-y"] + ins + [
        "-filter_complex", ";".join(fc), "-map", "[vout]", "-t", "15", "-an",
        "-c:v", "libx264", "-crf", "16", "-preset", "slow",
        "-movflags", "+faststart", silent]
    subprocess.run(cmd, check=True)

    mi, mtp, mlra, mth, off = measure(audio)
    master = f"{OUT}/{name}_master.mp4"
    subprocess.run([
        FF, "-loglevel", "error", "-y", "-i", silent, "-i", audio,
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


def wanted(name):
    """引数で本を絞れるようにする（02だけ、04aだけ、と組み直せる）。"""
    return len(sys.argv) < 2 or name in sys.argv[1:]


if __name__ == "__main__":
    # BGM と SE をミックス済みのトラック（se.py が書き出す）
    a02 = f"{HERE}/audio_02.wav"
    a04a = f"{HERE}/audio_04a.wav"
    a04b = f"{HERE}/audio_04b.wav"
    # 04 C1 は kling3_0 の素材。餃子自体が動く（seedance は静止画起点だと動かない）
    C1 = os.environ.get("SO_C1", f"{GEN}/04_c1_kling.mp4")
    C1_IN = float(os.environ.get("SO_C1_IN", "0.0"))

    if wanted("02_service_15s"):
        build("02_service_15s",
              [(f"{GEN}/02_c1.mp4", 0.04, 5.0), (f"{GEN}/02_c2_v2.mp4", 0.04, 5.0),
               (f"{GEN}/02_c3.mp4", 0.04, 5.0)],
              [("02_1", 0.45, 4.70), ("02_2", 5.40, 9.70), ("02_3", 10.35, 12.50)],
              "dim34", "02_logo", 12.75, 12.45, a02)

    if wanted("04a_taste_15s"):
        build("04a_taste_15s",
              [(C1, C1_IN, 6.0), (f"{GEN}/04_c2.mp4", 0.04, 5.0),
               (f"{GEN}/04_c3_v3m.mp4", 0.6, 4.0)],
              [("04a_1", 0.45, 5.70), ("04a_2", 6.35, 10.70)],
              "dim29", "04_logo", 11.4, 11.1, a04a)

    if wanted("03_recruit_15s"):
        build("03_recruit_15s",
              [(f"{GEN}/03_v1.mp4", 0.1, 5.0), (f"{GEN}/03_v2.mp4", 0.1, 5.0),
               (f"{GEN}/03_v3.mp4", 0.1, 5.0)],
              [("03_1", 0.45, 4.70), ("03_2", 5.40, 9.70), ("03_3", 10.35, 12.50)],
              "dim34", "03_logo", 12.75, 12.45, f"{HERE}/audio_03.wav")

    if wanted("05_sns_15s"):
        # 6カット目は1カット目の素材を別区間で使い回す（構成案の「1カット目に戻る」）
        build("05_sns_15s",
              [(f"{GEN}/05_v1.mp4", 0.0, 2.5), (f"{GEN}/05_v2.mp4", 0.5, 2.5),
               (f"{GEN}/05_v3.mp4", 0.8, 2.5), (f"{GEN}/05_v4.mp4", 1.0, 2.5),
               (f"{GEN}/05_v5.mp4", 0.5, 2.5), (f"{GEN}/05_v1.mp4", 2.4, 2.5)],
              [("05_1", 0.30, 2.30), ("05_2", 2.80, 4.80), ("05_3", 5.30, 7.30),
               ("05_4", 7.80, 9.80), ("05_5", 10.30, 12.30)],
              "dim29v", "05_logo", 13.00, 12.70, f"{HERE}/audio_05.wav",
              canvas=(1080, 1920))

    if wanted("07_internal_15s"):
        # 研修用なので締めのロゴを付けず、STEP 3 を最後まで残す
        # C1 は 4.8秒あたりでカメラが動いて構図が崩れるので 4.2秒で切り、
        # 足りないぶんを C2・C3 に振る
        build("07_internal_15s",
              [(f"{GEN}/07_v4.mp4", 0.0, 4.2), (f"{GEN}/07_v2.mp4", 0.1, 5.4),
               (f"{GEN}/07_v3.mp4", 0.1, 5.4)],
              [("07_1", 0.35, 4.05), ("07_2", 4.60, 9.45), ("07_3", 10.00, 14.95)],
              None, None, 0, 0, f"{HERE}/audio_07.wav")

    # 訴求B（時短）は取りやめ。名前を明示したときだけ作る
    if "04b_time_15s" in sys.argv[1:]:
        build("04b_time_15s",
              [(f"{GEN}/04_c3_v3m.mp4", 0.04, 5.0), (C1, C1_IN, 6.0),
               (f"{GEN}/04_c2.mp4", 1.04, 4.0)],
              [("04b_1", 0.45, 4.65), ("04b_2", 5.40, 10.70)],
              "dim29", "04_logo_top", 11.4, 11.1, a04b)
