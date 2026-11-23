"""第21回：絵の赤みを抑える（concept.md 2026-11-23）。左右の絵（a・b）に同じ補正をかける＝違いには影響しない。
赤÷青（100×100に縮めた平均）が 1.44 を超える問だけ、赤を下げ青を上げて半分ずつ寄せる（thumb_band.neutral と同じ式）。
使い方：python3 scripts/custom/ep021_neutralize.py <回のフォルダ>   （pictures の貼り戻しのあとに1回。補正済みなら何もしない）"""
import sys
from pathlib import Path
from PIL import Image, ImageStat

T = 1.44
ep = Path(sys.argv[1])
for qa in sorted(ep.glob("q*_a.png")):
    qb = qa.with_name(qa.name.replace("_a", "_b"))
    a, b = Image.open(qa).convert("RGB"), Image.open(qb).convert("RGB")
    r, g, bl = ImageStat.Stat(a.resize((100, 100))).mean
    ratio = r / max(bl, 1)
    if ratio <= T:
        print(qa.name, f"赤÷青 {ratio:.2f}：補正なし")
        continue
    k = (T / ratio) ** 0.5
    def fix(im):
        R, G, B = im.split()
        return Image.merge("RGB", (R.point(lambda v: min(255, int(v * k))), G, B.point(lambda v: min(255, int(v / k)))))
    fix(a).save(qa); fix(b).save(qb)
    r2, g2, b2 = ImageStat.Stat(fix(a).resize((100, 100))).mean
    print(qa.name, f"赤÷青 {ratio:.2f} → {r2 / b2:.2f}（左右に同じ補正）")
