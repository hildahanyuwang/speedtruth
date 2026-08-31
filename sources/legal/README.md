# Legal instruments cited in this submission

Primary sources for the chapter on **who can lawfully change a speed limit**. Every legal
claim made in the report is traceable to a document in this folder.

**Why these files are committed.** Two of the official portals involved are not reliably
reachable from every network: the Thai Royal Gazette site sits behind a Cloudflare
challenge, and several Indian government domains time out from some regions. A reviewer
who cannot open the source URL can still open the file. **The official URL is given for
every item so the copy can be checked against the original.**

**These are not challenge data.** Every file here is a statute, a ministerial regulation, a
government gazette notice, a departmental manual or a published journal article, issued
publicly by the state concerned or by an academic publisher. They fall outside the FDUA
restrictions that apply to the challenge dataset. The repository's `.gitignore` ignores
`*.pdf` globally for that reason; a narrow exception (`!sources/legal/**/*.pdf`) admits
this folder and nothing else.

**Naming.** Files were renamed from the download identifiers used by the source portals,
because those identifiers are not self-describing. **The original filename is recorded for
every item below** — it is the key back to the source portal's record.

---

## Thailand

Gazette citations follow the convention *Royal Thai Government Gazette*, Volume, Part,
page, date. Thai years are Buddhist Era (B.E.); the Gregorian year is given in brackets.
Note that the **signing date and the publication date differ** and are listed separately
where both are known.

| File | Instrument | Gazette | Original filename | Source |
|---|---|---|---|---|
| `TH_LandTrafficAct_BE2522_consolidated.pdf` | **Land Traffic Act B.E. 2522 (1979)**, consolidated text, Office of the Council of State. §139 at pp. 34–35 | — | `LandTrafficAct_2522_RoyalThaiPolice.pdf` | royalthaipolice.go.th/downloads/laws/laws_03.pdf |
| `TH_LandTrafficAct_Amendment13_BE2565.pdf` | **Land Traffic Act (No. 13) B.E. 2565 (2022)** | Vol. 139, Part 28 Kor, p. 5 (7 May 2022) | `17206117.pdf` | ratchakitcha.soc.go.th |
| `TH_MinReg_HighwaySpeed_BE2564_A.pdf` | **Ministerial Regulation Prescribing Vehicle Speeds on Designated National or Rural Highways B.E. 2564 (2021)**. Issued by the Minister of Transport under s.5(1), Highway Act B.E. 2535. Signed 4 Mar 2021 | Vol. 138, Part 17 Kor, p. 3 (10 March 2021) | `T_0003.pdf` | ratchakitcha.soc.go.th |
| `TH_MinReg_GeneralSpeed_BE2564_B.pdf` | **Ministerial Regulation Prescribing Speeds for Driving on Roadways B.E. 2564 (2021)**. Issued by the Prime Minister under s.5 para.1 and s.67 para.1, Land Traffic Act B.E. 2522. Signed 27 Oct 2021; in force 240 days after publication | Vol. 138, Part 77 Kor, p. 1 (23 November 2021) | `17188002.pdf` | ratchakitcha.soc.go.th |
| `TH_DirHighways_SpeedRoutes_No1_BE2564.pdf` | **Notification of the Director of National Highways on Designated Routes for Vehicle Speeds (No. 1)**. In force 1 Apr 2021 | Vol. 138, Special Part 69 Ngor, p. 50 (26 March 2021) | `T_0050.pdf` | ratchakitcha.soc.go.th |
| `TH_DirHighways_SpeedRoutes_No2_BE2564.pdf` | *ibid.* **(No. 2)**. In force 1 Sep 2021 | Vol. 138, Special Part 194 Ngor, p. 18 (23 August 2021) | `17175303.pdf` | ratchakitcha.soc.go.th |
| `TH_DirHighways_SpeedRoutes_No3_BE2565.pdf` | *ibid.* **(No. 3)**. In force 1 May 2022 | Vol. 139, Special Part 96 Ngor, p. 15 (27 April 2022) | `17204876.pdf` | ratchakitcha.soc.go.th |
| `TH_DirHighways_SpeedRoutes_No4_BE2566.pdf` | *ibid.* **(No. 4)**. In force 1 Jul 2023 | Vol. 140, Special Part 150 Ngor, p. 33 (26 June 2023) | `140D150S0000000003300.pdf` | ratchakitcha.soc.go.th |
| `TH_BKK_SpeedOrder_BE2567.pdf` | **Regulation of the Head of Traffic Officers in the Bangkok Metropolis on Speed Limits and Prohibition of Horn Use B.E. 2567 (2024)**. Issued under ss.4(38), 139(6) and 139(20), Land Traffic Act B.E. 2522. Signed 6 Dec 2024; in force 24 Dec 2024 | Vol. 141, Special Part 352 Ngor, p. 44 (23 December 2024) | `54027.pdf` | ratchakitcha.soc.go.th |
| `TH_BKK_SpeedOrder_BE2561.pdf` | **Regulation of Traffic Officers in the Bangkok Metropolis on Prescribing Vehicle Speeds B.E. 2561 (2018)**. Issued under s.139(6). Signed 16 Jan 2018 | Vol. 135, Special Part 33 Ngor, p. 58 (14 February 2018) | `2133438.pdf` | ratchakitcha.soc.go.th |
| `TH_Phatthalung_SpeedOrder_BE2561.pdf` | **Regulation of Traffic Officers of Phatthalung Province on Prescribing Vehicle Speeds within the rates fixed by ministerial regulation B.E. 2561 (2018)** | Vol. 135, Special Part 38 Ngor, p. 32 (20 February 2018) | `2133885.pdf` | ratchakitcha.soc.go.th |
| `TH_Pattani_SpeedOrder_BE2561.pdf` | **Regulation of Traffic Officers of Pattani Province…B.E. 2561 (2018)**. Issued under ss.139(6) and 139(15). Signed 15 Mar 2018 | Vol. 135, Special Part 80 Ngor, p. 22 (5 April 2018) | `2137211.pdf` | ratchakitcha.soc.go.th |

## India

| File | Instrument | Original filename | Source |
|---|---|---|---|
| `IN_MotorVehiclesAct_1988.pdf` | **Motor Vehicles Act, 1988 (Act 59 of 1988)**. s.112 "Limits of speed" at pp. 65–66 | `MotorVehiclesAct_1988_IndiaCode_a1988-59.pdf` | indiacode.nic.in/bitstream/123456789/9460/1/a1988-59.pdf |
| `IN_MH_MVDept_Manual_PartIII.pdf` | **Government of Maharashtra, Motor Vehicles Department Manual, Part III**, §8.1 "Limits of speed (MVA S 112)" | `MH_MVDept_Manual_PartIII_ControlOfTraffic.pdf` | transport.maharashtra.gov.in/Site/Upload/GR/CONTROL_OF_TRAFFIC.pdf |
| `IN_SO1522E_MaxSpeed_2018.pdf` | **S.O. 1522(E)**, Ministry of Road Transport and Highways, dated 6 April 2018, fixing maximum speeds by road class and vehicle category under the proviso to s.112(1). Supersedes S.O. 1997(E) of 5 August 2014. File no. RT-11028/07/2017-MVL. *Gazette of India*, Extraordinary, Part II, Section 3, Sub-section (ii), No. 1377. Clause 2 provides that no cognizance is taken under s.183 if the detected speed is within 5 per cent of the maximum | `184582.pdf` | egazette.nic.in |
| `IN_Mumbai_AddlCP_CoastalRoad_Notif187_2026.pdf` | **Notification No. 187/Addl CP/Traffic/Permanent/2026**, Additional Commissioner of Police (Traffic), Mumbai, 25 August 2026 (Marathi). Issued under s.115 of the Motor Vehicles Act 1988 and Government of Maharashtra notification MVA 0589/CR-1061/TRA-2 dated 11 May 1990, as amended 27 September 1996 | `202608250000_823227_Costal Road  permanent Notification -187_1.pdf` | trafficpolicemumbai.maharashtra.gov.in |

## Academic

| File | Reference |
|---|---|
| `Mubiru_Evdorides_2026_FutureTransp_6-1-29.pdf` | Mubiru, J., & Evdorides, H. (2026). Pedestrian safety in developing countries: A systematic literature review and gap analysis. *Future Transportation*, 6(1), 29. https://doi.org/10.3390/futuretransp6010029 |

---

## Sources cited but not reproduced here

| Source | Why not included | Where to verify |
|---|---|---|
| **Speed Variation Analysis**, World Bank, 2019 | Publicly hosted; no redistribution needed | hdl.handle.net/10986/33097 |
| **Government of Maharashtra notification MVA 0589/CR-1061/TRA-2** (11 May 1990, amended 27 Sep 1996) — the instrument delegating traffic powers to the Mumbai police | Not retrieved. Its number is known only because the Mumbai notification above cites it | Maharashtra Government Gazette |

---

## Key pages, viewable without downloading anything

GitHub cannot preview most of these PDFs — it reports "Unable to render code block". That
is a limitation of the in-page viewer, not a damaged file: these are scans, or they use
embedded subset fonts the viewer cannot handle. **Downloading any of them works.**

So that the operative wording can be read in the browser, `excerpts/` holds the single
page of each document that carries the provision this submission relies on:

| Page image | What is on it |
|---|---|
| [`TH_MinReg_HighwaySpeed_BE2564_A__p1_conditions_and_three_wheeler.png`](excerpts/TH_MinReg_HighwaySpeed_BE2564_A__p1_conditions_and_three_wheeler.png) | The three conditions a road must meet before 120 km/h may apply — two or more lanes each way, a barrier median, no at-grade U-turns — and clause 3(2), which sets **65 km/h for three-wheelers** |
| [`TH_BKK_SpeedOrder_BE2567__p2_exemptions_and_signature.png`](excerpts/TH_BKK_SpeedOrder_BE2567__p2_exemptions_and_signature.png) | The **thirteen exempted roads**, item 4.4 being Phahonyothin; the repeal clause; and the signature block dated 6 December 2024 |
| [`IN_SO1522E_MaxSpeed_2018__p2_speed_table.png`](excerpts/IN_SO1522E_MaxSpeed_2018__p2_speed_table.png) | The full central speed table in English, row 6 setting **50 km/h for three-wheeled vehicles** on every road class, plus the 5 per cent enforcement tolerance and the file number |
| [`IN_Mumbai_CoastalRoad_Notif187_2026__p2_speed_table_and_signature.png`](excerpts/IN_Mumbai_CoastalRoad_Notif187_2026__p2_speed_table_and_signature.png) | **80 / 60 / 40 km/h** for straight sections, tunnels and curves on one road; the list of vehicles barred from it, which includes all three-wheelers; and the signature of the Additional Commissioner of Police (Traffic) |

These are page images of the committed PDFs, not separate sources. Anything they show can
be checked against the full document in the same folder, or against the official URL.

## Notes for anyone re-reading these files

**Thai gazette PDFs from 2024 do not extract as text.** The 2024 Bangkok order and the
other 2024 police regulations embed subsetted fonts without a ToUnicode map, so
`pdftotext` and `pypdf` return mojibake for the body while the running head extracts
correctly. They were read by rendering each page to a 200 dpi image. The 2018 and 2021
instruments, and all four Director of Highways notices, extract normally with
`pdftotext -enc UTF-8 -layout`.

**Two acts of 1979 are easily confused.** `พระราชบัญญัติจราจรทางบก` (Land **Traffic** Act) and
`พระราชบัญญัติการขนส่งทางบก` (Land **Transport** Act) share the year B.E. 2522 and differ by one
word. Only the former governs speed limits.

## Limits of what these documents establish

- The effect of **S.O. 1522(E)** was the subject of subsequent litigation. **Its current
  status has not been verified for this submission**, and no claim is made that the 2018
  table is the limit in force today.
- The **Maharashtra delegation instrument** has not been obtained. Which specific offices
  the State Government has authorised under s.112(2) is therefore recorded as
  *to be confirmed*, not asserted. Section 112(2) itself, and §8.1(3) of the Maharashtra
  departmental manual, both name no office.
- The Mumbai notification is cited for **who signs and under what authority**. It concerns
  a road opened in August 2025 and is **not part of the road network analysed in this
  study**, whose Maharashtra extract dates from May 2025.

*Files retrieved 30–31 August 2026.*
