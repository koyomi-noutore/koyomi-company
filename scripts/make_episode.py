"""1本の動画をつくる手順をまとめたもの（社則7章：毎回の作業は「plan.json を書く→このスクリプトを実行→監査」だけ）。

使い方:
  python3 scripts/make_episode.py <回のフォルダ> <手順> [引数] [--work <作業フォルダ>]

  回のフォルダ：outputs/YYYY-MM-DD_<回番号>/（plan.json と description.md を置く）
  作業フォルダ：途中のファイル（元の絵の原寸・描き直し・声・フォント・こよみ先生の絵・動画の部品）。
                省略すると ~/.cache/koyomi/<回のフォルダ名>/。成果物フォルダには残さない（社則6章）。

手順（ふつうは all → check → 監査 → upload の順）:
  setup                       フォント（npm の Zen Maru Gothic, OFL）とこよみ先生の6表情のPNGを作業フォルダに用意する
  pictures                    絵をすべて作る：元の絵（画像API 1回/問）→ 描き直し（1回/問）→ 予備 → プログラムの違い
                              → 貼り戻し → answers.json → 描き直しの使う部分を <回>/edits/ に残す。
                              作業フォルダか <回>/edits/ にあるものは作り直さない（画像APIの無駄打ちをしない）
  pictures base|edit <問> [版]  1問ずつ（edit の版は省略で "1"）
  pictures batch base|edit[:版] [問 ...]  まとめてバッチ（約半額）で頼み、終わるまで待つ。問を省くと全問。
                              版2以降の描き直しの指示は plan.json の questions[].edit_prompts に書く
                              plan.json の images.batch が true なら、pictures（引数なし）も元の絵と描き直し(版1)をバッチで先に作る
  pictures retry <問> <版>      予備の描き直し（plan.json の retries）
  pictures compose|answers    貼り戻しだけ／answers.json だけ
  voice [id ...]              声（Fish Audio）。声に渡す文が変わったセリフだけ作り直す。id を書くとそのセリフを作り直す
  audio                       声・BGM・効果音を1本の WAV に（BGMと効果音はプログラムで合成したオリジナル）
  video                       動画（1920×1080, 30fps）を <回>/video.mp4 に書き出す。timeline.json も書く
  thumbnail                   サムネ（1280×720, 2MB未満）を <回>/thumbnail.jpg に
  all                         setup → pictures → voice → audio → video → thumbnail → check
  check                       数値チェック（<回>/check.json）と、目で見る確認用の一覧画像（<作業>/sheet.png）
  frame <秒>                  その時刻の画面を1枚 <作業>/frame_<秒>.png に
  balance                     Fish Audio の残高とプランの枠
  upload                      監査に合格した動画を YouTube に**非公開**でアップロードし、サムネを設定する
                              （<回>/audit_passed が必要。監査が合格のときに書く）
  short                       ショート（knowledge/shorts.md）：plan.json の short.question の1問を縦1080×1920に（上下2枚・15〜45秒・
                              最後に長尺へ案内）。声→音→動画→説明欄→数値チェック→一覧画像。画像APIは使わない
  short-voice [id ...]        ショートの声だけを作り直して、映像はそのままで音を入れ替える（id を書くとそのセリフだけ、省くと全部）
  retitle [サムネ]             アップ済みの動画のタイトル（description.md）とサムネ（既定 thumbnail_v3.jpg）だけを差し替える（説明欄・タグは変えない）
  short [n] / short-upload [n] n本目のショート（2本目は <回>/short2/。plan.json の shorts）
  log-time <工程> <秒>        スクリプトの外の工程（監査など）の時間を outputs/<回>/timing.json に足す
  short-upload                ショートを非公開でアップロード（<回>/short/audit_passed と、長尺の <回>/upload.json が必要）

サムネの確認（2026-11-24 CEO厳守）：scripts/thumb_same_check.py（左右が同じ絵か）を、thumbnail の直後と、upload・retitle・short-upload の前に自動で行う。
  対象は <回>/ab/thumb_*.jpg と <回>/thumbnail.jpg。1枚でも不合格なら止まる（終了コード1）。サムネが1枚もなくても止まる。
  ショート自身のサムネは0:00の画面（左右に並べた絵ではない）なので確認の対象外。かわりに、short-upload では元の長尺のサムネが全部合格でなければ上げない。
  既存の在庫（第10〜19回など）は作り直さない（CEO判断）。それらの回で止まっても作り直さず、報告する。

2回分をつないだ全10問の回（2026-11-26 CEO決定）：scripts/combine_episodes.py が <回>/ に plan.json（combined あり）・絵・answers.json・description.md を作る。
  そのあとは voice → audio → video → thumbnail → check（all も可。pictures は何もしない＝画像APIは使わない）。サムネは plan.json の thumbnail.style=band（thumb_band.py）。

費用の記録：画像APIは <回>/image_usage.jsonl、声は <作業>/voice/usage.jsonl に自動で残る。cost.md は制作部が書く。
"""
import json
import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
FONT_PKG = "@expo-google-fonts/zen-maru-gothic@0.4.2"
FONT_FILE = "package/700Bold/ZenMaruGothic_700Bold.ttf"


def log(msg):
    print(f"[make_episode] {msg}", flush=True)


def setup(work):
    work.mkdir(parents=True, exist_ok=True)
    font = work / "fontpkg" / FONT_FILE
    if not font.exists():
        (work / "fontpkg").mkdir(exist_ok=True)
        subprocess.run(["npm", "pack", "--silent", FONT_PKG], cwd=work / "fontpkg", check=True, stdout=subprocess.DEVNULL)
        tgz = next((work / "fontpkg").glob("*.tgz"))
        subprocess.run(["tar", "xzf", tgz.name], cwd=work / "fontpkg", check=True)
    owl = work / "owl"
    if not (owl / "koyomi_normal.png").exists():
        env = dict(os.environ, NODE_PATH=subprocess.run(["npm", "root", "-g"], capture_output=True, text=True).stdout.strip())
        subprocess.run(["node", str(HERE / "render_expressions.js"), str(owl), "480"], check=True, env=env)
    return font


def combined(ep):
    """2回分をつないだ回（scripts/combine_episodes.py が作る。plan.json に combined がある）。絵・答えはもう <回>/ にある。"""
    return "combined" in json.loads((ep / "plan.json").read_text(encoding="utf-8"))


def pictures(ep, work, args):
    if combined(ep):
        log("絵：つないだ回なので作らない（元の回の絵・答えを写してある。画像APIは使わない）")
        return
    import ep_pictures as P
    pw = work / "pictures"
    pw.mkdir(parents=True, exist_ok=True)
    if args and args[0] in ("base", "edit"):
        q = int(args[1])
        return P.base(q, pw) if args[0] == "base" else P.edit(q, pw, *(args[2:3] or ["1"]))
    if args and args[0] == "batch":
        qs = [int(x) for x in args[2:]] or list(P.diffs())
        kind, _, ver = args[1].partition(":")
        return P.base_batch(qs, pw) if kind == "base" else P.edit_batch(qs, pw, ver or "1")
    if not args and P._I.get("batch"):
        todo = [q for q in P.diffs() if not (ep / f"q{q}_a.png").exists()]
        P.base_batch(todo, pw)
        need1 = [q for q, ds in P.diffs().items() if any(d.get("src", "1") == "1" and not P.patch_path(ep, q, d).exists() for d in ds)
                 and (q, "1") not in P.PROGRAM_EDITS and (q, "1") not in P.RETRY]
        P.edit_batch(need1, pw, "1")
    if args and args[0] == "retry":
        return P.retry(int(args[1]), args[2], pw)
    if not args or args[0] == "compose":
        for q, ds in P.diffs().items():
            # 描き直しの版ごとに、使う部分が <回>/edits/ に残っていない版だけを作る（残っている版は作り直さない：画像APIの無駄打ち防止）
            need = sorted({d.get("src", "1") for d in ds if not P.patch_path(ep, q, d).exists()})
            if not (ep / f"q{q}_a.png").exists() and not (pw / f"q{q}_a.png").exists():
                P.base(q, pw)
            for v in need:
                if (pw / f"edit_{q}_{v}.png").exists():
                    continue
                if (q, v) in P.PROGRAM_EDITS:
                    if not (pw / f"q{q}_a.png").exists():
                        (pw / f"q{q}_a.png").write_bytes((ep / f"q{q}_a.png").read_bytes())
                    P.program_edit(q, v, pw)
                elif (q, v) in P.RETRY:
                    P.retry(q, v, pw)
                else:
                    P.edit(q, pw, v)
            P.compose(q, pw, ep)
            log(f"第{q}問の絵：OK")
    if not args or args[0] in ("compose", "answers"):
        r = P.answers(pw, ep)
        P.export_patches(pw, ep)
        for Q in r["questions"]:
            log(f"第{Q['q']}問 {Q['level']}：範囲外の差 {Q['outside_box_pixels_diff_gt15']}画素（最大{Q['outside_box_max_distance_px']}px） "
                + " ".join(f"違い{a['id']}={a['object_screen_width_pct']}%{'' if a['in_level_range'] else '(目安外)'}" for a in Q["answers"]))


def voice(work, ids, ep=None):
    import ep_timeline as T
    import ep_voice as V
    # 最低品質1・2：漢字が残っている／文が多い／詰まっているなら、声を作らずに止める（対照表は readings_check.md）
    P = T.readings_check((ep or Path(os.environ["KOYOMI_EPISODE_DIR"])) / "readings_check.md")
    if P:
        raise SystemExit("声を作る前に直すこと：\n" + "\n".join(P))
    res = V.make_all(work / "voice", ids)
    over = [r["id"] for r in res if not r["fits"]]
    gaps = V.gap_problems(res)
    log(f"声：{len(res)}セリフ、枠を超えたもの {over or 'なし'}、間が0.4秒未満 {gaps or 'なし'}")


def audio(work):
    import ep_audio as A
    A.main(str(work / "voice"), str(work / "mix.wav"))


def video(ep, work, font):
    import ep_timeline as T
    import ep_video as Vd
    T.export(ep / "timeline.json")
    # ep_video は作業フォルダの owl/ と voice/voice.json を使い、動画の部品（part*.mp4）も作業フォルダに書く
    Vd.main(str(ep), str(work), str(font), str(work / "mix.wav"))
    log(f"動画：{ep / 'video.mp4'}")


def thumb_files(ep):
    """確認の対象：<回>/ab/thumb_*.jpg（テストと比較の案）と <回>/thumbnail.jpg（アップロード用）。"""
    return sorted((ep / "ab").glob("thumb_*.jpg")) + ([ep / "thumbnail.jpg"] if (ep / "thumbnail.jpg").exists() else [])


def thumb_guard(ep, what="サムネ", files=None, need=True):
    """サムネが左右まったく同じ絵か確かめる（2026-11-24 CEO厳守。scripts/thumb_same_check.py）。1枚でも不合格なら、ここで止める（終了コード1）。
    サムネを作った直後と、アップロードの前（upload・retitle・short-upload）で呼ぶ。files を省くと thumb_files(ep)。
    need が True でサムネが1枚も無いときも止める（サムネなしでアップロードしない）。"""
    import thumb_same_check as Tc
    files = thumb_files(ep) if files is None else files
    if not files:
        if need:
            raise SystemExit(f"{what}の確認：サムネ（{ep / 'thumbnail.jpg'}）がありません。サムネなしでは先へ進めません")
        return
    bad = []
    for f_ in files:
        ok, dd = Tc.check(f_)
        log(f"{what}の確認：{'合格' if ok else '不合格（左右がちがう）'} {f_}  差={dd}")
        if not ok:
            bad.append(f_.name)
    if bad:
        log(f"{what}の確認：{len(bad)}枚が不合格です（{', '.join(bad)}）。サムネは、違いを作る前の元の絵を左右に2枚並べる決まりです（knowledge/episode-checklist.md【厳守】）。"
            "作り直してから進めてください。")
        sys.exit(1)


def plan_thumb(ep):
    return json.loads((ep / "plan.json").read_text(encoding="utf-8")).get("thumbnail", {})


def thumbnail(ep, font):
    # テストと比較の案（<回>/ab/thumb_A.jpg）があれば、それをアップロード用のサムネにする（2026-11-14 監査：旧型で上書きしていた）
    if (ep / "ab" / "thumb_A.jpg").exists():
        (ep / "thumbnail.jpg").write_bytes((ep / "ab" / "thumb_A.jpg").read_bytes())
        log(f"サムネ：{ep / 'thumbnail.jpg'}（ab/thumb_A.jpg を写した）")
    elif plan_thumb(ep).get("style") == "band":     # 2026-11-26 つないだ長尺：サムネの標準（黄帯・左右とも元の絵）
        import thumb_band as B
        c = plan_thumb(ep)
        B.make(ep / "thumbnail.jpg", ep, c["question"], B.Y if c.get("band") == "yellow" else B.K, tuple(c["top"]), tuple(c["bottom"]))
        log(f"サムネ：{ep / 'thumbnail.jpg'}（thumb_band.py）")
    else:
        import ep_thumbnail as Th
        log(f"サムネ：{Th.make(ep, font)}")
    thumb_guard(ep, "サムネを作った直後")      # 2026-11-24 CEO厳守：左右がちがえば、ここで止める


def check(ep, work):
    import ep_check as C
    r = C.numeric(ep, work)
    sheet = C.contact_sheet(ep, work, work / "sheet.png", setup(work)) if (ep / "video.mp4").exists() else None
    log(f"数値チェック：{'問題なし' if not r['problems'] else '問題あり'}")
    for p in r["problems"]:
        log(f"  - {p}")
    if sheet:
        log(f"一覧画像：{sheet}")
    log(f"拡大チェック（消し残り）：{C.zoom_sheet(ep, work / 'zoom.png')}")
    if r.get("blocking"):   # 2026-11-25 CEO決定：上級が4.0%を超える・同じ物／同じ変化のくり返しは、ここで止める
        log("止める：次を直してから進める（監査に回さない）")
        for p in r["blocking"]:
            log(f"  × {p}")
        sys.exit(1)
    return r


def upload(ep):
    if not (ep / "audit_passed").exists():
        raise SystemExit("監査の合格（<回>/audit_passed）がありません。合格していない動画はアップロードしない（社則6章）")
    thumb_guard(ep, "アップロード前")           # 2026-11-24 CEO厳守：ab/thumb_*.jpg と thumbnail.jpg の全部が合格でなければ上げない
    import youtube_upload as U
    U.upload(ep, thumbnail=ep / "thumbnail.jpg")


def main():
    argv = sys.argv[1:]
    work = None
    if "--work" in argv:
        i = argv.index("--work")
        work = Path(argv[i + 1]).resolve()
        del argv[i:i + 2]
    ep = Path(argv[0]).resolve()
    step, args = argv[1], argv[2:]
    os.environ["KOYOMI_EPISODE_DIR"] = str(ep)
    os.environ.setdefault("KOYOMI_IMAGE_USAGE_LOG", str(ep / "image_usage.jsonl"))
    work = work or Path.home() / ".cache" / "koyomi" / ep.name
    work.mkdir(parents=True, exist_ok=True)
    if step == "log-time":     # 監査など、スクリプトの外の工程の時間を記録する：log-time <工程> <秒>
        record_time(ep, args[0], float(args[1]), "手で記録")
        return
    import time as _time
    t0 = _time.time()
    try:
        run_step(ep, work, step, args)
    finally:
        record_time(ep, STEP_GROUP.get(step, step), _time.time() - t0, " ".join([step] + args))


# 工程ごとの時間（2026-11-18 CEO指示：outputs/<回>/timing.json）。絵・音声・書き出し・監査 にまとめる
STEP_GROUP = {"pictures": "絵", "voice": "音声", "audio": "音声", "video": "書き出し", "thumbnail": "書き出し",
              "check": "監査（数値チェック）", "short": "ショート", "short-voice": "ショート", "upload": "アップロード", "short-upload": "アップロード"}


def record_time(ep, group, sec, detail):
    import datetime
    p = ep / "timing.json"
    data = json.loads(p.read_text(encoding="utf-8")) if p.exists() else {"runs": [], "total_sec_by_step": {}}
    data["runs"].append({"step": group, "detail": detail, "sec": round(sec, 1),
                         "at": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")})
    tot = data["total_sec_by_step"]
    tot[group] = round(tot.get(group, 0) + sec, 1)
    data["total_sec_all"] = round(sum(tot.values()), 1)
    p.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")


def run_step(ep, work, step, args):
    if step == "setup":
        log(f"フォント：{setup(work)}")
    elif step == "pictures":
        pictures(ep, work, args)
    elif step == "voice":
        voice(work, args)
    elif step == "audio":
        audio(work)
    elif step == "video":
        video(ep, work, setup(work))
    elif step == "thumbnail":
        thumbnail(ep, setup(work))
    elif step == "check":
        check(ep, work)
    elif step == "frame":
        import ep_video as Vd
        out = work / f"frame_{args[0]}.png"
        Vd.frame(float(args[0]), str(ep), str(work), str(setup(work)), str(out))
        log(f"画面：{out}")
    elif step == "balance":
        import ep_voice as V
        print(json.dumps(V.balance(), ensure_ascii=False))
    elif step == "all":
        font = setup(work)
        pictures(ep, work, [])
        voice(work, [])
        audio(work)
        video(ep, work, font)
        thumbnail(ep, font)
        check(ep, work)
    elif step == "upload":
        upload(ep)
    elif step == "retitle":
        import youtube_upload as U
        new_thumb = ep / (args[0] if args else "thumbnail_v3.jpg")
        thumb_guard(ep, "差し替えるサムネ", files=[new_thumb])    # 2026-11-24 CEO厳守：差し替えるサムネも左右が同じか確かめる
        U.retitle_and_thumbnail(ep, new_thumb)
    elif step == "short":
        import ep_short as S
        S.use(args[0] if args else 1)          # short 2 で2本目（<回>/short2/）
        font = setup(work)
        res = S.voice(ep, work)
        log(f"ショートの声：{len(res)}セリフ、枠を超えたもの {[r['id'] for r in res if not r['fits']] or 'なし'}")
        S.audio(ep, work)
        log(f"ショートの動画：{S.video(ep, work, font)}")
        if (ep / "upload.json").exists():   # 説明欄には長尺のURLが要る。まだなら short-upload のときに書く
            S.description(ep)
        r = S.check(ep, work)
        log(f"ショートの数値チェック：{r['duration']}秒 {r['size']} {'問題なし' if not r['problems'] else r['problems']}")
        log(f"一覧画像：{S.contact_sheet(ep, work, font, work / S.SUB / 'sheet.png')}")
    elif step == "short-voice":
        import ep_short as S
        vd = work / "short"
        vs = json.loads((vd / "voice.json").read_text(encoding="utf-8"))
        for v in vs:
            if not args or v["id"] in args:
                (vd / f"voice_{v['id']}.wav").unlink(missing_ok=True)
        res = S.voice(ep, work)
        log(f"ショートの声：{len(res)}セリフ、枠を超えたもの {[r['id'] for r in res if not r['fits']] or 'なし'}")
        S.audio(ep, work)
        log(f"音を入れ替えた：{S.remux(ep, work)}")
        r = S.check(ep, work)
        log(f"ショートの数値チェック：{r['duration']}秒 {'問題なし' if not r['problems'] else r['problems']}")
        log(f"声：{r['voice']}")
    elif step == "short-upload":
        import ep_short as S
        S.use(args[0] if args else 1)
        if not (ep / S.SUB / "audit_passed").exists():
            raise SystemExit(f"ショートの監査の合格（<回>/{S.SUB}/audit_passed）がありません")
        # ショートのサムネは0:00の画面（暗い幕と大きな文字。knowledge/shorts.md）で、絵を左右に並べたものではない。
        # thumb_same_check は「左右の絵が同じか」を見る検査なので、ショート自身のサムネは確認の対象外。
        # そのかわり、ショートは長尺へ案内する（関連動画・説明欄）ので、元の長尺のサムネ（ab/thumb_*.jpg と thumbnail.jpg）が全部合格でなければ上げない。
        thumb_guard(ep, "ショートのアップロード前（元の長尺のサムネ）")
        import youtube_upload as U
        S.description(ep)
        U.upload(ep / S.SUB, short=True)
    else:
        raise SystemExit(__doc__)


if __name__ == "__main__":
    main()
