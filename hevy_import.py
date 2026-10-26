#!/usr/bin/env python3
"""Hevyのエクスポートテキストを sets.csv (1セット1行) に取り込み、BIG3を集計する。

使い方:
  python hevy_import.py                 # クリップボードから取り込み
  python hevy_import.py --file x.txt    # ファイルから取り込み
  python hevy_import.py --inbox         # inbox/*.txt を取り込んで削除 (スマホ用)
  python hevy_import.py report          # 集計のみ (README.md のBIG3表を更新)
"""
import argparse
import csv
import hashlib
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

BIG3 = {
    "スクワット (バーベル)": 100,
    "ベンチプレス (バーベル)": 70,
    "デッドリフト (バーベル)": 120,
}
FIELDS = ["session_id", "date", "routine", "exercise", "exercise_note",
          "set_no", "weight_kg", "reps"]
README_START, README_END = "<!-- BIG3:START -->", "<!-- BIG3:END -->"
LB_TO_KG = 0.45359237
MAX_REPS_FOR_1RM = 12  # これ以上の高回数は推定1RMの精度が落ちるので除外

URL_RE = re.compile(r"^https?://(?:www\.)?hevy\.com/workout/([A-Za-z0-9_-]+)")
DATE_RE = re.compile(
    r"^\S+?,\s*(\d{1,2})月\s*(\d{1,2}),\s*(\d{4})\s+(\d{1,2}):(\d{2})\s*(午前|午後)?\s*$")
SET_RE = re.compile(
    r"^セット\s*(\d+):\s*(?:([\d.,]+)\s*(kg|lbs?)\s*[x×]\s*(\d+)|(\d+)\s*レップ数)\s*$")


def parse_date(m):
    mon, day, year, hour, minute, ampm = m.groups()
    hour = int(hour)
    if ampm == "午前" and hour == 12:
        hour = 0
    elif ampm == "午後" and hour != 12:
        hour += 12
    return datetime(int(year), int(mon), int(day), hour, int(minute))


def parse_session(buf, session_id, warn):
    """buf: 1セッション分の行。日付行が無ければ None。"""
    idx = next((i for i, l in enumerate(buf) if DATE_RE.match(l)), None)
    if idx is None:
        if any(buf):
            warn("日付行が見つからないブロックをスキップしました: " + " / ".join(x for x in buf if x)[:60])
        return None
    date = parse_date(DATE_RE.match(buf[idx]))
    routine = next((l for l in reversed(buf[:idx]) if l), "")
    if not session_id:
        session_id = "h-" + hashlib.sha1(f"{date:%Y-%m-%d %H:%M}|{routine}".encode()).hexdigest()[:10]

    exercises, cur = [], None
    for line in buf[idx + 1:]:
        if not line:
            cur = None
        elif m := SET_RE.match(line):
            if cur is None:
                warn(f"種目名のないセットを無視: {line}")
                continue
            no = int(m.group(1))
            if m.group(4):
                w = float(m.group(2).replace(",", ""))
                if m.group(3).startswith("lb"):
                    w = round(w * LB_TO_KG, 2)
                cur["sets"].append((no, w, int(m.group(4))))
            else:
                cur["sets"].append((no, None, int(m.group(5))))
        elif line.startswith("セット"):
            warn(f"解釈できないセット行 ({routine} {date:%F}): {line}")
        elif cur is None:
            cur = {"name": line, "note": "", "sets": []}
            exercises.append(cur)
        else:  # 種目名の直後の行 = メモ
            cur["note"] = (cur["note"] + " " + line.strip('"“”')).strip()
    return {"id": session_id, "date": date, "routine": routine, "exercises": exercises}


def parse_export(text, warn=print):
    """テキスト全体 -> [(session, raw_text), ...]。@hevyapp + URL 行がセッションの区切り。"""
    sessions, buf = [], []

    def flush(sid):
        nonlocal buf
        s = parse_session(buf, sid, warn)
        if s:
            body = "\n".join(buf[next(i for i, l in enumerate(buf) if DATE_RE.match(l)) - 1:]).strip()
            sessions.append((s, body + (f"\n\n@hevyapp\nhttps://hevy.com/workout/{sid}\n" if sid else "\n")))
        buf = []

    for line in text.splitlines():
        line = line.strip()
        if line == "@hevyapp":
            continue
        if m := URL_RE.match(line):
            flush(m.group(1))
        else:
            buf.append(line)
    flush(None)
    return sessions


def load_rows(csv_path):
    if not csv_path.exists():
        return []
    with csv_path.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def import_text(text, data_dir):
    csv_path, raw_dir = data_dir / "sets.csv", data_dir / "raw"
    known = {r["session_id"] for r in load_rows(csv_path)}
    new_rows, added, skipped = [], 0, 0
    for s, raw in parse_export(text, warn=lambda m: print("警告:", m, file=sys.stderr)):
        if s["id"] in known:
            skipped += 1
            continue
        known.add(s["id"])
        added += 1
        raw_dir.mkdir(exist_ok=True)
        (raw_dir / f"{s['date']:%Y-%m-%d}_{s['id']}.txt").write_text(raw, encoding="utf-8")
        for ex in s["exercises"]:
            for no, w, r in ex["sets"]:
                new_rows.append({
                    "session_id": s["id"], "date": f"{s['date']:%Y-%m-%d %H:%M}",
                    "routine": s["routine"], "exercise": ex["name"], "exercise_note": ex["note"],
                    "set_no": no, "weight_kg": "" if w is None else f"{w:g}", "reps": r})
    if new_rows:
        is_new = not csv_path.exists()
        with csv_path.open("a", encoding="utf-8", newline="") as f:
            wr = csv.DictWriter(f, FIELDS)
            if is_new:
                wr.writeheader()
            wr.writerows(new_rows)
    print(f"取り込み: {added}セッション ({len(new_rows)}セット) / 重複スキップ: {skipped}")
    return added


def epley(w, r):
    return w if r == 1 else w * (1 + r / 30)


def write_readme(path, block):
    """README.md の BIG3:START〜END の間だけを差し替える (無ければ先頭に追加)。"""
    marked = f"{README_START}\n{block}\n{README_END}"
    old = path.read_text(encoding="utf-8") if path.exists() else ""
    if README_START in old and README_END in old:
        head, rest = old.split(README_START, 1)
        new = head + marked + rest.split(README_END, 1)[1]
    else:
        new = marked + "\n\n" + old
    path.write_text(new, encoding="utf-8")


def report(data_dir, exclude_notes=()):
    rows = load_rows(data_dir / "sets.csv")
    out = ["### BIG3 進捗", "", f"| 種目 | 最大重量 | 日付 | 推定1RM(最高) | 目標 | 目標まで |", "|---|---|---|---|---|---|"]
    tot_max = tot_e1 = tot_goal = 0
    for name, goal in BIG3.items():
        best = best_e1 = None
        for r in rows:
            if r["exercise"] != name or not r["weight_kg"]:
                continue
            if any(k and k in r["exercise_note"] for k in exclude_notes):
                continue
            w, reps = float(r["weight_kg"]), int(r["reps"])
            if best is None or (w, r["date"]) >= (best[0], best[1]):
                best = (w, r["date"])
            if reps <= MAX_REPS_FOR_1RM:
                e = epley(w, reps)
                best_e1 = e if best_e1 is None else max(best_e1, e)
        mx = best[0] if best else 0
        e1 = best_e1 or 0
        tot_max, tot_e1, tot_goal = tot_max + mx, tot_e1 + e1, tot_goal + goal
        out.append(f"| {name} | {mx:g} kg | {best[1][:10] if best else '-'} | {e1:.1f} kg | {goal} kg | {goal - mx:+g} kg |")
    out.append(f"| **合計** | **{tot_max:g} kg** | | **{tot_e1:.1f} kg** | **{tot_goal} kg** | **{tot_goal - tot_max:+g} kg** |")
    out += ["", f"更新: {datetime.now():%Y-%m-%d %H:%M} / 推定1RMは Epley式 (回数{MAX_REPS_FOR_1RM}以下のセットのみ)"]
    if exclude_notes:
        out.append("メモに次を含む種目は除外: " + ", ".join(exclude_notes))
    text = "\n".join(out)
    write_readme(data_dir / "README.md", text)
    print(text)
    update_charts(data_dir)


def update_charts(data_dir):
    """README に貼る成長グラフ (viz/*.svg) を作り直す。失敗しても取り込み自体は成功扱い。"""
    viz = data_dir / "viz"
    if not (viz / "build_svg.py").exists():
        return
    try:
        sys.path.insert(0, str(viz))
        import build_svg
        build_svg.main()
    except Exception as e:  # グラフは付加機能なので取り込みを止めない
        print("警告: グラフの更新に失敗:", e, file=sys.stderr)


def read_clipboard():
    try:
        return subprocess.run(["pbpaste"], capture_output=True, text=True, check=True).stdout
    except (FileNotFoundError, subprocess.CalledProcessError):
        import tkinter
        root = tkinter.Tk()
        root.withdraw()
        return root.clipboard_get()


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("command", nargs="?", choices=["import", "report"], default="import")
    p.add_argument("--file", type=Path, help="クリップボードの代わりにこのファイルを読む")
    p.add_argument("--inbox", action="store_true", help="inbox/*.txt を取り込み、成功したら削除")
    p.add_argument("--data-dir", type=Path, default=Path(__file__).resolve().parent)
    p.add_argument("--exclude-notes", default="", help="メモにこの語を含む種目を集計から除外 (カンマ区切り 例: ポーズ,ラーセン)")
    a = p.parse_args()
    excl = [k.strip() for k in a.exclude_notes.split(",") if k.strip()]

    if a.command == "import":
        if a.inbox:
            files = sorted((a.data_dir / "inbox").glob("*.txt"))
            for f in files:
                import_text(f.read_text(encoding="utf-8"), a.data_dir)
                f.unlink()
            if not files:
                print("inbox は空です")
        else:
            text = a.file.read_text(encoding="utf-8") if a.file else read_clipboard()
            import_text(text, a.data_dir)
    report(a.data_dir, excl)


if __name__ == "__main__":
    main()
