"""台本のタイムライン。plan.json の timeline・lines・questions から、セリフの一覧と声に渡す文を作る。
- 時刻は動画の頭からの秒。
- 表情はこよみ先生が出るオープニング・うんちく・エンディングだけで使う（出題中・答え合わせ中・ルール説明は絵を出さない）。
- 声に渡す文は、字幕の文からかぎかっこを外し、plan.json の voice_override・readings（読みの表）で漢字を全部ひらがなにしたもの。
  漢字が1字でも残ったら声を作らずに止める（2026-11-15 最低品質1：読み間違いゼロ）。対照表は <回>/readings_check.md。
- 間のチェック（最低品質2）：1つのセリフは1〜2文、枠に対して1秒あたりの文字数が多すぎない（MAX_CPS）。
"""
import json, re
from pathlib import Path
from episode_plan import plan, questions

_T = plan()["timeline"]
TOTAL = _T["total"]
OPENING, RULE, UNCHIKU, ENDING = tuple(_T["opening"]), tuple(_T["rule"]), tuple(_T["unchiku"]), tuple(_T["ending"])
Q_START = {int(k): v for k, v in _T["q_start"].items()}
CARD, SOLVE, ANSWER = _T["card"], _T["solve"], _T["answer"]
GO_DELAY = _T.get("go_delay", 0.8)   # 札の読み上げのあと「どうぞ」までの秒（出題の頭から）。間を0.4秒以上とるため 1.3 にする（2026-11-18）
HINT_AT, TEN_AT = _T.get("hint_at"), _T["ten_at"]      # 出題の頭からの秒。hint_at が null ならヒントなし（2026-11-07 CEO決定で標準はヒントなし）
ANS_FIRST, ANS_STEP = _T["ans_first"], _T["ans_step"]
CTA = tuple(_T["cta"]) if _T.get("cta") else None     # 登録のお願いの区切り（2026-11-14 CEO指示：1問目の答え合わせの直後）
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
        L.append((f"q{q}_card", s, LEVEL_NUM[Q["level"]].format(q) + Q["scene"] + "です。", "normal", s + CARD + GO_DELAY))
        L.append((f"q{q}_go", s + CARD + GO_DELAY, Q["go"], "normal", s + CARD + 8))
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
    for part, base in (("unchiku", UNCHIKU[0]), ("ending", ENDING[0])) + ((("cta", CTA[0]),) if CTA else ()):
        L += [(x["id"], base + x["at"], x["text"], x["face"], base + x["until"]) for x in Ls[part]]
    # 決まった時刻に入れるセリフ（例：中盤のコメントのお願い）。lines.extra の at・until は動画の頭からの秒
    L += [(x["id"], x["at"], x["text"], x.get("face", "smile"), x["until"]) for x in Ls.get("extra", [])]
    return sorted(L, key=lambda l: l[1])


# 数字＋助数詞の読みを固定する（concept.md「第10回からの改善」2026-11-18 夜：第4問＝だいよんもん。4＝よん、7＝なな、9＝きゅう）
_D = {0: "", 1: "いち", 2: "に", 3: "さん", 4: "よん", 5: "ご", 6: "ろく", 7: "なな", 8: "はち", 9: "きゅう"}


def num_kana(n):
    """0〜999 の数をひらがなに（よん・なな・きゅうに固定。百の位の音便も入れる）。"""
    if n == 0:
        return "ぜろ"
    h, r = divmod(n, 100)
    t, o = divmod(r, 10)
    hs = {0: "", 1: "ひゃく", 3: "さんびゃく", 6: "ろっぴゃく", 8: "はっぴゃく"}.get(h, _D[h] + "ひゃく")
    ts = "" if t == 0 else ("じゅう" if t == 1 else _D[t] + "じゅう")
    return hs + ts + _D[o]


_TSU = {1: "ひとつ", 2: "ふたつ", 3: "みっつ", 4: "よっつ", 5: "いつつ", 6: "むっつ", 7: "ななつ", 8: "やっつ", 9: "ここのつ", 10: "とお"}
_COUNTERS = [   # (正規表現, 読みを作る関数)。長い物から順に置き換える
    (r"第(\d+)問", lambda n: "だい" + num_kana(n) + "もん"),
    (r"(\d+)問目", lambda n: num_kana(n) + "もんめ"),
    (r"(\d+)問", lambda n: num_kana(n) + "もん"),
    (r"(\d+)時半", lambda n: {4: "よじ", 7: "しちじ", 9: "くじ"}.get(n, num_kana(n) + "じ") + "はん"),
    (r"(\d+)秒", lambda n: num_kana(n) + "びょう"),
    (r"(\d+)分", lambda n: {1: "いっぷん", 3: "さんぷん", 4: "よんぷん", 6: "ろっぷん", 8: "はっぷん", 10: "じゅっぷん"}.get(n, num_kana(n) + "ふん")),
    (r"(\d+)個", lambda n: {1: "いっこ", 6: "ろっこ", 8: "はっこ", 10: "じゅっこ"}.get(n, num_kana(n) + "こ")),
    (r"(\d+)枚", lambda n: num_kana(n) + "まい"),
    (r"(\d+)本", lambda n: {1: "いっぽん", 3: "さんぼん", 6: "ろっぽん", 8: "はっぽん", 10: "じゅっぽん"}.get(n, num_kana(n) + "ほん")),
    (r"(\d+)代", lambda n: num_kana(n) + "だい"),
    (r"(\d+)つ", lambda n: _TSU.get(n, num_kana(n))),
    (r"(\d+)", lambda n: num_kana(n)),
]


def fix_numbers(t):
    import re as _re
    for pat, f in _COUNTERS:
        t = _re.sub(pat, lambda m: f(int(m.group(1))), t)
    return t


def to_voice(lid, text):
    t = VOICE_OVERRIDE.get(lid, text).replace("「", "").replace("」", "")
    t = fix_numbers(t)     # 数字＋助数詞の読みを先に固定する（読みの表より優先）
    for a, b in READINGS:  # 上から順に置き換える（長い語を先に書く）
        t = t.replace(a, b)
    return t


VOICE_TEXT = {ln[0]: to_voice(ln[0], ln[2]) for ln in lines()}

KANJI = re.compile(r"[\u3400-\u9fff々〆ヶ]")
SENT = re.compile(r"[^。！？!?]+[。！？!?]*")
MAX_CPS = 5.0          # 声に渡す文（ひらがな）の文字数 ÷ 枠の秒。声の速さは約5.5字/秒（第7回の実測）なので、5.0を超えると枠いっぱいで詰まって聞こえる
MAX_CPS_CARD = 6.2     # 問題の札（第○問、○級。場面です。）だけは決まった短い文で、どうぞの手前まで使ってよい


def sentences(t):
    return [x.strip() for x in SENT.findall(t) if x.strip(" 、。！？")]


def voice_problems():
    """読み（漢字の残り）と間（文の数・詰まり）の問題を一覧にする。"""
    P = []
    for lid, t0, text, face, t_end in lines():
        vt = VOICE_TEXT[lid]
        k = KANJI.findall(vt)
        if k:
            P.append(f"{lid}：声に渡す文に漢字が残っている {''.join(k)}（readings か voice_override に読みを足す）")
        n = len(sentences(vt))
        if n > 2:
            P.append(f"{lid}：1つのセリフに{n}文（1〜2文まで）")
        chars = len(re.sub(r"[\s、。！？!?「」・…ー]", "", vt))
        slot = t_end - t0
        lim = MAX_CPS_CARD if lid.endswith("_card") else MAX_CPS
        if slot > 0 and chars / slot > lim:
            P.append(f"{lid}：枠 {slot:.1f}秒に{chars}字（{chars / slot:.1f}字/秒、上限{lim}）。枠を延ばすか文を減らす")
    return P


def readings_check(path):
    """字幕の文と声に渡す文の対照表（監査で読みを全部確かめる）。問題があれば先頭に書く。"""
    P = voice_problems()
    out = ["# 読みの対照表（字幕 → 声に渡す文）", "", "監査は全行の読みを確かめる。声に渡す文に漢字は残さない。", ""]
    out += ["## 問題", ""] + [f"- {p}" for p in P] + [""] if P else ["問題：なし（漢字の残り・文の数・詰まり）", ""]
    out += ["| id | 秒 | 字幕 | 声に渡す文 |", "|---|---|---|---|"]
    for lid, t0, text, face, t_end in lines():
        out.append(f"| {lid} | {t0:.1f} | {text} | {VOICE_TEXT[lid]} |")
    Path(path).write_text("\n".join(out) + "\n", encoding="utf-8")
    return P


def export(path):
    """編集の設計（タイムライン）を JSON で書き出す（リポジトリに残す素材）。"""
    data = {"total_sec": TOTAL, "fps": 30, "opening": OPENING, "rule": RULE, "unchiku": UNCHIKU, "ending": ENDING, "cta": CTA,
            "questions": {q: {"start": Q_START[q], "card": [Q_START[q], Q_START[q] + CARD],
                              "solve": [Q_START[q] + CARD, Q_START[q] + CARD + SOLVE],
                              "hint_at": None if HINT_AT is None else Q_START[q] + CARD + HINT_AT, "ten_sec_at": Q_START[q] + CARD + TEN_AT,
                              "answer": [Q_START[q] + CARD + SOLVE, Q_START[q] + CARD + SOLVE + ANSWER], **QUESTIONS[q]}
                          for q in QUESTIONS},
            "lines": [{"id": l[0], "start": l[1], "slot_end": l[4], "subtitle": l[2], "voice_text": VOICE_TEXT[l[0]], "face": l[3]}
                      for l in lines()]}
    Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
