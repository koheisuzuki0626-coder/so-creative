/* 料金シミュレーター。
   「お客様にどの組み合わせを選ばせても採算が崩れない」ことの担保がここ。
   金額・工数のどれかを動かしたら必ずこれを通すこと。 */
import { check, report, PW, open, pick, setLens, splitSec, setNar, setNarAll, narOf, matsuToNone, priceModes, hoursModes, narFee, reachableNar, reachable, maxPieces, PRICE, HOURS, TIERS, LENGTHS, price, hours, leadWeeks, RATE, MEASURED, REVISION_HOURS, CREDITS_PER_SEC } from './lib.mjs';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
const ROOT = fileURLToPath(new URL('..', import.meta.url)).replace(/\/$/, '');
const HOURS_NARRATION = () => HOURS.narration;
const pwmod = (await import(PW)).default;

const browser = await pwmod.chromium.launch();
const page = await open(browser, {});
await page.locator('#plans').scrollIntoViewIfNeeded();
await page.waitForTimeout(700);

/* ---- 選択肢の構成 ---- */
check('仕上げの段が3つ', (await page.locator('#calc-tier .calc-opt').count()) === 3);
check('段の名前が梅竹松',
    (await page.locator('#calc-tier .calc-opt').allInnerTexts()).join('|') === '梅 標準|竹 上|松 特上');
/* 9/22 から尺は本ごとに選ぶ（select）。1本のときは行が1つだけ出る */
check('本ごとの尺の行が本数ぶん出る', (await page.locator('#calc-len .calc-len-row').count()) === 1);
check('尺が8つ', (await page.locator('#calc-len select[data-kind="len"][data-row="0"] option').count()) === LENGTHS.length);
check('本数が6つ', (await page.locator('#calc-cnt .calc-opt').count()) === 6);
/* 初期は AI。AIは料金に含むので、これが素の状態。
   'none' を初期にすると表示額が差し引き後になり、「AIは込み」と
   言いながら AI を選ぶと上がる見え方になる。
   段を触る前に見る（松を選ぶと human に固定されるため） */
check('初期表示はAIナレーション', (await narOf(page, 0)) === 'ai');
/* 9/22：ナレーションを本ごとの行に入れたので、手順は3つになった */
check('操作の順番を番号で示している',
    (await page.locator('.calc-step').allInnerTexts()).join('') === '123');
/* 段・本数・ナレーションはラジオ（丸が見えることで「選ぶところ」だと分かる）。
   尺だけは select。6本 × 8つの尺を丸で並べると48個になり、画面の大半を占めてしまう */
check('実物のラジオで組んである',
    (await page.locator('.calc input[type="radio"]').count()) === 3 + 6);
check('尺の行に名前がついている（読み上げ用）',
    (await page.locator('#calc-len select[data-kind="len"][data-row="0"]').getAttribute('aria-label')) === '1本目の尺'
    && (await page.locator('#calc-len select[data-kind="nar"][data-row="0"]').getAttribute('aria-label')) === '1本目のナレーション'
    && (await page.locator('#calc-len-name-0').innerText()) === '1本目');

/* ---- 段の説明は客先向けの言葉か ---- */
for (const [t, must, use, rev] of [['ume', '登場人物なし', 'SNS', 2], ['take', '2人まで', '採用', 3], ['matsu', '人物ナレーション込み（1名', '展示会', 3]]) {
    await page.locator(`#calc-tier .calc-opt[data-tier="${t}"]`).click();
    const h = await page.locator('#calc-tier-hint').innerText();
    check(`${t} の中身が納品物の言葉で出る`, h.includes(must) && /納品/.test(h), h.slice(0, 34));
    check(`${t} の向いている用途が出る`, h.includes('向いている用途') && h.includes(use));
    check(`${t} の修正回数が出る（${rev}回）`, h.includes(`修正${rev}回まで`), (h.match(/修正\d回まで/) || [''])[0]);
    /* 4K は売り文句にしない（中身は1080pの引き伸ばしなので）。FAQ にだけ正直に書く */
    check(`${t} は 1080p 納品と書いてある`, /1080p（フルHD）で納品/.test(h));
    check(`${t} の説明に 4K を出していない`, !/4K/.test(h));
    /* 9/22：ナレーションは本ごとに選べる。入れない本ぶんだけ引くことと、
       人物は何本に入れても1名ぶんであることが、段の説明から読めること */
    check(`${t} のナレーションの扱いが出る`, t === 'matsu'
        ? /人物ナレーション込み（1名/.test(h) && /本ごとに選べます/.test(h)
        : /本ごとに選べます。入れない本は1本につき −¥25,000/.test(h)
            && /何本に入れても1名ぶん/.test(h));
}
const plansText = await page.locator('#plans').innerText();
check('生成回数など内部の手順を出していない',
    !/カットにつき|回まで生成|回以上生成/.test(plansText));
/* 実証で使えないと分かったものを売り文句に残していないか */
check('落とした仕様が段の説明に残っていない',
    !/ちらつき|正方形|3形式|2形式|720p|4K/.test(plansText), plansText.slice(0, 40));
check('修正回数が5回に戻っていない', !/5回/.test(plansText));

/* ---- ナレーションの選択（なし／AI音声／人が読む の3択） ---- */
check('ナレーションが3択', (await page.locator('#calc-len select[data-kind="nar"][data-row="0"] option').count()) === 3);
/* AI音声を売るなら、合成音声だと分かる書き方にしておく。
   4エンジン×9声を試して不採用にしたものを、期待値を伏せて売らないため */
check('AIナレーションが合成音声だと分かる書き方になっている',
    /合成音声なので機械の声だと分かる/.test(await page.locator('.calc-why').innerText()));
check('AIナレーションが追加料金なしだと分かる',
    /AIナレーション 追加料金なし/.test(await page.locator('.calc-why').innerText()));
check('使わないと差し引かれることが書いてある',
    /ナレーションは1本ごとに選べます。入れない本は1本につき ¥25,000 を差し引きます/
        .test(await page.locator('.calc-why').innerText()));
await page.locator('#calc-tier .calc-opt[data-tier="matsu"]').click();
/* 9/19 に、松でもナレーションを選べるようにした。以前は human に固定していて、
   人物ナレーションが要らない案件で松を選べなかった。既定は human のまま */
check('松でもナレーションを選べる',
    !(await page.locator('#calc-len select[data-kind="nar"][data-row="0"]').isDisabled())
    && (await narOf(page, 0)) === 'human');
check('松はナレーションが込み（¥0）',
    /人物（松に1名込み）/.test(await page.locator('#calc-nar-dt').innerText())
    && (await page.locator('#calc-narfee').innerText()) === '¥0');
await page.locator('#calc-cnt .calc-opt[data-count="2"]').click();
check('松は本数が増えてもナレーション料は¥0のまま',
    (await page.locator('#calc-narfee').innerText()) === '¥0');
await page.locator('#calc-cnt .calc-opt[data-count="1"]').click();
await page.locator('#calc-tier .calc-opt[data-tier="ume"]').click();
check('梅では3択すべて選べる',
    (await page.locator('#calc-len select[data-kind="nar"][data-row="0"] option').allInnerTexts())
        .join('|') === 'ナレーションなし|AIナレーション|人物ナレーション');
/* AIは料金に含む（¥0）。人物だけ加算される。違いを画面で確かめる */
await setNarAll(page, 'ai');
await page.locator('#calc-cnt .calc-opt[data-count="2"]').click();
check('AIナレーションは追加料金なし（内訳が ¥0）',
    (await page.locator('#calc-narfee').innerText()) === '¥0'
    && /料金に含まれます/.test(await page.locator('#calc-nar-dt').innerText())
    && Number((await page.locator('#calc-total').innerText()).replace(/[^\d]/g, '')) === price(TIERS[0], 60, 2, 'ai')
    && !/〜/.test(await page.locator('#calc-total').innerText()));
/* AIを込みにした以上、使わない案件から同じ額は取らない。
   松は人物ナレーションが込みなので対象外 */
await setNarAll(page, 'none');
/* 9/22：入れない本1本につき引くので、2本なら2本ぶん */
check('ナレーションなしは差し引きが内訳に出る',
    (await page.locator('#calc-narfee').innerText()) === `−¥${(PRICE.noNarration * 2).toLocaleString('ja-JP')}`
    && /差し引き/.test(await page.locator('#calc-nar-dt').innerText())
    && Number((await page.locator('#calc-total').innerText()).replace(/[^\d]/g, '')) === price(TIERS[0], 60, 2, 'none'));
check('差し引きは AI を選ぶより安い（本数ぶん引く）',
    price(TIERS[0], 60, 2, 'none') === price(TIERS[0], 60, 2, 'ai') - PRICE.noNarration * 2);
/* 松の人物ぶんを返す額。¥70,000 をそのまま返すと 15秒×1本で下限を割るので、
   いちばん短い尺でも持つ額（AI -2.5万／なし -5万）にしてある */
check('松をAIに替えると人物ぶんが引かれる',
    price(TIERS[2], 30, 2, 'ai') === price(TIERS[2], 30, 2, 'human') - PRICE.matsuToAi);
/* 松は「人物の手配ぶん」と「入れない本のぶん」の両方が引かれる。
   1本だけのときは 9/19 までと同じ −¥50,000 になる */
check('松でナレーションを使わないとさらに引かれる',
    price(TIERS[2], 30, 1, 'none') === price(TIERS[2], 30, 1, 'human') - matsuToNone()
    && price(TIERS[2], 30, 2, 'none')
        === price(TIERS[2], 30, 2, 'human') - PRICE.matsuToAi - PRICE.noNarration * 2);
{
    /* 引いたあとでも、どの組み合わせも時間単価の下限を割らないこと。
       ここが割ると「松を選ぶほど損」になる */
    const bad = [];
    for (const { sec, n } of reachable()) {
        for (const nar of ['human', 'ai', 'none']) {
            const r = price(TIERS[2], sec, n, nar) / hours(TIERS[2], sec, n, nar);
            if (r < RATE * 0.95) bad.push(`${sec}秒×${n}本/${nar}: ¥${Math.round(r)}`);
        }
    }
    check('松はナレーションを外しても下限を割らない', bad.length === 0, bad.slice(0, 3).join(','));
}
await setNarAll(page, 'ai');
await setNarAll(page, 'human');
check('人物ナレーションは本数で増えず「〜」が付く',
    (await page.locator('#calc-narfee').innerText()) === `¥${PRICE.narrationHuman.toLocaleString('ja-JP')}〜`
    && Number((await page.locator('#calc-total').innerText()).replace(/[^\d]/g, '')) === price(TIERS[0], 60, 2, 'human')
    && /〜/.test(await page.locator('#calc-total').innerText()));
await setNarAll(page, 'none');
await page.locator('#calc-cnt .calc-opt[data-count="1"]').click();


/* ---- 全組み合わせの金額・上限・時間単価 ---- */
const wrong = [], capBad = [], rates = [], leadBad = [];
for (const t of TIERS) {
    await page.locator(`#calc-tier .calc-opt[data-tier="${t.id}"]`).click();
    for (const sec of LENGTHS) {
        /* 本ごとに尺を選ぶ形になったので、合計 sec 秒を n 本に割って入れる。
           1本あたり15秒を下回らない割り方が無い組み合わせは飛ばす */
        for (let n = 1; n <= 6; n += 1) {
            if (await page.locator(`#calc-cnt input[data-count="${n}"]`).isDisabled()) {
                capBad.push(`${t.label}${sec}秒/${n}本 が選べない`);
            }
        }
        const cap = Math.min(6, Math.floor(sec / LENGTHS[0]));
        for (let n = 1; n <= cap; n += 1) {
            await setLens(page, splitSec(sec, n));
            for (const nar of (t.narration ? ['human'] : ['none', 'ai', 'human'])) {
                if (!t.narration) await setNarAll(page, nar);
                const shown = Number((await page.locator('#calc-total').innerText()).replace(/[^\d]/g, ''));
                const want = price(t, sec, n, nar);
                const c = `${t.label}${sec}秒×${n}本/${nar}`;
                if (shown !== want) wrong.push(`${c}: ${shown}≠${want}`);
                rates.push({ c, nar, rate: shown / hours(t, sec, n, nar) });
            }
            if (!t.narration) await setNarAll(page, 'ai');
        }
        await setLens(page, [sec]);
        const lead = await page.locator('#calc-lead-v').innerText();
        const wantLead = `約${leadWeeks(t, sec)}週間`;
        if (lead !== wantLead) leadBad.push(`${t.label}${sec}秒: ${lead}≠${wantLead}`);
    }
}
check('表示金額が計算式と一致する', wrong.length === 0, JSON.stringify(wrong.slice(0, 3)));
check('本数の上限が尺に応じて効く', capBad.length === 0, JSON.stringify(capBad.slice(0, 3)));
check('納期が工数から出た値と一致する', leadBad.length === 0, JSON.stringify(leadBad.slice(0, 3)));

/* かつては「どの組み合わせでも時間単価が一定」を検証していたが、
   段の特典を「人が出るか／声が入るか」に絞ったことで工数の伸びが価格より
   緩くなり、一定にはならなくなった。守るべきはもともと一定であることではなく
   「目標を割らないこと」なので、不変条件をそちらに変えた。 */
const lo = rates.slice().sort((a, b) => a.rate - b.rate)[0];
const hi = rates.slice().sort((a, b) => b.rate - a.rate)[0];
/* 基本料金と本数料金は工数に比例しないので、端の組み合わせで数%ぶれる。
   問題なのは「大きく割ること」なので、下側だけ5%の幅を持たせる */
check(`どの組み合わせでも時間単価が ¥${RATE} の95%を下回らない`, lo.rate >= RATE * 0.95,
    `最低 ${lo.c} ¥${Math.round(lo.rate)}/h（目標比 ${(lo.rate / RATE * 100).toFixed(1)}%） / ${rates.length}通り`);
check('時間単価が現実離れしていない（計算式の壊れ検知）', hi.rate <= RATE * 3,
    `最高 ${hi.c} ¥${Math.round(hi.rate)}/h`);

/* 上位の段ほど儲からない、という並びになっていないか。
   以前これが起きていて（松がいちばん薄い）、特典を組み直す理由になった */
const byTier = TIERS.map((t) => {
    const rs = rates.filter((r) => r.c.startsWith(t.label)).map((r) => r.rate);
    return { label: t.label, avg: rs.reduce((a, b) => a + b, 0) / rs.length };
});
/* 誤差ではなく「実質的に逆転している」ことだけを拾いたいので 2% の幅を持たせる */
check('上の段ほど時間単価が実質的に下がらない',
    byTier.every((x, i) => i === 0 || x.avg >= byTier[i - 1].avg * 0.98),
    byTier.map((x) => `${x.label} ¥${Math.round(x.avg)}`).join(' / '));

/* モデルが実測より短く見積もっていないこと。
   短い側に倒れると納期に遅れる。倍率を下げるなら実測を伴わせる */
for (const m of MEASURED) {
    const t = TIERS.find((x) => x.id === m.tier);
    const model = hours(t, m.sec, 1);
    check(`工数モデルが実測より短くない（${m.label} ${m.sec}秒）`, model >= m.workHours,
        `モデル ${model.toFixed(1)}h / 実測 ${m.workHours}h（${(model / m.workHours).toFixed(1)}倍の余裕）`);
}

/* 逆に、実測から離れて重すぎてもいけない。以前は 3.1倍で、納期が長く出すぎ
   （5分の松で7週）、時間単価の目標 ¥14,900 も見かけ上のものになっていた。
   本編1本の安全率は 1.3〜2.0倍に収める（打合せ・素材待ちのぶん） */
{
    const m = MEASURED[0];
    const ratio = hours(TIERS.find((x) => x.id === m.tier), m.sec, 1) / m.workHours;
    check('工数モデルの安全率が実測の 1.3〜2.0倍', ratio >= 1.3 && ratio <= 2.0, `${ratio.toFixed(2)}倍`);
}

/* クレジット原価は秒単価に対して小さいこと（超えるなら秒単価に原価項を足す） */
check('クレジット原価が梅の秒単価の 10% 未満',
    CREDITS_PER_SEC * 7.7 < TIERS[0].perSec * 0.10, `¥${Math.round(CREDITS_PER_SEC * 7.7)}/秒 vs ¥${TIERS[0].perSec}`);

/* 実測できた唯一の係数。段の差（修正2/3/3回）はこれを根拠にしている */
check('修正1往復の係数が実測と合っている', Math.abs(REVISION_HOURS - 0.62) < 0.05,
    `実測 ${REVISION_HOURS}h / モデル 0.62h`);

/* ---- 納期の形 ---- */
check('15秒は据え置きで2週間', leadWeeks(TIERS[0], 15) === 2 && leadWeeks(TIERS[2], 15) === 2);
check('尺が伸びても納期が跳ねない', leadWeeks(TIERS[0], 300) <= 4, `5分梅 ${leadWeeks(TIERS[0], 300)}週`);
check('納期は尺について単調に増える',
    TIERS.every((t) => LENGTHS.every((s, i) => i === 0 || leadWeeks(t, s) >= leadWeeks(t, LENGTHS[i - 1]))));
check('段が上がると納期も延びるか同じ',
    LENGTHS.every((s) => leadWeeks(TIERS[0], s) <= leadWeeks(TIERS[1], s)
                      && leadWeeks(TIERS[1], s) <= leadWeeks(TIERS[2], s)));
check('ナレーションを足しても納期は延びないか1週だけ',
    LENGTHS.every((s) => leadWeeks(TIERS[0], s, 'human') - leadWeeks(TIERS[0], s, 'none') <= 1));
/* ¥70,000 は大半がナレーターへの外注費なので、「÷1.0h」を自分の時間単価としては使わない。
   工数が 1.0h 増えるぶんで単価が落ちないことだけを、ナレーションありの組み合わせで見る */
for (const mode of ['ai', 'human']) {
    const narRates = rates.filter((r) => r.nar === mode);
    const nlo = narRates.slice().sort((a, b) => a.rate - b.rate)[0];
    check(`${mode} でも時間単価の目標を割らない`, nlo.rate >= RATE * 0.95,
        `最低 ${nlo.c} ¥${Math.round(nlo.rate)}/h / ${narRates.length}通り`);
}
check('ナレーションの工数は1本 1.0h（AI・人で同じ）', HOURS_NARRATION() === 1.0);

/* ---- 段のはしごが逆転していないか ----
   松は「竹＋ナレーション」の上位互換（3人目・ナレ込み・修正は同じ3回）なので、
   松のほうが安くなる組み合わせがあると、高い金を払って下位の仕様を買う選択肢ができる。
   ナレーションを本数課金にする前は 5通りで逆転していた（15秒×1本〜90秒×6本） */
{
    const take = TIERS.find((t) => t.id === 'take');
    const matsu = TIERS.find((t) => t.id === 'matsu');
    const inverted = [];
    for (const sec of LENGTHS) {
        for (let n = 1; n <= 6; n++) {
            if (sec / n < 15) continue;
            if (price(take, sec, n, 'human') > price(matsu, sec, n, 'human')) inverted.push(`${sec}秒×${n}本`);
        }
    }
    /* ナレーションを「1名 ¥70,000〜」にした（2026-09-17）ことで逆転が3件に増えた。
       松の秒単価に溶けているナレーション相当（竹との差 1,750×秒）が
       ¥70,000 に届かない 15秒・30秒だけ。しかも今回は
       **竹＋ナレのほうが時間単価が高い**（＝松が安い）ので、
       以前の「松のほうが時間単価が高いから放置」という理由は成り立たない。
       価格は動かさず、計算機がその場で「松のほうが安い」と出して潰す（下の検査） */
    /* 1本あたり15秒未満は選べないので、この一覧に 15秒×2本 は出てこない
       （2本にすると合計が30秒になる。下の検査は maxPieces で回している） */
    check('竹＋人物が松を上回るのは15秒・30秒だけ',
        inverted.join(',') === '15秒×1本,30秒×1本,30秒×2本', inverted.join(',') || 'なし');
    /* AIは料金に含むので、どの組み合わせでも松を上回らない */
    check('AIナレーションでは逆転しない',
        reachable().every(({ sec, n }) => price(take, sec, n, 'ai') <= price(matsu, sec, n, 'human')));
    check('松は本数が増えてもナレーション料は増えない',
        price(matsu, 30, 2, 'human') - price(matsu, 30, 1, 'human') === PRICE.perExtra,
        `¥${price(matsu, 30, 2, 'human') - price(matsu, 30, 1, 'human')}`);
    /* 松は料金は増えないが工数は増える。秒単価に入っているのは1本ぶんの 1.0h なので、
       2本目のナレーション（原稿・配置）はちゃんと工数に乗る。1.5h + 1.0h */
    check('松は料金は増えないが工数は2本目ぶん増える',
        Math.abs(hours(matsu, 30, 2) - hours(matsu, 30, 1) - 2.5) < 1e-9,
        `${(hours(matsu, 30, 2) - hours(matsu, 30, 1)).toFixed(2)}h`);

    /* 逆転する組み合わせでは、計算機が「松のほうが安い」と言うこと。
       言わないまま出すと、下位の仕様を高く買う選択肢が残る */
    const warnBad = [];
    for (const t of TIERS.filter((x) => !x.narration)) {
        for (const sec of LENGTHS) {
            const cap = maxPieces(sec);
            for (let n = 1; n <= cap; n += 1) {
                for (const mode of ['ai', 'human']) {
                    const want = price(t, sec, n, mode) > price(matsu, sec, n, 'human');
                    await pick(page, t.id, sec, n);
                    await setNarAll(page, mode);
                    await page.waitForTimeout(40);
                    const hint = await page.locator('#calc-nar-hint').innerText();
                    const shown = /松（人物ナレーション1名込み/.test(hint);
                    if (shown !== want) warnBad.push(`${t.label}${sec}秒×${n}本/${mode}: ${shown}≠${want}`);
                    await setNarAll(page, 'none');
                }
            }
        }
    }
    check('松のほうが安いときだけ、その旨が出る', warnBad.length === 0,
        JSON.stringify(warnBad.slice(0, 3)));
}

/* ---- 料金のしくみを説明している文章 ----
   9/19 に松のナレーションを選べるようにしたとき、計算機だけ直して
   「金額の内訳」と README が「松は込みなので対象外」のまま残っていた。
   金額を文章にも書いている以上、そこも計算機の値と突き合わせる */
{
    const y = (n) => `¥${n.toLocaleString('ja-JP')}`;
    const note = await page.locator('#plans .plan-note').innerText();
    /* 9/22：本ごとに選べるようになったので「使わないなら ¥50,000」は
       1本のときだけの数字になった。文章はルールで書く（手配ぶん＋入れない本ぶん） */
    check('内訳の文章に松の差し引きが書いてある',
        new RegExp(`人物を1本も使わない場合は、その手配ぶん ${y(PRICE.matsuToAi)}`).test(note)
        && new RegExp(`入れない本は、そのうえで1本につき ${y(PRICE.noNarration)}`).test(note),
        note.split('\n').find((l) => l.includes('人物ナレーション')) || '');
    check('「使わないなら ¥50,000」という1本だけの数字が残っていない',
        !/使わないなら ¥50,000/.test(note));
    check('「松は対象外」という古い書き方が残っていない',
        !/松は人物ナレーション込みのため対象外/.test(note));
    const readme = readFileSync(`${ROOT}/README.md`, 'utf8');
    check('README の料金の考え方にも松の差し引きがある',
        readme.includes(y(PRICE.matsuToAi)) && readme.includes('入れない本1本につき'));
}

/* ---- 段の順序と独立性 ---- */
/* 直前の「松のほうが安い」の確認ループが 'none' で終わるので、素の状態（AI）に戻す。
   戻さないと差し引きが乗って、以降の金額の検査が全部ずれる。
   なお段を選び直すとナレーションは段の既定に戻る（松は human／梅・竹は ai） */
await setNarAll(page, 'ai');
await page.waitForTimeout(60);
const ladder = [];
for (const t of TIERS) ladder.push(await pick(page, t.id, 90, 1));
check('段が上がるほど高い', ladder[0] < ladder[1] && ladder[1] < ladder[2], JSON.stringify(ladder));
/* 初期状態（AIナレーション）での額。AIは料金に含むので従来と同じ。
   ここが 380,000 になったら、初期が「なし」に戻って差し引きが効いている */
check('梅は従来価格を据え置き', ladder[0] === 405000, `¥${ladder[0]}`);
check('短い尺でも松が選べる',
    (await pick(page, 'matsu', 30, 1)) === price(TIERS[2], 30, 1, 'human'),
    String(await pick(page, 'matsu', 30, 1)));
check('長い尺でも梅が選べる', (await pick(page, 'ume', 300, 1)) === price(TIERS[0], 300, 1));

/* ---- 本ごとに尺を変える（9/22） ----
   料金は合計秒数と本数だけで決まるので、割り方が変わっても金額は動かない。
   変わるのは「何を何秒で作るか」が内訳とメールに出るかどうか */
{
    await page.locator('#calc-tier .calc-opt[data-tier="ume"]').click();
    await setNarAll(page, 'ai');
    await setLens(page, [30, 90, 15]);
    await page.waitForTimeout(60);
    const shown = Number((await page.locator('#calc-total').innerText()).replace(/[^\d]/g, ''));
    check('尺がばらばらでも合計で計算する', shown === price(TIERS[0], 30 + 90 + 15, 3, 'ai'), String(shown));
    check('内訳に本ごとの尺が出る',
        /合計2分15秒（30秒×1本、90秒×1本、15秒×1本）/.test(await page.locator('#calc-len-dt').innerText()),
        await page.locator('#calc-len-dt').innerText());
    check('割り方が違っても同じ合計なら同じ額', shown === await pick(page, 'ume', 135, 3));
    await setLens(page, [45, 45, 45]);
    await page.waitForTimeout(60);
    check('同じ尺が続くところはまとめて書く',
        /合計2分15秒（45秒×3本）/.test(await page.locator('#calc-len-dt').innerText()),
        await page.locator('#calc-len-dt').innerText());
    /* 本数を増やしたぶんは直前の本と同じ尺で埋める。
       毎回15秒に戻ると、同じ尺を並べたい人が本数ぶん選び直すことになる */
    await setLens(page, [90]);
    await page.locator('#calc-cnt .calc-opt[data-count="3"]').click();
    await page.waitForTimeout(60);
    check('本数を増やすと直前の尺で埋まる',
        (await page.locator('#calc-len select[data-kind="len"][data-row="2"]').inputValue()) === '90');
    /* 本ごとに15秒以上なので、1本が短くなりすぎることがない。
       以前は合計を本数で割っていたので本数に上限を置いていた（countCap） */
    await page.locator('#calc-cnt .calc-opt[data-count="6"]').click();
    await page.waitForTimeout(60);
    check('本数に使えない選択肢が無い',
        (await page.locator('#calc-cnt input:disabled').count()) === 0);
}

/* ---- ナレーションを本ごとに選ぶ（9/22） ----
   決め方は2つだけ。
     1. 人物（1名の手配）は、1本でも使えば ¥70,000。本数では増えない
     2. ナレーションを入れない本は、1本につき ¥25,000 を引く
   1本だけのときは 9/19 までと同じ額になる（下で確かめる） */
{
    await page.locator('#calc-tier .calc-opt[data-tier="ume"]').click();
    await setLens(page, [30, 30, 30]);
    await setNarAll(page, 'ai');
    await setNar(page, 0, 'human');
    await setNar(page, 1, 'none');
    await page.waitForTimeout(80);
    const want = priceModes(TIERS[0], 90, ['human', 'none', 'ai']);
    const shown = Number((await page.locator('#calc-total').innerText()).replace(/[^\d]/g, ''));
    check('本ごとに違うナレーションでも計算が合う', shown === want, `${shown}≠${want}`);
    check('内訳に本数で出る',
        /人物 1本・AI 1本・なし 1本/.test(await page.locator('#calc-nar-dt').innerText()),
        await page.locator('#calc-nar-dt').innerText());

    /* 人物は手配が1回なので、何本に入れても額は同じ。ここが本数で増えると
       「1人が同じ収録でまとめて読む」という実態と合わなくなる */
    const one = priceModes(TIERS[0], 90, ['human', 'ai', 'ai']);
    const three = priceModes(TIERS[0], 90, ['human', 'human', 'human']);
    check('人物は何本に入れても1名ぶんのまま', one === three, `${one}≠${three}`);

    /* なしは本数ぶん引く。AIは料金に含まれている＝入れない本はそのぶん工数が要らない */
    check('なしは本数ぶん引く',
        priceModes(TIERS[0], 90, ['none', 'none', 'ai'])
            === priceModes(TIERS[0], 90, ['ai', 'ai', 'ai']) - PRICE.noNarration * 2);

    /* 1本だけのときは 9/19 までと同じ額（梅 なし −25,000 / 人物 +70,000、
       松 AI −25,000 / なし −50,000）。ここが動くと既存のお客様への説明が変わる */
    const same = [
        ['ume', 'none', -PRICE.noNarration], ['ume', 'ai', 0], ['ume', 'human', PRICE.narrationHuman],
        ['matsu', 'human', 0], ['matsu', 'ai', -PRICE.matsuToAi], ['matsu', 'none', -matsuToNone()],
    ].every(([id, nar, fee]) => {
        const t = TIERS.find((x) => x.id === id);
        return narFee(t, [nar]) === fee;
    });
    check('1本だけなら 9/19 までと同じ額', same);

    /* 引いたあとでも、選べる全部の組み合わせで時間単価の下限を割らないこと。
       ここが割ると「ナレーションを外すほど損」になる */
    const bad = [];
    for (const t of TIERS) {
        for (const { sec, n, modes } of reachableNar()) {
            const r = priceModes(t, sec, modes) / hoursModes(t, sec, modes);
            if (r < RATE * 0.95) bad.push(`${t.label}${sec}秒×${n}本/${modes.join()}: ¥${Math.round(r)}`);
        }
    }
    check('本ごとに選んでも下限を割らない', bad.length === 0, bad.slice(0, 3).join(','));

    /* 本数を増やしたぶんは直前の本と同じナレーションで埋める */
    await setLens(page, [30]);
    await setNarAll(page, 'none');
    await page.locator('#calc-cnt .calc-opt[data-count="3"]').click();
    await page.waitForTimeout(60);
    check('本数を増やすと直前のナレーションで埋まる', (await narOf(page, 2)) === 'none');
    /* 段を変えたら全部の本を既定に戻す。松は人物込みなので意味が変わる */
    await page.locator('#calc-tier .calc-opt[data-tier="matsu"]').click();
    await page.waitForTimeout(60);
    check('段を変えると全部の本が既定に戻る',
        (await narOf(page, 0)) === 'human' && (await narOf(page, 2)) === 'human');
    // 次の検査が前提にしている状態（梅・1本・AI）へ戻す
    await page.locator('#calc-tier .calc-opt[data-tier="ume"]').click();
    await page.locator('#calc-cnt .calc-opt[data-count="1"]').click();
    await setNarAll(page, 'ai');
}

/* ---- プリセット ---- */
check('プリセットは用途名',
    (await page.locator('.calc-preset b').allInnerTexts()).join('|') === 'SNS広告|会社紹介|ブランド映像');
for (const [t, sec] of [['ume', 30], ['take', 90], ['matsu', 180]]) {
    await page.locator(`.calc-preset[data-tier="${t}"]`).click();
    await page.waitForTimeout(80);
    const on = await page.locator('#calc-tier input:checked').getAttribute('data-tier');
    const shown = Number((await page.locator('#calc-total').innerText()).replace(/[^\d]/g, ''));
    check(`プリセット(${t})が段ごと切り替わる`,
        on === t && shown === price(TIERS.find(x => x.id === t), sec, 1), `${on} ¥${shown}`);
}

/* ---- メール本文 ----
   9/19 に本文を詰めた。松でもナレーションを選べるようにしたら差し引きの行が増え、
   最長が 1,901 文字になって mailto の上限を超えたため。
   「AI（料金に含まれます）」→「AI」、「ご希望の公開時期」→「公開時期」など */
await pick(page, 'take', 90, 2);
const mailLink = () => page.locator('#calc-mail').getAttribute('href');
const href = await mailLink();
const q = new URLSearchParams(href.split('?')[1]);
const body = q.get('body') || '';
check('相談ボタンがメールを開く', href.startsWith('mailto:bonvoyage.ti@icloud.com?'));
check('件名に段と尺と本数が入る', /竹・合計90秒／2本/.test(q.get('subject') || ''), q.get('subject'));
check('本文に選んだ内容が入る',
    /・仕上げ：竹（上）/.test(body) && /・ナレーション：AI/.test(body)
    && new RegExp(`・概算金額：¥${price(TIERS[1], 90, 2).toLocaleString('ja-JP')}（税込）`).test(body)
    && new RegExp(`・納品目安：約${leadWeeks(TIERS[1], 90)}週間`).test(body));
/* 本ごとの尺は本数の行に「30/60秒」と詰めて書く。
   全角で並べると1文字9バイトになり、mailto の上限に触るため */
check('本文に内訳も入る', /・基本料金：¥90,000/.test(body)
    && /・尺 合計90秒 × ¥4,900（竹）/.test(body)
    && /・本数 2本（30\/60秒）：/.test(body));
/* 尺と本数は件名と内訳にあるので、選んだ内容では繰り返さない（mailto の長さ対策） */
check('選んだ内容で尺と本数を繰り返していない', !/・合計の尺：/.test(body) && !/・本数：2本/.test(body));
check('先方に書いてもらう欄がある',
    /会社名・お名前：/.test(body) && /映像の用途：/.test(body) && /公開時期：/.test(body));
await pick(page, 'ume', 60, 2);
await setNarAll(page, 'human');
await page.waitForTimeout(60);
const narBody = new URLSearchParams((await mailLink()).split('?')[1]).get('body') || '';
/* 9/22：本ごとに選べるので、本文は「人物2」のように本数で書く。
   金額は1名ぶんのまま（何本に入れても増えない） */
check('人物ナレーションを足すと本文に単位と金額が入る',
    /・ナレーション：人物2/.test(narBody)
    && new RegExp(`・ナレーション 人物1名：¥${PRICE.narrationHuman.toLocaleString('ja-JP')}〜`).test(narBody));
await setNarAll(page, 'ai');
await page.waitForTimeout(60);
const aiBody = new URLSearchParams((await mailLink()).split('?')[1]).get('body') || '';
/* 直前で 60秒×2本 を選んでいる。AI は本数ぶん増えるので 2本ぶんの額が出る */
check('AIを選ぶと本文に「料金に含まれます」と入り、金額行は出ない',
    /・ナレーション：AI/.test(aiBody) && !/・ナレーション 人物/.test(aiBody));
await setNarAll(page, 'none');
/* mailto はクライアント側の長さ制限があるので、最長の組み合わせでも収まること。
   以前は 松300秒×6本 の1通りだけ見ていたが、pick() が段の既定（松は human）に
   戻すため、差し引きの行が出るケースを踏んでいなかった。実測の最長は
   梅300秒×3本/human の1,748文字で、松/AI の差し引き行もここで見る（9/19） */
const mailLens = [];
for (const [t, sec, n, nar] of [
    ['matsu', 300, 6, 'human'], ['matsu', 300, 6, 'ai'], ['matsu', 300, 6, 'none'],
    ['matsu', 180, 3, 'ai'], ['ume', 300, 3, 'human'], ['take', 300, 6, 'human'],
]) {
    await pick(page, t, sec, n);
    await setNarAll(page, nar);
    await page.waitForTimeout(40);
    const href = await page.locator('#calc-mail').getAttribute('href');
    mailLens.push({ k: `${t}${sec}秒×${n}本/${nar}`, len: href.length });
}
/* 9/22 追加。本ごとに尺を選べるようになったので、本当の最長は
   「6本ぜんぶ尺が違う」場合になった。上の pick() では踏めない */
for (const lens of [[15, 30, 45, 60, 90, 300], [15, 45, 90, 120, 180, 300], [30, 45, 60, 90, 120, 180]]) {
    await page.locator('#calc-tier .calc-opt[data-tier="matsu"]').click();
    await setLens(page, lens);
    await setNarAll(page, 'none');
    await page.waitForTimeout(40);
    const href = await page.locator('#calc-mail').getAttribute('href');
    mailLens.push({ k: `松 ${lens.join('/')}秒/none`, len: href.length });
}
const over = mailLens.filter((x) => x.len >= 1800);
check('最長の組み合わせでも mailto が収まる', over.length === 0,
    JSON.stringify(mailLens.sort((a, b) => b.len - a.len).slice(0, 3)));

check('JS エラーなし', page.__errors.length === 0, JSON.stringify(page.__errors));
await browser.close();
report();
