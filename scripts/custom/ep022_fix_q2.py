"""第22回 第2問③（りすがいない）の消し跡の修正：りすの尾の先が残った所（x 200〜275, y 1080〜1118）を、すぐ横の平らな背景（x+100）で埋める。
q2_b.png だけに使う（pictures の貼り戻しとあか補正のあとに実行。何度やっても同じ）。使い方: python3 scripts/custom/ep022_fix_q2.py <回のフォルダ>"""
import sys
from pathlib import Path
from PIL import Image, ImageFilter
ep = Path(sys.argv[1])
b = Image.open(ep / "q2_b.png").convert("RGB")
r = (195, 1072, 285, 1124)
src = b.crop((r[0] + 105, r[1], r[2] + 105, r[3]))
m = Image.new("L", src.size, 255).filter(ImageFilter.GaussianBlur(1))
mm = Image.new("L", src.size, 0); mm.paste(255, (8, 8, src.width - 8, src.height - 8)); mm = mm.filter(ImageFilter.GaussianBlur(6))
b.paste(src, r[:2], mm); b.save(ep / "q2_b.png")
