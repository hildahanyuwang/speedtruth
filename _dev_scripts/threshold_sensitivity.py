#!/usr/bin/env python
"""SpeedTruth, how much of the answer is the threshold?

WHY THIS EXISTS
---------------
The published headline is that 92% of the Thai network is posted above the speed its
road environment can survive. A reviewer's first move should be to ask how much of that
is a fact about Thailand and how much is an arithmetic consequence of the survivable
speed this project chose. The weighting sensitivity already answers "what if the three
factors are weighted wrong". It does not answer "what if the ruler itself is wrong",
which is the more basic question.

This script answers it the same way: recompute the published quantity under a family of
alternative rulers and report the range rather than a point.

Three families, because they test different objections:
  FLOOR   raise only the 30 km/h pedestrian floor to 40 or 50. Tests the specific
          claim that the lowest threshold is doing the work.
  SHIFT   add a constant to every threshold. Tests "your whole ruler is too strict".
  MARGIN  keep the ruler and require the gap to exceed 10, 20 or 30 km/h before it
          counts. Tests "a gap of 1 km/h is not a finding".

It reads only the committed per-segment outputs and does no re-scoring: the gap is
posted limit minus survivable speed, so every variant is arithmetic on published
fields. Keyless, no confidential inputs beyond the two outputs it reads.

Run:  python _dev_scripts/threshold_sensitivity.py
Out:  output/threshold_sensitivity.json
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "output" / "speed_safety_score.geojson"
CV = ROOT / "output" / "speed_safety_score_cv.geojson"
OUT = ROOT / "output" / "threshold_sensitivity.json"


def summarise(df, name):
    """The published pair of headline quantities, per region."""
    out = {"variant": name, "by_region": {}}
    for reg in ("THA", "MAH"):
        d = df[df.region == reg]
        above = d.gap > 0
        out["by_region"][reg] = {
            "n": int(len(d)),
            "n_above": int(above.sum()),
            "pct_above": round(100 * float(above.mean()), 1),
            "median_gap": float(d.gap.median()),
        }
    t, m = out["by_region"]["THA"], out["by_region"]["MAH"]
    # The finding the application actually rests on is not the 92%. It is that the two
    # countries point in opposite directions. Report the two halves of that separately,
    # because a single boolean hides which half failed: at the harshest variant the
    # ratio between the countries is at its widest while the Thai median sits exactly on
    # zero, and collapsing both into one flag would report that as a reversal.
    out["ratio_above"] = (round(t["pct_above"] / m["pct_above"], 1)
                          if m["pct_above"] else None)
    out["thailand_median_positive"] = bool(t["median_gap"] > 0)
    out["maharashtra_median_negative"] = bool(m["median_gap"] < 0)
    out["direction_still_opposite"] = bool(t["median_gap"] >= 0 > m["median_gap"])
    return out


def main():
    import geopandas as gpd
    import numpy as np

    missing = [p for p in (BASE, CV) if not p.exists()]
    if missing:
        sys.exit("needs the per-segment outputs, which are FDUA-restricted and live "
                 "outside the public repository: " + ", ".join(p.name for p in missing))

    g = gpd.read_file(BASE)[["seg_id", "region", "speed_limit"]]
    c = gpd.read_file(CV)[["seg_id", "safe_threshold_v3"]]
    d = g.merge(c, on="seg_id", validate="one_to_one")
    base_thr = d.safe_threshold_v3.copy()

    results = []

    def run(name, thr):
        d["gap"] = d.speed_limit - thr
        results.append(summarise(d, name))

    run("published", base_thr)

    # FLOOR: the objection is that the 30 km/h pedestrian floor decides the answer.
    for floor in (40, 50, 60):
        run(f"floor_raised_to_{floor}", np.maximum(base_thr, floor))

    # SHIFT: the objection is that the whole ruler is too strict.
    for delta in (5, 10, 20, 30):
        run(f"all_thresholds_plus_{delta}", base_thr + delta)

    # MARGIN: the objection is that a 1 km/h gap is not a finding. Arithmetically this
    # is the same test as SHIFT by the same amount, since both subtract a constant from
    # the gap. It is run and reported anyway because the two objections are different
    # objections, and a reader who raises one should be able to see it answered in the
    # words they used. The identical rows are the point, not an error.
    for margin in (10, 20, 30):
        d["gap"] = d.speed_limit - base_thr - margin
        r = summarise(d, f"gap_must_exceed_{margin}")
        r["identical_to"] = f"all_thresholds_plus_{margin}"
        results.append(r)

    thr_mix = {}
    # computed before printing so the summary can show it
    for reg in ("THA", "MAH"):
        s = base_thr[d.region == reg].round(0).value_counts()
        thr_mix[reg] = {str(int(k)): int(v) for k, v in s.items()}

    payload = {
        "generated_by": "_dev_scripts/threshold_sensitivity.py",
        "question": "How much of the published headline is a property of the network, "
                    "and how much is a property of the chosen survivable speed?",
        "threshold_mix_published": thr_mix,
        "variants": results,
    }
    OUT.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    w = max(len(r["variant"]) for r in results)
    print(f"\n{'variant':{w}}  {'THA above':>10} {'THA med':>8}  {'MAH above':>10} "
          f"{'MAH med':>8}  {'ratio':>6}  direction")
    print("-" * (w + 62))
    for r in results:
        t, m = r["by_region"]["THA"], r["by_region"]["MAH"]
        print(f"{r['variant']:{w}}  {t['pct_above']:>9.1f}% {t['median_gap']:>8.0f}  "
              f"{m['pct_above']:>9.1f}% {m['median_gap']:>8.0f}  "
              f"{(r['ratio_above'] or 0):>5.1f}x  "
              f"{'opposite' if r['direction_still_opposite'] else 'not opposite'}")
    print("\nThe published threshold mix, for the reader who suspects one value is "
          "carrying the result:")
    for reg, mix in thr_mix.items():
        tot = sum(mix.values())
        parts = sorted(mix.items(), key=lambda kv: -kv[1])
        print(f"  {reg}: " + "  ".join(f"{k} km/h {100*v/tot:.1f}%" for k, v in parts))
    print(f"\nwrote {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
