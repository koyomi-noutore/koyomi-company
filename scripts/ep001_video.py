"""第1回（001）の動画を組み立てる。PILでフレームを描き、ffmpeg（libx264）にパイプで渡す。4つに分けて並列に描き、最後につなぐ。
使い方:
  python3 scripts/ep001_video.py <成果物フォルダ> <作業フォルダ> <フォント.ttf> <音声.wav>
  成果物フォルダ：q1_a.png … q5_b.png、answers.json があること。作業フォルダ：koyomi_*.png（render_expressions.js）と voice/voice.json。
  単体のフレーム確認：python3 scripts/ep001_video.py --frame <秒> <成果物> <作業> <フォント> <出力.png>
答え合わせの赤丸・ヒントの位置は answers.json（= scripts/ep001_diffs.json）から計算する。
"""
import json, math, subprocess, sys
from functools import lru_cache
from multiprocessing import Pool
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter
sys.path.insert(0, str(Path(__file__).parent))
import ep001_timeline as T

W, H, FPS = 1920, 1080, 30
BG = (246, 236, 216)
INK = (59, 47, 37)
IW, IH, TOP, GAP = 940, 525, 110, 13
XS = [(W - 2 * IW - GAP) // 2, (W - 2 * IW - GAP) // 2 + IW + GAP]
OWL_SIZE, OWL_XY = 380, (W - 380 - 40, H - 380 - 10)
SUB_SIZE = 72                       # 字幕：画面の高さの6.7%
SUB_BOX = (24, 1480, 1046)          # 字幕の箱：左端・右端・下端（右下のこよみ先生と重ならない）
LEVEL_COLOR = {"初級": (96, 150, 90), "中級": (214, 128, 48), "上級": (176, 62, 52)}
LEVEL_STARS = {"初級": "★☆☆", "中級": "★★☆", "上級": "★★★"}
RED = (220, 30, 30)

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
    CTX["scale"] = IW / ans["image_size"][0], IH / ans["image_size"][1]
    CTX["voice"] = {v["id"]: v for v in json.loads((WORK / "voice" / "voice.json").read_text(encoding="utf-8"))}
    CTX["lines"] = T.lines()


# ---------- 部品 ----------
def ease(x):
    x = min(max(x, 0.0), 1.0)
    return 1 - (1 - x) ** 3


def text_center(d, xy, s, size, fill=INK, stroke=0, stroke_fill=None, anchor="mm"):
    d.text(xy, s, font=font(size), fill=fill, anchor=anchor, stroke_width=stroke, stroke_fill=stroke_fill)


@lru_cache(maxsize=8)
def picture(q, side):
    return Image.open(OUT / f"q{q}_{side}.png").convert("RGB").resize((IW, IH), Image.LANCZOS)


@lru_cache(maxsize=None)
def owl_img(face, angle_q):
    im = Image.open(WORK / "owl" / f"koyomi_{face}.png").convert("RGBA").resize((OWL_SIZE, OWL_SIZE), Image.LANCZOS)
    return im.rotate(angle_q / 4, resample=Image.BICUBIC, center=(OWL_SIZE / 2, OWL_SIZE * 0.85))


def face_events():
    ev = [(ln[1], ln[3]) for ln in CTX["lines"] if not ln[0].endswith("_card")]
    for q, s in T.Q_START.items():
        ev.append((s, T.QUESTIONS[q]["card_face"]))
        ev += [(s + 8.0, "think"), (s + T.CARD + T.HINT_AT + 7.0, "think"), (s + T.CARD + T.TEN_AT + 3.0, "think")]
    return sorted(ev)


def face_at(t):
    if "faces" not in CTX:
        CTX["faces"] = face_events()
    f = "smile"
    for t0, face in CTX["faces"]:
        if t0 <= t:
            f = face
        else:
            break
    return f


def draw_owl(im, t):
    face = face_at(t)
    if face in ("normal", "think") and (t % 4.1) < 0.14:  # まばたき
        face += "_blink"
    ang = 3.0 * math.sin(2 * math.pi * t / 3.2)          # ゆらゆら
    bob = int(round(6 * math.sin(2 * math.pi * t / 1.6)))
    o = owl_img(face, int(round(ang * 4)))
    im.paste(o, (OWL_XY[0], OWL_XY[1] + bob), o)


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
    if "subs" in CTX:
        return CTX["subs"]
    subs = []
    L = CTX["lines"]
    for i, (lid, t0, text, face, t_end) in enumerate(L):
        if lid.endswith("_card"):
            continue  # カードの文字がそのまま字幕の代わり
        dur = CTX["voice"][lid]["dur"]
        cs = chunks(text)
        total = sum(len(c) for c in cs)
        nxt = min([l[1] for l in L if l[1] > t0] + [T.TOTAL])
        tt = t0
        for j, c in enumerate(cs):
            d = dur * len(c) / total
            end = tt + d if j < len(cs) - 1 else min(t0 + dur + 0.8, nxt)
            subs.append((tt, end, c)); tt += d
    CTX["subs"] = subs
    return subs


@lru_cache(maxsize=256)
def sub_img(text):
    ls = wrap(text, 18)
    f = font(SUB_SIZE)
    lh = SUB_SIZE + 22
    wmax = max(f.getlength(l) for l in ls)
    bw, bh = int(wmax + 64), int(lh * len(ls) + 40)
    im = Image.new("RGBA", (bw, bh), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((0, 0, bw - 1, bh - 1), 22, fill=(52, 40, 30, 235), outline=(255, 248, 230, 255), width=4)
    for k, l in enumerate(ls):
        d.text((bw / 2, 20 + lh * k + lh / 2), l, font=f, fill=(255, 255, 255), anchor="mm")
    return im


def draw_subtitle(im, t):
    for t0, t1, c in subtitle_schedule():
        if t0 <= t < t1:
            s = sub_img(c)
            x0, x1, yb = SUB_BOX
            x = x0 + (x1 - x0 - s.width) // 2
            im.paste(s, (x, yb - s.height), s)
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


# ---------- 画面ごとの描画 ----------
@lru_cache(maxsize=8)
def question_base(q, guide=True):
    im = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(im)
    for x, side in zip(XS, "ab"):
        d.rounded_rectangle((x - 6, TOP - 6, x + IW + 6, TOP + IH + 6), 10, fill=(120, 90, 60))
        im.paste(picture(q, side), (x, TOP))
    Q = T.QUESTIONS[q]
    col = LEVEL_COLOR[Q["level"]]
    d.rounded_rectangle((20, 18, 250, 92), 37, fill=col)
    text_center(d, (135, 55), f"第{q}問", 54, fill=(255, 255, 255))
    text_center(d, (270, 55), f"{Q['level']}　{Q['scene']}", 54, anchor="lm")
    if guide:
        text_center(d, (24 + (1480 - 24) / 2, 700), "右の絵で、違いを3つ さがしましょう", 60, fill=(110, 84, 60))
    return im


def answer_boxes(q, side="b"):
    sx, sy = CTX["scale"]
    out = []
    for a in CTX["answers"][q]["answers"]:
        x0, y0, x1, y1 = a[f"circle_{side}_px"]
        out.append((x0 * sx, y0 * sy, x1 * sx, y1 * sy))
    return out


def draw_circle(d, x, box, num, k=1.0):
    x0, y0, x1, y1 = box
    cx, cy = x + (x0 + x1) / 2, TOP + (y0 + y1) / 2
    rx, ry = ((x1 - x0) / 2 + 10) * k, ((y1 - y0) / 2 + 10) * k
    d.ellipse((cx - rx - 3, cy - ry - 3, cx + rx + 3, cy + ry + 3), outline=(255, 255, 255), width=14)
    d.ellipse((cx - rx, cy - ry, cx + rx, cy + ry), outline=RED, width=8)
    bx, by = cx - rx * 0.71 - 4, cy - ry * 0.71 - 4
    bx, by = max(x + 26, bx), max(TOP + 26, by)
    d.ellipse((bx - 24, by - 24, bx + 24, by + 24), fill=RED, outline=(255, 255, 255), width=3)
    d.text((bx, by + 1), str(num), font=font(34), fill=(255, 255, 255), anchor="mm")


def ans_times(q):
    return [ln[1] for ln in CTX["lines"] if ln[0].startswith(f"q{q}_ans") and not ln[0].endswith("ans0")]


def render_question(q, t):
    s = T.Q_START[q]
    st = s + T.CARD
    im = question_base(q, t < st + T.SOLVE).copy()
    d = ImageDraw.Draw(im)
    if t < st + T.SOLVE:
        el = t - st
        rem = max(0.0, T.SOLVE - el)
        x0, x1, y0, y1 = 760, 1760, 36, 76
        d.rounded_rectangle((x0, y0, x1, y1), 20, fill=(225, 212, 188), outline=(150, 120, 90), width=3)
        frac = rem / T.SOLVE
        col = (96, 160, 90) if rem > 30 else (226, 150, 40) if rem > 10 else (214, 60, 50)
        if frac > 0:
            d.rounded_rectangle((x0 + 4, y0 + 4, x0 + 4 + (x1 - x0 - 8) * frac, y1 - 4), 16, fill=col)
        num = math.ceil(rem - 1e-6)
        big = rem <= 10 and (rem % 1) > 0.6
        text_center(d, (1840, 56), f"{num}", 70 if big else 60, fill=(214, 60, 50) if rem <= 10 else INK)
        # 45秒のヒント：違い（hint_diff）のある辺りを、広めの光の輪でそっと示す
        h0 = st + T.HINT_AT
        if h0 <= t < h0 + 7.0:
            draw_hint(im, q, t - h0)
    else:
        text_center(d, (1290, 56), "答え合わせ", 60, fill=RED)
        times = ans_times(q)
        for x, side in zip(XS, "ab"):
            for i, (ta, b) in enumerate(zip(times, answer_boxes(q, side))):
                if t >= ta:
                    k = 1.0 + 0.35 * (1 - ease((t - ta) / 0.3))
                    draw_circle(d, x, b, i + 1, k)
    return im


def draw_hint(im, q, dt):
    Q = CTX["answers"][q]
    b = answer_boxes(q)[Q["hint_diff"] - 1]
    cx, cy = XS[1] + (b[0] + b[2]) / 2, TOP + (b[1] + b[3]) / 2
    r = max(b[2] - b[0], b[3] - b[1]) * 1.0 + 70
    a = min(1.0, dt / 0.6, (7.0 - dt) / 0.8) * (0.75 + 0.25 * math.sin(dt * 5))
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ld = ImageDraw.Draw(layer)
    ld.ellipse((cx - r, cy - r, cx + r, cy + r), outline=(255, 214, 60, int(230 * a)), width=16)
    layer = layer.filter(ImageFilter.GaussianBlur(5))
    im.paste(layer, (0, 0), layer)


@lru_cache(maxsize=8)
def card_img(q):
    Q = T.QUESTIONS[q]
    col = LEVEL_COLOR[Q["level"]]
    im = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((330, 150, 1590, 830), 60, fill=(255, 250, 238), outline=col, width=16)
    text_center(d, (960, 320), f"第{q}問", 190, fill=col)
    text_center(d, (960, 530), f"{Q['level']}　{LEVEL_STARS[Q['level']]}", 120)
    text_center(d, (960, 710), Q["scene"], 120)
    return im


def render_card(q, t):
    s = T.Q_START[q]
    dt = t - s
    prev = CTX.setdefault(("prev", q), None)
    if prev is None:
        prev = CTX[("prev", q)] = render_base(s - 1 / FPS)
    if dt < 2.6:
        off = int((1 - ease(dt / 0.45)) * W)
        im = prev.copy()
        im.paste(card_img(q).crop((0, 0, W - off, H)), (off, 0))
    else:
        k = ease((dt - 2.6) / 0.4)
        im = Image.blend(card_img(q), render_question(q, t), k)
    return im


@lru_cache(maxsize=1)
def opening_base():
    im = Image.new("RGB", (W, H), BG)
    thumbs = [picture(q, "a").resize((360, 201), Image.LANCZOS) for q in range(1, 6)]
    x = (W - (5 * 360 + 4 * 16)) // 2
    for k, th in enumerate(thumbs):
        th = Image.blend(Image.new("RGB", th.size, BG), th, 0.55)
        im.paste(th, (x + k * 376, 430))
    d = ImageDraw.Draw(im)
    text_center(d, (960, 200), "秋の間違い探し　5問", 130, stroke=6, stroke_fill=(255, 250, 238))
    text_center(d, (960, 340), "こよみ先生のまいにち脳トレ", 60, fill=(150, 90, 50))
    return im


@lru_cache(maxsize=1)
def rule_base():
    im = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(im)
    for x, label in zip(XS, ("左の絵", "右の絵")):
        d.rounded_rectangle((x - 6, TOP - 6, x + IW + 6, TOP + IH + 6), 10, fill=(120, 90, 60))
        d.rectangle((x, TOP, x + IW, TOP + IH), fill=(255, 250, 238))
        text_center(d, (x + IW / 2, TOP + 120), label, 90)
    text_center(d, (XS[1] + IW / 2, TOP + 300), "違いは 3つ", 110, fill=RED)
    text_center(d, (XS[0] + IW / 2, TOP + 300), "くらべて みよう", 80, fill=(110, 84, 60))
    d.rounded_rectangle((760, 36, 1760, 76), 20, fill=(96, 160, 90))
    text_center(d, (1840, 56), "90", 60)
    text_center(d, (380, 56), "1問 90秒", 60, fill=INK)
    return im


def render_unchiku(t):
    u = T.UNCHIKU[0]
    im = Image.new("RGB", (W, H), (250, 240, 222))
    d = ImageDraw.Draw(im)
    leaves(d, t)
    text_center(d, (300, 70), "こよみ先生の 秋の小話", 56, fill=(150, 90, 50), anchor="lm")
    dt = t - u
    if dt < 4:
        text_center(d, (760, 400), "秋の小話", 170, fill=(180, 70, 40), stroke=6, stroke_fill=(255, 250, 238))
    elif dt < 15:
        text_center(d, (760, 400), "もみつ　→　もみじ", 150, stroke=6, stroke_fill=(255, 250, 238))
        text_center(d, (760, 560), "（葉の色が変わる）", 70, fill=(110, 84, 60))
    elif dt < 23:
        text_center(d, (760, 250), "もみち", 80, fill=(180, 70, 40))
        text_center(d, (760, 430), "黄葉", 240, fill=(200, 150, 20), stroke=8, stroke_fill=(255, 250, 238))
        text_center(d, (760, 650), "万葉集のころ", 70, fill=(110, 84, 60))
    else:
        text_center(d, (760, 400), "黄葉　→　紅葉", 160, stroke=6, stroke_fill=(255, 250, 238))
        text_center(d, (760, 570), "平安時代から", 70, fill=(110, 84, 60))
    return im


def render_ending(t):
    im = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(im)
    dt = t - T.ENDING[0]
    if dt < 4.5:
        leaves(d, t, n=40, seed=7, colors=((214, 80, 50), (232, 176, 48), (96, 150, 90), (90, 120, 200)))
        text_center(d, (760, 380), "おつかれさまでした", 130, stroke=6, stroke_fill=(255, 250, 238))
        text_center(d, (760, 540), "5問 おしまい", 90, fill=(180, 70, 40))
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
            text_center(d, (610, y + 110), "次回も 秋の絵で 5問", 60, fill=(150, 90, 50))
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


def render_base(t):
    seg = segment_of(t)
    if seg[0] == "op":
        im = opening_base().copy(); leaves(ImageDraw.Draw(im), t, n=12)
    elif seg[0] == "rule":
        im = rule_base().copy()
    elif seg[0] == "unchiku":
        im = render_unchiku(t)
    elif seg[0] == "end":
        im = render_ending(t)
    elif seg[0] == "card":
        return render_card(seg[1], t)
    else:
        im = render_question(seg[1], t)
    return im


def render(t):
    im = render_base(t)
    draw_subtitle(im, t)
    draw_owl(im, t)
    return im


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


if __name__ == "__main__":
    if sys.argv[1] == "--frame":
        t, out, work, fontp, png = float(sys.argv[2]), *sys.argv[3:7]
        setup(out, work, fontp)
        render(t).save(png)
    else:
        main(*sys.argv[1:5])
