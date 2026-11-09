"""
Deterministic clinical logic for the dashboards: gestational tracking,
"record as of a visit", medication safety checks, test schedule,
alerts and rule-based suggestions.

Safety checks are deliberately RULE-BASED, not ML: an allergy or drug
interaction must be caught every single time, and the rule must be
traceable to a source table (Dataset 4 crosswalks).

Everything here is decision SUPPORT for a synthetic research dataset,
not clinical advice.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from .data import MaternalData


# ------------------------------------------------------------------ gestation
def gestational_age(lmp: pd.Timestamp, on: pd.Timestamp):
    days = int((on - lmp).days)
    return days // 7, days % 7


def trimester(weeks: float) -> str:
    return "First" if weeks < 14 else "Second" if weeks < 28 else "Third"


MILESTONES = [
    (0, 12, "Booking visit, dating scan, first blood tests"),
    (11, 14, "NT / first-trimester screening window"),
    (14, 14, "Calcium supplementation and iron-folic acid begin (India AMB)"),
    (18, 22, "Detailed anomaly scan"),
    (24, 28, "Glucose test for gestational diabetes (OGTT)"),
    (28, 28, "Third trimester begins; repeat Hb; anti-D if Rh-negative"),
    (32, 36, "Growth scan and fetal presentation check"),
    (35, 37, "GBS swab (where offered); birth planning"),
    (37, 37, "Term (early term begins)"),
    (40, 40, "Expected date of delivery"),
]


def milestones_table(ga_weeks: float) -> pd.DataFrame:
    rows = []
    for lo, hi, text in MILESTONES:
        status = "Done" if ga_weeks > hi else "Now" if lo <= ga_weeks <= hi + 0.99 else "Upcoming"
        window = f"{lo} wk" if lo == hi else f"{lo}–{hi} wk"
        rows.append({"Window": window, "Milestone": text, "Status": status})
    return pd.DataFrame(rows)


# ------------------------------------------------------------------ record
@dataclass
class Record:
    """Everything known about one pregnancy up to and including a visit."""
    patient: pd.Series
    visit: pd.Series
    visits: pd.DataFrame           # visits up to now
    labs: pd.DataFrame             # labs up to now
    labs_today: pd.DataFrame
    meds: pd.DataFrame             # medication events up to now
    meds_today: pd.DataFrame
    nutrition: pd.DataFrame        # nutrition assessments up to now
    food_recs_today: pd.DataFrame
    ga_weeks: int
    ga_days: int


def record_as_of(data: MaternalData, pregnancy_id: str, visit_id: str) -> Record:
    p = data.patients.loc[data.patients.Pregnancy_ID == pregnancy_id].iloc[0]
    allv = data.visits[data.visits.Pregnancy_ID == pregnancy_id]
    v = allv[allv.Visit_ID == visit_id].iloc[0]
    upto = allv[allv.Visit_Date <= v.Visit_Date]
    ids = set(upto.Visit_ID)
    labs = data.labs[data.labs.Visit_ID.isin(ids)]
    meds = data.meds[data.meds.Visit_ID.isin(ids)]
    nut = data.nutrition[data.nutrition.Visit_ID.isin(ids)]
    return Record(
        patient=p, visit=v, visits=upto, labs=labs,
        labs_today=labs[labs.Visit_ID == visit_id],
        meds=meds, meds_today=meds[meds.Visit_ID == visit_id],
        nutrition=nut,
        food_recs_today=data.food_recs[data.food_recs.Visit_ID == visit_id],
        ga_weeks=int(v.Gestational_Week), ga_days=int(v.Gestational_Days),
    )


def latest_numeric(labs: pd.DataFrame, test: str):
    t = labs[(labs.Test_Name == test) & labs.Result_Num.notna()].sort_values("Investigation_Date")
    return (None, None) if t.empty else (float(t.Result_Num.iloc[-1]), t.Investigation_Date.iloc[-1])


# ------------------------------------------------------------------ medications
def active_medications(rec: Record) -> pd.DataFrame:
    m = rec.meds[~rec.meds.Generic_Name.isin(["No_Regular_Medication", "None", ""])]
    if m.empty:
        return m
    m = m.sort_values("Event_Date")
    last = m.groupby("Generic_Name").tail(1)
    first = m.groupby("Generic_Name").Event_Date.min().rename("Started_On")
    out = last.merge(first, left_on="Generic_Name", right_index=True)
    return out.sort_values("Started_On")


ALLERGY_KEYWORDS = {
    "penicillin": ["penicillin", "amoxicillin"],
    "amoxicillin": ["penicillin", "amoxicillin"],
    "cephalosporin": ["cephalexin", "cef"],
    "nsaids": ["aspirin", "nsaid", "ibuprofen", "diclofenac"],
    "aspirin": ["aspirin", "nsaid", "ibuprofen", "diclofenac"],
    "sulfonamide": ["sulfa", "co-trimoxazole"],
    "iron_preparation": ["iron"],
}

INTERACTION_KEYWORDS = {
    "iron": ["iron"], "calcium": ["calcium"], "levothyroxine": ["levothyroxine"],
    "methyldopa": ["methyldopa"], "aspirin": ["aspirin"], "anticoagulants": ["warfarin", "heparin"],
    "nsaids": ["nsaid", "ibuprofen", "diclofenac"], "labetalol": ["labetalol"],
    "insulin": ["insulin"], "metformin": ["metformin"],
}


def _kw_match(drug_name: str, group: str) -> bool:
    keys = INTERACTION_KEYWORDS.get(group.strip().lower(), [group.strip().lower()])
    d = drug_name.lower()
    return any(k in d for k in keys)


def safety_check(data: MaternalData, rec: Record, drugs: list[str]) -> pd.DataFrame:
    """Check a list of medicine names against allergies, interactions and pregnancy risk."""
    rows = []
    allergy = str(rec.patient.Drug_Allergies).strip()
    reaction = str(rec.patient.Drug_Allergy_Reaction).strip()
    akey = allergy.lower()
    master = data.med_master.set_index("Generic_Name")

    for d in drugs:
        dl = d.lower()
        # 1. allergy
        if akey == "multiple":
            rows.append({"Medicine": d, "Check": "Allergy", "Severity": "Serious",
                         "Finding": f"Patient has MULTIPLE drug allergies (reaction: {reaction}). Confirm before prescribing."})
        elif akey not in ("", "none") and any(k in dl for k in ALLERGY_KEYWORDS.get(akey, [akey])):
            rows.append({"Medicine": d, "Check": "Allergy", "Severity": "Critical",
                         "Finding": f"Documented {allergy} allergy (reaction: {reaction}) conflicts with {d}."})
        # 2. pregnancy-avoid flag from master
        if d in master.index and master.loc[d, "Not_for_Routine_Pregnancy_Use"] == "Yes":
            rows.append({"Medicine": d, "Check": "Pregnancy", "Severity": "Serious",
                         "Finding": f"Not for routine pregnancy use: {master.loc[d, 'Pregnancy_Role']}"})
        # 3. renal caution
        if str(rec.patient.Renal_Disease) == "Yes" and d in master.index:
            rows.append({"Medicine": d, "Check": "Renal", "Severity": "Warning",
                         "Finding": master.loc[d, "Renal_Considerations"]})

    # 4. interactions between every pair of listed drugs
    for _, r in data.med_interactions.iterrows():
        a = [d for d in drugs if _kw_match(d, r.Drug_A)]
        b = [d for d in drugs if _kw_match(d, r.Drug_B_or_Group)]
        for x in a:
            for y in b:
                if x != y:
                    rows.append({"Medicine": f"{x} + {y}", "Check": "Interaction", "Severity": "Warning",
                                 "Finding": f"{r.Mechanism_or_Concern}. {r.Recommended_Data_Action}"})
    df = pd.DataFrame(rows, columns=["Medicine", "Check", "Severity", "Finding"])
    order = {"Critical": 0, "Serious": 1, "Warning": 2}
    return df.drop_duplicates().sort_values("Severity", key=lambda s: s.map(order))


def drug_profile(data: MaternalData, name: str) -> dict:
    m = data.med_master[data.med_master.Generic_Name == name]
    return {} if m.empty else m.iloc[0].to_dict()


# ------------------------------------------------------------------ tests
SCHEDULE = [
    # (from_wk, to_wk, test name in D3, why)
    (0, 13, "Haemoglobin", "Booking Hb"),
    (0, 13, "ABO_Group", "Blood group"),
    (0, 13, "HIV_Test", "Booking infection screen"),
    (0, 13, "Syphilis_Test", "Booking infection screen"),
    (0, 13, "Hepatitis_B_HBsAg", "Booking infection screen"),
    (0, 13, "Booking_Dating_Ultrasound", "Dating scan"),
    (18, 22, "Structural_Anomaly_Scan", "Anomaly scan"),
    (24, 28, "GDM_Screening", "GDM screening (OGTT)"),
    (26, 30, "Haemoglobin", "Third-trimester Hb"),
    (32, 36, "Fetal_Growth_Assessment", "Growth scan"),
    (35, 37, "Group_B_Streptococcus_Swab", "GBS swab"),
]


def test_plan(rec: Record) -> pd.DataFrame:
    """Due / overdue / upcoming tests relative to the current gestational age."""
    ga = rec.ga_weeks + rec.ga_days / 7
    rows = []
    for lo, hi, test, why in SCHEDULE:
        done = rec.labs[(rec.labs.Test_Name == test) &
                        (rec.labs.Gestational_Week >= lo) & (rec.labs.Gestational_Week <= hi)]
        if not done.empty:
            continue
        if ga > hi + 1:
            status = "Overdue"
        elif lo - 4 <= ga <= hi + 1:
            status = "Due now" if ga >= lo else "Due soon"
        else:
            continue
        rows.append({"Test": test.replace("_", " "), "Window": f"{lo}–{hi} wk", "Reason": why, "Status": status})
    # Rh-negative women need anti-D / ICT planning around 28 weeks.
    if str(rec.patient.RhD_Status).lower().startswith("neg") and ga < 30:
        rows.append({"Test": "Indirect Antiglobulin Test", "Window": "28 wk",
                     "Reason": "Rh-negative: antibody screen + anti-D planning", "Status": "Due soon"})
    # Urine protein is checked at every ANC visit.
    rows.append({"Test": "Urine Protein", "Window": "every visit", "Reason": "Pre-eclampsia screening",
                 "Status": "Every visit"})
    return pd.DataFrame(rows)


# ------------------------------------------------------------------ alerts & suggestions
def alerts(rec: Record) -> list[tuple[str, str, str]]:
    """(severity, title, consequence) – severity in critical/serious/warning/good."""
    out = []
    v = rec.visit
    sbp, dbp = v.SBP_mmHg, v.DBP_mmHg
    n_high = int(((rec.visits.SBP_mmHg >= 140) | (rec.visits.DBP_mmHg >= 90)).sum())
    if sbp >= 160 or dbp >= 110:
        out.append(("critical", f"Severe-range BP {sbp}/{dbp} mmHg",
                    "Risk of severe pre-eclampsia, eclampsia, stroke and placental abruption — urgent review."))
    elif sbp >= 140 or dbp >= 90:
        out.append(("serious", f"Raised BP {sbp}/{dbp} mmHg ({n_high} raised reading(s) so far)",
                    "Hypertension in pregnancy can progress to pre-eclampsia and lead to early delivery or growth restriction."))
    prot = rec.labs[(rec.labs.Test_Name == "Urine_Protein") & rec.labs.Is_Abnormal]
    if not prot.empty and n_high:
        out.append(("critical", "Raised BP with proteinuria",
                    "Pattern consistent with pre-eclampsia — needs confirmation and close monitoring."))
    elif not prot.empty:
        out.append(("warning", f"Proteinuria on {len(prot)} test(s)",
                    "Watch BP closely; rule out urinary infection or renal cause."))

    hb, _ = latest_numeric(rec.labs, "Haemoglobin")
    if hb is not None:
        if hb < 7:
            out.append(("critical", f"Severe anaemia (Hb {hb:.1f} g/dL)",
                        "Risk of heart strain, PPH complications, preterm birth and low birth weight."))
        elif hb < 11:
            hbs = rec.labs[(rec.labs.Test_Name == "Haemoglobin")].sort_values("Investigation_Date").Result_Num
            drop = hbs.iloc[0] - hbs.iloc[-1] if len(hbs) > 1 else 0
            extra = f", fallen {drop:.1f} g/dL since booking" if drop >= 1 else ""
            out.append(("serious", f"Anaemia (Hb {hb:.1f} g/dL{extra})",
                        "Linked to fatigue, infection, preterm birth, low birth weight and poor tolerance of blood loss at delivery."))
    if rec.labs[(rec.labs.Test_Name.isin(["GDM_Screening", "Two_Hour_Glucose"])) & rec.labs.Is_Abnormal].shape[0]:
        out.append(("serious", "Abnormal glucose / GDM screen",
                    "GDM raises risk of a large baby, birth injury, C-section and newborn hypoglycaemia."))
    if v.SpO2_percent < 95:
        out.append(("serious", f"Low SpO2 {v.SpO2_percent}%", "Assess for respiratory or cardiac cause."))
    if v.Fetal_Movement_Status == "Reduced":
        out.append(("critical", "Reduced fetal movements reported", "Needs same-day fetal wellbeing assessment (CTG)."))
    if v.Fetal_Presentation in ("Breech", "Transverse") and rec.ga_weeks >= 36:
        out.append(("warning", f"{v.Fetal_Presentation} presentation at {rec.ga_weeks} weeks",
                    "Discuss external cephalic version or planned mode of birth."))
    if rec.labs[(rec.labs.Test_Name == "TSH") & rec.labs.Is_Abnormal].shape[0]:
        out.append(("warning", "Abnormal TSH", "Untreated thyroid dysfunction affects fetal neuro-development."))
    return out


def suggestions(data: MaternalData, rec: Record) -> list[tuple[str, str]]:
    """Rule-based medication suggestions for the doctor to review: (medicine, reason)."""
    active = set(active_medications(rec).Generic_Name)
    names = " ".join(active).lower()
    ga = rec.ga_weeks
    out = []
    hb, _ = latest_numeric(rec.labs, "Haemoglobin")
    if hb is not None and hb < 11 and not (rec.meds.Event_Type == "Therapeutic supplementation").any():
        out.append(("Iron + folic acid", f"Hb {hb:.1f} g/dL — consider therapeutic (treatment) dose of iron; "
                                         f"IV iron if Hb < 8 g/dL or intolerant (India AMB)."))
    n_high = int(((rec.visits.SBP_mmHg >= 140) | (rec.visits.DBP_mmHg >= 90)).sum())
    if n_high >= 2 and not any(k in names for k in ["labetalol", "nifedipine", "methyldopa", "antihypertensive"]):
        out.append(("Labetalol", f"{n_high} raised BP readings and no antihypertensive on record."))
    p = rec.patient
    high_pe = sum(str(p[c]) == "Yes" for c in ["Preexisting_Hypertension", "Previous_PreEclampsia",
                                               "Preexisting_Diabetes", "Renal_Disease", "Autoimmune_Disease",
                                               "Multiple_Pregnancy"])
    if high_pe >= 1 and 12 <= ga <= 28 and "aspirin" not in names:
        out.append(("Low-dose aspirin", "High-risk factor for pre-eclampsia present; aspirin is started from 12 weeks."))
    if ga >= 14 and "calcium" not in names:
        out.append(("Calcium carbonate + vitamin D3", "Routine calcium from 14 weeks is not on record."))
    if rec.labs[(rec.labs.Test_Name.isin(["GDM_Screening", "Two_Hour_Glucose"])) & rec.labs.Is_Abnormal].shape[0] \
            and not any(k in names for k in ["metformin", "insulin"]):
        out.append(("Metformin", "Abnormal glucose test — start medical nutrition therapy first; "
                                 "metformin/insulin if targets not met in 1–2 weeks."))
    if rec.labs[(rec.labs.Test_Name == "TSH") & rec.labs.Is_Abnormal].shape[0] and "levothyroxine" not in names:
        out.append(("Levothyroxine", "TSH above pregnancy reference range."))
    return out


def weight_gain_target(bmi: float):
    """IOM gestational weight-gain range (kg) by pre-pregnancy BMI."""
    if bmi < 18.5:
        return 12.5, 18.0, "Underweight"
    if bmi < 25:
        return 11.5, 16.0, "Normal"
    if bmi < 30:
        return 7.0, 11.5, "Overweight"
    return 5.0, 9.0, "Obese"
