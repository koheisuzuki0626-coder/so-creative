/* 料金シミュレーター。
   「お客様にどの組み合わせを選ばせても採算が崩れない」ことの担保がここ。
   金額・工数のどれかを動かしたら必ずこれを通すこと。 */
import { check, report, PW, open, pick, PRICE, HOURS, TIERS, LENGTHS, countCap, price, hours, leadWeeks, RATE, MEASURED, REVISION_HOURS, CREDITS_PER_SEC } from './lib.mjs';
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
check('尺が8つ', (await page.locator('#calc-len .calc-opt').count()) === LENGTHS.length);
check('本数が6つ', (await page.locator('#calc-cnt .calc-opt').count()) === 6);
check('ナレーションが2択', (await page.locator('#calc-nar .calc-opt').count()) === 2);
check('操作の順番を番号で示している',
    (await page.locator('.calc-step').allInnerTexts()).join('') === '1234');
check('実物のラジオで組んである',
    (await page.locator('.calc input[type="radio"]').count()) === 3 + 8 + 6 + 2);

/* ---- 段の説明は客先向けの言葉か ---- */
for (const [t, must, use, rev] of [['ume', '登場人物なし', 'SNS', 2], ['take', '2人まで', '採用', 3], ['matsu', 'ナレーション込み', '展示会', 3]]) {
    await page.locator(`#calc-tier .calc-opt[data-tier="${t}"]`).click();
    const h = await page.locator('#calc-tier-hint').innerText();
    check(`${t} の中身が納品物の言葉で出る`, h.includes(must) && /納品/.test(h), h.slice(0, 34));
    check(`${t} の向いている用途が出る`, h.includes('向いている用途') && h.includes(use));
    check(`${t} の修正回数が出る（${rev}回）`, h.includes(`修正${rev}回まで`), (h.match(/修正\d回まで/) || [''])[0]);
    /* 4K は全段で無料。ナレーションは梅・竹が追加、松が込み */
    check(`${t} で 4K 納品を案内している`, /4K/.test(h));
    check(`${t} のナレーションの扱いが出る`, t === 'matsu' ? /ナレーション込み/.test(h) : /ナレーションは1本 ¥30,000/.test(h));
}
const plansText = await page.locator('#plans').innerText();
check('生成回数など内部の手順を出していない',
    !/カットにつき|回まで生成|回以上生成/.test(plansText));
/* 実証で使えないと分かったものを売り文句に残していないか（4K は無料で出すことにしたので除外） */
check('落とした仕様が段の説明に残っていない',
    !/ちらつき|正方形|3形式|2形式|720p/.test(plansText), plansText.slice(0, 40));
check('修正回数が5回に戻っていない', !/5回/.test(plansText));

/* ---- ナレーションの選択 ---- */
await page.locator('#calc-tier .calc-opt[data-tier="matsu"]').click();
check('松では「なし」が選べず「あり」に固定',
    (await page.locator('#calc-nar input[data-nar="off"]').isDisabled())
    && (await page.locator('#calc-nar input[data-nar="on"]').isChecked()));
check('松の内訳にナレーションは加算されない',
    /松に込み/.test(await page.locator('#calc-nar-dt').innerText())
    && (await page.locator('#calc-narfee').innerText()) === '¥0');
await page.locator('#calc-tier .calc-opt[data-tier="ume"]').click();
check('梅では「なし」が選べる', !(await page.locator('#calc-nar input[data-nar="off"]').isDisabled()));
await page.locator('#calc-nar .calc-opt[data-nar="on"]').click();
await page.locator('#calc-cnt .calc-opt[data-count="2"]').click();
check('梅のナレーションは本数ぶん加算',
    (await page.locator('#calc-narfee').innerText()) === `¥${(PRICE.narration * 2).toLocaleString('ja-JP')}`
    && Number((await page.locator('#calc-total').innerText()).replace(/[^\d]/g, '')) === price(TIERS[0], 30, 2, true));
await page.locator('#calc-nar .calc-opt[data-nar="off"]').click();
await page.locator('#calc-cnt .calc-opt[data-count="1"]').click();


/* ---- 全組み合わせの金額・上限・時間単価 ---- */
const wrong = [], capBad = [], rates = [], leadBad = [];
for (const t of TIERS) {
    await page.locator(`#calc-tier .calc-opt[data-tier="${t.id}"]`).click();
    for (const sec of LENGTHS) {
        await page.locator(`#calc-len .calc-opt[data-sec="${sec}"]`).click();
        const cap = countCap(sec);
        for (let n = 1; n <= 6; n += 1) {
            const dis = await page.locator(`#calc-cnt input[data-count="${n}"]`).isDisabled();
            if (dis !== (n > cap)) capBad.push(`${t.label}${sec}秒/${n}本`);
        }
        for (let n = 1; n <= cap; n += 1) {
            await page.locator(`#calc-cnt .calc-opt[data-count="${n}"]`).click();
            for (const nar of (t.narration ? [false] : [false, true])) {
                if (!t.narration) await page.locator(`#calc-nar .calc-opt[data-nar="${nar ? 'on' : 'off'}"]`).click();
                const shown = Number((await page.locator('#calc-total').innerText()).replace(/[^\d]/g, ''));
                const want = price(t, sec, n, nar);
                const c = `${t.label}${sec}秒×${n}本${nar ? '+ナレ' : ''}`;
                if (shown !== want) wrong.push(`${c}: ${shown}≠${want}`);
                rates.push({ c, rate: shown / hours(t, sec, n, nar) });
            }
            if (!t.narration) await page.locator('#calc-nar .calc-opt[data-nar="off"]').click();
        }
        await page.locator('#calc-cnt .calc-opt[data-count="1"]').click();
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
    LENGTHS.every((s) => leadWeeks(TIERS[0], s, true) - leadWeeks(TIERS[0], s) <= 1));
/* ナレーション追加の時間単価。¥30,000 ÷ 1.0h ＝ ¥30,000/h で目標を割らない */
check('ナレーション追加が時間単価の目標を割らない', PRICE.narration / HOURS_NARRATION() >= RATE * 0.95,
    `¥${Math.round(PRICE.narration / HOURS_NARRATION())}/h`);

/* ---- 段の順序と独立性 ---- */
const ladder = [];
for (const t of TIERS) ladder.push(await pick(page, t.id, 90, 1));
check('段が上がるほど高い', ladder[0] < ladder[1] && ladder[1] < ladder[2], JSON.stringify(ladder));
check('梅は従来価格を据え置き', ladder[0] === 405000, `¥${ladder[0]}`);
check('短い尺でも松が選べる', (await pick(page, 'matsu', 30, 1)) === price(TIERS[2], 30, 1));
check('長い尺でも梅が選べる', (await pick(page, 'ume', 300, 1)) === price(TIERS[0], 300, 1));

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

/* ---- メール本文 ---- */
await pick(page, 'take', 90, 2);
const mailLink = () => page.locator('#calc-mail').getAttribute('href');
const href = await mailLink();
const q = new URLSearchParams(href.split('?')[1]);
const body = q.get('body') || '';
check('相談ボタンがメールを開く', href.startsWith('mailto:bonvoyage.ti@icloud.com?'));
check('件名に段と尺と本数が入る', /竹・90秒 × 2本/.test(q.get('subject') || ''), q.get('subject'));
check('本文に選んだ内容が入る',
    /・仕上げ：竹（上）/.test(body) && /・合計の尺：90秒/.test(body) && /・本数：2本/.test(body) && /・ナレーション：なし/.test(body)
    && new RegExp(`・概算金額：¥${price(TIERS[1], 90, 2).toLocaleString('ja-JP')}（税別）`).test(body)
    && new RegExp(`・納品目安：約${leadWeeks(TIERS[1], 90)}週間`).test(body));
check('本文に内訳も入る', /・基本料金：¥90,000/.test(body) && /・尺 90秒 × ¥4,900（竹）/.test(body));
check('先方に書いてもらう欄がある',
    /会社名 \/ お名前：/.test(body) && /映像の用途：/.test(body) && /ご希望の公開時期：/.test(body));
await pick(page, 'ume', 60, 2);
await page.locator('#calc-nar .calc-opt[data-nar="on"]').click();
await page.waitForTimeout(60);
const narBody = new URLSearchParams((await mailLink()).split('?')[1]).get('body') || '';
check('ナレーションを足すと本文に本数と金額が入る',
    /・ナレーション：あり/.test(narBody) && new RegExp(`・ナレーション 2本：¥${(PRICE.narration * 2).toLocaleString('ja-JP')}`).test(narBody));
await page.locator('#calc-nar .calc-opt[data-nar="off"]').click();
// mailto はクライアント側の長さ制限があるので、最長の組み合わせでも収まること
await pick(page, 'matsu', 300, 6);
const longest = await page.locator('#calc-mail').getAttribute('href');
check('最長の組み合わせでも mailto が収まる', longest.length < 1800, `${longest.length}文字`);

check('JS エラーなし', page.__errors.length === 0, JSON.stringify(page.__errors));
await browser.close();
report();
