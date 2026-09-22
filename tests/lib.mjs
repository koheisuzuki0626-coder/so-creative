/* テストの土台。結果の集計と、よく使う操作をまとめてある。
   これらは scratchpad ではなくリポジトリに置くこと。
   一時ディレクトリに置いていたぶんは消えて失われた。 */
export const state = { fail: 0, total: 0 };
export function check(name, ok, note = '') {
    state.total += 1;
    if (!ok) state.fail += 1;
    console.log(`${ok ? 'PASS' : 'FAIL'}  ${name}${note ? '  ' + note : ''}`);
}
export function report() {
    console.log(state.fail ? `\nRESULT: ${state.fail} / ${state.total} 件 FAILED`
                           : `\nRESULT: ALL PASS (${state.total}件)`);
    process.exit(state.fail ? 1 : 0);
}
export const BASE = process.env.BASE || 'http://127.0.0.1:8899';
/* Playwright の場所。環境が違うときは PW=/path/to/playwright/index.js で差し替える */
export const PW = process.env.PW || '/opt/node22/lib/node_modules/playwright/index.js';

/* 料金と工数のモデル。index.html のコメントと同じもの。
   ここを書き換えるときは index.html も必ず合わせること */
/* narrationAi は 0。AIナレーションは料金に含める（2026-09-17）。
   工数（1本 1.0h）はかかるので、時間単価はそのぶん下がる。下限は下の検査で見ている */
export const PRICE = { base: 90000, perExtra: 65000, narrationAi: 0, narrationHuman: 70000,
    /* AIナレーションは料金に含まれている。使わない（テロップのみ）なら返す。
       梅・竹だけ。松は人物ナレーションが込みで、これは秒単価に溶けているので対象外。
       3万にすると梅15秒×1本だけが ¥21,429/h（目標の93.2%）で下限を割る。
       2.75万でも95.2%しか残らないので、余白を見て2.5万にした（97.3%）。 */
    noNarration: 25000,
    /* 松の人物ナレーション1名も外せる（9/19）。返す額は「いちばん短い尺でも
       時間単価の下限を割らない額」で決めた。index.html の PRICE と同じ値にすること */
    matsuToAi: 25000, matsuToNone: 50000 };
export const TIERS = [
    { id: 'ume',   label: '梅', perSec: 3500, hours: 1.0,  narration: false },
    { id: 'take',  label: '竹', perSec: 4900, hours: 1.22, narration: false },
    { id: 'matsu', label: '松', perSec: 6650, hours: 1.36, narration: true },
];
export const LENGTHS = [15, 30, 45, 60, 90, 120, 180, 300];
/* 9/22 まで：「合計の尺」を「本数」で割る形だったので、1本が短くなりすぎないよう
   本数に上限を置いていた（countCap）。いまは本ごとに尺を選ぶので、
   1本あたりは必ず15秒以上になり、上限そのものが要らない。
   代わりに「合計 sec 秒を最大で何本に割れるか」を使う */
export const maxPieces = (sec) => Math.min(6, Math.floor(sec / LENGTHS[0]));
/* 到達できる (合計秒数, 本数) の全部。1〜6本、各本 LENGTHS のどれか。
   下限の検査はこの集合で回す（LENGTHS だけを見ると 45=15+30 のような合計を見落とす） */
/* ナレーションも本ごとに選べるので、金額を決めるのは
   (合計秒数, 本数, なしの本数, 人物を使うか) の4つ。その全部を返す */
export function reachableNar() {
    const out = [];
    for (const { sec, n } of reachable()) {
        for (let nNone = 0; nNone <= n; nNone += 1) {
            for (const hasHuman of [true, false]) {
                if (nNone === n && hasHuman) continue;   // 全部なしなら人物はいない
                const modes = [...Array(nNone).fill('none'),
                    ...Array(n - nNone).fill(hasHuman ? 'human' : 'ai')];
                out.push({ sec, n, nNone, hasHuman, modes });
            }
        }
    }
    return out;
}
export function reachable() {
    const out = [];
    for (let n = 1; n <= 6; n += 1) {
        const seen = new Set();
        const rec = (i, sum) => {
            if (i === n) { seen.add(sum); return; }
            for (const l of LENGTHS) rec(i + 1, sum + l);
        };
        rec(0, 0);
        for (const sec of seen) out.push({ sec, n });
    }
    return out;
}
/* nar … 'none' | 'ai' | 'human'。松は human が込み。
   2026-09-17 に2段階の変更をした。

   1. 「1本 ¥30,000」（合成音声の前提）→「1名 ¥70,000〜」（人のナレーター）。
      合成音声の日本語が使えなかったため（4エンジン×9声を試して不採用。
      `成果物/サンプル映像/工数記録_サンプル映像03_05_07.md`）
   2. AIナレーションと人物ナレーションを**選べる**ようにし、
      AIナレーションは料金に含めた（追加料金なし）

   **AIナレーションは料金に含める**（追加料金なし）。合成音声なので原価がほぼゼロで、
   かかるのは原稿・声の選定・配置の 1.0h だけ。ここを有料にすると
   「声を入れたいだけ」の相談を落とす。
   **人物ナレーションは 1名 ¥70,000〜。**本数では増えない（1人が同じ収録で
   複数本を読んでも手配は1回で、費用もほぼ変わらない）。声を2人使うなら別途見積り。

   **工数はどちらも 1本 1.0h。**原稿と配置は本数ぶん要るので、AI でも人でも同じ。
   人物の ¥70,000 のうち大半はナレーターへの外注費で、これは工数ではなく原価。 */
/* 9/22：ナレーションを本ごとに選べるようにしたので、モードの配列で受ける。
   決め方は2つだけ。

   1. **人物ナレーション（1名の手配）は、1本でも使えば ¥70,000。**本数では増えない。
      1人が同じ収録で複数本を読んでも手配は1回で、費用もほぼ変わらないため。
      松は秒単価に1名ぶんが溶けているので ¥0。人物を1本も使わないなら、
      その手配ぶん（¥25,000）を返す。
   2. **ナレーションを入れない本は、1本につき ¥25,000 を引く。**
      AIナレーションは料金に含まれている（＝入れない本はそのぶん 工数 が要らない）。

   1本だけのときは、9/19 までと同じ額になる（梅 なし −25,000 / 人物 +70,000、
   松 AI −25,000 / なし −50,000）。 */
export const narFee = (t, modes) => {
    const hasHuman = modes.includes('human');
    const nNone = modes.filter((m) => m === 'none').length;
    return (t.narration ? (hasHuman ? 0 : -PRICE.matsuToAi)
        : (hasHuman ? PRICE.narrationHuman : 0))
        - PRICE.noNarration * nNone;
};
/* 原稿・声の選定・配置は1本 1.0h。ナレーションを入れない本は 0。
   松の秒単価にはナレーション1本ぶんの 1.0h が入っているので、
   人物を使う松は1本ぶん差し引く（ここを引かないと 60秒松の 15.2h が動く） */
export const narTracks = (t, modes) =>
    modes.filter((m) => m !== 'none').length - (t.narration && modes.includes('human') ? 1 : 0);
/* 同じモードを本数ぶん並べた配列。4引数の呼び出しはこれを通す */
export const sameModes = (n, nar) => Array.from({ length: n }, () => nar);

/* 既定は 'ai'。計算機の初期状態（AIナレーション）と揃える。
   ここを 'none' にすると差し引きが既定になり、
   4引数を省いた検査が計算機の表示と食い違う */
export const priceModes = (t, sec, modes) =>
    PRICE.base + t.perSec * sec + PRICE.perExtra * (modes.length - 1) + narFee(t, modes);
export const price = (t, sec, n, nar = 'ai') => priceModes(t, sec, sameModes(n, nar));
/* 工数モデル（2026-09-16 に実測へ合わせた）。
     工数 = 3.0h + 0.15h × 倍率 × 秒数 + 1.5h × (本数−1) + 1.0h × ナレーション本数
   実測（下の MEASURED）に、実案件の打合せ・素材待ち・要件の揺れぶんとして
   約1.5倍の安全率をかけてある。60秒の松で 15.2h（実測 10.5h）。
   段の倍率 1.0 / 1.22 / 1.36 は工程別の実測から:
     竹 ＝ 梅 ＋ キャラクターシート 1.0h ＋ 修正1回 0.6h
     松 ＝ 竹 ＋ ナレーション 1.0h（修正は竹と同じ3回）
   ナレーションの工数は実測 1.0h（原稿・声の選定・配置）で、AI でも人でも同じ。
   人の ¥70,000 は大半がナレーターへの外注費なので、
   **この 1.0h で割った値は自分の時間単価ではない。**
   価格の倍率（1.0 / 1.4 / 1.9）は据え置きなので、上の段ほど時間単価が高い。
   index.html の HOURS / TIERS[].hours と同じ値にすること */
export const HOURS = { base: 3.0, perSec: 0.15, perExtra: 1.5, narration: 1.0 };
export const hoursModes = (t, sec, modes) =>
    HOURS.base + HOURS.perSec * t.hours * sec + HOURS.perExtra * (modes.length - 1)
    + HOURS.narration * narTracks(t, modes);
export const hours = (t, sec, n, nar = 'ai') => hoursModes(t, sec, sameModes(n, nar));
export const leadWeeks = (t, sec, nar = 'ai', n = 1) =>
    Math.max(2, Math.round((HOURS.base + HOURS.perSec * t.hours * sec
        + HOURS.narration * narTracks(t, sameModes(n, nar))) / 25 + 1));
/* 目標の時間単価。以前の ¥14,900 は「60秒の松が32h かかる」という重いモデルからの
   逆算だった。モデルを実測に合わせた結果、同じ価格で ¥23,000/h を下回らない */
export const RATE = 23000;

/* 実測値（2026-09-13〜15・営業ロープレ1件）。
   架空クライアントのため、素材待ち・返信待ち・要件の揺れが入っていない。
   実案件で測り直すまでは下限の目安として扱う。

   ここに入れていない実測がある（2026-09-17・サンプル映像 02/04 の15秒×2本、
   成果物/サンプル映像/工数記録_サンプル映像02_04.md）。
   経過2.6h・修正の往復12回で、モデルの 6.8h（15秒2本・梅）より軽く出ているが、
   **物差しが違うのでこの配列には入れない**：
     - 指示を出す側と手を動かす側が分かれた数字で、上の 11.5h（人が手を動かした時間）
       とは比較できない
     - テロップのPNG生成・BGMとSEの合成・ffmpeg の組み立てまで含んでおり、
       人が手作業でやる前提のモデルとは前提が違う
     - 自社サンプルなので判断基準が自分の好みになり、往復が12回（上は4回）に膨らんだ
   モデルを下げる根拠として使うなら、実案件で人が手を動かして測り直すこと。 */
export const MEASURED = [
    /* 2026-09-15 に工程別で実測。合計11.5h の内訳は
       構成1.0 / キャラシート1.0 / 生成・選別3.0 / つなぎ2.0 /
       ナレーション1.0 / 15秒版1.0 / 修正4往復2.5。
       本編ぶんは 15秒版の1.0h を除いた 10.5h として扱う。
       （修正4往復は現行の松の上限3回より1回多い。上限どおりなら 9.9h） */
    { label: '本編',   sec: 59, tier: 'matsu', workHours: 10.5 },
    { label: '追加尺', sec: 15, tier: 'matsu', workHours: 1 },
];
/* 修正1往復あたりの実測。モデルの係数 0.62h とほぼ一致した唯一の項目 */
export const REVISION_HOURS = 0.625;
/* クレジット原価の実測（Seedance 2.5 1080p 5秒＝45cr、採用率35%）。
   納品物 2,462cr ÷ 74秒（本編59秒＋展示会用15秒）＝ 33cr/秒。本編の尺だけで割ると 41cr/秒 で、
   ここは安全側の 41 を使う。追加購入単価 $0.0475〜0.05/cr × ¥154 ≒ ¥310/秒 */
export const CREDITS_PER_SEC = 41;

export async function open(pw, { width = 1280, height = 900, mobile = false, page: file = 'index.html' } = {}) {
    const { mockFonts, mockYtimg } = await import('./route.mjs');
    const ctx = { viewport: { width, height }, deviceScaleFactor: mobile ? 3 : 1 };
    if (mobile) { ctx.isMobile = true; ctx.hasTouch = true; }
    const p = await pw.newPage(ctx);
    const errors = [];
    p.on('pageerror', (e) => errors.push(String(e)));
    await mockFonts(p); await mockYtimg(p);
    await p.goto(`${BASE}/${file}`, { waitUntil: 'networkidle' });
    await p.evaluate(() => document.fonts.ready);
    await p.waitForTimeout(500);
    p.__errors = errors;
    return p;
}
/* 9/22 から、尺は本ごとに選ぶ形になった（合計の尺を本数で割る形ではない）。
   pick(sec, n) の意味は前と同じ「合計 sec 秒を n 本」なので、
   選択肢の尺だけで合計 sec になる組み合わせをここで探して入れる。
   料金は合計秒数と本数だけで決まるので、どの割り方でも金額は同じ */
export function splitSec(sec, n) {
    const memo = new Map();
    const go = (left, k) => {
        if (k === 0) return left === 0 ? [] : null;
        const key = `${left},${k}`;
        if (memo.has(key)) return memo.get(key);
        let out = null;
        for (const l of LENGTHS) {
            if (l > left) break;
            const rest = go(left - l, k - 1);
            if (rest) { out = [l, ...rest]; break; }
        }
        memo.set(key, out);
        return out;
    };
    const got = go(sec, n);
    if (!got) throw new Error(`${sec}秒 を ${n}本 に割れない（選べる尺: ${LENGTHS.join()}）`);
    return got;
}
export const setLens = async (p, parts) => {
    await p.locator(`#calc-cnt .calc-opt[data-count="${parts.length}"]`).click();
    for (const [i, sec] of parts.entries()) {
        await p.locator(`#calc-len select[data-kind="len"][data-row="${i}"]`).selectOption(String(sec));
    }
};
/* ナレーションも本ごとに選ぶ（9/22）。i 本目だけ、または全部まとめて */
export const setNar = async (p, i, mode) =>
    p.locator(`#calc-len select[data-kind="nar"][data-row="${i}"]`).selectOption(mode);
export const setNarAll = async (p, mode) => {
    const n = await p.locator('#calc-len select[data-kind="nar"]').count();
    for (let i = 0; i < n; i += 1) await setNar(p, i, mode);
};
export const narOf = async (p, i) =>
    p.locator(`#calc-len select[data-kind="nar"][data-row="${i}"]`).inputValue();
export const pick = async (p, tier, sec, n = 1) => {
    await p.locator(`#calc-tier .calc-opt[data-tier="${tier}"]`).click();
    await setLens(p, splitSec(sec, n));
    await p.waitForTimeout(60);
    return Number((await p.locator('#calc-total').innerText()).replace(/[^\d]/g, ''));
};
