#!/usr/bin/env python3
"""MVフル尺（264秒）を素材21本から組む。

素材は Drive にある生成元（/tmp/mv_src）。合計160秒を264秒へ伸ばすので
各カットをスローにする。曲の区切りに合わせた重みを手で与えてある。

    python3 mv_full.py            # 組む
    python3 mv_full.py --check    # 尺の割り当てだけ表示
"""
import subprocess, sys, os, json

SRC = "/tmp/mv_src"
SONG = "/Users/suzukikohei/.claude/uploads/91759498-2c22-50c7-811e-7648d73f6600/d9205b59-___.mp3"
OUT = "/tmp/MV_full_v1.mp4"
TOTAL = 264.0
PEAK_AT = 215.0   # 曲の最大音量

# (ファイル, 表示名, 重み) ※重みは「だいたい何秒にしたいか」。最後に正規化する
CUTS = [
    ("MV_00_無人の部屋_朝.mp4",        "無人の部屋・朝",        14),
    ("MV_10_手_アルバムを開く.mp4",     "手① アルバムを開く",    13),
    ("MV_02_出会い_ホーム_2人.mp4",     "回想① 出会い",          16),
    ("MV_11_手_ページをめくる.mp4",     "手② ページをめくる",    9),
    ("MV_03_夏_花火の帰り道.mp4",       "回想② 夏・花火の帰り道", 16),
    ("MV_04_秋_はじめての料理.mp4",     "秋・はじめての料理",     14),
    ("MV_14_海沿いの2人乗り.mp4",       "海沿いの2人乗り",        8),
    ("MV_15_夏祭り_はぐれる.mp4",       "夏祭り はぐれる",        5.5),
    ("MV_16_夏祭り_手が見つかる.mp4",   "夏祭り 手が見つかる",    8),
    ("MV_17_花火.mp4",                  "花火",                   10),
    ("MV_18_知らない街_1カット.mp4",    "知らない街",             18),
    ("MV_19_雨宿り.mp4",                "雨宿り",                 13),
    ("MV_20_引っ越し.mp4",              "引っ越し",               10),
    ("MV_05_冬_駅の別れぎわ.mp4",       "冬・駅の別れぎわ",       11),
    ("MV_21_誕生日.mp4",                "誕生日",                 8),
    ("MV_06_喧嘩のあと.mp4",            "喧嘩のあと",             8),
    ("MV_07_朝の台所_コーヒー.mp4",     "朝の台所・コーヒー",     8),
    ("MV_12_手_最後の1枚の前で止まる.mp4","手③ 最後の1枚の前で",  9),
    ("MV_08_2人の正面_最大音量.mp4",    "★最大音量 2人の正面",   15),   # 等速で固定
    ("MV_13_手_閉じて立ち去る.mp4",     "手④ 閉じて立ち去る",    13),
    ("MV_09_無人の部屋_夕方.mp4",       "無人の部屋・夕方",       14),
]
FIXED = "MV_08_2人の正面_最大音量.mp4"   # ここだけ等速（曲の山と合わせる）


def dur(path):
    out = subprocess.run(["ffprobe","-v","error","-show_entries","format=duration",
                          "-of","default=nw=1:nk=1", path], capture_output=True, text=True)
    return float(out.stdout.strip())


def plan():
    rows = []
    for fn, name, w in CUTS:
        p = os.path.join(SRC, fn)
        rows.append({"file": p, "name": name, "w": float(w), "src": dur(p)})
    # ★最大音量は曲の山なので PEAK_AT 秒ちょうどから等速で置く。
    # そのために前半と後半を別々に正規化する（片方だけ合わせると山がずれる）。
    fi = [i for i, r in enumerate(rows)
          if os.path.basename(r["file"]) == FIXED][0]
    peak = rows[fi]
    before, after = rows[:fi], rows[fi + 1:]
    s_before = PEAK_AT / sum(r["w"] for r in before)
    s_after = (TOTAL - PEAK_AT - peak["src"]) / sum(r["w"] for r in after)
    t = 0.0
    for r in rows:
        if r is peak:
            r["target"] = r["src"]
        else:
            r["target"] = r["w"] * (s_before if r in before else s_after)
        r["speed"] = r["target"] / r["src"]
        r["in"] = t
        t += r["target"]
    return rows, t


def main():
    rows, total = plan()
    for r in rows:
        print(f"{r['in']:7.1f} {r['target']:6.2f}秒  ×{r['speed']:.2f}  {r['name']}")
    print(f"合計 {total:.2f}秒 / 曲 {TOTAL}秒")
    if "--check" in sys.argv:
        return

    ins, filt, labs = [], [], []
    for i, r in enumerate(rows):
        ins += ["-i", r["file"]]
        filt.append(
            f"[{i}:v]setpts={r['speed']:.6f}*PTS,fps=30,"
            f"scale=1920:1080:force_original_aspect_ratio=increase,"
            f"crop=1920:1080,setsar=1[v{i}]")
        labs.append(f"[v{i}]")
    filt.append("".join(labs) + f"concat=n={len(rows)}:v=1:a=0[vv]")
    cmd = (["ffmpeg","-v","error","-y"] + ins + ["-i", SONG,
           "-filter_complex", ";".join(filt),
           "-map","[vv]","-map",f"{len(rows)}:a",
           "-c:v","libx264","-crf","18","-preset","medium","-pix_fmt","yuv420p",
           "-c:a","aac","-b:a","192k","-shortest", OUT])
    print("組んでいる…")
    subprocess.run(cmd, check=True)
    print("できた:", OUT, f"{dur(OUT):.2f}秒")


if __name__ == "__main__":
    main()
