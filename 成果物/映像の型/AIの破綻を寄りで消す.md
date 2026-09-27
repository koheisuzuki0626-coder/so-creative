# AIの破綻を「寄り」で消す（生成し直さない直し方）

2026-09-27 に `recruit-3min.mp4` の 45〜50秒で実際にやった手順。
**生成クレジットを使わずに、ffmpeg だけで直せる。**

## 使える条件

| 使える | 使えない |
|---|---|
| 破綻している部分が**主役でない**（背景・添え物） | 破綻している部分が**内容そのもの**（例：「指で差す」の指） |
| 寄りにしても**意味が保てる**（むしろ強まる） | 寄りにすると意味が消える |
| 元が 1920x1080 で、寄せても 1.5〜3倍程度 | それ以上の拡大（甘くなりすぎる） |

**判断の目安：破綻部分が画面面積の何%か。**
- `recruit-3min` の手＝寄りの画面を占めていた → 直す価値あり
- `internal-15s` の指差し＝**0.87%** → 通常再生では見えない。触らない

## 手順

### ① カットの境界を出す

```bash
ffmpeg -nostdin -v error -i 入力.mp4 \
  -filter:v "select='gt(scene,0.2)',metadata=print:file=-" -an -f null - 2>&1 \
  | grep pts_time
```

### ② 寄りの枠を決める（静止画で試す）

```bash
ffmpeg -nostdin -v error -ss 47 -i 入力.mp4 -frames:v 1 \
  -vf "crop=620:349:660:450,scale=1920:1080" -y 試し.jpg
```
`crop=幅:高さ:x:y`。16:9 を保つこと。**目で見て決める。**

### ③ 焼き込みテロップは colorkey で抜いて重ね直す

テロップを再現しようとするとフォントが合わない。
**元の帯をそのまま抜いて重ねれば、体裁は完全に一致する。**

```bash
[0:v]crop=1920:210:0:825,format=rgba,colorkey=0x101010:0.35:0.10[tel];
[zoom][tel]overlay=0:825:format=auto
```

⚠️ `lumakey` と `blend=screen` は**うまくいかなかった**——
lumakey は帯が半透明で残り、blend は色がマゼンタに転ぶ（YUVの黒でpadしたため）。
**colorkey が正解。**

### ④ 該当カットだけ差し替えて、尺と音は保つ

```bash
ffmpeg -nostdin -v error -i 入力.mp4 -filter_complex "\
[0:v]trim=0:45,setpts=PTS-STARTPTS[v1];\
[0:v]trim=45:50,setpts=PTS-STARTPTS,split[m1][m2];\
[m1]crop=620:349:660:450,scale=1920:1080,setsar=1[zoom];\
[m2]crop=1920:210:0:825,format=rgba,colorkey=0x101010:0.35:0.10[tel];\
[zoom][tel]overlay=0:825:format=auto,format=yuv420p,setsar=1[v2];\
[0:v]trim=50,setpts=PTS-STARTPTS[v3];\
[v1][v2][v3]concat=n=3:v=1:a=0[outv]" \
-map "[outv]" -map "0:a" -c:v libx264 -crf 24 -preset slow \
-pix_fmt yuv420p -c:a copy -movflags +faststart -y 出力.mp4
```

- `-c:a copy` で音は無加工。尺が変わらないので**同期がずれない**
- `crf 24 / preset slow` で元と同程度のサイズ（33MB→36MB だった）
- 終わったら `ffprobe` で**尺が一致しているか**必ず確認する

## 検証

直したら、同じ物差し（Gemini の映像分析）でもう一度見る。
ただし **Gemini は毎回どこかに新しい粗さを見つける**ので、
「全部消す」を目標にしない。**誰が見ても分かる破綻だけ**を直す。

関連：`成果物/競合分析/自分のサンプル12本_競合と同じ物差し_2026-09.md`
