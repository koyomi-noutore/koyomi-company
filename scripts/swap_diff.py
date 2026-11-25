"""つないだ回（combine_episodes.py で作った全10問）の、1つの違いを別の物の違いに差し替える（2026-11-26 CEO決定）。
元の回のフォルダは触らない。新しい回のフォルダの qN_b.png・plan.json・answers.json だけを直す。画像は Vertex 経由（違いの範囲のまわりだけ描き直す）。

使い方:
  python3 scripts/swap_diff.py <回のフォルダ> <swaps.json> [--dry]
  swaps.json（回のフォルダに置く）＝[{"q":問,"id":違いの番号,"label":"かごが黒","type":"色","line":"答えの文","voice":"声に渡す文（ひらがな）",
     "box":[x0,y0,x1,y1],"object_w":物の幅px,"prompt":"英語の指示（範囲のまわりの切り出しに対して）","context":"増える・入れ替えのときだけ","feather":10}, ...]
やること（1つの差し替えごと）:
  1. 古い違いの範囲を、左の絵（qN_a.png）と同じに戻す（古い違いを消す）。
  2. 新しい範囲のまわり（正方形）を切り出し、Vertex で描き直させ、新しい範囲だけ右の絵（qN_b.png）に貼る。
  3. plan.json の diffs・声の上書き（voice_override）と answers.json を直す。描き直した切り出しは <回>/edits/ に残す。
  画像の呼び出しは1つの差し替えにつき1回（<回>/edits/ に結果があれば作り直さない。--dry は画像を作らず、戻しと範囲だけ確かめる）。
"""
import json
import os
import sys
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
if len(sys.argv) > 1:       # gemini_image は読み込み時にこの変数を見る（費用の記録）。import より前に入れる
    os.environ.setdefault("KOYOMI_IMAGE_USAGE_LOG", str(Path(sys.argv[1]).resolve() / "image_usage.jsonl"))
from make_differences import feather_mask

LEVEL_RANGE = {"やさしい": (6.0, 8.0), "初級": (5.0, 6.0), "中級": (4.0, 5.0), "上級": (3.0, 4.0)}
KEEP = (" Keep everything else in this picture exactly the same: same composition, same position of every object, same colors, same style "
        "(thick dark outlines, watercolor picture-book). Do not add or remove anything else. Leave no faint outline, ghost or smudge. No text.")


def crop_square(size, box, margin=150):
    W, H = size
    x0, y0, x1, y1 = box
    s = int(max(x1 - x0, y1 - y0) + 2 * margin)
    s = min(s, W, H)
    cx, cy = (x0 + x1) // 2, (y0 + y1) // 2
    left = min(max(cx - s // 2, 0), W - s)
    top = min(max(cy - s // 2, 0), H - s)
    return left, top, left + s, top + s


def outside_diff(a, b, boxes, thr=15):
    import numpy as np
    d = np.asarray(ImageChops.difference(a, b).convert("L")) > thr
    ys, xs = np.nonzero(d)
    dist = np.full(len(xs), 1e9)
    for x0, y0, x1, y1 in boxes:
        dx = np.maximum(np.maximum(x0 - xs, xs - x1), 0)
        dy = np.maximum(np.maximum(y0 - ys, ys - y1), 0)
        dist = np.minimum(dist, np.hypot(dx, dy))
    out = dist > 0
    return int(out.sum()), float(dist[out].max()) if out.any() else 0.0


def answer_entry(d, Q, level, cx0, cx1, safe):
    s = 960 / (cx1 - cx0)
    to = lambda r: [round((r[0] - Q["content_px"][0]) * s), round((r[1] - Q["content_px"][1]) * s),
                    round((r[2] - Q["content_px"][0]) * s), round((r[3] - Q["content_px"][1]) * s)]
    lo, hi = LEVEL_RANGE[level]
    pct_scr = round(d["object_w"] * s / 1920 * 100, 2)
    sb = to(d["box"])
    return {"id": d["id"], "type": d["type"], "label": d["label"], "line": d["line"], "box_px": d["box"], "box_screen": sb,
            "circle_a_screen": sb, "circle_b_screen": sb, "object_w_px": d["object_w"],
            "object_picture_width_pct": round(d["object_w"] / (cx1 - cx0) * 100, 2), "object_screen_width_pct": pct_scr,
            "in_level_range": lo <= pct_scr <= hi, "in_safe_y": safe[0] <= sb[1] and sb[3] <= safe[1] and 0 <= sb[0] and sb[2] <= 960,
            "edit_version": "swap", "made_by": "gemini", "note": d.get("note", "")}


def main(argv):
    ep = Path(argv[0]).resolve()
    spec = json.loads((ep / argv[1]).read_text(encoding="utf-8") if not Path(argv[1]).is_absolute() else Path(argv[1]).read_text(encoding="utf-8"))
    dry = "--dry" in argv
    os.environ.setdefault("KOYOMI_IMAGE_USAGE_LOG", str(ep / "image_usage.jsonl"))
    plan_p, ans_p = ep / "plan.json", ep / "answers.json"
    plan = json.loads(plan_p.read_text(encoding="utf-8"))
    ans = json.loads(ans_p.read_text(encoding="utf-8"))
    calls = 0
    for sw in spec:
        q, did = sw["q"], sw["id"]
        PQ = next(x for x in plan["questions"] if x["q"] == q)
        AQ = next(x for x in ans["questions"] if x["q"] == q)
        old = next(x for x in PQ["diffs"] if x["id"] == did)
        a = Image.open(ep / f"q{q}_a.png").convert("RGB")
        b = Image.open(ep / f"q{q}_b.png").convert("RGB")
        # 1. 古い違いを消す（古い範囲＋ぼかしの広がりを、左の絵と同じに戻す）
        ox0, oy0, ox1, oy1 = old["box"]
        pad = 48
        hard = Image.new("L", a.size, 0)
        ImageDraw.Draw(hard).rectangle((ox0 - pad, oy0 - pad, ox1 + pad, oy1 + pad), fill=255)
        b = Image.composite(a, b, hard)
        # 2. 新しい範囲のまわりを描き直す
        cb = crop_square(a.size, sw["box"])
        patch = ep / "edits" / f"q{q}_d{did}_swap.png"
        crop = a.crop(cb)
        if patch.exists():
            ed = Image.open(patch).convert("RGB")
        elif dry:
            ed = crop
        else:
            from gemini_image import generate
            import time, urllib.error
            for k in range(8):      # Vertex は1分あたりの回数に上限がある（429）。待って取り直す
                try:
                    ed = generate(sw["prompt"] + KEEP, images=[crop], aspect="1:1", size="1K").resize(crop.size, Image.LANCZOS)
                    break
                except urllib.error.HTTPError as e:
                    if e.code not in (429, 503) or k == 7:
                        raise
                    print(f"[swap] {e.code}。{30 * (k + 1)}秒待つ", flush=True)
                    time.sleep(30 * (k + 1))
            patch.parent.mkdir(exist_ok=True)
            ed.save(patch)
            (ep / "edits" / f"q{q}_d{did}_swap.json").write_text(json.dumps({"crop": cb, "prompt": sw["prompt"], "box": sw["box"]}, ensure_ascii=False), encoding="utf-8")
            calls += 1
        full = a.copy()
        full.paste(ed, cb[:2])
        m = feather_mask(a.size, sw["box"], sw.get("feather", 10))
        b = Image.composite(full, b, m)
        if sw.get("smooth"):    # 消したあとの薄い輪郭の跡（空・壁など平らな所）をぼかして消す。範囲 box の中に収める
            from PIL import ImageFilter
            b = Image.composite(b.filter(ImageFilter.GaussianBlur(14)), b, feather_mask(a.size, sw["smooth"], 20))
        b.save(ep / f"q{q}_b.png")
        # 3. plan.json・answers.json・声
        new = {"id": did, "type": sw["type"], "label": sw["label"], "line": sw["line"], "box": sw["box"], "object_w": sw["object_w"], "src": "swap"}
        if sw.get("context"):
            new["context"] = sw["context"]
        PQ["diffs"] = [new if x["id"] == did else x for x in PQ["diffs"]]
        plan["voice_override"][f"q{q}_ans{did}"] = sw["voice"]
        AQ["answers"] = [answer_entry(new, AQ, PQ["level"], AQ["content_px"][0], AQ["content_px"][2], (54, 918)) if x["id"] == did else x for x in AQ["answers"]]
        n, mx = outside_diff(a, b, [x["box"] for x in PQ["diffs"]])
        AQ["outside_box_pixels_diff_gt15"], AQ["outside_box_max_distance_px"] = n, round(mx, 1)
        print(f"第{q}問 違い{did}：{old['label']} → {sw['label']}（範囲外の差 {n}画素・最大{mx:.1f}px）")
    plan_p.write_text(json.dumps(plan, ensure_ascii=False, indent=1), encoding="utf-8")
    ans_p.write_text(json.dumps(ans, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"画像の呼び出し：{calls}回")


if __name__ == "__main__":
    main(sys.argv[1:])
