#!/usr/bin/env python3
"""制作の前に読む知見の抜き出し（fixtures/youtube_insights.md から）。

本人の指示（2026-11-23）：「分析して貯めた知見ファイルは今後の制作の参考にして」。

知見ファイルは 800KB を超えていて、毎回全部は読めない。そこで
  ① 畳んである節（A・D・E・F・B ＝「# C.」より前）は全部
  ② 時系列（C）からは、そのジャンルの回を新しい順に N 件
を出す。①が型の本体、②は最近の実例。

    python3 tools/insights_brief.py 採用          # 採用動画を作る前に
    python3 tools/insights_brief.py WebCM -n 5
    python3 tools/insights_brief.py --digest-only  # ①だけ

似た実写の素材を自分の過去の制作から引くのは tools/find_reference.py。
"""
import argparse
import re
import sys
from pathlib import Path

INSIGHTS = Path(__file__).resolve().parent.parent / "fixtures" / "youtube_insights.md"
C_HEAD = "# C. 時系列"
ENTRY_RE = re.compile(r"^## \d{4}-\d{2}-\d{2}", re.M)


def split(text):
    """(畳んだ節, 時系列の回のリスト) を返す。"""
    i = text.find("\n" + C_HEAD)
    if i < 0:
        return text, []
    digest, rest = text[:i], text[i:]
    starts = [m.start() for m in ENTRY_RE.finditer(rest)]
    entries = [rest[a:b] for a, b in zip(starts, starts[1:] + [len(rest)])]
    return digest, entries


def pick(entries, genre, n):
    """そのジャンルの回を新しい順に n 件。判定は回の頭（お題が書かれる所）だけで見る。
    本文の途中にジャンル名が出ただけの回を拾うと、関係ない回で埋まる。"""
    g = genre.lower()

    def topic(e):
        # 自動リサーチの回はお題の行（【自動・「〇〇」リサーチ】）だけで見る。
        # 頭400字で見ると「企業紹介ムービー」の回の本文の「採用動画」に当たった（11-23）
        m = re.search(r"【自動・「([^」]*)」", e[:400])
        return m.group(1) if m else e[:400]

    hits = [e for e in entries if g in topic(e).lower()]
    return hits[-n:][::-1]


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("genre", nargs="?", default="")
    ap.add_argument("-n", type=int, default=3)
    ap.add_argument("--digest-only", action="store_true")
    a = ap.parse_args(argv)
    digest, entries = split(INSIGHTS.read_text(encoding="utf-8"))
    out = [digest.rstrip()]
    if a.genre and not a.digest_only:
        hits = pick(entries, a.genre, a.n)
        out.append(f"\n\n# 時系列から「{a.genre}」の最近の回（{len(hits)}件）\n")
        out.extend(hits if hits else ["（該当する回なし）\n"])
    sys.stdout.write("\n".join(out) + "\n")


if __name__ == "__main__":
    main()
