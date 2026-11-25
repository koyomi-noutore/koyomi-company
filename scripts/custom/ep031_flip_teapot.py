"""第31回 第4問②「右のポットが黄色」：ポットの胴・ふた・取っ手を、陰影を残したまま黄色に塗る（形と位置は変えない）。
（最初は左右反転で作ったが、消し跡が残ったため色の違いに変更。ファイル名は plan.json の program_edits のまま）
使い方: python3 scripts/custom/ep031_flip_teapot.py <作業フォルダ> → <作業>/edit_4_2.png"""
import sys
from pathlib import Path
import numpy as np, cv2
w = Path(sys.argv[1])
a = cv2.imread(str(w / "q4_a.png"))
x0, y0, x1, y1 = 1380, 930, 1740, 1220
c = a[y0:y1, x0:x1].copy()
m = np.zeros(c.shape[:2], np.uint8)
bgd, fgd = np.zeros((1, 65)), np.zeros((1, 65))
cv2.grabCut(c, m, (30, 20, 320, 255), bgd, fgd, 8, cv2.GC_INIT_WITH_RECT)
fg = np.where((m == 1) | (m == 3), 255, 0).astype(np.uint8)
n, lab, st, _ = cv2.connectedComponentsWithStats(fg)
i = 1 + int(np.argmax(st[1:, cv2.CC_STAT_AREA]))
fg = (lab == i).astype(np.uint8) * 255
dark = ((c.max(2) < 75) & (cv2.dilate(fg, np.ones((3, 3), np.uint8)) > 0)).astype(np.uint8) * 255
dark = cv2.morphologyEx(dark, cv2.MORPH_CLOSE, np.ones((9, 9), np.uint8))
cs, _ = cv2.findContours(dark, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
M = np.zeros_like(fg); cv2.drawContours(M, [max(cs, key=cv2.contourArea)], -1, 255, -1)
body = ((M > 0) & (c.max(2) >= 75)).astype(np.float32)        # 輪郭の黒い線は残す
body = cv2.GaussianBlur(body, (3, 3), 0)[..., None]
L = cv2.cvtColor(c, cv2.COLOR_BGR2GRAY).astype(np.float32) / 255.0
L = np.clip((L - 0.45) / 0.55, 0, 1)                           # 白〜水色の陰影 → 0..1
shade = 0.55 + 0.45 * L                                         # 暗い所は濃い黄、明るい所は明るい黄
yel = np.stack([40 * shade, 205 * shade, 255 * shade], -1)      # BGR の黄色（陰影つき）
out = (yel * body + c.astype(np.float32) * (1 - body)).astype(np.uint8)
e = a.copy(); e[y0:y1, x0:x1] = out
cv2.imwrite(str(w / "edit_4_2.png"), e)
