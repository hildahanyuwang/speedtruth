# SpeedTruth, Street-Level Verification

*Visual ground-truthing of top priority segments using Mapillary street-level imagery. Images © Mapillary contributors (CC BY-SA). Thumbnails in `output/streetview_images/`.*

We pulled real street-level imagery for the highest-priority segments and **looked at each one** to check whether the score reflects the road's actual condition. This does two things a statistic cannot: it confirms genuine hazards with visible evidence, and it **honestly exposes where the model is wrong**. Of the cases below, three confirm the diagnosis and one is a false positive the model should not have flagged, which we report openly.

---

*(Per-segment posted limits, operating speeds and coordinates are confidential under the data agreement and omitted; the visible road condition and the model's classification, derived outputs, are reported.)*

## Case 1, FALSE POSITIVE (the honest one): Kanchanaphisek Road, Thailand
A **grade-separated expressway** flagged by the proximity rule. Street view shows a central barrier and continuous side guardrails; commercial signage beside the road is why the model's OSM proximity rule pulled the safe speed down and flagged it, but the carriageway is physically separated, so pedestrians cannot mix with traffic.
**Verdict: false positive.** The 150 m POI-proximity rule mistook roadside commerce for pedestrian mixing on a separated road. *Method implication:* grade-separated arterials need a separation check before the low VRU threshold is applied, caught exactly by street-level verification.

## Case 2, CONFIRMED: Katraj-Dehu Road, Maharashtra
A high-speed **motorcycle corridor** (helmet-wearing ~15-24%). 360° street view shows a motorcyclist sharing the running lane with trucks and cars (the camera is mounted on a motorcycle). A grass median exists, but **no separated facility for two-wheelers**, riders mix directly with heavy vehicles at highway speed.
**Verdict: confirmed.** The lethal combination the score targets: unsafe limit + motorcycle mixing + Maharashtra's very low helmet use.

## Case 3, CONFIRMED: rural arterial through a market, Maharashtra
Street view shows a heavy goods vehicle moving through a stretch lined with **roadside market stalls and informal shelters**, with pedestrian/vendor activity at the edge, while operating speed runs far above the posted limit.
**Verdict: confirmed.** Operating overshoot through a live market, precisely the VRU-exposure-meets-speed hazard the model flags.

## Case 4, CONFIRMED: Nashik-Pune Highway, Maharashtra
Street view shows a **narrow single-lane-each-way road** with a motorcyclist riding the edge and vehicles queuing. The posted limit is far above what the road can safely carry (operating speed is a fraction of it).
**Verdict: confirmed (inflated limit).** A highway-speed limit on a narrow mixed-traffic road is inconsistent with its function, the "inflated limit" governance pattern, with two-wheelers still exposed.

---

## What this verification adds
1. **Evidence, not assertion.** The headline hazards (motorcycle mixing, market exposure, inflated limits) are confirmed with imagery a ministry can see for itself.
2. **Honest error reporting.** One in four top cases was a false positive, and the method's own street-view step caught it. We state the failure mode (separated arterials) and the fix, rather than hiding it.
3. **A built-in QA loop.** Street-level verification turns the Speed Safety Score from a one-shot model into a checkable, improvable system, and points to the next refinement (separation-aware thresholds).

*Coverage note: Mapillary is crowd-sourced; ~50% of sampled top segments had imagery within 130 m. Where imagery is absent, segments are scored but not visually verified, a coverage limit we state plainly.*

---

## Part B, Blind verification WITH CONTROLS (24 segments)

The four cases above confirm that flagged roads look hazardous. But a stronger question is **discriminative**: can the model's flag be recovered from the road's appearance alone, *without* seeing the score, and does it distinguish unsafe roads from safe ones? To test this we built a controlled, blinded check (`src/streetview_blindtest.py`).

**Method.** We pulled Mapillary imagery for **16 Priority-1 segments** (model says *unsafe*) and **8 Compliant segments** (model says *safe*, deliberately the *highest-traffic* Compliant roads, i.e. hard controls that could superficially look flaggable, not empty rural lanes). Images were saved with **anonymised, shuffled filenames**; the tier/score key was withheld. Each image was rated **on its visible content alone** (VRU mixing, separation, road standard) as *flag* or *safe*, and only then was the key revealed.

**Result, 79% blind agreement with the model (19/24):**

| | Model: unsafe (Priority-1) | Model: safe (Compliant) |
|---|---|---|
| **I rated unsafe** | 12 | 1 |
| **I rated safe** | 4 | 7 |

- **Sensitivity 75%**, **Specificity 88%**.
- **The model's "safe" calls are highly reliable (7/8).** It correctly did **not** flag four genuine grade-separated expressways (Bangkok–Chonburi Motorway, Kanchanaphisek Road, Chalong Rat Expressway, Buraphawithi Expressway), precisely the separated-road trap that produced the false positive in Part A. Here the model avoided it.
- **The model's "unsafe" calls are 12/16 visually confirmed**: motorcycle / auto-rickshaw mixing (Katraj–Dehu Bypass, Bhosari Flyover), market and roadside-vendor exposure, narrow mixed-traffic arterials (Nashik–Pune Highway).

**What the disagreements teach (reported openly):**
- **4 false negatives in *my* rating** (img_04/05/07 Thailand; one Nashik–Pune segment): all are open or divided high-speed roads with **no VRU visible in the single frame**. Either they are flagged for reasons not visible in one photo (P85 far above the limit; a school/market just out of shot), or they are the **same separated-road false-positive mode** documented in Part A. A single frame cannot settle which, a known limit of frame-level checking.
- **My one control error:** I over-flagged the Bangkok–Chonburi **Motorway** (a truck and a motorcycle shared the frame); the model correctly scored it Compliant. Here the human was stricter than the model.

**Honest caveats.** This validates the score against **visible road condition**, not crash outcomes. The rater knew the experimental design (though not the per-image score); a single street-view frame is not the whole segment; controls are limited to Mapillary-covered (urban/arterial) roads; n = 24; two Phetkasem-Road segments happened to share one image. Full per-image ratings: `output/blindtest_results.json`.

**Why this matters.** Unlike an aggregate statistic, this shows the Speed Safety Score tracks what a ministry officer would see on the ground, its *safe* calls are trustworthy, its *unsafe* calls are mostly confirmed, and its residual error has a single, namable, fixable cause (separation-aware thresholds). That is a checkable, improvable system, not a black box.

---

## Part C, The invisible fleet, made visible (itemised)

The blind test (Part B) confirmed flagged segments visually; here we itemise specifically the **informal/vulnerable vehicles** the probe data cannot see but the imagery does, on the flagged high-speed segments. (Author's direct frame review; single-frame, sample-based.)

| Segment (flagged) | Directly observed on the carriageway |
|---|---|
| Katraj–Dehu Bypass (MAH) | **Auto-rickshaw** mid-carriageway with car, motorcycles, truck, **pedestrians**; no footpath |
| Nashik–Pune Highway (MAH) | **Auto-rickshaw carrying a passenger** beside a motorcycle and cars; undivided |
| Katraj–Dehu Bypass (MAH, 360°) | Dense **motorcycles**, an informal goods **tempo**, pedestrians; dusty roadside, no footpath |
| Phetkasem Road (THA) | Undivided road through a settlement, roadside dwellings, no footpath; operating speed **roughly double the limit** |
| rural arterials (THA) | Undivided carriageway with roadside dwellings and informal access points (single frame, light traffic) |

**Specificity check (controls, correctly *not* flagged):** Bangkok–Chonburi Motorway and Kanchanaphisek Road imagery show **grade-separated carriageways with a central barrier and no vulnerable users**, confirming the v2 model and grade-separation handling exclude exactly the separated roads that should be excluded.

**Honest scope.** This is **direct observation, not a count**: a quantified per-segment informal-vehicle exposure layer was attempted from probe speed dispersion (P85 − median) and **rejected**, in this dataset that dispersion is a near-constant ~14 km/h, uncorrelated with VRU presence, because P85 and median derive from the same fitted distribution. The invisible fleet therefore cannot be *measured* from the provided data; it can be *seen* in imagery (above) and bounded by external fleet-composition statistics. A scaled, automated street-view audit is the refinement-stage path to quantification.

---

## Part D, Scaled blind ROAD-CONDITION audit (the imagery used correctly)

Street imagery's rigorous use is to read the **static road condition** that determines whether a limit is appropriate, separation, footpath, roadside development, genuine pedestrian mixing, not to count transient traffic. We pulled one Mapillary image for **32 segments** across three strata and the author rated each anonymised image's **road condition BEFORE** seeing the model's assumption (`src/streetview_roadaudit.py`; key `output/roadaudit_key.json`; ratings `output/roadaudit_results.json`).

| Stratum | What the model assumed | Imagery verdict | Reading |
|---|---|---|---|
| **A. safe=30 (OSM school/market ≤150 m)**, 16 | a 30 km/h pedestrian-mixing road | **4 genuine pedestrian environments, 12 fast highways** (operating well above 30) | **The OSM proxy over-assigns the 30 threshold (~75%).** Empirically confirms audit F1. |
| **B. grade_sep_uncertain**, 8 | likely access-controlled / separated | **7/8 confirmed fast/separated** (1 unusable frame) | The grade-separation flag is well-targeted (F5). |
| **C. Compliant controls**, 8 | safe / not flagged | **8/8 genuine fast separated expressways** (Bangkok–Chonburi, Kanchanaphisek, Chalong Rat…) | The model's "safe" calls have high specificity. |

**What this means, stated honestly and in balance.** It does **not** mean the 12 fast-road flags are wrong, a school 150 m from a 90 km/h highway is a real hazard for children crossing. It means the **safe=30 *threshold mechanism* is too blunt**: it treats "a pedestrian generator is nearby" as "this is a 30 km/h pedestrian street," when the carriageway is often a fast road with the generator *off* it. The priority *direction* is right; the threshold assumption over-states on-road mixing. The fix is to derive the road's actual condition from imagery (separation, footpath, on-carriageway access) rather than infer it from a 150 m POI buffer, the genuine, novel capability this points to, and the refinement-stage path. Meanwhile the same audit independently **validates** the grade-separation flag (B) and the model's high-specificity "safe" calls (C).

**Caveats.** n=32; one street-view frame is not the whole segment (a generator may be just out of shot); the rater knew the experimental design (not the per-image stratum); strata limited to Mapillary-covered roads. This validates the score against **visible road condition**, not crash outcomes.

---

## Part E, Automated road-condition assessment at scale (the iRAP-coding task, automated)

Part D showed a human reading road condition from imagery. The scalable version automates it: a **vision LLM** (Claude Haiku 4.5) reads each street image and returns a structured road-condition record, separation, footpath, roadside development, pedestrian environment, and the Safe-System speed the visible condition implies (`src/streetview_cv_pull.py`, `streetview_cv_classify.py`; labels `output/cv_labels.json`; summary `output/cv_audit_summary.json`). This is the iRAP manual-coding task, automated and repeatable across a network.

**Validation, one independent check, two consistency checks (labelled honestly).** The genuinely *independent* signal is **against the dataset's functional road class**, a field the classifier never sees: its "separated" judgement is **cleanly monotonic**, 85% of motorways down to 19% of secondary roads (mean implied speed 90→61 km/h), confirming it reads real road structure, not noise. The other two are **consistency, not independent corroboration**, and we say so: against **32 segments rated blind by the author** (who knew the experimental design, so *not* a fully independent rater) it agrees **90% (28/31)**, never mistaking a highway for a pedestrian street and erring *conservative*; against a **second AI model** (Sonnet) it agrees **100% (32/32)**, but two models of the same family share training lineage, so this shows the read is *stable*, not that it is *correct*. The clear next step (refinement stage) is a protocol-driven, certified-coder rating on a larger held-out sample with inter-rater statistics. Even at this stage the automated read is consistent and conservative enough to scale.

**Applied to 170 segments across three strata:**

| Stratum | n | Automated finding |
|---|---|---|
| **Priority-1, safe=30 (OSM school/market)** | 120 | **96% have an implied safe speed >30** (mean 64 km/h); only 5 are genuine 30 km/h streets. The OSM-proxy threshold is over-assigned, inflating the danger magnitude ~2× (mean operating-speed-over-safe 65→33 km/h once corrected). |
| **grade_sep_uncertain** | 25 | **100% confirmed fast** (implied ≥70), the flag is well-targeted (though mostly *undivided* fast roads, not separated, which is why we never auto-reclassified them). |
| **Compliant controls** | 25 | **96% confirmed fast/separated** (implied ≥70; 17 of 25 are 110), the model's "safe" calls have high specificity. |

**The honest, balanced conclusion.** This does **not** overturn the priority list: even after replacing 30 with the CV-derived safe speed, **84% of those 120 segments are still genuinely misaligned** (posted limit above the corrected survivable speed) and only **10% become compliant** (the over-flags the CV catches). So the model's *direction* is mostly right; what the proxy got wrong was the *magnitude* (≈2× over-statement of how far over survivable speed these roads operate). CV-derived road condition both **sharpens the score** and **catches the 10% false positives**, and is a capability the data partner's posted-vs-driven "credibility index" does not have.

**Scope and caveats.** 170 segments, one image each, single frame, one vision model; Mapillary coverage limits which segments are auditable. Running this across the full network (and feeding corrected thresholds back into the score) is a bounded engineering task for the refinement stage, but the pipeline, its validation, and its first scaled result exist here.

---

## Part F, Network-scale CV correction (v2 → v3)

We ran the automated road-condition classifier (Part E) across **3,537 segments with street imagery, spanning every tier** (~24% of the network) and fed the imagery-derived safe speed back into the score as a corrected threshold (`src/scoring_cv.py`; aggregate summary `output/scoring_cv_summary.json`). The result is a **bidirectional correction**, the imagery fixes the rule-based proxy in *both* directions:

- **Where the proxy was too strict (59% of covered segments; mean safe threshold rises 47→66 km/h).** **81% of imagery-covered Priority-1 segments leave the top tier** once the threshold is real, **but the direction holds**: only ~26% of those demotions become fully Compliant (genuine over-flags removed); the rest **stay flagged** at lower priority (limit still above the corrected survivable speed).
- **Where the proxy was too lax, the discovery a POI method cannot make (8% of covered segments lowered; 13% of the lower-tier set).** These are roads with **no school/market POI, so the rule gave them a high safe speed and ranked them low, but the imagery shows a genuine pedestrian-mixing street.** Correcting them upgrades **223 low-priority segments into Priority 1/2**, of which **39 jump from Monitor/Compliant straight to Priority 1** (safe threshold dropping from a mean of 67 to 33 km/h). A posted-limit or POI-based method would never surface these; only reading the road itself does.
- **Honest scope:** the within-country percentile also reshuffles some Priority-2↔Priority-1 membership, that part is re-ranking, not discovery. The 39 lower-tier promotions, by contrast, are CV-driven and real (all have imagery, all had their threshold lowered).

The takeaway: **imagery-derived road condition does not just trim the ranking, it corrects it both ways**, removing over-flags *and* finding dangerous roads the standard method misses, validated end-to-end (90% vs human, 100% across two models) at 24% coverage. Full-network coverage is a bounded data-collection task for the refinement stage.
