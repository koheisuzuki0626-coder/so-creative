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
let p = await open(browser, {});
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
    const idx = readFileSync(`${ROOT}/index.html`, 'utf8');
    const fun = readFileSync(`${ROOT}/funnel.html`, 'utf8');
    const fromIdx = (idx.match(/const SECTIONS = \[([^\]]+)\]/) || [])[1] || '';
    const fromFun = (fun.match(/const SECTIONS = \[([\s\S]*?)\];/) || [])[1] || '';
    const idsIdx = [...fromIdx.matchAll(/'([a-z]+)'/g)].map((m) => m[1]);
    const idsFun = [...fromFun.matchAll(/\['([a-z]+)',/g)].map((m) => m[1]);
    check('節の並びが index と funnel で一致',
        idsIdx.length === 8 && idsIdx.join() === idsFun.join(), `${idsIdx.join()} / ${idsFun.join()}`);

    await q.goto(`${BASE}/funnel.html`, { waitUntil: 'networkidle' });
    const t = await q.locator('body').innerText();
    check('どこまで読んで帰ったかの表が出る',
        /どこまで読んで帰ったか/.test(t) && /つくれる動画/.test(t) && /いちばん落ちているのは/.test(t));
    await q.close();
}

/* ---- 相談まで進んだ場合 ---- */
p = await open(browser, {});
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

/* ---- 外部送信は既定で無効 ---- */
p = await open(browser, {});
check('計測IDが空なら外部に送らない', (await p.evaluate(() => typeof window.gtag)) === 'undefined');
check('外部の計測タグを読み込んでいない',
    !/googletagmanager|google-analytics/.test(await (await p.request.get(`${BASE}/index.html`)).text()));
check('Cookie を置いていない', (await p.context().cookies()).length === 0);
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
p = await open(browser, {});
const visit = async (sec, contact) => {
    await p.goto(`${BASE}/index.html`, { waitUntil: 'networkidle' });
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
check('4段階が数えられる', steps.length === 4, JSON.stringify(steps));
check('検討した人と相談した人が分かる', steps[2] === '3人' && steps[3] === '1人', JSON.stringify(steps));
check('落ちた人数が一番上に出る', /2人/.test(await p.locator('.headline-num b').innerText()));
const tbl = await p.locator('#bysec tbody tr').evaluateAll(els => els.map(e => [...e.querySelectorAll('td')].map(t => t.textContent.trim())));
check('尺ごとの通過率が出る(値下げの判断材料)',
    tbl.some(r => r[0] === '5分' && r[4] === '0%') && tbl.some(r => r[0] === '90秒' && r[4] === '100%'),
    JSON.stringify(tbl));
check('落ちている尺に印が付く', (await p.locator('#bysec tbody tr.bad').count()) === 1);
const bars = await p.locator('.bar').evaluateAll(els => els.map(e => e.getBoundingClientRect().width));
check('棒に幅がある', bars.length === 4 && bars.every(w => w > 1), JSON.stringify(bars.map(Math.round)));
await browser.close();
report();
