"""在庫の間違い探し2回分（5問×2）を、1本の長尺（全10問・約20分）にまとめる（2026-11-26 CEO決定）。画像APIは使わない。

使い方:
  python3 scripts/combine_episodes.py <新しいフォルダ> <元の回のフォルダA> <元の回のフォルダB>
      [--topic-a 題材A] [--topic-b 題材B] [--thumb A1|B1|...]
  例: python3 scripts/combine_episodes.py outputs/2026-11-26_w10_001 outputs/2026-11-23_022 outputs/2026-11-23_023 \
        --topic-a きのこ狩り --topic-b 芋煮会 --thumb A1

やること（元の回のフォルダは読むだけ。書き換えない）:
  1. 2回分の絵（qN_a.png・qN_b.png）・answers.json・plan.json の問題を読む。
  2. やさしい順に並べ直す（やさしい2・初級4・中級2・上級2 → 1〜10問目）。A・B が交互になる（A1 B1 A2 B2 …）。
  3. 新しいフォルダに、10問の plan.json・answers.json・絵・description.md を作る。
     新しく作る：冒頭の予告・各問の声かけ・うんちく（秋の日はつるべ落とし）・エンディング（第34回と同じ汎用の案内）。
     答えの文は元の回の文（番号の言い方は「N問目」）。季節は元の回の season。
  3b. つなぐ前に、check が止める項目（同じ物・同じ変化／上級の大きさ）を一覧にして出す（--preflight なら一覧だけ。何も作らない）。
      止める項目があるときは、scripts/swap_diff.py で違いを差し替えてから進める（2026-11-26 CEO：重なる2問のうち1問だけ、その場面の別の物の違いに）。
  4. そのあとは make_episode.py <新しいフォルダ> voice → audio → video → thumbnail → check（または all。絵は作り直さない）。
うんちくの題材（TALK）は秋用。別の季節の組を作るときは TALK を差し替える（knowledge/episode-index.md で重なりを確かめる）。
"""
import json
import re
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

LEVEL_ORDER = ["やさしい", "初級", "中級", "上級"]
CARD, SOLVE, ANSWER = 3.0, 90.0, 15.0
OPENING_END = 7.0          # 5秒以内に予告（op 0〜3.9秒・op2 3.9〜7.0秒）、10秒以内に1問目が始まる
UNCHIKU_LEN = 32.0
ENDING_LEN = 37.0
MID_AFTER = 5              # うんちくを入れる位置（5問目のあと）
SEASON_KANA = {"春": "はる", "夏": "なつ", "秋": "あき", "冬": "ふゆ"}

# transcribe_check で読み違いが続いた文の言い換え（声に渡す文だけ。字幕は元の文のまま）
VOICE_PATCH = {"ひしゃくの、むきが、はんたいに、なりました。": "ひしゃくの、むきが、ぎゃくに、なりました。"}

# 各問の案内（2問目以降。字幕の文, 声に渡す文）。{n} は fix_numbers が「N問目」を読みに直す
GO_VARIANTS = [
    ("では、{n}問目。どうぞ。", "では、{n}問目。どうぞ。"),
    ("つぎは、{n}問目です。どうぞ。", "つぎは、{n}問目です。どうぞ。"),
    ("{n}問目も、3つ探してください。どうぞ。", "{n}問目も、みっつ、さがしてください。どうぞ。"),
    ("さあ、{n}問目。どうぞ。", "さあ、{n}問目。どうぞ。"),
    ("ゆっくり、{n}問目。どうぞ。", "ゆっくり、{n}問目。どうぞ。"),
    ("もう少しです。{n}問目、どうぞ。", "もうすこしです。{n}問目、どうぞ。"),
]

# うんちく（秋・1つ）。過去の回と同じ話にしない（knowledge/episode-index.md）。texts＝[文字, x, y, 大きさ, 色, ふち]
TALK = {
    "header": "こよみ先生の 秋の小話",
    "lines": [
        ("u1", 0.0, 7.0, "smile", "ここでひと休み。こよみ先生の季節のお話です。", "ここでひとやすみ。こよみせんせいの、きせつのおはなしです。"),
        ("u2", 7.0, 15.0, "think", "「秋の日はつるべ落とし」って、聞いたことはありますか？",
         "あきのひは、つるべおとしって、きいたことはありますか？"),
        ("u3", 15.0, 25.0, "surprise", "つるべとは、井戸の水をくむ桶のこと。すとんと落ちるように、日が暮れるという意味です。",
         "つるべとは、いどの、みずをくむ、おけのこと。すとんとおちるように、ひがくれるという、いみです。"),
        ("u4", 25.0, 32.0, "wink", "秋は暗くなるのが早いので、足もとに気をつけましょうね。",
         "あきは、くらくなるのが、はやいので、あしもとに、きをつけましょうね。"),
    ],
    "slides": [
        {"until": 7, "texts": [["ひと休み", 960, 330, 130, [180, 70, 40], 6], ["こよみ先生の 季節のお話", 960, 520, 80, [110, 84, 60], 0]]},
        {"until": 15, "texts": [["「秋の日は つるべ落とし」", 960, 330, 100, [180, 70, 40], 6], ["って 聞いたことは ありますか？", 960, 520, 80, [59, 47, 37], 0]]},
        {"until": 25, "texts": [["つるべは 井戸の 水くみの桶", 960, 330, 100, [180, 70, 40], 6],
                                ["すとんと 落ちるように 日が暮れる", 960, 520, 88, [59, 47, 37], 0]]},
        {"until": 40, "texts": [["秋は 暗くなるのが 早い", 960, 330, 110, [180, 70, 40], 6], ["足もとに 気をつけて", 960, 520, 100, [59, 47, 37], 0]]},
    ],
}

# エンディング：登録のお願いは最後だけ（理由つき）。e3・e4 は第34回と同じ文（汎用の案内）
ENDING = [
    ("e1", 0.0, 3.6, "yay", "これで10問、おしまいです。", None),
    ("e2", 3.6, 10.2, "smile", "30個の違い、いくつ見つかりましたか。今日の称号です。",
     "さんじゅっこの、ちがい、いくつみつかりましたか。きょうのしょーごーです。"),
    ("e3", 10.2, 21.0, "smile", "チャンネル登録とベルで、毎朝8時半に問題が届きます。毎日の頭の体操にどうぞ。",
     "チャンネルとうろくとベルで、まいあさはちじはんに、もんだいがとどきます。まいにちの、あたまのたいそうにどうぞ。"),
    ("e4", 21.0, 36.0, "wink", "ほかにも、いろいろな間違い探しがあります。もっと難しい問題に挑戦したい方は、画面の動画をクリックしてくださいね。",
     "ほかにも、いろいろな、まちがいさがしがあります。もっとむずかしいもんだいに、ちょうせんしたいかたは、がめんのどうがを、クリックしてくださいね。"),
]
ENDING_TITLES = [["30個", "秋の達人"], ["22〜29個", "秋の名探偵"], ["11〜21個", "どんぐり拾い"], ["0〜10個", "落ち葉の旅人"]]
ENDING_NOTE = "落ち葉の旅人も、毎日ためせば 名人です"


def load(d):
    d = Path(d)
    return {"dir": d, "plan": json.loads((d / "plan.json").read_text(encoding="utf-8")),
            "ans": json.loads((d / "answers.json").read_text(encoding="utf-8"))}


def order_questions(srcs):
    """やさしい順。同じ難易度の中は A・B を交互に（A1 B1 A2 B2 …）。"""
    out = []
    for lv in LEVEL_ORDER:
        per = [[(k, s, Q) for Q in s["plan"]["questions"] if Q["level"] == lv] for k, s in zip("AB", srcs)]
        n = max(len(p) for p in per)
        for i in range(n):
            for p in per:
                if i < len(p):
                    out.append(p[i])
    return out


def stop_list(seq):
    """つなぐ前の確認：check が「止める」項目（同じ物・同じ変化のくり返し／上級の大きさ）を、どの問のどの違いか分かる形で一覧にする。
    seq＝order_questions の結果。くり返しは後ろの問の違いを差し替える候補にする（ep_check の判定と同じ：_object_of・表記ゆれ表）。"""
    import ep_check as C
    out, seen_label, seen_obj = [], {}, {}
    for newq, (tag, s_, Q) in enumerate(seq, 1):
        A = next(x for x in s_["ans"]["questions"] if x["q"] == Q["q"])
        size = {a["id"]: a["object_screen_width_pct"] for a in A["answers"]}
        src = f"{tag}={s_['dir'].name}の{Q['q']}問目"
        for d in Q["diffs"]:
            lab = str(d.get("label", "")).strip()
            obj = C._object_of(lab)
            here = f"第{newq}問 違い{d['id']}「{lab}」（{src}・{Q['level']}・{size.get(d['id'])}%）"
            if lab in seen_label:
                out.append(f"差し替え候補 {here}：同じ変化が{seen_label[lab]}にもある")
            elif obj and obj in seen_obj:
                out.append(f"差し替え候補 {here}：同じ物「{obj}」が{seen_obj[obj]}にもある")
            seen_label.setdefault(lab, f"第{newq}問 違い{d['id']}")
            if obj:
                seen_obj.setdefault(obj, f"第{newq}問 違い{d['id']}「{lab}」")
            if Q["level"] == "上級" and size.get(d["id"], 0) > C.UPPER_MAX:
                out.append(f"差し替え候補 {here}：上級なのに{C.UPPER_MAX}%を超える（3.0〜{C.UPPER_MAX}%の小さい物に）")
    return out


def fmt(t):
    t = int(t)
    return f"{t // 60}:{t % 60:02d}"


def main(argv):
    opts = {}
    pos = []
    i = 0
    while i < len(argv):
        if argv[i].startswith("--"):
            if argv[i] == "--preflight":      # 何も作らず、止める項目の一覧だけ出す
                opts["preflight"] = "1"
                i += 1
                continue
            opts[argv[i][2:]] = argv[i + 1]
            i += 2
        else:
            pos.append(argv[i])
            i += 1
    new, da, db = (Path(x).resolve() for x in pos)
    srcs = [load(da), load(db)]
    pre_only = "preflight" in opts
    season = srcs[0]["plan"]["season"]
    if srcs[1]["plan"]["season"] != season:
        raise SystemExit("2回の季節（plan.json の season）がちがいます。同じ季節の組だけつなぐ")
    seq = order_questions(srcs)
    n = len(seq)
    if n != 10:
        raise SystemExit(f"問題が{n}問です（全10問の組だけ）")
    import os
    os.environ.setdefault("KOYOMI_EPISODE_DIR", str(srcs[0]["dir"]))     # ep_check を読み込むために要る（中身は使わない）
    stops = stop_list(seq)
    print(f"つなぐ前の確認：check が止める項目 {len(stops)}件" + ("" if not stops else "（差し替えが要る。scripts/swap_diff.py）"))
    for x in stops:
        print("  × " + x)
    if pre_only:
        return
    ta = opts.get("topic-a") or srcs[0]["plan"]["topics"][0]
    tb = opts.get("topic-b") or srcs[1]["plan"]["topics"][0]
    if (new / "swaps.json").exists() and "force" not in opts:
        raise SystemExit(f"{new} には差し替え（swaps.json）がある。つなぎ直すと差し替えが消える。やり直すときは --force 1")
    new.mkdir(parents=True, exist_ok=True)

    # ---- 絵・答え・問題 ----
    ans_meta = {k: srcs[0]["ans"][k] for k in ("screen", "note")}
    questions, answers, order_note, over = [], [], [], {}
    for newq, (tag, s, Q) in enumerate(seq, 1):
        oq = Q["q"]
        for side in "ab":
            shutil.copy2(s["dir"] / f"q{oq}_{side}.png", new / f"q{newq}_{side}.png")
        A = next(x for x in s["ans"]["questions"] if x["q"] == oq)
        A = dict(A, q=newq)
        answers.append(A)
        go, go_v = (("右の絵の違いを、3つ探してください。どうぞ。", "みぎのえのちがいを、みっつさがしてください。どうぞ。") if newq == 1
                    else GO_VARIANTS[(newq - 2) % len(GO_VARIANTS)])
        keep = {k: v for k, v in Q.items() if k in ("scene", "level", "answers_intro", "hint_diff", "content_box", "diffs")}
        questions.append({"q": newq, **keep, "go": go.format(n=newq), "_go_voice": go_v.format(n=newq),
                          "src": {"episode": s["dir"].name, "q": oq, "tag": tag}})
        order_note.append(f"{newq}問目＝{tag}（{s['dir'].name}）の元の{oq}問目 {Q['level']}「{Q['scene']}」")
    (new / "answers.json").write_text(json.dumps({**ans_meta, "questions": answers}, ensure_ascii=False, indent=1), encoding="utf-8")

    # ---- 声・読み ----
    vo, readings = {}, []
    seen = set()
    for s in srcs:
        for r in s["plan"]["readings"]:
            if tuple(r) not in seen:
                seen.add(tuple(r))
                readings.append(list(r))
    readings.sort(key=lambda r: -len(r[0]))     # 長い語を先に置き換える
    for newq, (tag, s, Q) in enumerate(seq, 1):
        oq = Q["q"]
        ov = s["plan"]["voice_override"]
        card = ov.get(f"q{oq}_card")
        m_ = re.match(r"(?:\d+問目|[ぁ-ん]+もんめ)、", card or "")     # 元は「1問目、…」か「いちもんめ、…」。番号だけ新しい番号の「N問目」に
        if not m_:
            raise SystemExit(f"{s['dir'].name} の q{oq}_card の読みが想定外：{card!r}")
        vo[f"q{newq}_card"] = f"{newq}問目、" + card[m_.end():]
        vo[f"q{newq}_go"] = questions[newq - 1].pop("_go_voice")
        for k in range(1, 4):                                # 答えの文は元の回のまま（読みの上書きも引き継ぐ）
            if f"q{oq}_ans{k}" in ov:
                vo[f"q{newq}_ans{k}"] = VOICE_PATCH.get(ov[f"q{oq}_ans{k}"], ov[f"q{oq}_ans{k}"])

    season_kana = SEASON_KANA[season]
    lines = {
        "opening": [
            {"id": "op", "at": 0.0, "text": f"{season}の間違い探し、全10問。", "face": "smile", "until": 3.9},
            {"id": "op2", "at": 3.9, "text": "だんだん、難しくなります。", "face": "wink", "until": OPENING_END},
        ],
        "rule": [],
        "unchiku": [{"id": i_, "at": a, "text": t, "face": f, "until": u} for i_, a, u, f, t, _ in TALK["lines"]],
        "ending": [{"id": i_, "at": a, "text": t, "face": f, "until": u} for i_, a, u, f, t, _ in ENDING],
    }
    vo["op"] = f"{season_kana}の、まちがいさがし、10問。"
    vo["op2"] = "だんだん、むずかしくなります。"
    for i_, a, u, f, t, v in TALK["lines"]:
        vo[i_] = v
    for i_, a, u, f, t, v in ENDING:
        if v:
            vo[i_] = v

    # ---- 時刻 ----
    q_start = {}
    t = OPENING_END
    for q in range(1, n + 1):
        if q == MID_AFTER + 1:
            unchiku = [t, t + UNCHIKU_LEN]
            t += UNCHIKU_LEN
        q_start[str(q)] = t
        t += CARD + SOLVE + ANSWER
    ending = [t, t + ENDING_LEN]
    total = ending[1]
    mid_q = q_start[str(MID_AFTER)] + CARD + 12     # 5問目の出題の12秒後に、コメントのお願い（半分まで来た声かけ）
    lines["extra"] = [{"id": "c_comment", "at": mid_q, "face": "smile", "until": mid_q + 9.0,
                       "text": "半分まで来ました。見つかった数を、あとでコメントで教えてくださいね。"}]
    vo["c_comment"] = "はんぶんまで、きました。みつかったかずを、あとでコメントでおしえてくださいね。"
    timeline = {"total": total, "opening": [0.0, OPENING_END], "rule": [OPENING_END, OPENING_END], "q_start": q_start,
                "unchiku": unchiku, "ending": ending, "card": CARD, "solve": SOLVE, "answer": ANSWER, "hint_at": None,
                "ten_at": 80.0, "ans_first": 1.6, "ans_step": 4.3, "solve_calls": [[30, "あと60秒です。"], [60, "あと30秒です。"]],
                "go_delay": 2.8}

    # ---- 画面・題・サムネ ----
    base = srcs[0]["plan"]["screens"]
    screens = dict(base)
    screens.update({"opening_title": f"{ta}と{tb}の間違い探し　全10問", "opening_sub": "やさしい問題から 順番に",
                    "unchiku_header": TALK["header"], "unchiku_slides": TALK["slides"],
                    "ending_titles": ENDING_TITLES, "ending_note": ENDING_NOTE, "ending_next": "ほかの間違い探しも どうぞ"})
    title = f"【間違い探し】60代70代の認知症予防｜{ta}と{tb} 簡単〜難しい全10問"
    if len(title) > 42:
        raise SystemExit(f"タイトルが{len(title)}字（42字以内）：{title}。--topic-a / --topic-b で題材を短くする")
    tsrc = opts.get("thumb", "A1")
    tq = next(i for i, (tag, s, Q) in enumerate(seq, 1) if f"{tag}{Q['q']}" == tsrc)
    plan = {
        "episode": new.name, "season": season, "topics": [ta, tb],
        "note": f"2回分を1本にした長尺（全10問・約{round(total / 60)}分。2026-11-26 CEO決定）。元：{da.name}・{db.name}。公開日は未定。サムネ・タイトルは仮の型（3案テストはしない）。",
        "combined": {"sources": [da.name, db.name], "order": order_note},
        "youtube": {"title": title, "description_file": "description.md", "publish_plan": "未定（CEOが決める）"},
        "screens": screens, "timeline": timeline, "lines": lines, "readings": readings, "voice_override": vo,
        "voice": srcs[0]["plan"]["voice"], "questions": questions,
        "thumbnail": {"style": "band", "question": tq, "band": "yellow", "top": ["60代70代", " 全部見つけられる？"],
                      "bottom": ["間違いさがし", " 全10問"], "big_text": "間違いさがし", "highlight": "間違いさがし",
                      "note": "scripts/thumb_band.py（黄帯・左右とも元の絵＝違いゼロ）"},
    }
    (new / "plan.json").write_text(json.dumps(plan, ensure_ascii=False, indent=1), encoding="utf-8")

    # ---- 説明欄（チャプター：0:00 から・全部10秒以上） ----
    ch = [(0.0, f"1問目 {questions[0]['scene']}（{questions[0]['level']}）")]
    for q in range(1, n + 1):
        Q = questions[q - 1]
        s0 = q_start[str(q)]
        if q == MID_AFTER + 1:
            ch.append((unchiku[0], "こよみ先生の季節のお話「秋の日はつるべ落とし」"))
        if q > 1:
            ch.append((s0, f"{q}問目 {Q['scene']}（{Q['level']}）"))
        ch.append((s0 + CARD + SOLVE, f"{q}問目の答え"))
    ch.append((ending[0], "エンディング・今日の称号"))
    ch.sort()
    bad = [(a, b) for (a, _), (b, _) in zip(ch, ch[1:]) if b - a < 10] + ([(ch[-1][0], total)] if total - ch[-1][0] < 10 else [])
    if bad or ch[0][0] != 0:
        raise SystemExit(f"チャプターが10秒未満か 0:00 から始まっていない：{bad}")
    chapters = "\n".join(f"{fmt(a)} {b}" for a, b in ch)
    listing = "\n".join(f"{q}問目 {Q['scene']}（{Q['level']}）" for q, Q in enumerate(questions, 1))
    desc = f"""# {new.name} YouTube 投稿用メタデータ

- 2回分（{da.name}・{db.name}）を1本にした長尺（全10問・約{round(total / 60)}分）。公開日は未定。季節は{season}（再生リストは「{season}の間違い探し」と長尺）。
- タイトルは42字以内（2026-11-26 CEO決定の型）。サムネはサムネの標準の黄帯（thumbnail.jpg）。3案テストはしない。
- 終了画面はYouTubeのおすすめに任せる（エンディングの案内は汎用）。説明欄とタグに「レクリエーション」「デイサービス」を入れた。

## タイトル
```
{title}
```

## 説明欄
```
シニアの脳トレに、{ta}と{tb}のイラストの間違い探しです。やさしい問題から難しい問題まで、全10問。
{season}の水彩画で、ほっとする頭の体操を、こよみ先生といっしょにどうぞ。
高齢者のレクリエーションやデイサービスでも、みんなで楽しめます。

今日の10問
{listing}

【あそびかた】
・全部で10問です。やさしい問題から、だんだん難しくなります。
・1問90秒で、右の絵の、左の絵との違いを3つ探してください。
・最後に、見つけた数で「今日の称号」をおくります。
・いくつ見つかったか、コメントで教えてくださいね。

【目次】
{chapters}

【投稿】
毎日朝8時半に新しい問題をお届けします

【クレジット】
音声：Fish Audio

#脳トレ #間違い探し #レクリエーション
```

## タグ（12個）
```
脳トレ, 間違い探し, 頭の体操, 間違い探し 高齢者, シニア 脳トレ, 高齢者 レクリエーション, デイサービス レクリエーション, 介護 レクリエーション, 秋の間違い探し, きのこ狩り, 芋煮会, こよみ先生
```
"""
    (new / "description.md").write_text(desc, encoding="utf-8")

    print(f"作った：{new}（全{n}問・{total:.1f}秒＝{fmt(total)}）\nタイトル（{len(title)}字）：{title}")
    print("\n".join(order_note))
    print("チャプター：\n" + chapters)
    print(f"check が止める項目：{len(stops)}件" + ("" if not stops else "（上の一覧。swap_diff.py で差し替える）"))


if __name__ == "__main__":
    main(sys.argv[1:])
