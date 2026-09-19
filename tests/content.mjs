/* 文言と実装がズレていないか。
   同じことを複数箇所に書いているので、片方だけ直すと嘘になる。
   ここはその突き合わせ専用。 */
import { check, report, open, BASE, PW, TIERS, LENGTHS, leadWeeks, RATE } from './lib.mjs';
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
/* 適格請求書発行事業者の登録をしていないので、消費税を別途請求しない。
   表示額がそのまま総額。「税別」が1つでも残っていたら落とす */
check('金額の表示は税込で揃っている',
    !/税別|税抜/.test(await (await page.request.get(`${BASE}/index.html`)).text()));
/* 免税事業者だと先に伝える。発注側は仕入税額控除の扱いが変わるので、
   見積りを見たあとの画面に置く。経過措置の割合や期限は時期で変わるので
   書かない（書くと古くなる） */
/* 支払条件。着手金を取る理由（生成費が納品前に出る）と、キャンセル時の
   段階を書いてあること。金額の割合は料金セクションと FAQ の2か所に
   書いているので、片方だけ直すと嘘になる */
{
    const pay = await page.locator('.plan-pay').innerText();
    check('着手金50%と書いてある', /着手金\s*50%/.test(pay), pay.slice(0, 40));
    check('残金50%と納品後を書いてある', /残金\s*50%/.test(pay) && /納品後/.test(pay));
    check('支払期日を書いてある', /納品日から30日以内/.test(pay));
    check('キャンセルの段階を書いてある',
        ['構成案', '絵コンテ', '初稿'].every(w => pay.includes(w)), pay);
    const payFaq = faqUi.find(u => /お支払い/.test(u.q));
    check('支払条件を FAQ にも置いている', !!payFaq);
    const figures = ['50%', '80%', '100%', '30日以内'];
    check('FAQ と料金セクションで割合・期日が揃っている',
        figures.every(w => pay.includes(w) && payFaq.a.includes(w)),
        figures.filter(w => !(pay.includes(w) && payFaq.a.includes(w))).join(','));
}
/* ロゴは「重ねる」と「映像の中の物に入れる」で難易度が違う。
   混ぜて書くと期待がずれるので、両方に触れていることを見る */
{
    const logo = faqUi.find(u => /ロゴを映像/.test(u.q));
    check('ロゴの FAQ がある', !!logo);
    check('重ねられると書いてある', /重ねて/.test(logo.a), logo && logo.a.slice(0, 40));
    check('映像の中の物に入れるのは苦手だと書いてある',
        /映像の中の物にロゴが入った状態をつくるのは苦手/.test(logo.a));
    check('苦手な例を挙げている',
        ['看板', '車体', 'パッケージ', '名札'].every(w => logo.a.includes(w)));
    check('理由（細かい文字を描けない）を書いてある', /細かい文字を正しく描けない/.test(logo.a));
    check('代わりの進め方を書いてある', /無地のまま生成/.test(logo.a));
}
{
    const tax = await page.locator('.plan-tax').innerText();
    check('インボイス未登録を料金セクションに明記している',
        /適格請求書発行事業者の登録はしておりません/.test(tax), tax.slice(0, 40));
    check('仕入税額控除に触れている', /仕入税額控除/.test(tax));
    check('経理担当への確認を促している', /経理/.test(tax));
    check('経過措置の割合や期限は書いていない',
        !/80%|50%|8割|5割|経過措置|2029年/.test(tax), tax);
    check('インボイスの注記は料金セクションの中にある',
        await page.locator('#plans .plan-tax').count() === 1);
}
/* 「撮影しない理由」の写真の上に置く印（9/19）。
   白い丸＋赤（#d92e26）の禁止マークをやめ、見出しと同じ言葉の札にした。
   赤はサイト全体でここにしか出てこない色だったので、戻っていないことも見る */
{
    const marks = await page.locator('#why .stage-mark').allInnerTexts();
    check('印が文字になっている',
        marks.length === 2 && /出演者[\s\S]*0人/.test(marks[0]) && /撮影日[\s\S]*0日/.test(marks[1]),
        JSON.stringify(marks));
    check('印に画像やアイコンを使っていない',
        await page.locator('#why .stage-mark svg, #why .stage-mark img').count() === 0);
    check('丸に戻っていない',
        await page.locator('#why .stage-mark').first().evaluate(
            (el) => getComputedStyle(el).borderRadius !== '50%'));
    /* 1枚目のステージは背景も写真も暗い。札を黒にすると溶けて読めないので、
       白で抜いていること（9/19 に黒→白へ直した） */
    const mk = await page.locator('#why .stage-mark').first().evaluate((el) => {
        const cs = getComputedStyle(el);
        const lum = (c) => {
            const [r, g, bl] = (c.match(/[\d.]+/g) || [0, 0, 0]).slice(0, 3).map(Number)
                .map((x) => { x /= 255; return x <= 0.03928 ? x / 12.92 : ((x + 0.055) / 1.055) ** 2.4; });
            return 0.2126 * r + 0.7152 * g + 0.0722 * bl;
        };
        return { bg: lum(cs.backgroundColor), fg: lum(cs.color) };
    });
    check('札が白っぽい（暗い背景に溶けない）', mk.bg > 0.6, JSON.stringify(mk));
    /* スマホでも札を出す。写真の重なりだけ畳み、札は PC と同じ見た目にする
       （9/19。いったん「スマホでは出さない」と決めたが、出す方に変えた）。
       数字を vw で縮めると PC より小さくなるので、大きさが揃うことも見る */
    {
        const sp = await open(browser, { width: 390, height: 780, mobile: true });
        check('スマホでも札がある', await sp.locator('#why .stage-mark').count() === 2);
        check('スマホでは写真の重なりは畳んでいる',
            await sp.locator('#why .stack figure').first().isVisible() === false);
        const numSize = (pg) => pg.locator('#why .stage-mark b').first()
            .evaluate((el) => getComputedStyle(el).fontSize);
        const spSize = await numSize(sp);
        const whyText = await sp.locator('#why').innerText();
        check('スマホでも言いたいことは本文に残っている',
            ['誰の顔も', '撮影日を', '登場人物はすべて AI が生成']
                .every((w) => whyText.includes(w)), whyText.slice(0, 60));
        await sp.close();
        const wide = await open(browser, { width: 1440 });
        const wideSize = await numSize(wide);
        check('札の大きさが PC と揃っている', spSize === wideSize, `${spSize} / ${wideSize}`);
        await wide.close();
    }
    check('札の文字は濃い色', mk.fg < 0.2, JSON.stringify(mk));
    /* 経緯をコメントに書いてあるので、コメントを外してから見る */
    const css = (await (await page.request.get(`${BASE}/assets/site.css`)).text())
        .replace(/\/\*[\s\S]*?\*\//g, '');
    check('サイトに赤（#d92e26）が残っていない', !/#d92e26/i.test(css),
        (css.match(/.{0,30}#d92e26.{0,30}/i) || [''])[0]);
}

/* 料金セクションの下半分（9/19）。以前は同じ白い箱が5枚続いていて、
   計算機の根拠（金額の内訳）と、読まなくても発注できる注記が同じ格だった。
   箱は「金額の内訳」だけにして、残り4つは .plan-foot にまとめて格を下げる。
   また箱が増えたら落とす */
{
    const boxOf = (sel) => page.locator(sel).evaluate((el) => {
        const cs = getComputedStyle(el);
        return { bg: cs.backgroundColor,
                 border: parseFloat(cs.borderTopWidth) + parseFloat(cs.borderLeftWidth)
                       + parseFloat(cs.borderRightWidth) + parseFloat(cs.borderBottomWidth) };
    });
    const note = await boxOf('#plans .plan-note');
    check('金額の内訳は箱のまま残っている',
        note.bg !== 'rgba(0, 0, 0, 0)' && note.border > 0, JSON.stringify(note));
    for (const sel of ['.plan-common', '.plan-pay', '.plan-tax']) {
        const b = await boxOf(`#plans ${sel}`);
        check(`${sel} を箱にしていない`,
            b.bg === 'rgba(0, 0, 0, 0)' && b.border === 0, JSON.stringify(b));
    }
    check('注記は1つのまとまりに入っている',
        await page.locator('#plans .plan-foot > *').count() === 3
        && await page.locator('#plans .plan-foot .plan-common').count() === 1
        && await page.locator('#plans .plan-foot .plan-tax').count() === 1);
    /* 見た目を落としただけで、中身は消していない */
    const footText = await page.locator('#plans .plan-foot').innerText();
    check('注記の中身が残っている',
        ['どの組み合わせにも含まれます', 'お支払いとキャンセル', '適格請求書', '5分を超える場合']
            .every((w) => footText.includes(w)), footText.slice(0, 60));
}
/* 制作の流れの各工程に添える一行は、納期（2〜4営業日など）を書く欄。
   01 だけ「1回・約60分」と所要時間を約束していたので外した（9/19）。
   打ち合わせの長さを先に決め打ちすると、案件によって守れなくなる */
{
    const flow = await page.locator('#process .flow').innerText();
    check('打ち合わせの所要時間を約束していない', !/\d+\s*分/.test(flow),
        (flow.match(/.{0,16}\d+\s*分.{0,16}/) || [''])[0]);
    /* 打ち合わせをやめ、ヒアリングもメールにした（9/19）。売りとして書く */
    check('ヒアリングがメールのみだと書いてある',
        /メールのみ・打ち合わせは不要です/.test(flow));
    check('シートに記入する形だと書いてある', /シートにご記入/.test(flow));
    /* 4回だけ、という約束は別の場所にもあるので、そこは崩れていないこと */
    const proc = await page.locator('#process').innerText();
    check('お客様の対応は4回だけ、が残っている', /4回だけです/.test(proc));
    check('4回ともメールだと書いてある', /いずれもメールで完結します/.test(proc));
    /* 打ち合わせが要るかどうかは FAQ でも聞かれる。ここが「必要ありません」で
       始まっていないと、流れの説明と食い違う */
    const meetFaq = faqUi.find((u) => /打ち合わせや立ち会い/.test(u.q));
    check('打ち合わせの FAQ が「必要ありません」で始まる',
        !!meetFaq && /^必要ありません/.test(meetFaq.a), meetFaq && meetFaq.a.slice(0, 30));
    check('FAQ もメールで完結すると書いてある', /すべてメールで完結します/.test(meetFaq.a));
    /* 会社概要の対応地域も、打ち合わせ前提の書き方が残っていないこと */
    const ab = await open(browser, { page: 'about.html' });
    check('会社概要もメールで完結と書いてある',
        /お問い合わせから納品までメールで完結します/.test(await ab.locator('body').innerText()));
    await ab.close();
}

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
    /* サンプルは「見せられないものは売らない」の裏づけなので、欠けたら落とす。
       ミュージックビデオ（9/19 追加・現09）だけは、クレジット残が足りず 90秒の MV を
       1本つくれないため、サンプルなしで先に公開している。黙って緩めないよう、
       例外はこの1枚に限る形で書く。サンプルができたらこの除外を外す */
    const noSample = await page.locator('.genre:not(:has(.sample-video))').evaluateAll(
        (els) => els.map((e) => e.id));
    check('サンプルが無いのはミュージックビデオだけ',
        noSample.join(',') === 'genre-mv', noSample.join(','));
    check('ミュージックビデオ以外の全ジャンルにサンプルが入っている',
        (await page.locator('.genre .sample-video').count())
        === (await page.locator('.genre').count()) - 1);
    /* サンプルが無いぶん、いまどういう状態かをカードに書く。
       黙って空にすると「作れないジャンル」に見える */
    check('ミュージックビデオのカードに状態と料金の扱いが書いてある',
        /サンプルは準備中/.test(await page.locator('#genre-mv').innerText())
        && /料金表ではなく個別にお見積り/.test(await page.locator('#genre-mv').innerText()),
        await page.locator('#genre-mv').innerText());
    /* 09 アニメーション・図解（9/19 追加）。生成AIを使っていない唯一のサンプル。
       文字が主役の題材はAIが画面内の文字を描けないので、プログラム描画だと
       明記してあること（これが売り文句であり、嘘をつかないための断りでもある） */
    {
        const an = await page.locator('#genre-animation').innerText();
        check('アニメーションのカードにサンプルがある',
            await page.locator('#genre-animation .sample-video').count() === 1);
        check('プログラム描画だと明記している', /すべてプログラムで描いています/.test(an), an.slice(0, 60));
        check('架空の題材だと断っている', /架空の健康保険組合/.test(an));
        check('尺違いに触れている', /尺違い/.test(an));
    }
    /* about.html のフッターのジャンル一覧は静的に書いてある（トップは自動生成）。
       「ズレたら e2e で落ちる」と about.html に書いてあったのに検査が無かったので、
       ここで突き合わせる。09 追加のときに MV の載せ忘れも見つかった */
    {
        const cards = await page.locator('#genres .genre h3').allInnerTexts();
        const ap = await open(browser, { page: 'about.html' });
        const foot = await ap.locator('#footer-genres li').allInnerTexts();
        check('about のフッターのジャンル一覧がトップのカードと一致',
            JSON.stringify(cards) === JSON.stringify(foot),
            `top=${cards.join('/')} about=${foot.join('/')}`);
        await ap.close();
    }
    /* MV は計算機に乗せない。工数を一度も測っていないので、
       定価を出すと測る前に金額を宣言することになる */
    /* 6列の割り付けをジャンルの枚数に合わせているので、枚数を足すと
       最後の1枚が3分の1幅で取り残されることがある（08 を足したとき実際に起きた）。
       行ごとに幅を使い切っているかを見て、取り残しを機械で拾う */
    {
        const wide = await open(browser, { width: 1280, page: 'index.html' });
        const rows = await wide.evaluate(() => {
            const by = new Map();
            for (const el of document.querySelectorAll('.genre')) {
                const r = el.getBoundingClientRect();
                const k = Math.round(r.top + scrollY);
                if (!by.has(k)) by.set(k, []);
                by.get(k).push(Math.round(r.width));
            }
            const gap = 20;
            return [...by.values()].map((ws) =>
                ({ n: ws.length, total: ws.reduce((a, b) => a + b, 0) + gap * (ws.length - 1) }));
        });
        const full = Math.max(...rows.map((r) => r.total));
        check('ジャンルの各行が幅を使い切っている',
            rows.every((r) => Math.abs(r.total - full) <= 4),
            JSON.stringify(rows));
        check('最後の行に1枚だけ取り残されていない',
            rows[rows.length - 1].n >= 2, JSON.stringify(rows));
        await wide.close();
    }

    check('ミュージックビデオのカードに金額を書いていない',
        !/¥[\d,]+/.test(await page.locator('#genre-mv').innerText()));
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
/* 文言の方向（2026-09-20）：撮影が「無い」ことではなく、AI だから
   できるようになることを前に出す。ただし書けるのは確かめられる事実だけ。 */
{
    const svc = await page.locator('#service').innerText();
    check('できるようになることを書いている',
        /訴求違い/.test(svc) && /差し替え/.test(svc), svc.slice(0, 40));
    check('自社サンプルの日数と一致している', /3日間/.test(svc));
    check('2本目の値段が料金表と一致している', /¥65,000/.test(svc));
    check('誇大な言い方をしていない',
        !/必ず|絶対|劇的|革命|No\.?1|業界最|最先端/.test(svc), svc.slice(0, 60));
    /* お客様の状況を勝手に決めつけない（2026-09-20）。
       「年に1本の大仕事」と書いたが、こちらで確かめられない前提だった */
    check('相手の制作頻度を決めつけていない',
        !/年に1本|年1本|どこの会社も|みなさん/.test(svc), svc.slice(0, 60));
    const hero = await page.locator('.hero-inner').innerText();
    check('ヒーローもできることで書いている',
        /3日で1本できる/.test(hero) && /訴求違い/.test(hero));
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
/* 経歴。クライアント事例が0本のあいだ、発注の判断材料がサイトに何もない状態を
   埋めるためのもの。前職の社名と受注額は出さないと決めた（2026-09-18）。
   検査に社名を書くとこのファイル経由で公開されてしまうので、書かない。
   「経て」「一貫して担当」で職歴の形になっていることだけを見る */
{
    const career = rows.find(([k]) => k === '経歴');
    check('会社概要に経歴の行がある', !!career, rows.map(([k]) => k).join('/'));
    check('経歴が職歴の形になっている',
        /経て/.test(career[1]) && /一貫して担当/.test(career[1]), career && career[1]);
    check('経歴に受注額を書いていない', !/万円|1,500|1500/.test(career[1]), career && career[1]);
    check('経歴が長すぎない', career[1].length <= 120, String(career[1].length));
}

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

/* ---- 修正回数 ----
   段によって違う（梅2・竹3・松3）。about.html が「3回まで調整できる」と
   言い切っていて、梅（標準）で受注したら約束を破る状態だった（2026-09-17 に直した）。
   index.html は全箇所「段階に応じて2〜3回」で揃えているので、about も揃える */
check('about: 修正回数に段の限定が付いている', /仕上げの段階に応じて2〜3回まで/.test(about));
check('index: 修正回数に段の限定が付いている', /段階に応じて2〜3回/.test(idx));
check('段ごとの回数を FAQ に書いている',
    faqUi.some(u => /修正は何回/.test(u.q) && /梅は2回、竹と松は3回/.test(u.a)));
{
    /* 画面に出る文字で見る。許すのは「2〜3回まで」「竹と松は3回まで」と、
       竹・松の段カードの中の「修正3回まで」だけ。それ以外の言い切りは落とす */
    const ok = /2〜3回まで|竹と松は3回まで|修正3回まで/;
    for (const f of ['index.html', 'about.html']) {
        const pg = await open(browser, { page: f });
        const body = await pg.locator('body').innerText();
        const bad = [...body.matchAll(/.{0,8}3回まで/g)].map(m => m[0]).filter(t => !ok.test(t));
        check(`${f}: 段の限定なしに「3回まで」と書いていない`, bad.length === 0, bad.join(' / '));
        await pg.close();
    }
}

/* ---- 公開範囲 ---- */
/* 最後の CTA。アドレスの文字組みは残したまま、押す先をボタンでも出す（9/19）。
   ここはサイトで一番の転換点なので、リンクがテキストだけの状態に戻ったら落とす */
{
    const btn = page.locator('.cta-band .pill-invert');
    check('最後のCTAにボタンがある', await btn.count() === 1);
    check('CTAのボタンがメールに繋がっている',
        (await btn.getAttribute('href') || '').startsWith('mailto:bonvoyage.ti@icloud.com'),
        await btn.getAttribute('href'));
}

for (const [f, html] of [['index.html', idx], ['about.html', about], ['privacy.html', privacy]]) {
    check(`${f} は検索結果に出さない`, /name="robots" content="noindex/.test(html));
}
const rb = await (await page.request.get(`${BASE}/robots.txt`)).text();
check('robots.txt でクロールは止めていない', /Allow: \//.test(rb) && !/Disallow: \//.test(rb));

/* ---- ロードマップ(社内用・要約版) ----
   9/17 に2ページに割った。roadmap.html は判断だけを短く置き、
   根拠（各段階の中身・松2本の実測・12ヶ月の計算）は record.html に移した。
   折りたたみを開かないと読めない資料だったのが「分かりづらい」の中身だったので、
   要約版には fold を1つも置かない。ここではそれを検査する */
{
    const rm = await open(browser, { page: 'roadmap.html' });
    const t = await rm.locator('body').innerText();

    check('目標が計画と一致', /¥11,295,000/.test(t) && /¥10,408,605/.test(t));
    check('要約版に折りたたみを置いていない',
        await rm.locator('details').count() === 0);
    check('裏づけのページへ導線がある',
        await rm.locator('a[href^="record.html"]').count() >= 2);

    /* いまの位置。4つのタイルで、営業を始める前に押さえる数字が読める */
    const now = await rm.locator('.now .stop b').allInnerTexts();
    check('いまの位置が4つのタイルで読める', now.length === 4, now.join('/'));
    check('未開業・クレジット残・事例0本・初入金までが出ている',
        now.join('/') === '未開業/246.84/0本/約1ヶ月', now.join('/'));

    /* 支払条件を 9/17 に決めた（着手金50%＋納品後50%、期日は納品日から30日以内）。
       手元資金の表はこの前提で引き直してある */
    check('支払条件が手元資金の前提に入っている',
        /着手金50% は着手した月/.test(t) && /残金50% は納品月の翌月/.test(t));
    /* 表そのものを見る。前後の比較を書いた本文にも旧数字が出るので、
       本文まで含めて検索すると「直したのに落ちる」ことになる */
    const need = await rm.locator('#cash tbody tr td:last-child').allInnerTexts();
    check('必要な貯蓄が新しい支払条件で引き直されている',
        need.join('/') === '40万/50万/60万', need.join('/'));
    check('底が10月末になっている', /底は10月末/.test(t));
    check('着手金を値引きの対象にしないと書いている', /着手金は値引きの対象にしない/.test(t));

    /* 4段階は1行ずつの表に畳んだ。月商は計画（README の料金の考え方）と同じ */
    const stages = await rm.locator('table.t-wide tbody tr').count();
    check('4つの段階が表になっている', stages >= 4, String(stages));
    check('段階ごとの月商が計画と一致',
        /¥600,000/.test(t) && /¥915,000/.test(t) && /¥1,125,000/.test(t));

    /* P0 はいま動いている段階なので、要約版に残りタスクを置く */
    check('P0 の残りタスクが載っている',
        ['開業届', 'ひな形', 'プロフィール', '手元資金'].every((w) => t.includes(w)));

    /* 9/18 にチェックリスト式へ直した。状態は HTML に持たせてブラウザには保存しない
       （端末ごとに違う状態を持つとリポジトリの記録とズレるため）。
       残り＝未チェックがページ上部、済＝チェック済みが P0 に並ぶ */
    const ckAll = await rm.locator('.ck.p0 li').count();
    const ckDone = await rm.locator('.ck.p0 li.done').count();
    const ckLeft = await rm.locator('.ck.p0 li:not(.done)').count();
    check('チェックリストになっている', ckAll >= 12 && ckDone >= 9, `${ckDone}/${ckAll}`);
    /* 件数を手で書いているので、実際のチェック数とズレたら落とす。
       数えるのは P0 のぶんだけ（「このあとの宿題」は別勘定） */
    check('進捗の数字が実際のチェック数と合っている',
        t.includes(`${ckAll}項目中 ${ckDone}件 完了`), `${ckDone}/${ckAll}`);
    check('残りは未チェックで置いてある', ckLeft === 3, String(ckLeft));

    /* このあとの宿題。いま動かせないものなので、全部未チェックで始まる。
       日付ではなく着手条件で書くと決めたので、各項目に条件が要る */
    const next = await rm.locator('.ck.next li').allInnerTexts();
    check('このあとの宿題が載っている', next.length >= 5, String(next.length));
    check('宿題は未チェックで置いてある',
        await rm.locator('.ck.next li.done').count() === 0);
    check('宿題に着手条件が書いてある',
        next.every((x) => /てから|届いたら|ときに|まで|次号|1本目/.test(x)),
        next.find((x) => !/てから|届いたら|ときに|まで|次号|1本目/.test(x)) || '');
    check('実測と受注経路の宿題が入っている',
        next.some((x) => /実消費クレジット/.test(x))
        && next.some((x) => /受注経路/.test(x)), next.join(' | '));
    /* COLOWORKS（日本コロムビアのAIクリエイター公募）は 9/18 に登録し、同日に取り下げた。
       宿題として残っていると嘘になるので、載っていないことを見る */
    check('取り下げた COLOWORKS が残っていない', !/COLOWORKS/i.test(t));

    /* 未チェックのまま「済」と書いていないか（チェック漏れではなく書き間違いを拾う）。
       宿題の側は「登録済み」のように途中経過を書くので、P0 の残りだけを見る */
    const leftTxt = await rm.locator('.ck.p0 li:not(.done)').allInnerTexts();
    check('未チェックの項目を済と書いていない', !leftTxt.some((x) => /済/.test(x)), leftTxt.join(' | '));

    const doneTxt = await rm.locator('.ck.p0 li.done').allInnerTexts();
    check('決着ぶんが済に入っている',
        doneTxt.some((d) => /支払条件/.test(d) && /9\/17/.test(d))
        && doneTxt.some((d) => /インボイス/.test(d) && /登録しない/.test(d)), doneTxt.join(' | '));
    /* 済の項目はいつ終わったかが分かること。日付のない「済」は後から検算できない */
    check('済の項目に日付が入っている',
        doneTxt.every((d) => /\d+\/\d+/.test(d)), doneTxt.find((d) => !/\d+\/\d+/.test(d)) || '');
    check('崩れるときの表がある', /この計画が崩れるとき/.test(t));
    check('未開業であることを書いている', /未開業/.test(t));

    /* 9/18 にチェックを押せるようにした。押したぶんはこの端末の localStorage にだけ
       残り、リポジトリには入らない。だから「何件ズレているか」を必ず画面に出す。
       確定させるときは HTML を直してコミットする（＝ズレが0に戻る） */
    check('チェックを押せる',
        await rm.locator('.ck li .box[role="checkbox"]').count() === ckAll + next.length,
        String(await rm.locator('.ck li .box[role="checkbox"]').count()));
    check('押す前はズレの知らせが出ていない', await rm.locator('#ck-local').isVisible() === false);
    await rm.locator('[data-id="p0-kaigyo"] .box').click();
    check('押すとチェックが付く',
        await rm.locator('[data-id="p0-kaigyo"]').evaluate((el) => el.classList.contains('done')));
    check('押すと件数が増える',
        (await rm.locator('#ck-count').innerText()).includes(`${ckDone + 1}件`),
        await rm.locator('#ck-count').innerText());
    /* 知らせは件数だけでなく、確定のしかた（HTML を直してコミット）まで書く。
       端末間の同期はしないと決めた（9/18）ので、ここが唯一の確定経路になる */
    check('押すとズレの知らせが出る',
        await rm.locator('#ck-local').isVisible()
        && (await rm.locator('#ck-local').innerText()).includes('1件'));
    check('知らせに確定のしかたが書いてある',
        /コミット/.test(await rm.locator('#ck-local').innerText()),
        await rm.locator('#ck-local').innerText());
    await rm.reload({ waitUntil: 'networkidle' });
    check('押した状態が再読込のあとも残る',
        await rm.locator('[data-id="p0-kaigyo"]').evaluate((el) => el.classList.contains('done')));
    await rm.locator('#ck-reset').click();
    check('「記録の状態に戻す」で元に戻る',
        await rm.locator('#ck-local').isVisible() === false
        && (await rm.locator('#ck-count').innerText()).includes(`${ckDone}件`));
    /* プライベートブラウズなどで localStorage が触れないことがある。
       そこで例外が出るとページ全体が止まるので、落ちずに表示だけ出ることを見る */
    {
        const np = await open(browser, { page: 'roadmap.html' });
        await np.addInitScript(() => {
            Object.defineProperty(window, 'localStorage', { get() { throw new Error('denied'); } });
        });
        await np.reload({ waitUntil: 'networkidle' });
        check('localStorage が使えなくても表示が壊れない',
            await np.locator('.ck.p0 li.done').count() === ckDone && np.__errors.length === 0,
            JSON.stringify(np.__errors));
        await np.close();
    }

    check('社内用なので検索に出さない',
        (await rm.evaluate(() => document.querySelector('meta[name="robots"]')?.content || '')).includes('noindex'));
    check('ロードマップで横溢れなし',
        (await rm.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth)) <= 0);
    /* 要約版なので長さそのものを見る。ここが膨らんだら分割した意味がなくなる */
    check('要約版が長くなりすぎていない', t.length < 4000, String(t.length));
    await rm.close();
}

/* ---- ヒーローの背景 ----
   YouTube のサムネイルを流していたのを、実際に納品した映像そのものに
   差し替えた（9/19）。テロップは焼き込まれているので、上側16:9を切り出して
   帯ごと外してある。文字の読みやすさは a11y.mjs のコントラスト検査が見る */
{
    const v = page.locator('#hero-video');
    check('ヒーローの背景がサンプル映像になっている', await v.count() === 1);
    check('映像は自前で配信している',
        /assets\/works\/hero-reel\.(webm|mp4)/.test(idx) && !/i\.ytimg\.com[^"']*hero/.test(idx));
    check('mp4 と webm の両方を置いている',
        /hero-reel\.mp4/.test(idx) && /hero-reel\.webm/.test(idx));
    check('音を出さず、繰り返し、インラインで再生する',
        ['muted', 'loop', 'playsinline'].every((a) => idx.includes(a)));
    /* 回線と電池を使うので、ポスターを置いて先に絵を出す */
    check('ポスター画像がある',
        (await v.getAttribute('poster') || '').includes('hero-reel.jpg'));
    /* 画面から外れたら止める作りなので、ここまでのスクロールで止まっている。
       先頭に戻したら再開することまで見る */
    await page.evaluate(() => window.scrollTo({ top: 0, behavior: 'instant' }));
    await page.waitForTimeout(500);
    check('先頭に戻ると再生が再開する',
        await v.evaluate((e) => !e.paused && e.currentTime > 0),
        JSON.stringify(await v.evaluate((e) => ({ paused: e.paused, t: e.currentTime }))));
    /* 「動きを減らす」設定のときは再生しない（ポスターのまま止める） */
    {
        const still = await open(browser, { page: 'index.html' });
        await still.emulateMedia({ reducedMotion: 'reduce' });
        await still.reload({ waitUntil: 'domcontentloaded' });
        await still.waitForTimeout(900);
        check('動きを減らす設定では再生しない',
            await still.locator('#hero-video').evaluate((e) => e.paused));
        await still.close();
    }
}

/* ---- 社内2ページの「前提」に書いた目標時間単価 ----
   料金と工数のモデルを動かすとここがズレる。9/16 に工数モデルを実測へ
   合わせたとき、古い ¥14,900（重いモデルからの逆算）が残ったまま 9/19 まで
   気づかなかった。lib.mjs の RATE を唯一の出どころにして突き合わせる */
{
    const want = `¥${RATE.toLocaleString('ja-JP')}`;
    for (const file of ['roadmap.html', 'record.html']) {
        const pg = await open(browser, { page: file });
        const body = await pg.locator('body').innerText();
        check(`${file} の前提が目標時間単価と一致`, body.includes(want), want);
        check(`${file} に古い時間単価が残っていない`, !/14,900/.test(body),
            (body.match(/.{0,24}14,900.{0,24}/) || [''])[0]);
        await pg.close();
    }
}

/* ---- 実測記録と裏づけ(社内用) ----
   もとは roadmap.html の中にあった。数字はサイトの料金表・工数モデルから
   出しているので、料金を動かしたらここもズレる。主要な数字だけ突き合わせる */
{
    const rc = await open(browser, { page: 'record.html' });

    /* 折りたたむ前に、たたんだ状態のままで主要な数字が読めるかを見る。
       たたんだ見出しに数字が出ていないと、開かないと何も分からない資料になる */
    const folded = await rc.locator('body').innerText();
    check('たたんだままでも年商・年収が読める',
        /¥11,295,000/.test(folded) && /¥10,408,605/.test(folded));
    check('たたんだままでも天井と必要な問い合わせ数が読める',
        /1,950万/.test(folded) && /6\.7件/.test(folded));
    check('ロードマップへ戻る導線がある',
        await rc.locator('a[href^="roadmap.html"]').count() >= 1);

    /* 折りたたみを全部開いてから、中身の数字を突き合わせる */
    const foldCount = await rc.evaluate(() => {
        const d = document.querySelectorAll('details.fold');
        d.forEach((x) => { x.open = true; });
        return d.length;
    });
    check('折りたたみが存在する', foldCount >= 5);
    check('「すべて開く」ボタンがある', await rc.locator('#openall').count() === 1);

    const t = await rc.locator('body').innerText();
    check('四半期計が計画と一致',
        /¥1,800,000/.test(t) && /¥2,745,000/.test(t) && /¥3,375,000/.test(t) && /¥11,295,000/.test(t));
    check('P1〜P3 の中身が移っている',
        /90秒で足場をつくる/.test(t) && /3分を売れるようにする/.test(t) && /年収1,000万に乗せる/.test(t));
    /* サンプルは 9/17 に5本足して7ジャンル全部に載った。
       「01と06の2本だけ」が残っていたら実態とズレている */
    check('サンプルが7ジャンル全部に載ったと書いてある',
        /7ジャンル全部にサンプルが載った/.test(t) && /719\.30/.test(t));
    check('サンプルが架空案件だと断ってある', /全部が架空案件のもの/.test(t));
    /* 実工数は工程別に測り直して 11.5h（本編10.5 ＋ 15秒版1.0）。
       以前の「17.0h」は内訳を取る前の概算だった（2026-09-16 訂正） */
    check('松2本の実測が記録されている',
        /2,442/.test(t) && /1,221/.test(t) && /11\.5時間/.test(t));
    check('クレジット残高とプランが最新', /246\.84/.test(t) && /Max/.test(t));
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
    check('実際に納品した2本の尺と時間単価が載っている',
        /59秒/.test(t) && /15秒/.test(t) && /¥41,905\/h/.test(t) && /¥80,000\/h/.test(t));
    check('料金表どおりの金額を出している',
        /¥647,100/.test(t) && /¥520,000/.test(t));
    check('追加尺が料金表の2本目にあたると書いている',
        /¥65,000/.test(t) && /¥189,750/.test(t) && /上乗せ/.test(t));
    check('追加尺がほぼ純利益だと書いている', /純利益/.test(t) && /2時間/.test(t));
    check('2本・架空案件だけの数字だと断っている', /2本/.test(t) && /架空/.test(t));
    check('営業ロープレであって実案件でないと明記', /ロープレ/.test(t) && /架空/.test(t));
    check('社内用なので検索に出さない',
        (await rc.evaluate(() => document.querySelector('meta[name="robots"]')?.content || '')).includes('noindex'));
    check('裏づけのページで横溢れなし',
        (await rc.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth)) <= 0);
    await rc.close();
}

/* ---- 見積書・契約書・請求書のひな形 ----
   数字（着手金50%・期日・修正回数・キャンセルの按分・−¥25,000・¥70,000）は
   サイトの料金ページに揃えてある。サイトだけ直すとひな形が古い条件のまま
   お客様に出ていくので、突き合わせて見張る（9/18 作成） */
{
    const T = '成果物/_テンプレート';
    const mitsu = readFileSync(`${ROOT}/${T}/見積書.md`, 'utf8');
    const keiyaku = readFileSync(`${ROOT}/${T}/業務委託契約書.md`, 'utf8');
    const seikyu = readFileSync(`${ROOT}/${T}/請求書.md`, 'utf8');
    const hearing = readFileSync(`${ROOT}/${T}/ヒアリングシート.md`, 'utf8');
    const all = mitsu + keiyaku + seikyu;

    check('ひな形3点が空でない', [mitsu, keiyaku, seikyu].every(x => x.length > 500));
    check('ひな形に税別・税抜が残っていない', !/税別|税抜/.test(all));
    check('ひな形3点とも消費税を別途請求しない旨がある',
        [mitsu, keiyaku, seikyu].every(x => /消費税を(別途請求|区分して請求)/.test(x)));
    check('支払条件がサイトと揃っている(着手金50%・納品日から30日以内)',
        [mitsu, keiyaku].every(x => /50%/.test(x) && /納品日から30日以内/.test(x)));
    check('着手金の期日が契約書と請求書で揃っている',
        [keiyaku, seikyu].every(x => /請求書発行日から14日以内/.test(x)));
    check('キャンセルの按分がサイトと揃っている',
        [mitsu, keiyaku].every(x => /80%/.test(x) && /100%/.test(x) && /絵コンテ/.test(x)));
    check('修正回数がサイトと揃っている(梅2・竹3・松3)',
        /梅2回・竹3回・松3回/.test(keiyaku) && /梅2回・竹3回・松3回/.test(mitsu));
    check('ナレーションの条件が見積書にある',
        /−¥25,000/.test(mitsu) && /¥70,000/.test(mitsu));
    check('料金の単位がサイトと揃っている(基本料金と追加本数)',
        /¥90,000/.test(mitsu) && /¥65,000/.test(mitsu));
    check('契約書にAI特有の免責がある',
        /著作権による保護を\s*受けない場合がある/.test(keiyaku) && /意図しない類似/.test(keiyaku));
    check('契約書に権利の帰属がある', /報酬の完済をもって/.test(keiyaku) && /制限なく利用できる/.test(keiyaku));
    check('実績掲載は相手が断れる形になっている', /公開を\s*希望しない場合/.test(keiyaku));
    check('請求書に登録番号の欄が無い', !/登録番号 \||T\d{13}/.test(seikyu), (seikyu.match(/T\d{13}/) || [''])[0]);
    /* 番号の例(S-20261001-001)に7桁以上の数字が含まれるので、全文の数字検索ではなく
       振込先の行が空欄(＿)のままかを見る */
    /* MV・リリックビデオ用の特約（9/19 追加）。企業向けの条項では
       楽曲の権利を扱えないので、受ける前に必ず要る。
       サイトの 08 のカードは「料金表ではなく個別にお見積り」と書いてあるので、
       見積書側にも料金表の対象外であることが書かれていること */
    check('契約書に楽曲の特約がある',
        /## 第7条（楽曲を扱う場合の特約）/.test(keiyaku)
        && /乙は本楽曲の権利処理を行わない/.test(keiyaku));
    check('楽曲の特約がMV以外では外せると書いてある',
        /この条を丸ごと削除する/.test(keiyaku) && /条番号を1つずつ繰り上げる/.test(keiyaku));
    check('楽曲の特約に権利・差替え・容姿・クレジットが入っている',
        ['著作隣接権', '差し替わった場合', '容姿', 'クレジット'].every((w) => keiyaku.includes(w)));
    /* 条番号を繰り下げたので、重複や飛びが出ていないこと */
    check('契約書の条番号が第1条から連番',
        (keiyaku.match(/^## 第(\d+)条/gm) || []).map((x) => Number(x.match(/\d+/)[0]))
            .every((n, i) => n === i + 1),
        (keiyaku.match(/^## 第\d+条/gm) || []).join(','));
    check('見積書にMVの扱いが書いてある',
        /料金表の対象外/.test(mitsu) && /楽曲の権利処理/.test(mitsu));

    /* ヒアリングシート（9/19）。打ち合わせをやめてメールだけで着手するための土台。
       計算機が送るメール本文と項目がズレると、計算機から来た問い合わせに
       同じことを聞き直すことになるので、本文の項目を含んでいるかを見る */
    {
        check('ヒアリングシートがある', hearing.length > 500);
        const fromCalc = ['会社名 / お名前', '映像の用途', '公開時期', '参考'];
        check('計算機のメール本文の項目を含んでいる',
            fromCalc.every((w) => hearing.includes(w) && idx.includes(w)),
            fromCalc.filter((w) => !(hearing.includes(w) && idx.includes(w))).join(','));
        /* 段と尺と本数が決まらないと見積りが出せない。そこへ繋がる欄があること */
        check('見積りに必要な項目を聞いている',
            ['尺', '本数', 'ナレーション', '予算'].every((w) => hearing.includes(w)));
        /* 聞くだけでなく、あとで揉める3点を先に伝える欄があること。
           ロゴの制約はサイトの FAQ と同じことを言っている必要がある */
        const logoFaq = faqUi.find((u) => /ロゴを映像/.test(u.q));
        check('ロゴの制約を先に伝える欄がある',
            /映像の中の物/.test(hearing) && /重ね/.test(hearing)
            && ['看板', '車体', 'パッケージ', '名札'].every((w) =>
                hearing.includes(w) && logoFaq.a.includes(w)));
        check('修正回数がサイトと揃っている', /梅2回・竹3回・松3回/.test(hearing));
        /* 往復を増やさないのがこのシートの目的。そこが書かれていること */
        check('聞き直しを1通にまとめると書いてある', /1通にまとめる/.test(hearing));
    }

    check('実在の口座番号を書いていない',
        /＿＿銀行 ＿＿支店/.test(seikyu) && /普通 ＿/.test(seikyu) && /名義 \| ＿/.test(seikyu));
}

/* ---- 配信できるか ---- */
for (const f of ['assets/site.css', 'assets/logo-mark.png', 'assets/favicon.png',
                 'assets/apple-touch-icon.png', 'assets/ogp.png', 'privacy.html',
                 'funnel.html', 'roadmap.html', 'record.html']) {
    const st = (await page.request.get(`${BASE}/${f}`)).status();
    check(`${f} が配信できる`, st === 200, `HTTP ${st}`);
}
await browser.close();
report();
