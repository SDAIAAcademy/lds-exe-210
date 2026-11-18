# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Score a participant's claims sheet of lab 1.1 against the key.

    uv run labs/solutions/score_claims.py <claims_sheet.csv>

A claim scores when its tag is right (صحيح، خاطئ، غير مسند) and, where the verdict rests on a
numbered clause, the clause column names that clause. Prints one line per claim and a total.
An empty sheet (the starting file) scores 0 and does not fail. Exit code 0 always: this is
feedback, not a gate.
"""
import csv
import json
import sys
from pathlib import Path

SOL = Path(__file__).resolve().parent
TAGS = {"صحيح", "خاطئ", "غير مسند"}


def norm_tag(t):
    t = (t or "").strip().replace("ـ", "")
    aliases = {"صحيحة": "صحيح", "خاطئة": "خاطئ", "غير مسندة": "غير مسند", "غيرمسند": "غير مسند"}
    return aliases.get(t, t)


def digits(s):
    table = str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")
    return (s or "").translate(table)


def score(path):
    key = json.loads((SOL / "key.json").read_text(encoding="utf-8"))["claims"]
    with open(path, encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    by_n = {}
    for r in rows:
        try:
            by_n[int(digits(r.get("n", "")).strip())] = r
        except ValueError:
            continue
    total = 0
    lines = []
    for i, (tag, clause) in enumerate(zip(key["tags"], key["clauses"]), 1):
        r = by_n.get(i, {})
        got = norm_tag(r.get("tag"))
        cited = digits(r.get("clause", ""))
        tag_ok = got == tag
        clause_ok = (not clause) or (clause in cited)
        mark = "OK " if tag_ok and clause_ok else "-- "
        if tag_ok and clause_ok:
            total += 1
        note = "" if got in TAGS or not got else f" (unknown tag: {got})"
        if tag_ok and not clause_ok:
            note += f" (tag right, clause {clause} missing)"
        lines.append(f"{mark}{i:>2}  {got or '(blank)'}{note}")
    print("\n".join(lines))
    print(f"score: {total} of {len(key['tags'])}")
    return total


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(0)
    score(sys.argv[1])
