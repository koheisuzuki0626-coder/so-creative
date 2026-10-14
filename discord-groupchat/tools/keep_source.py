#!/usr/bin/env python3
"""生成した【元素材】を残す。完成品だけ残して元が消える事故を止めるため。

    python3 tools/keep_source.py 04_c1_kling.mp4 --案件 サンプル映像 --カット "04 C1 真俯瞰"
    python3 tools/keep_source.py *.mp4 --案件 サンプル映像        # まとめて
    python3 tools/keep_source.py --台帳                            # 台帳を見るだけ

**なぜ要るか（2026-10-15）**
餃子CM（04）の1カットが「AIっぽい」と分かったのに、直せなかった。
`build.py` は完成品を完全に再現できるのに、その入力である生成素材
（`04_c1_kling.mp4` 等）がどこにも残っていなかった。完成mp4はテロップが
焼き込まれているので切り直しもできず、**生成し直す以外に道がない**状態に
なった。ボットの生成物は一時フォルダに置かれるだけで、Higgsfieldのweb UIで
作った分は手元のダウンロードに埋もれて消える。

**置き場を Drive にした理由**
リポジトリは GitHub Pages が配信しているので、8秒の素材を溜めると
clone が重くなる（完成品15秒で3.7MB、素材はその数倍×カット数×本数）。
Drive には既に経路がある（`tools/drive_put.py`・2026-10-12 接続確認済み）。
**台帳だけリポジトリに置く**ので、何がどこにあるかは git で追える。
"""
import argparse
import datetime
import pathlib
import re
import subprocess
import sys

BASE = pathlib.Path(__file__).resolve().parent.parent.parent
LEDGER = BASE / "成果物" / "サンプル映像" / "素材元_台帳.md"
HEAD = """# 生成した元素材の台帳

実体は Google Drive の `so-creative/動画/<案件>/_生成元/`。
ここには**何がどこにあるか**だけを置く（リポジトリを重くしないため）。

⚠️ 完成品だけ残して元素材を捨てないこと。2026-10-15、餃子CMの1カットを
直そうとして元が無く、生成し直す以外に道が無くなった。

| 日付 | 案件 | カット | ファイル | 尺 | 解像度 | サイズ | Drive |
|---|---|---|---|---|---|---|---|
"""


def probe(p):
    """尺・解像度を測る。測れなければ空で返す（止めない）。"""
    def ff(args):
        try:
            return subprocess.run(["ffprobe", "-v", "error", *args, str(p)],
                                  capture_output=True, text=True, timeout=30).stdout.strip()
        except Exception:
            return ""
    d = ff(["-show_entries", "format=duration", "-of", "csv=p=0"])
    wh = ff(["-select_streams", "v:0", "-show_entries", "stream=width,height",
             "-of", "csv=p=0:s=x"])
    try:
        d = f"{float(d):.1f}秒"
    except Exception:
        d = "—"
    return d, (wh or "—")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="*")
    ap.add_argument("--案件", default="サンプル映像")
    ap.add_argument("--カット", default="")
    ap.add_argument("--台帳", action="store_true")
    a = ap.parse_args()

    if a.台帳 or not a.files:
        print(LEDGER.read_text(encoding="utf-8") if LEDGER.exists()
              else "台帳はまだ空です。")
        return 0

    rows = []
    for f in a.files:
        p = pathlib.Path(f).expanduser().resolve()
        if not p.exists():
            print(f"⚠️ 見つかりません: {f}")
            continue
        d, wh = probe(p)
        mb = f"{p.stat().st_size / 1e6:.1f}MB"
        print(f"→ Drive へ: {p.name}（{d} / {wh} / {mb}）")
        r = subprocess.run([sys.executable, str(pathlib.Path(__file__).parent / "drive_put.py"),
                            "--project", f"{a.案件}_生成元", str(p)],
                           capture_output=True, text=True)
        out = (r.stdout or r.stderr).strip()
        print(out[:400])
        if r.returncode != 0:
            print("⚠️ Drive に入らなかった。ファイルは消さないこと。")
            continue
        m = re.search(r"https://drive\.google\.com/\S+", out)
        link = f"[開く]({m.group(0)})" if m else "—"
        rows.append(f"| {datetime.date.today()} | {a.案件} | {a.カット or '—'} "
                    f"| `{p.name}` | {d} | {wh} | {mb} | {link} |")

    if rows:
        LEDGER.parent.mkdir(parents=True, exist_ok=True)
        cur = LEDGER.read_text(encoding="utf-8") if LEDGER.exists() else HEAD
        LEDGER.write_text(cur.rstrip() + "\n" + "\n".join(rows) + "\n", encoding="utf-8")
        print(f"\n台帳に {len(rows)}件 書いた: {LEDGER.relative_to(BASE)}")
        print("⚠️ 台帳をコミットすること（実体はDrive、所在はgitで追う）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
