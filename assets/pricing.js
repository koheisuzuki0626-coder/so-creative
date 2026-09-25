/* 料金シミュレーター。2026-09-23 に index.html から切り出した。
   料金で検索して来た人が最初に着くのは pricing.html なので、計算機もそちらに置く。
   二重に持つと式が食い違うため、index には残していない。
   track は assets/funnel.js が先に定義する（読み込み順に依存する）。 */
(() => {
const track = window.soTrack || (() => {});
        /* ---------- 料金シミュレーター ----------
           料金 = 基本料金 ¥90,000 + 秒単価×合計秒数 + ¥65,000×(本数-1) + ナレーション調整
           工数 = 3.0h + 0.15h×倍率×合計秒数 + 1.5h×(本数-1) + 1.0h×ナレーション本数

           尺とナレーションは本ごとに選ぶ（2026-09-22）。ナレーション調整は2つだけ。
             1. 人物（1名の手配）は、1本でも使えば +¥70,000。本数では増えない。
                松は秒単価に1名ぶんが溶けているので ±0。どの本にも人の声を
                入れないなら、ナレーターの手配ぶん −¥25,000 を返す
                （画面に出る登場人物の数とは無関係）
             2. ナレーションを入れない本は、1本につき −¥25,000
           1本だけのときは 9/19 までと同じ額（梅 なし −25,000／人物 +70,000、
           松 AI −25,000／なし −50,000）。工数は「ナレーションを入れた本の数」で、
           松で人物を使うときだけ、秒単価に溶けている1本ぶんを引く。

           価格は市場向けの値（受注ゼロで「高くて落ちた」データがまだ無いので動かさない）。
           工数は 2026-09-15 の実測（想工業・60秒 松相当 10.5h ＋ 15秒版 1.0h）に、
           実案件の打合せ・素材待ち・要件の揺れを見込んで約1.5倍の安全率をかけたもの。
           どの組み合わせでも時間単価 ¥23,000/h（e2e の RATE）を割らないことを
           tests/pricing.mjs で確かめている。数字を動かすときは必ず通すこと。

           仕上げの段階(梅/竹/松)は、秒単価と工数の両方に倍率をかける。
             工数の倍率 梅1.0 / 竹1.22 / 松1.36 … 実測の工程別内訳から
               竹 ＝ 梅 ＋ キャラクターシート(1.0h) ＋ 修正1回(0.6h)
               松 ＝ 竹 ＋ ナレーション(1.0h。ただし1本目だけ。2本目以降は加算する)
             ナレーションは AI と人物のどちらかを選ぶ（2026-09-17）。
             **AIナレーションは料金に含める。**合成音声なのでクレジットは約5（¥25）で、
             かかるのは実測 1.0h（原稿・声の選定・配置）だけ。
             ここを有料にすると「声を入れたいだけ」の相談を落とす。
             ただし**日本語の合成音声は4エンジン×9声を試して不採用にした**ので、
             「機械の声だと分かる」と明記する。サンプルの音声もAIだと書く。
             人物ナレーション 1名 ¥70,000〜 は、ナレーターへの外注費 ＋ 同じ 1.0h。
             1人が複数本読んでも手配は1回なので、本数では増えない。
             **ナレーションを入れない本は、1本につき ¥25,000 を差し引く**（全段）。
             込みにしているものを使わないので返す形。3万にすると
             梅15秒×1本だけ ¥21,429/h（目標の93.2%）で下限を割るため 2.5万。
             松の人物ぶんは秒単価に溶けているが、返すのは「手配1回ぶん」なので
               本数では増えない。工数は尺ではなく本数で増えるので、
               松も2本目以降のナレーションは加算する
               （足さないと 竹＋ナレ > 松 という逆転が5通り出る）。
             4K は書かない（2026-09-16）。素材の生成そのものが 1080p（Seedance 2.5・9クレジット/秒）で、
               4K は完成した1080pにアップスケーラ（Bytedance Upscale・1.2クレジット）をかけただけ。
               原価が安いのは処理が軽いからで、中身が増えていないことの裏返し。
               納品先（採用サイト・55インチ）はどちらも1080pで足りる。
             価格の倍率 1.0 / 1.4 / 1.9 は据え置きなので、上の段ほど時間単価が高い。

           段の中身は使う機能そのもの。1回の生成は4〜15秒しかつくれないため、
           尺が伸びるとカット数が増え、工数もクレジットも尺に比例する。
           クレジット原価は 41cr/秒 ≒ ¥310/秒（追加購入単価）で、松の秒単価の5%。
           実績は納品物 2,462cr ÷ 74秒（本編59秒＋展示会用15秒）＝ 33cr/秒。
           本編の尺だけで割った 41 を安全側として採っている。 */
        const PRICE = { base: 90000, perExtra: 65000, narrationAi: 0, narrationHuman: 70000,
            /* AIナレーションは料金に含まれているので、使わないなら返す。梅・竹だけ。
               松は人物ナレーションが込みで、これは秒単価に溶けているので対象外。
               3万にすると梅15秒×1本だけ ¥21,429/h（目標の93.2%）で下限を割るため 2.5万 */
            noNarration: 25000,
            /* 松は人物ナレーション1名が込み。これも外せるようにした（9/19）。
               返す額は「いちばん短い尺でも時間単価の下限を割らない額」で決まる。
               松の秒単価に溶けている人物ぶんは尺に比例するので、短い尺ほど溶けている額が
               小さく、¥70,000 をそのまま返すと 15秒×1本で ¥16,962/h（目標の73.7%）になる。
               AIに替える -2.5万／使わない -5万 なら、全24通りで最低 ¥23,061/h（100.3%） */
            /* 松の人物ぶんを返すのは「手配1回ぶん」なので、本数では増えない。
               1本だけでナレーションも入れないなら、これに noNarration が乗って
               合計 −¥50,000 になる（9/19 までと同じ額） */
            matsuToAi: 25000 };
        /* 段の説明は「お客様が受け取るもの」で書く。
           生成回数のような内部の手順は、多くて嬉しいものか分からないうえ、
           お客様には確かめようがないので出さない(工数の根拠としては README に残す)。
           ここに並ぶのは全部、納品物を見れば確認できるものにしてある。 */
        /* 段の違いは「人が出るか」「何人まで出せて、ナレーションが込みか」の2つだけ。
           AIナレーションは全段とも料金に含む。人物ナレーションは 1名 ¥70,000〜（松は1名込み）。
           画質は全段共通（1080p）。4K はサイトに書かない（上記）。画面の向きは案件ごとに設計する。
           解像度や書き出し形式で差をつけるのはやめた。手間が増えないものに
           価格差をつけると、値付けの根拠ではなく口実になるため */
        const TIERS = [
            { id: 'ume', label: '梅', sub: '標準', perSec: 3500, hours: 1.0, narration: false,
              detail: '登場人物なし（設備・製品・空間を中心に構成） ／ AIナレーションは料金に含まれます（本ごとに選べます。入れない本は1本につき −¥25,000／人物ナレーションは1名 ¥70,000〜で、何本に入れても1名ぶん） ／ 修正2回まで ／ 1080p（フルHD）で納品',
              use: 'SNS 投稿・社内共有・製品やサービスの紹介' },
            { id: 'take', label: '竹', sub: '上', perSec: 4900, hours: 1.22, narration: false,
              detail: '登場人物2人まで（同じ人物を最後まで同じ顔で出せます） ／ AIナレーションは料金に含まれます（本ごとに選べます。入れない本は1本につき −¥25,000／人物ナレーションは1名 ¥70,000〜で、何本に入れても1名ぶん） ／ 修正3回まで ／ 1080p（フルHD）で納品',
              use: '採用サイト・会社紹介・サービス紹介' },
            { id: 'matsu', label: '松', sub: '特上', perSec: 6650, hours: 1.36, narration: true,
              detail: '登場人物3人まで（4人以上は個別にお見積り） ／ 人物ナレーション込み（1名。声を選び、話す速さまで調整します。2人目は別途お見積り／ナレーションは本ごとに選べます。どの本にも人の声を入れないなら −¥25,000、ナレーションを入れない本は1本につきさらに −¥25,000） ／ 修正3回まで ／ 1080p（フルHD）で納品',
              use: '展示会での上映・ブランド映像・じっくり見せたい会社紹介' },
        ];
        const LENGTHS = [
            { sec: 15,  label: '15秒' },
            { sec: 30,  label: '30秒' },
            { sec: 45,  label: '45秒' },
            { sec: 60,  label: '60秒' },
            { sec: 90,  label: '90秒' },
            { sec: 120, label: '2分' },
            { sec: 180, label: '3分' },
            { sec: 300, label: '5分' },
        ];
        /* 以前は「合計の尺」を「本数」で割る形だったので、1本が短くなりすぎないよう
           本数に上限を置いていた（countCap）。9/22 に本ごとに尺を選ぶ形へ変えたので、
           1本あたりは必ず15秒以上になり、上限そのものが要らなくなった */

        /* 納期は工数から出す。固定の早見表にすると、尺が伸びたときに
           実際の手間より長い数字を出してしまう(3分48hで5週間など)。

             納期 = 工数 ÷ 週に充てられる時間 ＋ 確認の往復
             LEAD_WEEK_HOURS … 1本に集中して充てられる週あたりの時間。
                               年間の制作可能時間 1,373h ÷ 46週 ≒ 30h のうち、
                               主軸の1本に充てるぶん
             LEAD_REVIEW     … 構成案・絵コンテ・初稿チェックの往復ぶん
             最低2週間        … どんなに短くてもこの往復は縮まらない

           仕上げの段階で工数が変わるので、納期も段によって変わる。
           修正を3回とも使う場合は、別途1回1週間ほど見てもらう(本文に明記) */
        const LEAD_WEEK_HOURS = 25, LEAD_REVIEW = 1;
        const HOURS = { base: 3.0, perSec: 0.15, perExtra: 1.5, narration: 1.0 };   // 工数モデル（実測×約1.5）。tests/lib.mjs と同じ値
        /* 2026-09-24：本数ぶんの 1.5h/本 を足し忘れていて、複数本のときだけ
           納期を短く見せていた（工数モデルには入っているのに納期だけ落ちていた）。
           この式は上の「工数」の定義と1対1で対応させること */
        const leadWeeks = (sec, t, narN = 0, n = 1) =>
            Math.max(2, Math.round((HOURS.base + HOURS.perSec * t.hours * sec
                + HOURS.perExtra * (n - 1) + HOURS.narration * narN) / LEAD_WEEK_HOURS + LEAD_REVIEW));
        const leadTime = (sec, t, narN, n) => `約${leadWeeks(sec, t, narN, n)}週間`;
        const yen = (n) => `¥${n.toLocaleString('ja-JP')}`;
        /* 合計は選択肢に無い秒数になりうる（120+90=210秒など）ので、その場で組み立てる */
        const secLabel = (sec) => {
            const hit = LENGTHS.find((l) => l.sec === sec);
            if (hit) return hit.label;
            const m = Math.floor(sec / 60), r = sec % 60;
            return m ? (r ? `${m}分${r}秒` : `${m}分`) : `${sec}秒`;
        };

        /* 2026-09-24：1ページに1台の作りだったのを、何台でも置けるようにした。
           つくれる動画のジャンルごとに、その尺を入れた計算機を置くため。

           台ごとに変えたのは3つ。
             1. DOM の参照を id から、計算機の中の data-c にした
                （id はページに1つしか置けない）
             2. ラジオの name に台ごとの印を付けた
                （同じ name だと、別の台で選んだものが連動して外れる）
             3. ファネルの記録に where を足した
                （どの計算機で触ったのかが分からないと、通過率が読めない）

           器が空のときは JS で組み立てる。料金ページは自前の器を持っているので
           そのまま使い、ジャンルの側は <div class="calc" data-calc-len="60"> だけ置く。 */
        const shellHtml = (uid) => `
            <div class="calc-picks">
                <div class="calc-row">
                    <p class="calc-label" id="calc-tier-label-${uid}"><span class="calc-step">1</span>仕上げの段階を選ぶ</p>
                    <div class="calc-opts" role="radiogroup" aria-labelledby="calc-tier-label-${uid}" data-c="tier"></div>
                    <p class="calc-hint" data-c="tier-hint"></p>
                </div>
                <div class="calc-row">
                    <p class="calc-label" id="calc-cnt-label-${uid}"><span class="calc-step">2</span>何本つくるかを選ぶ</p>
                    <div class="calc-opts" role="radiogroup" aria-labelledby="calc-cnt-label-${uid}" data-c="cnt"></div>
                    <p class="calc-hint" data-c="cnt-hint"></p>
                </div>
                <div class="calc-row">
                    <p class="calc-label" id="calc-len-label-${uid}"><span class="calc-step">3</span>それぞれの尺とナレーションを選ぶ</p>
                    <div class="calc-lens" data-c="len"></div>
                    <p class="calc-hint" data-c="len-hint"></p>
                    <p class="calc-hint" data-c="nar-hint"></p>
                </div>
            </div>
            <div class="calc-out">
                <p class="calc-out-head">お見積り</p>
                <p class="calc-total"><span data-c="total">¥195,000</span><small>税込</small></p>
                <dl class="calc-break">
                    <div><dt>基本料金</dt><dd data-c="base">¥90,000</dd></div>
                    <div><dt data-c="len-dt">尺</dt><dd data-c="lenfee">¥0</dd></div>
                    <div><dt data-c="cnt-dt">本数 1本</dt><dd data-c="cntfee">¥0</dd></div>
                    <div><dt data-c="nar-dt">ナレーション</dt><dd data-c="narfee">¥0</dd></div>
                </dl>
                <p class="calc-lead">納品目安 <strong data-c="lead-v">約2週間</strong></p>
                <div class="calc-actions">
                    <a href="mailto:" class="pill pill-solid calc-cta" data-c="mail">この内容で相談する</a>
                    <button type="button" class="calc-copy" data-c="copy">内容をコピー</button>
                </div>
                <p class="calc-note" data-c="copy-msg">メールソフトが開き、選んだ内容が本文に入ります。</p>
            </div>`;

        document.querySelectorAll('.calc').forEach((el, i) => setupCalc(el, i));

        function setupCalc(calc, ci) {
            /* 2026-09-25：pricing.js を2回読んでいるページがあり、同じ器を2回組み立てて
               段と本数の選択肢が二重に生えていた。読み込み側は直したが、
               ここでも一度組んだ器には印を付けて、二度目は何もしない */
            if (calc.dataset.calcReady === '1') { return; }
            calc.dataset.calcReady = '1';
            const uid = calc.dataset.calcId || `c${ci}`;
            if (!calc.querySelector('[data-c="tier"]')) calc.innerHTML = shellHtml(uid);
            const q = (k) => calc.querySelector(`[data-c="${k}"]`);
            /* どの計算機で触ったのか。ジャンルの側は data-calc-where に
               そのジャンルの id を入れる。料金ページは 'plans' */
            const where = calc.dataset.calcWhere || 'plans';
            const lenBox = q('len');
            const lenHint = q('len-hint');
            const cntBox = q('cnt');
            const cntHint = q('cnt-hint');
            /* 本ごとの尺（秒）。長さが本数、合計が尺の合計。
               料金は base + 秒単価 × 合計秒数 + ¥65,000 × (本数 − 1) なので、
               どう割り振っても合計が同じなら金額は変わらない。
               変わるのは「何を何秒で作るか」が相手に伝わるかどうか */
            /* 置いた場所の尺で始める。ジャンルの計算機は、そのサンプルの実尺 */
            const initLen = Number(calc.dataset.calcLen) || 30;
            let lens = [initLen];
            /* 本ごとのナレーション。lens と同じ長さで、同じ添字が同じ本を指す。
               'none' | 'ai' | 'human' */
            let nars = [];   // tier が決まってから defaultNar で埋める
            const MAX_COUNT = 6;
            const totalSec = () => lens.reduce((a, b) => a + b, 0);
            let tier = TIERS.find((t) => t.id === calc.dataset.calcTier) || TIERS[0];
            /* 初期は 'ai'。AIナレーションは料金に含まれているので、これが素の状態。
               'none' を初期にすると表示額が差し引き後になり、
               「AIは込み」と言いながら AI を選ぶと上がる見え方になる */

            /* 段によってナレーションの意味が違う（松は人物1名込み、梅・竹はAI込み）ので、
               段を変えたら既定に戻す。持ち越すと、松を選んだのに人物ぶんが
               引かれた額が出る、という分かりにくい状態になる */
            const defaultNar = (t) => (t.narration ? 'human' : 'ai');
            /* 段が決まってから埋める。松で始める計算機なら 'human'、梅・竹なら 'ai' */
            nars = lens.map(() => defaultNar(tier));
            let summary = '';
            // 段差の状態。used=自分で条件を変えた / cta=相談ボタンまで進んだ
            let used = false, cta = false, resultTimer;

            // 送信先はお問い合わせ欄のリンクを唯一の出どころにする(二重管理を避ける)
            const mailLink = q('mail');
            const mailAddr = (document.querySelector('.cta-mail')?.getAttribute('href') || '')
                .replace(/^mailto:/, '') || mailLink.getAttribute('href').replace(/^mailto:/, '');
            if (!mailAddr) { return; }   // 宛先が分からない器は動かさない（空のメールを出さない）

            // 実物のラジオボタンで組む。丸が見えることで「選ぶところ」だと分かる
            function makeOpt(text, box, group, value, onPick) {
                const label = document.createElement('label');
                label.className = 'calc-opt';
                const input = document.createElement('input');
                input.type = 'radio';
                input.name = group;
                input.value = String(value);
                const dot = document.createElement('span');
                dot.className = 'calc-dot';
                dot.setAttribute('aria-hidden', 'true');
                const text_ = document.createElement('span');
                text_.className = 'calc-opt-t';
                text_.dataset.narText = '';
                text_.textContent = text;
                label.append(input, dot, text_);
                input.addEventListener('change', () => { if (input.checked) onPick(); });
                box.append(label);
                return { label, input };
            }

            const tierBox = q('tier');
            const tierHint = q('tier-hint');
            TIERS.forEach((t) => {
                const o = makeOpt(`${t.label} ${t.sub}`, tierBox, `calc-tier-${uid}`, t.id,
                    () => { tier = t; nars = nars.map(() => defaultNar(t)); touch(); render(); });
                o.label.dataset.tier = t.id;
                o.input.dataset.tier = t.id;
            });

            for (let n = 1; n <= MAX_COUNT; n += 1) {
                const o = makeOpt(`${n}本`, cntBox, `calc-cnt-${uid}`, n, () => { setCount(n); touch(); render(); });
                o.label.dataset.count = String(n);
                o.input.dataset.count = String(n);
            }
            /* 本数を変えたとき、いま入っている尺は残す。
               増えたぶんは直前の本と同じ尺で埋める（同じ尺を並べたい人が多いため） */
            function setCount(n) {
                while (lens.length > n) { lens.pop(); nars.pop(); }
                while (lens.length < n) {
                    lens.push(lens[lens.length - 1] ?? 30);
                    nars.push(nars[nars.length - 1] ?? defaultNar(tier));
                }
            }
            /* 本ごとに「尺」と「ナレーション」を1行で選ぶ。select にしたのは、
               6本 × 8つの尺を丸で並べると48個になり、選ぶところが画面の大半を占めるため */
            function buildLens() {
                /* 本数が変わったときだけ組み直す。毎回つくり直すと、
                   選んだ直後に select が別物になってフォーカスが飛ぶ */
                if (lenBox.children.length === lens.length) {
                    lenBox.querySelectorAll('select[data-kind="len"]').forEach((sel) => {
                        sel.value = String(lens[Number(sel.dataset.row)]);
                    });
                    lenBox.querySelectorAll('select[data-kind="nar"]').forEach((sel) => {
                        sel.value = nars[Number(sel.dataset.row)];
                    });
                    return;
                }
                lenBox.textContent = '';
                lens.forEach((sec, i) => {
                    const row = document.createElement('div');
                    row.className = 'calc-len-row';
                    row.dataset.row = String(i);
                    const name = document.createElement('span');
                    name.id = `calc-len-name-${uid}-${i}`;
                    name.textContent = `${i + 1}本目`;
                    row.append(name);

                    const lenSel = document.createElement('select');
                    lenSel.dataset.row = String(i);
                    lenSel.dataset.kind = 'len';
                    lenSel.setAttribute('aria-label', `${i + 1}本目の尺`);
                    LENGTHS.forEach(({ sec: v, label }) => {
                        const opt = document.createElement('option');
                        opt.value = String(v);
                        opt.dataset.sec = String(v);
                        opt.textContent = label;
                        if (v === sec) opt.selected = true;
                        lenSel.append(opt);
                    });
                    lenSel.addEventListener('change', () => {
                        lens[i] = Number(lenSel.value);
                        touch();
                        render();
                    });

                    const narSel = document.createElement('select');
                    narSel.dataset.row = String(i);
                    narSel.dataset.kind = 'nar';
                    narSel.setAttribute('aria-label', `${i + 1}本目のナレーション`);
                    for (const v of ['none', 'ai', 'human']) {
                        const opt = document.createElement('option');
                        opt.value = v;
                        opt.dataset.nar = v;
                        opt.textContent = NAR_LABEL[v];
                        if (v === nars[i]) opt.selected = true;
                        narSel.append(opt);
                    }
                    narSel.addEventListener('change', () => {
                        nars[i] = narSel.value;
                        touch();
                        render();
                    });

                    row.append(lenSel, narSel);
                    lenBox.append(row);
                });
            }
            const narHint = q('nar-hint');
            /* 行の select は単体で読めるように長め、内訳とメールは短く */
            const NAR_LABEL = { none: 'ナレーションなし', ai: 'AIナレーション', human: '人物ナレーション' };
            const NAR_SHORT = { none: 'なし', ai: 'AI', human: '人物' };
            /* AIナレーションは料金に含める（追加料金なし）。合成音声なので原価がほぼゼロ。
               人物ナレーションは 1名 ¥70,000〜。1人が同じ収録で複数本を読んでも手配は1回。
               松は人物ナレーション1名が込み。
               工数はどちらも 1本 1.0h。松の秒単価には1本ぶんが入っているので、
               松が工数として足すのは2本目以降（ここを本数にすると 60秒松の 15.2h が動く）。
               tests/lib.mjs の narFee / narTracks と同じ */
            const count = () => lens.length;
            /* 「30秒×2本、90秒×1本」。並びは選んだ順のまま、隣り合う同じ尺だけまとめる */
            const lensText = () => {
                const g = [];
                for (const sec of lens) {
                    const last = g[g.length - 1];
                    if (last && last.sec === sec) last.n += 1;
                    else g.push({ sec, n: 1 });
                }
                return g.map((x) => `${secLabel(x.sec)}×${x.n}本`).join('、');
            };
            /* メール用。「15×4/60/180秒」のように、秒数だけを詰めて並べる。
               mailto は URL 長に上限（Outlook で約2,048字）があり、全角は1文字9バイトに
               なるので、ここだけは半角の数字と / で書く。画面のほうは lensText() で
               「15秒×4本、60秒×1本」と読みやすく出している */
            const lensJoin = () => {
                const g = [];
                for (const sec of lens) {
                    const last = g[g.length - 1];
                    if (last && last.sec === sec) last.n += 1;
                    else g.push({ sec, n: 1 });
                }
                return `${g.map((x) => (x.n === 1 ? x.sec : `${x.sec}x${x.n}`)).join('/')}秒`;
            };
            /* 決め方は2つだけ（tests/lib.mjs の narFee / narTracks と同じ）。
               1. 人物ナレーション（1名の手配）は、1本でも使えば ¥70,000。本数では増えない。
                  1人が同じ収録で複数本を読んでも手配は1回で、費用もほぼ変わらないため。
                  松は秒単価に1名ぶんが溶けているので ¥0。どの本にも人の声を
                  入れないなら、ナレーターの手配ぶん（¥25,000）を返す。
               2. ナレーションを入れない本は、1本につき ¥25,000 を引く。
                  AIナレーションは料金に含まれているので、使わない本のぶんは返す。
               1本だけのときは 9/19 までと同じ額になる */
            const hasHuman = () => nars.includes('human');
            /* ファネルの記録用。本ごとに違うときは 'mixed' でまとめる */
            const narSummary = () => (nars.every((m) => m === nars[0]) ? nars[0] : 'mixed');
            const noneCount = () => nars.filter((m) => m === 'none').length;
            const narFee = () => (tier.narration
                ? (hasHuman() ? 0 : -PRICE.matsuToAi)
                : (hasHuman() ? PRICE.narrationHuman : 0))
                - PRICE.noNarration * noneCount();
            /* 原稿・声の選定・配置は1本 1.0h。入れない本は 0。
               松の秒単価にはナレーション1本ぶんの 1.0h が入っているので、
               人物を使う松は1本ぶん差し引く（ここを引かないと 60秒松の 15.2h が動く） */
            const narTracks = () =>
                nars.filter((m) => m !== 'none').length - (tier.narration && hasHuman() ? 1 : 0);

            /* 初期表示の render とユーザー操作を分ける。
               「自分で条件を変えた」だけを検討中とみなす */
            const totalNow = () => PRICE.base + tier.perSec * totalSec() + PRICE.perExtra * (count() - 1) + narFee();

            function touch() {
                if (!used) { used = true; track('calc_use', { where, sec: totalSec(), count: count(), tier: tier.id, nar: narSummary() }); }
            }

            // 選び終えたところを1回だけ拾う(連打のたびに送らない)
            function settled(total) {
                clearTimeout(resultTimer);
                resultTimer = setTimeout(() => {
                    if (used) track('calc_result', { where, sec: totalSec(), count: count(), total, tier: tier.id, nar: narSummary() });
                }, 900);
            }

            function render() {
                const sec = totalSec();
                const n = count();

                tierBox.querySelectorAll('input').forEach((i) => {
                    i.checked = i.dataset.tier === tier.id;
                });
                tierHint.innerHTML = '';
                tierHint.append(tier.detail);
                const useLine = document.createElement('span');
                useLine.className = 'calc-tier-use';
                useLine.textContent = `向いている用途：${tier.use}`;
                tierHint.append(useLine);

                cntBox.querySelectorAll('input').forEach((i) => {
                    i.disabled = false;
                    i.checked = Number(i.dataset.count) === n;
                });
                cntHint.textContent = n === 1
                    ? ''
                    : `${n}本それぞれの尺を、下で別々に選べます。`;

                buildLens();
                lenHint.textContent = n === 1
                    ? ''
                    : `合計 ${secLabel(sec)}（${lensText()}）`;

                /* 松も3つとも選べる（9/19）。以前は「人が読む」に固定していたが、
                   人物ナレーションが要らない案件で松を選べなくなっていた。
                   松の既定は human。引く額は段によって変わるのでラベルも書き換える */
                /* 短い尺では、梅・竹にナレーションを足すと松（人1名込み・登場人物3人）
                   より高くなる。松の秒単価に溶けているナレーション相当
                   （竹との差 1,750/秒）が足す額に届かないため。
                   黙っていると下位の仕様を高く買う選択肢が残るので、その場で知らせる */
                const matsuTier = TIERS.find((x) => x.narration);
                const cheaperMatsu = !tier.narration && nars.some((m) => m !== 'none')
                    && tier.perSec * sec + narFee() > matsuTier.perSec * sec;
                /* 本ごとに違うモードを選べるので、使っているモードのぶんだけ説明を出す */
                const used_ = new Set(nars);
                const lines = [];
                if (used_.has('human')) {
                    lines.push(tier.narration
                        ? '<b>人物</b>… 松は1名ぶんが含まれています。声を2人使う場合は別途お見積りします。'
                        : `<b>人物</b>… ナレーター1名の手配と、原稿づくり・声の選定・映像への配置まで含みます。${yen(PRICE.narrationHuman)}〜で、<strong>何本に入れても1名ぶんのまま</strong>です（同じ収録でまとめて読むため）。`);
                }
                if (used_.has('ai')) {
                    lines.push(`<b>AI</b>… 追加料金なしで入れられます。声を選んで速さも調整できますが、<strong>合成音声なので機械の声だと分かる仕上がりになります。</strong>${tier.narration && !hasHuman() ? `どの本にも人の声を入れないので、松に込みのナレーター手配ぶん ${yen(PRICE.matsuToAi)} を差し引きます。` : ''}`);
                }
                if (used_.has('none')) {
                    lines.push(`<b>なし</b>… 声を入れず、テロップだけで伝えます。<strong>入れない本1本につき ${yen(PRICE.noNarration)}</strong> を差し引きます（いまは ${noneCount()}本ぶん）。`);
                }
                narHint.innerHTML = cheaperMatsu
                    ? 'この尺と本数なら、松（人物ナレーション1名込み・登場人物3人まで）のほうが安くなります。'
                    : lines.join('<br>');
                narHint.classList.toggle('calc-hint-warn', cheaperMatsu);

                const lenFee = tier.perSec * sec;
                const cntFee = PRICE.perExtra * (n - 1);
                const narN = narTracks();
                const narFeeNow = narFee();
                const total = PRICE.base + lenFee + cntFee + narFeeNow;
                const lenLabel = secLabel(sec);
                /* 「〜」を付けるのは人のときだけ。AI は額が決まっている */
                const approx = !tier.narration && hasHuman();
                /* 内訳の行。本ごとに違うので「人物1本・AI2本」のように数で書く */
                const narCounts = ['human', 'ai', 'none']
                    .map((m) => [m, nars.filter((x) => x === m).length])
                    .filter(([, c]) => c > 0)
                    .map(([m, c]) => `${NAR_SHORT[m]}${n === 1 ? '' : ` ${c}本`}`)
                    .join('・');
                const narNote = tier.narration
                    ? (hasHuman() ? '松に人の声1名込み' : '人の声を使わないので手配ぶんを差し引き')
                    : hasHuman() ? '1名・本数では増えません'
                    : noneCount() > 0 ? `入れない${noneCount()}本ぶんを差し引き`
                    : '料金に含まれます';
                const narText = `ナレーション ${narCounts}（${narNote}）`;
                /* メール用は詰める。「人物2/AI1/なし3」。
                   全角1文字が9バイトになるので、区切りは半角 */
                const narJoin = ['human', 'ai', 'none']
                    .map((m) => [m, nars.filter((x) => x === m).length])
                    .filter(([, c]) => c > 0)
                    .map(([m, c]) => `${NAR_SHORT[m]}${n === 1 ? '' : c}`)
                    .join('/');

                q('total').textContent = yen(total) + (approx ? '〜' : '');
                q('base').textContent = yen(PRICE.base);
                q('len-dt').textContent = n === 1
                    ? `尺 ${lenLabel} × ${yen(tier.perSec)}（${tier.label}）`
                    : `尺 合計${lenLabel}（${lensText()}） × ${yen(tier.perSec)}（${tier.label}）`;
                q('lenfee').textContent = yen(lenFee);
                q('cnt-dt').textContent = n === 1
                    ? '本数 1本'
                    : `本数 ${n}本（2本目以降 ${n - 1}本）`;
                q('cntfee').textContent = yen(cntFee);
                q('nar-dt').textContent = narText;
                q('narfee').textContent =
                    narFeeNow < 0 ? `−${yen(-narFeeNow)}`
                    : approx ? `${yen(narFeeNow)}〜` : yen(narFeeNow);
                q('lead-v').textContent = leadTime(sec, tier, narN, n);
                settled(total);

                /* 尺・本数は件名と内訳の両方に出るので、選んだ内容では繰り返さない。
                   mailto は URL 長にクライアント側の制限（Outlook で約2,048字）があり、
                   松・5分・6本のような端の組み合わせで超えるため */
                summary = [
                    '料金シミュレーターからのご相談です。',
                    '',
                    '■ 選んだ内容',
                    `・仕上げ：${tier.label}（${tier.sub}）`,
                    `・ナレーション：${narJoin}`,
                    `・概算金額：${yen(total)}（税込）`,
                    `・納品目安：${leadTime(sec, tier, narN, n)}`,
                    '',
                    '■ 内訳',
                    `・基本料金：${yen(PRICE.base)}`,
                    `・尺 ${n === 1 ? lenLabel : `合計${lenLabel}`} × ${yen(tier.perSec)}（${tier.label}）：${yen(lenFee)}`,
                    `・本数 ${n}本${n === 1 ? '' : `（${lensJoin()}）`}：${yen(cntFee)}`,
                    ...(!tier.narration && hasHuman() ? [`・ナレーション 人物1名：${yen(PRICE.narrationHuman)}〜`] : []),
                    /* 引きは1行にまとめる。松の人物ぶんと「なし」の本数ぶんを別の行にすると、
                       6本ぜんぶ「なし」のときに mailto の上限に触る。内訳は画面に出ている */
                    ...(narFeeNow < 0 ? [`・ナレーションの差し引き：−${yen(-narFeeNow)}`] : []),
                    '',
                    '■ ご記入ください',
                    '・会社名・お名前：',
                    '・映像の用途：',
                    '・公開時期：',
                    '・参考URL：',
                    '・ご要望：',
                ].join('\r\n');

                const subject = `動画制作のご相談（${tier.label}・合計${lenLabel}／${n}本）`;
                mailLink.href = `mailto:${mailAddr}`
                    + `?subject=${encodeURIComponent(subject)}`
                    + `&body=${encodeURIComponent(summary)}`;
            }

            // 相談まで進んだ人。ここまで来た人と calc_use の差が、価格で落ちた人数
            mailLink.addEventListener('click', () => {
                cta = true;
                track('calc_cta', { where, sec: totalSec(), count: count(), total: totalNow(), tier: tier.id, nar: narSummary(), how: 'mail' });
            });

            // メールソフトが開かない環境向けに、同じ本文をコピーできるようにする
            const copyBtn = q('copy');
            const copyMsg = q('copy-msg');
            const defaultMsg = copyMsg.textContent;
            let msgTimer;
            copyBtn.addEventListener('click', async () => {
                cta = true;
                track('calc_cta', { where, sec: totalSec(), count: count(), total: totalNow(), tier: tier.id, nar: narSummary(), how: 'copy' });
                let ok = false;
                try {
                    await navigator.clipboard.writeText(summary);
                    ok = true;
                } catch {
                    const ta = document.createElement('textarea');
                    ta.value = summary;
                    ta.setAttribute('readonly', '');
                    ta.style.cssText = 'position:fixed;top:-9999px';
                    document.body.append(ta);
                    ta.select();
                    try { ok = document.execCommand('copy'); } catch { ok = false; }
                    ta.remove();
                }
                copyMsg.textContent = ok
                    ? 'コピーしました。メールに貼り付けてお送りください。'
                    : 'コピーできませんでした。お手数ですが手入力でお願いします。';
                clearTimeout(msgTimer);
                msgTimer = setTimeout(() => { copyMsg.textContent = defaultMsg; }, 4000);
            });

            calc.querySelectorAll('.calc-preset').forEach((b) => {
                b.addEventListener('click', () => {
                    // よくある組み合わせは全部そろいの尺。同じ尺を本数ぶん並べる
                    lens = Array.from({ length: Number(b.dataset.cnt) }, () => Number(b.dataset.len));
                    tier = TIERS.find((t) => t.id === b.dataset.tier) || tier;
                    /* 2026-09-24：段を変えてもナレーションを既定に戻していなかった。
                       ラジオで松を選ぶと ¥1,287,000、同じ条件をプリセットで選ぶと
                       ¥1,262,000（松＋AIで −25,000）になり、料金表とも食い違っていた。
                       本数も変わるので、nars の長さも lens に合わせる */
                    nars = lens.map(() => defaultNar(tier));
                    touch();
                    track('calc_preset', { where, preset: b.querySelector('b')?.textContent || '', sec: totalSec(), count: count(), tier: tier.id });
                    render();
                });
            });

            render();


            /* 離脱時の最終状態。used かつ !cta が「価格で黙って帰った人」。
               どの金額を見て帰ったかが total に残る。
               閉じる瞬間は通常の送信が間に合わないので pagehide で送る */
            let left = false;
            const onLeave = () => {
                if (left || !used) return;
                left = true;
                track('calc_leave', { where, sec: totalSec(), count: count(), total: totalNow(), tier: tier.id, nar: narSummary(), used, cta });
            };
            window.addEventListener('pagehide', onLeave);
            document.addEventListener('visibilitychange', () => {
                if (document.visibilityState === 'hidden') onLeave();
            });
        }

})();
