"""かくし絵 試作4（方式③）：試作3の絵とAIで取った5つの位置をそのまま使い、物の範囲だけをプログラムで周りになじませる。
画像APIは使わない。共通のプログラムは変えない（画面と丸は kakushie_ai.py の screen・circles を読むだけ）。

使い方：python3 scripts/kakushie_blend.py <試作3のフォルダ> <設定json> <出力フォルダ>
設定（段階ごと）：
  texture   周りの模様を重ねる濃さ（0〜1）。物の範囲に、近くの同じ面から写した模様を半透明で重ねる
  color     色を周りに寄せる強さ（0〜1）。物の範囲の色の平均・ばらつき（R・G・B）を、物の周りの輪の値に合わせる
  sat       彩度を周りに寄せる強さ（0〜1）
  line_keep 元の輪郭の線（暗い線）を残す割合（0〜1）。形で見つけられるように少し残す
  line_thr  輪郭の線とみなす暗さ（周りの明るさの平均からの差、0〜255）
  texture_mode "mirror"（標準）：物のすぐ外側 band px の模様を、ふちで折り返して内側へ写す。"patch"：下の方法
  （patch：模様は、物と同じ大きさの近くの範囲のうち、周りの輪の色に近い画素が6割以上あるものから写す。無ければ重ねない）
  shrink    なじませる範囲（楕円）を枠の何倍にするか / feather はふちのぼかし（px）
"""
import json, sys
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

sys.path.insert(0, str(Path(__file__).parent))
import kakushie_ai as KA


def ellipse_mask(size, box, shrink, feather):
    W, H = size
    x0, y0, x1, y1 = box
    cx, cy, rx, ry = (x0 + x1) / 2, (y0 + y1) / 2, (x1 - x0) / 2 * shrink, (y1 - y0) / 2 * shrink
    m = Image.new("L", size, 0)
    ImageDraw.Draw(m).ellipse((cx - rx, cy - ry, cx + rx, cy + ry), fill=255)
    return np.asarray(m.filter(ImageFilter.GaussianBlur(feather)), dtype=np.float32) / 255


def ring_mask(size, box, shrink, width):
    """物の楕円のすぐ外側の輪（ここの色を「周り」とみなす）。"""
    inner = ellipse_mask(size, box, shrink, 0) > 0.5
    x0, y0, x1, y1 = box
    k = 1 + 2 * width / max(x1 - x0, y1 - y0)
    outer = ellipse_mask(size, box, shrink * k, 0) > 0.5
    return outer & ~inner


def stats(a, m):
    v = a[m]
    return v.mean(0), v.std(0) + 1e-3


def best_patch(a, box, others, ring_px):
    """物と同じ大きさの近くの範囲（16方向・距離0.6〜1.6倍）から、「周りの輪にある色」に近い画素がいちばん多いものを選ぶ。
    （別の面＝空・地面・落ち葉などが入った範囲は選ばれにくい）。ほかの物の枠と重なる所・絵の外は使わない。"""
    H, W, _ = a.shape
    x0, y0, x1, y1 = box
    w, h = x1 - x0, y1 - y0
    pal = ring_px[np.random.default_rng(0).choice(len(ring_px), min(400, len(ring_px)), replace=False)]   # 周りの色の見本
    best = None
    for d in (0.6, 0.8, 1.0, 1.2, 1.4, 1.6):
        for t in range(16):
            ang = t * np.pi / 8
            nx0, ny0 = int(x0 + np.cos(ang) * w * d), int(y0 + np.sin(ang) * h * d)
            if nx0 < 0 or ny0 < 0 or nx0 + w > W or ny0 + h > H:
                continue
            nb = (nx0, ny0, nx0 + w, ny0 + h)
            if any(not (nb[2] <= o[0] or nb[0] >= o[2] or nb[3] <= o[1] or nb[1] >= o[3]) for o in others + [tuple(box)]):
                continue
            p = a[ny0:ny0 + h:6, nx0:nx0 + w:6].reshape(-1, 3)
            dist = np.abs(p[:, None, :] - pal[None, :, :]).sum(-1).min(1)
            score = (dist < 45).mean()
            if best is None or score > best[0]:
                best = (score, nb)
    return best[1] if best and best[0] > 0.6 else None


def mirror_texture(a, box, shrink, band):
    """物の楕円のすぐ外側（幅 band px）の模様を、ふちで折り返して内側へ写す（行ったり来たり）。
    楕円の外のごく近くしか使わないので、空・地面など別の面が入りにくい。"""
    from scipy.ndimage import map_coordinates
    x0, y0, x1, y1 = box
    cx, cy, rx, ry = (x0 + x1) / 2, (y0 + y1) / 2, (x1 - x0) / 2 * shrink, (y1 - y0) / 2 * shrink
    yy, xx = np.mgrid[y0:y1, x0:x1].astype(np.float32)
    u, v = (xx - cx) / rx, (yy - cy) / ry
    rho = np.sqrt(u * u + v * v) + 1e-6
    b = band / ((rx + ry) / 2)
    t = np.mod(np.clip(1 - rho, 0, None), 2 * b)
    t = np.where(t > b, 2 * b - t, t)
    k = (1 + t) / rho
    sx, sy = cx + u * k * rx, cy + v * k * ry
    H, W, _ = a.shape
    sx, sy = np.clip(sx, 0, W - 1), np.clip(sy, 0, H - 1)
    return np.stack([map_coordinates(a[..., c], [sy, sx], order=1) for c in range(3)], -1)


def blend(img, items, lv):
    a = np.asarray(img, dtype=np.float32)
    out = a.copy()
    H, W, _ = a.shape
    boxes = [tuple(it["box_px"]) for it in items]
    used = []
    for i, it in enumerate(items):
        box = [max(0, boxes[i][0]), max(0, boxes[i][1]), min(W, boxes[i][2]), min(H, boxes[i][3])]
        m = ellipse_mask((W, H), box, lv["shrink"], lv["feather"])
        inner = m > 0.02
        ring = ring_mask((W, H), box, lv["shrink"], lv.get("ring", 40))
        rmu, rsd = stats(a, ring)
        omu, osd = stats(a, m > 0.5)
        x0, y0, x1, y1 = box
        reg = a[y0:y1, x0:x1].copy()
        # 1. 色を周りに寄せる（平均とばらつきを、周りの輪に合わせる）
        matched = (reg - omu) / osd * rsd + rmu
        reg_c = reg + (matched - reg) * lv["color"]
        # 2. 彩度を周りに寄せる
        def sat(x):
            mx, mn = x.max(-1), x.min(-1)
            return (mx - mn) / (mx + 1e-3)
        rs = sat(a[ring]).mean()
        g = reg_c.mean(-1, keepdims=True)
        cur = sat(reg_c).mean()
        f = 1 + (rs / max(cur, 1e-3) - 1) * lv["sat"]
        reg_c = g + (reg_c - g) * f
        # 3. 周りの模様を半透明で重ねる（近くの同じ面から写す）
        if lv.get("texture_mode", "mirror") == "mirror":
            tex, nb = mirror_texture(a, box, lv["shrink"], lv.get("band", 60)), "mirror"
        else:
            nb = best_patch(a, box, [b for j, b in enumerate(boxes) if j != i], a[ring])
            tex = a[nb[1]:nb[3], nb[0]:nb[2]] if nb else None
        if tex is not None:
            reg_c = reg_c * (1 - lv["texture"]) + tex * lv["texture"]
        used.append({"name": it["name"], "texture_from": nb})
        # 4. 元の輪郭の線（周りより暗い線）を少し残す
        lum = reg.mean(-1)
        line = np.clip((rmu.mean() - lv["line_thr"] - lum) / 40, 0, 1)[..., None]
        line_col = reg * 0.6 + reg_c * 0.4          # 線は元の線の色を、なじませた色に少し寄せる
        reg_c = reg_c * (1 - line * lv["line_keep"]) + line_col * line * lv["line_keep"]
        mm = m[y0:y1, x0:x1, None]
        out[y0:y1, x0:x1] = out[y0:y1, x0:x1] * (1 - mm) + np.clip(reg_c, 0, 255) * mm
    return Image.fromarray(np.clip(out, 0, 255).astype(np.uint8)), used


def main(src_dir, cfgp, out):
    src_dir, out = Path(src_dir), Path(out)
    out.mkdir(parents=True, exist_ok=True)
    cfg = json.loads(Path(cfgp).read_text(encoding="utf-8"))
    ans = json.loads((src_dir / "answers.json").read_text(encoding="utf-8"))
    img = Image.open(src_dir / "puzzle.jpg").convert("RGB")
    items = ans["items"]
    rec = {"source": str(src_dir / "puzzle.jpg"), "image_size": img.size, "items": items, "levels": cfg["levels"], "texture_from": {}}
    for name, lv in cfg["levels"].items():
        pz, used = blend(img, items, lv)
        pz.save(out / f"{name}_puzzle.jpg", quality=90)
        KA.screen(pz, items).save(out / f"{name}_screen.jpg", quality=90)
        KA.screen(KA.circles(pz, items), items, answer=True).save(out / f"{name}_answer_screen.jpg", quality=90)
        rec["texture_from"][name] = used
    (out / "answers.json").write_text(json.dumps(rec, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main(*sys.argv[1:4])
