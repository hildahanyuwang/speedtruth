# SpeedTruth

**Identifying where posted speed limits are misaligned with real-world road conditions, and the governance failures behind them.**

A submission to the **ADB AI for Safer Roads Innovation Challenge 2026** (Thailand & Maharashtra, India). SpeedTruth scores every road segment on how far its posted limit and operating speed depart from **Safe System survivable speeds**, weighted by vulnerable-road-user (VRU) exposure, and attaches a plain-language *governance flag* explaining the probable reason the limit has drifted from reality.

> **Framing.** Not "do drivers obey the limit?" but **"is the limit itself right for this road and its most vulnerable users?"**, the question the standard speed-compliance KPI silently skips. Where a limit is wrong, that is a *governance-maintenance failure*: the limit-review process has fallen behind the road.

---

## What makes it different

- **We audited and rebuilt our own model** (12 documented fixes) when the data didn't support the first design, and report every fix (`METHODOLOGY.md` §3.6).
- **We automated iRAP-style road-condition reading from street imagery** with a vision model, whose reads **track functional road class independently** (an unseen field) and are consistency-checked at 90% vs a human rating (a certified-coder study is the refinement-stage upgrade), then used it across 3,537 segments (24% of the network) to *correct our own thresholds in both directions at network scale*, surfacing **39 dangerous roads a posted-limit/POI method structurally cannot find** (`STREETVIEW_VERIFICATION.md` Parts D–F). This is a layer the posted-vs-driven "credibility index" does not have.
- **We are honest about what the data cannot see**, the informal "invisible fleet" of auto-rickshaws, modified and human-powered vehicles, so scores on those corridors are flagged as a conservative lower bound, not hidden.
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
| *Bonus:* visual validation | [`STREETVIEW_VERIFICATION.md`](STREETVIEW_VERIFICATION.md), blind test + automated CV audit |
| *Bonus:* honest adoption path | [`ADOPTION.md`](ADOPTION.md), what a ministry still needs, with timelines |

## Approach in brief
1. **Harmonize** two heterogeneous country datasets into one schema; clean. → `harmonize.py`
2. **VRU exposure** from OpenStreetMap via Overpass, joined per segment (150 m). → `fetch_osm_vru.py`, `vru.py`
3. **Score** against **Safe System survivable speeds** (pedestrian 30 / urban 50 / rural 70 / motorway 110 km/h), three independent factors, transparent and rule-based. → `scoring.py`
4. **Verify & correct** road condition from street imagery with a vision model. → `streetview_cv_*.py`, `scoring_cv.py`
5. **Diagnose, map & cost**, governance flags + intervention priorities. → `make_map.py`, `make_priority_map.py`, `prioritize.py`

## Validation (no crash data was provided, so we are explicit)
- **Blind street-view test against controls:** 79% agreement; the model's "safe" calls are highly reliable.
- **Automated road-condition CV:** reads track functional road class *independently*; 90% consistency vs a human rating; bidirectional network-scale self-correction. (Certified-coder reliability study = refinement stage.)
- **Stability:** Priority-1 set holds at Jaccard 0.82–0.95 under ±30% weight changes.
- **Sample-size robustness (challenge FAQ's explicit ask):** the score correlates *positively* with `SampleSizeTotal` (THA +0.24, MAH +0.43) and Priority-1 segments are *better*-sampled than average, so flags are not a low-sample artefact; high-confidence-only re-ranking retains 78% (THA) / 65% (MAH) of Priority-1. (`src/sensitivity_samplesize.py`)
- **External convergence (WorldPop):** open population density (FAQ-suggested) confirms the OSM exposure signal (Spearman +0.32/+0.46) and finds ~1,159 high-population segments with no OSM POI, so OSM exposure is a lower bound. (`src/worldpop_exposure.py`)
- **External convergence:** with iRAP pedestrian star ratings.
- **Honest nulls:** a district-level test against police black spots did *not* converge, expected (reactive vs proactive), reported plainly.

## Data & compliance (FDUA)
**No challenge data is included in this repository.** The datasets are provided under ADB's Fair Data Use Agreement, which requires confidentiality and deletion within 14 days of participation ending. Per FDUA §4.4, only **derived outputs** (scores, classifications, aggregated maps) are shared, never raw probe values (posted limits, P85, distributions) or anything that could reconstruct them. `.gitignore` blocks all raw data, geometry-bearing derivatives, and per-segment tables. To reproduce, place the challenge files in the project root.

## Setup & reproduce
```bash
pip install -r requirements.txt
python src/fetch_osm_vru.py MAH && python src/fetch_osm_vru.py THA  # OSM VRU POIs
python src/scoring.py      # → Speed Safety Score
python src/make_map.py && python src/make_priority_map.py      # → interactive maps
# optional, needs MLY_TOKEN + ANTHROPIC_API_KEY:
python src/streetview_cv_pull.py && python src/streetview_cv_classify.py  # road-condition CV
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
