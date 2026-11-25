"""「この○○なーんだ？」虫めがねクイズ ショートの試作（2026-11-24 CEO案）。新しいファイルだけ。共通のプログラムは変えない。

使い方：python3 scripts/mushimegane_shorts.py <出力フォルダ> [id ...]   id は scripts/mushimegane_defs.json の items（kabu・tanuki・oden）
  <出力>/<id>.mp4（縦1080×1920・30fps）と readings_check.md。作業ファイルは ~/.cache/koyomi/mushimegane/。
  絵（<id>.png）が無いときだけ画像APIを1枚使う（Vertex 標準）。あれば作り直さない。
画面：季節の背景（scripts/season_theme.json の冬＝winter_A。2026-11-24 CEO厳守）に大きな見出し。中央の正方形の絵を黒でおおい、
虫めがねがゆっくり動いて、レンズの円の中だけ絵が見える（直径は正方形の約3割・道すじは約12秒）。最後に黒を外して「正解は、○○でした」。
音・声・こよみ先生・矢印は text_shorts.py の部品を使い、最後の流れは short_outro.py の build_outro。
2026-11-25 CEO：虫めがねは速めに、正方形のほぼ全部をジグザグになぞる（最後に特徴的な所）。答えの前に「わかったかな？」、黒い覆いは右下の角から「ペロッ」とめくる。
最初の画面（0:00）は暗い幕の上に大きな文字（吹き出しなし）。
"""
import json, math, random, subprocess, sys, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import text_shorts as T
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
WALK = 14                                # 虫めがねが道すじを通る秒数＝考える時間（速めに全体をなぞる）
MARGIN = 0.10                            # レンズの中心が動ける範囲の端（レンズの半径＝正方形の15%）
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


def make_route(item, seed):
    """気まぐれに動く道すじ（2026-11-25 CEO）。正方形を g×g のます目に分け、ます目の中心を順不同で回る。
    出発は start に近います目（当てにくい所）。feature（特徴的な所）の近くのます目は最後に回り、最後は finale の点。
    ます目の順は、近い3つのうちから乱数（種＝seed）で選ぶ。各点は少しずらし、点と点の間はなめらかな曲線（3次スプライン）でつなぐ。
    戻り値：曲線上の点の列（0〜1）。同じ seed なら同じ道すじ。"""
    import numpy as np
    from scipy.interpolate import CubicSpline
    rnd = random.Random(seed)
    g = item.get("grid", 4)
    cs = np.linspace(0.13, 0.87, g)
    cells = [(x, y) for y in cs for x in cs]
    fx, fy = item["feature"][:2]; fr = item.get("feature_r", 0.24)
    near_f = [c for c in cells if math.hypot(c[0] - fx, c[1] - fy) <= fr]
    rest = [c for c in cells if c not in near_f]
    cur = min(rest, key=lambda c: math.hypot(c[0] - item["start"][0], c[1] - item["start"][1]))
    order = [cur]; rest.remove(cur)
    skip = item.get("skip", 0)                       # 回らずに飛ばすます目の数（道すじを短くする）
    for _ in range(skip):
        if len(rest) > 4:
            rest.pop(rnd.randrange(len(rest)))
    while rest:
        nb = sorted(rest, key=lambda c: math.hypot(c[0] - cur[0], c[1] - cur[1]))[:3]
        cur = rnd.choices(nb, weights=[0.6, 0.3, 0.1][:len(nb)])[0]
        order.append(cur); rest.remove(cur)
    fin = tuple(item["finale"])
    ff = list(near_f)
    while ff:
        nxt = min(ff, key=lambda c: math.hypot(c[0] - cur[0], c[1] - cur[1]) - 0.0 * math.hypot(c[0] - fin[0], c[1] - fin[1])) if len(ff) > 1 else ff[0]
        order.append(nxt); ff.remove(nxt); cur = nxt
    pts = [(x + rnd.uniform(-0.035, 0.035), y + rnd.uniform(-0.035, 0.035)) for x, y in order] + [fin]
    pts[0] = (min(max(pts[0][0], 0.1), 0.9), min(max(pts[0][1], 0.1), 0.9))
    P = np.array(pts)
    ch = np.r_[0, np.cumsum(np.hypot(*np.diff(P, axis=0).T))]
    ss = np.linspace(0, ch[-1], int(ch[-1] / 0.004))
    cx, cy = CubicSpline(ch, P[:, 0], bc_type="natural"), CubicSpline(ch, P[:, 1], bc_type="natural")
    D = np.stack([np.clip(cx(ss), 0.05, 0.95), np.clip(cy(ss), 0.05, 0.95)], axis=1)
    return D


def route_stats(item, D, speed_px=None):
    """道すじの長さ・のぞいた面積・歩く秒数・特徴的な所を早く見せていないか。"""
    import numpy as np
    L = float(np.hypot(*np.diff(D, axis=0).T).sum())
    n = S // 6
    yy, xx = np.mgrid[0:n, 0:n]
    seen = np.zeros((n, n), bool)
    r = (LENS_D / 2) / 6
    for px, py in D[::5]:
        seen |= (xx + .5 - px * n) ** 2 + (yy + .5 - py * n) ** 2 <= r * r
    cov = float(seen.mean())
    cum = np.r_[0, np.cumsum(np.hypot(*np.diff(D, axis=0).T))]
    fx, fy = item["feature"][:2]
    dist = np.hypot(D[:, 0] - fx, D[:, 1] - fy)
    early = dist[cum < 0.88 * cum[-1]].min()           # 最後の1割より前に、特徴的な所にどこまで近づくか
    w = L * S / (speed_px or item.get("speed_px", 135))
    return {"length": L, "coverage": cov, "walk": w, "early_min_dist": float(early)}


def build_path(item):
    """道すじの点（0〜1）。seed があれば make_route（気まぐれな曲線）。なければ path（点の列）か rows（ジグザグ）。"""
    if "seed" in item:
        return [tuple(p) for p in make_route(item, item["seed"])]
    if "path" in item:
        pts = [tuple(p) for p in item["path"]]
    else:
        pts = []
        for y, dr in item["rows"]:
            xs = (MARGIN, 1 - MARGIN) if dr == "LR" else (1 - MARGIN, MARGIN)
            pts += [(xs[0], y), (xs[1], y)]
        if item.get("finale"):
            pts.append(tuple(item["finale"]))
    for _ in range(2):                                   # Chaikin：角を丸める（端の点は残す）
        q = [pts[0]]
        for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
            q += [(0.75 * x0 + 0.25 * x1, 0.75 * y0 + 0.25 * y1), (0.25 * x0 + 0.75 * x1, 0.25 * y0 + 0.75 * y1)]
        pts = q + [pts[-1]]
    return pts


_PATHS = {}


def _prep(item):
    if item["id"] not in _PATHS:
        pts = build_path(item)
        seg = [math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(pts, pts[1:])]
        cum = [0.0]
        for l in seg:
            cum.append(cum[-1] + l)
        if "seed" in item:
            W = max(1, round(cum[-1] * S / item.get("speed_px", 135)))      # 平均の速さが speed_px になる秒数
        else:
            W = WALK
        _PATHS[item["id"]] = (pts, cum, W)
    return _PATHS[item["id"]]


def walk_of(item):
    """虫めがねが道すじを歩く秒数（考える時間）。seed の道すじは、長さと速さ（speed_px）から決まる。"""
    return _prep(item)[2]


def lens_pos(item, t):
    """道すじを通る。seed の道すじは、速さを少しゆらす（±25%・周期約5秒）。それ以外は一定の速さ（最初と最後は少しゆっくり）。t＝0〜歩く秒数。"""
    import bisect
    pts, cum, W = _prep(item)
    u = min(max(t / W, 0), 1)
    if "seed" in item:
        ph = (item["seed"] % 7) * 0.9
        w = 2 * math.pi / 5.0
        G = lambda x: x - 0.25 / w * (math.cos(w * x + ph) - math.cos(ph))          # 速さ 1+0.25sin(w t+ph) の積分
        u = G(u * W) / G(W)
    else:
        u = u * u * (3 - 2 * u) * 0.35 + u * 0.65
    d = u * cum[-1]
    i = min(max(bisect.bisect_right(cum, d) - 1, 0), len(cum) - 2)
    f = (d - cum[i]) / max(cum[i + 1] - cum[i], 1e-9)
    return (pts[i][0] + (pts[i + 1][0] - pts[i][0]) * f, pts[i][1] + (pts[i + 1][1] - pts[i][1]) * f)


def coverage(item):
    """道すじでレンズがのぞけた面積の割合（正方形に対して）。0.02秒ごとのレンズの円を重ねて数える。"""
    import numpy as np
    n = S // 4
    yy, xx = np.mgrid[0:n, 0:n]
    seen = np.zeros((n, n), bool)
    r = (LENS_D / 2) / 4
    W = walk_of(item)
    for i in range(int(W / 0.02) + 1):
        px, py = lens_pos(item, i * 0.02)
        seen |= (xx + .5 - px * n) ** 2 + (yy + .5 - py * n) ** 2 <= r * r
    return float(seen.mean())


def mean_speed(item):
    """平均の速さ（px/秒）と、いちばん遅い・速い所。"""
    W = walk_of(item); pts = [lens_pos(item, i * 0.1) for i in range(int(W / 0.1) + 1)]
    v = [math.hypot(b[0] - a[0], b[1] - a[1]) * S / 0.1 for a, b in zip(pts, pts[1:])]
    return sum(v) / len(v), min(v), max(v)


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


def peel_square(pic, L):
    """黒い覆いを右下の角から「ペロッ」とめくる。折り目は x+y=L の線（L が 2S→0 で、角から左上へ進む）。
    めくれた部分は折り返されて、覆いの上に灰色の裏側として重なる。折り目のそばに影をつける。"""
    import numpy as np
    yy, xx = np.mgrid[0:S, 0:S].astype(np.float32)
    ssum = xx + yy
    P = np.array(pic).astype(np.float32)
    out = np.empty_like(P); out[:] = BLACK
    d_rev = np.clip((ssum - L) / 1.414, 0, None)                      # 折り目から、見えている絵までの距離
    rev = ssum >= L
    shade = 1 - 0.40 * np.exp(-d_rev / 28)                              # 折り目のそばは影
    out[rev] = (P * shade[..., None])[rev]
    rx, ry = L - yy, L - xx                                              # 折り返された先（もとの位置）
    flap = (~rev) & (rx >= 0) & (rx < S) & (ry >= 0) & (ry < S)
    d_f = np.clip((L - ssum) / 1.414, 0, None)
    g = 150 - 85 * np.clip(d_f / 90, 0, 1)                             # 折り目で明るく、遠ざかると暗い（紙の裏側）
    out[flap] = np.stack([g, g * 0.99, g * 0.97], axis=-1)[flap]
    edge = (~rev) & (~flap) & (d_f < 14)                               # 折り返しの先の影
    return Image.fromarray(out.clip(0, 255).astype(np.uint8))


def head(d, mode, item):
    if mode == "answer":
        T.text_c(d, (W // 2, 250), "正解は", 110, INK)
        T.text_c(d, (W // 2, 395), f"「{item['answer']}」！", T.fit(d, f"「{item['answer']}」！", 150, 900), ACC)
    elif mode in ("ready", "peel"):
        T.text_c(d, (W // 2, 330), "わかったかな？", T.fit(d, "わかったかな？", 150, 900), ACC)
    else:
        T.text_c(d, (W // 2, LINE_Y[0]), f"この{item['kind']}", T.fit(d, f"この{item['kind']}", 125, 900), INK)
        T.text_c(d, (W // 2, LINE_Y[1]), "なーんだ？", 125, ACC)
        T.text_c(d, (W // 2, LINE_Y[2]), SUB, SUB_SIZE, INK)


def frame(item, pic, mode, t=0.0, remain=None, L=None):
    """mode：cover（黒でおおい、レンズの所だけ見える。t＝秒）／ready（歩き終わり。「わかったかな？」）／peel（めくれる途中。L＝折り目）／answer（黒を外す）。"""
    im = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(im)
    head(d, mode, item)
    if mode == "answer":
        im.paste(pic, (SX, SY))
        d.rectangle((SX - 3, SY - 3, SX + S + 2, SY + S + 2), outline=INK, width=6)
        return im
    if mode == "peel":
        im.paste(peel_square(pic, L), (SX, SY))
        d.rectangle((SX - 3, SY - 3, SX + S + 2, SY + S + 2), outline=INK, width=6)
        return im
    sq = Image.new("RGB", (S, S), BLACK)
    px, py = lens_pos(item, walk_of(item) if mode == "ready" else t)
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
    intro = (item.get("intro_sub", f"この{item['kind']}、なーんだ？虫めがねで、のぞいてみてね。"), item["intro_voice"])
    d = say("intro", intro)
    # 最初の画面（0:00＝サムネ）：暗い幕の上に大きな文字。吹き出しは出さない（こよみ先生は今の位置）
    vl = T.intro_lines([f"この{item['kind']}", "なーんだ？", ["虫めがねで", "accent"], ["のぞいてみてね", "accent"]], explicit=True)
    seq.append((T.speaker(T.veil(frame(item, pic, "cover", 0), vl, T.INTRO_GAP), "normal", None), max(5.0, d + 0.6))); t += seq[-1][1]
    # 考える時間＝虫めがねが道すじを通る（15コマ/秒。のこり秒数を右上に出す）
    step = 1 / 15
    W = walk_of(item)
    w_tap, d_tap = T.voice(item["id"], "tap", T.TAP[1])     # 出題中（残り約10秒）に、声と吹き出しで「わかったら、画面を2回タップしてね」（2026-11-25 CEO）
    off_tap = T.tap_offset(W, d_tap)
    voices.append((w_tap, t + off_tap, "tap", T.TAP))
    for i in range(W * 15):
        tt = i * step
        seq.append((T.timer(T.speaker(frame(item, pic, "cover", tt), "think" if tt > 3 else "smile", T.TAP[0] if T.tap_window(off_tap, d_tap, tt, step) else None), W - int(tt)), step))
    t += W
    ev["solve_end"] = t
    # わかったかな？（ワンクッション。声と大きな文字）→ 黒い覆いをめくる → 正解
    rd = ("わかったかな？", "わかったかな？")
    d = say("ready", rd)
    seq.append((T.speaker(frame(item, pic, "ready"), "smile", rd[0]), max(2.0, d + 0.5))); t += seq[-1][1]
    n_peel = 24
    for k in range(n_peel):
        u = (k + 1) / n_peel
        u = u * u * (3 - 2 * u)
        seq.append((T.speaker(frame(item, pic, "peel", L=2 * S * (1 - u) + 0.0), "surprise", None), 0.05))
    t += n_peel * 0.05
    ans = (f"正解は、{item['answer']}でした。", f"せいかいは、{item['answer_voice']}でした。")
    ev["pon"] = [t + 0.3]
    d = say("ans", ans)
    seq.append((T.speaker(frame(item, pic, "answer"), "yay", ans[0]), max(3.5, d + 1.5))); t += seq[-1][1]
    ev["end_at"] = t
    cta = ("左下をクリックして、ほかの問題にも挑戦してくださいね。", "ひだりしたをクリックして、ほかのもんだいにも、ちょうせんしてくださいね。")
    cta_veil = [("ほかの問題にも", 110, (255, 255, 255)), ("挑戦！", 110, (255, 255, 255)), ("左下をクリック", 120, T.ACCENT)]
    frames, length = build_outro(frame(item, pic, "answer"), lambda key, ln, off: say(key, ln, t + off), T.veil, T.speaker, T.arrow, comment="text", cta=cta, cta_veil=cta_veil)   # コメントは3本とも「何秒でわかったか」（2026-11-25 CEO）
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
