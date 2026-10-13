"""Builds docs/index.html from prices.csv (run after flight_finder.py)."""
import csv
import html
import os
from collections import defaultdict

CITIES = {"TYS": "Knoxville", "BNA": "Nashville"}
COLORS = {"TYS": "#2a7de1", "BNA": "#e8793a"}

rows = list(csv.DictReader(open("prices.csv", encoding="utf-8")))
for r in rows:
    r["price"] = float(r["price"])
    r["day"] = r["checked_at"][:10]

latest_day = max(r["day"] for r in rows)
latest = [r for r in rows if r["day"] == latest_day]

# cheapest per destination/date in the latest check
best = {}
for r in latest:
    k = (r["dest"], r["date"])
    if k not in best or r["price"] < best[k]["price"]:
        best[k] = r
overall = min(best.values(), key=lambda r: r["price"])

# price history: cheapest per day per destination
hist = defaultdict(dict)
for r in rows:
    d = hist[r["dest"]]
    d[r["day"]] = min(d.get(r["day"], 1e9), r["price"])
days = sorted({r["day"] for r in rows})


def chart():
    W, H, P = 640, 260, 40
    allp = [p for d in hist.values() for p in d.values()]
    lo, hi = min(allp) * 0.95, max(allp) * 1.05
    if hi == lo:
        hi = lo + 1

    def x(i):
        return P + (W - 2 * P) * (i / max(len(days) - 1, 1)) if len(days) > 1 else W / 2

    def y(p):
        return H - P - (H - 2 * P) * (p - lo) / (hi - lo)

    out = [f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="Price history">']
    for t in range(5):
        v = lo + (hi - lo) * t / 4
        out.append(f'<line x1="{P}" x2="{W-P}" y1="{y(v):.0f}" y2="{y(v):.0f}" class="grid"/>'
                   f'<text x="{P-6}" y="{y(v)+4:.0f}" text-anchor="end" class="ax">${v:,.0f}</text>')
    for dest, d in hist.items():
        pts = [(x(days.index(k)), y(v)) for k, v in sorted(d.items())]
        if len(pts) > 1:
            out.append('<polyline fill="none" stroke="%s" stroke-width="2.5" points="%s"/>'
                       % (COLORS[dest], " ".join(f"{a:.0f},{b:.0f}" for a, b in pts)))
        for a, b in pts:
            out.append(f'<circle cx="{a:.0f}" cy="{b:.0f}" r="4" fill="{COLORS[dest]}"/>')
    out.append(f'<text x="{P}" y="{H-12}" class="ax">{days[0]}</text>'
               f'<text x="{W-P}" y="{H-12}" text-anchor="end" class="ax">{days[-1]}</text></svg>')
    legend = "".join(f'<span><i style="background:{COLORS[k]}"></i>{v}</span>' for k, v in CITIES.items())
    return "".join(out) + f'<div class="legend">{legend}</div>'


def esc(s):
    return html.escape(str(s))


table = ""
for (dest, d), r in sorted(best.items(), key=lambda kv: kv[1]["price"]):
    stops = "Nonstop" if r["stops"] == "0" else f'{r["stops"]} stop' + ("s" if r["stops"] != "1" else "")
    table += (f'<tr><td>{CITIES[dest]}</td><td>{esc(d)}</td><td class="p">${r["price"]:,.0f}</td>'
              f'<td>{esc(r["airlines"])}</td><td>{stops}</td><td>{esc(r["duration_h"])}h</td></tr>')

page = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Flights São Paulo to Knoxville / Nashville</title>
<style>
:root{{--bg:#f6f7f9;--card:#fff;--tx:#1b1f24;--mu:#667;--ln:#e3e6ea;--ac:#0a7d4f}}
@media (prefers-color-scheme:dark){{:root{{--bg:#121417;--card:#1b1f24;--tx:#eceff3;--mu:#9aa3ad;--ln:#2c323a;--ac:#4cc38a}}}}
body{{margin:0;padding:20px;background:var(--bg);color:var(--tx);font:16px/1.5 system-ui,sans-serif}}
.w{{max-width:760px;margin:0 auto}}
h1{{font-size:1.4rem;margin:0 0 4px}} .sub{{color:var(--mu);margin:0 0 18px}}
.card{{background:var(--card);border:1px solid var(--ln);border-radius:14px;padding:18px;margin-bottom:16px}}
.big{{font-size:2.6rem;font-weight:700;color:var(--ac);line-height:1.1}}
.box{{overflow-x:auto}} table{{width:100%;border-collapse:collapse;font-size:.95rem}}
th,td{{text-align:left;padding:8px 6px;border-bottom:1px solid var(--ln);white-space:nowrap}}
th{{color:var(--mu);font-weight:500}} .p{{font-weight:600}}
svg{{width:100%;height:auto}} .grid{{stroke:var(--ln)}} .ax{{fill:var(--mu);font-size:11px}}
.legend{{display:flex;gap:16px;color:var(--mu);font-size:.9rem}}
.legend i{{display:inline-block;width:10px;height:10px;border-radius:50%;margin-right:6px}}
.note{{color:var(--mu);font-size:.85rem}}
</style></head><body><div class="w">
<h1>São Paulo (GRU) to Knoxville / Nashville</h1>
<p class="sub">One-way, Jan 6 or 7, 2027. American, LATAM, Delta, United, GOL. Up to 2 stops. Updated {esc(latest_day)}.</p>
<div class="card"><div class="note">Cheapest right now</div>
<div class="big">${overall["price"]:,.0f}</div>
<div>{CITIES[overall["dest"]]} on {esc(overall["date"])} with {esc(overall["airlines"])}, {esc(overall["duration_h"])}h</div></div>
<div class="card"><b>Cheapest by city and date</b><div class="box"><table>
<tr><th>To</th><th>Date</th><th>Price</th><th>Airline</th><th>Stops</th><th>Time</th></tr>{table}</table></div></div>
<div class="card"><b>Price history (daily cheapest)</b>{chart()}</div>
<p class="note">Prices come from Google Flights and may differ slightly on the airline's site. Seat selection isn't shown here, so check the airline before buying (basic economy fares often charge for seats).</p>
</div></body></html>"""

os.makedirs("docs", exist_ok=True)
open("docs/index.html", "w", encoding="utf-8").write(page)
print("Wrote docs/index.html")
