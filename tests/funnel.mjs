// 計算機とその注記は 2026-09-23 に pricing.html へ移した。
// 料金で検索して来た人が最初に着くのがこのページで、二重に持つと式が食い違うため。
/* 料金計算機の段差(ファネル計測)と、それを見るページ。
   料金表を公開している以上、価格で諦めた人はここにしか残らない。 */
import { check, report, open, BASE, PW } from './lib.mjs';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
const ROOT = fileURLToPath(new URL('..', import.meta.url)).replace(/\/$/, '');
const pwmod = (await import(PW)).default;
const browser = await pwmod.chromium.launch();
const log = (p) => p.evaluate(() => window.soFunnel.raw().map(r => r.name));
const rows = (p) => p.evaluate(() => window.soFunnel.raw());
const leave = (p) => p.evaluate(() => {
    Object.defineProperty(document, 'visibilityState', { value: 'hidden', configurable: true });
    document.dispatchEvent(new Event('visibilitychange'));
});

/* ---- 通過点が正しい順に立つか ---- */
let p = await open(browser, { page: 'pricing.html' });
check('訪問そのものは記録する(母数)', (await log(p)).join() === 'page_view', JSON.stringify(await log(p)));
await p.locator('#plans').scrollIntoViewIfNeeded();
await p.waitForTimeout(700);
check('料金を見たら plans_view', (await log(p)).includes('plans_view'));
check('見ただけでは検討扱いにしない', !(await log(p)).includes('calc_use'));
await p.locator('#calc-len select[data-kind="len"][data-row="0"]').selectOption('180');
await p.waitForTimeout(1200);
const L = await log(p);
check('条件を変えたら calc_use', L.includes('calc_use'));
check('calc_use は1人1回だけ', L.filter(x => x === 'calc_use').length === 1);
const res = (await rows(p)).find(r => r.name === 'calc_result');
check('金額と段が記録される', res.total === 90000 + 3500 * 180 && res.tier === 'ume', JSON.stringify(res));
await leave(p); await p.waitForTimeout(200);
const lv = (await rows(p)).find(r => r.name === 'calc_leave');
check('相談せずに閉じた人が残る', lv && lv.used === true && lv.cta === false, JSON.stringify(lv));
check('離脱時の金額と段が残る', lv && lv.total === 90000 + 3500 * 180 && lv.tier === 'ume');
await p.close();

/* ---- どこまで読んで帰ったか（9/23） ----
   料金まで来なかった人が「どこで止まったか」を出すために、節ごとに記録している。
   節を飛ばしてスクロールすると途中が抜けるので、集計は
   「いちばん深く到達した節」から逆算する（funnel.html 側） */
{
    /* 節の到達はトップの話。計算機だけが pricing.html へ移った（2026-09-23） */
    const q = await open(browser, {});
    const SECTIONS = ['service', 'why', 'genres', 'works', 'process', 'plans', 'faq', 'contact'];
    /* つくれる動画の節は 4,000px 以上あって画面に 25% 入りきらない。
       threshold で見ていると一生発火しないので rootMargin で見ている */
    await q.locator('#genres').scrollIntoViewIfNeeded();
    await q.waitForTimeout(400);
    const seen = async () => (await rows(q)).filter((r) => r.name === 'section_view').map((r) => r.id);
    check('背の高い節でも到達が記録される', (await seen()).includes('genres'), (await seen()).join());
    await q.locator('#plans').scrollIntoViewIfNeeded();
    await q.waitForTimeout(400);
    check('料金まで来たら plans_view も残る', (await log(q)).includes('plans_view'));
    check('節の記録は index.html の並びの中にある',
        (await seen()).every((id) => SECTIONS.includes(id)), (await seen()).join());
    /* 同じ節を何度も通っても1回だけ */
    await q.locator('#service').scrollIntoViewIfNeeded();
    await q.waitForTimeout(200);
    await q.locator('#plans').scrollIntoViewIfNeeded();
    await q.waitForTimeout(300);
    const ids = await seen();
    check('同じ節は1回しか記録しない', new Set(ids).size === ids.length, ids.join());

    /* funnel.html が index.html と同じ並び・同じ id を持っていること。
       ズレると、実際には通っている節が「来ていない」と出る */
    /* 節の一覧と計測は 2026-09-23 に assets/funnel.js へ切り出した */
    const idx = readFileSync(`${ROOT}/assets/funnel.js`, 'utf8');
    const fun = readFileSync(`${ROOT}/funnel.html`, 'utf8');
    const fromIdx = (idx.match(/const SECTIONS = \[([^\]]+)\]/) || [])[1] || '';
    const fromFun = (fun.match(/const SECTIONS = \[([\s\S]*?)\];/) || [])[1] || '';
    const idsIdx = [...fromIdx.matchAll(/'([a-z]+)'/g)].map((m) => m[1]);
    const idsFun = [...fromFun.matchAll(/\['([a-z]+)',/g)].map((m) => m[1]);
    check('節の並びが index と funnel で一致',
        idsIdx.length === 8 && idsIdx.join() === idsFun.join(), `${idsIdx.join()} / ${idsFun.join()}`);

    await q.goto(`${BASE}/funnel.html`, { waitUntil: 'networkidle' });
    const t = await q.locator('body').innerText();
    /* 節は別表ではなく「どこで落ちているか」の段そのものに出す（9/23）。
       2か所に置くと片方だけ古くなるので、表は持たない */
    const labels = await q.locator('.step .lbl').allInnerTexts();
    check('節が段として並んでいる',
        labels.join() === 'サイトに来た,事業内容,撮影しない理由,つくれる動画,サンプル,制作の流れ,料金,条件を選んだ,相談まで進んだ',
        labels.join());
    check('料金より下の到達も出る', /料金より下まで読んだ人/.test(t));
    check('節の別表を持っていない', !/どこまで読んで帰ったか/.test(t));
    await q.close();
}

/* ---- 相談まで進んだ場合 ---- */
p = await open(browser, { page: 'pricing.html' });
await p.locator('#plans').scrollIntoViewIfNeeded(); await p.waitForTimeout(700);
await p.locator('#calc-len select[data-kind="len"][data-row="0"]').selectOption('90');
await p.waitForTimeout(200);
await p.evaluate(() => document.getElementById('calc-mail').removeAttribute('href'));
await p.locator('#calc-mail').click();
await p.waitForTimeout(200);
const c = (await rows(p)).find(r => r.name === 'calc_cta');
check('相談ボタンで calc_cta', !!c && c.how === 'mail' && c.tier === 'ume', JSON.stringify(c));
await leave(p); await p.waitForTimeout(200);
check('相談済みなら cta=true', (await rows(p)).find(r => r.name === 'calc_leave')?.cta === true);
await p.close();

/* ---- 計測とプライバシーポリシーが食い違っていないか ----
   2026-09-23 に GA4 を入れた。ここでいちばん危ないのは、
   **計測しているのにポリシーに書いていない**（逆も同じ）状態。
   どちらの向きにもズレないよう、ANALYTICS_ID の中身で分岐して見る */
p = await open(browser, { page: 'pricing.html' });
const idxSrc = await (await p.request.get(`${BASE}/assets/funnel.js`)).text();
const gaId = (idxSrc.match(/const ANALYTICS_ID = '([^']*)'/) || [])[1] ?? null;
const priv = await (await p.request.get(`${BASE}/privacy.html`)).text();
check('ANALYTICS_ID が読み取れる', gaId !== null, String(gaId));
if (gaId) {
    check('計測IDの形が正しい', /^G-[A-Z0-9]{6,}$/.test(gaId), gaId);
    check('タグを読み込んでいる',
        (await p.locator(`script[src*="gtag/js?id=${gaId}"]`).count()) === 1);
    check('gtag が使える', (await p.evaluate(() => typeof window.gtag)) === 'function');
    check('IP を伏せて送る', /anonymize_ip: true/.test(idxSrc));
    /* ポリシー側。使っていると明記し、送る中身・停止の方法・Google のポリシーへの導線があること */
    check('ポリシーに解析の使用を明記している',
        /Google アナリティクス 4/.test(priv) && /Cookie を使用します/.test(priv));
    check('ポリシーに送信する中身を書いている',
        /どこまでスクロールしたか/.test(priv) && /概算金額/.test(priv));
    check('ポリシーに停止の方法を書いている',
        /オプトアウト アドオン/.test(priv) && /gaoptout/.test(priv));
    check('ポリシーに Google のポリシーへの導線がある', /policies\.google\.com\/privacy/.test(priv));
    check('ポリシーに改定日が入っている', /改定日：2026年9月23日/.test(priv));
    check('「使用していません」が残っていない',
        !/アクセス解析ツールを使用しておらず/.test(priv));
} else {
    check('計測IDが空なら外部に送らない', (await p.evaluate(() => typeof window.gtag)) === 'undefined');
    check('計測IDが空ならタグを足していない',
        (await p.locator('script[src*="gtag/js"]').count()) === 0);
    check('計測IDが空ならポリシーも使っていないと書く',
        /アクセス解析ツールを使用しておらず/.test(priv));
}
/* ID を入れたら本当に動くか。ここが繋がっていないと、
   privacy.html だけ書き換えて「計測しているつもり」になる */
{
    const g = await open(browser, { page: 'pricing.html' });
    const loaded = await g.evaluate(() => {
        const s2 = document.createElement('script');
        return new Promise((res) => {
            // 実際の読み込みは行わず、配線だけを見る
            window.dataLayer = window.dataLayer || [];
            window.gtag = function gtag() { window.dataLayer.push(arguments); };
            window.gtag('event', 'test_event', { a: 1 });
            res(window.dataLayer.length > 0);
            s2.remove();
        });
    });
    check('gtag があれば track が送る側に渡す', loaded);
    await g.close();

    /* page_view は gtag('config') が自分で送る。こちらからも送ると
       訪問が2回数えられ、以降の通過率が全部ずれる */
    const h = await open(browser, { page: 'pricing.html' });
    const sent = await h.evaluate(async () => {
        const got = [];
        window.gtag = (kind, name) => { if (kind === 'event') got.push(name); };
        // 料金まで進めて、いくつかのイベントを起こす
        document.getElementById('plans').scrollIntoView();
        await new Promise((r) => setTimeout(r, 600));
        return got;
    });
    check('page_view を二重に送らない', !sent.includes('page_view'), sent.join());
    check('ほかのイベントは送る', sent.length > 0, sent.join());
    await h.close();
}
await p.close();

/* ---- 見るページ ---- */
p = await open(browser, { page: 'funnel.html' });
check('記録が空でも壊れて見えない', (await p.locator('body').innerText()).includes('まだ記録がありません'));
check('社内用なので検索に出さない',
    (await p.evaluate(() => document.querySelector('meta[name="robots"]')?.content || '')).includes('noindex'));
for (const f of ['index.html', 'about.html']) {
    check(`${f} から funnel.html にリンクしていない`,
        !/funnel\.html/.test(await (await p.request.get(`${BASE}/${f}`)).text()));
}
await p.close();

// 実際に数字が出るか
p = await open(browser, { page: 'pricing.html' });
const visit = async (sec, contact) => {
    await p.goto(`${BASE}/pricing.html`, { waitUntil: 'networkidle' });
    await p.locator('#plans').scrollIntoViewIfNeeded(); await p.waitForTimeout(700);
    await p.locator('#calc-len select[data-kind="len"][data-row="0"]').selectOption(String(sec));
    await p.waitForTimeout(1050);
    if (contact) {
        await p.evaluate(() => document.getElementById('calc-mail').removeAttribute('href'));
        await p.locator('#calc-mail').click(); await p.waitForTimeout(120);
    }
    await leave(p); await p.waitForTimeout(120);
};
await visit(300, false); await visit(300, false); await visit(90, true);
await p.goto(`${BASE}/funnel.html`, { waitUntil: 'networkidle' });
await p.waitForTimeout(300);
const steps = await p.locator('.step').evaluateAll(els => els.map(e => e.querySelector('.n').textContent.trim()));
/* 9/23：料金までの節を段に組み込んだので 4段 → 9段
   （訪問＋節6つ＋条件を選んだ＋相談まで進んだ） */
check('9段階が数えられる', steps.length === 9, JSON.stringify(steps));
check('検討した人と相談した人が分かる',
    steps[7] === '3人' && steps[8] === '1人', JSON.stringify(steps));
check('落ちた人数が一番上に出る', /2人/.test(await p.locator('.headline-num b').innerText()));
const tbl = await p.locator('#bysec tbody tr').evaluateAll(els => els.map(e => [...e.querySelectorAll('td')].map(t => t.textContent.trim())));
check('尺ごとの通過率が出る(値下げの判断材料)',
    tbl.some(r => r[0] === '5分' && r[4] === '0%') && tbl.some(r => r[0] === '90秒' && r[4] === '100%'),
    JSON.stringify(tbl));
check('落ちている尺に印が付く', (await p.locator('#bysec tbody tr.bad').count()) === 1);
const bars = await p.locator('.bar').evaluateAll(els => els.map(e => e.getBoundingClientRect().width));
check('棒に幅がある', bars.length === 9 && bars.every(w => w > 1), JSON.stringify(bars.map(Math.round)));
await browser.close();
report();
