#!/usr/bin/env python3
"""BIG3 の成長記録を README 用の静的SVGにする (標準ライブラリのみ)。

使い方:
  python3 viz/build_svg.py     # viz/big3_weight.svg と viz/big3_1rm.svg を生成

  big3_weight.svg ... 最大重量 (各日の最重量セットと、それまでの自己ベスト)
  big3_1rm.svg    ... 推定1RM (Epley式、12回以下のセット。READMEのBIG3表と同じ条件)
どちらも 自己ベスト合計 + 種目ごと の4段で、年末目標を点線で重ねる。
ライト/ダークは prefers-color-scheme で切り替わる (GitHubのREADMEでも有効)。
インタラクティブ版 (ホバーで内訳、回数の上限の切り替え) は viz/build_growth.py の growth.html。
補助ありのセットは除く。hevy_import.py の取り込み後に自動で呼ばれる。
"""
import sys
from datetime import date, timedelta
from math import ceil, floor, log10
from pathlib import Path
from xml.sax.saxutils import escape

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_growth import build  # noqa: E402

MAX_REPS_FOR_1RM = 12  # hevy_import.py と同じ
W = 600
M = {"l": 40, "r": 12, "t": 22, "b": 24}
SERIES = ["s1", "s2", "s3"]  # スクワット / ベンチ / デッド (固定順)
EPOCH = date(1970, 1, 1)

STYLE = """
:root { --ink:#0b0b0b; --ink2:#52514e; --muted:#898781; --grid:#e1e0d9; --axis:#c3c2b7; --ring:#ffffff;
        --s1:#2a78d6; --s2:#eb6834; --s3:#1baf7a; }
@media (prefers-color-scheme: dark) {
  :root { --ink:#f0efec; --ink2:#c3c2b7; --muted:#898781; --grid:#2c2c2a; --axis:#383835; --ring:#0d1117;
          --s1:#3987e5; --s2:#d95926; --s3:#199e70; }
}
text { font-family: system-ui, -apple-system, "Segoe UI", "Hiragino Sans", sans-serif; fill: var(--muted); font-size: 12px; }
.t { fill: var(--ink); font-size: 14px; font-weight: 600; }
.v { fill: var(--ink); font-size: 14px; font-weight: 600; }
.l { fill: var(--ink2); font-size: 12px; }
.grid { stroke: var(--grid); stroke-width: 1; }
.axis { stroke: var(--axis); stroke-width: 1; }
.goal { stroke: var(--muted); stroke-width: 1.5; stroke-dasharray: 4 3; }
"""


def days_of(d):
    return (date.fromisoformat(d) - EPOCH).days


def e1rm(w, r):
    return w if r == 1 else w * (1 + r / 30)


def series(lift, mode):
    """各日の代表セットと、そこまでの自己ベスト (growth_template.html の series() と同じ)。"""
    best, out = 0.0, []
    for day in lift["days"]:
        top = None
        for w, r in day["sets"]:
            if mode == "rm" and r > MAX_REPS_FOR_1RM:
                continue
            v = e1rm(w, r) if mode == "rm" else w
            if top is None or v > top[0] or (v == top[0] and r > top[2]):
                top = (v, w, r)
        if top is None:
            continue
        new = top[0] > best + 1e-9
        out.append({"d": day["d"], "v": top[0], "new": new, "pb": top[0] if new else best})
        if new:
            best = top[0]
    return out


def total_series(S):
    dates = sorted({p["d"] for s in S for p in s})
    cur, idx, out = [0.0] * len(S), [0] * len(S), []
    for d in dates:
        for i, s in enumerate(S):
            while idx[i] < len(s) and s[idx[i]]["d"] <= d:
                cur[i] = s[idx[i]]["pb"]
                idx[i] += 1
        if all(cur):
            v = sum(cur)
            if not out or abs(out[-1]["v"] - v) > 1e-9:
                out.append({"d": d, "v": v})
    return out


def nice_step(mx):
    raw = mx / 4
    p = 10 ** floor(log10(raw))
    m = raw / p
    return (1 if m <= 1 else 2 if m <= 2 else 5 if m <= 5 else 10) * p


def panel(y0, height, t0, t1, *, title, color, goal, ymax, step, dots, fmt):
    """y0 から height の高さのパネル1つ分のSVG断片。"""
    px = lambda d: M["l"] + (days_of(d) - t0) / (t1 - t0) * (W - M["l"] - M["r"])
    stp = nice_step(ymax)
    top = ceil(ymax / stp) * stp
    py = lambda v: height - M["b"] - v / top * (height - M["t"] - M["b"])
    o = [f'<g transform="translate(0 {y0})">']
    o.append(f'<rect x="{M["l"]}" y="1" width="10" height="3" rx="1.5" style="fill:{color}"/>'
             f'<text class="t" x="{M["l"] + 16}" y="8">{escape(title)}</text>')
    v = 0
    while v <= top:
        o.append(f'<line class="{"axis" if v == 0 else "grid"}" x1="{M["l"]}" x2="{W - M["r"]}" y1="{py(v):.1f}" y2="{py(v):.1f}"/>'
                 f'<text x="{M["l"] - 6}" y="{py(v) + 4:.1f}" text-anchor="end">{v:g}</text>')
        v += stp
    # 目盛り: 期間が約9か月以内なら1か月ごと、それより長ければ3か月ごと
    sm = 1 if t1 - t0 <= 270 else 3
    d0 = EPOCH + timedelta(days=t0)
    m = d0.year * 12 + (d0.month - 1) // sm * sm
    while True:
        tick = date(m // 12, m % 12 + 1, 1)
        td = (tick - EPOCH).days
        if td > t1:
            break
        if td >= t0:
            x = M["l"] + (td - t0) / (t1 - t0) * (W - M["l"] - M["r"])
            o.append(f'<line class="axis" x1="{x:.1f}" x2="{x:.1f}" y1="{height - M["b"]}" y2="{height - M["b"] + 4}"/>'
                     f'<text x="{x:.1f}" y="{height - 6}" text-anchor="middle">{tick.year % 100}/{tick.month}</text>')
        m += sm
    o.append(f'<line class="goal" x1="{M["l"]}" x2="{W - M["r"]}" y1="{py(goal):.1f}" y2="{py(goal):.1f}"/>'
             f'<text x="{M["l"] + 4}" y="{py(goal) - 5:.1f}">年末目標 {goal:g}kg</text>')
    path, prev = "", None
    for p in step:
        path += f'M{px(p["d"]):.1f} {py(p["v"]):.1f}' if prev is None else f'H{px(p["d"]):.1f}V{py(p["v"]):.1f}'
        prev = p["v"]
    path += f'H{px(EPOCH_STR(t1)):.1f}'
    o.append(f'<path d="{path}" fill="none" style="stroke:{color}" stroke-width="2" stroke-linejoin="round"/>')
    for p in dots:
        o.append(f'<circle cx="{px(p["d"]):.1f}" cy="{py(p["v"]):.1f}" r="3" style="fill:{color};stroke:var(--ring)" fill-opacity=".6" stroke-width="1"/>')
    last = step[-1]["v"]
    xe = W - M["r"]
    o.append(f'<text class="v" x="{xe - 4}" y="{py(last) - 8:.1f}" text-anchor="end">{fmt(last)}kg</text>'
             f'<circle cx="{xe}" cy="{py(last):.1f}" r="4" style="fill:{color};stroke:var(--ring)" stroke-width="2"/>')
    o.append("</g>")
    return "".join(o)


def EPOCH_STR(days):
    return (EPOCH + timedelta(days=days)).isoformat()


def render(data, mode):
    rm = mode == "rm"
    fmt = (lambda v: f"{v:.1f}") if rm else (lambda v: f"{v:g}")
    S = [series(l, mode) for l in data["lifts"]]
    total = total_series(S)
    alld = [days_of(day["d"]) for l in data["lifts"] for day in l["days"]]
    t0, t1 = min(alld), max(alld)

    parts, y = [], 0
    # 凡例 (点・線・点線)
    dot_label = "各日の最高推定1RM" if rm else "各日の最重量セット"
    parts.append(
        f'<g transform="translate(0 14)">'
        f'<circle cx="{M["l"] + 4}" cy="-4" r="3.5" style="fill:var(--ink2)" fill-opacity=".55"/><text class="l" x="{M["l"] + 14}" y="0">{dot_label}</text>'
        f'<line x1="{M["l"] + 150}" x2="{M["l"] + 172}" y1="-4" y2="-4" style="stroke:var(--ink2)" stroke-width="2"/><text class="l" x="{M["l"] + 178}" y="0">自己ベスト</text>'
        f'<line class="goal" x1="{M["l"] + 250}" x2="{M["l"] + 272}" y1="-4" y2="-4"/><text class="l" x="{M["l"] + 278}" y="0">年末目標</text></g>')
    y += 30
    tt = "推定1RM(自己ベスト)の合計" if rm else "自己ベストの合計"
    parts.append(panel(y, 200, t0, t1, title=tt, color="var(--ink2)", goal=data["totalGoal"],
                       ymax=max(data["totalGoal"], total[-1]["v"]), step=total, dots=[], fmt=fmt))
    y += 212
    for l, s, c in zip(data["lifts"], S, SERIES):
        parts.append(panel(y, 160, t0, t1, title=l["name"], color=f"var(--{c})", goal=l["goal"],
                           ymax=max(l["goal"], *(p["v"] for p in s)),
                           step=[p | {"v": p["pb"]} for k, p in enumerate(s) if k == 0 or p["new"]], dots=s, fmt=fmt))
        y += 168
    desc = ("BIG3の推定1RMの推移" if rm else "BIG3の最大重量の推移")
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {y}" width="{W}" height="{y}" role="img" aria-label="{desc}">'
            f'<title>{desc}</title><style>{STYLE}</style>{"".join(parts)}</svg>\n')


def main():
    data = build()
    if not all(l["days"] for l in data["lifts"]):
        print("グラフ: BIG3の3種目すべてに記録が入ったら作成します")
        return
    out = Path(__file__).parent
    for name, mode in (("big3_weight.svg", "weight"), ("big3_1rm.svg", "rm")):
        (out / name).write_text(render(data, mode), encoding="utf-8")
    print("SVGを更新:", "viz/big3_weight.svg, viz/big3_1rm.svg")


if __name__ == "__main__":
    main()
