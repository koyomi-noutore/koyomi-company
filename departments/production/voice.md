# 声：Fish Audio モデルの利用条件の確認

確認日：2026-11-05　確認者：事業部長（leader）。concept.md「声（2026-11-06 CEO決定）」の指示による。

## 対象のモデル
| 項目 | 内容（Fish Audio API `GET /model/{id}` の返り値） |
|---|---|
| モデルID | `63819275ce38440ea245ca988abf976e` |
| 名前 | 女性アナウンス |
| 説明 | 静かで力強く落ち着いた女性ボイス |
| 種類 | tts。利用者が作って公開したモデル（visibility: public、train_mode: fast） |
| 作成者 | 「escrow FH」（Fish Audio の利用者）。同じ作成者のモデルは5つあり、どれも「落ち着いた女性」「女性ナレーション」のような一般的な名前 |
| licensed | false（Fish Audio 公式のライセンス済みの声ではない） |
| DMCAによる削除 | なし（dmca_taken_down: false） |
| 利用回数 | 17,851回 |

## 規約の本文で確かめたこと（事実）
出典：Fish Audio 利用規約 https://fish.audio/terms （Effective date: August 18, 2024）。2026-11-05に本文を取得して読んだ。
- **商用利用**：無料の利用者は「個人的・非商用」に限られる。**有料サービスの利用者は商用利用が許される**（"if you are a user of Paid Services, you are licensed to use the Services for commercial uses …"）。
- **他の利用者が公開したモデル**：公開されたモデルは、サービスの機能が許す範囲で、他の利用者が使ってよい（Public User Submission の条項。"you grant all other users of the Services a license to access that Public User Submission, and to use and exercise all rights in it, as permitted by the functionality of the Services"）。
- **クレジット表記**：規約に表記の義務はない。
- **AIであることの表示**：AIで作ったものを、すべて人間が作ったように見せてはいけない（禁止事項 (q)）。配るときはAIで作ったと明かすことが勧められている。→ 説明欄に「音声はAIで合成しています（Fish Audio）」と書く。
- **他人の権利**：他人の知的財産権などを侵す使い方は禁止（禁止事項 (a)）。

## 会社のアカウントの状態（事実。APIで確認）
- 有料プラン：**plus（年払い）**。今の期間は **2026-12-07 まで**。自動更新は**オフ**（cancel_at_period_end: true）。
- API用の残高：0.83ドル（これまでのチャージは計5ドル）。今回の試しの読み上げ（2回）のあと、API用の残高もプランの枠（206,192／250,000）も変わらなかった。どこから引かれるかは未確認。

## 判断（意見）
- 有料プランの期間中なので、商用（収益化するYouTube）で使える。クレジット表記は不要だが、AI音声であることは説明欄に書く。
- 実在の人物や既存のキャラの声をまねたモデルかどうかは、**完全には確かめられない**。利用者が作ったモデルで、元になった声の出どころは公開されていないため。わかる範囲では、名前・説明・タグに実在の人物やキャラの名前はなく、削除の申し立てもない。concept.md の「まねたモデルなら使わない」には当たらないと判断して使う。ただし不安は残るので、CEOに報告する。
- **CEOに決めてほしいこと**：
  1. 2026-12-07 に有料プランが切れる。そのあとは商用利用の条件（有料サービスの利用者であること）を満たさなくなるおそれがある。更新するかどうか。
  2. 出どころがわかる声のほうが安心なら、Fish Audio 公式のライセンス済みの声か、自分たちで用意した声への切り替えを検討する。
