"""型1（2026-11-28 CEO決定の標準）で thumb_Y_1.jpg を作り直す。帯・文字は scripts/thumb_band.make_type1（標準の仕組み）を使い、
絵だけこの試作の Y_a.png（主役を大きく切り出したもの。make_thumbs.py の pic）に差し替える。使い方：python3 make_thumb_type1.py"""
import sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2] / "scripts"))
sys.path.insert(0, str(HERE))
import thumb_band as TB
import importlib.util
spec = importlib.util.spec_from_file_location("mt", HERE / "make_thumbs.py")
src = (HERE / "make_thumbs.py").read_text(encoding="utf-8").split("\nfor st in")[0]   # 関数だけ読む（4枚を作り直さない）
ns = {"__file__": str(HERE / "make_thumbs.py")}; exec(src, ns)
p, top = ns["pic"]("Y")
TB.pics = lambda ep, q, sat=1.15: (p, p, top)      # 左右とも同じ元の絵（違いゼロ）
TB.make_type1(HERE / "thumb_Y_1.jpg", HERE, 1)
print(HERE / "thumb_Y_1.jpg")
