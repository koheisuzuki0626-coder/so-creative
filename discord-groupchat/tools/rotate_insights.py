#!/usr/bin/env python3
"""youtube_insights.md の、終わった月の追記ログを書庫へ送る。

なぜ要るか：1ファイルが 725KB・7,624行まで育って、人が読める大きさでなく
なった（2026-10-08）。内訳は【整理された節 58KB ＋ 追記ログ 667KB】で、
育っているのは追記ログのほう。

壊してはいけないもの：
 ・ボットは `## YYYY-MM-DD HH:MM` を【末尾に追記】する（_append_note_sync）
 ・読み返し（知見見せて）は "\\n## " で分割して【末尾n件】を見る
 → だから【今月ぶんと整理された節は、元のファイルに残す】。
 ・取り込み済み判定（_backfill_insights_sync）と見出し拾い読み
   （_insight_lines_for）は、書庫も合わせて見るようにしてある。
   ⚠️ ここを書庫を見ない形に戻すと、過去の知見が二重に取り込まれる。

使い方:
  discord-groupchat/venv/bin/python tools/rotate_insights.py --check  （何が動くか見るだけ）
  discord-groupchat/venv/bin/python tools/rotate_insights.py          （実行）
"""
import pathlib
import re
import sys
from datetime import datetime

BASE = pathlib.Path(__file__).resolve().parent.parent
LIVE = BASE / "fixtures" / "youtube_insights.md"
ARCHIVE = BASE / "fixtures" / "insights_archive"
HEAD = re.compile(r"^## (20\d\d-\d\d)-\d\d")


def split(text):
    """(整理された節, [(月, 本文), ...]) に分ける。1行も落とさない。"""
    lines = text.split("\n")
    first = next((i for i, l in enumerate(lines) if HEAD.match(l)), len(lines))
    head, blocks, cur, buf = lines[:first], [], None, []
    for l in lines[first:]:
        m = HEAD.match(l)
        if m:
            if cur is not None:
                blocks.append((cur, buf))
            cur, buf = m.group(1), [l]
        else:
            buf.append(l)
    if cur is not None:
        blocks.append((cur, buf))
    return head, blocks


def main() -> int:
    check = "--check" in sys.argv
    if not LIVE.exists():
        print("youtube_insights.md が無い")
        return 1
    text = LIVE.read_text(encoding="utf-8")
    head, blocks = split(text)
    now = datetime.now().strftime("%Y-%m")
    old = sorted({m for m, _ in blocks if m < now})
    if not old:
        print(f"✅ 送る月は無い（今月 {now} ぶんだけ残っている）")
        return 0

    print(f"元: {len(text.split(chr(10)))}行 / {len(text.encode()) / 1024:.0f}KB")
    moved = 0
    for mon in old:
        body = [l for m, b in blocks if m == mon for l in b]
        moved += len(body)
        dest = ARCHIVE / f"{mon}.md"
        out = f"# YouTube知見 {mon}（書庫）\n\n" + "\n".join(body).strip() + "\n"
        print(f"  {mon} → {dest.relative_to(BASE)}  {len(body)}行")
        if not check:
            ARCHIVE.mkdir(parents=True, exist_ok=True)
            dest.write_text(out, encoding="utf-8")

    keep = [l for m, b in blocks if m >= now for l in b]
    note = (f"\n> 📦 {old[0]}〜{old[-1]} のログは `insights_archive/` に移した"
            f"（{moved}行）。取り込み済み判定も見出し拾い読みも書庫を見るので、"
            f"二重に入ることはない。\n")
    new = "\n".join(head).rstrip() + "\n" + note + "\n" + "\n".join(keep).strip() + "\n"
    print(f"残り: {len(new.split(chr(10)))}行 / {len(new.encode()) / 1024:.0f}KB")
    # 1行も落としていないこと
    before = sum(1 for l in text.split("\n") if l.strip())
    after = sum(1 for l in new.split("\n") if l.strip())
    arch = moved - sum(1 for m, b in blocks if m in old for l in b if not l.strip())
    print(f"中身のある行: 元 {before} ／ 残り {after} ＋ 書庫 {arch}"
          f" = {after + arch}  {'✅一致' if before <= after + arch else '⚠️ 落ちている'}")
    if not check:
        LIVE.write_text(new, encoding="utf-8")
        print("書き換えた")
    else:
        print("（--check なので書き換えていない）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
