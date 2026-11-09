"""
DATASET 6 - INDIA MATERNAL & NEONATAL OUTCOME / DELIVERY ENGINE

Final relational layer of the Maternal Health Project.

Grain
-----
Primary outcome table:
    1 row = 1 pregnancy outcome / delivery episode.

Supporting tables:
    1 row = 1 maternal outcome event
    1 row = 1 neonatal outcome record
    1 row = 1 outcome definition / evidence record

Inputs
------
Dataset 1: Patient & Pregnancy Baseline
Dataset 2: ANC Clinical & Vitals
Dataset 3: Laboratory & Investigations
Dataset 4: Medication & Treatment
Dataset 5: Nutrition & Food

Design principles
-----------------
- Delivery/outcome is generated from the longitudinal pregnancy trajectory.
- No fake post-delivery ANC visits are created.
- Gestational age is internally checked against dates where possible.
- Early delivery is an outcome, not a disease category.
- Maternal and neonatal outcomes are kept distinct.
- Delivery indications are separated from delivery mode.
- Emergency obstetric complications are represented explicitly.
- Neonatal outcomes include birth weight, Apgar, resuscitation and NICU.
- Outcome data remain synthetic research data and do not constitute
  clinical prediction or medical advice.

The generator intentionally uses controlled vocabularies and validation
rather than unconstrained random strings.
"""

import os
import re
from datetime import timedelta, datetime

import numpy as np
import pandas as pd
from openpyxl.utils import get_column_letter


PROJECT = os.environ.get("MH_PROJECT", r"D:\Maternal_Health_Project")
BASE = os.path.join(PROJECT, "datasets")

D1 = os.path.join(BASE, "dataset1_patient_pregnancy", "patient_pregnancy.csv")
D2 = os.path.join(BASE, "dataset2_anc_clinical_vitals", "anc_clinical_vitals.csv")
D2_PLAN = os.path.join(BASE, "dataset2_anc_clinical_vitals", "pregnancy_delivery_plan.csv")
D3 = os.path.join(BASE, "dataset3_laboratory_investigations", "laboratory_investigations.csv")
D4 = os.path.join(BASE, "dataset4_medication_treatment", "medication_events.csv")
D5 = os.path.join(BASE, "dataset5_nutrition_food", "nutrition_assessments.csv")

OUT = os.path.join(BASE, "dataset6_outcome_delivery")
os.makedirs(OUT, exist_ok=True)

SEED = 20261008
rng = np.random.default_rng(SEED)
days_rng = np.random.default_rng(SEED + 6)


def norm(x):
    return re.sub(r"[^a-z0-9]+", "", str(x).lower())


def find_col(df, candidates, required=False):
    lookup = {norm(c): c for c in df.columns}
    for c in candidates:
        if norm(c) in lookup:
            return lookup[norm(c)]
    if required:
        raise KeyError(
            f"Required column not found. Tried {candidates}. "
            f"Available columns: {list(df.columns)}"
        )
    return None


def txt(x):
    if pd.isna(x):
        return ""
    return str(x).strip()


def num(x):
    try:
        return float(str(x).replace(",", "").strip())
    except Exception:
        return np.nan


def dateval(x):
    try:
        return pd.to_datetime(x)
    except Exception:
        return pd.NaT


def clamp(x, lo, hi):
    return max(lo, min(hi, x))


# ================================================================
# CONTROLLED VOCABULARIES / EVIDENCE
# ================================================================

def outcome_definitions():
    rows = [
        ("OUT-001", "Live birth", "Birth outcome", "Infant born with signs of life", "A/B"),
        ("OUT-002", "Stillbirth", "Birth outcome", "Fetal death before/at delivery according to applicable reporting definition", "A/B"),
        ("OUT-003", "Miscarriage", "Pregnancy outcome", "Pregnancy loss before the locally applicable gestational threshold", "B"),
        ("OUT-004", "Termination of pregnancy", "Pregnancy outcome", "Pregnancy ended by induced termination", "A/B"),
        ("OUT-005", "Preterm birth", "Gestational outcome", "Birth before 37 completed weeks", "A/B"),
        ("OUT-006", "Low birth weight", "Neonatal outcome", "Birth weight below 2500 g", "A/B"),
        ("OUT-007", "Very low birth weight", "Neonatal outcome", "Birth weight below 1500 g", "A/B"),
        ("OUT-008", "Small for gestational age", "Neonatal outcome", "Birth size below the selected gestational-age reference threshold", "B"),
        ("OUT-009", "Large for gestational age", "Neonatal outcome", "Birth size above the selected gestational-age reference threshold", "B"),
        ("OUT-010", "Postpartum haemorrhage", "Maternal complication", "Clinically significant postpartum bleeding; threshold depends on delivery context/definition", "A/B"),
        ("OUT-011", "Hypertensive complication", "Maternal complication", "Pre-eclampsia/eclampsia/gestational hypertension complication", "A/B"),
        ("OUT-012", "Gestational diabetes", "Maternal complication", "GDM affecting pregnancy and/or delivery management", "A/B"),
        ("OUT-013", "Maternal transfusion", "Maternal complication", "Blood component transfusion during pregnancy/delivery/postpartum episode", "A/B"),
        ("OUT-014", "Maternal ICU/HDU admission", "Maternal complication", "Higher-level maternal care during delivery episode", "A/B"),
        ("OUT-015", "Neonatal intensive care", "Neonatal outcome", "NICU admission for neonatal monitoring/treatment", "A/B"),
        ("OUT-016", "Neonatal resuscitation", "Neonatal outcome", "Resuscitative support at birth", "A/B"),
        ("OUT-017", "Congenital anomaly", "Neonatal outcome", "Documented congenital anomaly identified at/around delivery", "A/B"),
    ]
    return pd.DataFrame(rows, columns=[
        "Outcome_Code", "Outcome_Name", "Outcome_Domain",
        "Definition", "Evidence_Grade"
    ])


def evidence_register():
    rows = [
        ("EV6-001", "WHO", "WHO recommendations on care of the preterm or low-birth-weight infant",
         "Preterm/LBW outcome framing and neonatal care context", "B",
         "https://www.who.int/publications/i/item/9789240058262"),
        ("EV6-002", "WHO", "WHO recommendations: maternal and newborn care for a positive postnatal experience",
         "Maternal/newborn postnatal outcome and care framework", "B",
         "https://www.who.int/publications/i/item/9789240045989"),
        ("EV6-003", "WHO", "WHO recommendations on antenatal care",
         "ANC and pregnancy outcome context", "B",
         "https://www.who.int/publications/i/item/9789241549912"),
        ("EV6-004", "MoHFW/NHM", "LaQshya / labour room and maternity operating standards",
         "Indian intrapartum and maternity-care context", "A",
         "https://nhm.gov.in/"),
        ("EV6-005", "MoHFW/NHM", "Maternal and newborn health programme guidance",
         "Indian maternal and neonatal care context", "A",
         "https://nhm.gov.in/"),
        ("EV6-006", "WHO", "Postpartum haemorrhage recommendations",
         "PPH outcome and emergency-care context", "B",
         "https://www.who.int/publications/i/item/9789240085398"),
    ]
    return pd.DataFrame(rows, columns=[
        "Evidence_ID", "Organization", "Source_Title",
        "Use_In_Dataset", "Evidence_Grade", "Reference_URL"
    ])


# ================================================================
# INPUT SUMMARIES
# ================================================================

def summarize_visits(d2):
    p = find_col(d2, ["Patient_ID"], True)
    pr = find_col(d2, ["Pregnancy_ID"], True)
    gw = find_col(d2, ["Gestational_Week", "Gestational Week"], True)
    vd = find_col(d2, ["Visit_Date", "Date"], True)

    def col(*names):
        return find_col(d2, list(names))

    result = {}

    for key, g in d2.groupby([p, pr], dropna=False):
        g = g.copy()
        g["_gw"] = pd.to_numeric(g[gw], errors="coerce")
        g["_date"] = pd.to_datetime(g[vd], errors="coerce")

        def any_text(names, terms):
            c = col(*names)
            if not c:
                return False
            blob = " ".join(g[c].astype(str).str.lower().tolist())
            return any(t in blob for t in terms)

        max_gw = g["_gw"].max()
        last = g.sort_values(["_gw", "_date"]).iloc[-1]

        sbp_c = col("SBP_mmHg", "SBP")
        dbp_c = col("DBP_mmHg", "DBP")
        sbp_max = pd.to_numeric(g[sbp_c], errors="coerce").max() if sbp_c else np.nan
        dbp_max = pd.to_numeric(g[dbp_c], errors="coerce").max() if dbp_c else np.nan

        result[(str(key[0]), str(key[1]))] = {
            "max_gw": max_gw,
            "last_visit_date": last["_date"],
            "sbp_max": sbp_max,
            "dbp_max": dbp_max,
            "hypertension": bool(
                (not np.isnan(sbp_max) and sbp_max >= 140) or
                (not np.isnan(dbp_max) and dbp_max >= 90)
            ),
            "hospitalisation": any_text(
                ["Hospitalisation_Required", "Visit_Outcome"],
                ["hospital", "admission"]
            ),
            "delivery_indicated": any_text(
                ["Delivery_Indicated", "Visit_Outcome"],
                ["delivery", "induction", "cesarean", "caesarean"]
            ),
            "referral": any_text(
                ["Referral_Required", "Referral_Reason"],
                ["yes", "required", "high risk"]
            ),
            "fetal_concern": any_text(
                ["Fetal_Status", "Placental_Concern", "Clinical_Assessment"],
                ["concern", "abnormal", "distress", "growth restriction"]
            ),
        }

    return result


def summarize_labs(d3):
    p = find_col(d3, ["Patient_ID"], True)
    pr = find_col(d3, ["Pregnancy_ID"], True)
    name = find_col(d3, ["Investigation_Name", "Test_Name", "Investigation"])
    result_col = find_col(d3, ["Result", "Result_Value", "Value"])
    flag_col = find_col(d3, ["Abnormal_Flag", "Flag"])

    result = {}

    for key, g in d3.groupby([p, pr], dropna=False):
        anaemia = False
        gdm = False
        thyroid = False
        infection = False

        if name:
            for _, r in g.iterrows():
                n = txt(r[name]).lower()
                v = num(r[result_col]) if result_col else np.nan

                if any(x in n for x in ["haemoglobin", "hemoglobin", "hb"]):
                    if not np.isnan(v) and v < 11:
                        anaemia = True

                if any(x in n for x in ["gdm", "ogtt", "two_hour", "2_hour"]):
                    # FIX: the old logic set GDM=True whenever a GDM screening
                    # test merely EXISTED. Screening is universal, so all 200
                    # pregnancies were labelled GDM. GDM now requires an
                    # abnormal/high diagnostic result.
                    flag = txt(r[flag_col]).lower() if flag_col else ""
                    if flag in {"abnormal", "high", "critical"}:
                        gdm = True

                if "tsh" in n or "thyroid" in n:
                    thyroid = True

                if any(x in n for x in ["hiv", "syphilis", "hepatitis", "infection"]):
                    infection = True

        result[(str(key[0]), str(key[1]))] = {
            "anaemia": anaemia,
            "gdm": gdm,
            "thyroid": thyroid,
            "infection_screening": infection,
        }

    return result


def summarize_meds(d4):
    if d4 is None or d4.empty:
        return {}

    p = find_col(d4, ["Patient_ID"])
    pr = find_col(d4, ["Pregnancy_ID"])
    name = find_col(d4, ["Medication_Name", "Generic_Name", "Medication"])
    event = find_col(d4, ["Event_Type", "Medication_Event", "Treatment_Event"])

    if not p or not pr or not name:
        return {}

    result = {}
    for key, g in d4.groupby([p, pr], dropna=False):
        blob = " ".join(g[name].astype(str).str.lower().tolist())
        event_blob = " ".join(g[event].astype(str).str.lower().tolist()) if event else ""

        result[(str(key[0]), str(key[1]))] = {
            "aspirin": "aspirin" in blob,
            "antihypertensive": any(x in blob for x in ["labetalol", "nifedipine", "methyldopa"]),
            "insulin": "insulin" in blob,
            "metformin": "metformin" in blob,
            "iron": "iron" in blob or "folic" in blob,
            "calcium": "calcium" in blob,
            "magnesium": "magnesium sulfate" in blob,
            "uterotonic": any(x in blob for x in ["oxytocin", "misoprostol", "carboprost"]),
            "tranexamic": "tranexamic" in blob,
            "anti_d": "anti-d" in blob or "anti d" in blob,
            "emergency_event": any(x in event_blob for x in ["emergency", "delivery", "postpartum", "pph"]),
        }

    return result


def summarize_nutrition(d5):
    if d5 is None or d5.empty:
        return {}

    p = find_col(d5, ["Patient_ID"])
    pr = find_col(d5, ["Pregnancy_ID"])
    pattern = find_col(d5, ["Dietary_Pattern"])
    risk = find_col(d5, ["Nutritional_Risk_Level"])

    if not p or not pr:
        return {}

    result = {}
    for key, g in d5.groupby([p, pr], dropna=False):
        result[(str(key[0]), str(key[1]))] = {
            "diet_pattern": txt(g[pattern].iloc[-1]) if pattern else "",
            "nutrition_risk": txt(g[risk].iloc[-1]) if risk else "",
        }
    return result


# ================================================================
# OUTCOME GENERATION
# ================================================================

def gestational_category(weeks, days=0):
    if weeks is None or np.isnan(weeks):
        return "Unknown"
    total = weeks + (days / 7 if days else 0)
    if total < 20:
        return "Pregnancy loss <20 weeks"
    if total < 37:
        return "Preterm birth"
    if total < 39:
        return "Early term"
    if total < 41:
        return "Full term"
    if total < 42:
        return "Late term"
    return "Post-term"


def infer_mode(risk_flags, gest_weeks, multiple=False):
    # Controlled synthetic distribution, modified by trajectory.
    if multiple:
        choices = ["Caesarean section", "Vaginal birth", "Assisted vaginal birth"]
        probs = [0.55, 0.35, 0.10]
    elif risk_flags >= 3:
        choices = ["Caesarean section", "Vaginal birth", "Assisted vaginal birth"]
        probs = [0.48, 0.43, 0.09]
    elif risk_flags == 2:
        choices = ["Vaginal birth", "Caesarean section", "Assisted vaginal birth"]
        probs = [0.52, 0.39, 0.09]
    else:
        choices = ["Vaginal birth", "Caesarean section", "Assisted vaginal birth"]
        probs = [0.67, 0.25, 0.08]

    # Very early births have more operative/assisted complexity.
    if gest_weeks < 34:
        choices = ["Caesarean section", "Vaginal birth", "Assisted vaginal birth"]
        probs = [0.58, 0.34, 0.08]

    return str(rng.choice(choices, p=probs))


def delivery_indications(mode, hypertension, gdm, fetal_concern, preterm):
    indications = []

    if hypertension and rng.random() < 0.65:
        indications.append("Hypertensive disorder")
    if fetal_concern and rng.random() < 0.55:
        indications.append("Fetal/placental concern")
    if preterm and rng.random() < 0.35:
        indications.append("Spontaneous preterm labour")
    # rng is always drawn so the random stream (and all other outcomes)
    # stays identical to the original run; only GDM-linked fields change.
    gdm_draw = rng.random()
    if gdm and gdm_draw < 0.25:
        indications.append("Diabetes-related obstetric indication")

    if mode == "Caesarean section" and not indications:
        indications.append(
            str(rng.choice([
                "Previous caesarean / obstetric history",
                "Non-reassuring fetal status",
                "Malpresentation",
                "Labour dystocia",
                "Other obstetric indication"
            ]))
        )

    if mode == "Assisted vaginal birth" and not indications:
        indications.append("Prolonged/assisted second stage")

    if not indications:
        indications.append("Spontaneous labour")

    return "; ".join(dict.fromkeys(indications))


def build_outcomes(d1, d2, d3, d4, d5):
    pcol = find_col(d1, ["Patient_ID"], True)
    prcol = find_col(d1, ["Pregnancy_ID"], True)

    visit_summary = summarize_visits(d2)
    lab_summary = summarize_labs(d3)
    med_summary = summarize_meds(d4)
    nut_summary = summarize_nutrition(d5)

    rows = []
    maternal_events = []
    neonatal_rows = []

    # FIX: use the delivery week Dataset 2 actually planned. Previously the
    # delivery week was capped at the LAST ANC visit, so women whose last
    # check-up happened before 37 weeks were wrongly labelled preterm.
    planned_week = {}
    if os.path.exists(D2_PLAN):
        plan = pd.read_csv(D2_PLAN)
        planned_week = dict(zip(plan["Pregnancy_ID"].astype(str), plan["Planned_Delivery_Week"]))

    for _, preg in d1.iterrows():
        patient = txt(preg[pcol])
        pregnancy = txt(preg[prcol])
        key = (patient, pregnancy)

        vs = visit_summary.get(key, {})
        ls = lab_summary.get(key, {})
        ms = med_summary.get(key, {})
        ns = nut_summary.get(key, {})

        max_gw = num(vs.get("max_gw", np.nan))
        if np.isnan(max_gw):
            max_gw = 39.0

        last_date = vs.get("last_visit_date", pd.NaT)

        # Small controlled amount of pregnancy loss/termination, with
        # trajectories ending early. Most records progress to delivery.
        loss_roll = rng.random()

        if loss_roll < 0.015 and max_gw < 20:
            outcome_type = "Miscarriage"
            outcome_date = (
                last_date if not pd.isna(last_date)
                else pd.Timestamp.today().normalize()
            )
            final_gw = clamp(max_gw, 8, 19)
            mode = "Not applicable"
            indication = "Pregnancy loss"
            live_birth = False
        elif loss_roll < 0.020 and max_gw < 20:
            outcome_type = "Termination of pregnancy"
            outcome_date = (
                last_date if not pd.isna(last_date)
                else pd.Timestamp.today().normalize()
            )
            final_gw = clamp(max_gw, 8, 19)
            mode = "Not applicable"
            indication = "Termination"
            live_birth = False
        else:
            # Early delivery is tied to the observed ANC trajectory.
            if max_gw >= 37:
                delivery_weeks = float(
                    rng.choice([37, 38, 39, 40, 41], p=[0.12,0.20,0.38,0.24,0.06])
                )
                delivery_weeks = min(delivery_weeks, max_gw)
            else:
                # Keep the synthetic delivery within the observed trajectory.
                # For very early trajectories (<28 weeks), avoid the old
                # lower=28 bug that could create a delivery after the final
                # observed gestational age.
                upper_week = max(1, int(np.floor(max_gw)))
                lower = max(20, upper_week - 1)
                if upper_week < 20:
                    delivery_weeks = float(upper_week)
                else:
                    delivery_weeks = float(rng.integers(lower, upper_week + 1))

            if pregnancy in planned_week:
                delivery_weeks = float(planned_week[pregnancy])

            final_gw = delivery_weeks
            preterm = final_gw < 37

            risk_flags = sum([
                bool(vs.get("hypertension", False)),
                bool(ls.get("anaemia", False)),
                bool(ls.get("gdm", False)),
                bool(vs.get("fetal_concern", False)),
                bool(vs.get("hospitalisation", False)),
                bool(vs.get("referral", False)),
            ])

            # Dataset 1 stores multiplicity in a dedicated column.
            # Do not pass the entire pandas Series to txt(), because
            # pd.isna(Series) produces a Series and causes the ambiguous
            # truth-value error seen during generation.
            multiple_col = find_col(
                d1,
                ["Multiple_Pregnancy", "Multiple_Gestation", "Multiple_Pregnancy_Flag"]
            )
            multiple_value = txt(preg[multiple_col]) if multiple_col else ""
            multiple = multiple_value.lower() in {"yes", "true", "1", "multiple", "twins", "triplets"}

            mode = infer_mode(
                risk_flags,
                final_gw,
                multiple=multiple
            )

            indication = delivery_indications(
                mode,
                bool(vs.get("hypertension", False)),
                bool(ls.get("gdm", False)),
                bool(vs.get("fetal_concern", False)),
                preterm
            )

            outcome_type = "Live birth"
            outcome_date = (
                last_date + timedelta(days=max(0, int((final_gw - max_gw) * 7)))
                if not pd.isna(last_date)
                else pd.Timestamp.today().normalize()
            )
            live_birth = True

        # Synthetic maternal outcome flags.
        hypertensive = bool(vs.get("hypertension", False))
        gdm = bool(ls.get("gdm", False))

        if live_birth:
            pph_probability = 0.035
            if mode == "Caesarean section":
                pph_probability += 0.025
            if hypertensive:
                pph_probability += 0.015

            pph = bool(rng.random() < pph_probability)
            transfusion = bool(pph and rng.random() < 0.20)
            icu = bool((hypertensive and rng.random() < 0.04) or
                       (pph and transfusion and rng.random() < 0.08))

            maternal_hypertensive_complication = bool(
                hypertensive and rng.random() < 0.55
            )
        else:
            pph = False
            transfusion = False
            icu = False
            maternal_hypertensive_complication = False

        # Neonatal values only for live birth.
        if live_birth:
            if final_gw < 32:
                mean_w = 1450
                sd_w = 300
            elif final_gw < 34:
                mean_w = 1850
                sd_w = 320
            elif final_gw < 37:
                mean_w = 2450
                sd_w = 350
            elif final_gw >= 41:
                mean_w = 3300
                sd_w = 430
            else:
                mean_w = 3050
                sd_w = 420

            if gdm:
                mean_w += 180

            birth_weight = int(clamp(rng.normal(mean_w, sd_w), 700, 5200))

            sex = str(rng.choice(["Female", "Male"], p=[0.49, 0.51]))

            if final_gw < 34:
                apgar1 = int(rng.choice([5,6,7,8], p=[0.10,0.25,0.45,0.20]))
                apgar5 = int(clamp(apgar1 + rng.integers(1,4), 6, 10))
            elif final_gw < 37:
                apgar1 = int(rng.choice([6,7,8,9], p=[0.05,0.15,0.50,0.30]))
                apgar5 = int(clamp(apgar1 + rng.integers(0,3), 7, 10))
            else:
                apgar1 = int(rng.choice([7,8,9], p=[0.08,0.42,0.50]))
                apgar5 = int(clamp(apgar1 + rng.integers(0,2), 8, 10))

            resuscitation = bool(
                final_gw < 34 and rng.random() < 0.30 or
                apgar1 <= 6 and rng.random() < 0.55
            )

            nicu_probability = 0.015
            if final_gw < 34:
                nicu_probability = 0.55
            elif final_gw < 37:
                nicu_probability = 0.18
            elif birth_weight < 2500:
                nicu_probability = 0.12

            nicu = bool(rng.random() < nicu_probability)

            if final_gw < 37:
                neonatal_status = "Preterm live birth"
            elif birth_weight < 2500:
                neonatal_status = "Term/near-term low birth weight"
            else:
                neonatal_status = "Liveborn, clinically stable"

            if birth_weight < 1500:
                bw_category = "Very low birth weight"
            elif birth_weight < 2500:
                bw_category = "Low birth weight"
            elif birth_weight >= 4000:
                bw_category = "High birth weight"
            else:
                bw_category = "Normal birth weight range"

            congenital_anomaly = bool(rng.random() < 0.015)
        else:
            sex = ""
            birth_weight = np.nan
            apgar1 = np.nan
            apgar5 = np.nan
            resuscitation = False
            nicu = False
            neonatal_status = "No live birth"
            bw_category = "Not applicable"
            congenital_anomaly = False

        # SGA/LGA are represented as screening flags, not diagnosis claims.
        if live_birth:
            sga = bool(
                birth_weight < 2500 and final_gw >= 37
                or (birth_weight < 2200 and final_gw < 37)
            )
            lga = bool(birth_weight >= 4000)
        else:
            sga = False
            lga = False

        gest_cat = gestational_category(final_gw)

        maternal_discharge = (
            "Routine postpartum discharge"
            if live_birth and not icu and not transfusion
            else "Extended maternal observation"
            if live_birth
            else "Pregnancy-loss care pathway"
        )

        postpartum_followup = "Yes"

        rows.append({
            "Outcome_ID": f"OUTC-{len(rows)+1:06d}",
            "Patient_ID": patient,
            "Pregnancy_ID": pregnancy,
            "Outcome_Date": outcome_date.strftime("%Y-%m-%d") if not pd.isna(outcome_date) else "",
            "Final_Gestational_Week": int(final_gw) if not np.isnan(final_gw) else "",
            # FIX: delivery weeks are whole numbers, so days were always 0.
            # A separate RNG adds 0-6 days without disturbing the main stream.
            "Final_Gestational_Days": int(days_rng.integers(0, 7)) if not np.isnan(final_gw) else "",
            "Gestational_Category": gest_cat,
            "Pregnancy_Outcome": outcome_type,
            "Live_Birth": "Yes" if live_birth else "No",
            "Delivery_Mode": mode,
            "Delivery_Indication": indication,
            "Hypertensive_Complication": "Yes" if maternal_hypertensive_complication else "No",
            "Gestational_Diabetes_Outcome": "Yes" if gdm else "No",
            "Postpartum_Haemorrhage": "Yes" if pph else "No",
            "Maternal_Transfusion": "Yes" if transfusion else "No",
            "Maternal_ICU_HDU": "Yes" if icu else "No",
            "Maternal_Discharge_Status": maternal_discharge,
            "Postpartum_Follow_Up_Required": postpartum_followup,
            "Dietary_Pattern_at_Final_Assessment": ns.get("diet_pattern", ""),
            "Nutrition_Risk_at_Final_Assessment": ns.get("nutrition_risk", ""),
            "Dataset4_Uterotonic_Exposure_Flag": "Yes" if ms.get("uterotonic", False) else "No",
            "Dataset4_Tranexamic_Exposure_Flag": "Yes" if ms.get("tranexamic", False) else "No",
        })

        maternal_events.append({
            "Maternal_Outcome_Event_ID": f"MOE-{len(maternal_events)+1:07d}",
            "Outcome_ID": rows[-1]["Outcome_ID"],
            "Patient_ID": patient,
            "Pregnancy_ID": pregnancy,
            "Event_Type": (
                "Delivery outcome" if live_birth
                else "Pregnancy outcome"
            ),
            "Event_Date": rows[-1]["Outcome_Date"],
            "Gestational_Week": rows[-1]["Final_Gestational_Week"],
            "Hypertensive_Complication": rows[-1]["Hypertensive_Complication"],
            "Postpartum_Haemorrhage": rows[-1]["Postpartum_Haemorrhage"],
            "Maternal_Transfusion": rows[-1]["Maternal_Transfusion"],
            "Maternal_ICU_HDU": rows[-1]["Maternal_ICU_HDU"],
            "Clinical_Significance": (
                "Routine delivery outcome"
                if live_birth and not (pph or transfusion or icu or maternal_hypertensive_complication)
                else "Requires documented maternal complication follow-up"
            ),
        })

        if live_birth:
            neonatal_rows.append({
                "Neonatal_Outcome_ID": f"NEO-{len(neonatal_rows)+1:06d}",
                "Outcome_ID": rows[-1]["Outcome_ID"],
                "Patient_ID": patient,
                "Pregnancy_ID": pregnancy,
                "Birth_Date": rows[-1]["Outcome_Date"],
                "Gestational_Week": rows[-1]["Final_Gestational_Week"],
                "Sex": sex,
                "Birth_Weight_g": birth_weight,
                "Birth_Weight_Category": bw_category,
                "Small_for_Gestational_Age_Flag": "Yes" if sga else "No",
                "Large_for_Gestational_Age_Flag": "Yes" if lga else "No",
                "Apgar_1_Min": apgar1,
                "Apgar_5_Min": apgar5,
                "Resuscitation_Required": "Yes" if resuscitation else "No",
                "NICU_Admission": "Yes" if nicu else "No",
                "Congenital_Anomaly_Flag": "Yes" if congenital_anomaly else "No",
                "Neonatal_Status": neonatal_status,
                "Breastfeeding_Initiation_Status": (
                    "Initiated before discharge"
                    if not nicu and rng.random() < 0.88
                    else "Delayed/assisted"
                    if nicu
                    else "Not documented"
                ),
            })

    return (
        pd.DataFrame(rows),
        pd.DataFrame(maternal_events),
        pd.DataFrame(neonatal_rows),
    )


# ================================================================
# VALIDATION
# ================================================================

def validate(outcomes, maternal, neonatal, definitions):
    issues = []

    required_outcome = [
        "Outcome_ID", "Patient_ID", "Pregnancy_ID",
        "Outcome_Date", "Final_Gestational_Week",
        "Pregnancy_Outcome", "Delivery_Mode"
    ]
    required_maternal = [
        "Maternal_Outcome_Event_ID", "Outcome_ID",
        "Patient_ID", "Pregnancy_ID"
    ]
    required_neonatal = [
        "Neonatal_Outcome_ID", "Outcome_ID",
        "Patient_ID", "Pregnancy_ID", "Birth_Weight_g"
    ]

    for c in required_outcome:
        if c not in outcomes.columns:
            issues.append(f"Outcome table missing column: {c}")
    for c in required_maternal:
        if c not in maternal.columns:
            issues.append(f"Maternal table missing column: {c}")
    for c in required_neonatal:
        if c not in neonatal.columns:
            issues.append(f"Neonatal table missing column: {c}")

    if outcomes["Outcome_ID"].duplicated().any():
        issues.append("Duplicate Outcome_ID")
    if maternal["Maternal_Outcome_Event_ID"].duplicated().any():
        issues.append("Duplicate Maternal_Outcome_Event_ID")
    if neonatal["Neonatal_Outcome_ID"].duplicated().any():
        issues.append("Duplicate Neonatal_Outcome_ID")

    outcome_ids = set(outcomes["Outcome_ID"])
    if not set(maternal["Outcome_ID"]).issubset(outcome_ids):
        issues.append("Maternal events contain orphan Outcome_ID")
    if not set(neonatal["Outcome_ID"]).issubset(outcome_ids):
        issues.append("Neonatal events contain orphan Outcome_ID")

    live_ids = set(
        outcomes.loc[outcomes["Live_Birth"] == "Yes", "Outcome_ID"]
    )
    neo_ids = set(neonatal["Outcome_ID"])
    if not neo_ids.issubset(live_ids):
        issues.append("Neonatal records exist for non-live-birth outcomes")

    nonlive = outcomes[outcomes["Live_Birth"] == "No"]
    if not nonlive.empty:
        bad_modes = nonlive[
            ~nonlive["Delivery_Mode"].isin(
                ["Not applicable", "Not Applicable", ""]
            )
        ]
        if not bad_modes.empty:
            issues.append("Non-live-birth outcomes have a delivery mode")

    live = outcomes[outcomes["Live_Birth"] == "Yes"]
    if not live.empty:
        if (pd.to_numeric(live["Final_Gestational_Week"], errors="coerce") < 20).any():
            issues.append("Live birth below 20 weeks detected")

    if not neonatal.empty:
        bw = pd.to_numeric(neonatal["Birth_Weight_g"], errors="coerce")
        if (bw <= 0).any() or (bw > 6000).any():
            issues.append("Implausible neonatal birth weight")

        ap1 = pd.to_numeric(neonatal["Apgar_1_Min"], errors="coerce")
        ap5 = pd.to_numeric(neonatal["Apgar_5_Min"], errors="coerce")
        if ((ap1 < 0) | (ap1 > 10)).any():
            issues.append("Apgar 1-minute outside 0-10")
        if ((ap5 < 0) | (ap5 > 10)).any():
            issues.append("Apgar 5-minute outside 0-10")

    # Controlled delivery modes.
    allowed_modes = {
        "Vaginal birth", "Caesarean section",
        "Assisted vaginal birth", "Not applicable"
    }
    if not set(outcomes["Delivery_Mode"]).issubset(allowed_modes):
        issues.append("Uncontrolled Delivery_Mode value")

    # Controlled pregnancy outcomes.
    allowed_outcomes = {
        "Live birth", "Stillbirth", "Miscarriage",
        "Termination of pregnancy"
    }
    if not set(outcomes["Pregnancy_Outcome"]).issubset(allowed_outcomes):
        issues.append("Uncontrolled Pregnancy_Outcome value")

    return issues


# ================================================================
# MAIN
# ================================================================

def main():
    print("=" * 76)
    print("DATASET 6 - INDIA MATERNAL & NEONATAL OUTCOME / DELIVERY ENGINE")
    print("=" * 76)

    print("\nLoading Dataset 1-5...")

    d1 = pd.read_csv(D1)
    d2 = pd.read_csv(D2)
    d3 = pd.read_csv(D3)

    d4 = pd.read_csv(D4) if os.path.exists(D4) else pd.DataFrame()
    d5 = pd.read_csv(D5) if os.path.exists(D5) else pd.DataFrame()

    print(f"Dataset 1: {len(d1):,} pregnancies")
    print(f"Dataset 2: {len(d2):,} ANC visits")
    print(f"Dataset 3: {len(d3):,} investigations")
    print(f"Dataset 4: {len(d4):,} medication events")
    print(f"Dataset 5: {len(d5):,} nutrition assessments")

    print("\nBuilding outcome definitions and evidence register...")
    definitions = outcome_definitions()
    evidence = evidence_register()

    print("\nGenerating longitudinal pregnancy outcomes...")
    outcomes, maternal, neonatal = build_outcomes(
        d1, d2, d3, d4, d5
    )

    print(f"Pregnancy outcomes: {len(outcomes):,}")
    print(f"Maternal outcome events: {len(maternal):,}")
    print(f"Neonatal outcome records: {len(neonatal):,}")

    print("\nValidating...")
    issues = validate(
        outcomes, maternal, neonatal, definitions
    )

    outputs = {
        "outcome_delivery.csv": outcomes,
        "maternal_outcome_events.csv": maternal,
        "neonatal_outcomes.csv": neonatal,
        "outcome_definitions.csv": definitions,
        "outcome_evidence_register.csv": evidence,
    }

    for filename, df in outputs.items():
        df.to_csv(
            os.path.join(OUT, filename),
            index=False,
            encoding="utf-8-sig"
        )

    xlsx = os.path.join(OUT, "outcome_delivery_india.xlsx")
    with pd.ExcelWriter(xlsx, engine="openpyxl") as writer:
        for filename, df in outputs.items():
            sheet = filename.replace(".csv", "")[:31]
            df.to_excel(writer, sheet_name=sheet, index=False)

        wb = writer.book
        for ws in wb.worksheets:
            ws.freeze_panes = "A2"
            ws.auto_filter.ref = ws.dimensions

            for cell in ws[1]:
                cell.font = cell.font.copy(bold=True)

            for col_idx, col in enumerate(ws.columns, 1):
                max_len = 0
                for cell in col[:200]:
                    max_len = max(max_len, len(str(cell.value or "")))
                ws.column_dimensions[
                    get_column_letter(col_idx)
                ].width = min(max(max_len + 2, 12), 42)

    # Summary statistics.
    outcome_counts = outcomes["Pregnancy_Outcome"].value_counts().to_dict()
    mode_counts = outcomes["Delivery_Mode"].value_counts().to_dict()
    gest_counts = outcomes["Gestational_Category"].value_counts().to_dict()

    live = outcomes[outcomes["Live_Birth"] == "Yes"]

    summary = [
        "DATASET 6 - MATERNAL & NEONATAL OUTCOME / DELIVERY",
        "=" * 70,
        "",
        "Synthetic research dataset. NOT a clinical prediction or decision system.",
        "",
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"Dataset 1 pregnancies: {len(d1):,}",
        f"Dataset 2 ANC visits: {len(d2):,}",
        f"Dataset 3 investigations: {len(d3):,}",
        f"Dataset 4 medication events: {len(d4):,}",
        f"Dataset 5 nutrition assessments: {len(d5):,}",
        "",
        f"Pregnancy outcome rows: {len(outcomes):,}",
        f"Maternal event rows: {len(maternal):,}",
        f"Neonatal outcome rows: {len(neonatal):,}",
        "",
        "Pregnancy outcomes:",
    ]

    for k, v in sorted(outcome_counts.items()):
        summary.append(f"  {k}: {v:,}")

    summary += ["", "Delivery modes:"]
    for k, v in sorted(mode_counts.items()):
        summary.append(f"  {k}: {v:,}")

    summary += ["", "Gestational outcome categories:"]
    for k, v in sorted(gest_counts.items()):
        summary.append(f"  {k}: {v:,}")

    if not live.empty:
        summary += [
            "",
            "Maternal complication flags among outcomes:",
            f"  PPH: {(live['Postpartum_Haemorrhage'] == 'Yes').sum():,}",
            f"  Maternal transfusion: {(live['Maternal_Transfusion'] == 'Yes').sum():,}",
            f"  Maternal ICU/HDU: {(live['Maternal_ICU_HDU'] == 'Yes').sum():,}",
            f"  Hypertensive complication: {(live['Hypertensive_Complication'] == 'Yes').sum():,}",
            "",
            "Neonatal outcome flags:",
            f"  NICU admissions: {(neonatal['NICU_Admission'] == 'Yes').sum():,}",
            f"  Resuscitation required: {(neonatal['Resuscitation_Required'] == 'Yes').sum():,}",
            f"  Low birth weight: {(neonatal['Birth_Weight_Category'] == 'Low birth weight').sum():,}",
            f"  Very low birth weight: {(neonatal['Birth_Weight_g'] < 1500).sum():,}",
        ]

    summary += [
        "",
        "Relational flow:",
        "  Patient/Pregnancy -> ANC -> Labs -> Medications/Nutrition -> Outcome",
        "",
        "Validation:",
        f"  Issues: {len(issues)}",
        f"  Status: {'PASS' if not issues else 'FAIL'}",
    ]

    with open(
        os.path.join(OUT, "dataset6_summary.txt"),
        "w",
        encoding="utf-8"
    ) as f:
        f.write("\n".join(summary))

    report = [
        "DATASET 6 VALIDATION REPORT",
        "=" * 70,
        f"Generated: {datetime.now().isoformat()}",
        "",
        f"Outcome rows: {len(outcomes):,}",
        f"Maternal event rows: {len(maternal):,}",
        f"Neonatal rows: {len(neonatal):,}",
        "",
        f"Duplicate Outcome_ID: {'PASS' if not outcomes['Outcome_ID'].duplicated().any() else 'FAIL'}",
        f"Duplicate maternal event ID: {'PASS' if not maternal['Maternal_Outcome_Event_ID'].duplicated().any() else 'FAIL'}",
        f"Duplicate neonatal ID: {'PASS' if not neonatal['Neonatal_Outcome_ID'].duplicated().any() else 'FAIL'}",
        f"Outcome referential integrity: {'PASS' if not issues else 'CHECK'}",
        "",
    ]

    if issues:
        report.append("ISSUES:")
        report.extend(f"  - {x}" for x in issues)
    else:
        report.append("No validation issues detected.")

    with open(
        os.path.join(OUT, "dataset6_validation_report.txt"),
        "w",
        encoding="utf-8"
    ) as f:
        f.write("\n".join(report))

    print("\n" + "=" * 76)
    print("DATASET 6 GENERATION COMPLETE")
    print("=" * 76)
    print(f"Pregnancy outcomes:       {len(outcomes):,}")
    print(f"Maternal events:          {len(maternal):,}")
    print(f"Neonatal outcomes:        {len(neonatal):,}")
    print(f"Outcome definitions:      {len(definitions):,}")
    print(f"Validation issues:        {len(issues)}")
    print(f"Validation status:        {'PASS' if not issues else 'FAIL'}")
    print(f"\nOutput folder:\n{OUT}")


if __name__ == "__main__":
    main()
