#!/usr/bin/env python3
"""MVフル尺 v3（264秒／32カット）。

インサートと顔のヨリは静止画。ゆっくりズームをかけて映像にする（生成しない）。
★最大音量は PEAK_AT 秒ちょうどから等速で置き、前後を別々に正規化する。

    python3 mv_v3.py --check   # 割り当てだけ
    python3 mv_v3.py           # 組む
"""
import subprocess, sys, os

SRC = "/tmp/mv_src"; INS = "/tmp/ins"
SONG = "/Users/suzukikohei/.claude/uploads/91759498-2c22-50c7-811e-7648d73f6600/d9205b59-___.mp3"
OUT = "/tmp/MV_full_v3.mp4"
TOTAL = 264.0
PEAK_AT = 215.0
PEAK = "MV_08_2人の正面_最大音量.mp4"

# kind: v=動画 / s=静止画（ズーム） / p=最大音量
CUTS = [
 ("v", "MV_00_無人の部屋_朝.mp4",            "無人の部屋・朝",        14),
 ("s", "01_金魚鉢の金魚.png",                 "▸ 金魚鉢の金魚",         3.0),
 ("v", "MV_10_手_アルバムを開く.mp4",         "手① アルバムを開く",     13),
 ("v", "MV_02_出会い_ホーム_2人.mp4",         "回想① 出会い",           16),
 ("s", "02_彼女の足元.png",                   "▸ 彼女の足元",           2.5),
 ("v", "MV_11_手_ページをめくる.mp4",         "手② ページをめくる",     9),
 ("v", "MV_03_夏_花火の帰り道.mp4",           "回想② 夏・花火の帰り道", 16),
 ("s", "N5_彼ヨリ_2人で歩く.png",             "● 彼ヨリ 路地",          2.5),
 ("v", "MV_22_引っ越してきた.mp4",            "引っ越してきた",         10),
 ("v", "MV_04_秋_はじめての料理.mp4",         "秋・はじめての料理",     14),
 ("s", "10_彼女ヨリ_台所.png",                "● 彼女ヨリ 台所",        2.5),
 ("v", "MV_14_海沿いの2人乗り.mp4",           "海沿いの2人乗り",        8),
 ("s", "N6_2人ヨリ_自転車_正面.png",          "● 2人ヨリ 自転車",       2.5),
 ("v", "MV_15_夏祭り_はぐれる.mp4",           "夏祭り はぐれる",        5.5),
 ("v", "MV_16_夏祭り_手が見つかる.mp4",       "夏祭り 手が見つかる",    8),
 ("v", "MV_17_花火.mp4",                      "花火",                   7),
 ("s", "05_川面に散る光.png",                 "▸ 川面に散る光",         5.5),
 ("v", "MV_18_知らない街_1カット.mp4",        "知らない街",             18),
 ("s", "06_軒先の雨だれ.png",                 "▸ 軒先の雨だれ",         3.0),
 ("v", "MV_23_雨宿り_シャツ.mp4",             "雨宿り（シャツを掛ける）", 10),
 ("s", "R2_彼女ヨリ_シャツ.png",              "● 彼女ヨリ 雨",          2.5),
 ("v", "MV_21_誕生日.mp4",                    "誕生日",                 8),
 ("s", "R3_彼ヨリ_笑い.png",                  "● 彼ヨリ 笑い",          2.5),
 ("v", "MV_24_喧嘩.mp4",                      "喧嘩",                   9),
 ("v", "MV_06_喧嘩のあと.mp4",                "喧嘩のあと",             8),
 ("v", "MV_07_朝の台所_コーヒー.mp4",         "朝の台所・コーヒー",     8),
 ("v", "MV_25_冬の別れ_彼が去る.mp4",         "冬・駅の別れぎわ",       11),
 ("v", "MV_12_手_最後の1枚の前で止まる.mp4",  "手③ 最後の1枚の前で",    9),
 ("p", PEAK,                                  "★ 最大音量 2人の正面",   0),
 ("v", "MV_13b_手_閉じるだけ.mp4",            "手④ 閉じる",             6),
 ("s", "09_閉じた表紙.png",                   "▸ 閉じた表紙",           4.5),
 ("v", "MV_26_アルバムを取って去る.mp4",      "アルバムを取って去る",   14),
 ("s", "Z_無人の部屋_夕方.png",               "▸ 無人の部屋・夕方",     6.0),
]


def dur(p):
    o = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                        "-of", "default=nw=1:nk=1", p], capture_output=True, text=True)
    return float(o.stdout.strip())


def path(kind, name):
    return os.path.join(INS if kind == "s" else SRC, name)


def plan():
    pi = [i for i, c in enumerate(CUTS) if c[0] == "p"][0]
    psrc = dur(path("v", CUTS[pi][1]))
    fb = sum(c[3] for c in CUTS[:pi] if c[0] == "s")
    fa = sum(c[3] for c in CUTS[pi + 1:] if c[0] == "s")
    wb = sum(c[3] for c in CUTS[:pi] if c[0] == "v")
    wa = sum(c[3] for c in CUTS[pi + 1:] if c[0] == "v")
    sb = (PEAK_AT - fb) / wb
    sa = (TOTAL - PEAK_AT - psrc - fa) / wa
    rows, t = [], 0.0
    for i, (k, name, label, w) in enumerate(CUTS):
        if k == "p":
            tgt, sp = psrc, 1.0
        elif k == "s":
            tgt, sp = float(w), None
        else:
            tgt = w * (sb if i < pi else sa)
            sp = tgt / dur(path(k, name))
        rows.append(dict(kind=k, src=path(k, name), label=label,
                         inn=t, dur=tgt, speed=sp))
        t += tgt
    return rows, t


def main():
    rows, total = plan()
    for i, r in enumerate(rows, 1):
        m = int(r["inn"] // 60); s = r["inn"] - m * 60
        sp = f'×{r["speed"]:.2f}' if r["speed"] else "静止画"
        print(f'{i:02d} {m}:{s:04.1f} {r["dur"]:5.1f}秒 {sp:>7} {r["label"]}')
    print(f"合計 {total:.2f}秒 / 曲 {TOTAL}秒")
    if "--check" in sys.argv:
        return

    ins, filt, labs = [], [], []
    for i, r in enumerate(rows):
        if r["kind"] == "s":
            # ⚠️ zoompan は入力1フレームにつき d フレームを吐く。
            # -loop で何枚も入れると d 倍に伸びる（実際に90倍になった）。
            # 画像は1フレームだけ渡し、尺は d だけで決める。
            ins += ["-i", r["src"]]
            n = int(r["dur"] * 30)
            filt.append(
                f'[{i}:v]scale=3840:-1,zoompan=z=\'min(1.0+0.05*on/{n},1.05)\':'
                f'd={n}:s=1920x1080:fps=30,setsar=1,trim=duration={r["dur"]:.3f},'
                f'setpts=PTS-STARTPTS[v{i}]')
        else:
            ins += ["-i", r["src"]]
            filt.append(
                f'[{i}:v]setpts={r["speed"]:.6f}*PTS,fps=30,'
                f'scale=1920:1080:force_original_aspect_ratio=increase,'
                f'crop=1920:1080,setsar=1[v{i}]')
        labs.append(f"[v{i}]")
    filt.append("".join(labs) + f"concat=n={len(rows)}:v=1:a=0[vv]")
    cmd = (["ffmpeg", "-v", "error", "-y"] + ins + ["-i", SONG,
           "-filter_complex", ";".join(filt),
           "-map", "[vv]", "-map", f"{len(rows)}:a",
           "-c:v", "libx264", "-crf", "18", "-preset", "medium", "-pix_fmt", "yuv420p",
           "-c:a", "aac", "-b:a", "192k", "-shortest", OUT])
    print("組んでいる…")
    subprocess.run(cmd, check=True)
    print("できた:", OUT, f"{dur(OUT):.2f}秒")


if __name__ == "__main__":
    main()
