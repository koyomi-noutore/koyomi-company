"""過去回の一覧 knowledge/episode-index.md を outputs から機械的に作る（2026-11-25 CEO決定：題材・違い・うんちくの重なり確認）。
使い方：python3 scripts/episode_index.py      （作り直すたびに全部書き直す。AIは読み直さない）
間違い探し＝plan.json（題材・各問の場面と違いの label・うんちく）、文字の脳トレ・ちがうのどーれだ＝problem.json か description.md、
虫めがね＝mushimegane_defs.json と upload.json。"""
import json, re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "knowledge/episode-index.md"


def jl(p):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except Exception:
        return None


def vid(d):
    u = jl(d / "upload.json")
    return u.get("video_id", "") if u else ""


def title_of(d):
    u = jl(d / "upload.json")
    if u and u.get("title"):
        return u["title"]
    m = (d / "description.md")
    if m.exists():
        t = re.search(r"```\n(.+?)\n```", m.read_text(encoding="utf-8"))
        return t.group(1) if t else ""
    return ""


def cell(s):
    return str(s).replace("|", "／").replace("\n", " ").strip()


def unchiku(p):
    sc = p.get("screens", {})
    sl = sc.get("unchiku_slides") or []
    words = [t[0] for s in sl[1:] for t in s.get("texts", [])]
    if words:
        return "・".join(words)
    return p.get("unchiku_source", "")


def machigai():
    rows = []
    for d in sorted(ROOT.glob("outputs/20*_0[0-9][0-9]")):
        p = jl(d / "plan.json")
        if not p or not p.get("questions"):
            continue
        n = int(d.name.split("_")[-1])
        topic = p.get("screens", {}).get("opening_title", "") or (p.get("youtube") or {}).get("title", "")
        qs = []
        for q in p["questions"]:
            labs = "・".join(x.get("label", "") for x in q.get("diffs", []))
            qs.append(f"{q['q']}{q.get('scene', '')}（{labs}）")
        rows.append(f"| 第{n}回 | {cell(p.get('season', ''))} | {cell(topic)} | {cell(' ／ '.join(qs))} | {cell(unchiku(p))} | {vid(d)} | {d.name} |")
    return rows


def text_shorts():
    rows = []
    for d in sorted(ROOT.glob("outputs/*_text_*")):
        pr = jl(d / "problem.json") or {}
        kind = pr.get("kind", "")
        if pr.get("series") or kind in ("easy", "hard", "pic") or "main" in pr:
            what = f"ちがうのどーれだ：{pr.get('main', '')}の中に{pr.get('odd', '')}" if pr.get("main") else f"ちがうのどーれだ：{pr.get('id', '')}"
        elif pr:
            body = pr.get("items") or pr.get("rows") or pr.get("across") or ""
            if pr.get("across"):
                body = f"{pr.get('across')}／{pr.get('down')}→{pr.get('answer')}"
            what = f"{pr.get('title', kind)}：{json.dumps(body, ensure_ascii=False)[:120]}"
        else:
            what = "（problem.json なし）"
        rows.append(f"| {d.name.split('_', 1)[1]} | {cell(pr.get('level', ''))} | {cell(what)} | {cell(title_of(d))} | {vid(d)} |")
    return rows


def mushi():
    defs = jl(ROOT / "scripts/mushimegane_defs.json") or {}
    items = defs.get("items", defs) if isinstance(defs, dict) else defs
    rows = []
    for d in sorted(ROOT.glob("outputs/*_mushi_*")):
        rows.append(f"| {d.name.split('_', 1)[1]} | {cell(title_of(d))} | {vid(d)} |")
    return rows


def main():
    L = ["# 過去回の一覧（題材・違い・うんちく）", "",
         "scripts/episode_index.py が outputs から機械的に作る（手で直さない。作り直すときは実行し直す）。題材・違い・うんちくを決める前に、これで重なりを確かめる（episode-checklist.md「過去の回との重なり」）。", "",
         "## 間違い探し（長尺）", "", "| 回 | 季節 | 題材（オープニングの題名） | 各問の場面（違い） | うんちく | 長尺の動画ID | フォルダ |", "|---|---|---|---|---|---|---|"]
    L += machigai()
    L += ["", "## 文字の脳トレ・ちがうのどーれだ（ショート）", "", "| 回 | 難しさ | 問題 | タイトル | 動画ID |", "|---|---|---|---|---|"]
    L += text_shorts()
    L += ["", "## 虫めがねクイズ（ショート）", "", "| 回 | タイトル | 動画ID |", "|---|---|---|"]
    L += mushi()
    OUT.write_text("\n".join(L) + "\n", encoding="utf-8")
    print(OUT, len(L))


if __name__ == "__main__":
    main()
