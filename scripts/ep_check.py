"""完成物の数値チェックと、目で見る確認用の一覧画像（社則7章：画像を見るのは1枚にまとめて1回）。
結果は <回>/check.json に書き、問題があれば一覧にして返す。"""
import json
import re
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

import ep_timeline as T
from episode_plan import plan

LEVEL_RANGE = {"やさしい": (6.0, 8.0), "初級": (5.0, 6.0), "中級": (4.0, 5.0), "上級": (3.0, 4.0)}   # concept.md「難易度の引き下げ（2026-11-18）」：画面幅に対する%（2026-11-18 CEO確認）
TOL_UP = 1.5   # 大きすぎる側（易しくなる向き）は広めに許す：監査は2回とも軽微扱い（第8回 2026-11-18）。難易度を下げる方針（2026-11-18）にも沿う
TOL = 0.3   # 難易度表の「約」の幅（ポイント）。第5問の宝珠 2.07%・第3問の石 1.83% を「約」として扱った（事業部長判断 2026-11-06、監査で確認）


def probe(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration:stream=codec_type,width,height,r_frame_rate",
                        "-of", "json", str(path)], capture_output=True, text=True, check=True)
    return json.loads(r.stdout)


MIN_CENTER_DIST_PCT = 30  # 絵の幅に対する、違いの中心どうしの最小距離（%）
MIN_GAP_PCT = 10          # 違いの範囲どうしの最小のすき間（%）


_EASY = ("増える", "なくなる", "形", "色", "大きさ", "一部欠け")   # 色ははっきり違う色だけ（監査で確かめる）
LEVEL_TYPES = {"やさしい": _EASY, "初級": _EASY + ("向き", "入れ替え"), "中級": _EASY + ("向き", "入れ替え", "模様", "数"),
               "上級": _EASY + ("向き", "入れ替え", "模様", "数")}
DIFF_TYPES = ("増える", "なくなる", "色", "形", "向き", "模様", "大きさ", "数", "一部欠け", "入れ替え")


UPPER_MAX = 4.0   # 上級（第5問）の大きさの上限（2026-11-25 CEO決定。目安 3.0〜4.0% の上を超えたら止める）


_ATTR = ("向き", "色", "形", "数", "模様", "大きさ", "柄", "中", "上", "下", "横", "前", "後ろ", "うしろ", "奥", "手前", "左", "右", "端", "先", "底", "内側", "外側", "まわり", "そば")                 # 「〜の向き」のように、物ではなく性質を指す語
_ALIAS = {"長ぐつ": "長靴", "ながぐつ": "長靴", "カップ": "コップ", "おわん": "わん", "お椀": "わん", "椀": "わん", "お茶わん": "茶わん",
          "どんぐり": "どんぐり", "かご": "かご", "籠": "かご", "ひしゃく": "ひしゃく", "柄杓": "ひしゃく"}   # 表記ゆれを同じ物として数える（2026-11-26）


def _object_of(label):
    """違いの label（例「小さい雪だるまのマフラーが緑」）から物の名前（「マフラー」）を取り出す。
    「クーラーボックスの向き」のように取り出した語が性質（向き・色…）なら、その前の物の名前を使う。表記ゆれは _ALIAS で同じ物にする。"""
    head = str(label).split("が")[0].split("は")[0]
    parts = [x.strip() for x in head.split("の") if x.strip()]
    obj = parts[-1] if parts else ""
    while obj in _ATTR and len(parts) >= 2:     # 「かごの中」「机の上」のように位置・性質の語なら、その前の物の名前に
        parts = parts[:-1]
        obj = parts[-1]
    if len(obj) == 1 and len(parts) >= 2 and "\u3041" <= obj <= "\u30ff":   # 「湯のみ」→「み」にしない（かな1字なら前とつなぐ。「カップの花」の花はそのまま）
        obj = parts[-2] + "の" + obj
    return _ALIAS.get(obj, obj)


def _objects_of(label):
    """違いに出てくる物の名前の集まり。「器がみかんに」のような入れ替えは、変わった先（みかん）も数える（2026-11-26 監査 W10-3-2）。"""
    lab = str(label)
    objs = {_object_of(lab)}
    m = re.search(r"が(.+?)(?:に|へ)(?:なる|なった|変わる|かわる)?$", lab)
    if m:
        objs.add(_object_of(m.group(1)))
    objs |= {k for k, v in _ALIAS.items() for o in list(objs) if v == o}   # 表記ゆれの別の書き方も持つ（ティーカップ／カップ＝コップ。2026-11-26 監査 W10-2-3）
    return {o for o in objs if o}


def _same_obj(a, b):
    """同じ物か。表記の一方がもう一方を含む（植木／植木鉢、みかん／みかん箱）なら同じ物と数える（2026-11-26 監査 W10-3-1）。"""
    return a == b or (min(len(a), len(b)) >= 2 and (a in b or b in a))


def repeat_problems():
    """同じ物・同じ変化は1回の動画の中で1度まで（2026-11-25 CEO決定）。plan.json の diffs の label で調べる。"""
    from episode_plan import plan as _plan
    seen_label, seen_obj, out = {}, {}, []
    for Q in _plan()["questions"]:
        for d in Q.get("diffs", []):
            lab = str(d.get("label", "")).strip()
            if not lab:
                continue
            objs = _objects_of(lab)
            key = (Q["q"], d["id"])
            hit = next(((o, seen_obj[s_]) for o in objs for s_ in seen_obj if _same_obj(o, s_)), None)
            if lab in seen_label:
                q0, i0 = seen_label[lab]
                out.append(f"第{Q['q']}問 違い{d['id']}：同じ変化「{lab}」が第{q0}問 違い{i0}にもある（1回の動画で1度まで。2026-11-25 CEO決定）")
            elif hit:
                obj, (q0, i0, lab0) = hit
                out.append(f"第{Q['q']}問 違い{d['id']}：同じ物「{obj}」が第{q0}問 違い{i0}（{lab0}）にもある（1回の動画で1度まで。2026-11-25 CEO決定）")
            seen_label.setdefault(lab, key)
            for obj in objs:
                seen_obj.setdefault(obj, (Q["q"], d["id"], lab))
    return out


def numeric(out_dir, work):
    out, work = Path(out_dir), Path(work)
    problems, info = [], {}
    blocking = []   # 2026-11-25 CEO決定：これが1つでもあれば check で止める（make_episode が終了コード1）
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
            if Q["level"] == "上級" and p > UPPER_MAX:   # 2026-11-25 CEO決定：上級は4.0%以下。超えたら止める
                blocking.append(f"第{Q['q']}問 違い{a['id']}：上級なのに大きさ {p}%（上級は{UPPER_MAX}%以下。2026-11-25 CEO決定）")
            if not (lo - TOL <= p <= hi + TOL_UP):
                problems.append(f"第{Q['q']}問 違い{a['id']}：大きさ {p}% が{Q['level']}の目安 {lo}〜{hi}% の外")
            if not a["in_safe_y"]:
                problems.append(f"第{Q['q']}問 違い{a['id']}：上の帯か字幕の場所にかかる")
            if a["type"] not in LEVEL_TYPES[Q["level"]]:   # 難易度ごとに使える違いの種類（concept.md 2026-11-18 の表）
                problems.append(f"第{Q['q']}問 違い{a['id']}：{Q['level']}では使わない種類「{a['type']}」")
        # 足す・入れ替える違いには context（この場所に、この置かれ方で普通あるか）を書く（concept.md「第10回からの改善」）
        from episode_plan import plan as _plan
        _pq = {x["q"]: x for x in _plan()["questions"]}[Q["q"]]
        for dd in _pq.get("diffs", []):
            if dd["type"] in ("増える", "入れ替え") and not str(dd.get("context", "")).strip():
                problems.append(f"第{Q['q']}問 違い{dd['id']}：{dd['type']}なのに context（置かれ方）が空")
        # 違いの種類を混ぜる（2026-11-15 最低品質4）：「増える・なくなる」は1問に1つまで。type は決まった種類から
        types = [a["type"] for a in Q["answers"]]
        bad = [t for t in types if t not in DIFF_TYPES]
        if bad:
            problems.append(f"第{Q['q']}問：違いの type が決まりの種類にない {bad}（{'・'.join(DIFF_TYPES)}）")
        if sum(t in ("増える", "なくなる") for t in types) > 1:
            problems.append(f"第{Q['q']}問：「増える・なくなる」が{sum(t in ('増える', 'なくなる') for t in types)}つ（1つまで）")
    blocking += repeat_problems()
    vj = work / "voice" / "voice.json"
    import ep_timeline as T
    problems += [f"読み・間：{p}" for p in T.readings_check(out / "readings_check.md")]
    if T.CTA:
        problems.append("timeline.cta がある（登録のお願いはエンディングだけ。2026-11-15）")
    if vj.exists():
        import ep_voice as V
        res = json.loads(vj.read_text(encoding="utf-8"))
        over = [v["id"] for v in res if not v["fits"]]
        if over:
            problems.append(f"声が枠に収まらない：{over}")
        problems += [f"間が0.4秒未満：{g}" for g in V.gap_problems(res)]
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
    problems = blocking + problems
    res = {"problems": problems, "blocking": blocking, "info": info}
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


def zoom_sheet(out_dir, path, cols=3):
    """消し残りの拡大チェック（2026-11-14 CEO指摘・audit チェックリスト）：違いごとに、範囲のまわりを画面の大きさに縮めてから3倍にし、
    左（元の絵）・右（違いのある絵）を並べた一覧を作る。ひも・尾・輪郭の切れ端・影が残っていないかを見る。"""
    import json
    from PIL import Image, ImageDraw
    out = Path(out_dir)
    ans = json.loads((out / "answers.json").read_text(encoding="utf-8"))
    tiles = []
    for Q in ans["questions"]:
        cx0, cy0, cx1, cy1 = Q["content_px"]; s = 960 / (cx1 - cx0)
        ims = {k: Image.open(out / f"q{Q['q']}_{k}.png").convert("RGB").crop((cx0, cy0, cx1, cy1)).resize((960, 1080), Image.LANCZOS) for k in "ab"}
        for a in Q["answers"]:
            x0, y0, x1, y1 = a["box_screen"]; m = 14
            r = (max(0, x0 - m), max(0, y0 - m), min(960, x1 + m), min(1080, y1 + m))
            k = 3 if max(r[2] - r[0], r[3] - r[1]) * 3 <= 330 else 330 / max(r[2] - r[0], r[3] - r[1])
            pair = [ims[x].crop(r).resize((int((r[2] - r[0]) * k), int((r[3] - r[1]) * k)), Image.LANCZOS) for x in "ab"]
            t = Image.new("RGB", (pair[0].width * 2 + 8, pair[0].height + 26), "white")
            t.paste(pair[0], (0, 26)); t.paste(pair[1], (pair[0].width + 8, 26))
            ImageDraw.Draw(t).text((4, 4), f"Q{Q['q']}-{a['id']} {a['type']} {a['label']}", fill=(200, 0, 0))
            tiles.append(t)
    W = max(t.width for t in tiles) + 10; H = max(t.height for t in tiles) + 10
    sheet = Image.new("RGB", (W * cols, H * ((len(tiles) + cols - 1) // cols)), (230, 230, 230))
    for i, t in enumerate(tiles):
        sheet.paste(t, ((i % cols) * W, (i // cols) * H))
    sheet.save(path)
    return path


def short_safe(ep, work, n=1):
    """ショートの画面の作りの判定（shorts.md「ショートの画面の作り（2026-11-18 夜 改訂）」）。
    文字・こよみ先生が左右36px・上120pxにかからないこと、絵が左右中央にあることを確かめ、
    実機の画面を重ねた確認画像 <回>/short*/phone_question.png・phone_end.png と、お手本と並べた compare_competitor1.png を作る。"""
    import ep_short as S
    S.use(n)
    S.setup(ep, work, S.CTX.get("font") or str(next(Path(work).glob("fontpkg/package/*/*.ttf"))))
    return S.safe_check(ep, work)
