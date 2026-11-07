"""第2回 第1問②：描き直し（版1）で花束全体が5輪に描き直されたので、増えた花のうち1輪だけを元の絵に貼る（3輪→4輪）。
元の3輪は元の絵のまま。貼るのは、元の絵で壁（花のない所）だった画素だけ（画像APIは使わない）。
python3 ep002_q1_one_flower.py <作業フォルダ>  →  <作業>/edit_1_one.png"""
import sys
from pathlib import Path
import numpy as np
from PIL import Image, ImageFilter

BOX = (215, 935, 382, 1110)    # 増えた1輪（左上）のまわり（8:9の絵の座標）

w = Path(sys.argv[1])
a = Image.open(w / "q1_a.png").convert("RGB")
e = Image.open(w / "edit_1_1.png").convert("RGB")
A, E = np.asarray(a.crop(BOX)).astype(int), np.asarray(e.crop(BOX)).astype(int)
Ha = np.asarray(a.crop(BOX).convert("HSV")).astype(int)
wall_a = Ha[..., 1] < 110                                            # 元の絵で壁（彩度が低い）＝花のない所
changed = np.abs(A - E).max(2) > 25
m = changed & wall_a
m = np.asarray(Image.fromarray((m * 255).astype(np.uint8)).filter(ImageFilter.MinFilter(3)).filter(ImageFilter.MaxFilter(5))) > 0
mask = Image.fromarray((m & wall_a) .astype(np.uint8) * 255).filter(ImageFilter.GaussianBlur(1))
out = a.copy(); c = a.crop(BOX); c.paste(e.crop(BOX), (0, 0), mask); out.paste(c, BOX[:2])
out.save(w / "edit_1_one.png")
