"""プログラムで作る違い（画像APIを使わない・大きさを正確に決められる）。plan.json の questions[].program_ops に書く。
make_episode.py の pictures から program_edits 経由で呼ばれる：python3 scripts/program_diffs.py <作業フォルダ>
（KOYOMI_EPISODE_DIR が回のフォルダ）。program_ops の版ごとに <作業>/edit_<問>_<版>.png を書く。

program_ops の書き方：{"<版>": [操作, ...]}。版の絵は元の絵（q<問>_a.png）から作る（"base": "<版>" で別の版の上に重ねられる）。
  {"op": "copy", "src": [x0,y0,x1,y1], "dst": [x, y], "width": 目標の幅px, "rot": 角度, "flip": true/false}
      src の中の物を、まわりの地との色の差で切り抜き、width に縮め（拡げ）て dst（左上）に貼る ＝「増える」
      "from_q": n で、同じ回の別の問の元の絵から切り抜く（同じ絵柄の物を足すとき）
      "from_file": "<作業フォルダの絵>" で、描き直しの版などから切り抜く／"circle": [cx,cy,r] で円で切り抜く
      "poly": [[x,y], ...] で、物を手で囲んだ多角形（元の絵の座標）で切り抜く（自動の切り抜きで地が付いてくるとき）
  {"op": "recolor", "box": [x0,y0,x1,y1], "hue": 色相（0〜255）, "sat": 彩度の倍率, "val": 明るさの倍率}
      box の中の物（地と色が違う所）の色を変える ＝「色」（上級だけ）
  {"op": "flip", "box": [x0,y0,x1,y1]}
      box の中の物を左右反対にし、もとの物の跡は地の色でうめる ＝「向き」（地が無地の所だけ）
切り抜きは「box のふちの色（地）」との差で決めるので、地が無地に近い所の物に使う。
地に模様があるときは "mask": "outline"（物の濃い輪郭線で閉じた内側を物とする）を使う。
輪郭線が閉じていない物（鳥・葉・かご）は "mask": "hull"（輪郭線を囲む凸の形の中で、地の色と違う所）。
"""
import json, os, sys
from pathlib import Path
import numpy as np
from PIL import Image, ImageFilter
from scipy import ndimage

THR = 38


def outline_mask(crop, dark=115, close=3):
    """絵本の絵は物のまわりに濃い輪郭線がある。その線で閉じた内側を物とする（地に模様があっても使える）。"""
    C = np.asarray(crop.convert("L")).astype(float)
    line = C < dark
    line = ndimage.binary_closing(line, iterations=close)
    filled = ndimage.binary_fill_holes(line)
    lab, n = ndimage.label(filled)
    h, w = filled.shape
    center = np.zeros_like(filled); center[h // 4:3 * h // 4, w // 4:3 * w // 4] = True
    keep = [i for i in range(1, n + 1) if ((lab == i) & center).sum() > 20]
    if not keep:
        raise SystemExit(f"輪郭で閉じた物が見つからない：{crop.size}")
    m = np.isin(lab, keep)
    return ndimage.binary_dilation(m, iterations=1), None


def hull_mask(crop, thr=THR, dark=130):
    """輪郭線が閉じていない物（鳥・葉・かご）：中央にかかる輪郭線を囲む凸の形の中で、地の色と違う所を物とする。"""
    from scipy.spatial import ConvexHull
    from PIL import ImageDraw
    C = np.asarray(crop).astype(float)
    L = C.mean(2)
    line = ndimage.binary_dilation(L < dark, iterations=3)
    lab, n = ndimage.label(line)
    h, w = L.shape
    center = np.zeros_like(line); center[h // 4:3 * h // 4, w // 4:3 * w // 4] = True
    keep = [i for i in range(1, n + 1) if ((lab == i) & center).any()]
    if not keep:
        raise SystemExit(f"輪郭線が見つからない：{crop.size}")
    ys, xs = np.nonzero(np.isin(lab, keep) & (L < dark))
    hull = ConvexHull(np.c_[xs, ys])
    poly = Image.new("L", (w, h), 0)
    ImageDraw.Draw(poly).polygon([(float(xs[i]), float(ys[i])) for i in hull.vertices], fill=255)
    inside = np.asarray(poly) > 0
    border = np.concatenate([C[0], C[-1], C[:, 0], C[:, -1]])
    bg = np.median(border, 0)
    m = inside & ((np.sqrt(((C - bg) ** 2).sum(2)) > thr) | (L < dark))
    m = ndimage.binary_closing(m, iterations=2) & inside
    return ndimage.binary_fill_holes(m), bg


def obj_mask(crop, thr=THR, mode=None):
    if mode == "outline":
        return outline_mask(crop)
    if mode == "hull":
        return hull_mask(crop, thr)
    """box のふちの色（地）との差で物を切り抜く。box の中央にかかる部分だけを残す（ふちにかかったほかの物は捨てる）。"""
    C = np.asarray(crop).astype(float)
    border = np.concatenate([C[0], C[-1], C[:, 0], C[:, -1]])
    bg = np.median(border, 0)
    m = np.sqrt(((C - bg) ** 2).sum(2)) > thr
    m = ndimage.binary_opening(m, iterations=1)
    m = ndimage.binary_closing(m, iterations=2)
    lab, n = ndimage.label(m)
    h, w = m.shape
    center = np.zeros_like(m); center[h // 4:3 * h // 4, w // 4:3 * w // 4] = True
    keep = [i for i in range(1, n + 1) if ((lab == i) & center).any()]
    if not keep:
        raise SystemExit(f"物が見つからない：{crop.size}")
    m = np.isin(lab, keep)
    m = ndimage.binary_fill_holes(m)
    edge = np.zeros_like(m); edge[0] = edge[-1] = True; edge[:, 0] = edge[:, -1] = True
    if (m & edge).sum() > 0.25 * edge.sum():
        raise SystemExit(f"切り抜きが box のふちに広がりすぎ（地が無地でない）：{crop.size}")
    return m, bg


def fill_bg(C, m, iters=150):
    """m の所を、まわりから少しずつぼかしてうめる（無地の地のための簡単な穴うめ）。"""
    B = C.copy()
    B[m] = C[~m].mean(0) if (~m).any() else 200
    for _ in range(iters):
        bl = np.asarray(Image.fromarray(np.clip(B, 0, 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(2))).astype(float)
        B[m] = bl[m]
    return B


def apply(im, op, work=None):
    if op["op"] == "copy":
        if op.get("from_file"):     # 作業フォルダの別の絵（描き直しの版など）から切り抜く
            src_im = Image.open(Path(work) / op["from_file"]).convert("RGB")
        elif op.get("from_q"):
            src_im = Image.open(Path(work) / f"q{op['from_q']}_a.png").convert("RGB")
        else:
            src_im = im
        crop = src_im.crop(tuple(op["src"]))
        if op.get("circle") and op.get("thr_in_circle"):   # 円の中で、まわりの地の色と違う所だけ（花びらのように地がすけて見える物）
            cx, cy, rr = op["circle"]
            C = np.asarray(crop).astype(float)
            yy, xx = np.mgrid[0:C.shape[0], 0:C.shape[1]]
            inc = (xx + op["src"][0] - cx) ** 2 + (yy + op["src"][1] - cy) ** 2 <= rr ** 2
            bg = np.median(C[~inc], 0) if (~inc).any() else np.median(C.reshape(-1, 3), 0)
            m = inc & (np.sqrt(((C - bg) ** 2).sum(2)) > op["thr_in_circle"])
            m = ndimage.binary_fill_holes(ndimage.binary_closing(m, iterations=2)) & inc
            op = dict(op, _mask=m)
        if op.get("_mask") is not None:
            m = op["_mask"]
        elif op.get("circle"):    # [cx, cy, r]：丸い物を円で切り抜く（元の絵の座標）
            cx, cy, rr = op["circle"]
            import math
            op = dict(op, poly=[[cx + rr * math.cos(t / 36 * 2 * math.pi), cy + rr * math.sin(t / 36 * 2 * math.pi)] for t in range(36)])
        if op.get("_mask") is not None:
            pass
        elif op.get("poly"):      # 物のまわりを手で囲んだ多角形（元の絵の座標）。地に模様があって自動の切り抜きができないとき
            from PIL import ImageDraw
            pm = Image.new("L", crop.size, 0)
            ImageDraw.Draw(pm).polygon([(x - op["src"][0], y - op["src"][1]) for x, y in op["poly"]], fill=255)
            m = np.asarray(pm) > 0
        else:
            m, _ = obj_mask(crop, op.get("thr", THR), op.get("mask"))
        ys, xs = np.nonzero(m)
        crop = crop.crop((xs.min(), ys.min(), xs.max() + 1, ys.max() + 1))
        m = m[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
        k = op["width"] / crop.width
        size = (max(1, round(crop.width * k)), max(1, round(crop.height * k)))
        obj = crop.resize(size, Image.LANCZOS)
        mk = Image.fromarray((m * 255).astype(np.uint8)).resize(size, Image.LANCZOS)
        if op.get("flip"):
            obj, mk = obj.transpose(Image.FLIP_LEFT_RIGHT), mk.transpose(Image.FLIP_LEFT_RIGHT)
        if op.get("rot"):
            obj = obj.rotate(op["rot"], resample=Image.BICUBIC, expand=True)
            mk = mk.rotate(op["rot"], resample=Image.BICUBIC, expand=True)
        mk = mk.filter(ImageFilter.MinFilter(3)).filter(ImageFilter.GaussianBlur(0.8))
        im.paste(obj, tuple(op["dst"]), mk)
    elif op["op"] == "recolor":
        box = tuple(op["box"])
        crop = im.crop(box)
        m, _ = obj_mask(crop, op.get("thr", THR), op.get("mask"))
        H = np.asarray(crop.convert("HSV")).astype(float)
        if "hue" in op:
            H[..., 0] = np.where(m, op["hue"], H[..., 0])
        H[..., 1] = np.where(m, np.clip(H[..., 1] * op.get("sat", 1.0), 0, 255), H[..., 1])
        H[..., 2] = np.where(m, np.clip(H[..., 2] * op.get("val", 1.0), 0, 255), H[..., 2])
        im.paste(Image.fromarray(H.astype(np.uint8), "HSV").convert("RGB"), box[:2])
    elif op["op"] == "flip":
        box = tuple(op["box"])
        crop = im.crop(box)
        m, _ = obj_mask(crop)
        C = np.asarray(crop).astype(float)
        B = fill_bg(C, ndimage.binary_dilation(m, iterations=2))
        out = Image.fromarray(np.clip(B, 0, 255).astype(np.uint8))
        mk = Image.fromarray((m[:, ::-1] * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(0.8))
        out.paste(crop.transpose(Image.FLIP_LEFT_RIGHT), (0, 0), mk)
        im.paste(out, box[:2])
    return im


def main(work):
    ep = Path(os.environ["KOYOMI_EPISODE_DIR"])
    plan = json.loads((ep / "plan.json").read_text(encoding="utf-8"))
    for Q in plan["questions"]:
        for ver, ops in Q.get("program_ops", {}).items():
            if not isinstance(ops, list):
                continue
            base = Path(work) / f"q{Q['q']}_a.png"
            im = Image.open(base if base.exists() else ep / f"q{Q['q']}_a.png").convert("RGB")
            for op in ops:
                im = apply(im, op, work)
            im.save(Path(work) / f"edit_{Q['q']}_{ver}.png")


if __name__ == "__main__":
    main(sys.argv[1])
