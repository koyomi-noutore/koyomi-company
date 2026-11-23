"""第22回 第5問①「カップの真ん中の花がオレンジ色になる」を、画像APIを使わずにプログラムで作る（ファイル名は最初に小鳥の向きで作った名残り）。
元の絵（q5_a.png）のカップの真ん中の花の範囲の、青い画素だけの色相をオレンジに変える。物を動かさないので消し跡は出ない。
使い方: python3 scripts/custom/ep022_flip_sparrow.py <作業フォルダ>   → <作業>/edit_5_flip.png"""
import sys
from pathlib import Path
import numpy as np
from PIL import Image
w = Path(sys.argv[1])
a = Image.open(w / "q5_a.png").convert("RGB")
R = (246, 912, 306, 983)
c = a.crop(R); arr = np.asarray(c).astype(int)
blue = (arr[..., 2] > arr[..., 0] + 25) & (arr[..., 2] > 90)
hsv = np.asarray(c.convert("HSV")).copy()
hsv[..., 0] = np.where(blue, 20, hsv[..., 0])
hsv[..., 1] = np.where(blue, np.minimum(255, hsv[..., 1] * 1.5 + 30), hsv[..., 1])
c2 = Image.fromarray(hsv, "HSV").convert("RGB")
a2 = a.copy(); a2.paste(c2, R[:2]); a2.save(w / "edit_5_flip.png")
