#!/usr/bin/env python3
"""営業文面Dの〔差し込み文〕を下書きする。読まずに送れる形にするための道具。

    python3 tools/draft_outreach.py 50        # 上から50社ぶん下書き

**作り話を書かない**ことが全部。AIに書かせるのではなく、
【相手の採用ページに実際にある文字列】だけを抜いて組み立てる。
抜けなかった会社は自動で外す——営業文面Dの決めごと
「〔　〕を埋めずに送らない。埋められない会社はリストから外す」を、機械にやらせている。

外す条件（どれかに当たったら下書きを作らない）：
  ・募集職種が1つも抜けない    … 調べ足りていないのと同じ
  ・「営業お断り」の表示がある   … 特定電子メール法のオプトイン例外から外れる
  ・問い合わせ先が見つからない   … 送り先が無い

⚠️ 抜いた文字列は【そのまま】使う。言い換えない。言い換えた瞬間に、
   相手のページに無いことを書く余地が生まれる。
"""
import asyncio, html as htmlmod, json, pathlib, re, sys
from urllib.parse import urljoin

BASE = pathlib.Path(__file__).resolve().parent.parent.parent
OUT = BASE / "成果物" / "送り先リスト"
RAW = OUT / "_収集"

# 「営業お断り」。これがあるとオプトイン規制の例外に当たらない（総務省ガイドライン）
NG_RE = re.compile(
    r"営業(目的)?の(メール|ご連絡|お問[い合]*わせ)[^。]{0,12}(お断り|ご遠慮|受け付けて?おりません)|"
    r"営業・?勧誘[^。]{0,10}(お断り|ご遠慮)|セールス[^。]{0,10}(お断り|ご遠慮)|"
    r"売り?込み[^。]{0,8}(お断り|ご遠慮)")
# 募集職種。相手のページから【そのまま】抜く。
# ⚠️ 2026-10-14：ゆるい正規表現だと
#    「採用ページでです。 応募ご希望の方はの募集を拝見しました。」という文ができた。
#    職種の語そのものを並べて、当たったものだけ使う。数は減るが、それでいい
#    （営業文面Dの決めごと：埋められない会社はリストから外す）。
JOB_WORDS = re.compile(
    "施工管理|現場監督|設計|測量|積算|技術者|技術職|土木|建築|電気工事|設備|"
    "オペレーター|製造|加工|組立|塗装|溶接|品質管理|生産管理|保全|整備|"
    "システムエンジニア|プログラマ|エンジニア|開発|"
    "営業|企画|広報|マーケティング|経理|総務|人事|事務|受付|"
    "看護師|介護職|介護福祉士|保育士|理学療法士|作業療法士|支援員|相談員|調理|"
    "ドライバー|運転手|配送|倉庫|販売|接客|美容師|調理師|研究|分析|検査|"
    "スタッフ|職|員")
# ⚠️ 2026-10-14・2回失敗してから決めた形。
#   ①ラベル無しで職種語を本文から拾う → 建設会社が「ITの募集」になった（語はページのどこかに在っただけ）
#   ②ラベルだけ見て中を自由に取る → 「です。応募ご希望の方はの募集」という文ができた
#   いまの形：【ラベルの中にある】かつ【職種語を含む】かつ【文の切れ端でない】を全部要求する。
#   数は減る。それでいい（営業文面Dの決めごと：埋められない会社はリストから外す）。
JOB_LABEL_RE = re.compile(
    r"(?:募集職種|募集ポジション|職種名|職\s*種|募集区分)[\s：:｜|】\]]{1,3}"
    r"([^\n<>｜|、。]{2,20})")
JOB_NG = re.compile(r"です|ます|ください|ご希望|方は|について|こちら|される|以下|下記|"
                    r"募集|採用|応募|ページ|内容|詳細|未定|なし")
# ⚠️ 2026-10-14：`[\w.+-]+@[\w-]+\.[\w.-]+` だと Googleフォントの
#   `wght@100..900` を宛先に採用した（存在しないアドレスに送るところだった）。
#   末尾を本物のTLDに限り、連続ドットを弾く。
MAIL_RE = re.compile(r"[A-Za-z0-9][\w.+-]{0,62}@(?:[A-Za-z0-9]"
                     r"(?:[A-Za-z0-9-]*[A-Za-z0-9])?\.)+[A-Za-z]{2,24}\b")
# 代表アドレスを個人アドレスより先に使う
MAIL_GENERIC = re.compile(r"^(info|inquiry|contact|mail|office|soumu|somu|jinji|"
                          r"saiyo|saiyou|recruit|jinzai|hr|honsha|post|support)\b", re.I)
# 送り先。mailto: のほうが本文中の文字列より確実なので先に見る
MAILTO_RE = re.compile(r"mailto:([\w.+-]+@[\w-]+\.[\w.-]+)", re.I)
# お問い合わせ・会社概要へのリンク（送り先はここに在ることが多い）
CONTACT_LINK_RE = re.compile(
    r"<a[^>]+href=[\"']([^\"'#]+)[\"'][^>]*>(?:(?!</a>).){0,80}?"
    r"(?:お問\s*い?\s*合\s*わせ|問い合わせ|contact|会社概要|企業情報|company)", re.I)
CONTACT_URL_RE = re.compile(r"(contact|inquiry|otoiawase|toiawase|company|about)", re.I)


async def get(session, url, timeout=20):
    import aiohttp
    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=timeout)) as r:
            return await r.text(errors="ignore") if r.status == 200 else None
    except Exception:
        return None


def text_of(html):
    h = re.sub(r"<(script|style)[\s\S]*?</\1>", " ", html, flags=re.I)
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", h))


def contact_urls(top_html, base):
    """トップのリンクから、送り先が在りそうなページを拾う。"""
    out = []
    for m in CONTACT_LINK_RE.finditer(top_html):
        u = urljoin(base, m.group(1))
        if u not in out:
            out.append(u)
    if not out:
        for m in re.finditer(r"href=[\"']([^\"'#]+)[\"']", top_html):
            u = urljoin(base, m.group(1))
            if CONTACT_URL_RE.search(u) and u not in out:
                out.append(u)
    return out[:2]


# 採用トップから1階層奥の募集要項へ（職種の表はここに在ることが多い）
JOB_PAGE_RE = re.compile(r"(recruit|saiyo|saiyou|job|career|entry|boshu|youkou|requirement)", re.I)


def job_detail_urls(rec_html, base):
    out = []
    for m in re.finditer(r"href=[\"']([^\"'#]+)[\"']", rec_html):
        u = urljoin(base, m.group(1))
        if (JOB_PAGE_RE.search(u) and u.rstrip("/") != base.rstrip("/")
                and not re.search(r"\.(pdf|jpg|png|zip)$", u, re.I) and u not in out):
            out.append(u)
    return out[:2]


def draft(c, pages):
    """下書きを組む。作れなければ理由を返す。"""
    joined = " ".join(text_of(h) for h in pages)
    if NG_RE.search(joined):
        return None, "営業お断りの表示あり"
    raw = " ".join(pages)
    bad = re.compile(r"(example|sentry|sample|noreply|no-reply|\.png|\.jpg|\.gif|"
                     r"wixpress|cdn|googlegroups|googleapis|u003e|\.\.)", re.I)
    mails = [m for m in MAILTO_RE.findall(raw) if not bad.search(m)]
    mails += [m for m in MAIL_RE.findall(joined) if not bad.search(m) and m not in mails]
    # info@ のような代表アドレスを、個人名のアドレスより先に
    mails.sort(key=lambda m: 0 if MAIL_GENERIC.match(m) else 1)
    c["mail_found"] = mails[0] if mails else ""
    jobs = []
    for m in JOB_LABEL_RE.finditer(joined):
        j = htmlmod.unescape(m.group(1))
        j = re.sub(r"[【\[（(]?(?:新卒|中途|正社員|契約社員|パート|アルバイト)[】\]）)]?", " ", j)
        # 表の次のセルまで食い込むので、最初の空白で切る（実例：「土木技術職 業務内」）
        j = j.replace("\u3000", " ").strip(" ・:：/／|｜-−—")
        j = j.split(" ")[0].strip("　 ・:：/／|｜-−—")
        j = re.sub(r"[【】〔〕《》\[\]]", "", j).strip()
        if not (2 <= len(j) <= 20) or JOB_NG.search(j) or not JOB_WORDS.search(j):
            continue
        if j not in jobs:
            jobs.append(j)
    if not jobs:
        return None, "募集職種が抜けない"
    # 1行目：相手のページにある文字列だけで組む
    # 「正社員」「新卒採用」だけでは中身が無いので使わない。職種が抜けた会社だけ送る
    line = f"採用ページで{jobs[0]}の募集を拝見しました。"
    return {"insert": line, "jobs": jobs[:3],
            "mail": mails[0] if mails else ""}, None


async def main(limit):
    import aiohttp
    rows = [c for c in json.loads((RAW / "checked.json").read_text(encoding="utf-8"))
            if c.get("no_video")]
    rows = rows[:limit]
    print(f"下書き対象 {len(rows)}社")
    sem = asyncio.Semaphore(6)
    async with aiohttp.ClientSession(headers={"User-Agent": "so-creative outreach drafter"}) as s:
        async def one(c):
            async with sem:
                pages = []
                urls = list((c.get("checked_urls") or [])[:3])
                top = None
                for u in urls:
                    h = await get(s, u)
                    await asyncio.sleep(0.2)
                    if h:
                        pages.append(h)
                        if top is None:
                            top, top_url = h, u
                # 職種の表は採用トップの1階層奥に在ることが多いので降りる
                recs = (c.get("checked_urls") or [])[1:2]
                if recs and len(pages) > 1:
                    for u in job_detail_urls(pages[1], recs[0]):
                        h = await get(s, u)
                        await asyncio.sleep(0.2)
                        if h:
                            pages.append(h)
                # 送り先のためにお問い合わせ・会社概要も見る
                if top:
                    for u in contact_urls(top, top_url):
                        h = await get(s, u)
                        await asyncio.sleep(0.2)
                        if h:
                            pages.append(h)
                if not pages:
                    c["draft"], c["skip"] = None, "ページが取れない"
                    return c
                d, why = draft(c, pages)
                c["draft"], c["skip"] = d, why
                return c
        for i in range(0, len(rows), 100):
            await asyncio.gather(*(one(c) for c in rows[i:i + 100]))
            print(f"  {min(i+100,len(rows))}/{len(rows)}", flush=True)
    ok = [c for c in rows if c.get("draft")]
    ng = [c for c in rows if not c.get("draft")]
    import collections
    withmail = [c for c in ok if c["draft"]["mail"]]
    print(f"\n下書きできた {len(ok)}社 / 外した {len(ng)}社")
    anymail = [c for c in rows if c.get("mail_found")]
    print(f"   うち送り先（メール）が取れた {len(withmail)}社"
          f"（{len(withmail)*100//max(len(ok),1)}%）")
    print(f"   ＝ノールックでメール送信できる {len(withmail)}社／{len(rows)}社"
          f"（{len(withmail)*100//max(len(rows),1)}%）")
    print(f"   参考：職種に関係なくメールが在った会社 {len(anymail)}社"
          f"（{len(anymail)*100//max(len(rows),1)}%）")
    for why, n in collections.Counter(c.get("skip") for c in ng).most_common():
        print(f"   外した理由 {why}: {n}社")
    (RAW / "drafts.json").write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
    print("\n■ 下書きの例")
    for c in ok[:6]:
        print(f"  {c['name'][:18]:20} {c['pref']:5} 「{c['draft']['insert']}」"
              f"  連絡先 {c['draft']['mail'] or '—'}")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main(int(sys.argv[1]) if len(sys.argv) > 1 else 50)))
