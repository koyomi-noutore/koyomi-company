"""「ちがうのどれ？（仲間はずれ探し）」ショートの試作（2026-11-23 CEO案）。新しいファイルだけ。共通のプログラムは変えない。

使い方：python3 scripts/chigau_shorts.py <出力フォルダ> [種類 ...]   種類＝easy（漢字・やさしい）・hard（漢字・むずかしい）・mikan（絵）
  mp4 と readings_check.md を <出力> に書く。作業ファイルは ~/.cache/koyomi/chigau/ に置く。
  絵の元（mikan_src.png）が無いときだけ画像APIを1回使う（Vertex 標準）。あれば作り直さない。
流れ・音・こよみ先生・矢印は scripts/text_shorts.py の build をそのまま使う（KINDS・LINES に足すだけ）。
"""
import functools, math, random, sys, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import text_shorts as T
from PIL import Image, ImageDraw, ImageFont

W, H = T.W, T.H
WORK = Path.home() / ".cache/koyomi/chigau"
T.WORK = WORK                                   # 声・こよみ先生の画像の置き場（text_shorts の関数がここを使う）
PANEL = (70, 440, 1010, 1285)                   # 問題の台紙。下の1300より下は、こよみ先生と吹き出しの場所
INNER = (90, 460, 990, 1265)                    # 文字・絵を置く範囲（左右の端・右のボタンを避ける）


def font_w(size, weight="900Black"):
    return ImageFont.truetype(str(Path.home() / f".cache/koyomi/fonts/package/{weight}/NotoSansJP_{weight}.ttf"), size)


TITLE = "ちがうのどーれだ？"


def base(what, bg=T.CARD):
    """見出し（1行に収まる範囲で大きく）＋説明文2行（2026-11-23 CEO）。what＝字・みかん など。"""
    im = Image.new("RGB", (W, H), T.BG)
    d = ImageDraw.Draw(im)
    T.text_c(d, (W // 2, 272), TITLE, T.fit(d, TITLE, 120, 900), (255, 255, 255))
    for y, s_ in ((347, f"一つだけ違う{what}があるよ。"), (396, "見つけてみてね！")):
        T.text_c(d, (W // 2, y), s_, T.fit(d, s_, 46, 860), T.ACCENT)
    d.rounded_rectangle(PANEL, 40, fill=bg)
    return im, d


def circle(d, x, y, r):
    d.ellipse((x - r, y - r, x + r, y + r), outline=T.RED, width=12)


def glyph(ch, size, angle=0, weight="900Black"):
    """1文字を透明な正方形に描き、angle 度まわす。"""
    s = int(size * 1.5)
    g = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    ImageDraw.Draw(g).text((s / 2, s / 2), ch, font=font_w(size, weight), fill=T.INK + (255,), anchor="mm")
    return g.rotate(angle, resample=Image.BICUBIC) if angle else g


# ---------- ① 漢字・やさしい（整列ぎみ・季の中に李） ----------
EASY = {"main": "季", "odd": "李", "cols": 4, "rows": 5, "odd_at": (3, 1)}   # (行, 列)


@functools.lru_cache(maxsize=None)   # コマごとに呼ばれるので、一度だけ計算する（hard の書き出しが500秒かかった反省）
def layout_easy():
    rnd = random.Random(11)
    x0, y0, x1, y1 = INNER
    cw, ch = (x1 - x0) / EASY["cols"], (y1 - y0) / EASY["rows"]
    out = []
    for r in range(EASY["rows"]):
        for c in range(EASY["cols"]):
            cx = x0 + cw * (c + .5) + rnd.randint(-14, 14)
            cy = y0 + ch * (r + .5) + rnd.randint(-12, 12)
            out.append((EASY["odd"] if (r, c) == EASY["odd_at"] else EASY["main"], cx, cy, 138 + rnd.randint(-8, 8), rnd.randint(-6, 6)))
    return out


def easy_frame(state, remain=None):
    im, d = base("字")
    for ch, cx, cy, sz, ang in layout_easy():
        g = glyph(ch, sz, ang)
        im.paste(g, (int(cx - g.width / 2), int(cy - g.height / 2)), g)
        if ch == EASY["odd"] and state:
            circle(d, cx, cy, 84)
    return im


# ---------- ② 漢字・むずかしい（大きさ・向きばらばら・字どうしは重ならない・末の中に未） ----------
TILT = 120                                     # 向きの回転は±120度まで（2026-11-23 CEO。hard だけ）
HARD = {"key": "hard", "main": "末", "odd": "未", "n": 16, "weight": "700Bold", "size": (140, 170), "tilt": TILT, "seed": 5, "odd_i": 5}   # 2026-11-23 監査1回目：太さを下げ、回転は±30度、最小90px


@functools.lru_cache(maxsize=None)
def _layout_scatter(key):
    cfg = CFGS[key]
    """大きい字から順に、重ならない場所をさがして置く。重なりは、字を描いた実際の形（インク）で、置くたびに検査する（回転しても重ならない）。"""
    import numpy as np
    from PIL import ImageFilter
    rnd = random.Random(cfg["seed"])
    x0, y0, x1, y1 = INNER
    sizes = sorted([rnd.randint(*cfg["size"]) for _ in range(cfg["n"])], reverse=True)
    odd_i = cfg["odd_i"]                                          # 大きさの順で6番目＝大きい方の字（小さすぎて見えない、を避ける）
    occ = np.zeros((H, W), bool)
    placed = []
    for i, sz in enumerate(sizes):
        ch = cfg["odd"] if i == odd_i else cfg["main"]
        for _ in range(8000):
            ang = rnd.randint(-cfg["tilt"], cfg["tilt"])
            g = glyph(ch, sz, ang, cfg["weight"]).split()[3].point(lambda v: 255 if v > 30 else 0).filter(ImageFilter.MaxFilter(9))   # ふち4pxぶん太らせて、字どうしの間をあける
            bb = g.getbbox(); full = g.size[0]                  # 字の形の外枠だけにして、端まで使う
            g = g.crop(bb); gw, gh = g.size
            px = rnd.randint(x0, x1 - gw); py = rnd.randint(y0, y1 - gh)
            cx = px + gw / 2 - (bb[0] + gw / 2 - full / 2); cy = py + gh / 2 - (bb[1] + gh / 2 - full / 2)   # 字の中心（回転前の中心）
            m = np.array(g) > 0
            if not (occ[py:py + gh, px:px + gw] & m).any():
                occ[py:py + gh, px:px + gw] |= m
                placed.append((ch, cx, cy, sz, ang)); break
        else:
            raise SystemExit(f"置ききれない（{i}個目）。個数か大きさを減らす")
    return placed


def layout_scatter(cfg):
    return _layout_scatter(cfg["key"])


def layout_hard():
    return layout_scatter(HARD)


# ---------- ②b 漢字・ふつう（追加：大の中に犬。差は「ちょん」の点があるかどうかで、スマホでも見分けやすい） ----------
FUTSU = {"key": "futsu", "main": "大", "odd": "犬", "n": 20, "weight": "700Bold", "size": (120, 150), "tilt": 60, "seed": 9, "odd_i": 6}
CFGS = {"hard": HARD, "futsu": FUTSU}


def futsu_frame(state, remain=None):
    im, d = base("字")
    for ch, cx, cy, sz, ang in layout_scatter(FUTSU):
        g = glyph(ch, sz, ang, FUTSU["weight"])
        im.paste(g, (int(cx - g.width / 2), int(cy - g.height / 2)), g)
        if ch == FUTSU["odd"] and state:
            circle(d, cx, cy, int(sz * 0.62))
    return im


def hard_frame(state, remain=None):
    im, d = base("字")
    for ch, cx, cy, sz, ang in layout_hard():
        g = glyph(ch, sz, ang, HARD["weight"])
        im.paste(g, (int(cx - g.width / 2), int(cy - g.height / 2)), g)
        if ch == HARD["odd"] and state:
            circle(d, cx, cy, int(sz * 0.62))
    return im


# ---------- ③ 絵（みかん3×5・1つだけ左右反転） ----------
MIKAN = {"cols": 3, "rows": 5, "odd_at": (3, 1)}                 # (行, 列)
PROMPT = ("A single cute mandarin orange (mikan) with one green leaf attached on the top, leaning to the right side, a small brown stem, "
          "simple flat illustration, clean bold outlines, soft shading, a few tiny dimple dots on the skin, centered, "
          "on a plain pure white background. No text, no letters, no shadow on the ground, nothing else in the picture.")


def mikan_pic():
    """元の絵を1枚だけ画像APIで作る（あれば作り直さない）。白い背景を完全な白にして、余白を切り、高さ150pxにする。"""
    src = WORK / "mikan_src.png"
    if not src.exists():
        import gemini_image as G
        G.generate(PROMPT, aspect="1:1", size="1K").save(src)
    im = Image.open(src).convert("RGB")
    import numpy as np
    a = np.array(im)
    a[(a > 236).all(axis=2)] = 255
    im = Image.fromarray(a)
    bb = Image.fromarray(255 - a.min(axis=2)).point(lambda v: 255 if v > 40 else 0).getbbox()
    im = im.crop(bb)
    return im.resize((round(im.width * 150 / im.height), 150), Image.LANCZOS)


MITTEN = {"cols": 3, "rows": 5, "odd_at": (1, 2)}
MITTEN_PROMPT = ("A single red knitted winter mitten, front view, with a white snowflake pattern on the back of the hand and a thick white fluffy cuff, thumb pointing left, "
                 "simple flat illustration, clean bold dark outlines, soft shading, centered, on a plain pure white background. No text, no letters, no ground shadow, nothing else in the picture.")
SNOW_BOX = (425, 280, 705, 560)                 # 元の絵（1024px）の中の雪の結晶の場所。違い＝この模様があるか、ないか


_ODD = []


def _is_red(a):
    """手袋の赤（影・光の部分も含む）。灰色・桃色・白は赤でない。"""
    r, g, b = a[..., 0].astype(int), a[..., 1].astype(int), a[..., 2].astype(int)
    return (r > 185) & (g < 72) & (b < 68) & (r - g > 120)   # 手袋の赤は約 (230, 59, 53)。ほんの少し明るいにじみも「赤でない」にする


@functools.lru_cache(maxsize=None)
def mitten_pics():
    """冬の絵：赤い毛糸の手袋（画像API 1枚）。違う1つは、雪の結晶の模様を消したもの（プログラム）。"""
    import numpy as np
    import numpy as np
    from scipy.ndimage import binary_dilation, gaussian_filter
    src = WORK / "mitten_src.png"
    if not src.exists():
        import gemini_image as G
        G.generate(MITTEN_PROMPT, aspect="1:1", size="1K").save(src)
    a = np.array(Image.open(src).convert("RGB"))
    a[(a > 236).all(axis=2)] = 255
    o = a.copy()
    x0, y0, x1, y1 = SNOW_BOX
    sub = o[y0:y1, x0:x1]
    off = ~_is_red(sub)                                    # 赤から外れる画素（白・灰色・桃色の線・ふちのにじみ）すべて
    off = binary_dilation(off, iterations=4)               # 4px広げて、にじみの残りも含める
    ok = (~off).astype(float)                              # 周りの赤をなめらかに平均して塗る（いちばん近い色だと、まだらの跡が残る）
    for _ in range(2):
        num = np.stack([gaussian_filter(sub[..., c] * ok, 25) for c in range(3)], axis=-1)
        den = gaussian_filter(ok, 25)[..., None] + 1e-6
        sub[off] = (num / den)[off].astype(np.uint8)
        ok = np.ones_like(ok)
    bb = Image.fromarray(255 - a.min(axis=2)).point(lambda v: 255 if v > 40 else 0).getbbox()
    _ODD.append(Image.fromarray(o))
    out = []
    for arr in (a, o):
        im = Image.fromarray(arr).crop(bb)
        out.append(im.resize((round(im.width * 150 / im.height), 150), Image.LANCZOS))
    return out


def odd_full():
    """結晶を消した絵（切り取り・縮小の前の大きさ）。確認用。"""
    import numpy as np
    mitten_pics()
    return _ODD[0]


def mitten_frame(state, remain=None):
    im, d = base("手袋", bg=(255, 255, 255))
    pic, odd = mitten_pics()
    x0, y0, x1, y1 = INNER
    cw, ch = (x1 - x0) / MITTEN["cols"], (y1 - y0) / MITTEN["rows"]
    for r in range(MITTEN["rows"]):
        for c in range(MITTEN["cols"]):
            p = odd if (r, c) == MITTEN["odd_at"] else pic
            cx, cy = x0 + cw * (c + .5), y0 + ch * (r + .5)
            im.paste(p, (int(cx - p.width / 2), int(cy - p.height / 2)))
            if (r, c) == MITTEN["odd_at"] and state:
                circle(d, cx, cy, 98)
    return im


def mikan_frame(state, remain=None):
    im, d = base("みかん", bg=(255, 255, 255))
    pic = mikan_pic(); odd = pic.transpose(Image.FLIP_LEFT_RIGHT)
    x0, y0, x1, y1 = INNER
    cw, ch = (x1 - x0) / MIKAN["cols"], (y1 - y0) / MIKAN["rows"]
    for r in range(MIKAN["rows"]):
        for c in range(MIKAN["cols"]):
            p = odd if (r, c) == MIKAN["odd_at"] else pic
            cx, cy = x0 + cw * (c + .5), y0 + ch * (r + .5)
            im.paste(p, (int(cx - p.width / 2), int(cy - p.height / 2)))
            if (r, c) == MIKAN["odd_at"] and state:
                circle(d, cx, cy, 98)
    return im


# ---------- T.build に登録（流れ・声・音・こよみ先生・矢印は共通） ----------
T.KINDS["easy"] = ({"think": 15, "veil": [TITLE, "一つだけ違う字があるよ。", "見つけてみてね！"]}, easy_frame, 1)
T.KINDS["hard"] = ({"think": 20, "veil": [TITLE, "一つだけ違う字があるよ。", "見つけてみてね！"]}, hard_frame, 1)
T.KINDS["mikan"] = ({"think": 15, "veil": [TITLE, "一つだけ違うみかんがあるよ。", "見つけてみてね！"]}, mikan_frame, 1)
T.LINES["easy"] = {"intro": ("違う漢字が、1つだけあります。どれでしょう？", "ちがうかんじが、ひとつだけあります。どれでしょう？"),
                   "ans": [("「季節」の『季』の中に、「李（すもも）」の『李』が、混ざっていました。", "きせつの、き、のなかに、すももの、り、が、まざっていました。")]}
T.LINES["hard"] = {"intro": ("違う漢字が、1つだけあります。どれでしょう？", "ちがうかんじが、ひとつだけあります。どれでしょう？"),
                   "ans": [("「年末」の『末』の中に、「未来」の『未』が、混ざっていました。", "ねんまつの、まつ、のなかに、みらいの、み、が、まざっていました。")]}
T.LINES["mikan"] = {"intro": ("違うみかんが、1つだけあります。どれでしょう？", "ちがうみかんが、ひとつだけあります。どれでしょう？"),
                    "ans": [("葉っぱが反対向きの、みかんでした。", "はっぱが、はんたいむきの、みかんでした。")]}
T.KINDS["futsu"] = ({"think": 18, "veil": [TITLE, "一つだけ違う字があるよ。", "見つけてみてね！"]}, futsu_frame, 1)
T.KINDS["mitten"] = ({"think": 15, "veil": [TITLE, "一つだけ違う手袋があるよ。", "見つけてみてね！"]}, mitten_frame, 1)
T.LINES["futsu"] = {"intro": ("違う漢字が、1つだけあります。どれでしょう？", "ちがうかんじが、ひとつだけあります。どれでしょう？"),
                    "ans": [("「大小」の『大』の中に、「犬」の『犬』が、混ざっていました。", "だいしょうの、だい、のなかに、いぬの、いぬ、が、まざっていました。")]}
T.LINES["mitten"] = {"intro": ("違う手袋が、1つだけあります。どれでしょう？", "ちがうてぶくろが、ひとつだけあります。どれでしょう？"),
                     "ans": [("模様のない、手袋でした。", "もようのない、てぶくろでした。")]}
def load_problem(path):
    """問題の定義（problem.json）から、散らし配置の漢字の回を登録する（2026-11-23：字の組を増やすため）。
    kind は "scatter"。main（たくさんある字）・odd（1つだけ違う字）・n・weight・size・tilt・seed・odd_i・think・lines（intro と ans）。"""
    import json
    P = json.loads(Path(path).read_text(encoding="utf-8"))
    key = P["id"]
    cfg = {"key": key, "main": P["main"], "odd": P["odd"], "n": P["n"], "weight": P["weight"], "size": tuple(P["size"]),
           "tilt": P["tilt"], "seed": P["seed"], "odd_i": P["odd_i"]}
    CFGS[key] = cfg

    def frame(state, remain=None, cfg=cfg):
        im, d = base("字")
        for ch, cx, cy, sz, ang in layout_scatter(cfg):
            g = glyph(ch, sz, ang, cfg["weight"])
            im.paste(g, (int(cx - g.width / 2), int(cy - g.height / 2)), g)
            if ch == cfg["odd"] and state:
                circle(d, cx, cy, int(sz * 0.62))
        return im
    T.KINDS[key] = ({"think": P["think"], "veil": [TITLE, "一つだけ違う字があるよ。", "見つけてみてね！"]}, frame, 1)
    T.LINES[key] = {"intro": tuple(P["lines"]["intro"]), "ans": [tuple(x) for x in P["lines"]["ans"]]}
    T.PROBLEM_ID = key
    return key


ORDER = ["easy", "hard", "mikan"]


def check():
    """答えが1つだけ・字が重ならない・字が表示できる、を数値で確かめる（目で見る前に）。"""
    import numpy as np
    res = []
    for name, lay, main, odd in (("easy", layout_easy(), EASY["main"], EASY["odd"]), ("hard", layout_hard(), HARD["main"], HARD["odd"]), ("futsu", layout_scatter(FUTSU), FUTSU["main"], FUTSU["odd"])):
        n_odd = sum(1 for c, *_ in lay if c == odd); kinds = {c for c, *_ in lay}
        res.append(f"{name}：字の数 {len(lay)}（{main}×{len(lay) - n_odd}、{odd}×{n_odd}）種類 {sorted(kinds)}  答え1つ：{'OK' if n_odd == 1 and kinds == {main, odd} else 'NG'}")
        # 重なり：字を1枚ずつ別の面に描いたインクどうしが触れていないか
        masks = []
        for ch, cx, cy, sz, ang in lay:
            g = glyph(ch, sz, ang, CFGS[name]["weight"] if name in CFGS else "900Black").split()[3].point(lambda v: 255 if v > 30 else 0)
            m = Image.new("L", (W, H), 0); m.paste(g, (int(cx - g.width / 2), int(cy - g.height / 2))); masks.append(np.array(m) > 0)
        ov = sum(int((masks[i] & masks[j]).any()) for i in range(len(masks)) for j in range(i + 1, len(masks)))
        res.append(f"{name}：インクが重なる字の組 {ov}（0 が合格）")
        # 豆腐：字の形が、存在しない文字（.notdef＝四角）と同じでないか
        nd = np.array(glyph("￿", 140).split()[3]) > 30
        for ch in kinds:
            g = np.array(glyph(ch, 140).split()[3]) > 30
            res.append(f"{name}：「{ch}」は豆腐でない：{'OK' if g.sum() > 0 and not (g.shape == nd.shape and (g == nd).all()) else 'NG（豆腐）'}")
    a = np.array(mikan_frame(0)); b = np.array(mikan_frame(1))
    pic = np.array(mikan_pic()); odd = pic[:, ::-1]
    res.append(f"mikan：反転で元と違う画素 {(pic != odd).any(axis=2).mean() * 100:.0f}%（違いが見える）／同じ絵14枚・違う絵1枚：構成どおり（台紙に貼る絵は2種類だけ）")
    pic, odd = mitten_pics()
    import numpy as np
    diff = (np.array(pic).astype(int) != np.array(odd).astype(int)).any(axis=2)
    box = np.array(odd_full())[SNOW_BOX[1]:SNOW_BOX[3], SNOW_BOX[0]:SNOW_BOX[2]]
    res.append(f"mitten：結晶の範囲で赤から外れる画素（違う1枚）{int((~_is_red(box)).sum())}個／{box.shape[0] * box.shape[1]}（0に近いのが合格）")
    res.append(f"mitten：元と違う画素 {diff.mean() * 100:.1f}%（雪の結晶の有無）。台紙に貼る絵は元14枚・違う1枚の2種類だけ")
    return res


def build(kind, out):
    """text_shorts.build と同じ流れ。最後だけ共通の部品 short_outro（コメント→左下をクリック）を使う。"""
    from short_outro import build_outro
    cfg, frame, n_ans = T.KINDS[kind]; L = T.LINES[kind]
    seq, voices, ev, t = [], [], {}, 0.0

    def say(key, line, at=None):
        w, dur = T.voice(kind, key, line[1]); voices.append((w, (t if at is None else at) + 0.3, key, line)); return dur + 0.3
    d_intro = say("intro", L["intro"])
    vl = [(s_, 96 if i < 2 else 72, (255, 255, 255) if i < 2 else T.ACCENT) for i, s_ in enumerate(cfg["veil"])]
    seq.append((T.speaker(T.veil(frame(0), vl), "normal", L["intro"][0]), max(4.0, d_intro + 0.4))); t += seq[-1][1]
    say("tap", T.TAP)
    for s_ in range(cfg["think"], 0, -1):
        seq.append((T.timer(T.speaker(frame(0), "think" if s_ < cfg["think"] - 3 else "smile", T.TAP[0]), s_), 1.0)); t += 1.0
    ev["solve_end"] = t
    d0 = say("ans0", T.ANS0)
    seq.append((T.speaker(frame(0), "surprise", T.ANS0[0]), max(1.5, d0 + 0.2))); t += seq[-1][1]
    line = L["ans"][0]
    ev["pon"] = [t + 0.3]
    dk = say("ans1", line)
    seq.append((T.speaker(frame(1), "yay", line[0]), max(2.5, dk + 0.4) + 1.0)); t += seq[-1][1]
    ev["end_at"] = t
    n_ans_end = len(seq)
    frames, length = build_outro(frame(1), lambda key, ln, off: say(key, ln, t + off), T.veil, T.speaker, T.arrow, comment="text")
    seq += frames; total = t + length
    tmp = WORK / f"_{kind}"; tmp.mkdir(parents=True, exist_ok=True)
    lst = []
    for i, (im, dt) in enumerate(seq):
        p = tmp / f"{i:03d}.png"; im.save(p); lst.append(f"file '{p}'\nduration {dt}\n")
    (tmp / "list.txt").write_text("".join(lst) + f"file '{tmp / f'{len(seq) - 1:03d}.png'}'\n", encoding="utf-8")
    T.mix_audio(voices, ev, total, tmp / "mix.wav")
    T.readings_check(kind, voices, out)
    import subprocess
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(tmp / "list.txt"), "-i", str(tmp / "mix.wav"),
                    "-map", "0:v", "-map", "1:a", "-vf", f"fps={T.FPS},format=yuv420p", "-c:v", "libx264", "-crf", "20", "-c:a", "aac", "-b:a", "192k",
                    "-ar", "48000", "-t", f"{total:.2f}", "-movflags", "+faststart", str(out / f"{kind}.mp4")], check=True)
    shots = [seq[0][0], seq[2][0], seq[n_ans_end - 1][0], frames[0][0], frames[len(frames) // 2][0]]   # 0:00・問題・答え・最後の2段
    S = Image.new("RGB", (len(shots) * 270, 480))
    for i, im_ in enumerate(shots):
        S.paste(im_.resize((270, 480)), (i * 270, 0))
    S.save(out / f"{kind}_frames.jpg", quality=85)
    for p in tmp.iterdir():
        p.unlink()
    tmp.rmdir()
    return round(total, 1)


if __name__ == "__main__":
    out = Path(sys.argv[1]).resolve(); out.mkdir(parents=True, exist_ok=True)
    WORK.mkdir(parents=True, exist_ok=True)
    kinds = sys.argv[2:] or ORDER
    if "--check" in kinds:
        print("\n".join(check())); sys.exit()
    for k in kinds:
        if k.endswith(".json"):
            k = load_problem(k)
        t = time.time()
        sec = build(k, out)
        print(k, sec, "秒（作業", round(time.time() - t), "秒）", flush=True)
