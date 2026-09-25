#!/usr/bin/env python3
"""出来上がったファイルを Google Drive へ入れる。

    python3 tools/drive_put.py 動画.mp4 [もう1本.mp4 ...]
    python3 tools/drive_put.py --project 〇〇工業_会社紹介動画 完成.mp4
    python3 tools/drive_put.py --folder <フォルダID> 資料.pdf

置き場は **アプリが作った `so-creative`**（マイドライブ直下）。その下を
`動画` / `画像` → 案件ごとに仕切る。案件名は 成果物/<案件>/ のパスから
拾うので、成果物の中のファイルなら --project は要らない。
手で作ったフォルダに入れたい時だけ --folder で指定する（ただし
drive.file では書き込めないので、アプリが作ったフォルダに限る）。

認証とアップロードの実体はボットと同じものを使う（鍵の持ち方を二重に
しないため）。繋がっていなければ、その理由に合った案内が出る。

権限は drive.file。スコープを変えた直後は `tools/drive_auth.py` を
1回流すまで上がらない。手順は 成果物/開業準備/Google Driveの設定.md。
"""
import os
import pathlib
import sys

BASE = pathlib.Path(__file__).resolve().parent.parent

# .env を先に読む（このスクリプトは source 無しで叩けるようにしたい）
env = BASE / ".env"
if env.exists():
    for line in env.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

sys.path.insert(0, str(BASE))
os.chdir(BASE)
import ai_group_chat as bot  # noqa: E402


def main(argv):
    folder = project = None
    args = list(argv)
    while args and args[0] in ("--folder", "--project"):
        if len(args) < 2:
            print(f"⚠️ {args[0]} のあとに値が要ります")
            return 2
        if args[0] == "--folder":
            folder = args[1]
        else:
            project = args[1]
        args = args[2:]
    if not args:
        print(__doc__)
        return 2

    paths = []
    for a in args:
        p = pathlib.Path(a).expanduser()
        if not p.exists():
            print(f"⚠️ 見つかりません: {p}")
            return 1
        paths.append(p)

    if bot._drive_service() is None:
        # 理由は3つある（繋いでいない／切れた／権限を変えた）。ボット側の
        # 案内文がその見分けを持っているので、それをそのまま出す。
        print("⚠️ Driveにつながっていません。")
        print("   " + bot._drive_need_auth().replace("\n", "\n   "))
        print("   認証し直す: python3 tools/drive_auth.py")
        return 1

    # 置き場の規則はボット側と同じものを使う（so-creative/動画|画像/案件）。
    # --folder を渡せばそれが優先。
    ok = 0
    for p in paths:
        # _drive_upload はDiscord向けの文を返すので、URLだけ取り出す
        try:
            dest = folder or bot._drive_dest_for(p, project or "")
        except Exception as e:  # noqa: BLE001
            # 置き場を決められない時、_drive_root は投げる（黙ってマイドライブ
            # 直下へ散らさないため）。ここで受けて、上げずに止める。
            print(f"❌ {p.name} … 置き場を決められませんでした"
                  f"（{type(e).__name__}）。間違った場所に置かないよう"
                  "上げていません。")
            continue
        res = bot._drive_upload(str(p), folder_id=dest) or ""
        link = next((w for w in res.split() if w.startswith("http")), "")
        if link:
            print(f"✅ {p.name}\n   {link}")
            ok += 1
        else:
            print(f"❌ {p.name} … {res.strip() or '上げられなかった'}")
    return 0 if ok == len(paths) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
