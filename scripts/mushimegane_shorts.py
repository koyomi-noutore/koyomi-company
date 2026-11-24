"""「この○○なーんだ？」虫めがねクイズ ショートの試作（2026-11-24 CEO案）。新しいファイルだけ。共通のプログラムは変えない。

使い方：python3 scripts/mushimegane_shorts.py <出力フォルダ> [id ...]   id は scripts/mushimegane_defs.json の items（kabu・tanuki・oden）
  <出力>/<id>.mp4（縦1080×1920・30fps）と readings_check.md。作業ファイルは ~/.cache/koyomi/mushimegane/。
  絵（<id>.png）が無いときだけ画像APIを1枚使う（Vertex 標準）。あれば作り直さない。
画面：季節の背景（scripts/season_theme.json の冬＝winter_A。2026-11-24 CEO厳守）に大きな見出し。中央の正方形の絵を黒でおおい、
虫めがねがゆっくり動いて、レンズの円の中だけ絵が見える（直径は正方形の約3割・道すじは約12秒）。最後に黒を外して「正解は、○○でした」。
音・声・こよみ先生・矢印は text_shorts.py の部品を使い、最後の流れは short_outro.py の build_outro（short_outro.py は変えていない。言い方の差し替えは、この中で SO.COMMENT・SO.CTA・SO.CTA_VEIL に実行時に入れる。T.CARD と同じやり方）。
"""
import json, math, subprocess, sys, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import text_shorts as T
import short_outro as SO
from short_outro import build_outro
from PIL import Image, ImageDraw

W, H, FPS = T.W, T.H, T.FPS
WORK = Path.home() / ".cache/koyomi/mushimegane"
T.WORK = WORK
DEFS = json.loads((Path(__file__).parent / "mushimegane_defs.json").read_text(encoding="utf-8"))["items"]
_ST = json.loads((Path(__file__).parent / "season_theme.json").read_text(encoding="utf-8"))
SEASON = "冬"                              # 2026-11-24 CEO厳守：ショートの背景は長尺と同じ季節の色。今は全部「冬」（season_theme.json の season_default → winter_A）
THEME = _ST["themes"][_ST["season_default"][SEASON]]
BG, INK, ACC = tuple(THEME["bg"]), tuple(THEME["ink"]), tuple(THEME["accent"])
T.CARD, T.INK = tuple(THEME["panel"]), tuple(THEME["ink"])   # 共通部品（吹き出し・のこり秒数の丸）の色もこの季節の色に（このプログラムの中だけ）
BLACK = (22, 20, 18)
S = 720                                  # 正方形の一辺
SX, SY = (W - S) // 2, 500               # 正方形の左上（下の y 1300 より下はこよみ先生と吹き出し）
LENS_D = round(S * 0.30)                 # レンズの直径＝正方形の約3割
LINE_Y = (190, 322, 440)                 # 0:00 の3行の中心の高さ。文字の大きさは 125・125・90px（上120pxと黒い正方形 y500〜 にかからない）
SUB, SUB_SIZE = "虫めがねでのぞいてね", 90
WALK = 12                                # 虫めがねが道すじを通る秒数＝考える時間
RIM = (120, 78, 46)


def picture(item):
    src = WORK / item["image"]
    if not src.exists():
        import os, gemini_image as G
        os.environ.setdefault("KOYOMI_IMAGE_USAGE_LOG", str(WORK / "image_usage.jsonl"))
        common = ("Watercolor painting with bold thick dark-brown outlines and soft color washes, a single subject drawn very large, filling most of the square frame, centered, "
                  "on a plain off-white paper background. No text, no letters, no people, no props other than described, no frame, no shadow on the ground. ")
        G.generate(common + "Subject: " + item["prompt_subject"] + " ", aspect="1:1", size="1K").save(src)
    return Image.open(src).convert("RGB").resize((S, S), Image.LANCZOS)


def lens_pos(path, t):
    """道すじの点を、1つずつゆっくり通る（点の近くでゆるやかに止まる）。t＝0〜WALK 秒。"""
    n = len(path) - 1
    u = min(max(t / WALK, 0), 1) * n
    i = min(int(u), n - 1); f = u - i
    f = f * f * (3 - 2 * f)
    return (path[i][0] + (path[i + 1][0] - path[i][0]) * f, path[i][1] + (path[i + 1][1] - path[i][1]) * f)


def magnifier(im, cx, cy):
    """虫めがねの絵（柄とふち）をプログラムで描く。"""
    d = ImageDraw.Draw(im)
    r = LENS_D // 2
    ang = math.radians(45)
    ux, uy = math.cos(ang), math.sin(ang)
    x0, y0, x1, y1 = cx + ux * (r + 4), cy + uy * (r + 4), cx + ux * (r + 190), cy + uy * (r + 190)
    d.line((x0, y0, x1, y1), fill=(70, 46, 28), width=40)
    d.line((x0, y0, x1, y1), fill=(150, 100, 60), width=28)
    for px, py in ((x1, y1),):
        d.ellipse((px - 20, py - 20, px + 20, py + 20), fill=(70, 46, 28))
    d.ellipse((cx - r - 12, cy - r - 12, cx + r + 12, cy + r + 12), outline=(70, 46, 28), width=26)
    d.ellipse((cx - r - 6, cy - r - 6, cx + r + 6, cy + r + 6), outline=RIM, width=14)
    return im


def frame(item, pic, mode, t=0.0, remain=None):
    """mode：cover（黒でおおい、レンズの所だけ見える）／answer（黒を外す）。"""
    im = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(im)
    if mode == "answer":
        T.text_c(d, (W // 2, 250), "正解は", 110, INK)
        T.text_c(d, (W // 2, 395), f"「{item['answer']}」！", T.fit(d, f"「{item['answer']}」！", 150, 900), ACC)
    else:
        T.text_c(d, (W // 2, LINE_Y[0]), f"この{item['kind']}", T.fit(d, f"この{item['kind']}", 125, 900), INK)
        T.text_c(d, (W // 2, LINE_Y[1]), "なーんだ？", 125, ACC)
        T.text_c(d, (W // 2, LINE_Y[2]), SUB, SUB_SIZE, INK)
    if mode == "answer":
        im.paste(pic, (SX, SY))
        d.rectangle((SX - 3, SY - 3, SX + S + 2, SY + S + 2), outline=INK, width=6)
        return im
    sq = Image.new("RGB", (S, S), BLACK)
    px, py = lens_pos(item["path"], t)
    cx, cy = px * S, py * S
    r = LENS_D // 2
    mask = Image.new("L", (S, S), 0)
    ImageDraw.Draw(mask).ellipse((cx - r, cy - r, cx + r, cy + r), fill=255)
    sq.paste(pic, (0, 0), mask)
    im.paste(sq, (SX, SY))
    magnifier(im, SX + cx, SY + cy)
    return im


def build(item, out):
    pic = picture(item)
    seq, voices, ev, t = [], [], {}, 0.0

    def say(key, line, at=None):
        w, dur = T.voice(item["id"], key, line[1]); voices.append((w, (t if at is None else at) + 0.3, key, line)); return dur + 0.3
    intro = (item.get("intro_sub", f"この{item['kind']}、なーんだ？虫めがねで、のぞいてね。"), item["intro_voice"])
    d = say("intro", intro)
    f0 = T.speaker(frame(item, pic, "cover", 0), "normal", intro[0])
    seq.append((f0, max(5.0, d + 0.6))); t += seq[-1][1]
    # 考える時間＝虫めがねが道すじを通る12秒（15コマ/秒。のこり秒数を右上に出す）
    start = t
    step = 1 / 15
    for i in range(WALK * 15):
        tt = i * step
        seq.append((T.timer(T.speaker(frame(item, pic, "cover", tt), "think" if tt > 3 else "smile", "虫めがねの動きを見てね"), WALK - int(tt)), step))
    t += WALK
    ev["solve_end"] = t
    ans = (f"正解は、{item['answer']}でした。", f"せいかいは、{item['answer_voice']}でした。")
    ev["pon"] = [t + 0.3]
    d = say("ans", ans)
    seq.append((T.speaker(frame(item, pic, "answer"), "yay", ans[0]), max(3.5, d + 1.5))); t += seq[-1][1]
    ev["end_at"] = t
    o = item["outro"]
    SO.COMMENT["mm"] = {"line": tuple(o["line"]), "veil": [tuple(v) for v in o["veil"]]}
    cta = ("左下をクリックして、ほかの問題にも挑戦してくださいね。", "ひだりしたをクリックして、ほかのもんだいにも、ちょうせんしてくださいね。")
    cta_veil = [("ほかの問題にも", 110, (255, 255, 255)), ("挑戦！", 110, (255, 255, 255)), ("左下をクリック", 120, T.ACCENT)]
    SO.CTA, SO.CTA_VEIL = cta, cta_veil
    frames, length = build_outro(frame(item, pic, "answer"), lambda key, ln, off: say(key, ln, t + off), T.veil, T.speaker, T.arrow, comment="mm")
    seq += frames; total = t + length
    tmp = WORK / f"_{item['id']}"; tmp.mkdir(parents=True, exist_ok=True)
    lst = []
    for i, (im, dt) in enumerate(seq):
        p = tmp / f"{i:04d}.jpg"; im.save(p, quality=95); lst.append(f"file '{p}'\nduration {dt}\n")
    (tmp / "list.txt").write_text("".join(lst) + f"file '{tmp / f'{len(seq) - 1:04d}.jpg'}'\n", encoding="utf-8")
    T.mix_audio(voices, ev, total, tmp / "mix.wav")
    T.readings_check(item["id"], voices, out)
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(tmp / "list.txt"), "-i", str(tmp / "mix.wav"),
                    "-map", "0:v", "-map", "1:a", "-vf", f"fps={FPS},format=yuv420p", "-c:v", "libx264", "-crf", "20", "-c:a", "aac", "-b:a", "192k",
                    "-ar", "48000", "-t", f"{total:.2f}", "-movflags", "+faststart", str(out / f"{item['id']}.mp4")], check=True)
    for p in tmp.iterdir():
        p.unlink()
    tmp.rmdir()
    return round(total, 1)


if __name__ == "__main__":
    out = Path(sys.argv[1]).resolve(); out.mkdir(parents=True, exist_ok=True); WORK.mkdir(parents=True, exist_ok=True)
    ids = sys.argv[2:] or [i["id"] for i in DEFS]
    for it in DEFS:
        if it["id"] in ids:
            t0 = time.time()
            print(it["id"], build(it, out), "秒（作業", round(time.time() - t0), "秒）", flush=True)
