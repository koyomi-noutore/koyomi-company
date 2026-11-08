"""第3回：プログラムで作る違い（画像APIは使わない）。
- 第4問「増える」：空を舞う紅葉の葉（元の絵 [1165,714,1229,777]）を1.25倍にして、空の別の所（左上の [520,640]）に1枚足す → <作業>/edit_4_leaf.png
- 第5問「色」2つ：右のさざんかの花1輪をピンク→白、地面の落ち葉1枚を茶→緑 → <作業>/edit_5_color.png
python3 ep003_program.py <作業フォルダ>"""
import sys
from pathlib import Path
import numpy as np
from PIL import Image, ImageFilter

w = Path(sys.argv[1])

# 第4問：舞う葉を1枚増やす
a = Image.open(w / "q4_a.png").convert("RGB")
SRC, DST, K = (1150, 700, 1244, 792), (520, 640), 1.25
crop = a.crop(SRC)
C = np.asarray(crop).astype(int)
leaf = (C[..., 0] - C[..., 2] > 40) | (C.mean(2) < 150)            # 葉の色と輪郭
leaf = np.asarray(Image.fromarray((leaf * 255).astype(np.uint8)).filter(ImageFilter.MaxFilter(3))) > 0
size = (round(crop.width * K), round(crop.height * K))
big = crop.resize(size, Image.LANCZOS).rotate(-25, resample=Image.BICUBIC, fillcolor=(255, 255, 255))
mask = Image.fromarray((leaf * 255).astype(np.uint8)).resize(size, Image.LANCZOS).rotate(-25, resample=Image.BICUBIC).filter(ImageFilter.GaussianBlur(0.8))
out = a.copy(); out.paste(big, DST, mask); out.save(w / "edit_4_leaf.png")

# 第5問：色を2か所変える
from scipy import ndimage
a = Image.open(w / "q5_a.png").convert("RGB")
out = a.copy()
FLOWER = (1546, 1259, 1632, 1361)
c = np.asarray(a.crop(FLOWER)).astype(float)
pink = (c[..., 0] - c[..., 1] > 30) & (c[..., 0] > 160)
lab, n = ndimage.label(ndimage.binary_closing(pink, iterations=2))
main = lab == max(range(1, n + 1), key=lambda i: (lab == i).sum())     # この花の花びらだけ（となりの花には触れない）
main = ndimage.binary_fill_holes(main) & pink
L = c.mean(2)
white = np.stack([255 - (255 - L) * 0.35, 255 - (255 - L) * 0.38, 255 - (255 - L) * 0.33], 2)   # 白い花びら（陰はうすく残す）
c2 = np.where(main[..., None], white, c)
out.paste(Image.fromarray(np.clip(c2, 0, 255).astype(np.uint8)), FLOWER[:2])
LEAF = (976, 1670, 1068, 1712)
crop = out.crop(LEAF)
c = np.asarray(crop.convert("HSV")).astype(int)
rgb = np.asarray(crop).astype(int)
deep = (c[..., 0] < 40) & (c[..., 1] > 105) & (c[..., 2] < 225)   # 葉そのもの（まわりの薄いにじみより色が濃い）
lab, n = ndimage.label(ndimage.binary_closing(deep, iterations=2))
brown = ndimage.binary_fill_holes(lab == max(range(1, n + 1), key=lambda i: (lab == i).sum())) & (c[..., 0] < 40) & (rgb.mean(2) >= 110) 
dark = rgb.mean(2) < 120
xs = [x for x in range(dark.shape[1]) if dark[:, x].any()]
bottom = np.interp(np.arange(dark.shape[1]), xs, [np.nonzero(dark[:, x])[0].max() for x in xs])   # 葉の下の線（列ごと、間は補う）
bottom = ndimage.maximum_filter1d(bottom, 9)                        # 1列だけ線が欠けた所でずれないように
yy = np.arange(dark.shape[0])[:, None]
brown &= yy <= bottom[None, :] + 1                                  # 下の線より下（影のにじみ）は変えない
brown = ndimage.binary_closing(brown, structure=np.ones((1, 9))) & (rgb.mean(2) >= 80) & (yy <= bottom[None, :] + 1)   # 細いすき間（葉脈）もうめる。真っ黒な輪郭は残す
c[..., 0] = np.where(brown, 55, c[..., 0])                          # 茶 → 落ち着いた黄緑
c[..., 1] = np.where(brown, (c[..., 1] * 0.75).astype(int), c[..., 1])
out.paste(Image.fromarray(c.astype(np.uint8), "HSV").convert("RGB"), LEAF[:2])
out.save(w / "edit_5_color.png")

# 第4問「自転車のかごがない」：AIの描き直しで、かごの跡にうすい灰色のにじみが残ったので、ハンドルより右の白い紙の所だけ紙の色にもどす
e = Image.open(w / "edit_4_1.png").convert("RGB")
a4 = Image.open(w / "q4_a.png").convert("RGB")
R = (1615, 1262, 1752, 1405)
c = np.asarray(e.crop(R)).astype(int)
ca = np.asarray(a4.crop(R)).astype(int)
L = c.mean(2)
paper = np.median(c[L > np.percentile(L, 60)], 0)
red = (c[..., 0] - c[..., 1] > 60)
basket = ndimage.binary_dilation(np.abs(ca - c).max(2) > 25, iterations=4)   # 元の絵でかごがあった所
fix = basket & (L > 165) & ~red & (np.abs(c - paper).max(2) > 4)
fix &= ~ndimage.binary_dilation((L <= 165) | red, iterations=6)       # 本物の線・ハンドル・赤い車体のそば（6px）は変えない
c2 = np.where(fix[..., None], paper, c)
e.paste(Image.fromarray(c2.astype(np.uint8)), R[:2])
e.save(w / "edit_4_1c.png")

