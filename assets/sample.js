/* サンプル映像の「AIナレーションあり／なし」切り替え。
   2026-09-23 に index.html から切り出した。カードが works.html へ移ったため、
   置き場を1つにして両方から読む。 */
    /* 会社紹介サンプルの「AIナレーションあり／なし」切り替え。
       この音声は合成音声なので、ボタンにも注釈にも「AI」と書く。
       人が読んだものと誤解されると、人物ナレーションの見積りがずれる。
       同じ映像で音だけ違うので、再生位置と再生状態を保ったまま差し替える。
       段の違い（松は人物ナレーション1名込み、AIナレーションは全段とも料金に含む）を
       納品物そのもので確かめてもらうための仕掛け */
    (() => {
        const video = document.getElementById('sample-video');
        if (!video) return;
        for (const btn of document.querySelectorAll('.sample-sw')) {
            btn.addEventListener('click', () => {
                if (btn.classList.contains('is-on')) return;
                const at = video.currentTime;
                const playing = !video.paused && !video.ended;
                video.src = 'assets/works/' + btn.dataset.file;
                video.load();
                const restore = () => {
                    video.removeEventListener('loadedmetadata', restore);
                    try { video.currentTime = at; } catch (e) { /* 巻き戻せない環境では先頭から */ }
                    if (playing) video.play().catch(() => {});
                };
                video.addEventListener('loadedmetadata', restore);
                for (const b of document.querySelectorAll('.sample-sw')) {
                    const on = b === btn;
                    b.classList.toggle('is-on', on);
                    b.setAttribute('aria-pressed', String(on));
                }
            });
        }
    })();
