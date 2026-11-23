"""かくし絵 試作3（画像AIの描き直し方式、2026-11-19 CEO決定）。共通のプログラムは変えず、この1ファイルだけで動く。

使い方：python3 scripts/kakushie_ai.py <out> <工程>
  gen <n>      … 絵を n 枚、バッチ1回でまとめて生成する（<out>/cand_<i>.png）。画像APIの回数は n 回。
  locate <i>   … 候補 i の絵で、画像AI（文字で答えるモデル）に5つの物の位置を答えさせる（<out>/cand_<i>_loc.json）
  sheet        … 候補ぜんぶに、AIが答えた位置の丸を付けて並べた一覧（<out>/candidates_sheet.jpg）
  make <i>     … 候補 i を採用：puzzle.png・answer.png・screen.png・answer_screen.png・answers.json・video.mp4
キーは環境変数 GEMINI_API_KEY からだけ読む。
"""
import json, os, subprocess, sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).parent))

ITEMS = [  # 名前・英語・隠す場所・見本の形（kakushie.py の線画）
    {"name": "柿", "en": "persimmon (round fruit with a four-leaf calyx on top)", "where": "in the big white-and-grey cloud in the upper sky, formed by the cloud's own curling outlines and shading", "shape": "kaki"},
    {"name": "どんぐり", "en": "acorn (pointed nut with a scaly cap)", "where": "in the bark of the large tree trunk on the left, formed by the bark's cracks and knots in the same brown bark colors", "shape": "donguri"},
    {"name": "もみじ", "en": "maple leaf (five-pointed leaf)", "where": "in the mossy grey rock at the lower right, formed by the rock's cracks and moss edges in the same grey and green colors", "shape": "momiji"},
    {"name": "きのこ", "en": "mushroom (round cap on a short thick stem)", "where": "in the wooden fence boards in the middle right, formed by the wood grain lines and knots in the same pale wood colors", "shape": "kinoko"},
    {"name": "栗", "en": "chestnut (shiny nut, round bottom, pointed top)", "where": "in the ripples of the small stream at the bottom left, formed by the water's wave lines in the same blue and white colors", "shape": "kuri"},
]

STYLE = ("A Japanese picture-book illustration in watercolor with bold dark ink outlines and clear colors, for seniors. "
         "PORTRAIT composition, the painting fills the entire canvas edge to edge, no border. No people.")

PROMPT = (
    "Create a HIDDEN-PICTURE PUZZLE (like the classic 'hidden pictures' puzzles in children's magazines): "
    "an autumn countryside scene in Japan. Scene: a large tree trunk on the left with rough bark, a big puffy cloud in the sky, "
    "a wooden board fence in the middle right, a mossy grey rock at the lower right, a small stream with ripples at the bottom left, "
    "fallen leaves on the ground, distant hills. " + STYLE + "\n\n"
    "Exactly FIVE objects are hidden inside the scenery. Each one is part of the texture of the surface it sits on:\n"
    + "\n".join(f"{i + 1}. a {it['en']} hidden {it['where']}." for i, it in enumerate(ITEMS)) + "\n\n"
    "RULES for the hidden objects (very important):\n"
    "- Every one of the five MUST be present. Its outline must be clear and complete enough that a person who searches carefully can recognize the shape.\n"
    "- Draw each hidden object ONLY with the colors and line style of the surface around it, as if the surface naturally forms that shape. "
    "NEVER paint it in the object's natural color (no orange persimmon, no brown chestnut on water, no red maple leaf). It must not stand out at first glance.\n"
    "- Each hidden object is about 8% to 10% of the picture width. Keep them away from the picture edges (at least 8% inside).\n"
    "- Do NOT draw any other persimmons, acorns, maple leaves, mushrooms or chestnuts anywhere in the picture (the fallen leaves on the ground are plain oval leaves).\n"
    "- Absolutely NO numbers, letters, labels, arrows, circles, frames or markers anywhere. Do not mark the hidden objects in any way."
)

LOCATE = (
    "This is a hidden-picture puzzle. Five objects are camouflaged inside the scenery: "
    + ", ".join(f"{it['en']}" for it in ITEMS) + ". "
    "For each of the five, find where its SHAPE is hidden (it is drawn with the same colors as its surroundings, not in its natural color). "
    "Answer only with JSON: a list of objects {\"label\": one of [" + ", ".join(f'\"{it["name"]}\"' for it in ITEMS) + "], "
    "\"box_2d\": [ymin, xmin, ymax, xmax] normalized to 0-1000, \"found\": true/false, "
    "\"visibility\": 1-5 (1 = almost invisible, 3 = hidden but findable when searching, 5 = obvious at first glance), "
    "\"natural_color\": true if it is painted in the object's own natural color}. "
    "Also add a final object {\"label\": \"text\", \"found\": true/false} telling whether any numbers, letters or labels are drawn in the picture."
)

PW, PH = 960, 1080          # 出題画面の絵の大きさ（左半分）
FONT = Path.home() / ".cache/koyomi/fonts/package/900Black/NotoSansJP_900Black.ttf"
FONT_B = Path.home() / ".cache/koyomi/fonts/package/700Bold/NotoSansJP_700Bold.ttf"


def crop_89(im):
    """8:9 に中央で切る（出題画面の左半分に合わせる）。"""
    w, h = im.size
    if w / h > PW / PH:
        nw = round(h * PW / PH); x = (w - nw) // 2
        return im.crop((x, 0, x + nw, h))
    nh = round(w * PH / PW); y = (h - nh) // 2
    return im.crop((0, y, w, y + nh))


def gen(out, n):
    import gemini_image as G
    os.environ.setdefault("KOYOMI_IMAGE_USAGE_LOG", str(out / "image_usage.jsonl"))
    G.USAGE_LOG = os.environ["KOYOMI_IMAGE_USAGE_LOG"]
    have = sorted(out.glob("cand_*.png"))
    start = len([p for p in have if p.stem.count("_") == 1])
    jobs = {f"cand_{start + i}": {"prompt": PROMPT, "aspect": "4:5", "size": "2K"} for i in range(n)}
    (out / "prompt.txt").write_text(PROMPT, encoding="utf-8")
    res = G.generate_batch(jobs, name="kakushie_003")
    for k, im in res.items():
        crop_89(im).save(out / f"{k}.png")
        print(k, im.size)


BLEND = ("Edit this hidden-picture puzzle. Keep the whole scene, composition, colors and every other detail exactly the same. "
         "Change ONLY the five hidden objects (the persimmon in the cloud, the acorn in the tree bark, the mushroom on the fence boards, "
         "the maple leaf on the rock, the chestnut in the stream) so that they are much better camouflaged and NOT visible at first glance:\n"
         "- Remove their solid fill and shading. Let the surrounding texture run straight through each shape: cloud swirls through the persimmon, "
         "bark cracks and bark color through the acorn, wood grain lines and plank gaps through the mushroom, moss patches and rock cracks over the maple leaf, "
         "water ripple lines through the chestnut.\n"
         "- Keep only the OUTLINE of each shape, drawn {strength}, in the same color as the nearby texture lines, so the shape can still be found by a person who searches.\n"
         "- Make each shape a little smaller (about 8% of the picture width).\n"
         "- Do not add anything else. No numbers, letters, labels, arrows, circles or markers.")
STRENGTH = {"blend_mid": "as a thin line, about as dark as the surrounding texture lines, with a few small gaps",
            "blend_strong": "as a thin, broken line, slightly lighter than the surrounding texture lines, with several gaps"}


def blend(out, i):
    """候補 i を元に、隠れ方を2段階で描き直す（バッチ1回・2枚）。"""
    import gemini_image as G
    G.USAGE_LOG = str(out / "image_usage.jsonl")
    src = Image.open(out / f"cand_{i}.png").convert("RGB")
    jobs = {k: {"prompt": BLEND.format(strength=v), "images": [src], "aspect": "4:5", "size": "2K"} for k, v in STRENGTH.items()}
    (out / "prompt_blend.txt").write_text("\n\n".join(f"[{k}]\n" + j["prompt"] for k, j in jobs.items()), encoding="utf-8")
    for k, im in G.generate_batch(jobs, name="kakushie_003_blend").items():
        crop_89(im.resize(src.size) if abs(im.width / im.height - src.width / src.height) < 0.01 else im).resize(src.size).save(out / f"cand_{k}.png")
        print(k, im.size)


def locate(out, i):
    """位置は、文字で答えるモデル（gemini-2.5-flash）に聞く。画像の生成ではない。"""
    import base64, io, urllib.request
    im = Image.open(out / f"cand_{i}.png").convert("RGB")
    buf = io.BytesIO(); im.save(buf, "JPEG", quality=92)
    body = {"contents": [{"parts": [{"text": LOCATE}, {"inline_data": {"mime_type": "image/jpeg", "data": base64.b64encode(buf.getvalue()).decode()}}]}],
            "generationConfig": {"responseMimeType": "application/json", "temperature": 0.2}}
    model = os.environ.get("KAKUSHIE_LOCATE_MODEL", "gemini-3.5-flash")
    from gemini_image import generate_content  # 2026-11-24：Vertex 経由に統一
    res = generate_content(model, body)
    txt = "".join(p.get("text", "") for p in res["candidates"][0]["content"]["parts"])
    data = json.loads(txt)
    W, H = im.size
    for d in data:
        if "box_2d" in d:
            y0, x0, y1, x1 = d["box_2d"]
            d["box_px"] = [round(x0 * W / 1000), round(y0 * H / 1000), round(x1 * W / 1000), round(y1 * H / 1000)]
    rec = {"model": model, "usage": res.get("usageMetadata", {}), "items": data}
    (out / f"cand_{i}_loc.json").write_text(json.dumps(rec, ensure_ascii=False, indent=1), encoding="utf-8")
    with open(out / "image_usage.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps({"model": model, "kind": "locate", "key": f"cand_{i}", **{k: rec["usage"].get(k) for k in ("promptTokenCount", "candidatesTokenCount", "totalTokenCount")}}) + "\n")
    for d in data:
        print(d)


def font(s, p=FONT):
    return ImageFont.truetype(str(p), s)


def circles(im, items, num=True, show=None):
    im = im.copy(); d = ImageDraw.Draw(im)
    for k, it in enumerate(items):
        if show is not None and k >= show:
            break
        x0, y0, x1, y1 = it["box_px"]
        cx, cy, r = (x0 + x1) / 2, (y0 + y1) / 2, max(x1 - x0, y1 - y0) / 2 * 1.15 + 10
        w = max(6, im.width // 160)
        d.ellipse((cx - r - w, cy - r - w, cx + r + w, cy + r + w), outline=(255, 255, 255), width=w * 2)
        d.ellipse((cx - r, cy - r, cx + r, cy + r), outline=(220, 30, 30), width=w)
        if num:
            s = max(28, im.width // 30)
            bx, by = cx + r * 0.72, cy - r * 0.72
            d.ellipse((bx - s, by - s, bx + s, by + s), fill=(220, 30, 30), outline=(255, 255, 255), width=4)
            d.text((bx, by), str(k + 1), font=font(int(s * 1.3)), fill=(255, 255, 255), anchor="mm")
    return im


def sheet(out):
    cs = sorted(p for p in out.glob("cand_*.png") if not p.stem.endswith("_loc"))
    tiles = []
    for p in cs:
        im = Image.open(p).convert("RGB")
        lp = out / f"{p.stem}_loc.json"
        if lp.exists():
            items = [d for d in json.loads(lp.read_text(encoding="utf-8"))["items"] if "box_px" in d]
            im = circles(im, items)
        im = im.resize((640, 720))
        ImageDraw.Draw(im).text((10, 10), p.stem, font=font(40), fill=(255, 0, 0), stroke_width=3, stroke_fill=(255, 255, 255))
        tiles.append(im)
    S = Image.new("RGB", (640 * len(tiles), 720), "white")
    for k, t in enumerate(tiles):
        S.paste(t, (640 * k, 0))
    S.save(out / "candidates_sheet.jpg", quality=85)
    print(out / "candidates_sheet.jpg")


def icon(shape, size=130):
    import kakushie as K
    ic = Image.new("RGBA", (size, size), (0, 0, 0, 0)); di = ImageDraw.Draw(ic)
    for pts in K.transform(K.shape_lines(shape), (size / 2, size / 2), size * 0.85, 0, 99):
        di.line(pts, fill=(59, 47, 37, 255), width=6, joint="curve")
    return ic


def screen(pic, items, answer=False, show=5, timer=None):
    """左に絵（960×1080）、右に物の名前と形の見本。答えの画面は見つけた物に赤い番号。"""
    sc = Image.new("RGB", (1920, 1080), (246, 236, 216))
    sc.paste(pic.resize((PW, PH), Image.LANCZOS), (0, 0))
    d = ImageDraw.Draw(sc)
    d.text((1440, 78), "答え" if answer else "かくし絵", font=font(76), fill=(59, 47, 37), anchor="mm")
    d.text((1440, 158), "かくれているもの 5つ" if not answer else "ここに かくれていました", font=font(44, FONT_B), fill=(180, 70, 40), anchor="mm")
    for k, it in enumerate(items):
        y = 270 + k * 158
        d.rounded_rectangle((1040, y - 70, 1840, y + 70), 24, fill=(255, 250, 240), outline=(210, 190, 160), width=3)
        ic = icon(it["shape"])
        sc.paste(ic, (1070, y - 65), ic)
        d.text((1240, y), it["name"], font=font(72), fill=(59, 47, 37), anchor="lm")
        if answer and k < show:
            d.ellipse((1720, y - 42, 1804, y + 42), fill=(220, 30, 30), outline=(255, 255, 255), width=4)
            d.text((1762, y), str(k + 1), font=font(56), fill=(255, 255, 255), anchor="mm")
    if timer is not None:
        d.text((1440, 1040), f"のこり {timer} 秒", font=font(40, FONT_B), fill=(120, 100, 80), anchor="mm")
    return sc


def make(out, i):
    pic = Image.open(out / f"cand_{i}.png").convert("RGB")
    loc = json.loads((out / f"cand_{i}_loc.json").read_text(encoding="utf-8"))["items"]
    by = {d["label"]: d for d in loc if "box_px" in d}
    items = [dict(it, **{k: by[it["name"]][k] for k in ("box_px", "visibility", "natural_color") if k in by[it["name"]]}) for it in ITEMS]
    W = pic.width
    for it in items:
        x0, y0, x1, y1 = it["box_px"]
        it["width_pct_of_picture"] = round((x1 - x0) / W * 100, 1)
        it.pop("en"); it.pop("where")
    pic.save(out / "puzzle.png")
    circles(pic, items).save(out / "answer.png")
    screen(pic, items).save(out / "screen.png")
    screen(circles(pic, items), items, answer=True).save(out / "answer_screen.png")
    (out / "answers.json").write_text(json.dumps({"source": f"cand_{i}.png", "image_size": pic.size, "located_by": json.loads((out / f"cand_{i}_loc.json").read_text(encoding="utf-8"))["model"], "items": items},
                                                 ensure_ascii=False, indent=1), encoding="utf-8")
    # 試作動画 30秒：出題 20秒（のこり秒の表示）→ 答え 10秒（1つずつ丸が出る）
    fr = out / "_frames"; fr.mkdir(exist_ok=True)
    seq = []
    for s in range(20):
        p = fr / f"q{s:02d}.png"; screen(pic, items, timer=20 - s).save(p); seq.append((p, 1.0))
    p = fr / "a0.png"; screen(pic, items, answer=True, show=0).save(p); seq.append((p, 1.5))
    for k in range(1, 6):
        p = fr / f"a{k}.png"; screen(circles(pic, items, show=k), items, answer=True, show=k).save(p); seq.append((p, 1.5 if k < 5 else 2.5))
    lst = fr / "list.txt"
    lst.write_text("".join(f"file '{p}'\nduration {t}\n" for p, t in seq) + f"file '{seq[-1][0]}'\n", encoding="utf-8")
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(lst), "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo",
                    "-vf", "fps=30,format=yuv420p", "-c:v", "libx264", "-crf", "20", "-c:a", "aac", "-shortest", "-t", "30", str(out / "video.mp4")], check=True)
    for p in fr.iterdir():
        p.unlink()
    fr.rmdir()
    for p in ("screen", "answer_screen"):
        Image.open(out / f"{p}.png").convert("RGB").save(out / f"{p}.jpg", quality=90)
    print("ok", out)


if __name__ == "__main__":
    out = Path(sys.argv[1]).resolve(); out.mkdir(parents=True, exist_ok=True)
    step = sys.argv[2]
    if step == "gen":
        gen(out, int(sys.argv[3]))
    elif step == "blend":
        blend(out, sys.argv[3])
    elif step == "locate":
        locate(out, sys.argv[3])
    elif step == "sheet":
        sheet(out)
    elif step == "make":
        make(out, sys.argv[3])
