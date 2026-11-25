"""「文字の脳トレ」ショートの試作（2026-11-20 CEO指示）。画像APIを使わず、文字だけをプログラムで描く。共通のプログラムは使わない（新しいファイルだけ）。

使い方：python3 scripts/text_shorts.py <出力フォルダ> [種類 ...]   種類＝pref・cross・kanji（省略で全部）
出力：<出力>/<種類>.mp4（縦1080×1920・30fps）と <種類>_frames.jpg（場面ごとの一覧）。
2026-11-21 CEO：声（こよみ先生・ですます調）・左下にこよみ先生と吹き出し・最後は「左下をクリックしてほかの脳トレにも挑戦」＋矢印。

画面の流れ（どの種類も同じ）：
  0〜4秒   暗い幕の上に問題文（大きな文字）。下の絵（問題）はうっすら見える ＝ 0:00 の画面がそのままサムネになる
  考える時間 問題＋のこり秒数＋「わかったら 画面を2回タップしてね」
  答え     答えを1つずつ出す（黄色）
  最後     暗い幕の上に「ほかの脳トレにも挑戦！ 左下をクリック」と矢印（関連動画のリンクへ）
文字の場所は、スマホでボタンや題名に隠れない範囲（knowledge/shorts.md：左右36px・上120px・下のタイトルの帯を避け、文字の幅は800px以内）。
"""
import subprocess, sys

from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).parent))
import os
os.environ.setdefault("KOYOMI_EPISODE_DIR", str(Path(__file__).resolve().parent.parent / "outputs/2026-11-23_012"))   # 声の設定（こよみ先生の声・速さ）と音の部品を第12回の台本から借りる

W, H, FPS = 1080, 1920, 30
FONT = Path.home() / ".cache/koyomi/fonts/package/900Black/NotoSansJP_900Black.ttf"
# 色は scripts/season_theme.json の季節の色から読む（2026-11-24 夜 CEO厳守：ショートの背景は長尺と同じ季節の色。紺の決め打ちはやめた）。
# 季節は set_season(season) か、問題の problem.json の "season"、または --season で決める（--season が最優先）。どれも無ければ「冬」（winter_A）。
# 呼ぶ側（chigau_shorts.py・mushimegane_shorts.py）が T.BG・T.CARD・T.INK・T.RED・T.ACCENT を今までの名前で読めるように、名前は変えていない。
BG = CARD = INK = RED = SEASON_ACCENT = EDGE = HIT = None
THEME_NAME = ""
SEASON_ARG = None           # コマンドラインで指定された季節（あれば problem.json の season より優先）
ACCENT = (255, 205, 40)     # 暗い幕（VEIL）の上の強調の黄色。幕は季節によらず暗いので、この色は季節で変えない
VEIL = 0.62                 # 暗い幕の濃さ


def set_season(season=None, theme=None):
    """季節の色（背景・カード・文字・赤など）を入れ替える。BG＝背景、CARD＝パネル、INK＝文字、RED＝答えの丸・のこり少ない秒数、
    SEASON_ACCENT＝見出し・吹き出しの枠、EDGE＝カードの縁、HIT＝答えの欄の塗り。"""
    global BG, CARD, INK, RED, SEASON_ACCENT, EDGE, HIT, THEME_NAME
    from season_pick import pick
    THEME_NAME, t = pick(season, theme)
    BG, CARD, INK, RED, SEASON_ACCENT, EDGE, HIT = (t[k] for k in ("bg", "panel", "ink", "alert", "accent", "edge", "hit"))
    return THEME_NAME


set_season()
X0, X1 = 90, 990            # 中身を置く横の範囲（左右の端・右のボタンを避ける）
Y_TOP, Y_BOTTOM = 230, 1500  # 中身を置く縦の範囲（上120px・下のタイトルの帯を避ける）


def f(size):
    return ImageFont.truetype(str(FONT), size)


def text_c(d, xy, s, size, fill, stroke=0, stroke_fill=None):
    d.text(xy, s, font=f(size), fill=fill, anchor="mm", stroke_width=stroke, stroke_fill=stroke_fill)


def fit(d, s, size, maxw=800):
    while d.textlength(s, font=f(size)) > maxw and size > 30:
        size -= 4
    return size


def veil(im, lines, gap=1.35):
    """暗い幕＋大きな文字（行ごとに [文字, 大きさ, 色]）。gap＝行の高さ（文字の大きさの何倍か）。"""
    v = Image.blend(im, Image.new("RGB", im.size, (0, 0, 0)), VEIL)
    d = ImageDraw.Draw(v)
    total = sum(int(sz * gap) for _, sz, _ in lines)
    y = 900 - total // 2
    for s, sz, col in lines:
        sz = fit(d, s, sz)
        y += int(sz * gap) // 2
        text_c(d, (W // 2, y), s, sz, col, stroke=6, stroke_fill=(0, 0, 0))
        y += int(sz * gap) // 2
    return v


INTRO_GAP = 1.5          # 最初の画面の行の高さ（2026-11-25 CEO：行間も広げる）
INTRO_MAX, INTRO_CHARS, INTRO_HEIGHT = 170, 7, 1150   # 1行の大きさの上限・1行の字数の目安・全体の高さの上限


PARTICLES = "はがをにのでともや"
PUNCT = "？！。、」』）"


def _atoms(s):
    """行を、切ってよい所で区切った塊にする。各塊は (文字, 前の塊と空白・読点で分かれていたか)。"""
    import re
    out = []
    for ti, chunk in enumerate([x for x in re.split(r"[ \u3000、]+", s.strip()) if x]):
        cur, first = "", True
        for i, ch in enumerate(chunk):
            cur += ch
            nxt = chunk[i + 1] if i + 1 < len(chunk) else ""
            hira_next = "\u3040" <= nxt <= "\u309f"
            kana_run = len(re.search(r"[\u3040-\u309f]*$", cur).group(0))
            cut = nxt and ((ch in "？！") or (ch in PARTICLES and not hira_next and nxt not in PUNCT)
                           or (kana_run >= 4 and "\u4e00" <= nxt <= "\u9fff"))      # 4字以上のひらがな（あてはまる）のあと、漢字が続くとき
            if cut:
                out.append((cur, first and ti > 0)); cur, first = "", False
        if cur:
            out.append((cur, first and ti > 0))
    return out


def _split_line(s):
    """（互換）1つの入力行を、言葉の途中で切らずに行に分ける。_split_rows の1行版。"""
    return _split_rows([s])


def _split_rows(texts):
    """入力の行（texts）を、言葉の途中で切らずに、出力の行 [(文字, 何番目の入力行か)] にする（2026-11-25 監査R-1）。
    切ってよい所：空白・読点、「？」「！」のあと、助詞（は・が・を・に・の・で・と・も・や）のあと（助詞のあとにひらがなが続くときは言葉の途中なので切らない）、
    4字以上のひらがなのあとに漢字が続く所（あてはまる｜漢字は？）。1行 INTRO_CHARS 字までに詰め、1〜2字だけの行は前（なければ次）の行につなぐ（入力の行をまたいでもよい）。
    切れる所がなければ1行のまま（小さくなる）。空白で分けた塊をつなぐときは、空白を1つ残す。"""
    rows = []   # [文字, 入力行の番号]
    for ti, t in enumerate(texts):
        mine = []
        for a, sp in _atoms(t):
            pure = lambda x: x.replace(" ", "")
            if mine and len(pure(mine[-1])) + len(pure(a)) <= INTRO_CHARS:
                mine[-1] += (" " if sp else "") + a
            else:
                mine.append(a)
        rows += [[m, ti] for m in mine]
    k = 0
    while k < len(rows) and len(rows) > 1:
        if len(rows[k][0].replace(" ", "")) <= 2:
            if k > 0:
                rows[k - 1][0] += rows.pop(k)[0]; k -= 1
            else:
                rows[1][0] = rows[0][0] + rows[1][0]; rows.pop(0)
            continue
        k += 1
    return rows


def intro_lines(texts, explicit=False):
    """最初の画面（0:00＝サムネ）の文字の行と大きさ。
    自動（explicit=False）：texts＝入力の行。長い行は _split_line で言葉の切れ目で分け、1行ごとに幅800pxに収まる最大の大きさ（上限170px）にし、
      1画面の中の大きさは、いちばん小さい行の1.2倍までにそろえる。最後の入力行は黄色、ほかは白。全体が高すぎるときはまとめて小さくする。
    作る人が行を書く（explicit=True。problem.json の "intro_lines"）：texts の各要素は "行" か ["行", "accent"]（黄色）。そのとおりの行で、
      幅800pxに収まる最大の大きさ。100px未満になる行があれば、理由を出して止まる。"""
    d = ImageDraw.Draw(Image.new("RGB", (10, 10)))
    rows = []
    if explicit:
        for t in texts:
            txt, col = (t, "white") if isinstance(t, str) else (t[0], t[1] if len(t) > 1 else "white")
            sz = fit(d, txt, INTRO_MAX, 800)
            if sz < 100:
                raise SystemExit(f"intro_lines の「{txt}」が長すぎる（{len(txt)}字。幅800pxだと{sz}px）。100px以上にするため、1行7〜8字までに分けて書き直す")
            rows.append([txt, ACCENT if col == "accent" else (255, 255, 255), sz])
        sizes = [r[2] for r in rows]
    else:
        for part, i in _split_rows(texts):
            rows.append([part, (255, 255, 255) if i < len(texts) - 1 or len(texts) == 1 else ACCENT])
        sizes = [fit(d, r[0], INTRO_MAX, 800) for r in rows]
        cap = round(min(sizes) * 1.2)
        sizes = [min(sz, cap) for sz in sizes]
    tot = sum(sz * INTRO_GAP for sz in sizes)
    if tot > INTRO_HEIGHT:
        sizes = [int(sz * INTRO_HEIGHT / tot) for sz in sizes]
    return [(r[0], sz, r[1]) for r, sz in zip(rows, sizes)]


def intro_from_cfg(cfg):
    """その問題の最初の画面の行。cfg に "intro_lines" があればそれを使い、なければ "veil" を自動で分ける。"""
    return intro_lines(cfg["intro_lines"], explicit=True) if cfg.get("intro_lines") else intro_lines(cfg["veil"])


def header(d, title, sub=None):
    sz = fit(d, title, 84)
    text_c(d, (W // 2, 300), title, sz, INK)
    if sub:
        text_c(d, (W // 2, 395), sub, fit(d, sub, 54), SEASON_ACCENT)


def footer(d, remain=None, tap=True):
    if remain is not None:
        d.rounded_rectangle((W // 2 - 160, 1360, W // 2 + 160, 1450), 40, fill=CARD, outline=EDGE, width=4)
        text_c(d, (W // 2, 1405), f"のこり {remain}", 56, RED if remain <= 3 else INK)
    if tap:
        text_c(d, (W // 2, 1500), "わかったら 画面を2回タップしてね", fit(d, "わかったら 画面を2回タップしてね", 50), INK)


# ---------- ① 都道府県の穴埋め ----------
PREF = {"title": "「は行」で始まる 都道府県", "sub": "□にあてはまる漢字は？",
        "items": [("□□道", "北海道"), ("□庫県", "兵庫県"), ("□井県", "福井県")],
        "think": 12, "veil": ["「は行」の都道府県", "□の漢字は？"]}


def pref_frame(state, remain=None):
    im = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(im)
    header(d, PREF["title"], PREF["sub"])
    for i, it in enumerate(PREF["items"]):
        q, a = it[0], it[1]
        label = it[2] if len(it) > 2 else None   # 2026-11-23：「宮城県の県庁所在地」のような見出し（なければ今までどおり）
        y = 640 + i * 270
        d.rounded_rectangle((X0 + 30, y - 120, X1 - 30, y + 120), 40, fill=CARD, outline=EDGE, width=4)
        if label:
            text_c(d, (W // 2, y - 80), label, fit(d, label, 46, 700), INK)
        shown = a if i < state else q
        step = min(200, 740 // len(shown))
        size = 170 if not label else min(150, step - 20)
        cy = y if not label else y + 28
        x = W // 2 - (len(shown) * step) // 2 + step // 2
        for k, ch in enumerate(shown):
            cx = x + k * step
            if ch == "□":
                hb = size // 2 - 10
                d.rounded_rectangle((cx - hb, cy - hb, cx + hb, cy + hb), 16, outline=RED, width=10)
            else:
                hit = i < state and q[k] == "□"
                text_c(d, (cx, cy), ch, size, RED if hit else INK)
    return im


# ---------- ② ひらがな十字（真ん中に入る1文字） ----------
CROSS = {"across": "さ□な", "down": "あ□り", "answer": "か", "think": 17,
         "veil": ["真ん中の□に", "あてはまる", "ひらがなは？"]}


def cross_frame(state, remain=None):
    im = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(im)
    header(d, "□にあてはまる ひらがなは？", "たて・よこ どちらも 言葉になります")
    cs, cx, cy = 290, W // 2, 860
    cells = [(-1, 0, CROSS["across"][0]), (1, 0, CROSS["across"][2]), (0, -1, CROSS["down"][0]), (0, 1, CROSS["down"][2]), (0, 0, "□")]
    for dx, dy, ch in cells:
        x, y = cx + dx * cs, cy + dy * cs
        d.rounded_rectangle((x - cs // 2 + 8, y - cs // 2 + 8, x + cs // 2 - 8, y + cs // 2 - 8), 30,
                            fill=HIT if (ch == "□" and state) else CARD, outline=EDGE, width=4)
        if ch == "□":
            if state:
                text_c(d, (x, y), CROSS["answer"], 210, RED)
            else:
                d.rounded_rectangle((x - 90, y - 90, x + 90, y + 90), 16, outline=RED, width=10)
        else:
            text_c(d, (x, y), ch, 210, INK)
    return im


# ---------- ③ 漢字の間違い探し（左右、違いは2つ） ----------
KANJI = {"word": "姫路城", "rows": 6, "diffs": {(2, 2): "域", (5, 1): "略"}, "think": 19,
         "veil": ["左右で違う", "漢字を", "2つ探そう"]}


def kanji_frame(state, remain=None):
    im = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(im)
    header(d, "左と右で ちがう漢字は？", "ちがいは 2つ")
    cw, ch = 132, 138
    panels = [(W // 2 - 430, False), (W // 2 + 10, True)]
    for px, right in panels:
        pw = cw * 3 + 20
        d.rounded_rectangle((px, 450, px + pw, 450 + KANJI["rows"] * ch + 30), 24, fill=CARD, outline=EDGE, width=4)
        for r in range(KANJI["rows"]):
            for c in range(3):
                s = KANJI["diffs"].get((r, c), KANJI["word"][c]) if right else KANJI["word"][c]
                x, y = px + 10 + cw * c + cw // 2, 465 + ch * r + ch // 2
                text_c(d, (x, y), s, 116, INK)
                if right and (r, c) in KANJI["diffs"] and state > list(KANJI["diffs"]).index((r, c)):
                    d.ellipse((x - 76, y - 76, x + 76, y + 76), outline=RED, width=10)
    return im


# ---------- 声（こよみ先生・ですます調）。字幕＝吹き出しの文、声＝ひらがなにした文 ----------
LINES = {
    "pref": {"intro": ("「は行」の都道府県です。□にあてはまる漢字は？",
                       "はぎょうの、とどうふけんです。しかくにあてはまるかんじは？"),
             "ans": [("北海道です。", "ほっかいどうです。"), ("兵庫県です。", "ひょうごけんです。"), ("福井県です。", "ふくいけんです。")]},
    "cross": {"intro": ("真ん中にあてはまる、ひらがなは？",
                        "まんなかにあてはまる、ひらがなは？"),
              "ans": [("答えは「か」です。さかなと、あかりです。", "こたえは、かです。さかなと、あかりです。")]},
    "kanji": {"intro": ("違う漢字が、2つあります。",
                        "ちがうかんじが、ふたつあります。"),
              "ans": [("3行目、お城の「城」が、区域の「域」に。", "さんぎょうめ、おしろの、しろが、くいきの、いきに。"), ("6行目、路地の「路」が、省略の「略」になっていました。", "ろくぎょうめ、ろじの、ろが、しょうりゃくの、りゃくに、なっていました。")]},
}
TAP = ("わかったら、画面を2回タップしてね。", "わかったら、がめんを、にかいタップしてね。")
TAP_REMAIN = 10     # 2026-11-25 CEO：「2回タップ」の呼びかけは出題中（考える時間の残りが約10秒のとき）に出す


TAP_EARLY = 2.0   # 2026-11-25 CEO：「2回タップ」の声の開始を2秒早く（ep_short.tap_at も同じ）


def tap_offset(think, dur):
    """考える時間（think 秒）の初めから数えて、「2回タップ」の声を始める秒。残りが約 TAP_REMAIN 秒のとき。考える時間が短い（14秒より短い）ときは真ん中。
    ただし声が、残り5〜1秒のカウント音（ピッ）にかからないように、残り5.5秒より前に終わらせる。"""
    off = think - TAP_REMAIN if think >= TAP_REMAIN + 4 else think / 2
    return max(0.5, min(off, think - 5.5 - dur) - TAP_EARLY)   # 2026-11-25 CEO：2回タップの声は2秒早く


def tap_window(off, dur, i, step=1.0):
    """出題中の吹き出し：その秒（i〜i+step）が、声の間（off〜off+dur＋少し）にかかるか。"""
    return i + step > off and i < off + dur + 0.3
ANS0 = ("答えです。", "こたえです。")
CTA = ("左下をクリックして、ほかの脳トレにも挑戦してくださいね。", "ひだりしたをクリックして、ほかののうトレにも、ちょうせんしてくださいね。")
WORK = Path.home() / ".cache/koyomi/text_shorts"
OWL_XY, OWL_S = (40, 1300), 240             # こよみ先生：左下の余白（クイズの大きさ・形は変えない）
BUBBLE = (300, 1325, 890, 1530)             # 吹き出し（右のボタン x900〜 にかからない）


def owl(face):
    d = WORK / "owl"
    if not (d / "koyomi_normal.png").exists():
        d.mkdir(parents=True, exist_ok=True)
        subprocess.run(["node", str(Path(__file__).parent / "render_expressions.js"), str(d), "480"], check=True)
    return Image.open(d / f"koyomi_{face}.png").convert("RGBA").resize((OWL_S, OWL_S), Image.LANCZOS)


def wrap(d, s, size, maxw):
    out, cur = [], ""
    for ch in s:
        if d.textlength(cur + ch, font=f(size)) > maxw and cur and ch not in "、。」』）！？":   # 句読点は行の頭に置かない
            out.append(cur); cur = ch
        else:
            cur += ch
    return out + [cur] if cur else out


def speaker(im, face, sub=None):
    """左下にこよみ先生、右に吹き出し（今話している文）。"""
    o = owl(face); im.paste(o, OWL_XY, o)
    if sub:
        d = ImageDraw.Draw(im)
        x0, y0, x1, y1 = BUBBLE
        d.rounded_rectangle(BUBBLE, 30, fill=(255, 255, 255), outline=SEASON_ACCENT, width=5)
        d.polygon([(x0 + 2, y0 + 80), (x0 - 34, y0 + 110), (x0 + 2, y0 + 125)], fill=(255, 255, 255))
        d.line([(x0 + 2, y0 + 80), (x0 - 34, y0 + 110), (x0 + 2, y0 + 125)], fill=SEASON_ACCENT, width=5)
        sz = 46
        ls = wrap(d, sub, sz, x1 - x0 - 50)
        while len(ls) > 3:
            sz -= 4; ls = wrap(d, sub, sz, x1 - x0 - 50)
        y = (y0 + y1) / 2 - (len(ls) - 1) * sz * 0.65
        for l in ls:
            d.text((x0 + 25, y), l, font=f(sz), fill=INK, anchor="lm"); y += sz * 1.3
    return im


def timer(im, remain):
    d = ImageDraw.Draw(im)
    cx, cy, r = 955, 185, 52
    d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=CARD, outline=RED if remain <= 3 else SEASON_ACCENT, width=6)
    text_c(d, (cx, cy), str(remain), 56, RED if remain <= 3 else INK)
    return im


def arrow(im, t):
    """左下の関連動画のリンクを指す矢印（間違いさがしのショートと同じ形・動き）。"""
    import math
    from ep_short import LINK_XY
    d2 = ImageDraw.Draw(im)
    wig = 14 * math.sin(2 * math.pi * t / 1.0)
    tx, ty = LINK_XY[0] + 50 + wig * 0.7, LINK_XY[1] - 40 + wig * 0.7
    sx, sy = 560, 1280
    ang = math.atan2(ty - sy, tx - sx)
    hx, hy = tx - 90 * math.cos(ang), ty - 90 * math.sin(ang)
    px, py = -math.sin(ang), math.cos(ang)
    for wdt, col in ((46, (255, 255, 255)), (30, (230, 60, 30))):
        d2.line((sx, sy, hx, hy), fill=col, width=wdt)
        e = wdt / 30
        d2.polygon([(tx + 8 * (e - 1) * math.cos(ang), ty + 8 * (e - 1) * math.sin(ang)),
                    (hx + 54 * e * px, hy + 54 * e * py), (hx - 54 * e * px, hy - 54 * e * py)], fill=col)
    return im


PROBLEM_ID = ""      # 問題ごとに声の保管場所を分ける（同じ種類の別の問題と上書きしない）


def voice(kind, key, vt):
    """声は Fish Audio（第12回と同じ こよみ先生の声・速さ）。同じ文はもう一度作らない（別の問題で作った同じ文の声は使い回す）。"""
    import hashlib, json, os, shutil, wave
    vd = WORK / (f"voice_{PROBLEM_ID}" if PROBLEM_ID else "voice"); vd.mkdir(parents=True, exist_ok=True)
    pool = WORK / "voice_pool"; pool.mkdir(parents=True, exist_ok=True)
    wav, meta = vd / f"{kind}_{key}.wav", vd / f"{kind}_{key}.json"
    from ep_timeline import BAD_SPLITS
    bad = [b for b in BAD_SPLITS if b in vt]
    if bad:   # 2026-11-22：「にはいる」が「には・いる」と読まれた。声を作る前に止める
        raise SystemExit(f"声に渡す文に {bad} がある（{kind}/{key}：{vt}）。「あてはまる」に言い換える")
    if not (wav.exists() and meta.exists() and json.loads(meta.read_text(encoding="utf-8"))["voice_text"] == vt):
        pw = pool / (hashlib.sha1(vt.encode("utf-8")).hexdigest()[:16] + ".wav")
        if pw.exists():
            shutil.copy(pw, wav)
        else:
            os.environ.setdefault("KOYOMI_EPISODE_DIR", str(Path(__file__).resolve().parent.parent / "outputs/2026-11-23_012"))
            import ep_voice as V
            V.tts_line(vt, wav)
            shutil.copy(wav, pw)
        meta.write_text(json.dumps({"voice_text": vt}, ensure_ascii=False), encoding="utf-8")
    with wave.open(str(wav)) as w:
        return wav, w.getnframes() / w.getframerate()


KINDS = {"pref": (PREF, pref_frame, len(PREF["items"])), "cross": (CROSS, cross_frame, 1), "kanji": (KANJI, kanji_frame, 2)}


def mix_audio(voices, ev, total, path):
    """音は間違い探しのショート（scripts/ep_short.py の audio）と同じ部品・同じ鳴らし方（2026-11-21 CEO：新しい音は足さない）。
    0秒のピンポン、BGM（考える時間は0.7倍）、残り5〜1秒のカウント音、答えの前のチャイム、答えごとのポン、最後のチャイム。
    声はセリフごとに大きさをそろえ、話している間はBGMを下げる。"""
    import wave
    import numpy as np
    import ep_audio as A
    from ep_short import VOICE_RMS_DB
    SR = A.SR
    n = int(total * SR); tt = np.arange(n) / SR

    def put(track, x, at):
        s0 = int(at * SR); e = min(n, s0 + len(x)); track[s0:e] += x[:e - s0]
    vo = np.zeros(n)
    for w, at, _, _ in voices:
        x = A.read_wav(w)
        x = x * (10 ** (VOICE_RMS_DB / 20) / (np.sqrt(np.mean(x[np.abs(x) > 0.01] ** 2)) + 1e-9))
        put(vo, np.clip(x, -0.9, 0.9), at)
    vo *= 0.6 / max(np.abs(vo).max(), 1e-9)
    sfx = np.zeros(n)
    put(sfx, A.chime((79, 84, 88), 0.18), 0.0)
    for k in range(5):
        put(sfx, A.tick(), ev["solve_end"] - 5 + k)
    put(sfx, A.chime((84, 79), 0.25), ev["solve_end"])
    for at in ev.get("pon", []):
        put(sfx, A.pon(), at)
    put(sfx, A.chime((84, 88), 0.25, 0.16), ev["end_at"])
    music = A.bgm()
    music = np.tile(music, int(np.ceil(n / len(music))))[:n]
    from scipy.ndimage import uniform_filter1d   # np.convolve の移動平均は遅い（2026-11-22）。同じ移動平均を速く計算する
    act = uniform_filter1d((np.abs(vo) > 0.01).astype(float), int(0.3 * SR), mode="constant") > 0.02
    duck = uniform_filter1d(np.where(act, 0.45, 1.0), int(0.15 * SR), mode="nearest")
    gain = np.where(tt < ev["solve_end"], 0.7, 1.0)
    fade = np.clip(np.minimum(tt / 0.3, (total - tt) / 1.5), 0, 1)
    mix = vo + sfx + music * gain * duck * fade
    mix *= min(1.0, 0.95 / np.abs(mix).max())
    st = np.repeat((mix * 32767).astype(np.int16)[:, None], 2, axis=1)
    with wave.open(str(path), "wb") as wv:
        wv.setnchannels(2); wv.setsampwidth(2); wv.setframerate(SR); wv.writeframes(st.tobytes())


def readings_check(kind, voices, out):
    """字幕の文と、声に渡した文の対照表（漢字が残っていないかも書く）。"""
    import re
    p = out / "readings_check.md"
    head = "# 読みの対照表（字幕の文 → 声に渡した文）\n\n漢字が声の文に残っていたら「漢字あり」。声の文はひらがなとカタカナだけにする。\n"
    txt = p.read_text(encoding="utf-8") if p.exists() else head
    txt = re.sub(rf"\n## {kind}\n.*?(?=\n## |\Z)", "", txt, flags=re.S)
    rows = [f"\n## {kind}\n| セリフ | 字幕 | 声に渡した文 | 確認 |\n|---|---|---|---|"]
    for _, at, key, (sub, vt) in voices:
        bad = re.findall(r"[\u4e00-\u9fff]", vt)
        rows.append(f"| {key}（{at:.1f}秒） | {sub} | {vt} | {'漢字あり：' + ''.join(bad) if bad else 'OK'} |")
    p.write_text(txt.rstrip() + "\n" + "\n".join(rows) + "\n", encoding="utf-8")


def build(kind, out):
    cfg, frame, n_ans = KINDS[kind]
    L = LINES[kind]
    seq, voices, t = [], [], 0.0     # seq：(画像, 秒)、voices：(声のファイル, 開始秒)

    ev = {}                          # 効果音の時刻（間違い探しのショートと同じ鳴らし方）

    def say(key, line):
        w, dur = voice(kind, key, line[1]); voices.append((w, t + 0.3, key, line)); return dur + 0.3

    # 1. 暗い幕＋問題文（0:00 から出ている＝サムネ）
    d_intro = say("intro", L["intro"])
    vl = intro_from_cfg(cfg)     # 2026-11-25 CEO：文字を大きく・行間を広く。最初の画面は吹き出しを出さない（サムネ。こよみ先生は今の位置のまま）
    seq.append((speaker(veil(frame(0), vl, INTRO_GAP), "normal", None), max(4.0, d_intro + 0.4))); t += seq[-1][1]
    # 2. 考える時間（右上にのこり秒数）。はじめに「わかったら2回タップ」
    w_tap, d_tap = voice(kind, "tap", TAP[1])     # 出題中（残り約10秒）に、声と吹き出しで「わかったら、画面を2回タップしてね」
    off_tap = tap_offset(cfg["think"], d_tap)
    voices.append((w_tap, t + off_tap, "tap", TAP))
    for s_ in range(cfg["think"], 0, -1):
        i_ = cfg["think"] - s_
        seq.append((timer(speaker(frame(0), "think" if s_ < cfg["think"] - 3 else "smile", TAP[0] if tap_window(off_tap, d_tap, i_) else None), s_), 1.0)); t += 1.0
    # 3. 答え
    ev["solve_end"] = t
    d0 = say("ans0", ANS0)
    seq.append((speaker(frame(0), "surprise", ANS0[0]), max(1.5, d0 + 0.2))); t += seq[-1][1]
    per = max(1, len(L["ans"]) // n_ans) if n_ans >= len(L["ans"]) else 1
    for k in range(1, n_ans + 1):
        line = L["ans"][min(k - 1, len(L["ans"]) - 1)] if n_ans == len(L["ans"]) else (L["ans"][0] if k == 1 else None)
        ev.setdefault("pon", []).append(t + 0.3)
        dk = say(f"ans{k}", line) if line else 0
        last = k == n_ans
        seq.append((speaker(frame(k), "yay" if last else "smile", line[0] if line else L["ans"][0][0]), max(2.5, dk + 0.4) + (1.0 if last else 0))); t += seq[-1][1]
    # 4. 最後の2段（2026-11-23 CEO・共通）：①コメントの呼びかけ → ②「左下をクリック」＋矢印。共通の部品 scripts/short_outro.py を使う
    ev["end_at"] = t
    answer_img = seq[-1][0]
    from short_outro import build_outro

    def say_outro(key, line, off):
        w, dur = voice(kind, key, line[1]); voices.append((w, t + off + 0.3, key, line)); return dur + 0.1

    base = frame(n_ans)
    outro, length = build_outro(base, say_outro, veil, speaker, arrow, comment="text")
    seq.extend(outro)
    t += length
    total = t
    tmp = out / f"_{kind}"; tmp.mkdir(parents=True, exist_ok=True)
    lst = []
    for i, (im, dt) in enumerate(seq):
        p = tmp / f"{i:03d}.png"; im.save(p); lst.append(f"file '{p}'\nduration {dt}\n")
    (tmp / "list.txt").write_text("".join(lst) + f"file '{tmp / f'{len(seq) - 1:03d}.png'}'\n", encoding="utf-8")
    mix_wav = tmp / "mix.wav"
    mix_audio(voices, ev, total, mix_wav)
    readings_check(kind, voices, out)
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(tmp / "list.txt"), "-i", str(mix_wav),
                    "-map", "0:v", "-map", "1:a", "-vf", f"fps={FPS},format=yuv420p",
                    "-c:v", "libx264", "-crf", "20", "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-t", f"{total:.2f}",
                    "-movflags", "+faststart", str(out / f"{kind}.mp4")], check=True)
    # 一覧画像：0:00・問題（考える時間）・答え・最後の2段（コメント／左下をクリック）
    n_out = len(outro)
    shots = [seq[0][0], seq[2][0], answer_img, outro[0][0], outro[n_out // 2][0]]
    S = Image.new("RGB", (len(shots) * 270, 480))
    for i, im_ in enumerate(shots):
        S.paste(im_.resize((270, 480)), (i * 270, 0))
    S.save(out / f"{kind}_frames.jpg", quality=85)
    for p in tmp.iterdir():
        p.unlink()
    tmp.rmdir()
    return round(total, 1)


def load_problem(path):
    """問題の定義（problem.json）を読み、その種類の設定を差し替える。形は outputs/2026-11-23_text_004/problem.json を見る。"""
    import json
    global PROBLEM_ID
    P = json.loads(Path(path).read_text(encoding="utf-8"))
    kind = P["kind"]
    PROBLEM_ID = P["id"]
    if (P.get("season") or P.get("theme")) and not SEASON_ARG:    # 問題に季節が書いてあれば、その季節の色（--season があればそちらが先。どちらも無ければ冬のまま）
        set_season(P.get("season"), P.get("theme"))
    cfg = KINDS[kind][0]
    for k in ("title", "sub", "think", "veil", "intro_lines", "across", "down", "answer", "word", "rows"):
        if k in P:
            cfg[k] = P[k]
    if "items" in P:
        cfg["items"] = [tuple(x) for x in P["items"]]
    if "diffs" in P:
        cfg["diffs"] = {(r, c): ch for r, c, ch in P["diffs"]}
    LINES[kind] = {"intro": tuple(P["lines"]["intro"]), "ans": [tuple(x) for x in P["lines"]["ans"]]}
    return kind


def take_season(argv):
    """コマンドラインの `--season 冬`（季節またはテーマ名）を取り除いて、その季節の色にする。なければ何もしない。"""
    global SEASON_ARG
    if "--season" in argv:
        i = argv.index("--season")
        SEASON_ARG = argv[i + 1]
        del argv[i:i + 2]
        set_season(SEASON_ARG)
    return SEASON_ARG


if __name__ == "__main__":
    take_season(sys.argv)
    out = Path(sys.argv[1]).resolve(); out.mkdir(parents=True, exist_ok=True)
    args = sys.argv[2:]
    if args and args[0].endswith(".json"):          # 問題の定義から作る：<出力フォルダ> <problem.json>
        k = load_problem(args[0])
        print(k, build(k, out), "秒")
    else:
        for k in (args or list(KINDS)):
            print(k, build(k, out), "秒")
