"""
SpeedTruth, stage 1 of the automated road-condition layer: pull Mapillary imagery
and write a manifest for the vision model to classify.

Single parameterised entry point. It replaces three near-duplicate scripts
(`imagery_cv_pull.py`, `imagery_cv_pull_full.py`, `imagery_cv_pull_lower.py`) that
differed only in which segments they sampled; the fetch loop, the manifest record and
the rate limiting were copy-pasted between them. The ADB technical review asked for
exactly this: "You could use a single parameterised entry point which would make the
reproduction path unambiguous."

    MLY_TOKEN=... python src/imagery_pull.py --scope stratified
    MLY_TOKEN=... python src/imagery_pull.py --scope priority
    MLY_TOKEN=... python src/imagery_pull.py --scope lower

THE THREE SCOPES, AND WHY EACH EXISTS

  stratified  The validation sample. Three named strata with quotas: segments the
              school/market proxy pushed to a 30 km/h threshold, segments flagged as
              possibly grade-separated, and low-ranked controls. This is the sample the
              blind road-condition audit was drawn against, so it stays fixed.
              -> output/cv_images/, output/cv_manifest.json

  priority    The decision-relevant set: every Priority 1 and Priority 2 segment, plus a
              random sample of lower tiers so the layer can also catch roads the proxy
              UNDER-flagged. Keyed by seg_id so the classified condition joins straight
              back to the score.
              -> output/cv_images_full/, output/cv_manifest_full.json

  lower       Extends the same manifest with the busiest lower-tier segments. Tests the
              other direction: a segment with no school/market POI gets a high threshold
              and ranks low, but if the imagery shows a genuine pedestrian-mixing street,
              the proxy missed it. Finding those is discovery, not re-ranking.
              -> appends to output/cv_manifest_full.json

`priority` and `lower` are resumable: they skip seg_ids already in the manifest, so an
interrupted pull can be restarted without re-fetching. `stratified` writes a fresh
manifest, because its quotas define a fixed validation sample.

One image per segment. That is the binding limitation of this whole layer and it is
stated wherever its results are: it supports the direction of a correction, not its
precision. Images (c) Mapillary contributors, CC BY-SA.

Next stage: imagery_cv_classify.py (needs ANTHROPIC_API_KEY).
"""
from __future__ import annotations

import argparse
import json
import os
import time
import urllib.parse
import urllib.request
import warnings
from collections import Counter

import geopandas as gpd
import pandas as pd

warnings.filterwarnings("ignore")

SCORES = "output/speed_safety_score.geojson"
LOWER_TIERS = ["Watch", "Lower priority"]
PRIORITY_TIERS = ["Priority 1", "Priority 2"]

# Phase 1 outputs on disk still carry the pre-rename tier vocabulary; normalise on load
# so this runs against either vintage. See CHANGELOG_PHASE2.md.
TIER_RENAME = {"Monitor": "Watch", "Compliant": "Lower priority"}

SCOPES = {
    "stratified": dict(
        out="output/cv_images", manifest="output/cv_manifest.json",
        prefix="cv_", width=3, resume=False, with_seg_id=False,
        sleep_fetch=0.2, sleep_loop=0.15,
    ),
    "priority": dict(
        out="output/cv_images_full", manifest="output/cv_manifest_full.json",
        prefix="cvf_", width=5, resume=True, with_seg_id=True,
        sleep_fetch=0.13, sleep_loop=0.1,
    ),
    "lower": dict(
        out="output/cv_images_full", manifest="output/cv_manifest_full.json",
        prefix="cvf_", width=5, resume=True, with_seg_id=True,
        sleep_fetch=0.13, sleep_loop=0.1,
    ),
}

QUOTA = {"P1_safe30": 120, "gradesep": 25, "control": 25}   # stratified scope only
N_LOWER_SAMPLE = 1500      # priority scope: random lower-tier segments added to P1+P2
N_LOWER_CAND = 4000        # lower scope: busiest lower-tier candidates considered


def get_img(token, lon, lat, d=0.0015, timeout=25):
    """One Mapillary image near the point, or None. Never raises: a missing image is a
    normal outcome (coverage is patchy), not an error worth stopping a long pull for."""
    bbox = f"{lon-d},{lat-d},{lon+d},{lat+d}"
    url = ("https://graph.mapillary.com/images?"
           + urllib.parse.urlencode({"access_token": token,
                                     "fields": "id,thumb_1024_url",
                                     "bbox": bbox, "limit": 1}))
    try:
        data = json.load(urllib.request.urlopen(url, timeout=timeout)).get("data", [])
        return data[0] if data else None
    except Exception:
        return None


def midpoints(df):
    mid = df.geometry.interpolate(0.5, normalized=True)
    df = df.copy()
    df["lon"], df["lat"] = mid.x.values, mid.y.values
    return df


def load_scores():
    if not os.path.exists(SCORES):
        raise SystemExit(f"missing {SCORES}; run src/scoring.py first")
    g = gpd.read_file(SCORES)
    g["tier"] = g["tier"].replace(TIER_RENAME)
    return g


def candidates(scope, g):
    """Return {stratum_label: dataframe} in the order they should be pulled."""
    if scope == "stratified":
        return {
            "P1_safe30": midpoints(g[(g.safe_threshold == 30) & (g.has_school_market)
                                     & (g.tier == "Priority 1")]
                                   .sort_values("speed_safety_score", ascending=False)).head(600),
            "gradesep":  midpoints(g[g.grade_sep_uncertain]
                                   .sort_values("p85", ascending=False)).head(200),
            "control":   midpoints(g[g.tier == "Lower priority"]
                                   .sort_values("traffic_pct", ascending=False)).head(300),
        }
    if scope == "priority":
        prio = g[g.tier.isin(PRIORITY_TIERS)]
        pool = g[g.tier.isin(LOWER_TIERS)]
        lower = pool.sample(n=min(N_LOWER_SAMPLE, len(pool)), random_state=7)
        both = gpd.GeoDataFrame(pd.concat([prio, lower]))
        print(f"Candidates: {len(prio)} P1+P2 + {len(lower)} lower = {len(both)}", flush=True)
        return {"_all": midpoints(both)}
    if scope == "lower":
        cand = (g[g.tier.isin(LOWER_TIERS)]
                .sort_values("traffic_pct", ascending=False).head(N_LOWER_CAND))
        print(f"Lower-tier candidates (by traffic): {len(cand)}", flush=True)
        return {"_all": midpoints(cand)}
    raise ValueError(scope)


def record(row, stratum, fn, with_seg_id):
    rec = {
        "stratum": stratum, "region": row["region"], "name": str(row["name"]),
        "road_class": row["road_class"], "land_use": row["land_use"],
        "speed_limit": float(row["speed_limit"]), "p85": float(row["p85"]),
        "safe_threshold": float(row["safe_threshold"]),
        "has_school_market": bool(row["has_school_market"]),
        "grade_sep_uncertain": bool(row["grade_sep_uncertain"]),
        "tier": row["tier"], "severity": row["severity"],
        "lat": round(float(row["lat"]), 5), "lon": round(float(row["lon"]), 5),
        "file": fn,
    }
    if with_seg_id:
        # seg_id first, matching the manifests the classifier already consumes
        rec = {"seg_id": str(row["seg_id"]),
               **rec,
               "speed_safety_score": round(float(row["speed_safety_score"]), 2)}
    return rec


def next_index(manifest, prefix):
    """Highest existing index + 1.

    The superseded `_full` script used len(manifest), which silently overwrites images
    whenever the manifest is not contiguous (any interrupted or pruned run). Taking the
    max is the safe form and is identical when nothing is missing.
    """
    idxs = []
    for k in manifest:
        tail = k[len(prefix):] if k.startswith(prefix) else k.split("_")[-1]
        if tail.isdigit():
            idxs.append(int(tail))
    return max(idxs, default=-1) + 1


def main():
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--scope", required=True, choices=sorted(SCOPES),
                    help="which sampling frame to pull")
    ap.add_argument("--limit", type=int, default=None,
                    help="stop after N new images (for a dry run)")
    args = ap.parse_args()

    token = os.environ.get("MLY_TOKEN")
    if not token:
        raise SystemExit("MLY_TOKEN not set. This stage needs a Mapillary API token.")

    cfg = SCOPES[args.scope]
    os.makedirs(cfg["out"], exist_ok=True)
    g = load_scores()
    pools = candidates(args.scope, g)

    manifest = {}
    done = set()
    if cfg["resume"] and os.path.exists(cfg["manifest"]):
        with open(cfg["manifest"], encoding="utf-8") as fh:
            manifest = json.load(fh)
        done = {v.get("seg_id") for v in manifest.values()}
        print(f"Resuming: {len(manifest)} already in {cfg['manifest']}", flush=True)

    idx = next_index(manifest, cfg["prefix"])
    pulled = 0

    for label, df in pools.items():
        quota = QUOTA.get(label)
        got = 0
        if quota:
            print(f"Pulling {label} (target {quota})...", flush=True)
        for _, row in df.iterrows():
            if quota and got >= quota:
                break
            if args.limit and pulled >= args.limit:
                break
            if cfg["resume"] and str(row["seg_id"]) in done:
                continue

            im = get_img(token, row["lon"], row["lat"])
            time.sleep(cfg["sleep_fetch"])
            if not im or not im.get("thumb_1024_url"):
                continue

            iid = f"{cfg['prefix']}{idx:0{cfg['width']}d}"
            fn = f"{cfg['out']}/{iid}.jpg"
            try:
                urllib.request.urlretrieve(im["thumb_1024_url"], fn)
            except Exception:
                continue

            stratum = row["tier"] if label == "_all" else label
            manifest[iid] = record(row, stratum, fn, cfg["with_seg_id"])
            if cfg["resume"]:
                done.add(str(row["seg_id"]))
            idx += 1
            got += 1
            pulled += 1

            if cfg["resume"] and pulled % 25 == 0:
                _save(manifest, cfg["manifest"])
                print(f"  pulled {pulled} (manifest {len(manifest)})", flush=True)
            elif quota and got % 10 == 0:
                print(f"  {label}: {got}/{quota}", flush=True)
            time.sleep(cfg["sleep_loop"])

        if quota:
            print(f"  {label}: collected {got}", flush=True)
        if args.limit and pulled >= args.limit:
            print(f"  stopping at --limit {args.limit}", flush=True)
            break

    _save(manifest, cfg["manifest"])
    key = "stratum" if args.scope == "stratified" else "tier"
    print(f"\nManifest {cfg['manifest']}: {len(manifest)} images "
          f"({pulled} new this run) -> {cfg['out']}/")
    print(f"  by {key}: {dict(Counter(v[key] for v in manifest.values()))}")
    print("Next: ANTHROPIC_API_KEY=... python src/imagery_cv_classify.py "
          f"{cfg['manifest']}")


def _save(manifest, path):
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
