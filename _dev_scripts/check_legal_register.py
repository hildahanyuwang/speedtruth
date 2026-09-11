#!/usr/bin/env python
"""SpeedTruth, validate the legal source register against the files on disk.

WHY THIS EXISTS
---------------
The legal chapter was the one part of this project a reader could not check by
running anything. Every other published figure is recomputed by reproduce.py; the
statutes and gazette notices could only be read. This script closes that gap as far
as it can be closed: it cannot verify what a Thai regulation says, but it can verify
that the register is complete, internally consistent, and points at files that exist.

What it checks:
  1. every PDF in sources/legal/ has exactly one row in the register
  2. every row marked held=yes points at a file that exists
  3. every row marked held=no points at no file, and carries a note saying why
  4. every excerpt image referenced exists, and every excerpt image is referenced
  5. dates parse as ISO and are not in the future
  6. evidence_level is one of the declared values
  7. a held row has a source_url, so the copy can be checked against the original
  8. ids are unique

Run:  python _dev_scripts/check_legal_register.py
Exit: 0 if the register is consistent, 1 otherwise.
"""
import csv
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LEGAL = ROOT / "speedtruth-submission" / "sources" / "legal"
if not LEGAL.exists():                      # also runnable from inside the repo
    LEGAL = ROOT / "sources" / "legal"
REGISTER = LEGAL / "register.csv"

# What each level means, so that "verified" is never a matter of opinion:
EVIDENCE_LEVELS = {
    "original": "the gazette or official publication itself; operative text read here",
    "official_consolidated": "an official consolidated text issued by a state body",
    "official_secondary": "a government channel reproducing the instrument, not the gazette",
    "published_article": "a peer-reviewed article",
    "not_obtained": "cited, original not held",
}
DATE_FIELDS = ("signed", "published", "in_force", "last_verified")


def main():
    if not REGISTER.exists():
        sys.exit(f"missing {REGISTER}")

    rows = list(csv.DictReader(REGISTER.open(encoding="utf-8")))
    problems = []
    today = date.today()

    seen_ids = set()
    for r in rows:
        rid = r["id"]
        if rid in seen_ids:
            problems.append(f"{rid}: duplicate id")
        seen_ids.add(rid)

        if r["evidence_level"] not in EVIDENCE_LEVELS:
            problems.append(f"{rid}: evidence_level '{r['evidence_level']}' is not declared")

        for f in DATE_FIELDS:
            v = r[f].strip()
            if not v:
                continue
            try:
                d = date.fromisoformat(v)
            except ValueError:
                problems.append(f"{rid}: {f}='{v}' is not an ISO date")
                continue
            if d > today:
                problems.append(f"{rid}: {f}='{v}' is in the future")

        if not r["last_verified"].strip():
            problems.append(f"{rid}: no last_verified date")

        if r["held"] == "yes":
            if not r["file"].strip():
                problems.append(f"{rid}: held=yes but no file")
            elif not (LEGAL / r["file"]).exists():
                problems.append(f"{rid}: file not found: {r['file']}")
            if not r["source_url"].strip():
                problems.append(f"{rid}: held=yes but no source_url, so the copy "
                                f"cannot be checked against the original")
        elif r["held"] == "no":
            if r["file"].strip():
                problems.append(f"{rid}: held=no but names a file")
            if not r["notes"].strip():
                problems.append(f"{rid}: held=no but does not say why")
        else:
            problems.append(f"{rid}: held='{r['held']}' is neither yes nor no")

        if r["excerpt"].strip() and not (LEGAL / r["excerpt"]).exists():
            problems.append(f"{rid}: excerpt not found: {r['excerpt']}")

    # every PDF on disk must be registered, and vice versa
    on_disk = {p.relative_to(LEGAL).as_posix() for p in LEGAL.rglob("*.pdf")}
    in_register = {r["file"] for r in rows if r["file"].strip()}
    for missing in sorted(on_disk - in_register):
        problems.append(f"file on disk with no row in the register: {missing}")
    for phantom in sorted(in_register - on_disk):
        problems.append(f"row points at a file that is not on disk: {phantom}")

    excerpts_on_disk = {p.relative_to(LEGAL).as_posix() for p in LEGAL.rglob("*.png")}
    excerpts_used = {r["excerpt"] for r in rows if r["excerpt"].strip()}
    for unused in sorted(excerpts_on_disk - excerpts_used):
        problems.append(f"excerpt image referenced by no row: {unused}")

    held = sum(1 for r in rows if r["held"] == "yes")
    print(f"\nLegal source register: {len(rows)} entries, {held} held here, "
          f"{len(rows) - held} cited but not reproduced.")
    by_level = {}
    for r in rows:
        by_level[r["evidence_level"]] = by_level.get(r["evidence_level"], 0) + 1
    for lvl, n in sorted(by_level.items()):
        print(f"  {n:>2}  {lvl:<22} {EVIDENCE_LEVELS[lvl]}")

    gaps = [r for r in rows if r["evidence_level"] == "not_obtained"]
    if gaps:
        print("\nKnown gaps, stated rather than left implicit:")
        for r in gaps:
            print(f"  {r['id']}  {r['title_en'][:70]}")

    if problems:
        print(f"\n{len(problems)} problem(s):")
        for p in problems:
            print(f"  - {p}")
        return 1
    print("\nRegister is consistent with the files on disk.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
