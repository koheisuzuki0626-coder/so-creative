/* 通過率の計測。2026-09-23 に index.html から切り出した。
   トップと料金ページの両方が読む。track はここにしか置かない
   （同じものを2つ持つと、片方だけ直したときに数が合わなくなる）。 */
        /* ===== 料金計算機の段差(ファネル計測) =====
           料金表を公開しているので、高いと感じた人は連絡せずに閉じる。
           そのままでは「誰が価格で諦めたか」が一切残らないため、
           計算機の通過点にだけ印を打つ。氏名・メールなどは一切送らない。

           見たいのはこの差:
             calc_use  … 自分で条件を変えた ＝ 具体的に検討した人
             calc_cta  … 相談ボタンまで進んだ人
           この2つの人数の差が、価格で落ちた人数。
           calc_leave に離脱時の組み合わせが入るので、
           「松を見た人だけが落ちている」のか「全体的に落ちている」のかまで分かる。

           送信先: ANALYTICS_ID に GA4 の測定ID(G-XXXXXXX)を入れると送信が始まる。
           空のままなら外部には一切送らず、Cookie も置かない。
           入れる前にプライバシーポリシーを用意すること(README 参照)。
           記録はいつでも localStorage に残るので、
           開発者コンソールで soFunnel() と打てば手元で表にして確認できる。
           ただし見えるのは自分のブラウザの分だけ。
           訪問者ぶんを集めるには ANALYTICS_ID が要る。 */
        const ANALYTICS_ID = 'G-21JRKTWE3V';

        /* 計測IDが入っているときだけ gtag.js を読み込む。
           空なら script も足さないので、外部への通信も Cookie も発生しない。
           入れる前に privacy.html の「Cookie・アクセス解析」を書き換えること
           （使っていないと書いたまま送り始めると、書いてあることと違う） */
        if (ANALYTICS_ID) {
            const g = document.createElement('script');
            g.async = true;
            g.src = `https://www.google${''}tagmanager.com/gtag/js?id=${encodeURIComponent(ANALYTICS_ID)}`;
            document.head.append(g);
            window.dataLayer = window.dataLayer || [];
            window.gtag = function gtag() { window.dataLayer.push(arguments); };
            window.gtag('js', new Date());
            /* IPの下位を伏せる。日本国内向けでも、取る必要のない情報は取らない */
            window.gtag('config', ANALYTICS_ID, { anonymize_ip: true });
        }

        /* 保存キーを社名に合わせて変えた（2026-09-23）。ただの改名で
           これまでの記録を捨てると、通過率が断絶して比べられなくなる。
           古いキーが残っていたら1度だけ引き継いで、古いほうは消す。 */
        (() => {
            try {
                const prev = localStorage.getItem('so.funnel');
                if (!prev) { return; }
                if (!localStorage.getItem('so-creative.funnel')) {
                    localStorage.setItem('so-creative.funnel', prev);
                }
                localStorage.removeItem('so.funnel');
            } catch { /* noop */ }
        })();

        /* いま見ているページ。どの入口から入ったかを残すために送る。
           ファイル名だけにする（ディレクトリやクエリは要らない） */
        const PAGE = (location.pathname.split('/').pop() || 'index.html');

        /* 1回の訪問をまとめるための印。
           2026-09-24：sessionStorage に持たせた。サイトが複数ページに分かれたあと、
           読み込みごとに振り直していたので、トップ→料金 と進んだ1人が
           「別人2人」として数えられていた。分母（訪問）と分子（条件を選んだ）が
           別ページのものになり、通過率が構造的に低く出ていた。
           sessionStorage はタブを閉じるまで残るので、「同じタブの中＝1訪問」になる。
           使えない環境（プライベートモード等）では、これまでどおりページ単位に落ちる */
        const SID = (() => {
            const KEY = 'so-creative.sid';
            const mk = () => Math.random().toString(36).slice(2, 10);
            try {
                const had = sessionStorage.getItem(KEY);
                if (had) { return had; }
                const made = mk();
                sessionStorage.setItem(KEY, made);
                return made;
            } catch { return mk(); }
        })();

        const track = (() => {
            const LOG = 'so-creative.funnel';
            const push = (row) => {
                try {
                    const a = JSON.parse(localStorage.getItem(LOG) || '[]');
                    a.push(row);
                    localStorage.setItem(LOG, JSON.stringify(a.slice(-300)));
                } catch { /* プライベートモード等では黙って諦める */ }
            };
            return (name, params = {}) => {
                push({ t: new Date().toISOString(), s: SID, p: PAGE, name, ...params });
                /* page_view は gtag('config') が自分で送るので、こちらからは送らない。
                   両方送ると GA4 側で訪問が2回数えられ、以降の通過率が全部ずれる。
                   手元の localStorage には残すので、通過率を見るページの母数は変わらない */
                if (name !== 'page_view' && typeof window.gtag === 'function') {
                    window.gtag('event', name, { ...params, transport_type: 'beacon' });
                }
            };
        })();

        /* 手元で確認するための表示。コンソールで soFunnel() と打つ。
           localStorage に溜まった記録を、訪問単位で数えて出す */
        window.soFunnel = () => {
            let rows = [];
            try { rows = JSON.parse(localStorage.getItem('so-creative.funnel') || '[]'); } catch { /* noop */ }
            const yen = (n) => `¥${Number(n).toLocaleString('ja-JP')}`;
            if (!rows.length) {
                console.log('まだ記録がありません。「料金」まで進んで、尺か本数を選んでから、もう一度 soFunnel() と打ってください。');
                return;
            }
            const uniq = (name) => new Set(rows.filter((r) => r.name === name).map((r) => r.s)).size;
            const visit = uniq('page_view'), plans = uniq('plans_view');
            const use = uniq('calc_use'), cta = uniq('calc_cta');
            const pct = (a, b) => (b ? `${Math.round((a / b) * 100)}%` : '—');
            const bar = (n) => '█'.repeat(Math.round((visit ? n / visit : 0) * 20)) || '·';
            const steps = [
                ['1. 訪問',           visit, '—'],
                ['2. 料金を見た',     plans, pct(plans, visit)],
                ['3. 条件を変えた',   use,   pct(use, plans)],
                ['4. 相談まで進んだ', cta,   pct(cta, use)],
            ];
            // console.table が読みづらい環境もあるので、文字でも出す
            console.log('%c so-creative ファネル ', 'background:#1d1d1f;color:#d9b45f;font-weight:600');
            steps.forEach(([name, n, p]) => {
                console.log(`${name.padEnd(16, '　')} ${String(n).padStart(4)}人  ${String(p).padStart(4)}  ${bar(n)}`);
            });
            const lost = use - cta;
            console.log(`\n価格で落ちた人：${lost}人（検討した ${use}人 のうち ${pct(lost, use)}）`);
            const bail = rows.filter((r) => r.name === 'calc_leave' && !r.cta && r.total);
            if (bail.length) {
                console.log('相談せずに閉じたときの金額:');
                bail.forEach((r) => console.log(`  ${r.sec}秒 × ${r.count}本 → ${yen(r.total)}`));
            }
            console.log('生ログは soFunnel.raw() で見られます。soFunnel.clear() で消せます。');
            return undefined;
        };
        window.soFunnel.raw = () => {
            try { return JSON.parse(localStorage.getItem('so-creative.funnel') || '[]'); } catch { return []; }
        };
        window.soFunnel.clear = () => {
            try { localStorage.removeItem('so-creative.funnel'); } catch { /* noop */ }
            console.log('記録を消しました。');
        };

        /* どこまで読んで帰ったかを残す。料金だけ見ていても
           「料金を見なかった人がどこで止まったか」が分からないので、
           節ごとに1回だけ記録する。plans_view は母数として残す（既存の集計が使う）。
           並びは通過率のページ（funnel.html）の段と同じにすること */
        const SECTIONS = ['service', 'why', 'genres', 'works', 'process', 'plans', 'faq', 'contact'];
        /* そのページに実際に置かれている節だけ。
           2026-09-24：ページが分かれたので、「読まずに帰った節」と
           「そもそもそのページに無い節」を取り違えないように、一緒に送る。
           例：料金ページを直接開いた人には plans しか無い。
           その手前の節まで到達したことにしてはいけない */
        const PRESENT = SECTIONS.filter((id) => document.getElementById(id));

        // 訪問そのもの。ここが母数になる
        track('page_view', { secs: PRESENT.join(',') });

window.soTrack = track;

        if ('IntersectionObserver' in window) {
            const seen = new Set();
            const io = new IntersectionObserver((es) => {
                for (const e of es) {
                    if (!e.isIntersecting) continue;
                    const id = e.target.id;
                    if (seen.has(id)) continue;
                    seen.add(id);
                    track('section_view', { id });
                    if (id === 'plans') track('plans_view');
                    io.unobserve(e.target);
                }
            /* threshold ではなく rootMargin で見る。つくれる動画の節は 4,000px 以上あり、
               画面に 25% 入りきらないので threshold だと一生発火しない。
               下を 20% 削って「画面の上 80% に入ったら到達」とする */
            }, { threshold: 0, rootMargin: '0px 0px -20% 0px' });
            for (const id of PRESENT) {
                io.observe(document.getElementById(id));
            }
        }
