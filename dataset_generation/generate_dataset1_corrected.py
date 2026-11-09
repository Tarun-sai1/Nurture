# ============================================================
# DATASET 1 GENERATOR
# Maternal Health Project
#
# Dataset 1: Patient & Pregnancy Baseline
# Grain: 1 row = 1 pregnancy
#
# Adds:
#   Drug_Allergies
#   Drug_Allergy_Reaction
#   Current_Pre_Pregnancy_Medications
#   Previous_Medication_Adverse_Reaction
#
# Seed is kept at 20261008 so the 200-pregnancy cohort remains
# reproducible.
# ============================================================

import os
import random
from datetime import datetime, timedelta

import numpy as np
import pandas as pd


# ============================================================
# 1. CONFIGURATION
# ============================================================

PROJECT_ROOT = os.environ.get("MH_PROJECT", r"D:\Maternal_Health_Project")

OUTPUT_DIR = os.path.join(
    PROJECT_ROOT,
    "datasets",
    "dataset1_patient_pregnancy",
)

CSV_OUTPUT = os.path.join(
    OUTPUT_DIR,
    "patient_pregnancy.csv",
)

EXCEL_OUTPUT = os.path.join(
    OUTPUT_DIR,
    "patient_pregnancy.xlsx",
)

SUMMARY_OUTPUT = os.path.join(
    OUTPUT_DIR,
    "dataset1_summary.txt",
)

VALIDATION_OUTPUT = os.path.join(
    OUTPUT_DIR,
    "dataset1_validation_report.txt",
)

SEED = 20261008
N_PATIENTS = 200

random.seed(SEED)
rng = np.random.default_rng(SEED)

os.makedirs(OUTPUT_DIR, exist_ok=True)


# ============================================================
# 2. HELPER FUNCTIONS
# ============================================================

def weighted_choice(options, probabilities):
    return rng.choice(options, p=probabilities)


def yes_no(probability):
    return "Yes" if rng.random() < probability else "No"


def random_date(start_date, end_date):
    delta = (end_date - start_date).days
    return start_date + timedelta(
        days=int(rng.integers(0, delta + 1))
    )


def normal_value(mean, sd, minimum=None, maximum=None):
    value = rng.normal(mean, sd)

    if minimum is not None:
        value = max(value, minimum)

    if maximum is not None:
        value = min(value, maximum)

    return value


def calculate_bmi(weight_kg, height_cm):
    height_m = height_cm / 100.0
    return weight_kg / (height_m ** 2)


def format_date_for_excel(value):
    if pd.isna(value):
        return ""

    return pd.Timestamp(value).strftime("%d-%b-%Y")


# ============================================================
# 3. ARCHETYPES
# ============================================================

ARCHETYPES = [
    "Normal",
    "Anaemia_Risk",
    "GDM_Risk",
    "Hypertension_Risk",
    "Thyroid_Risk",
    "Renal_Risk",
    "High_Risk_Combined",
    "Multiple_Pregnancy",
    "Obstetric_History_Risk",
]

ARCHETYPE_WEIGHTS = [
    0.40,
    0.12,
    0.12,
    0.10,
    0.06,
    0.04,
    0.06,
    0.04,
    0.06,
]


# ============================================================
# 4. CONTROLLED VOCABULARIES
# ============================================================

RESIDENCE_TYPES = [
    "Urban",
    "Semi-Urban",
    "Rural",
]

DATING_METHODS = [
    "LMP",
    "First_Trimester_Ultrasound",
    "Second_Trimester_Ultrasound",
]

ABO_GROUPS = [
    "A",
    "B",
    "AB",
    "O",
]

RHD_STATUSES = [
    "Positive",
    "Negative",
]

HIV_STATUSES = [
    "Negative",
    "Positive",
]

HEPATITIS_B_STATUSES = [
    "Negative",
    "Positive",
]

SMOKING_STATUSES = [
    "Never",
    "Former",
    "Current",
]

ALCOHOL_USE = [
    "None",
    "Occasional",
    "Regular",
]

SUBSTANCE_USE = [
    "None",
    "Past",
    "Current",
]

PHYSICAL_ACTIVITY_LEVELS = [
    "Low",
    "Moderate",
    "High",
]

DIETARY_PATTERNS = [
    "Omnivorous",
    "Vegetarian",
    "Vegan",
    "Eggitarian",
]

DIETARY_RESTRICTIONS = [
    "None",
    "Religious",
    "Cultural",
    "Medical",
    "Personal",
]

FOOD_ALLERGY_OPTIONS = [
    "None",
    "Peanut",
    "Tree_Nuts",
    "Milk",
    "Egg",
    "Shellfish",
    "Fish",
    "Wheat",
    "Multiple",
]

DRUG_ALLERGY_OPTIONS = [
    "Penicillin",
    "Amoxicillin",
    "Cephalosporin",
    "Sulfonamide",
    "NSAIDs",
    "Aspirin",
    "Iron_Preparation",
    "Multiple",
]

ALLERGY_REACTIONS = [
    "Rash",
    "Urticaria",
    "Facial_Swelling",
    "Breathing_Difficulty",
    "Anaphylaxis",
]

MEDICATION_ADVERSE_REACTIONS = [
    "Nausea",
    "Vomiting",
    "Dizziness",
    "Headache",
    "Rash",
    "Gastrointestinal_Discomfort",
    "Hypoglycaemia",
]


# ============================================================
# 5. MEDICATION HISTORY
# ============================================================

def generate_baseline_medication_history(archetype):
    medications = []

    if archetype in {
        "Hypertension_Risk",
        "High_Risk_Combined",
    }:
        medications.append(
            weighted_choice(
                [
                    "Antihypertensive",
                    "No_Regular_Medication",
                ],
                [0.75, 0.25],
            )
        )

    if archetype == "Thyroid_Risk":
        medications.append("Levothyroxine")

    if archetype == "Renal_Risk":
        medications.append(
            weighted_choice(
                [
                    "Renal_Disease_Medication",
                    "No_Regular_Medication",
                ],
                [0.60, 0.40],
            )
        )

    if archetype == "GDM_Risk":
        medications.append(
            weighted_choice(
                [
                    "Metformin",
                    "No_Regular_Medication",
                ],
                [0.35, 0.65],
            )
        )

    if archetype == "Anaemia_Risk":
        medications.append(
            weighted_choice(
                [
                    "Iron_Supplement",
                    "Folic_Acid",
                    "No_Regular_Medication",
                ],
                [0.30, 0.20, 0.50],
            )
        )

    if not medications and rng.random() < 0.08:
        medications.append(
            weighted_choice(
                [
                    "Multivitamin",
                    "Analgesic_As_Needed",
                    "No_Regular_Medication",
                ],
                [0.30, 0.20, 0.50],
            )
        )

    if not medications:
        return "None"

    # Remove duplicates while preserving order.
    return "; ".join(dict.fromkeys(medications))


# ============================================================
# 6. DRUG ALLERGY
# ============================================================

def generate_drug_allergy():
    if rng.random() < 0.88:
        return "None", "None"

    allergy = weighted_choice(
        DRUG_ALLERGY_OPTIONS,
        [
            0.30,
            0.12,
            0.10,
            0.12,
            0.12,
            0.08,
            0.04,
            0.12,
        ],
    )

    reaction = weighted_choice(
        ALLERGY_REACTIONS,
        [
            0.55,
            0.25,
            0.08,
            0.08,
            0.04,
        ],
    )

    return allergy, reaction


# ============================================================
# 7. PREVIOUS MEDICATION ADVERSE REACTION
# ============================================================

def generate_previous_medication_adverse_reaction():
    if rng.random() < 0.12:
        return weighted_choice(
            MEDICATION_ADVERSE_REACTIONS,
            [
                0.20,
                0.12,
                0.10,
                0.10,
                0.08,
                0.20,
                0.20,
            ],
        )

    return "None"


# ============================================================
# 8. GENERATE 200 PREGNANCIES
# ============================================================

records = []

print("=" * 70)
print("DATASET 1 - PATIENT & PREGNANCY BASELINE GENERATOR")
print("=" * 70)
print(f"\nGenerating {N_PATIENTS} pregnancies...")

for i in range(1, N_PATIENTS + 1):

    patient_id = f"P{i:04d}"
    pregnancy_id = f"PRG{i:04d}"

    archetype = weighted_choice(
        ARCHETYPES,
        ARCHETYPE_WEIGHTS,
    )

    # --------------------------------------------------------
    # Demographics
    # --------------------------------------------------------

    if archetype == "Normal":
        age = int(rng.integers(21, 36))
    elif archetype in {
        "High_Risk_Combined",
        "Hypertension_Risk",
        "GDM_Risk",
    }:
        age = int(rng.integers(28, 41))
    else:
        age = int(rng.integers(19, 39))

    height_cm = round(
        float(
            normal_value(
                160,
                7,
                145,
                180,
            )
        ),
        1,
    )

    if archetype == "GDM_Risk":
        bmi = round(
            float(
                normal_value(
                    28.5,
                    4.0,
                    20,
                    40,
                )
            ),
            1,
        )
    elif archetype == "Hypertension_Risk":
        bmi = round(
            float(
                normal_value(
                    29.0,
                    4.0,
                    20,
                    42,
                )
            ),
            1,
        )
    elif archetype == "High_Risk_Combined":
        bmi = round(
            float(
                normal_value(
                    30.0,
                    4.5,
                    20,
                    45,
                )
            ),
            1,
        )
    elif archetype == "Anaemia_Risk":
        bmi = round(
            float(
                normal_value(
                    22.5,
                    3.5,
                    17,
                    34,
                )
            ),
            1,
        )
    else:
        bmi = round(
            float(
                normal_value(
                    24.5,
                    3.5,
                    17,
                    38,
                )
            ),
            1,
        )

    weight_kg = round(
        bmi * (height_cm / 100.0) ** 2,
        1,
    )

    bmi = round(
        calculate_bmi(
            weight_kg,
            height_cm,
        ),
        1,
    )

    residence_type = weighted_choice(
        RESIDENCE_TYPES,
        [0.55, 0.25, 0.20],
    )

    # --------------------------------------------------------
    # Pregnancy dates
    # --------------------------------------------------------

    lmp_start = datetime(2025, 1, 1)
    lmp_end = datetime(2026, 9, 1)

    lmp_date = random_date(
        lmp_start,
        lmp_end,
    )

    edd_date = lmp_date + timedelta(days=280)

    dating_method = weighted_choice(
        DATING_METHODS,
        [0.45, 0.45, 0.10],
    )

    # --------------------------------------------------------
    # Obstetric history
    # --------------------------------------------------------

    if age <= 24:
        gravida = int(
            weighted_choice(
                [1, 2, 3],
                [0.70, 0.25, 0.05],
            )
        )
    else:
        gravida = int(
            weighted_choice(
                [1, 2, 3, 4],
                [0.35, 0.35, 0.22, 0.08],
            )
        )

    max_previous_pregnancies = max(
        gravida - 1,
        0,
    )

    if max_previous_pregnancies == 0:
        para = 0
    else:
        para = int(
            rng.integers(
                0,
                max_previous_pregnancies + 1,
            )
        )

    previous_miscarriage = (
        yes_no(0.12)
        if max_previous_pregnancies > 0
        else "No"
    )

    previous_stillbirth = (
        yes_no(0.025)
        if max_previous_pregnancies > 0
        else "No"
    )

    previous_preterm_birth = (
        yes_no(0.08)
        if max_previous_pregnancies > 0
        else "No"
    )

    previous_sga = (
        yes_no(0.07)
        if max_previous_pregnancies > 0
        else "No"
    )

    previous_lga = (
        yes_no(0.06)
        if max_previous_pregnancies > 0
        else "No"
    )

    previous_c_section = (
        yes_no(0.16)
        if max_previous_pregnancies > 0
        else "No"
    )

    previous_pregnancy_complications = "None"

    if archetype == "Obstetric_History_Risk":
        previous_pregnancy_complications = weighted_choice(
            [
                "Previous_PreEclampsia",
                "Previous_GDM",
                "Previous_Preterm_Birth",
                "Previous_PPH",
                "None",
            ],
            [0.25, 0.25, 0.20, 0.10, 0.20],
        )
    elif previous_miscarriage == "Yes":
        previous_pregnancy_complications = "Previous_Miscarriage"
    elif previous_preterm_birth == "Yes":
        previous_pregnancy_complications = "Previous_Preterm_Birth"

    # --------------------------------------------------------
    # Medical history
    # --------------------------------------------------------

    if archetype in {
        "Hypertension_Risk",
        "High_Risk_Combined",
    }:
        preexisting_hypertension = yes_no(0.70)
    else:
        preexisting_hypertension = yes_no(0.04)

    if archetype == "GDM_Risk":
        preexisting_diabetes = yes_no(0.18)
    elif archetype == "High_Risk_Combined":
        preexisting_diabetes = yes_no(0.15)
    else:
        preexisting_diabetes = yes_no(0.025)

    if archetype == "Thyroid_Risk":
        thyroid_disease = yes_no(0.85)
    elif archetype == "High_Risk_Combined":
        thyroid_disease = yes_no(0.25)
    else:
        thyroid_disease = yes_no(0.07)

    if archetype == "Renal_Risk":
        renal_disease = yes_no(0.80)
    elif archetype == "High_Risk_Combined":
        renal_disease = yes_no(0.20)
    else:
        renal_disease = yes_no(0.025)

    cardiac_disease = (
        yes_no(0.12)
        if archetype == "High_Risk_Combined"
        else yes_no(0.025)
    )

    epilepsy = yes_no(0.02)
    asthma = yes_no(0.08)
    autoimmune_disease = yes_no(0.025)

    if archetype == "Anaemia_Risk":
        haematological_disorder = yes_no(0.50)
    elif archetype == "High_Risk_Combined":
        haematological_disorder = yes_no(0.15)
    else:
        haematological_disorder = yes_no(0.025)

    if archetype == "GDM_Risk":
        previous_gdm = yes_no(0.55)
    elif archetype == "High_Risk_Combined":
        previous_gdm = yes_no(0.30)
    else:
        previous_gdm = yes_no(0.06)

    if archetype in {
        "Hypertension_Risk",
        "High_Risk_Combined",
        "Obstetric_History_Risk",
    }:
        previous_preeclampsia = yes_no(0.25)
    else:
        previous_preeclampsia = yes_no(0.03)

    # --------------------------------------------------------
    # Multiple pregnancy
    # --------------------------------------------------------

    if archetype == "Multiple_Pregnancy":
        multiple_pregnancy = "Yes"
        number_of_fetuses = int(
            weighted_choice(
                [2, 3],
                [0.95, 0.05],
            )
        )
    else:
        multiple_pregnancy = yes_no(0.015)
        number_of_fetuses = (
            2 if multiple_pregnancy == "Yes" else 1
        )

    # --------------------------------------------------------
    # Blood / infection / haemoglobinopathy
    # --------------------------------------------------------

    abo_group = weighted_choice(
        ABO_GROUPS,
        [0.28, 0.24, 0.08, 0.40],
    )

    rhd_status = weighted_choice(
        RHD_STATUSES,
        [0.94, 0.06],
    )

    hiv_status = weighted_choice(
        HIV_STATUSES,
        [0.995, 0.005],
    )

    hepatitis_b_status = weighted_choice(
        HEPATITIS_B_STATUSES,
        [0.985, 0.015],
    )

    if haematological_disorder == "Yes":
        known_haemoglobinopathy = weighted_choice(
            ["Yes", "No"],
            [0.65, 0.35],
        )
    else:
        known_haemoglobinopathy = weighted_choice(
            ["No", "Yes"],
            [0.97, 0.03],
        )

    # --------------------------------------------------------
    # Lifestyle
    # --------------------------------------------------------

    smoking_status = weighted_choice(
        SMOKING_STATUSES,
        [0.88, 0.08, 0.04],
    )

    alcohol_use = weighted_choice(
        ALCOHOL_USE,
        [0.82, 0.15, 0.03],
    )

    substance_use = weighted_choice(
        SUBSTANCE_USE,
        [0.97, 0.02, 0.01],
    )

    physical_activity_level = weighted_choice(
        PHYSICAL_ACTIVITY_LEVELS,
        [0.25, 0.60, 0.15],
    )

    # --------------------------------------------------------
    # Diet
    # --------------------------------------------------------

    dietary_pattern = weighted_choice(
        DIETARY_PATTERNS,
        [0.55, 0.22, 0.05, 0.18],
    )

    dietary_restriction = weighted_choice(
        DIETARY_RESTRICTIONS,
        [0.55, 0.20, 0.10, 0.05, 0.10],
    )

    if rng.random() < 0.88:
        food_allergies = "None"
    else:
        food_allergies = weighted_choice(
            FOOD_ALLERGY_OPTIONS[1:],
            [0.20, 0.18, 0.15, 0.12, 0.10, 0.08, 0.10, 0.07],
        )

    # --------------------------------------------------------
    # Medication safety baseline
    # --------------------------------------------------------

    drug_allergies, drug_allergy_reaction = (
        generate_drug_allergy()
    )

    current_pre_pregnancy_medications = (
        generate_baseline_medication_history(
            archetype
        )
    )

    previous_medication_adverse_reaction = (
        generate_previous_medication_adverse_reaction()
    )

    # --------------------------------------------------------
    # Complete record
    # --------------------------------------------------------

    records.append(
        {
            "Patient_ID": patient_id,
            "Pregnancy_ID": pregnancy_id,

            "Age_Years": age,
            "Height_cm": height_cm,
            "Pre_Pregnancy_Weight_kg": weight_kg,
            "Pre_Pregnancy_BMI": bmi,
            "Residence_Type": residence_type,

            "LMP_Date": lmp_date,
            "EDD_Date": edd_date,
            "Dating_Method": dating_method,

            "Gravida": gravida,
            "Para": para,
            "Previous_Miscarriage": previous_miscarriage,
            "Previous_Stillbirth": previous_stillbirth,
            "Previous_Preterm_Birth": previous_preterm_birth,
            "Previous_SGA_Baby": previous_sga,
            "Previous_LGA_Baby": previous_lga,
            "Previous_C_Section": previous_c_section,
            "Previous_Pregnancy_Complications":
                previous_pregnancy_complications,

            "Preexisting_Hypertension":
                preexisting_hypertension,
            "Preexisting_Diabetes":
                preexisting_diabetes,
            "Thyroid_Disease":
                thyroid_disease,
            "Renal_Disease":
                renal_disease,
            "Cardiac_Disease":
                cardiac_disease,
            "Epilepsy":
                epilepsy,
            "Asthma":
                asthma,
            "Autoimmune_Disease":
                autoimmune_disease,
            "Haematological_Disorder":
                haematological_disorder,
            "Previous_PreEclampsia":
                previous_preeclampsia,
            "Previous_GDM":
                previous_gdm,

            "Multiple_Pregnancy":
                multiple_pregnancy,
            "Number_of_Fetuses":
                number_of_fetuses,

            "ABO_Group":
                abo_group,
            "RhD_Status":
                rhd_status,
            "HIV_Status":
                hiv_status,
            "Hepatitis_B_Status":
                hepatitis_b_status,
            "Known_Haemoglobinopathy":
                known_haemoglobinopathy,

            "Smoking_Status":
                smoking_status,
            "Alcohol_Use":
                alcohol_use,
            "Substance_Use":
                substance_use,
            "Physical_Activity_Level":
                physical_activity_level,

            "Dietary_Pattern":
                dietary_pattern,
            "Dietary_Restriction":
                dietary_restriction,
            "Food_Allergies":
                food_allergies,

            # NEW
            "Drug_Allergies":
                drug_allergies,
            "Drug_Allergy_Reaction":
                drug_allergy_reaction,
            "Current_Pre_Pregnancy_Medications":
                current_pre_pregnancy_medications,
            "Previous_Medication_Adverse_Reaction":
                previous_medication_adverse_reaction,
        }
    )


# ============================================================
# 9. DATAFRAME AND COLUMN ORDER
# ============================================================

df = pd.DataFrame(records)

column_order = [
    "Patient_ID",
    "Pregnancy_ID",

    "Age_Years",
    "Height_cm",
    "Pre_Pregnancy_Weight_kg",
    "Pre_Pregnancy_BMI",
    "Residence_Type",

    "LMP_Date",
    "EDD_Date",
    "Dating_Method",

    "Gravida",
    "Para",
    "Previous_Miscarriage",
    "Previous_Stillbirth",
    "Previous_Preterm_Birth",
    "Previous_SGA_Baby",
    "Previous_LGA_Baby",
    "Previous_C_Section",
    "Previous_Pregnancy_Complications",

    "Preexisting_Hypertension",
    "Preexisting_Diabetes",
    "Thyroid_Disease",
    "Renal_Disease",
    "Cardiac_Disease",
    "Epilepsy",
    "Asthma",
    "Autoimmune_Disease",
    "Haematological_Disorder",
    "Previous_PreEclampsia",
    "Previous_GDM",

    "Multiple_Pregnancy",
    "Number_of_Fetuses",

    "ABO_Group",
    "RhD_Status",
    "HIV_Status",
    "Hepatitis_B_Status",
    "Known_Haemoglobinopathy",

    "Smoking_Status",
    "Alcohol_Use",
    "Substance_Use",
    "Physical_Activity_Level",

    "Dietary_Pattern",
    "Dietary_Restriction",
    "Food_Allergies",

    "Drug_Allergies",
    "Drug_Allergy_Reaction",
    "Current_Pre_Pregnancy_Medications",
    "Previous_Medication_Adverse_Reaction",
]

df = df[column_order]


# ============================================================
# 10. VALIDATION
# ============================================================

validation = []

validation.append("DATASET 1 VALIDATION REPORT")
validation.append("=" * 70)
validation.append(
    "Generated on: "
    + datetime.now().strftime("%Y-%m-%d %H:%M:%S")
)
validation.append(f"Random seed: {SEED}")
validation.append("")

# Record count
record_count_error = (
    0 if len(df) == N_PATIENTS else 1
)

validation.append("RECORD COUNT")
validation.append("-" * 50)

if record_count_error == 0:
    validation.append(
        f"PASS: Exactly {N_PATIENTS} pregnancies generated."
    )
else:
    validation.append(
        f"FAIL: Expected {N_PATIENTS}, got {len(df)}."
    )

validation.append("")

# Patient IDs
duplicate_patient_ids = int(
    df["Patient_ID"].duplicated().sum()
)

validation.append("PATIENT ID CHECK")
validation.append("-" * 50)

if duplicate_patient_ids == 0:
    validation.append(
        "PASS: Patient_ID values are unique."
    )
else:
    validation.append(
        f"FAIL: {duplicate_patient_ids} duplicate Patient_ID values."
    )

validation.append("")

# Pregnancy IDs
duplicate_pregnancy_ids = int(
    df["Pregnancy_ID"].duplicated().sum()
)

validation.append("PREGNANCY ID CHECK")
validation.append("-" * 50)

if duplicate_pregnancy_ids == 0:
    validation.append(
        "PASS: Pregnancy_ID values are unique."
    )
else:
    validation.append(
        f"FAIL: {duplicate_pregnancy_ids} duplicate Pregnancy_ID values."
    )

validation.append("")

# Required columns
missing_columns = [
    column
    for column in column_order
    if column not in df.columns
]

validation.append("COLUMN CHECK")
validation.append("-" * 50)

if not missing_columns:
    validation.append(
        f"PASS: All {len(column_order)} expected columns are present."
    )
else:
    validation.append(
        "FAIL: Missing columns:"
    )
    validation.extend(
        f"  {column}"
        for column in missing_columns
    )

validation.append("")

# Nulls
null_counts = df.isna().sum()
null_columns = null_counts[null_counts > 0]

validation.append("NULL VALUE CHECK")
validation.append("-" * 50)

if len(null_columns) == 0:
    validation.append(
        "PASS: No missing values."
    )
else:
    validation.append(
        "WARNING: Missing values found:"
    )

    for column, count in null_columns.items():
        validation.append(
            f"  {column}: {count}"
        )

validation.append("")

# BMI
bmi_errors = 0

for _, row in df.iterrows():
    calculated_bmi = calculate_bmi(
        row["Pre_Pregnancy_Weight_kg"],
        row["Height_cm"],
    )

    if abs(
        calculated_bmi
        - row["Pre_Pregnancy_BMI"]
    ) > 0.15:
        bmi_errors += 1

validation.append("BMI CONSISTENCY CHECK")
validation.append("-" * 50)

if bmi_errors == 0:
    validation.append(
        "PASS: BMI values are mathematically consistent."
    )
else:
    validation.append(
        f"FAIL: {bmi_errors} BMI inconsistencies."
    )

validation.append("")

# EDD
edd_errors = 0

for _, row in df.iterrows():
    expected_edd = (
        pd.Timestamp(row["LMP_Date"])
        + pd.Timedelta(days=280)
    )

    actual_edd = pd.Timestamp(
        row["EDD_Date"]
    )

    if expected_edd != actual_edd:
        edd_errors += 1

validation.append("EDD CONSISTENCY CHECK")
validation.append("-" * 50)

if edd_errors == 0:
    validation.append(
        "PASS: EDD = LMP + 280 days for all pregnancies."
    )
else:
    validation.append(
        f"FAIL: {edd_errors} EDD inconsistencies."
    )

validation.append("")

# Gravida / Para
gravida_para_errors = 0

for _, row in df.iterrows():
    if row["Para"] < 0:
        gravida_para_errors += 1

    if row["Para"] > row["Gravida"] - 1:
        gravida_para_errors += 1

validation.append("GRAVIDA / PARA CHECK")
validation.append("-" * 50)

if gravida_para_errors == 0:
    validation.append(
        "PASS: Gravida/Para relationships are valid."
    )
else:
    validation.append(
        f"FAIL: {gravida_para_errors} Gravida/Para errors."
    )

validation.append("")

# Drug allergy consistency
drug_allergy_errors = 0

for _, row in df.iterrows():
    allergy = str(
        row["Drug_Allergies"]
    ).strip()

    reaction = str(
        row["Drug_Allergy_Reaction"]
    ).strip()

    if allergy == "None" and reaction != "None":
        drug_allergy_errors += 1

    if allergy != "None" and reaction == "None":
        drug_allergy_errors += 1

validation.append("DRUG ALLERGY CONSISTENCY CHECK")
validation.append("-" * 50)

if drug_allergy_errors == 0:
    validation.append(
        "PASS: Drug allergy and reaction fields are consistent."
    )
else:
    validation.append(
        f"FAIL: {drug_allergy_errors} drug allergy inconsistencies."
    )

validation.append("")

# Adverse reaction values
valid_adverse_values = set(
    MEDICATION_ADVERSE_REACTIONS
    + ["None"]
)

invalid_adverse_values = (
    ~df[
        "Previous_Medication_Adverse_Reaction"
    ].isin(valid_adverse_values)
)

adverse_reaction_errors = int(
    invalid_adverse_values.sum()
)

validation.append(
    "PREVIOUS MEDICATION ADVERSE REACTION CHECK"
)
validation.append("-" * 50)

if adverse_reaction_errors == 0:
    validation.append(
        "PASS: Medication adverse-reaction values are valid."
    )
else:
    validation.append(
        f"FAIL: {adverse_reaction_errors} invalid values."
    )

validation.append("")

# Medication history
missing_medication_history = int(
    df[
        "Current_Pre_Pregnancy_Medications"
    ].isna().sum()
)

validation.append(
    "PRE-PREGNANCY MEDICATION HISTORY CHECK"
)
validation.append("-" * 50)

if missing_medication_history == 0:
    validation.append(
        "PASS: Every pregnancy has a baseline medication-history value."
    )
else:
    validation.append(
        f"FAIL: {missing_medication_history} missing medication-history values."
    )

validation.append("")

# Summary of new fields
validation.append(
    "MEDICATION-SAFETY BASELINE SUMMARY"
)
validation.append("-" * 50)

validation.append("Drug allergies:")

for value, count in (
    df["Drug_Allergies"].value_counts().items()
):
    validation.append(
        f"  {value}: {count}"
    )

validation.append("")
validation.append(
    "Current pre-pregnancy medications:"
)

for value, count in (
    df[
        "Current_Pre_Pregnancy_Medications"
    ].value_counts().items()
):
    validation.append(
        f"  {value}: {count}"
    )

validation.append("")
validation.append(
    "Previous medication adverse reactions:"
)

for value, count in (
    df[
        "Previous_Medication_Adverse_Reaction"
    ].value_counts().items()
):
    validation.append(
        f"  {value}: {count}"
    )

validation.append("")

critical_errors = (
    record_count_error
    + duplicate_patient_ids
    + duplicate_pregnancy_ids
    + len(missing_columns)
    + bmi_errors
    + edd_errors
    + gravida_para_errors
    + drug_allergy_errors
    + adverse_reaction_errors
    + missing_medication_history
)

validation.append("=" * 70)

if critical_errors == 0:
    validation.append("FINAL STATUS: PASS")
    validation.append(
        "Dataset 1 passed all structural and consistency checks."
    )
else:
    validation.append("FINAL STATUS: REVIEW REQUIRED")
    validation.append(
        f"Critical validation issues: {critical_errors}"
    )


# ============================================================
# 11. SAVE VALIDATION REPORT
# ============================================================

with open(
    VALIDATION_OUTPUT,
    "w",
    encoding="utf-8",
) as file:
    file.write("\n".join(validation))


# ============================================================
# 12. SAVE SUMMARY
# ============================================================

summary = [
    "DATASET 1 - PATIENT & PREGNANCY",
    "=" * 70,
    (
        "Generated on: "
        + datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ),
    f"Random seed: {SEED}",
    "",
    "GRAIN",
    "1 row = 1 pregnancy.",
    "",
    f"Total pregnancies: {len(df):,}",
    f"Total columns: {len(df.columns):,}",
    "",
    "NEW MEDICATION-SAFETY BASELINE FIELDS",
    "1. Drug_Allergies",
    "2. Drug_Allergy_Reaction",
    "3. Current_Pre_Pregnancy_Medications",
    "4. Previous_Medication_Adverse_Reaction",
    "",
    "DESIGN",
    (
        "Baseline medication/allergy context is stored in "
        "Dataset 1."
    ),
    (
        "Pregnancy-specific medication and treatment events "
        "will be stored in Dataset 4."
    ),
    "",
    "VALIDATION",
    f"Critical validation issues: {critical_errors}",
    "See dataset1_validation_report.txt for details.",
]

with open(
    SUMMARY_OUTPUT,
    "w",
    encoding="utf-8",
) as file:
    file.write("\n".join(summary))


# ============================================================
# 13. SAVE CSV
# ============================================================

df.to_csv(
    CSV_OUTPUT,
    index=False,
    encoding="utf-8-sig",
)


# ============================================================
# 14. SAVE EXCEL
# ============================================================
#
# Important:
# writer.book["Patient_Pregnancy"] is used to access the
# openpyxl worksheet.
# ============================================================

df_excel = df.copy()

df_excel["LMP_Date"] = (
    df_excel["LMP_Date"]
    .apply(format_date_for_excel)
)

df_excel["EDD_Date"] = (
    df_excel["EDD_Date"]
    .apply(format_date_for_excel)
)

with pd.ExcelWriter(
    EXCEL_OUTPUT,
    engine="openpyxl",
) as writer:

    df_excel.to_excel(
        writer,
        index=False,
        sheet_name="Patient_Pregnancy",
    )

    worksheet = writer.book["Patient_Pregnancy"]

    worksheet.freeze_panes = "A2"
    worksheet.auto_filter.ref = worksheet.dimensions

    for column_cells in worksheet.columns:

        column_letter = (
            column_cells[0].column_letter
        )

        max_length = 0

        for cell in column_cells:
            if cell.value is None:
                length = 0
            else:
                length = len(str(cell.value))

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
# 15. FINAL OUTPUT
# ============================================================

print("\n" + "=" * 70)
print("DATASET 1 GENERATION COMPLETE")
print("=" * 70)

print(
    f"\nPregnancies generated: {len(df):,}"
)

print(
    f"Columns generated: {len(df.columns):,}"
)

print("\n--- New Medication-Safety Fields ---")
print("Drug_Allergies")
print("Drug_Allergy_Reaction")
print("Current_Pre_Pregnancy_Medications")
print("Previous_Medication_Adverse_Reaction")

print("\n--- Validation ---")
print(
    f"Critical validation issues: {critical_errors}"
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
