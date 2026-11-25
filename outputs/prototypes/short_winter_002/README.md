# ショートの最初の画面・最後の画面の見本 short_winter_002（2026-11-25 CEO指示）
short_winter_001 と同じ問題（文字の脳トレ：十字 cross／ちがうのどーれだ：easy＝季と李）。
- cross.mp4 37.3秒（cross_0000.jpg／cross_end.jpg）、easy.mp4 37.9秒（easy_0000.jpg／easy_end.jpg）。
- 最初の画面：暗い幕の上の文字を大きく。cross は 130・158・130px、easy は「ちがうの／どーれだ？／見つけて／みてね！」170・158・170・170px（001は 96・96・72px）。吹き出しなし。
- 最後の「左下をクリック」の場面：吹き出しなし（矢印と重ならない）。こよみ先生は左下のまま。
- 声は変えていない（文は同じ）。書き出しは1本ずつ（pgrep確認）。

## 差し戻し1回目（R-1）の直し
- 最初の画面の行分けを、言葉の途中で切らない規則に直した（scripts/text_shorts.py の _split_rows・intro_lines）。既存の problem.json 31件の結果は split_check.md。
- problem.json に "intro_lines" 欄を追加（作る人が行を書く）。easy は intro_lines を使う（行・大きさは前と同じ）。cross は大きさが 130・156・130px に（前は 130・158・130px）ので書き出し直した。
