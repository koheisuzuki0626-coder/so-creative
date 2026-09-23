# サイトはどこにあるか

**`main` ブランチにある。この作業ブランチには無い。**

| | |
|---|---|
| 公開URL | https://koheisuzuki0626-coder.github.io/so-creative/ |
| ファイルの置き場 | `main` の直下（`index.html` / `works.html` / `pricing.html` / `about.html` / `privacy.html`）と `main` の `assets/` |
| 公開の状態 | **全ページ noindex。**URLを知っている人しか見られない |

## なぜ作業ブランチに置かないのか

2026-09-24 まで、この作業ブランチに**古い `index.html`（「so. — Film Studio」）が
1枚だけ残っていた**。社名も中身も違う別物で、これを本物のサイトだと思って直すと、
公開サイトには一切反映されない。実害が出る前に消した（Gitの履歴には残っている）。

サイトを直すときは `main` を見ること。

## 直し方

`git checkout` は使わない（ボットがこの作業ブランチのツリーで動いているため、
切り替えると次の再起動で数百コミット前のコードに戻る）。
`git show origin/main:index.html` で取り出し、一時インデックス＋`commit-tree` で
`main` へ積む。

反映は自動ではない。**プッシュのあとに Pages を建て直す**こと。

```
gh api -X POST repos/koheisuzuki0626-coder/so-creative/pages/builds
```

## 人に見せてはいけないページ

`roadmap.html` / `record.html` / `funnel.html` は社内用。
傷病手当金・生活費・貯金・開業届の話が書いてある。noindex だが
**URLを知っていれば誰でも読める**ので、URLを人に送らないこと。
