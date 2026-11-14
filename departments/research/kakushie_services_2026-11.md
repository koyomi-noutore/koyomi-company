# かくし絵（方法③）画像生成サービス候補の調査

調査日：2026-11-12／調査部
契約・登録・APIキー作成は一切していない（社則4章）。円換算は **1ドル=150円の仮定**。

## 先に伝えること（調査の限界）
- この調査環境では、WebFetch で各社の公式ページ（replicate.com、fal.ai、huggingface.co、runpod.io、segmind.com）と解説記事（activepieces.com）が **すべて開けなかった**（ネットワーク許可外で名前解決に失敗）。
- そのため部署ルール「出典2つ以上・うち1つは本文を開いて確認」を **満たせていない**。以下の数字・規約は、すべて **ウェブ検索の結果の要約（検索結果の抜粋）だけ** が根拠で、**本文未確認**。
- CEOに出す前に、下記URLのどれか（特に各社の料金ページとControlNetのライセンス全文）を本文で確かめる必要がある。許可が出れば、再度本文確認を行う（要：replicate.com / fal.ai / huggingface.co / runpod.io を許可）。

## 候補A：Replicate（1回いくらのAPI）
### 事実（検索抜粋ベース・本文未確認）
1. 提供：Replicate。Monster Labs の QR Code ControlNet を使った illusion 系モデルが複数ある。
   - lucataco/illusion-diffusion-hq：Monster Labs QrCode ControlNet + SD Realistic Vision v5.1。入力は prompt、入力画像、steps、guidance scale、seed、幅高さ、border など。
   - andreasjansson/illusion：controlnet_conditioning_scale の既定値が2.2（調整可）。入力画像なしだとQRコードが生成される＝シルエット画像を渡す使い方ができる。
   - 出典：https://replicate.com/lucataco/illusion-diffusion-hq ／ https://replicate.com/andreasjansson/illusion/versions/78f9ae9a2f745f2946ee682f6cc86f7c5b97b3c06cf9c0b672cc474e1ebd725f/api
2. 料金：lucataco/illusion-diffusion-hq は「1回あたり約$0.011」（新しいページ）／「約$0.020」（古いキャッシュ）と検索結果にあり、**数字が割れている**。
   - 仮に$0.011〜$0.020 = 約1.7〜3円/枚。1本20〜40枚で約33〜120円、月8本でも約260〜960円（意見：試算）。
   - GPU秒単価（別モデルを自前で動かす場合）：L40S $0.000975/秒（$3.51/時）、A100 80GB $0.0014/秒、H100 $0.001525/秒。出典：https://replicate.com/pricing （検索抜粋）、https://www.spheron.network/blog/replicate-pricing-2026-per-second-cost/
   - 月額の最低料金：**未確認**（従量課金と言われるが、本文で確認できていない）。
3. 商用利用：Replicateの利用規約の該当箇所は **未確認**。モデルごとの制約が別にある。lucataco版の土台は SD Realistic Vision v5.1（SD1.5系）。ControlNet本体は下の「ライセンス共通事項」参照。
4. 日本から使えるか・支払い：**未確認**（クレジットカード払いと思われるが根拠なし）。Python公式クライアントがあり、環境変数 REPLICATE_API_TOKEN で呼ぶ形が一般的（一般知識。本文未確認）。
5. 画風（意見）：土台がRealistic Vision（写実系）なので、そのままだと水彩・絵本風には寄りにくい。プロンプトで「watercolor, picture book」を指定するか、水彩系モデルを土台にした版を探す必要がある。作例の確認はできていない。

## 候補B：fal.ai（1回いくらのAPI、モデルごとの単位）
### 事実（検索抜粋ベース・本文未確認）
1. 提供：fal.ai。`fal-ai/illusion-diffusion`（「画像で条件づけて illusion を作る」）がある。SDXL系は `fal-ai/sdxl-controlnet-union`（汎用ControlNet）。QRモンスター専用のSDXLモデル（monster-labs/control_v1p_sdxl_qrcode_monster）は、fal上では見つからなかった。`fal-ai/controlnetsdxl` は廃止（deprecated）。
   - 出典：https://fal.ai/models/fal-ai/illusion-diffusion/api ／ https://fal.ai/models/fal-ai/sdxl-controlnet-union/api
   - 入力スキーマ（シルエット画像・conditioning scale）は **未確認**。
2. 料金：illusion-diffusion のページは「1計算秒あたり$0」と表示され（プレースホルダと思われる）、**単価は不明**。fal のドキュメントは「モデルごとに課金単位が違う（1枚／1メガピクセル／計算秒）」と説明。出典：https://fal.ai/docs/documentation/model-apis/pricing.md ／ https://pricepertoken.com/fal-ai-pricing 。月額最低料金：**未確認**。
3. 商用利用・規約：**未確認**。
4. 日本から使えるか・支払い：**未確認**。PythonクライアントはあるはずだがURLでは確認できていない。
5. 画風（意見）：SDXLベースが使えるなら、SD1.5より水彩・絵本風は出しやすいはず。ただし上記のとおりQR専用SDXL ControlNetは未提供の可能性があり、効き具合の調整ができるか未確認。

## 候補C：RunPod（自前でGPUを借りる）
### 事実（検索抜粋ベース・本文未確認）
1. 提供：RunPod。GPUを時間貸しし、自分で Stable Diffusion + Monster Labs の ControlNet（diffusers）を動かす。入力画像・conditioning scale は自分のコードで自由に調整できる（ControlNet自体の仕様。一般知識）。
   - Monster Labs の ControlNet：SD1.5版 https://huggingface.co/monster-labs/control_v1p_sd15_qrcode_monster ／ SDXL版 https://huggingface.co/monster-labs/control_v1p_sdxl_qrcode_monster 。モデルカードでは、ガイダンスの値が高いと読みやすく、低いと創造的になる、と説明される（検索抜粋）。
2. 料金：RTX 4090 が Community Cloud $0.34/時、Secure Cloud $0.69/時（2026年5〜8月時点の複数の解説記事。RunPod公式のRTX 4090ページにも同じ数字とされる）。秒単位課金。出典：https://www.runpod.io/gpu-instance/rtx-4090 ／ https://diyai.io/ai-tools/hosting/runpod-pricing/
   - 試算（意見）：1本の制作で2時間借りると、$0.34〜0.69×2 = $0.68〜1.38 = 約100〜210円。月8本で約800〜1,700円。ただし起動中は何もしなくても課金される。止め忘れに注意。
   - 最低入金額・月額最低：**未確認**。
3. 商用利用：RunPod側の規約は **未確認**。使うモデルのライセンスに従う（下記）。
4. 日本から使えるか・支払い：**未確認**。PythonからはRunPodのAPI/SDKまたはSSHで操作できる。ただし毎回GPUの起動・停止とセットアップが要り、「プログラムから1回呼ぶ」より手間が大きい（意見）。
5. 画風（意見）：土台モデルを自由に選べるので、水彩・絵本風のSD1.5/SDXLモデルや LoRA を足せる。3候補の中で画風の自由度は最も高い。ライセンスは使うモデルごとに確認が必要。

## ライセンス共通事項（3候補に共通）
- Monster Labs の SD1.5版ControlNetのライセンス表記は **openrail++**（Hugging Faceの表記、PromptLayerも同じ）。出典：https://www.promptlayer.com/models/controlv1psd15qrcodemonster
- 商用利用の可否は検索結果からは確認できなかった。一般にOpenRAIL++は商用利用を認めつつ用途制限を付ける型だが、**このモデルの全文は未確認**。SDXL版のライセンスも **未確認**。
- 土台モデル（Realistic Vision など）や追加LoRAには別々のライセンスがあり、商用不可のものもある。使う前に1つずつ確認が要る。
- YouTube収益化での使用可否（生成物の権利）は、各サービスの規約も含め **未確認**。

## 比較表
| 項目 | A Replicate | B fal.ai | C RunPod自前 |
|---|---|---|---|
| 形 | 1回いくらのAPI | 1回いくらのAPI（単位はモデルごと） | GPU時間貸し |
| ControlNet(illusion) | あり（illusion-diffusion-hq 他） | あり（illusion-diffusion）、QR専用SDXLは未確認 | 自分で構築 |
| 効き具合の調整 | あり（conditioning scale 他） | 未確認 | 自由 |
| 1枚の目安 | 約$0.011〜0.020（約1.7〜3円） | 不明（表示$0は信頼できない） | 時間課金。2時間で約100〜210円 |
| 月額最低 | 未確認 | 未確認 | 未確認 |
| 商用 | 未確認（要本文） | 未確認 | モデル次第 |
| 日本・支払い | 未確認 | 未確認 | 未確認 |
| 水彩・絵本風 | 工夫が要る（意見） | SDXLなら期待（意見） | 最も自由（意見） |
| 手間 | 小 | 小 | 大 |

## 推奨（意見）
1. **第一候補：Replicate**。プログラムから1回呼ぶ形で、単価が小さく（試算で月数百〜千円程度）、illusion系モデルが揃っていて、conditioning scale も調整できそう。社則7章の「仕組みで回す」にも合う。
2. 画風が水彩にならない場合の**第二候補：RunPodの自前**。画風は自由だが、運用の手間が大きい。
3. fal.ai は単価と入力仕様が確認できず、現時点では比較できない。
4. **推奨は暫定**。商用条件と料金は本文未確認のため、本文確認が済むまで契約しないのが安全（意見）。

## CEOに決めてほしいこと
- 契約するサービス（まずReplicateを少額クレジットで試すかどうか）と、支払い方法。
- 月の予算の上限（目安：Replicateなら月1,000円以内、RunPodなら月2,000円以内で足りる見込みだが、試算にすぎない）。
- 本文確認のため、調査環境のネットワークで replicate.com / fal.ai / huggingface.co / runpod.io を許可してよいか。
