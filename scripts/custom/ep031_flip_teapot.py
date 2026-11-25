"""第31回 第4問②「右のポットの口が反対向き」：ポットのまわりを左右反転して同じ場所に戻す（AIでは変わらなかったため）。
使い方: python3 scripts/custom/ep031_flip_teapot.py <作業フォルダ> → <作業>/edit_4_2.png"""
import sys
from pathlib import Path
from PIL import Image, ImageOps
w = Path(sys.argv[1])
a = Image.open(w / "q4_a.png").convert("RGB")
r = (1415, 955, 1705, 1190)
e = a.copy(); e.paste(ImageOps.mirror(a.crop(r)), r[:2]); e.save(w / "edit_4_2.png")
