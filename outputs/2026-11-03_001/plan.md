# 001 企画書・台本：秋の間違い探し5問（約10分）【新方針での作り直し版】

- 作成：企画部（2026-11-03 初版、2026-11-05 作り直し）／状態：**監査待ち**。作り直しの指示はCEO、事業部長経由で受けた
- 作り直しの理由：2026-11-06 のCEO決定（concept.md・ng-list.md）。変更点は次の4つ。
  - 絵を画面いっぱいに出す（1枚960×1080・約8:9）
  - 出題中・答え合わせ中はキャラの絵を出さない
  - 難易度を1段階引き上げる
  - 声を Fish Audio にする
- 前の版（横長の絵・旧難易度）は git に残っている（コミット 89ec39b）。前の版から変えたところは末尾の「作り直しで変えたところ」にまとめた。
- 投稿日：未定（月・水・金のいずれか。事業部長が決める）。
- 書き方：【事実】は確認したこと、または規則から計算したこと。【意見】は企画部の判断・提案。

---

## 1. 企画の概要

| 項目 | 内容 |
|---|---|
| 季節（大枠） | 秋 |
| 題材 | 柿・紅葉（あわせて栗・さんま・いちょうも絵に入れる） |
| ジャンル | 間違い探し。5問×違い3つで15個 |
| 長さ | 10分15秒（計算は7章） |
| うんちく | 「もみじ」ということばと、万葉集の「黄葉」 |

| 問 | 難易度 | 場面 | 違い3つの種類 |
|---|---|---|---|
| 第1問 | 初級 | 縁側 | 物がない・増える・形が変わる |
| 第2問 | 初級 | 商店街 | 物がない・増える・形が変わる |
| 第3問 | 中級 | 山道（読み：やまみち） | 本数・模様・増える |
| 第4問 | 中級 | 台所 | 本数・向き・模様 |
| 第5問 | 上級 | 神社（境内） | 物がない（背景の細部）・色・向き |

【事実】重複ルールの確認。concept.md の 2026-11-06 版に照らした。
- 季節（秋）は数えない。題材（柿・紅葉）は、ネタ帳でほかの回に使われていない（`knowledge/neta.md`）。
- 5つの場面は `knowledge/scenes.md` の候補にある（1 縁側、8 商店街、31 山道、2 台所、20 神社の境内）。ほかの回では使っていない。
- 事業部長の指示により、場面と題材は前の版のまま。第1回はまだ公開していない。
- うんちくは初めて使う。

---

## 2. 画面と絵の指示（制作部 → Gemini）

### 2-1. 画面のつくり（事実：concept.md と事業部長の指示）
- 出題中と答え合わせ中は、左右の絵で画面全体（1920×1080）を埋める。絵1枚は **960×1080**（縦横比 約8:9）。
- 画面の上の端に、問題番号・難易度・残り時間の細い帯が出る。高さは**約5%**（約54px）。
- セリフがあるときは、下の端に字幕が出る。高さは**約12%**（約130px）。
- 出題中・答え合わせ中は、こよみ先生の絵を出さない。声だけで案内する。
- **違いを置かない所**：絵の**上5%（y 0〜54）と下15%（y 918〜1080）**。違いは y 54〜918 の間に置く。

### 2-2. 違いの大きさ（事実：concept.md の難易度表を絵の幅に直した値）
絵1枚は画面幅の50%なので、絵の幅に対する割合は画面幅に対する割合の2倍になる。

| 難易度 | 画面幅に対して | 絵の幅に対して | 960pxの絵で | 違いの種類 |
|---|---|---|---|---|
| 初級 | 約3〜4% | 約6〜8% | 約58〜77px | 物がない・増える・形が変わる |
| 中級 | 約2〜3% | 約4〜6% | 約38〜58px | 上に加えて、小物の向き・模様・本数 |
| 上級 | 約1.5〜2% | 約3〜4% | 約29〜38px | 上に加えて、色の違いも可。背景の細部にも隠す |

【意見】目立ち方の工夫
- 初級は、手前から中ほどの、ほかと離れた物を使う。
- 中級は、似た物がまわりにある所（きのこの群れ・道具の並び）を使う。
- 上級は、奥の物や物の一部（鳥居の端・柱の根もと・ハトの頭）を使う。
- 色の違いを使うのは上級の1つだけ。初級・中級は色だけの違いにしない（制作部ルール）。
- 制作部は元の絵ができたら物の幅を計る。表の幅に合わないときは、企画部に相談する（大きすぎる場合も、易しすぎるので相談する）。

### 2-3. 絵の縦横比の作り方
【意見】
- Gemini には8:9の設定がないと思われる（制作部が確認する）。そこで **4:5（縦長）で作り、上下を5%ずつ切って8:9にする**。
- 4:5の絵を幅960に縮めると高さ1200。上下60pxずつを切ると960×1080になる。
- このとき、生成した絵での「違いを置かない所」は**上約10%と下約20%**になる。プロンプトでも、この範囲には大事な物を置かないよう指示する。
- 画質：2Kで作れば960×1080より大きい。引き伸ばしでぼやけることはない（制作部ルール）。

**共通のスタイル文（各場面のプロンプトの先頭に付ける）**
```
A warm Japanese picture-book illustration in soft watercolor with gentle colored-pencil outlines,
like a cozy picture book for all ages, drawn with clear, crisp details. Autumn palette: persimmon
orange, maple red, ginkgo yellow, warm browns and soft greens. Natural, hand-drawn, slightly rounded
shapes; not geometric, not flat vector, not photorealistic. PORTRAIT-ISH composition, slightly taller
than wide (about 8:9); the scene is arranged vertically, with a near foreground, a middle ground and
a background stacked from bottom to top. Keep the top 10% of the picture simple (sky, eaves or
leaves only) and the bottom 20% simple (plain floor, ground or pavement only): put every main object
listed below in the middle part of the picture. No people. Absolutely no text, letters, numbers,
logos or symbols anywhere, including on signs, curtains, boxes and lanterns. The main objects are
clearly drawn, separated from each other with a little space around each, and fully visible (not
cut off by the picture edge and not hidden behind other objects).
```
- 設定案：`gemini_image.generate(prompt, aspect="4:5", size="2K")`。そのあと960×1080（8:9）に切り出す。

### 2-4. 第1問 縁側（初級）
```
Scene: looking out from inside an old Japanese house across a wooden veranda (engawa) into a small
autumn garden in warm late-afternoon light. Background (upper middle): a persimmon tree with orange
fruit and a moss-covered stone lantern among red maple leaves. Middle: the wooden veranda. Main
objects: (1) a calico cat sleeping on a flat floor cushion on the veranda, with its striped tail
curled neatly around its body; (2) a round wooden tray on the veranda holding exactly three
persimmons, a brown clay teapot and two teacups, with a little empty space on the tray; (3) a large
woven bamboo basket standing on the veranda; (4) a flat stepping stone just below the veranda edge
with a pair of wooden geta sandals on it, the pair about one fourteenth of the picture width;
(5) a few strings of dried persimmons hanging from the eaves at the upper right, kept below the top
tenth of the picture. Each persimmon on the tray is about one sixteenth of the picture width.
```

### 2-5. 第2問 商店街（初級）
```
Scene: a narrow old Japanese shopping street in autumn, seen from the street in front of a small
fruit and vegetable shop with a wooden front and a tiled roof; the street goes back into the
distance at the upper left. Main objects: (1) a wooden display stand in front of the shop with flat
bamboo baskets of persimmons and sweet potatoes; (2) one big green Japanese pumpkin (kabocha)
sitting alone on the stand, about one thirteenth of the picture width, with empty space next to it;
(3) a round flat bamboo basket full of chestnuts on the stand, about one twelfth of the picture
width; (4) an old-fashioned black bicycle with a wire front basket parked in front of the shop
(the basket about one fourteenth of the picture width); (5) a Shiba dog sitting on the pavement;
(6) a plain indigo shop curtain (noren) with no writing and no pattern; (7) a potted yellow
chrysanthemum by the door; a few ginkgo leaves on the stone pavement. Paper lanterns, if any, are
completely blank. The neighbouring shops are simple and have no writing.
```
【意見】看板・のれん・提灯に文字が出やすい場面。文字が出たら描き直す（予備の呼び出しを使う）。

### 2-6. 第3問 山道（中級）
```
Scene: a gentle mountain walking path in autumn, with rough stone steps winding up through red
maple and yellow trees toward misty hills at the top. Main objects: (1) a wooden bench beside the
path with a small red rucksack and a folded white hand towel (tenugui) with a blue polka-dot pattern
lying on it, the towel about one eighteenth of the picture width; (2) a tree stump with one brown
squirrel sitting on it, facing right and holding an acorn, about one eighteenth of the picture
width; (3) a cluster of exactly three brown mushrooms at the foot of a maple tree, each mushroom
about one twentieth of the picture width; (4) a small stack of round stones (a cairn) at the side
of the path; (5) a few spiky chestnut burrs on the ground; (6) a small wooden footbridge over a
little stream. No signposts.
```

### 2-7. 第4問 台所（中級）
```
Scene: an old-fashioned Japanese country kitchen in autumn with dark wooden beams, a window showing
a persimmon tree outside at the top, and a clay cooking stove (kamado) at the left. Main objects:
(1) a sturdy wooden table in the middle; (2) a round bamboo colander (zaru) on the table holding
exactly three purple sweet potatoes, each about one eighteenth of the picture width, with space for
one more; (3) a metal kettle with its spout clearly pointing to the left, sitting on the stove;
(4) a small tray with a teapot and two cylindrical teacups (yunomi), each teacup about one
twentieth of the picture width, both decorated with the same simple wavy blue lines;
(5) an oval plate with two grilled Pacific saury fish; (6) a small basket of chestnuts; (7) a few
wooden ladles hanging on the wall. No clock, no calendar, no paper with writing.
```

### 2-8. 第5問 神社（上級）
```
Scene: the quiet grounds of a small Japanese shrine in late autumn, with a tall golden ginkgo tree
and yellow leaves scattered on the stone-paved path that leads up to a small wooden shrine building
in the upper middle. Main objects: (1) the shrine building with a gabled roof; on the ridge of the
roof there are exactly three short round crosswise logs (katsuogi), clearly separated; (2) a pair
of stone guardian lion-dog statues (komainu) on pedestals on both sides of the path, the left one
wearing a small red cloth bib, the bib about one twenty-eighth of the picture width; (3) a stone
lantern beside the path whose light box has a round window, the window about one thirtieth of the
picture width; (4) a red torii gate at the side; (5) a few grey pigeons on the path; (6) a plain
wooden offering box with no writing; (7) a bamboo broom leaning against the ginkgo trunk.
No wooden plaques with writing, no paper charms with letters.
```

---

## 3. 各問の違い3つ（制作部の実測で選び直した確定版）

【事実】選び直しの経緯（outputs/2026-11-03_001/diff_candidates.md、制作部 2026-11-06）
- 2章のプロンプトで描いた物は、Gemini が大きく描いたため、ほとんどが難易度表の約2倍の大きさになった。たとえば、ねこのしっぽは7.25%、さつまいもは6.0%、鰹木は3.10%。
- そこで、画像APIの呼び出しを足さずに、いまの元の絵5枚の中から、難易度表に入る物や物の一部を選び直した（事業部長の案C）。
- 元の絵は1856×2088。画面では960×1080に縮める。画面幅に対する%は「幅px×0.02694」で計算した。
- 下の「位置」は元の絵でのおおよその中心。違いを置かない所（元の絵で y 0〜104 と y 1775〜2088）には入っていない。
- 幅の読みの誤差は±0.1%前後。描き直しのあとに差分の範囲でも測り直し、answers.json に書く（制作部）。

【事実】作り方
- 1問につき1回の描き直しで3つまとめて作り、範囲ごとに元の絵へ貼り戻す（concept.md）。
- 例外：第5問③のハトは、プログラムで頭を左右反転して作る（AIの描き直しを使わない）。

【意見】描き直しの注意
- 消すときは `KEEP_REMOVE`、増える・形・向き・模様・色のときは `KEEP_ALT` を使う。
- 小さな違いは、範囲のまわりを切り出して大きく描き直す方式（crop）を先に試す。範囲は物より一回り広く取る。

### 第1問 縁側（初級：画面幅の約3〜4%）
| # | 物 | どう変える | 種類 | 幅（画面幅） | 位置(x,y) | 答え合わせの一言 |
|---|---|---|---|---|---|---|
| 1 | 奥の下駄の鼻緒 | なくなる（台だけ残る） | 物がない | 3.37% | (630, 1530) | 「下駄の鼻緒が、ひとつありません。」 |
| 2 | お盆の柿 | 3つ → 4つ | 増える | 3.72%（柿1つぶん） | (1080, 1560) | 「柿が、よっつに増えました。」 |
| 3 | 手前の湯のみ | 低い湯のみ → 背の高い筒形 | 形が変わる | 3.12% | (1280, 1640) | 「湯のみが、背の高い形になりましたね。」 |
```
Edit this close-up and make exactly these three changes: (a) remove the thong straps (hanao) from
the back geta sandal, leaving only its wooden base; (b) add one more persimmon of the same size on
the round tray, so there are four; (c) the front low teacup becomes a tall cylindrical teacup, same
color and pattern, same place.
```

### 第2問 商店街（初級）
| # | 物 | どう変える | 種類 | 幅（画面幅） | 位置(x,y) | 一言 |
|---|---|---|---|---|---|---|
| 1 | ざるのさつまいも（1本） | なくなる | 物がない | 3.58% | (930, 1260) | 「おいもが、ひとつありません。」 |
| 2 | 柴犬の首 | 赤い首輪がつく | 増える | 約3.5%（首の幅） | (1220, 1640) | 「わんちゃんに、首輪がつきました。」 |
| 3 | 店先の大きな提灯（無地） | 細長い形 → 丸い形 | 形が変わる | 3.45% | (620, 730) | 「提灯の形が、まるくなっていますね。」 |
```
Edit this illustration and make exactly these three changes: (a) remove one sweet potato from the
bamboo basket; (b) the Shiba dog now wears a simple red collar; (c) the big hanging paper lantern in
front of the shop becomes round instead of long, same color, still completely blank.
```
【意見】②は赤い首輪が「増える」違いで、色だけの違いではない。

### 第3問 山道（中級：画面幅の約2〜3%）
| # | 物 | どう変える | 種類 | 幅（画面幅） | 位置(x,y) | 一言 |
|---|---|---|---|---|---|---|
| 1 | 道の左のいがぐり（小さいほう） | なくなる（いがぐりが1つへる） | 本数 | 2.37% | (905, 1390) | 「いがぐりが、ひとつへりました。」 |
| 2 | 真ん中のきのこのかさ | 無地 → 白い水玉模様 | 模様 | 2.34% | (575, 930) | 「きのこに、水玉模様がつきました。」 |
| 3 | 石の塔 | いちばん上に中くらいの石が1つ増える | 増える・本数 | 約2.0〜2.4%（足す石。描き直し後に測る） | (740, 1070) | 「石の塔が、ひとつ高くなりましたね。」 |
```
Edit this illustration and make exactly these three changes: (a) remove the smaller spiky chestnut
burr on the left side of the path; (b) the cap of the middle mushroom now has small white polka
dots, same shape; (c) add one more medium-sized round stone on the top of the stone stack.
```

### 第4問 台所（中級）
| # | 物 | どう変える | 種類 | 幅（画面幅） | 位置(x,y) | 一言 |
|---|---|---|---|---|---|---|
| 1 | 壁にかけた道具（右から2つ目のへら） | なくなる（道具が1つへる） | 本数 | 2.86% | (1615, 640) | 「壁の道具が、ひとつへっています。」 |
| 2 | やかんの注ぎ口 | 左向き → 右向き | 向き | 2.83% | (190, 900) | 「やかんの口が、反対を向いています。」 |
| 3 | 手前の湯のみ | 波線 → ごばん目の模様（同じ青） | 模様 | 2.77% | (1025, 1250) | 「湯のみの模様が、変わっていますね。」 |
```
Edit this illustration and make exactly these three changes: (a) remove the second wooden spatula
from the right among the utensils hanging on the wall; (b) turn the kettle so that its spout points
to the right instead of the left, same kettle, same place; (c) the front teacup now has a blue
checkered (grid) pattern instead of wavy lines, same blue color, same shape.
```
【意見】③は模様の違いで、色は変えない。湯のみは第1問③（形）にも出てくるが、違いの種類が別なので重なりとは見なさない。

### 第5問 神社（上級：画面幅の約1.5〜2%）
| # | 物 | どう変える | 種類 | 幅（画面幅） | 位置(x,y) | 一言 |
|---|---|---|---|---|---|---|
| 1 | 灯籠のてっぺんの宝珠（ほうじゅ） | なくなる | 物がない（背景の細部） | 2.07%（目安「約1.5〜2%」の範囲として事業部長が認めた） | (1495, 1030) | 「灯籠のてっぺんの飾りが、ありません。」 |
| 2 | 鳥居の左の柱の根もと（黒い根巻き） | 黒 → 赤（柱と同じ色） | 色 | 1.97% | (125, 1255) | 「鳥居の柱の根もとが、赤くなりました。」 |
| 3 | 右のハトの頭 | 左向き → 右向き（プログラムで左右反転） | 向き | 1.62% | (995, 1530) | 「右のハトが、反対を向いていますね。」 |
```
Edit this illustration and make exactly these two changes: (a) remove the small protruding left end
of the upper crossbeam of the red torii; (b) the black base band at the bottom of the left torii
pillar is now red, the same red as the pillar.
（③のハトはAIで描き直さず、プログラムで頭を左右反転する）
```
【意見】
- ①と②はどちらも鳥居だが、上の端と下の根もとで縦に約450px離れている（制作部の確認）。
- ヒントは③のハトの辺りを示す。

### 違いの種類の集計
【事実】15個の内訳は次のとおり。色の違いは上級の1つ（鳥居の根巻き）だけ。
- 物がない：3（第1問①、第2問①、第5問①）
- 増える：3（第1問②、第2問②、第3問③）
- 形が変わる：2（第1問③、第2問③）
- 本数：2（第3問①、第4問①）
- 模様：2（第3問②、第4問③）
- 向き：2（第4問②、第5問③）
- 色：1（第5問②）

---

## 4. 台本（秒数つき）

- 時刻は動画の頭からの時刻。字数は、句読点とかぎかっこを除いた数。
- **表情の指定は、こよみ先生が画面に出るオープニング・うんちく・エンディングだけ。** 出題中・答え合わせ中は声だけで、絵は出さない。
- 声は Fish Audio「女性アナウンス」（モデルID `63819275ce38440ea245ca988abf976e`）。ゆっくり読ませる。
- 【事実】各セリフの字数を話す枠の秒数で割った速さは、最大で**252字/分（オープニング）**。どのパートも300字/分を超えない。動画全体では764字（約75字/分）。答え合わせは最大50字（15秒で200字/分）、ヒントは最大24字（6秒で240字/分）。
- 出題中に話すのは「開始」「45秒のヒント」「残り10秒」の3回だけ。それ以外の約75秒は、黙って探す時間。
- ヒントは、声でヒントを言い、違いのある辺りを**うっすら示す**（concept.md）。

### 4-0. 読みの指定（Fish Audio が読み違えたときのために）
| 字 | 読み | 注意 |
|---|---|---|
| 山道 | やまみち | 「さんどう」と読ませない（第1回の監査で指摘） |
| 紅葉・もみじ | もみじ | 「こうよう」と読ませない。うんちく 6:12 は声の文をひらがなの「もみじ」にしてある |
| 黄葉 | もみち | うんちくの中。字幕は「黄葉」、声は「もみち」 |
| 縁側 | えんがわ | |
| 下駄 | げた | |
| 鼻緒 | はなお | |
| 湯のみ | ゆのみ | |
| 柿 | かき | |
| 首輪 | くびわ | |
| 提灯 | ちょうちん | |
| いがぐり | いがぐり | ひらがなで書く |
| 水玉模様 | みずたまもよう | |
| 石の塔 | いしのとう | |
| へら | へら | 台本では「壁の道具」と言う |
| 鳥居 | とりい | |
| 根もと | ねもと | |
| 横木 | よこぎ | 台本では「上の木」と言う |
| 宝珠 | ほうじゅ | 台本では「てっぺんの飾り」と言う |
| 灯籠 | とうろう | 今回の台本では使わない |
| お社 | おやしろ | 今回の台本では使わない |
| 万葉集 | まんようしゅう | |
| 小話 | こばなし | |
| 称号 | しょうごう | |
| 第1問〜第5問 | だいいちもん〜だいごもん | |
| 初級・中級・上級 | しょきゅう・ちゅうきゅう・じょうきゅう | |
| 90秒／10秒 | きゅうじゅうびょう／じゅうびょう | |
| 15個 | じゅうごこ | |

【意見】聞き違えやすい言い方を避ける。
- 「2本」は「にほん」が「日本」に聞こえるので、「1本」「2本」は使わない。本数の違いも「ひとつへりました」「ひとつ増えました」と言う。
- 「4つ」は「よっつ」とひらがなで書く（「しつ」「よんつ」と読ませない）。
- 「横木」「へら」「根巻き」「島木」は耳で聞いてわかりにくいので、「上の木」「壁の道具」「柱の根もと」と言いかえた。

### 4-1. オープニング（0:00〜0:15・15秒）
| 時刻 | 表情 | セリフ | 画面 |
|---|---|---|---|
| 0:00 | にっこり | みなさん、こんにちは。こよみ先生です。秋がふかまって、柿のおいしい季節になりましたね。今日は、秋の間違い探しを5問、いっしょに楽しみましょう。（63字） | こよみ先生が登場（ゆらゆら・まばたき）。タイトル「秋の間違い探し 5問」 |

### 4-2. ルール説明（0:15〜0:25・10秒）
| 時刻 | 表情 | セリフ | 画面 |
|---|---|---|---|
| 0:15 | ふつう | 左と右の絵をくらべます。90秒で、右の絵の違いを3つ探してください。（31字） | 左右に絵の枠、「90秒」「違いは3つ」の大きな文字 |

【意見】ルール説明は、こよみ先生を出す最後の場面とする。concept.md はオープニングに含めて扱っていると読んだ。出さないほうがよければ、制作部の判断で消してよい。

### 4-3. 各問の流れ（共通）
| 問の頭から | 長さ | 内容 | 画面 |
|---|---|---|---|
| 0秒 | 3秒 | 難易度カード（スライド／フェード） | カード |
| 3秒 | 90秒 | 出題。上の帯に問題番号・難易度・残り時間。残り10秒でカウント音 | 左右の絵で画面いっぱい。キャラの絵はなし |
| 48秒（出題45秒） | 7秒 | 声でヒント＋違いの辺りをうっすら示す | 同上 |
| 93秒 | 15秒 | 答え合わせ。赤丸を1つずつ効果音つき | 同上 |

### 4-4. 第1問 縁側・初級（0:25〜2:13）
| 時刻 | セリフ |
|---|---|
| 0:25 | 第1問、初級。縁側です。（カード） |
| 0:28 | さあ、どうぞ。 |
| 0:31〜1:13 | （黙って探す時間） |
| 1:13 | ヒントです。足もとの石のあたりを、よく見てくださいね。（違い①の辺りをうっすら示す） |
| 1:19〜1:48 | （黙って探す時間） |
| 1:48 | あと10秒です。（カウント音） |
| 1:58 | 答えです。下駄の鼻緒が、ひとつありません。柿が、よっつに増えました。湯のみが、背の高い形になりましたね。（赤丸①②③） |

### 4-5. 第2問 商店街・初級（2:13〜4:01）
| 時刻 | セリフ |
|---|---|
| 2:13 | 第2問、初級。商店街です。 |
| 2:16 | さあ、どうぞ。 |
| 2:19〜3:01 | （黙って探す時間） |
| 3:01 | ヒントです。お店の上のほうを、よく見てくださいね。（違い③の提灯の辺り） |
| 3:07〜3:36 | （黙って探す時間） |
| 3:36 | あと10秒です。 |
| 3:46 | 答えです。おいもが、ひとつありません。わんちゃんに、首輪がつきました。提灯の形が、まるくなっていますね。 |

### 4-6. 第3問 山道・中級（4:01〜5:49）
| 時刻 | セリフ |
|---|---|
| 4:01 | 第3問、中級。山道です。（読み：やまみち） |
| 4:04 | 少しむずかしくなります。どうぞ。 |
| 4:08〜4:49 | （黙って探す時間） |
| 4:49 | ヒントです。木の根もとのあたりを、よく見てくださいね。（違い②のきのこの辺り） |
| 4:55〜5:24 | （黙って探す時間） |
| 5:24 | あと10秒です。 |
| 5:34 | 答えです。いがぐりが、ひとつへりました。きのこに、水玉模様がつきました。石の塔が、ひとつ高くなりましたね。 |

### 4-7. うんちく（5:49〜6:19・30秒）
- 字幕はかぎかっこ付き。**声（Fish Audio に渡す文）はかぎかっこを外す。**
- 字数は114字（30秒で228字/分）。6:12 のセリフは28字で、7秒の枠では240字/分。
- 【事実】調査部が出典の本文で確かめ直した（research_unchiku.md「本文での確認（2026-11-05）」）。5:53 と 6:04 は合格。6:12 は、事業部長の指示で案Bに差し替えた（5章）。数字は入れない。

| 時刻 | 表情 | 字幕（かっこ付き） | 声に渡す文（かっこなし） | 画面 |
|---|---|---|---|---|
| 5:49 | にっこり | ここで、ひと休み。秋の小話です。 | ここで、ひと休み。秋の小話です。 | こよみ先生が登場。もみじ・いちょうの葉が舞う |
| 5:53 | ふつう | 「もみじ」は、葉の色が変わることをあらわす、むかしのことば「もみつ」から生まれたといわれます。 | もみじは、葉の色が変わることをあらわす、むかしのことば、もみつから生まれたといわれます。 | 「もみつ → もみじ」 |
| 6:04 | びっくり | 万葉集のころは、黄色い葉と書いて「もみち」と読むのが、ふつうだったそうです。 | 万葉集のころは、黄色い葉と書いて、もみちと読むのが、ふつうだったそうです。 | 大きく「黄葉」（ふりがな もみち） |
| 6:12 | にっこり | 平安時代になると、赤いもみじが秋の主役になったといわれます。 | 平安時代になると、赤いもみじが秋の主役になったといわれます。（読みは「もみじ」。「こうよう」と読ませない） | 「平安時代」「古今集の秋の歌」の文字と、赤いもみじ（かえで）の葉の絵。黄葉から紅葉への矢印は使わない |

### 4-8. 第4問 台所・中級（6:19〜8:07）
| 時刻 | セリフ |
|---|---|
| 6:19 | 第4問、中級。台所です。 |
| 6:22 | 後半です。どうぞ。 |
| 6:25〜7:07 | （黙って探す時間） |
| 7:07 | ヒントです。お茶の道具のあたりを見てください。（違い③の湯のみの辺り） |
| 7:13〜7:42 | （黙って探す時間） |
| 7:42 | あと10秒です。 |
| 7:52 | 答えです。壁の道具が、ひとつへっています。やかんの口が、反対を向いています。湯のみの模様が、変わっていますね。 |

### 4-9. 第5問 神社・上級（8:07〜9:55）
| 時刻 | セリフ |
|---|---|
| 8:07 | 第5問、上級。神社です。 |
| 8:10 | 最後の問題です。じっくりどうぞ。 |
| 8:14〜8:55 | （黙って探す時間） |
| 8:55 | ヒントです。手前の道のあたりを、よく見てくださいね。（違い③のハトの辺り） |
| 9:01〜9:30 | （黙って探す時間） |
| 9:30 | あと10秒です。 |
| 9:40 | 答えです。灯籠のてっぺんの飾りが、ありません。鳥居の柱の根もとが、赤くなりました。右のハトが、反対を向いていますね。 |

### 4-10. エンディング（9:55〜10:15・20秒・終了画面用）
| 時刻 | 表情 | セリフ（82字） | 画面 |
|---|---|---|---|
| 9:55 | やったー | これで5問、おしまいです。おつかれさまでした。 | こよみ先生が登場。紙ふぶき |
| 9:59 | にっこり | 15個の違い、いくつ見つかりましたか。画面で、今日の称号を見てくださいね。 | 称号の表（下） |
| 10:06 | ウインク | 次回も秋の絵で5問です。チャンネル登録をして、また来てください。 | 終了画面（次の動画・登録ボタン） |

**今日の称号（画面に表示。15個中いくつ見つけたか）**
| 見つけた数 | 称号 |
|---|---|
| 15個 | 秋の名探偵 |
| 11〜14個 | もみじ名人 |
| 6〜10個 | 実りの秋さん |
| 0〜5個 | どんぐりさん（これから、ぐんぐん育ちます） |

【意見】
- 難易度を上げたので、称号の区切りは前の版より甘めでもよいかもしれない。区切りは今のままにし、分析部のコメントの反応を見て直す。
- 一番下の称号も、責めない言い方にしてある。

---

## 5. うんちく：「もみじ」と万葉集の「黄葉」

【事実】調査部の本文での確認（research_unchiku.md「本文での確認（2026-11-05）」。コトバンクのページの本文を読んだもの）

| 台本 | 内容 | 本文での裏付け |
|---|---|---|
| 5:53 | 「もみじ」は、動詞「もみず（古くは もみつ）」の連用形が名詞になったことば。上代は「もみち」と清音で読んだ | 精選版 日本国語大辞典、デジタル大辞泉（コトバンク「紅葉」）、日本大百科全書（コトバンク「もみじ」） |
| 6:04 | 『万葉集』では、「黄葉」と書いて「もみち」と読むのが通例だった | 日本大百科全書（コトバンク「もみじ」）、精選版 日本国語大辞典「こうよう【黄葉】」の補助注記（コトバンク「黄葉」） |
| 6:12 | 平安時代になると、赤く紅葉する楓（かえで）が秋の代表とされるようになった。『古今集』の秋の歌も紅葉の歌が中心 | 改訂新版 世界大百科事典（コトバンク「もみじ」）、日本大百科全書（同） |

- 6:12 は、前の文（「紅葉と書くことがふえたのは平安時代から」）から**案Bに差し替えた**。書き方の変化は、本文で読めた出典が1つしかなかったため（事業部長の指示）。
- 数字（「紅葉」と書く例の数など）は、出典ごとに違うので台本に入れない。
- 「揉み出づ」の説は辞典の本文に出てこないので使わない。医学的な効果には触れていない。

出典（主な出典は、本文を読んだコトバンクの3ページ）：
- コトバンク「紅葉」（精選版 日本国語大辞典・デジタル大辞泉）：https://kotobank.jp/word/%E7%B4%85%E8%91%89-63295
- コトバンク「もみじ」（日本大百科全書〔執筆：小町谷照彦〕・改訂新版 世界大百科事典）：https://kotobank.jp/word/%E3%82%82%E3%81%BF%E3%81%98-1601082
- コトバンク「黄葉」（精選版 日本国語大辞典）：https://kotobank.jp/word/%E9%BB%84%E8%91%89
- 補助：大阪大学の論文（上代は清音の「もみつ」）：https://ir.library.osaka-u.ac.jp/repo/ouka/all/84028/ooe_043_010.pdf
- JapanKnowledge のURLは外した（開けなかった。404）。

---

## 6. タイトル・説明欄・タグ

### タイトル案（型：【脳トレ】＋季節のテーマ＋ジャンル＋こよみ先生と10分）
1. 【脳トレ】柿と紅葉の秋 間違い探し5問｜こよみ先生と10分
2. 【脳トレ】秋の縁側から神社まで 間違い探し5問｜こよみ先生と10分
3. 【脳トレ】柿と紅葉の秋 間違い探し5問 初級から上級まで｜こよみ先生と10分

**推す案：1**（前の版と同じ）
【意見】
- 「柿」「紅葉」は一目で秋とわかる。サムネイルの絵とも合う。
- 3は、難易度を上げたことが伝わるが、長くてスマホで後ろが切れやすい。分析部の結果が出たら見直す。

### 説明欄（本文）
```
秋の間違い探しを5問おとどけします。こよみ先生といっしょに、毎日の頭の体操をどうぞ。

今日の5問
第1問 縁側（初級）
第2問 商店街（初級）
第3問 山道（中級）
第4問 台所（中級）
第5問 神社（上級）

【あそびかた】
・全部で5問です。
・1問90秒で、右の絵の、左の絵との違いを3つ探してください。
・45秒たつと、こよみ先生が声でヒントを出します。
・最後に、見つけた数で「今日の称号」をおくります。

【目次】
0:00 オープニング
0:15 ルール説明
0:25 第1問 縁側（初級）
1:58 第1問の答え
2:13 第2問 商店街（初級）
3:46 第2問の答え
4:01 第3問 山道（中級）
5:34 第3問の答え
5:49 こよみ先生の秋の小話「もみじ」
6:19 第4問 台所（中級）
7:52 第4問の答え
8:07 第5問 神社（上級）
9:40 第5問の答え
9:55 エンディング・今日の称号

【投稿】毎週 月・水・金曜日に新しい問題をお届けします

【クレジット】
音声：Fish Audio（AIで合成した音声です）
BGM・効果音：オリジナル（制作部がプログラムで作成）

#脳トレ #間違い探し #頭の体操
```
【事実】
- 目次の時刻は4章の台本の秒数から計算した。各問は、カード3秒＋出題90秒＋答え15秒＝108秒。構成の秒数は前の版と変わっていないので、時刻も同じになる。
- YouTubeのチャプターの条件（0:00から始まる・各区間10秒以上）を満たす。一番短い区間はルール説明の10秒。
- VOICEVOX の表記は外した。Fish Audio の規約に表記の義務はないが、AIで作ったことを明かすよう求めている（departments/production/voice.md）。

### タグ（11個）
脳トレ, 間違い探し, 頭の体操, 秋の間違い探し, 間違い探し 高齢者, シニア 脳トレ, 介護 レクリエーション, 脳トレ 秋, 間違い探し 3つ, こよみ先生, まいにち脳トレ

---

## 7. 合計時間

| パート | 計算 | 秒 |
|---|---|---|
| オープニング | | 15 |
| ルール説明 | | 10 |
| 第1〜3問 | (3＋90＋15)×3 | 324 |
| うんちく | | 30 |
| 第4〜5問 | (3＋90＋15)×2 | 216 |
| エンディング | | 20 |
| **合計** | | **615秒＝10分15秒** |

【事実】concept.md の秒数どおりに積むと10分15秒になり、「約10分」の範囲に入る。前の版と同じ長さ。

---

## 8. 次に頼むこと
- production：
  - 縦長の元の絵5枚を作る（4:5で作り、8:9に切り出す）。そのあと描き直しを5回。
  - 物の幅を計り、2-2章の幅（大きすぎ・小さすぎの両方）と、違いを置かない所（上5%・下15%）を確かめる。
  - 声は Fish Audio で作り、読み違いは4-0の表で直す。うんちく 6:12（28字）が7秒の枠に入るかを確かめる。
- research：うんちくの本文確認は済んだ（反映済み）。
- audit：作り直した plan.md と、完成した絵・動画を審査する。とくに「易しすぎないか」「上級の色の違いが1つだけか」を見る。

---

## 作り直しで変えたところ（2026-11-05・11-06、前の版＝コミット 89ec39b との違い。11-06 の行は日付つき）

| 場所 | 前の版 | 作り直し版 | 理由 |
|---|---|---|---|
| 2章 画面 | 絵1枚は940×529（横長・16:9）。右下にこよみ先生 | 絵1枚は960×1080（約8:9）で、画面いっぱい。上に帯（5%）、下に字幕（12%）。違いは上5%・下15%に置かない | CEO決定（画面のつくり） |
| 2章 プロンプト | 横長の構図。第1問は見本の絵を使い回せる | 5問とも縦長に近い構図で書き直し（4:5で作り、8:9に切り出す案）。見本の使い回しはやめる | 横長の絵は使えない |
| 2-2章・3章 難易度 | 初級5〜7%、中級4〜5%、上級3〜3.5%（画面幅） | 初級3〜4%、中級2〜3%、上級1.5〜2%（画面幅）。中級に本数・向き・模様、上級に色・背景の細部を入れる | CEO決定（1段階引き上げ）。ng-list「第1回は易しすぎた」 |
| 3章 違い15個 | 急須・竹かご・ねこ／自転車・かぼちゃ・犬／リス・リュック・石の塔／さんま・やかん・さつまいも／ハト・ほうき・灯籠2基 | 下駄・柿・しっぽ／自転車のかご・かぼちゃ・栗の入れ物／きのこ・リスの向き・手ぬぐいの模様／さつまいもの本数・やかんの向き・湯のみの模様／よだれかけの色・屋根の鰹木・灯籠の窓 | 新しい水準で選び直した（やかんの向き・かぼちゃは、小さめにして残した） |
| 4章 表情 | 全セリフに表情を指定。ヒントはウインク | 表情はオープニング・ルール説明・うんちく・エンディングだけ。ヒントは声＋うっすら示す | CEO決定（出題中・答え合わせ中はキャラの絵を出さない） |
| 4章 ヒント・答えのセリフ | 前の違いに合わせた文 | 新しい違いに合わせて書き直し。速さはどれも300字/分以下 | 違いを変えたため |
| 4-0 読み | 「山道」だけ | 読みの表を追加（山道・紅葉・黄葉・灯籠・お社など）。「2本」は使わない | Fish Audio が読み違えたときのため |
| 4-7・5章 うんちく | 6:12「『紅葉』と書くことがふえたのは、平安時代からだそうです。」。出典はJapanKnowledgeを含む検索の抜粋 | 6:12を「平安時代になると、赤いもみじが秋の主役になったといわれます。」に差し替えた（案B）。画面は平安・古今集の秋の歌の話にし、黄葉から紅葉への矢印はやめた。5:53・6:04はそのまま。出典はコトバンク「紅葉」「もみじ」「黄葉」の本文を中心にし、JapanKnowledgeを外した | 調査部の本文確認（2026-11-05）と事業部長の指示 |
| 6章 説明欄 | 音声：VOICEVOX:冥鳴ひまり。ヒント「こよみ先生がヒントを出します」 | 音声：Fish Audio（AIで合成した音声です）。ヒント「声でヒントを出します」 | CEO決定（声） |
| 6章 タイトル | 3案目「実りの秋」 | 3案目を「初級から上級まで」に。推す案は1のまま | 難易度を上げたことを伝える案を入れた |
| 7章 合計時間・目次 | 615秒 | 615秒（変わらない） | 構成の秒数が同じ |
| 3章 違い15個（2026-11-06） | 下駄・柿・しっぽ／自転車のかご・かぼちゃ・栗の入れ物／きのこ・リスの向き・手ぬぐいの模様／さつまいもの本数・やかんの向き・湯のみの模様／よだれかけの色・屋根の鰹木・灯籠の窓 | 鼻緒・柿・湯のみの形／さつまいも・首輪・提灯の形／いがぐり・きのこの水玉・石の塔／壁のへら・やかんの向き・湯のみの模様／灯籠の宝珠・鳥居の根巻きの色・ハトの向き（鳥居の横木の端は、描き直しで2回とも消えなかったため宝珠に差し替え）。実測値と位置を併記した | 描いた物が目安の約2倍の大きさになったため、制作部が実測して選び直した（diff_candidates.md）。第5問③はプログラムで左右反転して作る |
| 4章 ヒント（2026-11-06） | 第2問「栗のあたり」、第3問「ベンチの上」、第5問「お社の屋根」 | 第2問「お店の上のほう」（提灯）、第3問「木の根もとのあたり」（きのこ）、第5問「手前の道のあたり」（ハト）。第1問・第4問はそのまま | 違いを選び直したため。答えは言わず、辺りだけを示す |
| 4章 答えのセリフ（2026-11-06） | 前の違いに合わせた文 | 5問とも書き直した。最大50字で、15秒の枠に収まる（200字/分以下） | 違いを選び直したため |
| 4-0 読み（2026-11-06） | 山道・紅葉・黄葉など | 鼻緒・湯のみ・首輪・提灯・いがぐり・水玉模様・鳥居・根もと・横木・宝珠・へらを追加した。「よっつ」はひらがなにし、聞き取りにくいことばは言いかえた | 新しいことばが入ったため |
