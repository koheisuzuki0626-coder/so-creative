#!/usr/bin/env python3
"""制作の前に読む知見の抜き出し（fixtures/youtube_insights.md ＋ insights_archive/）。

本人の指示（2026-11-23）：
  「分析して貯めた知見ファイルは今後の制作の参考にして」
  「（最近の3回だけでは）制作の品質に偏りがでるから全部から参照して欲しい」

記録は全部で約52万字・600回超あり、1度には読めない。そこで【件数で切らずに】
  ① 畳んである節（A・D・E・F・B ＝「# C.」より前）…… 全部
  ② 時系列のうち、作るジャンルの系統の回 …………… 全部（書庫の分も、古い順に）
  ③ 時系列の全部（他のジャンルも含む）………………… --chunks で束に分けて書き出す
     → 束ごとに読み手を立てて、今回の制作に効く点だけを拾わせる（CLAUDE.md の手順）
とする。①②は自分で全文を読む。③は全部を誰かが必ず読む形にする。

    python3 tools/insights_brief.py 採用                  # ①＋②
    python3 tools/insights_brief.py --chunks /tmp/束      # ③（束のファイルを書き出す）
    python3 tools/insights_brief.py --digest-only         # ①だけ

似た実写の素材を自分の過去の制作から引くのは tools/find_reference.py。
"""
import argparse
import re
import sys
from pathlib import Path

FIX = Path(__file__).resolve().parent.parent / "fixtures"
INSIGHTS = FIX / "youtube_insights.md"
ARCHIVE = FIX / "insights_archive"
C_HEAD = "# C. 時系列"
ENTRY_RE = re.compile(r"^## \d{4}-\d{2}-\d{2}", re.M)
CHUNK_CHARS = 60000

# ジャンルの系統。お題の書き方は時期で変わってきた（会社紹介動画→コーポレートムービー→
# 企業紹介ムービー、ミュージックビデオ→MV 公式 など）。1つの語で当てると、
# 言い方を変える前の回が丸ごと抜けて、それこそ偏る。
FAMILIES = [
    ("会社紹介", ["会社紹介", "コーポレート", "企業紹介", "企業vp", "企業 ブランディング",
                "会社プロモーション", "企業プロモーション"]),
    ("MV", ["mv", "ミュージックビデオ"]),
    ("WebCM", ["webcm"]),
    ("マニュアル", ["マニュアル", "研修", "社内報"]),
    ("展示会", ["展示会"]),
    ("採用", ["採用"]),
    ("サービス紹介", ["サービス紹介"]),
    ("アニメーション", ["アニメーション"]),
    ("SNS縦型", ["sns", "縦型"]),
]


def split(text):
    """(畳んだ節, 時系列の回のリスト) を返す。"""
    i = text.find("\n" + C_HEAD)
    if i < 0:
        return text, []
    digest, rest = text[:i], text[i:]
    return digest, _entries(rest)


def _entries(text):
    starts = [m.start() for m in ENTRY_RE.finditer(text)]
    return [text[a:b] for a, b in zip(starts, starts[1:] + [len(text)])]


def all_entries():
    """書庫（古い順）＋いまのファイルの時系列。全部。"""
    out = []
    if ARCHIVE.is_dir():
        for p in sorted(ARCHIVE.glob("*.md")):
            out.extend(_entries(p.read_text(encoding="utf-8")))
    out.extend(split(INSIGHTS.read_text(encoding="utf-8"))[1])
    return out


def topic(e):
    # 自動リサーチの回はお題の行（【自動・「〇〇」リサーチ】）だけで見る。
    # 頭400字で見ると「企業紹介ムービー」の回の本文の「採用動画」に当たった（11-23）
    m = re.search(r"【自動・「([^」]*)」", e[:400])
    return m.group(1) if m else e[:400]


def family_of(genre):
    g = (genre or "").lower()
    for name, words in FAMILIES:
        if g == name.lower() or any(w in g or g in w for w in words):
            return name, words
    return genre, [g]


def pick(entries, genre, n=None):
    """そのジャンルの系統の回を【全部】、古い順に。n は試験用にだけ残してある
    （件数で切ると、最近の回に寄って偏る。本人の指摘 11-23）。"""
    _, words = family_of(genre)
    hits = [e for e in entries if any(w in topic(e).lower() for w in words)]
    return hits if n is None else hits[-n:]


def chunks(entries, size=CHUNK_CHARS):
    """全部の回を、回の途中で切らずに size 字前後の束にする。"""
    out, cur, n = [], [], 0
    for e in entries:
        if cur and n + len(e) > size:
            out.append("".join(cur))
            cur, n = [], 0
        cur.append(e)
        n += len(e)
    if cur:
        out.append("".join(cur))
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("genre", nargs="?", default="")
    ap.add_argument("--digest-only", action="store_true")
    ap.add_argument("--chunks", metavar="DIR")
    a = ap.parse_args(argv)
    ents = all_entries()
    if a.chunks:
        d = Path(a.chunks)
        d.mkdir(parents=True, exist_ok=True)
        for old in d.glob("束_*.md"):
            old.unlink()
        cs = chunks(ents)
        for i, c in enumerate(cs, 1):
            (d / f"束_{i:02d}.md").write_text(c, encoding="utf-8")
        print(f"{len(ents)}回・{sum(map(len, ents)):,}字を {len(cs)}束に分けた → {d}")
        return
    digest = split(INSIGHTS.read_text(encoding="utf-8"))[0]
    out = [digest.rstrip()]
    if a.genre and not a.digest_only:
        name, _ = family_of(a.genre)
        hits = pick(ents, a.genre)
        out.append(f"\n\n# 時系列から「{name}」の系統の回【全部・古い順】（{len(hits)}件・"
                   f"{sum(map(len, hits)):,}字）\n")
        out.extend(hits if hits else ["（該当する回なし）\n"])
    sys.stdout.write("\n".join(out) + "\n")


if __name__ == "__main__":
    main()
