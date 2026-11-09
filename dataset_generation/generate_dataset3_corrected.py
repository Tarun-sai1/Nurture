# ============================================================
# DATASET 3 GENERATOR
# Maternal Health Project
#
# Dataset 3: Laboratory & Investigations
# Grain: 1 row = 1 investigation/test performed
#
# Inputs:
#   Dataset 1 - Patient & Pregnancy
#   Dataset 2 - ANC Clinical & Vitals
#
# Outputs:
#   laboratory_investigations.csv
#   laboratory_investigations.xlsx
#   dataset3_summary.txt
#   dataset3_validation_report.txt
#
# IMPORTANT:
#   Urine protein/proteinuria is schedule-driven, not randomly
#   omitted. Full urinalysis is not incorrectly forced at every
#   ANC visit.
# ============================================================

import os
import random
from datetime import datetime

import numpy as np
import pandas as pd


# ============================================================
# 1. PATHS / CONFIGURATION
# ============================================================

PROJECT_ROOT = os.environ.get("MH_PROJECT", r"D:\Maternal_Health_Project")

DATASET1_PATH = os.path.join(
    PROJECT_ROOT,
    "datasets",
    "dataset1_patient_pregnancy",
    "patient_pregnancy.csv"
)

DATASET2_PATH = os.path.join(
    PROJECT_ROOT,
    "datasets",
    "dataset2_anc_clinical_vitals",
    "anc_clinical_vitals.csv"
)

OUTPUT_DIR = os.path.join(
    PROJECT_ROOT,
    "datasets",
    "dataset3_laboratory_investigations"
)

CSV_OUTPUT = os.path.join(
    OUTPUT_DIR,
    "laboratory_investigations.csv"
)

EXCEL_OUTPUT = os.path.join(
    OUTPUT_DIR,
    "laboratory_investigations.xlsx"
)

SUMMARY_OUTPUT = os.path.join(
    OUTPUT_DIR,
    "dataset3_summary.txt"
)

VALIDATION_OUTPUT = os.path.join(
    OUTPUT_DIR,
    "dataset3_validation_report.txt"
)

SEED = 20261008

random.seed(SEED)
rng = np.random.default_rng(SEED)

os.makedirs(OUTPUT_DIR, exist_ok=True)


# ============================================================
# 2. LOAD INPUT DATASETS
# ============================================================

print("=" * 70)
print("DATASET 3 - LABORATORY & INVESTIGATIONS GENERATOR")
print("=" * 70)

print("\nLoading Dataset 1...")

if not os.path.exists(DATASET1_PATH):
    raise FileNotFoundError(
        f"Dataset 1 not found:\n{DATASET1_PATH}"
    )

df_patient = pd.read_csv(DATASET1_PATH)

print(f"Dataset 1 loaded: {len(df_patient):,} pregnancies")

print("\nLoading Dataset 2...")

if not os.path.exists(DATASET2_PATH):
    raise FileNotFoundError(
        f"Dataset 2 not found:\n{DATASET2_PATH}"
    )

df_anc = pd.read_csv(DATASET2_PATH)

print(f"Dataset 2 loaded: {len(df_anc):,} ANC visits")


# ============================================================
# 3. REQUIRED COLUMN CHECK
# ============================================================

required_d1 = [
    "Patient_ID",
    "Pregnancy_ID",
    "Age_Years",
    "Pre_Pregnancy_BMI",
    "LMP_Date",
    "EDD_Date",
    "Preexisting_Hypertension",
    "Preexisting_Diabetes",
    "Thyroid_Disease",
    "Renal_Disease",
    "Known_Haemoglobinopathy",
    "Previous_GDM",
    "Previous_PreEclampsia",
    "Multiple_Pregnancy",
    "Number_of_Fetuses",
    "ABO_Group",
    "RhD_Status",
    "HIV_Status",
    "Hepatitis_B_Status",
]

required_d2 = [
    "Patient_ID",
    "Pregnancy_ID",
    "Visit_ID",
    "Visit_Date",
    "Gestational_Week",
    "Gestational_Days",
    "Trimester",
    "Visit_Type",
    "High_Risk_Visit",
    "Unscheduled_Visit",
    "Weight_kg",
    "SBP_mmHg",
    "DBP_mmHg",
    "Risk_Level",
    "Symptoms_Present",
    "Symptoms",
]

missing_d1 = [c for c in required_d1 if c not in df_patient.columns]
missing_d2 = [c for c in required_d2 if c not in df_anc.columns]

if missing_d1:
    raise ValueError(
        "Dataset 1 is missing required columns:\n"
        + "\n".join(missing_d1)
    )

if missing_d2:
    raise ValueError(
        "Dataset 2 is missing required columns:\n"
        + "\n".join(missing_d2)
    )


# ============================================================
# 4. TYPE CONVERSION
# ============================================================

for col in ["LMP_Date", "EDD_Date"]:
    df_patient[col] = pd.to_datetime(
        df_patient[col],
        errors="coerce"
    )

for col in ["Visit_Date", "Next_Visit_Date"]:
    if col in df_anc.columns:
        df_anc[col] = pd.to_datetime(
            df_anc[col],
            errors="coerce"
        )

for col in [
    "Age_Years",
    "Pre_Pregnancy_BMI",
    "Number_of_Fetuses",
]:
    df_patient[col] = pd.to_numeric(
        df_patient[col],
        errors="coerce"
    )

for col in [
    "Gestational_Week",
    "Gestational_Days",
    "Weight_kg",
    "SBP_mmHg",
    "DBP_mmHg",
]:
    df_anc[col] = pd.to_numeric(
        df_anc[col],
        errors="coerce"
    )


# ============================================================
# 5. MERGE PATIENT INFORMATION INTO ANC VISITS
# ============================================================

merge_columns = [
    "Patient_ID",
    "Pregnancy_ID",
    "Age_Years",
    "Pre_Pregnancy_BMI",
    "Preexisting_Hypertension",
    "Preexisting_Diabetes",
    "Thyroid_Disease",
    "Renal_Disease",
    "Known_Haemoglobinopathy",
    "Previous_GDM",
    "Previous_PreEclampsia",
    "Multiple_Pregnancy",
    "Number_of_Fetuses",
    "ABO_Group",
    "RhD_Status",
    "HIV_Status",
    "Hepatitis_B_Status",
]

df = df_anc.merge(
    df_patient[merge_columns],
    on=["Patient_ID", "Pregnancy_ID"],
    how="left",
    validate="many_to_one"
)


# ============================================================
# 6. HELPER FUNCTIONS
# ============================================================

def clean_bool(value):
    if pd.isna(value):
        return False

    if isinstance(value, bool):
        return value

    text = str(value).strip().lower()

    return text in {
        "true",
        "yes",
        "y",
        "1",
        "positive",
        "present",
    }


def normal_value(
    mean,
    sd,
    minimum=None,
    maximum=None
):
    value = rng.normal(mean, sd)

    if minimum is not None:
        value = max(value, minimum)

    if maximum is not None:
        value = min(value, maximum)

    return value


def round_value(value, decimals=2):
    if pd.isna(value):
        return np.nan

    return round(float(value), decimals)


def gestational_age_string(week, days):
    return f"{int(week)}w{int(days)}d"


def has_condition(row, column):
    if column not in row.index:
        return False

    return clean_bool(row[column])


def has_hypertension(row):
    sbp = float(row["SBP_mmHg"])
    dbp = float(row["DBP_mmHg"])

    return (
        has_condition(row, "Preexisting_Hypertension")
        or sbp >= 140
        or dbp >= 90
    )


def has_diabetes_risk(row):
    return (
        has_condition(row, "Preexisting_Diabetes")
        or has_condition(row, "Previous_GDM")
    )


def has_renal_risk(row):
    return has_condition(row, "Renal_Disease")


def has_thyroid_risk(row):
    return has_condition(row, "Thyroid_Disease")


def has_haematological_risk(row):
    return has_condition(row, "Known_Haemoglobinopathy")


# ============================================================
# 7. URINE PROTEIN SCHEDULE
# ============================================================
#
# Source-supported ANC urine protein/proteinuria checks:
#
#   Booking / early ANC
#   16 weeks
#   25 weeks
#   28 weeks
#   31 weeks
#   34 weeks
#   36 weeks
#   38 weeks
#   40 weeks
#   41 weeks
#
# For additional/high-risk/unscheduled visits, proteinuria
# may also be assessed.
#
# ============================================================

URINE_PROTEIN_SCHEDULED_WEEKS = {
    16,
    25,
    28,
    31,
    34,
    36,
    38,
    40,
    41,
}


def urine_protein_due(week, visit_type):
    week = int(week)
    visit_text = str(visit_type).strip().lower()

    # Any ANC visit at or before 12 weeks is treated as
    # the booking/early pregnancy assessment.
    if week <= 12:
        return True

    if week in URINE_PROTEIN_SCHEDULED_WEEKS:
        return True

    # Additional/high-risk/unscheduled visits
    if (
        "high" in visit_text
        or "unscheduled" in visit_text
        or "urgent" in visit_text
    ):
        return True

    return False


# ============================================================
# 8. INVESTIGATION STORAGE
# ============================================================

investigations = []


def add_investigation(
    visit_row,
    test_category,
    test_name,
    specimen_type,
    result,
    unit="",
    reference_range="",
    abnormal_flag="Normal",
    performed_reason="Routine ANC",
):
    week = int(visit_row["Gestational_Week"])
    days = int(visit_row["Gestational_Days"])

    investigation_id = (
        f"{visit_row['Visit_ID']}_"
        f"{len(investigations) + 1:04d}"
    )

    investigations.append({
        "Investigation_ID": investigation_id,
        "Patient_ID": visit_row["Patient_ID"],
        "Pregnancy_ID": visit_row["Pregnancy_ID"],
        "Visit_ID": visit_row["Visit_ID"],
        "Investigation_Date": visit_row["Visit_Date"],
        "Gestational_Week": week,
        "Gestational_Days": days,
        "Gestational_Age": gestational_age_string(
            week,
            days
        ),
        "Trimester": visit_row["Trimester"],
        "Test_Category": test_category,
        "Test_Name": test_name,
        "Specimen_Type": specimen_type,
        "Result": result,
        "Unit": unit,
        "Reference_Range": reference_range,
        "Abnormal_Flag": abnormal_flag,
        "Performed_Reason": performed_reason,
    })


# ============================================================
# 9. HAEMATOLOGY
# ============================================================

def generate_hb(row, week):
    base = 12.2

    if week >= 20:
        base -= 0.3

    if week >= 28:
        base -= 0.2

    if week >= 32:
        base -= 0.1

    if has_haematological_risk(row):
        base -= 1.5

    value = normal_value(
        base,
        0.45,
        minimum=7.0,
        maximum=15.5,
    )

    if value < 10:
        flag = "Low"
    elif value < 11:
        flag = "Borderline_Low"
    else:
        flag = "Normal"

    return round_value(value, 1), flag


def generate_rbc(row, week):
    base = 4.15

    if week >= 20:
        base -= 0.15

    if has_haematological_risk(row):
        base -= 0.35

    value = normal_value(
        base,
        0.25,
        minimum=2.5,
        maximum=5.5,
    )

    flag = "Low" if value < 3.8 else "Normal"

    return round_value(value, 2), flag


def generate_wbc(row, week):
    base = 8.5

    if week >= 20:
        base += 0.8

    value = normal_value(
        base,
        1.5,
        minimum=4.0,
        maximum=18.0,
    )

    flag = "High" if value > 15 else "Normal"

    return round_value(value, 1), flag


def generate_platelets(row, week):
    base = 250

    if week >= 28:
        base -= 15

    if has_hypertension(row):
        base -= 10

    value = normal_value(
        base,
        25,
        minimum=70,
        maximum=400,
    )

    flag = "Low" if value < 150 else "Normal"

    return round_value(value, 0), flag


def generate_mcv(row):
    base = 78 if has_haematological_risk(row) else 86

    value = normal_value(
        base,
        4,
        minimum=60,
        maximum=105,
    )

    if value < 80:
        flag = "Low"
    elif value > 100:
        flag = "High"
    else:
        flag = "Normal"

    return round_value(value, 1), flag


def generate_mch(row):
    base = 26 if has_haematological_risk(row) else 29

    value = normal_value(
        base,
        2,
        minimum=20,
        maximum=35,
    )

    if value < 27:
        flag = "Low"
    elif value > 33:
        flag = "High"
    else:
        flag = "Normal"

    return round_value(value, 1), flag


def generate_mchc(row):
    base = 32 if has_haematological_risk(row) else 33

    value = normal_value(
        base,
        1.2,
        minimum=27,
        maximum=37,
    )

    if value < 32:
        flag = "Low"
    elif value > 36:
        flag = "High"
    else:
        flag = "Normal"

    return round_value(value, 1), flag


# ============================================================
# 10. GLUCOSE
# ============================================================

def generate_fasting_glucose(row, week):
    base = 82

    if has_diabetes_risk(row):
        base += 12

    if week >= 24 and has_diabetes_risk(row):
        base += 5

    value = normal_value(
        base,
        8,
        minimum=55,
        maximum=180,
    )

    if value >= 126:
        flag = "High"
    elif value >= 100:
        flag = "Borderline_High"
    else:
        flag = "Normal"

    return round_value(value, 1), flag


def generate_two_hour_glucose(row):
    base = 105

    if has_diabetes_risk(row):
        base += 30

    value = normal_value(
        base,
        15,
        minimum=70,
        maximum=220,
    )

    if value >= 140:
        flag = "High"
    elif value >= 120:
        flag = "Borderline_High"
    else:
        flag = "Normal"

    return round_value(value, 1), flag


def generate_gdm_screening(row):
    base = 115

    if has_diabetes_risk(row):
        base += 35

    value = normal_value(
        base,
        18,
        minimum=70,
        maximum=220,
    )

    if value >= 140:
        result = "Abnormal"
        flag = "Abnormal"
    else:
        result = "Normal"
        flag = "Normal"

    return round_value(value, 1), result, flag


# ============================================================
# 11. URINE
# ============================================================

def generate_urine_protein(row):
    # Proteinuria is more likely in hypertensive pregnancies.
    probability = 0.20 if has_hypertension(row) else 0.04

    if rng.random() < probability:
        if (
            has_hypertension(row)
            and rng.random() < 0.25
        ):
            return "2+", "Abnormal"

        return "1+", "Abnormal"

    return "Negative", "Normal"


def generate_urine_glucose(row):
    if (
        has_diabetes_risk(row)
        and rng.random() < 0.15
    ):
        return "Positive", "Abnormal"

    return "Negative", "Normal"


def generate_urine_leukocytes(row):
    if rng.random() < 0.08:
        return "Positive", "Abnormal"

    return "Negative", "Normal"


def generate_urine_nitrite(row):
    if rng.random() < 0.04:
        return "Positive", "Abnormal"

    return "Negative", "Normal"


# ============================================================
# 12. INFECTION SCREENING
# ============================================================

def infection_result(
    baseline_status,
    positive_probability=0.01,
):
    if pd.notna(baseline_status):
        text = str(baseline_status).strip().lower()

        if text in {
            "positive",
            "reactive",
            "detected",
        }:
            return "Positive", "Abnormal"

        if text in {
            "negative",
            "non-reactive",
            "not detected",
        }:
            return "Negative", "Normal"

    if rng.random() < positive_probability:
        return "Positive", "Abnormal"

    return "Negative", "Normal"


# ============================================================
# 13. THYROID / RENAL
# ============================================================

def generate_tsh(row):
    base = 2.8 if has_thyroid_risk(row) else 2.0

    value = normal_value(
        base,
        0.6,
        minimum=0.1,
        maximum=8.0,
    )

    if value > 4.0:
        flag = "High"
    elif value < 0.3:
        flag = "Low"
    else:
        flag = "Normal"

    return round_value(value, 2), flag


def generate_creatinine(row):
    base = 1.07 if has_renal_risk(row) else 0.72

    value = normal_value(
        base,
        0.12,
        minimum=0.35,
        maximum=3.0,
    )

    flag = "High" if value > 1.1 else "Normal"

    return round_value(value, 2), flag


# ============================================================
# 14. ULTRASOUND
# ============================================================

def add_ultrasound_if_due(row):
    week = int(row["Gestational_Week"])

    # Booking / dating scan
    if week <= 12:
        if int(row["Number_of_Fetuses"]) == 1:
            result = "Singleton viable intrauterine pregnancy"
        else:
            result = (
                f"{int(row['Number_of_Fetuses'])}-fetus pregnancy"
            )

        add_investigation(
            row,
            "Ultrasound",
            "Booking_Dating_Ultrasound",
            "Imaging",
            result,
            reference_range="Viable intrauterine pregnancy",
            abnormal_flag="Normal",
            performed_reason="Booking/early pregnancy assessment",
        )

    # Structural anomaly scan
    if 18 <= week <= 22:
        if rng.random() < 0.05:
            result = (
                "Minor/indeterminate finding requiring follow-up"
            )
            flag = "Abnormal"
        else:
            result = (
                "No major structural abnormality identified"
            )
            flag = "Normal"

        add_investigation(
            row,
            "Ultrasound",
            "Structural_Anomaly_Scan",
            "Imaging",
            result,
            reference_range=(
                "Expected fetal anatomy for gestational age"
            ),
            abnormal_flag=flag,
            performed_reason="Mid-trimester structural assessment",
        )

    # Growth scan for selected high-risk pregnancies
    if (
        week >= 28
        and (
            has_condition(row, "Multiple_Pregnancy")
            or has_hypertension(row)
            or str(row["Risk_Level"]).strip().lower() == "high"
        )
    ):
        if rng.random() < 0.08:
            result = "Growth measurement requires follow-up"
            flag = "Abnormal"
        else:
            result = (
                "Fetal growth appropriate for gestational age"
            )
            flag = "Normal"

        add_investigation(
            row,
            "Ultrasound",
            "Fetal_Growth_Assessment",
            "Imaging",
            result,
            reference_range=(
                "Appropriate growth for gestational age"
            ),
            abnormal_flag=flag,
            performed_reason=(
                "High-risk/fetal growth monitoring"
            ),
        )

    # Placental assessment if Dataset 2 indicates concern
    if (
        week >= 36
        and "Placental_Concern" in row.index
        and clean_bool(row["Placental_Concern"])
    ):
        add_investigation(
            row,
            "Ultrasound",
            "Placental_Assessment",
            "Imaging",
            "Placental location/relationship assessed",
            reference_range=(
                "No clinically significant placental concern"
            ),
            abnormal_flag="Normal",
            performed_reason="Previous placental concern",
        )


# ============================================================
# 15. GBS
# ============================================================

def add_gbs_if_due(row):
    week = int(row["Gestational_Week"])

    if week == 36:
        if rng.random() < 0.15:
            result = "Positive"
            flag = "Abnormal"
        else:
            result = "Negative"
            flag = "Normal"

        add_investigation(
            row,
            "Infection_Screening",
            "Group_B_Streptococcus_Swab",
            "Vaginal/Rectal_Swab",
            result,
            reference_range="Negative",
            abnormal_flag=flag,
            performed_reason="Late-pregnancy GBS screening",
        )


# ============================================================
# 16. GENERATE INVESTIGATIONS
# ============================================================

print("\nGenerating investigations...")

processed_visits = 0

sort_columns = [
    "Patient_ID",
    "Pregnancy_ID",
    "Visit_Date",
]

for _, row in df.sort_values(
    by=sort_columns
).iterrows():

    processed_visits += 1

    week = int(row["Gestational_Week"])
    is_booking = week <= 12

    # --------------------------------------------------------
    # A. BLOOD GROUP / RH
    # --------------------------------------------------------

    if is_booking:
        add_investigation(
            row,
            "Blood_Group",
            "ABO_Group",
            "Blood",
            row["ABO_Group"],
            reference_range="A/B/AB/O",
            abnormal_flag="Normal",
            performed_reason="Booking blood group assessment",
        )

        add_investigation(
            row,
            "Blood_Group",
            "RhD_Status",
            "Blood",
            row["RhD_Status"],
            reference_range="RhD positive or negative",
            abnormal_flag="Normal",
            performed_reason="Booking RhD assessment",
        )

    # --------------------------------------------------------
    # B. CBC / HAEMATOLOGY
    # --------------------------------------------------------

    if (
        is_booking
        or week == 28
        or (
            week >= 16
            and has_haematological_risk(row)
            and rng.random() < 0.35
        )
    ):
        hb, flag = generate_hb(row, week)

        add_investigation(
            row,
            "Haematology",
            "Haemoglobin",
            "Blood",
            hb,
            unit="g/dL",
            reference_range="Pregnancy-specific reference",
            abnormal_flag=flag,
            performed_reason=(
                "Booking anaemia screening"
                if is_booking
                else "Repeat anaemia screening/monitoring"
            ),
        )

        rbc, flag = generate_rbc(row, week)

        add_investigation(
            row,
            "Haematology",
            "RBC_Count",
            "Blood",
            rbc,
            unit="10^12/L",
            reference_range="Pregnancy-specific reference",
            abnormal_flag=flag,
            performed_reason="Complete blood count",
        )

        wbc, flag = generate_wbc(row, week)

        add_investigation(
            row,
            "Haematology",
            "WBC_Count",
            "Blood",
            wbc,
            unit="10^9/L",
            reference_range="Pregnancy-specific reference",
            abnormal_flag=flag,
            performed_reason="Complete blood count",
        )

        platelets, flag = generate_platelets(row, week)

        add_investigation(
            row,
            "Haematology",
            "Platelet_Count",
            "Blood",
            platelets,
            unit="10^9/L",
            reference_range="150-400 x10^9/L",
            abnormal_flag=flag,
            performed_reason="Complete blood count",
        )

        mcv, flag = generate_mcv(row)

        add_investigation(
            row,
            "Haematology",
            "MCV",
            "Blood",
            mcv,
            unit="fL",
            reference_range="80-100 fL",
            abnormal_flag=flag,
            performed_reason="Red cell indices",
        )

        mch, flag = generate_mch(row)

        add_investigation(
            row,
            "Haematology",
            "MCH",
            "Blood",
            mch,
            unit="pg",
            reference_range="27-33 pg",
            abnormal_flag=flag,
            performed_reason="Red cell indices",
        )

        mchc, flag = generate_mchc(row)

        add_investigation(
            row,
            "Haematology",
            "MCHC",
            "Blood",
            mchc,
            unit="g/dL",
            reference_range="32-36 g/dL",
            abnormal_flag=flag,
            performed_reason="Red cell indices",
        )

    # --------------------------------------------------------
    # C. HAEMOGLOBIN ELECTROPHORESIS
    # --------------------------------------------------------

    if is_booking:
        if has_haematological_risk(row):
            result = (
                "Variant/haemoglobinopathy pattern identified"
            )
            flag = "Abnormal"
        else:
            result = "HbAA pattern"
            flag = "Normal"

        add_investigation(
            row,
            "Haematology",
            "Hb_Electrophoresis",
            "Blood",
            result,
            reference_range=(
                "No clinically significant haemoglobinopathy"
            ),
            abnormal_flag=flag,
            performed_reason=(
                "Booking haemoglobinopathy screening"
            ),
        )

    # --------------------------------------------------------
    # D. IDCT FOR RH-NEGATIVE PREGNANCY
    # --------------------------------------------------------

    rh_status = str(row["RhD_Status"]).strip().lower()

    if is_booking and (
        rh_status in {
            "negative",
            "rhd negative",
            "rh negative",
        }
    ):
        result = (
            "Positive"
            if rng.random() < 0.05
            else "Negative"
        )

        flag = (
            "Abnormal"
            if result == "Positive"
            else "Normal"
        )

        add_investigation(
            row,
            "Immunohaematology",
            "Indirect_Antiglobulin_Test",
            "Blood",
            result,
            reference_range="Negative",
            abnormal_flag=flag,
            performed_reason=(
                "RhD-negative pregnancy assessment"
            ),
        )

    # --------------------------------------------------------
    # E. GDM SCREENING AT ~25 WEEKS
    # --------------------------------------------------------

    if week == 25:
        _, screening_result, screening_flag = (
            generate_gdm_screening(row)
        )

        add_investigation(
            row,
            "Glucose",
            "GDM_Screening",
            "Blood",
            screening_result,
            unit="mg/dL",
            reference_range="Screening threshold",
            abnormal_flag=screening_flag,
            performed_reason="Gestational diabetes screening",
        )

        fasting, flag = generate_fasting_glucose(row, week)

        add_investigation(
            row,
            "Glucose",
            "Fasting_Glucose",
            "Blood",
            fasting,
            unit="mg/dL",
            reference_range="Pregnancy-specific threshold",
            abnormal_flag=flag,
            performed_reason="GDM evaluation",
        )

        two_hour, flag = generate_two_hour_glucose(row)

        add_investigation(
            row,
            "Glucose",
            "Two_Hour_Glucose",
            "Blood",
            two_hour,
            unit="mg/dL",
            reference_range="Pregnancy-specific threshold",
            abnormal_flag=flag,
            performed_reason="GDM evaluation",
        )

    # --------------------------------------------------------
    # F. GLUCOSE FOLLOW-UP FOR DIABETES-RISK PATIENTS
    # --------------------------------------------------------

    if (
        week > 25
        and has_diabetes_risk(row)
        and rng.random() < 0.35
    ):
        fasting, flag = generate_fasting_glucose(row, week)

        add_investigation(
            row,
            "Glucose",
            "Fasting_Glucose",
            "Blood",
            fasting,
            unit="mg/dL",
            reference_range="Pregnancy-specific threshold",
            abnormal_flag=flag,
            performed_reason="Glycaemic monitoring",
        )

    # --------------------------------------------------------
    # G. URINE PROTEIN / PROTEINURIA
    # --------------------------------------------------------
    #
    # NO RANDOM 75% PROBABILITY.
    # This is schedule-driven.
    # --------------------------------------------------------

    if urine_protein_due(
        week,
        row["Visit_Type"]
    ):
        result, flag = generate_urine_protein(row)

        add_investigation(
            row,
            "Urine",
            "Urine_Protein",
            "Urine",
            result,
            reference_range="Negative",
            abnormal_flag=flag,
            performed_reason=(
                "Routine ANC proteinuria assessment"
            ),
        )

    # --------------------------------------------------------
    # H. FULLER URINALYSIS AT BOOKING
    # --------------------------------------------------------

    if is_booking:
        result, flag = generate_urine_glucose(row)

        add_investigation(
            row,
            "Urine",
            "Urine_Glucose",
            "Urine",
            result,
            reference_range="Negative",
            abnormal_flag=flag,
            performed_reason="Booking urinalysis",
        )

        result, flag = generate_urine_leukocytes(row)

        add_investigation(
            row,
            "Urine",
            "Urine_Leukocytes",
            "Urine",
            result,
            reference_range="Negative",
            abnormal_flag=flag,
            performed_reason="Booking urinalysis",
        )

        result, flag = generate_urine_nitrite(row)

        add_investigation(
            row,
            "Urine",
            "Urine_Nitrite",
            "Urine",
            result,
            reference_range="Negative",
            abnormal_flag=flag,
            performed_reason="Booking urinalysis",
        )

    # --------------------------------------------------------
    # I. URINE IN CASE OF URINARY SYMPTOMS
    # --------------------------------------------------------

    symptoms = str(row["Symptoms"]).lower()

    urinary_keywords = [
        "urinary",
        "dysuria",
        "burning",
        "frequency",
        "uti",
        "urine",
        "flank pain",
    ]

    urinary_symptoms = any(
        keyword in symptoms
        for keyword in urinary_keywords
    )

    if urinary_symptoms:
        result, flag = generate_urine_leukocytes(row)

        add_investigation(
            row,
            "Urine",
            "Urine_Leukocytes",
            "Urine",
            result,
            reference_range="Negative",
            abnormal_flag=flag,
            performed_reason="Urinary symptoms",
        )

        result, flag = generate_urine_nitrite(row)

        add_investigation(
            row,
            "Urine",
            "Urine_Nitrite",
            "Urine",
            result,
            reference_range="Negative",
            abnormal_flag=flag,
            performed_reason="Urinary symptoms",
        )

    # --------------------------------------------------------
    # J. HIV
    # --------------------------------------------------------

    if is_booking or week == 28:
        result, flag = infection_result(
            row["HIV_Status"],
            positive_probability=0.01,
        )

        add_investigation(
            row,
            "Infection_Screening",
            "HIV_Test",
            "Blood",
            result,
            reference_range="Negative",
            abnormal_flag=flag,
            performed_reason=(
                "Booking HIV screening"
                if is_booking
                else "Repeat HIV screening"
            ),
        )

    # --------------------------------------------------------
    # K. HEPATITIS B
    # --------------------------------------------------------

    if is_booking:
        result, flag = infection_result(
            row["Hepatitis_B_Status"],
            positive_probability=0.015,
        )

        add_investigation(
            row,
            "Infection_Screening",
            "Hepatitis_B_HBsAg",
            "Blood",
            result,
            reference_range="Negative",
            abnormal_flag=flag,
            performed_reason="Booking hepatitis B screening",
        )

    # --------------------------------------------------------
    # L. SYPHILIS
    # --------------------------------------------------------

    if is_booking or week == 28:
        result, flag = infection_result(
            None,
            positive_probability=0.01,
        )

        add_investigation(
            row,
            "Infection_Screening",
            "Syphilis_Test",
            "Blood",
            result,
            reference_range="Negative",
            abnormal_flag=flag,
            performed_reason=(
                "Booking syphilis screening"
                if is_booking
                else "Repeat syphilis screening"
            ),
        )

    # --------------------------------------------------------
    # M. RUBELLA
    # --------------------------------------------------------

    if is_booking:
        result = (
            "Immune"
            if rng.random() < 0.90
            else "Non-immune"
        )

        flag = (
            "Normal"
            if result == "Immune"
            else "Abnormal"
        )

        add_investigation(
            row,
            "Infection_Screening",
            "Rubella_Immunity",
            "Blood",
            result,
            reference_range="Immune",
            abnormal_flag=flag,
            performed_reason=(
                "Booking rubella immunity assessment"
            ),
        )

    # --------------------------------------------------------
    # N. THYROID
    # --------------------------------------------------------

    if is_booking and has_thyroid_risk(row):
        tsh, flag = generate_tsh(row)

        add_investigation(
            row,
            "Endocrine",
            "TSH",
            "Blood",
            tsh,
            unit="mIU/L",
            reference_range="Pregnancy-specific reference",
            abnormal_flag=flag,
            performed_reason="Known thyroid disease",
        )

    elif (
        week >= 16
        and has_thyroid_risk(row)
        and rng.random() < 0.40
    ):
        tsh, flag = generate_tsh(row)

        add_investigation(
            row,
            "Endocrine",
            "TSH",
            "Blood",
            tsh,
            unit="mIU/L",
            reference_range="Pregnancy-specific reference",
            abnormal_flag=flag,
            performed_reason="Thyroid disease monitoring",
        )

    # --------------------------------------------------------
    # O. RENAL FUNCTION
    # --------------------------------------------------------

    if is_booking and has_renal_risk(row):
        creatinine, flag = generate_creatinine(row)

        add_investigation(
            row,
            "Renal",
            "Serum_Creatinine",
            "Blood",
            creatinine,
            unit="mg/dL",
            reference_range="Pregnancy-specific reference",
            abnormal_flag=flag,
            performed_reason="Known renal disease",
        )

    elif (
        week >= 20
        and has_renal_risk(row)
        and rng.random() < 0.35
    ):
        creatinine, flag = generate_creatinine(row)

        add_investigation(
            row,
            "Renal",
            "Serum_Creatinine",
            "Blood",
            creatinine,
            unit="mg/dL",
            reference_range="Pregnancy-specific reference",
            abnormal_flag=flag,
            performed_reason="Renal disease monitoring",
        )

    # --------------------------------------------------------
    # P. ULTRASOUND
    # --------------------------------------------------------

    add_ultrasound_if_due(row)

    # --------------------------------------------------------
    # Q. GBS
    # --------------------------------------------------------

    add_gbs_if_due(row)


# ============================================================
# 17. BUILD FINAL DATAFRAME
# ============================================================

df_lab = pd.DataFrame(investigations)

if df_lab.empty:
    raise RuntimeError(
        "Dataset 3 generated zero investigation records."
    )

df_lab = df_lab.sort_values(
    by=[
        "Patient_ID",
        "Pregnancy_ID",
        "Investigation_Date",
        "Visit_ID",
        "Test_Category",
        "Test_Name",
    ]
).reset_index(drop=True)


# ============================================================
# 18. VALIDATION
# ============================================================

validation_messages = []

validation_messages.append(
    "DATASET 3 VALIDATION REPORT"
)

validation_messages.append("=" * 70)

validation_messages.append(
    f"Generated on: "
    f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
)

validation_messages.append(
    f"Random seed: {SEED}"
)

validation_messages.append("")

validation_messages.append(
    f"Dataset 1 pregnancies: {len(df_patient):,}"
)

validation_messages.append(
    f"Dataset 2 ANC visits: {len(df_anc):,}"
)

validation_messages.append(
    f"Dataset 3 investigations: {len(df_lab):,}"
)

validation_messages.append("")


# ------------------------------------------------------------
# Null check
# ------------------------------------------------------------

null_counts = df_lab.isna().sum()
null_columns = null_counts[null_counts > 0]

validation_messages.append("NULL VALUE CHECK")
validation_messages.append("-" * 50)

if len(null_columns) == 0:
    validation_messages.append(
        "PASS: No missing values in Dataset 3."
    )
else:
    validation_messages.append(
        "WARNING: Missing values found:"
    )

    for column, count in null_columns.items():
        validation_messages.append(
            f"  {column}: {count}"
        )

validation_messages.append("")


# ------------------------------------------------------------
# Duplicate ID check
# ------------------------------------------------------------

duplicate_ids = (
    df_lab["Investigation_ID"]
    .duplicated()
    .sum()
)

validation_messages.append("INVESTIGATION ID CHECK")
validation_messages.append("-" * 50)

if duplicate_ids == 0:
    validation_messages.append(
        "PASS: Investigation_ID values are unique."
    )
else:
    validation_messages.append(
        f"FAIL: {duplicate_ids} duplicate Investigation_ID values."
    )

validation_messages.append("")


# ------------------------------------------------------------
# Patient/Pregnancy linkage
# ------------------------------------------------------------

valid_patient_pairs = set(
    zip(
        df_patient["Patient_ID"],
        df_patient["Pregnancy_ID"],
    )
)

invalid_linkages = 0

for _, row in df_lab.iterrows():
    key = (
        row["Patient_ID"],
        row["Pregnancy_ID"],
    )

    if key not in valid_patient_pairs:
        invalid_linkages += 1

validation_messages.append(
    "PATIENT/PREGNANCY LINKAGE CHECK"
)

validation_messages.append("-" * 50)

if invalid_linkages == 0:
    validation_messages.append(
        "PASS: All Dataset 3 records link to Dataset 1."
    )
else:
    validation_messages.append(
        f"FAIL: {invalid_linkages} invalid patient/pregnancy links."
    )

validation_messages.append("")


# ------------------------------------------------------------
# ANC visit linkage
# ------------------------------------------------------------

valid_visits = set(
    zip(
        df_anc["Patient_ID"],
        df_anc["Pregnancy_ID"],
        df_anc["Visit_ID"],
    )
)

invalid_visit_links = 0

for _, row in df_lab.iterrows():
    key = (
        row["Patient_ID"],
        row["Pregnancy_ID"],
        row["Visit_ID"],
    )

    if key not in valid_visits:
        invalid_visit_links += 1

validation_messages.append("ANC VISIT LINKAGE CHECK")
validation_messages.append("-" * 50)

if invalid_visit_links == 0:
    validation_messages.append(
        "PASS: All Dataset 3 investigations link to Dataset 2."
    )
else:
    validation_messages.append(
        f"FAIL: {invalid_visit_links} invalid visit links."
    )

validation_messages.append("")


# ------------------------------------------------------------
# Urine protein validation
# ------------------------------------------------------------

validation_messages.append(
    "URINE PROTEIN SCHEDULE VALIDATION"
)

validation_messages.append("-" * 50)

urine_protein_df = df_lab[
    df_lab["Test_Name"] == "Urine_Protein"
].copy()

expected_urine_protein_visits = 0
missing_urine_protein_visits = []

for _, visit in df.iterrows():
    week = int(visit["Gestational_Week"])

    if urine_protein_due(
        week,
        visit["Visit_Type"]
    ):
        expected_urine_protein_visits += 1

        visit_id = visit["Visit_ID"]

        exists = (
            urine_protein_df["Visit_ID"]
            == visit_id
        ).any()

        if not exists:
            missing_urine_protein_visits.append(
                visit_id
            )

validation_messages.append(
    f"Expected urine-protein assessments: "
    f"{expected_urine_protein_visits:,}"
)

validation_messages.append(
    f"Generated urine-protein assessments: "
    f"{len(urine_protein_df):,}"
)

if not missing_urine_protein_visits:
    validation_messages.append(
        "PASS: No scheduled urine-protein assessment is missing."
    )
else:
    validation_messages.append(
        "FAIL: Missing urine-protein assessments:"
    )

    for visit_id in missing_urine_protein_visits[:20]:
        validation_messages.append(
            f"  {visit_id}"
        )

    if len(missing_urine_protein_visits) > 20:
        validation_messages.append(
            f"  ... and "
            f"{len(missing_urine_protein_visits) - 20} more"
        )

validation_messages.append("")


# ------------------------------------------------------------
# Gestational age check
# ------------------------------------------------------------

gestational_errors = 0

for _, row in df_lab.iterrows():
    week = int(row["Gestational_Week"])
    days = int(row["Gestational_Days"])

    if not 0 <= week <= 45:
        gestational_errors += 1

    if not 0 <= days <= 6:
        gestational_errors += 1

validation_messages.append(
    "GESTATIONAL AGE CHECK"
)

validation_messages.append("-" * 50)

if gestational_errors == 0:
    validation_messages.append(
        "PASS: Gestational ages are within valid ranges."
    )
else:
    validation_messages.append(
        f"FAIL: {gestational_errors} gestational-age errors."
    )

validation_messages.append("")


# ------------------------------------------------------------
# Date consistency check
# ------------------------------------------------------------

date_errors = 0

anc_visit_dates = (
    df_anc[
        [
            "Patient_ID",
            "Pregnancy_ID",
            "Visit_ID",
            "Visit_Date",
        ]
    ]
    .drop_duplicates(
        subset=[
            "Patient_ID",
            "Pregnancy_ID",
            "Visit_ID",
        ]
    )
)

visit_date_lookup = {
    (
        row["Patient_ID"],
        row["Pregnancy_ID"],
        row["Visit_ID"],
    ): row["Visit_Date"]
    for _, row in anc_visit_dates.iterrows()
}

for _, row in df_lab.iterrows():
    key = (
        row["Patient_ID"],
        row["Pregnancy_ID"],
        row["Visit_ID"],
    )

    expected_date = visit_date_lookup.get(key)

    if pd.notna(expected_date):
        actual_date = pd.Timestamp(
            row["Investigation_Date"]
        )

        expected_date = pd.Timestamp(expected_date)

        if actual_date != expected_date:
            date_errors += 1

validation_messages.append(
    "DATE CONSISTENCY CHECK"
)

validation_messages.append("-" * 50)

if date_errors == 0:
    validation_messages.append(
        "PASS: Investigation dates match ANC visit dates."
    )
else:
    validation_messages.append(
        f"FAIL: {date_errors} investigation-date mismatches."
    )

validation_messages.append("")


# ------------------------------------------------------------
# Test distributions
# ------------------------------------------------------------

category_counts = (
    df_lab["Test_Category"]
    .value_counts()
)

test_counts = (
    df_lab["Test_Name"]
    .value_counts()
)

abnormal_counts = (
    df_lab["Abnormal_Flag"]
    .value_counts()
)

validation_messages.append(
    "TEST CATEGORY DISTRIBUTION"
)

validation_messages.append("-" * 50)

for category, count in category_counts.items():
    validation_messages.append(
        f"{category}: {count:,}"
    )

validation_messages.append("")

validation_messages.append(
    "TEST NAME DISTRIBUTION"
)

validation_messages.append("-" * 50)

for test_name, count in test_counts.items():
    validation_messages.append(
        f"{test_name}: {count:,}"
    )

validation_messages.append("")

validation_messages.append(
    "ABNORMAL RESULT SUMMARY"
)

validation_messages.append("-" * 50)

for flag, count in abnormal_counts.items():
    validation_messages.append(
        f"{flag}: {count:,}"
    )

validation_messages.append("")


# ------------------------------------------------------------
# Specific test counts
# ------------------------------------------------------------

validation_messages.append(
    "CONDITION-SPECIFIC INVESTIGATION SUMMARY"
)

validation_messages.append("-" * 50)

validation_messages.append(
    f"TSH tests: "
    f"{(df_lab['Test_Name'] == 'TSH').sum():,}"
)

validation_messages.append(
    f"Serum creatinine tests: "
    f"{(df_lab['Test_Name'] == 'Serum_Creatinine').sum():,}"
)

validation_messages.append(
    f"Glucose investigations: "
    f"{(df_lab['Test_Category'] == 'Glucose').sum():,}"
)

validation_messages.append(
    f"GBS tests: "
    f"{(df_lab['Test_Name'] == 'Group_B_Streptococcus_Swab').sum():,}"
)

validation_messages.append(
    f"Ultrasound investigations: "
    f"{(df_lab['Test_Category'] == 'Ultrasound').sum():,}"
)

validation_messages.append("")


# ------------------------------------------------------------
# Final validation status
# ------------------------------------------------------------

critical_errors = (
    duplicate_ids
    + invalid_linkages
    + invalid_visit_links
    + len(missing_urine_protein_visits)
    + gestational_errors
    + date_errors
)

validation_messages.append("=" * 70)

if critical_errors == 0:
    validation_messages.append(
        "FINAL STATUS: PASS"
    )
    validation_messages.append(
        "Dataset 3 passed all critical structural checks."
    )
else:
    validation_messages.append(
        "FINAL STATUS: REVIEW REQUIRED"
    )
    validation_messages.append(
        f"Critical validation issues: {critical_errors}"
    )


# ============================================================
# 19. SAVE VALIDATION REPORT
# ============================================================

with open(
    VALIDATION_OUTPUT,
    "w",
    encoding="utf-8",
) as f:
    f.write(
        "\n".join(validation_messages)
    )


# ============================================================
# 20. CREATE SUMMARY
# ============================================================

summary_lines = [
    "DATASET 3 - LABORATORY & INVESTIGATIONS",
    "=" * 70,
    (
        f"Generated on: "
        f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    ),
    f"Random seed: {SEED}",
    "",
    "DATASET GRAIN",
    "1 row = 1 investigation/test performed.",
    "",
    "INPUT DATASETS",
    f"Dataset 1: {DATASET1_PATH}",
    f"Dataset 2: {DATASET2_PATH}",
    "",
    "OUTPUT",
    f"Total investigations: {len(df_lab):,}",
    (
        f"Unique pregnancies: "
        f"{df_lab['Pregnancy_ID'].nunique():,}"
    ),
    (
        f"Unique ANC visits represented: "
        f"{df_lab['Visit_ID'].nunique():,}"
    ),
    "",
    "URINE TESTING DESIGN",
    (
        "Urine protein/proteinuria is generated systematically "
        "at booking/early ANC and scheduled ANC weeks."
    ),
    (
        "Scheduled weeks: booking/early ANC, 16, 25, 28, "
        "31, 34, 36, 38, 40 and 41."
    ),
    (
        "Urine glucose, leukocytes and nitrite are not treated "
        "as mandatory at every ANC visit."
    ),
    (
        "They are generated at booking or when urinary symptoms "
        "make them clinically relevant."
    ),
    "",
    "TEST CATEGORIES",
]

for category, count in category_counts.items():
    summary_lines.append(
        f"{category}: {count:,}"
    )

summary_lines.extend([
    "",
    "TESTS",
])

for test_name, count in test_counts.items():
    summary_lines.append(
        f"{test_name}: {count:,}"
    )

summary_lines.extend([
    "",
    "VALIDATION",
    f"Critical validation errors: {critical_errors}",
    (
        "See dataset3_validation_report.txt "
        "for complete validation."
    ),
])

with open(
    SUMMARY_OUTPUT,
    "w",
    encoding="utf-8",
) as f:
    f.write(
        "\n".join(summary_lines)
    )


# ============================================================
# 21. SAVE CSV
# ============================================================

df_lab.to_csv(
    CSV_OUTPUT,
    index=False,
    encoding="utf-8-sig",
)


# ============================================================
# 22. SAVE EXCEL
# ============================================================
#
# IMPORTANT FIX:
#
# WRONG:
#     worksheet = writer["Laboratory_Investigations"]
#
# pandas.ExcelWriter itself is NOT subscriptable.
#
# CORRECT:
#     worksheet = writer.book["Laboratory_Investigations"]
#
# Dates are written as text to avoid Excel ###### display.
# ============================================================

df_excel = df_lab.copy()

df_excel["Investigation_Date"] = (
    pd.to_datetime(
        df_excel["Investigation_Date"],
        errors="coerce",
    )
    .dt.strftime("%d-%b-%Y")
)

with pd.ExcelWriter(
    EXCEL_OUTPUT,
    engine="openpyxl",
) as writer:

    df_excel.to_excel(
        writer,
        index=False,
        sheet_name="Laboratory_Investigations",
    )

    # CORRECT ACCESS TO THE OPENPYXL WORKSHEET
    worksheet = writer.book["Laboratory_Investigations"]

    # Freeze header
    worksheet.freeze_panes = "A2"

    # Enable filter
    worksheet.auto_filter.ref = worksheet.dimensions

    # Reasonable column widths
    for column_cells in worksheet.columns:

        column_letter = column_cells[0].column_letter

        max_length = 0

        for cell in column_cells:

            value = cell.value

            if value is None:
                length = 0
            else:
                length = len(str(value))

            max_length = max(
                max_length,
                length,
            )

        worksheet.column_dimensions[
            column_letter
        ].width = min(
            max(max_length + 2, 12),
            40,
        )


# ============================================================
# 23. FINAL CONSOLE OUTPUT
# ============================================================

print("\n" + "=" * 70)
print("DATASET 3 GENERATION COMPLETE")
print("=" * 70)

print(
    f"\nTotal ANC visits processed: "
    f"{processed_visits:,}"
)

print(
    f"Total investigations generated: "
    f"{len(df_lab):,}"
)

print(
    f"Unique pregnancies: "
    f"{df_lab['Pregnancy_ID'].nunique():,}"
)

print(
    f"Unique ANC visits represented: "
    f"{df_lab['Visit_ID'].nunique():,}"
)

print("\n--- Test Categories ---")

for category, count in category_counts.items():
    print(
        f"{category:<30} {count:,}"
    )

print("\n--- Urine Protein Check ---")

print(
    f"Expected urine-protein assessments: "
    f"{expected_urine_protein_visits:,}"
)

print(
    f"Generated urine-protein assessments: "
    f"{len(urine_protein_df):,}"
)

if not missing_urine_protein_visits:
    print("Urine protein schedule: PASS")
else:
    print("Urine protein schedule: FAIL")

print("\n--- Validation ---")

print(
    f"Critical validation errors: "
    f"{critical_errors}"
)

if critical_errors == 0:
    print("Validation status: PASS")
else:
    print("Validation status: REVIEW REQUIRED")

print("\n--- Files Created ---")

print(f"CSV:        {CSV_OUTPUT}")
print(f"Excel:      {EXCEL_OUTPUT}")
print(f"Summary:    {SUMMARY_OUTPUT}")
print(f"Validation: {VALIDATION_OUTPUT}")

print("\n" + "=" * 70)
