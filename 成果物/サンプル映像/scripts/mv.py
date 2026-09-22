# -*- coding: utf-8 -*-
"""ミュージックビデオのサンプルを組む。30秒版とフル尺（4分24秒）版。

曲は鈴木さんの音源。BPM 160 なので1小節は 1.5秒。曲頭からグリッドが
揃っているので、カットの切れ目を全部小節頭に置ける。

構成は先に測って決めた（1秒ごとの音量と音の重心を出した）：
  0-24    イントロ（薄い）          小節 0-16
  24-84   Aメロ（音量小・低域なし）  小節 16-56
  84-108  一段上がる                小節 56-72
  108-120 落ちる（ブレイク）        小節 72-80
  120-156 いちばん強い              小節 80-104
  156-168 重心が 2600Hz に落ちる    小節 104-112
  168-252 上がったまま続く          小節 112-168
  252-264 アウトロ                  小節 168-176

素材は kling3_0 pro の5秒×32本。1本は 5.04秒しかないので、1カットは
最長3小節（4.5秒）。88カットに割るために、同じ素材を使い回している。
2回目・3回目は寄り倍率と使い始めを変えるので、同じ画には見えない。
素材は3つの群に分けて、曲の強さに合う群から採る。
"""
import os
import subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
FF = ("/usr/local/lib/python3.11/dist-packages/imageio_ffmpeg/binaries/"
      "ffmpeg-linux-x86_64-v7.0.2")
SRC = os.environ.get("SO_MV", f"{HERE}/mv")
OUT = f"{HERE}/out"
os.makedirs(OUT, exist_ok=True)

W, H, FPS = 1920, 1080, 24
BAR = 1.5                      # BPM 160 の1小節
CLIP = 5.04                    # 素材1本の長さ

# 6本の素材はもともと暗く撮れているので、締めるだけに留める。
# 黒を落として中間をわずかに上げ、彩度はほぼ触らない（ネオンが濁る）
GRADE = ("curves=m='0/0 0.10/0.07 0.40/0.42 0.75/0.79 1/1',"
         "eq=contrast=1.06:saturation=1.04")

# 素材を曲の強さで3群に分ける。群は重ねない（重ねると一部の素材だけ
# 使用回数が跳ね上がって、同じ画が何度も出てくる）
POOLS = {
    # 静かなところ（イントロ・ブレイク・アウトロ）。動きが少なく間が持つ画
    "quiet": ["c1", "c4", "c13", "c14", "c19", "c24",
              "c28", "c29", "c30", "c34", "c35", "c36"],
    # 中くらい（Aメロ）。場所が読める画
    "mid": ["c3", "c6", "c11", "c15", "c18", "c23", "c27", "c32", "c5", "c2"],
    # 強いところ（上がり・サビ）。動きの量が多い画
    "energy": ["c17", "c21", "c22", "c12", "c25", "c31",
               "c16", "c33", "c20", "c26"],
}
# いちばん詰めるところ（1小節＝1.5秒）は全部から採る。速いので繰り返しが
# 気にならないぶん、ここで群の偏りを均す
POOLS["all"] = POOLS["energy"] + POOLS["mid"] + POOLS["quiet"]

# (群, 各カットの小節数) を曲の順に並べる。合計 176小節 = 264.0秒
PLAN = [
    ("quiet",  [3, 3, 3, 3, 2, 2]),       # 0-24    イントロ
    ("mid",    [3] * 8),                  # 24-60   Aメロ前半
    ("mid",    [2] * 8),                  # 60-84   Aメロ後半（少し詰める）
    ("energy", [2] * 8),                  # 84-108  一段上がる
    ("quiet",  [3, 3, 2]),                # 108-120 ブレイク（間を取る）
    ("energy", [2] * 12),                 # 120-156 サビ
    ("quiet",  [2] * 4),                  # 156-168 重心が落ちるところ
    ("energy", [2] * 12),                 # 168-204 サビ戻り
    ("all",    [1] * 16),                 # 204-228 いちばん詰める
    ("mid",    [2] * 8),                  # 228-252 引いていく
    ("quiet",  [3, 3, 2]),                # 252-264 アウトロ
]

# 使い始めの秒。長いカットは頭しか取れない（素材が 5.04秒しかない）
TIN = {3: [0.15, 0.50], 2: [0.20, 1.10, 2.00], 1: [0.30, 1.60, 2.90, 3.50]}
ZOOM = [1.00, 1.32, 1.55, 1.75]        # 2回目以降は寄せて別カットに見せる
NO_REPEAT = 6                          # 直近このカット数は同じ素材を使わない


def build_cuts():
    """(素材, 使い始め, 小節数, 寄り倍率) の並びを作る。"""
    cuts, recent, used = [], [], {}
    idx = {k: 0 for k in POOLS}
    for pool, bars_list in PLAN:
        names = POOLS[pool]
        for bars in bars_list:
            # 直近に出ていない素材まで送る
            for _ in range(len(names)):
                name = names[idx[pool] % len(names)]
                idx[pool] += 1
                if name not in recent:
                    break
            n = used.get(name, 0)
            tins = TIN[bars]
            tin = tins[n % len(tins)]
            assert tin + bars * BAR <= CLIP + 1e-6, (name, tin, bars)
            cuts.append((name, tin, bars, ZOOM[min(n, len(ZOOM) - 1)]))
            used[name] = n + 1
            recent.append(name)
            if len(recent) > NO_REPEAT:
                recent.pop(0)
    # 締めは夜明けのカットに固定する。雨が止んだところで終わらせたい
    src, tin, bars, z = cuts[-1]
    cuts[-1] = ("c36", TIN[bars][0], bars, 1.00)
    return cuts


def render_chunk(cuts, path):
    ins, fc = [], []
    for i, (src, tin, bars, z) in enumerate(cuts):
        dur = bars * BAR
        ins += ["-i", f"{SRC}/{src}.mp4"]
        # 素材は 1276x720 で 16:9 ぴったりではないので、出力比で切ってから合わせる
        fc.append(
            f"[{i}:v]trim={tin}:{tin + dur},setpts=PTS-STARTPTS,"
            f"crop='min(iw,ih*{W}/{H})/{z}':'min(ih,iw*{H}/{W})/{z}',"
            f"scale={W}:{H}:flags=lanczos,setsar=1,{GRADE},fps={FPS}[v{i}]")
    fc.append("".join(f"[v{i}]" for i in range(len(cuts)))
              + f"concat=n={len(cuts)}:v=1:a=0,format=yuv420p[vout]")
    total = sum(c[2] for c in cuts) * BAR
    subprocess.run([FF, "-loglevel", "error", "-y"] + ins +
                   ["-filter_complex", ";".join(fc), "-map", "[vout]",
                    "-t", str(total), "-an",
                    "-c:v", "libx264", "-crf", "16", "-preset", "medium",
                    path], check=True)


def render(cuts, song, name, chunk=12):
    """カットが多いとフィルタが重いので、chunk 本ずつ焼いてから繋ぐ。"""
    parts = []
    for n in range(0, len(cuts), chunk):
        p = f"{OUT}/{name}_part{n // chunk:02d}.mp4"
        render_chunk(cuts[n:n + chunk], p)
        parts.append(p)
        print("  part%02d ok (%d カット)" % (n // chunk, len(cuts[n:n + chunk])),
              flush=True)
    lst = f"{OUT}/{name}_parts.txt"
    with open(lst, "w") as f:
        f.write("".join("file '%s'\n" % p for p in parts))
    silent = f"{OUT}/{name}_silent.mp4"
    subprocess.run([FF, "-loglevel", "error", "-y", "-f", "concat",
                    "-safe", "0", "-i", lst, "-c", "copy", silent], check=True)
    for p in parts + [lst]:
        os.remove(p)

    total = sum(c[2] for c in cuts) * BAR
    master = f"{OUT}/{name}_master.mp4"
    subprocess.run([FF, "-loglevel", "error", "-y", "-i", silent,
                    "-i", song, "-map", "0:v", "-map", "1:a",
                    "-t", str(total), "-c:v", "copy",
                    "-c:a", "aac", "-b:a", "192k",
                    "-movflags", "+faststart", master], check=True)
    web = f"{OUT}/{name}_web.mp4"
    subprocess.run([FF, "-loglevel", "error", "-y", "-i", master,
                    "-c:v", "libx264", "-crf", "26", "-preset", "slow",
                    "-c:a", "aac", "-b:a", "128k",
                    "-movflags", "+faststart", web], check=True)
    os.remove(silent)
    for p in (master, web):
        print("%s: %dKB" % (os.path.basename(p), os.path.getsize(p) // 1024))
    return web


# 30秒版のカット割り（108.0〜138.0秒を使う。12.0秒の位置でサビ頭）
CUTS_30 = [
    ("c1", 0.20, 3, 1.00), ("c4", 0.30, 3, 1.00), ("c6", 0.30, 2, 1.00),
    ("c2", 0.20, 3, 1.00), ("c3", 0.30, 2, 1.00), ("c5", 0.40, 2, 1.00),
    ("c3", 2.00, 2, 1.55), ("c2", 3.40, 1, 1.60), ("c5", 3.40, 1, 1.60),
    ("c1", 3.40, 1, 1.70),
]


if __name__ == "__main__":
    import sys
    want = sys.argv[1] if len(sys.argv) > 1 else "full"
    if want == "30":
        render(CUTS_30, f"{SRC}/mv_song.wav", "mv_30s")
    else:
        cuts = build_cuts()
        t = 0.0
        print("秒            小節 尺     素材 寄り")
        for src, tin, bars, z in cuts:
            d = bars * BAR
            print("%6.1f→%6.1f  %2d  %4.1f秒  %-4s %.2f"
                  % (t, t + d, bars, d, src, z))
            t += d
        n = {}
        for c in cuts:
            n[c[0]] = n.get(c[0], 0) + 1
        print("\n合計 %.1f秒 / %d小節 / %dカット / 素材 %d本"
              % (t, t / BAR, len(cuts), len(n)))
        print("素材ごとの使用回数: "
              + " ".join("%s:%d" % (k, v) for k, v in sorted(n.items())))
        render(cuts, f"{SRC}/song_full.wav", "mv_full")
