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


def render_chunk(cuts, path, unit=BAR):
    """cuts の3つ目は尺。unit=BAR なら小節数、unit=1.0 なら秒で読む。"""
    ins, fc = [], []
    for i, (src, tin, bars, z) in enumerate(cuts):
        dur = bars * unit
        ins += ["-i", f"{SRC}/{src}.mp4"]
        # 素材は 1276x720 で 16:9 ぴったりではないので、出力比で切ってから合わせる
        fc.append(
            f"[{i}:v]trim={tin}:{tin + dur},setpts=PTS-STARTPTS,"
            f"crop='min(iw,ih*{W}/{H})/{z}':'min(ih,iw*{H}/{W})/{z}',"
            f"scale={W}:{H}:flags=lanczos,setsar=1,{GRADE},fps={FPS}[v{i}]")
    fc.append("".join(f"[v{i}]" for i in range(len(cuts)))
              + f"concat=n={len(cuts)}:v=1:a=0,format=yuv420p[vout]")
    total = sum(c[2] for c in cuts) * unit
    subprocess.run([FF, "-loglevel", "error", "-y"] + ins +
                   ["-filter_complex", ";".join(fc), "-map", "[vout]",
                    "-t", str(total), "-an",
                    "-c:v", "libx264", "-crf", "16", "-preset", "medium",
                    path], check=True)


def render(cuts, song, name, chunk=12, unit=BAR):
    """カットが多いとフィルタが重いので、chunk 本ずつ焼いてから繋ぐ。"""
    parts = []
    for n in range(0, len(cuts), chunk):
        p = f"{OUT}/{name}_part{n // chunk:02d}.mp4"
        render_chunk(cuts[n:n + chunk], p, unit)
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

    total = sum(c[2] for c in cuts) * unit
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

# ダンス版（30秒）。踊り手は1人。Reference Element で同じ人物を通し、
# 衣装（黒の長袖＋深紅のロングスカート）はプロンプトの文言でも固定した。
# d53 は逆光のシルエットなので衣装が読めない。繋ぎとして中盤に置く。
# d75 は雨上がりの夜明けで色味がひとつだけ違うので、締めに固定する。
CUTS_DANCE = [
    ("d71", 0.20, 3, 1.00),    #  0.0- 4.5  路地の街・後ろ姿
    ("d72", 0.30, 3, 1.00),    #  4.5- 9.0  歩道橋・正面
    ("d53", 0.30, 2, 1.00),    #  9.0-12.0  高架下のシルエット
    ("d73", 0.20, 2, 1.00),    # 12.0-15.0  サビ頭。駐車場のフラッドライト
    ("d61", 0.20, 2, 1.00),    # 15.0-18.0  街路の真ん中
    ("d74", 0.30, 2, 1.00),    # 18.0-21.0  ネオンの路地・引き
    ("d71", 2.00, 2, 1.45),    # 21.0-24.0  1カット目に寄って戻る
    ("d61", 3.00, 1, 1.60),    # 24.0-25.5  ここから1小節で詰める
    ("d73", 3.20, 1, 1.55),    # 25.5-27.0
    ("d75", 1.50, 2, 1.00),    # 27.0-30.0  夜明け。両腕を上げて終わる
]

# ダンス版・インサート入り（30秒）。尺は秒で書く（render に unit=1.0 を渡す）。
#
# テンポはわざと崩している。小節（1.5秒）に全部乗せると律儀すぎて
# 曲に対して編集が後ろに引っ込むので、狙いは3つ：
#   ・インサートを 0.25〜0.45秒のフラッシュで拍の途中に差し込んで拍を食う
#   ・ダンスのカットは逆に伸ばして息を持たせる（半端な尺にする）
#   ・サビ頭の 12.00秒だけはきっちり合わせる。芯が1本通れば崩れても保つ
# 締めの d75 は4.00秒。ここだけ長く置いて落とす。
#
# インサートは街の風景版の素材（c*）から、人が写らない寄りの画を採った。
# 踊り手が1人という前提と矛盾させないため、傘の群れ（c21）や
# 自転車（c32）のような人の写る画は外している。
CUTS_DANCE_INS = [
    ("d71", 0.00, 2.60, 1.00),   #  0.00 路地の街・後ろ姿
    ("c4",  2.00, 0.35, 1.00),   #  2.60 窓の雨粒とボケたネオン
    ("d71", 2.60, 1.85, 1.00),   #  2.95 同じカットの続きに戻る
    ("c1",  1.80, 0.45, 1.00),   #  4.80 水たまりの赤い波紋
    ("d72", 0.30, 3.10, 1.00),   #  5.25 歩道橋・正面
    ("c31", 2.10, 0.30, 1.00),   #  8.35 水たまりを足が通る
    ("c20", 2.00, 0.30, 1.00),   #  8.65 シャッターのネオンの線
    ("d53", 0.30, 2.35, 1.00),   #  8.95 高架下のシルエット
    ("c22", 1.60, 0.70, 1.00),   # 11.30 マンホールの蒸気。サビ直前の溜め
    ("d73", 0.20, 2.40, 1.00),   # 12.00 ★サビ頭。駐車場のフラッドライト
    ("c19", 2.00, 0.28, 1.00),   # 14.40 排水から流れ出る水
    ("d61", 0.30, 2.12, 1.00),   # 14.68 街路の真ん中
    ("c30", 1.80, 0.55, 1.00),   # 16.80 地下道の階段
    ("d74", 0.30, 2.45, 1.00),   # 17.35 ネオンの路地・引き
    ("c13", 1.90, 0.40, 1.00),   # 19.80 自販機
    ("d71", 2.00, 1.70, 1.45),   # 20.20 1カット目に寄って戻る
    ("c15", 2.00, 0.25, 1.00),   # 21.90 手すりの水滴
    ("d61", 3.20, 1.15, 1.60),   # 22.15 ここから詰めていく
    ("c28", 2.00, 0.25, 1.00),   # 23.30 濡れた植物にネオン
    ("d73", 3.40, 0.95, 1.55),   # 23.55
    ("c14", 1.90, 0.30, 1.00),   # 24.50 コインランドリーの窓
    ("d72", 3.60, 0.85, 1.70),   # 24.80
    ("c35", 1.90, 0.35, 1.00),   # 25.65 電話ボックス
    ("d75", 1.00, 4.00, 1.00),   # 26.00 夜明け。長く置いて落とす
]

# ダンス版・インサート連打（30秒）。尺はフレーム数で書く（unit=1/FPS）。
#
# ひとつ前の版はインサートが2〜3秒ごとに1枚ずつで、崩したつもりが
# 別の一定さになっていた。そこで「いつ来るか読めない」ほうを作り込む：
#   ・溜め（最初の5.25秒はインサートなし。ダンスからダンスへ直接繋ぐ）
#   ・3連打 → 単発 → サビ直前に4連打で刻みを速くして突っ込む
#   ・サビ後は逆に5.5秒インサートを入れない（裏を取る）
#   ・20秒台で6連打、以降は2〜3枚ずつを短い間隔で挟んで畳む
#   ・締めの d75 は4.00秒。ここだけ長く置いて落とす
#
# 尺を秒で書くと 1フレームに乗らず、35カットぶんの端数が積もって
# サビ頭がずれる。だからフレーム数で書く。288f = 12.00秒（サビ頭）、
# 624f = 26.00秒（締めの頭）、720f = 30.00秒。
CUTS_DANCE_INS2 = [
    ("d71", 0.00, 74, 1.00),   #   0f  0.00 路地の街・後ろ姿。長く見せて溜める
    ("d72", 0.30, 52, 1.00),   #  74f  3.08 インサートを挟まずダンスへ直接繋ぐ
    ("c4",  2.00,  5, 1.00),   # 126f  5.25 ★3連打
    ("c20", 2.00,  4, 1.00),   # 131f  5.46 ★
    ("c1",  1.80,  6, 1.00),   # 135f  5.63 ★
    ("d72", 2.40, 62, 1.00),   # 141f  5.88 歩道橋に戻る
    ("c31", 2.10,  8, 1.00),   # 203f  8.46 単発
    ("d53", 0.30, 40, 1.00),   # 211f  8.79 高架下のシルエット
    ("c22", 1.60,  6, 1.00),   # 251f 10.46 ★サビ直前の4連打。刻みを速くする
    ("c19", 2.00,  5, 1.00),   # 257f 10.71 ★
    ("c15", 2.00,  4, 1.00),   # 262f 10.92 ★
    ("c30", 1.80,  5, 1.00),   # 266f 11.08 ★
    ("d53", 2.10, 17, 1.00),   # 271f 11.29 シルエットに戻って突っ込む
    ("d73", 0.20, 70, 1.00),   # 288f 12.00 ★サビ頭。ここだけきっちり合わせる
    ("d61", 0.30, 61, 1.00),   # 358f 14.92 サビ後は5.5秒インサートを入れない
    ("c13", 1.90,  7, 1.00),   # 419f 17.46 単発
    ("d74", 0.30, 49, 1.00),   # 426f 17.75 ネオンの路地・引き
    ("c14", 1.90,  5, 1.00),   # 475f 19.79 ★6連打
    ("c35", 1.90,  4, 1.00),   # 480f 20.00 ★
    ("c28", 2.00,  4, 1.00),   # 484f 20.17 ★
    ("c33", 2.00,  5, 1.00),   # 488f 20.33 ★
    ("c26", 2.00,  4, 1.00),   # 493f 20.54 ★
    ("c23", 2.00,  4, 1.00),   # 497f 20.71 ★
    ("d71", 2.00, 37, 1.45),   # 501f 20.88 1カット目に寄って戻る
    ("c31", 2.40,  4, 1.00),   # 538f 22.42 ★2連打
    ("c20", 2.30,  3, 1.00),   # 542f 22.58 ★
    ("d61", 3.20, 23, 1.60),   # 545f 22.71 ここから畳んでいく
    ("c19", 2.30,  4, 1.00),   # 568f 23.67 ★3連打
    ("c4",  2.30,  3, 1.00),   # 572f 23.83 ★
    ("c1",  2.10,  4, 1.00),   # 575f 23.96 ★
    ("d73", 3.40, 20, 1.55),   # 579f 24.13
    ("c15", 2.30,  4, 1.00),   # 599f 24.96 ★2連打
    ("c30", 2.10,  4, 1.00),   # 603f 25.13 ★
    ("d72", 4.20, 17, 1.70),   # 607f 25.29
    ("d75", 1.00, 96, 1.00),   # 624f 26.00 夜明け。長く置いて落とす
]                              # 720f 30.00


if __name__ == "__main__":
    import sys
    want = sys.argv[1] if len(sys.argv) > 1 else "full"
    if want == "30":
        render(CUTS_30, f"{SRC}/mv_song.wav", "mv_30s")
    elif want == "dance_ins2":
        f = 0
        ins = 0
        for src, tin, fr, z in CUTS_DANCE_INS2:
            assert tin + fr / FPS <= CLIP + 1e-6, (src, tin, fr)
            if not src.startswith("d"):
                ins += 1
            print("%4df %5.2f→%5.2f  %2df %4.2f秒  %-4s %.2f"
                  % (f, f / FPS, (f + fr) / FPS, fr, fr / FPS, src, z))
            f += fr
        print("合計 %df = %.2f秒 / %dカット（うちインサート %d枚）"
              % (f, f / FPS, len(CUTS_DANCE_INS2), ins))
        assert f == 720, f
        render(CUTS_DANCE_INS2, f"{SRC}/mv_song.wav", "mv_dance_ins2_30s",
               unit=1.0 / FPS)
    elif want == "dance_ins":
        t = 0.0
        for src, tin, dur, z in CUTS_DANCE_INS:
            assert tin + dur <= CLIP + 1e-6, (src, tin, dur)
            print("%5.2f→%5.2f  %4.2f秒  %-4s %.2f" % (t, t + dur, dur, src, z))
            t += dur
        print("合計 %.2f秒 / %dカット" % (t, len(CUTS_DANCE_INS)))
        assert abs(t - 30.0) < 1e-6, t
        render(CUTS_DANCE_INS, f"{SRC}/mv_song.wav", "mv_dance_ins_30s",
               unit=1.0)
    elif want == "dance":
        t = 0.0
        for src, tin, bars, z in CUTS_DANCE:
            d = bars * BAR
            assert tin + d <= CLIP + 1e-6, (src, tin, bars)
            print("%5.1f→%5.1f  %4.1f秒  %-4s %.2f" % (t, t + d, d, src, z))
            t += d
        print("合計 %.1f秒 / %dカット" % (t, len(CUTS_DANCE)))
        render(CUTS_DANCE, f"{SRC}/mv_song.wav", "mv_dance_30s")
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
