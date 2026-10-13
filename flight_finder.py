"""
Daily flight finder: GRU -> TYS (Knoxville) and BNA (Nashville)
Dates: Jan 6 and Jan 7, 2027 (one-way)
Airlines: American, LATAM, Delta, United, GOL
Max 2 stops. Prints the cheapest options and logs history to prices.csv.

Setup:
  pip install requests
  export SERPAPI_KEY="your_key"        # https://serpapi.com (Google Flights data)
Optional email (all four needed):
  SMTP_HOST, SMTP_USER, SMTP_PASS, EMAIL_TO
"""
import csv
import os
import smtplib
import sys
from datetime import date, datetime
from email.message import EmailMessage

import requests

ORIGIN = "GRU"
DESTINATIONS = {"TYS": "Knoxville", "BNA": "Nashville"}
DATES = ["2027-01-06", "2027-01-07"]
AIRLINES = "AA,LA,DL,UA,G3"  # American, LATAM, Delta, United, GOL
MAX_STOPS_PARAM = 3          # SerpApi: 3 = 2 stops or fewer
CURRENCY = "USD"
HISTORY_FILE = "prices.csv"


def search(dest, day):
    params = {
        "engine": "google_flights",
        "departure_id": ORIGIN,
        "arrival_id": dest,
        "outbound_date": day,
        "type": 2,  # one-way
        "stops": MAX_STOPS_PARAM,
        "include_airlines": AIRLINES,
        "currency": CURRENCY,
        "hl": "en",
        "api_key": os.environ["SERPAPI_KEY"],
    }
    r = requests.get("https://serpapi.com/search.json", params=params, timeout=60)
    r.raise_for_status()
    data = r.json()
    offers = data.get("best_flights", []) + data.get("other_flights", [])
    results = []
    for o in offers:
        if "price" not in o:
            continue
        segs = o["flights"]
        results.append({
            "dest": dest,
            "city": DESTINATIONS[dest],
            "date": day,
            "price": o["price"],
            "stops": len(segs) - 1,
            "airlines": " + ".join(dict.fromkeys(s["airline"] for s in segs)),
            "flights": ", ".join(s.get("flight_number", "?") for s in segs),
            "duration_h": round(o.get("total_duration", 0) / 60, 1),
            "notes": "; ".join(
                e for s in segs for e in s.get("extensions", [])
                if "seat" in e.lower() or "basic" in e.lower()
            ),
        })
    return results


def main():
    all_results = []
    for dest in DESTINATIONS:
        for day in DATES:
            try:
                all_results += search(dest, day)
            except Exception as e:
                print(f"Error searching {dest} {day}: {e}", file=sys.stderr)

    if not all_results:
        print("No results found.")
        return

    all_results.sort(key=lambda x: x["price"])
    lines = [f"Flight check {date.today()}  ({ORIGIN} -> Knoxville/Nashville, max 2 stops)", ""]
    best = all_results[0]
    lines.append(
        f"CHEAPEST: ${best['price']} | {best['city']} ({best['dest']}) | {best['date']} | "
        f"{best['airlines']} | {best['stops']} stop(s) | {best['duration_h']}h"
    )
    lines.append("")
    lines.append("Cheapest per destination/date:")
    for dest in DESTINATIONS:
        for day in DATES:
            opts = [r for r in all_results if r["dest"] == dest and r["date"] == day]
            if opts:
                o = opts[0]
                lines.append(
                    f"  {o['city']} {day}: ${o['price']} - {o['airlines']}, "
                    f"{o['stops']} stop(s), {o['duration_h']}h {('[' + o['notes'] + ']') if o['notes'] else ''}"
                )
            else:
                lines.append(f"  {DESTINATIONS[dest]} {day}: no results")
    report = "\n".join(lines)
    print(report)

    new_file = not os.path.exists(HISTORY_FILE)
    with open(HISTORY_FILE, "a", newline="") as f:
        w = csv.writer(f)
        if new_file:
            w.writerow(["checked_at", "dest", "date", "price", "stops", "airlines", "flights", "duration_h", "notes"])
        for r in all_results:
            w.writerow([datetime.now().isoformat(timespec="minutes"), r["dest"], r["date"], r["price"],
                        r["stops"], r["airlines"], r["flights"], r["duration_h"], r["notes"]])

    if all(os.environ.get(k) for k in ("SMTP_HOST", "SMTP_USER", "SMTP_PASS", "EMAIL_TO")):
        msg = EmailMessage()
        msg["Subject"] = f"Cheapest GRU flight today: ${best['price']} to {best['city']}"
        msg["From"] = os.environ["SMTP_USER"]
        msg["To"] = os.environ["EMAIL_TO"]
        msg.set_content(report)
        with smtplib.SMTP_SSL(os.environ["SMTP_HOST"], 465) as s:
            s.login(os.environ["SMTP_USER"], os.environ["SMTP_PASS"])
            s.send_message(msg)


if __name__ == "__main__":
    main()
