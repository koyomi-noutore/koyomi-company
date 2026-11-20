"""「文字の脳トレ」ショートの試作（2026-11-20 CEO指示）。画像APIを使わず、文字だけをプログラムで描く。共通のプログラムは使わない（新しいファイルだけ）。

使い方：python3 scripts/text_shorts.py <出力フォルダ> [種類 ...]   種類＝pref・cross・kanji（省略で全部）
出力：<出力>/<種類>.mp4（縦1080×1920・30fps・音は無音）と <種類>_frames.jpg（場面ごとの一覧）。試作なので声は付けない（CEO 11/20）。

画面の流れ（どの種類も同じ）：
  0〜4秒   暗い幕の上に問題文（大きな文字）。下の絵（問題）はうっすら見える ＝ 0:00 の画面がそのままサムネになる
  考える時間 問題＋のこり秒数＋「わかったら 画面を2回タップしてね」
  答え     答えを1つずつ出す（黄色）
  最後     暗い幕の上に「答えはコメントでも教えてね」
文字の場所は、スマホでボタンや題名に隠れない範囲（knowledge/shorts.md：左右36px・上120px・下のタイトルの帯を避け、文字の幅は800px以内）。
"""
import subprocess, sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

W, H, FPS = 1080, 1920, 30
FONT = Path.home() / ".cache/koyomi/fonts/package/900Black/NotoSansJP_900Black.ttf"
BG = (34, 48, 74)           # 落ち着いた2色：濃い藍
CARD = (250, 243, 228)      #               生成り（カード）
INK = (40, 34, 30)
ACCENT = (255, 205, 40)     # 答え・強調の黄色
RED = (220, 50, 40)
VEIL = 0.62                 # 暗い幕の濃さ
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


def veil(im, lines):
    """暗い幕＋大きな文字（行ごとに [文字, 大きさ, 色]）。"""
    v = Image.blend(im, Image.new("RGB", im.size, (0, 0, 0)), VEIL)
    d = ImageDraw.Draw(v)
    total = sum(int(sz * 1.35) for _, sz, _ in lines)
    y = 900 - total // 2
    for s, sz, col in lines:
        sz = fit(d, s, sz)
        y += int(sz * 1.35) // 2
        text_c(d, (W // 2, y), s, sz, col, stroke=6, stroke_fill=(0, 0, 0))
        y += int(sz * 1.35) // 2
    return v


def header(d, title, sub=None):
    sz = fit(d, title, 76)
    text_c(d, (W // 2, 300), title, sz, (255, 255, 255))
    if sub:
        text_c(d, (W // 2, 390), sub, fit(d, sub, 48), ACCENT)


def footer(d, remain=None, tap=True):
    if remain is not None:
        d.rounded_rectangle((W // 2 - 150, 1290, W // 2 + 150, 1390), 40, fill=CARD)
        text_c(d, (W // 2, 1340), f"のこり {remain}", 56, RED if remain <= 3 else INK)
    if tap:
        text_c(d, (W // 2, 1450), "わかったら 画面を2回タップしてね", fit(d, "わかったら 画面を2回タップしてね", 50), (255, 255, 255))


# ---------- ① 都道府県の穴埋め ----------
PREF = {"title": "「は行」で始まる 都道府県", "sub": "□に入る漢字は？",
        "items": [("□□道", "北海道"), ("□庫県", "兵庫県"), ("□井県", "福井県")],
        "think": 10, "veil": ["「は行」で始まる", "都道府県を 3つ", "□に入る漢字は？"]}


def pref_frame(state, remain=None):
    im = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(im)
    header(d, PREF["title"], PREF["sub"])
    for i, (q, a) in enumerate(PREF["items"]):
        y = 560 + i * 230
        d.rounded_rectangle((X0 + 60, y - 95, X1 - 60, y + 95), 36, fill=CARD)
        shown = a if i < state else q
        x = W // 2 - (len(shown) * 150) // 2 + 75
        for k, ch in enumerate(shown):
            cx = x + k * 150
            if ch == "□":
                d.rounded_rectangle((cx - 62, y - 62, cx + 62, y + 62), 14, outline=RED, width=8)
            else:
                hit = i < state and q[k] == "□"
                text_c(d, (cx, y), ch, 130, RED if hit else INK)
    return im


# ---------- ② ひらがな十字（真ん中に入る1文字） ----------
CROSS = {"across": "さ□な", "down": "あ□り", "answer": "か", "think": 15,
         "veil": ["真ん中の □ に", "入る ひらがなは？", "たて・よこ どちらも 言葉に"]}


def cross_frame(state, remain=None):
    im = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(im)
    header(d, "□に入る ひらがなは？", "たて・よこ どちらも 言葉になります")
    cs, cx, cy = 230, W // 2, 860
    cells = [(-1, 0, CROSS["across"][0]), (1, 0, CROSS["across"][2]), (0, -1, CROSS["down"][0]), (0, 1, CROSS["down"][2]), (0, 0, "□")]
    for dx, dy, ch in cells:
        x, y = cx + dx * cs, cy + dy * cs
        d.rounded_rectangle((x - cs // 2 + 8, y - cs // 2 + 8, x + cs // 2 - 8, y + cs // 2 - 8), 30,
                            fill=ACCENT if (ch == "□" and state) else CARD)
        if ch == "□":
            if state:
                text_c(d, (x, y), CROSS["answer"], 170, RED)
            else:
                d.rounded_rectangle((x - 70, y - 70, x + 70, y + 70), 14, outline=RED, width=8)
        else:
            text_c(d, (x, y), ch, 170, INK)
    if state:
        w1, w2 = CROSS["across"].replace("□", CROSS["answer"]), CROSS["down"].replace("□", CROSS["answer"])
        text_c(d, (W // 2, 1190), f"よこ：{w1}　たて：{w2}", fit(d, f"よこ：{w1}　たて：{w2}", 64), ACCENT)
    return im


# ---------- ③ 漢字の間違い探し（左右、違いは2つ） ----------
KANJI = {"word": "姫路城", "rows": 7, "diffs": {(2, 2): "域", (5, 1): "略"}, "think": 20,
         "veil": ["左と右で", "ちがう漢字が 2つ", "見つけられますか？"]}


def kanji_frame(state, remain=None):
    im = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(im)
    header(d, "左と右で ちがう漢字は？", "ちがいは 2つ")
    cw, ch = 128, 118
    panels = [(X0 + 10, False), (W // 2 + 15, True)]
    for px, right in panels:
        pw = cw * 3 + 20
        d.rounded_rectangle((px, 470, px + pw, 470 + KANJI["rows"] * ch + 30), 24, fill=CARD)
        for r in range(KANJI["rows"]):
            for c in range(3):
                s = KANJI["diffs"].get((r, c), KANJI["word"][c]) if right else KANJI["word"][c]
                x, y = px + 10 + cw * c + cw // 2, 485 + ch * r + ch // 2
                text_c(d, (x, y), s, 104, INK)
                if right and (r, c) in KANJI["diffs"] and state > list(KANJI["diffs"]).index((r, c)):
                    d.ellipse((x - 66, y - 66, x + 66, y + 66), outline=RED, width=10)
    if state >= 2:
        ans = "　".join(f"{KANJI['word'][c]}→{v}" for (r, c), v in KANJI["diffs"].items())
        text_c(d, (W // 2, 1395), ans, 60, ACCENT)
    return im


KINDS = {"pref": (PREF, pref_frame, len(PREF["items"])), "cross": (CROSS, cross_frame, 1), "kanji": (KANJI, kanji_frame, 2)}


def build(kind, out):
    cfg, frame, n_ans = KINDS[kind]
    seq = []   # (画像, 秒)
    q0 = frame(0)
    seq.append((veil(q0, [(s, 96 if i < 2 else 72, (255, 255, 255) if i < 2 else ACCENT) for i, s in enumerate(cfg["veil"])]), 4.0))
    for s in range(cfg["think"], 0, -1):
        im = frame(0); footer(ImageDraw.Draw(im), s); seq.append((im, 1.0))
    im = frame(0); d = ImageDraw.Draw(im); text_c(d, (W // 2, 1340), "答えです", 72, ACCENT); seq.append((im, 1.5))
    for k in range(1, n_ans + 1):
        im = frame(k); footer(ImageDraw.Draw(im), None, tap=False)
        seq.append((im, 2.5 if k < n_ans else 4.0))
    last = frame(n_ans)
    seq.append((veil(last, [("答えは コメントでも", 88, (255, 255, 255)), ("教えてね", 88, (255, 255, 255)),
                            ("わかったら 画面を2回タップ", 64, ACCENT)]), 5.0))
    tmp = out / f"_{kind}"; tmp.mkdir(parents=True, exist_ok=True)
    lst = []
    for i, (im, t) in enumerate(seq):
        p = tmp / f"{i:03d}.png"; im.save(p); lst.append(f"file '{p}'\nduration {t}\n")
    (tmp / "list.txt").write_text("".join(lst) + f"file '{tmp / f'{len(seq) - 1:03d}.png'}'\n", encoding="utf-8")
    total = sum(t for _, t in seq)
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(tmp / "list.txt"),
                    "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo", "-vf", f"fps={FPS},format=yuv420p",
                    "-c:v", "libx264", "-crf", "20", "-c:a", "aac", "-t", f"{total:.2f}", "-movflags", "+faststart",
                    str(out / f"{kind}.mp4")], check=True)
    # 場面ごとの一覧（確認用：幕・考える・答え・最後）
    picks = [seq[0][0], seq[1][0], seq[-2][0], seq[-1][0]]
    S = Image.new("RGB", (4 * 270, 480))
    for i, im in enumerate(picks):
        S.paste(im.resize((270, 480)), (i * 270, 0))
    S.save(out / f"{kind}_frames.jpg", quality=85)
    for p in tmp.iterdir():
        p.unlink()
    tmp.rmdir()
    return total


if __name__ == "__main__":
    out = Path(sys.argv[1]).resolve(); out.mkdir(parents=True, exist_ok=True)
    for k in (sys.argv[2:] or list(KINDS)):
        print(k, build(k, out), "秒")
