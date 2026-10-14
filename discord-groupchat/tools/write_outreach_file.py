#!/usr/bin/env python3
"""下書き済みの会社を、送り方で3つに分けて 成果物/送り先リスト/ に書く。

分け方は「どう送るか」で決める：
  ①メール送信できる … 送り先と差し込み文が両方そろっている。読まずに送れる
  ②フォームに貼る   … 差し込み文はできたが、メールを公開していない
  ③外した           … 書ける事実が無い（営業文面Dの決めごと）
"""
import json, pathlib, sys, collections

BASE = pathlib.Path(__file__).resolve().parent.parent.parent
OUT = BASE / "成果物" / "送り先リスト"
RAW = OUT / "_収集"


def main():
    rows = json.loads((RAW / "drafts.json").read_text(encoding="utf-8"))
    mail = [c for c in rows if c.get("draft") and c["draft"]["mail"]]
    form = [c for c in rows if c.get("draft") and not c["draft"]["mail"]]
    drop = [c for c in rows if not c.get("draft")]
    key = lambda c: (c.get("pref", ""), c["name"])
    mail.sort(key=key); form.sort(key=key)

    L = ["# 営業メールの差し込み文（機械で下書き・2026-10）", ""]
    L += [f"対象 {len(rows)}社。差し込み文は**相手の採用ページに実際にある文字列だけ**で",
          "組んである（作り話を書かない）。抜けなかった会社は外した。", "",
          f"| 送り方 | 社数 |", "|---|---|",
          f"| ①メールで送れる（読まずに送れる） | {len(mail)} |",
          f"| ②問い合わせフォームに貼る | {len(form)} |",
          f"| ③外した（書ける事実が無い） | {len(drop)} |", ""]
    L += ["## ① メールで送れる", "",
          "営業文面Dの〔　〕にこの文を入れてそのまま送る。", "",
          "| 会社 | 都道府県 | 送り先 | 差し込み文 | 根拠 |", "|---|---|---|---|---|"]
    for c in mail:
        b = "募集区分" if c["draft"].get("kubun") else "募集職種"
        L.append(f"| {c['name']} | {c.get('pref','')} | {c['draft']['mail']} "
                 f"| {c['draft']['insert']} | {b} |")
    L += ["", "## ② 問い合わせフォームに貼る", "",
          "メールを公開していない会社。フォームの本文欄に営業文面Dを貼り、",
          "〔　〕にこの文を入れる。**フォームに「営業お断り」と書いてあったら送らない。**", "",
          "| 会社 | 都道府県 | 差し込み文 | 採用ページ |", "|---|---|---|---|"]
    for c in form:
        u = (c.get("checked_urls") or [""])[-1]
        L.append(f"| {c['name']} | {c.get('pref','')} | {c['draft']['insert']} | {u} |")
    L += ["", "## ③ 外した", ""]
    for why, n in collections.Counter(c.get("skip") for c in drop).most_common():
        L.append(f"- {why}：{n}社")
    L += ["", "外した会社は `_収集/drafts.json` に残してある。採用ページの作りが",
          "変われば抜けるようになるので、捨てていない。", ""]

    p = OUT / "全国_営業文面_2026-10.md"
    p.write_text("\n".join(L), encoding="utf-8")
    print(f"書いた {p.relative_to(BASE)}")
    print(f"  ①メールで送れる {len(mail)}社 / ②フォーム {len(form)}社 / ③外した {len(drop)}社")
    return 0


if __name__ == "__main__":
    sys.exit(main())
