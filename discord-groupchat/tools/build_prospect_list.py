#!/usr/bin/env python3
"""送り先リストを作る。ユースエール認定企業（全国）から、採用動画の無い会社を選ぶ。

    python3 tools/build_prospect_list.py fetch     # ①一覧と詳細を集める（数分）
    python3 tools/build_prospect_list.py check     # ②採用ページを見て動画の有無を判定
    python3 tools/build_prospect_list.py build     # ③Markdown のリストに書き出す

母集団を【ユースエール認定企業】にした理由（2026-10-14）：
  ・厚労省が「若者の採用・育成に積極的」と認定した**中小企業**に限られる
  ・全国2,178社・47都道府県。撮影が無いので商圏は全国で成立する
  ・詳細ページに【企業採用ページURL】【従業員数】【業種】【所在地】が載っていて、
    採用ページを推測しなくていい
  ・すべて公開情報。前職で知った情報は一切使っていない

⚠️ 機械検査だけでは別ドメインの採用サイトを見落とす。
   2026-09-24 の30社では取りこぼしが2社（7%）あった。
   送る前に、◎の会社だけは1社ずつ目視すること。
"""
import asyncio, json, pathlib, re, sys, unicodedata

BASE = pathlib.Path(__file__).resolve().parent.parent.parent
OUT = BASE / "成果物" / "送り先リスト"
RAW = OUT / "_収集"
RAW.mkdir(parents=True, exist_ok=True)
LIST_URL = "https://wakamono-koyou-sokushin.mhlw.go.jp/search/service/ninteilist.action"
DETAIL = ("https://wakamono-koyou-sokushin.mhlw.go.jp/search/service/"
          "portalkigyodetail.action?action=showDetail&kigyo_id=")

# 動画がある、と見なす手がかり。トップと採用ページの HTML に対して当てる。
# ⚠️ 語を増やすときは誤検知を数えること。2026-09-24 には Wix のテンプレート文字列を
#    .mp4 と誤検知した例がある。
VIDEO_RE = re.compile(
    r"youtube\.com/(embed|watch)|youtu\.be/|player\.vimeo\.com|vimeo\.com/\d|"
    r"<video[\s>]|\.mp4[\"'?]|\.m3u8|wistia|brightcove|movie|ムービー|"
    r"採用動画|会社紹介動画|紹介ムービー|PV動画", re.I)
CONC = 6          # 相手は官公庁のサイト。同時接続は控えめに


def norm(s):
    return unicodedata.normalize("NFKC", re.sub(r"\s+", "", s or ""))


async def get(session, url, timeout=20):
    import aiohttp
    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=timeout)) as r:
            if r.status != 200:
                return None
            return await r.text(errors="ignore")
    except Exception:
        return None


def parse_list(html):
    """都道府県ごとの企業一覧を取る。"""
    out, blocks = [], re.split(r"<h4>([^<]+)</h4>", html)
    for i in range(1, len(blocks), 2):
        pref, body = blocks[i].strip(), blocks[i + 1]
        nxt = body.find("<h4>")
        if nxt > 0:
            body = body[:nxt]
        for m in re.finditer(r"kigyo_id=(\d+)\"[^>]*>([^<]+)</a>", body):
            out.append({"pref": pref, "id": m.group(1), "name": norm(m.group(2))})
    return out


def parse_detail(html):
    t = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html))
    def grab(label, nxt):
        m = re.search(re.escape(label) + r"\s*(.*?)\s*" + re.escape(nxt), t)
        return m.group(1).strip() if m else ""
    site = grab("企業ホームページURL", "企業採用ページURL")
    rec = grab("企業採用ページURL", "従業員")
    emp = grab("従業員", "業種")
    ind = grab("大分類：", " 中分類")
    addr = grab("所在地", "企業ホームページURL")
    n = re.search(r"(\d+)", emp)
    return {"site": site if site.startswith("http") else "",
            "recruit": rec if rec.startswith("http") else "",
            "employees": int(n.group(1)) if n else None,
            "industry": ind, "address": addr}


async def fetch():
    import aiohttp
    async with aiohttp.ClientSession(headers={"User-Agent": "so-creative prospect list builder"}) as s:
        html = await get(s, LIST_URL, 40)
        if not html:
            print("一覧が取れませんでした"); return 1
        comps = parse_list(html)
        print(f"一覧 {len(comps)}社 / {len(set(c['pref'] for c in comps))}都道府県")
        sem = asyncio.Semaphore(CONC)
        async def one(c):
            async with sem:
                h = await get(s, DETAIL + c["id"])
                await asyncio.sleep(0.15)
                if h:
                    c.update(parse_detail(h))
                return c
        done = 0
        for i in range(0, len(comps), 200):
            chunk = comps[i:i + 200]
            await asyncio.gather(*(one(c) for c in chunk))
            done += len(chunk)
            print(f"  詳細 {done}/{len(comps)}", flush=True)
        (RAW / "youthyell.json").write_text(
            json.dumps(comps, ensure_ascii=False, indent=1), encoding="utf-8")
        got = sum(1 for c in comps if c.get("site"))
        print(f"書き出し: {RAW/'youthyell.json'}（サイトURLが取れた {got}社）")
    return 0


async def check(limit=None):
    import aiohttp
    comps = json.loads((RAW / "youthyell.json").read_text(encoding="utf-8"))
    # ◎の条件（2026-09-24 と同じ）：従業員30〜300名。予算があり、決裁が近い
    def emp(c):
        try:
            return int(c.get("employees") or 0)
        except (TypeError, ValueError):
            return 0
    target = [c for c in comps if c.get("site") and 30 <= emp(c) <= 300]
    if limit:
        target = target[:limit]
    print(f"検査対象 {len(target)}社（従業員30〜300名・サイトあり）")
    async with aiohttp.ClientSession(headers={"User-Agent": "so-creative prospect list builder"}) as s:
        sem = asyncio.Semaphore(CONC)
        async def one(c):
            async with sem:
                hits = []
                for url in [u for u in (c.get("site"), c.get("recruit")) if u]:
                    h = await get(s, url)
                    await asyncio.sleep(0.2)
                    if h is None:
                        hits.append("取得失敗"); continue
                    m = VIDEO_RE.search(h)
                    if m:
                        hits.append(m.group(0)[:24])
                # ⚠️ ここの式を2026-10-14 に1度壊した（0社になった）。
                #    成功したのに当たらなかったときは hits に何も入らない。
                #    「空＝動画なし」だが、全部取得失敗のときも実質空に見えるので、
                #    失敗の数を数えて分ける。
                c["video_hits"] = hits
                real = [x for x in hits if x != "取得失敗"]
                fails = [x for x in hits if x == "取得失敗"]
                urls = [u for u in (c.get("site"), c.get("recruit")) if u]
                c["no_video"] = bool(urls) and not real and len(fails) < len(urls)
                return c
        done = 0
        for i in range(0, len(target), 100):
            await asyncio.gather(*(one(c) for c in target[i:i + 100]))
            done += len(target[i:i + 100])
            print(f"  検査 {done}/{len(target)}", flush=True)
    (RAW / "checked.json").write_text(
        json.dumps(target, ensure_ascii=False, indent=1), encoding="utf-8")
    ok = [c for c in target if c.get("no_video")]
    print(f"動画が見当たらない: {len(ok)}社 / {len(target)}社（{len(ok)/max(1,len(target))*100:.0f}%）")
    return 0


PREF_ORDER = ["愛知県", "岐阜県", "三重県", "静岡県"]   # 近い順。◎はここから


def build():
    """checked.json から Markdown のリストを書き出す。"""
    rows = json.loads((RAW / "checked.json").read_text(encoding="utf-8"))
    ok = [c for c in rows if c.get("no_video")]
    # 優先度：◎＝東海4県（訪問が要る話になっても近い）／○＝それ以外
    def pri(c):
        return "◎" if c["pref"] in PREF_ORDER else "○"
    ok.sort(key=lambda c: (PREF_ORDER.index(c["pref"]) if c["pref"] in PREF_ORDER else 99,
                           c["pref"], -int(c.get("employees") or 0)))
    lines = [
        "# 送り先リスト：全国・採用動画（ユースエール認定企業）",
        "",
        f"**{len(ok)}社。**母集団はユースエール認定企業（全国2,178社）。",
        "",
        "> **送らない。**リストを作るのは可だが、送信は営業活動で労務にあたる",
        "> （2026-09-20・保険者に確認）。**開業届を出してから**送る。",
        "",
        "---",
        "",
        "## どうやって選んだか（再現できるように書く）",
        "",
        "母集団は厚生労働省の",
        "**[ユースエール認定企業一覧](https://wakamono-koyou-sokushin.mhlw.go.jp/search/service/ninteilist.action)**。",
        "「若者の採用・育成に積極的」と国が認定した**中小企業**で、**すべて公開情報**。",
        "前職で知った情報は一切使っていない。",
        "",
        "この母集団を選んだ理由：**認定を取る時点で、採用に予算と手間をかけている会社**だから。",
        "求人媒体から拾うより、ニーズが顕在化している確率が高い。",
        "撮影が無いので**商圏は全国**。訪問の要否で絞っていない。",
        "",
        "| 段 | 条件 | 残り |",
        "|---|---|---|",
        "| 0 | 母集団（ユースエール認定・全国47都道府県） | **2,178社** |",
        "| 1 | 自社サイトのURLが載っている | 1,997社 |",
        "| 2 | **従業員30〜300名**（予算があり、決裁が近い） | 1,303社 |",
        f"| 3 | **トップと採用ページに動画が見当たらない**（実際に取得して確認） | **{len(ok)}社** |",
        "",
        "⚠️ **機械検査だけでは別ドメインの採用サイトを見落とす。**",
        "2026-09-24 の30社では取りこぼしが2社（7%）あった。**送る前に1社ずつ目視すること。**",
        "",
        "作り直すときは `discord-groupchat/tools/build_prospect_list.py`。",
        "",
        "### 優先度の意味",
        "",
        "| | 条件 | 考え方 |",
        "|---|---|---|",
        "| **◎** | 東海4県（愛知・岐阜・三重・静岡） | 訪問が要る話になっても近い |",
        "| **○** | それ以外の43都道府県 | 撮影が無いので制作は同じようにできる |",
        "",
        "---",
        "",
        "## リスト",
        "",
        "| | 都道府県 | 会社名 | 従業員 | 業種 | サイト | 採用ページ |",
        "|---|---|---|---:|---|---|---|",
    ]
    for c in ok:
        rec = f"[採用]({c['recruit']})" if c.get("recruit") else "—"
        lines.append(f"| {pri(c)} | {c['pref']} | {c['name']} | {c.get('employees') or '—'}名 "
                     f"| {(c.get('industry') or '')[2:]} | [サイト]({c['site']}) | {rec} |")
    (OUT / "全国_採用動画_2026-10.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    import collections
    cc = collections.Counter(pri(c) for c in ok)
    print(f"書き出し: {OUT/'全国_採用動画_2026-10.md'}")
    print(f"  {len(ok)}社（◎{cc['◎']} / ○{cc['○']}）")
    cp = collections.Counter(c["pref"] for c in ok)
    print("  上位10:", " / ".join(f"{k}{v}" for k, v in cp.most_common(10)))
    return 0


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "fetch"
    lim = int(sys.argv[2]) if len(sys.argv) > 2 else None
    sys.exit(build() if cmd == "build" else asyncio.run(fetch() if cmd == "fetch" else check(lim)))
