# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Check the obligations table of an applicability note (lab 1.2) against the five points.

    uv run labs/solutions/check_note.py <note_obligations.csv> [--drafter "<name>"]

The five points are the course's own checklist (labs/files/checklist.md). The script checks what
a table can show; the trainer still reads the note for sense and for the one-page rule. It also
lists which of the four lines every note must catch are missing. The starting file (a header and
no lines) fails every point and does not crash. Exit code 0 when all five points pass, 1 otherwise.
"""
import csv
import datetime as dt
import json
import sys
from pathlib import Path

SOL = Path(__file__).resolve().parent


def parse_date(s):
    try:
        return dt.date.fromisoformat((s or "").strip())
    except ValueError:
        return None


def check(path, drafter=None):
    key = json.loads((SOL / "key.json").read_text(encoding="utf-8"))
    drafter = drafter or key["drafter"]
    read = dt.date.fromisoformat(key["read_date"])
    nxt = dt.date.fromisoformat(key["next_edition"])
    with open(path, encoding="utf-8-sig", newline="") as f:
        rows = [{k: (v or "").strip() for k, v in r.items() if k} for r in csv.DictReader(f)]
    rows = [r for r in rows if any(r.values())]
    problems = {p: [] for p in range(1, 6)}

    # 1 coverage: every system in every market
    if not rows:
        for p in problems:
            problems[p].append("no lines")
    for sid, markets in key["systems"].items():
        for m in [x.strip() for x in markets.replace("(عبر شريك النشر المحلي)", "").split("،")]:
            m = m.removeprefix("و").strip()
            if not any(r.get("system") == sid and m and m in r.get("market", "") for r in rows):
                problems[1].append(f"{sid} in {m}")

    for n, r in enumerate(rows, 2):
        where = f"line {n}"
        # 2 a row of the change table and a clause
        if r.get("row") not in key["rows"]:
            problems[2].append(f"{where}: row '{r.get('row')}' is not in the change table")
        if not r.get("clause"):
            problems[2].append(f"{where}: no clause")
        # 3 force of the row; nothing advisory or draft in now or next
        force = key["rows"].get(r.get("row"))
        if force and r.get("force") != force:
            problems[3].append(f"{where}: {r.get('row')} is {force}, the note says '{r.get('force')}'")
        if force in ("استرشادي", "مشروع") and r.get("horizon") in ("الآن", "التالي"):
            problems[3].append(f"{where}: an {force} row placed in {r.get('horizon')}")
        # 4 horizon and date
        h = r.get("horizon")
        if h not in key["horizons"]:
            problems[4].append(f"{where}: horizon '{h}'")
        if h in ("الآن", "التالي"):
            d = parse_date(r.get("date"))
            if not d:
                problems[4].append(f"{where}: {h} without a date (YYYY-MM-DD)")
            elif h == "الآن" and d > nxt:
                problems[4].append(f"{where}: {d} is after the next edition, so it is التالي")
            elif h == "التالي" and d <= nxt:
                problems[4].append(f"{where}: {d} falls before the next edition, so it is الآن")
        # 5 one owner, an approver who is neither the owner nor the drafter, a review date
        owner, approver = r.get("owner"), r.get("approver")
        if not owner or "،" in owner or "/" in owner:
            problems[5].append(f"{where}: one owner needed")
        if not approver:
            problems[5].append(f"{where}: no approver")
        elif approver == owner or approver == drafter:
            problems[5].append(f"{where}: {approver} approves their own line")
        rv = parse_date(r.get("review"))
        if not rv or rv < read or rv > nxt:
            problems[5].append(f"{where}: review date '{r.get('review')}' must fall between {read} and {nxt}")

    passed = 0
    names = {1: "coverage", 2: "source", 3: "force", 4: "horizon and date", 5: "owner and review"}
    for p in range(1, 6):
        ok = not problems[p]
        passed += ok
        print(f"{'PASS' if ok else 'FAIL'} {p} {names[p]}" + ("" if ok else f": {'; '.join(problems[p][:4])}"
                                                             + (" ..." if len(problems[p]) > 4 else "")))
    missing = [m for m in key["must_catch"]
               if not any(r.get("system") == m["system"] and m["market"] in r.get("market", "")
                          and r.get("row") == m["row"] and r.get("horizon") == m["horizon"]
                          and (not m.get("date") or r.get("date") == m["date"]) for r in rows)]
    print(f"lines that every note must catch: {len(key['must_catch']) - len(missing)} of {len(key['must_catch'])}")
    for m in missing:
        print(f"  missing: {m['system']} {m['market']} {m['row']} {m['horizon']} {m.get('date', '')}".rstrip())
    print(f"five-point checklist: {passed} of 5")
    return passed == 5 and not missing


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        sys.exit(0)
    drafter = None
    if "--drafter" in args:
        i = args.index("--drafter")
        drafter = args[i + 1]
        args = args[:i] + args[i + 2:]
    sys.exit(0 if check(args[0], drafter) else 1)
