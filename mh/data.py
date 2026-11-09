"""
Data layer: loads the six raw datasets and their reference tables, and
fixes types once so every other module can rely on clean columns.

Rules
- Raw CSVs are read with keep_default_na=False so literal values such as
  "None" stay real categories; only empty strings become missing.
- Lab results keep the original text AND get a numeric copy (Result_Num).
- Every table carries Pregnancy_ID; event tables also carry Visit_ID.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "datasets"


def _read(rel: str) -> pd.DataFrame:
    df = pd.read_csv(RAW / rel, keep_default_na=False, na_values=[""], low_memory=False)
    for c in df.columns:
        # pandas >= 3 uses a dedicated string dtype, so test "not numeric"
        # rather than dtype == object.
        if not pd.api.types.is_numeric_dtype(df[c]):
            df[c] = df[c].fillna("").astype(object)
    return df


def _dates(df: pd.DataFrame, cols) -> pd.DataFrame:
    for c in cols:
        if c in df.columns:
            df[c] = pd.to_datetime(df[c], errors="coerce")
    return df


@dataclass
class MaternalData:
    patients: pd.DataFrame          # D1  one row per pregnancy
    visits: pd.DataFrame            # D2  one row per ANC visit
    labs: pd.DataFrame              # D3  one row per test
    meds: pd.DataFrame              # D4  one row per medication event
    med_master: pd.DataFrame
    med_interactions: pd.DataFrame
    med_allergy: pd.DataFrame
    nutrition: pd.DataFrame         # D5  one row per nutrition assessment
    food_recs: pd.DataFrame
    food_master: pd.DataFrame
    nutrition_rules: pd.DataFrame
    food_allergens: pd.DataFrame
    outcomes: pd.DataFrame          # D6  one row per pregnancy
    neonatal: pd.DataFrame
    maternal_events: pd.DataFrame


def load_data() -> MaternalData:
    d1 = _dates(_read("dataset1_patient_pregnancy/patient_pregnancy.csv"), ["LMP_Date", "EDD_Date"])

    d2 = _dates(_read("dataset2_anc_clinical_vitals/anc_clinical_vitals.csv"),
                ["Visit_Date", "Next_Visit_Date"])
    d2 = d2.sort_values(["Pregnancy_ID", "Visit_Date"]).reset_index(drop=True)
    d2["Visit_No"] = d2.groupby("Pregnancy_ID").cumcount() + 1
    d2["GA_Weeks"] = d2["Gestational_Week"] + d2["Gestational_Days"] / 7.0

    d3 = _dates(_read("dataset3_laboratory_investigations/laboratory_investigations.csv"),
                ["Investigation_Date"])
    d3["Result_Num"] = pd.to_numeric(d3["Result"], errors="coerce")
    d3["Is_Abnormal"] = ~d3["Abnormal_Flag"].isin(["Normal", ""])

    d4 = _dates(_read("dataset4_medication_treatment/medication_events.csv"), ["Event_Date"])

    d5 = _read("dataset5_nutrition_food/nutrition_assessments.csv")
    d5 = d5.merge(d2[["Visit_ID", "Visit_Date"]], on="Visit_ID", how="left")

    recs = _read("dataset5_nutrition_food/food_recommendation_events.csv")
    recs = recs.merge(d2[["Visit_ID", "Visit_Date"]], on="Visit_ID", how="left")

    d6 = _dates(_read("dataset6_outcome_delivery/outcome_delivery.csv"), ["Outcome_Date"])
    neo = _dates(_read("dataset6_outcome_delivery/neonatal_outcomes.csv"), ["Birth_Date"])
    mat = _read("dataset6_outcome_delivery/maternal_outcome_events.csv")

    return MaternalData(
        patients=d1, visits=d2, labs=d3, meds=d4,
        med_master=_read("dataset4_medication_treatment/medication_master_india.csv"),
        med_interactions=_read("dataset4_medication_treatment/medication_interaction_rules.csv"),
        med_allergy=_read("dataset4_medication_treatment/medication_allergy_crosswalk.csv"),
        nutrition=d5, food_recs=recs,
        food_master=_read("dataset5_nutrition_food/food_master_india.csv"),
        nutrition_rules=_read("dataset5_nutrition_food/nutrition_rulebook.csv"),
        food_allergens=_read("dataset5_nutrition_food/food_allergen_crosswalk.csv"),
        outcomes=d6, neonatal=neo, maternal_events=mat,
    )


def yes(s: pd.Series) -> pd.Series:
    """Map Yes/No-like text to 1/0."""
    return s.astype(str).str.strip().str.lower().isin(["yes", "true", "1", "y", "positive"]).astype(int)


def targets(data: MaternalData) -> pd.DataFrame:
    """Pregnancy-level labels used by the ML models."""
    o = data.outcomes[["Pregnancy_ID", "Gestational_Category", "Final_Gestational_Week"]].copy()
    o["preterm"] = (o["Gestational_Category"] == "Preterm birth").astype(int)
    o["gdm"] = yes(data.outcomes["Gestational_Diabetes_Outcome"])
    n = data.neonatal[["Pregnancy_ID", "NICU_Admission"]].copy()
    n["nicu"] = yes(n["NICU_Admission"])
    return o.merge(n[["Pregnancy_ID", "nicu"]], on="Pregnancy_ID", how="left")
