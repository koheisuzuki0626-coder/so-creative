#!/usr/bin/env python3
"""MVフル尺にカラコレを当てる（B強＋カットごとの黒の持ち上げ）。2026-10-18。

    python3 mv_grade.py            # /tmp/MV_noalbum_v11.mp4 → /tmp/MV_grade_B.mp4
    python3 mv_grade.py --check    # 持ち上げ量の割り当てだけ出す

淡い映画っぽい質感。黒を持ち上げ、ハイライトを黄寄り・シャドウを青寄りにし、
彩度とコントラストを落として粒子を乗せる。

⚠️ 全編に同じ持ち上げを当てると暗いカットが濁る。
このMVは輝度が 20.8（誕生日）〜177.7（海沿い）と7倍以上ひらいていて、
明るい側に合わせた数値がそのまま暗い側に効くため。
**持ち上げだけカットごとに変え、色味（中間・ハイライト・彩度・コントラスト）は
カット間で揃える。**ここまで変えるとカットが切り替わるたびに色が飛ぶ。

⚠️ カットごとに書き出して concat すると【3フレームずれた】。
-ss / -t がフレーム境界に丸められ、29カットぶん積もる。
★最大音量は215.0秒ちょうど（6450フレーム目）に置く約束なので、
trim を【フレーム番号】で指定して1パスで焼くこと。

輝度は各カットから5枚抜いて 160x90 に縮め、グレースケールの平均を取った値
（measure() で取り直せる。PIL が要るので venv の python で動かす）。
"""
import json
import subprocess
import sys

SRC = "/tmp/MV_noalbum_v11.mp4"
OUT = "/tmp/MV_grade_B.mp4"
FPS = 30

# (カット番号, イン点秒, 平均輝度)
CUTS = [
    ( 1,   0.000,   75.4),  # ▸ 金魚鉢の金魚
    ( 2,   5.200,   74.9),  # 無人の部屋・朝
    ( 3,  14.400,  103.4),  # 回想① 出会い（前半）
    ( 4,  21.100,  129.4),  # ▸ 彼女の足元
    ( 5,  26.300,  103.1),  # 回想① 出会い（後半）
    ( 6,  33.000,   42.6),  # 回想② 夏・花火の帰り道
    ( 7,  44.300,   54.3),  # ● 彼ヨリ 路地（スロー）
    ( 8,  52.600,  119.1),  # 引っ越してきた
    ( 9,  62.900,   48.6),  # 秋・はじめての料理
    (10,  77.300,   92.3),  # ● 彼女ヨリ 台所
    (11,  82.500,  177.7),  # 海沿いの2人乗り
    (12,  90.700,  154.1),  # ● 2人ヨリ 自転車
    (13,  95.900,   72.9),  # 夏祭り はぐれる
    (14, 101.600,   79.4),  # 夏祭り 手が見つかる
    (15, 109.800,   32.5),  # 花火
    (16, 117.000,   29.0),  # ▸ 川面に散る光
    (17, 120.100,  109.7),  # 知らない街
    (18, 138.700,   62.3),  # 雨・2人の正面
    (19, 148.000,  106.3),  # 雨宿り（シャツを掛ける）
    (20, 159.300,  111.2),  # ● 彼女ヨリ 雨
    (21, 164.500,   20.8),  # 誕生日
    (22, 172.700,   27.8),  # ● 彼ヨリ 笑み
    (23, 177.900,   60.5),  # 喧嘩
    (24, 187.200,   24.1),  # 喧嘩のあと
    (25, 195.400,  119.2),  # 朝の台所・コーヒー
    (26, 203.700,   68.6),  # 冬・駅の別れぎわ
    (27, 215.000,  134.5),  # ★ 最大音量 2人の正面
    (28, 230.000,   56.1),  # 立って・取って・去る
    (29, 254.000,   58.2),  # 締め 無人の部屋・夕
]

LIFT = dict(r=0.105, g=0.095, b=0.145)   # 黒の持ち上げ。これに k を掛ける
MID = dict(r=0.545, g=0.505, b=0.475)    # 中間（ハイライトを黄、シャドウを青へ）
TOP = dict(r=0.955, g=0.925, b=0.885)
SAT, CON, GRAIN = 0.76, 0.92, 7


def k_of(luma):
    """暗いほど持ち上げを弱める。輝度110以上で等倍、30以下で0.40倍。"""
    return max(0.40, min(1.0, 0.40 + 0.60 * (luma - 30) / 80))


def grade(k):
    c = ":".join(
        f"{ch}='0/{LIFT[ch] * k:.4f} 0.5/{MID[ch]} 1/{TOP[ch]}'" for ch in "rgb")
    return (f"curves={c},eq=saturation={SAT}:contrast={CON},"
            f"noise=alls={GRAIN}:allf=t")


def measure(src=SRC):
    """輝度を取り直す。CUTS の3つめの値を入れ替えるときに使う。"""
    import os
    import tempfile
    from PIL import Image, ImageStat
    tmp = tempfile.mkdtemp()
    out = []
    ends = [c[1] for c in CUTS[1:]] + [frames(src) / FPS]
    for (n, inn, _), end in zip(CUTS, ends):
        vals = []
        for i in range(5):
            t = inn + (end - inn) * (i + 0.5) / 5
            f = os.path.join(tmp, "f.png")
            subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{t:.2f}", "-i", src,
                            "-frames:v", "1", "-vf", "scale=160:90",
                            "-update", "1", "-y", f], check=True)
            vals.append(ImageStat.Stat(Image.open(f).convert("L")).mean[0])
        out.append((n, inn, sum(vals) / len(vals)))
    return out


def frames(src=SRC):
    return int(round(float(subprocess.run(
        ["ffprobe", "-v", "error", "-count_frames", "-select_streams", "v:0",
         "-show_entries", "stream=nb_read_frames", "-of", "csv=p=0", src],
        capture_output=True, text=True).stdout.strip())))


def main():
    nf = frames()
    starts = [int(round(inn * FPS)) for _, inn, _ in CUTS] + [nf]
    for i, (n, inn, luma) in enumerate(CUTS):
        print(f"{n:02d} {starts[i]:5d}f 輝度{luma:5.1f} 持ち上げ×{k_of(luma):.2f}")
    if "--check" in sys.argv:
        return
    parts = [f"[0:v]split={len(CUTS)}" + "".join(f"[s{i}]" for i in range(len(CUTS)))]
    for i, (_, _, luma) in enumerate(CUTS):
        parts.append(f"[s{i}]trim=start_frame={starts[i]}:end_frame={starts[i + 1]},"
                     f"setpts=PTS-STARTPTS,{grade(k_of(luma))}[g{i}]")
    parts.append("".join(f"[g{i}]" for i in range(len(CUTS)))
                 + f"concat=n={len(CUTS)}:v=1:a=0[out]")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", SRC,
                    "-filter_complex", ";".join(parts),
                    "-map", "[out]", "-map", "0:a",
                    "-c:v", "libx264", "-crf", "18", "-preset", "medium",
                    "-pix_fmt", "yuv420p", "-c:a", "copy", OUT], check=True)
    print(f"全{nf}フレーム → {OUT}")


if __name__ == "__main__":
    main()
