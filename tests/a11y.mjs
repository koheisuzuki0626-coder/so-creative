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

/* ---- 紙に出したときに読めるか（2026-09-26） ----
   紙も画面と同じ濃色で刷る。ブラウザは既定で背景色を刷らないので、
   print-color-adjust: exact が外れるとその瞬間に地が白くなり、
   ほぼ白の文字だけが残って白紙になる。料金・品質・権利のページは
   「稟議に添える」「法務に見せる」と書いてあるので、刷られる前提で持たせる。
   遷移も切っておく。切らないと、印刷に切り替えた瞬間から 0.9s かけて
   0 → 1 へ動くので、その途中で刷られると半透明のまま紙に乗る */
{
    const lum = (c) => {
        const v = (c.match(/[\d.]+/g) || []).slice(0, 3).map(Number)
            .map((x) => { x /= 255; return x <= 0.03928 ? x / 12.92 : ((x + 0.055) / 1.055) ** 2.4; });
        return 0.2126 * v[0] + 0.7152 * v[1] + 0.0722 * v[2];
    };
    /* 地に対して。紙も画面と同じ地なので、白い紙ではなく実際の地と比べる */
    const cr = (c, bg) => {
        const a = lum(c) + 0.05, b = lum(bg) + 0.05;
        return a > b ? a / b : b / a;
    };
    for (const file of ['index.html', 'pricing.html', 'quality.html', 'copyright.html', 'about.html']) {
        const page = await open(browser, { page: file, width: 1280 });
        await page.emulateMedia({ media: 'print' });
        await page.waitForTimeout(400);
        const r = await page.evaluate(() => {
            const g = (s) => { const e = document.querySelector(s); return e ? getComputedStyle(e).color : null; };
            const nav = document.getElementById('nav');
            const bodyCs = getComputedStyle(document.body);
            return {
                head: g('h1') || g('h2'),
                body: g('.body-text'),
                /* 紙の地。ここが白に戻っていたら、濃色の指定が外れている */
                bg: bodyCs.backgroundColor,
                /* これが exact でないと、ブラウザは背景色を落として刷る */
                exact: bodyCs.printColorAdjust || bodyCs.webkitPrintColorAdjust,
                navHidden: !nav || getComputedStyle(nav).display === 'none',
                faded: [...document.querySelectorAll('.reveal, .reveal-stagger > *')]
                    .filter((e) => getComputedStyle(e).opacity !== '1').length,
                /* 紙の上では触れないので、既定の組み合わせの額が
                   「お見積り」の見出しのまま固定で刷られてしまう */
                calcShown: [...document.querySelectorAll('.calc')]
                    .filter((e) => getComputedStyle(e).display !== 'none').length,
                /* 見本の映像は poster を持っている。消すと
                   「こうなりました」の下が空のまま刷られる */
                samples: [...document.querySelectorAll('.sample-video, .ba-media')]
                    .filter((e) => e.tagName === 'VIDEO').length,
                samplesHidden: [...document.querySelectorAll('.sample-video, .ba-media')]
                    .filter((e) => e.tagName === 'VIDEO' && getComputedStyle(e).display === 'none').length,
                /* 背景で流しているだけ。poster が無いので紙では白い箱になる */
                heroVideoShown: [...document.querySelectorAll('.hero-video')]
                    .filter((e) => getComputedStyle(e).display !== 'none').length,
                /* 横スクロールの入れ物はページをまたげない。
                   丸ごと次ページへ送られ、手前に空白のページができる */
                clipped: [...document.querySelectorAll('.compare-wrap, .genre-price-table, .genre-index')]
                    .filter((e) => getComputedStyle(e).overflowX !== 'visible').length,
                /* よくあるご質問は details。閉じたまま刷ると、
                   質問だけが並んで答えが1つも出ない */
                faqs: document.querySelectorAll('.faq-a').length,
                faqsHidden: [...document.querySelectorAll('.faq-a')]
                    .filter((e) => e.offsetHeight === 0).length,
                /* hero は紙では中身の高さまで縮む。中に絶対配置のものが
                   残っていると、縮んだぶんだけ本文の上に重なって刷られる
                   （SCROLL の案内がチップスの上に乗っていた） */
                floating: [...document.querySelectorAll('.hero *')]
                    .filter((e) => { const c = getComputedStyle(e);
                        return c.display !== 'none' && (c.position === 'absolute' || c.position === 'fixed'); })
                    .map((e) => e.className || e.tagName),
                /* 濃色の地に白い字を置いた部品は、地が刷られないと
                   白い紙に白い字として残る。フッターの「相談してみる」が
                   まさにそうなっていた。刷られる文字を全部見て回る */
                invisible: (() => {
                    const out = [];
                    for (const e of document.querySelectorAll('body *')) {
                        const t = [...e.childNodes]
                            .filter((n) => n.nodeType === 3).map((n) => n.textContent.trim()).join('');
                        if (!t) continue;
                        /* video / audio の中の文字は、再生できないブラウザ向けの
                           控えの文。動くブラウザでは描かれないので数えない */
                        if (e.matches('video, audio, canvas, noscript')) continue;
                        const cs = getComputedStyle(e);
                        if (cs.display === 'none' || cs.visibility === 'hidden' || +cs.opacity === 0) continue;
                        if (e.closest('[hidden]')) continue;
                        let hidden = false;
                        for (let a = e; a; a = a.parentElement) {
                            const s2 = getComputedStyle(a);
                            if (s2.display === 'none' || s2.visibility === 'hidden' || +s2.opacity === 0) { hidden = true; break; }
                        }
                        if (hidden) continue;
                        out.push([t.slice(0, 20), cs.color, cs.backgroundColor]);
                    }
                    return out;
                })(),
            };
        });
        check(`${file} は紙でも地が濃いまま`, lum(r.bg) < 0.1, r.bg);
        check(`${file} は紙でも背景色を落とさない`, r.exact === 'exact', String(r.exact));
        /* 紙も画面と同じ絵になったので、しきい値も画面と同じ AA に揃える。
           ここだけ 7 にしていたのは、白い紙に薄い灰を刷ると飛ぶからだった */
        check(`${file} は紙でも見出しが読める`, cr(r.head, r.bg) >= 7, `${cr(r.head, r.bg).toFixed(1)}:1`);
        check(`${file} は紙でも本文が読める`, cr(r.body, r.bg) >= 4.5, `${cr(r.body, r.bg).toFixed(1)}:1`);
        check(`${file} は紙にヘッダーを刷らない`, r.navHidden);
        check(`${file} は紙で中身が薄くならない`, r.faded === 0, `${r.faded} 個が半透明`);
        check(`${file} は紙に計算機を刷らない`, r.calcShown === 0, `${r.calcShown} 個`);
        check(`${file} は紙にも見本の映像を残す`, r.samplesHidden === 0, `${r.samplesHidden} / ${r.samples} 本が非表示`);
        check(`${file} は紙に背景の映像を刷らない`, r.heroVideoShown === 0, `${r.heroVideoShown} 個`);
        check(`${file} は紙で囲いを外している`, r.clipped === 0, `${r.clipped} 個がはみ出し切り`);
        check(`${file} は紙でも答えを開いておく`, r.faqsHidden === 0, `${r.faqsHidden} / ${r.faqs} 件が閉じたまま`);
        check(`${file} は紙の hero に浮いたものを残さない`, r.floating.length === 0, r.floating.join(' / '));
        /* 文字ごとに、その要素が自分で地を持っていればそれと、
           持っていなければページの地と比べる。
           半透明（チップスの rgba(255,255,255,0.07) など）は、
           そのまま読むと真っ白として扱ってしまうので、地の上に重ねてから見る */
        const over = (fg, bg) => {
            const f = (fg.match(/[\d.]+/g) || []).map(Number);
            const b = (bg.match(/[\d.]+/g) || []).map(Number);
            const a = f.length > 3 ? f[3] : 1;
            if (a >= 1) return fg;
            return `rgb(${[0, 1, 2].map((i) => f[i] * a + b[i] * (1 - a)).join(', ')})`;
        };
        const faint = r.invisible.filter(([, c, b]) => {
            const own = b && !/transparent/.test(b) && !/rgba\([^)]*,\s*0\)/.test(b);
            return cr(c, own ? over(b, r.bg) : r.bg) < 3;
        });
        check(`${file} は紙でも文字が地から浮く`, faint.length === 0,
            faint.slice(0, 3).map(([t, c]) => `「${t}」${c}`).join(' / ') || `${r.invisible.length} 個を確認`);
        await page.close();
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
