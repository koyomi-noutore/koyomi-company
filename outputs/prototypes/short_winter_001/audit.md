# 監査：ショートの季節の背景（winter_A）＋ thumb_guard（2026-11-24）

判定：**合格（軽微あり）・一発合格**（重大なし）

## 見たもの
- `git diff origin/main` ：season_theme.json・season_pick.py（新規）・text_shorts.py・chigau_shorts.py・ep_short.py・make_episode.py・thumb_same_check.py
- 試しの2本の 0:00・答えの jpg と frames.jpg を1枚にまとめた一覧画像（目で1回）、ffprobe
- WCAG のコントラスト比（監査で計算し直し）、季節の選び方・import・thumb_guard をプログラムで実行（書き込みなし）

## 【厳守】ショートの背景は季節の色
- 紺（34,48,74）の決め打ち：scripts/*.py に残りなし（grep。コメントの説明だけ）。
- 指定なし → winter_A（text_shorts の既定・season_pick(None)・ep_short で season の無い場合）。--season／problem.json の season／plan.json の season・theme で切り替わる。存在しない名前は止まる。
- 間違い探しのショート（ep_short）は長尺と同じ季節：第10回・第1回＝秋、第17・24〜26回＝winter_A。
- 今までの呼び方：chigau_shorts・mushimegane_shorts の import が通り、T.BG・T.CARD・T.INK・T.RED・T.ACCENT がそのまま読める。
- WCAG（winter_A）：ink/bg 13.0、ink/panel 14.7、accent/bg 7.0（見出しの下の説明文 46〜54px）、alert/panel 8.0、alert/hit 6.75、alert/bg 7.1、ink/hit 12.4 → 本文 7:1・大きな文字 4.5:1 の目安をすべて満たす。
- 幕（0:00・最後）：幕の下の背景は (90,91,95)。白 6.8、黄 4.5（白い札の上では 4.1）だが、黒い6pxのふち取りがあり一覧画像で読める。
- 目視：2本とも冬の白と薄い青灰で、見出し・札・吹き出し・答えの赤・丸が読める。
- 完成済みの動画：outputs の video.mp4 87本はどれも今日 13:00 以降の更新なし。text_018 の完成品（40.02秒）はそのまま、試作は prototypes に別に書き出し。

## 【厳守】サムネの左右（thumb_guard）
- thumbnail 直後・upload 前・retitle 前（差し替える1枚）・short-upload 前（元の長尺のサムネ）で呼ぶ。1枚でも不合格、またはサムネ0枚で止まる（終了コード1）。
- 全回で実行：第20〜26回は全部合格（差 2.6〜3.8、基準 4.0）。第1〜19回・第13回は止まる（差 6〜24）。第6回は thumb_B だけ合格・他は不合格で止まる＝「1枚でも」を確認。
- 第13・17〜19回などの在庫で止まるのは checklist のCEO判断（作り直さない）どおり。これらはすでにアップロード済み（upload.json あり）で、今の運用を止めない。

## 軽微（次の回から直す・記録）
1. 0:00 の画面は幕のせいで背景が灰色に見える（幕 0.62、shorts.md の 50〜60%程度を守った結果）。冬の色はわからない。**CEOへの確認事項**：このままでよいか／幕を薄くするか。
2. 幕の下の札・漢字が明るい背景だと透けて強く見える（ちがうのどーれだの牛、十字の札）。文字は読める。
3. 札の縁（edge）と背景の差が 2.1〜2.4（WCAG の図形の目安 3:1 未満）。札は白と薄い青灰の差 1.13 で、縁で見分ける形。
4. scripts/showa_quiz.py のショートは秋の色（クリーム）の決め打ちのまま。昭和なつかしクイズは試作だけで公開予定にないため軽微。使うときに season_pick を通す。
5. 環境変数 KOYOMI_THEME が --season より先に効く（text_shorts のコメントは「--season が最優先」）。説明と動きが少し違う。
6. 秋の accent/bg は 4.65（大きな文字の目安は満たすが本文の 7:1 には届かない）。秋のショートを作るときに見る。
