# SpeedTruth

**Identifying where posted speed limits are misaligned with real-world road conditions, and the governance failures behind them.**

A submission to the **ADB AI for Safer Roads Innovation Challenge 2026** (Thailand & Maharashtra, India). SpeedTruth scores every road segment on how far its posted limit and operating speed depart from **Safe System survivable speeds**, weighted by vulnerable-road-user (VRU) exposure, and attaches a plain-language *governance flag* explaining the probable reason the limit has drifted from reality.

> **Framing.** Not "do drivers obey the limit?" but **"is the limit itself right for this road and its most vulnerable users?"**, the question the standard speed-compliance KPI silently skips. Where a limit is wrong, that is a *governance-maintenance failure*: the limit-review process has fallen behind the road.

---

## What makes it different

- **The model was audited and rebuilt** (12 documented fixes) when the data did not support the first design, and every fix is reported rather than folded in silently (`METHODOLOGY.md` §3.6). The code says why the previous version was wrong.
- **Road condition is read from street imagery** by a vision model and fed back into an already-computed score, across 3,537 segments (24% of the network), correcting the rule's own thresholds in both directions. Most of that correction moved segments *down*. It also promoted **39 segments from the bottom two tiers straight to Priority 1**: roads with no school or market tagged, which the rule therefore scored low, and which the photograph shows to be pedestrian-mixing streets (`IMAGERY_VERIFICATION.md` Parts D–F). A posted-limit or POI method cannot surface those.
- **What the data cannot see is flagged, not hidden**: the informal fleet of auto-rickshaws, modified and human-powered vehicles does not appear in probe data, so scores on those corridors are marked a conservative lower bound.
- **Two axes, decision-ready:** an absolute cross-country severity *and* a within-country priority, on an interactive map where every segment opens a costed decision card.

## What it delivers (mapped to the challenge)

| Challenge deliverable | In this repo |
|---|---|
| Analytical model + methodology | `src/` pipeline + [`METHODOLOGY.md`](METHODOLOGY.md) (incl. the model self-audit) |
| **Speed Safety Score** (per-segment classification) | `src/scoring.py` (rule-based), `src/scoring_cv.py` (imagery-corrected v3) |
| Geospatial visualization of Speed-Unsafe Segments | `src/make_map.py`, `src/make_priority_map.py` → interactive HTML; [`index.html`](index.html) front door |
| Findings Summary (≤5 pages) | [`FINDINGS.md`](FINDINGS.md) / `FINDINGS.docx` |
| *Bonus:* worked intervention dossier | [`PILOT_CORRIDOR.md`](PILOT_CORRIDOR.md), one corridor, flag → costed action |
| *Bonus:* investment corridor short-list | [`CORRIDORS.md`](CORRIDORS.md), flagged segments rolled into fundable corridors (`src/corridors.py`, `output/corridor_map.html`) |
| *Bonus:* visual validation | [`IMAGERY_VERIFICATION.md`](IMAGERY_VERIFICATION.md), blind test + automated CV audit |
| *Bonus:* honest adoption path | [`ADOPTION.md`](ADOPTION.md), what a ministry still needs, with timelines |

## Approach in brief
1. **Harmonize** two heterogeneous country datasets into one schema; clean. → `harmonize.py`
2. **VRU exposure** from OpenStreetMap via Overpass, joined per segment (150 m). → `fetch_osm_vru.py`, `vru.py`
3. **Score** against **Safe System survivable speeds** (pedestrian 30 / urban 50 / rural 70 / motorway 110 km/h), three independent factors, transparent and rule-based. → `scoring.py`
4. **Verify & correct** road condition from street imagery with a vision model. → `imagery_pull.py / imagery_cv_classify.py`, `scoring_cv.py`
5. **Diagnose, map & cost**, governance flags + intervention priorities. → `make_map.py`, `make_priority_map.py`, `prioritize.py`

## Validation (no crash data was provided, so each check is labelled for what it is)
- **Blind imagery test:** the model agreed with a blind human rating on **19 of 24 segments (79%)**. The sample is small and each segment is judged from a single frame, so this supports the *direction* of the correction, not its precision.
- **Road-condition read, one independent check and one consistency check, kept apart:** the independent signal is against the dataset's functional road class, a field the classifier never sees, and the read is cleanly monotonic across it. The **90% (28 of 31)** figure is agreement with a rating by the author, who knew the experimental design, so it is **consistency, not independent corroboration**. A certified-coder study on a larger held-out sample is the refinement-stage upgrade.
- **Stability, two tests that answer different questions.** Perturbing the published weights by ±30% holds the Priority-1 set at Jaccard 0.82–0.95. Across **2,000 random weightings spanning the whole simplex**, the *ordering* barely moves (median rank correlation **0.954**) but the *cut-off* does: only **481 of the 1,473 Priority 1 segments** are Priority 1 under nearly any weighting, and **992 depend on the weighting chosen**. Both of those counts are checked by `reproduce.py`.
- **Sample-size robustness (challenge FAQ's explicit ask):** the score correlates *positively* with `SampleSizeTotal` (THA +0.24, MAH +0.43) and Priority-1 segments are *better*-sampled than average, so flags are not a low-sample artefact; high-confidence-only re-ranking retains 78% (THA) / 65% (MAH) of Priority-1. (`src/sensitivity_samplesize.py`)
- **External convergence (WorldPop):** open population density (FAQ-suggested) confirms the OSM exposure signal (Spearman +0.32/+0.46) and finds ~1,159 high-population segments with no OSM POI, so OSM exposure is a lower bound. (`src/worldpop_exposure.py`)
- **External convergence, directional only:** iRAP/ThaiRAP rate 19% of Thai roads 3-star or better for pedestrians; this analysis reaches the same systemic conclusion from a different input (`FINDINGS.md` §3.5). Same direction, not the same measurement.
- **Honest nulls:** a district-level test against police black spots did *not* converge, expected (reactive vs proactive), reported plainly.

## Data & compliance (FDUA)
**No challenge data is included in this repository.** The datasets are provided under ADB's Fair Data Use Agreement, which requires confidentiality and deletion within 14 days of participation ending. Per FDUA §4.4, only **derived outputs** (scores, classifications, aggregated maps) are shared, never raw probe values (posted limits, P85, distributions) or anything that could reconstruct them. `.gitignore` blocks all raw data, geometry-bearing derivatives, and any per-segment table that carries or reconstructs a probe value. To run the pipeline itself, place the challenge files in the project root.

## Setup & reproduce

**Check the published numbers in one command, with no credentials:**
```bash
pip install -r requirements.txt
python reproduce.py          # checks each published figure against the committed outputs
```
It compares each published figure with the value recomputed from the committed outputs
and exits non-zero if any has drifted. `python reproduce.py --chain` prints the upstream
pipeline order.

**44 of the 61 figures are checked here, with no API keys and none of the confidential
data.** They run against `output/reproduction_bundle.csv`, one row per scored segment
carrying the classifications and flags but no coordinates and no speed value of any kind.

**The other 17 are not attempted, and the script names them rather than dropping them.**
All seventeen need a posted limit or an observed speed, which the licence keeps out of
this repository; anyone holding the challenge data gets all 61 from the same command. The
output also marks which figures are recomputed from per-segment data and which are only
checked against a committed aggregate, because those are not the same evidence.

**[REPRODUCIBILITY.md](REPRODUCIBILITY.md)** sets out the two tiers, what the bundle
deliberately excludes, and what it still discloses.

**Re-run the pipeline itself** (needs the challenge data under FDUA, plus API keys):
```bash
python src/fetch_osm_vru.py MAH && python src/fetch_osm_vru.py THA  # OSM VRU POIs
python src/scoring.py      # → Speed Safety Score
python src/make_map.py && python src/make_priority_map.py      # → interactive maps
# optional, needs MLY_TOKEN + ANTHROPIC_API_KEY:
python src/imagery_pull.py --scope priority && python src/imagery_cv_classify.py  # road-condition CV
# optional supplementary analyses (FAQ-recommended robustness + external checks):
python src/sensitivity_samplesize.py   # SampleSizeTotal sensitivity (FAQ-recommended)
python src/validate_thairsc.py         # external outcome convergence vs provincial death rates
python src/worldpop_exposure.py        # WorldPop population cross-check (downloads open rasters to worldpop/)
```

## Limitations (stated honestly)
- The **posted-limit field is unvalidated** (commercial-probe estimate); SpeedTruth flags for **review**, never asserts a limit is definitively wrong.
- **No crash data** → no outcome-based ground truth; the model does not predict crashes.
- **~80% of the network lacks probe data** and is excluded, disproportionately the local/rural roads where VRUs are most exposed, so network-wide risk is under-covered, not over-stated.
- Helmet data is **aggregate context**, not a scoring input; OSM and street-imagery coverage are **lower bounds**.

## Team
SpeedTruth (solo). Contact: Hanyu Wang (Hilda).

*Network data © OpenStreetMap contributors, Overture Maps Foundation. Street imagery © Mapillary contributors (CC BY-SA).*
