"""第2回 第4問②（じょうろのはす口）・第5問②（屋根の鳥）：AIの描き直しで消した物の輪郭が薄く残った（監査の差し戻し）。
元の絵（a）で物があった所を5px広げた範囲のうち、描き直しの絵で本物の線（じょうろの管・屋根）でない所を、紙の地の色でうめる。
python3 ep002_clean_ghost.py <作業フォルダ>  →  <作業>/edit_4_2c.png, edit_5_2c.png"""
import sys
from pathlib import Path
import numpy as np
from PIL import Image, ImageFilter

JOBS = {4: (150, 1288, 262, 1388), 5: (488, 220, 596, 314)}   # 問: 範囲（8:9の絵の座標）
M = 12

w = Path(sys.argv[1])
for q, (x0, y0, x1, y1) in JOBS.items():
    a = Image.open(w / f"q{q}_a.png").convert("RGB")
    ed = Image.open(w / f"edit_{q}_2.png").convert("RGB")
    r = (x0 - M, y0 - M, x1 + M, y1 + M)
    A, E = np.asarray(a.crop(r)).astype(int), np.asarray(ed.crop(r)).astype(int)
    La, Le = A.mean(2), E.mean(2)
    paper = np.median(E[Le > np.percentile(Le, 50)], 0)               # 紙の地の色
    obj = La < paper.mean() - 8                                       # 元の絵で物があった所
    obj = np.asarray(Image.fromarray((obj * 255).astype(np.uint8)).filter(ImageFilter.MaxFilter(11))) > 0
    real = Le < 190                                                   # 描き直しで残す本物の線・色（管・瓦）
    real = np.asarray(Image.fromarray((real * 255).astype(np.uint8)).filter(ImageFilter.MaxFilter(13))) > 0
    # 描き直しが少しずれた位置に描いた薄い輪郭も消す：元の絵では紙だった所で、描き直しが紙より少し暗い所
    faint = (Le < paper.mean() - 5) & (La >= paper.mean() - 5)
    faint = np.asarray(Image.fromarray((faint * 255).astype(np.uint8)).filter(ImageFilter.MaxFilter(5))) > 0
    fill = (obj | faint) & ~real
    noise = E - np.asarray(ed.crop(r).filter(ImageFilter.GaussianBlur(3))).astype(int)
    out = np.where(fill[..., None], np.clip(paper + np.clip(noise, -2, 2), 0, 255), E).astype(np.uint8)
    res = ed.copy(); res.paste(Image.fromarray(out), r[:2])
    res.save(w / f"edit_{q}_2c.png")
