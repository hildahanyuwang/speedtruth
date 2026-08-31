# SpeedTruth, Path to Ministry Adoption

> **Terminology note (Phase 2, 2026-08).** This document is the Phase 1 record and its
> wording is unchanged. Two **priority-tier** labels were renamed for the Phase 2 application:
> `Monitor` → **`Watch`**, and `Compliant` → **`Lower priority`**. The rename applies to the
> *within-region priority* axis only. The **severity** axis keeps its own four values
> (`Critical` / `Serious` / `Marginal` / `Compliant`), where `Compliant` is the correct word:
> operating speed at or below the survivable speed. Reason for the change, and every other
> change made since Phase 1, are recorded in `CHANGELOG_PHASE2.md`.

*An honest map of what stands between this submission and a transport ministry using it in practice. We state the gaps openly rather than imply the tool is deployment-ready.*

**Where it is today:** a validated, reproducible, FDUA-compliant analytical pipeline that turns standard probe + open data into a per-segment Speed Safety Score, an interactive decision map, a costed work-list, and an automated imagery-based road-condition check. It is a decision-support prototype, **not yet an operational system**.

## What a ministry needs before it can rely on this

| # | Missing piece | Why it's needed | When | Owner |
|---|---|---|---|---|
| 1 | **Posted-limit ground truth**, field-audit a stratified sample to calibrate the unvalidated limit field | The limit field is a commercial estimate; the model currently flags for *review*, not action | Refinement (weeks) | Team + ministry survey unit |
| 2 | **Outcome linkage**, corridor-level trauma admissions / insurance claims / police crash coordinates, pre-registered before testing | Converts the score from theoretical-risk to evidence-anchored; closes the validation gap | Refinement (weeks–months) | Ministry + health/insurance data owners |
| 3 | **Full-network imagery coverage**, fill Mapillary gaps (commissioned drive or dashcam programme) | Today ~24% of segments have imagery for the CV layer; the rest fall back to the proxy | Refinement | Team + ministry |
| 4 | **Certified-coder CV validation**, independent iRAP-trained raters on a statistically meaningful held-out sample, with inter-rater statistics | Lifts the road-condition layer from "consistency-checked" to professional-grade | Refinement | iRAP-style assessor |
| 5 | **Corridor aggregation, DELIVERED in this submission** (`CORRIDORS.md`): flagged segments clustered into contiguous same-road corridors; top 20% hold ~76% of benefit | Matches the unit of decision and budgeting | **Done** | Team |
| 6 | **GIS / workflow integration**, rebuild on ADB's GIS platform and export to the ministry's existing system; define the *standing limit-review mechanism* (trigger rules, ownership, review cadence) | Makes it a recurring process, not a one-off report | Finalist stage | Team + ADB + ministry |

## A credible 90-day path (if shortlisted)
1. **Weeks 1–3:** corridor aggregation; commission/secure one outcome proxy and pre-register the convergence test; recruit an independent CV coder.
2. **Weeks 4–8:** field-audit a limit-calibration sample; run the certified-coder validation; report the confusion matrix and failure modes.
3. **Weeks 9–12:** rebuild outputs on the ADB GIS platform; co-design the limit-review workflow with a ministry counterpart; deliver a corridor-level investment plan with local unit costs.

We are explicit that items 1, 2 and 4, the ones that would most change a funding decision, are **not** achievable in the application window and are the core of the refinement-stage work.
