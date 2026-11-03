# 001 企画書・台本：秋の間違い探し5問（約10分）

- 作成：企画部（2026-11-03）／状態：**監査待ち**（audit の審査前。うんちくは research の裏付け待ち）
- 依頼：CEO（Ichiro）指示、事業部長経由
- 投稿日：未定（月・水・金のいずれか。事業部長が決める）
- 書き方：【事実】は確認済みのこと・規則から計算したこと。【意見】は企画部の判断・提案。

---

## 1. 企画の概要

| 項目 | 内容 |
|---|---|
| テーマ | 秋（実りと紅葉：柿・栗・さんま・もみじ・いちょう） |
| ジャンル | 間違い探し 5問 × 違い3つ ＝ 15個 |
| 長さ | 10分15秒（計算は7章） |
| うんちく | 「もみじ」ということばと、万葉集の「黄葉」 |

| 問 | 難易度 | 場面 | 違いの型（消える／増える／形・向き） |
|---|---|---|---|
| 第1問 | 初級 | 縁側 | 消える・増える・形（ねこが起きる） |
| 第2問 | 初級 | 商店街（八百屋の店先） | 消える・増える・向き（犬がうしろ向き） |
| 第3問 | 中級 | 山道 | 増える・消える・形（石の塔が高くなる） |
| 第4問 | 中級 | 台所 | 増える・向き（やかんの口）・消える |
| 第5問 | 上級 | 神社 | 増える・向き（ほうきが倒れる）・消える |

【事実】重複ルールの確認（`knowledge/neta.md`）
- ネタ帳に使用済みの回はまだない（001が最初）。テーマ60日・場面14日・うんちく再利用なし、いずれも抵触しない。
- 見本 `001-sample` は非公開の見本で、本番の回としては数えていない。
- 5問の場面はすべて別。どの問も色だけの違いはない。

【意見】ネタ帳の運用について
- 全回を季節で統一する方針（concept.md）なので、「秋」をテーマ単位にすると60日ルールで2本目から使えなくなる。テーマは「柿」「紅葉」「新米」など**一段細かい単位**で数えるのがよいと考える（ネタ帳の001行も小テーマで記録した）。事業部長の確認がほしい。
- 週3本×5場面だと、14日で最大30場面を使う。concept.md の「30場面以上」でぎりぎりになるので、場面の候補を40程度まで増やしておくとよい。002〜007の企画で場面を割り振るとき、今回の5場面は 2026-11-17 以降まで使わない。

---

## 2. 絵の指示（制作部 → Gemini）

### 2-1. 共通

【事実】画面の作り（`scripts/compose_sample.py`）
- 1枚の絵は画面に幅940px（画面幅1920pxの**約49%**）で映る。したがって「画面幅の3%」＝**絵の幅の約6.1%**。
- こよみ先生は画面右下（x1500〜1880, y680〜1070）にいて、右の絵（y110〜639）とは重ならない。

【意見】難易度ごとの大きさの目安（物そのものの幅。画面幅で計った値）

| 難易度 | 画面幅に対して | 絵の幅に対して | 目立ち方 |
|---|---|---|---|
| 初級 | 5〜7% | 10〜15% | 絵の手前・中央寄り。まわりと色がちがう物 |
| 中級 | 4〜5% | 8〜10% | 中ほど。まわりに似た物がある |
| 上級 | 3〜3.5% | 6〜7% | 奥や端。似た色の中にある。ただし3%未満にはしない |

制作部は元の絵ができたら物の幅を計り、上の表に合わない物は違いの対象を差し替える（企画部に相談）。

**共通のスタイル文（各場面のプロンプトの先頭に付ける）**
```
A warm Japanese picture-book illustration in soft watercolor with gentle colored-pencil outlines,
like a cozy picture book for all ages. Autumn palette: persimmon orange, maple red, ginkgo yellow,
warm browns and soft greens. Natural, hand-drawn, slightly rounded shapes; not geometric, not flat
vector, not photorealistic. Wide 16:9 landscape composition. No people. Absolutely no text, letters,
numbers, logos or symbols anywhere, including on signs, curtains, boxes and lanterns.
The main objects listed below are large, clearly separated from each other with some space around
each, and fully visible (not cut off by the picture edge and not hidden behind other objects).
```
- 設定：`gemini_image.generate(prompt, aspect="16:9", size="2K")`（見本と同じ）。

### 2-2. 第1問 縁側（初級）
【意見】見本の `outputs/2026-11-03_001-sample/picture_a.png` は監査済みで、下の物（急須・竹かご・ねこ）がそろっている。**見本の元の絵をそのまま使えば呼び出しを1回減らせる**（見本の違いは使わず、違いは下の3つを新しく作る）。描き直す場合は次のプロンプト。
```
Scene: a traditional Japanese wooden veranda (engawa) open to a small autumn garden in warm
late-afternoon light. Main objects: (1) a persimmon tree with orange fruit on the left of the garden;
(2) several strings of dried persimmons hanging from the eaves on the right; (3) a moss-covered stone
lantern in the middle of the garden with red maple leaves around it; (4) a calico cat sleeping curled
up on a flat floor cushion on the veranda, about one seventh of the picture width; (5) a large round
wooden tray in the front left holding three persimmons, a fairly big brown clay teapot (about one
tenth of the picture width) and two teacups; (6) a large empty woven bamboo basket standing on the
veranda floor to the right of the cat, about one seventh of the picture width. Leave plain wooden
floor around the tray, the cat and the basket.
```

### 2-3. 第2問 商店街（初級）
```
Scene: a cozy old Japanese shopping street in autumn, seen from the street in front of a small fruit
and vegetable shop with a wooden front and a tiled roof. Main objects: (1) a wooden display stand in
front of the shop with flat bamboo baskets of persimmons, chestnuts and sweet potatoes; (2) one big
green Japanese pumpkin (kabocha) sitting alone on the right end of the stand, about one tenth of the
picture width, with empty space next to it; (3) a plain indigo shop curtain (noren) with no writing
and no pattern; (4) two round red paper lanterns hanging from the eaves, completely blank; (5) an
old-fashioned black bicycle parked on the left, about one sixth of the picture width; (6) a Shiba dog
sitting on the ground in front of the stand, facing the viewer, about one tenth of the picture width;
(7) a potted yellow chrysanthemum by the door; a few ginkgo leaves on the stone pavement.
The neighbouring shops in the background are simple and also have no writing.
```
【意見】看板・のれん・提灯に文字が出やすい場面。文字が出たら描き直す（予備の呼び出しを使う）。

### 2-4. 第3問 山道（中級）
```
Scene: a gentle mountain walking path in autumn, with rough stone steps going up through red maple
and yellow trees, soft mist on distant hills. Main objects: (1) a small arched wooden footbridge over
a little stream on the left; (2) a wooden bench beside the path with a small red rucksack on it, the
rucksack about one eleventh of the picture width; (3) a tree stump in the foreground with one brown
squirrel holding an acorn on it, the squirrel about one eleventh of the picture width, with free space
on the stump next to it; (4) a small stack of three round stones (a little cairn) at the side of the
path, about one twelfth of the picture width; (5) a cluster of brown mushrooms at the foot of a tree;
(6) a few spiky chestnut burrs on the ground. No signposts.
```

### 2-5. 第4問 台所（中級）
```
Scene: an old-fashioned Japanese country kitchen in autumn with dark wooden beams, a window showing a
persimmon tree outside, and a clay cooking stove (kamado). Main objects: (1) a sturdy wooden table in
the front; (2) a long oval plate on the table with two grilled Pacific saury fish side by side, with
room for one more; (3) a round bamboo colander (zaru) on the table piled with purple sweet potatoes,
about one ninth of the picture width; (4) a metal kettle with its spout clearly pointing to the left,
sitting on the stove, about one tenth of the picture width; (5) a clay pot (donabe) with a lid;
(6) a small basket of chestnuts; (7) a few wooden ladles hanging on the wall.
No clock, no calendar, no paper with writing.
```

### 2-6. 第5問 神社（上級）
```
Scene: the quiet grounds of a small Japanese shrine in late autumn, with a big golden ginkgo tree and
yellow leaves scattered on the stone-paved path. Main objects: (1) a red torii gate on the left;
(2) a pair of small stone lanterns standing side by side in the background near the ginkgo tree,
each about one fourteenth of the picture width; (3) a pair of stone guardian lion-dog statues
(komainu) on pedestals; (4) a small wooden shrine building with a plain wooden offering box with no
writing; (5) two grey pigeons pecking on the path, each about one fourteenth of the picture width;
(6) a bamboo broom leaning diagonally against the ginkgo tree trunk, about one twelfth of the picture
width; (7) a stone water basin with two bamboo ladles. No wooden plaques with writing, no paper
charms with letters.
```

---

## 3. 各問の違い3つ

【事実】作り方は concept.md どおり、**1問につき1回の描き直しで3つまとめて作り**、範囲ごとに元の絵へ貼り戻す（`scripts/make_differences.py`）。範囲（box）は元の絵ができてから制作部が決める。

【意見】描き直しの注意（見本READMEの反省から）
- `make_differences.py` の `KEEP` は「消す」用の文（"Fill the area naturally with what would be behind it"）。「増える」「形が変わる」には次の文を使うことを提案する：
  `Keep everything else in the picture exactly the same: same composition, same position of every object, same colors, same style. Do not add or remove anything else. Leave no faint outline, ghost or smudge. No text.`
- 範囲は物より一回り広く取る（ぼかしで元の物が透けないように）。動物の一部を変えるものは full 方式が安全（見本③の反省）。
- 「増える」は、増えた物が範囲の中に収まるように、範囲を空いている場所まで広げておく。

### 第1問 縁側（初級）
| # | 物 | どう変える | 型 | 大きさの目安（画面幅） | こよみ先生の一言（答え合わせ） |
|---|---|---|---|---|---|
| 1 | お盆の上の急須 | なくなる（お盆の木目が見える。柿と湯のみは残す） | 消える | 約5% | 「急須がなくなっています。」 |
| 2 | 空の竹かご | 中に柿が山盛りになる | 増える | 約6.5% | 「かごに、柿がいっぱい。」 |
| 3 | 眠っているねこ | 顔を上げて目を開ける（同じ座布団・同じ毛の柄） | 形が変わる | 約7% | 「ねこちゃんが、目をさましましたね。」 |

描き直しの指示（1回）：
```
Edit this illustration and make exactly these three changes: (a) remove the brown clay teapot from
the round tray, showing the empty wooden tray where it stood; the persimmons and teacups stay;
(b) fill the empty bamboo basket with a heap of orange persimmons; (c) the calico cat wakes up: it
lifts its head and opens its eyes, still lying on the same cushion with the same fur pattern.
```

### 第2問 商店街（初級）
| # | 物 | どう変える | 型 | 大きさの目安 | 一言 |
|---|---|---|---|---|---|
| 1 | 自転車 | なくなる（後ろの店の壁と道が見える） | 消える | 約7% | 「自転車がありません。」 |
| 2 | かぼちゃ | 1つ → 2つに増える（となりの空きに） | 増える | 約5% | 「かぼちゃが、ふたつに増えました。」 |
| 3 | 柴犬 | こちら向きのおすわり → うしろ向き（しっぽとおしりが見える） | 向きが変わる | 約5% | 「わんちゃんは、うしろ向きですね。」 |
```
Edit this illustration and make exactly these three changes: (a) remove the black bicycle, showing
the shop wall and the stone pavement behind it; (b) add a second green pumpkin of the same size right
next to the first one on the display stand; (c) the Shiba dog sits in the same place but now faces
away from the viewer, so we see its back and curled tail.
```

### 第3問 山道（中級）
| # | 物 | どう変える | 型 | 大きさの目安 | 一言 |
|---|---|---|---|---|---|
| 1 | 切り株のリス | 1ぴき → 2ひき | 増える | 約4.5% | 「リスが2ひきになりました。」 |
| 2 | ベンチの赤いリュック | なくなる（ベンチの板が見える） | 消える | 約4.5% | 「リュックがありません。」 |
| 3 | 石の塔（3段） | 5段に高くなる | 形が変わる | 約4%（高さは約1.7倍） | 「石の塔が、高くなりましたね。」 |
```
Edit this illustration and make exactly these three changes: (a) add a second brown squirrel of the
same size sitting next to the first one on the tree stump; (b) remove the red rucksack from the
wooden bench, showing the plain bench boards; (c) make the little stack of stones taller: five round
stones instead of three, the same kind of stones, in the same place.
```

### 第4問 台所（中級）
| # | 物 | どう変える | 型 | 大きさの目安 | 一言 |
|---|---|---|---|---|---|
| 1 | お皿のさんま | 2ひき → 3びき | 増える | 約5.5%（お皿の空き部分） | 「さんまが3びきに増えました。」 |
| 2 | かまどの上のやかん | 注ぎ口が左向き → 右向き | 向きが変わる | 約5% | 「やかんの口が、反対を向いています。」 |
| 3 | ざるのさつまいも | なくなる（空のざるだけ残る） | 消える | 約5.5% | 「おいもが消えて、ざるが空っぽですね。」 |
```
Edit this illustration and make exactly these three changes: (a) add a third grilled saury fish on
the oval plate, next to the other two; (b) turn the kettle so that its spout points to the right
instead of the left, same kettle, same place; (c) remove all the sweet potatoes from the bamboo
colander, leaving the empty colander on the table.
```
【意見】②は描き直しでやかん全体が少し変わりやすい。範囲はやかん全体を囲み、形だけが反転に見えるか監査で確認する。

### 第5問 神社（上級）
| # | 物 | どう変える | 型 | 大きさの目安 | 一言 |
|---|---|---|---|---|---|
| 1 | 参道のハト | 2羽 → 3羽 | 増える | 約3.5% | 「ハトが1羽増えました。」 |
| 2 | いちょうに立てかけた竹ぼうき | 地面に倒れて横になる | 向きが変わる | 約4%（倒れた後は約6%） | 「ほうきが、たおれています。」 |
| 3 | 奥の小さな石灯籠（2基） | 片方がなくなる（いちょうの落ち葉と地面） | 消える | 約3.5% | 「奥の灯籠が、ひとつありませんね。」（びっくり） |
```
Edit this illustration and make exactly these three changes: (a) add a third grey pigeon of the same
size pecking on the path near the other two; (b) the bamboo broom has fallen over and now lies flat on
the ground at the foot of the ginkgo tree; (c) remove the right one of the two small stone lanterns
in the background, showing the ground with yellow ginkgo leaves and the trees behind it.
```
【意見】上級は「奥にある・似た物のそば」で難しくする。物の大きさは3%を割らないようにする（計って3%未満なら、①のハトを少し大きく描き直す）。

### 違いの型の集計
【事実】15個の内訳：消える5、増える5、形・向きが変わる5。色だけの違いは0。

---

## 4. 台本（秒数つき）

- 時刻は動画の頭からの時刻。字数は句読点とかぎかっこを除いた数。
- 【事実】各セリフの字数／話す枠の秒数から計算した速さは、最大で**252字/分（オープニング）**。どのパートも300字/分を超えない。動画全体では723字（約71字/分）。
- 表情：ふつう／にっこり／びっくり／かんがえ中／ウインク／やったー。
- 出題中に話すのは「開始」「45秒のヒント」「残り10秒」の3回だけ。それ以外の約75秒は黙って探す時間（表情は「かんがえ中」でゆらゆら・まばたき）。

### 4-1. オープニング（0:00〜0:15・15秒）
| 時刻 | 表情 | セリフ | 画面 |
|---|---|---|---|
| 0:00 | にっこり | みなさん、こんにちは。こよみ先生です。秋がふかまって、柿のおいしい季節になりましたね。今日は、秋の間違い探しを5問、いっしょに楽しみましょう。（63字） | タイトル「秋の間違い探し 5問」、5問の絵をうすく並べる |

### 4-2. ルール説明（0:15〜0:25・10秒）
| 時刻 | 表情 | セリフ | 画面 |
|---|---|---|---|
| 0:15 | ふつう | 左と右の絵をくらべます。90秒で、右の絵の違いを3つ探してください。（31字） | 左右に絵の枠、「90秒」「違いは3つ」の大きな文字 |

### 4-3. 各問の流れ（共通）
| 問の頭から | 長さ | 内容 | 表情 |
|---|---|---|---|
| 0秒 | 3秒 | 難易度カード（スライド／フェード） | ふつう |
| 3秒 | 90秒 | 出題。残り時間のバー。残り10秒でカウント音 | ふつう → かんがえ中 → ウインク（45秒） → かんがえ中 |
| 93秒 | 15秒 | 答え合わせ。赤丸を1つずつ効果音つき | にっこり |

### 4-4. 第1問 縁側・初級（0:25〜2:13）
| 時刻 | 表情 | セリフ |
|---|---|---|
| 0:25 | ふつう | 第1問、初級。縁側です。（9字・カード） |
| 0:28 | ふつう | さあ、どうぞ。 |
| 0:31〜1:13 | かんがえ中 | （黙って探す時間） |
| 1:13 | ウインク | ヒントです。お茶のお盆のあたりを、よく見てくださいね。（違い①の辺りを光らせる） |
| 1:19〜1:48 | かんがえ中 | （黙って探す時間） |
| 1:48 | ふつう | あと10秒です。（カウント音） |
| 1:58 | にっこり | 答えです。急須がなくなっています。かごに、柿がいっぱい。ねこちゃんが、目をさましましたね。（赤丸①②③） |

### 4-5. 第2問 商店街・初級（2:13〜4:01）
| 時刻 | 表情 | セリフ |
|---|---|---|
| 2:13 | ふつう | 第2問、初級。商店街です。 |
| 2:16 | ふつう | さあ、どうぞ。 |
| 2:19〜3:01 | かんがえ中 | （黙って探す時間） |
| 3:01 | ウインク | ヒントです。お店の前の、わんちゃんを見てください。（違い③の辺り） |
| 3:07〜3:36 | かんがえ中 | （黙って探す時間） |
| 3:36 | ふつう | あと10秒です。 |
| 3:46 | にっこり | 答えです。自転車がありません。かぼちゃが、ふたつに増えました。わんちゃんは、うしろ向きですね。 |

### 4-6. 第3問 山道・中級（4:01〜5:49）
| 時刻 | 表情 | セリフ |
|---|---|---|
| 4:01 | ふつう | 第3問、中級。山道です。 |
| 4:04 | ふつう | 少しむずかしくなります。どうぞ。 |
| 4:08〜4:49 | かんがえ中 | （黙って探す時間） |
| 4:49 | ウインク | ヒントです。道ばたの、石のあたりを見てください。（違い③の辺り） |
| 4:55〜5:24 | かんがえ中 | （黙って探す時間） |
| 5:24 | ふつう | あと10秒です。 |
| 5:34 | にっこり | 答えです。リスが2ひきになりました。リュックがありません。石の塔が、高くなりましたね。 |

### 4-7. うんちく（5:49〜6:19・30秒）
| 時刻 | 表情 | セリフ（106字） | 画面 |
|---|---|---|---|
| 5:49 | にっこり | ここで、ひと休み。秋の小話です。 | もみじ・いちょうの葉が舞う |
| 5:53 | ふつう | 「もみじ」は、葉の色が変わることをあらわす、むかしのことば「もみつ」から生まれたといわれます。 | 「もみつ → もみじ」 |
| 6:04 | びっくり | 万葉集のころは、黄色い葉と書いて「もみち」と読むのがふつうでした。 | 大きく「黄葉」（ふりがな もみち） |
| 6:12 | にっこり | 「紅葉」と書くことがふえたのは、平安時代からだそうです。 | 「黄葉 → 紅葉」 |

### 4-8. 第4問 台所・中級（6:19〜8:07）
| 時刻 | 表情 | セリフ |
|---|---|---|
| 6:19 | ふつう | 第4問、中級。台所です。 |
| 6:22 | ふつう | 後半です。どうぞ。 |
| 6:25〜7:07 | かんがえ中 | （黙って探す時間） |
| 7:07 | ウインク | ヒントです。かまどの上を、よく見てくださいね。（違い②の辺り） |
| 7:13〜7:42 | かんがえ中 | （黙って探す時間） |
| 7:42 | ふつう | あと10秒です。 |
| 7:52 | にっこり | 答えです。さんまが3びきに増えました。やかんの口が、反対を向いています。おいもが消えて、ざるが空っぽですね。 |

### 4-9. 第5問 神社・上級（8:07〜9:55）
| 時刻 | 表情 | セリフ |
|---|---|---|
| 8:07 | びっくり | 第5問、上級。神社です。 |
| 8:10 | ふつう | 最後の問題です。じっくりどうぞ。 |
| 8:14〜8:55 | かんがえ中 | （黙って探す時間） |
| 8:55 | ウインク | ヒントです。奥の、いちょうの木のそばを見てください。（違い③の辺り） |
| 9:01〜9:30 | かんがえ中 | （黙って探す時間） |
| 9:30 | ふつう | あと10秒です。 |
| 9:40 | にっこり→びっくり（③の赤丸で） | 答えです。ハトが1羽増えました。ほうきが、たおれています。奥の灯籠が、ひとつありませんね。 |

### 4-10. エンディング（9:55〜10:15・20秒・終了画面用）
| 時刻 | 表情 | セリフ（82字） | 画面 |
|---|---|---|---|
| 9:55 | やったー | これで5問、おしまいです。おつかれさまでした。 | 紙ふぶき |
| 9:59 | にっこり | 15個の違い、いくつ見つかりましたか。画面で、今日の称号を見てくださいね。 | 称号の表（下） |
| 10:06 | ウインク | 次回も秋の絵で5問です。チャンネル登録をして、また来てください。 | 終了画面（次の動画・登録ボタン） |

**今日の称号（画面に表示。15個中いくつ見つけたか）**
| 見つけた数 | 称号 |
|---|---|
| 15個 | 秋の名探偵 |
| 11〜14個 | もみじ名人 |
| 6〜10個 | 実りの秋さん |
| 0〜5個 | どんぐりさん（これから、ぐんぐん育ちます） |

【意見】一番下の称号も、責めない・ほめる言い方にした。次回予告は002の企画が決まったら場面名を入れる（字数が増える場合は「チャンネル登録を…」の行を短くして20秒に収める）。

---

## 5. うんちく：「もみじ」と万葉集の「黄葉」

【事実】（ウェブ検索で確認。出典は下）
1. 「もみじ」は、動詞「もみず（古くは もみつ）」＝秋に草木の葉が赤や黄に色づくこと、の連用形が名詞になったことば。上代（奈良時代ごろ）は「もみち」と清音で読んだ。
2. 『万葉集』では、「紅葉」「赤葉」と書く1、2の例を除いて、「黄葉」と書くのが通例だった。
3. 平安時代に入ると、『白氏文集』の影響もあって「紅葉」と書くようになった（辞典の説明）。また、『万葉集』では紅葉より黄葉を詠んだ歌の方が多いとされる（JR西日本の解説）。

出典：
- コトバンク「もみじ」（日本大百科全書ほか）：https://kotobank.jp/word/%E3%82%82%E3%81%BF%E3%81%98-1601082
- コトバンク「紅葉」（精選版 日本国語大辞典ほか）：https://kotobank.jp/word/紅葉-63295
- JR西日本「Blue Signal」vol.127：https://www.westjr.co.jp/company/info/issue/bsignal/09_vol_127/poet.html

【事実】確認の限界：この作業環境では kotobank.jp と japanknowledge.com のページを直接開けなかった（ネットワークの許可外）。上の内容は検索結果の抜粋で確認したもの。**research に、各ページの本文で1〜3を確かめてもらう必要がある**（調査部ルール：信頼できる出典2つ以上）。
- 語源には「紅花を揉んで色を出す『揉み出づ』から」という説もあるが、本文で確認できなかったため台本では使わない。台本は「〜といわれます」「〜だそうです」と言い切らない形にした。
- 医学的な効果には触れていない。

---

## 6. タイトル・説明欄・タグ

### タイトル案（型：【脳トレ】＋季節のテーマ＋ジャンル＋こよみ先生と10分）
1. 【脳トレ】柿と紅葉の秋 間違い探し5問｜こよみ先生と10分
2. 【脳トレ】秋の縁側から神社まで 間違い探し5問｜こよみ先生と10分
3. 【脳トレ】実りの秋 間違い探し5問｜こよみ先生と10分

**推す案：1**
【意見】理由：「柿」「紅葉」は一目で秋とわかり、サムネイルの絵（柿・もみじ）とも合う。2は場面が伝わるが長く、スマホで後ろが切れやすい。3は短いが中身が伝わりにくい。分析部の結果が出たら見直す。

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
・45秒たつと、こよみ先生がヒントを出します。
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

【投稿】毎週 月・水・金曜日 ○時ごろ（時刻は事業部長が記入）

【クレジット】
音声：VOICEVOX:（話者名・制作部が記入）
BGM・効果音：（制作部が音源と表記を記入）

#脳トレ #間違い探し #頭の体操
```
【事実】目次の時刻は4章の台本の秒数から計算した（各問＝カード3秒＋出題90秒＋答え15秒＝108秒）。YouTubeのチャプターは0:00から始まり、各区間10秒以上の条件を満たす（最短はルール説明・各問の答えの10〜15秒）。
【意見】「認知症予防」などの医学的な言い方は入れていない。AI生成の表示は concept.md で「原則不要」なので入れていないが、入れても害はないので事業部長の判断に任せる。

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

【事実】concept.md の秒数どおりに積むと10分15秒になる（「約10分」の範囲）。
【意見】10分ちょうどにそろえる必要があれば、各問の答え合わせを15秒→12秒にすると15秒短くなる（ただし赤丸3つを効果音つきで出すには15秒が見やすい）。今は concept.md どおりの15秒で出す。

---

## 8. 次に頼むこと
- research：5章のうんちく1〜3を出典本文で確認。
- production：元の絵5枚（第1問は見本の流用も可）＋描き直し5回。物の大きさを計り、3章の目安に合わない物は企画部へ。称号・うんちくの文字は動画側で入れる。
- audit：本 plan.md と完成した絵・答えの審査。
