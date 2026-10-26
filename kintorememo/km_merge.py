#!/usr/bin/env python3
"""km_parse.py が作ったCSVを sets.csv に追記する。

使い方:
  python3 kintorememo/km_merge.py km_bench.csv [km_squat.csv ...]

- Hevy に同じ日・同じ種目の記録がある日は取り込まない (乗り換え時期の二重記録を防ぐ)
- 取り込み済みの (session_id, 種目) は飛ばすので、何度実行しても重複しない
  (km の session_id は日付単位なので、同じ日のベンチとスクワットは同じIDになる)
"""
import csv
import sys
from pathlib import Path

FIELDS = ["session_id", "date", "routine", "exercise", "exercise_note", "set_no", "weight_kg", "reps"]
sets_csv = Path(__file__).resolve().parent.parent / "sets.csv"

with sets_csv.open(encoding="utf-8", newline="") as f:
    rows = list(csv.DictReader(f))
hevy_days = {(r["date"][:10], r["exercise"]) for r in rows if not r["session_id"].startswith("km-")}
known = {(r["session_id"], r["exercise"]) for r in rows}

new, skipped_hevy = [], set()
for path in sys.argv[1:]:
    with open(path, encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f):
            if (r["date"], r["exercise"]) in hevy_days:
                skipped_hevy.add((r["date"], r["exercise"]))
            elif (r["session_id"], r["exercise"]) not in known:
                new.append(r)
known_new = {(r["session_id"], r["exercise"]) for r in new}

with sets_csv.open("a", encoding="utf-8", newline="") as f:
    csv.DictWriter(f, FIELDS).writerows(new)
print(f"追記: {len(known_new)}日分 ({len(new)}セット)")
for d, ex in sorted(skipped_hevy):
    print(f"Hevyに記録があるのでスキップ: {d} {ex}")
