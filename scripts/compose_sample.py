"""見本の画面（1920×1080）を組み立てる：左に元の絵、右に間違いのある絵、右下にこよみ先生。
文字は入れない（字幕は動画側で入れる）。答えの画面には円を描く。"""
import json, sys
from pathlib import Path
from PIL import Image, ImageDraw
sys.path.insert(0, str(Path(__file__).parent))
from koyomi_svg import koyomi_svg, render_png

W, H, BG = 1920, 1080, (246, 236, 216)
IW, IH, TOP, GAP = 940, 529, 110, 13  # 上：タイトル用、下：字幕用の余白


def compose(out_dir, diffs):
    out = Path(out_dir)
    a = Image.open(out / "picture_a.png"); b = Image.open(out / "picture_b.png")
    scale = IW / a.width
    xs = [(W - 2 * IW - GAP) // 2, (W - 2 * IW - GAP) // 2 + IW + GAP]
    owl_png = out / "koyomi_futsu.png"
    svg = koyomi_svg("futsu", 400)
    (out / "koyomi_futsu.svg").write_text(svg, encoding="utf-8")
    render_png(svg, str(owl_png), 400)
    owl = Image.open(owl_png).convert("RGBA").resize((380, 380), Image.LANCZOS)

    def frame(with_answers):
        f = Image.new("RGB", (W, H), BG)
        d = ImageDraw.Draw(f)
        for x, im in zip(xs, (a, b)):
            d.rounded_rectangle((x - 6, TOP - 6, x + IW + 6, TOP + IH + 6), 10, fill=(120, 90, 60))
            f.paste(im.resize((IW, IH), Image.LANCZOS), (x, TOP))
        if with_answers:
            for df in diffs:
                x0, y0, x1, y1 = [v * scale for v in df["box"]]
                for x in xs:
                    d.ellipse((x + x0 - 8, TOP + y0 - 8, x + x1 + 8, TOP + y1 + 8), outline=(220, 30, 30), width=8)
        f.paste(owl, (W - 380 - 40, H - 380 - 10), owl)
        return f

    frame(False).save(out / "sample_question.png")
    frame(True).save(out / "sample_answer.png")
    ans = [{"id": d["id"], "level": d["level"], "label": d["label"], "box_px": d["box"],
            "box_ratio": [round(d["box"][0] / a.width, 4), round(d["box"][1] / a.height, 4),
                          round(d["box"][2] / a.width, 4), round(d["box"][3] / a.height, 4)],
            "screen_width_pct": round((d["box"][2] - d["box"][0]) * scale / W * 100, 1)} for d in diffs]
    (out / "answers.json").write_text(json.dumps({"image_size": a.size, "answers": ans}, ensure_ascii=False, indent=1), encoding="utf-8")
