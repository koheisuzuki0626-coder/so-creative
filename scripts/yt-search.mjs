#!/usr/bin/env node
// YouTube の検索結果を実データで取る。
//
// 【なぜ要るか】
// 市場調査を「相場まとめ記事」（一括見積もりサイトの集客記事）から
// 組み立てると、出どころも母数も書いていない数字を並べることになる。
// 実際に公開されている動画なら、再生数も投稿日もチャンネルも
// その場で確認できる。検算できる数字だけで話すための道具。
//
// fetch-youtube.mjs と同じく ytInitialData を読む。公式APIの鍵が要らない
// 代わりに YouTube のフロントエンド実装に依存するので、壊れたら
// 「0件」ではなく例外で止める（静かに空の結果を返さない）。
//
// 使い方:
//   node scripts/yt-search.mjs "AIミュージックビデオ"
//   node scripts/yt-search.mjs --works "AI MV"     # 作り方・解説を除く
//   node scripts/yt-search.mjs --json "細川たかし"  # JSON で出す

const UA = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 '
    + '(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36';

/* 作品ではなく「作り方」の動画を外すための語。
   AI 系の検索は解説動画が上位を埋めるので、これが無いと
   作品の分布を見誤る（実測：20件中12件が解説だった） */
const HOWTO = /作り方|方法|使い方|解説|徹底|完全|やってみた|作ってみた|紹介|比較|おすすめ|講座|入門|網羅|フル活用|見せます|極意|まとめ|最新版|丸投げ|最強|神ツール/;

const MONTHS = { 分: 0, 時間: 0, 日: 1 / 30, 週間: 7 / 30, か月: 1, 年: 12 };

/** 「8 か月前」→ 8（月）。並べ替えと月あたり再生数に使う */
export function agoInMonths(text) {
    const m = String(text || '').match(/(\d+)\s*(分|時間|日|週間|か月|年)/);
    if (!m) return null;
    return Number(m[1]) * MONTHS[m[2]];
}

export async function ytSearch(query) {
    const url = `https://www.youtube.com/results?search_query=${encodeURIComponent(query)}`;
    const res = await fetch(url, { headers: { 'User-Agent': UA, 'Accept-Language': 'ja-JP,ja;q=0.9' } });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const html = await res.text();
    const m = html.match(/var ytInitialData = (\{.+?\});<\/script>/s);
    if (!m) throw new Error(`ytInitialData が見つからない（${html.length}B）。実装が変わった可能性`);

    const out = [];
    const walk = (node) => {
        if (!node || typeof node !== 'object') return;
        const v = node.videoRenderer;
        if (v) {
            const views = Number(String(v.viewCountText?.simpleText || '').replace(/[^\d]/g, '')) || null;
            const months = agoInMonths(v.publishedTimeText?.simpleText);
            out.push({
                title: v.title?.runs?.[0]?.text || '',
                channel: v.ownerText?.runs?.[0]?.text || '',
                views,
                ago: v.publishedTimeText?.simpleText || '',
                months,
                perMonth: views && months ? Math.round(views / months) : null,
                length: v.lengthText?.simpleText || '',
                url: v.videoId ? `https://www.youtube.com/watch?v=${v.videoId}` : '',
            });
        }
        for (const k in node) walk(node[k]);
    };
    walk(JSON.parse(m[1]));
    if (out.length === 0) throw new Error('1件も取れなかった。実装が変わった可能性');
    return out;
}

export const worksOnly = (rows) => rows.filter((r) => !HOWTO.test(r.title));

if (import.meta.url === `file://${process.argv[1]}`) {
    const args = process.argv.slice(2);
    const asJson = args.includes('--json');
    const onlyWorks = args.includes('--works');
    const query = args.filter((a) => !a.startsWith('--')).join(' ');
    if (!query) {
        console.error('使い方: node scripts/yt-search.mjs [--works] [--json] "検索語"');
        process.exit(1);
    }
    const all = await ytSearch(query);
    const rows = onlyWorks ? worksOnly(all) : all;
    if (asJson) {
        console.log(JSON.stringify(rows, null, 2));
    } else {
        console.log(`"${query}"  ${rows.length}件${onlyWorks ? `（解説を除く／全${all.length}件）` : ''}\n`);
        for (const r of rows) {
            const v = r.views ? r.views.toLocaleString('ja-JP') : '—';
            const pm = r.perMonth ? `${r.perMonth.toLocaleString('ja-JP')}/月` : '';
            console.log(`${v.padStart(12)}回  ${String(r.ago).padEnd(8)}${pm.padStart(12)}  ${r.length.padStart(6)}  ${r.title}`);
            console.log(`${' '.repeat(14)}${r.channel}  ${r.url}`);
        }
    }
}
