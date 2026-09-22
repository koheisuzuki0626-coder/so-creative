#!/usr/bin/env python3
"""出来上がったファイルを Google Drive の「動画」フォルダへ入れる。

    python3 tools/drive_put.py 動画.mp4 [もう1本.mp4 ...]
    python3 tools/drive_put.py --folder <フォルダID> 資料.pdf

置き場は ai_group_chat.DRIVE_UPLOAD_FOLDER（＝Driveの「動画」フォルダ）。
何を渡してもここに入る。
認証とアップロードの実体はボットと同じものを使う（鍵の持ち方を二重に
しないため）。トークンが切れていたら、その場で言う。
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
    folder = None
    args = list(argv)
    if args and args[0] == "--folder":
        if len(args) < 2:
            print("⚠️ --folder のあとにフォルダIDが要ります")
            return 2
        folder = args[1]
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
        print("⚠️ Driveにつながっていません（トークン切れ or 鍵なし）。\n"
              "   認証し直す: python3 tools/drive_auth.py")
        return 1

    # 置き場の規則はボット側と同じものを使う（動画は「動画」フォルダ、
    # それ以外はマイドライブ直下）。--folder を渡せばそれが優先。
    ok = 0
    for p in paths:
        # _drive_upload はDiscord向けの文を返すので、URLだけ取り出す
        dest = folder or bot._drive_dest_for(p)
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
