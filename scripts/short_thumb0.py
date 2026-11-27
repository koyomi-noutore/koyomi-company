"""ショートのサムネを「動画の0秒目の画面」にする（2026-11-27 CEO決定・厳守）。

Studio の「動画からフレームを選択」の一番左（0:00）と同じ画面を、ショートを作ったプログラムで描き直し、
thumbnails.set でサムネに設定する。動画ファイル（git管理外）が無くても作れる。

使い方：
  python3 scripts/short_thumb0.py render <ショートのフォルダ>      # <フォルダ>/thumb0.jpg を作り、確認画像との差を出す
  python3 scripts/short_thumb0.py set <ショートのフォルダ>         # render ＋ 差が小さければ YouTube に設定
  python3 scripts/short_thumb0.py all [--dry-run]                   # upload.json のあるショートを全部（1本ずつ別プロセス）

ショートのフォルダ：
  間違い探し      outputs/<回>/short・short2（plan.json・q*_a.png・answers.json から ep_short で描く）
  文字・ちがう    outputs/<日付>_text_NNN（problem.json。無いものは text_001〜003・010〜014 の決まった種類）
  虫めがね        outputs/<日付>_mushi_NNN（description.md の見出しの id で mushimegane_defs.json を引く）

照合（描き直した画面が、実際の動画の0秒目と同じか）：
  間違い探し      <フォルダ>/phone_intro.png（作ったときの確認画像。最初の幕）と、描き直した画面の phone_mock を比べる
  文字・虫めがね  <フォルダ>/frames.jpg の一番左（0:00、270×480）と比べる
  差（平均の色の差）が LIMIT を超えたら「不一致」で設定しない。確認画像の無いものは「照合なし」（all では設定しない）。
季節の色は、問題の季節 → 冬 → 秋 → winter_A〜C の順に試し、いちばん近いものを使う（作ったときの --season が残っていないため）。
"""
import json, os, re, subprocess, sys
from pathlib import Path
from PIL import Image, ImageChops, ImageStat

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).parent))
LIMIT = 6.0
SEASONS = [None, "冬", "秋", "winter_A", "winter_B", "winter_C"]   # 照合が LIMIT 以下になったところで止める
BUILTIN = {"text_001": ("T", "pref"), "text_002": ("T", "cross"), "text_003": ("T", "kanji"),
           "text_010": ("C", "easy"), "text_011": ("C", "hard"), "text_012": ("C", "mikan"),
           "text_013": ("C", "futsu"), "text_014": ("C", "mitten")}


def ensure_font():
    nb = Path.home() / ".cache/koyomi/fonts/package/900Black/NotoSansJP_900Black.ttf"
    if not nb.exists():
        nb.parents[2].mkdir(parents=True, exist_ok=True)
        subprocess.run(["npm", "pack", "--silent", "@expo-google-fonts/noto-sans-jp@0.4.4"], cwd=nb.parents[2], stdout=subprocess.DEVNULL, check=True)
        for t_ in nb.parents[2].glob("noto*.tgz"):
            subprocess.run(["tar", "xzf", t_.name], cwd=nb.parents[2], check=True)


def diff(a, b):
    a, b = a.convert("RGB"), b.convert("RGB").resize(a.size)
    return round(sum(ImageStat.Stat(ImageChops.difference(a, b)).mean) / 3, 2)


def kind_of(folder):
    b = folder.name
    if b.startswith("short"):
        return "ep"
    return "mushi" if "_mushi_" in b else "text"


# ---------- 描き直し ----------
def render_ep(folder, season):
    ep = folder.parent
    os.environ["KOYOMI_EPISODE_DIR"] = str(ep)
    if season:
        os.environ["KOYOMI_THEME"] = season
    import ep_short as S
    n = 1 if folder.name == "short" else int(folder.name[5:])
    S.use(n)
    c = S.cfg()
    q = c["question"]
    ans = {Q["q"]: Q for Q in json.loads((ep / "answers.json").read_text(encoding="utf-8"))["questions"]}[q]
    S.CTX.update(ep=ep, drawn=[], Q=ans, voice=[], lines=[], end_at=1e9, total=1e9)
    S.CROP = tuple(ans["content_px"])
    from PIL import ImageDraw
    pics = {s: Image.open(ep / f"q{q}_{s}.png").convert("RGB").crop(S.CROP).resize((S.PW, S.PH), Image.LANCZOS) for s in "ab"}
    S.apply_season()
    base = Image.new("RGB", (S.W, S.H), S.BG)
    for s, y in S.YS.items():
        base.paste(pics[s], (S.PX, y))
        ImageDraw.Draw(base).rectangle((S.PX - 4, y - 4, S.PX + S.PW + 3, y + S.PH + 3), outline=S.FRAME, width=4)
    S.CTX["base"] = base
    S.CTX["bold"] = str(Path.home() / ".cache/koyomi/fonts/package/900Black/NotoSansJP_900Black.ttf")
    im = S.render(0.0)
    ref = folder / "phone_intro.png"
    return im, (S.phone_mock(im), Image.open(ref)) if ref.exists() else None


def old_intro(mod, kind, cfg, frame):
    """当時の build() の「最初の画面」の行を、そのまま当時のモジュールで計算する（声は作らない）。"""
    import inspect, textwrap
    src = textwrap.dedent(inspect.getsource(mod.build)).splitlines()
    body, seen = [], False
    for ln in src[1:]:
        t = ln.strip()
        if t.startswith("seq.append(("):
            expr = t[len("seq.append(("):]
            depth, i = 0, 0
            for i, ch in enumerate(expr):
                depth += ch in "([{"
                depth -= ch in ")]}"
                if ch == "," and depth == 0:
                    break
            body.append("    __im = " + expr[:i])
            seen = True
            break
        if "say(" in t or "voice(" in t or t.startswith("def ") or t.startswith("w, dur") or t.startswith("from ") or t.startswith("import "):
            continue
        body.append("    " + t)
    assert seen
    code = "def __f(kind, cfg, frame, L, n_ans, d_intro):\n" + "\n".join(body) + "\n    return __im\n"
    g = dict(vars(mod)); loc = {}
    exec(code, g, loc)
    return loc["__f"](kind, cfg, frame, mod.LINES.get(kind) if hasattr(mod, "LINES") else None, 1, 0.0)


def render_text(folder, season):
    import text_shorts as T
    if season:
        T.SEASON_ARG = season
        T.set_season(season)
    P = folder / "problem.json"
    key = re.search(r"(text_\d+)", folder.name).group(1)
    if P.exists():
        k = json.loads(P.read_text(encoding="utf-8"))["kind"]
        if k in ("pref", "cross", "kanji"):
            kind = T.load_problem(P)
        elif k == "scatter":
            import chigau_shorts as C
            kind = C.load_problem(P)
        else:
            import chigau_pic_shorts as CP
            kind = CP.load_problem(P)
    else:
        mod, kind = BUILTIN[key]
        if mod == "C":
            import chigau_shorts  # noqa: F401  （T.KINDS に easy などを登録する）
    cfg, frame, _ = T.KINDS[kind]
    import importlib
    mod = T if (P.exists() and json.loads(P.read_text(encoding="utf-8"))["kind"] in ("pref", "cross", "kanji")) or (not P.exists() and BUILTIN[key][0] == "T") else importlib.import_module("chigau_shorts")
    if mod is not T:
        mod.LINES = T.LINES
        g = vars(mod)
        if "T" in g:   # chigau_shorts の build は T.〜 で text_shorts の部品を呼ぶ
            pass
    im = old_intro(mod, kind, cfg, frame)
    return im, tile0(folder)


def render_mushi(folder, season):
    import text_shorts as T
    if season:
        T.SEASON_ARG = season
        T.set_season(season)
    import mushimegane_shorts as M
    head = (folder / "description.md").read_text(encoding="utf-8").splitlines()[0]
    iid = re.search(r"（([a-z]+)・", head).group(1)
    item = next(i for i in M.DEFS if i["id"] == iid)
    pic = M.picture(item)
    vl = T.intro_lines([f"この{item['kind']}", "なーんだ？", ["虫めがねで", "accent"], ["のぞいてみてね", "accent"]], explicit=True)
    im = T.speaker(T.veil(M.frame(item, pic, "cover", 0), vl, T.INTRO_GAP), "normal", None)
    return im, tile0(folder)


def old_scripts(folder):
    """upload.json を足したコミットの scripts/ を作業場所に取り出す。ほかのフォルダ（絵・声の部品）は今のリポジトリを指す。"""
    import tempfile
    c = subprocess.run(["git", "-C", str(ROOT), "log", "--diff-filter=A", "--format=%H", "-1", "--", str(folder / "upload.json")],
                       capture_output=True, text=True).stdout.strip()
    base = Path(tempfile.gettempdir()) / "koyomi_old" / c[:10]
    if not (base / "scripts").exists():
        base.mkdir(parents=True, exist_ok=True)
        tar = subprocess.run(["git", "-C", str(ROOT), "archive", c, "scripts"], capture_output=True, check=True).stdout
        subprocess.run(["tar", "x", "-C", str(base)], input=tar, check=True)
        for p in ROOT.iterdir():
            if p.name not in ("scripts", ".git") and not (base / p.name).exists():
                (base / p.name).symlink_to(p)
    return base / "scripts"


def tile0(folder):
    f = folder / "frames.jpg"
    if not f.exists():
        return None
    return Image.open(f).crop((0, 0, 270, 480))


def render_one(folder, season):
    ensure_font()
    k = kind_of(folder)
    if k == "mushi":   # 絵の元画像（作業場所）が無いと画像APIで描き直してしまう（費用・別の絵）。描き直さない
        raise SystemExit("虫めがねは元の絵が無いので描き直せない")
    im, ref = {"ep": render_ep, "text": render_text}[k](folder, season)
    if ref is None:
        return im, None
    mine, theirs = ref if isinstance(ref, tuple) else (im.resize((270, 480), Image.LANCZOS), ref)
    return im, diff(mine, theirs)


def best(folder):
    """季節を変えて描き直し、確認画像にいちばん近いものを thumb0.jpg に保存する。別プロセスで1季節ずつ（モジュールの状態を持ち越さない）。"""
    res = []
    for s in SEASONS:
        r = subprocess.run([sys.executable, __file__, "_one", str(folder), s or "-"], capture_output=True, text=True)
        m = re.search(r"DIFF (\S+)", r.stdout)
        if not m:
            res.append((99.0, s, r.stderr.strip()[-300:]))
            continue
        d = m.group(1)
        res.append((99.0 if d == "None" else float(d), s, d))
        if d == "None" or float(d) <= LIMIT:
            break
    res.sort(key=lambda x: x[0])
    d, s, raw = res[0]
    subprocess.run([sys.executable, __file__, "_one", str(folder), s or "-", "--save"], capture_output=True, text=True)
    return (None if raw == "None" else d), s, res


def set_thumb(folder):
    from youtube_upload import access_token, set_thumbnail
    vid = json.loads((folder / "upload.json").read_text(encoding="utf-8"))["video_id"]
    r = set_thumbnail(vid, folder / "thumb0.jpg", access_token())
    return vid, bool(r.get("items"))


def short_folders():
    out = []
    for f in sorted(ROOT.glob("outputs/**/upload.json")):
        j = json.loads(f.read_text(encoding="utf-8"))
        d = f.parent
        if j.get("short") or ("_text_" in d.name or "_mushi_" in d.name):
            out.append(d)
    return out


def main():
    a = sys.argv[1:]
    if a[0] == "_one":
        folder, season = Path(a[1]).resolve(), (None if a[2] == "-" else a[2])
        if kind_of(folder) == "text":   # 動画を作った当時のプログラムで描く（画面の作りが後から変わっているため）
            sys.path.insert(0, str(old_scripts(folder)))
            for m in [m for m in list(sys.modules) if m in ("text_shorts", "chigau_shorts", "chigau_pic_shorts", "short_outro", "season_pick")]:
                del sys.modules[m]
        im, d = render_one(folder, season)
        if "--save" in a:
            im.convert("RGB").save(folder / "thumb0.jpg", quality=90)
        print("DIFF", d)
        return
    if a[0] in ("render", "set"):
        folder = Path(a[1]).resolve()
        d, s, res = best(folder)
        print(folder.name, "差", d, "季節", s or "問題の季節", [(x[0], x[1]) for x in res])
        if a[0] == "set":
            if d is None or d > LIMIT:
                sys.exit(f"照合できない・不一致（差 {d}）。設定しない")
            print(set_thumb(folder))
        return
    if a[0] == "all":
        dry = "--dry-run" in a
        log = []
        for folder in short_folders():
            d, s, res = best(folder)
            # 照合画像の無い文字の回（text_010〜014 など）は、当時のプログラムで描いたので設定してよい（記録に「照合なし」と残す）
            ok = (d is not None and d <= LIMIT) or (d is None and kind_of(folder) == "text" and s is None)
            vid = json.loads((folder / "upload.json").read_text(encoding="utf-8"))["video_id"]
            done = set_thumb(folder)[1] if ok and not dry else False
            log.append({"folder": str(folder.relative_to(ROOT)), "video_id": vid, "diff": d, "season": s, "set": done})
            print(json.dumps(log[-1], ensure_ascii=False), flush=True)
        (ROOT / "logs" / "short_thumb0_last.json").write_text(json.dumps(log, ensure_ascii=False, indent=1), encoding="utf-8")
        return
    sys.exit(__doc__)


if __name__ == "__main__":
    main()
