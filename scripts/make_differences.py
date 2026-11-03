"""間違い探しを作る：AIに一部を描き直させ、決めた範囲だけを元の絵に貼り戻す。
答えの位置・指示文・難易度は下の DIFFS（元画像のピクセル座標）で管理する。

使い方:
  python3 scripts/make_differences.py <元の絵.png> <出力フォルダ> <作業フォルダ>
  （作業フォルダには描き直しの途中画像を置く。完成物フォルダには残さない）

描き直しの方式:
  full … 絵全体を渡して描き直させる
  crop … 範囲のまわり（4:3）を切り出して大きく描き直させる。細かい消し残りが出にくい
"""
import json, sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter
sys.path.insert(0, str(Path(__file__).parent))
from gemini_image import generate

KEEP = (" Keep everything else in the picture exactly the same: same composition, same position of every object, "
        "same colors, same style. Fill the area naturally with what would be behind it. "
        "Leave no faint outline, ghost or smudge of the removed object. No text.")

# 001「柿・秋の縁側」（元の絵 2752×1536）
DIFFS = [
    {"id": 1, "level": "やさしい", "label": "竹かごがない", "box": [1470, 730, 1925, 1060], "mode": "crop",
     "prompt": "Edit this close-up of a picture-book illustration: completely remove the woven bamboo basket standing on the "
               "wooden veranda floor. Where it stood, continue the plain wooden floor boards, and behind it continue the green "
               "garden bushes with the same green color as the surrounding bushes."},
    {"id": 2, "level": "ふつう", "label": "灯籠の前の紅葉の若木がない", "box": [840, 650, 1120, 880], "mode": "full",
     "prompt": "Edit this illustration: remove the small red maple sapling standing in front of and to the left of the stone "
               "lantern, showing the green bushes and grass behind it. Do not change the stone lantern."},
    # ③は crop だと形が残って白く塗られるだけだった（再審査1で不合格）。full で描き直し、
    # 範囲の左端をしっぽの先より外へ広げて、ぼかしで元のしっぽが透けないようにした。
    {"id": 3, "level": "むずかしい", "label": "猫のしっぽがない", "box": [1135, 1050, 1400, 1192], "feather": 16, "mode": "full",
     "prompt": "Edit this illustration: remove the striped tail of the sleeping calico cat, so the cat has no visible tail; "
               "show the patterned cushion where the tail was. Do not change anything else about the cat."},
]


def feather_mask(size, box, feather):
    m = Image.new("L", size, 0)
    ImageDraw.Draw(m).rounded_rectangle(box, radius=feather, fill=255)
    return m.filter(ImageFilter.GaussianBlur(feather / 2))


def crop_box(img_size, box, margin=120, aspect=4 / 3):
    W, H = img_size
    x0, y0, x1, y1 = box
    w = max(x1 - x0 + 2 * margin, (y1 - y0 + 2 * margin) * aspect)
    h = w / aspect
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    left = int(min(max(cx - w / 2, 0), W - w)); top = int(min(max(cy - h / 2, 0), H - h))
    return left, top, left + int(w), top + int(h)


def edited_full(base, d, work_dir):
    cache = Path(work_dir) / f"edit_{d['id']}_{d['mode']}.png"
    if cache.exists():
        return Image.open(cache).convert("RGB")
    if d["mode"] == "full":
        ed = generate(d["prompt"] + KEEP, images=[base]).resize(base.size, Image.LANCZOS)
    else:
        cb = crop_box(base.size, d["box"])
        crop = base.crop(cb)
        out = generate(d["prompt"] + KEEP, images=[crop], aspect="4:3", size="2K")
        ed = base.copy(); ed.paste(out.resize(crop.size, Image.LANCZOS), cb[:2])
    ed.save(cache)
    return ed


def make(base_path, out_dir, work_dir, diffs=DIFFS):
    base = Image.open(base_path).convert("RGB")
    result = base.copy()
    for d in diffs:
        ed = edited_full(base, d, work_dir)
        result = Image.composite(ed, result, feather_mask(base.size, d["box"], d.get("feather", 24)))
    out = Path(out_dir); out.mkdir(parents=True, exist_ok=True)
    base.save(out / "picture_a.png")
    result.save(out / "picture_b.png")
    (Path(work_dir) / "diffs.json").write_text(json.dumps(diffs, ensure_ascii=False, indent=1), encoding="utf-8")
    return result


if __name__ == "__main__":
    make(*sys.argv[1:4])
