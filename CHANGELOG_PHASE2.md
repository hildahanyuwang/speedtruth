# Changelog — Phase 2

Every change made to this project after the Phase 1 submission, what prompted it, and where
it landed. Phase 1 documents are kept as they were reviewed; where their wording is now out
of step with the application, this file is the reconciliation, not a silent edit.

Phase 2 Step 3 asks entrants to act on the technical review. The rows below marked
**[review]** cite the reviewer's own words.

---

## 2026-08-13

### 1. `streetview` naming removed throughout **[review]**

> *"The naming is legacy and could be misread. I verified you are calling the Mapillary API
> and there is no GSV."*

The reviewer had to check this by hand. That is one check too many, so the ambiguity is gone:

| Was | Now |
|---|---|
| `STREETVIEW_VERIFICATION.md` | `IMAGERY_VERIFICATION.md` |
| `src/streetview.py` | `src/verification_shortlist.py` |
| `src/streetview_cv_pull{,_full,_lower}.py` | `src/imagery_cv_pull{,_full,_lower}.py` |
| `src/streetview_cv_classify.py` | `src/imagery_cv_classify.py` |
| `src/streetview_blindtest.py` | `src/imagery_blindtest.py` |
| `src/streetview_roadaudit.py` | `src/imagery_roadaudit.py` |
| `_dev_scripts/download_streetview.py` | `_dev_scripts/download_imagery.py` |
| `output/streetview_images/` | `output/imagery_samples/` |
| prose: "street-view review", "blind street-view test", "Street view shows…" | "street-level imagery review", "blind imagery test", "The imagery shows…" |

### 2. The Google Street View boundary, stated instead of implied

Renaming alone would have hidden a real distinction. The precise position, which anyone can
check in the code:

- **Every image this pipeline ingests comes from Mapillary** (`graph.mapillary.com`, CC BY-SA).
  That is the only imagery the vision model is ever shown —
  `imagery_cv_pull*.py`, `imagery_cv_classify.py`, `imagery_blindtest.py`, `imagery_roadaudit.py`,
  `_dev_scripts/download_imagery.py`.
- **`src/verification_shortlist.py` emits Google Maps URL strings and nothing else.** It
  downloads no image, calls no Google API, and extracts no feature. The links exist so a
  human can open a panorama and look at the road. This is why the file was renamed away
  from `streetview.py`: it is a shortlist for human verification, not an imagery pipeline.
- **Google Street View imagery is never ingested**, because its terms forbid feature
  extraction. This is now written into the module docstring rather than left to inference.
- The ADB-supplied `StreetImageLink` field is a lon/lat string. We use it as a coordinate
  only; `DATA_INVENTORY.md` now says so explicitly.

### 3. Priority-tier labels renamed

Decided 2026-08-10. The rename covers the **within-region priority** axis only:

| Old (Phase 1) | New |
|---|---|
| Priority 1 | Priority 1 |
| Priority 2 | Priority 2 |
| **Monitor** | **Watch** |
| **Compliant** | **Lower priority** |

Two reasons. `Compliant` was simply the wrong word for "bottom half of the within-region
ranking". And under the two-axis design a segment can legitimately read `severity = Critical`
and `priority = Compliant` at the same time, which is correct but reads as a contradiction to
a non-technical reader.

**The severity axis is unchanged** — `Critical` / `Serious` / `Marginal` / `Compliant` — where
`Compliant` is the right word: operating speed at or below the survivable speed.

Applied in: `src/scoring.py`, `src/scoring_cv.py`, `src/make_map.py`, `src/evaluate.py`,
`src/sensitivity_samplesize.py`, the imagery scripts that filter on tier, and
`_dev_scripts/prepare_egis_uploads.py` (which relabels Phase 1 outputs on export, so the
published layers carry the product vocabulary without re-running the whole pipeline).
Phase 1 documents carry a terminology note instead of rewritten text.

### 4. Headline figure reconciled to the imagery-corrected count

`index.html` said **5,973** segments at Critical severity. That is the rule-based score
**before** the imagery correction. The layers published to ArcGIS Online carry the corrected
`severity`, which gives **4,861** (Thailand 4,652 + Maharashtra 209). A judge filtering
`severity = Critical` on the map would have got a different number from the one in the text.

The application uses the **corrected** figure. 5,973 remains meaningful as the "before"
value, and the gap between them is the point, not an embarrassment: see item 5.

### 5. Wording brought down to what the evidence carries **[review]**

> *"The headline numbers are stated quite loudly rather than the caveats… it just needs a bit
> more re-framing."*

This was the review's only named weakness. Changes on the front page:

> **Amended 25 September 2026.** "The front page" here meant `index.html`, the page the
> Phase 1 submission opened on. `README.md` was missed, and carried both of the first two
> wordings below for another seven weeks. Phase 2 submits the repository URL, which means
> `README.md` is now the page a reader opens first, so the same two changes have been made
> there, along with the stability claim in item 5b. The entry is amended rather than
> rewritten, because a changelog that quietly becomes true is not a changelog.

- **"iRAP-style road-condition coding" → dropped.** The reviewer asked for it, and iRAP
  released Star Rating Model v3.10 in May 2026; describing our work as "iRAP-style" while
  not implementing v3.10 would mislead anyone who knows the model.
- **"90% agreement… the model's 'safe' calls are reliable" → replaced.** The blind test
  agreed on 19 of 24 segments (79%). The sample is small and each segment is judged from a
  single frame, so it now says the evidence supports the **direction** of the correction, not
  its precision — and states that imagery covers ~24% of the network, in the same breath.
- **"~13–14× benefit-cost" removed from the four headline numbers.** It is drawn from
  published intervention studies, not an economic evaluation of these roads. It survives on
  the corridor card with that qualifier attached.
- **The fourth headline number is now 1,736** — the count of segments the imagery re-banded,
  roughly half of those it covered, with the net movement downward. It replaces a number that
  overstated with one that shows the model correcting itself.

### 6. One command that recomputes every published number — `reproduce.py` **[review]**

> *"The pipeline was not re-executed for this review. The assessment is based on code
> inspection and the committed outputs… The specific verification figures were not
> independently reproduced."*
> *"…could be replaced with a single top level script that regenerates exactly the
> report's numbers."*

```
python reproduce.py
```

Recomputes 22 published figures from the committed outputs, checks each against the
value that was actually published, prints where each one appears, and exits non-zero if
any has drifted. **It needs no API keys and none of the FDUA-restricted data**, which is
the point: a reviewer has to be able to run it. `--chain` prints the upstream pipeline,
stage by stage, including the stages a third party cannot run and why.

Current state: **22 figures checked, 0 mismatched.**

Two things the script recomputes that are worth stating outright, because both cut
against a more flattering reading:

- **The imagery correction cannot change how many segments are Priority 1** (1,473 before,
  1,473 after) because the priority tier is a within-region percentile rank. It changes
  *which* segments — 1,090 entered or left. Absolute severity is where the correction
  actually shows.
- **Of the 1,736 segments the imagery moved, 1,552 moved to a less severe band and 184 to
  a more severe one.** The correction mostly found our own rule too harsh. It did not
  mostly uncover hidden danger.

### 7. Three near-duplicate imagery pull scripts merged into one **[review]**

> *"The number of near duplicate street imagery pull scripts suggests the exploratory
> history has been committed alongside the pipeline. You could use a single parameterised
> entry point which would make the reproduction path unambiguous."*

`imagery_cv_pull.py`, `imagery_cv_pull_full.py` and `imagery_cv_pull_lower.py` differed
only in which segments they sampled; the fetch loop, the manifest record and the rate
limiting were copy-pasted between them. They are now one script:

```
MLY_TOKEN=... python src/imagery_pull.py --scope {stratified|priority|lower}
```

Each scope's sampling frame is preserved exactly — verified against the superseded
scripts: `stratified` 600/200/300 candidate pools, `priority` 3,679 Priority-1/2 plus a
1,500 lower-tier sample, `lower` the 4,000 busiest lower-tier segments.

**One defect fixed in the merge.** The superseded `_full` script numbered new images with
`len(manifest)`. Whenever the manifest was not contiguous — any interrupted or pruned run —
that reuses an existing index and silently overwrites an image already pulled. The merged
script takes the highest existing index plus one, which is identical when nothing is
missing and safe when something is.

---

## What has not changed, deliberately

- **Phase 1 deliverables keep their reviewed wording.** `FINDINGS`, `METHODOLOGY`,
  `IMAGERY_VERIFICATION` and `ADOPTION` carry a terminology note pointing here. Rewriting the
  record that was assessed would destroy the audit trail this project is built on.
- **The process log is untouched.** `PROGRESS.md`, `RESUME_HERE.md` and `_process_records/`
  record what was believed at the time, including what later turned out to be wrong.
- **Safe System thresholds are applied as a contextual overlay, not a per-segment multiplier.**
  The reviewer praised this specifically; the deepening asked for is in the evidence base,
  not the design.
