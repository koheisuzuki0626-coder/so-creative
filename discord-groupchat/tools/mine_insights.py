#!/usr/bin/env python3
"""insights/ に溜まった分析文を【横断で集計】する。動画は見ない（API消費ゼロ）。

1本ずつ読んで終わっていた分析を、ジャンル単位の数字にする。
出るもの：カット数・1カット秒・テロップの字数と位置・音の構成・
そして【AIで作れないと判定された要素】の頻度。

  ./venv/bin/python tools/mine_insights.py          # 画面に出す
  ./venv/bin/python tools/mine_insights.py --write  # 成果物へ md を書く

⚠️ 否定を読むこと。「ナレーションはなく」を素朴に数えると
   ナレーション有りに化ける（実際この文面が多数派）。
"""
import argparse
import collections
import pathlib
import re
import statistics
import sys

BASE = pathlib.Path(__file__).resolve().parent.parent
INS = BASE / "insights"
OUT = BASE.parent / "成果物" / "YouTubeリサーチ提案資料" / "ジャンル別の型.md"

GENRE_FIX = {"会社紹介動画 制作事例": "会社紹介・コーポレート",
             "コーポレートムービー 制作事例": "会社紹介・コーポレート",
             "企業VP": "会社紹介・コーポレート",
             "企業紹介ムービー 制作実績": "会社紹介・コーポレート",
             "MV 制作実績": "MV", "MV 公式": "MV", "ミュージックビデオ": "MV",
             "WebCM 制作事例": "WebCM", "webcm": "WebCM"}
# 企業映像でないもの（急上昇・題材の取り違え）は集計から外す
SKIP = re.compile(r"急上昇|トップ100|^(今|試し|実行|他の動画ない|YouTube)$|AI動画")

# ② カット割り：「22カット・数えた」。
# 「1カットの平均秒数は」の 1 を拾わないよう、直後が「の平均」なら捨てる。
CUTS = re.compile(r"(\d{1,3})\s*カット(?!の平均)")
AVG = re.compile(r"平均[^0-9。\n]{0,8}?([0-9]+(?:\.[0-9]+)?)\s*秒")
# ③ テロップ：「2〜15文字程度」「8〜12文字」「15字」
TELOP_RANGE = re.compile(r"([0-9]{1,2})\s*[〜～-]\s*([0-9]{1,2})\s*[文]?字")
TELOP_ONE = re.compile(r"([0-9]{1,2})\s*[文]?字(?![〜～-])")
POSITIONS = ["画面上部", "上部", "画面下部", "下部", "画面中央", "中央",
             "全面", "左上", "右上", "左下", "右下"]

# ④ 音：否定を先に見る。
# ⚠️ 窓に「、」を含めてはいけない。含めると
#    「BGMが流れており、ナレーションはなく」で【BGMが無い】と判定される
#    （最初の実装がこれで、BGMありが48%という嘘の数字が出た）。
_ABSENT = ("ありません|ございません|入っていません|聞こえません|使われていません|"
           "ない|なく|無い|無く|なし|無し|流れていません|не")
SOUND_KEYS = {
    "BGM":        (r"BGM|劇伴|音楽",   r"(BGM|劇伴|音楽)[はもが]?\s*(?:" + _ABSENT + r")"),
    "ナレーション": (r"ナレーション|語り", r"(ナレーション|語り)[はもが]?\s*(?:" + _ABSENT + r")"),
    "環境音":      (r"環境音|生活音|アンビ", r"(環境音|生活音)[はもが]?\s*(?:" + _ABSENT + r")"),
    "効果音":      (r"効果音|SE\b",    r"(効果音|SE)[はもが]?\s*(?:" + _ABSENT + r")"),
    "セリフ":      (r"セリフ|台詞|会話",  r"(セリフ|台詞|会話)[はもが]?\s*(?:" + _ABSENT + r")"),
}
# ⑧ AIで再現できるか の3段
TIERS = ["そのまま作れる", "工夫すれば作れる", "作れない"]
# 「作れない」の中身を束ねる語（実物を見て決めた）
CANT = {
    "実在の人物・タレントの顔": r"実在|有名|タレント|俳優|芸能|本人の顔|著名",
    "ロゴ・商標": r"ロゴ|商標|企業名の正確|ブランドマーク",
    "画面内の文字・テロップ": r"文字|テキスト|表記|注意書|字幕|テロップ",
    "手・指の動き": r"手の|指の|手元の細か|手指",
    "顔の一貫性": r"一貫性|同一人物|同じ顔|キャラクターの維持",
    "口の動き・リップシンク": r"口の動き|リップ|口元",
    "商品の正確な再現": r"パッケージ|商品の形状|製品の正確|実在の商品",
    "物理的に正しい動き": r"物理|重力|液体|流体|煙|水の",
    "長尺の連続性": r"長尺|長い尺|連続した|つながり",
}


def genre_of(text, fallback="?"):
    m = re.search(r"^# YouTube[「【]?(.*?)[」】]?\s*リサーチ", text, re.M)
    g = (m.group(1).strip() if m else fallback) or fallback
    return GENRE_FIX.get(g, g)


def section(block, head, nxt):
    """①〜⑨ の1節を取り出す。見つからなければ空。"""
    i = block.find(head)
    if i < 0:
        return ""
    ends = [block.find(n, i + 1) for n in nxt]
    ends = [e for e in ends if e > i]
    return block[i:min(ends)] if ends else block[i:i + 600]


def collect():
    data = collections.defaultdict(lambda: {
        "n": 0, "cuts": [], "avg": [], "telop": [], "pos": collections.Counter(),
        "sound": collections.defaultdict(lambda: [0, 0]),   # [あり, 判定できた数]
        "cant": collections.Counter(), "cant_raw": [],
    })
    for f in sorted(INS.glob("*.md")):
        t = f.read_text(encoding="utf-8", errors="replace")
        g = genre_of(t)
        if SKIP.search(g):
            continue
        for blk in t.split("\n## ")[1:]:
            if "②" not in blk and "⑧" not in blk:
                continue
            d = data[g]
            d["n"] += 1
            # ② カット割り
            s2 = section(blk, "② カット", ["③", "\n④"])
            for m in CUTS.finditer(s2):
                v = int(m.group(1))
                if 3 <= v <= 300:
                    d["cuts"].append(v)
                    break                      # 1本につき1つ（最初の宣言を採る）
            a = AVG.search(s2)
            if a and 0.3 <= float(a.group(1)) <= 30:
                d["avg"].append(float(a.group(1)))
            # ③ テロップ
            s3 = section(blk, "③ テロップ", ["\n④", "\n⑤"])
            r = TELOP_RANGE.search(s3)
            if r:
                lo, hi = int(r.group(1)), int(r.group(2))
                if 1 <= lo <= hi <= 40:
                    d["telop"].append((lo + hi) / 2)
            else:
                o = TELOP_ONE.search(s3)
                if o and 1 <= int(o.group(1)) <= 40:
                    d["telop"].append(float(o.group(1)))
            for p in POSITIONS:
                if p in s3:
                    d["pos"][p] += 1
                    break
            # ④ 音（否定を先に見る）
            s4 = section(blk, "④ 音", ["\n⑤", "\n⑥"])
            for key, (yes, neg) in SOUND_KEYS.items():
                if not re.search(yes, s4):
                    continue
                d["sound"][key][1] += 1
                if not re.search(neg, s4):
                    d["sound"][key][0] += 1
            # ⑧ 作れない
            s8 = section(blk, "⑧", ["\n⑨"])
            i = s8.find("作れない")
            if i >= 0:
                tail = s8[i:i + 400]
                d["cant_raw"].append(tail)
                for label, pat in CANT.items():
                    if re.search(pat, tail):
                        d["cant"][label] += 1
    return data


def med(v):
    return f"{statistics.median(v):.1f}" if v else "—"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args()
    data = collect()
    rows = sorted(data.items(), key=lambda kv: -kv[1]["n"])
    rows = [(g, d) for g, d in rows if d["n"] >= 10]

    L = []
    L.append("# ジャンル別の型（既存の分析文を横断集計）\n")
    L.append(f"`insights/` の {len(list(INS.glob('*.md')))} レポートから機械的に集計。"
             "動画は見ていない（API消費ゼロ）。\n")
    L.append("数字は**中央値**。1本の分析につき1つだけ採る。\n")

    L.append("\n## カット数と1カットの長さ\n")
    L.append("| ジャンル | 本数 | カット数 | 1カット秒 | 取れた件数 |")
    L.append("|---|---:|---:|---:|---|")
    for g, d in rows:
        L.append(f"| {g} | {d['n']} | {med(d['cuts'])} | {med(d['avg'])} "
                 f"| {len(d['cuts'])}/{len(d['avg'])} |")

    L.append("\n## テロップ\n")
    L.append("| ジャンル | 1枚の字数 | 位置（最多） | 取れた件数 |")
    L.append("|---|---:|---|---|")
    for g, d in rows:
        p = d["pos"].most_common(1)
        L.append(f"| {g} | {med(d['telop'])} | "
                 f"{p[0][0] + f'（{p[0][1]}本）' if p else '—'} | {len(d['telop'])} |")

    L.append("\n## 音の構成（その要素に触れた分析のうち、あった割合）\n")
    keys = list(SOUND_KEYS)
    L.append("| ジャンル | " + " | ".join(keys) + " |")
    L.append("|---" * (len(keys) + 1) + "|")
    for g, d in rows:
        cells = []
        for k in keys:
            yes, tot = d["sound"][k]
            cells.append(f"{yes*100//tot}%（{tot}本）" if tot else "—")
        L.append(f"| {g} | " + " | ".join(cells) + " |")

    L.append("\n## AIで「作れない」と判定された要素\n")
    L.append("受けてはいけない案件・先に断っておくべき条件が、ここに出る。\n")
    allcant = collections.Counter()
    for g, d in rows:
        allcant.update(d["cant"])
    L.append("| 要素 | 件数 | 全体に占める割合 |")
    L.append("|---|---:|---:|")
    tot = sum(len(d["cant_raw"]) for g, d in rows) or 1
    for label, c in allcant.most_common():
        L.append(f"| {label} | {c} | {c*100//tot}% |")
    L.append(f"\n（「作れない」の記述がある分析 {tot} 本が母数）\n")

    L.append("\n## ジャンル別の「作れない」上位3つ\n")
    for g, d in rows:
        top = "／".join(f"{k}({v})" for k, v in d["cant"].most_common(3)) or "—"
        L.append(f"- **{g}** … {top}")

    text = "\n".join(L) + "\n"
    print(text)
    if args.write:
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text(text, encoding="utf-8")
        print(f"書き出し: {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
