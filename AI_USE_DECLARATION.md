# AI use declaration

**SpeedTruth — ADB AI for Safer Roads Innovation Challenge, Phase 2**

The Phase 1 technical review asked that the declaration made for the vision model
"continue in Phase 2". This document is that declaration.

Every figure quoted below can be recomputed with `python reproduce.py`, which needs no
API key and none of the restricted challenge data.

---

## 1. In the analytical pipeline

One AI model produces output that feeds the published Speed Safety Score. Software tools
were also used in implementation and in searching for sources; they produce no figure in
the published score, and every published figure is recomputed independently by
`reproduce.py`.

**Street-imagery classification — `claude-haiku-4-5-20251001`**

| | |
|---|---|
| Where | `src/imagery_cv_classify.py`; model set by the `CV_MODEL` environment variable, the identifier above is the default |
| Task | Read one street-level image per road segment and report the visible road context (vulnerable road users mixing with traffic, physical separation, road standard) |
| Input | Mapillary imagery only, pulled via the Mapillary Graph API in `src/imagery_pull.py` |
| Coverage | 3,537 of 14,711 segments (24% of the network), **one image per segment** |
| Effect on the published score | The imagery reading moved 1,736 segments to a different severity band: **1,552 to a less severe band and 184 to a more severe one**. Net change in Critical: **−1,112** |

**How its output was checked.** Two independent tests, both committed:

- **Blind test** (`src/imagery_blindtest.py`, results in `output/blindtest_results.json`).
  16 Priority-1 and 8 Compliant segments, the Compliant controls deliberately chosen as
  the highest-traffic ones so they were hard cases rather than empty rural lanes. Images
  were saved under anonymised, shuffled filenames and the score key was withheld until
  after rating. Agreement **19 of 24 (79%)**; sensitivity 75%, specificity 88%.
- **Road-condition audit** (`src/imagery_roadaudit.py`, results in `output/cv_validation.json`),
  32 segments, checked for consistency against a human rating and, independently, against
  functional road class — a field the model never saw.

**What that evidence does and does not support.** One frame per segment, and the sample
sizes above are modest. These checks support the *direction* of the imagery correction.
They do not establish its precision, and the report should not be read as if they did.

**Not used: Google Street View.** Feature extraction is not permitted under its terms. The
`StreetImageLink` field in the challenge data is used as a coordinate only; no imagery
behind it is ingested. The Phase 1 reviewer independently confirmed that the modules whose
names then read `streetview` (legacy naming, since corrected) call the Mapillary API.

---

## 2. Simulated stakeholder review, before submission

Ahead of submission the work was put through a **simulated stakeholder review**: several
external AI models were prompted to read a redacted package in the role of different
readers this proposal would meet — a road-safety engineer, a funding body, a national
road authority — and to raise the objections each of them would raise. Two rounds were
run: three reviews of the Phase 1 submission, then two of a revised one.

The models used in that exercise were **GPT, Grok and Gemini**.

**What was taken from it, and what was not.** The scoring scale those reviews applied, and
the threshold for "advance", were set by the author for that exercise alone. They are not
ADB's evaluation criteria and no score from them appears anywhere as an external
judgement. What was used is the list of objections the reviews converged on — chiefly
that this work has no crash-outcome validation and cannot obtain one from the data
provided. That limitation is stated in `METHODOLOGY.md` and has not been argued away.

---

## 3. Deliberately not used

- **Google Street View imagery**, for the licensing reason above.
- **Invented coefficients.** Where the literature has no value — there is no published
  survivable-speed threshold for a three-wheeler *occupant*, and no validated conversion
  from fleet composition to an adjusted threshold — no multiplier was created to fill the
  gap. The absence is reported instead. See `METHODOLOGY.md`.

---

## 4. How to check any of this

```bash
python reproduce.py            # recompute every published figure from committed outputs
python reproduce.py --chain    # print the upstream pipeline, stage by stage
```

`reproduce.py` reads only the committed outputs in `output/`. It needs no credentials and
none of the FDUA-restricted source data, so a reviewer can run it. What it cannot do is
re-derive the scores from the raw challenge data: that chain needs the restricted data, a
Mapillary token and a vision-model key. `--chain` prints that path so it is at least
unambiguous which stage produced which file.
