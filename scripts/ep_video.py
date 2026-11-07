"""動画を組み立てる（make_episode.py から呼ぶ）。PILでフレームを描き、ffmpeg（libx264）にパイプで渡す。4つに分けて並列に描き、最後につなぐ。
画面のつくり（knowledge/concept.md 2026-11-06）：
  - 出題中・答え合わせ中は、左右の絵（各960×1080）で画面いっぱい。上の端に細い帯（約5%）、セリフがある間だけ下の端に字幕。
    この間、こよみ先生の絵は出さない（声だけ）。
  - こよみ先生（6表情・ゆらゆら・まばたき）は、オープニング・うんちく・エンディングだけに出す（ルール説明にも出さない）。
画面の文字（オープニングの題・うんちくの画面・称号）は plan.json の screens から読む。
答え合わせの赤丸・ヒントの位置は answers.json（= plan.json の diffs）から計算する。
"""
import json, math, subprocess, sys
from functools import lru_cache
from multiprocessing import Pool
from pathlib import Path
from PIL import Image, ImageChops, ImageDraw, ImageFont, ImageFilter
sys.path.insert(0, str(Path(__file__).parent))
import ep_timeline as T
from episode_plan import plan

W, H, FPS = 1920, 1080, 30
BG = (246, 236, 216)
INK = (59, 47, 37)
PW, PH = 960, 1080                  # 絵1枚の大きさ（画面の半分）
XS = [0, 960]                       # 左の絵・右の絵の左端
BAND_H = 54                         # 上の帯（画面の高さの5%）
SUB_SIZE = 68                       # 字幕の文字の高さ（画面の高さの6.3%）
OWL_SIZE = 420
LEVEL_COLOR = {"初級": (96, 150, 90), "中級": (214, 128, 48), "上級": (176, 62, 52)}
LEVEL_STARS = {"初級": "★☆☆", "中級": "★★☆", "上級": "★★★"}
RED = (220, 30, 30)
OWL_SEGMENTS = ("op", "unchiku", "end")   # こよみ先生の絵を出す場面

OUT = WORK = FONT = None
CTX = {}


def font(size):
    return _font(FONT, size)


@lru_cache(maxsize=64)
def _font(path, size):
    return ImageFont.truetype(path, size)


def setup(out, work, fontp):
    global OUT, WORK, FONT
    OUT, WORK, FONT = Path(out), Path(work), str(fontp)
    ans = json.loads((OUT / "answers.json").read_text(encoding="utf-8"))
    CTX["answers"] = {Q["q"]: Q for Q in ans["questions"]}
    CTX["voice"] = {v["id"]: v for v in json.loads((WORK / "voice" / "voice.json").read_text(encoding="utf-8"))}
    CTX["lines"] = T.lines()


def ease(x):
    x = min(max(x, 0.0), 1.0)
    return 1 - (1 - x) ** 3


def text_center(d, xy, s, size, fill=INK, stroke=0, stroke_fill=None, anchor="mm"):
    d.text(xy, s, font=font(size), fill=fill, anchor=anchor, stroke_width=stroke, stroke_fill=stroke_fill)


@lru_cache(maxsize=12)
def picture(q, side):
    """8:9 の高解像度の絵（1856×2088）を 960×1080 に縮める（引き伸ばしはしない）。"""
    im = Image.open(OUT / f"q{q}_{side}.png").convert("RGB").crop(tuple(CTX["answers"][q]["content_px"]))
    assert im.width >= PW and im.height >= PH, "絵が画面の大きさより小さい"
    return im.resize((PW, PH), Image.LANCZOS)


# ---------- こよみ先生（オープニング・うんちく・エンディングだけ） ----------
@lru_cache(maxsize=None)
def owl_img(face, angle_q):
    im = Image.open(WORK / "owl" / f"koyomi_{face}.png").convert("RGBA").resize((OWL_SIZE, OWL_SIZE), Image.LANCZOS)
    return im.rotate(angle_q / 4, resample=Image.BICUBIC, center=(OWL_SIZE / 2, OWL_SIZE * 0.85))


def face_at(t):
    if "faces" not in CTX:
        CTX["faces"] = sorted((ln[1], ln[3]) for ln in CTX["lines"] if ln[0][0] in "oue")
    f = "smile"
    for t0, face in CTX["faces"]:
        if t0 <= t:
            f = face
        else:
            break
    return f


def draw_owl(im, t, xy):
    face = face_at(t)
    if face in ("normal", "think") and (t % 4.1) < 0.14:   # まばたき
        face += "_blink"
    ang = 3.0 * math.sin(2 * math.pi * t / 3.2)             # ゆらゆら
    bob = int(round(6 * math.sin(2 * math.pi * t / 1.6)))
    o = owl_img(face, int(round(ang * 4)))
    im.paste(o, (xy[0], xy[1] + bob), o)


# ---------- 字幕 ----------
PUNCT = "、。」）！？"


def wrap(s, maxc):
    """2行に分けられるなら、読点（、）か「の前で、なるべく同じ長さに分ける。だめなら字数で折り返す。"""
    if len(s) <= maxc + (1 if s[-1:] in PUNCT else 0):
        return [s]
    best = None
    for k in range(1, len(s)):
        if s[k - 1] == "、" or s[k] == "「":
            a, b = s[:k], s[k:]
            if len(a) <= maxc + 1 and len(b) <= maxc + 1:
                sc = max(len(a), len(b))
                if best is None or sc < best[0]:
                    best = (sc, [a, b])
    if best:
        return best[1]
    # 読点で分けられないときは、助詞（が・は・を・に・の・と）の後ろで分ける（ことばの途中で切らない）
    for k in range(1, len(s)):
        if s[k - 1] in "がはをにのと" and s[k] not in PUNCT:
            a, b = s[:k], s[k:]
            if len(a) <= maxc + 1 and len(b) <= maxc + 1:
                sc = max(len(a), len(b))
                if best is None or sc < best[0]:
                    best = (sc, [a, b])
    if best:
        return best[1]
    lines, cur = [], ""
    for ch in s:
        if len(cur) >= maxc and ch not in PUNCT:
            lines.append(cur); cur = ""
        cur += ch
    if cur:
        lines.append(cur)
    return lines


def chunks(text, maxc=18):
    """1行18字以内・2行以内のかたまりに分ける。"""
    sents = [x + "。" for x in text.split("。") if x]
    out = []
    for s in sents:
        if len(wrap(s, maxc)) <= 2:
            out.append(s); continue
        parts, cur = [], ""
        for p in [x + "、" for x in s.split("、")]:
            if cur and len(wrap(cur + p, maxc)) > 2:
                parts.append(cur); cur = ""
            cur += p
        parts.append(cur)
        out += [x.rstrip("、") if x.endswith("。、") else x for x in parts]
    return [c[:-1] if c.endswith("。、") else c for c in out]


def subtitle_schedule():
    """セリフがある間だけ出す字幕の表。難易度カードの読み上げは、カードの字が字幕の代わり。"""
    if "subs" in CTX:
        return CTX["subs"]
    subs = []
    L = CTX["lines"]
    for lid, t0, text, face, t_end in L:
        if lid.endswith("_card"):
            continue
        dur = CTX["voice"][lid]["dur"]
        cs = chunks(text)
        total = sum(len(c) for c in cs)
        nxt = min([l[1] for l in L if l[1] > t0] + [T.TOTAL])
        tt = t0
        for j, c in enumerate(cs):
            d = dur * len(c) / total
            end = tt + d if j < len(cs) - 1 else min(t0 + dur + 0.6, nxt)
            subs.append((tt, end, c)); tt += d
    CTX["subs"] = subs
    return subs


@lru_cache(maxsize=256)
def sub_img(text, maxc):
    ls = wrap(text, maxc)
    f = font(SUB_SIZE)
    lh = SUB_SIZE + 16
    wmax = max(f.getlength(l) for l in ls)
    bw, bh = int(wmax + 60), int(lh * len(ls) + 26)
    im = Image.new("RGBA", (bw, bh), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((0, 0, bw - 1, bh - 1), 20, fill=(52, 40, 30, 235), outline=(255, 248, 230, 255), width=4)
    for k, l in enumerate(ls):
        d.text((bw / 2, 13 + lh * k + lh / 2), l, font=f, fill=(255, 255, 255), anchor="mm")
    return im


def draw_subtitle(im, t, area):
    """area＝(左端, 右端, 下端)。出題・答え合わせでは画面の下の端（下15%の中）に出す。"""
    for t0, t1, c in subtitle_schedule():
        if t0 <= t < t1:
            x0, x1, yb = area
            s = sub_img(c, int((x1 - x0 - 80) / (SUB_SIZE * 1.02)))   # 字幕の箱が area からはみ出さない字数で折り返す
            im.paste(s, (x0 + (x1 - x0 - s.width) // 2, yb - s.height), s)
            return


# ---------- 落ち葉（オープニング・うんちく・エンディング） ----------
def leaves(d, t, n=18, seed=3, colors=((214, 80, 50), (232, 176, 48), (200, 110, 40))):
    import random
    r = random.Random(seed)
    for i in range(n):
        x0, sp, ph, sz = r.uniform(0, W), r.uniform(40, 80), r.uniform(0, 100), r.uniform(18, 34)
        c = colors[i % len(colors)]
        y = ((t + ph) * sp) % (H + 100) - 50
        x = x0 + 40 * math.sin((t + ph) * 0.9)
        a = (t + ph) * 1.3
        pts = [(x + sz * math.cos(a + k * math.pi / 2.5) * (1 if k % 2 == 0 else 0.45),
                y + sz * math.sin(a + k * math.pi / 2.5) * (1 if k % 2 == 0 else 0.45)) for k in range(5)]
        d.polygon(pts, fill=c)


# ---------- 出題・答え合わせ（画面いっぱい） ----------
@lru_cache(maxsize=10)
def question_base(q):
    im = Image.new("RGB", (W, H), BG)
    for x, side in zip(XS, "ab"):
        im.paste(picture(q, side), (x, 0))
    d = ImageDraw.Draw(im)
    d.line((W // 2, 0, W // 2, H), fill=(255, 250, 238), width=4)   # 左右の絵の境目
    return im


def draw_band(im, q, t, mode):
    """上の端の細い帯（高さ54px＝5%）。半透明で、絵をなるべく隠さない。"""
    Q = T.QUESTIONS[q]
    layer = Image.new("RGBA", (W, BAND_H), (52, 40, 30, 165))
    d = ImageDraw.Draw(layer)
    col = LEVEL_COLOR[Q["level"]]
    d.rounded_rectangle((10, 7, 150, BAND_H - 7), 18, fill=col + (255,))
    d.text((80, BAND_H // 2), f"第{q}問", font=font(34), fill=(255, 255, 255), anchor="mm")
    d.text((168, BAND_H // 2), f"{Q['level']}　{Q['scene']}", font=font(34), fill=(255, 255, 255), anchor="lm")
    if mode == "solve":
        rem = max(0.0, T.SOLVE - (t - T.Q_START[q] - T.CARD))
        bx0, bx1, by0, by1 = 1100, 1790, 15, BAND_H - 15
        d.rounded_rectangle((bx0, by0, bx1, by1), 12, fill=(225, 212, 188, 230))
        frac = rem / T.SOLVE
        c = (110, 180, 100) if rem > 30 else (236, 170, 50) if rem > 10 else (230, 70, 60)
        if frac > 0:
            d.rounded_rectangle((bx0 + 3, by0 + 3, bx0 + 3 + (bx1 - bx0 - 6) * frac, by1 - 3), 9, fill=c + (255,))
        num = math.ceil(rem - 1e-6)
        d.text((1855, BAND_H // 2), f"{num}", font=font(42 if rem <= 10 and (rem % 1) > 0.6 else 36),
               fill=(255, 120, 100) if rem <= 10 else (255, 255, 255), anchor="mm")
    else:
        d.text((W - 30, BAND_H // 2), "答え合わせ", font=font(36), fill=(255, 210, 120), anchor="rm")
    im.paste(layer, (0, 0), layer)


def answer_boxes(q, side="b"):
    """絵の上での、赤丸の範囲（絵の左上からの画面の座標）。answers.json の circle_a_screen / circle_b_screen。"""
    return [tuple(a[f"circle_{side}_screen"]) for a in CTX["answers"][q]["answers"]]


def circle_geom(x, box, k=1.0):
    x0, y0, x1, y1 = box
    cx, cy = x + (x0 + x1) / 2, (y0 + y1) / 2
    rx, ry = ((x1 - x0) / 2 + 8) * k, ((y1 - y0) / 2 + 8) * k
    return cx, cy, rx, ry


def draw_circle(d, x, box, k=1.0):
    cx, cy, rx, ry = circle_geom(x, box, k)
    d.ellipse((cx - rx - 3, cy - ry - 3, cx + rx + 3, cy + ry + 3), outline=(255, 255, 255), width=12)
    d.ellipse((cx - rx, cy - ry, cx + rx, cy + ry), outline=RED, width=7)


def badge_pos(x, box, others, k=1.0):
    """番号札の位置。赤丸の左上・右上・右下・左下の順に試し、ほかの答えの範囲（赤丸の中）に重ならない所を選ぶ
    （第1回作り直し版の監査：③の札が②の赤丸の中の物を隠した）。絵の中に収める。"""
    cx, cy, rx, ry = circle_geom(x, box, k)
    best = None
    for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
        bx = min(max(x + 26, cx + sx * (rx * 0.71 + 4)), x + PW - 26)
        by = min(max(BAND_H + 26, cy + sy * (ry * 0.71 + 4)), int(H * 0.85) - 26)
        hit = sum(1 for (ox0, oy0, ox1, oy1) in others
                  if ox0 - 26 < bx - x < ox1 + 26 and oy0 - 26 < by < oy1 + 26)
        if best is None or hit < best[0]:
            best = (hit, bx, by)
        if hit == 0:
            break
    return best[1], best[2]


def draw_badge(d, x, box, num, k=1.0, others=()):
    """番号札。赤丸の線に隠れないよう、赤丸を全部描いたあとに描く（第1回の監査の指摘）。"""
    bx, by = badge_pos(x, box, others, k)
    d.ellipse((bx - 24, by - 24, bx + 24, by + 24), fill=RED, outline=(255, 255, 255), width=3)
    d.text((bx, by + 1), str(num), font=font(34), fill=(255, 255, 255), anchor="mm")


def ans_times(q):
    return [ln[1] for ln in CTX["lines"] if ln[0].startswith(f"q{q}_ans") and not ln[0].endswith("ans0")]


def draw_hint(im, q, dt):
    """45秒のヒント：違いのある辺りを、右の絵の中だけで、うっすら光る輪でそっと示す（7秒）。"""
    Q = CTX["answers"][q]
    b = answer_boxes(q)[Q["hint_diff"] - 1]
    cx, cy = XS[1] + (b[0] + b[2]) / 2, (b[1] + b[3]) / 2
    rx, ry = (b[2] - b[0]) / 2 * 1.2 + 30, (b[3] - b[1]) / 2 * 1.2 + 30
    a = min(1.0, dt / 0.8, (7.0 - dt) / 1.0) * (0.7 + 0.3 * math.sin(dt * 4))
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ld = ImageDraw.Draw(layer)
    ld.ellipse((cx - rx, cy - ry, cx + rx, cy + ry), outline=(255, 214, 60, int(230 * a)), width=12)
    layer = layer.filter(ImageFilter.GaussianBlur(3))
    clip = Image.new("L", (W, H), 0)
    ImageDraw.Draw(clip).rectangle((XS[1] + 2, BAND_H, W - 1, H - 1), fill=255)
    layer.putalpha(ImageChops.multiply(layer.getchannel("A"), clip))
    im.paste(layer, (0, 0), layer)


def render_question(q, t):
    st = T.Q_START[q] + T.CARD
    im = question_base(q).copy()
    if t < st + T.SOLVE:
        h0 = None if T.HINT_AT is None or not T.QUESTIONS[q]["hint"] else st + T.HINT_AT
        if h0 is not None and h0 <= t < h0 + 7.0:
            draw_hint(im, q, t - h0)
        draw_band(im, q, t, "solve")
    else:
        d = ImageDraw.Draw(im)
        shown = []
        for x, side in zip(XS, "ab"):
            for i, (ta, b) in enumerate(zip(ans_times(q), answer_boxes(q, side))):
                if t >= ta:
                    shown.append((x, b, i + 1, 1.0 + 0.35 * (1 - ease((t - ta) / 0.3))))
        for x, b, n, k in shown:     # 先に赤丸を全部
            draw_circle(d, x, b, k)
        for x, b, n, k in shown:     # 最後に番号札（ほかの答えの範囲を避ける）
            others = [ob for (ox, ob, on, _) in shown if ox == x and on != n]
            draw_badge(d, x, b, n, k, others)
        draw_band(im, q, t, "answer")
    draw_subtitle(im, t, (20, W - 20, H - 14))
    return im


@lru_cache(maxsize=8)
def card_img(q):
    Q = T.QUESTIONS[q]
    col = LEVEL_COLOR[Q["level"]]
    im = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((340, 170, 1580, 850), 60, fill=(255, 250, 238), outline=col, width=16)
    text_center(d, (960, 340), f"第{q}問", 190, fill=col)
    text_center(d, (960, 550), f"{Q['level']}　{LEVEL_STARS[Q['level']]}", 120)
    text_center(d, (960, 730), Q["scene"], 120)
    return im


def render_card(q, t):
    """難易度カード：右からスライドして入り、最後の0.4秒で出題画面へフェード。"""
    s = T.Q_START[q]
    dt = t - s
    key = ("prev", q)
    if key not in CTX:
        CTX[key] = render(s - 1 / FPS)
    if dt < 2.6:
        off = int((1 - ease(dt / 0.45)) * W)
        im = CTX[key].copy()
        im.paste(card_img(q).crop((0, 0, W - off, H)), (off, 0))
        return im
    return Image.blend(card_img(q), render_question(q, t), ease((dt - 2.6) / 0.4))


# ---------- オープニング・ルール説明・うんちく・エンディング ----------
@lru_cache(maxsize=1)
def opening_base():
    im = Image.new("RGB", (W, H), BG)
    thumbs = [picture(q, "a").resize((216, 243), Image.LANCZOS) for q in range(1, 6)]
    x = 60
    for k, th in enumerate(thumbs):
        th = Image.blend(Image.new("RGB", th.size, BG), th, 0.6)
        im.paste(th, (x + k * 236, 560))
    d = ImageDraw.Draw(im)
    SC = plan()["screens"]
    text_center(d, (650, 230), SC["opening_title"], 120, stroke=6, stroke_fill=(255, 250, 238))
    text_center(d, (650, 380), SC["opening_sub"], 58, fill=(150, 90, 50))
    return im


@lru_cache(maxsize=1)
def rule_base():
    """ルール説明：左右に絵の枠。こよみ先生は出さない（concept.md の登場場面にないため）。"""
    im = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(im)
    for x, label in zip(XS, ("左の絵", "右の絵")):
        d.rounded_rectangle((x + 40, 60, x + PW - 40, 840), 24, fill=(255, 250, 238), outline=(150, 115, 80), width=6)
        text_center(d, (x + PW / 2, 200), label, 100)
    text_center(d, (XS[0] + PW / 2, 480), "くらべて みよう", 84, fill=(110, 84, 60))
    text_center(d, (XS[1] + PW / 2, 430), "違いは 3つ", 120, fill=RED)
    text_center(d, (XS[1] + PW / 2, 640), "1問 90秒", 100, fill=INK)
    return im


def render_unchiku(t):
    u = T.UNCHIKU[0]
    im = Image.new("RGB", (W, H), (250, 240, 222))
    d = ImageDraw.Draw(im)
    leaves(d, t)
    SC = plan()["screens"]
    text_center(d, (80, 80), SC["unchiku_header"], 56, fill=(150, 90, 50), anchor="lm")
    dt = t - u
    # うんちくの画面：plan.json の screens.unchiku_slides。until（うんちくの頭からの秒）までその画面を出す
    slide = next((x for x in SC["unchiku_slides"] if dt < x["until"]), SC["unchiku_slides"][-1])
    for text, x, y, size, col, stroke in slide["texts"]:
        text_center(d, (x, y), text, size, fill=tuple(col), stroke=stroke, stroke_fill=(255, 250, 238) if stroke else None)
    if slide.get("maple"):
        mx, my, mr, mc = slide["maple"]
        draw_maple(d, mx, my, mr, tuple(mc))
    draw_subtitle(im, t, (20, 1400, H - 24))
    draw_owl(im, t, (W - OWL_SIZE - 40, H - OWL_SIZE - 30))
    return im


def draw_maple(d, cx, cy, r, col):
    """かえでの葉（5つに分かれた形）を簡単に描く。"""
    pts = []
    for k in range(10):
        a = -math.pi / 2 + k * math.pi / 5
        rr = r if k % 2 == 0 else r * 0.45
        pts.append((cx + rr * math.cos(a), cy + rr * math.sin(a) * 0.95))
    d.polygon(pts, fill=col, outline=(120, 30, 25))
    d.line((cx, cy, cx, cy + r * 1.1), fill=(120, 30, 25), width=6)


def render_opening(t):
    im = opening_base().copy()
    leaves(ImageDraw.Draw(im), t, n=12)
    draw_subtitle(im, t, (20, 1400, H - 24))
    draw_owl(im, t, (W - OWL_SIZE - 60, 140))
    return im


def render_rule(t):
    im = rule_base().copy()
    draw_subtitle(im, t, (20, W - 20, H - 24))
    return im


def render_ending(t):
    im = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(im)
    dt = t - T.ENDING[0]
    if dt < 4.5:
        leaves(d, t, n=40, seed=7, colors=((214, 80, 50), (232, 176, 48), (96, 150, 90), (90, 120, 200)))
        text_center(d, (700, 380), "おつかれさまでした", 130, stroke=6, stroke_fill=(255, 250, 238))
        text_center(d, (700, 540), f"{len(T.QUESTIONS)}問 おしまい", 90, fill=(180, 70, 40))
    else:
        text_center(d, (420, 80), "今日の称号", 80, fill=(180, 70, 40))
        y = 170
        for i, (cnt, name) in enumerate(T.TITLES):
            d.rounded_rectangle((60, y, 1160, y + 100), 24, fill=(255, 250, 238), outline=(180, 140, 100), width=4)
            text_center(d, (110, y + 50), cnt, 60, anchor="lm")
            text_center(d, (520, y + 50), name, 68, fill=(180, 70, 40) if i == 0 else INK, anchor="lm")
            y += 118
        text_center(d, (610, y + 30), T.TITLE_NOTE, 50, fill=(110, 84, 60))
        if dt >= 11.5:
            text_center(d, (610, y + 110), plan()["screens"]["ending_next"], 60, fill=(150, 90, 50))
    draw_subtitle(im, t, (20, 1400, H - 24))
    draw_owl(im, t, (W - OWL_SIZE - 40, H - OWL_SIZE - 60))
    return im


def segment_of(t):
    if t < T.OPENING[1]:
        return ("op",)
    if t < T.RULE[1]:
        return ("rule",)
    if T.UNCHIKU[0] <= t < T.UNCHIKU[1]:
        return ("unchiku",)
    if t >= T.ENDING[0]:
        return ("end",)
    for q, s in T.Q_START.items():
        if s <= t < s + T.CARD + T.SOLVE + T.ANSWER:
            return ("card", q) if t < s + T.CARD else ("q", q)
    raise ValueError(t)


def render(t):
    seg = segment_of(t)
    return {"op": lambda: render_opening(t), "rule": lambda: render_rule(t), "unchiku": lambda: render_unchiku(t),
            "end": lambda: render_ending(t), "card": lambda: render_card(seg[1], t),
            "q": lambda: render_question(seg[1], t)}[seg[0]]()


def encode_part(args):
    out, work, fontp, f0, f1, path = args
    setup(out, work, fontp)
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
           "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-tune", "animation", "-pix_fmt", "yuv420p",
           "-threads", "2", "-g", "60", path]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for i in range(f0, f1):
        p.stdin.write(render(i / FPS).tobytes())
    p.stdin.close()
    assert p.wait() == 0
    return path


def main(out, work, fontp, audio):
    n = int(T.TOTAL * FPS)
    parts = 4
    bounds = [n * k // parts for k in range(parts + 1)]
    paths = [str(Path(work) / f"part{k}.mp4") for k in range(parts)]
    with Pool(parts) as pool:
        pool.map(encode_part, [(out, work, fontp, bounds[k], bounds[k + 1], paths[k]) for k in range(parts)])
    lst = Path(work) / "parts.txt"
    lst.write_text("".join(f"file '{p}'\n" for p in paths))
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(lst), "-i", audio,
                    "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
                    "-movflags", "+faststart", "-shortest", str(Path(out) / "video.mp4")], check=True)


def frame(t, out, work, fontp, png):
    setup(out, work, fontp)
    render(t).save(png)
