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

PRICE_NOTE = ('<p class="body-text measure" style="margin-top:14px">'
              '<b>この表はナレーション込みの額です。</b>梅・竹は<b>AIナレーション</b>が、'
              '松は<b>人に読んでもらうぶん1名</b>が含まれています。'
              'ナレーションを入れない（テロップだけにする）場合は、<b>1本につき ¥25,000 を引きます</b>。'
              '松で人ではなくAIにする場合も ¥25,000 引きです。'
              '<a href="pricing.html#plans">料金ページの計算機</a>で、その組み合わせの実額が出ます。</p>')

BASEP, PER = 90000, {'ume': 3500, 'take': 4900, 'matsu': 6650}
LAB = {15: '15秒', 30: '30秒', 60: '60秒', 90: '90秒', 180: '3分'}
yen = lambda n: '¥' + format(n, ',')


def price_table(secs, heads):
    rows = ''.join(
        f'\n                        <tr><th scope="row">{LAB[s]}</th>'
        + ''.join(f'<td>{yen(BASEP + PER[t] * s)}</td>' for t in ('ume', 'take', 'matsu'))
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
    url = f'{BASE}/{g["file"]}'
    ld_offers = '' if g.get('no_price') else f''',
        "offers": {{
          "@type": "AggregateOffer",
          "priceCurrency": "JPY",
          "lowPrice": "{BASEP + PER['ume'] * g['secs'][0]}",
          "highPrice": "{BASEP + PER['matsu'] * g['secs'][-1]}",
          "offerCount": "{len(g['secs']) * 3}"
        }}'''
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
        "duration": "PT{g['sample_sec']}S",
        "uploadDate": "2026-09-20",
        "publisher": {{ "@id": "{BASE}/#org" }}
      }},
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
                <p class="body-text measure"><b>2本目以降は ¥65,000 です。</b>{g['second_note']}</p>
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
                <h2 class="headline">つくった実例（{LAB[g['sample_sec']]}）</h2>
                <p class="body-text measure">{g['sample_lead']}</p>
                <figure class="sample reveal">
                    <video class="sample-video" controls preload="none" playsinline
                           poster="{g['poster']}"
                           src="{g['video']}"
                           aria-label="{g['label']}のサンプル {LAB[g['sample_sec']]}">
                        お使いのブラウザでは再生できません。
                    </video>
                </figure>
                <p class="genre-note"><b>{g['specs']}</b>（書き出したファイルを実測した値）</p>
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
    page = head_top + meta + head_mid + ld + head_rest + main + tail
    # 計算機を置くページは pricing.js も読む
    if not g.get('no_price'):
        page = page.replace('    <script src="assets/funnel.js" defer></script>',
                            '    <script src="assets/funnel.js" defer></script>\n'
                            '    <script src="assets/pricing.js" defer></script>')
    return page


from genre_data import GENRES  # noqa: E402

for g in GENRES:
    (ROOT / g['file']).write_text(build(g), encoding='utf-8')
    print('書き出し:', g['file'])
