"""台本のタイムライン。plan.json の timeline・lines・questions から、セリフの一覧と声に渡す文を作る。
- 時刻は動画の頭からの秒。
- 表情はこよみ先生が出るオープニング・うんちく・エンディングだけで使う（出題中・答え合わせ中・ルール説明は絵を出さない）。
- 声に渡す文は、字幕の文からかぎかっこを外し、plan.json の readings（読みの表）の語をひらがなにしたもの。
"""
import json
from pathlib import Path
from episode_plan import plan, questions

_T = plan()["timeline"]
TOTAL = _T["total"]
OPENING, RULE, UNCHIKU, ENDING = tuple(_T["opening"]), tuple(_T["rule"]), tuple(_T["unchiku"]), tuple(_T["ending"])
Q_START = {int(k): v for k, v in _T["q_start"].items()}
CARD, SOLVE, ANSWER = _T["card"], _T["solve"], _T["answer"]
HINT_AT, TEN_AT = _T.get("hint_at"), _T["ten_at"]      # 出題の頭からの秒。hint_at が null ならヒントなし（2026-11-07 CEO決定で標準はヒントなし）
ANS_FIRST, ANS_STEP = _T["ans_first"], _T["ans_step"]
QUESTIONS = {q: {"scene": Q["scene"], "level": Q["level"], "go": Q["go"], "hint": Q.get("hint"),
                 "answers": [d["line"] for d in Q["diffs"]], "answers_intro": Q.get("answers_intro", "答えです。")}
             for q, Q in questions().items()}
LEVEL_NUM = {"やさしい": "第{}問、やさしい問題。", "初級": "第{}問、初級。", "中級": "第{}問、中級。", "上級": "第{}問、上級。"}
_S = plan()["screens"]
TITLES = [tuple(x) for x in _S["ending_titles"]]
TITLE_NOTE = _S["ending_note"]
READINGS = [tuple(x) for x in plan()["readings"]]
VOICE_OVERRIDE = plan().get("voice_override", {})


def lines():
    """セリフの一覧：(id, 開始秒, 字幕の文, 表情, 枠の終わり秒)。"""
    Ls = plan()["lines"]
    L = []
    for part, base in (("opening", OPENING[0]), ("rule", RULE[0])):
        L += [(x["id"], base + x["at"], x["text"], x["face"], base + x["until"]) for x in Ls[part]]
    for q, Q in QUESTIONS.items():
        s = Q_START[q]
        # カードの読み上げは3秒を少し超えてもよい（「どうぞ」を出題開始の0.8秒後にしてある）
        L.append((f"q{q}_card", s, LEVEL_NUM[Q["level"]].format(q) + Q["scene"] + "です。", "normal", s + CARD + 0.8))
        L.append((f"q{q}_go", s + CARD + 0.8, Q["go"], "normal", s + CARD + 8))
        if HINT_AT is not None and Q["hint"]:
            L.append((f"q{q}_hint", s + CARD + HINT_AT, Q["hint"], "wink", s + CARD + HINT_AT + 7))
        # 出題中の声かけ（ヒントではない）：plan.json の timeline.solve_calls ＝ [[出題の頭からの秒, 文], ...]（2026-11-12 youtube-playbook 5章）
        for k, (at, text) in enumerate(_T.get("solve_calls", [])):
            L.append((f"q{q}_call{k}", s + CARD + at, text, "normal", s + CARD + at + 4))
        L.append((f"q{q}_ten", s + CARD + TEN_AT, "あと10秒です。", "normal", s + CARD + TEN_AT + 3))
        a = s + CARD + SOLVE
        L.append((f"q{q}_ans0", a, Q["answers_intro"], "smile", a + ANS_FIRST))
        for i, line in enumerate(Q["answers"]):
            L.append((f"q{q}_ans{i + 1}", a + ANS_FIRST + ANS_STEP * i, line, "smile", a + ANS_FIRST + ANS_STEP * (i + 1)))
    for part, base in (("unchiku", UNCHIKU[0]), ("ending", ENDING[0])):
        L += [(x["id"], base + x["at"], x["text"], x["face"], base + x["until"]) for x in Ls[part]]
    # 決まった時刻に入れるセリフ（例：中盤のコメントのお願い）。lines.extra の at・until は動画の頭からの秒
    L += [(x["id"], x["at"], x["text"], x.get("face", "smile"), x["until"]) for x in Ls.get("extra", [])]
    return sorted(L, key=lambda l: l[1])


def to_voice(lid, text):
    t = VOICE_OVERRIDE.get(lid, text).replace("「", "").replace("」", "")
    for a, b in READINGS:  # 上から順に置き換える（長い語を先に書く）
        t = t.replace(a, b)
    return t


VOICE_TEXT = {ln[0]: to_voice(ln[0], ln[2]) for ln in lines()}


def export(path):
    """編集の設計（タイムライン）を JSON で書き出す（リポジトリに残す素材）。"""
    data = {"total_sec": TOTAL, "fps": 30, "opening": OPENING, "rule": RULE, "unchiku": UNCHIKU, "ending": ENDING,
            "questions": {q: {"start": Q_START[q], "card": [Q_START[q], Q_START[q] + CARD],
                              "solve": [Q_START[q] + CARD, Q_START[q] + CARD + SOLVE],
                              "hint_at": None if HINT_AT is None else Q_START[q] + CARD + HINT_AT, "ten_sec_at": Q_START[q] + CARD + TEN_AT,
                              "answer": [Q_START[q] + CARD + SOLVE, Q_START[q] + CARD + SOLVE + ANSWER], **QUESTIONS[q]}
                          for q in QUESTIONS},
            "lines": [{"id": l[0], "start": l[1], "slot_end": l[4], "subtitle": l[2], "voice_text": VOICE_TEXT[l[0]], "face": l[3]}
                      for l in lines()]}
    Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
