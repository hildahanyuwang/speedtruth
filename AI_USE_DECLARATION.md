# AI use declaration

**SpeedTruth — ADB AI for Safer Roads Innovation Challenge, Phase 2**

The Phase 1 technical review asked that the vision-model declaration "continue in Phase 2
alongside a declaration of any other tools used". This document is that declaration.

---

## The model in the pipeline

**Street-imagery classification — `claude-haiku-4-5-20251001`**

| | |
|---|---|
| Where | `src/imagery_cv_classify.py`; model set by the `CV_MODEL` environment variable, the identifier above is the default |
| Task | Read one street-level image per road segment and report the visible road context (vulnerable road users mixing with traffic, physical separation, road standard) |
| Input | Mapillary imagery only, pulled via the Mapillary Graph API in `src/imagery_pull.py`. **No Google Street View**: feature extraction is not permitted under its terms, and the `StreetImageLink` field is used as a coordinate only |
| Coverage | 3,537 of 14,711 segments (24% of the network), **one image per segment** |
| Effect on the published score | Moved 1,736 segments to a different severity band: **1,552 to a less severe band and 184 to a more severe one**. Net change in Critical: **−1,112** |

**Two validations, both in the repository.** A **blind test** (`src/imagery_blindtest.py`,
`output/blindtest_summary.json`): 16 Priority-1 and 8 Compliant segments, controls chosen
as the highest-traffic ones so they were hard cases, images shuffled and anonymised, score
key withheld until after rating. Agreement **19 of 24 (79%)**. And a **road-condition
audit** (`src/imagery_roadaudit.py`, `output/roadaudit_summary.json` and
`output/cv_audit_summary.json`) over 32 segments, checked against a human rating and,
independently, against functional road class, a field the model never saw. The rated
images are committed as well. The per-image result files are not: each row carries that
segment's posted limit and observed speed, so they are kept local under the Fair Data Use
Agreement.

One frame per segment, and both samples are small. This supports the *direction* of the
imagery correction, not its precision.

---

## Any other tools

Software tools assisted implementation and source search. **No output from them reaches a
published figure**; every published figure is recomputed from the committed outputs by
`python reproduce.py`.

Before submitting, several general-purpose AI models (GPT, Grok and Gemini) were prompted
to read a redacted package as the different readers this proposal would meet, and to raise
the objections each would raise. Nothing from that exercise enters the pipeline or the
published figures.

The research question, the analytical choices, and the primary sources are the author's.
The Royal Gazette originals behind the legal chapters could not be retrieved
programmatically; they were located and downloaded by hand and read page by page.
