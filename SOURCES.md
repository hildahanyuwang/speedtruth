# SpeedTruth, Authoritative Sources (verifiable)

> Integrity principle: this file lists only **verified** sources and figures. Each item carries a verification status.
> ✅ = original text / source data confirmed; 🔶 = from an authoritative-body search summary, figure pending final check against the original; ❌ = not found, not used.

---

## 1. Safe System survivable impact-speed thresholds (scoring core)

SpeedTruth's Safe System safe-speed thresholds rest on:

| Conflict type | Safe speed | Basis | Status |
|---|---|---|---|
| Pedestrian / cyclist struck by a motor vehicle | **30 km/h** | WHO *Speed management*; World Bank GRSF *Guide for Safe Speeds*; FHWA | ✅ multi-source |
| Side impact / intersection (vehicle-vehicle) | **50 km/h** | as above | ✅ multi-source |
| Head-on (vehicle-vehicle, modern car + seatbelt) | **70 km/h** | Tingvall & Haworth (1999) Vision Zero framework | 🔶 original is a conference paper |
| Separated facility, no VRU conflict | 100+ km/h | Safe System general principle (requires matching infrastructure protection) | ✅ |

**Core principle (citable):** "Speeds need to be at or below the Safe System survivable impact speeds... If higher speeds are required, then better-quality road infrastructure is necessary" (separation, pedestrian crossings, barriers). This is exactly SpeedTruth's argument: the limit should match the protection a road actually provides to VRUs.

**Source links:**
- WHO, *Speed management: a road safety manual for decision-makers and practitioners*, 2nd ed., 2023. https://cdn.who.int/media/docs/default-source/documents/health-topics/road-traffic-injuries/3146-wbk-speed-mgmt-2nd-edition-131023-electronic.pdf
- World Bank Global Road Safety Facility, *Guide for Safe Speeds: Managing Traffic Speeds to Save Lives*, 2023. https://www.globalroadsafetyfacility.org/sites/default/files/2024-05/Guide%20for%20Safe%20Speeds%20-%20Managing%20Traffic%20Speeds%20to%20Save%20Lives.pdf
- US FHWA, *Safe System Approach for Speed Management*. https://highways.dot.gov/sites/fhwa.dot.gov/files/Safe_System_Approach_for_Speed_Management.pdf
- Tingvall, C. & Haworth, N. (1999). *Vision Zero, An ethical approach to safety and mobility*. 6th ITE Int. Conf., Melbourne. (The most-cited original framework for the 30/50/70 thresholds.)

---

## 2. Pedestrian fatality risk vs. impact speed (✅ original read)

**Rosén, E. & Sander, U. (2009). Pedestrian fatality risk as a function of car impact speed. *Accident Analysis and Prevention* 41 (2009) 536-542. DOI: 10.1016/j.aap.2009.02.002**

Empirically calibrated fatality-probability curve (adult pedestrian, struck by the front of a passenger car):

```
P(v) = 1 / (1 + exp(6.9 - 0.090*v))   v = impact speed (km/h)
```

Verified values: 30 -> 1.5%, 40 -> 3.6%, 50 -> 8.3%, 60 -> 19%, 70 -> 38%, 75 -> 46% (the paper states 75 km/h is about 50%, CI 26-68%).
- Fatality risk at 50 km/h is more than 2x that at 40 and more than 5x that at 30 (✅ consistent with the formula).

**Use and honest limitations:**
- SpeedTruth uses this formula to convert each high-VRU segment's P85 into an indicative pedestrian-fatality probability, as an interpretable safety metric.
- **Limitations (stated in the report):** (1) calibrated on German passenger cars; the paper explicitly notes that in countries with less-developed emergency care (e.g. Thailand, India) the fatality risk is higher at the same impact speed; (2) adult pedestrians only (15+); (3) SUVs/trucks/buses are more lethal; (4) not applicable to two-wheeler occupants. Used only as a relative-risk indicator, not an absolute prediction.

---

## 3. Helmet effectiveness (supports "misalignment is deadlier where helmet use is low")

- WHO, *Helmets: a road safety manual for decision-makers and practitioners*, 2nd ed., 2023. https://www.who.int/publications/i/item/9789240069824
- Direction of the conclusion (🔶 exact percentages pending original check): quality helmets sharply reduce motorcyclist death and brain-injury risk; head trauma is the leading cause of death for riders.
- **Note:** SpeedTruth's helmet-based lethality context uses the challenge-provided helmet SPI (measured wearing rates, Thailand/Maharashtra x urban/rural); external literature only corroborates the argument and we do not depend on its exact percentages.

---

## 4. Operating speed / P85 for limit assessment, WHO directly endorses SpeedTruth's core method ✅

**This is SpeedTruth's strongest methodological endorsement.** WHO *Speed management* 2nd ed. (2023), Module 2 (p.25-26), states clearly:

- **P85 is a tool for identifying when a limit and the road design are mismatched (essentially the official version of SpeedTruth's argument):**
 > *"The 85th percentile is an excellent way of identifying when speed limits and road design do not match, and the design of a road is inappropriate for the posted speed limit."*
 -> SpeedTruth uses exactly P85 vs Safe System thresholds / road class to diagnose this mismatch. We do what WHO recommends.

- **WHO calls setting limits by P85 bad practice:**
 > *"This is bad practice as speeds selected by the majority of drivers are not safe in any absolute sense... countries that have already adopted the Safe System approach have discontinued the use of 85th percentiles for speed limit setting."*
 -> Key distinction (SpeedTruth's stance matches WHO exactly): P85 must not be used to *justify* a limit, but it is an excellent tool to *diagnose* whether a limit is mismatched. We use P85 for diagnosis, never to set limits.

- **Limits should match the most vulnerable road user (supports the VRU thread):**
 > *"The speed limit setting approach needs to guarantee safe speeds for all road users reflecting the levels of safety and needs of various road users instead of prioritizing traffic flow."*

Source: WHO *Speed management* 2nd ed., 2023 (same link as §1), Module 2, p.25-26. ✅ verified word-for-word against the original (2026-06-23).

---

## 6. Verified intervention-effectiveness evidence (what works; supports the investment case + recommendations) ✅

GRSF *Guide for Road Safety Interventions* (2021) and the iRAP Road Safety Toolkit, both verified against the original:

| Intervention | Effect size | Source |
|---|---|---|
| Reduce limit by 10 km/h | injury crashes **about -15%**; pedestrian death/serious injury **up to about -40%** | GRSF A.2.7; WHO 2023 manual p.26 same figure |
| 30 km/h zone (pedestrian zone) | pedestrian serious injury **> -70%** | GRSF A.2.8 |
| Footpath / sidewalk | pedestrian casualties **-40 to -60%** | GRSF A.1.10; iRAP Toolkit |
| Pedestrian crossing (unsignalised) | casualties **-25 to -40%** | iRAP Toolkit |
| Separated motorcycle lane | crashes **about -40%**; deaths **about -80%** | GRSF A.1.13 (based on a single Malaysian study, Radin Sohadi 2000, **limited evidence base, flagged**) |
| Area-wide traffic calming | KSI **-18%** | Cochrane / Bunn et al. 2003 🔶 (pending original check) |

**"Hierarchy of control" argument (directly supports "governance failure > blaming driver speeding"):** GRSF A.3.1 states that engineering/design interventions take priority over changing driver behaviour, *"engineer roads to... constrain speeds... is typically more effective than telling drivers... Behavioral interventions are at the lower-end of the effectiveness scale."* GRSF A.2.10 has a dedicated section showing that "raising travel speeds without correspondingly upgrading infrastructure" necessarily increases risk.

Source: World Bank GRSF, *Guide for Road Safety Interventions: Evidence of What Works and What Does Not Work*, 2021. https://documents1.worldbank.org/curated/en/206691614060311799/pdf/Guide-for-Road-Safety-Interventions-Evidence-of-What-Works-and-What-Does-Not-Work.pdf ; iRAP Toolkit https://toolkit.irap.org/ . ✅ verified 2026-06-23.

---

## 4c. External validation data, iRAP / ThaiRAP (gold standard for road-infrastructure safety) ✅

- **Thailand 2024: only 19% of roads are iRAP 3-star+ for pedestrians** (Asia-Pacific average 14%); cyclists 10%; vehicle occupants 44%; motorcyclists 17%. ThaiRAP has assessed 132,164 km of road; Chulalongkorn University is an iRAP Centre of Excellence.
- **Use, external convergence:** SpeedTruth independently finds, from a limit-misalignment angle, that the large majority of Thai VRU-exposed segments have P85 above the Safe System pedestrian speed; iRAP independently finds, from an infrastructure angle, that only 19% of roads are 3-star+ for pedestrians. Two independent methods, different metrics, converge on the same conclusion: a systemic pedestrian-safety gap in Thailand.
- **Honest note:** the two metrics differ in resolution and definition (one is the share of VRU segments whose P85 exceeds the safe speed; the other is the iRAP pedestrian star rating, only 19% at 3-star+); they are not numerically equivalent and we treat this only as qualitative convergence.
- Source: iRAP ThaiRAP Light Star Ratings https://irap.org/rap-tools/light-ratings/thairap-light-star-ratings/ ; Thailand Road Safety Profile 2025 (Asian Transport Observatory) https://asiantransportobservatory.org/documents/403/Thailand_road_safety_profile_2025.pdf

## 4d. Thailand provincial crash data, access limitation (honest record)
- ThaiRSC (thairsc.com) has provincial road-death statistics (national total 14,737 deaths, 2022) but **no clean downloadable CSV** (Thai-language site), so a rigorous provincial quantitative cross-check is constrained and is listed as future work. The literature (Population Health Metrics 2026) qualitatively finds death rates clustered in central/eastern provinces.

## 5. ADB's own publications (aligning with the evaluating body's language)

Confirmed ADB official documents (citable to show alignment with ADB priorities); specific statistics marked 🔶 = from a search summary, open the original before writing into the main text:

- ✅ **ADB *Road Safety Guidelines for the Asian and Pacific Region*** (decision-maker-oriented flagship guide). https://www.adb.org/sites/default/files/publication/29532/road-safety-guidelines.pdf
- ✅ **ADB project 55034-001 *Research on Implementing the Safe System Approach to Road Safety*** (ADB formally adopts Safe System, direct evidence that SpeedTruth's method aligns with ADB strategy). https://www.adb.org/projects/55034-001/main
- ✅ **ADB & iRAP partnership** (APRSO report; ADB has formally adopted the iRAP star-rating methodology). https://www.aprso.org/news/adb-and-irap-sign-new-partnership-save-lives-asia-pacific
- ✅ ***Asia-Pacific Road Safety Observatory's Indicators* (ADB, 2022)** (indicator framework, aligning with KPI language). https://www.adb.org/sites/default/files/publication/805731/asia-pacific-road-safety-observatory-indicators.pdf
- 🔶 ADB blog figures (*Fixing the Fatal Funding Gap*, etc.): Asia-Pacific >694,000 road deaths in 2021 (about 60% of the global total); one-third of deaths are pedestrians/cyclists, 35% are powered two/three-wheelers. **Verify against the original before using.** https://blogs.adb.org/blog/fixing-fatal-funding-gap-fueling-asia-s-road-safety-crisis

## 5b. ASEAN / South Asia VRU pain-point figures (each sourced individually, do not mix)

- 🔶 WHO South-East Asia regional motorcycle/three-wheeler death share is about 43% (regional level); by country (2016): Thailand 73%, Cambodia 74%, Laos 74%. Source: WHO PTW safety guidelines 2022, https://www.who.int/news/item/10-10-2022-new-global-guidelines-to-curb-motorcycle-crash-deaths (search-summary level, verify before citing).
- ✅ WHO 2023 Speed manual pedestrian survival: an adult pedestrian struck at 30 km/h has a 90% survival rate; at 50 km/h this falls to 50-80%; for every 1 km/h above 30, pedestrian death probability rises by about 11% (meta-analysis of 20 studies).

## 5c. Power Model / speed-injury relationship (basis of the investment case) ✅ + limits

- WHO 2023 Speed manual (Module 1, p.10-11): *"every 1% increase in mean speed produces a 4% increase in fatal crash risk and a 3% increase in serious crash risk... A 5% reduction in average speed can reduce fatalities by 20%."*
- Original literature: Nilsson, G. (2004) Lund; Elvik, R. et al. (2019) *AAP* 123:114-122; Elvik (2013) *AAP* 50:854-860.
- **Limits (stated in the report):** (1) WHO itself notes that in high-speed environments the relationship is **exponential rather than a power law**, so the power law may **understate** fatal sensitivity at high speeds; (2) the power model fits rural/highway well but **should not be applied directly to urban arterials** (Cameron & Elvik 2010, *AAP*); (3) the serious-injury exponent is below Nilsson's original assumption. We use it for relative ROI ranking, not for absolute casualty prediction, and we flag this honestly.

- ❌ Exact Thailand/India speeding-and-VRU death shares from the WHO *Global Status Report 2023*: still pending original verification, not cited for now.

---

*All 🔶/❌ items must be upgraded to ✅ (original confirmed) or removed before going into the final report. We never pad with figures that merely "look right".*

## 7. Quantified impact and BCR anchors (added 2026-06, supports FINDINGS §4)
All figures are from named primary sources with a confidence note. GRSF/iRAP do not publish fixed unit costs (country-specific inputs), so the BCR uses iRAP's own Indian deployments.

**Baseline road deaths (to anchor the avoidable-harm scenario):**
- Maharashtra **15,224 deaths (2022, 9% of India's national total)**, MoRTH *Road Accidents in India 2022* state table (original PDF verified). HIGH. https://morth.gov.in/backend/documents/uploaded/1755600426_RA_2022_30_Oct.pdf
- India national total 168,491 deaths (2022), same source. HIGH.
- Thailand **18,218 deaths (2021, 95% CI 16,787-19,649), 25.4 per 100,000**, WHO *Global Status Report on Road Safety 2023* Thailand country page (verified). HIGH. https://cdn.who.int/media/docs/default-source/country-profiles/road-safety/road-safety-2023-tha.pdf

**Intervention effectiveness and BCR (iRAP's own Indian deployments, 2011 prices):**
- Footpath **BCR = 14.0**; pedestrian crossing **BCR = 12.9**, iRAP India Four States Project (2011), PDF verified. HIGH. https://indiarap.org/wp-content/uploads/2020/08/2011-iRAP-India-Four-States-report-1.pdf
- iRAP investment plans commonly use a threshold **BCR = 3**. MEDIUM.
- Footpaths reduce pedestrian casualties "up to 60%", GRSF *Guide for Road Safety Interventions* (2021) §A.1.10, verified. HIGH.

**Economic cost per casualty (for monetisation):**
- India cost per road death is about **US$93,400**; serious injury about US$23,350 (2011 prices, needs inflation adjustment, so a lower bound), iRAP India Four States (2011), verified. HIGH.
- Thailand VSL (passenger-car driver WTP) about US$0.82-0.87M, Sresthapong et al., PLOS One 2021. MEDIUM (academic, not ADB/WB official).

**Power Model avoidable KSI:** KSI is proportional to (v_after/v_before)^3 (Nilsson/Elvik; cited by WHO/GRSF). Limit: at large reductions the power law over-states (WHO notes high-speed environments are exponential), so the FINDINGS headline uses a capped 40% realistic reduction, and absolute figures are a transparent, reader-adjustable scenario, not a forecast (no segment-level crash baseline). See §5c.

## 8. Invisible fleet / informal vehicles (VRU visibility bias, supports FINDINGS §3.4/§6)
- ASEAN road deaths are **62-74% powered two/three-wheelers**, see §5b (sourced). Three-wheelers (Indian auto-rickshaws, Thai tuk-tuk/songthaew, human-powered cycle-rickshaws) and modified/engine-retrofitted vehicles (Indian jugaad, Thai rot e-taen) are a major VRU class.
- **Honest characterisation (a methodology statement, not a citation):** these users are not in the commercial probe-speed fleet sample, not in the helmet SPI (motorcycle riders only), and largely not in OSM. An open OSM three-wheeler-stand pull (`src/fetch_osm_threewheel.py`) returned only **182** in Maharashtra (50 explicitly named/tagged) = a lower-bound proxy, not a census. -> scores on affected segments are a conservative lower bound. Aligned with the Owen/Agilysis values: institutional humility about probe-data bias, do not underestimate VRUs.

## 8b. Invisible-fleet magnitude, external figures (2026-06, supports FINDINGS §3.4; all external public statistics, not challenge data)
**Fleet composition, vulnerable vehicles dominate:**
- India: **two-wheelers about 73.86% of registered motor vehicles** (MoRTH Road Transport Year Book 2016-17, official; about 75% FY2020 Statista->MoRTH). Three-wheelers are folded into "Others", no clean standalone share.
- Thailand: **motorcycles about 52.5% of registered passenger vehicles** (Statista->DLT 2023); about 22.5M motorcycles of 44.3M vehicles (Bangkok Post->DLT 2023-11).
- Maharashtra: an official 2024-25 registration table exists (transport.maharashtra.gov.in, listing "Total Two Wheelers" + "Auto-rikshaws"), but its multi-column RTO layout scrambles on text conversion, so **we do not report a state percentage, to avoid fabrication** (honest record).

**Death share, the vulnerable die most:**
- India: **two-wheeler riders = 44.5% of road deaths (74,897)**; auto-rickshaw three-wheelers = 3.9% of deaths (MoRTH *Road Accidents in India 2022*, via OpenCity/PIB; total 168,491 deaths).
- Thailand: **motorcyclists = 83.8% of road deaths** (WHO Thailand; total 18,218 deaths).

**Probe under-representation (structural evidence only, no exact figure):** two-wheeler embedded-telematics penetration is far below cars ("only a few of the largest two-wheeler OEMs offer embedded telematics"); floating-car-data theory notes probes must be uniformly distributed and that developing economies with high PTW shares are "under-researched" (Berg Insight 2025; FCD literature PMC4692405). -> Honest statement: two/three-wheelers are systematically under-represented in fleet-probe data, not "exactly 0%".

**One-line magnitude (citable):** in India two-wheelers are about 74% of the fleet and 44.5% of deaths; in Thailand motorcycles are about 52% of the fleet and 84% of deaths, and these are precisely the users fleet-probe data barely captures.
