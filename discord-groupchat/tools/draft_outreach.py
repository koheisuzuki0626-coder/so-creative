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
# 取得したページの控え。正規表現を直すたびに731社を取り直すと25分かかるので残す
CACHE = pathlib.Path("/tmp/so-draft-pages")

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
    r"([^\n<>｜|、。]{2,28})")
# 二段目。職種である必要はないが、営業文面Dの決めごとは
# 「相手の求人を読んだ**証拠**を1行」であって「本当のこと」ではない。
#
# 基準は本人が決めた：「見ずに書いても、拾った1語があるならいい」（2026-10-14）。
#   ＝相手のページから実際に拾った語が入っていること。これだと募集区分は通り、
#   何も拾っていない「採用ページを拝見しました」だけが落ちる。
#   ⚠️ 強い順に落とすこと。同じ会社に弱い1行を当ててはいけない。
#      ①募集職種（見ないと書けない・1社専用になりやすい）
#      ②社員インタビューの見出し（載せていない会社も多い・商品に直結する）
#      ③募集区分（拾った語ではあるが、採用ページがある会社なら全部に当てはまる）
#
# 社員インタビューは、載せていない会社も多いので見ないと書けない。
# しかも商品に直結する（撮影せずに、ある文章を映像の構成にできる）。
# 相手の見出しの言葉をそのまま使うので、文も1通りにならない。
# ⚠️ 2026-10-14：「◯◯の募集を拝見しました」と書く前に、相手が
#   「現在募集しておりません」と書いていないかを見る。94社のうち8社が該当した。
#   募集していない会社に「募集を拝見しました」は出せない。
#   インタビュー基準の1行は募集を主張しないので、この除外は掛けない。
NOHIRE_RE = re.compile(
    r"現在[^。]{0,10}(?:募集|採用)[^。]{0,14}(?:ございません|ありません|しており?ません|"
    r"行って?おりません|予定はありません)|募集(?:は)?(?:終了|停止|締切)")
KUBUN_RE = re.compile(r"(新卒採用|中途採用|キャリア採用|第二新卒|通年採用)")
VOICE_RE = re.compile(
    r">\s*((?:社員|先輩|スタッフ|職員|若手)(?:インタビュー|の声|紹介|を知る)|"
    r"働く(?:人|仲間|社員)|インタビュー)\s*<")
JOB_NG = re.compile(r"です|ます|ください|ご希望|方は|について|こちら|される|以下|下記|"
                    r"募集|採用|応募|ページ|内容|詳細|未定|なし")
# ⚠️ 2026-10-14：`[\w.+-]+@[\w-]+\.[\w.-]+` だと Googleフォントの
#   `wght@100..900` を宛先に採用した（存在しないアドレスに送るところだった）。
#   末尾を本物のTLDに限り、連続ドットを弾く。
# ⚠️ 末尾に \b を使ってはいけない。Pythonでは日本語も「語の文字」なので
#   「info@example.co.jpまでお願いします」の `jp` と `ま` の間に境界が立たず、
#   正規表現が戻って `.co` までで切った（実例：info@chuo-kensetsu.co）。
#   存在しないアドレスに送るところだった。英数字とドットが続かないことで見る。
MAIL_RE = re.compile(r"[A-Za-z0-9][\w.+-]{0,62}@(?:[A-Za-z0-9]"
                     r"(?:[A-Za-z0-9-]*[A-Za-z0-9])?\.)+[A-Za-z]{2,24}"
                     r"(?![A-Za-z0-9.-])")
MAILTO_RE_STRICT = True
# 代表アドレスを個人アドレスより先に使う
MAIL_GENERIC = re.compile(r"^(info|inquiry|contact|mail|office|soumu|somu|jinji|"
                          r"saiyo|saiyou|recruit|jinzai|hr|honsha|post|support)\b", re.I)
# ⚠️ 2026-10-14：49社を目で見たら5社が【別人の宛先】だった。読まずに送ったら事故。
#   佐賀県庁(pref.saga.lg.jp)／制作会社(onceinteractive.com)／
#   第三者の分析会社(infegy.com)／test@test.com／.co.jp の切れ残り(.co)。
#   原因は「ページに在るメールを何でも採る」こと。相手の会社のものだと言える根拠が要る。
#   採る条件：①相手のサイトと同じドメイン か ②プロバイダのアドレス（中小企業に多い）。
#   それ以外の会社ドメインは、誰か別の会社のものなので採らない。
MAIL_ISP = re.compile(
    r"@(?:[\w-]+\.)?(?:ocn\.ne\.jp|nifty\.com|plala\.or\.jp|biglobe\.ne\.jp|"
    r"so-net\.ne\.jp|wakwak\.com|ybb\.ne\.jp|"
    r"dion\.ne\.jp|cometweb\.ne\.jp|canvas\.ne\.jp|"
    r"enjoy\.ne\.jp|topaz\.ne\.jp|themis\.ocn\.ne\.jp|gaea\.ocn\.ne\.jp)$", re.I)
# 本人でないと分かっているもの
# ⚠️ 2026-10-14・47社を目で見て足した。どれも「ページに在った」が送り先ではない。
#   taro@／tarou@ はフォームの記入例（山田太郎）。1〜2文字は切れ残り。
#   security@・webmaster@ は技術担当で、営業を送る先ではない。
#   gmail・yahoo は、独自ドメインを持つ会社のページに在っても他人のものの疑いが強い
#   （実例：clbdemisodo02@gmail.com）。プロバイダのアドレス（ocn等）は中小企業の
#   自社用なので残す。
MAIL_NEVER = re.compile(
    r"@(?:test\.|example\.)|\.lg\.jp$|\.go\.jp$|@(?:pref|city)\.|"
    r"^(?:taro|tarou|tarow|yamada|hanako|sample|dummy|aaa+|xxx+|abc)[._\d-]*@|"
    r"[._-](?:taro|tarou|yamada|hanako)[._\d-]*@|"
    r"^(?:security|webmaster|postmaster|abuse|admin|root|hostmaster|noc)@|"
    r"^.{1,2}@|"
    r"@(?:gmail|yahoo|outlook|hotmail|icloud|aol|protonmail)\.", re.I)


def site_host(url):
    m = re.match(r"https?://([^/]+)", url or "")
    return (m.group(1).lower().replace("www.", "") if m else "")


def mail_is_theirs(mail, host):
    """その会社のアドレスだと言える根拠があるか。無ければ採らない。"""
    if MAIL_NEVER.search(mail):
        return False
    dom = mail.rsplit("@", 1)[-1].lower()
    if host and (dom == host or host.endswith("." + dom) or dom.endswith("." + host)):
        return True
    # 会社名の部分が共通（example.co.jp ↔ mail.example.com）
    core = host.split(".")[0] if host else ""
    if core and len(core) >= 4 and core in dom:
        return True
    return bool(MAIL_ISP.search("@" + dom))
# 送り先。mailto: のほうが本文中の文字列より確実なので先に見る
MAILTO_RE = re.compile(r"mailto:([A-Za-z0-9][\w.+-]{0,62}@(?:[A-Za-z0-9]"
                       r"(?:[A-Za-z0-9-]*[A-Za-z0-9])?\.)+[A-Za-z]{2,24})"
                       r"(?![A-Za-z0-9.-])", re.I)
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
    nohire = bool(NOHIRE_RE.search(joined))
    raw = " ".join(pages)
    bad = re.compile(r"(example|sentry|sample|noreply|no-reply|\.png|\.jpg|\.gif|"
                     r"wixpress|cdn|googlegroups|googleapis|u003e|\.\.)", re.I)
    mails = [m for m in MAILTO_RE.findall(raw) if not bad.search(m)]
    mails += [m for m in MAIL_RE.findall(joined) if not bad.search(m) and m not in mails]
    # info@ のような代表アドレスを、個人名のアドレスより先に
    host = site_host((c.get("checked_urls") or [""])[0])
    mails = [m for m in mails if mail_is_theirs(m, host)]
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
        # 「①土木技術者」「(1)製造」の番号を落とす
        j = re.sub(r"^(?:[①-⑳]|\(\d\)|\d[.)]|[・･])\s*", "", j).strip()
        # 「総合職：複数の職種を経験し…」のように説明が続くので手前で切る
        j = re.split(r"[：:]", j)[0].strip()
        # 括弧が閉じていないのは切れている（実例：「設計職（ハードウェア」）
        if j.count("（") != j.count("）") or j.count("(") != j.count(")"):
            j = re.split(r"[（(]", j)[0].strip()
        # ⚠️ ここに「上限いっぱいなら捨てる」を置いてはいけない。上限を28字に広げた分
        #    普通の職種まで上限に当たり、174社→63社まで落ちた（2026-10-14 実測）。
        #    切れの検出は【括弧が閉じていない】と【：以降は説明】の2つで足りる。
        if not (2 <= len(j) <= 24) or JOB_NG.search(j) or not JOB_WORDS.search(j):
            continue
        if j not in jobs:
            jobs.append(j)
    if not jobs:
        # 二段目：社員インタビュー。トップを除いた＝採用ページ以降だけを見る
        has_rec = len(c.get("checked_urls") or []) > 1
        voice = VOICE_RE.findall(" ".join(pages[1:]))
        if voice and has_rec:
            line = f"採用ページの{voice[0]}を拝見しました。"
            return {"insert": line, "jobs": [], "voice": voice[0], "kubun": "",
                    "mail": c.get("mail_found", "")}, None
        kubun = KUBUN_RE.findall(joined)
        if kubun and has_rec and not nohire:
            line = f"採用ページで{kubun[0]}の募集を拝見しました。"
            return {"insert": line, "jobs": [], "voice": "", "kubun": kubun[0],
                    "mail": c.get("mail_found", "")}, None
        # 四段目：拾う語が無い会社。「採用ページを拝見しました」とだけ書く（本人の判断）。
        # ⚠️ 2026-10-14 実測：ここに落ちる22社のうち7社は出してはいけない側だった。
        #   「現在募集しておりません」1社／採用ページに文字がほとんど無い2社
        #   （画像かJS。阿部土建は本文107字）／urlが /recruit/ なだけで採用の話が
        #   出てこない4社。この層は【こちらの読み取りが効いていない会社】なので、
        #   「動画が見当たらない」という元の判定自体も当てになりにくい。
        rec = " ".join(text_of(h) for h in pages[1:])
        if (has_rec and not nohire and len(rec) >= 800
                and rec.count("採用") + rec.count("募集") >= 3):
            return {"insert": "採用ページを拝見しました。", "jobs": [], "voice": "",
                    "kubun": "", "plain": True,
                    "mail": c.get("mail_found", "")}, None
        return None, "拾える語が1つも無い"
    # 1行目：相手のページにある文字列だけで組む
    if nohire:
        return None, "募集していないと書いてある"
    # 「正社員」「新卒採用」だけでは中身が無いので使わない。職種が抜けた会社だけ送る
    line = f"採用ページで{jobs[0]}の募集を拝見しました。"
    return {"insert": line, "jobs": jobs[:3], "voice": "", "kubun": "",
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
                cf = CACHE / (re.sub(r"\W+", "_", c["name"])[:60] + ".txt")
                if cf.exists():
                    pages = cf.read_text(encoding="utf-8").split("\x00")
                    d, why = draft(c, pages)
                    c["draft"], c["skip"] = d, why
                    return c
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
                CACHE.mkdir(parents=True, exist_ok=True)
                cf.write_text("\x00".join(pages), encoding="utf-8")
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
