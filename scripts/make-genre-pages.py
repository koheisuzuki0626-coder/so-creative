"""ジャンルごとのページをつくる（2026-09-24）。

    python3 scripts/make-genre-pages.py

company-video.html を骨組みにして、ジャンルごとの中身を差し込む。
骨組み（head の共通部分・ナビ・フッター・スクリプト）は company-video.html から
そのまま取るので、そちらを直せばこちらにも反映される。**手で7ページを直さない。**

中身は works.html の各ジャンルの注記から起こしたもので、
作っていないものは書かない（「毎日分析しています」のような文はリサーチのある
ジャンルにしか置かない）。
"""
import re, pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
BASE = 'https://koheisuzuki0626-coder.github.io/so-creative'
src = (ROOT / 'company-video.html').read_text(encoding='utf-8')

# ---- 骨組みを切り出す ----
head_top = src[:src.index('    <title>')]
head_mid = src[src.index('    <link rel="icon"'):src.index('    <script type="application/ld+json">')]
head_rest = src[src.index('    <script>document.documentElement.classList.add'):src.index('        <section class="page-head">')]
tail = src[src.index('        </section>\n    </main>') + len('        </section>\n'):]
# sample.js は「AIナレーションあり／なし」の切り替え用で、#sample-video が
# 無ければ即 return する。生成ページにその UI は無いので読み込まない
# （骨組み元の company-video.html には在るため、そのままだと混入する）。
tail = tail.replace('    <script src="assets/sample.js" defer></script>\n', '')
# sample.js は「AIナレーションあり／なし」の切り替え用で、#sample-video が
# 無ければ即 return する。生成ページにその UI は無いので読み込まない
# （骨組み元の company-video.html には在るため、そのままだと混入する）。
tail = tail.replace('    <script src="assets/sample.js" defer></script>\n', '')

PRICE_NOTE = ('<p class="body-text measure" style="margin-top:14px">'
              '<b>この表はナレーション込みの額です。</b>梅・竹は<b>AIナレーション</b>が、'
              '松は<b>人に読んでもらうぶん1名</b>が含まれています。'
              'ナレーションを入れない（テロップだけにする）場合は、<b>1本につき ¥25,000 を引きます</b>。'
              '松で人ではなくAIにする場合は <b>¥70,000</b> 引きです。'
              '<a href="pricing.html#plans">料金ページの計算機</a>で、その組み合わせの実額が出ます。</p>')

# 料金モデル。tests/lib.mjs の PRICE.base / TIERS[].perSec と同じ値にすること。
# 秒単価は段ごとに1つ（2026-10-14 に逓減をやめた。お客様から見て分かりにくかった）。
# 短尺を下げるのは基本料金で達成している（¥180,000 → ¥120,000）。
# ⚠️ 秒単価を上げて基本料金を下げる形にしないこと。複数本×長尺で値上がりする。
BASEP = 120000
PER = {'ume': 4000, 'take': 5400, 'matsu': 8000}


def list_price(t, sec):
    """表に載せる「1本・ナレーションの増減なし」の値段"""
    return BASEP + PER[t] * sec
LAB = {15: '15秒', 30: '30秒', 60: '60秒', 90: '90秒', 180: '3分', 264: '4分24秒'}


def iso_dur(sec):
    """秒を ISO 8601 の duration にする。
    ⚠️ "PT264S" も規格上は正しいが、検索エンジンの表示で分に直されない例が
    あるので、60秒以上は分と秒に割る。"""
    m, r = divmod(int(sec), 60)
    if not m:
        return f'PT{r}S'
    return f'PT{m}M{r}S' if r else f'PT{m}M'
yen = lambda n: '¥' + format(n, ',')


def price_table(secs, heads):
    rows = ''.join(
        f'\n                        <tr><th scope="row">{LAB[s]}</th>'
        + ''.join(f'<td>{yen(list_price(t, s))}</td>' for t in ('ume', 'take', 'matsu'))
        + '</tr>' for s in secs)
    return f'''                <div class="compare-wrap" tabindex="0" role="region" aria-label="尺ごとの料金の表（横にスクロールできます）">
                <table class="compare">
                    <thead><tr><th scope="col">尺（1本）</th><th scope="col">梅（{heads[0]}）</th><th scope="col">竹（{heads[1]}）</th><th scope="col">松（{heads[2]}）</th></tr></thead>
                    <tbody>{rows}
                    </tbody>
                </table>
                </div>
                <p class="swipe-hint">横にスクロールすると、表の続きが見られます。</p>
                {PRICE_NOTE}'''


def compare_table(rows):
    body = ''.join(
        f'\n                        <tr><th scope="row">{a}</th><td class="old">{b}</td><td class="new">{c}</td></tr>'
        for a, b, c in rows)
    return f'''                <div class="compare-wrap" tabindex="0" role="region" aria-label="撮影する場合との比較の表（横にスクロールできます）">
                <table class="compare">
                    <thead><tr><th scope="col"></th><th scope="col">撮影してつくる場合</th><th scope="col">so-creative</th></tr></thead>
                    <tbody>{body}
                    </tbody>
                </table>
                </div>
                <p class="swipe-hint">横にスクロールすると、表の続きが見られます。</p>'''


def build(g):
    measured_section = measured(g)
    url = f'{BASE}/{g["file"]}'
    ld_offers = '' if g.get('no_price') else f''',
        "offers": {{
          "@type": "AggregateOffer",
          "priceCurrency": "JPY",
          "lowPrice": "{list_price('ume', g['secs'][0])}",
          "highPrice": "{list_price('matsu', g['secs'][-1])}",
          "offerCount": "{len(g['secs']) * 3}"
        }}'''
    # 縦型は 16:9 の箱に入れると左右が黒帯になる。CSS の .is-vertical が
    # 9:16 に直して幅を絞る。works.html では前から付いていたが、ジャンルページの
    # 生成側には無く、SNSのサンプルがずっと黒帯のまま出ていた（2026-10-20 に気づいた）。
    vcls = ' is-vertical' if g.get('vertical') else ''
    # 2本目以降のサンプル（g['extra']）。構造化データにも1本ずつ VideoObject を出す。
    # ⚠️ 1ジャンル1本という前提を 2026-10-20 に外した（SNSに2本目を足したため）。
    #    「本数を重ねる運用に向く」と書いているジャンルの実例が1本しかないのは、
    #    主張と中身が合っていなかった。extra が無いジャンルは今までどおり。
    ld_extra = ''.join(f''',
      {{
        "@type": "VideoObject",
        "name": "{g['label']}のサンプル（{LAB[x['sec']]}）{x['ld_suffix']}",
        "description": "{x['ld']}",
        "thumbnailUrl": "{BASE}/{x['poster']}",
        "contentUrl": "{BASE}/{x['video']}",
        "duration": "{iso_dur(x['sec'])}",
        "uploadDate": "{x['upload_date']}",
        "publisher": {{ "@id": "{BASE}/#org" }}
      }}''' for x in g.get('extra', []))
    # 実例の節に続けて出す2本目以降。
    # ⚠️ 見出しは h3。p に見た目だけ付けると、読み上げで2本目の始まりが分からない。
    #    .eyebrow は既にある小見出しの見た目なので、CSS は足さない。
    # 1本目にも札を付ける（2本あるときだけ）。付けないと2本が地続きに見える。
    first_label = (f'''
                <h3 class="eyebrow">{g['first_head']}</h3>''' if g.get('extra') else '')
    extra_html = ''.join(f'''
                <h3 class="eyebrow" style="margin-top:38px">{x['head']}</h3>
                <p class="body-text measure">{x['lead']}</p>
                <figure class="sample reveal">
                    <video class="sample-video{vcls}" controls preload="none" playsinline
                           poster="{x['poster']}"
                           src="{x['video']}"
                           aria-label="{g['label']}のサンプル {LAB[x['sec']]}{x['ld_suffix']}">
                        お使いのブラウザでは再生できません。
                    </video>
                </figure>
                <p class="genre-note"><b>{x['specs']}</b>（書き出したファイルを実測した値）</p>''' for x in g.get('extra', []))
    ld = f'''    <script type="application/ld+json">
    {{
      "@context": "https://schema.org",
      "@graph": [
      {{
        "@type": "Service",
        "@id": "{url}#service",
        "name": "{g['service']}",
        "serviceType": "{g['service']}",
        "provider": {{ "@id": "{BASE}/#org" }},
        "areaServed": [
          {{ "@type": "AdministrativeArea", "name": "愛知県" }},
          {{ "@type": "AdministrativeArea", "name": "岐阜県" }},
          {{ "@type": "AdministrativeArea", "name": "三重県" }},
          {{ "@type": "Country", "name": "日本" }}
        ],
        "description": "{g['ld_desc']}"{ld_offers}
      }},
      {{
        "@type": "VideoObject",
        "name": "{g['label']}のサンプル（{LAB[g['sample_sec']]}）",
        "description": "{g['ld_video']}",
        "thumbnailUrl": "{BASE}/{g['poster']}",
        "contentUrl": "{BASE}/{g['video']}",
        "duration": "{iso_dur(g['sample_sec'])}",
        "uploadDate": "{g.get('upload_date', '2026-09-20')}",
        "publisher": {{ "@id": "{BASE}/#org" }}
      }}{ld_extra},
      {{
        "@type": "BreadcrumbList",
        "itemListElement": [
        {{ "@type": "ListItem", "position": 1, "name": "ホーム", "item": "{BASE}/" }},
        {{ "@type": "ListItem", "position": 2, "name": "{g['service']}", "item": "{url}" }}
        ]
      }}
      ]
    }}
    </script>
'''
    meta = f'''    <title>{g['title']}</title>
    <meta name="description" content="{g['desc']}">
    <meta property="og:title" content="{g['og_title']}">
    <meta property="og:description" content="{g['og_desc']}">
    <meta property="og:type" content="website">
    <link rel="canonical" href="{url}">
    <meta property="og:url" content="{url}">
'''
    price_section = '' if g.get('no_price') else f'''
        <section class="section section-alt">
            <div class="wrap reveal">
                <h2 class="headline">料金</h2>
                <p class="body-text measure">尺と本数で決まります。表示はすべて税込で、<b>消費税は申し受けません</b>（適格請求書発行事業者の登録なし）。出演者の手配費・撮影費は一切かかりません。</p>
{price_table(g['secs'], g['tier_heads'])}
                <p class="body-text measure" style="margin-top:18px">{g['price_note']}</p>
                <p class="body-text measure"><b>2本目以降は、制作費 ¥100,000 とその本の尺ぶんだけが乗ります（企画・構成費は1案件に1回なので、2本目にはかかりません）。</b>{g['second_note']}</p>
                <div class="genre-calc">
                    <p class="genre-calc-head">条件を変えて、いくらになるか</p>
                    <div class="calc" data-calc-len="{g['sample_sec']}" data-calc-id="{g['uid']}" data-calc-where="page-{g['uid']}"></div>
                </div>
            </div>
        </section>
'''
    if g.get('no_price'):
        price_section = f'''
        <section class="section section-alt">
            <div class="wrap reveal">
                <h2 class="headline">料金</h2>
                <p class="body-text measure">{g['price_note']}</p>
            </div>
        </section>
'''
    main = f'''        <section class="page-head">
            <div class="wrap reveal">
                <p class="eyebrow">{g['eyebrow']}</p>
                <h1 class="display">{g['h1']}</h1>
                <p class="lead-line about-lead">{g['lead']}</p>
            </div>
        </section>

        <section class="section section-alt">
            <div class="wrap reveal">
                <h2 class="headline">つくった実例（{LAB[g['sample_sec']]}）</h2>{first_label}
                <p class="body-text measure">{g['sample_lead']}</p>
                <figure class="sample reveal">
                    <video class="sample-video{vcls}" controls preload="none" playsinline
                           poster="{g['poster']}"
                           src="{g['video']}"
                           aria-label="{g['label']}のサンプル {LAB[g['sample_sec']]}">
                        お使いのブラウザでは再生できません。
                    </video>
                </figure>
                <p class="genre-note"><b>{g['specs']}</b>（書き出したファイルを実測した値）</p>{extra_html}
                <p class="body-text measure" style="margin-top:14px">ほかのジャンルのサンプルは<a href="works.html#{g['anchor']}">制作サンプルのページ</a>にまとめています。</p>
            </div>
        </section>

        <section class="section">
            <div class="wrap reveal">
                <h2 class="headline">撮影をやめると、何が消えるか</h2>
{compare_table(g['compare'])}
                <p class="body-text measure" style="margin-top:18px">{g['compare_note']}</p>
            </div>
        </section>

        <section class="section section-alt">
            <div class="wrap reveal">
                <h2 class="headline">{g['how_head']}</h2>
                <p class="body-text measure">{g['how_lead']}</p>
                <ul class="calc-why">
{g['how_items']}
                </ul>
            </div>
        </section>
{measured_section}

        <section class="section">
            <div class="wrap reveal">
                <h2 class="headline">できないことも書いておきます</h2>
                <p class="body-text measure">AIで映像をつくる以上、向かないものがあります。先にお伝えします。</p>
                <ul class="calc-why">
{g['cant_items']}
                </ul>
                <p class="body-text measure" style="margin-top:16px">{g['cant_note']}</p>
            </div>
        </section>
{price_section}
        <section class="section">
            <div class="wrap reveal">
                <h2 class="headline">進め方</h2>
                <ul class="calc-why">
                    <li><b>1. ヒアリング</b>誰に何を伝えたいかを伺います。資料がなくても構いません。オンラインで30分ほど。</li>
                    <li><b>2. 構成案と絵コンテ</b>何をどの順番で見せるかを、実際の画でお見せします。<b>ここでご確認いただいてから制作に入ります。</b></li>
                    <li><b>3. 制作</b>生成・選別・編集。テロップとBGMまで込みです。</li>
                    <li><b>4. ご確認と修正</b>段階に応じて2〜3回まで無料です（一般的には2回まで、3回目から1回 ¥3〜10万が相場）。</li>
                    <li><b>5. 納品</b>MP4（{g['delivery']}）。用途の制限はありません。</li>
                </ul>
                <p class="body-text measure" style="margin-top:16px">{g['lead_note']}</p>
            </div>
        </section>

        <section class="cta-band" id="contact">
            <div class="wrap reveal">
                <p class="eyebrow">Contact</p>
                <h2 class="display">{g['cta_h']}</h2>
                <p class="body-text measure" style="margin-top:28px;">{g['cta_lead']}<a href="works.html">他のジャンルのサンプル</a>もご覧いただけます。</p>
                <a class="cta-mail" href="mailto:bonvoyage.ti@icloud.com">bonvoyage.ti@icloud.com</a>
                <p class="cta-actions"><a class="pill pill-invert" href="mailto:bonvoyage.ti@icloud.com">メールで相談する</a></p>
                <p class="cta-hint"><strong>名古屋市</strong>を拠点に、<strong>愛知・岐阜・三重</strong>を中心としてご相談を承っています。打ち合わせはオンラインで完結し、全国どこからでもご依頼いただけます。</p>
            </div>
        </section>
'''
    # 用途の帯は company-video.html の骨組みから来るので、
    # aria-current をこのページへ付け替える（付いたままだと全ページが「会社紹介」になる）
    nav = head_rest
    nav = nav.replace(' aria-current="page"', '')
    nav = nav.replace(f'<a href="{g["file"]}">', f'<a href="{g["file"]}" aria-current="page">')
    page = head_top + meta + head_mid + ld + nav + main + tail
    # 計算機を置くページは pricing.js も読む。
    # 骨組み（company-video.html）が既に読んでいるなら足さない。
    # 2026-09-25：ここで二重に足していて、6ページで計算機が2回初期化され、
    # 段と本数の選択肢が二重に生えていた。
    if not g.get('no_price') and 'assets/pricing.js' not in page:
        page = page.replace('    <script src="assets/funnel.js" defer></script>',
                            '    <script src="assets/funnel.js" defer></script>\n'
                            '    <script src="assets/pricing.js" defer></script>')
    # ミュージックビデオは計算機を置かないので、骨組みから来た pricing.js を外す
    if g.get('no_price'):
        page = page.replace('\n    <script src="assets/pricing.js" defer></script>', '')
    return page


from genre_data import GENRES  # noqa: E402

def measured(g):
    """実測の節。measured_items を持つジャンルだけ出す。
    ⚠️ 母数が少ないジャンルには数字を出さないこと。公開する数字としては弱く、
    載せると他ページの信頼まで下げる。

    2026-10-13：社内向けは「社内報12本・研修18本」しか見ておらず、付けなかった。
    2026-10-14：マニュアル動画85本が別のお題で貯まっていたので、
    合計115本（マニュアル85・研修18・社内広報12）として付けた。本人の判断。
    内訳をリード文に書いてあるので、聞かれても答えられる。"""
    if not g.get('measured_items'):
        return ''
    return f"""
        <section class="section measured">
            <div class="wrap reveal">
                <h2 class="headline">{g['measured_head']}</h2>
                <p class="body-text measure">{g['measured_lead']}</p>
                <ul class="calc-why">
{g['measured_items']}
                </ul>
            </div>
        </section>
"""


for g in GENRES:
    (ROOT / g['file']).write_text(build(g), encoding='utf-8')
    print('書き出し:', g['file'])
