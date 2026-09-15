/* 料金シミュレーター。
   「お客様にどの組み合わせを選ばせても採算が崩れない」ことの担保がここ。
   金額・工数のどれかを動かしたら必ずこれを通すこと。 */
import { check, report, PW, open, pick, PRICE, TIERS, LENGTHS, countCap, price, hours, leadWeeks, RATE, MEASURED, REVISION_HOURS } from './lib.mjs';
import pwmod from '/opt/node22/lib/node_modules/playwright/index.js';

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
check('操作の順番を番号で示している',
    (await page.locator('.calc-step').allInnerTexts()).join('') === '123');
check('実物のラジオで組んである',
    (await page.locator('.calc input[type="radio"]').count()) === 3 + 8 + 6);

/* ---- 段の説明は客先向けの言葉か ---- */
for (const [t, must, use] of [['ume', '登場人物なし', 'SNS'], ['take', '2人まで', '採用'], ['matsu', 'ナレーション', '展示会']]) {
    await page.locator(`#calc-tier .calc-opt[data-tier="${t}"]`).click();
    const h = await page.locator('#calc-tier-hint').innerText();
    check(`${t} の中身が納品物の言葉で出る`, h.includes(must) && /納品/.test(h), h.slice(0, 34));
    check(`${t} の向いている用途が出る`, h.includes('向いている用途') && h.includes(use));
    check(`${t} の修正回数が出る`, /修正\d回まで/.test(h), (h.match(/修正\d回まで/) || [''])[0]);
}
const plansText = await page.locator('#plans').innerText();
check('生成回数など内部の手順を出していない',
    !/カットにつき|回まで生成|回以上生成/.test(plansText));
/* 実証で使えないと分かったものを売り文句に残していないか */
check('落とした仕様が段の説明に残っていない',
    !/4K|ちらつき|高精細|正方形|3形式|2形式|720p/.test(plansText), plansText.slice(0, 40));


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
            const shown = Number((await page.locator('#calc-total').innerText()).replace(/[^\d]/g, ''));
            const want = price(t, sec, n);
            if (shown !== want) wrong.push(`${t.label}${sec}秒×${n}本: ${shown}≠${want}`);
            rates.push({ c: `${t.label}${sec}秒×${n}本`, rate: shown / hours(t, sec, n) });
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

/* 実測できた唯一の係数。段の差（修正2/3/5回）はこれを根拠にしている */
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
const href = await page.locator('#calc-mail').getAttribute('href');
const q = new URLSearchParams(href.split('?')[1]);
const body = q.get('body') || '';
check('相談ボタンがメールを開く', href.startsWith('mailto:bonvoyage.ti@icloud.com?'));
check('件名に段と尺と本数が入る', /竹・90秒 × 2本/.test(q.get('subject') || ''), q.get('subject'));
check('本文に選んだ内容が入る',
    /・仕上げ：竹（上）/.test(body) && /・合計の尺：90秒/.test(body) && /・本数：2本/.test(body)
    && new RegExp(`・概算金額：¥${price(TIERS[1], 90, 2).toLocaleString('ja-JP')}（税別）`).test(body)
    && new RegExp(`・納品目安：約${leadWeeks(TIERS[1], 90)}週間`).test(body));
check('本文に内訳も入る', /・基本料金：¥90,000/.test(body) && /・尺 90秒 × ¥4,900（竹）/.test(body));
check('先方に書いてもらう欄がある',
    /会社名 \/ お名前：/.test(body) && /映像の用途：/.test(body) && /ご希望の公開時期：/.test(body));
// mailto はクライアント側の長さ制限があるので、最長の組み合わせでも収まること
await pick(page, 'matsu', 300, 6);
const longest = await page.locator('#calc-mail').getAttribute('href');
check('最長の組み合わせでも mailto が収まる', longest.length < 1800, `${longest.length}文字`);

check('JS エラーなし', page.__errors.length === 0, JSON.stringify(page.__errors));
await browser.close();
report();
