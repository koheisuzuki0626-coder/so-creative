# ふたつの目 ― Kling 3.0 の指示文（8カット）

- モデル：kling3_0／mode=std／sound=off／16:9
- 開始画像：絵コンテのAI画（Higgsfield のジョブIDをそのまま渡す）
- 料金：1秒 1.5クレジット → 合計57秒で 約86クレジット（2026-10-29 の見積もり。ナレーションに合わせて尺を延ばした後の値）
- 生成する秒数（編集での使用秒数）：C05 7（7）／C06 8（7.5）／C09 7（6.5）／C10 8（8）／C11 6（6）／C13 7（6.5）／C17 6（6）／C18 8（8）
- 共通の書き出し：「Animate this nihonga painting subtly. Keep the painted style, composition and colors exactly. No new objects, no text.」

| カット | 秒 | 開始画像のジョブID | 動きの指示 |
|---|---|---|---|
| C05 | 7 | c2156b2d-0df5-4376-b889-5438190c253b | Gentle snowfall drifting down, lantern lights flickering softly, mist moving slowly over the river, very slow camera push-in. The fortress stays unchanged. |
| C06 | 8 | 3c03be92-7ae3-41ff-ba73-043ded815956 | The bearers and retainers walk slowly away along the pine-lined road, the palanquin sways slightly, slow pan to the left. The child is seen only from behind. |
| C09 | 7 | 78d8b139-c018-4659-86ba-f9f61e4bc901 | Reeds sway gently in the foreground, mist drifts over the river, the small boat rocks slightly, slow push-in toward the river. |
| C10 | 8 | add23c1e-7f41-4ba1-b04e-1cb6ccc7f7ec | Torrential rain streaks diagonally, banners and camp curtains whip in the wind, storm clouds churn, one flash of lightning, slight handheld shake. No fighting, no blood. |
| C11 | 6 | 50964bf8-a931-48dc-b0ed-aad5516a230b | Candlelight flickers; the hand in the black sleeve slowly opens the folding fan a little, the hand in the white sleeve rests calmly, very slow push-in. Faces stay out of frame. |
| C13 | 7 | 18db8dd8-931e-4600-a65d-944a6913a5b9 | Workers haul the huge stones with ropes, moving slowly forward, dust drifts in the sunbeams, slow pan from left to right. |
| C17 | 6 | 539ff950-394c-4267-b94c-a246a85657ad | Looms and spinning frames move in a steady rhythm, threads vibrate, dust motes float in the window light, slow push-in down the aisle. |
| C18 | 8 | e54ae546-f69d-4129-abe2-3817e10f677f | Welding sparks burst from the car body as workers move, slow pan to the right into the glowing modern factory line with streaks of light. No logos, no emblems, no text. |

差し替え：できた動画を `KLING_DIR/Cxx.mp4` に置いて `assemble.py` を回すと、静止画の代わりに使われる。
