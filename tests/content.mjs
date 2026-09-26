/* 文言と実装がズレていないか。
   同じことを複数箇所に書いているので、片方だけ直すと嘘になる。
   ここはその突き合わせ専用。 */
import { check, report, open, BASE, PW, TIERS, LENGTHS, leadWeeks, RATE, PRICE, price, hours } from './lib.mjs';
import { readFileSync, existsSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
const pwmod = (await import(PW)).default;
const ROOT = fileURLToPath(new URL('..', import.meta.url)).replace(/\/$/, '');
const browser = await pwmod.chromium.launch();
const page = await open(browser, {});
const idx = readFileSync(`${ROOT}/index.html`, 'utf8');
/* 計算機は 2026-09-23 に assets/pricing.js へ切り出した。
   値（秒単価・ナレーションの増減）はそちらにある */
const calcSrc = readFileSync(`${ROOT}/assets/pricing.js`, 'utf8');
/* ジャンルのカードとサンプルは 2026-09-23 に works.html へ移した */
const worksSrc = readFileSync(`${ROOT}/works.html`, 'utf8');
const pricingHtml = readFileSync(`${ROOT}/pricing.html`, 'utf8');
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
/* 9/22：「登場人物を増やすと値段が上がるのか」を聞かれた。
   上がるのは段をまたぐときだけで、段の中（竹の1人と2人）は同額。
   人数そのものは料金に入っていないので、そう言い切る。
   曖昧なままだと、2人出したい相談で高い段を勧められたように見える */
/* 「人数そのもので変わらない」とだけ書くと「何人出しても同じ」に読める。
   実際は 0人→1人（梅→竹）と 2人→3人（竹→松）で上がるので、
   「同じ段の中なら変わらない／段が上がれば上がる」の両方を書く */
check('人数と料金の関係を FAQ で説明している',
    faqUi.some((u) => /梅・竹・松/.test(u.q)
        && /同じ段の中なら人数で変わりません/.test(u.a)
        && /3人出したい場合は松になり、そのぶん高くなります/.test(u.a)));
check('「人数では変わらない」とだけ書いていない',
    !faqUi.some((u) => /登場人物の人数そのもので料金は変わりません/.test(u.a)));
/* 9/22：上限（松で3人）を超える場合の行き先が書いていなかった。
   尺（5分超）と本数（上限超）には「同じ考え方でお見積り」があるのに人数だけ無く、
   しかも採用のサンプルが4人で、自分のサンプルが上限を超えていた */
check('4人以上の行き先が FAQ にある',
    faqUi.some((u) => /登場人物が4人以上になる場合も同様です/.test(u.a))
    && faqUi.some((u) => /4人以上を出す場合は料金表の範囲を超えるため、個別にお見積りします/.test(u.a)));
check('採用のサンプルが上限を超えていることを書いている',
    /4人は料金表の上限（松で3人）を超えます/.test(worksSrc));
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
/* 支払条件。9/22 に着手金を外し、納品後の一括払いにした。
   「着手金はいただきません」と明記していること（黙って消すと、
   前の条件を見た人との食い違いに気づけない）。キャンセルの段階も。
   金額の割合は料金セクションと FAQ の2か所に書いているので、
   片方だけ直すと嘘になる */
{
    /* 支払条件・税の注記は 2026-09-23 に pricing.html へ移した */
    const pc = await open(browser, { page: 'pricing.html' });
    const pay = await pc.locator('.plan-pay').innerText();
    check('全額を納品後と書いてある', /全額を納品後/.test(pay), pay.slice(0, 40));
    check('着手金を取らないと明記している', /着手金はいただきません/.test(pay));
    check('着手金50%の記述が残っていない', !/着手金\s*50%/.test(pay) && !/残金\s*50%/.test(pay), pay);
    /* 前金を相談する条件は内部ルール（record.html）であって、サイトには出さない。
       出した瞬間に、条件そのものが受注率の抵抗になる */
    check('前金の条件をサイトに書いていない',
        !/前金/.test(await page.locator('body').innerText())
        && !/前金/.test(await pc.locator('body').innerText()));
    check('支払期日を書いてある', /納品日から30日以内/.test(pay));
    check('キャンセルの段階を書いてある',
        ['絵コンテ', '初稿'].every(w => pay.includes(w)), pay);
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
    const pp = await open(browser, { page: 'pricing.html' });
    const tax = await pp.locator('.plan-tax').innerText();
    check('インボイス未登録を料金セクションに明記している',
        /適格請求書発行事業者の登録はしておりません/.test(tax), tax.slice(0, 40));
    check('仕入税額控除に触れている', /仕入税額控除/.test(tax));
    check('経理担当への確認を促している', /経理/.test(tax));
    check('経過措置の割合や期限は書いていない',
        !/80%|50%|8割|5割|経過措置|2029年/.test(tax), tax);
    /* 計算機と注記は 2026-09-23 に pricing.html へ移した */
    check('インボイスの注記は料金セクションの中にある',
        await pp.locator('#plans .plan-tax').count() === 1);
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
    const boxOf = (sel, pg = page) => pg.locator(sel).evaluate((el) => {
        const cs = getComputedStyle(el);
        return { bg: cs.backgroundColor,
                 border: parseFloat(cs.borderTopWidth) + parseFloat(cs.borderLeftWidth)
                       + parseFloat(cs.borderRightWidth) + parseFloat(cs.borderBottomWidth) };
    });
    /* 料金の節は pricing.html にある（2026-09-23 に移した） */
    const pg2 = await open(browser, { page: 'pricing.html' });
    const note = await boxOf('#plans .plan-note', pg2);
    check('金額の内訳は箱のまま残っている',
        note.bg !== 'rgba(0, 0, 0, 0)' && note.border > 0, JSON.stringify(note));
    for (const sel of ['.plan-common', '.plan-pay', '.plan-tax']) {
        const b = await boxOf(`#plans ${sel}`, pg2);
        check(`${sel} を箱にしていない`,
            b.bg === 'rgba(0, 0, 0, 0)' && b.border === 0, JSON.stringify(b));
    }
    check('注記は1つのまとまりに入っている',
        await pg2.locator('#plans .plan-foot > *').count() === 3
        && await pg2.locator('#plans .plan-foot .plan-common').count() === 1
        && await pg2.locator('#plans .plan-foot .plan-tax').count() === 1);
    /* 見た目を落としただけで、中身は消していない */
    const footText = await pg2.locator('#plans .plan-foot').innerText();
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
    /* ジャンルのカードとサンプルは 2026-09-23 に works.html へ移した */
    const wp = await open(browser, { page: 'works.html' });
    const works = await wp.locator('#genres').innerText();
    const v = wp.locator('.sample-video');
    check('ジャンルのカードにサンプル映像が入っている', (await v.count()) >= 1);
    /* 06 展示会は、同じ案件を無音・テロップ主体で別設計した1本。
       「短く切っただけではない」という主張の裏づけとして置いている */
    check('展示会のカードにもサンプルがある',
        (await wp.locator('#genre-event .sample-video').count()) === 1);
    check('展示会のサンプルは無音だと書いてある',
        /15秒・無音/.test(await wp.locator('#genre-event').innerText()));
    check('展示会のサンプルは実際に音が入っていない', await wp.locator('#genre-event .sample-video').evaluate((v) => v.muted === true));
    /* 02 サービス紹介と 04 広告CM のサンプル（2026-09-17 追加）。
       どちらも架空の題材で、クライアント実績には見せない書き方になっていること */
    check('サービス紹介のカードにサンプルがある',
        (await wp.locator('#genre-service .sample-video').count()) === 1);
    check('サービス紹介のサンプルは架空の題材だと書いてある',
        /架空の業務ソフト/.test(await wp.locator('#genre-service').innerText()));
    check('広告CMのカードにサンプルがある',
        (await wp.locator('#genre-ad .sample-video').count()) === 1);
    check('広告CMのサンプルは架空の題材だと書いてある',
        /架空の冷凍餃子/.test(await wp.locator('#genre-ad').innerText()));
    check('追加した2本も自前で配信している',
        /assets\/works\/service-15s\.mp4/.test(worksSrc) && /assets\/works\/cm-15s-taste\.mp4/.test(worksSrc));
    check('追加した2本にもポスター画像がある',
        /poster="assets\/works\/service-15s\.jpg"/.test(worksSrc)
        && /poster="assets\/works\/cm-15s-taste\.jpg"/.test(worksSrc));
    /* 05 SNSショートと 07 社内向けのサンプル（2026-09-17 追加）。
       05 は最初から縦型で組んでいるので、16:9 のまま出していないことも見る */
    check('SNSショートのカードにサンプルがある',
        (await wp.locator('#genre-sns .sample-video').count()) === 1);
    check('SNSショートのサンプルは架空の題材だと書いてある',
        /架空のコインランドリー/.test(await wp.locator('#genre-sns').innerText()));
    check('SNSショートのサンプルは縦型で表示している',
        (await wp.locator('#genre-sns .sample-video.is-vertical').count()) === 1
        && await wp.locator('#genre-sns .sample-video').evaluate(
            (v) => v.clientHeight > v.clientWidth));
    check('社内向けのカードにサンプルがある',
        (await wp.locator('#genre-internal .sample-video').count()) === 1);
    check('社内向けのサンプルは架空の題材だと書いてある',
        /架空の倉庫/.test(await wp.locator('#genre-internal').innerText()));
    check('さらに追加した2本も自前で配信している',
        /assets\/works\/sns-15s-vertical\.mp4/.test(worksSrc)
        && /assets\/works\/internal-15s\.mp4/.test(worksSrc));
    check('さらに追加した2本にもポスター画像がある',
        /poster="assets\/works\/sns-15s-vertical\.jpg"/.test(worksSrc)
        && /poster="assets\/works\/internal-15s\.jpg"/.test(worksSrc));
    /* 03 採用の3分版（2026-09-17 追加）。他のサンプルが15秒〜60秒なので、
       尺が違うことが分かる書き方になっていること */
    check('採用のカードにサンプルがある',
        (await wp.locator('#genre-recruit .sample-video').count()) === 1);
    check('採用のサンプルは架空の題材だと書いてある',
        /架空の製造業/.test(await wp.locator('#genre-recruit').innerText()));
    check('採用のサンプルは3分だと書いてある',
        /サンプル（3分）/.test(await wp.locator('#genre-recruit').innerText()));
    check('採用のサンプルも自前で配信している',
        /assets\/works\/recruit-3min\.mp4/.test(worksSrc));
    check('採用のサンプルにもポスター画像がある',
        /poster="assets\/works\/recruit-3min\.jpg"/.test(worksSrc));
    /* サンプルは「見せられないものは売らない」の裏づけなので、欠けたら落とす。
       9/19〜9/21 はミュージックビデオ（現09）だけクレジット残が足りず例外にしていたが、
       9/22 に30秒版を入れたので例外は無くなった。空のカードを増やさないため、
       ここは「1枚も欠けていない」で固定する */
    const noSample = await page.locator('.genre:not(:has(.sample-video))').evaluateAll(
        (els) => els.map((e) => e.id));
    check('サンプルの無いジャンルが1枚も無い', noSample.length === 0, noSample.join(','));
    check('全ジャンルにサンプルが入っている',
        (await page.locator('.genre .sample-video').count())
        === (await page.locator('.genre').count()));
    /* MVだけ料金計算機に乗せていない。尺が3〜4分になると相場と2倍以上離れるうえ、
       実工数をまだ測っていないため。カードにその扱いを書いていないと、
       料金表に無いことが「出せない」に見える */
    check('ミュージックビデオのカードに料金の扱いが書いてある',
        /料金表ではなく個別にお見積り/.test(await wp.locator('#genre-mv').innerText()),
        await wp.locator('#genre-mv').innerText());
    check('ミュージックビデオのサンプルは30秒だと書いてある',
        /サンプル（30秒）/.test(await wp.locator('#genre-mv').innerText()));
    check('ミュージックビデオのサンプルも自前で配信している',
        /assets\/works\/mv-30s-dance\.mp4/.test(worksSrc));
    check('ミュージックビデオのサンプルにもポスター画像がある',
        /poster="assets\/works\/mv-30s-dance\.jpg"/.test(worksSrc));
    /* 曲は鈴木さん自身のもの。権利の出所を書いていないと、
       既存曲を無断で使ったように見える */
    check('ミュージックビデオの曲の出所を書いている',
        /自作のオリジナル曲/.test(await wp.locator('#genre-mv').innerText()));
    /* 09 アニメーション・図解（9/19 追加）。生成AIを使っていない唯一のサンプル。
       文字が主役の題材はAIが画面内の文字を描けないので、プログラム描画だと
       明記してあること（これが売り文句であり、嘘をつかないための断りでもある） */
    {
        const an = await wp.locator('#genre-animation').innerText();
        check('アニメーションのカードにサンプルがある',
            await wp.locator('#genre-animation .sample-video').count() === 1);
        check('プログラム描画だと明記している', /すべてプログラムで描いています/.test(an), an.slice(0, 60));
        check('架空の題材だと断っている', /架空の健康保険組合/.test(an));
        check('尺違いに触れている', /尺違い/.test(an));
    }
    /* フッターのジャンル一覧は全ページ静的に書いてある（2026-09-23 に
       カードからの自動生成をやめた。カードが works.html へ移ったため）。
       ズレると案内が食い違うので、works.html の見出しと突き合わせる */
    {
        const cards = await (await open(browser, { page: 'works.html' }))
            .locator('#genres .genre h3').allInnerTexts();
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
        /* カードは 2026-09-23 に works.html へ移した */
        const wide = await open(browser, { width: 1280, page: 'works.html' });
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
        /* 1列に積む作りのときは「取り残し」という概念が無いので、
           2枚以上並ぶ行があるときだけ見る */
        check('最後の行に1枚だけ取り残されていない',
            rows.length === 0 || !rows.some((r) => r.n >= 2)
            || rows[rows.length - 1].n >= 2, JSON.stringify(rows));
        await wide.close();
    }

    check('ミュージックビデオのカードに金額を書いていない',
        !/¥[\d,]+/.test(await wp.locator('#genre-mv').innerText()));
    check('サンプルは「01 会社紹介」のカードの中にある',
        (await wp.locator('#genre-company .sample-video').count()) === 1
        && (await page.locator('#works .sample-video').count()) === 0);
    check('サンプルは自前で配信している（YouTube 埋め込みではない）',
        /assets\/works\/company-60s-telop\.mp4/.test(worksSrc) && !/youtube\.com\/embed/.test(idx));
    check('ポスター画像を指定している（読み込み前に真っ黒にしない）',
        /poster="assets\/works\/company-60s\.jpg"/.test(worksSrc));
    check('サンプルだと分かる見出しになっている', /サンプル（60秒）/.test(works));
    /* 段の差（松はナレーション込み・梅竹は¥30,000で追加）を納品物そのもので確かめられる。
       同じ映像で音だけ差し替える。ナレーションは最終版（2026-09-17 差し替え） */
    check('ナレーションあり／なしを切り替えられる',
        (await wp.locator('.sample-sw').count()) === 2);
    /* この音声は合成音声。人が読んだものと誤解されると、
       人物ナレーション（1名 ¥70,000〜）の見積りがずれる */
    check('サンプルの音声がAIだとボタンに書いてある',
        /AIナレーションあり/.test(await wp.locator('.sample-switch').innerText()));
    check('サンプルの音声がAIだと注釈にも書いてある',
        /このナレーションはAI音声です/.test(await wp.locator('#genre-company').innerText()));
    check('初期表示はテロップ版', /company-60s-telop\.mp4"/.test(worksSrc));
    check('切り替えで実際に音源が変わる', await (async () => {
        const v = wp.locator('#sample-video');
        const before = await v.getAttribute('src');
        await wp.locator('.sample-sw', { hasText: 'ナレーションあり' }).click();
        await wp.waitForTimeout(400);
        const after = await v.evaluate((e) => e.getAttribute('src'));
        await wp.locator('.sample-sw', { hasText: 'ナレーションなし' }).click();
        await wp.waitForTimeout(200);
        return before !== after && /narration/.test(after);
    })());
    check('差し替え前の古いナレーション版を残していない', !/company-60s\.mp4/.test(worksSrc));
    /* 人物ナレーションの額は、実績の注釈・FAQ・計算機の3か所に出る。
       どれかだけ直すとここが落ちる */
    check('人物ナレーションの値段が実績でも料金表と同じ', /1名 ¥70,000〜/.test(works));

    /* ---- ジャンルごとの計算機（2026-09-24） ----
       トップの「つくれる動画」から works.html へ飛ぶと、サンプルは見られるのに
       いくらかが分からないまま帰る形だった。サンプルを見たその場で出せるように、
       ジャンルごとに計算機を置いた。尺はそのサンプルの実尺で始める。
       ミュージックビデオは料金表の対象外なので置かない */
    {
        const SEC = { 'genre-company': 60, 'genre-service': 15, 'genre-recruit': 180,
            'genre-ad': 15, 'genre-sns': 15, 'genre-event': 15,
            'genre-internal': 15, 'genre-animation': 60 };
        const got = await wp.evaluate(() => [...document.querySelectorAll('.calc')].map((c) => ({
            where: c.dataset.calcWhere,
            len: Number(c.dataset.calcLen),
            total: Number((c.querySelector('[data-c="total"]')?.textContent || '').replace(/[^\d]/g, '')),
            /* ラジオの name が台ごとに違うこと。同じだと別の台の選択が外れる */
            names: [...new Set([...c.querySelectorAll('input[type="radio"]')].map((i) => i.name))],
            inArticle: c.closest('article.genre')?.id || null,
        })));
        check('ジャンルの計算機が8台ある', got.length === 8, String(got.length));
        check('ミュージックビデオには置いていない',
            !got.some((g) => g.where === 'genre-mv'));
        for (const g of got) {
            check(`${g.where} の計算機がその記事の中にある`, g.inArticle === g.where, String(g.inArticle));
            check(`${g.where} がサンプルの実尺で始まる`, g.len === SEC[g.where], `${g.len}/${SEC[g.where]}`);
            /* 初期は梅・1本・AIナレーション。表と同じ 基本料金＋秒単価×尺 */
            check(`${g.where} の初期の額がモデルと合っている`,
                g.total === PRICE.base + TIERS[0].perSec * g.len, String(g.total));
            check(`${g.where} のラジオが他の台と混ざらない`,
                g.names.length === 2 && g.names.every((n) => n.endsWith(`-${g.where.replace('genre-', '')}`)),
                g.names.join());
        }
        /* 1台を変えても、ほかの台が動かないこと */
        const before = await wp.evaluate(() =>
            document.querySelectorAll('.calc')[1].querySelector('[data-c="total"]').textContent);
        await wp.evaluate(() => {
            const c = document.querySelectorAll('.calc')[0];
            const r = [...c.querySelectorAll('[data-c="tier"] input')].find((i) => i.dataset.tier === 'matsu');
            r.checked = true; r.dispatchEvent(new Event('change', { bubbles: true }));
        });
        await wp.waitForTimeout(250);
        const after = await wp.evaluate(() => [...document.querySelectorAll('.calc')]
            .slice(0, 2).map((c) => c.querySelector('[data-c="total"]').textContent));
        check('1台を変えてもほかの台は動かない', after[1] === before, `${before} → ${after[1]}`);
        check('変えた台だけが動く',
            after[0] === `¥${(PRICE.base + TIERS[2].perSec * 60).toLocaleString('ja-JP')}`, after[0]);
        /* どの計算機で触ったのかがファネルに残ること */
        const ev = await wp.evaluate(() => window.soFunnel.raw()
            .filter((r) => r.name === 'calc_use').map((r) => r.where));
        check('ファネルにどの計算機かが残る', ev.includes('genre-company'), ev.join());
    }

    /* トップの料金表が料金ページと同じ段を出していること。
       9/24 まで 30秒・60秒・3分 の3行しか出しておらず、15秒（SNS・展示会）と
       90秒（会社紹介でいちばん多い尺）が抜けていた */
    {
        const rowsOf = (html) => [...html.matchAll(
            /<tr><th scope="row">(15秒|30秒|60秒|90秒|3分)<\/th>((?:<td>[^<]*<\/td>){3})<\/tr>/g)]
            .map((m) => [m[1], [...m[2].matchAll(/<td>([^<]*)<\/td>/g)].map((x) => x[1])]);
        const idxRows = rowsOf(idx);
        const priRows = rowsOf(pricingHtml);
        check('トップの料金表が5段ある',
            idxRows.length === 5, idxRows.map((r) => r[0]).join());
        check('トップと料金ページの表が一致している',
            JSON.stringify(idxRows) === JSON.stringify(priRows.slice(0, 5)),
            `${idxRows.map((r) => r[0]).join()} / ${priRows.map((r) => r[0]).join()}`);
        const SECS = { '15秒': 15, '30秒': 30, '60秒': 60, '90秒': 90, '3分': 180 };
        const y = (n) => `¥${n.toLocaleString('ja-JP')}`;
        /* 9/24：見出しが「ナレーションなし」だったが、表の額は
           基本料金＋秒単価×尺そのもの。梅・竹はAIナレーション込み、
           松は人物1名ぶん込みの額で、計算機で「なし」を選ぶと
           松60秒で ¥489,000 → ¥439,000 と5万ずれていた。
           同じ条件で違う額を出す状態を、3ページとも作らない */
        /* 尺ごとの料金表を載せているページは全部見る。1ページだけ古い言い方が
           残ると、そのページから来た人にだけ違う額を伝えることになる */
        const WITH_TABLE = ['index.html', 'pricing.html', 'company-video.html', 'recruit-video.html'];
        for (const name of WITH_TABLE) {
            const html = readFileSync(`${ROOT}/${name}`, 'utf8');
            check(`${name} の料金表が「ナレーションなし」と名乗っていない`,
                !/ナレーションなし）<\/th>/.test(html) && !/料金（1本・ナレーションなし）/.test(html));
            check(`${name} にナレーション込みだと書いてある`,
                /この表はナレーション込みの額です/.test(html)
                && /1本につき ¥25,000 を引きます/.test(html));
        }
        /* 引く額はモデルと同じであること。ここを手で打つとズレる */
        check('引く額がモデルと合っている',
            idx.includes(`¥${PRICE.noNarration.toLocaleString('ja-JP')} を引きます`)
            && PRICE.noNarration === PRICE.matsuToAi,
            `${PRICE.noNarration}/${PRICE.matsuToAi}`);

        check('トップの料金表の金額がモデルと合っている',
            idxRows.every(([lab, cells]) => TIERS.every((t, i) =>
                cells[i] === y(PRICE.base + t.perSec * SECS[lab]))),
            JSON.stringify(idxRows));
    }
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
    /1名 ¥70,000〜/.test(idx) && /narrationHuman: 70000/.test(calcSrc));
/* AIを有料に戻すときは、ここと計算機と文言を必ず一緒に直す */
check('AIナレーションが計算機でも ¥0 になっている', /narrationAi: 0/.test(calcSrc));
/* AIを込みにした代わりに、使わないときは引く。額は3か所で揃っていること */
check('ナレーションなしの差し引きが計算機と文言で同じ',
    /noNarration: 25000/.test(calcSrc) && /−¥25,000/.test(pricingHtml)
    && /¥25,000 を差し引き/.test(idx));

const org = ld.find(d => d['@graph'])?.['@graph']?.find(x => x['@type'] === 'Organization') || {};
check('構造化データに代表者', org.founder?.name === '鈴木 宏平');
check('構造化データの所在地は市区町村まで',
    org.address?.addressRegion === '愛知県' && org.address?.addressLocality === '名古屋市' && !org.address?.streetAddress);
check('未確定の情報を入れていない', !/foundingDate|postalCode|streetAddress/.test(JSON.stringify(ld)));
check('電話番号を載せていない', !org.telephone && !/090-2968-9616|tel:/.test(idx + about + privacy));
/* 9/19 に HP から YouTube・Instagram への導線を外した（アカウントは残す）。
   sameAs・フッター・会社概要・実績欄の読み込みまで含めて、外部チャンネルへの
   参照が3ページのどこにも無いことを見る。復活させるときはこの検査ごと戻す */
check('YouTube・Instagram への導線が無い',
    !/youtube\.com|youtube-nocookie|instagram\.com|i\.ytimg\.com/i.test(idx + about + privacy),
    ((idx + about + privacy).match(/.{0,30}(youtube|instagram|ytimg)[^"'<]{0,30}/i) || [''])[0]);
check('sameAs を出していない', !org.sameAs);
/* 9/20 に「制作サンプル」欄を Before / After に入れ替えた。
   ジャンル欄と中身が重複していたため。写真1枚と、そこから作った動画を並べる */
{
    const ba = await page.locator('#works').innerText();
    check('写真1枚から動画までを並べている',
        (await page.locator('#works .ba-item').count()) === 2);
    check('左は商品写真', (await page.locator('#works .ba-item img.ba-media').count()) === 1);
    check('右は動画', (await page.locator('#works .ba-item video.ba-media').count()) === 1);
    check('「これが」「こうなりました」の並びになっている',
        /これが/.test(ba) && /こうなりました/.test(ba));
    check('商品も人も架空だと書いてある', /架空/.test(ba) && /実在しません/.test(ba));
    check('商品カットは写真そのままだと書いてある',
        /左の写真をそのまま使っています/.test(ba));
    check('ラベルを刷り直せると書いてある', /刷り直すだけ/.test(ba));
    check('体験談や効能を言わせていないと書いてある',
        /体験談や効能は言わせていません/.test(ba));
    check('動画を自前で配信している',
        /assets\/works\/ugc-mamoriha-talk\.mp4/.test(idx) && !/youtube\.com\/embed/.test(idx));
    check('ポスター画像を指定している',
        /poster="assets\/works\/ugc-mamoriha-talk\.jpg"/.test(idx));
    check('商品写真に代替テキストがある',
        ((await page.locator('#works .ba-item img.ba-media').getAttribute('alt')) || '').length > 10);
    check('videos.json をどのページも読んでいない', !/videos\.json/.test(idx + about + privacy));
}
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
const why = await (await open(browser, { page: 'pricing.html' })).locator('.calc-why').innerText();
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

/* ---- 色のトークンが4か所でズレていないか（2026-09-25） ----
   assets/site.css と、社内用3ページの中に書いた :root が別々に存在する。
   地の色を薄い緑に変えたとき、片方だけ直すと同じ「社内用」の紙なのに
   色が違って見える。まとめて動かすために突き合わせる */
{
    const css = readFileSync(`${ROOT}/assets/site.css`, 'utf8');
    const tok = (src, name) => (src.match(new RegExp(`--${name}:\\s*([^;]+);`)) || [])[1]?.trim();
    const WANT = ['bg', 'bg-alt', 'card', 'ink', 'ink-dim', 'ink-2', 'on-ink', 'accent', 'accent-ink'];
    const base = Object.fromEntries(WANT.map((k) => [k, tok(css, k)]));
    check('site.css に色のトークンが揃っている',
        WANT.every((k) => base[k]), JSON.stringify(base));
    for (const f of ['roadmap.html', 'record.html', 'funnel.html']) {
        const h = readFileSync(`${ROOT}/${f}`, 'utf8');
        const root = (h.match(/:root\s*\{([\s\S]*?)\}/) || [])[1] || '';
        const diff = WANT.filter((k) => {
            const v = tok(root, k);
            /* そのページが持っていないトークンは見ない（--accent-soft など） */
            return v !== undefined && v.replace(/#fff$/, '#ffffff') !== base[k];
        });
        check(`${f} の色が site.css と揃っている`, diff.length === 0,
            diff.map((k) => `${k}: ${tok(root, k)} ≠ ${base[k]}`).join(' / '));
    }

    /* ---- 濃色であることの歯止め（2026-09-25） ----
       白地に戻すような差し戻しを、数字で拾えるようにしておく。
       ここが落ちたら「色を変えた」ではなく「片方だけ戻った」を疑う */
    const lum = (hex) => {
        const h = hex.replace('#', '');
        const v = [0, 2, 4].map((i) => parseInt(h.slice(i, i + 2), 16) / 255)
            .map((c) => (c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4));
        return 0.2126 * v[0] + 0.7152 * v[1] + 0.0722 * v[2];
    };
    check('地が濃い', lum(base.bg) < 0.05, `${base.bg} → ${lum(base.bg).toFixed(3)}`);
    check('文字が明るい', lum(base.ink) > 0.8, `${base.ink}`);
    check('カードは地より明るい（沈ませない）', lum(base.card) > lum(base.bg),
        `${base.card} / ${base.bg}`);
    check('--on-ink は地と同じ濃さ（--ink を敷いた上の文字）',
        lum(base['on-ink']) < 0.05, base['on-ink']);
    /* 濃い深緑は濃地の上では読めない。明るいほうが入っていること */
    check('ブランド色は明るいほうを使っている', lum(base.accent) > 0.3, base.accent);

    /* select・スクロールバー・動画の操作部をブラウザ既定の白で描かせない。
       これが無いと計算機の select だけが白く浮く（2026-09-25 に実際に出た） */
    check('site.css が color-scheme: dark を宣言している', /color-scheme:\s*dark/.test(css));
    for (const f of ['roadmap.html', 'record.html', 'funnel.html']) {
        const h = readFileSync(`${ROOT}/${f}`, 'utf8');
        check(`${f} が color-scheme: dark を宣言している`, /color-scheme:\s*dark/.test(h));
    }

    /* カードの地を直書きの白に戻さない。白のままでいいのは
       「濃い帯の上の主ボタン」と「ヒーローに重なったナビの CTA」の2つだけ */
    const whites = (css.replace(/\/\*[\s\S]*?\*\//g, '').match(/background:\s*#fff\b/g) || []).length;
    check('直書きの白い地は2か所だけ', whites === 2, `${whites} か所`);

    /* --ink を背景に敷いた上に白い文字を置くと、白地に白になる */
    const onInkWhite = /background:\s*var\(--ink\);\s*color:\s*#fff/.test(css);
    check('--ink の上に白い文字を置いていない', !onInkWhite);

    /* スマホのブラウザが上下に敷く色。地と違うと、スクロールの上下端に
       別の色の帯が出て「読み込みに失敗した」ように見える */
    const PUB = ['index.html', 'pricing.html', 'works.html', 'about.html', 'privacy.html', 'copyright.html',
        'company-video.html', 'recruit-video.html', 'service-video.html', 'ad-video.html',
        'sns-video.html', 'exhibition-video.html', 'internal-video.html',
        'animation-video.html', 'music-video.html'];
    for (const f of PUB) {
        const h = readFileSync(`${ROOT}/${f}`, 'utf8');
        const tc = (h.match(/name="theme-color" content="([^"]*)"/) || [])[1];
        check(`${f} の theme-color が地と揃っている`, tc === base.bg, `${tc} ≠ ${base.bg}`);
        /* 黒いマークは濃地の上では消える。白いほうを読むこと */
        check(`${f} が明るいロゴマークを読んでいる`,
            /assets\/logo-mark-light\.svg/.test(h) && !/assets\/logo-mark\.svg/.test(h));
    }
}

/* ---- 「サンプル」と書いてあるリンクは、サンプルのページへ行く（2026-09-25） ----
   ヘッダーの「サンプル」が index.html#works（＝トップの Before/After の節）を
   指していた。本文では「制作サンプルのページ」として works.html へ案内しているので、
   同じ言葉で別の場所へ飛んでいた。言葉と行き先を結び直したので、戻ったら落とす。
   #works は「写真1枚から」という別の節。呼び分けること */
{
    const PUB = ['index.html', 'pricing.html', 'works.html', 'about.html', 'privacy.html', 'copyright.html',
        'company-video.html', 'recruit-video.html', 'service-video.html', 'ad-video.html',
        'sns-video.html', 'exhibition-video.html', 'internal-video.html',
        'animation-video.html', 'music-video.html'];
    for (const f of PUB) {
        const h = readFileSync(`${ROOT}/${f}`, 'utf8');
        const bad = [...h.matchAll(/<a[^>]*href="([^"]*)"[^>]*>([^<]*)<\/a>/g)]
            .filter(([, , text]) => text.includes('サンプル') || text.includes('つくれる動画'))
            /* works.html 本体か、その中の錨。works.html 自身では #genres */
            /* index と works は自分の中に #genres を持っているので、そこへの錨は正しい */
            .filter(([, href]) => !/^works\.html(#|$)/.test(href)
                                  && !(href === '#genres'
                                       && /id="genres"/.test(readFileSync(`${ROOT}/${f}`, 'utf8'))))
            .map(([, href, text]) => `${text} → ${href}`);
        check(`${f}「サンプル」「つくれる動画」と書いたリンクは works.html へ行く`, bad.length === 0,
            bad.join(' / '));
    }

    /* ヘッダーの「料金」も同じ。料金の本拠地は pricing.html で、
       トップの #plans は要約の節。下層から押して要約へ戻されると、
       押したのに何も進んでいないように見える */
    for (const f of PUB.filter((x) => x !== 'index.html')) {
        const h = readFileSync(`${ROOT}/${f}`, 'utf8');
        const nav = (h.match(/<div class="nav-main">([\s\S]*?)<\/div>/) || [])[1] || '';
        const want = f === 'pricing.html' ? '#plans' : 'pricing.html';
        const got = (nav.match(/<a[^>]*href="([^"]*)"[^>]*>料金<\/a>/) || [])[1];
        check(`${f} のヘッダーの「料金」が ${want} を指す`, got === want, String(got));
        const wantS = f === 'works.html' ? '#genres' : 'works.html';
        const gotS = (nav.match(/<a[^>]*href="([^"]*)"[^>]*>つくれる動画<\/a>/) || [])[1];
        check(`${f} のヘッダーの「つくれる動画」が ${wantS} を指す`, gotS === wantS, String(gotS));
        /* 呼び名は 2026-09-25 に「サンプル」→「作例」→「つくれる動画」。
           works.html の見出し「つくれる動画と、そのサンプル。」と揃えた。
           「実績」「事例」は使わない——works.html の9本は全部 so-creative が
           自社でつくったもので、受注した仕事ではないため */
        check(`${f} のヘッダーが「実績」「事例」を名乗っていない`,
            !/>(実績|事例)</.test(nav), nav.replace(/\s+/g, ' ').trim());
        /* How to はトップの Before/After の節（まもりば）。つくれる動画とは別物なので、
           同じ語が2つの行き先を指さないように固定する */
        const gotH = (nav.match(/<a[^>]*href="([^"]*)"[^>]*>How to<\/a>/) || [])[1];
        check(`${f} のヘッダーの「How to」が index.html#works を指す`,
            gotH === 'index.html#works', String(gotH));
    }

    /* フッターのサイトマップが同じ URL を2つの名前で並べていた
       （works.html が「Genres」と「Works — 制作サンプル」の2行）。
       そのぶん「写真1枚から」への道が、どのページからも消えていた */
    for (const f of PUB) {
        const h = readFileSync(`${ROOT}/${f}`, 'utf8');
        const map = h.slice(h.indexOf('f-site-h'));
        const hrefs = [...map.slice(0, map.indexOf('</nav>')).matchAll(/<a href="([^"]*)"/g)]
            .map((m) => m[1]);
        const dup = hrefs.filter((x, i) => hrefs.indexOf(x) !== i);
        check(`${f} のサイトマップに同じ行き先が2回出てこない`, dup.length === 0, dup.join(' / '));
    }
}

/* ---- 検索に出す／出さないの足並み（2026-09-24） ----
   sitemap.xml は公開5ページを載せているのに、全ページが noindex だった。
   いまは公開前なので意図どおりだが、切り替えのときに片方だけ直すと
   「sitemap では出しておいて中身は拒否する」食い違った状態が残る。
   noindex の有無と、robots.txt が sitemap を出しているかを、必ず一緒に動かす */
{
    /* 2026-09-24：ジャンルごとのページを7つ足した（用途別で検索の受け皿にする）。
       ここに並べたページは、noindex の付け外しも計測も足並みをそろえる */
    const PUBLIC = ['index.html', 'pricing.html', 'works.html', 'about.html', 'privacy.html', 'copyright.html',
        'company-video.html', 'recruit-video.html', 'service-video.html', 'ad-video.html',
        'sns-video.html', 'exhibition-video.html', 'internal-video.html',
        'animation-video.html', 'music-video.html'];
    const INTERNAL = ['funnel.html', 'roadmap.html', 'record.html'];
    const robotsOf = async (f) => {
        const h = await (await page.request.get(`${BASE}/${f}`)).text();
        return (h.match(/name="robots" content="([^"]*)"/) || [])[1] ?? '';
    };
    const pub = [];
    for (const f of PUBLIC) pub.push([f, await robotsOf(f)]);
    const noindexed = pub.filter(([, v]) => /noindex/.test(v)).map(([f]) => f);
    check('公開ページの noindex が全部そろっている',
        noindexed.length === 0 || noindexed.length === PUBLIC.length,
        pub.map(([f, v]) => `${f}:${v || '-'}`).join(' '));

    /* ---- 開業日の切り替え手順に書いてある枚数（2026-09-26） ----
       ロードマップの「サイトを検索に出す」に「公開◯ページの noindex を外す」と
       書いてある。ページを足したときにここを直し忘れると、当日その枚数だけ外して
       残りが noindex のまま取り残される。実際 6 のまま 15 まで増えていた。
       文章のほうを正とせず、PUBLIC の数と突き合わせる */
    {
        const rm = readFileSync(`${ROOT}/roadmap.html`, 'utf8');
        /* 太字の位置が動いても読めるよう、タグを落としてから数える */
        const n = Number((rm.replace(/<[^>]+>/g, '').match(/公開(\d+)ページの noindex/) || [])[1]);
        check('ロードマップの切り替え枚数が公開ページ数と合っている',
            n === PUBLIC.length, `ロードマップ ${n} / 実際 ${PUBLIC.length}`);
    }

    for (const f of INTERNAL) {
        check(`${f} は社内用なので必ず noindex`, /noindex/.test(await robotsOf(f)));
    }

    const sm = await (await page.request.get(`${BASE}/sitemap.xml`)).text();
    const locs = [...sm.matchAll(/<loc>([^<]+)<\/loc>/g)].map((m) => m[1]);
    const advertised = /^\s*Sitemap:/m.test(rb);
    /* 公開前は sitemap を robots.txt から出さない。出すのは noindex を外すのと同時 */
    check('noindex の間は robots.txt が sitemap を出していない',
        noindexed.length === 0 ? advertised : !advertised,
        `noindex:${noindexed.length} sitemap行:${advertised}`);
    /* sitemap が載せてよいのは公開ページだけ。社内用が混ざると外から辿られる */
    check('sitemap に社内用のページが入っていない',
        !INTERNAL.some((f) => locs.some((u) => u.endsWith(`/${f}`))), locs.join(' '));
    /* privacy.html は検索から直接来る種類のページではないので sitemap に入れない。
       それ以外の公開ページは全部載っていること（ジャンルのページを足したら自動で増える） */
    const SITEMAP_OUT = ['privacy.html'];
    const want = PUBLIC.filter((f) => !SITEMAP_OUT.includes(f) && f !== 'index.html');
    check('sitemap の中身が公開ページの並びと合っている',
        locs.length === want.length + 1
        && locs.some((u) => u.endsWith('/so-creative/'))
        && want.every((f) => locs.some((u) => u.endsWith(`/${f}`))),
        `${locs.length}件 / ${want.length + 1}件`);
    /* ---- 料金を出すページは、表と計算機の両方を載せる（2026-09-24） ----
       表だけだと自分の条件の額が分からず、計算機だけだと相場がつかめない。
       片方しか無いページがあると、そのページから来た人だけ情報が欠ける */
    {
        const BOTH = ['index.html', 'pricing.html', 'company-video.html', 'recruit-video.html',
            'service-video.html', 'ad-video.html', 'sns-video.html',
            'exhibition-video.html', 'internal-video.html', 'animation-video.html'];
        for (const f of BOTH) {
            const h = readFileSync(`${ROOT}/${f}`, 'utf8');
            check(`${f} に料金表がある`,
                /<tr><th scope="row">(15秒|30秒)<\/th>/.test(h));
            check(`${f} に計算機がある`,
                /class="calc[ "]/.test(h) && /<script[^>]+src="assets\/pricing\.js"/.test(h));
            /* 2026-09-25：生成側が骨組みと二重に足していて、6ページで pricing.js を
               2回読んでいた。計算機が2回組み立てられ、段と本数の選択肢が二重に生えた */
            check(`${f} が pricing.js を二重に読んでいない`,
                (h.match(/<script[^>]+src="assets\/pricing\.js"/g) || []).length === 1);
            check(`${f} が funnel.js を二重に読んでいない`,
                (h.match(/<script[^>]+src="assets\/funnel\.js"/g) || []).length === 1);
        }
        /* ミュージックビデオは料金表の対象外。どちらも置かない */
        const mv = readFileSync(`${ROOT}/music-video.html`, 'utf8');
        check('music-video.html はどちらも置かない',
            !/<tr><th scope="row">(15秒|30秒)<\/th>/.test(mv) && !/class="calc[ "]/.test(mv));

        /* works.html は8ジャンルとも表と計算機が並ぶ。額はモデルから出す */
        const w = readFileSync(`${ROOT}/works.html`, 'utf8');
        const arts = [...w.matchAll(
            /<article class="genre" id="(genre-[a-z]+)">([\s\S]*?)<\/article>/g)];
        const S = { '15秒': 15, '30秒': 30, '60秒': 60, '90秒': 90, '3分': 180 };
        for (const [, gid, body] of arts) {
            if (gid === 'genre-mv') {
                check('works の mv は表も計算機も置かない',
                    !/genre-price-table/.test(body) && !/class="calc"/.test(body));
                continue;
            }
            check(`works の ${gid} に表と計算機が並んでいる`,
                /genre-price-table/.test(body) && /class="calc"/.test(body));
            const rows = [...body.matchAll(
                /<tr><th scope="row">(15秒|30秒|60秒|90秒|3分)<\/th>((?:<td>[^<]*<\/td>){3})<\/tr>/g)];
            check(`works の ${gid} の表がモデルと合っている`,
                rows.length >= 3 && rows.every((m) => {
                    const cells = [...m[2].matchAll(/<td>([^<]*)<\/td>/g)].map((x) => x[1]);
                    return TIERS.every((t, i) => cells[i]
                        === `¥${(PRICE.base + t.perSec * S[m[1]]).toLocaleString('ja-JP')}`);
                }), `${rows.length}段`);
            check(`works の ${gid} がナレーション込みだと書いている`,
                /梅・竹はAIナレーション、松は人に読んでもらうぶん1名が含まれた額です/.test(body));
        }
    }

    /* ---- 用途別のページ（2026-09-24 に7つ足した） ----
       9ジャンルのうち専用ページがあるのは会社紹介と採用だけで、
       残り7つは works.html のアンカーだった。地域×用途の検索で
       当たるページが無かったので、1用途1ページにした。
       つくるのは scripts/make-genre-pages.py。手で7ページを直さない */
    {
        const GENRE_PAGES = [
            ['service-video.html', 'genre-service', false],
            ['ad-video.html', 'genre-ad', false],
            ['sns-video.html', 'genre-sns', false],
            ['exhibition-video.html', 'genre-event', false],
            ['internal-video.html', 'genre-internal', false],
            ['animation-video.html', 'genre-animation', false],
            /* ミュージックビデオは料金表の対象外なので、表も計算機も置かない */
            ['music-video.html', 'genre-mv', true],
        ];
        const worksSrcNow = readFileSync(`${ROOT}/works.html`, 'utf8');
        for (const [file, anchor, noPrice] of GENRE_PAGES) {
            const h = readFileSync(`${ROOT}/${file}`, 'utf8');
            check(`${file} に h1 が1つある`,
                (h.match(/<h1[^>]*>/g) || []).length === 1);
            check(`${file} の canonical が自分を指している`,
                h.includes(`<link rel="canonical" href="https://koheisuzuki0626-coder.github.io/so-creative/${file}">`));
            check(`${file} に構造化データがある`,
                /"@type": "Service"/.test(h) && /"@type": "VideoObject"/.test(h)
                && /"@type": "BreadcrumbList"/.test(h));
            check(`${file} が地域を書いている`, /名古屋/.test(h) && /愛知/.test(h));
            check(`${file} がサンプルのページへ戻れる`,
                h.includes(`href="works.html#${anchor}"`));
            check(`works.html の ${anchor} から ${file} へ行ける`,
                new RegExp(`id="${anchor}"[\\s\\S]{0,900}?href="${file}"`).test(worksSrcNow));
            check(`${file} が計測している`,
                /<script[^>]+src="assets\/funnel\.js"/.test(h));
            if (noPrice) {
                check(`${file} は料金表を置かない`,
                    !/<table class="compare">[\s\S]*?¥/.test(h.split('<h2 class="headline">料金</h2>')[1] || '')
                    && /個別にお見積り/.test(h));
                check(`${file} は計算機を置かない`, !/class="calc"/.test(h));
            } else {
                check(`${file} に計算機がある`,
                    /<div class="calc" data-calc-len="(\d+)"/.test(h)
                    && /<script[^>]+src="assets\/pricing\.js"/.test(h));
                check(`${file} の料金表がナレーション込みだと書いている`,
                    /この表はナレーション込みの額です/.test(h)
                    && !/ナレーションなし）<\/th>/.test(h));
                /* 表の額は基本料金＋秒単価×尺。手で打ち直すとここで落ちる */
                const rows = [...h.matchAll(
                    /<tr><th scope="row">(15秒|30秒|60秒|90秒|3分)<\/th>((?:<td>[^<]*<\/td>){3})<\/tr>/g)];
                const S = { '15秒': 15, '30秒': 30, '60秒': 60, '90秒': 90, '3分': 180 };
                check(`${file} の料金表がモデルと合っている`,
                    rows.length >= 3 && rows.every((m) => {
                        const cells = [...m[2].matchAll(/<td>([^<]*)<\/td>/g)].map((x) => x[1]);
                        return TIERS.every((t, i) => cells[i]
                            === `¥${(PRICE.base + t.perSec * S[m[1]]).toLocaleString('ja-JP')}`);
                    }), `${rows.length}段`);
            }
        }
        /* ---- 用途から選ぶ帯（2026-09-24） ----
           用途別のページどうしが互いに繋がっていること。1ページでも外れると、
           そこから他の用途へ行けないうえ、検索側から見ても孤立する */
        const USES = ['company-video.html', 'recruit-video.html', 'service-video.html',
            'ad-video.html', 'sns-video.html', 'exhibition-video.html',
            'internal-video.html', 'animation-video.html', 'music-video.html'];
        for (const f of USES) {
            const h = readFileSync(`${ROOT}/${f}`, 'utf8');
            const bar = (h.match(/<div class="nav-uses">([\s\S]*?)<\/div>/) || [])[1] || '';
            const hrefs = [...bar.matchAll(/href="([^"]+)"/g)].map((m) => m[1]);
            check(`${f} のヘッダーに用途の帯がある`, hrefs.length === 9, `${hrefs.length}件`);
            check(`${f} の帯が9つの用途をすべて指している`,
                USES.every((u) => hrefs.includes(u)), hrefs.join());
            /* いま見ているページに aria-current が1つだけ付いていること */
            const cur = [...bar.matchAll(/href="([^"]+)" aria-current="page"/g)].map((m) => m[1]);
            check(`${f} の帯が現在地を示している`,
                cur.length === 1 && cur[0] === f, cur.join());
            /* 折り返しの指定は帯を持つページだけ。全体に掛けると
               幅900px のトップでナビが折り返して CTA に重なる */
            check(`${f} のナビに has-uses が付いている`,
                /<nav id="nav" class="has-uses">/.test(h));
        }

        /* 手で書き足すと骨組みがズレるので、つくり手が残っていること */
        check('ジャンルのページをつくる手順が残っている',
            existsSync(`${ROOT}/scripts/make-genre-pages.py`)
            && existsSync(`${ROOT}/scripts/genre_data.py`));
    }

    /* 切り替えの手順を書いた場所が消えていないこと。消えると順番を思い出せない */
    check('公開に切り替える手順が sitemap.xml に書いてある',
        /noindex, nofollow を外す/.test(sm) && /Sitemap: の行を足す/.test(sm));
}

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
    /* 初入金までの期間は2度動いた。9/22 に着手金を外して「約1ヶ月」→「約2ヶ月」、
       9/24 にインボイスの登録を先に通すと決めて「約4ヶ月」（M+3）。
       収支の推移の表と同じ月数を指していること */
    check('未開業・クレジット残・事例0本・初入金までが出ている',
        now.join('/') === '未開業/246.84/0本/約4ヶ月', now.join('/'));
    /* 2026-09-25：お金の表を1本に畳んだとき、時期とやることを別の列に分けた。
       全角スペース決め打ちだと、セルの区切りが変わっただけで落ちる。
       見たい事実は「初入金が M+3 にある」ことなので、間の空白は問わない */
    check('初入金までがM+3と揃っている',
        /M\+3\s*初入金/.test(t) && /初受注は M\+2/.test(
            readFileSync(`${ROOT}/record.html`, 'utf8')));

    /* 2026-09-20：保険者に確認した結果、営業活動も労務にあたると分かった。
       手当（月17万・2027年12月まで）を受けている間は受注できないので、
       「収入ゼロ・生活費20〜30万・必要な貯蓄40〜60万」の表は実態と合わず外した。
       いまは実数（手当17万 − 生活費8万 − ツール代3.5万 ＝ ＋5.5万）で書く */
    check('営業ができない制約を書いている',
        /営業活動も労務にあたる/.test(t) && /2027年12月まで/.test(t));
    check('月次を実数で出している',
        /¥170,000/.test(t) && /¥80,000/.test(t) && /¥54,720/.test(t));
    check('開業後にもつ期間を出している', /約6ヶ月/.test(t));
    /* 収支の推移。開業日が未定なので M+0 からの相対で置く。
       9/21：要点だけを置いて表は record.html に分けていたが、開業の可否を決める数字なので
       月ごとの表そのものを要約版に載せた。要点も表も両方あることを見る */
    /* 9/24：インボイスの登録が通ってから声かけを始めると決めたので、
       「開業月に受注して納品、翌月入金」では成り立たなくなった。
       入金のない月が3つ続き、底は M+2 の −41.4万、手元が戻るのは M+4 */
    check('要約版に収支の推移の要点がある',
        /収支の推移/.test(t) && /入金のない月が3つ続く/.test(t));
    check('要約版に月ごとの表が載っている',
        /M\+0/.test(t) && /M\+11/.test(t) && /333\.9万/.test(t));
    check('置き直した理由が書いてある',
        /登録が通ってから声かけを始める/.test(t) && /受注も納品もできない月が先に来る/.test(t));
    check('月数が前提であって実績でないと断っている',
        /前提であって実績ではない/.test(t) && /実数で置き直すこと/.test(t));
    check('推移の前提を書いている',
        /支出 月13\.8万/.test(t) && /全額を納品後に請求/.test(t));
    /* 9/22 に着手金を外し、9/24 に登録を先に通す順番へ置き直した。
       表の数字が古いままだと判断を誤るので、底（M+2 −41.4万）と
       手元が戻る月（M+4 ＋10.5万）を見る */
    check('着手金なしの数字に直っている',
        /−13\.8万/.test(t) && !/484\.1万/.test(t));
    check('底と回復の月が新しい順番になっている',
        /−41\.4万/.test(t) && /＋10\.5万/.test(t) && !/38\.1万/.test(t));
    /* 必要な貯えが 14万 → 42万 に変わった。古い数字が残っていると開業日を誤る */
    check('開業前に残す額が置き直されている',
        /開業時点で 42万/.test(t) && !/開業時点で <b>14万<\/b>/.test(t));
    check('待つことが前進ではないと書いている', /事業の前進ではない/.test(t));
    /* 営業できない間は Higgsfield を Pro に落としている。戻し忘れると
       受注した月に90秒1本も作れない（Pro は600クレジット＝約18秒ぶん） */
    check('受注したら Max に戻すと書いている',
        /受注が決まったら、その日に Higgsfield を Max へ戻す/.test(t)
        && /約18秒ぶん/.test(t));
    check('合わなくなった前提を残していない',
        !/必要な貯蓄/.test(t) && !/底は10月末/.test(t), t.slice(0, 40));
    check('支払条件は残っている（決定事項）',
        /全額を納品後に請求/.test(t) && /納品日から30日以内/.test(t));
    check('着手金を取らないと書いている', /着手金は取らない/.test(t));

    /* 4段階は1行ずつの表に畳んだ。月商は計画（README の料金の考え方）と同じ */
    const stages = await rm.locator('table.t-wide tbody tr').count();
    check('4つの段階が表になっている', stages >= 4, String(stages));
    check('段階ごとの月商が計画と一致',
        /¥600,000/.test(t) && /¥915,000/.test(t) && /¥1,125,000/.test(t));

    /* P0 はいま動いている段階なので、要約版に残りタスクを置く */
    check('P0 の残りタスクが載っている',
        ['開業届', 'ひな形', 'プロフィール', '主治医'].every((w) => t.includes(w)));

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
    /* 2026-09-25 に P0 へ2件足した（障害年金の請求・失業保険の受給期間延長）。
       3 → 5。ここは手で書いてあるので、増やしたら必ず一緒に直す */
    check('残りは未チェックで置いてある', ckLeft === 5, String(ckLeft));

    /* このあとの宿題。いま動かせないものなので、全部未チェックで始まる。
       日付ではなく着手条件で書くと決めたので、各項目に条件が要る */
    const next = await rm.locator('.ck.next li').allInnerTexts();
    check('このあとの宿題が載っている', next.length >= 5, String(next.length));
    /* 9/24：宿題が1つ実際に終わった（送り先リスト30件）ので、
       「全部未チェック」では回らなくなった。守りたいのは
       「やっていないものを勝手にチェックしない」なので、
       チェックが付いたものには済んだ日付が入っていること、に変える */
    const doneNext = await rm.locator('.ck.next li.done').allInnerTexts();
    check('終わった宿題には済んだ日付が入っている',
        doneNext.every((x) => /\d+\/\d+/.test(x)),
        doneNext.find((x) => !/\d+\/\d+/.test(x)) || `${doneNext.length}件`);
    check('宿題がまだ残っている',
        (await rm.locator('.ck.next li:not(.done)').count()) >= 4);
    check('宿題に着手条件が書いてある',
        next.every((x) => /てから|届いたら|ときに|まで|次号|1本目/.test(x)),
        next.find((x) => !/てから|届いたら|ときに|まで|次号|1本目/.test(x)) || '');
    /* 9/23：GA4 を入れたので、自分のアクセスを除外する作業が要る。
       ただし営業を始める前にやると動作確認ができなくなるので、
       着手条件（他人のアクセスが混ざり始めてから）とセットで置く */
    check('GA4 の除外が宿題に入っている',
        /GA4 から自分のアクセスを除外する/.test(t)
        && /いまやると動作確認ができなくなる/.test(t));
    /* 9/23：退職時の書面を確認し、前職の取引先が使えないと確定した。
       いちばん近い経路が消えたので、紹介以外の経路の重みが上がっている。
       書面そのものは公開リポジトリに残さない（社名も条文も書かない）ので、
       ここでは「社名が混ざっていないこと」も見る */
    check('前職の取引先が使えないと書いてある',
        /前職の取引先は 9\/23 に使えないと確定している/.test(t));
    /* 退職合意書で、合意の存在と内容を第三者に開示しないことも約束している。
       so. としての行動制約だけを残し、条文は引用しない。
       社名そのものは、この検査に書くと検査ファイルが公開リポジトリに残るので書かない */
    check('退職時の書面を引用していない',
        !/誓約いたします|誓約致します|第１条|第4条（引き抜き/.test(idx + t));
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
        /* 9/24：インボイスは「登録しない」から「登録する」に変わった。
           決着の項目としては残るが、中身が逆になったので両方の経緯が書いてあること */
        && doneTxt.some((d) => /インボイス/.test(d) && /登録しない/.test(d)
            && /9\/24/.test(d) && /登録する/.test(d)), doneTxt.join(' | '));
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
    /* 長さの上限は外した（2026-09-23・本人の判断）。
       4000 →（9/21 入札の宿題）4200 →（9/21 収支の推移の表）4900 と上げてきて、
       足すたびに上限に当たる状態になっていた。数えるのはやめ、
       代わりに「折りたたみを置いていない」（下の検査）で読みやすさを守る。
       記録として、外した時点の長さは約4,900字。 */
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
        check(`${file} の前提が時間単価と一致`, body.includes(want), want);
        /* ¥23,000 は価格÷実測工数の結果であって、目標として決めた数字ではない。
           「目標の時間単価」と書くと、値下げの是非を時給の話にすり替えてしまう
           （実際は循環している）。言い切りの表現に戻っていないかを見る（9/21） */
        check(`${file} で時間単価を目標と書いていない`, !/目標の時間単価/.test(body),
            (body.match(/.{0,20}目標の時間単価.{0,20}/) || [''])[0]);
        /* 経緯の説明として ¥14,900 に触れるのは構わない（9/21 に追記した）。
           見るのは「前提」の行で、いまの数字として出ていないこと */
        const premise = await pg.locator('.note').innerText();
        check(`${file} に古い時間単価が残っていない`, !/14,900/.test(premise),
            (premise.match(/.{0,24}14,900.{0,24}/) || [''])[0]);
        await pg.close();
    }
}

/* ---- 時間単価の位置づけ（9/21）----
   ¥23,000 は価格÷実測工数の結果で、目標として決めた数字ではない。
   ここを取り違えると「時給を下げれば値下げできる」という循環した話になる。
   record.html と README の両方に、その旨と代わりの判断軸を残してある */
{
    const rc2 = await open(browser, { page: 'record.html' });
    const t2 = await rc2.locator('body').innerText();
    check('時間単価が結果の数字だと書いてある',
        /目標ではなく、結果の数字/.test(t2) && /割り算/.test(t2), t2.slice(0, 40));
    check('値下げの判断軸が年収と時間だと書いてある',
        /465h/.test(t2) && /713h/.test(t2));
    check('いま値下げの根拠がないと書いてある',
        /問い合わせが来ない/.test(t2) && /見積0件/.test(t2));
    await rc2.close();
    const readme2 = readFileSync(`${ROOT}/README.md`, 'utf8');
    check('README にも同じことが書いてある',
        /目標ではなく、価格 ÷ 実測工数の結果/.test(readme2)
        && /循環していて、値下げの根拠にならない/.test(readme2));
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

    /* 着手金は取らないと決めた（9/22）。ただし危ない相手には個別に前金を相談する、
       という内部ルールを持っている。受注率に効くのは「サイトに書いてあるか」で、
       回収リスクに効くのは「実際に取るか」なので、この2つは分けて持つ。
       ルールが消えると「なし」だけが残って、丸腰になったことに気づけない */
    check('前金を相談する内部ルールがある',
        /前金を相談する/.test(folded)
        && ['紹介ではない初対面', '30万を超える', '会社の実体が確認できない']
            .every((w) => folded.includes(w)), folded.length);
    check('未払いが出たら戻すと書いてある',
        /1件でも起きたら、そのとき条件を戻す/.test(folded));

    /* ロードマップの収支の表は「納品の翌月に入金」で組んである。これは
       so. の条件がそのまま通った最短の場合で、相手が大きいと相手のサイトになる。
       表だけ見て「必ずこうなる」と読まないよう、前提と上限（フリーランス法の60日）
       をここに置いている（9/22） */
    check('支払サイトは相手が決めると書いてある',
        /支払条件はこちらが決めるものではない/.test(folded));
    check('フリーランス法の60日を書いてある',
        /60日以内/.test(folded) && /起算日は.{0,4}納品日/.test(folded));
    check('60日サイトだと表が1ヶ月ずれると書いてある',
        /M\+3/.test(folded) && /約22万/.test(folded));

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
   数字（納品後の一括払い・期日・修正回数・キャンセルの按分・−¥25,000・¥70,000）は
   サイトの料金ページに揃えてある。サイトだけ直すとひな形が古い条件のまま
   お客様に出ていくので、突き合わせて見張る（9/18 作成） */
{
    const T = '成果物/_テンプレート';
    /* 9/24：見積書・契約書・請求書が _テンプレート/ と 書類ひな形/ の
       2か所にあり、中身が食い違っていた（片方は消費税を10%上乗せしていて、
       サイトの表示額より高く見積もる形になっていた）。書類ひな形/ に寄せた */
    const D = '成果物/書類ひな形';
    const mitsu = readFileSync(`${ROOT}/${D}/見積書.md`, 'utf8');
    const keiyaku = readFileSync(`${ROOT}/${D}/業務委託契約書.md`, 'utf8');
    const seikyu = readFileSync(`${ROOT}/${D}/請求書.md`, 'utf8');
    const hearing = readFileSync(`${ROOT}/${T}/ヒアリングシート.md`, 'utf8');
    const eigyo = readFileSync(`${ROOT}/${T}/営業文面.md`, 'utf8');
    const all = mitsu + keiyaku + seikyu;

    /* 料金の答え方と、詰められたときの返し方（9/23）。
       営業中はスマホで開くので record.html に移した（markdown では読めない）。
       金額と時間単価を本文に書いている以上、モデルとズレたら
       お客様の前で違う数字を言うことになるので、ここで突き合わせる。
       営業文面.md 側には移した旨のポインタだけを残し、数字は二重に持たない */
    {
        const y = (n) => `¥${n.toLocaleString('ja-JP')}`;
        const rec = readFileSync(`${ROOT}/record.html`, 'utf8');
        check('営業文面は record.html を指している',
            /record\.html/.test(eigyo) && /2か所に置かない/.test(eigyo));
        check('営業文面に数字を二重に持っていない',
            !/¥185,725/.test(eigyo) && !/23,143\/h/.test(eigyo));

        check('料金の答え方がある', /料金を聞かれたときの答え方/.test(rec));
        check('答え方の時間単価がモデルと合っている',
            TIERS.every((t) => rec.includes(`${y(Math.round(price(t, 90, 1, 'ai') / hours(t, 90, 1, 'ai')))}/h`)),
            TIERS.map((t) => Math.round(price(t, 90, 1, 'ai') / hours(t, 90, 1, 'ai'))).join());
        check('答え方の金額がモデルと合っている',
            rec.includes(y(PRICE.base)) && rec.includes(y(PRICE.noNarration))
            && rec.includes(y(PRICE.narrationHuman)));
        check('「工数だからこの値段」と言わない方針が書いてある',
            /「工数だからこの値段」とは言わない/.test(rec)
            && /価格は市場を見て決めています/.test(rec));
        check('2人目がタダなことを取り繕わない方針が書いてある',
            /段の中では同じです/.test(rec) && /取り繕って/.test(rec));

        /* 下げていい限界を実数で書いている。料金や工数を動かしたらここもズレる。
           とくに「梅は5〜6%しか下げられない」は、感覚で応じると壊れる線 */
        const limit = (id, sec) => {
            const t = TIERS.find((x) => x.id === id);
            const nar = t.narration ? 'human' : 'ai';
            return Math.round(RATE * 0.95 * hours(t, sec, 1, nar));
        };
        const cases = [['ume', 30], ['ume', 90], ['take', 90], ['matsu', 90]];
        check('詰められたときの返し方がある', /金額を詰められたときの返し方/.test(rec));
        check('下げていい限界がモデルと合っている',
            cases.every(([id, sec]) => rec.includes(y(limit(id, sec)))),
            cases.map(([i, sc]) => limit(i, sc)).join());
        check('尺を縮めたときの差額が合っている', rec.includes(y(TIERS[1].perSec * 30)));
        check('値引きではなく構成で答える方針が書いてある',
            /値引きで答えない。構成で答える/.test(rec) && /最初の3社に限って/.test(rec));
        check('引く基準が書いてある', /引くとき/.test(rec) && /当て馬/.test(rec));

        /* 入札参加資格の手順も移した。開業の週にスマホで開くもの */
        check('入札の手順が record.html にある',
            /入札に出られるようにする/.test(rec) && /新設のため決算書なし/.test(rec)
            && /令和10年3月10日/.test(rec));
        const research = readFileSync(`${ROOT}/成果物/リサーチ/2026-09-21_価格の実数.md`, 'utf8');
        check('リサーチ側は移した旨を書いている',
            /record\.html.*に移した/.test(research));
    }

    check('ひな形3点が空でない', [mitsu, keiyaku, seikyu].every(x => x.length > 500));
    /* 9/23：営業文面だけ「（税別）」のままだった。サイトは全部 税込 なので、
       メールで税別の額を伝えると見積書と食い違う。検査の対象に入れる */
    check('ひな形に税別・税抜が残っていない', !/税別|税抜/.test(all + eigyo));
    check('ひな形3点とも消費税を別途請求しない旨がある',
        [mitsu, keiyaku, seikyu].every(x => /消費税を(別途請求|別途申し受け|区分して請求)/.test(x)));
    check('支払条件がサイトと揃っている(全額を納品後・納品日から30日以内)',
        [mitsu, keiyaku].every(x => /納品後/.test(x) && /納品日から30日以内/.test(x)));
    /* 9/22 に着手金を外した。ひな形に古い条件が残っているとお客様に出ていく */
    check('ひな形に着手金の請求が残っていない',
        [mitsu, keiyaku, seikyu, hearing].every(x => !/着手金として/.test(x) && !/着手金の請求書/.test(x)));
    check('ひな形3点とも着手金を取らないと分かる',
        [mitsu, keiyaku, seikyu].every(x => /着手金(は|その他)/.test(x)));
    /* 9/24：サイトは「表示はすべて税込」「適格請求書発行事業者の登録はしておりません」
       と公開している。ひな形が小計（税別）＋消費税10%で組まれていて、
       竹60秒1本を ¥384,000 ではなく ¥422,400 で見積もる形になっていた */
    check('ひな形に消費税の上乗せが残っていない',
        [mitsu, seikyu].every(x => !/小計（税別）/.test(x) && !/消費税（10%）/.test(x)));
    check('見積書の例がサイトの式と合っている',
        mitsu.includes(`¥〔${(PRICE.base + TIERS[1].perSec * 60).toLocaleString('ja-JP')}〕（税込`),
        String(PRICE.base + TIERS[1].perSec * 60));
    /* ひな形は1か所だけ。2か所に置いて片方だけ直すと、高いほうで出てしまう */
    check('ひな形が2か所に無い',
        !existsSync(`${ROOT}/${T}/見積書.md`) && !existsSync(`${ROOT}/${T}/請求書.md`)
        && !existsSync(`${ROOT}/${T}/業務委託契約書.md`));
    check('元の置き場から書類ひな形へ案内している',
        /書類ひな形/.test(readFileSync(`${ROOT}/${T}/README.md`, 'utf8')));
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
    check('契約書に権利の帰属がある',
        /支払完了をもって/.test(keiyaku) && /制限なく使用できる/.test(keiyaku));
    check('実績掲載は相手が断れる形になっている', /掲載を望まない場合/.test(keiyaku));
    check('請求書に登録番号の欄が無い', !/登録番号 \||T\d{13}/.test(seikyu), (seikyu.match(/T\d{13}/) || [''])[0]);
    /* 番号の例(S-20261001-001)に7桁以上の数字が含まれるので、全文の数字検索ではなく
       振込先の行が空欄(＿)のままかを見る */
    /* MV・リリックビデオ用の特約（9/19 追加）。企業向けの条項では
       楽曲の権利を扱えないので、受ける前に必ず要る。
       サイトの 08 のカードは「料金表ではなく個別にお見積り」と書いてあるので、
       見積書側にも料金表の対象外であることが書かれていること */
    check('契約書に楽曲の特約がある',
        /### 第13条（楽曲を扱う場合の特約）/.test(keiyaku)
        && /乙は本楽曲の権利処理を行わない/.test(keiyaku));
    /* 9/24：末尾に置いたので、消しても前の条番号が動かない */
    check('楽曲の特約がMV以外では外せると書いてある',
        /この条を丸ごと削除する/.test(keiyaku) && /前の条番号は動かない/.test(keiyaku));
    check('楽曲の特約に権利・差替え・容姿・クレジットが入っている',
        ['著作隣接権', '差し替わった場合', '容姿', 'クレジット'].every((w) => keiyaku.includes(w)));
    /* 条番号を繰り下げたので、重複や飛びが出ていないこと */
    check('契約書の条番号が第1条から連番',
        (keiyaku.match(/^### 第(\d+)条/gm) || []).map((x) => Number(x.match(/\d+/)[0]))
            .every((n, i) => n === i + 1),
        (keiyaku.match(/^### 第\d+条/gm) || []).join(','));
    check('見積書にMVの扱いが書いてある',
        /料金表の対象外/.test(mitsu) && /楽曲の権利処理/.test(mitsu));

    /* ヒアリングシート（9/19）。打ち合わせをやめてメールだけで着手するための土台。
       計算機が送るメール本文と項目がズレると、計算機から来た問い合わせに
       同じことを聞き直すことになるので、本文の項目を含んでいるかを見る */
    {
        check('ヒアリングシートがある', hearing.length > 500);
        const fromCalc = ['会社名', 'お名前', '映像の用途', '公開時期', '参考'];
        /* 計算機は 9/23 に index.html から assets/pricing.js へ移った。
           メール本文の項目はそちらを見る（index.html を見ていると素通りする） */
        const calcJs = readFileSync(`${ROOT}/assets/pricing.js`, 'utf8');
        check('計算機のメール本文の項目を含んでいる',
            fromCalc.every((w) => hearing.includes(w) && calcJs.includes(w)),
            fromCalc.filter((w) => !(hearing.includes(w) && calcJs.includes(w))).join(','));
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

    /* 口座は 〔〕 の差し込みのまま。実在の番号を置いたまま配ると事故になる */
    check('実在の口座番号を書いていない',
        /金融機関 \| 〔/.test(seikyu) && /種別・口座番号 \| 〔/.test(seikyu)
        && /口座名義 \| 〔/.test(seikyu) && !/〕\s*\d{7}/.test(seikyu));
}

/* ---- 配信できるか ---- */
for (const f of ['assets/site.css', 'assets/logo-mark.png', 'assets/favicon.png',
                 'assets/apple-touch-icon.png', 'assets/ogp.png', 'privacy.html',
                 'funnel.html', 'roadmap.html', 'record.html']) {
    const st = (await page.request.get(`${BASE}/${f}`)).status();
    check(`${f} が配信できる`, st === 200, `HTTP ${st}`);
}

/* ---- ロゴに旧社名が残っていないか（2026-09-24） ----
   ワードマークの SVG が「so.」のまま 9/11 から取り残されていた。
   いまはどこからも使っていないので表示には出なかったが、
   あとで使うと旧社名が復活する。作り直したので、戻ったら落とす */
for (const f of ['assets/logo-word.svg', 'assets/logo-word-dark.svg',
                 'assets/logo-mark.svg', 'assets/logo-mark-light.svg']) {
    const r = await page.request.get(`${BASE}/${f}`);
    const t = r.status() === 200 ? await r.text() : '';
    check(`${f} が配信できる`, r.status() === 200, `HTTP ${r.status()}`);
    check(`${f} に旧社名が残っていない`, !/>so\.</.test(t) && !/aria-label="so\."/.test(t));
    check(`${f} が so-creative を名乗っている`, /so-creative/.test(t));
}
/* 文字はアウトライン化してあること。<text> だと、フォントの無い環境で
   別の字形になったり、まるごと出なかったりする */
for (const f of ['assets/logo-word.svg', 'assets/logo-word-dark.svg']) {
    const t = await (await page.request.get(`${BASE}/${f}`)).text();
    check(`${f} の文字がアウトライン化されている`, !/<text[\s>]/.test(t));
    check(`${f} に旧ブランド色（金）が残っていない`, !/b08733|856420|d9b45f/i.test(t));
    /* ブランド色の区切りが図形で入っていること（文字の「-」にすると色を変えられない）。
       2026-09-24 に金から深緑へ変えた。この2枚は明るい地に置く用なので、
       site.css の --accent（濃地用の明るい緑）ではなく濃いほうの深緑のままでよい */
    check(`${f} にブランド色の区切りがある`, /<rect[^>]*#1c5c45/.test(t));
}
await browser.close();
report();
