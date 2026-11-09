"""
Visit-level feature table built WITHOUT looking into the future.

For every ANC visit we compute features from:
  * the baseline record (D1), known at booking;
  * this visit and all EARLIER visits of the same pregnancy (D2);
  * labs, medications ordered at or before this visit (D3, D4).

Nothing from later visits or from the delivery record (D6) is used, so a
risk score shown to a doctor at 28 weeks is exactly what a real system
could have computed at 28 weeks.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .data import MaternalData, yes

# Human-readable names, used by the dashboard explanations.
FEATURE_LABELS = {
    "age": "Maternal age",
    "bmi_pre": "Pre-pregnancy BMI",
    "gravida": "Gravida (no. of pregnancies)",
    "para": "Para (previous births)",
    "prev_miscarriage": "Previous miscarriage",
    "prev_stillbirth": "Previous stillbirth",
    "prev_preterm": "Previous preterm birth",
    "prev_csection": "Previous C-section",
    "pre_htn": "Pre-existing hypertension",
    "pre_diabetes": "Pre-existing diabetes",
    "thyroid": "Thyroid disease",
    "renal": "Renal disease",
    "cardiac": "Cardiac disease",
    "prev_preeclampsia": "Previous pre-eclampsia",
    "prev_gdm": "Previous GDM",
    "multiple": "Multiple pregnancy (twins+)",
    "smoker": "Smoking (current/former)",
    "haemoglobinopathy": "Known haemoglobinopathy",
    "rural": "Rural residence",
    "ga_weeks": "Gestational age now",
    "sbp": "Systolic BP (this visit)",
    "dbp": "Diastolic BP (this visit)",
    "spo2": "SpO2 (this visit)",
    "weight_gain": "Weight gain since booking",
    "oedema": "Oedema grade",
    "risk_level": "Visit risk level",
    "max_sbp": "Highest systolic BP so far",
    "max_dbp": "Highest diastolic BP so far",
    "n_bp140": "Visits with SBP >= 140",
    "n_high_risk": "High-risk visits so far",
    "n_referrals": "Referrals so far",
    "n_additional": "Additional (unscheduled) visits",
    "reduced_fm_ever": "Reduced fetal movement reported",
    "fetal_concern_ever": "Fetal status needed assessment",
    "malpresentation": "Breech/transverse presentation",
    "min_hb": "Lowest Hb so far",
    "latest_hb": "Latest Hb",
    "hb_drop": "Hb drop since first test",
    "n_abnormal_labs": "Abnormal lab results so far",
    "gdm_abn": "Abnormal glucose / GDM screen",
    "proteinuria": "Proteinuria detected",
    "tsh_abn": "Abnormal TSH",
    "infection_pos": "Positive infection screen (HIV/syphilis/HBsAg/GBS)",
    "growth_concern": "Fetal growth / anomaly scan concern",
    "aspirin": "On low-dose aspirin",
    "antihypertensive": "On antihypertensive",
    "therapeutic_iron": "Therapeutic iron escalation",
    "levothyroxine": "On levothyroxine",
    "metformin": "On metformin",
}

FEATURES = list(FEATURE_LABELS.keys())


def _baseline(d1: pd.DataFrame) -> pd.DataFrame:
    b = pd.DataFrame({"Pregnancy_ID": d1["Pregnancy_ID"]})
    b["age"] = d1["Age_Years"].astype(float)
    b["bmi_pre"] = d1["Pre_Pregnancy_BMI"].astype(float)
    b["gravida"] = d1["Gravida"].astype(float)
    b["para"] = d1["Para"].astype(float)
    for new, col in [
        ("prev_miscarriage", "Previous_Miscarriage"), ("prev_stillbirth", "Previous_Stillbirth"),
        ("prev_preterm", "Previous_Preterm_Birth"), ("prev_csection", "Previous_C_Section"),
        ("pre_htn", "Preexisting_Hypertension"), ("pre_diabetes", "Preexisting_Diabetes"),
        ("thyroid", "Thyroid_Disease"), ("renal", "Renal_Disease"), ("cardiac", "Cardiac_Disease"),
        ("prev_preeclampsia", "Previous_PreEclampsia"), ("prev_gdm", "Previous_GDM"),
        ("multiple", "Multiple_Pregnancy"), ("haemoglobinopathy", "Known_Haemoglobinopathy"),
    ]:
        b[new] = yes(d1[col])
    b["smoker"] = d1["Smoking_Status"].isin(["Current", "Former"]).astype(int)
    b["rural"] = (d1["Residence_Type"] == "Rural").astype(int)
    return b


def _lab_flags_per_visit(d3: pd.DataFrame) -> pd.DataFrame:
    t = d3["Test_Name"]
    f = pd.DataFrame({"Visit_ID": d3["Visit_ID"]})
    f["hb_val"] = np.where(t == "Haemoglobin", d3["Result_Num"], np.nan)
    f["abn"] = d3["Is_Abnormal"].astype(int)
    f["gdm_abn"] = (t.isin(["GDM_Screening", "Two_Hour_Glucose", "Fasting_Glucose"]) & d3["Is_Abnormal"]).astype(int)
    f["proteinuria"] = ((t == "Urine_Protein") & d3["Is_Abnormal"]).astype(int)
    f["tsh_abn"] = ((t == "TSH") & d3["Is_Abnormal"]).astype(int)
    f["infection_pos"] = (t.isin(["HIV_Test", "Syphilis_Test", "Hepatitis_B_HBsAg",
                                  "Group_B_Streptococcus_Swab"]) & d3["Is_Abnormal"]).astype(int)
    f["growth_concern"] = (t.isin(["Fetal_Growth_Assessment", "Structural_Anomaly_Scan",
                                   "Placental_Assessment"]) & d3["Is_Abnormal"]).astype(int)
    return f.groupby("Visit_ID").agg(
        hb_visit=("hb_val", "min"), n_abn=("abn", "sum"), gdm_abn=("gdm_abn", "max"),
        proteinuria=("proteinuria", "max"), tsh_abn=("tsh_abn", "max"),
        infection_pos=("infection_pos", "max"), growth_concern=("growth_concern", "max"),
    )


def _med_flags_per_visit(d4: pd.DataFrame) -> pd.DataFrame:
    g = d4["Generic_Name"].str.lower()
    f = pd.DataFrame({"Visit_ID": d4["Visit_ID"]})
    f["aspirin"] = g.str.contains("aspirin").astype(int)
    f["antihypertensive"] = (g.str.contains("labetalol|nifedipine|antihypertensive|methyldopa")).astype(int)
    f["therapeutic_iron"] = (d4["Event_Type"] == "Therapeutic supplementation").astype(int)
    f["levothyroxine"] = g.str.contains("levothyroxine").astype(int)
    f["metformin"] = g.str.contains("metformin|insulin").astype(int)
    return f.groupby("Visit_ID").max()


def build_visit_features(data: MaternalData) -> pd.DataFrame:
    v = data.visits.copy()
    v = v.merge(_baseline(data.patients), on="Pregnancy_ID", how="left")

    v["ga_weeks"] = v["GA_Weeks"]
    v["sbp"], v["dbp"], v["spo2"] = v["SBP_mmHg"], v["DBP_mmHg"], v["SpO2_percent"]
    first_w = v.groupby("Pregnancy_ID")["Weight_kg"].transform("first")
    v["weight_gain"] = v["Weight_kg"] - first_w
    v["oedema"] = v["Oedema"].map({"Absent": 0, "Mild": 1, "Moderate": 2, "Severe": 3}).fillna(0)
    v["risk_level"] = v["Risk_Level"].map({"Low": 0, "Moderate": 1, "High": 2}).fillna(0)

    g = v.groupby("Pregnancy_ID")
    v["max_sbp"] = g["SBP_mmHg"].cummax()
    v["max_dbp"] = g["DBP_mmHg"].cummax()
    v["n_bp140"] = (v["SBP_mmHg"] >= 140).astype(int).groupby(v["Pregnancy_ID"]).cumsum()
    v["n_high_risk"] = yes(v["High_Risk_Visit"]).groupby(v["Pregnancy_ID"]).cumsum()
    v["n_referrals"] = yes(v["Referral_Required"]).groupby(v["Pregnancy_ID"]).cumsum()
    v["n_additional"] = (v["Visit_Type"] == "Additional_ANC").astype(int).groupby(v["Pregnancy_ID"]).cumsum()
    v["reduced_fm_ever"] = (v["Fetal_Movement_Status"] == "Reduced").astype(int).groupby(v["Pregnancy_ID"]).cummax()
    v["fetal_concern_ever"] = (v["Fetal_Status"] != "Stable").astype(int).groupby(v["Pregnancy_ID"]).cummax()
    v["malpresentation"] = v["Fetal_Presentation"].isin(["Breech", "Transverse"]).astype(int) \
        .groupby(v["Pregnancy_ID"]).cummax()

    # ---- labs up to and including this visit
    labs = _lab_flags_per_visit(data.labs)
    v = v.merge(labs, left_on="Visit_ID", right_index=True, how="left")
    g = v.groupby("Pregnancy_ID")
    v["min_hb"] = g["hb_visit"].cummin()
    v["latest_hb"] = g["hb_visit"].ffill()
    first_hb = g["hb_visit"].transform(lambda s: s.ffill().bfill().iloc[0] if s.notna().any() else np.nan)
    # first_hb uses bfill only to find the first measured value; for visits
    # before any Hb exists latest_hb is NaN, so hb_drop stays NaN there.
    v["hb_drop"] = first_hb - v["latest_hb"]
    v["n_abnormal_labs"] = v["n_abn"].fillna(0).groupby(v["Pregnancy_ID"]).cumsum()
    for c in ["gdm_abn", "proteinuria", "tsh_abn", "infection_pos", "growth_concern"]:
        v[c] = v[c].fillna(0).groupby(v["Pregnancy_ID"]).cummax()

    # ---- medications started at or before this visit
    meds = _med_flags_per_visit(data.meds)
    v = v.merge(meds, left_on="Visit_ID", right_index=True, how="left")
    for c in ["aspirin", "antihypertensive", "therapeutic_iron", "levothyroxine", "metformin"]:
        v[c] = v[c].fillna(0).groupby(v["Pregnancy_ID"]).cummax()

    keep = ["Visit_ID", "Pregnancy_ID", "Patient_ID", "Visit_Date", "Visit_No"] + FEATURES
    return v[keep].reset_index(drop=True)
