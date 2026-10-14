#!/usr/bin/env python3
"""問い合わせフォームを機械で埋める。【送信はしない】。

送信だけ人が押す理由（2026-10-14）：
  メールの失敗は静かで安い（宛先が無ければ返ってくるだけ）。
  フォームの失敗は【相手の会社に、崩れた文が、so-creative の名前で届く】。
  やり直しが走れば同じ会社に何通も入る。立ち上げの時期にそれは取り返せない。
  画面を見れば、フォームのページに書いてある「営業お断り」も人が気づける。
  1社5〜8秒。135社で15分ほど。全自動との差はその15分だけ。

使い方：
  ./venv/bin/python tools/fill_forms.py          # 続きから
  ./venv/bin/python tools/fill_forms.py --dry    # ブラウザを出さずに埋める先だけ数える
"""
import asyncio, json, os, pathlib, re, sys

BASE = pathlib.Path(__file__).resolve().parent.parent.parent
OUT = BASE / "成果物" / "送り先リスト"
RAW = OUT / "_収集"
DONE = RAW / "form_done.json"
TPL = BASE / "成果物" / "_テンプレート" / "営業文面.md"

# 送り主の情報。フォームの欄はすべて【こちらの情報】を聞いてくるので、全部手元にある
ME = {
    "company": "so-creative",
    "name": "鈴木 宏平",
    "kana": "スズキ コウヘイ",
    "mail": "bonvoyage.ti@icloud.com",
    # ⚠️ 電話番号をここに書かないこと。書けばGitHubに載って公開される。
    #   418社のフォームに入る番号なので、本人が置き場所を選べる形にしてある。
    #   置き方（どちらでも）：
    #     export OUTREACH_TEL=090-xxxx-xxxx
    #     echo 090-xxxx-xxxx > discord-groupchat/.outreach_tel   （.gitignore 済み）
    "tel": (os.environ.get("OUTREACH_TEL", "").strip()
            or (pathlib.Path(__file__).resolve().parent.parent / ".outreach_tel").read_text(
                encoding="utf-8").strip()
            if (pathlib.Path(__file__).resolve().parent.parent / ".outreach_tel").exists()
            else ""),
    "zip": "461-0040",
    "addr": "愛知県名古屋市東区砂田橋4-1-57",
    "url": "https://koheisuzuki0626-coder.github.io/so-creative/",
    "subject": "採用ページの動画について（so-creative／鈴木）",
}

# 欄の見分け方。name/id/placeholder/近くのラベルの文字で決める
FIELDS = [
    ("company", r"会社|御社|法人|企業|団体|組織|company|corp"),
    ("kana",    r"フリガナ|ふりがな|カナ|kana|furigana"),
    ("name",    r"お?名前|氏名|担当者|ご担当|name(?!.*company)|sei|mei"),
    ("mail",    r"メール|mail|email|e-mail"),
    ("tel",     r"電話|TEL|tel|phone"),
    ("zip",     r"郵便|zip|postal"),
    ("addr",    r"住所|所在地|address"),
    ("subject", r"件名|題名|subject|title"),
    ("url",     r"URL|ホームページ|サイト|website"),
]
BODY_RE = re.compile(r"内容|本文|ご?相談|ご?要望|メッセージ|message|body|comment|inquiry|詳細")
NG_RE = re.compile(
    r"営業(目的)?の(メール|ご連絡|お問[い合]*わせ)[^。]{0,12}"
    r"(お断り|ご遠慮|受け付けて?おりません)|営業[・、]?勧誘[^。]{0,10}(お断り|ご遠慮)")


def atena(name):
    n = name.replace("(株)", "株式会社").replace("（株）", "株式会社")
    n = n.replace("(有)", "有限会社").replace("（有）", "有限会社")
    return re.sub(r"\s+", "", re.split(r"[/／]", n)[0].strip())


def template():
    """営業文面.md のD節から本文を取る（写しを作らない）。"""
    m = re.search(r"^## D\.[\s\S]*?```\n([\s\S]*?)```", TPL.read_text(encoding="utf-8"), re.M)
    if not m:
        sys.exit("営業文面.md のD節が読めない")
    return m.group(1)


def body_for(c, tpl):
    """1社ぶんの本文を組む。埋まらない〔　〕が残ったら送らせない。"""
    d = c["draft"]
    b = tpl.replace("〇〇株式会社", atena(c["name"]))
    b = re.sub(r"〔求人から1行[\s\S]*?拝見しました。〕", d["insert"], b)
    # 2つ目の〔　〕は、インタビューが在る会社だけ埋める。無い会社では行ごと落とす
    if d.get("voice"):
        # ⚠️ ここで {d['voice']} を繰り返さないこと。直前の1行と同じ語が2回出る
        #   （「社員の声を拝見しました」→「社員の声の内容を…」）。
        b = re.sub(r"〔相手に合わせて1行[\s\S]*?できます。〕",
                   "その内容を、そのまま映像の構成にできます。", b)
    else:
        b = re.sub(r"\n〔相手に合わせて1行[\s\S]*?できます。〕\n", "\n", b)
    b = b.replace("〔金額〕", "240,000")      # 30秒・梅＝120,000＋4,000×30（税込）
    b = b.replace("〔週数〕", "2")             # 2026-10-14 本人が決定（約2週間）
    b = re.sub(r"^件名：.*\n", "", b)          # 件名は欄に入れる
    # フォームから送るので「本メールに返信」は成立しない
    b = b.replace("本メールに「配信停止」とだけご返信ください",
                  "上記アドレスに「配信停止」とだけご連絡ください")
    left = re.findall(r"〔[^〕]*〕", b)
    return b.strip(), left


async def fill(page, c, body):
    """欄を埋める。送信は押さない。"""
    put = {}
    inputs = await page.query_selector_all(
        "input[type=text], input[type=email], input[type=tel], input:not([type]), textarea")
    for el in inputs:
        try:
            if not await el.is_visible():
                continue
            hint = " ".join(filter(None, [
                await el.get_attribute("name") or "",
                await el.get_attribute("id") or "",
                await el.get_attribute("placeholder") or "",
                await el.evaluate("e => (e.labels&&e.labels[0]?e.labels[0].innerText:'')"
                                  " + (e.closest('tr,li,div,p')?"
                                  "e.closest('tr,li,div,p').innerText.slice(0,60):'')"),
            ]))
            tag = await el.evaluate("e => e.tagName")
            if tag == "TEXTAREA" or BODY_RE.search(hint):
                await el.fill(body); put["本文"] = True; continue
            for k, pat in FIELDS:
                if re.search(pat, hint, re.I) and ME.get(k):
                    await el.fill(ME[k]); put[k] = True; break
        except Exception:
            continue
    # 「個人情報の取り扱いに同意」のチェック
    for cb in await page.query_selector_all("input[type=checkbox]"):
        try:
            t = await cb.evaluate("e => (e.closest('label,li,div,p')?"
                                  "e.closest('label,li,div,p').innerText.slice(0,80):'')")
            if re.search(r"同意|承諾|agree|個人情報", t) and await cb.is_visible():
                await cb.check(); put["同意"] = True
        except Exception:
            continue
    return put


async def main(dry):
    rows = json.loads((RAW / "drafts.json").read_text(encoding="utf-8"))
    todo = [c for c in rows if c.get("draft") and not c["draft"]["mail"]]
    done = set(json.loads(DONE.read_text(encoding="utf-8"))) if DONE.exists() else set()
    todo = [c for c in todo if c["name"] not in done]
    tpl = template()

    # 送れない形のものは先に落とす（1社ずつ気づくのでは遅い）
    bad = {}
    for c in list(todo):
        _, left = body_for(c, tpl)
        if left:
            bad.setdefault(" / ".join(sorted(set(left))), []).append(c["name"])
            todo.remove(c)
    if bad:
        print("⚠️ 埋まらない〔　〕があるので、この分は送れない：")
        for k, v in bad.items():
            print(f"   {k} … {len(v)}社")
        print("   テンプレート（成果物/_テンプレート/営業文面.md）側を決める必要がある。\n")
    if not ME["tel"]:
        print("⚠️ 電話番号が未設定。必須の欄があるフォームはその場で飛ばす。")
        print("   入れるなら: export OUTREACH_TEL=090-xxxx-xxxx"
              "  または  echo 090-xxxx-xxxx > discord-groupchat/.outreach_tel\n")
    print(f"埋める先 {len(todo)}社（済み {len(done)}社）")
    if dry or not todo:
        return 0

    from playwright.async_api import async_playwright
    async with async_playwright() as p:
        br = await p.chromium.launch(headless=False)
        pg = await br.new_page()
        for i, c in enumerate(todo, 1):
            body, _ = body_for(c, tpl)
            url = (c.get("checked_urls") or [""])[-1]
            print(f"\n[{i}/{len(todo)}] {atena(c['name'])}  {url}")
            try:
                await pg.goto(url, timeout=25000)
                if NG_RE.search(await pg.content()):
                    print("   → このページに営業お断りの表示。飛ばす")
                    done.add(c["name"]); continue
                put = await fill(pg, c, body)
                if "本文" not in put:
                    print("   → 本文の欄が見つからない。飛ばす"); continue
                print(f"   埋めた: {'・'.join(put)}")
                print("   画面を見て、よければ送信を押す → Enter（s で飛ばす）")
            except Exception as e:
                print(f"   → 開けない（{type(e).__name__}）。飛ばす"); continue
            if (await asyncio.get_event_loop().run_in_executor(None, input)).strip().lower() != "s":
                done.add(c["name"])
                DONE.write_text(json.dumps(sorted(done), ensure_ascii=False, indent=1),
                                encoding="utf-8")
        await br.close()
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main("--dry" in sys.argv)))
