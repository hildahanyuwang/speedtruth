# Reproducibility, and the line the data licence draws

Every figure this project publishes is checked by one command, `python reproduce.py`.
This page says exactly what that command can and cannot verify for a reader who has
only this repository, and why the difference exists.

## The short version

```
python reproduce.py
```

- **40 of the 57 published figures are checked with no credentials and no confidential
  data.** 25 of those are recomputed from a per-segment table shipped in this
  repository; 15 are checked against committed aggregates and are marked `~` in the
  output, because a check against an aggregate is the weaker of the two.
- **17 figures are not attempted, and the script names them rather than dropping them.**
  All seventeen need a speed value, which the data licence keeps out of this repository.
- **A reader holding the challenge data gets all 57**, by placing the challenge files in
  the project root and running the pipeline in `python reproduce.py --chain` order. The
  same command then finds the per-segment outputs and uses them instead.

## Why seventeen figures cannot be checked here

The challenge datasets are provided under a Fair Data Use Agreement. Derived outputs —
scores, classifications, bands — may be published. The underlying probe measurements may
not be redistributed at the level of detail in which they were supplied.

Two files carry those measurements per segment: `output/speed_safety_score.geojson` and
`output/speed_safety_score_cv.geojson`. Both hold the posted speed limit and the observed
85th-percentile speed, so `.gitignore` blocks them and they are absent here.

The seventeen figures that depend on them, grouped by what they need:

| Figures | Needs |
|---|---|
| `limit_above_survivable`, `limit_above_survivable_pct_THA`, `limit_above_survivable_pct_MAH`, `limit_gap_median_THA`, `limit_gap_median_MAH` | posted limit − survivable speed, per segment |
| `critical_THA_limit_above`, `critical_THA_gap_median` | the same difference, on Critical segments only |
| `flagged_THA`, `flagged_THA_limit_above_pct`, `flagged_MAH_limit_needs_no_change` | sets defined by the sign of that difference |
| `flagged_MAH_enforcement_km`, `flagged_MAH_enforcement_median_excess` | observed speed against the posted limit |
| `threshold_floor30_share_THA`, `threshold_floor50_pct_above_THA`, `threshold_plus10_pct_above_THA`, `threshold_plus20_pct_above_THA` | the survivable threshold and the posted limit, per segment, under alternative rulers |
| `school_market_ped_fatality_median` | modelled fatality probability at the observed speed |

The last one is worth stating plainly: pedestrian fatality probability is a monotonic
function of the observed speed, so publishing it per segment would return the observed
speed exactly. It is withheld for that reason, not out of caution.

The four threshold figures deserve a note of their own. `output/threshold_sensitivity.json`
is shipped here and holds the full result of all eleven alternative rulers, so a reader
can see what the sensitivity run found. The script still declines to check the four
published figures against it, because a number verified against a summary this project
also published is not verified at all. They stay in the not-attempted list.

## What is shipped instead

`output/reproduction_bundle.csv`, one row per scored segment, built by
`_dev_scripts/make_reproduction_bundle.py`:

| Column | What it is |
|---|---|
| `seg_id` | identifier, matches the published map layers |
| `region` | `THA` or `MAH` |
| `road_class` | OpenStreetMap highway class |
| `has_school_market` | school or market beside the segment, from OpenStreetMap |
| `has_cv` | whether street-level imagery was available for this segment |
| `severity` | Safe System severity band from the rule-based score |
| `tier` | priority tier from the rule-based score, a within-region percentile |
| `severity_v3` | severity band after the imagery correction |
| `tier_v3` | priority tier after the imagery correction |

No coordinates. No speed of any kind. No thresholds, no score, and no score components.
The build script refuses to write the file if any restricted column is present, rather
than relying on the column list being correct.

## What the bundle does reveal, stated rather than glossed

`severity` is the observed speed minus the survivable speed, placed in one of four
bands. The survivable speed is reconstructible from open data, because it depends only
on road class, setting, and the presence of vulnerable road user generators. A reader
who reconstructs it can therefore bound the observed speed on a given segment to a
range.

That is a band, not a value, and it is the same reduction in detail that the published
map layers already carry. It is written here because a reproducibility claim that hides
its own residual disclosure is not a reproducibility claim.

## Three strengths of check, kept apart

The script distinguishes them because they are not the same evidence:

1. **Recomputed** — the figure is derived again from per-segment data present at run
   time. If the outputs changed, the number changes.
2. **Checked against a committed aggregate** (`~` in the output) — the figure is
   compared with a summary that an upstream script wrote, for example
   `output/corridors_summary.json`. This catches a published number drifting away from
   the outputs. It does not re-derive the number from the segments.
3. **Not attempted** — named in the output with the reason, never silently omitted.

## Running the full check with the challenge data

1. Place the challenge files in the project root.
2. Run the upstream stages in the order printed by `python reproduce.py --chain`.
   Stages 4 and 5 need a Mapillary token and a vision-model key; stages 1–3 and 6–8 do
   not.
3. Run `python reproduce.py`. With the per-segment outputs present it checks all 57 and
   reports nothing as skipped.

## Rebuilding the bundle

```
python _dev_scripts/make_reproduction_bundle.py
```

Run where the restricted outputs live. It writes the bundle and two aggregate-only
summaries of the imagery validation, whose per-image tables carry coordinates and speeds
and stay local.
