#!/usr/bin/env python3
"""ボットから本人へメールを送れるようにする（Macのブラウザで「許可」を押すだけ）。

    python3 tools/gmail_auth.py

使い道：claude CLI のログイン切れのような「本人にしか直せない故障」を
メールで知らせる（ai_group_chat.py の _alert_once_sync）。Discordの通知は
本人のスマホに来ないため（2026-11-18）。

- トークンは history/gmail_token.json（Drive とは別。.gitignore 済み）
- 宛先は、いま許可したアカウント自身のアドレス → history/gmail_to.txt
  （リポジトリにアドレスを書かないため、ここで取って保存する）
- 鍵は Drive と同じ OAuth クライアント（.env の GOOGLE_DRIVE_CLIENT_ID 等）
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
    from google.auth.transport.requests import AuthorizedSession
    flow = InstalledAppFlow.from_client_config(
        bot._drive_client_config(), scopes=bot.GMAIL_SCOPES)
    creds = flow.run_local_server(
        port=8765, open_browser=True, prompt="consent", access_type="offline",
        authorization_prompt_message="▼ ブラウザで「許可」を押してください:\n{url}",
        success_message="許可できました。このタブは閉じて大丈夫です。")
    bot.GMAIL_TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)
    bot.GMAIL_TOKEN_FILE.write_text(creds.to_json(), encoding="utf-8")
    os.chmod(bot.GMAIL_TOKEN_FILE, 0o600)
    r = AuthorizedSession(creds).get(
        "https://openidconnect.googleapis.com/v1/userinfo", timeout=30)
    email = (r.json() or {}).get("email", "") if r.ok else ""
    if not email:
        print(f"⚠️ アドレスが取れませんでした（HTTP {r.status_code}）")
        return 1
    bot.GMAIL_TO_FILE.write_text(email, encoding="utf-8")
    print("✅ 許可できました。宛先を保存しました。")
    if "--test" in sys.argv:
        ok, why = bot._send_mail_sync(
            "【ボット】通知のテスト",
            "Discordボットからのメール通知のテストです。届いていれば設定は完了です。")
        print(f"テスト送信: {'✅' if ok else '⚠️'} {why}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
