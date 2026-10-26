#!/usr/bin/env python3
"""ocr.swift の出力から筋トレメモの種目履歴を組み立て、TOTALで検算してCSVにする。

使い方:
  kintorememo/ocr raw/kintorememo/bench/*.(png|PNG) | python3 kintorememo/km_parse.py "ベンチプレス (バーベル)" km_bench.csv

処理の流れ (1画像ずつ):
  1. 「2026/10/14」のような日付見出しと、同じ高さにある「TOTAL:960.0Kg」を拾う
  2. 「65.0kg」(重量) を拾い、同じ高さにある「8回」(回数) と組にして1セットにする
  3. セットは、そのすぐ上にある日付見出しの日に属するとみなす
  4. セット行のすぐ下にある中央寄せのテキストをメモとする
  5. ocr.swift が CHECK を出した高さのセットには「補助あり」を付ける
スクショは重なりながら撮るので、同じ日が複数の画像に写る。
セット番号 (行の左端の数字) をキーに画像をまたいで統合する。
セット数が多く1画面に収まらない日も、前後の画像を合わせて1日分になる。
(見出しがスクロールで隠れても、画面上部に固定表示される日付見出しで日付を判定できる)

最後に各日について 重量×回数 の合計をアプリ表示の TOTAL と比べ、
一致しない日 (読み間違い・撮り漏れ) は CSV に入れずに NG として表示する。
CSV の列は sets.csv と同じ。session_id は km-<日付>、routine は 筋トレMEMO。
"""
import csv
import re
import sys

DATE = re.compile(r"(\d{4})/(\d{2})/(\d{2})")
TOTAL = re.compile(r"TOTAL\s*[:：]\s*([\d.]+)", re.I)
WEIGHT = re.compile(r"^([\d.]+)\s*kg", re.I)
NO_WEIGHT = re.compile(r"^(\d{1,2})\s+([\d.]+)\s*kg", re.I)  # セット番号と重量が1つにつながって読まれた行 (例「4 100.0kg」)
REPS = re.compile(r"^(\d+)\s*回?$|^(\d+)\s*回")  # 「回」が読み落とされることがある
FAILED = re.compile(r"^[ー\-－—]\s*回")          # 0回 (潰れたセット) は「ー 回」と表示される
REPS_X = (0.45, 0.6)  # 回数の列の横位置
RM_X = (0.58, 0.72)   # RM列の横位置


def reps_from_rm(w, rm):
    """アプリのRM列は 重量 × (1 + 回数/40) (1回のときは重量そのもの) なので回数を逆算できる。
    「回」が「|」「1」+「口」に分かれて誤認識され、8回→「8|」、9回→「91」となることがあるため、その照合に使う"""
    r = round((rm / w - 1) * 40)
    return r if r > 0 else 1
# メモではないテキスト (lbs換算・列見出し・セット番号・ゴミ箱アイコンの誤認識など)
NOISE = re.compile(r"(Lbs|LDS|kg|^\d+$|^[血面皿]$|セット|重さ|回数|^RM$|補助)", re.I)
ROW = 0.012    # 同じ行とみなす y の差 (画面高さ比)
FOOTER = 0.90  # これより下はタブバーなので無視

exercise, out_path = sys.argv[1], sys.argv[2]
images, cur = [], None
for line in sys.stdin:
    line = line.rstrip("\n")
    if line.startswith("### "):
        cur = []
        images.append(cur)
        continue
    y, x, t = line.split("\t", 2)
    if float(y) < FOOTER:
        cur.append((float(y), float(x), t.strip()))

sessions = {}  # date -> {"total", "sets": {セット番号: (重量, 回数, メモ)}}
for obs in images:
    heads = sorted((y, f"{m[1]}-{m[2]}-{m[3]}") for y, x, t in obs if (m := DATE.search(t)))
    totals = [(y, float(m[1])) for y, x, t in obs if (m := TOTAL.search(t))]
    checks = [y for y, x, t in obs if x == -1]

    def owner(y):
        above = [d for hy, d in heads if hy < y]
        return above[-1] if above else None

    for hy, d in heads:
        tot = next((v for ty, v in totals if abs(ty - hy) < ROW), None)
        s = sessions.setdefault(d, {"total": None, "sets": {}})
        s["total"] = s["total"] or tot
    weights = sorted([(y, float(m[1]), None) for y, x, t in obs if 0.12 < x < 0.3 and (m := WEIGHT.match(t))]
                     + [(y, float(m[2]), int(m[1])) for y, x, t in obs if x < 0.1 and (m := NO_WEIGHT.match(t))])
    rows = []
    for wy, w, no in weights:
        same = [(x, t) for y, x, t in obs if abs(y - wy) < ROW]
        r = next((int(m[1] or m[2]) for x, t in same if REPS_X[0] < x < REPS_X[1] and (m := REPS.match(t))), None)
        if r is None and any(REPS_X[0] < x < REPS_X[1] and FAILED.match(t) for x, t in same):
            r = 0
        rm = next((float(m[1]) for x, t in same if RM_X[0] < x < RM_X[1] and (m := WEIGHT.match(t))), None)
        if r != 0 and rm and w and reps_from_rm(w, rm) != r:
            r = reps_from_rm(w, rm)
        if no is None:
            no = next((int(t) for x, t in same if x < 0.1 and t.isdigit()), None)
        rows.append([wy, w, r, no, owner(wy)])
    # セット番号が読めなかった行は、同じ日の前後の行から補う
    for i, row in enumerate(rows):
        if row[3] is None:
            prev = rows[i - 1] if i > 0 else None
            nxt = rows[i + 1] if i + 1 < len(rows) else None
            if prev and prev[4] == row[4] and prev[3] is not None:
                row[3] = prev[3] + 1
            elif nxt and nxt[4] == row[4] and nxt[3] is not None:
                row[3] = nxt[3] - 1
    for wy, w, r, no, d in rows:
        if d is None or r is None or no is None:
            print(f"読めない行 {d} y={wy:.3f}: 重量{w} 回数{r} セット番号{no}", file=sys.stderr)
            continue
        notes = [t for y, x, t in obs if ROW < y - wy < 0.035 and x > 0.05 and not NOISE.search(t)
                 and not DATE.search(t) and not TOTAL.search(t)]
        note = "、".join(notes)
        if any(abs(cy - wy) < ROW for cy in checks):
            note = f"{note}、補助あり" if note else "補助あり"
        # 画面下端の行はメモが切れていることがあるので、長く読めた方を残す
        old = sessions[d]["sets"].get(no)
        if old is None or len(note) > len(old[2]):
            sessions[d]["sets"][no] = (w, r, note)

ng = 0
with open(out_path, "w", newline="", encoding="utf-8") as f:
    out = csv.writer(f)
    out.writerow(["session_id", "date", "routine", "exercise", "exercise_note", "set_no", "weight_kg", "reps"])
    for d in sorted(sessions, reverse=True):
        s = sessions[d]
        got = sum(w * r for w, r, _ in s["sets"].values())
        nos = sorted(s["sets"])
        if s["total"] is None or abs(got - s["total"]) > 0.01 or nos != list(range(1, len(nos) + 1)):
            ng += 1
            print(f"NG {d}: 読取合計 {got:g} / 表示TOTAL {s['total']}  sets={dict(sorted(s['sets'].items()))}")
            continue
        for no in nos:
            w, r, n = s["sets"][no]
            if r == 0:  # 潰れたセットは推定1RMを狂わせるので入れない (TOTALにも含まれない)
                continue
            out.writerow([f"km-{d}", d, "筋トレMEMO", exercise, n, no, f"{w:g}", r])
print(f"{len(sessions)}日中 {len(sessions) - ng}日 TOTAL一致 → {out_path}", file=sys.stderr)
