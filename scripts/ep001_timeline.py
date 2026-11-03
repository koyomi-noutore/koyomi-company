"""第1回（001）の台本タイムライン。outputs/2026-11-03_001/plan.md 4章の時刻・セリフ・表情をそのまま写したもの。
- 時刻は動画の頭からの秒。
- 6:04 のセリフは事業部長の連絡（2026-11-03、調査部の確認結果）で変更した版。
- 第5問の答えの③は、灯籠1基が画面幅3%未満だったため「2基とも消える」に変えたので、セリフも合わせて変えた（README参照）。
- 答えのセリフは scripts/ep001_diffs.json の line から取る（答えの位置と同じ場所で管理する）。
"""
import json
from pathlib import Path

DIFFS = {int(k): v for k, v in json.loads(Path(__file__).with_name("ep001_diffs.json").read_text(encoding="utf-8")).items()}

TOTAL = 615.0
OPENING, RULE = (0.0, 15.0), (15.0, 25.0)
Q_START = {1: 25.0, 2: 133.0, 3: 241.0, 4: 379.0, 5: 487.0}
UNCHIKU = (349.0, 379.0)
ENDING = (595.0, 615.0)
CARD, SOLVE, ANSWER = 3.0, 90.0, 15.0
HINT_AT, TEN_AT = 45.0, 80.0  # 出題の頭からの秒

QUESTIONS = {
    1: {"scene": "縁側", "level": "初級", "card_face": "normal", "go": "さあ、どうぞ。",
        "hint": "ヒントです。お茶のお盆のあたりを、よく見てくださいね。"},
    2: {"scene": "商店街", "level": "初級", "card_face": "normal", "go": "さあ、どうぞ。",
        "hint": "ヒントです。お店の前の、わんちゃんを見てください。"},
    3: {"scene": "山道", "level": "中級", "card_face": "normal", "go": "少しむずかしくなります。どうぞ。",
        "hint": "ヒントです。道ばたの、石のあたりを見てください。"},
    4: {"scene": "台所", "level": "中級", "card_face": "normal", "go": "後半です。どうぞ。",
        "hint": "ヒントです。かまどの上を、よく見てくださいね。"},
    5: {"scene": "神社", "level": "上級", "card_face": "surprise", "go": "最後の問題です。じっくりどうぞ。",
        "hint": "ヒントです。奥の、いちょうの木のそばを見てください。"},
}
LEVEL_NUM = {"初級": "第{}問、初級。", "中級": "第{}問、中級。", "上級": "第{}問、上級。"}


def lines():
    """セリフの一覧：(id, 開始秒, セリフ, 表情, 枠の終わり秒)。枠を超える音声は ep001_voice.py が検出する。"""
    L = [
        ("op", 0.0, "みなさん、こんにちは。こよみ先生です。秋がふかまって、柿のおいしい季節になりましたね。今日は、秋の間違い探しを5問、いっしょに楽しみましょう。", "smile", 15.0),
        ("rule", 15.0, "左と右の絵をくらべます。90秒で、右の絵の違いを3つ探してください。", "normal", 25.0),
    ]
    for q, Q in QUESTIONS.items():
        s = Q_START[q]
        L.append((f"q{q}_card", s, LEVEL_NUM[Q["level"]].format(q) + Q["scene"] + "です。", Q["card_face"], s + CARD + 0.8))
        # カードの読み上げ（約3.2〜3.5秒）が3秒の枠を少し超えるので、「どうぞ」は出題開始の0.8秒後に言う
        L.append((f"q{q}_go", s + CARD + 0.8, Q["go"], "normal", s + CARD + 8))
        L.append((f"q{q}_hint", s + CARD + HINT_AT, Q["hint"], "wink", s + CARD + HINT_AT + 7))
        L.append((f"q{q}_ten", s + CARD + TEN_AT, "あと10秒です。", "normal", s + CARD + TEN_AT + 3))
        a = s + CARD + SOLVE
        L.append((f"q{q}_ans0", a, "答えです。", "smile", a + 1.6))
        # 答えの3つ：1.6秒から、4.3秒ずつ（15秒の枠に収める）
        for i, d in enumerate(DIFFS[q]):
            face = "surprise" if (q == 5 and i == 2) else "smile"
            L.append((f"q{q}_ans{i + 1}", a + 1.6 + 4.3 * i, d["line"], face, a + 1.6 + 4.3 * (i + 1)))
    u = UNCHIKU[0]
    L += [
        ("u1", u, "ここで、ひと休み。秋の小話です。", "smile", u + 4),
        ("u2", u + 4, "「もみじ」は、葉の色が変わることをあらわす、むかしのことば「もみつ」から生まれたといわれます。", "normal", u + 15),
        ("u3", u + 15, "万葉集のころは、黄色い葉と書いて「もみち」と読むのが、ふつうだったそうです。", "surprise", u + 23),
        ("u4", u + 23, "「紅葉」と書くことがふえたのは、平安時代からだそうです。", "smile", u + 30),
        ("e1", 595.0, "これで5問、おしまいです。おつかれさまでした。", "yay", 599.5),
        # e1 が4.35秒で4秒の枠を少し超えるので、e2・e3 を0.5秒ずつ後ろへ（20秒の枠には収まる）
        ("e2", 599.5, "15個の違い、いくつ見つかりましたか。画面で、今日の称号を見てくださいね。", "smile", 606.5),
        ("e3", 606.5, "次回も秋の絵で5問です。チャンネル登録をして、また来てください。", "wink", 615.0),
    ]
    return L


TITLES = [("15個", "秋の名探偵"), ("11〜14個", "もみじ名人"), ("6〜10個", "実りの秋さん"), ("0〜5個", "どんぐりさん")]
TITLE_NOTE = "どんぐりさんは、これから、ぐんぐん育ちます"
