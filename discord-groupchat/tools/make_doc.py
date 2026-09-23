#!/usr/bin/env python3
"""見積書・請求書を PDF で出す。金額は式から計算する（手で打たない）。

    python3 tools/make_doc.py 見積書 --to 株式会社ABC --title 会社紹介動画 \
        --tier 竹 --sec 60 --count 1 --nar ai
    python3 tools/make_doc.py 請求書 --to 株式会社ABC --title 会社紹介動画 \
        --tier 竹 --sec 60 --delivered 2026-10-01

なぜ計算させるか:
    ひな形は「小計（税別）＋消費税10%」で組まれていて、同じ案件で
    サイトより 38,400円 高い見積書が出る状態だった（2026-09-24 に発見）。
    適格請求書発行事業者の登録をしていないので消費税は申し受けない。
    表示額がそのまま総額。式を1か所にして、人が金額を打つ余地を無くす。

    料金 = 90,000 ＋ 秒単価 × 合計秒数 ＋ 65,000 ×（本数 − 1）＋ ナレーション調整
      秒単価 … 梅 3,500 ／ 竹 4,900 ／ 松 6,650
      ナレーション調整（assets/pricing.js の narFee と同じ式にする）
        梅・竹 … 人物 +70,000（何本に入れても1名ぶん）／ AI ±0
        松     … 人物 ±0（秒単価に1名ぶんが溶けている）／
                 人物を使わないなら手配1回ぶん −25,000 を返す
        共通   … ナレーションを入れない本は 1本につき −25,000

    2026-09-24：松で AI／なしを選んだとき、上の −25,000 を引いておらず
    サイトの計算機より 25,000 円高い見積書が出ていた。サイトが正
    （tests/pricing.mjs で時間単価の下限まで検証しているのはあちら）。
"""
import argparse
import datetime
import pathlib
import re
import sys

BASE = pathlib.Path(__file__).resolve().parent.parent.parent
FMT = BASE / "成果物" / "書類ひな形" / "_書式"
OUT = BASE / "成果物" / "書類ひな形" / "_発行済み"

PRICE_BASE = 90000
PER_SEC = {"梅": 3500, "竹": 4900, "松": 6650}
EXTRA_CUT = 65000
NARRATION_HUMAN = 70000
NO_NARRATION = 25000
MATSU_TO_AI = 25000                 # 松に込みの「ナレーター手配1回ぶん」を返す額
REVISIONS = {"梅": 2, "竹": 3, "松": 3}
TIER_NOTE = {"梅": "梅（標準）／人物は出ません",
             "竹": "竹（上）／登場人物2人まで",
             "松": "松（特上）／登場人物3人まで・人物ナレーション1名込み"}

# 工数と納期（tests/lib.mjs の hoursModes / leadWeeks と同じ式）。
#   工数 = 3.0h ＋ 0.15h×倍率×合計秒数 ＋ 1.5h×(本数−1) ＋ 1.0h×ナレーション本数
#   納期 = 工数 ÷ 週25h ＋ 確認の往復1週（最低2週）
HOUR_MULT = {"梅": 1.0, "竹": 1.22, "松": 1.36}
HOURS = {"base": 3.0, "per_sec": 0.15, "per_extra": 1.5, "narration": 1.0}
LEAD_WEEK_HOURS = 25
LEAD_REVIEW = 1


def yen(n):
    return f"{n:,}"


def nar_tracks(tier, count, nar):
    """工数に乗るナレーションの本数。入れない本は0。
    松で人物を使う時だけ、秒単価に溶けている1本ぶんを引く。"""
    if nar == "none":
        return 0
    return count - (1 if tier == "松" and nar == "human" else 0)


def work_hours(tier, sec, count, nar):
    return (HOURS["base"]
            + HOURS["per_sec"] * HOUR_MULT[tier] * sec * count
            + HOURS["per_extra"] * (count - 1)
            + HOURS["narration"] * nar_tracks(tier, count, nar))


def lead_time(tier, sec, count, nar):
    """納期。サイトの計算機と同じ式で出す。

    2026-09-24 まで固定の早見表（300秒以下は一律「約2〜3週間」など）だった。
    63通り中33通りでサイトと食い違い、しかも**見積書の方が短い**という
    守れない約束になっていた（竹300秒×3本で 約3〜4週間 と サイト 約8週間）。
    尺だけの表では、本数とナレーションで増える工数を数えられない。
    """
    weeks = max(2, round(work_hours(tier, sec, count, nar)
                         / LEAD_WEEK_HOURS + LEAD_REVIEW))
    return f"約{weeks}週間"


def calc(tier, sec, count, nar):
    """内訳の行と合計を返す。nar は ai / human / none。"""
    rows, total = [], 0
    rows.append(("基本料金", "ヒアリング・構成案・絵コンテ・編集・書き出し", PRICE_BASE))
    total += PRICE_BASE
    body = PER_SEC[tier] * sec * count
    rows.append(("尺", f"{sec}秒 × {count}本 × ¥{yen(PER_SEC[tier])}（{tier}）", body))
    total += body
    if count > 1:
        extra = EXTRA_CUT * (count - 1)
        rows.append(("本数", f"2本目以降 {count - 1}本 × ¥{yen(EXTRA_CUT)}", extra))
        total += extra
    # ナレーション調整。サイトの計算機（assets/pricing.js の narFee）と同じ形にする。
    # 「段による手配ぶん」と「入れない本のぶん」は別勘定で、両方乗ることがある。
    if tier == "松":
        if nar == "human":
            rows.append(("人物ナレーション", "1名（松は料金に含まれています）", 0))
        else:
            rows.append(("ナレーター手配なし",
                         "松に含まれる1名ぶんを お引きします", -MATSU_TO_AI))
            total -= MATSU_TO_AI
    elif nar == "human":
        rows.append(("人物ナレーション", "1名（何本に入れても1名ぶん）", NARRATION_HUMAN))
        total += NARRATION_HUMAN
    if nar == "ai":
        rows.append(("AIナレーション", "原稿・声の選定・速さの調整・配置（料金に含まれます）", 0))
    elif nar == "none":
        back = -NO_NARRATION * count
        rows.append(("ナレーションなし", f"{count}本ぶん お引きします", back))
        total += back
    return rows, total


def rows_html(rows):
    out = []
    for name, detail, amount in rows:
        sign = "−¥" + yen(-amount) if amount < 0 else "¥" + yen(amount)
        out.append(f'\n    <tr><td>{name}</td><td>{detail}</td>'
                   f'<td class="num">{sign}</td></tr>')
    return "".join(out)


def fill(template, values):
    out = template
    for k, v in values.items():
        out = out.replace("{{" + k + "}}", str(v))
        left = re.findall(r"\{\{([^}]+)\}\}", out)
    left = re.findall(r"\{\{([^}]+)\}\}", out)
    if left:
        raise SystemExit(f"⚠️ 埋めていない欄があります: {'、'.join(sorted(set(left)))}")
    return out


def render(html, out_pdf):
    import asyncio
    from playwright.async_api import async_playwright

    async def go():
        tmp = FMT / "_tmp_render.html"
        tmp.write_text(html, encoding="utf-8")
        try:
            async with async_playwright() as p:
                b = await p.chromium.launch()
                pg = await b.new_page()
                await pg.goto(tmp.as_uri())
                await pg.wait_for_timeout(500)
                await pg.pdf(path=str(out_pdf), format="A4", print_background=True)
                await b.close()
        finally:
            tmp.unlink(missing_ok=True)
    asyncio.run(go())


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("kind", choices=["見積書", "請求書", "業務委託契約書"])
    ap.add_argument("--to", required=True, help="宛先（御中は自動で付きます）")
    ap.add_argument("--title", required=True, help="件名")
    ap.add_argument("--tier", default="竹", choices=list(PER_SEC))
    ap.add_argument("--sec", type=int, default=60)
    ap.add_argument("--count", type=int, default=1)
    ap.add_argument("--nar", default="ai", choices=["ai", "human", "none"])
    ap.add_argument("--no", help="番号（省略すると日付から作ります）")
    ap.add_argument("--date", help="発行日 YYYY-MM-DD（既定は今日）")
    ap.add_argument("--delivered", help="納品日 YYYY-MM-DD（請求書の摘要に入ります）")
    ap.add_argument("--bank", default="〔金融機関名・支店名〕")
    ap.add_argument("--account", default="〔普通 1234567〕")
    ap.add_argument("--holder", default="スズキ コウヘイ")
    ap.add_argument("--note", default="", help="備考に1行足す")
    ap.add_argument("--addr", default="〔住所〕", help="契約書：甲の住所")
    ap.add_argument("--rep", default="〔代表取締役 ◯◯ ◯◯〕", help="契約書：甲の代表者")
    ap.add_argument("--out", help="書き出し先のPDF")
    a = ap.parse_args(argv)

    day = (datetime.date.fromisoformat(a.date) if a.date else datetime.date.today())
    rows, total = calc(a.tier, a.sec, a.count, a.nar)
    common = {
        "件名": a.title,
    }
    if a.kind in ("見積書", "請求書"):
        common |= {"宛先": a.to,
                   "発行日": f"{day.year}年{day.month}月{day.day}日",
                   "合計": yen(total), "内訳": rows_html(rows)}
    if a.kind == "見積書":
        common |= {
            "番号": a.no or f"Q-{day:%Y%m%d}-01",
            "段": TIER_NOTE[a.tier],
            "納期": lead_time(a.tier, a.sec, a.count, a.nar),
            "修正": REVISIONS[a.tier],
            "備考": f"<li>{a.note}</li>" if a.note else "",
        }
    elif a.kind == "業務委託契約書":
        NAR = {"ai": "AIナレーションあり（料金に含む）",
               "human": "人物ナレーションあり（1名）", "none": "なし"}
        common |= {
            "甲": a.to, "甲住所": a.addr, "甲代表": a.rep,
            "段": TIER_NOTE[a.tier],
            "尺本数": f"{a.sec}秒 × {a.count}本",
            "ナレーション": NAR[a.nar],
            "納期": lead_time(a.tier, a.sec, a.count, a.nar),
            "修正": REVISIONS[a.tier],
            "委託料": yen(total),
            "締結日": f"{day.year}年{day.month}月{day.day}日",
        }
    else:
        due = day + datetime.timedelta(days=30)
        d = (datetime.date.fromisoformat(a.delivered) if a.delivered else day)
        common |= {
            "番号": a.no or f"I-{day:%Y%m%d}-01",
            "支払期限": f"{due.year}年{due.month}月{due.day}日（納品日から30日以内）",
            "金融機関": a.bank, "口座": a.account, "名義": a.holder,
            "摘要": (f"納品日 {d.year}年{d.month}月{d.day}日／"
                     f"納品物 MP4 {a.count}本（1920×1080・{a.sec}秒）"),
        }
    html = fill((FMT / f"{a.kind}.html").read_text(encoding="utf-8"), common)
    OUT.mkdir(parents=True, exist_ok=True)
    stem = common.get("番号") or f"C-{day:%Y%m%d}-01"
    out = pathlib.Path(a.out) if a.out else OUT / f"{stem}_{a.kind}_{a.to}.pdf"
    render(html, out)
    print(f"✅ {out}")
    print(f"   {a.title}／{a.tier}・{a.sec}秒×{a.count}本・ナレーション={a.nar}")
    for name, detail, amount in rows:
        print(f"     {name:<16} {('−¥'+yen(-amount)) if amount<0 else '¥'+yen(amount):>10}")
    print(f"     {'合計':<16} {'¥'+yen(total):>10}（税込・消費税は申し受けません）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
