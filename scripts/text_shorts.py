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
    sz = fit(d, title, 84)
    text_c(d, (W // 2, 300), title, sz, (255, 255, 255))
    if sub:
        text_c(d, (W // 2, 395), sub, fit(d, sub, 54), ACCENT)


def footer(d, remain=None, tap=True):
    if remain is not None:
        d.rounded_rectangle((W // 2 - 160, 1360, W // 2 + 160, 1450), 40, fill=CARD)
        text_c(d, (W // 2, 1405), f"のこり {remain}", 56, RED if remain <= 3 else INK)
    if tap:
        text_c(d, (W // 2, 1500), "わかったら 画面を2回タップしてね", fit(d, "わかったら 画面を2回タップしてね", 50), (255, 255, 255))


# ---------- ① 都道府県の穴埋め ----------
PREF = {"title": "「は行」で始まる 都道府県", "sub": "□に入る漢字は？",
        "items": [("□□道", "北海道"), ("□庫県", "兵庫県"), ("□井県", "福井県")],
        "think": 12, "veil": ["「は行」で始まる", "都道府県の □ に", "入る漢字は？"]}


def pref_frame(state, remain=None):
    im = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(im)
    header(d, PREF["title"], PREF["sub"])
    for i, (q, a) in enumerate(PREF["items"]):
        y = 640 + i * 270
        d.rounded_rectangle((X0 + 30, y - 120, X1 - 30, y + 120), 40, fill=CARD)
        shown = a if i < state else q
        x = W // 2 - (len(shown) * 200) // 2 + 100
        for k, ch in enumerate(shown):
            cx = x + k * 200
            if ch == "□":
                d.rounded_rectangle((cx - 80, y - 80, cx + 80, y + 80), 16, outline=RED, width=10)
            else:
                hit = i < state and q[k] == "□"
                text_c(d, (cx, y), ch, 170, RED if hit else INK)
    return im


# ---------- ② ひらがな十字（真ん中に入る1文字） ----------
CROSS = {"across": "さ□な", "down": "あ□り", "answer": "か", "think": 17,
         "veil": ["真ん中の □ に", "入る ひらがなは？", "たて・よこ とも 言葉になる"]}


def cross_frame(state, remain=None):
    im = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(im)
    header(d, "□に入る ひらがなは？", "たて・よこ どちらも 言葉になります")
    cs, cx, cy = 290, W // 2, 860
    cells = [(-1, 0, CROSS["across"][0]), (1, 0, CROSS["across"][2]), (0, -1, CROSS["down"][0]), (0, 1, CROSS["down"][2]), (0, 0, "□")]
    for dx, dy, ch in cells:
        x, y = cx + dx * cs, cy + dy * cs
        d.rounded_rectangle((x - cs // 2 + 8, y - cs // 2 + 8, x + cs // 2 - 8, y + cs // 2 - 8), 30,
                            fill=ACCENT if (ch == "□" and state) else CARD)
        if ch == "□":
            if state:
                text_c(d, (x, y), CROSS["answer"], 210, RED)
            else:
                d.rounded_rectangle((x - 90, y - 90, x + 90, y + 90), 16, outline=RED, width=10)
        else:
            text_c(d, (x, y), ch, 210, INK)
    return im


# ---------- ③ 漢字の間違い探し（左右、違いは2つ） ----------
KANJI = {"word": "姫路城", "rows": 6, "diffs": {(2, 2): "域", (5, 1): "略"}, "think": 20,
         "veil": ["左と右で", "ちがう漢字が 2つ", "見つけられますか？"]}


def kanji_frame(state, remain=None):
    im = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(im)
    header(d, "左と右で ちがう漢字は？", "ちがいは 2つ")
    cw, ch = 132, 138
    panels = [(W // 2 - 430, False), (W // 2 + 10, True)]
    for px, right in panels:
        pw = cw * 3 + 20
        d.rounded_rectangle((px, 450, px + pw, 450 + KANJI["rows"] * ch + 30), 24, fill=CARD)
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
    "pref": {"intro": ("「は行」で始まる都道府県です。□に入る漢字は、わかりますか。",
                       "はぎょうで、はじまる、とどうふけんです。しかくにはいるかんじは、わかりますか。"),
             "ans": [("北海道です。", "ほっかいどうです。"), ("兵庫県です。", "ひょうごけんです。"), ("福井県です。", "ふくいけんです。")]},
    "cross": {"intro": ("真ん中に入るひらがなは、なんでしょう。たても、よこも、言葉になります。",
                        "まんなかにはいるひらがなは、なんでしょう。たても、よこも、ことばになります。"),
              "ans": [("答えは「か」。さかなと、あかりです。", "こたえは、か。さかなと、あかりです。")]},
    "kanji": {"intro": ("左と右で、違う漢字が2つあります。見つけられますか。",
                        "ひだりとみぎで、ちがうかんじが、ふたつあります。みつけられますか。"),
              "ans": [("3行目の「城」が「域」に。", "さんぎょうめの、しろが、いきに。"), ("6行目の「路」が「略」になっていました。", "ろくぎょうめの、みちが、りゃくに、なっていました。")]},
}
TAP = ("わかったら、画面を2回タップしてくださいね。", "わかったら、がめんを、にかいタップしてくださいね。")
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
        d.rounded_rectangle(BUBBLE, 30, fill=(255, 255, 255), outline=ACCENT, width=5)
        d.polygon([(x0 + 2, y0 + 80), (x0 - 34, y0 + 110), (x0 + 2, y0 + 125)], fill=(255, 255, 255))
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
    d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=CARD, outline=RED if remain <= 3 else ACCENT, width=6)
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


def voice(kind, key, vt):
    """声は Fish Audio（第12回と同じ こよみ先生の声・速さ）。同じ文はもう一度作らない。"""
    import json, os, wave
    vd = WORK / "voice"; vd.mkdir(parents=True, exist_ok=True)
    wav, meta = vd / f"{kind}_{key}.wav", vd / f"{kind}_{key}.json"
    if not (wav.exists() and meta.exists() and json.loads(meta.read_text(encoding="utf-8"))["voice_text"] == vt):
        os.environ.setdefault("KOYOMI_EPISODE_DIR", str(Path(__file__).resolve().parent.parent / "outputs/2026-11-23_012"))
        import ep_voice as V
        V.tts_line(vt, wav)
        meta.write_text(json.dumps({"voice_text": vt}, ensure_ascii=False), encoding="utf-8")
    with wave.open(str(wav)) as w:
        return wav, w.getnframes() / w.getframerate()


KINDS = {"pref": (PREF, pref_frame, len(PREF["items"])), "cross": (CROSS, cross_frame, 1), "kanji": (KANJI, kanji_frame, 2)}


def build(kind, out):
    cfg, frame, n_ans = KINDS[kind]
    L = LINES[kind]
    seq, voices, t = [], [], 0.0     # seq：(画像, 秒)、voices：(声のファイル, 開始秒)

    def say(key, line):
        w, dur = voice(kind, key, line[1]); voices.append((w, t + 0.3)); return dur + 0.3

    # 1. 暗い幕＋問題文（0:00 から出ている＝サムネ）
    d_intro = say("intro", L["intro"])
    vl = [(s_, 96 if i < 2 else 72, (255, 255, 255) if i < 2 else ACCENT) for i, s_ in enumerate(cfg["veil"])]
    seq.append((speaker(veil(frame(0), vl), "normal", L["intro"][0]), max(4.0, d_intro + 0.4))); t += seq[-1][1]
    # 2. 考える時間（右上にのこり秒数）。はじめに「わかったら2回タップ」
    say("tap", TAP)
    for s_ in range(cfg["think"], 0, -1):
        seq.append((timer(speaker(frame(0), "think" if s_ < cfg["think"] - 3 else "smile", TAP[0]), s_), 1.0)); t += 1.0
    # 3. 答え
    d0 = say("ans0", ANS0)
    seq.append((speaker(frame(0), "surprise", ANS0[0]), max(1.5, d0 + 0.2))); t += seq[-1][1]
    per = max(1, len(L["ans"]) // n_ans) if n_ans >= len(L["ans"]) else 1
    for k in range(1, n_ans + 1):
        line = L["ans"][min(k - 1, len(L["ans"]) - 1)] if n_ans == len(L["ans"]) else (L["ans"][0] if k == 1 else None)
        dk = say(f"ans{k}", line) if line else 0
        last = k == n_ans
        seq.append((speaker(frame(k), "yay" if last else "smile", line[0] if line else L["ans"][0][0]), max(2.5, dk + 0.4) + (1.0 if last else 0))); t += seq[-1][1]
    # 4. 最後：暗い幕＋「左下をクリック」と矢印（10コマ/秒で矢印を動かす）
    dc = say("cta", CTA)
    end = max(5.0, dc + 1.0)
    base = veil(frame(n_ans), [("ほかの脳トレにも", 100, (255, 255, 255)), ("挑戦！", 110, (255, 255, 255)), ("左下をクリック", 120, ACCENT)])
    base = speaker(base, "wink")
    for i in range(int(end * 10)):
        seq.append((arrow(base.copy(), i / 10), 0.1))
    t += end
    total = t
    tmp = out / f"_{kind}"; tmp.mkdir(parents=True, exist_ok=True)
    lst = []
    for i, (im, dt) in enumerate(seq):
        p = tmp / f"{i:03d}.png"; im.save(p); lst.append(f"file '{p}'\nduration {dt}\n")
    (tmp / "list.txt").write_text("".join(lst) + f"file '{tmp / f'{len(seq) - 1:03d}.png'}'\n", encoding="utf-8")
    # 音：声を時刻に置いて重ね、大きさをそろえる
    ins, flt = [], []
    for i, (w, at) in enumerate(voices):
        ins += ["-i", str(w)]; flt.append(f"[{i + 1}]adelay={int(at * 1000)}|{int(at * 1000)},aformat=channel_layouts=stereo[v{i}]")
    mix = ";".join(flt) + ";" + "".join(f"[v{i}]" for i in range(len(voices))) + f"amix=inputs={len(voices)}:normalize=0,apad,atrim=0:{total:.2f},loudnorm=I=-16:TP=-1.5[a]"
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(tmp / "list.txt"), *ins,
                    "-filter_complex", mix, "-map", "0:v", "-map", "[a]", "-vf", f"fps={FPS},format=yuv420p",
                    "-c:v", "libx264", "-crf", "20", "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-t", f"{total:.2f}",
                    "-movflags", "+faststart", str(out / f"{kind}.mp4")], check=True)
    idx = [0, 1, len(seq) - int(end * 10) - 1, len(seq) - 3]
    S = Image.new("RGB", (4 * 270, 480))
    for i, n in enumerate(idx):
        S.paste(seq[n][0].resize((270, 480)), (i * 270, 0))
    S.save(out / f"{kind}_frames.jpg", quality=85)
    for p in tmp.iterdir():
        p.unlink()
    tmp.rmdir()
    return round(total, 1)


if __name__ == "__main__":
    out = Path(sys.argv[1]).resolve(); out.mkdir(parents=True, exist_ok=True)
    for k in (sys.argv[2:] or list(KINDS)):
        print(k, build(k, out), "秒")
