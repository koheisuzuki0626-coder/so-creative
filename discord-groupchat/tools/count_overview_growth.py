#!/usr/bin/env python3
"""レポートの第1節（概観）が、渡していないデータで「伸びている」と書いていないかを数える。

2026-10-01（C2）に足した。概観の材料は【未視聴の候補の題名とチャンネル名だけ】で、
公開日も時系列も渡していない。それでも成長を論じていたら、埋めているということ。

基準値（C2 を入れる前・2026-09-30 のレポート）を取ってから C2 を入れ、
次の巡のレポートで同じ数え方をして減ったかを見る。
数えずに次の修正を積むと、効かない守りが増えるだけになる。

使い方:
  python3 tools/count_overview_growth.py            # 全日付
  python3 tools/count_overview_growth.py 2026-09-30 # その日だけ
"""
import re
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
INSIGHTS = Path(__file__).resolve().parent.parent / "insights"

# 時間の変化を主張する語だけ。「人気」「注目」のような強さの語は入れない
# （渡した題名からでも言えてしまうので、埋めた証拠にならない）。
GROWTH = re.compile(
    "伸び|伸長|増加|増え|急増|拡大傾向|高まっ|高まり|主流|定番化|"
    "トレンド化|流行|台頭|加速|好調|突出|増やす傾向|近年|最近の傾向")

# 概観の見出し（C2 の前後で変わる）
HEAD = re.compile(r"^## (?:トレンド概観|検索結果一覧の傾向.*)$")
NEXT = re.compile(r"^## ")


def overview_of(path):
    """そのレポートの概観の本文だけを返す。無ければ None。"""
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    out, inside = [], False
    for ln in lines:
        if HEAD.match(ln):
            inside = True
            continue
        if inside and NEXT.match(ln):
            break
        if inside:
            out.append(ln)
    return "\n".join(out).strip() if inside else None


def main():
    day = sys.argv[1] if len(sys.argv) > 1 else None
    files = sorted(p for p in INSIGHTS.glob("*.md")
                   if not day or p.name.startswith(day))
    hit, total = 0, 0
    for p in files:
        ov = overview_of(p)
        if ov is None:
            continue
        total += 1
        words = sorted(set(GROWTH.findall(ov)))
        if words:
            hit += 1
        print(f"{'⚠️' if words else '  '} {p.name}"
              + (f"  → {'・'.join(words)}" if words else ""))
    if total:
        print(f"\n概観のあるレポート {total}本 / 成長を論じているもの {hit}本"
              f"（{100 * hit / total:.0f}%）")
    else:
        print("概観のあるレポートが見つかりません")


if __name__ == "__main__":
    main()
