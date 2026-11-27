"""ナレーションの読みを制御する。

使い方:
  from yomi import to_tts, check
  to_tts(文)  … 読み辞書（knowledge/yomi.tsv）の語をカタカナに置き換えて、音声合成に渡す文を返す。
  check(文)   … 音声合成エンジンが実際にどう読むかを、カタカナで返す（読み確認表に使う）。
コマンド: python3 -I scripts/yomi.py 台本.txt  → 1行ごとに「元の文／置き換え後／エンジンの読み」を表示。
ルール：
  - 固有名詞・作品名・地名・人名・数字つきの言葉は、台本を書いた時点で読み辞書にあるか確認する。
  - 新しい誤読を見つけたら、yomi.tsv に1行足す（同じ誤読を二度起こさない）。
  - 字幕は元の漢字のまま。置き換えるのは音声に渡す文だけ。
"""
import os, re, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DICT = os.path.join(ROOT, "knowledge", "yomi.tsv")

def load():
    d = []
    for ln in open(DICT, encoding="utf-8"):
        if ln.startswith("#") or not ln.strip():
            continue
        p = ln.rstrip("\n").split("\t")
        if len(p) >= 2:
            d.append((p[0], p[1]))
    return sorted(d, key=lambda x: -len(x[0]))  # 長い語から置き換える

def to_tts(text):
    for k, v in load():
        text = text.replace(k, v)
    return text

def check(text):
    import pyopenjtalk
    return pyopenjtalk.g2p(to_tts(text).replace("\n", ""), kana=True)

if __name__ == "__main__":
    for ln in open(sys.argv[1], encoding="utf-8"):
        ln = ln.strip()
        if not ln:
            continue
        print("元　　:", ln); print("置換後:", to_tts(ln)); print("読み　:", check(ln)); print()
