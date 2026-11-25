/* 文言と実装がズレていないか。
   同じことを複数箇所に書いているので、片方だけ直すと嘘になる。
   ここはその突き合わせ専用。 */
import { check, report, open, BASE, PW, TIERS, LENGTHS, leadWeeks, FASTEST_WEEKS, RATE, PRICE, price, hours, listPrice, secFee } from './lib.mjs';
import { readFileSync, existsSync, readdirSync } from 'node:fs';
import { createHash } from 'node:crypto';
import { fileURLToPath } from 'node:url';
const pwmod = (await import(PW)).default;
const ROOT = fileURLToPath(new URL('..', import.meta.url)).replace(/\/$/, '');
const browser = await pwmod.chromium.launch();
const page = await open(browser, {});
/* 公開16ページ。検索まわりと <b> の検査で共通に使う */
const PUBLIC_PAGES = ['index.html', 'pricing.html', 'works.html', 'about.html', 'privacy.html',
    'copyright.html', 'quality.html', 'company-video.html', 'recruit-video.html',
    'service-video.html', 'ad-video.html', 'sns-video.html', 'exhibition-video.html',
    'internal-video.html', 'animation-video.html', 'music-video.html'];
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
    /* 1枚目のステージは背景も写真も暗い。札が溶けないことを見る。
       2026-09-26 まではここを「札が白いこと」で担保していたが、
       サイト全体を濃色にしたあとは、白い面はナビと CTA のボタンだけになり、
       押せない札がボタンに見えていた。濃いガラスに変えたので、
       見るのは「白いかどうか」ではなく
         ・札の中でラベルと数字が読めること（コントラスト）
         ・輪郭があること（塗りだけに頼らない）
       の2つにする */
    const mk = await page.locator('#why .stage-mark').first().evaluate((el) => {
        const cs = getComputedStyle(el);
        const lum = (c) => {
            const [r, g, bl] = (c.match(/[\d.]+/g) || [0, 0, 0]).slice(0, 3).map(Number)
                .map((x) => { x /= 255; return x <= 0.03928 ? x / 12.92 : ((x + 0.055) / 1.055) ** 2.4; });
            return 0.2126 * r + 0.7152 * g + 0.0722 * bl;
        };
        const label = getComputedStyle(el.querySelector('span')).color;
        const cr = (a, b) => (Math.max(a, b) + 0.05) / (Math.min(a, b) + 0.05);
        return {
            bg: lum(cs.backgroundColor), fg: lum(cs.color), label: lum(label),
            numCr: cr(lum(cs.backgroundColor), lum(cs.color)),
            labelCr: cr(lum(cs.backgroundColor), lum(label)),
            border: cs.borderTopWidth, borderColor: cs.borderTopColor,
            labelSize: parseFloat(getComputedStyle(el.querySelector('span')).fontSize),
            labelWeight: Number(getComputedStyle(el.querySelector('span')).fontWeight),
            unitSize: parseFloat(getComputedStyle(el.querySelector('i')).fontSize),
            numSize: parseFloat(getComputedStyle(el.querySelector('b')).fontSize),
        };
    });
    check('札の数字が読める', mk.numCr >= 4.5, `${mk.numCr.toFixed(2)}:1`);
    check('札のラベルが読める', mk.labelCr >= 4.5, `${mk.labelCr.toFixed(2)}:1`);
    /* 2026-10-09：本人の指摘「出演者０人が小さくて読みにくい」。
       コントラストは測って問題なかった（最悪の地でも 5.93:1）のに読めなかった。
       原因は寸法で、ラベルが 11.2px・単位が 16.2px しかなかった。
       一度 14px まで上げたが「まだ小さい」と再度指摘され、いまの値にした。
       上のコントラストの検査だけでは、小さすぎて読めない状態を素通りする。 */
    check('札のラベルが小さすぎない', mk.labelSize >= 20, `${mk.labelSize}px`);
    check('札のラベルが細すぎない', mk.labelWeight >= 600, `${mk.labelWeight}`);
    check('単位（人・日）が小さすぎない', mk.unitSize >= 28, `${mk.unitSize}px`);
    /* ⚠️ ここに「ラベル/数字の比」の検査を置いたが外した（2026-10-09）。
       「0 だけ巨大になるのを防ぐ」つもりだったが、守れていなかった。
       ラベルが読めるかどうかは絶対値（px）で決まるので、上の 20px の下限が
       あれば足りる。数字を大きくしたときに比だけが落ちて、デザインの方を
       小さく戻したくなる——検査が設計を縛る向きが逆だったので、消した。 */
    check('札に輪郭がある（暗い背景に溶けない）',
        parseFloat(mk.border) > 0 && !/rgba\(0, 0, 0, 0\)|transparent/.test(mk.borderColor),
        `${mk.border} ${mk.borderColor}`);
    /* 置き場所はスタックごとに違う。写真に焼き込まれたテロップと顔の位置が
       違うので、同じ位置に戻すとどちらかが必ず潰れる（2026-09-26 に実測して決めた） */
    {
        const pos = await page.locator('#why .stage-mark').evaluateAll(
            (els) => els.map((e) => getComputedStyle(e).left + '/' + getComputedStyle(e).top));
        check('2つの札は別の位置にある', pos.length === 2 && pos[0] !== pos[1], JSON.stringify(pos));
    }
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
    check('札の文字は明るい色（濃いガラスの上）', mk.fg > 0.7, JSON.stringify(mk));
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
    /* ⚠️ 2026-10-06：資産には中身から出した版（?v=）を打っている
       （tools/stamp_assets.py）。版まで含めて完全一致で見ると、映像を
       差し替えるたびにここが落ちる。版の有無は許して、「ポスターが
       指定されていること」だけを見る。この形はこのファイル内に8か所ある。 */
    check('追加した2本にもポスター画像がある',
        /poster="assets\/works\/service-15s\.jpg(\?v=[0-9a-f]+)?"/.test(worksSrc)
        && /poster="assets\/works\/cm-15s-taste\.jpg(\?v=[0-9a-f]+)?"/.test(worksSrc));
    /* 05 SNSショートと 07 社内向けのサンプル（2026-09-17 追加）。
       05 は最初から縦型で組んでいるので、16:9 のまま出していないことも見る */
    /* ⚠️ 2026-10-20：SNSだけサンプルが2本になった（コインランドリー／コーヒースタンド）。
       「本数を重ねる運用に向く」と書いているジャンルの実例が1本では裏づけが無いため。
       ここを1本に戻すときは、genre_data の 'extra' と works.html も一緒に戻すこと。 */
    check('SNSショートのカードにサンプルが2本ある',
        (await wp.locator('#genre-sns .sample-video').count()) === 2);
    check('SNSショートのサンプルは架空の題材だと書いてある',
        /架空のコインランドリー/.test(await wp.locator('#genre-sns').innerText())
        && /架空のコーヒースタンド/.test(await wp.locator('#genre-sns').innerText()));
    /* 縦型は【2本とも】見る。1本目だけ見ていると、足した側が 16:9 でも気づかない */
    check('SNSショートのサンプルは2本とも縦型で表示している',
        (await wp.locator('#genre-sns .sample-video.is-vertical').count()) === 2
        && (await wp.locator('#genre-sns .sample-video').evaluateAll(
            (vs) => vs.every((v) => v.clientHeight > v.clientWidth))));
    check('社内向けのカードにサンプルがある',
        (await wp.locator('#genre-internal .sample-video').count()) === 1);
    check('社内向けのサンプルは架空の題材だと書いてある',
        /架空の倉庫/.test(await wp.locator('#genre-internal').innerText()));
    check('さらに追加した2本も自前で配信している',
        /assets\/works\/sns-15s-vertical\.mp4/.test(worksSrc)
        && /assets\/works\/internal-15s\.mp4/.test(worksSrc));
    check('さらに追加した2本にもポスター画像がある',
        /poster="assets\/works\/sns-15s-vertical\.jpg(\?v=[0-9a-f]+)?"/.test(worksSrc)
        && /poster="assets\/works\/internal-15s\.jpg(\?v=[0-9a-f]+)?"/.test(worksSrc));
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
        /poster="assets\/works\/recruit-3min\.jpg(\?v=[0-9a-f]+)?"/.test(worksSrc));
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
    check('ミュージックビデオのサンプルは4分24秒だと書いてある',
        /サンプル（4分24秒）/.test(await wp.locator('#genre-mv').innerText()));
    check('ミュージックビデオのサンプルも自前で配信している',
        /assets\/works\/mv-full-264s\.mp4/.test(worksSrc));
    check('ミュージックビデオのサンプルにもポスター画像がある',
        /poster="assets\/works\/mv-full-264s\.jpg(\?v=[0-9a-f]+)?"/.test(worksSrc));
    /* 曲は鈴木さん自身のもの。権利の出所を書いていないと、
       既存曲を無断で使ったように見える */
    check('ミュージックビデオの曲の出所を書いている',
        /自作のオリジナル曲/.test(await wp.locator('#genre-mv').innerText()));
    /* 09 アニメーション・図解（9/19 追加）。生成AIを使っていない唯一のサンプル。
       文字が主役の題材はAIが画面内の文字を描けないので、プログラム描画だと
       明記してあること（これが売り文句であり、嘘をつかないための断りでもある） */
    {
        const an = await wp.locator('#genre-animation').innerText();
        /* 2026-11-25：自主制作の欄をなくし「ふたつの目」をここへ移したので2本。
           2本目は歴史の場面が生成AIなので、1本目とは作り方が違うと書いてあること */
        check('アニメーションのカードにサンプルが2本ある',
            await wp.locator('#genre-animation .sample-video').count() === 2);
        check('ふたつの目は生成AIの場面があると断っている', /歴史の場面8カットだけは日本画風の絵を生成AI/.test(an));
        check('地図の出典を出している', /国土数値情報（行政区域データ・2021年）国土交通省 を加工して作成/.test(an));
        check('自主制作の欄が残っていない', await wp.locator('#original').count() === 0);
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
        /poster="assets\/works\/company-60s\.jpg(\?v=[0-9a-f]+)?"/.test(worksSrc));
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
    /* 会社紹介のページでも聴き比べられる（2026-09-30）。それまではテロップ版だけで、
       「制作サンプルのページでどうぞ」と別ページへ送っていた。料金表は
       「ナレーション込みの額」なのに、そのページでは声入りを聴けなかった */
    {
        const cp = await open(browser, { page: 'company-video.html' });
        check('会社紹介のページにもナレーションの切り替えがある', (await cp.locator('.sample-sw').count()) === 2);
        check('会社紹介のページでも音声がAIだと書いてある',
            /AIナレーションあり/.test(await cp.locator('.sample-switch').innerText())
            && /このナレーションはAI音声です/.test(await cp.locator('body').innerText()));
        const v = cp.locator('#sample-video');
        const before = await v.getAttribute('src');
        await cp.locator('.sample-sw', { hasText: 'ナレーションあり' }).click();
        await cp.waitForTimeout(400);
        const after = await v.getAttribute('src');
        check('会社紹介のページで切り替えると音源が変わる', before !== after && /narration/.test(after), `${before} → ${after}`);
        check('会社紹介のページが聴き比べを別ページへ送っていない',
            !/制作サンプルのページ<\/a>でどうぞ/.test(readFileSync(`${ROOT}/company-video.html`, 'utf8')));
        await cp.close();
    }
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
                g.total === listPrice(TIERS[0], g.len), String(g.total));
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
            after[0] === `¥${listPrice(TIERS[2], 60).toLocaleString('ja-JP')}`, after[0]);
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
        /* 2026-10-14：松の「人物→AI」の返し（¥70,000）と、ナレーションを
           入れない本の引き（¥25,000）は別の額になった。本文も2つに分けてある。
           ⚠️ 1つの数字で書き直さないこと（どちらかが嘘になる）。 */
        check('引く額がモデルと合っている',
            idx.includes(`¥${PRICE.noNarration.toLocaleString('ja-JP')} を引きます`)
            && idx.includes(`¥${PRICE.matsuToAi.toLocaleString('ja-JP')}</b> 引きです`),
            `${PRICE.noNarration}/${PRICE.matsuToAi}`);

        check('トップの料金表の金額がモデルと合っている',
            idxRows.every(([lab, cells]) => TIERS.every((t, i) =>
                cells[i] === y(listPrice(t, SECS[lab])))),
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
    check('自社サンプルの日数と一致している', /着手から3日/.test(svc));
    check('2本目の値段が料金表と一致している', svc.includes(`¥${PRICE.perExtra.toLocaleString('en-US')}`));
    check('誇大な言い方をしていない',
        !/必ず|絶対|劇的|革命|No\.?1|業界最|最先端/.test(svc), svc.slice(0, 60));
    /* お客様の状況を勝手に決めつけない（2026-09-20）。
       「年に1本の大仕事」と書いたが、こちらで確かめられない前提だった */
    check('相手の制作頻度を決めつけていない',
        !/年に1本|年1本|どこの会社も|みなさん/.test(svc), svc.slice(0, 60));
    const hero = await page.locator('.hero-inner').innerText();
    check('ヒーローもできることで書いている',
        /最短3週間で納品/.test(hero) && /訴求違い/.test(hero));
}
check('人物ナレーションの追加料金が FAQ と計算機で同じ',
    /1名 ¥70,000〜/.test(idx) && /narrationHuman: 70000/.test(calcSrc));
/* AIを有料に戻すときは、ここと計算機と文言を必ず一緒に直す */
check('AIナレーションが計算機でも ¥0 になっている', /narrationAi: 0/.test(calcSrc));
/* AIを込みにした代わりに、使わないときは引く。額は3か所で揃っていること */
check('ナレーションなしの差し引きが計算機と文言で同じ',
    /noNarration: 25000/.test(calcSrc) && /−¥25,000/.test(pricingHtml)
    && /¥25,000 を差し引き/.test(idx));

/* 2026-09-26：@type を ["Organization", "ProfessionalService"] の配列にしたので、
   文字列一致では拾えなくなった。名古屋の事業者として正しい型で出すため */
const org = ld.find(d => d['@graph'])?.['@graph']
    ?.find(x => [].concat(x['@type']).includes('Organization')) || {};
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
        /poster="assets\/works\/ugc-mamoriha-talk\.jpg(\?v=[0-9a-f]+)?"/.test(idx));
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
    && rows.some(([k, v]) => k === '所在地' && /愛知県名古屋市/.test(v)));
/* 所在地は【郵便物が届く住所】でなければならない。特定電子メール法 第4条の表示事項で、
   営業メールの末尾から privacy.html 経由でここが参照先になる。市までの表記に戻すと
   要件を満たさなくなるので、郵便番号・番地・建物名まで在ることを見る（2026-10-15） */
{
    const loc = rows.find(([k]) => k === '所在地')[1];
    check('所在地に郵便番号がある', /〒\d{3}-\d{4}/.test(loc), loc);
    check('所在地が番地まで書いてある', /\d+-\d+-\d+/.test(loc), loc);
    check('所在地に建物名がある', /メガシティテラス/.test(loc), loc);
}
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
/* 「最短」は梅・15秒で修正1回で済んだ場合（2026-11-25）。上限まで使う目安の最小より短い */
check('タイトルの「最短3週間」が実態と合う',
    /最短3週間/.test(idx) && FASTEST_WEEKS === 3
    && FASTEST_WEEKS <= Math.min(...TIERS.flatMap(t => LENGTHS.map(s => leadWeeks(t, s)))));
check('「最短2週間」がどのページにも残っていない',
    ['index.html', 'works.html', 'company-video.html', 'pricing.html'].every((f) => !/最短2週間/.test(readFileSync(`${ROOT}/${f}`, 'utf8'))));
/* ジャンルページの納期の一文は、梅〜松の幅と一致させる */
for (const [f, sec] of [['ad-video.html', 15], ['animation-video.html', 60], ['exhibition-video.html', 15], ['internal-video.html', 15],
                        ['recruit-video.html', 90], ['service-video.html', 15], ['sns-video.html', 15], ['company-video.html', 60]]) {
    const want = `納期は${sec}秒で${rng(sec)}`;
    check(`${f} の納期が計算結果と一致`, readFileSync(`${ROOT}/${f}`, 'utf8').includes(want), want);
}

/* ---- <b> を入れ子にしない（2026-09-26） ----
   料金の文を差し替えたとき、既にある <b>…</b> の中に書き足してしまい、
   段落まるごとが太字になっていた。数えるだけでは釣り合ってしまうので、
   深さを見る。<style> と <script> の中の文字（CSS のコメントに <b> と
   書いてある）は数えない */
{
    const FILES = [...PUBLIC_PAGES, 'funnel.html'];
    for (const f of FILES) {
        const html = readFileSync(`${ROOT}/${f}`, 'utf8')
            .replace(/<style[\s\S]*?<\/style>/g, '')
            .replace(/<script[\s\S]*?<\/script>/g, '');
        let depth = 0, nested = 0, stray = 0, deepest = '';
        for (const m of html.matchAll(/<b\b[^>]*>|<\/b\s*>/g)) {
            if (m[0].startsWith('</')) { depth > 0 ? depth-- : stray++; }
            else {
                if (depth > 0 && !nested++) deepest = html.slice(Math.max(0, m.index - 50), m.index + 30).replace(/\s+/g, ' ');
                depth++;
            }
        }
        check(`${f} の <b> が入れ子になっていない`, nested === 0, deepest);
        check(`${f} の <b> が釣り合っている`, depth === 0 && stray === 0, `閉じ忘れ ${depth} / 余分 ${stray}`);
    }
}

/* ---- 検索まわり（2026-09-26） ----
   開業日まで noindex は外さない（体調しだいで未定。record.html の判断）。
   いま出来るのは、外した日にそのまま効く状態にしておくところまで。 */
{
    const PUB = PUBLIC_PAGES;
    const titles = new Map(), descs = new Map();
    for (const f of PUB) {
        const h = readFileSync(`${ROOT}/${f}`, 'utf8');
        const t = (h.match(/<title>([\s\S]*?)<\/title>/) || [])[1];
        const d = (h.match(/<meta name="description" content="([\s\S]*?)"/) || [])[1];
        check(`${f} に title がある`, !!t && t.length >= 15 && t.length <= 60, `${t ? t.length : 0}字`);
        check(`${f} に description がある`, !!d && d.length >= 70 && d.length <= 160, `${d ? d.length : 0}字`);
        check(`${f} に canonical がある`, /<link rel="canonical" href="https:/.test(h));
        check(`${f} の h1 は1つ`, (h.match(/<h1[\s>]/g) || []).length === 1);
        /* 構造化データが壊れていると、丸ごと読まれずに落ちる */
        for (const m of h.matchAll(/<script type="application\/ld\+json">([\s\S]*?)<\/script>/g)) {
            let ok = true;
            try { JSON.parse(m[1]); } catch { ok = false; }
            check(`${f} の JSON-LD が構文として正しい`, ok);
        }
        check(`${f} に JSON-LD がある`, /application\/ld\+json/.test(h));
        if (titles.has(t)) check(`title が他のページと重なっていない（${f}）`, false, `${titles.get(t)} と同じ`);
        if (descs.has(d)) check(`description が他のページと重なっていない（${f}）`, false, `${descs.get(d)} と同じ`);
        titles.set(t, f); descs.set(d, f);
    }
    check('title は16ページとも別の文', titles.size === PUB.length, `${titles.size} 種類`);
    check('description は16ページとも別の文', descs.size === PUB.length, `${descs.size} 種類`);

    /* 名古屋の事業者として正しい型で出す。Organization だけだと地域の扱いにならない。
       ただしこれで地図枠に出るわけではない（それは Google ビジネスプロフィール側） */
    const idx = readFileSync(`${ROOT}/index.html`, 'utf8');
    const org = JSON.parse(idx.match(/<script type="application\/ld\+json">([\s\S]*?)<\/script>/)[1])
        ['@graph'].find((n) => String(n['@id']).endsWith('#org'));
    check('事業者を ProfessionalService として出している',
        [].concat(org['@type']).includes('ProfessionalService'), String(org['@type']));
    check('所在地が名古屋市になっている', org.address.addressLocality === '名古屋市');
    check('営業時間を出している', !!org.openingHoursSpecification, JSON.stringify(org.openingHoursSpecification || null));
    check('価格帯が料金表の下限・上限と合っている', (() => {
        const all = TIERS.flatMap((t) => LENGTHS.filter((s) => s <= 180).map((s) => listPrice(t, s)));
        const lo = Math.min(...all), hi = Math.max(...all);
        return org.priceRange === `¥${lo.toLocaleString('en-US')}〜¥${hi.toLocaleString('en-US')}`;
    })(), org.priceRange);
    /* 電話番号はサイトから外してある。構造化データにも入れない */
    check('構造化データに電話番号を入れていない', !/"telephone"/.test(idx));

    /* sitemap。lastmod は合っていないと無視されるので、git から入れ直す
       （scripts/update-dates.py）。ここでは日付として成立しているかだけ見る */
    const sm = readFileSync(`${ROOT}/sitemap.xml`, 'utf8');
    const locs = [...sm.matchAll(/<loc>([^<]+)<\/loc>/g)].map((m) => m[1]);
    const mods = [...sm.matchAll(/<lastmod>([^<]+)<\/lastmod>/g)].map((m) => m[1]);
    check('sitemap の <loc> すべてに <lastmod> がある', locs.length === mods.length, `${locs.length} / ${mods.length}`);
    const today = new Date().toISOString().slice(0, 10);
    const future = mods.filter((d) => !/^\d{4}-\d{2}-\d{2}$/.test(d) || d > today);
    check('lastmod が日付として成立していて、未来になっていない', future.length === 0, future.join(' '));

    /* 背景の映像は 2.9MB ある。9/29 から開いた直後の画面は映像そのものなので狭い画面でも流すが、
       通信量を節約する設定の人には取りに行かせない */
    check('画面が狭いだけでは映像を諦めない',
        !/max-width: 860px\)'\)\.matches\s*\|\|/.test(idx));
}

/* ---- 省データ設定では取りに行かない／それでも本人は流せる（2026-10-20） ----
   ⚠️ ここは以前「ソースに removeAttribute('src') と書いてあるか」を正規表現で見ていた。
      実装を preload="none" に変えた瞬間、振る舞いは正しいのにテストだけが落ちた。
      書き方を見るテストは、書き方を変えるたびに嘘になる。
      【実際にバイトを取りに行ったか】で見る。 */
{
    const { mockFonts, mockYtimg } = await import('./route.mjs');
    const sd = await browser.newPage({ viewport: { width: 1280, height: 900 } });
    await sd.addInitScript(() => {
        Object.defineProperty(navigator, 'connection', {
            configurable: true,
            get: () => ({ saveData: true }),
        });
    });
    await mockFonts(sd); await mockYtimg(sd);
    const got = [];
    sd.on('request', (r) => { if (/hero-reel\.(mp4|webm)/.test(r.url())) got.push(r.url()); });
    /* ⚠️ networkidle では待てない。省データのときは映像を取りに行かないので、
       「静まるのを待つ」条件が、待っている当のものと噛み合わない */
    await sd.goto(`${BASE}/index.html`, { waitUntil: 'domcontentloaded' });
    await sd.waitForTimeout(1200);
    check('通信量を節約する設定では背景の映像を読み込まない', got.length === 0, got.join(' '));
    /* 取りに行かないことと、流せないことは別物。本人が押せる出口を必ず残す */
    check('通信量を節約する設定でも、再生ボタンは出ている',
        await sd.locator('.hero-play').isVisible());
    await sd.locator('.hero-play').click();
    for (let i = 0; i < 40 && got.length === 0; i += 1) await sd.waitForTimeout(100);
    check('押したときに初めて映像を取りに行く', got.length > 0, String(got.length));
    await sd.waitForTimeout(1200);
    check('押せば省データ設定でも再生が始まる',
        await sd.locator('#hero-video').evaluate((e) => !e.paused));
    await sd.close();
}

/* ---- タイトルの値段が、そのページが実際に薦める構成と合っているか（2026-09-28） ----
   company-video.html のタイトルだけ梅（60秒 ¥300,000）を出していた。
   ところが本文は「よく選ばれるのは60秒・竹（¥384,000）」と書いていて、
   載せているサンプルも登場人物2人＝竹。検索結果で ¥300,000 を見た人が
   そのサンプルを観ると、¥84,000 安く見積もることになる。
   recruit-video.html は前から竹の額（90秒 ¥531,000）を出していて、
   サンプルが4人で料金表の上限（松で3人）を超えることも本文に書いてある。
   その形に揃えた。music-video.html はタイトルに額を出していないので対象外。 */
{
    /* [ファイル, タイトルに出す尺, タイトルに出す段] */
    const LEAD = [
        ['company-video.html',    60, '竹'],
        ['recruit-video.html',    90, '竹'],
        ['service-video.html',    15, '梅'],
        ['ad-video.html',         15, '梅'],
        ['sns-video.html',        15, '梅'],
        ['exhibition-video.html', 15, '梅'],
        ['animation-video.html',  60, '梅'],
        ['internal-video.html',   15, '梅'],
    ];
    const yen = (n) => `¥${n.toLocaleString('en-US')}`;
    for (const [f, sec, label] of LEAD) {
        const h = readFileSync(`${ROOT}/${f}`, 'utf8');
        const t = TIERS.find((x) => x.label === label);
        const want = yen(price(t, sec, 1));
        const head = {
            title: (h.match(/<title>([\s\S]*?)<\/title>/) || [])[1] || '',
            description: (h.match(/<meta name="description" content="([\s\S]*?)"/) || [])[1] || '',
            'og:description': (h.match(/<meta property="og:description" content="([\s\S]*?)"/) || [])[1] || '',
        };
        /* 尺に付いた額だけを見る。本数加算の ¥65,000 のような別の額が
           同じ文に入っているのは正しい（sns-video の description がそれ）。
           そちらは「2本目の値段」の検査で見ている */
        for (const [where, text] of Object.entries(head)) {
            for (const m of text.matchAll(/(\d+)秒\s*(¥[\d,]+)/g)) {
                check(`${f} の ${where} の「${m[1]}秒 ${m[2]}」が料金表と合っている`,
                    Number(m[1]) === sec && m[2] === want, `期待 ${sec}秒 ${want}`);
            }
        }
        /* タイトルから額が消えていないこと（消すと上のループが空回りする） */
        check(`${f} の title が ${sec}秒・${label}（${want}）を出している`,
            new RegExp(`${sec}秒\\s*${want}`).test(head.title), head.title);
        /* 「よく選ばれるのは」が別の段を指していたら、タイトルとどちらかが古い */
        const rec = h.match(/よく選ばれるのは、[^。<]*?([梅竹松])/);
        if (rec) {
            check(`${f} の「よく選ばれるのは」がタイトルと同じ段（${label}）`,
                rec[1] === label, `本文 ${rec[1]} ／ タイトル ${label}`);
        }
    }
    /* サンプルに映る人数が、タイトルの段で作れる人数を超えていないか。
       超えるなら、その旨を本文に書いていること */
    const CAP = { '梅': 0, '竹': 2, '松': 3 };
    for (const [f, , label] of LEAD) {
        const h = readFileSync(`${ROOT}/${f}`, 'utf8');
        const m = h.match(/登場人物は(\d+)人/);
        if (!m) continue;
        const people = Number(m[1]);
        check(`${f} のサンプルの人数（${people}人）が ${label}（${CAP[label]}人まで）で作れる、または超える旨を書いている`,
            people <= CAP[label] || /料金表の(?:上限|範囲)/.test(h), `${label} は ${CAP[label]}人まで`);
    }
}

/* ---- 「会社紹介」と名指しで出す額を1つに揃える（2026-09-29） ----
   同じ「会社紹介」に4つの額が付いていた。
     ¥195,000  pricing.html のタイトル（30秒・梅）
     ¥300,000  company-video.html のタイトル（60秒・梅）
     ¥384,000  company-video.html の本文「よく選ばれるのは60秒・竹」
     ¥531,000  pricing.html の計算機プリセット（90秒・竹）
   基準は、ページに載せている動画そのもの（59秒・登場人物2人＝竹の60秒）。
   それ以外の額を「会社紹介は」と言って出さない。 */
{
    const want = `¥${price(TIERS.find((x) => x.label === '竹'), 60, 1).toLocaleString('en-US')}`;
    /* 「会社紹介…¥N」と名指しで書いている箇所。表の行や、本数加算の説明は対象外
       （そちらは尺ごと・差額ごとの額で、会社紹介1本の値段ではない） */
    for (const f of ['pricing.html', 'company-video.html', 'index.html']) {
        const h = readFileSync(`${ROOT}/${f}`, 'utf8');
        for (const m of h.matchAll(/会社紹介(?:動画)?(?:は|の)?\s*(\d+)秒\s*(¥[\d,]+)/g)) {
            check(`${f} の「会社紹介${m[1]}秒 ${m[2]}」が載せている動画の見積り（60秒 ${want}）と同じ`,
                m[1] === '60' && m[2] === want, `期待 60秒 ${want}`);
        }
    }
    /* 計算機のプリセットも同じ組み合わせであること（額は pricing.mjs で実際に押して見ている） */
    const pr = readFileSync(`${ROOT}/pricing.html`, 'utf8');
    const pre = pr.match(/<button[^>]*data-tier="([^"]*)"[^>]*data-len="([^"]*)"[^>]*>\s*<b>会社紹介<\/b>(\d+)秒/);
    check('会社紹介のプリセットが 60秒・竹 で、表示と data-len が一致している',
        !!pre && pre[1] === 'take' && pre[2] === '60' && pre[3] === '60',
        pre ? `${pre[1]} data-len=${pre[2]} 表示${pre[3]}秒` : '見つからない');
    /* 展示会ページの「会社紹介◯秒・段」も揃えておく */
    const ex = readFileSync(`${ROOT}/exhibition-video.html`, 'utf8');
    const exm = ex.match(/会社紹介(\d+)秒・([梅竹松])/);
    if (exm) {
        check('exhibition-video.html の「会社紹介」が 60秒・竹',
            exm[1] === '60' && exm[2] === '竹', `${exm[1]}秒・${exm[2]}`);
    }
    /* 90秒を会社紹介の定番として書き戻していないか */
    for (const f of ['index.html', 'pricing.html', 'company-video.html']) {
        const h = readFileSync(`${ROOT}/${f}`, 'utf8')
            /* 訂正のメモそのものは、外した言い方を引用してよい */
            .replace(/2026-09-29：[\s\S]*?-->/g, '');
        check(`${f} が90秒を会社紹介の定番として書いていない`,
            !/会社紹介[^。<]{0,10}(?:でいちばん多い尺|の定番)[^。<]{0,6}90秒/.test(h)
            && !/90秒[^。<]{0,6}会社紹介でいちばん多い/.test(h));
    }
}

/* ---- 秒単価の実数を本文に書いている所が、全部モデルと合っているか（2026-10-13） ----
   逓減（最初の30秒／31〜90秒／91秒以降）に変えたとき、表と計算機は直したのに
   index.html の FAQ（JSON-LD）とリード文、pricing.html の秒単価の行と
   計算機の静的な初期表示に【旧価格 梅4,000／竹5,400／松8,000】が残った。
   どのテストもそこを読んでいなかったので、1,603件が全部通ったまま
   公開ページに古い式が残る状態になっていた。
   「表の金額」だけでなく「文章に書いた秒単価」も突き合わせる。 */
{
    for (const f of ['index.html', 'pricing.html']) {
        const h = readFileSync(`${ROOT}/${f}`, 'utf8');
        /* 旧モデルの秒単価（1つの段に1つの単価）が残っていないか。
           逓減後は 4,000／5,400／8,000 はどの段のどの段階にも無い数字 */
/* 2026-10-13 に入れた逓減の単価が残っていないか（2026-10-14 に1つへ戻した）。
           いまの秒単価に無い額だけを「古い」と見なす */
        const live = new Set(TIERS.map((x) => x.perSec));
        const stale = [5500, 4500, 3200, 7400, 5700, 4300, 10500, 6400]
            .filter((n) => !live.has(n))
            .map((n) => `¥${n.toLocaleString('en-US')}`)
            .filter((x) => h.replace(/<!--[\s\S]*?-->/g, '').includes(x));
        check(`${f} に旧モデルの秒単価が残っていない`, stale.length === 0, stale.join());
        /* いまの秒単価が書いてあること */
        for (const t of TIERS) {
            const want = `¥${t.perSec.toLocaleString('en-US')}`;
            check(`${f} に${t.label}の秒単価が書いてある`, h.includes(want), want);
        }
    }
    /* FAQ の例示額が式と合っているか（30秒・梅／90秒・竹／3分・松） */
    const idxH = readFileSync(`${ROOT}/index.html`, 'utf8');
    for (const [sec, ti] of [[30, 0], [90, 1], [180, 2]]) {
        const want = `¥${listPrice(TIERS[ti], sec).toLocaleString('en-US')}`;
        check(`index.html の例示額（${sec}秒・${TIERS[ti].label}）が式と一致`,
            idxH.includes(want), want);
    }
}

/* ---- 実測の節（つくれる動画の説明欄）---- 
   2026-10-13 に足したとき、生成スクリプトの2行が重複していて
   【同じ節が2回出る】状態のまま公開されていた（翌日に発見）。
   出力を見れば分かるのに、テストが節の有無しか見ていなかった。
   ⚠️ 「ある」ではなく「1回だけある」を見ること。 */
{
    const GEN = ['service-video.html', 'ad-video.html', 'sns-video.html',
        'exhibition-video.html', 'internal-video.html', 'animation-video.html',
        'music-video.html'];
    for (const f of GEN) {
        const h = readFileSync(`${ROOT}/${f}`, 'utf8');
        const n = (h.match(/class="section measured"/g) || []).length;
        check(`${f} に実測の節が1つだけある`, n === 1, String(n));
    }
}

/* ---- 定額の部分は「企画・構成費」と呼ぶ（2026-09-29） ----
   「基本料金 ¥180,000」だと、動画の前にまず18万かかるように読める。
   中身（ヒアリング・構成案・絵コンテ・進行）が名前で分かるようにした。
   内部の記録（record.html の改定前の見積りの節など）は当時の呼び名のまま */
{
    for (const f of [...PUBLIC_PAGES, 'assets/pricing.js', '成果物/書類ひな形/見積書.md']) {
        const h = readFileSync(`${ROOT}/${f}`, 'utf8');
        check(`${f} で「基本料金」と呼んでいない`, !/基本料金/.test(h), (h.match(/.{0,20}基本料金.{0,20}/) || [''])[0]);
    }
    const pr = readFileSync(`${ROOT}/pricing.html`, 'utf8');
    check('料金ページに企画・構成費の額と中身が書いてある',
        pr.includes(`企画・構成費 ¥${PRICE.base.toLocaleString('en-US')}（1案件に1回）`)
        && pr.includes(`2本目以降 1本につき ¥${PRICE.perExtra.toLocaleString('en-US')}`) && /ヒアリング・企画・進行管理/.test(pr));
}

/* ---- 2本目の値段を ¥65,000 と言い切らない（2026-09-26） ----
   式は base + 秒単価 × 【合計】秒数 + ¥65,000 × (本数 − 1) なので、
   2本目にも秒単価がかかる。¥65,000 は本数加算だけの額で、2本目の値段ではない。
   「2本目以降は ¥65,000」と9ページに書いていて、15秒の2本目で ¥52,500、
   60秒・竹の2本目では ¥294,000 少なく見せていた。
   まとめて頼んで安くなるのは、段にも尺にもよらず1本につき ¥25,000
   （基本料金 ¥90,000 − 本数加算 ¥65,000）だけ。 */
{
    const PAGES = ['index.html', 'company-video.html', 'recruit-video.html', 'service-video.html',
        'ad-video.html', 'sns-video.html', 'exhibition-video.html', 'internal-video.html',
        'animation-video.html'];
    /* 2本目を ¥65,000 だと言い切る形。式の一部として出すぶんには問題ない */
    const WRONG = [
        /2本目[^。<]{0,12}は\s*(?:1本\s*)?¥65,000\s*(?:です|。|<)/,
        /2本目[^。<]{0,12}が\s*¥65,000/,
        /(?:追加|短尺|STEP[^。<]{0,8})[^。<]{0,20}1本\s*¥65,000/,
        /1本\s*¥65,000\s*で(?:出せ|済み)/,
        /尺の料金[がは][^。<]{0,10}かから/,
    ];
    for (const f of PAGES) {
        const html = readFileSync(`${ROOT}/${f}`, 'utf8')
            /* 訂正の記録そのものは、間違った言い方を引用してよい */
            .replace(/（2026-09-26 訂正）[\s\S]*?<\/b>/g, '');
        const hit = WRONG.map((re) => html.match(re)).find(Boolean);
        check(`${f} は2本目の値段を ¥65,000 と言い切っていない`, !hit, hit ? hit[0] : '');
    }
    /* 本文に出した「＋¥N」が、式から計算し直した額と合っているか */
/* 2026-10-13：秒単価が逓減になったので「本数加算 ＋ 秒単価 × 尺」では出せない。
       同じ尺をもう1本足したときの増分（合計が2倍になるぶん）で計算する。
       逓減があるので、この増分は1本目の値段より安い */
    /* 足す尺の増分は「どこに足すか」で変わる（逓減なので、すでに長い案件に
       足すほど安い）。段・1本目の尺・足す尺を、本文の文章と同じ組で持つ。
       2026-10-13 まで add(段, 尺) の2引数で「同じ尺を2本」として計算していたが、
       旧モデルは linear で増分が1本目の尺によらなかったので偶然合っていただけ。
       逓減にしたら service（60秒＋15秒）が ¥162,500 と ¥147,500 でずれた。
       exhibition は旧モデルのとき竹の案件に梅の秒単価で ¥160,000 と書いてあり、
       ¥21,000 少なかった（2026-10-13 に竹の額へ訂正）。 */
    /* 2026-10-14：秒単価を1つに戻したので、増分は「足す尺」だけで決まる
       （逓減のときは、すでに何秒あるかで変わった）。段は本文の記述と合わせる */
    const add = (label, addSec) =>
        PRICE.perExtra + TIERS.find((x) => x.label === label).perSec * addSec;
    const WANT = [
        ['index.html', add('梅', 30)],
        ['company-video.html', add('竹', 15)],
        ['recruit-video.html', add('竹', 30)],
        ['service-video.html', add('梅', 15)],
        ['ad-video.html', add('梅', 15)],
        ['sns-video.html', add('梅', 15)],
        ['exhibition-video.html', add('竹', 15)],
        ['internal-video.html', add('梅', 30)],
        ['animation-video.html', add('梅', 15)],
    ];
    const yen = (n) => `¥${n.toLocaleString('en-US')}`;
    for (const [f, want] of WANT) {
        const html = readFileSync(`${ROOT}/${f}`, 'utf8');
        check(`${f} の2本目の実額が式と一致`, html.includes(`＋${yen(want)}`), yen(want));
    }
/* まとめたときの差。2026-10-13 までは段にも尺にもよらず常に base − perExtra
       （¥80,000）の固定だった。秒単価を逓減にしたので**合計の尺が長いほど大きく**なる。
       固定でなくなった代わりに、次の2つは必ず成り立つ：
         ① まとめた方が必ず安い（最低でも base − perExtra ぶん）
         ② 合計の尺が長くなるほど差は縮まらない（逓減が効くため）
       ここを「一定」に戻さないこと。戻すと逓減を外したことになる */
    const floorGap = PRICE.base - PRICE.perExtra;
    const gap = (t, sec) => listPrice(t, sec) * 2 - (listPrice(t, sec * 2) + PRICE.perExtra);
    let bad = null, prev = null, nonMono = null;
    for (const t of TIERS) {
        prev = null;
        for (const sec of LENGTHS) {
            const g = gap(t, sec);
            if (g < floorGap) bad = `${t.label}${sec}秒 ¥${g}`;
            if (prev !== null && g < prev) nonMono = `${t.label}${sec}秒 ¥${g} < ¥${prev}`;
            prev = g;
        }
    }
    check('まとめ買いは必ず安い（最低 base − perExtra）', !bad, bad || `最低 ¥${floorGap.toLocaleString('en-US')}`);
    check('まとめ買いの差は尺が長いほど縮まらない', !nonMono, nonMono || `梅15秒 ¥${gap(TIERS[0], 15).toLocaleString('en-US')} → 梅90秒 ¥${gap(TIERS[0], 90).toLocaleString('en-US')}`);
}

/* ---- 「3日」を納期と読ませない（2026-09-26） ----
   3日は、自社サンプルを確認の往復なしで仕上げたときの制作工程だけの数字。
   工程表とFAQの納期（2026-11-25 から、ご確認の日数を含めて約4〜7週間）と食い違う。
   ヒーローに「3日で1本できる」とだけ出していたので、
   納品が3日だと読めた。数字を出すなら、条件も同じ場所に置く */
{
    const QUALIFIER = /自社|サンプル/;
    for (const f of ['index.html', 'works.html', 'company-video.html']) {
        const html = readFileSync(`${ROOT}/${f}`, 'utf8');
        const bad = [];
        for (const m of html.matchAll(/3日/g)) {
            const around = html.slice(Math.max(0, m.index - 400), m.index + 400);
            if (!QUALIFIER.test(around)) bad.push(html.slice(Math.max(0, m.index - 30), m.index + 10).replace(/\s+/g, ' '));
        }
        check(`${f} の「3日」に自社制作だと分かる条件が付いている`, bad.length === 0, bad.slice(0, 2).join(' / '));
    }
    /* 看板の速さは、工程表から出した数字（FASTEST_WEEKS＝3週間）とだけ言う */
    check('ヒーローの速さがタイトルと同じ数字', /最短3週間/.test(idx.split('<ul class="hero-chips">')[1] || ''));
    /* 「その週のうちに」「数日で公開」は、納品までの日数と矛盾する */
    check('納品が数日だと読める言い方をしていない',
        !/その週のうちに|数日で公開|数日で納品|3日で1本/.test(idx), idx.match(/その週のうちに|数日で公開|数日で納品|3日で1本/)?.[0] || '');
}

/* ---- 料金の説明文が段と矛盾していないか ----
   段で秒単価が変わるのに「1秒あたり ¥3,500」と書いてあると嘘になる */
const why = await (await open(browser, { page: 'pricing.html' })).locator('.calc-why').innerText();
check('内訳の秒単価が段の幅で書いてある',
    why.includes(`¥${Math.min(...TIERS.map((t) => t.perSec)).toLocaleString('en-US')}〜${Math.max(...TIERS.map((t) => t.perSec)).toLocaleString('en-US')}`) && /仕上げの段階/.test(why), why.split('\n').find(l => l.includes('1秒')) || '');
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
   assets/site.css と、社内用ページ（いまは funnel.html だけ）の中に書いた :root が別々に存在する。
   地の色を薄い緑に変えたとき、片方だけ直すと同じ「社内用」の紙なのに
   色が違って見える。まとめて動かすために突き合わせる */
{
    const css = readFileSync(`${ROOT}/assets/site.css`, 'utf8');
    const tok = (src, name) => (src.match(new RegExp(`--${name}:\\s*([^;]+);`)) || [])[1]?.trim();
    const WANT = ['bg', 'bg-alt', 'card', 'ink', 'ink-dim', 'ink-2', 'on-ink', 'accent', 'accent-ink'];
    const base = Object.fromEntries(WANT.map((k) => [k, tok(css, k)]));
    check('site.css に色のトークンが揃っている',
        WANT.every((k) => base[k]), JSON.stringify(base));
    for (const f of ['funnel.html']) {
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
    for (const f of ['funnel.html']) {
        const h = readFileSync(`${ROOT}/${f}`, 'utf8');
        check(`${f} が color-scheme: dark を宣言している`, /color-scheme:\s*dark/.test(h));
    }

    /* カードの地を直書きの白に戻さない。白のままでいいのは
       「濃い帯の上の主ボタン」と「ヒーローに重なったナビの CTA」の2つだけ。
       @media print の中は紙の話なので数えない（紙は白が正しい） */
    const screenCss = css.replace(/\/\*[\s\S]*?\*\//g, '')
        .replace(/@media print\s*\{[\s\S]*$/, '');
    const whites = (screenCss.match(/background:\s*#fff\b/g) || []).length;
    check('直書きの白い地は2か所だけ', whites === 2, `${whites} か所`);

    /* --ink を背景に敷いた上に白い文字を置くと、白地に白になる */
    const onInkWhite = /background:\s*var\(--ink\);\s*color:\s*#fff/.test(css);
    check('--ink の上に白い文字を置いていない', !onInkWhite);

    /* スマホのブラウザが上下に敷く色。地と違うと、スクロールの上下端に
       別の色の帯が出て「読み込みに失敗した」ように見える */
    const PUB = ['index.html', 'pricing.html', 'works.html', 'about.html', 'privacy.html', 'copyright.html', 'quality.html',
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
    const PUB = ['index.html', 'pricing.html', 'works.html', 'about.html', 'privacy.html', 'copyright.html', 'quality.html',
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
    const PUBLIC = ['index.html', 'pricing.html', 'works.html', 'about.html', 'privacy.html', 'copyright.html', 'quality.html',
        'company-video.html', 'recruit-video.html', 'service-video.html', 'ad-video.html',
        'sns-video.html', 'exhibition-video.html', 'internal-video.html',
        'animation-video.html', 'music-video.html'];
    const INTERNAL = ['funnel.html'];
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

    /* ---- ランドマークとタグの釣り合い（2026-09-26） ----
       index.html だけ <main> が無く、余分な div の閉じタグが1つ宙に浮いていた。
       ブラウザは黙って直すので見た目には出ないが、
       ・スクリーンリーダーの「本文へ飛ぶ」が効かない
       ・a11y.mjs が本文を切り出す処理が空振りする（indexOf が -1 を返し、
         index.html だけ「自分自身にリンクしていない」検査が素通りしていた）
       の2つが起きていた */
    for (const f of PUBLIC) {
        const raw = readFileSync(`${ROOT}/${f}`, 'utf8');
        const h = raw.replace(/<!--[\s\S]*?-->/g, '');
        check(`${f} に <main> がある`, /<main[\s>]/.test(h) && /<\/main>/.test(h));
        const body = h.slice(h.indexOf('<body'), h.indexOf('</body>'))
            .replace(/<script[\s\S]*?<\/script>/g, '');
        for (const t of ['div', 'section', 'main', 'header', 'footer', 'ul', 'li']) {
            const o = (body.match(new RegExp(`<${t}[\\s>]`, 'g')) || []).length;
            const c = (body.match(new RegExp(`</${t}>`, 'g')) || []).length;
            if (o !== c) check(`${f} の <${t}> が釣り合っている`, false, `開 ${o} / 閉 ${c}`);
        }
        check(`${f} のタグが釣り合っている`, true);
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
                        === `¥${listPrice(t, S[m[1]]).toLocaleString('ja-JP')}`);
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
                            === `¥${listPrice(t, S[m[1]]).toLocaleString('ja-JP')}`);
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

/* ---- 退職時の書面を引用していない ----
   2026-11-23：もとはロードマップ（社内用）の検査の中で、index.html と
   ロードマップの本文をまとめて見ていた。ロードマップはリポジトリの外へ
   移したので、公開ページ（index.html）のぶんだけ残す。
   社名そのものは、この検査に書くと検査ファイルが公開リポジトリに残るので書かない */
check('退職時の書面を引用していない',
    !/誓約いたします|誓約致します|第１条|第4条（引き抜き/.test(idx));

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
    /* 2026-10-05：本人から「2周目の最後で止まる」。Chromium でも WebKit でも
       45秒・3周まわして再現しなかったので、原因を特定せず【止まったら戻す】側で
       保証することにした。画面に映っているのに止まっている状態を作らない。
       ⚠️ この3つの戻し道を消すと、iPhone で止まったまま復帰しなくなる。 */
    await v.evaluate((e) => e.pause());
    await page.waitForTimeout(700);
    check('映っているのに止まったら、再生に戻る',
        await v.evaluate((e) => !e.paused),
        JSON.stringify(await v.evaluate((e) => ({ paused: e.paused, t: +e.currentTime.toFixed(2) }))));
    /* loop が効かず末尾で ended になった場合も先頭へ戻す */
    await v.evaluate((e) => { e.currentTime = Math.max(0, e.duration - 0.15); });
    await page.waitForTimeout(1800);
    check('末尾まで行っても先頭から流し直す',
        await v.evaluate((e) => !e.paused && e.currentTime < 2),
        JSON.stringify(await v.evaluate((e) => ({ paused: e.paused, t: +e.currentTime.toFixed(2) }))));
    /* 2026-10-05：iPhone の本命の故障は【paused が false のまま時間だけ止まる】形。
       iOS がページを suspend すると m_pausedInternal が立ち、復帰時に下りないことが
       ある。このとき pause も ended も発火せず play() も拒否されないので、
       paused を見る保険は1つも引っかからない（実際それで2度直し損ねた）。
       見回りは currentTime が進んだかだけを見て、効かなければ要素ごと作り直す。
       ⚠️ 上の「止まったら再生に戻る」検査（paused で止まる種類）は【消さないこと】。
       故障の型が2つあるので、両方を別々に検査する。 */
    {
        const sp = await open(browser, { page: 'index.html' });
        await sp.waitForTimeout(2200);
        await sp.evaluate(() => {
            const e = document.getElementById('hero-video');
            e.__orig = true;
            Object.defineProperty(e, 'currentTime', { get: () => 5, set: () => {}, configurable: true });
            Object.defineProperty(e, 'paused', { get: () => false, configurable: true });
        });
        await sp.waitForTimeout(6500);
        const rebuilt = await sp.evaluate(() => !document.getElementById('hero-video').__orig);
        check('時間が止まったら（paused が false でも）要素ごと作り直して復帰する',
            rebuilt, rebuilt ? '作り直した' : '作り直していない');
        await sp.close();
    }
    /* 焼き直すたびに確かめる。-level を指定し忘れると x264 が 5.0 を選び、
       古い iPhone（4.2まで）で黙って再生されなくなる */
    check('source の type にコーデックまで書いてある',
        /type="video\/webm; codecs=vp9"/.test(idx) && /type="video\/mp4; codecs=avc1\./.test(idx));

    /* スマホでは映像を横幅に合わせ、空いた上下を【同じ映像のぼかし】で埋める。
       16:9 を縦長画面に cover で敷くと横の26%しか見えず、被写体が分からなかった。
       ⚠️ ぼかしは静止画ではなく canvas への描き写し。静止画にすると10カットのうち
       9カットで色が合わない。本当に動いているかは描いた枚数が増えることで確かめる
       （枚数を数えずに作ったとき、描けているつもりで一度も更新されていなかった）。 */
    {
        const sp = await open(browser, { page: 'index.html', width: 390, height: 844, mobile: true });
        await sp.waitForTimeout(1500);
        const fit = await sp.locator('#hero-video').evaluate((e) => getComputedStyle(e).objectFit);
        check('スマホでは映像を横幅に合わせる', fit === 'contain', fit);
        const shown = await sp.locator('.hero-blur').evaluate((e) => getComputedStyle(e).display);
        check('スマホでは空いた上下をぼかしで埋める', shown === 'block', shown);
        /* 映像がぼかしより前に描かれること（どちらも重なり順の指定が無いと canvas が上に来る） */
        const order = await sp.evaluate(() => {
            const v = getComputedStyle(document.querySelector('.hero-video'));
            return { pos: v.position, z: v.zIndex };
        });
        check('映像がぼかしより前に出る', order.pos !== 'static' && order.z !== 'auto', JSON.stringify(order));
        /* ぼかしを描いた枚数と、本編が実際に映したコマ数を同じ2秒で数える */
        const count = () => sp.evaluate(() => {
            const q = document.getElementById('hero-video').getVideoPlaybackQuality();
            return { blur: Number(document.querySelector('.hero-blur').dataset.frames || 0),
                     shown: q.totalVideoFrames - q.droppedVideoFrames };
        });
        const a = await count();
        await sp.waitForTimeout(2000);
        const b2 = await count();
        check('ぼかしが本編と連動して描き変わる', b2.blur > a.blur, `${a.blur} → ${b2.blur} 枚`);
        /* 2026-10-05：120ms の固定間隔（8fps）だと、40x23 を画面幅まで引き伸ばした
           ぼかしが段差として明滅して見えた（本人の指摘）。映像のコマに1対1で
           合わせる（requestVideoFrameCallback）ことで段差を無くしてある。
           ⚠️ 固定間隔のタイマーに戻すとチラつきが再発する。
           2026-11-23：前は「2秒で36枚（18fps）以上」と絶対値で見ていたが、
           全スイートを通しで回すとブラウザが混んで映像そのものが12〜15fpsしか
           映らず、毎回ここだけ落ちていた（単独なら21〜22fps で通る）。
           本編が映したコマ数に対する割合で見る。タイマーに戻すと 8/24 ≒ 0.33 になるので
           0.75 を割れば捕まる。 */
        const rate = (b2.blur - a.blur) / Math.max(1, b2.shown - a.shown);
        check('ぼかしが映像のコマに追従している（本編のコマ数の75%以上）', rate >= 0.75,
            `ぼかし ${b2.blur - a.blur} 枚 / 本編 ${b2.shown - a.shown} コマ（${(rate * 100).toFixed(0)}%）`);
        /* 枚数が合っていても、別のコマ（遅れたコマや、作り直す前の古い要素）を
           描いていたら色がずれる。次のコマが出た瞬間に、本編を同じ 40x23 に
           縮めたものとぼかしの色を比べる（0〜255 の平均差。一致すれば 0） */
        const diff = () => sp.evaluate(() => new Promise((res) => {
            const v = document.getElementById('hero-video'), bg = document.querySelector('.hero-blur');
            /* 本編が止まって次のコマが来ないと永遠に待つので、3秒で「不一致」扱いにする */
            setTimeout(() => res(999), 3000);
            v.requestVideoFrameCallback(() => {
                const c = document.createElement('canvas'); c.width = bg.width; c.height = bg.height;
                const g = c.getContext('2d'); g.drawImage(v, 0, 0, c.width, c.height);
                const A = bg.getContext('2d').getImageData(0, 0, c.width, c.height).data;
                const B = g.getImageData(0, 0, c.width, c.height).data;
                let d = 0;
                for (let i = 0; i < A.length; i += 4) {
                    d += Math.abs(A[i] - B[i]) + Math.abs(A[i + 1] - B[i + 1]) + Math.abs(A[i + 2] - B[i + 2]);
                }
                res(d / (A.length / 4) / 3);
            });
        }));
        const d1 = [];
        for (let i = 0; i < 3; i += 1) { d1.push(await diff()); await sp.waitForTimeout(700); }
        check('ぼかしは本編と同じコマを描いている', Math.max(...d1) < 4,
            d1.map((d) => d.toFixed(1)).join(' / '));
        /* 時間が止まって要素ごと作り直したあとも、新しい要素のコマを描き続けること。
           古い要素を握ったままだと、手前は動くのに背景だけ止まる */
        await sp.evaluate(() => {
            const e = document.getElementById('hero-video');
            e.__orig = true;
            Object.defineProperty(e, 'currentTime', { get: () => 5, set: () => {}, configurable: true });
            Object.defineProperty(e, 'paused', { get: () => false, configurable: true });
        });
        await sp.waitForTimeout(6500);
        const rebuiltM = await sp.evaluate(() => !document.getElementById('hero-video').__orig);
        check('スマホでも時間が止まったら要素ごと作り直す', rebuiltM, rebuiltM ? '作り直した' : '作り直していない');
        if (rebuiltM) {
            await sp.waitForTimeout(1500);
            const d2 = [];
            for (let i = 0; i < 3; i += 1) { d2.push(await diff()); await sp.waitForTimeout(700); }
            check('作り直したあとも、ぼかしは新しい本編と同じコマを描いている', Math.max(...d2) < 4,
                d2.map((d) => d.toFixed(1)).join(' / '));
        }
        await sp.close();
    }
    /* PC では画面いっぱいに敷く（横長なので切り取りが浅い） */
    check('PC では映像を画面いっぱいに敷く',
        await v.evaluate((e) => getComputedStyle(e).objectFit) === 'cover');

    /* 「動きを減らす」設定のときは再生しない（ポスターのまま止める） */
    {
        const still = await open(browser, { page: 'index.html' });
        await still.emulateMedia({ reducedMotion: 'reduce' });
        await still.reload({ waitUntil: 'domcontentloaded' });
        await still.waitForTimeout(900);
        check('動きを減らす設定では再生しない',
            await still.locator('#hero-video').evaluate((e) => e.paused));
        /* 動かさない人には、最初から見出しを出しておく（スクロールで出す演出をしない） */
        check('動きを減らす設定では、開いた直後から見出しが見える',
            Number(await still.locator('.hero h1').evaluate((e) => getComputedStyle(e).opacity)) === 1);
        /* ⚠️ 2026-10-20：ここで <source> ごと消していたため、本人が見たいと思っても
           二度と再生できなかった。自動で流さないことと、流せないことは別物。
           指定を残したまま止め、本人が押せる出口を1つ用意する */
        check('動きを減らす設定でも、映像の指定は消さない（本人が流せる）',
            await still.locator('#hero-video source').count() === 2);
        check('動きを減らす設定では、再生ボタンが出ている',
            await still.locator('.hero-play').isVisible());
        check('再生ボタンを押せば、動きを減らす設定でも再生が始まる', await (async () => {
            await still.locator('.hero-play').click();
            await still.waitForTimeout(1200);
            return await still.locator('#hero-video').evaluate((e) => !e.paused);
        })());
        await still.close();
    }
}

/* ---- スマホで「撮影しない理由」の区間が見切れない（2026-09-30） ----
   中身が約700px あり、画面に留めると2段のヘッダーの下に見出しの上が隠れていた
   （iPhone の Safari 390×664 の実機で報告）。スマホでは留めずに流す */
{
    for (const [w, h] of [[390, 664], [375, 560], [430, 740]]) {
        const pg = await open(browser, { page: 'index.html', width: w, height: h, mobile: true });
        const n = await pg.locator('.stage-pin').count();
        for (let i = 0; i < n; i++) {
            const st = await pg.locator('.stage-pin').nth(i).evaluate((e) => getComputedStyle(e).position);
            check(`${w}×${h}：撮影しない理由の区間${i + 1}を画面に留めていない`, st === 'static', st);
            /* 見出しまでスクロールしたとき、ヘッダーに隠れず、中身が全部見えている */
            /* 区間の頭に移ったとき（メニューから飛んだときと同じ。scroll-margin でヘッダーの下に止まる） */
            await pg.locator('.stage').nth(i).evaluate((e) => e.scrollIntoView({ block: 'start', behavior: 'instant' }));
            await pg.waitForTimeout(250);
            const r = await pg.evaluate((i) => {
                const nav = document.getElementById('nav').getBoundingClientRect().bottom;
                const h2 = document.querySelectorAll('.stage-copy .headline')[i].getBoundingClientRect();
                const op = Number(getComputedStyle(document.querySelectorAll('.stage-copy')[i]).opacity);
                return { nav: Math.round(nav), top: Math.round(h2.top), op };
            }, i);
            check(`${w}×${h}：区間${i + 1}の見出しがヘッダーの下に隠れない`, r.top >= r.nav, JSON.stringify(r));
            check(`${w}×${h}：区間${i + 1}の文字が最初から見えている`, r.op === 1, String(r.op));
        }
        await pg.close();
    }
}

/* ---- 札（出演者 0人／撮影日 0日）が本文に重ならない（2026-10-20） ----
   1000px 以下では .stack を height:132px の枠にして、その中へ札を絶対配置で
   中央寄せしていた。10-09 に札の「出演者」を 0.7rem → 1.65rem にしたとき
   札は 242px に伸びたが、枠は 132px のままだったので 110px が外へ出て、
   箇条書きの最終行に 10px 重なった（本人から「被ってる」の報告）。
   ⚠️ 縦の重なりだけで判定しないこと。PC は2段組で、縦だけ見ると左右の
      別々の列どうしが「重なっている」ことになる（実際に誤検知した）。
      矩形として交わっているかで見る。
   ⚠️ 札の文字を大きくするときは、枠の高さを決め打ちに戻さないこと。 */
{
    for (const w of [320, 375, 390, 430, 600, 820, 960, 1000, 1280, 1600]) {
        const pg = await open(browser, { page: 'index.html', width: w, height: 900, mobile: w < 700 });
        const hits = await pg.evaluate(() => [...document.querySelectorAll('.stack')].map((st) => {
            const m = st.querySelector('.stage-mark').getBoundingClientRect();
            let worst = 0;
            for (const el of st.closest('.stage-grid')
                .querySelectorAll('.stage-copy li, .stage-copy p, .stage-copy h2')) {
                const r = el.getBoundingClientRect();
                const ox = Math.min(m.right, r.right) - Math.max(m.left, r.left);
                const oy = Math.min(m.bottom, r.bottom) - Math.max(m.top, r.top);
                if (ox > 0 && oy > 0) worst = Math.max(worst, Math.round(Math.min(ox, oy)));
            }
            return { n: st.dataset.stack, worst };
        }));
        check(`${w}px：札が本文に重ならない`,
            hits.every((x) => x.worst === 0),
            hits.filter((x) => x.worst).map((x) => `${x.n} ${x.worst}px`).join(' '));
        /* 札そのものが画面から出ていないこと（はみ出すと右に余白がスクロールする） */
        const out = await pg.evaluate(() => [...document.querySelectorAll('.stage-mark')]
            .map((e) => Math.round(e.getBoundingClientRect().right - document.documentElement.clientWidth))
            .filter((n) => n > 0));
        check(`${w}px：札が画面の外へはみ出さない`, out.length === 0, out.join(' '));
        await pg.close();
    }
}

/* ---- 縦型サンプルのプレイヤーが 9:16 のまま、スマホでは幅を使う（2026-10-20） ----
   ⚠️ ここは「比率」と「幅の使い方」を必ず両方見ること。片方だけだと直したつもりで壊れる。
      ・比率だけ見る → 240px の小さい箱に入れたままでも通る（元の不具合）
      ・幅だけ見る → max-height で高さを止めて幅100%にすると通ってしまうが、
        縦横の両方が決まった時点で aspect-ratio が無視され、箱の比率が
        0.70〜1.05 に崩れて中で黒帯が出る（実際にこれを書いて踏んだ）
   直し方は「高さの上限から幅を逆算して max-width に入れる」。幅だけを縛る。 */
{
    for (const [page, w, h] of [
        ['sns-video.html', 390, 844], ['sns-video.html', 375, 667],
        ['sns-video.html', 430, 932], ['works.html', 390, 844],
        ['works.html', 320, 568], ['sns-video.html', 1280, 900]]) {
        const pg = await open(browser, { page, width: w, height: h, mobile: w < 700 });
        const r = await pg.evaluate(() => [...document.querySelectorAll('.sample-video.is-vertical')]
            .map((v) => {
                const box = v.closest('figure').parentElement;
                return {
                    ratio: Number((v.clientWidth / v.clientHeight).toFixed(3)),
                    share: Number((v.clientWidth / box.clientWidth).toFixed(2)),
                    tall: Math.round(v.clientHeight),
                };
            }));
        check(`${page} ${w}px：縦型プレイヤーの箱が 9:16 のまま`,
            r.length > 0 && r.every((x) => Math.abs(x.ratio - 0.5625) < 0.02),
            JSON.stringify(r.map((x) => x.ratio)));
        /* スマホでは、入れ物の6割以上を使う（240pxの箱に戻ったら落ちる） */
        if (w < 700) {
            check(`${page} ${w}px：スマホでは幅を使っている`,
                r.every((x) => x.share >= 0.6), JSON.stringify(r.map((x) => x.share)));
            /* ただし画面からはみ出すほど高くしない（ヘッダーを引いた残りに収める） */
            check(`${page} ${w}px：縦型でも画面の高さに収まる`,
                r.every((x) => x.tall <= h * 0.75), JSON.stringify(r.map((x) => x.tall)));
        }
        await pg.close();
    }
}

/* ---- 料金表と計算機に、出せる人数を出す（2026-09-30） ----
   ジャンルのページの表には前から「梅（人物なし）」とあったが、トップと料金ページの表、
   計算機の段の選択肢には「標準／上／特上」しかなく、何が違うのか人数で読めなかった */
{
    for (const f of ['index.html', 'pricing.html']) {
        const h = readFileSync(`${ROOT}/${f}`, 'utf8');
        const head = (h.match(/<thead><tr><th scope="col">尺(?:（1本）)?<\/th>([\s\S]*?)<\/tr><\/thead>/) || [])[1] || '';
        check(`${f} の料金表の見出しに人数がある`, /人物なし/.test(head) && /2人まで/.test(head) && /3人まで/.test(head), head.replace(/<[^>]+>/g, ' ').trim());
    }
    const pg = await open(browser, { page: 'pricing.html' });
    const opts = await pg.locator('#calc-tier .calc-opt').allInnerTexts();
    check('計算機の段の選択肢に人数がある',
        /人物なし/.test(opts[0] || '') && /2人まで/.test(opts[1] || '') && /3人まで/.test(opts[2] || ''), opts.join(' / ').replace(/\n/g, ' '));
    await pg.close();
}

/* ---- スマホで、ヒーローの文字の塊が画面に収まる（2026-09-30） ----
   画面に留めているので、はみ出すとボタンが下で切れ、見出しがヘッダーの下に潜る
   （375×560 で 631px の塊に対して使えるのは 457px だった） */
{
    for (const [w, h] of [[375, 560], [390, 664], [430, 740]]) {
        const pg = await open(browser, { page: 'index.html', width: w, height: h, mobile: true });
        const span = await pg.evaluate(() => document.getElementById('top').offsetHeight - innerHeight);
        await pg.evaluate((y) => window.scrollTo({ top: y, behavior: 'instant' }), span);
        await pg.waitForTimeout(350);
        const r = await pg.evaluate(() => {
            const nav = document.getElementById('nav').getBoundingClientRect().bottom;
            const h1 = document.querySelector('.hero h1').getBoundingClientRect();
            const act = document.querySelector('.hero-actions').getBoundingClientRect();
            return { nav: Math.round(nav), h1: Math.round(h1.top), act: Math.round(act.bottom), vh: innerHeight };
        });
        check(`${w}×${h}：ヒーローの見出しがヘッダーの下に潜らない`, r.h1 >= r.nav, JSON.stringify(r));
        check(`${w}×${h}：ヒーローのボタンが画面の下で切れない`, r.act <= r.vh, JSON.stringify(r));
        await pg.close();
    }
}

/* ---- 背の低い画面（スマホの横向き）ではヒーローを留めない（2026-09-30） ----
   高さ 390px では見出し・説明・ボタンが収まらず、ボタンが切れていた。
   留めずに最初から文字を出す。あわせて、社内ページの表が小さい iPhone で横にはみ出していた */
{
    for (const [w, h] of [[664, 390], [844, 390]]) {
        const pg = await open(browser, { page: 'index.html', width: w, height: h, mobile: true });
        const r = await pg.evaluate(() => ({
            pos: getComputedStyle(document.querySelector('.hero-pin')).position,
            op: Number(getComputedStyle(document.querySelector('.hero h1')).opacity),
        }));
        check(`${w}×${h}：ヒーローを留めていない`, r.pos !== 'sticky', r.pos);
        check(`${w}×${h}：開いた直後から見出しが見える`, r.op === 1, String(r.op));
        await pg.close();
    }
    for (const f of ['funnel.html', ...PUBLIC_PAGES]) {
        const pg = await open(browser, { page: f, width: 375, height: 560, mobile: true });
        const sw = await pg.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
        check(`375×560：${f} が横にはみ出さない`, sw <= 1, `${sw}px`);
        await pg.close();
    }
}

/* ---- ヒーロー：開いた直後は映像だけ、スクロールで見出し（2026-09-29） ----
   「ヒーローは動画だけ見せて、スクロールしたら撮影しない、映像制作って出るようにして」。
   .hero を画面2枚ぶんにして中を留め、--hero-r（0→1）で映像を落として文字を出す */
{
    const op = (pg, sel) => pg.locator(sel).first().evaluate((e) => Number(getComputedStyle(e).opacity));
    for (const [label, opts] of [['PC', {}], ['スマホ', { width: 390, height: 844, mobile: true }]]) {
        const pg = await open(browser, { page: 'index.html', ...opts });
        await pg.evaluate(() => window.scrollTo({ top: 0, behavior: 'instant' }));
        await pg.waitForTimeout(400);
        check(`${label}：開いた直後は見出しを出していない`, await op(pg, '.hero h1') === 0, String(await op(pg, '.hero h1')));
        check(`${label}：開いた直後は映像を原色で見せている`, await op(pg, '.hero-media') === 1, String(await op(pg, '.hero-media')));
        check(`${label}：開いた直後に映像が流れている`,
            await pg.locator('#hero-video').evaluate((e) => !e.paused && e.currentSrc !== ''),
            JSON.stringify(await pg.locator('#hero-video').evaluate((e) => ({ paused: e.paused, src: e.currentSrc }))));
        check(`${label}：スクロールを促す表示がある`, await op(pg, '.scroll-hint') > 0.9);
        const span = await pg.evaluate(() => document.getElementById('top').offsetHeight - innerHeight);
        check(`${label}：見出しを出すためのスクロールの区間がある`, span > 0, String(span));
        await pg.evaluate((y) => window.scrollTo({ top: y, behavior: 'instant' }), Math.round(span * 0.7));
        await pg.waitForTimeout(400);
        check(`${label}：スクロールすると見出しが出る`, await op(pg, '.hero h1') === 1);
        check(`${label}：スクロールすると説明とボタンも出る`,
            await op(pg, '.hero-lead') === 1 && await op(pg, '.hero-actions') === 1);
        check(`${label}：見出しが出たら映像は質感まで落ちる`, await op(pg, '.hero-media') < 0.2,
            String(await op(pg, '.hero-media')));
        check(`${label}：見出しが画面の中にある`,
            await pg.locator('.hero h1').evaluate((e) => { const r = e.getBoundingClientRect(); return r.top >= 0 && r.bottom <= innerHeight; }));
        await pg.close();
    }
    /* キーボードで相談ボタンに入ったら、スクロール前でも見えること */
    {
        const pg = await open(browser, { page: 'index.html' });
        await pg.locator('.hero-actions a').first().focus();
        check('スクロール前でも、キーボードで入ったボタンは見える', await op(pg, '.hero-actions') === 1);
        await pg.close();
    }
    /* JS が動かないときは最初から見出しが読める（隠したまま出てこない、を防ぐ） */
    {
        const ctx = await browser.newContext({ javaScriptEnabled: false, viewport: { width: 1280, height: 900 } });
        const pg = await ctx.newPage();
        await pg.goto(`${BASE}/index.html`, { waitUntil: 'domcontentloaded' });
        check('JS が動かないときは最初から見出しが見える', await op(pg, '.hero h1') === 1);
        await ctx.close();
    }
}

/* ---- 時間単価の位置づけ（9/21）----
   ¥23,000 は価格÷実測工数の結果で、目標として決めた数字ではない。
   ここを取り違えると「時給を下げれば値下げできる」という循環した話になる。
   README に、その旨と代わりの判断軸を残してある
   （2026-11-23：record.html 側の検査はページと一緒に外した） */
{
    const readme2 = readFileSync(`${ROOT}/README.md`, 'utf8');
    check('README にも同じことが書いてある',
        /目標ではなく、価格 ÷ 実測工数の結果/.test(readme2)
        && /循環していて、値下げの根拠にならない/.test(readme2));
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
       営業文面.md 側には移した旨のポインタだけを残し、数字は二重に持たない。
       2026-11-23：record.html はリポジトリの外へ移したので、record 側の突き合わせは外した */
    {
        check('営業文面に数字を二重に持っていない',
            !/¥185,725/.test(eigyo) && !/23,143\/h/.test(eigyo));

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
        mitsu.includes(`¥〔${listPrice(TIERS[1], 60).toLocaleString('ja-JP')}〕（税込`),
        String(listPrice(TIERS[1], 60)));
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
    check('料金の単位がサイトと揃っている(企画・構成費と追加本数)',
        mitsu.includes(`¥${PRICE.base.toLocaleString('en-US')}`) && mitsu.includes(`¥${PRICE.perExtra.toLocaleString('en-US')}`));
    check('契約書にAI特有の免責がある',
        /著作権による保護を\s*受けない場合がある/.test(keiyaku) && /意図しない類似/.test(keiyaku));
    check('契約書に権利の帰属がある',
        /支払完了をもって/.test(keiyaku) && /制限なく使用できる/.test(keiyaku));
    /* サイト（権利ページ・プライバシーポリシー）は「事前に個別の許諾」。
       契約書が「載せられる、嫌なら申し出る」だった食い違いを、許諾を取る側に揃えた（10/3） */
    check('実績掲載は事前の承諾を取る形になっている',
        /事前に甲の書面/.test(keiyaku) && !/掲載できる/.test(keiyaku) && !/掲載を望まない場合/.test(keiyaku));
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
    /* 9/24：末尾に置いたので、消しても前の条番号が動かない。
       10/03：手で消す運用をやめ、make_doc.py の --music で切り替える形にした。
       条文の実体は _書式/_楽曲特約.html にあり、契約書本体をコピーした
       「MV用の別書式」は作らない（写しが増えると食い違う。実際に第6条の
       「意図しない類似」がHTMLに無く、お客様に一度も届いていなかった）。
       守りたいのは【MV以外では付かないことが書かれている】ことなので、
       文言ではなく切り替えの仕組みが書かれているかを見る */
    check('楽曲の特約がMV以外では付かないと書いてある',
        /条件付き/.test(keiyaku)
        && /--music/.test(keiyaku)
        && /前の条番号は動かない/.test(keiyaku));
    check('楽曲の特約の実体が別ファイルだと書いてある',
        /_楽曲特約\.html/.test(keiyaku) && /別書式.{0,20}作らない/.test(keiyaku));
    /* 10/04：「容姿が実物と完全に一致することは保証しない」を外した。
       実在の人物を AI で似せて生成するのをやめ、実在の出演者が登場するのは
       甲が実写素材を提供した場合だけにしたので、この警告は不要になった
       （copyright.html の「実在の人物を AI で生成しません」と揃えた）。
       守りたいのは【出演者の扱いが書いてあること】なので、そちらで見る */
    check('楽曲の特約に権利・差替え・出演者・クレジットが入っている',
        ['著作隣接権', '差し替わった場合', '実在の出演者', 'クレジット']
            .every((w) => keiyaku.includes(w)));
    /* 2026-10-07：「作成しない」は結果の約束で、守れないので
       「似せることを指示して生成しない」に直した。生成モデルは実在の人物の
       画像で学習しているので、指示しなくても偶然似る。似ていないことを
       確かめる方法も無い（全人類と照合できない）。
       ⚠️ 「作成しない」に戻さないこと。discord-groupchat/test_routing.py 側にも
       同じ守り手がある（2026-10-13：main のこの検査だけ古い文言のままだった）。 */
    check('楽曲の特約でもAIで実在の人に似せない',
        /実在の人物に似せることを指示して映像を生成しない/.test(keiyaku)
        && /甲が実写の素材/.test(keiyaku));
    /* 条番号を繰り下げたので、重複や飛びが出ていないこと。
       10/03：枝番（第6条の2・第6条の3）を足したら、ここが「飛び」として
       落ちた。枝番は日本の法令で標準の書き方で、あとから条を足しても
       後続の番号が動かないためのもの。本体と枝番を分けて数える。 */
    const artAll = (keiyaku.match(/^### 第(\d+)条(の(\d+))?/gm) || []);
    const artBase = artAll.filter((x) => !/の\d/.test(x))
        .map((x) => Number(x.match(/\d+/)[0]));
    check('契約書の条番号が第1条から連番（本体）',
        artBase.every((n, i) => n === i + 1), artAll.join(','));
    /* 枝番は、親の条が在り、2から順に続いていること（第6条の3だけ在る、は誤り） */
    const branches = {};
    artAll.filter((x) => /の\d/.test(x)).forEach((x) => {
        const [, a, , b] = x.match(/第(\d+)条(の(\d+))?/);
        (branches[a] = branches[a] || []).push(Number(b));
    });
    check('枝番は親の条が在って2から順に続く',
        Object.entries(branches).every(([a, list]) =>
            artBase.includes(Number(a)) && list.every((n, i) => n === i + 2)),
        JSON.stringify(branches));
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
                 'funnel.html']) {
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
/* ジャンル一覧は「容器の地を 1px の隙間から覗かせて罫線にする」作りなので、
   カードの地が無い所には罫線の色が【面として】出る。実際に2か所出ていた
   （2026-10-06 本人の指摘）：説明が1行の項目の下に出た帯と、9個を2列に
   並べたときの10個目の空セル。どの幅でも面が出ないことを見る。
   ⚠️ 項目を9個から増減すると割り切れ方が崩れてここで落ちる。それが狙い。 */
for (const w of [390, 800, 1280]) {
    const pg = await open(browser, { page: 'index.html', width: w });
    await pg.waitForTimeout(700);
    const r = await pg.evaluate(() => {
        const ul = document.querySelector('.genre-index');
        if (!ul) return null;
        const li = [...ul.children];
        const gaps = li.map((x) => {
            const a = x.querySelector('a');
            return a ? Math.round(x.getBoundingClientRect().height - a.getBoundingClientRect().height) : 999;
        });
        const box = ul.getBoundingClientRect();
        const bw = parseFloat(getComputedStyle(ul).borderRightWidth) || 0;
        const last = li[li.length - 1].getBoundingClientRect();
        return { n: li.length, gap: Math.max(...gaps), tail: Math.round(box.right - bw - last.right) };
    });
    check(`ジャンル一覧 ${w}px：カードがセルを埋めている（罫線の色が帯で出ない）`,
        r && r.gap === 0, r && `すき間 ${r.gap}px`);
    check(`ジャンル一覧 ${w}px：最後の行に空セルが残らない`,
        r && Math.abs(r.tail) <= 2, r && `右端のずれ ${r.tail}px（${r.n}項目）`);
    await pg.close();
}

/* CSS・JS の参照に、中身から出した版（?v=ハッシュ）が打ってあること。
   GitHub Pages は assets に cache-control: max-age=600 を付けるので、
   版が無いとCSSを直しても最大10分は古いものが使われる。実際に
   「3列に直したのに2列のまま」という報告が出た（2026-10-06）。
   ⚠️ CSS や JS を直したら python3 tools/stamp_assets.py を実行すること。
   忘れるとここで落ちる。それが狙い。 */
{
    const hash = (f) => createHash('sha1').update(readFileSync(`${ROOT}/${f}`)).digest('hex').slice(0, 8);
    const want = new Map();
    /* CSS と、HTMLが直接参照している映像・ポスター。
       ⚠️ JS には打たない（生成スクリプトとテスト6か所が壊れる。実際に落ちた）。
       2026-10-06：動画に版が無かったため、30秒→60秒に差し替えても
       ブラウザが古い30秒版を使い続けた。CSSだけ塞いでも足りなかった。 */
    for (const a of ['assets/site.css', 'assets/works/hero-reel.mp4',
                     'assets/works/hero-reel.webm', 'assets/works/hero-reel.jpg']) {
        if (existsSync(`${ROOT}/${a}`)) want.set(a, hash(a));
    }
    const bad = [];
    let seen = 0;
    for (const f of readdirSync(ROOT).filter((x) => x.endsWith('.html'))) {
        const html = readFileSync(`${ROOT}/${f}`, 'utf8');
        for (const m of html.matchAll(/(?:href|src|poster)="(assets\/[\w./-]+\.(?:css|mp4|webm|jpg))(?:\?v=([0-9a-f]+))?"/g)) {
            if (!want.has(m[1])) continue;
            seen += 1;
            if (m[2] !== want.get(m[1])) bad.push(`${f}: ${m[1]} → ${m[2] || '版なし'}`);
        }
    }
    check('CSS・JS の参照に中身どおりの版が打ってある（古い版を掴ませない）',
        seen > 0 && bad.length === 0,
        bad.length ? `${bad.length}件ずれ: ${bad.slice(0, 3).join(' / ')}` : `${seen}件を確認`);
}

await browser.close();

report();
