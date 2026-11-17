"""セリフを Fish Audio で音声にする（make_episode.py から呼ぶ）。キーは環境変数 FISH_AUDIO_API_KEY からだけ読む（ログに出さない）。
モデル・話す速さは plan.json の voice（knowledge/concept.md の決定どおり）。利用条件は departments/production/voice.md。

使い方:
  python3 scripts/make_episode.py <回> voice [id ...]
    作業フォルダに voice_<id>.wav（48kHz・モノラルに変換したもの）と voice.json（長さ・枠・声に渡した文）を書く。
    id を指定すると、そのセリフだけ作り直す。作業フォルダにあるセリフは作り直さない（無駄打ちしない）。
    生成の回数と文字数は usage.jsonl に追記する。
  python3 scripts/make_episode.py <回> balance   残高とプランの枠を表示する
"""
import datetime, json, os, subprocess, sys, urllib.request, wave
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from ep_timeline import lines, VOICE_TEXT, sentences
GAP = 0.45     # 1つのセリフの中の文と文の間（秒）。最低品質2：0.4秒以上
from episode_plan import plan

API = "https://api.fish.audio"
_V = plan()["voice"]
MODEL_ID = _V["reference_id"]
SPEED = _V["speed"]
TTS_MODEL = _V.get("model", "s1")


def _key():
    k = os.environ.get("FISH_AUDIO_API_KEY")
    if not k:
        raise SystemExit("FISH_AUDIO_API_KEY が設定されていません")
    return k


def balance():
    out = {}
    for name, ep in (("api_credit_usd", "wallet/self/api-credit"), ("package", "wallet/self/package")):
        req = urllib.request.Request(f"{API}/{ep}", headers={"Authorization": f"Bearer {_key()}"})
        d = json.load(urllib.request.urlopen(req, timeout=60))
        out[name] = d.get("credit") if name == "api_credit_usd" else {"balance": d.get("balance"), "total": d.get("total"), "type": d.get("type")}
    return out


def tts(text, out_wav):
    body = {"text": text, "reference_id": MODEL_ID, "format": "wav", "prosody": {"speed": SPEED}}
    req = urllib.request.Request(f"{API}/v1/tts", data=json.dumps(body).encode(),
                                 headers={"Authorization": f"Bearer {_key()}", "model": TTS_MODEL, "Content-Type": "application/json"})
    raw = Path(str(out_wav) + ".raw.wav")
    raw.write_bytes(urllib.request.urlopen(req, timeout=300).read())
    # 48kHz・モノラルに変換し、前後の無音を少し整える
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(raw), "-ac", "1", "-ar", "48000",
                    "-af", "silenceremove=start_periods=1:start_threshold=-50dB,areverse,silenceremove=start_periods=1:start_threshold=-50dB,areverse,adelay=50,apad=pad_dur=0.15",
                    str(out_wav)], check=True)
    raw.unlink()
    with wave.open(str(out_wav)) as w:
        return w.getnframes() / w.getframerate()


def tts_line(text, out_wav):
    """2文のセリフは1文ずつ声にして、間に GAP 秒の無音をはさんでつなぐ（文の間を詰めない）。"""
    S = sentences(text)
    if len(S) <= 1:
        return tts(text, out_wav)
    parts = []
    for i, s in enumerate(S):
        p = Path(f"{out_wav}.part{i}.wav"); tts(s, p); parts.append(p)
    inputs, filt = [], ""
    for i, p in enumerate(parts):
        inputs += ["-i", str(p)]
    n = len(parts)
    chain = "".join(f"[{i}]apad=pad_dur={GAP}[p{i}];" for i in range(n - 1))
    filt = chain + "".join(f"[p{i}]" for i in range(n - 1)) + f"[{n - 1}]concat=n={n}:v=0:a=1"
    subprocess.run(["ffmpeg", "-v", "error", "-y", *inputs, "-filter_complex", filt, "-ac", "1", "-ar", "48000", str(out_wav)], check=True)
    for p in parts:
        p.unlink()
    with wave.open(str(out_wav)) as w:
        return w.getnframes() / w.getframerate()


def gap_problems(res, min_gap=0.4):
    """前のセリフの声の終わりから次のセリフまで min_gap 秒以上あいているか（最低品質2）。"""
    R = sorted(res, key=lambda r: r["start"])
    return [f"{a['id']}→{b['id']}：間 {b['start'] - a['start'] - a['dur']:.2f}秒" for a, b in zip(R, R[1:])
            if b["start"] - a["start"] - a["dur"] < min_gap]


def make_all(work, only=()):
    """作業フォルダにあるセリフ（声に渡す文が同じもの）は作り直さない。"""
    work = Path(work); work.mkdir(parents=True, exist_ok=True)
    only = set(only)
    vj = work / "voice.json"
    old = {v["id"]: v for v in json.loads(vj.read_text(encoding="utf-8"))} if vj.exists() else {}
    res = []
    for lid, t0, text, face, t_end in lines():
        vt = VOICE_TEXT.get(lid, text).replace("「", "").replace("」", "")
        wav = work / f"voice_{lid}.wav"
        regen = (lid in only) or not wav.exists() or old.get(lid, {}).get("voice_text") != vt
        if regen:
            dur = tts_line(vt, wav)
            with open(work / "usage.jsonl", "a", encoding="utf-8") as f:
                f.write(json.dumps({"time": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
                                    "id": lid, "chars": len(vt), "model": TTS_MODEL, "reference_id": MODEL_ID}, ensure_ascii=False) + "\n")
        else:
            dur = old[lid]["dur"]
        r = {"id": lid, "start": t0, "dur": round(dur, 2), "slot": round(t_end - t0, 2), "fits": t0 + dur <= t_end,
             "subtitle": text, "voice_text": vt}
        res.append(r)
        if regen or not r["fits"]:
            print(f"{lid:9s} {t0:7.1f}s  {dur:5.2f}s / slot {t_end - t0:5.2f}s  {'OK' if r['fits'] else 'OVER'}  {'NEW' if regen else '   '}  {vt}")
    vj.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    return res
