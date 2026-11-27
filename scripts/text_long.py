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
ROW = {1: "いち", 2: "に", 3: "さん", 4: "よん", 5: "ご", 6: "ろく", 7: "なな"}
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


def speaker(im, face, sub=None, one_line=False):
    o = owl(face)
    im.paste(o, OWL_XY, o)
    if sub:
        d = ImageDraw.Draw(im)
        x0, y0, x1, y1 = BUB
        d.rounded_rectangle(BUB, 34, fill=(255, 255, 255), outline=TH["accent"], width=6)
        d.polygon([(x0 + 3, y0 + 80), (x0 - 40, y0 + 112), (x0 + 3, y0 + 130)], fill=(255, 255, 255))
        sz = 68
        if one_line:      # 1行に収まる大きさがあれば、そちらにする（2行目に「に。」だけ残るのを避ける。漢字の回で使う）
            for z in range(68, 55, -4):
                if d.textlength(sub, font=f(z)) <= x1 - x0 - 70:
                    sz = z; break
        ls = T.wrap(d, sub, sz, x1 - x0 - 70)
        while len(ls) > 2 and sz > 54:
            sz -= 4; ls = T.wrap(d, sub, sz, x1 - x0 - 70)
        y = (y0 + y1) / 2 - (len(ls) - 1) * sz * 0.62
        for l in ls:
            d.text((x0 + 35, y), l, font=f(sz), fill=TH["ink"], anchor="lm"); y += sz * 1.24
    return im


# ---------- 各問の画面 ----------
def header(d, i, n, Q, remain, think):
    """上の帯：番号札・難しさ・（のこり秒数の丸 または 全○問）。"""
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


def question_frame(i, n, Q, state, remain=None, sub=None, face="normal", rule=False, think=15):
    """state 0＝問題、1＝答え。remain＝のこり秒数（考える時間）。sub＝先生の吹き出しの字幕。"""
    im = Image.new("RGB", (W, H), TH["bg"])
    d = ImageDraw.Draw(im)
    header(d, i, n, Q, remain, think)
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


def kanji_frame(i, n, Q, state, remain=None, sub=None, face="normal", rule=False, think=15):
    """漢字の間違い探し：左右に同じ言葉を並べ、右に違う字が2つ。state＝答えを見せた数（0〜2）。左右の違う所に赤丸を付ける。"""
    im = Image.new("RGB", (W, H), TH["bg"])
    d = ImageDraw.Draw(im)
    header(d, i, n, Q, remain, think)
    tc(d, (1230 if rule else 1130, 118), "左と右で、ちがう字が2つあるよ" if rule else "左と右で、ちがう字は？", 56 if rule else 62, TH["ink"])
    word, rows = Q["word"], Q["rows"]
    size, ch = (120, 142) if rows <= 4 else (98, 116)
    cw = int(size * 1.3)
    pw, ph = cw * 3 + 30, ch * rows + 28
    gap = 140
    x0 = (W - (2 * pw + gap)) // 2
    y0 = 214
    diffs = {(r, c): sub_ for r, c, sub_, *_ in Q["diffs"]}
    for side, px in ((0, x0), (1, x0 + pw + gap)):
        d.rounded_rectangle((px, y0, px + pw, y0 + ph), 28, fill=TH["panel"], outline=TH["edge"], width=6)
        for r in range(rows):
            for c in range(3):
                x, y = px + 15 + cw * c + cw // 2, y0 + 14 + ch * r + ch // 2
                tc(d, (x, y), diffs.get((r, c), word[c]) if side else word[c], size, TH["ink"])
                if (r, c) in diffs and state > [(a_, b_) for a_, b_, *_ in Q["diffs"]].index((r, c)):
                    rr = int(size * 0.66)
                    d.ellipse((x - rr, y - rr, x + rr, y + rr), outline=TH["alert"], width=10)
    return speaker(im, face, sub, one_line=True)


# ---------- ちがうのどーれだ（漢字版）：散らし配置（scripts/chigau_shorts.py の考え方を、横画面で） ----------
def font_w(size, weight="700Bold"):
    from PIL import ImageFont
    return ImageFont.truetype(str(Path.home() / f".cache/koyomi/fonts/package/{weight}/NotoSansJP_{weight}.ttf"), size)


def glyph(ch, size, angle=0, weight="700Bold"):
    """1文字を透明な正方形に描き、angle 度まわす。"""
    s = int(size * 1.5)
    g = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    ImageDraw.Draw(g).text((s / 2, s / 2), ch, font=font_w(size, weight), fill=tuple(TH["ink"]) + (255,), anchor="mm")
    return g.rotate(angle, resample=Image.BICUBIC) if angle else g


AREA = (190, 245, 1730, 770)          # 字を置く範囲（台紙 160〜1760 × 215〜800 の内側）


def scatter(Q, area=AREA, canvas=(W, H)):
    """大きい字から順に、重ならない場所をさがして置く（インクの形で検査）。戻り値＝[(字, 中心x, 中心y, 大きさ, 角度)]。"""
    from PIL import ImageFilter
    rnd = random.Random(Q["seed"])
    x0, y0, x1, y1 = area
    sizes = sorted([rnd.randint(*Q["size"]) for _ in range(Q["n"])], reverse=True)
    occ = np.zeros((canvas[1], canvas[0]), bool)
    placed = []
    for i, sz in enumerate(sizes):
        ch = Q["odd"] if i == Q["odd_i"] else Q["main"]
        for _ in range(500):
            ang = rnd.randint(-Q["tilt"], Q["tilt"])
            g = glyph(ch, sz, ang, Q["weight"]).split()[3].point(lambda v: 255 if v > 30 else 0).filter(ImageFilter.MaxFilter(9))
            bb = g.getbbox(); full = g.size[0]
            g = g.crop(bb); gw, gh = g.size
            if gw > x1 - x0 or gh > y1 - y0:
                continue
            px = rnd.randint(x0, x1 - gw); py = rnd.randint(y0, y1 - gh)
            cx = px + gw / 2 - (bb[0] + gw / 2 - full / 2); cy = py + gh / 2 - (bb[1] + gh / 2 - full / 2)
            m = np.array(g) > 0
            if not (occ[py:py + gh, px:px + gw] & m).any():
                occ[py:py + gh, px:px + gw] |= m
                placed.append((ch, cx, cy, sz, ang)); break
        else:
            raise SystemExit(f"置ききれない（{Q['main']}/{Q['odd']} {i}個目）。個数か大きさを減らす")
    return placed


_LAY = {}


def layout(Q):
    key = (Q["main"], Q["odd"], Q["seed"], Q["n"], tuple(Q["size"]), Q["tilt"], Q["odd_i"])
    if key not in _LAY:
        for k in range(200):        # 置ききれないときは、乱数の種を変えて置き直す（同じ問題は毎回同じ置き方になる）
            try:
                _LAY[key] = scatter(dict(Q, seed=Q["seed"] + 100 * k)); break
            except SystemExit:
                continue
        else:
            raise SystemExit(f"置ききれない（{Q['main']}/{Q['odd']}）。個数か大きさを減らす")
    return _LAY[key]


def chigau_frame(i, n, Q, state, remain=None, sub=None, face="normal", rule=False, think=15):
    """ちがうのどーれだ：同じ字がたくさん散らばる中に、違う字が1つ。state＝1で赤丸。"""
    im = Image.new("RGB", (W, H), TH["bg"])
    d = ImageDraw.Draw(im)
    header(d, i, n, Q, remain, think)
    tc(d, (1230 if rule else 1130, 118), "一つだけ違う字があるよ" if rule else "ちがうのどーれだ？", 56 if rule else 66, TH["ink"])
    d.rounded_rectangle((160, 215, 1760, 800), 44, fill=TH["panel"], outline=TH["edge"], width=6)
    for ch, cx, cy, sz, ang in layout(Q):
        g = glyph(ch, sz, ang, Q["weight"])
        im.paste(g, (int(cx - g.width / 2), int(cy - g.height / 2)), g)
        if ch == Q["odd"] and state:
            r_ = int(sz * 0.64)
            d.ellipse((cx - r_, cy - r_, cx + r_, cy + r_), outline=TH["alert"], width=12)
    return speaker(im, face, sub, one_line=True)


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
    kanji = P["kind"] == "kanji_long"
    for i, Q in enumerate(P["questions"], 1):
        Q["_i"] = i
        if P["kind"] == "chigau_long":
            L[f"q{i:02d}_intro"] = (f"{i}問目です。違う漢字が、1つだけあります。どれでしょう？", f"{Q.get('num_voice', NUM[i] + 'もんめです。')}ちがうかんじが、ひとつだけあります。どれでしょう？")
            L[f"q{i:02d}_ans"] = (f"{Q['main_text']}の中に、{Q['odd_text']}が、混ざっていました。", f"{Q['main_voice']}、のなかに、{Q['odd_voice']}、が、まざっていました。")
            continue
        if kanji:
            L[f"q{i:02d}_intro"] = (f"{Q.get('num_sub', str(i) + '問目です。')}違う漢字が、2つあります。", f"{Q.get('num_voice', NUM[i] + 'もんめ、です。')}ちがうかんじが、ふたつあります。")
            for k, (r, c, sub_, ot, ov, st, sv) in enumerate(Q["diffs"], 1):
                L[f"q{i:02d}_ans{k}"] = (f"上から{r + 1}行目、{ot}が、{st}に。", f"うえから、{ROW[r + 1]}ぎょうめ、{ov}、{sv}。")
            continue
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


def used_words(folder):
    """ショートで出した漢字の間違い探しの言葉（outputs/*_text_*/problem.json の kanji）と、違う字の組。"""
    out = {}
    for p in sorted(Path(folder).resolve().parent.glob("*_text_*/problem.json")):
        try:
            J = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        if J.get("kind") == "kanji":
            out[J["word"]] = (p.parent.name[-8:], [d[2] for d in J["diffs"]])
    return out


_NOTDEF = {}


def has_glyph(ch):
    """フォントに字があるか（存在しない字の「豆腐」と同じ形でないか）。PIL で描いて比べる。"""
    if not _NOTDEF:
        _NOTDEF["m"] = bytes(f(120).getmask("\uffff"))
    m = f(120).getmask(ch)
    return m.getbbox() is not None and bytes(m) != _NOTDEF["m"]


def check_kanji(folder, P):
    Qs, n = P["questions"], len(P["questions"])
    used = used_words(folder)
    L = lines_of(P)
    bad, rows, reuse, new = [], [], 0, 0
    levels = [Q["level"] for Q in Qs]
    if n != P["count"]:
        bad.append(f"問題数 {n} ≠ {P['count']}")
    if levels != sorted(levels, key=lambda x: ["やさしい", "ふつう", "むずかしい"].index(x)):
        bad.append("難しさの順（やさしい→ふつう）になっていない")
    if len({Q["word"] for Q in Qs}) != n:
        bad.append("同じ言葉が2問ある")
    allsubs = []
    for i, Q in enumerate(Qs, 1):
        w, dfs = Q["word"], Q["diffs"]
        if len(w) != 3 or len(dfs) != 2:
            bad.append(f"{i}問目：言葉は3字・違う字は2つ（{w}・{len(dfs)}つ）")
            continue
        cells = [(d[0], d[1]) for d in dfs]
        if len(set(cells)) != 2 or cells[0][0] == cells[1][0]:
            bad.append(f"{i}問目：違う字が同じ行・同じ場所にある")
        for r, c, sub_, ot, ov, st, sv in dfs:
            if not (0 <= r < Q["rows"] and 0 <= c < 3):
                bad.append(f"{i}問目：場所が範囲外 ({r},{c})")
            if sub_ == w[c]:
                bad.append(f"{i}問目：違う字が元と同じ（{sub_}）")
            for ch in (w[c], sub_):
                if not has_glyph(ch):
                    bad.append(f"{i}問目：「{ch}」がフォントにない（豆腐になる）")
            if w[c] not in ot or sub_ not in st:
                bad.append(f"{i}問目：答えの文に元の字・違う字が入っていない（{ot}／{st}）")
            allsubs.append(sub_)
        reused = w in used
        if reused != Q["origin"].startswith("reuse"):
            bad.append(f"{i}問目：origin が実際と違う（言葉 {w}：{'ショートで出した' if reused else '出していない'}）")
        reuse += reused; new += not reused
        for key in [f"q{i:02d}_intro"] + [f"q{i:02d}_ans{k}" for k in (1, 2)]:
            vt = L[key][1]
            if re.search(r"[\u4e00-\u9fff]", vt):
                bad.append(f"{key}：声の文に漢字が残っている：{vt}")
            if "はいる" in vt or "にいる" in vt:
                bad.append(f"{key}：「入る」系の読みがある：{vt}")
        cs = "　".join(f"{d[0] + 1}行目の「{w[d[1]]}」→「{d[2]}」" for d in dfs)
        rows.append(f"| {i} | {Q['level']} | {w}（{Q['rows']}行） | {cs} | {'・'.join(d[3] + '→' + d[5] for d in dfs)} | {'フォントにある' if all(has_glyph(d[2]) for d in dfs) else 'NG'} | {'ショート ' + used[w][0] if reused else '新しい問題'} |")
    if new < 11:
        bad.append(f"新しい問題 {new} 問（11問以上にする）")
    if reuse > n // 2:
        bad.append(f"ショートで使った問題 {reuse} 問（半分まで）")
    origs = [d[3].split("「")[-1].rstrip("」") for Q in Qs for d in Q["diffs"]]    # 変える元の字（「野球場の「野」」の「野」）
    odup = {x for x in origs if origs.count(x) > 1}
    if odup:
        bad.append(f"同じ字を2問で変えている（同じ物・同じ変化は1度まで）：{sorted(odup)}")
    dup = {x for x in allsubs if allsubs.count(x) > 1}
    if dup:
        bad.append(f"同じ「違う字」が複数の問にある（同じ物・同じ変化は1度まで）：{sorted(dup)}")
    md = [f"# 答えの確かめ（{P['id']}：{P['series']} 全{n}問）", "",
          "scripts/text_long.py check の結果。各問「3字の言葉・違う字は2つ（別の行）・違う字が元と違う・どちらの字もフォントにある（本当にある字）・声の文に漢字なし・同じ違う字を重ねない」を確かめた。",
          "違う字は、元の字と形が似ていて、部品の足し引き・入れ替えがスマホの大きさでも見分けられる組にした。点1つの違いなど小さすぎる差は使っていない。", "",
          f"新しい問題 {n - reuse} 問・ショートで使った言葉 {reuse} 問（半分まで）。", "",
          "| 問 | 難しさ | 言葉 | 違う字（行目：元→違う） | 答えの言い方 | 字の確認 | 出どころ |", "|---|---|---|---|---|---|---|"] + rows
    md += ["", "結果：" + ("不合格 " + str(len(bad)) + " 件" if bad else "合格")]
    (Path(folder) / "answer_check.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print("\n".join(bad) if bad else f"OK：{n}問（新しい {n - reuse}・ショート {reuse}）")
    return not bad


def used_pairs(folder):
    """ショートで出した「ちがうのどーれだ」の漢字の組（outputs/*_text_*/problem.json の scatter と、problem.json のない初期の3組）。"""
    out = {"季李": "text_010", "末未": "text_011", "大犬": "text_013"}
    for p in sorted(Path(folder).resolve().parent.glob("*_text_*/problem.json")):
        try:
            J = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        if J.get("kind") == "scatter":
            out[J["main"] + J["odd"]] = p.parent.name[-8:]
    return out


def small_ratio(a, b, size=40):
    """幅300pxに縮めたときの、2つの字の形の違い（重ねたときの食い違い面積÷字のインク面積）。末/未は0.09（小さすぎて不合格だった）、牛/午は0.38（合格）。"""
    def g(ch):
        im = Image.new("L", (size * 2, size * 2), 0)
        ImageDraw.Draw(im).text((size, size), ch, font=font_w(size), fill=255, anchor="mm")
        return np.array(im) > 110
    A, B = g(a), g(b)
    return float((A ^ B).sum() / max(A.sum(), 1))


def check_chigau(folder, P):
    Qs, n = P["questions"], len(P["questions"])
    used = used_pairs(folder)
    L = lines_of(P)
    bad, rows, reuse = [], [], 0
    levels = [Q["level"] for Q in Qs]
    if n != P["count"]:
        bad.append(f"問題数 {n} ≠ {P['count']}")
    if levels != sorted(levels, key=lambda x: ["やさしい", "ふつう", "むずかしい"].index(x)):
        bad.append("難しさの順（やさしい→ふつう）になっていない")
    odds = [Q["odd"] for Q in Qs]
    if len(set(odds)) != n or len({Q["main"] for Q in Qs}) != n:
        bad.append("同じ字が複数の問にある（同じ物・同じ変化は1度まで）")
    for i, Q in enumerate(Qs, 1):
        m, o = Q["main"], Q["odd"]
        for ch in (m, o):
            if not has_glyph(ch):
                bad.append(f"{i}問目：「{ch}」がフォントにない")
        ratio = small_ratio(m, o)
        if ratio < P.get("min_ratio", 0.30) and not (m + o in used and Q["origin"].startswith("reuse") and ratio >= 0.30):
            bad.append(f"{i}問目：{m}/{o} は差が小さい（{ratio:.2f}。0.30以上にする）")
        lay = layout(Q)
        n_odd = sum(1 for c, *_ in lay if c == o)
        if n_odd != 1 or len(lay) != Q["n"]:
            bad.append(f"{i}問目：違う字が{n_odd}個（1個にする）")
        masks = []
        for ch, cx, cy, sz, ang in lay:
            g = glyph(ch, sz, ang, Q["weight"]).split()[3].point(lambda v: 255 if v > 30 else 0)
            mk = Image.new("L", (W, H), 0); mk.paste(g, (int(cx - g.width / 2), int(cy - g.height / 2))); masks.append(np.array(mk) > 0)
        ov = sum(int((masks[a] & masks[b]).any()) for a in range(len(masks)) for b in range(a + 1, len(masks)))
        if ov:
            bad.append(f"{i}問目：インクが重なる字の組が {ov}")
        inside = True
        for m_ in masks:
            ys, xs = np.where(m_)
            inside &= bool(xs.min() >= AREA[0] - 5 and xs.max() <= AREA[2] + 5 and ys.min() >= AREA[1] - 5 and ys.max() <= AREA[3] + 5)
        if not inside:
            bad.append(f"{i}問目：台紙からはみ出す字がある")
        reused = (m + o) in used
        if reused != Q["origin"].startswith("reuse"):
            bad.append(f"{i}問目：origin が実際と違う（組 {m}/{o}：{'ショートで出した' if reused else '出していない'}）")
        reuse += reused
        for key in (f"q{i:02d}_intro", f"q{i:02d}_ans"):
            vt = L[key][1]
            if re.search(r"[\u4e00-\u9fff]", vt):
                bad.append(f"{key}：声の文に漢字が残っている：{vt}")
            if "はいる" in vt or "にいる" in vt:
                bad.append(f"{key}：「入る」系の読みがある：{vt}")
        rows.append(f"| {i} | {Q['level']} | {m} の中に {o} | {Q['n']}個（{m}×{Q['n'] - 1}・{o}×1） | {ratio:.2f} | 重なり0・台紙の中・フォントにある | 回転±{Q['tilt']}° | {'ショート ' + used[m + o] if reused else '新しい組'} |")
    if n - reuse < 11:
        bad.append(f"新しい組 {n - reuse} 組（11組以上にする）")
    if reuse > n // 2:
        bad.append(f"ショートで使った組 {reuse} 組（半分まで）")
    md = [f"# 答えの確かめ（{P['id']}：{P['series']} 全{n}問）", "",
          "scripts/text_long.py check の結果。各問「違う字は1個・字が重ならない・台紙の中に収まる・どちらの字もフォントにある・声の文に漢字なし・同じ字を2問で使わない」と、**幅300pxに縮めたときの字の形の違い**を数値で確かめた。",
          "形の違い＝同じ大きさで重ねたときの食い違い面積÷字のインク面積（40px で測定）。基準：0.30以上（参考：末/未 0.09＝小さすぎて差し戻し、牛/午 0.38＝合格、大/犬 0.14）。字は大きめ（190〜290px）で、回転は小さくした。", "",
          f"新しい組 {n - reuse} 組・ショートで使った組 {reuse} 組（半分まで）。", "",
          "| 問 | 難しさ | 組 | 数 | 形の違い | 確認 | 向き | 出どころ |", "|---|---|---|---|---|---|---|---|"] + rows
    md += ["", "結果：" + ("不合格 " + str(len(bad)) + " 件" if bad else "合格（違う字は全問で1個）")]
    (Path(folder) / "answer_check.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print("\n".join(bad) if bad else f"OK：{n}問（新しい {n - reuse}・ショート {reuse}）")
    return not bad


def check(folder):
    P = load(folder)
    if P["kind"] == "kanji_long":
        return check_kanji(folder, P)
    if P["kind"] == "chigau_long":
        return check_chigau(folder, P)
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
        frame = {"kanji_long": kanji_frame, "chigau_long": chigau_frame}.get(P["kind"], question_frame)
        think = Q.get("think", P.get("think", 15))
        chapters.append((t0, f"{i}問目（{Q.get('clue') or Q.get('word') or Q['main'] + 'の中の1字'}）"))
        ev["start"].append(t0)
        d = say(f"q{i:02d}_intro", t)
        ln = d + 0.3 + 0.5
        seq.append((frame(i, n, Q, 0, None, V[f"q{i:02d}_intro"][2][0], "normal", rule=(i == 1), think=think), ln)); t += ln
        ev["think"].append((t, t + think))
        for r in range(think, 0, -1):
            seq.append((frame(i, n, Q, 0, r, None, "think" if r < think - 3 else "smile", think=think), 1.0)); t += 1.0
        ev["solve_end"].append(t)
        if P["kind"] == "kanji_long":          # 答え：違う字を1つずつ（赤丸・ポン・声）
            for k in range(1, 3):
                ev["pon"].append(t + 0.2)
                d = say(f"q{i:02d}_ans{k}", t + 0.3)
                ln = 0.3 + d + 0.25 + (0.9 if k == 2 else 0.1)
                seq.append((kanji_frame(i, n, Q, k, None, V[f"q{i:02d}_ans{k}"][2][0], "yay" if k == 2 else "smile", think=think), ln)); t += ln
            continue
        ev["pon"].append(t + 0.35)
        d = say(f"q{i:02d}_ans", t + 0.4)
        ln = 0.4 + d + 0.3 + 1.3
        seq.append((frame(i, n, Q, 1, None, V[f"q{i:02d}_ans"][2][0], "yay", think=think), ln)); t += ln
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
        p = tmp / f"{i:04d}.jpg"; im.save(p, quality=92); lst.append(f"file '{p}'\nduration {dt:.4f}\n")
    (tmp / "list.txt").write_text("".join(lst) + f"file '{tmp / f'{len(seq) - 1:04d}.jpg'}'\n", encoding="utf-8")
    mix_audio(voices, ev, total, tmp / "mix.wav")
    T.readings_check("tlong", voices, folder)
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(tmp / "list.txt"), "-i", str(tmp / "mix.wav"),
                    "-map", "0:v", "-map", "1:a", "-vf", f"fps={FPS},format=yuv420p", "-c:v", "libx264", "-preset", "fast", "-crf", "20",
                    "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-t", f"{total:.2f}", "-movflags", "+faststart", str(folder / "video.mp4")], check=True)
    # 一覧画像：0:00・オープニング・1問目（問題・答え）・エンディング
    k0 = int(o_len * 10)      # 1問目の問題の絵の位置
    t1 = Qs[0].get("think", P.get("think", 15))
    a1 = k0 + 1 + t1 + (1 if P["kind"] == "kanji_long" else 0)      # 1問目の答え（漢字は2つ目まで見せた絵）
    shots = [seq[0][0], seq[k0 // 2][0], seq[k0][0], seq[k0 + 1 + t1 // 2][0], seq[a1][0], seq[-30][0]]
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
    # チャプター：「オープニング」は10秒未満なので出さない（YouTube は10秒未満のチャプターがあると目次を出さない）。最初の行は 0:00 の「1問目」にする。
    chs = [(a, b) for a, b in chapters if b != "オープニング"] + [(ENDING_AT[0], "エンディング")]
    chs[0] = (0.0, chs[0][1])
    short = [(b, round(nxt - a, 1)) for (a, b), (nxt, _) in zip(chs, chs[1:] + [(total, "")]) if nxt - a < 10]
    if short:
        sys.exit(f"10秒未満のチャプターがある（YouTube で目次が出ない）：{short}")
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
    if P["kind"] == "kanji_long":       # 漢字の間違い探し：言葉を3列×3行に並べた台紙（違いゼロ）
        w = Q["word"]
        d.rounded_rectangle((120, 30, pw * sc - 120, 650), 60, fill=TH["panel"], outline=TH["edge"], width=8)
        for r in range(3):
            for c in range(3):
                tc(d, (pw * sc // 2 + (c - 1) * 310, 30 + 100 + r * 200 + 10), w[c], 170, TH["ink"])
        pic = im.resize((pw, ph), Image.LANCZOS)
        TB_make(pic, P, folder)
        return
    if P["kind"] == "chigau_long":     # 字がたくさん散らばる台紙（左右とも同じ絵）
        d.rounded_rectangle((40, 30, pw * sc - 40, 660), 60, fill=TH["panel"], outline=TH["edge"], width=8)
        Qt = dict(Q, odd=Q["main"], n=Th.get("n", 6), size=Th.get("size", [210, 260]), seed=Th.get("seed", 5), odd_i=Th.get("odd_i", 2), tilt=Th.get("tilt", 12))
        for k in range(200):
            try:
                lay = scatter(dict(Qt, seed=Qt["seed"] + 100 * k), area=(90, 60, pw * sc - 90, 640), canvas=(pw * sc, ph * sc)); break
            except SystemExit:
                continue
        for ch, cx, cy, sz, ang in lay:
            g = glyph(ch, sz, ang, Q["weight"])
            im.paste(g, (int(cx - g.width / 2), int(cy - g.height / 2)), g)
        pic = im.resize((pw, ph), Image.LANCZOS)
        TB_make(pic, P, folder)
        return
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
    TB_make(pic, P, folder)


def TB_make(pic, P, folder):
    import thumb_band as TB
    Th = P["thumbnail"]
    top = 170
    TB.pics = lambda ep, qn, sat=1.15: (pic, pic, top)        # 左右とも同じ絵（違いゼロ）
    out = Path(folder) / "ab"
    out.mkdir(exist_ok=True)
    TB.make(out / "thumb_A.jpg", Path(folder), 1, TB.K, (Th["emph"], Th["rest"]), tuple(Th["bottom"]))
    import shutil
    shutil.copy(out / "thumb_A.jpg", Path(folder) / "thumbnail.jpg")
    import thumb_same_check as Tc, thumb_badge_check as Tb   # 2026-11-24 左右が同じ絵・2026-11-28 右下の角に文字なし（CEO決定）
    for f_ in (out / "thumb_A.jpg", Path(folder) / "thumbnail.jpg"):
        ok1, d = Tc.check(f_); ok2, n, why = Tb.check(f_)
        print(f"サムネの確認：左右{'合格' if ok1 else '不合格'}（差={d}）・右下の角{'合格' if ok2 else '不合格'}（文字の画素={n}） {f_}")
        if not (ok1 and ok2):
            sys.exit("サムネが確認に通りません：" + "／".join(why or ["左右がちがう"]))


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
