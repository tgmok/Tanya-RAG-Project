# Real-world validation slice — Industrial Safety and Health Analytics Database

**Source:** IHM Stefanini's "Industrial Safety and Health Analytics Database" (accident
records from 12 real manufacturing/industrial plants across 3 countries). Original
listing: `kaggle.com/datasets/ihmstefanini/industrial-safety-and-health-analytics-database`.
Fetched from the dataset author's own public mirror
(`github.com/theshreyansh/HS-E_Data_Analysis_IHM_Stefanini`, raw CSV) on 2026-09-14,
since Kaggle's own download requires account authentication this environment doesn't
have. Same data, same source, different host.
**Licence:** Published openly by IHM Stefanini for research/analysis use; no access
restriction on the mirrored CSV.

**This file is NOT part of Tanya's main corpus.** Like `nyc_inspections.md`, it exists
only for the Section 6 real-world validation check. These are real industrial accident
records from real plants, unrelated to TGMOK Holdings.

8 real accident records, filtered to the **Metals** industry sector (closest real-world
match to CNC precision machining, out of the dataset's Mining / Metals / Others sectors)
and picked for variety of Critical Risk category, to validate `cnc/safety_sop.md`
against real machine-shop-adjacent incident narratives.

---

## cnc-real-01 — Pressurized Systems (2016-01-12, Country_02)

- Accident Level: I · Potential Accident Level: III
- Party: Third Party (Remote)
- Description: During the unloading operation of the ustulado bag there was a need to
  unclog the discharge mouth of the silo truck. In performing this procedure, there was
  a maneuver of unhooking the hose without the total depressurisation of the system,
  causing the hose to whip and strike the operator.

## cnc-real-02 — Fall Prevention, Same Level (2016-01-16, Country_02)

- Accident Level: I · Potential Accident Level: III
- Party: Employee
- Description: The collaborator reports that he was on street 09 holding in his left
  hand a volumetric flask, when he slipped and, on placing his hand on the ground, the
  flask broke, causing a small wound.

## cnc-real-03 — Chemical Substances (2016-01-26, Country_01)

- Accident Level: I · Potential Accident Level: II
- Party: Third Party
- Description: At the moment the forklift operator went to manipulate a big bag of
  bioxide in section 70, just in front of the ladder leading to the manual-displacement
  area, material splashed at the height of his forehead.

## cnc-real-04 — Liquid Metal (2016-02-01, Country_02)

- Accident Level: I · Potential Accident Level: I
- Party: Employee
- Description: The collaborator reports that while working at the roasting unit he
  noticed the cyclone duct was obstructed and opened the door to try to unclog it; the
  material detached and was projected towards the employee.

## cnc-real-05 — Confined Space (2016-02-04, Country_02)

- Accident Level: I · Potential Accident Level: III
- Party: Employee
- Description: Due to accumulation of material on the conveyor and trailer of filter
  08FI0502, the employee cleaned the shutter using an air lance and was surprised by the
  fall of product that had accumulated above.

## cnc-real-06 — Other (2016-02-07, Country_01)

- Accident Level: I · Potential Accident Level: II
- Party: Third Party
- Description: Due to overheating of two bars in row 5 of cell 7, a spark was produced
  and projected, reaching the shift supervisor in the corridor and causing a first-degree
  burn to the neck.

## cnc-real-07 — Manual Tools (2016-02-15, Country_01)

- Accident Level: I · Potential Accident Level: II
- Party: Employee
- Description: The operator was manually displacing a zinc sheet adhered to an aluminium
  cathode. When the blade detached, it released suddenly from the cathode, bending and
  grazing the collaborator's hand.

## cnc-real-08 — Pressed (2016-02-18, Country_02)

- Accident Level: I · Potential Accident Level: III
- Party: Third Party (Remote)
- Description: When replacing the telescopic expansion joint of an HDPE pipe on the
  storm-drainage pumping system, the piece involuntarily moved when positioned in the
  holder, pressing the technician's finger against the holder.
