"""第22回 第5問①「小鳥の向きが反対」を、画像APIを使わずにプログラムで作る（AIの描き直しは小鳥を別の杭へ動かしたため）。
元の絵（q5_a.png）の小鳥のまわり（杭の中心 x=276 が真ん中）を左右反転して、同じ場所に戻す（杭の上に立ったまま向きだけ変わる）。
使い方: python3 scripts/custom/ep022_flip_sparrow.py <作業フォルダ>   → <作業>/edit_5_flip.png"""
import sys
from pathlib import Path
from PIL import Image, ImageOps
w = Path(sys.argv[1])
a = Image.open(w / "q5_a.png").convert("RGB")
R = (141, 55, 411, 215)
a2 = a.copy()
a2.paste(ImageOps.mirror(a.crop(R)), R[:2])
a2.save(w / "edit_5_flip.png")
