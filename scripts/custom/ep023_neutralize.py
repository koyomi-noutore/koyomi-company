"""第23回：絵の赤みを抑える（concept.md 2026-11-23）。左右の絵（a・b）に同じ補正をかける＝違いには影響しない。
赤÷青（100×100に縮めた平均）が 1.43 を超える問だけ、赤を下げ青を上げて半分ずつ寄せる（thumb_band.neutral と同じ式）。
第21回は一度の補正で整数の切り捨てが残り 1.45 をわずかに超えたため、左右とも 1.44 以下になるまで同じ補正をくり返す。
使い方：python3 scripts/custom/ep023_neutralize.py <回のフォルダ>   （pictures の貼り戻しのあとに1回。補正済みなら何もしない）"""
import sys
from pathlib import Path
from PIL import Image, ImageStat

T, LIMIT = 1.43, 1.44


def ratio(im):
    r, g, b = ImageStat.Stat(im.resize((100, 100))).mean
    return r / max(b, 1)


def fix(im, k):
    R, G, B = im.split()
    return Image.merge("RGB", (R.point(lambda v: min(255, round(v * k))), G, B.point(lambda v: min(255, round(v / k)))))


ep = Path(sys.argv[1])
for qa in sorted(ep.glob("q*_a.png")):
    qb = qa.with_name(qa.name.replace("_a", "_b"))
    a, b = Image.open(qa).convert("RGB"), Image.open(qb).convert("RGB")
    r0 = max(ratio(a), ratio(b))
    if r0 <= LIMIT:
        print(qa.name, f"赤÷青 {r0:.3f}：補正なし")
        continue
    for _ in range(8):
        k = (T / max(ratio(a), ratio(b))) ** 0.5
        a, b = fix(a, k), fix(b, k)
        if max(ratio(a), ratio(b)) <= LIMIT:
            break
    a.save(qa); b.save(qb)
    print(qa.name, f"赤÷青 {r0:.3f} → a {ratio(a):.3f} / b {ratio(b):.3f}（左右に同じ補正）")
