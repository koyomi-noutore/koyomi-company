"""「ちがうのどれ？（仲間はずれ探し）」ショートの試作（2026-11-23 CEO案）。新しいファイルだけ。共通のプログラムは変えない。

使い方：python3 scripts/chigau_shorts.py <出力フォルダ> [種類 ...]   種類＝easy（漢字・やさしい）・hard（漢字・むずかしい）・mikan（絵）
  mp4 と readings_check.md を <出力> に書く。作業ファイルは ~/.cache/koyomi/chigau/ に置く。
  絵の元（mikan_src.png）が無いときだけ画像APIを1回使う（Vertex 標準）。あれば作り直さない。
流れ・音・こよみ先生・矢印は scripts/text_shorts.py の build をそのまま使う（KINDS・LINES に足すだけ）。
"""
import math, random, sys, time
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
    T.text_c(d, (W // 2, 258), TITLE, T.fit(d, TITLE, 120, 900), (255, 255, 255))
    for y, s_ in ((352, f"一つだけ違う{what}があるよ。"), (412, "見つけてみてね！")):
        T.text_c(d, (W // 2, y), s_, T.fit(d, s_, 54, 860), T.ACCENT)
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
HARD = {"main": "末", "odd": "未", "n": 16, "weight": "700Bold"}   # 2026-11-23 監査1回目：太さを下げ、回転は±30度、最小90px


def layout_hard():
    """大きい字から順に、重ならない場所をさがして置く。重なりは、字を描いた実際の形（インク）で、置くたびに検査する（回転しても重ならない）。"""
    import numpy as np
    from PIL import ImageFilter
    rnd = random.Random(5)
    x0, y0, x1, y1 = INNER
    sizes = sorted([rnd.randint(140, 170) for _ in range(HARD["n"])], reverse=True)
    odd_i = 5                                          # 大きさの順で6番目＝大きい方の字（小さすぎて見えない、を避ける）
    occ = np.zeros((H, W), bool)
    placed = []
    for i, sz in enumerate(sizes):
        ch = HARD["odd"] if i == odd_i else HARD["main"]
        for _ in range(8000):
            ang = rnd.randint(-TILT, TILT)
            g = glyph(ch, sz, ang, HARD["weight"]).split()[3].point(lambda v: 255 if v > 30 else 0).filter(ImageFilter.MaxFilter(9))   # ふち4pxぶん太らせて、字どうしの間をあける
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
ORDER = ["easy", "hard", "mikan"]


def check():
    """答えが1つだけ・字が重ならない・字が表示できる、を数値で確かめる（目で見る前に）。"""
    import numpy as np
    res = []
    for name, lay, main, odd in (("easy", layout_easy(), EASY["main"], EASY["odd"]), ("hard", layout_hard(), HARD["main"], HARD["odd"])):
        n_odd = sum(1 for c, *_ in lay if c == odd); kinds = {c for c, *_ in lay}
        res.append(f"{name}：字の数 {len(lay)}（{main}×{len(lay) - n_odd}、{odd}×{n_odd}）種類 {sorted(kinds)}  答え1つ：{'OK' if n_odd == 1 and kinds == {main, odd} else 'NG'}")
        # 重なり：字を1枚ずつ別の面に描いたインクどうしが触れていないか
        masks = []
        for ch, cx, cy, sz, ang in lay:
            g = glyph(ch, sz, ang, HARD["weight"] if name == "hard" else "900Black").split()[3].point(lambda v: 255 if v > 30 else 0)
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
        t = time.time()
        sec = build(k, out)
        print(k, sec, "秒（作業", round(time.time() - t), "秒）", flush=True)
