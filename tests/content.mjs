/* 文言と実装がズレていないか。
   同じことを複数箇所に書いているので、片方だけ直すと嘘になる。
   ここはその突き合わせ専用。 */
import { check, report, open, BASE, PW, TIERS, LENGTHS, leadWeeks } from './lib.mjs';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
const pwmod = (await import(PW)).default;
const ROOT = fileURLToPath(new URL('..', import.meta.url)).replace(/\/$/, '');
const browser = await pwmod.chromium.launch();
const page = await open(browser, {});
const idx = readFileSync(`${ROOT}/index.html`, 'utf8');
const about = readFileSync(`${ROOT}/about.html`, 'utf8');
const privacy = readFileSync(`${ROOT}/privacy.html`, 'utf8');

/* ---- 構造化データが画面と一致するか ---- */
const ld = await page.evaluate(() => [...document.querySelectorAll('script[type="application/ld+json"]')]
    .map(s => JSON.parse(s.textContent)));
const faqLd = ld.find(d => d['@type'] === 'FAQPage')?.mainEntity || [];
const faqUi = await page.locator('#faq .faq-item').evaluateAll(els => els.map(e => ({
    q: e.querySelector('summary').textContent.trim(),
    a: e.querySelector('.faq-a').textContent.trim() })));
check('FAQ の件数が画面と構造化データで一致', faqLd.length === faqUi.length, `${faqLd.length}/${faqUi.length}`);
check('FAQ の文言が画面と構造化データで一致',
    faqUi.every((u, i) => faqLd[i]?.name === u.q && faqLd[i]?.acceptedAnswer?.text === u.a),
    JSON.stringify(faqUi.map((u, i) => faqLd[i]?.name === u.q)));
check('閉じていても本文が読める(クローラ対策)', faqUi.every(u => u.a.length > 30));
/* 縦型は段の特典ではなく別の1本。機械で切らないことを明記しているか */
check('縦型の扱いを FAQ で説明している',
    faqUi.some(u => /縦型/.test(u.q) && /設計し直します/.test(u.a) && /2本/.test(u.a)));
check('サイト本文に落とした仕様が残っていない',
    !/ちらつき除去|正方形/.test(idx), (idx.match(/ちらつき除去|正方形/) || [''])[0]);
/* 4K は画面から完全に外した（2026-09-16）。生成そのものが 1080p で、4K は完成品に
   アップスケーラをかけただけ。出せない品質を書かないので、画面のどこにも出さない */
const bodyText = await page.locator('body').innerText();
check('画面のどこにも 4K と書いていない', !/4K/.test(bodyText), (bodyText.match(/.{0,20}4K.{0,20}/) || [''])[0]);
check('画質は 1080p と書いてある', /1080p（フルHD）/.test(bodyText));
/* 制作の流れに置いていた「実例」（3日間・54回生成・4往復）は外した（2026-09-17）。
   代わりに、内部の生成回数や工数を客先の画面に出していないことだけを見る */
{
    const proc = await page.locator('#process').innerText();
    check('制作の流れに生成回数を出していない', !/回生成|カットを採用/.test(proc), proc.slice(0, 60));
    check('制作の流れに実工数（時間）を出していない', !/11\.5h|実工数/.test(proc));
    check('架空クライアントの名前を出していない', !/想工業/.test(proc));
}
/* 実績の先頭に置いた会社紹介のサンプル。自前ホスティングで、
   架空の題材だと分かる書き方になっていること（クライアント実績に見せない） */
{
    const works = await page.locator('#genres').innerText();
    const v = page.locator('.sample-video');
    check('ジャンルのカードにサンプル映像が入っている', (await v.count()) >= 1);
    /* 06 展示会は、同じ案件を無音・テロップ主体で別設計した1本。
       「短く切っただけではない」という主張の裏づけとして置いている */
    check('展示会のカードにもサンプルがある',
        (await page.locator('#genre-event .sample-video').count()) === 1);
    check('展示会のサンプルは無音だと書いてある',
        /15秒・無音/.test(await page.locator('#genre-event').innerText()));
    check('展示会のサンプルは実際に音が入っていない', await page.locator('#genre-event .sample-video').evaluate((v) => v.muted === true));
    /* 02 サービス紹介と 04 広告CM のサンプル（2026-09-17 追加）。
       どちらも架空の題材で、クライアント実績には見せない書き方になっていること */
    check('サービス紹介のカードにサンプルがある',
        (await page.locator('#genre-service .sample-video').count()) === 1);
    check('サービス紹介のサンプルは架空の題材だと書いてある',
        /架空の業務ソフト/.test(await page.locator('#genre-service').innerText()));
    check('広告CMのカードにサンプルがある',
        (await page.locator('#genre-ad .sample-video').count()) === 1);
    check('広告CMのサンプルは架空の題材だと書いてある',
        /架空の冷凍餃子/.test(await page.locator('#genre-ad').innerText()));
    check('追加した2本も自前で配信している',
        /assets\/works\/service-15s\.mp4/.test(idx) && /assets\/works\/cm-15s-taste\.mp4/.test(idx));
    check('追加した2本にもポスター画像がある',
        /poster="assets\/works\/service-15s\.jpg"/.test(idx)
        && /poster="assets\/works\/cm-15s-taste\.jpg"/.test(idx));
    /* 05 SNSショートと 07 社内向けのサンプル（2026-09-17 追加）。
       05 は最初から縦型で組んでいるので、16:9 のまま出していないことも見る */
    check('SNSショートのカードにサンプルがある',
        (await page.locator('#genre-sns .sample-video').count()) === 1);
    check('SNSショートのサンプルは架空の題材だと書いてある',
        /架空のコインランドリー/.test(await page.locator('#genre-sns').innerText()));
    check('SNSショートのサンプルは縦型で表示している',
        (await page.locator('#genre-sns .sample-video.is-vertical').count()) === 1
        && await page.locator('#genre-sns .sample-video').evaluate(
            (v) => v.clientHeight > v.clientWidth));
    check('社内向けのカードにサンプルがある',
        (await page.locator('#genre-internal .sample-video').count()) === 1);
    check('社内向けのサンプルは架空の題材だと書いてある',
        /架空の倉庫/.test(await page.locator('#genre-internal').innerText()));
    check('さらに追加した2本も自前で配信している',
        /assets\/works\/sns-15s-vertical\.mp4/.test(idx)
        && /assets\/works\/internal-15s\.mp4/.test(idx));
    check('さらに追加した2本にもポスター画像がある',
        /poster="assets\/works\/sns-15s-vertical\.jpg"/.test(idx)
        && /poster="assets\/works\/internal-15s\.jpg"/.test(idx));
    /* 03 採用の3分版（2026-09-17 追加）。他のサンプルが15秒〜60秒なので、
       尺が違うことが分かる書き方になっていること */
    check('採用のカードにサンプルがある',
        (await page.locator('#genre-recruit .sample-video').count()) === 1);
    check('採用のサンプルは架空の題材だと書いてある',
        /架空の製造業/.test(await page.locator('#genre-recruit').innerText()));
    check('採用のサンプルは3分だと書いてある',
        /サンプル（3分）/.test(await page.locator('#genre-recruit').innerText()));
    check('採用のサンプルも自前で配信している',
        /assets\/works\/recruit-3min\.mp4/.test(idx));
    check('採用のサンプルにもポスター画像がある',
        /poster="assets\/works\/recruit-3min\.jpg"/.test(idx));
    /* 7ジャンル全部にサンプルが入った。1つでも欠けたらここが落ちる */
    check('7ジャンル全部にサンプルが入っている',
        (await page.locator('.genre .sample-video').count()) === 7);
    check('サンプルは「01 会社紹介」のカードの中にある',
        (await page.locator('#genre-company .sample-video').count()) === 1
        && (await page.locator('#works .sample-video').count()) === 0);
    check('サンプルは自前で配信している（YouTube 埋め込みではない）',
        /assets\/works\/company-60s-telop\.mp4/.test(idx) && !/youtube\.com\/embed/.test(idx));
    check('ポスター画像を指定している（読み込み前に真っ黒にしない）',
        /poster="assets\/works\/company-60s\.jpg"/.test(idx));
    check('サンプルだと分かる見出しになっている', /サンプル（60秒）/.test(works));
    /* 段の差（松はナレーション込み・梅竹は¥30,000で追加）を納品物そのもので確かめられる。
       同じ映像で音だけ差し替える。ナレーションは最終版（2026-09-17 差し替え） */
    check('ナレーションあり／なしを切り替えられる',
        (await page.locator('.sample-sw').count()) === 2);
    /* この音声は合成音声。人が読んだものと誤解されると、
       人物ナレーション（1名 ¥70,000〜）の見積りがずれる */
    check('サンプルの音声がAIだとボタンに書いてある',
        /AIナレーションあり/.test(await page.locator('.sample-switch').innerText()));
    check('サンプルの音声がAIだと注釈にも書いてある',
        /このナレーションはAI音声です/.test(await page.locator('#genre-company').innerText()));
    check('初期表示はテロップ版', /company-60s-telop\.mp4"/.test(idx));
    check('切り替えで実際に音源が変わる', await (async () => {
        const v = page.locator('#sample-video');
        const before = await v.getAttribute('src');
        await page.locator('.sample-sw', { hasText: 'ナレーションあり' }).click();
        await page.waitForTimeout(400);
        const after = await v.evaluate((e) => e.getAttribute('src'));
        await page.locator('.sample-sw', { hasText: 'ナレーションなし' }).click();
        await page.waitForTimeout(200);
        return before !== after && /narration/.test(after);
    })());
    check('差し替え前の古いナレーション版を残していない', !/company-60s\.mp4/.test(idx));
    /* 人物ナレーションの額は、実績の注釈・FAQ・計算機の3か所に出る。
       どれかだけ直すとここが落ちる */
    check('人物ナレーションの値段が実績でも料金表と同じ', /1名 ¥70,000〜/.test(works));
    check('AIナレーションが込みだと実績にも書いてある', /全段とも料金に含まれます/.test(works));
    check('架空の題材だと書いてある', /架空の製造業を題材に/.test(works));
    check('架空クライアントの名前を出していない', !/想工業/.test(works));
}
check('人物ナレーションの追加料金が FAQ と計算機で同じ',
    /1名 ¥70,000〜/.test(idx) && /narrationHuman: 70000/.test(idx));
/* AIを有料に戻すときは、ここと計算機と文言を必ず一緒に直す */
check('AIナレーションが計算機でも ¥0 になっている', /narrationAi: 0/.test(idx));
/* AIを込みにした代わりに、使わないときは引く。額は3か所で揃っていること */
check('ナレーションなしの差し引きが計算機と文言で同じ',
    /noNarration: 25000/.test(idx) && /−¥25,000/.test(idx) && /−\u00a525,000|¥25,000 を差し引き/.test(idx));

const org = ld.find(d => d['@graph'])?.['@graph']?.find(x => x['@type'] === 'Organization') || {};
check('構造化データに代表者', org.founder?.name === '鈴木 宏平');
check('構造化データの所在地は市区町村まで',
    org.address?.addressRegion === '愛知県' && org.address?.addressLocality === '名古屋市' && !org.address?.streetAddress);
check('未確定の情報を入れていない', !/foundingDate|postalCode|streetAddress/.test(JSON.stringify(ld)));
check('電話番号を載せていない', !org.telephone && !/090-2968-9616|tel:/.test(idx + about + privacy));
check('SNS が sameAs に入っている',
    (org.sameAs || []).includes('https://www.instagram.com/so_maru_official/')
    && (org.sameAs || []).some(u => u.includes('youtube.com/@hzrinrng')));
check('共有トークンを貼っていない', !/stkn=|utm_source=/.test(idx + about + privacy));

/* ---- 会社概要 ---- */
const rows = await (await open(browser, { page: 'about.html' })).locator('#company .about-facts > div')
    .evaluateAll(els => els.map(e => [e.querySelector('dt').textContent.trim(), e.querySelector('dd').textContent.trim()]));
check('会社概要に項目がある', rows.length >= 5, `${rows.length}項目`);
check('見出しと中身が対になっている', rows.every(([k, v]) => k && v));
check('未記入のまま公開していない', !rows.some(([k, v]) => /[◯○●]{2,}|（氏名）|000-0000|TODO|未定/.test(k + v)));
check('会社概要と構造化データが一致',
    rows.some(([k, v]) => k === '代表者' && v === '鈴木 宏平')
    && rows.some(([k, v]) => k === '所在地' && v === '愛知県名古屋市'));

/* ---- プライバシーポリシーが実装と合っているか ---- */
const pv = await (await open(browser, { page: 'privacy.html' })).locator('main').innerText();
check('計測を入れていないという記述が実態と合う',
    /const ANALYTICS_ID = ''/.test(idx) === /アクセス解析ツールを使用しておらず/.test(pv));
check('入力フォームが無いという記述が実態と合う', !/<form/.test(idx) && /入力フォームを設置していません/.test(pv));
check('外部サービスの学習利用を明記', /AI モデルの学習）に利用される場合があります/.test(pv));
check('相対参照(前項など)を使っていない', !/前項|次項/.test(pv));

/* ---- 納期の文言が計算と合っているか ---- */
/* 梅〜松の幅。段で差が出ない尺は「約2週間」のように1つの数字で書く */
const rng = (sec) => {
    const [a, b] = [leadWeeks(TIERS[0], sec), leadWeeks(TIERS[2], sec)];
    return a === b ? `約${a}週間` : `約${a}〜${b}週間`;
};
for (const [label, sec] of [['30秒', 30], ['90秒', 90], ['3分', 180], ['5分', 300]]) {
    const want = `${label}で${rng(sec)}`;
    check(`本文の納期が計算結果と一致(${label})`, idx.includes(want), want);
}
check('タイトルの「最短2週間」が実態と合う',
    /最短2週間/.test(idx) && Math.min(...TIERS.flatMap(t => LENGTHS.map(s => leadWeeks(t, s)))) === 2);

/* ---- 料金の説明文が段と矛盾していないか ----
   段で秒単価が変わるのに「1秒あたり ¥3,500」と書いてあると嘘になる */
const why = await page.locator('.calc-why').innerText();
check('内訳の秒単価が段の幅で書いてある',
    /¥3,500〜6,650/.test(why) && /仕上げの段階/.test(why), why.split('\n').find(l => l.includes('1秒')) || '');
check('制作にかかる日数が何で変わるか書いてある',
    /尺と仕上げの段階によって前後します/.test(await page.locator('#process').innerText()));

/* ---- 公開範囲 ---- */
for (const [f, html] of [['index.html', idx], ['about.html', about], ['privacy.html', privacy]]) {
    check(`${f} は検索結果に出さない`, /name="robots" content="noindex/.test(html));
}
const rb = await (await page.request.get(`${BASE}/robots.txt`)).text();
check('robots.txt でクロールは止めていない', /Allow: \//.test(rb) && !/Disallow: \//.test(rb));

/* ---- ロードマップ(社内用) ----
   数字はサイトの料金表・工数モデルから出しているので、
   料金を動かしたらここもズレる。主要な数字だけ突き合わせる */
{
    const rm = await open(browser, { page: 'roadmap.html' });

    /* 折りたたむ前に、たたんだ状態のままで主要な数字が読めるかを見る。
       たたんだ見出しに数字が出ていないと、開かないと何も分からない資料になる */
    const folded = await rm.locator('body').innerText();
    check('たたんだままでも年商・年収が読める',
        /¥11,295,000/.test(folded) && /¥10,408,605/.test(folded));
    check('たたんだままでも天井と必要な問い合わせ数が読める',
        /1,950万/.test(folded) && /6\.7件/.test(folded));

    /* 折りたたみを全部開いてから、中身の数字を突き合わせる */
    const foldCount = await rm.evaluate(() => {
        const d = document.querySelectorAll('details.fold');
        d.forEach((x) => { x.open = true; });
        return d.length;
    });
    check('折りたたみが存在する', foldCount >= 5);
    check('「すべて開く」ボタンがある', await rm.locator('#openall').count() === 1);

    const t = await rm.locator('body').innerText();
    check('ロードマップの目標が計画と一致', /¥10,695,000/.test(t));
    check('ロードマップの四半期計が計画と一致',
        /¥1,800,000/.test(t) && /¥2,745,000/.test(t) && /¥3,375,000/.test(t) && /¥11,295,000/.test(t));
    check('未開業であることを書いている', /未開業/.test(t));
    check('クレジット残高とプランが最新', /1,592/.test(t) && /Max/.test(t));
    /* 実工数は工程別に測り直して 11.5h（本編10.5 ＋ 15秒版1.0）。
       以前の「17.0h」は内訳を取る前の概算だった（2026-09-16 訂正） */
    check('松2本の実測が記録されている',
        /2,442/.test(t) && /1,221/.test(t) && /11\.5時間/.test(t));
    check('松の4工程を実際に通した記録がある',
        /4K化/.test(t) && /Reframe 9:16/.test(t) && /Seed Audio/.test(t));
    check('4工程の原価の内訳が載っている',
        /138/.test(t) && /1\.2/.test(t) && /0\.4/.test(t) && /277\.6/.test(t));
    check('原価の大半がリフレームだと書いている', /99\.4%/.test(t));
    check('プラン上限への影響が載っている', /2\.3本/.test(t) && /5,400/.test(t));
    check('4工程の出力を検証した記録がある',
        /3840×2160/.test(t) && /1080×1920/.test(t) && /1440×1440/.test(t));
    check('縦型リフレームが使えないと結論している',
        /リフレームはテロップを組み直さない/.test(t) && /使えない/.test(t));
    check('松から落とす仕様を明示している',
        /落とす/.test(t) && /4K/.test(t) && /3形式/.test(t));
    check('縦型は追加本数で作ると書いている',
        /追加の1本|追加本数/.test(t) && /¥65,000\/h/.test(t));
    check('1,080クレジットを授業料として記録している', /1,080クレジットは授業料/.test(t));
    check('社内用なので検索に出さない',
        (await rm.evaluate(() => document.querySelector('meta[name="robots"]')?.content || '')).includes('noindex'));
    check('ロードマップで横溢れなし',
        (await rm.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth)) <= 0);
    check('実際に納品した2本の尺と時間単価が載っている',
        /59秒/.test(t) && /15秒/.test(t) && /¥41,905\/h/.test(t) && /¥80,000\/h/.test(t));
    check('料金表どおりの金額を出している',
        /¥647,100/.test(t) && /¥520,000/.test(t));
    check('追加尺が料金表の2本目にあたると書いている',
        /¥65,000/.test(t) && /¥189,750/.test(t) && /上乗せ/.test(t));
    check('追加尺がほぼ純利益だと書いている', /純利益/.test(t) && /2時間/.test(t));
    check('2本・架空案件だけの数字だと断っている', /2本/.test(t) && /架空/.test(t));
    check('営業ロープレであって実案件でないと明記', /ロープレ/.test(t) && /架空/.test(t));
    check('P0 から計測用テスト制作へリンクしている',
        await rm.locator('.stage a[href="#test-build"]').count() >= 1);
    for (const f of ['index.html', 'about.html']) {
        check(`${f} から roadmap.html にリンクしていない`,
            !/roadmap\.html/.test(await (await rm.request.get(`${BASE}/${f}`)).text()));
    }
    await rm.close();
}

/* ---- 配信できるか ---- */
for (const f of ['assets/site.css', 'assets/logo-mark.png', 'assets/favicon.png',
                 'assets/apple-touch-icon.png', 'assets/ogp.png', 'privacy.html',
                 'funnel.html', 'roadmap.html']) {
    const st = (await page.request.get(`${BASE}/${f}`)).status();
    check(`${f} が配信できる`, st === 200, `HTTP ${st}`);
}
await browser.close();
report();
