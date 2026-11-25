"""ショートの「最後の流れ」の共通の部品（2026-11-23 CEO決定。knowledge/shorts.md「すべてのショートの最後の流れ」）。

答え合わせのあと、
  ① コメントの呼びかけ（声＋大きな文字・約2秒）
  ② ほかの動画への呼びかけ（「左下をクリック」＋左下を指す矢印）
の順にする。間違い探し・文字の脳トレ・ちがうのどれ？ すべて共通。

使い方（呼ぶ側が、自分の「声を作る」「幕をかける」「こよみ先生を置く」「矢印を描く」を渡す）：
    from short_outro import build_outro
    frames, length = build_outro(base, say, veil, speaker, arrow, comment="find" or "text")
  base     ：答えが出たままの最後の問題の絵
  say      ：say(key, (字幕, 声に渡す文), 秒) -> 声の長さ。呼ぶ側が「今の時刻＋秒」に声を置く
  veil     ：veil(絵, [(文字, 大きさ, 色), ...]) -> 暗い幕をかけた絵
  speaker  ：speaker(絵, 表情, 字幕) -> 左下にこよみ先生と吹き出しを置いた絵
  arrow    ：arrow(絵, 秒) -> 矢印を描いた絵
  comment  ："text"＝「わかったら、コメントで…」（文字の脳トレ・ちがうのどれ？）／"find"＝「いくつ見つかったか、コメントで…」（間違い探し）
戻り値：frames＝[(絵, 秒)]（矢印は0.1秒ごと）、length＝全体の秒数。
text_shorts.py・ep_short.py の動きは変えていない。呼べる形にしただけ（今回の作り直しは「ちがうのどれ？」3本だけ）。
"""
COMMENT = {
    "text": {"line": ("わかったら、コメントで教えてくださいね。", "わかったら、コメントで、おしえてくださいね。"),
             "veil": [("わかったら", 110), ("コメントで", 120), ("教えてね", 120)]},
    "find": {"line": ("いくつ見つかったか、コメントで教えてくださいね。", "いくつみつかったか、コメントで、おしえてくださいね。"),
             "veil": [("いくつ 見つかったか", 100), ("コメントで", 120), ("教えてね", 120)]},
}
CTA = ("左下をクリックして、ほかの脳トレにも挑戦してくださいね。", "ひだりしたをクリックして、ほかののうトレにも、ちょうせんしてくださいね。")
WHITE, YELLOW = (255, 255, 255), (255, 205, 40)
CTA_VEIL = [("ほかの脳トレにも", 100, WHITE), ("挑戦！", 110, WHITE), ("左下をクリック", 120, YELLOW)]
COMMENT_MIN, CTA_MIN = 2.0, 5.0


def build_outro(base, say, veil, speaker, arrow, comment="text", cta=None, cta_veil=None):
    """comment は "text"／"find" のほか、{"line": (字幕, 声), "veil": [(文字, 大きさ), ...]} の辞書でもよい。cta・cta_veil で②の言い方も変えられる。
    ②（左下をクリック＋矢印）は吹き出しを出さない（矢印と重なるため。2026-11-25 CEO）。こよみ先生は今の位置のまま。"""
    c = COMMENT[comment] if isinstance(comment, str) else comment
    cta = cta or CTA
    frames, off = [], 0.0
    # ① コメントの呼びかけ（約2秒）
    d = say("comment", c["line"], off)
    n = max(COMMENT_MIN, d + 0.3)
    lines = [(s, sz, YELLOW if i == 2 else WHITE) for i, (s, sz) in enumerate(c["veil"])]
    frames.append((speaker(veil(base, lines), "smile", c["line"][0]), n)); off += n
    # ② 左下をクリック＋矢印
    d = say("cta", cta, off)
    end = max(CTA_MIN, d + 1.0)
    b2 = speaker(veil(base, cta_veil or CTA_VEIL), "wink", None)
    for i in range(int(end * 10)):
        frames.append((arrow(b2.copy(), i / 10), 0.1))
    return frames, off + end
