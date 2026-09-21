#!/usr/bin/env node
// 官公需情報ポータル（中小企業庁）の公開APIから、動画制作の入札案件を拾う。
//
// 【なぜ要るか】
// 2026-09-21 の調査で、so. が戦えるかは「撮影があるか」で反転すると分かった。
//   撮影なし（札幌市 建設産業PR動画・5本）  → so. は12社中5位
//   撮影8日（札幌市 採用広報WEB動画）      → so. は落札額の20倍。土俵に乗らない
// 撮影の有無はタイトルに書かれないので、本文まで見ないと選別できない。
// 成果物/リサーチ/2026-09-21_価格の実数.md を参照。
//
// API は鍵も登録も要らない。https://www.kkj.go.jp/api/?Query=...（XML）
//
// 使い方:
//   node scripts/bid-search.mjs                 # 既定のキーワードで探す
//   node scripts/bid-search.mjs "PR動画"        # キーワードを指定
//   node scripts/bid-search.mjs --all           # 撮影ありも含めて全部出す
//   node scripts/bid-search.mjs --deep          # リンク先（PDFの仕様書も）を開いて判定する
//   node scripts/bid-search.mjs --json
//
// --deep の PDF 読みには pdfjs-dist が要る。入っていなければ「PDF（要確認）」で返すだけ。
//   npm i pdfjs-dist            （または PDFJS=/path/to/pdfjs-dist/build/pdf.mjs で場所を指定）
// この repo に package.json は置かない方針なので、必要なときだけ入れる。
//
// 注意：so. はまだ入札できない（開業届と入札参加資格の登録が要る）。
// これは「どんな案件が出ているか」を掴むための道具。

const UA = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 '
    + '(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36';
const API = 'https://www.kkj.go.jp/api/';

const DEFAULT_QUERIES = ['動画制作', '映像制作', 'PR動画', '広報動画'];

/* 案件名がこれに当たらないものは落とす。API の検索は緩く、
   「標識撤去業務」のような無関係な案件まで返ってくる */
const IS_VIDEO = /動画|映像|ムービー|ＰＲ映像|プロモーション/;

/* 撮影が入る合図。本文に出たら「撮影あり」と見なす。
   確実ではないので、最終判断は仕様書を開いて行う */
const SHOOT = /撮影|ロケ|収録|カメラマン|出演者|キャスティング|取材/;
/* 撮影が無いと言い切っている書き方。これだけが確かな手がかり */
const NO_SHOOT = /撮影は行わない|撮影を伴わ(?:ない|ず)|撮影なし|撮影は不要/;
/* 実写でない気配。ただし「CG制作を含む動画制作」のように、
   撮影が無いとは言っていない書き方も混ざるので、断定には使わない */
const NOT_LIVE = /アニメーション|モーショングラフィック|イラスト|ＣＧ|CG制作|CG映像|既存の素材|提供(?:する|される)素材|素材は.{0,6}貸与/;

/* 本文の語から撮影の有無を当てる。
   PDF から抜いた文字は「撮 影」のように字間が空くので、空白は落としてから見る */
const judge = (raw) => {
    const text = String(raw).replace(/\s+/g, '');
    if (NO_SHOOT.test(text)) return 'なし（明記）';
    if (SHOOT.test(text)) return NOT_LIVE.test(text) ? '両方の語あり' : 'あり';
    if (NOT_LIVE.test(text)) return 'なしの可能性';
    return '不明';
};

const tag = (xml, name) => {
    const m = xml.match(new RegExp(`<${name}>(?:<!\\[CDATA\\[)?([\\s\\S]*?)(?:\\]\\]>)?</${name}>`));
    return m ? m[1].trim() : '';
};

export async function search(query) {
    const res = await fetch(`${API}?Query=${encodeURIComponent(query)}`, { headers: { 'User-Agent': UA } });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const xml = await res.text();
    const blocks = xml.split('<SearchResult>').slice(1);
    if (blocks.length === 0) throw new Error('0件。API の形式が変わった可能性');
    return blocks.map((b) => ({
        name: tag(b, 'ProjectName'),
        org: tag(b, 'OrganizationName'),
        pref: tag(b, 'PrefectureName'),
        date: tag(b, 'CftIssueDate').slice(0, 10),
        url: tag(b, 'ExternalDocumentURI'),
        shoot: judge(tag(b, 'ProjectDescription')),
    }));
}

/* 仕様書はたいてい PDF なので、読めるなら読む。pdfjs-dist が無ければ諦める */
let pdfjs = null, pdfjsTried = false;
async function loadPdfjs() {
    if (pdfjsTried) return pdfjs;
    pdfjsTried = true;
    const paths = [process.env.PDFJS, 'pdfjs-dist/legacy/build/pdf.mjs', 'pdfjs-dist/build/pdf.mjs'];
    for (const p of paths.filter(Boolean)) {
        try { pdfjs = await import(p); return pdfjs; } catch { /* 次を試す */ }
    }
    return null;
}

async function pdfText(buf) {
    const lib = await loadPdfjs();
    if (!lib) return null;
    const doc = await lib.getDocument({
        data: new Uint8Array(buf), useSystemFonts: true, verbosity: 0,
    }).promise;
    let out = '';
    for (let i = 1; i <= doc.numPages; i++) {
        const c = await (await doc.getPage(i)).getTextContent();
        out += c.items.map((it) => it.str).join('') + '\n';
    }
    return out;
}

const grab = (url) => fetch(url, { headers: { 'User-Agent': UA }, signal: AbortSignal.timeout(30000) });

/* PDF を読んで文字を返す。読めなければ null、スキャン画像なら '' */
async function readPdf(res) {
    const text = await pdfText(await res.arrayBuffer());
    if (text === null) return null;
    return text.replace(/\s/g, '').length < 80 ? '' : text;
}

/* 公告ページに貼られた仕様書などを拾う。撮影の有無は公告本文ではなく
   仕様書に書いてあることが多いので、そこまで辿らないと判定できない */
const SPEC_NAME = /仕様|shiyou|shiyousyo|要領|youkou|youryou|公告|koukoku|募集|bosyu|bosyuu|企画/i;
function specLinks(html, base) {
    const out = [];
    for (const m of html.matchAll(/href="([^"]+\.(?:pdf|PDF))"/g)) {
        const u = new URL(m[1], base).href;
        if (!out.includes(u)) out.push(u);
    }
    // 名前から仕様書らしいものを先に見る
    return out.sort((a, b) => Number(SPEC_NAME.test(b)) - Number(SPEC_NAME.test(a))).slice(0, 4);
}

/** リンク先まで開いて判定し直す。PDF は pdfjs-dist があれば読む。
    HTML の公告ページなら、貼られている仕様書 PDF も開く。
    画像だけの PDF（スキャン）は文字が取れないので、そこは人が開く */
export async function classify(row) {
    try {
        const res = await grab(row.url);
        if (!res.ok) return { ...row, shoot: `取得できず(${res.status})` };
        const type = res.headers.get('content-type') || '';

        if (/pdf/i.test(type) || /\.pdf$/i.test(row.url)) {
            const text = await readPdf(res);
            if (text === null) return { ...row, shoot: 'PDF（要確認）' };
            if (text === '') return { ...row, shoot: 'PDF画像（要確認）' };
            return { ...row, shoot: judge(text) };
        }

        const html = await res.text();
        const plain = html
            .replace(/<script[\s\S]*?<\/script>|<style[\s\S]*?<\/style>/g, '')
            .replace(/<[^>]+>/g, ' ');
        const first = judge(plain);
        if (first !== '不明') return { ...row, shoot: first };

        // 公告ページ本文では分からなかったので、貼られた PDF を開く
        for (const link of specLinks(html, row.url)) {
            try {
                const r = await grab(link);
                if (!r.ok) continue;
                const text = await readPdf(r);
                if (!text) continue;
                const v = judge(text);
                if (v !== '不明') return { ...row, shoot: v, from: link };
            } catch { /* 次の PDF へ */ }
        }
        return { ...row, shoot: '不明' };
    } catch (e) {
        return { ...row, shoot: `取得できず(${String(e.message).slice(0, 20)})` };
    }
}

if (import.meta.url === `file://${process.argv[1]}`) {
    const args = process.argv.slice(2);
    const asJson = args.includes('--json');
    const showAll = args.includes('--all');
    const queries = args.filter((a) => !a.startsWith('--'));
    const seen = new Map();
    for (const q of (queries.length ? queries : DEFAULT_QUERIES)) {
        for (const r of await search(q)) {
            if (!IS_VIDEO.test(r.name)) continue;
            if (!seen.has(r.url)) seen.set(r.url, r);
        }
    }
    let rows = [...seen.values()].sort((a, b) => b.date.localeCompare(a.date));
    if (args.includes('--deep')) {
        rows = [];
        for (const r of [...seen.values()].sort((a, b) => b.date.localeCompare(a.date))) {
            rows.push(await classify(r));
        }
    }
    const total = rows.length;
    if (!showAll) rows = rows.filter((r) => r.shoot !== 'あり');
    if (asJson) { console.log(JSON.stringify(rows, null, 2)); }
    else {
        console.log(`動画の案件 ${total}件${showAll ? '' : ` / うち撮影ありを除いて ${rows.length}件`}\n`);
        for (const r of rows) {
            console.log(`${r.date}  [撮影 ${r.shoot}]  ${r.name}`);
            console.log(`            ${r.pref} ${r.org}`);
            console.log(`            ${r.url}`);
            if (r.from) console.log(`            └ 判定に使った仕様書 ${r.from}`);
        }
        const unknown = rows.filter((r) => r.shoot === '不明').length;
        console.log(`\n※ 撮影の有無は本文の語から推測しただけ。応札するかの判断は仕様書を開いてから。`);
        console.log(`※ リンク先はたいてい入札公告で、撮影の記載がない。今回も ${unknown}件が「不明」。`);
        console.log('　 リンク先が HTML のページなら、そこに貼られた仕様書 PDF まで開いて判定している。');
        console.log('　 リンク先が PDF そのものの場合、仕様書の在り処は分からない。そこは人が発注者のページを開く。');
        if (args.includes('--deep') && !pdfjs) console.log('※ pdfjs-dist が無いので PDF は読めていない（npm i pdfjs-dist で読める）。');
        console.log('※ so. はまだ入札できない（開業届と入札参加資格の登録が要る）。');
    }
}
