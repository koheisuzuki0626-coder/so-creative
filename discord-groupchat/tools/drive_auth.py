#!/usr/bin/env python3
"""Google Drive につなぎ直す（Macのブラウザで完結する）。

    python3 tools/drive_auth.py

Discordの「ドライブ認証」はスマホから認可コードを貼る手順だが、
リダイレクト先の localhost:8765 はMac自身なので、Macでやるほうが速い。
ブラウザが開くので「許可」を押すだけ。コードの貼り付けは要らない。

トークンは history/drive_token.json に入る（.gitignore 済み）。
スコープを変えた時・鍵を入れ替えた時は、これを1回流して取り直す。

同意画面が「テスト中」のままだと更新用トークンは7日で切れる。スコープは
drive.file に戻してあるので（機微スコープではない＝審査が要らない）、
Google Cloud で同意画面を「本番環境」に公開しておくこと。2026-09-25。
"""
import os
import pathlib
import sys

BASE = pathlib.Path(__file__).resolve().parent.parent

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


def main():
    cid, sec = bot._drive_client_pair()
    if not cid or not sec:
        print("⚠️ 鍵（client_id / client_secret）が .env にありません。")
        return 2
    from google_auth_oauthlib.flow import InstalledAppFlow
    flow = InstalledAppFlow.from_client_config(
        bot._drive_client_config(), scopes=bot.DRIVE_SCOPES)
    creds = flow.run_local_server(
        port=8765, open_browser=True, prompt="consent", access_type="offline",
        authorization_prompt_message="▼ ブラウザで「許可」を押してください:\n{url}",
        success_message="認証できました。このタブは閉じて大丈夫です。")
    bot._drive_save_token(creds)
    print(f"✅ つながりました（{bot.DRIVE_TOKEN_FILE}）")
    print(f"   更新用トークン: {'あり' if creds.refresh_token else '⚠️ 無し'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
