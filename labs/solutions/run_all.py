# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Run every solution of LDS-EXE-210 and print PASS or the first difference.

    uv run labs/solutions/run_all.py      (from the repository root)

1. The file pack is deterministic: the generator, run again, writes the same bytes.
2. Lab 1.1: the reference sheet scores 13 of 13 with 6 correct, 4 wrong and 3 unsupported; the
   empty starting sheet scores 0 without an error; a sheet that falls for the planted errors
   loses exactly those claims.
3. Lab 1.2: the reference note passes the five points and catches the four must-catch lines;
   the empty starting table fails without an error; a note that keeps the old EU date for the
   screening tool and lets the drafter approve fails points 4 and 5.
4. The horizons: every reference line in now or next is on the right side of the next edition.
Paths in the output are relative to the repository.
"""
import contextlib
import csv
import datetime as dt
import hashlib
import importlib.util
import io
import json
import subprocess
import sys
import tempfile
from pathlib import Path

SOL = Path(__file__).resolve().parent
LABS = SOL.parent
ROOT = LABS.parent


def load(name):
    spec = importlib.util.spec_from_file_location(name, SOL / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def digest():
    h = hashlib.sha256()
    paths = sorted(list((LABS / "files").rglob("*")) + [SOL / n for n in (
        "key.json", "claims_reference.csv", "change_table_reference.csv", "note_obligations_reference.csv",
        "note_reference.md")])
    for p in paths:
        if p.is_file():
            h.update(p.relative_to(LABS).as_posix().encode())
            h.update(p.read_bytes())
    return h.hexdigest()


def quiet(fn, *a):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        out = fn(*a)
    return out, buf.getvalue()


def rel(p):
    return Path(p).relative_to(ROOT).as_posix()


def main():
    before = digest()
    subprocess.run([sys.executable, str(LABS / "_tools" / "prepare_files.py")], check=True,
                   stdout=subprocess.DEVNULL)
    assert digest() == before, "the generator wrote different bytes: the pack is not deterministic"
    print("PASS file pack: deterministic")

    key = json.loads((SOL / "key.json").read_text(encoding="utf-8"))
    sc = load("score_claims")
    ref = SOL / "claims_reference.csv"
    total, _ = quiet(sc.score, ref)
    assert total == 13, total
    assert key["claims"]["counts"] == {"صحيح": 6, "خاطئ": 4, "غير مسند": 3}, key["claims"]["counts"]
    empty = LABS / "files" / "claims_sheet.csv"
    total0, _ = quiet(sc.score, empty)
    assert total0 == 0, total0
    with tempfile.TemporaryDirectory() as d:
        fooled = Path(d) / "fooled.csv"
        with open(ref, encoding="utf-8-sig", newline="") as f:
            rows = list(csv.DictReader(f))
        for r in rows:  # a reader who trusts the summary tags every claim correct
            r["tag"] = "صحيح"
        with open(fooled, "w", encoding="utf-8-sig", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            w.writeheader()
            w.writerows(rows)
        t, _ = quiet(sc.score, fooled)
        assert t == 6, t
    print(f"PASS lab 1.1: {rel(ref)} scores 13 of 13 (6 correct, 4 wrong, 3 unsupported); "
          f"{rel(empty)} scores 0; trusting the summary scores 6")

    cn = load("check_note")
    note = SOL / "note_obligations_reference.csv"
    ok, out = quiet(cn.check, note)
    assert ok, out
    start = LABS / "files" / "note_obligations.csv"
    ok0, out0 = quiet(cn.check, start)
    assert not ok0 and "0 of 5" in out0, out0
    with tempfile.TemporaryDirectory() as d:
        bad = Path(d) / "bad.csv"
        with open(note, encoding="utf-8-sig", newline="") as f:
            rows = list(csv.DictReader(f))
        for r in rows:
            if r["system"] == "S4" and r["row"] == "C07":
                r["horizon"], r["date"], r["approver"] = "الآن", "2026-08-02", key["drafter"]
        with open(bad, "w", encoding="utf-8-sig", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            w.writeheader()
            w.writerows(rows)
        okb, outb = quiet(cn.check, bad)
        assert not okb and "FAIL 5" in outb and "missing: S4" in outb, outb
    print(f"PASS lab 1.2: {rel(note)} passes 5 of 5 and catches 4 of 4; {rel(start)} fails without error; "
          "the old EU date with a self-approving drafter fails")

    nxt = dt.date.fromisoformat(key["next_edition"])
    with open(note, encoding="utf-8-sig", newline="") as f:
        lines = list(csv.DictReader(f))
    now = [r for r in lines if r["horizon"] == "الآن"]
    nexts = [r for r in lines if r["horizon"] == "التالي"]
    assert all(dt.date.fromisoformat(r["date"]) <= nxt for r in now)
    assert all(dt.date.fromisoformat(r["date"]) > nxt for r in nexts)
    print(f"PASS horizons: {len(now)} now, {len(nexts)} next, "
          f"{sum(r['horizon'] == 'قيد المتابعة' for r in lines)} watch, "
          f"{sum(r['horizon'] == 'لا ينطبق' for r in lines)} not applicable")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
