"""「文字の脳トレ」長尺（20問）を作る（2026-11-25 CEO指示：文字クイズの長尺の実験）。画像APIは使わず、文字だけをプログラムで描く。
scripts/text_shorts.py の声の手順（voice）・こよみ先生（owl）・季節の色・読みの対照表を import して使い回す。text_shorts.py・chigau_shorts.py は変えていない。

使い方：
  python3 scripts/text_long.py check <回のフォルダ>    … 問題の定義（problem.json）の数値チェック。答えの確かめを answer_check.md に書く（声・画像は使わない）
  python3 scripts/text_long.py build <回のフォルダ>    … 声・動画（video.mp4）・サムネ（thumbnail.jpg・ab/thumb_A.jpg）・description.md・読みの対照表・一覧画像を作る
  python3 scripts/text_long.py voices <回のフォルダ>   … 声の wav だけ作る（transcribe_check の前）
回のフォルダは outputs/YYYY-MM-DD_tlong_NNN。定義は <フォルダ>/problem.json（例：outputs/2026-11-25_tlong_001/problem.json）。

画面（横1920×1080・30fps・季節の背景 scripts/season_theme.json）：
  オープニング（5秒以内に1問目を予告・10秒以内に1問目）→ 各問「問題（声で出題）→ 考える時間（15秒前後。カウントダウンと効果音）→ 答え」→ エンディング（汎用の案内・登録のお願いは最後だけ）
  こよみ先生は左下の隅。声の字幕は先生の横の吹き出し（画面の高さの6%以上）。
音：間違い探しと同じ BGM・効果音（ep_audio の部品。text_shorts.mix_audio と同じ鳴らし方）。
"""
import json, math, random, re, subprocess, sys, wave
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).parent))
import text_shorts as T
from season_pick import pick

W, H, FPS = 1920, 1080, 30
WORK = Path.home() / ".cache/koyomi/text_long"
T.WORK = WORK                                   # 声・こよみ先生の画像の置き場（text_shorts の voice・owl がここを使う）
LEVEL_COLOR = {"やさしい": (70, 140, 190), "ふつう": (214, 128, 48), "むずかしい": (176, 62, 52)}
NUM = {1: "いち", 2: "に", 3: "さん", 4: "よん", 5: "ご", 6: "ろく", 7: "なな", 8: "はち", 9: "きゅう", 10: "じゅう",
       11: "じゅういち", 12: "じゅうに", 13: "じゅうさん", 14: "じゅうよん", 15: "じゅうご", 16: "じゅうろく", 17: "じゅうなな",
       18: "じゅうはち", 19: "じゅうきゅう", 20: "にじゅう"}     # 「○問目」の読み（2026-11-23：「第2問」が崩れた。「にもんめ」と言う）
TH = {}                                          # 季節の色（setup が入れる）

PREFS = ["北海道", "青森県", "岩手県", "宮城県", "秋田県", "山形県", "福島県", "茨城県", "栃木県", "群馬県", "埼玉県", "千葉県", "東京都", "神奈川県",
         "新潟県", "富山県", "石川県", "福井県", "山梨県", "長野県", "岐阜県", "静岡県", "愛知県", "三重県", "滋賀県", "京都府", "大阪府", "兵庫県",
         "奈良県", "和歌山県", "鳥取県", "島根県", "岡山県", "広島県", "山口県", "徳島県", "香川県", "愛媛県", "高知県", "福岡県", "佐賀県", "長崎県",
         "熊本県", "大分県", "宮崎県", "鹿児島県", "沖縄県"]
CAPITALS = ["札幌市", "青森市", "盛岡市", "仙台市", "秋田市", "山形市", "福島市", "水戸市", "宇都宮市", "前橋市", "さいたま市", "千葉市", "新宿区", "横浜市",
            "新潟市", "富山市", "金沢市", "福井市", "甲府市", "長野市", "岐阜市", "静岡市", "名古屋市", "津市", "大津市", "京都市", "大阪市", "神戸市",
            "奈良市", "和歌山市", "鳥取市", "松江市", "岡山市", "広島市", "山口市", "徳島市", "高松市", "松山市", "高知市", "福岡市", "佐賀市", "長崎市",
            "熊本市", "大分市", "宮崎市", "鹿児島市", "那覇市"]


def setup(P):
    name, th = pick(P.get("season", "冬"))
    TH.clear(); TH.update(th); TH["name"] = name
    return name


def f(size):
    return T.f(size)


def tc(d, xy, s, size, fill, stroke=0, sf=None, anchor="mm"):
    d.text(xy, s, font=f(size), fill=fill, anchor=anchor, stroke_width=stroke, stroke_fill=sf)


def fit(d, s, size, maxw):
    while d.textlength(s, font=f(size)) > maxw and size > 30:
        size -= 4
    return size


# ---------- 舞う雪（オープニング・エンディング。ep_video.leaves と同じ形を横1920×1080で） ----------
def snow(d, t, n=46, seed=3):
    r = random.Random(seed)
    P = TH["particles"]
    fill, outline = tuple(P["fill"]), tuple(P["outline"])
    for i in range(n):
        x0, sp, ph, sz = r.uniform(0, W), r.uniform(30, 60), r.uniform(0, 100), r.uniform(8, 16)
        y = ((t + ph) * sp) % (H + 100) - 50
        x = x0 + 30 * math.sin((t + ph) * 0.7)
        d.ellipse((x - sz, y - sz, x + sz, y + sz), fill=fill, outline=outline, width=2)


# ---------- こよみ先生と吹き出し（左下の隅） ----------
OWL_S, OWL_XY = 230, (40, 815)
BUB = (300, 830, 1860, 1040)


def owl(face, size=OWL_S):
    return T.owl(face).resize((size, size), Image.LANCZOS)


def speaker(im, face, sub=None):
    o = owl(face)
    im.paste(o, OWL_XY, o)
    if sub:
        d = ImageDraw.Draw(im)
        x0, y0, x1, y1 = BUB
        d.rounded_rectangle(BUB, 34, fill=(255, 255, 255), outline=TH["accent"], width=6)
        d.polygon([(x0 + 3, y0 + 80), (x0 - 40, y0 + 112), (x0 + 3, y0 + 130)], fill=(255, 255, 255))
        sz = 68
        ls = T.wrap(d, sub, sz, x1 - x0 - 70)
        while len(ls) > 2 and sz > 54:
            sz -= 4; ls = T.wrap(d, sub, sz, x1 - x0 - 70)
        y = (y0 + y1) / 2 - (len(ls) - 1) * sz * 0.62
        for l in ls:
            d.text((x0 + 35, y), l, font=f(sz), fill=TH["ink"], anchor="lm"); y += sz * 1.24
    return im


# ---------- 各問の画面 ----------
def question_frame(i, n, Q, state, remain=None, sub=None, face="normal", rule=False, think=15):
    """state 0＝問題、1＝答え。remain＝のこり秒数（考える時間）。sub＝先生の吹き出しの字幕。"""
    im = Image.new("RGB", (W, H), TH["bg"])
    d = ImageDraw.Draw(im)
    lc = LEVEL_COLOR.get(Q["level"], TH["accent"])
    d.rounded_rectangle((60, 40, 400, 190), 40, fill=TH["accent"])
    tc(d, (230, 117), f"{i}問目", 100, (255, 255, 255))
    d.rounded_rectangle((430, 68, 700, 162), 36, fill=lc)
    tc(d, (565, 115), Q["level"], 56, (255, 255, 255))
    if remain is None:
        tc(d, (1860, 115), f"全{n}問", 52, TH["muted"], anchor="rm")
    else:
        cx, cy, r = 1760, 118, 90
        d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=TH["panel"])
        d.arc((cx - r, cy - r, cx + r, cy + r), -90, -90 + 360 * remain / think, fill=TH["alert"] if remain <= 3 else TH["accent"], width=16)
        tc(d, (cx, cy), str(remain), 104, TH["alert"] if remain <= 3 else TH["ink"])
    clue = Q["clue"]
    tc(d, (W // 2, 310), clue, fit(d, clue, 104, 1760), TH["ink"])
    rule_txt = "□の中の漢字を、考えてみてね" if rule else "□にあてはまる漢字は？"
    tc(d, (W // 2, 412), rule_txt, 54, TH["accent2"])
    d.rounded_rectangle((160, 455, 1760, 790), 44, fill=TH["panel"], outline=TH["edge"], width=6)
    shown = Q["a"] if state else Q["q"]
    step = min(280, 1500 // len(shown))
    size = min(230, step - 40)
    x = W // 2 - (len(shown) * step) // 2 + step // 2
    for k, ch in enumerate(shown):
        cx, cy = x + k * step, 622
        if Q["q"][k] == "□":
            hb = size // 2 + 4
            if state:
                d.rounded_rectangle((cx - hb, cy - hb, cx + hb, cy + hb), 24, fill=TH["hit"])
                tc(d, (cx, cy), ch, size, TH["alert"])
            else:
                d.rounded_rectangle((cx - hb, cy - hb, cx + hb, cy + hb), 24, outline=TH["alert"], width=14)
        else:
            tc(d, (cx, cy), ch, size, TH["ink"])
    return speaker(im, face, sub)


def card_frame(lines, face, sub, t=0.0, with_snow=True, owl_big=True):
    """オープニング・ひと言のカード・エンディング。lines＝[(文字, 大きさ, 色)]（中央に縦に並べる）。"""
    im = Image.new("RGB", (W, H), TH["bg"])
    d = ImageDraw.Draw(im)
    if with_snow:
        snow(d, t)
    total = sum(int(sz * 1.3) for _, sz, _ in lines)
    y = 400 - total // 2
    for s, sz, col in lines:
        sz = fit(d, s, sz, 1700)
        y += int(sz * 1.3) // 2
        tc(d, (W // 2, y), s, sz, col, stroke=0)
        y += int(sz * 1.3) // 2
    return speaker(im, face, sub)


# ---------- 音（text_shorts.mix_audio と同じ部品・同じ鳴らし方。問ごとに繰り返す） ----------
def mix_audio(voices, ev, total, path):
    import ep_audio as A
    from ep_short import VOICE_RMS_DB
    from scipy.ndimage import uniform_filter1d
    SR = A.SR
    n = int(total * SR)

    def put(track, x, at):
        s0 = int(at * SR)
        if s0 >= n:
            return
        e = min(n, s0 + len(x)); track[s0:e] += x[:e - s0]
    vo = np.zeros(n)
    for w, at, _, _ in voices:
        x = A.read_wav(w)
        x = x * (10 ** (VOICE_RMS_DB / 20) / (np.sqrt(np.mean(x[np.abs(x) > 0.01] ** 2)) + 1e-9))
        put(vo, np.clip(x, -0.9, 0.9), at)
    vo *= 0.6 / max(np.abs(vo).max(), 1e-9)
    sfx = np.zeros(n)
    for at in ev["start"]:
        put(sfx, A.chime((79, 84, 88), 0.18), at)           # 問の頭のピンポン（間違い探しのショートの0秒と同じ）
    for se in ev["solve_end"]:
        for k in range(5):
            put(sfx, A.tick(), se - 5 + k)                   # 残り5〜1秒のカウント音
        put(sfx, A.chime((84, 79), 0.25), se)                # 時間切れ（答えの前のチャイム）
    for at in ev["pon"]:
        put(sfx, A.pon(), at)                                # 答えのポン
    put(sfx, A.chime((84, 88), 0.25, 0.16), ev["end_at"])    # 最後のチャイム
    music = A.bgm()
    music = np.tile(music, int(np.ceil(n / len(music))))[:n]
    act = uniform_filter1d((np.abs(vo) > 0.01).astype(float), int(0.3 * SR), mode="constant") > 0.02
    duck = uniform_filter1d(np.where(act, 0.45, 1.0), int(0.15 * SR), mode="nearest")
    gain = np.ones(n)
    for a, b in ev["think"]:
        gain[int(a * SR):int(b * SR)] = 0.7                  # 考える時間のBGMは0.7倍
    tt = np.arange(n) / SR
    fade = np.clip(np.minimum(tt / 0.3, (total - tt) / 1.5), 0, 1)
    mix = vo + sfx + music * gain * duck * fade
    mix *= min(1.0, 0.95 / np.abs(mix).max())
    st = np.repeat((mix * 32767).astype(np.int16)[:, None], 2, axis=1)
    with wave.open(str(path), "wb") as wv:
        wv.setnchannels(2); wv.setsampwidth(2); wv.setframerate(SR); wv.writeframes(st.tobytes())


# ---------- 定義の読み込み・数値チェック ----------
def load(folder):
    P = json.loads((Path(folder) / "problem.json").read_text(encoding="utf-8"))
    setup(P)
    T.PROBLEM_ID = P["id"]
    return P


def lines_of(P):
    """声に渡す文（字幕, 声）。出題・答え・オープニング・ひと言・エンディング。"""
    n = len(P["questions"])
    L = {"open": tuple(P["opening"]["line"])}
    for i, Q in enumerate(P["questions"], 1):
        Q["_i"] = i
        L[f"q{i:02d}_intro"] = (f"{i}問目です。{Q['clue_sub']}□にあてはまる漢字は？", f"{Q.get('num_voice', NUM[i] + 'もんめ、です。')}{Q['clue_voice']}しかくにあてはまる、かんじは？")
        L[f"q{i:02d}_ans"] = (f"答えは、{Q['a']}です。", f"こたえは、{Q['ans_voice']}")
    for k, br in P.get("breaks", {}).items():
        L[f"break{int(k):02d}"] = tuple(br["line"])
    for j, ln in enumerate(P["ending"]["lines"]):
        L[f"end{j + 1}"] = tuple(ln)
    return L


def used_answers(folder):
    """ショートですでに出した都道府県の問題の答え（outputs/*_text_*/problem.json の pref）。"""
    out = {}
    for p in sorted(Path(folder).resolve().parent.glob("*_text_*/problem.json")):
        try:
            J = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        if J.get("kind") == "pref":
            for it in J["items"]:
                out.setdefault(it[1], []).append(p.parent.name[-8:])
    return out


def check(folder):
    P = load(folder)
    Qs, n = P["questions"], len(P["questions"])
    used = used_answers(folder)
    bad, rows, reuse, new = [], [], 0, 0
    levels = [Q["level"] for Q in Qs]
    if n != P["count"]:
        bad.append(f"問題数 {n} ≠ {P['count']}")
    if levels != sorted(levels, key=lambda x: ["やさしい", "ふつう", "むずかしい"].index(x)):
        bad.append("難しさの順（やさしい→ふつう）になっていない")
    for i, Q in enumerate(Qs, 1):
        q, a = Q["q"], Q["a"]
        if q.count("□") != 1:
            bad.append(f"{i}問目：□が1つでない")
        if len(q) != len(a) or not all(qc == "□" or qc == ac for qc, ac in zip(q, a)):
            bad.append(f"{i}問目：問題と答えの字が合わない（{q}／{a}）")
        k = q.index("□")
        pool = CAPITALS if a.endswith("市") or a.endswith("区") else PREFS
        cand = [x for x in pool if len(x) == len(q) and all(qc == "□" or qc == xc for qc, xc in zip(q, x))]
        if a not in cand:
            bad.append(f"{i}問目：答え {a} が正解の一覧にない")
        if len(cand) > 1 and not Q.get("clue_resolves"):
            bad.append(f"{i}問目：当てはまる候補が{cand}。clue_resolves に、ヒントで1つに決まる理由を書く")
        reused = a in used
        if reused != (Q["origin"].startswith("reuse")):
            bad.append(f"{i}問目：origin が実際と違う（ショートで{'出した' if reused else '出していない'}答え {a}：{used.get(a, '')}）")
        reuse += reused; new += not reused
        rows.append(f"| {i} | {Q['level']} | {Q['clue']} | {q} | {a}（□＝{a[k]}） | {len(cand)}：{'・'.join(cand)} | {Q.get('clue_resolves', '候補が1つ')} | {'ショート '+ '・'.join(used[a]) if reused else '新しい問題'} |")
    if new < 11:
        bad.append(f"新しい問題 {new} 問（11問以上にする）")
    if reuse > n // 2:
        bad.append(f"ショートで使った問題 {reuse} 問（半分まで）")
    if len({Q["a"] for Q in Qs}) != n:
        bad.append("同じ答えが2問ある")
    for i, Q in enumerate(Qs, 1):   # 声に渡す文：漢字が残っていない・「入る」を使わない
        for key in (f"q{i:02d}_intro", f"q{i:02d}_ans"):
            vt = lines_of(P)[key][1]
            if re.search(r"[一-鿿]", vt):
                bad.append(f"{key}：声の文に漢字が残っている：{vt}")
            if "はいる" in vt or "にいる" in vt:
                bad.append(f"{key}：「入る」系の読みがある：{vt}")
    md = [f"# 答えの確かめ（{P['id']}：{P['series']} 全{n}問）", "",
          "プログラム（scripts/text_long.py check）が、各問の「□を1つ含む文字列」に当てはまる都道府県（または県庁所在地）を全47から数えた結果。",
          "候補が複数のときは、ヒント（clue）で1つに決まる理由を書いてある。", "",
          f"新しい問題 {new} 問・ショートで使った問題 {reuse} 問（半分まで）。", "",
          "| 問 | 難しさ | ヒント | 問題 | 答え | 当てはまる候補（全47から） | 1つに決まる理由 | 出どころ |", "|---|---|---|---|---|---|---|---|"] + rows
    md += ["", "結果：" + ("不合格 " + str(len(bad)) + " 件" if bad else "合格（答えは全問で1つに決まる）")]
    (Path(folder) / "answer_check.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print("\n".join(bad) if bad else f"OK：{n}問（新しい {new}・ショート {reuse}）")
    return not bad


# ---------- 声 ----------
def make_voices(P):
    L = lines_of(P)
    V = {}
    for key, line in L.items():
        w, dur = T.voice("tlong", key, line[1])
        V[key] = (w, dur, line)
    return V


# ---------- 動画 ----------
def build(folder):
    folder = Path(folder).resolve()
    if not check(folder):
        sys.exit("check が不合格。直してから作る")
    P = load(folder)
    Qs, n, think = P["questions"], len(P["questions"]), P.get("think", 15)
    V = make_voices(P)
    seq, voices, chapters = [], [], []
    ev = {"start": [0.0], "solve_end": [], "pon": [], "think": []}
    t = 0.0

    def say(key, at):
        w, dur, line = V[key]
        voices.append((w, at + 0.3, key, line))
        return dur

    # オープニング（5秒以内に1問目を予告）
    d = say("open", 0.0)
    o_len = d + 0.3 + 0.6
    op = P["opening"]
    for k in range(int(o_len * 10)):
        tt = k / 10
        seq.append((card_frame([(op["title"], 200, TH["accent"]), (op["count"], 140, TH["ink"]), (op["sub"], 72, TH["accent2"])], "smile", V["open"][2][0], tt), 0.1))
    t += int(o_len * 10) / 10
    chapters.append((0.0, "オープニング"))
    for i, Q in enumerate(Qs, 1):
        key = f"break{i:02d}"
        if key in V:                       # ひと言のカード（例：ここからは ふつう）
            d = say(key, t)
            ln = d + 0.3 + 0.7
            br = P["breaks"][str(i)]
            seq.append((card_frame([(br["title"], 150, TH["accent"]), (br["sub"], 72, TH["accent2"])], "wink", V[key][2][0], 0, with_snow=False), ln)); t += ln
        t0 = t
        chapters.append((t0, f"{i}問目（{Q['clue']}）"))
        ev["start"].append(t0)
        d = say(f"q{i:02d}_intro", t)
        ln = d + 0.3 + 0.5
        seq.append((question_frame(i, n, Q, 0, None, V[f"q{i:02d}_intro"][2][0], "normal", rule=(i == 1), think=think), ln)); t += ln
        ev["think"].append((t, t + think))
        for r in range(think, 0, -1):
            seq.append((question_frame(i, n, Q, 0, r, None, "think" if r < think - 3 else "smile", think=think), 1.0)); t += 1.0
        ev["solve_end"].append(t)
        ev["pon"].append(t + 0.35)
        d = say(f"q{i:02d}_ans", t + 0.4)
        ln = 0.4 + d + 0.3 + 1.3
        seq.append((question_frame(i, n, Q, 1, None, V[f"q{i:02d}_ans"][2][0], "yay", think=think), ln)); t += ln
    # エンディング（汎用の案内・登録のお願いは最後だけ）
    ev["end_at"] = t
    ENDING_AT[0] = t
    e0, at = t, t
    texts = []
    for j in range(len(P["ending"]["lines"])):
        d = say(f"end{j + 1}", at)
        texts.append((at, at + 0.3 + d + 0.3, V[f"end{j + 1}"][2][0]))
        at += 0.3 + d + 0.7
    e_len = max(P["ending"].get("min_len", 20.0), at - e0 + 1.0)
    en = P["ending"]
    for k in range(int(e_len * 10)):
        tt = k / 10
        cur = next((s for a, b, s in texts if a + 0.0 <= e0 + tt < b), None)
        seq.append((card_frame([(en["title"], 150, TH["accent"]), (en["sub"], 80, TH["ink"]), (en["note"], 64, TH["accent2"])], "smile", cur, tt), 0.1))
    t += int(e_len * 10) / 10
    total = t
    tmp = WORK / f"_{P['id']}"
    tmp.mkdir(parents=True, exist_ok=True)
    for p in tmp.iterdir():
        p.unlink()
    lst = []
    for i, (im, dt) in enumerate(seq):
        p = tmp / f"{i:04d}.jpg"; im.save(p, quality=95, subsampling=0); lst.append(f"file '{p}'\nduration {dt:.4f}\n")
    (tmp / "list.txt").write_text("".join(lst) + f"file '{tmp / f'{len(seq) - 1:04d}.jpg'}'\n", encoding="utf-8")
    mix_audio(voices, ev, total, tmp / "mix.wav")
    T.readings_check("tlong", voices, folder)
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(tmp / "list.txt"), "-i", str(tmp / "mix.wav"),
                    "-map", "0:v", "-map", "1:a", "-vf", f"fps={FPS},format=yuv420p", "-c:v", "libx264", "-preset", "fast", "-crf", "20",
                    "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-t", f"{total:.2f}", "-movflags", "+faststart", str(folder / "video.mp4")], check=True)
    # 一覧画像：0:00・オープニング・1問目（問題・答え）・エンディング
    k0 = int(o_len * 10)      # 1問目の問題の絵の位置
    shots = [seq[0][0], seq[k0 // 2][0], seq[k0][0], seq[k0 + 1 + think // 2][0], seq[k0 + 1 + think][0], seq[-30][0]]
    S = Image.new("RGB", (3 * 640, 2 * 360))
    for k, im in enumerate(shots):
        S.paste(im.resize((640, 360)), ((k % 3) * 640, (k // 3) * 360))
    S.save(folder / "frames.jpg", quality=85)
    for p in tmp.iterdir():
        p.unlink()
    tmp.rmdir()
    write_description(P, folder, chapters, total)
    make_thumbnail(P, folder)
    (folder / "timeline.json").write_text(json.dumps({"total_sec": round(total, 1), "chapters": [[round(a, 1), b] for a, b in chapters]}, ensure_ascii=False, indent=1), encoding="utf-8")
    return round(total, 1)


def mmss(s):
    s = int(s)
    return f"{s // 60}:{s % 60:02d}"


def write_description(P, folder, chapters, total):
    D = P["description"]
    chs = list(chapters) + [(ENDING_AT[0], "エンディング")]
    body = D["body"].rstrip() + "\n\n【目次】\n" + "\n".join(f"{mmss(a)} {b}" for a, b in chs)
    desc = f"""# {P['id']} YouTube 投稿用メタデータ（文字の脳トレ 長尺）

- 作り方：python3 scripts/text_long.py build {Path(folder).name}（定義は problem.json）。長さ {mmss(total)}（{total:.0f}秒）。
- タイトル {len(D['title'])}文字（32字以内）。説明欄とタグに「レクリエーション」「デイサービス」。効果の約束はしていない。カテゴリは教育。再生リストは「文字の脳トレ｜毎日1分」（フォルダ名の _tlong_NNN で自動）。
- サムネ：thumbnail.jpg（ab/thumb_A.jpg と同じ）。左右とも同じ絵（問題の画面を2枚並べた）。thumb_same_check 合格。
- 終了画面の動画の枠は、YouTube のおすすめ（視聴者に適したコンテンツ＋最新のアップロード）に任せる（エンディングの声の案内は汎用）。

## タイトル
```
{D['title']}
```

## 説明欄
```
{body}
```

## タグ
```
{', '.join(D['tags'])}
```
"""
    (Path(folder) / "description.md").write_text(desc, encoding="utf-8")


ENDING_AT = [0.0]


def make_thumbnail(P, folder):
    """サムネ（thumbnail-title.md の標準：黒帯。左右とも同じ絵）。thumb_band.make を使い、絵だけ問題の画面に差し替える。1枚でよい。"""
    import thumb_band as TB
    Th = P["thumbnail"]
    Q = P["questions"][Th["q"] - 1]
    pw, ph, top = 636, 720 - 170, 170
    sc = 2
    im = Image.new("RGB", (pw * sc, ph * sc), TH["bg"])
    d = ImageDraw.Draw(im)
    clue = Q["clue"]
    tc(d, (pw * sc // 2, 120), clue, fit(d, clue, 120, pw * sc - 80), TH["ink"])
    d.rounded_rectangle((50, 215, pw * sc - 50, 655), 60, fill=TH["panel"], outline=TH["edge"], width=8)
    q = Q["q"]
    step = min(330, (pw * sc - 200) // len(q))
    size = min(300, step - 40)
    x = pw * sc // 2 - (len(q) * step) // 2 + step // 2
    cy = (215 + 655) // 2
    for k, ch in enumerate(q):
        cx = x + k * step
        if ch == "□":
            hb = size // 2 + 4
            d.rounded_rectangle((cx - hb, cy - hb, cx + hb, cy + hb), 30, outline=TH["alert"], width=18)
        else:
            tc(d, (cx, cy), ch, size, TH["ink"])
    pic = im.resize((pw, ph), Image.LANCZOS)
    TB.pics = lambda ep, qn, sat=1.15: (pic, pic, top)        # 左右とも同じ絵（違いゼロ）
    out = Path(folder) / "ab"
    out.mkdir(exist_ok=True)
    TB.make(out / "thumb_A.jpg", Path(folder), 1, TB.K, (Th["emph"], Th["rest"]), tuple(Th["bottom"]))
    import shutil
    shutil.copy(out / "thumb_A.jpg", Path(folder) / "thumbnail.jpg")


if __name__ == "__main__":
    cmd, folder = sys.argv[1], sys.argv[2]
    if cmd == "check":
        sys.exit(0 if check(folder) else 1)
    elif cmd == "voices":
        P = load(folder); V = make_voices(P)
        print(len(V), "行の声（", ", ".join(str(Path(v[0]).parent) for v in list(V.values())[:1]), "）")
    elif cmd == "thumb":
        make_thumbnail(load(folder), folder)
    elif cmd == "build":
        print("長さ", build(folder), "秒")
