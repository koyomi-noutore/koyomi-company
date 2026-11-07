"""第2回 第5問：舞っているいちょうの葉を1枚だけ茶色にする（上級の「色」の違い。画像APIは使わない）。
python3 ep002_q5_leaf.py <作業フォルダ>  →  <作業>/edit_5_leaf.png"""
import sys
from pathlib import Path
import numpy as np
from PIL import Image

BOX = (1166, 1137, 1244, 1206)   # 葉のまわり（8:9の絵の座標）

w = Path(sys.argv[1])
a = Image.open(w / "q5_a.png").convert("RGB")
hsv = np.asarray(a.crop(BOX).convert("HSV")).astype(int)
leaf = (hsv[..., 0] > 18) & (hsv[..., 0] < 50) & (hsv[..., 1] > 60)
hsv[..., 0] = np.where(leaf, 14, hsv[..., 0])                    # 黄 → 茶色みのある橙
hsv[..., 2] = np.where(leaf, (hsv[..., 2] * 0.72).astype(int), hsv[..., 2])   # 少し暗く（枯れ葉の茶色）
patch = Image.fromarray(hsv.astype(np.uint8), "HSV").convert("RGB")
out = a.copy(); out.paste(patch, BOX[:2])
out.save(w / "edit_5_leaf.png")
