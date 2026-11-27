# 名画プロジェクト（試作ラボ）

こよみ先生のリポジトリを一時的に借りた、名画ショートの試作置き場。**こよみ先生の社則・定例・NGリスト・knowledge/ とは別扱い。** 名画専用のリポジトリは、プロジェクトが本格的に動き出してから作る。

- `docs/handoff_2026-11-27.md`：引き継ぎメモ（方針・レビュー・次にやること）。**最初に読むこと。**
- `scripts/`：前の環境で作った試作スクリプト（コードだけで作るもの）。
  - `animate_painting.py`：最初の動きの試作（筆の流れに沿って絵の具を揺らす）。
  - `proto.py`：第1弾（フック→飛び込み→切り替え→絵の中）。共通部品（揺らす、ズーム、渦、タッチがほどける、額縁、白／黒、まばたき、字幕、Open JTalkの声、効果音）。
  - `hooks2.py`：フック第2版（絵があふれる、波が飛び出す、いきなり落ちる＝H4）。`proto.py` を読み込む。
  - `vertex.py`：Vertex AI（Gemini 3 Pro Image・Veo 3.1 Fast 720p）の共通部品。費用を `cost_log.md` に自動で書き、上限3,000円を超える前に止める。鍵は環境変数 `VERTEX_SA_KEY_B64` からメモリ上でだけ読む。
  - `world_starry.py`：試作W1（星月夜：H4のフック→白→目を開く→ゴッホの画風の一人称の世界）。`img`→`vid`→`build` の順に実行。作ったものは作り直さない。
  - 必要なもの：Python（numpy, opencv-python, pillow, pyopenjtalk）、ffmpeg、Noto Serif CJK フォント。
  - 実行時、`ROOT`（scripts の1つ上＝labs/meiga）の `src/` から絵を読み、`out/` と `work/` に書き出す。
- `cost_log.md`：Vertex AIの費用記録（見込み額。正式な額はGoogle Cloudの請求で確認）。
- `out/world/`：一人称の世界の試作（レビュー用にコミットする）。`work/` は途中のファイル（コミットしない）。
- `src/`：著作権の切れた名画の画像（GitHub上の小さめのもの。本番は高画質に替える）。
- 返答はすべて日本語で行うこと（Ichiroの希望）。
- `knowledge/shorts_theory.md`：ショートの一般則（日英の資料から）。台本と編集の土台。
- `knowledge/yomi.tsv` と `scripts/yomi.py`：ナレーションの読み制御。音声に渡す前に必ず通し、新しい誤読は yomi.tsv に足す。
- `docs/scripts_v3.md`：最新の台本（ゴッホ・北斎・ムンク）とレビューの記録。
