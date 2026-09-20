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


def layer(idx, st, en, is_text, b=None):
    """下敷き／文字のレイヤー。基本はどちらも同じ y 式で動かす。

    フェードの長さはテロップごとに上書きできる（05 の emo だけ倍近く遅い）。
    """
    b = b or {}
    out_d = b.get("txt_out", TXT_OUT)
    if is_text:
        fi, d_in = st + b.get("txt_lag", TXT_LAG), b.get("txt_in", TXT_IN)
    else:
        fi, d_in = st, b.get("blk_in", BLK_IN)
    fo = en - out_d
    return (f"[{idx}:v]format=rgba,"
            f"fade=t=in:st={fi}:d={d_in}:alpha=1,"
            f"fade=t=out:st={fo}:d={out_d}:alpha=1[t{idx}]")


def overlay_y(st, rise=RISE, rise_d=RISE_D):
    return f"'{rise}*max(0,1-(t-{st})/{rise_d})'"


def measure(path, tp=-2.0):
    """loudnorm の1パス目。2パスにしないと AAC 変換でピークが 0dB に張り付く。"""
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


def render_silent(path, cuts, telops, dim, logo, logo_at, dim_at, canvas,
                  grade=None):
    """映像だけを1本に焼く。cuts: [(file, in, dur)] / telops: [(key, st, en)]"""
    total = sum(c[2] for c in cuts)      # 15秒とは限らない（3分版がある）
    cw, ch = canvas
    ar = f"{cw}/{ch}"
    ins, fc = [], []
    for i, cut in enumerate(cuts):
        # 4つ目は寄り倍率（省略なら等倍）。同じ素材を寄り引きで2カットに
        # 使い分けるために足した。倍率が違えばサイズ違いの別カットに見える
        f, tin, dur = cut[0], cut[1], cut[2]
        z = cut[3] if len(cut) > 3 else 1.0
        # 5つ目はこのカットだけの階調。"" を渡すと grade をかけない。
        # 暗い実写に合わせた持ち上げを、明るい静止画にまでかけると白く飛ぶ
        g = cut[4] if len(cut) > 4 else grade
        ins += ["-i", f]
        # 素材のアスペクト比が出力と違うことがある（kling は 1928x1076 を返す）。
        # 出力比でセンタークロップしてから合わせる
        gf = f"{g}," if g else ""
        fc.append(f"[{i}:v]trim={tin}:{tin + dur},setpts=PTS-STARTPTS,"
                  f"crop='min(iw,ih*{ar})/{z}':'min(ih,iw*{ch}/{cw})/{z}',"
                  f"scale={cw}:{ch}:flags=lanczos,setsar=1,{gf}fps=24[v{i}]")
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
            ins += ["-loop", "1", "-t", str(total), "-i", f"{TELOP}/{suffix}.png"]
            fc.append(layer(idx, st, en, is_text, B[k]))
            tex.append((idx, None if static else st,
                        B[k].get("rise", RISE), B[k].get("rise_d", RISE_D)))
            idx += 1
    # 締め（暗転＋ロゴ）は本によって無い（07 研修は STEP 3 で終わる）
    ending = []
    if dim:
        ins += ["-loop", "1", "-t", str(total), "-i", f"{TELOP}/{dim}.png"]
        fc.append(f"[{idx}:v]format=rgba,fade=t=in:st={dim_at}:d=0.5:alpha=1[dim]")
        ending.append("dim")
        idx += 1
    if logo:
        ins += ["-loop", "1", "-t", str(total), "-i", f"{TELOP}/{logo}.png"]
        fc.append(f"[{idx}:v]format=rgba,fade=t=in:st={logo_at}:d=0.5:alpha=1[lg]")
        ending.append("lg")

    cur = "[bg]"
    for n, (i, st, rise, rise_d) in enumerate(tex):
        nxt = f"[o{n}]"
        pos = "0:0" if st is None else f"0:y={overlay_y(st, rise, rise_d)}"
        fc.append(f"{cur}[t{i}]overlay={pos}{nxt}")
        cur = nxt
    for n, lab in enumerate(ending):
        nxt = f"[e{n}]"
        fc.append(f"{cur}[{lab}]overlay=0:0{nxt}")
        cur = nxt
    fc.append(f"{cur}null,format=yuv420p[vout]")

    subprocess.run([FF, "-loglevel", "error", "-y"] + ins + [
        "-filter_complex", ";".join(fc), "-map", "[vout]", "-t", str(total), "-an",
        "-c:v", "libx264", "-crf", "16", "-preset", "slow",
        "-movflags", "+faststart", path], check=True)


def build(name, cuts, telops, dim, logo, logo_at, dim_at, audio,
          canvas=(1920, 1080), tp=-2.0, limit=0.82, loudnorm=True, chunk=0,
          grade=None):
    """chunk を渡すとその本数ずつ別々に焼いてから連結する。

    テロップは1枚につき PNG を尺いっぱい展開するので、3分 × 44枚を一度に
    流すとメモリが 14GB を超えて止まる。章ごとに分けると同じ絵のまま収まる。
    """
    silent = f"{OUT}/{name}_silent.mp4"
    if not chunk or len(cuts) <= chunk:
        render_silent(silent, cuts, telops, dim, logo, logo_at, dim_at, canvas,
                      grade)
    else:
        parts, off = [], 0.0
        for n in range(0, len(cuts), chunk):
            grp = cuts[n:n + chunk]
            dur = sum(c[2] for c in grp)
            # このかたまりに収まるテロップだけを、頭を0に寄せて渡す
            tl = []
            for (k, st, en) in telops:
                if off <= st < off + dur:
                    assert en <= off + dur + 1e-6, f"{k} がかたまりをまたいでいる"
                    tl.append((k, st - off, en - off))
            in_grp = (lambda x: off <= x < off + dur)
            part = f"{OUT}/{name}_part{n // chunk:02d}.mp4"
            render_silent(part, grp, tl,
                          dim if dim and in_grp(dim_at) else None,
                          logo if logo and in_grp(logo_at) else None,
                          logo_at - off, dim_at - off, canvas, grade)
            parts.append(part)
            print(f"  {name} part{n // chunk:02d} ok", flush=True)
            off += dur
        lst = f"{OUT}/{name}_parts.txt"
        with open(lst, "w") as f:
            f.write("".join(f"file '{p}'\n" for p in parts))
        subprocess.run([FF, "-loglevel", "error", "-y", "-f", "concat",
                        "-safe", "0", "-i", lst, "-c", "copy",
                        "-movflags", "+faststart", silent], check=True)
        for p in parts + [lst]:
            os.remove(p)

    # SE だけのトラック（BGM なし）は loudnorm を通さない。
    # LUFS が低く出るぶん I=-16 に合わせようと持ち上げられ、
    # ピークが 0dB に張り付く。se.py 側で正規化済みなのでそのまま使う
    if loudnorm:
        mi, mtp, mlra, mth, off = measure(audio, tp)
        af = (f"loudnorm=I=-16:TP={tp}:LRA=11:measured_I={mi}:measured_TP={mtp}:"
              f"measured_LRA={mlra}:measured_thresh={mth}:offset={off}:linear=true,"
              f"alimiter=limit={limit}:attack=1:release=40")
    else:
        af = f"alimiter=limit={limit}:attack=5:release=60,volume=0.8"
    master = f"{OUT}/{name}_master.mp4"
    subprocess.run([
        FF, "-loglevel", "error", "-y", "-i", silent, "-i", audio,
        "-map", "0:v:0", "-map", "1:a:0", "-c:v", "copy",
        "-af", af,
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

    # 9/20 に組み直した。3カット（焼き6秒・箸5秒・食卓4秒）は前半が重く、
    # 冷凍であることも、商品名に入っている羽根も、パッケージも映っていなかった。
    # 並べる／皿に返した羽根／パッケージの3つを足して9カットにしている。
    # 締めはロゴ札をやめてパッケージそのもの。名前は袋に刷ってあるので重複する
    if wanted("04a_taste_15s"):
        build("04a_taste_15s",
              [(f"{GEN}/04_v1.mp4", 0.30, 1.6),        # 凍ったまま並べる
               (C1, C1_IN, 1.5),                        # 焼き
               (C1, C1_IN + 3.4, 1.2, 1.35),            # 蒸気（寄り）
               (f"{GEN}/04_v2.mp4", 0.10, 1.6),         # 皿に返した羽根
               (f"{GEN}/04_v2.mp4", 3.30, 1.3, 1.70),   # 羽根の寄り
               (f"{GEN}/04_c2.mp4", 0.04, 1.6),         # 箸で持ち上げ
               (f"{GEN}/04_c2.mp4", 3.60, 1.2, 1.35),   # 肉汁（寄り）
               (f"{GEN}/04_c3_v3m.mp4", 0.80, 1.8),     # 食卓
               # パッケージは刷った静止画なので、持ち上げはかけない
               (f"{GEN}/04_pack.mp4", 0.00, 3.2, 1.0, "")],
              # テロップはカットの切れ目で終える（次の画に食い込ませない）
              [("04a_1", 0.40, 4.15), ("04a_2", 4.50, 7.05),
               ("04a_3", 7.50, 9.90)],
              None, None, 0.0, 0.0, a04a,
              # 台所が暗く、食べ物のCMとしては沈んでいた。暗部と中間を
              # 起こし、白は飛ばさない。彩度もわずかに上げる
              grade="curves=m='0/0.04 0.14/0.37 0.35/0.60 0.6/0.79 0.85/0.94 1/1',"
                    "eq=saturation=1.10")

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
               # C3 は畳んだタオルが乾燥機から出てくる画になっていたので撮り直した。
               # 畳むのは次のカットなので、ここはふわっとした洗濯物を抱え出す。
               # 後半は手元が画面いっぱいになるので頭から2.5秒だけ使う
               (f"{GEN}/05_v3b.mp4", 0.2, 2.5), (f"{GEN}/05_v4.mp4", 1.0, 2.5),
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
              None, None, 0, 0, f"{HERE}/audio_07.wav",
              loudnorm=False, limit=0.72)

    if wanted("03_recruit_3min"):
        # 全36カット × 5.0秒 = 180秒。構成案では17・18・34・35・36 を
        # 6〜7秒にしていたが、素材が5.04秒なので全カット等尺に直した
        R3 = os.environ.get("SO_R3", f"{GEN}/r3")
        # 「全体的に古い」という指摘で、応募者が職場を判断する9カットを撮り直した。
        # 機械まわり（旋盤・切削・検査）はそのまま。w** が撮り直したぶん。
        # 02 は名札を直す手元だったのを、朝いちばんに工場へ入る画に変えた
        # 36 は最後の外観。33 と同じ建物の夜に差し替えた
        REDO = {1, 2, 20, 21, 30, 31, 32, 33, 35, 36}
        cuts = [(f"{R3}/{'w' if i in REDO else 'v'}{i:02d}.mp4", 0.02, 5.0)
                for i in range(1, 37)]
        # テロップはカット頭から0.45秒後に出て、カット終わりの0.35秒前に消える
        tel = []
        for i in (3, 5, 8, 10, 11, 13, 15, 17, 18, 19, 22, 24, 25,
                  27, 28, 29, 30, 31, 32, 34):
            st = (i - 1) * 5.0
            tel.append((f"r3_{i:02d}", st + 0.45, st + 4.65))
        build("03_recruit_3min", cuts, tel,
              "dim34", "r3_logo", 176.2, 175.8, f"{HERE}/audio_03_3min.wav",
              chunk=6)

    # 訴求B（時短）は取りやめ。名前を明示したときだけ作る
    if "04b_time_15s" in sys.argv[1:]:
        build("04b_time_15s",
              [(f"{GEN}/04_c3_v3m.mp4", 0.04, 5.0), (C1, C1_IN, 6.0),
               (f"{GEN}/04_c2.mp4", 1.04, 4.0)],
              [("04b_1", 0.45, 4.65), ("04b_2", 5.40, 10.70)],
              "dim29", "04_logo_top", 11.4, 11.1, a04b)
