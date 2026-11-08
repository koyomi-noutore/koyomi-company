"""完成物の数値チェックと、目で見る確認用の一覧画像（社則7章：画像を見るのは1枚にまとめて1回）。
結果は <回>/check.json に書き、問題があれば一覧にして返す。"""
import json
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

import ep_timeline as T
from episode_plan import plan

LEVEL_RANGE = {"初級": (3.0, 4.0), "中級": (2.0, 3.0), "上級": (1.5, 2.0)}   # concept.md（画面幅に対する%）
TOL = 0.2   # 難易度表の「約」の幅（ポイント）。第5問の宝珠 2.07%・第3問の石 1.83% を「約」として扱った（事業部長判断 2026-11-06、監査で確認）


def probe(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration:stream=codec_type,width,height,r_frame_rate",
                        "-of", "json", str(path)], capture_output=True, text=True, check=True)
    return json.loads(r.stdout)


MIN_CENTER_DIST_PCT = 30  # 絵の幅に対する、違いの中心どうしの最小距離（%）
MIN_GAP_PCT = 10          # 違いの範囲どうしの最小のすき間（%）


def numeric(out_dir, work):
    out, work = Path(out_dir), Path(work)
    problems, info = [], {}
    ans = json.loads((out / "answers.json").read_text(encoding="utf-8"))
    for Q in ans["questions"]:
        lo, hi = LEVEL_RANGE[Q["level"]]
        if len(Q["answers"]) != 3:
            problems.append(f"第{Q['q']}問：違いが3つではない")
        if Q["outside_box_max_distance_px"] > 24:
            problems.append(f"第{Q['q']}問：範囲の外に差（範囲から{Q['outside_box_max_distance_px']}px）")
        # 違いどうしの散らばり（2026-11-06 CEO指示）：中心どうしの距離が絵の幅の30%以上、かつ範囲どうしが重ならず離れていること
        cx0, cy0, cx1, cy1 = Q["content_px"]
        cw = cx1 - cx0
        boxes = [(a["id"], a["box_px"]) for a in Q["answers"]]
        for i in range(len(boxes)):
            for j in range(i + 1, len(boxes)):
                (ia, A), (ib, B) = boxes[i], boxes[j]
                ca = ((A[0] + A[2]) / 2, (A[1] + A[3]) / 2)
                cb = ((B[0] + B[2]) / 2, (B[1] + B[3]) / 2)
                dist = ((ca[0] - cb[0]) ** 2 + (ca[1] - cb[1]) ** 2) ** 0.5 / cw * 100
                gap_x = max(B[0] - A[2], A[0] - B[2], 0)
                gap_y = max(B[1] - A[3], A[1] - B[3], 0)
                gap = max(gap_x, gap_y) / cw * 100
                if dist < MIN_CENTER_DIST_PCT or gap < MIN_GAP_PCT:
                    problems.append(f"第{Q['q']}問 違い{ia}と{ib}：近すぎる（中心の距離 {dist:.0f}%・すき間 {gap:.0f}%。目安は中心{MIN_CENTER_DIST_PCT}%以上・すき間{MIN_GAP_PCT}%以上）")
        for a in Q["answers"]:
            p = a["object_screen_width_pct"]
            if not (lo - TOL <= p <= hi + TOL):
                problems.append(f"第{Q['q']}問 違い{a['id']}：大きさ {p}% が{Q['level']}の目安 {lo}〜{hi}% の外")
            if not a["in_safe_y"]:
                problems.append(f"第{Q['q']}問 違い{a['id']}：上の帯か字幕の場所にかかる")
            if Q["level"] != "上級" and a["type"] == "色":
                problems.append(f"第{Q['q']}問 違い{a['id']}：{Q['level']}で色だけの違い")
    vj = work / "voice" / "voice.json"
    if vj.exists():
        over = [v["id"] for v in json.loads(vj.read_text(encoding="utf-8")) if not v["fits"]]
        if over:
            problems.append(f"声が枠に収まらない：{over}")
    else:
        problems.append("声がまだない")
    vid = out / "video.mp4"
    if vid.exists():
        pr = probe(vid)
        v = next(s for s in pr["streams"] if s["codec_type"] == "video")
        info["video"] = {"duration": float(pr["format"]["duration"]), "size": [v["width"], v["height"]], "fps": v["r_frame_rate"]}
        if [v["width"], v["height"]] != [1920, 1080] or abs(float(pr["format"]["duration"]) - T.TOTAL) > 0.5:
            problems.append(f"動画の大きさか長さが違う：{info['video']}")
    else:
        problems.append("動画がまだない")
    th = out / "thumbnail.jpg"
    if th.exists():
        im = Image.open(th)
        info["thumbnail"] = {"size": list(im.size), "bytes": th.stat().st_size}
        if im.size != (1280, 720) or th.stat().st_size >= 2_000_000:
            problems.append(f"サムネの大きさか容量が違う：{info['thumbnail']}")
    else:
        problems.append("サムネがまだない")
    res = {"problems": problems, "info": info}
    (out / "check.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    return res


def contact_sheet(out_dir, work, path, fontp=None):
    """主な場面を1枚にまとめる：オープニング・各問の答え合わせの最後・うんちく・エンディング・サムネ。"""
    out, work = Path(out_dir), Path(work)
    times = [("オープニング", 8)] + [(f"第{q}問 答え", s + T.CARD + T.SOLVE + T.ANSWER - 0.5) for q, s in T.Q_START.items()]
    times += [("うんちく", T.UNCHIKU[0] + 20), ("エンディング", T.ENDING[0] + 10)]
    tiles = []
    for label, t in times:
        f = work / f"sheet_{t:.1f}.png"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", str(t), "-i", str(out / "video.mp4"), "-frames:v", "1",
                        "-vf", "scale=640:360", str(f)], check=True)
        tiles.append((label, Image.open(f).convert("RGB")))
    if (out / "thumbnail.jpg").exists():
        tiles.append(("サムネ", Image.open(out / "thumbnail.jpg").convert("RGB").resize((640, 360))))
    cols = 3
    rows = (len(tiles) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * 650, rows * 390), (255, 255, 255))
    d = ImageDraw.Draw(sheet)
    for k, (label, im) in enumerate(tiles):
        x, y = (k % cols) * 650, (k // cols) * 390
        sheet.paste(im, (x, y + 25))
        d.text((x + 4, y + 2), label, fill=(0, 0, 0), font=ImageFont.truetype(str(fontp), 20) if fontp else None)
    sheet.save(path)
    return path
