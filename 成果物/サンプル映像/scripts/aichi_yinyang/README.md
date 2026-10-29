# ふたつの目 ― 愛知の陰陽図（自主制作・1分54秒）の作り方

2026-10-29 制作。完成品は `assets/works/original-aichi-yinyang.mp4`（main・サイト掲載用に圧縮）。
生成した元素材（Kling の動画8本・AI画8枚・金鯱の絵・ナレーション15本）は Drive にあり、所在は `../../素材元_台帳.md`。

## 地図のデータ（公開データ・再取得できる）
国土数値情報 行政区域（N03・2021年、国土交通省）を簡略化した GeoJSON：
`https://raw.githubusercontent.com/smartnews-smri/japan-topography/main/data/municipality/geojson/s0010/N03-21_{23,21,22,24,20}_210101.json`
（23=愛知、21=岐阜、22=静岡、24=三重、20=長野）。`/tmp/aichi_map/data/pref_XX.json` に置いて使う。
出典の表示（「国土数値情報（行政区域データ・2021年）国土交通省 を加工して作成」）は利用条件なので、図にも動画の説明にも必ず入れる。

## スクリプト（すべて /tmp/aichi_map/ を作業場所にしている）
| ファイル | 役割 |
|---|---|
| render_map.py | 地図に太極図を重ねた1枚絵（目＝名古屋城・岡崎城） |
| verify.py | 仮説の検証：S字と等距離線の、尾張・三河の塗り分けとの一致率（89.5% / 89.6%） |
| render_seizu.py / zumen.py | 仮説図（製図風）と A3 の図面（PDF・1:400,000） |
| map_frames.py | 絵コンテ用の地図のコマ |
| anim.py | 地図12カットのアニメーション（Playwright でコマごとに書き出す） |
| ekonte.py | 絵コンテ PDF |
| audio_mix.py | BGM（都節の音階）・効果音の合成と、ナレーションの配置・ダッキング |
| telops.py | 年号の文字 |
| snow.py | C05 に重ねる雪（Kling では雪が途中で止まるため） |
| kling_qc.py | Kling の動画を落として6コマ並べる（破綻の確認用） |
| assemble.py | 21カットを `timeline.json` の尺でつなぎ、音を載せる（KLING_DIR に Cxx.mp4 があれば静止画の代わりに使う） |
| finalize_c18.sh | C18 が届いたら、落として確認用のコマを作り、完成版を組む |
| gallery.py | 絵画・地図・図面・動画までを1ページにまとめる（Mac用HTMLと、スマホ用PDF） |
| taiji_ref.py | 太極図の型紙（AIに絵を描かせるとき image_references に渡す） |
| find_dots.py | 絵の中の「目」（2つの玉）の中心を、色と範囲から測る |
| fusion.py | 陰陽図の絵を、正確な地図と融合させた1枚絵 |
| ezu_guide.py / ezu_check.py / ezu_finish.py | 絵地図：下絵（塗り分け＋名所の印）→ 本当の輪郭とのずれの確認 → 本当の線・城の金の点・地名を重ねる |
| title_png.py | 締め（C21）の題字 |
| fusion_anim_layers.py | 金鯱×地図の動画の層：地図の土台（base.png）・線と文字（top.png・透過）・位置合わせの値（params.json） |
| fusion_anim.py | 金鯱の動画を回転・拡大して、2つの玉を名古屋城・岡崎城に合わせて地図に重ねる |
| fanim_qc.py | 重ねた動画のコマに城の本当の位置の印を描いて並べる（ずれの確認） |

## 決めたこと・分かったこと
- 尺はナレーション（Seed Audio の「太郎」・speech_rate -10）に合わせて延ばした。声を急がせない
- Kling 3.0 std は 1284×716。編集で lanczos 拡大
- Kling に送ると、無関係なプリセット（IN THE DARK）を勧められて送信されないことがある → `declined_preset_id` で外す
- C05 の1回目は写真のような霧が絵から浮いたので撮り直し。「No fog, no mist」を入れて解消
- 「尾張と三河の境は太極図のS字に沿う」は不支持（等距離の直線と差 0.1 ポイント）。映像でもそのまま言っている
- 金鯱×地図の動画（10-30）：カメラ固定の Kling でも、**87コマ目（3.6秒）から黒い鯱の鱗に金が滲んだ**。最初と最後のコマで玉の位置だけ比べていて見落とし、胴の領域の R−B（黄み）を全コマで測って見つけた。0〜84コマを往復させて 7.0秒・切れ目のないループにした：
  ```
  ffmpeg -i 融合用_金鯱_カメラ固定_高画質.mp4 -filter_complex "[0]trim=end_frame=85,setpts=PTS-STARTPTS,split[a][b];[b]reverse,trim=start_frame=1:end_frame=84,setpts=PTS-STARTPTS[r];[a][r]concat=n=2:v=1:a=0[v]" -map "[v]" -c:v libx264 -crf 10 -pix_fmt yuv420p -r 24 kin_pingpong.mp4
  python3 fusion_anim.py kin_pingpong.mp4 融合_金鯱×地図_動画.mp4
  ```
- ffmpeg の `color` 入力は既定で 25fps。24fps の動画と混ぜると**毎秒1コマ重複する**（動きが1秒ごとに引っかかる）。`r=24` を付ける
