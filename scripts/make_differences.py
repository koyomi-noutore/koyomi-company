"""間違い探しを作る：AIに絵全体を描き直させ、決めた範囲だけを元の絵に貼り戻す。
答えの位置はこのファイルの DIFFS（元画像のピクセル座標）で管理する。"""
import json, sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter
sys.path.insert(0, str(Path(__file__).parent))
from gemini_image import generate

KEEP = (" Keep everything else in the picture exactly the same: same composition, same position of every object, "
        "same colors, same style. Fill the area naturally with what would be behind it. No text.")


def feather_mask(size, box, feather):
    m = Image.new("L", size, 0)
    ImageDraw.Draw(m).rounded_rectangle(box, radius=feather, fill=255)
    return m.filter(ImageFilter.GaussianBlur(feather / 2))


def make(base_path, diffs, out_dir, work_dir):
    base = Image.open(base_path).convert("RGB")
    result = base.copy()
    for d in diffs:
        cache = Path(work_dir) / f"edit_{d['id']}.png"
        if cache.exists():
            ed = Image.open(cache).convert("RGB")
        else:
            ed = generate(d["prompt"] + KEEP, images=[base]).resize(base.size, Image.LANCZOS)
            ed.save(cache)
        x0, y0, x1, y1 = d["box"]
        mask = feather_mask(base.size, d["box"], d.get("feather", 24))
        result = Image.composite(ed, result, mask)
    result.save(Path(out_dir) / "picture_b.png")
    base.save(Path(out_dir) / "picture_a.png")
    return result
