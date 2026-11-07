"""問題の絵を作る（make_episode.py から呼ぶ）。縦長（約8:9）で、画面では左右に960×1080ずつ並べる。
プロンプト・違い・範囲は outputs/<回>/plan.json から読む。
答えの範囲（box）・種類・物の大きさは plan.json の questions[].diffs で管理する（座標は 8:9 に切り抜いた高解像度の絵のピクセル）。

作り方:
  Gemini（gemini-3-pro-image、2K）に aspectRatio "4:5" で描かせ、上下を同じだけ切って 8:9 にする（拡大処理は使わない）。
  画面に出すときは 960×1080 に縮める（引き伸ばしはしない）。

使い方（作業フォルダに途中画像を置く。キャッシュがあれば API は呼ばない）:
  export KOYOMI_IMAGE_USAGE_LOG=outputs/2026-11-03_001/image_usage.jsonl
  python3 scripts/make_episode.py <回> pictures base <問> <作業>          # 元の絵（API 1回）
  python3 scripts/make_episode.py <回> pictures edit <問> <作業> [版]     # 違い3つをまとめて描き直し（API 1回）
  python3 scripts/make_episode.py <回> pictures retry <問> <版> <作業>     # うまくいかない違いだけ、切り出して描き直す（予備 1回）
  python3 scripts/make_episode.py <回> pictures compose <問> <作業> <出力>   # 範囲ごとに貼り戻す（API 0回）
  python3 scripts/make_episode.py <回> pictures answers <作業> <出力>        # answers.json を書く
  python3 scripts/make_episode.py <回> pictures patches <作業> <出力>        # 描き直しの使う範囲だけを <出力>/edits/ に残す
  （作業フォルダがなくても、<出力>/qN_a.png と <出力>/edits/ から compose で qN_b.png を作り直せる）
"""
import json, sys
from pathlib import Path
from PIL import Image, ImageChops, ImageDraw, ImageFilter
sys.path.insert(0, str(Path(__file__).parent))
from make_differences import feather_mask
from episode_plan import plan, questions

SCREEN_W, SCREEN_H = 1920, 1080
PIC_W, PIC_H = 960, 1080          # 画面での絵1枚の大きさ
SAFE_Y = (54, 918)                # 画面での「違いを置いてよい」縦の範囲（上の帯5%・下の字幕15%を避ける）

_P = plan()
_I = _P["images"]
STYLE = _I["style"]
KEEP_ALT, KEEP_REMOVE = _I["keep_alt"], _I["keep_remove"]
_Q = questions()
SCENES = {q: Q["prompt"] for q, Q in _Q.items()}
EDITS = {q: Q["edit_prompt"] for q, Q in _Q.items()}
# うまくいかなかった違いだけを、範囲のまわりを切り出して描き直す（予備の呼び出し）。plan.json の questions[].retries
RETRY = {(q, v): r for q, Q in _Q.items() for v, r in Q.get("retries", {}).items()}
# AIで描き直さず、プログラムで作る違い（plan.json の questions[].program_edits：{版: スクリプト}）。
# スクリプトは「python3 <スクリプト> <作業フォルダ>」で <作業>/edit_<問>_<版>.png を書く。
PROGRAM_EDITS = {(q, v): sc for q, Q in _Q.items() for v, sc in Q.get("program_edits", {}).items()}
QUESTIONS = {q: (Q["scene"], Q["level"], Q.get("hint_diff")) for q, Q in _Q.items()}
# 画面に出す範囲（x0, y0, x1, y1）。8:9 のまま、Gemini が絵の左右に残した白いふちを切り落とす（縮めるだけ。引き伸ばしはしない）
CONTENT = {q: tuple(Q["content_box"]) for q, Q in _Q.items()}
LEVEL_RANGE = {"初級": (3.0, 4.0), "中級": (2.0, 3.0), "上級": (1.5, 2.0)}  # 画面幅に対する%（concept.md）


def diffs():
    return {q: Q["diffs"] for q, Q in _Q.items()}


def crop_89(im):
    """4:5 の絵の上下を同じだけ切って 8:9 にする（拡大はしない）。"""
    w, h = im.size
    ch = round(w * 9 / 8)
    top = (h - ch) // 2
    return im.crop((0, top, w, top + ch)), top


def base(q, work):
    w = Path(work)
    out = w / f"q{q}_a.png"
    if out.exists():
        return Image.open(out)
    src = w / f"q{q}_src.png"
    if not src.exists():
        from gemini_image import generate
        generate(STYLE + SCENES[q], model=_I["model"], aspect=_I["aspect"], size=_I["size"]).save(src)
    im = Image.open(src).convert("RGB")
    a, top = crop_89(im)
    a.save(out)
    (w / f"q{q}_crop.json").write_text(json.dumps({"src_size": im.size, "crop_top": top, "size": a.size}), encoding="utf-8")
    return a


def edit(q, work, ver="1"):
    w = Path(work)
    out = w / f"edit_{q}_{ver}.png"
    if out.exists():
        return Image.open(out)
    from gemini_image import generate
    src = Image.open(w / f"q{q}_src.png").convert("RGB")
    prompt = EDITS[q] + KEEP_ALT + KEEP_REMOVE
    ed = generate(prompt, images=[src], model=_I["model"], aspect=_I["aspect"], size=_I["size"])
    if ed.size != src.size:
        ed = ed.resize(src.size, Image.LANCZOS)
    ed.save(w / f"edit_{q}_{ver}_src.png")
    crop_89(ed)[0].save(out)
    (w / f"edit_{q}_{ver}.prompt.txt").write_text(prompt, encoding="utf-8")
    return Image.open(out)


def base_batch(qs, work):
    """元の絵をまとめてバッチで作る（約半額・急がないとき）。作業フォルダにあるものは頼まない。"""
    w = Path(work)
    qs = [q for q in qs if not (w / f"q{q}_src.png").exists()]
    if not qs:
        return
    from gemini_image import generate_batch
    res = generate_batch({f"base{q}": {"prompt": STYLE + SCENES[q], "aspect": _I["aspect"], "size": _I["size"]} for q in qs},
                         model=_I["model"], name="koyomi-base")
    for q in qs:
        if f"base{q}" in res:
            res[f"base{q}"].save(w / f"q{q}_src.png")
            base(q, w)


def edit_batch(qs, work, ver="1"):
    """描き直し（違い3つをまとめて）をバッチで頼む。元の絵（q{q}_src.png）がある問だけ。"""
    w = Path(work)
    qs = [q for q in qs if not (w / f"edit_{q}_{ver}.png").exists() and (w / f"q{q}_src.png").exists()]
    if not qs:
        return
    from gemini_image import generate_batch
    srcs = {q: Image.open(w / f"q{q}_src.png").convert("RGB") for q in qs}
    prompt = lambda q: EDITS[q] + KEEP_ALT + KEEP_REMOVE
    res = generate_batch({f"edit{q}": {"prompt": prompt(q), "images": [srcs[q]], "aspect": _I["aspect"], "size": _I["size"]}
                          for q in qs}, model=_I["model"], name="koyomi-edit")
    for q in qs:
        ed = res.get(f"edit{q}")
        if ed is None:
            continue
        if ed.size != srcs[q].size:
            ed = ed.resize(srcs[q].size, Image.LANCZOS)
        ed.save(w / f"edit_{q}_{ver}_src.png")
        crop_89(ed)[0].save(w / f"edit_{q}_{ver}.png")
        (w / f"edit_{q}_{ver}.prompt.txt").write_text(prompt(q), encoding="utf-8")


def program_edit(q, ver, work):
    """プログラムで作る違い（画像APIは使わない）。"""
    import subprocess
    out = Path(work) / f"edit_{q}_{ver}.png"
    if not out.exists():
        subprocess.run([sys.executable, PROGRAM_EDITS[(q, ver)], str(work)], check=True)
    return Image.open(out)


def retry(q, ver, work):
    w = Path(work)
    out = w / f"edit_{q}_{ver}.png"
    if out.exists():
        return Image.open(out)
    from gemini_image import generate
    r = RETRY[(q, ver)]
    a = Image.open(w / f"q{q}_a.png").convert("RGB")
    crop = a.crop(r["crop"])
    im = generate(r["prompt"], images=[crop], model=_I["model"], aspect=r["aspect"], size=_I["size"]).resize(crop.size, Image.LANCZOS)
    ed = a.copy(); ed.paste(im, r["crop"][:2]); ed.save(out)
    (w / f"edit_{q}_{ver}.prompt.txt").write_text(r["prompt"], encoding="utf-8")
    return ed


PATCH_MARGIN = 48   # 描き直しの絵から、範囲のまわりこれだけ広く切り出して残す（ぼかしの広がりより大きい）


def patch_path(out_dir, q, d):
    return Path(out_dir) / "edits" / f"q{q}_d{d['id']}_{d.get('src', '1')}.png"


def export_patches(work, out_dir):
    """描き直しの絵（作業フォルダ）から、使う範囲のまわりだけを切り出して成果物フォルダの edits/ に残す（再現用・容量を小さく）。"""
    for q, ds in diffs().items():
        for d in ds:
            f = Path(work) / f"edit_{q}_{d.get('src', '1')}.png"
            if not f.exists():      # 作業フォルダにない描き直しは、すでに edits/ に残してある
                continue
            ed = Image.open(f).convert("RGB")
            x0, y0, x1, y1 = d["box"]; m = PATCH_MARGIN
            r = (max(0, x0 - m), max(0, y0 - m), min(ed.width, x1 + m), min(ed.height, y1 + m))
            p = patch_path(out_dir, q, d); p.parent.mkdir(parents=True, exist_ok=True)
            ed.crop(r).save(p)
            p.with_suffix(".json").write_text(json.dumps({"offset": r[:2]}), encoding="utf-8")


def edited_image(q, d, work, out_dir, a):
    """貼り戻しに使う描き直しの絵。作業フォルダになければ、成果物フォルダの edits/ の切り出しから組み立てる。"""
    f = Path(work) / f"edit_{q}_{d.get('src', '1')}.png"
    if not f.exists() and (q, d.get("src", "1")) in PROGRAM_EDITS and not patch_path(out_dir, q, d).exists():
        program_edit(q, d.get("src", "1"), work)
    if f.exists():
        return Image.open(f).convert("RGB")
    p = patch_path(out_dir, q, d)
    ed = a.copy(); ed.paste(Image.open(p).convert("RGB"), tuple(json.loads(p.with_suffix(".json").read_text())["offset"]))
    return ed


MARGIN_PROMPT = ("Edit this illustration: the left and right edges of the picture are blank white paper margins. "
                 "Fill only those blank white margins with a natural continuation of the scene in exactly the same "
                 "picture-book watercolor style, so the painting reaches the very edge of the picture on both sides. "
                 "Do not add any new objects, people, animals or text in the margins; continue only the background "
                 "(trees, ground, sky, walls, floor). Do not change anything inside the painted area.")


def margin_strips(q, out_dir):
    return [Path(out_dir) / "edits" / f"q{q}_margin_{side}.png" for side in ("left", "right")]


def fill_margins(q, work, out_dir):
    """plan.json の questions[].margins（左右の白いふちの幅 px）を、AIに描き足させる（画像API 1回）。
    描き足した左右の帯だけを <回>/edits/ に残し、compose で左右の絵（a・b）の両方に同じものを貼る（新しい違いは生まれない）。"""
    M = _Q[q].get("margins")
    if not M or all(p.exists() for p in margin_strips(q, out_dir)):
        return
    w = Path(work)
    src = Image.open(w / f"q{q}_src.png").convert("RGB")
    from gemini_image import generate
    ed = generate(MARGIN_PROMPT, images=[src], model=_I["model"], aspect=_I["aspect"], size=_I["size"])
    if ed.size != src.size:
        ed = ed.resize(src.size, Image.LANCZOS)
    ed.save(w / f"q{q}_margins_src.png")
    full = crop_89(ed)[0]
    f = M.get("feather", 24)
    L, R = M["left"] + f + 8, M["right"] + f + 8
    p_left, p_right = margin_strips(q, out_dir)
    p_left.parent.mkdir(parents=True, exist_ok=True)
    full.crop((0, 0, L, full.height)).save(p_left)
    full.crop((full.width - R, 0, full.width, full.height)).save(p_right)


def apply_margins(q, im, out_dir):
    """描き足した左右の帯を、ぼかしてつなぎながら貼る。"""
    M = _Q[q].get("margins")
    if not M:
        return im
    p_left, p_right = margin_strips(q, out_dir)
    f = M.get("feather", 24)
    im = im.copy()
    for p, side in ((p_left, "left"), (p_right, "right")):
        strip = Image.open(p).convert("RGB")
        x0 = 0 if side == "left" else im.width - strip.width
        edge = M[side]
        mask = Image.new("L", strip.size, 0)
        dr = ImageDraw.Draw(mask)
        for i in range(strip.width):    # 白いふちの中は全部、つなぎ目 f px はなだらかに
            dist = (edge - i) if side == "left" else (i - (strip.width - edge))
            v = 255 if dist >= 0 else max(0, int(255 * (1 + dist / f)))
            dr.line((i, 0, i, strip.height), fill=v)
        im.paste(strip, (x0, 0), mask)
    return im


def compose(q, work, out_dir):
    """範囲ごとに貼り戻す。元の絵は作業フォルダの q{q}_a.png、なければ成果物フォルダの q{q}_a.png を使う。"""
    w = Path(work)
    src_a = w / f"q{q}_a.png" if (w / f"q{q}_a.png").exists() else Path(out_dir) / f"q{q}_a.png"
    a = Image.open(src_a).convert("RGB")
    if _Q[q].get("margins"):
        fill_margins(q, w, out_dir)
        a = apply_margins(q, a, out_dir)
    b = a.copy()
    for d in diffs()[q]:
        ed = edited_image(q, d, work, out_dir, a)
        m = feather_mask(a.size, d["box"], d.get("feather", 16))
        for k in d.get("keep", []):  # 範囲の中でも、元の絵のまま残す所
            m = ImageChops.subtract(m, feather_mask(a.size, k, 10))
        b = Image.composite(ed, b, m)
    out = Path(out_dir); out.mkdir(parents=True, exist_ok=True)
    a.save(out / f"q{q}_a.png"); b.save(out / f"q{q}_b.png")
    return a, b


def outside_diff(a, b, boxes, thr=15):
    """範囲の外で差が thr を超える画素の数と、範囲からの最大距離（px）。"""
    import numpy as np
    d = np.asarray(ImageChops.difference(a, b).convert("L")) > thr
    ys, xs = np.nonzero(d)
    dist = np.full(len(xs), 1e9)
    for x0, y0, x1, y1 in boxes:
        dx = np.maximum(np.maximum(x0 - xs, xs - x1), 0); dy = np.maximum(np.maximum(y0 - ys, ys - y1), 0)
        dist = np.minimum(dist, np.hypot(dx, dy))
    out = dist > 0
    return int(out.sum()), float(dist[out].max()) if out.any() else 0.0


def answers(work, out_dir):
    D = diffs()
    res = {"screen": {"size": [SCREEN_W, SCREEN_H], "picture_size_on_screen": [PIC_W, PIC_H],
                      "safe_y_on_screen": list(SAFE_Y), "level_range_pct_of_screen_width": LEVEL_RANGE},
           "note": "box_px・circle_px は 8:9 に切り抜いた高解像度の絵（qN_a.png、1856×2088）のピクセル。"
                   "content_px はそのうち画面に出す範囲（白いふちを除いた8:9）。*_screen は画面の上での座標（右の絵は x に960を足す）。"
                   "object_screen_width_pct は、変わる物そのものの幅を画面幅で割った値。",
           "questions": []}
    for q, (scene, level, hint) in QUESTIONS.items():
        a = Image.open(Path(out_dir) / f"q{q}_a.png").convert("RGB")
        b = Image.open(Path(out_dir) / f"q{q}_b.png").convert("RGB")
        cx0, cy0, cx1, cy1 = CONTENT[q]
        assert abs((cy1 - cy0) / (cx1 - cx0) - 9 / 8) < 0.002 and cx1 - cx0 >= PIC_W and cy1 - cy0 >= PIC_H
        s = PIC_W / (cx1 - cx0)
        to_scr = lambda r: [round((r[0] - cx0) * s), round((r[1] - cy0) * s), round((r[2] - cx0) * s), round((r[3] - cy0) * s)]
        n, mx = outside_diff(a, b, [d["box"] for d in D[q]])
        lo, hi = LEVEL_RANGE[level]
        qa = []
        for d in D[q]:
            pct = round(d["object_w"] * s / SCREEN_W * 100, 2)
            sb = to_scr(d["box"])
            ca, cb = d.get("circle_a", d.get("circle", d["box"])), d.get("circle_b", d.get("circle", d["box"]))
            qa.append({"id": d["id"], "type": d["type"], "label": d["label"], "line": d["line"],
                       "box_px": d["box"], "box_screen": sb,
                       "circle_a_screen": to_scr(ca), "circle_b_screen": to_scr(cb),
                       "object_w_px": d["object_w"], "object_screen_width_pct": pct,
                       "in_level_range": lo <= pct <= hi,
                       "in_safe_y": SAFE_Y[0] <= sb[1] and sb[3] <= SAFE_Y[1] and 0 <= sb[0] and sb[2] <= PIC_W,
                       "edit_version": d.get("src", "1"), "made_by": "program" if d.get("src") == "flip" else "gemini",
                       "note": d.get("note", "")})
        res["questions"].append({"q": q, "scene": scene, "level": level, "hint_diff": hint,
                                 "image_size": list(a.size), "content_px": list(CONTENT[q]), "scale_to_screen": round(s, 5),
                                 "outside_box_pixels_diff_gt15": n, "outside_box_max_distance_px": round(mx, 1),
                                 "answers": qa})
    Path(out_dir, "answers.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    return res


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "base":
        base(int(sys.argv[2]), sys.argv[3])
    elif cmd == "edit":
        edit(int(sys.argv[2]), sys.argv[3], *(sys.argv[4:5] or ["1"]))
    elif cmd == "retry":
        retry(int(sys.argv[2]), sys.argv[3], sys.argv[4])
    elif cmd == "compose":
        compose(int(sys.argv[2]), sys.argv[3], sys.argv[4])
    elif cmd == "patches":
        export_patches(sys.argv[2], sys.argv[3])
    elif cmd == "answers":
        r = answers(sys.argv[2], sys.argv[3])
        for Q in r["questions"]:
            print(Q["q"], Q["level"], Q["outside_box_pixels_diff_gt15"], Q["outside_box_max_distance_px"],
                  [(a["id"], a["object_screen_width_pct"], a["in_level_range"], a["in_safe_y"]) for a in Q["answers"]])
