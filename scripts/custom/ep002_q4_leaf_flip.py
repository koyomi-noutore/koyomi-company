"""第2回 第4問③：地面に落ちたいちょうの葉を1枚、左右反対の向きにする（中級の「向き」。画像APIは使わない）。
監査の差し戻し（けむりの向きは変わる範囲が広すぎて易しい）で差し替えた。背景は白っぽい地面なので、葉の跡は地面の色でうめる。
python3 ep002_q4_leaf_flip.py <作業フォルダ>  →  <作業>/edit_4_flip.png"""
import sys
from pathlib import Path
import numpy as np
from PIL import Image, ImageFilter

BOX = (366, 1603, 466, 1675)   # 地面に落ちた葉のまわり（8:9の絵の座標）

w = Path(sys.argv[1])
a = Image.open(w / "q4_a.png").convert("RGB")
crop = a.crop(BOX)
C = np.asarray(crop).astype(float)
H = np.asarray(crop.convert("HSV")).astype(int)
yellow = (H[..., 0] > 15) & (H[..., 0] < 50) & (H[..., 1] > 90)          # 葉の黄色
dark = C.mean(2) < 150                                                     # 輪郭の線
near = np.asarray(Image.fromarray((yellow * 255).astype(np.uint8)).filter(ImageFilter.MaxFilter(9))) > 0
leaf = yellow | (dark & near)
leaf = np.asarray(Image.fromarray((leaf * 255).astype(np.uint8)).filter(ImageFilter.MaxFilter(3))) > 0
# 葉の跡を、まわりの地面からなだらかにうめる（くり返しぼかす）
bg = C.copy()
bg[leaf] = C[~leaf].mean(0)
for _ in range(200):
    blur = np.asarray(Image.fromarray(bg.astype(np.uint8)).filter(ImageFilter.GaussianBlur(2))).astype(float)
    bg[leaf] = blur[leaf]
out_c = Image.fromarray(bg.astype(np.uint8))
leaf_img = crop.transpose(Image.FLIP_LEFT_RIGHT)
mask = Image.fromarray((leaf[:, ::-1] * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(0.8))
out_c.paste(leaf_img, (0, 0), mask)
out = a.copy(); out.paste(out_c, BOX[:2])
out.save(w / "edit_4_flip.png")
