"""第1回（001・秋の間違い探し5問）の問題の絵を作る。
プロンプトは outputs/2026-11-03_001/plan.md の2章・3章をそのまま使う。
答えの範囲（box、元の絵のピクセル座標）・型・難易度はこのファイルの DIFFS で管理する。

使い方（作業フォルダには途中画像を置く。完成物フォルダには残さない）:
  export KOYOMI_IMAGE_USAGE_LOG=outputs/2026-11-03_001/image_usage.jsonl
  python3 scripts/ep001_pictures.py base  <問> <作業フォルダ>      # 元の絵（API 1回。第1問は見本を流用＝0回）
  python3 scripts/ep001_pictures.py edit  <問> <作業フォルダ> [版]  # 3つの違いをまとめて描き直し（API 1回）
  python3 scripts/ep001_pictures.py compose <問> <作業フォルダ> <出力フォルダ>  # 範囲ごとに貼り戻す（API 0回）
  python3 scripts/ep001_pictures.py answers <作業フォルダ> <出力フォルダ>       # answers.json を書く
作業フォルダにキャッシュがあれば、APIは呼ばない（無駄打ちしない）。
"""
import json, shutil, sys
from pathlib import Path
from PIL import Image, ImageChops
sys.path.insert(0, str(Path(__file__).parent))
from make_differences import feather_mask

ROOT = Path(__file__).resolve().parent.parent
SAMPLE_A = ROOT / "outputs/2026-11-03_001-sample/picture_a.png"
SIZE = (2752, 1536)

STYLE = ("A warm Japanese picture-book illustration in soft watercolor with gentle colored-pencil outlines, "
         "like a cozy picture book for all ages. Autumn palette: persimmon orange, maple red, ginkgo yellow, "
         "warm browns and soft greens. Natural, hand-drawn, slightly rounded shapes; not geometric, not flat "
         "vector, not photorealistic. Wide 16:9 landscape composition. No people. Absolutely no text, letters, "
         "numbers, logos or symbols anywhere, including on signs, curtains, boxes and lanterns. "
         "The main objects listed below are large, clearly separated from each other with some space around "
         "each, and fully visible (not cut off by the picture edge and not hidden behind other objects).\n")

# plan.md 3章の【意見】の文（「増える」「形・向きが変わる」用）と、KEEP（「消す」用、make_differences.py）を合わせる。
KEEP_ALT = (" Keep everything else in the picture exactly the same: same composition, same position of every object, "
            "same colors, same style. Do not add or remove anything else. Leave no faint outline, ghost or smudge. No text.")
KEEP_REMOVE = (" Where an object is removed, fill the area naturally with what would be behind it, "
               "and leave no faint outline, ghost or smudge of the removed object.")

SCENES = {
    1: None,  # 見本の元の絵（監査済み）を流用
    2: ("Scene: a cozy old Japanese shopping street in autumn, seen from the street in front of a small fruit "
        "and vegetable shop with a wooden front and a tiled roof. Main objects: (1) a wooden display stand in "
        "front of the shop with flat bamboo baskets of persimmons, chestnuts and sweet potatoes; (2) one big "
        "green Japanese pumpkin (kabocha) sitting alone on the right end of the stand, about one tenth of the "
        "picture width, with empty space next to it; (3) a plain indigo shop curtain (noren) with no writing "
        "and no pattern; (4) two round red paper lanterns hanging from the eaves, completely blank; (5) an "
        "old-fashioned black bicycle parked on the left, about one sixth of the picture width; (6) a Shiba dog "
        "sitting on the ground in front of the stand, facing the viewer, about one tenth of the picture width; "
        "(7) a potted yellow chrysanthemum by the door; a few ginkgo leaves on the stone pavement. "
        "The neighbouring shops in the background are simple and also have no writing."),
    3: ("Scene: a gentle mountain walking path in autumn, with rough stone steps going up through red maple "
        "and yellow trees, soft mist on distant hills. Main objects: (1) a small arched wooden footbridge over "
        "a little stream on the left; (2) a wooden bench beside the path with a small red rucksack on it, the "
        "rucksack about one eleventh of the picture width; (3) a tree stump in the foreground with one brown "
        "squirrel holding an acorn on it, the squirrel about one eleventh of the picture width, with free space "
        "on the stump next to it; (4) a small stack of three round stones (a little cairn) at the side of the "
        "path, about one twelfth of the picture width; (5) a cluster of brown mushrooms at the foot of a tree; "
        "(6) a few spiky chestnut burrs on the ground. No signposts."),
    4: ("Scene: an old-fashioned Japanese country kitchen in autumn with dark wooden beams, a window showing a "
        "persimmon tree outside, and a clay cooking stove (kamado). Main objects: (1) a sturdy wooden table in "
        "the front; (2) a long oval plate on the table with two grilled Pacific saury fish side by side, with "
        "room for one more; (3) a round bamboo colander (zaru) on the table piled with purple sweet potatoes, "
        "about one ninth of the picture width; (4) a metal kettle with its spout clearly pointing to the left, "
        "sitting on the stove, about one tenth of the picture width; (5) a clay pot (donabe) with a lid; "
        "(6) a small basket of chestnuts; (7) a few wooden ladles hanging on the wall. "
        "No clock, no calendar, no paper with writing."),
    5: ("Scene: the quiet grounds of a small Japanese shrine in late autumn, with a big golden ginkgo tree and "
        "yellow leaves scattered on the stone-paved path. Main objects: (1) a red torii gate on the left; "
        "(2) a pair of small stone lanterns standing side by side in the background near the ginkgo tree, "
        "each about one fourteenth of the picture width; (3) a pair of stone guardian lion-dog statues "
        "(komainu) on pedestals; (4) a small wooden shrine building with a plain wooden offering box with no "
        "writing; (5) two grey pigeons pecking on the path, each about one fourteenth of the picture width; "
        "(6) a bamboo broom leaning diagonally against the ginkgo tree trunk, about one twelfth of the picture "
        "width; (7) a stone water basin with two bamboo ladles. No wooden plaques with writing, no paper "
        "charms with letters."),
}

EDITS = {
    1: ("Edit this illustration and make exactly these three changes: (a) remove the brown clay teapot from "
        "the round tray, showing the empty wooden tray where it stood; the persimmons and teacups stay; "
        "(b) fill the empty bamboo basket with a heap of orange persimmons; (c) the calico cat wakes up: it "
        "lifts its head and opens its eyes, still lying on the same cushion with the same fur pattern."),
    2: ("Edit this illustration and make exactly these three changes: (a) remove the black bicycle, showing "
        "the shop wall and the stone pavement behind it; (b) add a second green pumpkin of the same size right "
        "next to the first one on the display stand; (c) the Shiba dog sits in the same place but now faces "
        "away from the viewer, so we see its back and curled tail."),
    3: ("Edit this illustration and make exactly these three changes: (a) add a second brown squirrel of the "
        "same size sitting next to the first one on the tree stump; (b) remove the red rucksack from the "
        "wooden bench, showing the plain bench boards; (c) make the little stack of stones taller: five round "
        "stones instead of three, the same kind of stones, in the same place."),
    4: ("Edit this illustration and make exactly these three changes: (a) add a third grilled saury fish on "
        "the oval plate, next to the other two; (b) turn the kettle so that its spout points to the right "
        "instead of the left, same kettle, same place; (c) remove all the sweet potatoes from the bamboo "
        "colander, leaving the empty colander on the table."),
    5: ("Edit this illustration and make exactly these three changes: (a) add a third grey pigeon of the same "
        "size pecking on the path near the other two; (b) the bamboo broom has fallen over and now lies flat on "
        "the ground at the foot of the ginkgo tree; (c) remove the right one of the two small stone lanterns "
        "in the background, showing the ground with yellow ginkgo leaves and the trees behind it."),
}

# 答え。box は元の絵（2752×1536）のピクセル座標。物より一回り広く取る。
# src は貼り戻しに使う描き直しの版（edit_<問>_<版>.png）。hint は45秒ヒントで光らせる違いの id。
QUESTIONS = {
    1: {"scene": "縁側", "level": "初級", "hint": 1, "diffs": []},
    2: {"scene": "商店街", "level": "初級", "hint": 3, "diffs": []},
    3: {"scene": "山道", "level": "中級", "hint": 3, "diffs": []},
    4: {"scene": "台所", "level": "中級", "hint": 2, "diffs": []},
    5: {"scene": "神社", "level": "上級", "hint": 3, "diffs": []},
}
DIFFS_FILE = Path(__file__).with_name("ep001_diffs.json")
if DIFFS_FILE.exists():
    for q, v in json.loads(DIFFS_FILE.read_text(encoding="utf-8")).items():
        QUESTIONS[int(q)]["diffs"] = v


def base(q, work):
    out = Path(work) / f"q{q}_a.png"
    if out.exists():
        return Image.open(out)
    if SCENES[q] is None:
        shutil.copy(SAMPLE_A, out)
        return Image.open(out)
    from gemini_image import generate
    im = generate(STYLE + SCENES[q], aspect="16:9", size="2K")
    if im.size != SIZE:
        im = im.resize(SIZE, Image.LANCZOS)
    im.save(out)
    return im


def edit(q, work, ver="1", extra=""):
    out = Path(work) / f"edit_{q}_{ver}.png"
    if out.exists():
        return Image.open(out)
    from gemini_image import generate
    a = Image.open(Path(work) / f"q{q}_a.png").convert("RGB")
    prompt = (extra or EDITS[q]) + KEEP_ALT + KEEP_REMOVE
    im = generate(prompt, images=[a], aspect="16:9", size="2K").resize(a.size, Image.LANCZOS)
    im.save(out)
    (Path(work) / f"edit_{q}_{ver}.prompt.txt").write_text(prompt, encoding="utf-8")
    return im


def compose(q, work, out_dir):
    a = Image.open(Path(work) / f"q{q}_a.png").convert("RGB")
    b = a.copy()
    for d in QUESTIONS[q]["diffs"]:
        ed = Image.open(Path(work) / f"edit_{q}_{d.get('src', '1')}.png").convert("RGB")
        b = Image.composite(ed, b, feather_mask(a.size, d["box"], d.get("feather", 24)))
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


def answers(work, out_dir, screen_img_w=940, screen_w=1920):
    res = {"image_size": list(SIZE), "screen": {"picture_width_px": screen_img_w, "screen_width_px": screen_w},
           "questions": []}
    for q, Q in QUESTIONS.items():
        a = Image.open(Path(out_dir) / f"q{q}_a.png").convert("RGB")
        b = Image.open(Path(out_dir) / f"q{q}_b.png").convert("RGB")
        n, mx = outside_diff(a, b, [d["box"] for d in Q["diffs"]])
        s = screen_img_w / SIZE[0]
        res["questions"].append({
            "q": q, "scene": Q["scene"], "level": Q["level"], "hint_diff": Q["hint"],
            "outside_box_pixels_diff_gt15": n, "outside_box_max_distance_px": round(mx, 1),
            "answers": [{
                "id": d["id"], "type": d["type"], "label": d["label"], "line": d["line"],
                "box_px": d["box"],
                "box_ratio": [round(d["box"][i] / SIZE[i % 2], 4) for i in range(4)],
                "object_width_px": d["object_w"],
                "object_screen_width_pct": round(d["object_w"] * s / screen_w * 100, 1),
                "box_screen_width_pct": round((d["box"][2] - d["box"][0]) * s / screen_w * 100, 1),
                "edit_version": d.get("src", "1"),
            } for d in Q["diffs"]]})
    Path(out_dir, "answers.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    return res


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "base":
        base(int(sys.argv[2]), sys.argv[3])
    elif cmd == "edit":
        edit(int(sys.argv[2]), sys.argv[3], *(sys.argv[4:5] or ["1"]))
    elif cmd == "compose":
        compose(int(sys.argv[2]), sys.argv[3], sys.argv[4])
    elif cmd == "answers":
        print(json.dumps(answers(sys.argv[2], sys.argv[3]), ensure_ascii=False, indent=1))
