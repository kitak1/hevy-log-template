#!/usr/bin/env python3
"""sets.csv から BIG3 の成長記録グラフ (viz/growth.html) を作る。

使い方:
  python3 viz/build_growth.py          # viz/growth.html を生成
  open viz/growth.html                 # ブラウザで開く (hevy-log/ の中で実行)

表すもの (画面上部のボタンで切り替え):
  - 最大重量: 各日の最重量セットと、それまでの自己ベスト (実際に挙げた重量だけ)
  - 推定1RM: Epley式 重量×(1+回数÷30) (1回は重量そのまま)。1RMの計算に使う回数の上限を
    5 / 8 / 12回以下から選べる (回数が多いほど高めに出るため)
  - どちらも 3種目の自己ベスト合計の推移と、年末目標 (hevy_import.BIG3) を重ねる
補助ありのセットは両方から除く。
HTML は自己完結 (データ埋め込み・外部ファイルなし) で、スマホ幅にも合わせて描き直す。
自己ベストの計算は画面側 (growth_template.html) で行うので、ここでは日ごとのセット一覧を渡すだけ。
"""
import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from hevy_import import BIG3  # noqa: E402  種目名と年末目標

SHORT = {n: n.split(" (")[0] for n in BIG3}  # 表示名: 「スクワット (バーベル)」→「スクワット」


def build():
    days = {name: {} for name in BIG3}  # 種目 -> 日付 -> [[重量, 回数], ...]
    with (ROOT / "sets.csv").open(encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f):
            name = r["exercise"]
            if name not in BIG3 or not r["weight_kg"] or "補助" in r["exercise_note"]:
                continue
            w, reps = float(r["weight_kg"]), int(r["reps"])
            if reps >= 1:
                days[name].setdefault(r["date"][:10], []).append([w, reps])
    lifts = [{"name": SHORT[n], "goal": g, "days": [{"d": d, "sets": s} for d, s in sorted(days[n].items())]}
             for n, g in BIG3.items()]
    return {"lifts": lifts, "totalGoal": sum(BIG3.values())}


HTML = (Path(__file__).parent / "growth_template.html").read_text(encoding="utf-8")


def main():
    data = build()
    if not all(l["days"] for l in data["lifts"]):
        sys.exit("BIG3の3種目すべてに記録が入ってから実行してください")
    out = Path(__file__).parent / "growth.html"
    out.write_text(HTML.replace("__DATA__", json.dumps(data, ensure_ascii=False)), encoding="utf-8")
    n = sum(len(l["days"]) for l in data["lifts"])
    print(f"{out} を作成 / {n}日分の記録")


if __name__ == "__main__":
    main()
