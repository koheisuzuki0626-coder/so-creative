/* 読みやすさ。全テキストのコントラストと、日本語の折り返し。 */
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { check, report, open, PW } from './lib.mjs';
const pwmod = (await import(PW)).default;
const ROOT = fileURLToPath(new URL('..', import.meta.url)).replace(/\/$/, '');
const browser = await pwmod.chromium.launch();
for (const file of ['index.html', 'works.html', 'pricing.html', 'company-video.html', 'recruit-video.html', 'about.html', 'privacy.html', 'copyright.html', 'quality.html',
                    'funnel.html', 'roadmap.html', 'record.html']) {
    const page = await open(browser, { page: file });
    const bad = await page.evaluate(() => {
        const L = (c) => { const v = c.map(x => { x /= 255; return x <= 0.03928 ? x / 12.92 : Math.pow((x + 0.055) / 1.055, 2.4); });
            return 0.2126 * v[0] + 0.7152 * v[1] + 0.0722 * v[2]; };
        const px = (c) => { const m = c.match(/[\d.]+/g); return m ? m.slice(0, 3).map(Number) : null; };
        const bgOf = (el) => { let n = el;
            while (n) { const c = getComputedStyle(n).backgroundColor;
                const m = c.match(/[\d.]+/g);
                if (m && (m.length < 4 || Number(m[3]) > 0.85)) return px(c);
                n = n.parentElement; } return [255, 255, 255]; };
        const out = [];
        for (const el of document.querySelectorAll('body *')) {
            const txt = [...el.childNodes].filter(n => n.nodeType === 3 && n.textContent.trim()).map(n => n.textContent.trim()).join('');
            if (!txt) continue;
            const s = getComputedStyle(el);
            if (s.visibility === 'hidden' || s.display === 'none' || Number(s.opacity) < 0.5) continue;
            const r = el.getBoundingClientRect();
            if (r.width === 0 || r.height === 0) continue;
            const fg = px(s.color); if (!fg) continue;
            const bg = bgOf(el);
            const l1 = L(fg) + 0.05, l2 = L(bg) + 0.05;
            const ratio = Math.max(l1, l2) / Math.min(l1, l2);
            const size = parseFloat(s.fontSize), bold = Number(s.fontWeight) >= 700;
            const need = (size >= 24 || (size >= 18.66 && bold)) ? 3 : 4.5;
            if (ratio < need) out.push({ t: txt.slice(0, 24), ratio: +ratio.toFixed(2), need, size });
        }
        return out;
    });
    check(`${file} 全テキストが AA を満たす`, bad.length === 0, JSON.stringify(bad.slice(0, 3)));
    const wrap = await page.evaluate(() => getComputedStyle(document.body).wordBreak);
    check(`${file} 日本語を文節で折り返す`, wrap === 'auto-phrase', wrap);
    // 最終行に1〜3文字だけ残っていないか(日本語の泣き別れ)
    const orphan = await page.evaluate(() => {
        const out = [];
        for (const el of document.querySelectorAll('p, li, dd, h1, h2, h3')) {
            const t = el.textContent.trim();
            if (t.length < 20) continue;
            const r = el.getClientRects();
            if (r.length < 2) continue;
            const last = r[r.length - 1], first = r[0];
            if (last.width > 0 && last.width < first.width * 0.06) out.push(t.slice(0, 20));
        }
        return out;
    });
    check(`${file} 最終行に1〜3文字だけ残る箇所がない`, orphan.length === 0, JSON.stringify(orphan.slice(0, 2)));
    check(`${file} JS エラーなし`, page.__errors.length === 0, JSON.stringify(page.__errors));
    await page.close();
}
/* 出現アニメーションで消えたままにならないこと。
   threshold を割合で見ていたころ、画面より背の高い塊（ジャンル欄は
   スマホで 6,400px）は「12%が同時に見える」状態を作れず、
   中身が丸ごと出てこなかった。狭くて短い画面ほど起きやすい */
const revealCases = [
    ['index.html', 375, 667, 'index iPhone SE'],
    ['index.html', 360, 640, 'index Android 小'],
    ['index.html', 1280, 900, 'index PC'],
    ['about.html', 375, 667, 'about iPhone SE'],
    ['roadmap.html', 375, 667, 'roadmap iPhone SE'],
    ['record.html', 375, 667, 'record iPhone SE'],
    ['funnel.html', 375, 667, 'funnel iPhone SE'],
];
for (const [file, w, h, label] of revealCases) {
    const page = await open(browser, { width: w, height: h, mobile: w < 700, page: file });
    /* 端まで送る。ページが長いので刻んで進める。
       html に scroll-behavior:smooth が効いているので instant を明示しないと
       送りきる前にループが終わる */
    const total = await page.evaluate(() => document.body.scrollHeight);
    for (let y = 0; y < total + h; y += Math.floor(h * 0.6)) {
        await page.evaluate((v) => window.scrollTo({ top: v, behavior: 'instant' }), y);
        await page.waitForTimeout(70);
    }
    await page.waitForTimeout(1800);
    const hidden = await page.evaluate(() => {
        const out = [];
        for (const el of document.querySelectorAll('.reveal, .reveal-stagger > *')) {
            if (Number(getComputedStyle(el).opacity) > 0.5) continue;
            const t = (el.id || el.className || el.tagName).toString().slice(0, 40);
            out.push(t);
        }
        return out;
    });
    check(`${label} 一番下まで送れば出現アニメーションが全部出る`,
        hidden.length === 0, JSON.stringify(hidden.slice(0, 5)));
    /* ジャンルのカードは 2026-09-23 に works.html へ移した */
    if (file === 'works.html') {
        const genres = await page.evaluate(() => {
            const all = [...document.querySelectorAll('.genre')];
            return { n: all.length, hidden: all.filter((e) => Number(getComputedStyle(e).opacity) < 0.5).length };
        });
        check(`${label} つくれる動画のジャンルが9本とも見える`,
            genres.n === 9 && genres.hidden === 0, JSON.stringify(genres));
    }
    await page.close();
}

/* カードが実際に見えることまで確かめる（親に .in が付かないと消える） */
{
    /* PCだけでなくスマホでも見る。背の高い塊は画面より大きいので、
       割合（threshold）で判定していると永久に出てこない（2026-09-24）。 */
    for (const [w, vh, mob] of [[1280, 940, false], [375, 667, true]]) {
    const p = await open(browser, { page: 'works.html', width: w, height: vh, mobile: mob });
    const docH = await p.evaluate(() => document.body.scrollHeight);
    for (let y = 0; y < docH; y += Math.round(vh * 0.6)) {
        await p.evaluate((v) => window.scrollTo(0, v), y);
        await p.waitForTimeout(220);
    }
    await p.waitForTimeout(1200);
    const dim = await p.evaluate(() => [...document.querySelectorAll('.genre')]
        .filter((e) => +getComputedStyle(e).opacity < 0.9).length);
    check(`works.html のカード9枚が最後まで送れば見える（${w}px）`, dim === 0, String(dim));
    await p.close();
    }
}

await browser.close();

/* JSが動かない端末で真っ白にならないこと（2026-09-24 に実機で発生）。
   .reveal を無条件に opacity:0 にしていたため、JSが届く前や動かないときに
   ヘッダー以外が全部消えていた。隠すのは html に .js が付いてから。
   JSを切ったページは evaluate できないので、ソースの作りで見る。 */
{
    const css = readFileSync(`${ROOT}/assets/site.css`, 'utf8');
    check('隠すのは .js が付いてから', /\.js \.reveal \{[^}]*opacity: 0/.test(css),
          (css.match(/^[^\n]*\.reveal \{[^\n]*/m) || [''])[0]);
    check('無条件に隠していない', !/^\.reveal \{[^}]*opacity: 0/m.test(css));
    for (const file of ['index.html', 'works.html', 'pricing.html', 'company-video.html', 'recruit-video.html',
                        'about.html', 'privacy.html', 'copyright.html', 'quality.html']) {
        const html = readFileSync(`${ROOT}/${file}`, 'utf8');
        check(`${file} に .js を付ける1行がある`,
              /classList\.add\('js'\)/.test(html));
    }
}


/* ページの本文が自分自身にリンクしていないこと（2026-09-24）。
   トップからジャンルの節を works.html へ移したとき、「9本まとめて見る」という
   リンクが一緒に付いてきて、works.html が自分を指していた。
   フッターのサイトマップは全ページを並べる場所なので対象外。 */
{
    for (const file of ['index.html', 'works.html', 'pricing.html', 'company-video.html', 'recruit-video.html',
                        'about.html', 'privacy.html', 'copyright.html', 'quality.html']) {
        const html = readFileSync(`${ROOT}/${file}`, 'utf8');
        const main = html.slice(html.indexOf('<main>'), html.indexOf('</main>'));
        const self = [...main.matchAll(/<a[^>]*href="([^"#]+\.html)"/g)]
            .map((m) => m[1]).filter((h) => h === file);
        check(`${file} の本文が自分自身にリンクしていない`, self.length === 0, String(self.length));
    }
}


/* .reveal-stagger の中身が消えないこと（2026-09-24 に works.html で発生）。
   カードの親だけが reveal-stagger で、下層ページのスクリプトは .reveal しか
   見ていなかった。親に .in が付かず、9枚のカードが opacity:0 のまま消えていた。
   .reveal だけを見るテストでは気づけなかったので、ここで押さえる。 */
{
    for (const file of ['index.html', 'works.html', 'pricing.html', 'company-video.html', 'recruit-video.html',
                        'about.html', 'privacy.html', 'copyright.html', 'quality.html']) {
        const html = readFileSync(`${ROOT}/${file}`, 'utf8');
        if (!html.includes('reveal-stagger')) { continue; }
        check(`${file} は reveal-stagger も監視している`,
              /querySelectorAll\('\.reveal, \.reveal-stagger'\)/.test(html));
        /* 割合（threshold）だけで見ると、画面より背の高い塊は永久に出てこない。
           出現アニメーションは rootMargin で判定していること。
           ※ヒーロー動画の再生制御にも IntersectionObserver を使っているが、
           そちらは画面いっぱいの要素なので割合で問題ない */
        check(`${file} の出現アニメーションは rootMargin で判定している`,
              /threshold: 0, rootMargin: '0px 0px -1\d% 0px'/.test(html));
    }
}

report();
