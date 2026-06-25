# SpeedTruth, Methodology & Evaluation

*ADB AI for Safer Roads 2026 · Speed Safety Score for identifying speed-limit misalignment*

---

## 1. Problem framing

This challenge is **not** about detecting whether drivers speed. It is about whether the **posted speed limit itself is appropriate** for the road's real-world function and its exposure to vulnerable road users (VRUs).

SpeedTruth reframes limit misalignment as a **governance-failure identification** problem: where a posted limit is inconsistent with Safe System principles, it is evidence that the limit-review mechanism has not kept pace with the road's actual operating conditions. The Speed Safety Score therefore not only ranks risk but attaches a structured *governance flag* explaining the probable reason a limit has drifted from reality.

## 2. Data and honest limitations

| Input | Source | Use |
|---|---|---|
| Operating speed (P85, median), posted limit, %-over-limit | commercial probe (challenge data) | Core speed signals |
| Road class, urban/rural, geometry | Overture (challenge data) | Function & length |
| Helmet-wearing SPI (country × urban/rural) | ADB challenge xlsx | VRU lethality proxy |
| VRU generators (schools, markets, hospitals, transit, worship) | OpenStreetMap via Overpass | VRU exposure |

**Limitations stated up front (these constrain every claim below):**
- **Posted limit is unvalidated.** The challenge guide states the limit field is commercial-probe-derived and "not validated." We therefore treat it as an *estimate* and never assert a limit is definitively wrong, only that a segment warrants **review**.
- **No crash/injury data.** This removes any supervised, outcome-based validation. Our evaluation (§6) uses internal consistency and convergent signals instead, and we do **not** claim to predict crashes.
- **Helmet SPI is aggregate** (country × urban/rural, a two-value constant per country), not per-segment. In v2 it is **not a scoring factor**; it is reported as a lethality *context* only (§3.3).
- **OSM coverage is a lower bound.** Crowdsourced POIs under-represent some areas; VRU exposure is a known-presence signal, not a census.
- **The most vulnerable users are the least visible.** Informal three-wheelers, modified and human-powered vehicles are absent from probe, helmet and OSM data, so scores on the corridors they frequent are a conservative lower bound (§3.3).
- **Only ~one-fifth of the network is scored** (valid probe data only); the unscored remainder skews toward the local/rural roads where VRUs are most exposed.
- **Pedestrian fatality curve is indicative.** See §3.4.

## 3. Speed Safety Score design

A per-segment composite score in [0, 100], reported on **two axes**: an **absolute Safe-System severity** (Critical / Serious / Marginal / Compliant, by how many km/h operating speed exceeds the survivable speed, comparable across countries) and a **within-country priority** percentile (Priority 1 / 2 / Monitor / Compliant, for each ministry to sequence its own network). Reporting both avoids treating a constructed "top 10%" as if it were an absolute danger level. Computed only on segments with valid probe speed (`AnalysisStatus = Valid`); network-only segments are excluded from scoring (about four-fifths of the full network, disproportionately the local/rural roads where VRUs are most exposed, a coverage limitation that makes network-wide risk under-covered, not over-stated).

### 3.1 Safe System anchor (survivable impact speeds)
Each segment is assigned a **safe speed threshold** = the speed at which the most vulnerable user present can survive a crash (WHO *Speed Management*; World Bank GRSF *Guide for Safe Speeds*; Tingvall & Haworth 1999, see `SOURCES.md`):

| Context (data-driven) | Threshold |
|---|---|
| School/market adjacent, or high VRU density (pedestrian mixing) | **30 km/h** |
| Urban, other (intersections / side-impact) | **50 km/h** |
| Rural undivided (head-on risk) | **70 km/h** |
| Motorway (separated, no VRU conflict) | **110 km/h** |

VRU context is derived from OSM exposure (§3.3), not assumed from urban/rural alone, this distinguishes a separated urban expressway from a street with pedestrian crossings.

### 3.2 Sub-factors (weights in `src/scoring.py::WEIGHTS`)
The composite uses **three independent factors** (model v2; see §3.6 for the internal audit that produced this design):

| Factor | Meaning | Weight |
|---|---|---|
| `oper_excess` | P85 above the safe threshold (hardest safety signal) | 0.45 |
| `limit_excess` | Posted limit above the safe threshold (limit itself permits unsafe speed) | 0.35 |
| `vru_exposure` | VRU generator exposure along the segment (length-robust) | 0.20 |

Each factor is normalised with a **smooth saturating transform** `x/(x+k)` (k = the within-country median of positive values), which, unlike a hard cap, keeps the most extreme segments rank-ordered instead of flattening them all to 1. Weights are an explicit, documented policy choice and are stress-tested in §6 (Priority-1 set stable at Jaccard 0.82–0.95 under ±30% perturbation). The two earlier factors `dev_gap` and `func_mismatch` were **removed from the composite** (audit §3.6) and retained only as governance diagnostics.

### 3.3 VRU exposure, lethality context, and the invisible fleet
1. **Exposure** → a school/market within 150 m (a genuine pedestrian generator) sets the safe threshold to 30 (§3.1); a length-robust weighted POI count feeds the `vru_exposure` factor. *(v2 change: the threshold trigger is now presence of a real pedestrian generator, not a length-confounded density quantile, audit §3.6.)*
2. **Lethality context (reported, not scored).** Helmet non-wearing is **only a two-value urban/rural stratum constant** per country (Maharashtra ≈ 15–24% wearing vs Thailand ≈ 67–79%), so it cannot honestly act as a per-segment factor. We therefore report it as a **lethality context overlay** (~1.5× Maharashtra, ~1.2× Thailand) rather than multiplying the score by it, an earlier multiplier was found to be dominated by the urban/rural base-score gap and is removed (audit §3.6).
3. **The invisible fleet.** Auto-rickshaws, modified/engine-retrofitted vehicles and human-powered rickshaws, a large, higher-risk share of South/Southeast-Asian traffic, are absent from fleet-based probe speeds, from motorcycle-only helmet data, and largely from OSM (an open three-wheeler-stand pull returned only 182 stands in Maharashtra, a lower bound). Their under-representation means scores on affected corridors are a **conservative lower bound**; this is stated as a direction-of-bias limitation, not silently absorbed.

### 3.4 Auxiliary indicator, pedestrian fatality probability
For interpretability we report, per segment, the probability that a pedestrian struck at the segment's P85 dies, using the empirically calibrated curve of **Rosén & Sander (2009)**:

`P(v) = 1 / (1 + exp(6.9 − 0.090·v))` (v = impact speed, km/h)

Verified values: 30→1.5%, 50→8.3%, 70→38%, 75→46%. **Indicative only**: calibrated on German passenger cars and adult pedestrians; the authors explicitly note fatality risk is *higher* in countries with less-developed emergency care (i.e. Thailand/India). Not applied to two-wheeler occupants.

### 3.5 Grade-separation handling (honest, not silent)
Some fast `trunk` segments are in reality access-controlled expressways where pedestrians cannot reach the carriageway, and would be false positives if judged against a pedestrian threshold. The v2 presence-based trigger already prevents this (they have no school/market, so they are not pushed to 30 and do not enter the priority tier, verified: 0–11 of 1,163 candidates reach Priority 1). Lacking OSM access/dual-carriageway tags to confirm separation, we **flag** the 1,163 candidates (`grade_sep_uncertain`) and report severity with and without them, rather than reclassifying, which would risk hiding genuinely dangerous undivided rural highways at the same speeds. Coordinate-level confirmation is reserved for the refinement stage.

### 3.6 Internal model audit (why v2 differs from v1)
We audited the first model against its own data and rebuilt it where the data did not support the design. Key findings and fixes:
- **Saturation.** A hard `/40` normalisation flattened 65–74% of Priority-1 segments' main factors to 1, destroying within-tier discrimination → replaced with the smooth `x/(x+k)` transform (§3.2).
- **Redundancy.** `dev_gap` correlated 0.80 with `oper_excess − limit_excess`, and `func_mismatch` was zero for 60% of segments (it rewards conformity to a class median, not safety) → both removed from the composite.
- **Helmet multiplier reversed.** As a near-constant 1.5× it was dominated by the urban/rural base-score gap (within-country score-vs-helmet correlation was *negative*) → removed from the score, reported as context (§3.3).
- **Length confounding.** `vru_per_km` correlated 0.58 with 1/length → length floor added; threshold trigger made presence-based.
- **Definitional headline.** "Limit exceeds safe speed" near pedestrians is near-automatic; we now state it as Safe System *doctrine*, not an empirical discovery.
- **Imagery-confirmed at scale, taking up the challenge's explicit call to cross-reference the `StreetImageLink` and improve the `LandUse`/`SpeedLimit` classifications (the proxy over-assigns).** We automated the iRAP coding task: a vision LLM reads each street image's road condition (`STREETVIEW_VERIFICATION.md` Parts D–F), whose reads **track functional road class independently** (an unseen field) and are consistency-checked at **90%** vs a human rating, a certified-coder reliability study being the refinement-stage upgrade. Run on 170 segments, it finds **96% of safe=30 Priority-1 segments have an implied safe speed >30** (mean 64), so the OSM proxy over-states the danger magnitude ≈2×; yet **84% remain genuinely misaligned at the corrected threshold** (direction right, magnitude inflated), while it independently confirms the grade-separation flag (100%) and controls (96%). Fed back across **3,537 imagery-covered segments (24% of the network; v3, `scoring_cv.py`)**, this is a **bidirectional correction**: it removes over-flags (81% of covered Priority-1 demoted, the proxy too strict) *and* catches under-flags the POI proxy missed, promoting **39 low-priority segments straight to Priority 1** where imagery shows pedestrian-mixing the rule could not see (Part F). The validated pipeline exists in `src/`; full-network coverage is a refinement-stage data task.

The rebuild is reproducible (identical inputs → identical tiers) and the Priority-1 set is stable under ±30% weight perturbation (Jaccard 0.82–0.95). Full audit log in `PROGRESS.md` §12b.

## 4. Governance flags
Each scored segment receives a rule-based, **probabilistic** diagnosis of why the limit may be unmaintained (language deliberately hedged, "probable", "may"):
- Limit above Safe System safe speed → limit setting itself permissive.
- P85 ≫ limit → road encourages high speed; limit not updated after road upgrade / weak enforcement feedback.
- Limit ≫ P85 → inflated limit; possible road reclassification without limit downgrade.
- Limit far from class norm → classification inconsistency.
- Urban high-VRU-lethality + unsafe operating speed → priority downgrade candidate.

## 5. Evaluation methodology

**There is no crash ground truth in the provided data.** We are explicit that this rules out supervised, outcome-based validation, and we do not claim the score predicts collisions. Instead we validate the score's *construct* through five converging checks:

1. **Internal consistency (Safe System monotonicity).** Tier should rise monotonically with operating-speed excess over the safe threshold and with VRU exposure. We report tier-vs-factor distributions to confirm the score behaves as designed.
2. **Face validity (spot-checks).** Top-ranked segments are inspected via the dataset's StreetView coordinates to confirm they are plausibly unsafe (e.g. genuinely a high-speed road beside a school), and a sample of Compliant segments to confirm the converse.
3. **Sensitivity analysis (including the challenge FAQ's explicit ask).** We perturb weights, Safe System thresholds, and the VRU buffer distance, and report the stability of the Priority-1 set (Jaccard 0.82–0.95 under ±30% weights). We also ran the **SampleSizeTotal** check the FAQ specifically recommends (`src/sensitivity_samplesize.py`, figure `output/sensitivity_samplesize.png`): the Speed Safety Score correlates *positively* with sample size (Thailand +0.24, Maharashtra +0.43), so high scores are **not** a low-sample artefact; Priority-1 segments are in fact *better* sampled than the rest (Thailand median 323k vs 208k probes; Maharashtra 49k vs 16k); and when we keep only high-confidence segments (sample ≥ the region median) and re-rank, the Priority-1 set is retained at **78% (Thailand) / 65% (Maharashtra)**, with the headline Critical-severity and school/market findings holding or strengthening. Maharashtra's lower retention reflects its lower probe coverage (which the FAQ itself flags), so we treat Indian flags as warranting more on-ground verification. A trustworthy ranking should not hinge on one arbitrary parameter, or on sample density.
4. **Convergent validity (internal + external).**
  - *Internal:* the score correlates positively but **weakly** with the dataset's own `PercentOverLimit` (rho ≈ +0.09; a signal NOT used to build it). The weakness is expected and desirable, a strong correlation would mean we had merely rebuilt speed-enforcement detection rather than limit-appropriateness.
  - *External:* SpeedTruth independently finds the large majority of Thai VRU-exposed segments operate above their Safe System pedestrian speed; iRAP/ThaiRAP independently rate only **19%** of Thai roads 3-star+ for pedestrians. Two independent methods, different metrics, converge on the same conclusion, a systemic pedestrian-safety gap. (The metrics are not numerically equivalent; this is qualitative convergence, not an equality claim.)
  - *External (population convergence).* WorldPop 2020 population density (an FAQ-suggested open source) corroborates the OSM exposure factor: segments we flag as exposed sit in significantly denser population (Spearman +0.32 Thailand, +0.46 Maharashtra; Maharashtra school/market median 1,625 vs 466 /km^2), and ~1,159 high-population segments carry no OSM POI, confirming OSM exposure is a genuine lower bound (`src/worldpop_exposure.py`).
  - *External (honest null).* Aggregated to province level, the score does **not** correlate with published 2022 provincial road-death *rates* (ThaiRSC via Population Health Metrics 2026; 10-province extremes; Spearman ≈ 0, `src/validate_thairsc.py`). This is expected and informative: death rate per population is exposure- and volume-driven (the highest-rate provinces are motorway/industrial corridors whose limits match their road design), whereas the score isolates limit *misalignment*. Like the police-black-spot null, a reactive, exposure-weighted outcome should not equal a proactive limit-appropriateness index, the divergence sharpens what the tool does and does not claim.
5. **Coverage honesty.** Any segment dropped (no probe data, zero/invalid speed) is reported, not silently excluded; VRU exposure is labelled a lower bound.

This is reported transparently, including where checks are weak, rather than asserting a single accuracy number we cannot substantiate.

## 6. Scalability & replicability
The pipeline is country-agnostic: it consumes the standard challenge schema, derives Safe System thresholds from open OSM data, and sources lethality from helmet SPI, all available or derivable for any ADB member country. Country-specific elements (expected-limit baselines, UTM projection, helmet SPI) are parameterised, not hard-coded to one geography. Adding a new country requires only its Overture/probe extract and an OSM Overpass pull.

---
*All thresholds and numbers trace to `SOURCES.md` (verified) or `src/` (computed). Final weights/breakpoints are calibrated once both regions' real VRU exposure is loaded; see `PROGRESS.md`.*
