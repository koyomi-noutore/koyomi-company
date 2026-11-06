"""第1回（001・作り直し版 2026-11-05）の問題の絵を作る。縦長（約8:9）で、画面では左右に960×1080ずつ並べる。
プロンプトは outputs/2026-11-03_001/plan.md の2章・3章をそのまま使う。
答えの範囲（box）・種類・物の大きさは scripts/ep001_diffs.json で管理する（座標は 8:9 に切り抜いた高解像度の絵のピクセル）。

作り方:
  Gemini（gemini-3-pro-image、2K）に aspectRatio "4:5" で描かせ、上下を同じだけ切って 8:9 にする（拡大処理は使わない）。
  画面に出すときは 960×1080 に縮める（引き伸ばしはしない）。

使い方（作業フォルダに途中画像を置く。キャッシュがあれば API は呼ばない）:
  export KOYOMI_IMAGE_USAGE_LOG=outputs/2026-11-03_001/image_usage.jsonl
  python3 scripts/ep001_pictures.py base    <問> <作業>          # 元の絵（API 1回）
  python3 scripts/ep001_pictures.py edit    <問> <作業> [版]     # 違い3つをまとめて描き直し（API 1回）
  python3 scripts/ep001_pictures.py retry   <問> <版> <作業>     # うまくいかない違いだけ、切り出して描き直す（予備 1回）
  python3 scripts/ep001_pictures.py compose <問> <作業> <出力>   # 範囲ごとに貼り戻す（API 0回）
  python3 scripts/ep001_pictures.py answers <作業> <出力>        # answers.json を書く
  python3 scripts/ep001_pictures.py patches <作業> <出力>        # 描き直しの使う範囲だけを <出力>/edits/ に残す
  （作業フォルダがなくても、<出力>/qN_a.png と <出力>/edits/ から compose で qN_b.png を作り直せる）
"""
import json, sys
from pathlib import Path
from PIL import Image, ImageChops, ImageDraw, ImageFilter
sys.path.insert(0, str(Path(__file__).parent))
from make_differences import feather_mask

SCREEN_W, SCREEN_H = 1920, 1080
PIC_W, PIC_H = 960, 1080          # 画面での絵1枚の大きさ
SAFE_Y = (54, 918)                # 画面での「違いを置いてよい」縦の範囲（上の帯5%・下の字幕15%を避ける）

STYLE = ("A warm Japanese picture-book illustration in soft watercolor with gentle colored-pencil outlines, "
         "like a cozy picture book for all ages, drawn with clear, crisp details. Autumn palette: persimmon "
         "orange, maple red, ginkgo yellow, warm browns and soft greens. Natural, hand-drawn, slightly rounded "
         "shapes; not geometric, not flat vector, not photorealistic. PORTRAIT-ISH composition, slightly taller "
         "than wide (about 8:9); the scene is arranged vertically, with a near foreground, a middle ground and "
         "a background stacked from bottom to top. Keep the top 10% of the picture simple (sky, eaves or "
         "leaves only) and the bottom 20% simple (plain floor, ground or pavement only): put every main object "
         "listed below in the middle part of the picture. No people. Absolutely no text, letters, numbers, "
         "logos or symbols anywhere, including on signs, curtains, boxes and lanterns. The main objects are "
         "clearly drawn, separated from each other with a little space around each, and fully visible (not "
         "cut off by the picture edge and not hidden behind other objects).\n")

# plan.md 3章の【意見】（第1回の制作と同じ）
KEEP_ALT = (" Keep everything else in the picture exactly the same: same composition, same position of every object, "
            "same colors, same style. Do not add or remove anything else. Leave no faint outline, ghost or smudge. No text.")
KEEP_REMOVE = (" Where an object is removed, fill the area naturally with what would be behind it, "
               "and leave no faint outline, ghost or smudge of the removed object.")

SCENES = {
    1: ("Scene: looking out from inside an old Japanese house across a wooden veranda (engawa) into a small "
        "autumn garden in warm late-afternoon light. Background (upper middle): a persimmon tree with orange "
        "fruit and a moss-covered stone lantern among red maple leaves. Middle: the wooden veranda. Main "
        "objects: (1) a calico cat sleeping on a flat floor cushion on the veranda, with its striped tail "
        "curled neatly around its body; (2) a round wooden tray on the veranda holding exactly three "
        "persimmons, a brown clay teapot and two teacups, with a little empty space on the tray; (3) a large "
        "woven bamboo basket standing on the veranda; (4) a flat stepping stone just below the veranda edge "
        "with a pair of wooden geta sandals on it, the pair about one fourteenth of the picture width; "
        "(5) a few strings of dried persimmons hanging from the eaves at the upper right, kept below the top "
        "tenth of the picture. Each persimmon on the tray is about one sixteenth of the picture width."),
    2: ("Scene: a narrow old Japanese shopping street in autumn, seen from the street in front of a small "
        "fruit and vegetable shop with a wooden front and a tiled roof; the street goes back into the "
        "distance at the upper left. Main objects: (1) a wooden display stand in front of the shop with flat "
        "bamboo baskets of persimmons and sweet potatoes; (2) one big green Japanese pumpkin (kabocha) "
        "sitting alone on the stand, about one thirteenth of the picture width, with empty space next to it; "
        "(3) a round flat bamboo basket full of chestnuts on the stand, about one twelfth of the picture "
        "width; (4) an old-fashioned black bicycle with a wire front basket parked in front of the shop "
        "(the basket about one fourteenth of the picture width); (5) a Shiba dog sitting on the pavement; "
        "(6) a plain indigo shop curtain (noren) with no writing and no pattern; (7) a potted yellow "
        "chrysanthemum by the door; a few ginkgo leaves on the stone pavement. Paper lanterns, if any, are "
        "completely blank. The neighbouring shops are simple and have no writing."),
    3: ("Scene: a gentle mountain walking path in autumn, with rough stone steps winding up through red "
        "maple and yellow trees toward misty hills at the top. Main objects: (1) a wooden bench beside the "
        "path with a small red rucksack and a folded white hand towel (tenugui) with a blue polka-dot pattern "
        "lying on it, the towel about one eighteenth of the picture width; (2) a tree stump with one brown "
        "squirrel sitting on it, facing right and holding an acorn, about one eighteenth of the picture "
        "width; (3) a cluster of exactly three brown mushrooms at the foot of a maple tree, each mushroom "
        "about one twentieth of the picture width; (4) a small stack of round stones (a cairn) at the side "
        "of the path; (5) a few spiky chestnut burrs on the ground; (6) a small wooden footbridge over a "
        "little stream. No signposts."),
    4: ("Scene: an old-fashioned Japanese country kitchen in autumn with dark wooden beams, a window showing "
        "a persimmon tree outside at the top, and a clay cooking stove (kamado) at the left. Main objects: "
        "(1) a sturdy wooden table in the middle; (2) a round bamboo colander (zaru) on the table holding "
        "exactly three purple sweet potatoes, each about one eighteenth of the picture width, with space for "
        "one more; (3) a metal kettle with its spout clearly pointing to the left, sitting on the stove; "
        "(4) a small tray with a teapot and two cylindrical teacups (yunomi), each teacup about one "
        "twentieth of the picture width, both decorated with the same simple wavy blue lines; "
        "(5) an oval plate with two grilled Pacific saury fish; (6) a small basket of chestnuts; (7) a few "
        "wooden ladles hanging on the wall. No clock, no calendar, no paper with writing."),
    5: ("Scene: the quiet grounds of a small Japanese shrine in late autumn, with a tall golden ginkgo tree and "
        "yellow leaves scattered on the stone-paved path that leads up to a small wooden shrine building "
        "in the upper middle. Main objects: (1) the shrine building with a gabled roof; on the ridge of the "
        "roof there are exactly three short round crosswise logs (katsuogi), clearly separated; (2) a pair "
        "of stone guardian lion-dog statues (komainu) on pedestals on both sides of the path, the left one "
        "wearing a small red cloth bib, the bib about one twenty-eighth of the picture width; (3) a stone "
        "lantern beside the path whose light box has a round window, the window about one thirtieth of the "
        "picture width; (4) a red torii gate at the side; (5) a few grey pigeons on the path; (6) a plain "
        "wooden offering box with no writing; (7) a bamboo broom leaning against the ginkgo trunk. "
        "No wooden plaques with writing, no paper charms with letters."),
}

# 違いは outputs/2026-11-03_001/diff_candidates.md で選び直したもの（plan.md 3章の物は大きすぎたため。事業部長の指示・案C）
EDITS = {
    1: ("Edit this illustration and make exactly these three small changes: (a) on the stepping stone, the BACK one "
        "of the two wooden geta sandals (the upper one) has no thong strap any more: only the plain wooden base is "
        "left; the front geta stays exactly the same; (b) on the round tray, add one more persimmon of the same size "
        "next to the three persimmons, so there are four; (c) the front small teacup on the tray becomes a taller, "
        "cylindrical teacup (about twice as tall), same color and same tea; the back teacup stays the same."),
    2: ("Edit this illustration and make exactly these three small changes: (a) in the flat basket of purple sweet "
        "potatoes on the display stand, remove one sweet potato, showing the woven basket bottom where it was; "
        "(b) the Shiba dog now wears a simple red collar around its neck; nothing else about the dog changes; "
        "(c) the big paper lantern hanging from the eaves above the flowers becomes round like a ball instead of a "
        "long cylinder, same blank cream paper and same black top and bottom rims, same place."),
    3: ("Edit this illustration and make exactly these three small changes: (a) among the spiky chestnut burrs on "
        "the left side of the stone path, remove the smaller burr that is behind and to the right of the open burr "
        "with the shiny chestnut, showing the ground with leaves; (b) the cap of the middle (smallest) mushroom of "
        "the three now has small white polka dots; its shape and brown color stay the same; (c) on top of the small "
        "stack of round stones (the cairn), add one more small round grey-blue stone, so the stack is one stone "
        "taller."),
    4: ("Edit this illustration and make exactly these three small changes: (a) on the wall, remove the flat wooden "
        "spatula (the second utensil from the right), showing the plain wall and the empty hook; the other three "
        "utensils stay; (b) the kettle on the stove now has its spout on the right side pointing to the right "
        "instead of the left, same kettle, same size, same place; (c) the front teacup on the small tray now has a "
        "blue checkered (grid) pattern instead of wavy lines, same blue color, same shape; the back teacup stays."),
    5: ("Edit this illustration and make exactly these three small changes: (a) on the red torii gate, the left end "
        "of the lower crossbeam (the short block sticking out to the left of the left pillar) is gone, so the "
        "crossbeam ends at the left pillar; (b) the black band at the bottom of the left torii pillar is now red, "
        "the same red as the pillar; (c) the right one of the two grey pigeons on the path now faces right instead "
        "of left (it turned around), same size, same place."),
}

# うまくいかなかった違いだけを、範囲のまわりを切り出して描き直す（予備の呼び出し）。必要になったら足す。
RETRY = {
    # 1回目：いがぐりが消えず、2つとも描き直されただけだった → 切り出して描き直す
    (3, "2a"): {"crop": [700, 1200, 1100, 1520], "aspect": "5:4",
                "prompt": "Edit this close-up of a picture-book illustration: there are two spiky chestnut burrs side by side. "
                          "Completely remove the smaller burr on the right (the closed one without a visible chestnut), "
                          "and fill its place with the same sandy ground and fallen leaves as around it. The open burr with "
                          "the shiny chestnut on the left stays exactly the same." + KEEP_ALT + KEEP_REMOVE},
    # 1回目：3つとも変わらなかった → 鳥居の左側とハトを含む範囲を切り出して描き直す
    (5, "2"): {"crop": [0, 760, 1200, 1720], "aspect": "5:4",
               "prompt": "Edit this close-up of a picture-book illustration and make exactly these three small changes: "
                         "(a) on the red torii gate at the left, the lower horizontal crossbeam has a short block sticking "
                         "out to the LEFT of the left pillar: remove that sticking-out block, so the crossbeam ends at the left "
                         "pillar, and show the orange autumn trees behind it; (b) the dark grey-black band at the very bottom "
                         "of the left torii pillar is painted red now, the same red as the rest of the pillar; (c) the grey "
                         "pigeon at the lower right turns around and now faces RIGHT: its head and beak point to the right "
                         "and its tail to the left, same size and same place." + KEEP_ALT + KEEP_REMOVE},
    # 2回目：(b)の根巻きの色だけできた。(a)(c)はできなかったので、(a)は灯籠の宝珠に替え、(c)と合わせて小さく切り出して描き直す（予備の最後の1回）
    (5, "3"): {"crop": [860, 950, 1630, 1720], "aspect": "1:1",
               "prompt": "Edit this close-up of a picture-book illustration and make exactly these two small changes: "
                         "(a) the stone lantern at the upper right has a round onion-shaped knob (finial) on the very top of "
                         "its roof: remove that knob completely, so the roof ends flat at the top, and show the tree trunk and "
                         "bushes behind it; (b) the larger grey pigeon on the right side of the path is turned around so that "
                         "it faces RIGHT: its head and beak are now on its right side pointing right, and its tail points left; "
                         "same pigeon, same size, same place. The smaller pigeon on the left stays exactly the same."
                         + KEEP_ALT + KEEP_REMOVE},
}

DIFFS_FILE = Path(__file__).with_name("ep001_diffs.json")
QUESTIONS = {1: ("縁側", "初級", 1), 2: ("商店街", "初級", 3), 3: ("山道", "中級", 2), 4: ("台所", "中級", 3), 5: ("神社", "上級", 3)}  # (場面, 難易度, ヒントで示す違いの id。企画部の確定版で変わりうる)
# 画面に出す範囲（x0, y0, x1, y1）。8:9 のまま、Gemini が絵の左右に残した白いふち（紙の余白）を切り落とす。
# 縮めて 960×1080 にするだけで、引き伸ばしはしない（どの範囲も 960×1080 より大きい）。
# 第1問・第3問は、白いふちを全部切ると絵が拡大され、違いの物が難易度の目安を超える（第1問は約4.0〜4.4%、第3問は約3.2〜3.6%）。
# そのため第1問は一部だけ切り、第3問は切らない（白いふちが少し残る）。
CONTENT = {1: (138, 300, 1714, 2073), 2: (0, 0, 1856, 2088), 3: (0, 0, 1856, 2088), 4: (34, 38, 1822, 2050), 5: (0, 0, 1856, 2088)}
LEVEL_RANGE = {"初級": (3.0, 4.0), "中級": (2.0, 3.0), "上級": (1.5, 2.0)}  # 画面幅に対する%（concept.md）


def diffs():
    return {int(k): v for k, v in json.loads(DIFFS_FILE.read_text(encoding="utf-8")).items()} if DIFFS_FILE.exists() else {}


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
        generate(STYLE + SCENES[q], aspect="4:5", size="2K").save(src)
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
    ed = generate(prompt, images=[src], aspect="4:5", size="2K")
    if ed.size != src.size:
        ed = ed.resize(src.size, Image.LANCZOS)
    ed.save(w / f"edit_{q}_{ver}_src.png")
    crop_89(ed)[0].save(out)
    (w / f"edit_{q}_{ver}.prompt.txt").write_text(prompt, encoding="utf-8")
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
    im = generate(r["prompt"], images=[crop], aspect=r["aspect"], size="2K").resize(crop.size, Image.LANCZOS)
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
            ed = Image.open(Path(work) / f"edit_{q}_{d.get('src', '1')}.png").convert("RGB")
            x0, y0, x1, y1 = d["box"]; m = PATCH_MARGIN
            r = (max(0, x0 - m), max(0, y0 - m), min(ed.width, x1 + m), min(ed.height, y1 + m))
            p = patch_path(out_dir, q, d); p.parent.mkdir(parents=True, exist_ok=True)
            ed.crop(r).save(p)
            p.with_suffix(".json").write_text(json.dumps({"offset": r[:2]}), encoding="utf-8")


def edited_image(q, d, work, out_dir, a):
    """貼り戻しに使う描き直しの絵。作業フォルダになければ、成果物フォルダの edits/ の切り出しから組み立てる。"""
    f = Path(work) / f"edit_{q}_{d.get('src', '1')}.png"
    if f.exists():
        return Image.open(f).convert("RGB")
    p = patch_path(out_dir, q, d)
    ed = a.copy(); ed.paste(Image.open(p).convert("RGB"), tuple(json.loads(p.with_suffix(".json").read_text())["offset"]))
    return ed


def compose(q, work, out_dir):
    """範囲ごとに貼り戻す。元の絵は作業フォルダの q{q}_a.png、なければ成果物フォルダの q{q}_a.png を使う。"""
    w = Path(work)
    src_a = w / f"q{q}_a.png" if (w / f"q{q}_a.png").exists() else Path(out_dir) / f"q{q}_a.png"
    a = Image.open(src_a).convert("RGB")
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
