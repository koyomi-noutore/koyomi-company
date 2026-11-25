"""書き出した声を文字起こしして、読み間違いがないかを確かめる（2026-11-22 CEO指示：「入る」が「いる」と読まれた再発防止）。
Gemini（文字で答えるモデル）に音声を渡し、聞こえたとおりにひらがなで書き起こしてもらう。キーは環境変数 GEMINI_API_KEY からだけ読む。

使い方：python3 scripts/transcribe_check.py <出力のmd> <声のwav> [<声のwav> ...]
  各wavの隣に <名前>.json（{"voice_text": 声に渡した文}）があれば、渡した文と聞こえた文を並べて書く。
  聞こえた文に「いる」があって「はいる」「あてはまる」がない所、渡した文と大きく違う所を「要確認」にする。
"""
import base64, json, os, re, sys, urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

MODEL = os.environ.get("KOYOMI_STT_MODEL", "gemini-3.5-flash")
PROMPT = ("この音声は日本語の短いセリフです。聞こえたとおりに、全部ひらがなで書き起こしてください。"
          "漢字・カタカナに直さず、補ったり直したりしないでください。読点は聞こえた区切りに入れてください。書き起こした文だけを答えてください。")


def transcribe(wav):
    data = base64.b64encode(Path(wav).read_bytes()).decode()
    body = {"contents": [{"parts": [{"text": PROMPT}, {"inline_data": {"mime_type": "audio/wav", "data": data}}]}],
            "generationConfig": {"temperature": 0}}
    from gemini_image import generate_content  # 2026-11-24：Vertex 経由（無料クレジット）に統一
    import time, urllib.error
    for i in range(8):     # Vertex は1分あたりの回数に上限があり 429 が返ることがある（2026-11-24）：待って取り直す
        try:
            res = generate_content(MODEL, body, timeout=45)
            break
        except (TimeoutError, ConnectionError) as e:    # 読み取りの時間切れ（2026-11-25）：取り直す
            if i == 7:
                raise
            time.sleep(10)
        except urllib.error.HTTPError as e:
            if e.code not in (429, 503) or i == 7:
                raise
            time.sleep(15 * (i + 1))
    return "".join(p.get("text", "") for p in res["candidates"][0]["content"]["parts"]).strip()


def norm(s):
    """カタカナはひらがなに、のばす棒（ー）は「う」にそろえてから比べる（文字起こしの書き方の違いを読み間違いと数えない）。"""
    s = "".join(chr(ord(c) - 0x60) if "ァ" <= c <= "ヶ" else c for c in s).replace("ー", "う")
    return re.sub(r"[\s、。！？!?「」・…]", "", s)


def main(out, wavs):
    rows, flags = [], 0
    for w in wavs:
        w = Path(w)
        meta = w.with_suffix(".json")
        vt = json.loads(meta.read_text(encoding="utf-8"))["voice_text"] if meta.exists() else ""
        heard = transcribe(w)
        note = []
        if "いる" in heard and not re.search(r"はいる|あてはまる", heard):
            note.append("「いる」と聞こえる")
        if vt and norm(heard) != norm(vt):
            note.append("渡した文と違う")
        flags += bool(note)
        rows.append(f"| {w.stem} | {vt} | {heard} | {'要確認：' + '・'.join(note) if note else 'OK'} |")
    txt = [f"# 文字起こしによる読みの確認（{MODEL}）", "",
           "書き出した声を Gemini に聞かせ、聞こえたとおりにひらがなで書き起こしたもの。「にはいる」が「には いる」と読まれた件（2026-11-22）の再発防止。", "",
           f"結果：{'要確認 ' + str(flags) + ' 件' if flags else 'すべて OK（「いる」と読まれた所なし）'}", "",
           "| 声のファイル | 声に渡した文 | 聞こえた文（文字起こし） | 判定 |", "|---|---|---|---|"] + rows
    Path(out).write_text("\n".join(txt) + "\n", encoding="utf-8")
    print(f"{out}：{'要確認 ' + str(flags) if flags else 'OK'}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2:])
