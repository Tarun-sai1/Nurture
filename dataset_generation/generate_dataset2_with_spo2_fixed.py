import os
# ============================================================
# MATERNAL HEALTH PROJECT
# DATASET 2: ANC CLINICAL & VITALS
# ============================================================

import pandas as pd
import numpy as np

from pathlib import Path
from datetime import timedelta


# ============================================================
# 1. CONFIGURATION
# ============================================================

RANDOM_SEED = 20261008

rng = np.random.default_rng(RANDOM_SEED)


# ============================================================
# 2. PROJECT PATHS
# ============================================================

PROJECT_DIR = Path(
    os.environ.get("MH_PROJECT", r"D:\Maternal_Health_Project")
)

DATASET1_DIR = (
    PROJECT_DIR
    / "datasets"
    / "dataset1_patient_pregnancy"
)

OUTPUT_DIR = (
    PROJECT_DIR
    / "datasets"
    / "dataset2_anc_clinical_vitals"
)

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True
)


# ============================================================
# 3. INPUT FILE
# ============================================================

INPUT_FILE = (
    DATASET1_DIR
    / "patient_pregnancy.csv"
)


if not INPUT_FILE.exists():

    raise FileNotFoundError(
        f"\nDataset 1 not found:\n{INPUT_FILE}\n\n"
        "Generate Dataset 1 first."
    )


# ============================================================
# 4. LOAD DATASET 1
# ============================================================

df_patients = pd.read_csv(
    INPUT_FILE
)

df_patients["LMP_Date"] = pd.to_datetime(
    df_patients["LMP_Date"]
)

df_patients["EDD_Date"] = pd.to_datetime(
    df_patients["EDD_Date"]
)


print()
print("=" * 70)
print("DATASET 2: ANC CLINICAL & VITALS")
print("=" * 70)

print(
    f"Dataset 1 records loaded: {len(df_patients)}"
)


# ============================================================
# 5. VALIDATE DATASET 1
# ============================================================

required_columns = [

    "Patient_ID",
    "Pregnancy_ID",
    "Age_Years",
    "Height_cm",
    "Pre_Pregnancy_Weight_kg",
    "Pre_Pregnancy_BMI",
    "LMP_Date",
    "EDD_Date",
    "Gravida",
    "Para",
    "Previous_PreEclampsia",
    "Previous_GDM",
    "Preexisting_Hypertension",
    "Preexisting_Diabetes",
    "Thyroid_Disease",
    "Renal_Disease",
    "Cardiac_Disease",
    "Multiple_Pregnancy",
    "Number_of_Fetuses"
]


missing_columns = [

    col
    for col in required_columns
    if col not in df_patients.columns

]


if missing_columns:

    raise ValueError(
        "Dataset 1 is missing required columns:\n"
        + "\n".join(missing_columns)
    )


# ============================================================
# 6. ANC SCHEDULE
# ============================================================
#
# These are planned ANC milestones.
#
# Additional visits may be created for high-risk patients.
#
# Early delivery terminates the pregnancy timeline.
# ============================================================

SCHEDULED_WEEKS = [
    8,
    12,
    16,
    20,
    25,
    28,
    31,
    34,
    36,
    38,
    40,
    41
]


# ============================================================
# 7. HELPER FUNCTIONS
# ============================================================

def clamp(value, low, high):

    return max(
        low,
        min(
            high,
            value
        )
    )


def trimester_from_week(week):

    if week < 14:
        return "First"

    elif week < 28:
        return "Second"

    else:
        return "Third"


def gestational_date(lmp, week, days=0):

    return (
        lmp
        + timedelta(
            days=(week * 7) + days
        )
    )


def weighted_choice(values, probabilities):

    return rng.choice(
        values,
        p=np.array(probabilities)
        / np.sum(probabilities)
    )


# ============================================================
# 8. DETERMINE PREGNANCY DELIVERY PROFILE
# ============================================================
#
# This creates a hidden pregnancy trajectory.
#
# Dataset 6 will later use the final pregnancy outcome.
#
# IMPORTANT:
# Early delivery is an outcome, NOT a disease category.
# ============================================================

def determine_delivery_week(row):

    high_risk = False

    risk_score = 0


    # --------------------------------------------
    # Risk factors
    # --------------------------------------------

    if row["Preexisting_Hypertension"] == "Yes":
        risk_score += 2

    if row["Preexisting_Diabetes"] == "Yes":
        risk_score += 2

    if row["Previous_PreEclampsia"] == "Yes":
        risk_score += 1

    if row["Previous_GDM"] == "Yes":
        risk_score += 1

    if row["Renal_Disease"] == "Yes":
        risk_score += 2

    if row["Cardiac_Disease"] == "Yes":
        risk_score += 2

    if row["Multiple_Pregnancy"] == "Yes":
        risk_score += 3

    if row["Age_Years"] >= 35:
        risk_score += 1

    if row["Pre_Pregnancy_BMI"] >= 30:
        risk_score += 1


    # --------------------------------------------
    # High-risk probability
    # --------------------------------------------

    if risk_score >= 3:

        high_risk = True


    # --------------------------------------------
    # Early delivery
    # --------------------------------------------

    if high_risk:

        early_probability = 0.28

    else:

        early_probability = 0.12


    early_delivery = (
        rng.random()
        < early_probability
    )


    if early_delivery:

        if (
            row["Multiple_Pregnancy"]
            == "Yes"
        ):

            delivery_week = int(
                rng.integers(
                    32,
                    37
                )
            )

        elif risk_score >= 3:

            delivery_week = int(
                rng.integers(
                    34,
                    37
                )
            )

        else:

            delivery_week = int(
                rng.integers(
                    35,
                    37
                )
            )

    else:

        if (
            row["Multiple_Pregnancy"]
            == "Yes"
        ):

            delivery_week = int(
                rng.integers(
                    36,
                    39
                )
            )

        else:

            delivery_week = int(
                rng.integers(
                    38,
                    41
                )
            )


    return delivery_week


# ============================================================
# 9. GENERATE ANC VISITS
# ============================================================

visit_records = []

# FIX: the delivery week decided here was never saved, so Dataset 6 had to
# guess delivery from the LAST ANC visit (a 38-week birth whose last visit
# was at 36 weeks became "preterm"). It is now saved in a separate file so
# the ANC visit table itself contains no future information.
delivery_plan = []


for _, patient in df_patients.iterrows():

    patient_id = patient["Patient_ID"]

    pregnancy_id = patient["Pregnancy_ID"]

    lmp = patient["LMP_Date"]


    # --------------------------------------------------------
    # Determine pregnancy delivery week
    # --------------------------------------------------------

    delivery_week = determine_delivery_week(
        patient
    )

    delivery_plan.append({
        "Patient_ID": patient["Patient_ID"],
        "Pregnancy_ID": patient["Pregnancy_ID"],
        "Planned_Delivery_Week": int(delivery_week),
    })


    # --------------------------------------------------------
    # Determine high-risk status
    # --------------------------------------------------------

    high_risk = False

    risk_score = 0


    if patient["Preexisting_Hypertension"] == "Yes":
        risk_score += 2

    if patient["Preexisting_Diabetes"] == "Yes":
        risk_score += 2

    if patient["Previous_PreEclampsia"] == "Yes":
        risk_score += 1

    if patient["Previous_GDM"] == "Yes":
        risk_score += 1

    if patient["Renal_Disease"] == "Yes":
        risk_score += 2

    if patient["Cardiac_Disease"] == "Yes":
        risk_score += 2

    if patient["Multiple_Pregnancy"] == "Yes":
        risk_score += 3

    if patient["Age_Years"] >= 35:
        risk_score += 1


    if risk_score >= 3:

        high_risk = True


    # --------------------------------------------------------
    # Build visit weeks
    # --------------------------------------------------------

    visit_weeks = []


    for week in SCHEDULED_WEEKS:

        if week < delivery_week:

            visit_weeks.append(
                week
            )


    # --------------------------------------------------------
    # Add first ANC visit if required
    # --------------------------------------------------------

    if len(visit_weeks) == 0:

        visit_weeks = [
            min(
                8,
                delivery_week - 1
            )
        ]


    # --------------------------------------------------------
    # High-risk additional visits
    # --------------------------------------------------------

    if high_risk:

        additional_candidates = [

            10,
            14,
            18,
            22,
            26,
            30,
            32,
            35,
            37

        ]


        for week in additional_candidates:

            if (
                week < delivery_week
                and rng.random() < 0.45
            ):

                visit_weeks.append(
                    week
                )


    # Remove duplicates
    visit_weeks = sorted(
        set(visit_weeks)
    )


    # --------------------------------------------------------
    # Add delivery-adjacent visit
    # --------------------------------------------------------

    if delivery_week > 36:

        if (
            delivery_week - 1
            not in visit_weeks
        ):

            if rng.random() < 0.35:

                visit_weeks.append(
                    delivery_week - 1
                )


    visit_weeks = sorted(
        set(visit_weeks)
    )


    # --------------------------------------------------------
    # Generate visits
    # --------------------------------------------------------

    previous_weight = (
        patient["Pre_Pregnancy_Weight_kg"]
    )


    previous_sbp = None

    previous_dbp = None


    for visit_number, week in enumerate(
        visit_weeks,
        start=1
    ):

        # ====================================================
        # GESTATIONAL AGE
        # ====================================================

        gestational_days = int(
            rng.integers(
                0,
                7
            )
        )


        visit_date = gestational_date(
            lmp,
            week,
            gestational_days
        )


        trimester = (
            trimester_from_week(
                week
            )
        )


        # ====================================================
        # VISIT TYPE
        # ====================================================

        if visit_number == 1:

            visit_type = "Booking"

        elif week in SCHEDULED_WEEKS:

            visit_type = "Routine_ANC"

        else:

            visit_type = "Additional_ANC"


        scheduled_visit = (
            "Yes"
            if week in SCHEDULED_WEEKS
            else "No"
        )


        # ====================================================
        # HIGH-RISK VISIT
        # ====================================================

        high_risk_visit = (
            "Yes"
            if high_risk
            else "No"
        )


        # ====================================================
        # UNSCHEDULED VISIT
        # ====================================================

        unscheduled_visit = (
            "Yes"
            if week not in SCHEDULED_WEEKS
            else "No"
        )


        # ====================================================
        # WEIGHT
        # ====================================================

        # Approximate progressive pregnancy weight gain.
        # We intentionally allow individual variation.

        if visit_number == 1:

            weight = (
                patient[
                    "Pre_Pregnancy_Weight_kg"
                ]
                +
                rng.normal(
                    0.5,
                    0.7
                )
            )

        else:

            expected_gain = (

                0.25
                *
                max(
                    week - 12,
                    0
                )

            )

            weight = (
                patient[
                    "Pre_Pregnancy_Weight_kg"
                ]
                +
                expected_gain
                +
                rng.normal(
                    0,
                    1.0
                )
            )


        # Multiple pregnancy
        if (
            patient["Multiple_Pregnancy"]
            == "Yes"
        ):

            weight += (
                0.15
                *
                max(
                    week - 12,
                    0
                )
            )


        weight = round(
            max(
                weight,
                patient[
                    "Pre_Pregnancy_Weight_kg"
                ]
                - 1.5
            ),
            1
        )


        # Prevent unrealistic jump
        if visit_number > 1:

            maximum_jump = 3.0

            if (
                weight
                > previous_weight
                + maximum_jump
            ):

                weight = round(
                    previous_weight
                    + rng.uniform(
                        0.4,
                        maximum_jump
                    ),
                    1
                )


        previous_weight = weight


        # ====================================================
        # BMI
        # ====================================================

        bmi = round(

            weight
            /
            (
                patient["Height_cm"]
                / 100
            ) ** 2,

            1
        )


        # ====================================================
        # BLOOD PRESSURE
        # ====================================================

        if previous_sbp is None:

            if (
                patient[
                    "Preexisting_Hypertension"
                ]
                == "Yes"
            ):

                sbp = rng.normal(
                    135,
                    8
                )

                dbp = rng.normal(
                    86,
                    6
                )

            else:

                sbp = rng.normal(
                    112,
                    8
                )

                dbp = rng.normal(
                    72,
                    5
                )

        else:

            sbp = (
                previous_sbp
                + rng.normal(
                    0,
                    4
                )
            )

            dbp = (
                previous_dbp
                + rng.normal(
                    0,
                    3
                )
            )


        # ----------------------------------------------------
        # Pregnancy hypertension trajectory
        # ----------------------------------------------------

        if week >= 28:

            if (
                patient[
                    "Previous_PreEclampsia"
                ]
                == "Yes"
                and rng.random() < 0.15
            ):

                sbp += rng.uniform(
                    5,
                    15
                )

                dbp += rng.uniform(
                    3,
                    10
                )


        # ----------------------------------------------------
        # Random physiological variation
        # ----------------------------------------------------

        sbp = int(
            round(
                clamp(
                    sbp,
                    90,
                    180
                )
            )
        )

        dbp = int(
            round(
                clamp(
                    dbp,
                    50,
                    115
                )
            )
        )


        previous_sbp = sbp
        previous_dbp = dbp


        # ====================================================
        # FUNDAL HEIGHT
        # ====================================================

        if week < 20:

            fundal_height = round(
                max(
                    8,
                    week
                    - rng.uniform(
                        0,
                        2
                    )
                ),
                1
            )

        else:

            fundal_height = round(
                week
                +
                rng.normal(
                    0,
                    2
                ),
                1
            )


        # Multiple pregnancy
        if (
            patient[
                "Multiple_Pregnancy"
            ]
            == "Yes"
        ):

            fundal_height += rng.uniform(
                2,
                5
            )


        fundal_height = round(
            clamp(
                fundal_height,
                8,
                45
            ),
            1
        )


        # ====================================================
        # FETAL HEART RATE
        # ====================================================

        if week < 12:

            fhr = int(
                round(
                    rng.uniform(
                        140,
                        170
                    )
                )
            )

        else:

            fhr = int(
                round(
                    rng.normal(
                        145,
                        8
                    )
                )
            )


        fhr = int(
            clamp(
                fhr,
                110,
                170
            )
        )


        # ====================================================
        # FETAL PRESENTATION
        # ====================================================

        if week < 28:

            fetal_presentation = (
                "Not_Assessed"
            )

        elif week < 34:

            fetal_presentation = weighted_choice(

                [
                    "Cephalic",
                    "Breech",
                    "Transverse"
                ],

                [
                    0.65,
                    0.25,
                    0.10
                ]
            )

        else:

            fetal_presentation = weighted_choice(

                [
                    "Cephalic",
                    "Breech",
                    "Transverse"
                ],

                [
                    0.82,
                    0.14,
                    0.04
                ]
            )


        # ====================================================
        # FETAL MOVEMENT
        # ====================================================

        if week < 18:

            fetal_movement = (
                "Not_Expected"
            )

        else:

            fetal_movement = weighted_choice(

                [
                    "Normal",
                    "Reduced",
                    "Not_Reported"
                ],

                [
                    0.93,
                    0.04,
                    0.03
                ]
            )


        # ====================================================
        # OEDEMA
        # ====================================================

        if week < 20:

            oedema = weighted_choice(

                [
                    "Absent",
                    "Mild"
                ],

                [
                    0.96,
                    0.04
                ]
            )

        else:

            oedema = weighted_choice(

                [
                    "Absent",
                    "Mild",
                    "Moderate"
                ],

                [
                    0.82,
                    0.15,
                    0.03
                ]
            )


        # ====================================================
        # SYMPTOMS
        # ====================================================

        symptom_pool = [

            "None",
            "Nausea",
            "Vomiting",
            "Fatigue",
            "Headache",
            "Back_Pain",
            "Heartburn",
            "Constipation",
            "Leg_Cramps",
            "Swelling"
        ]


        symptom = weighted_choice(

            symptom_pool,

            [
                0.52,
                0.08,
                0.03,
                0.08,
                0.05,
                0.07,
                0.05,
                0.04,
                0.04,
                0.04
            ]
        )


        if symptom == "None":

            symptoms_present = "No"
            symptoms = "None"
            symptom_severity = "None"

        else:

            symptoms_present = "Yes"
            symptoms = symptom

            symptom_severity = weighted_choice(

                [
                    "Mild",
                    "Moderate",
                    "Severe"
                ],

                [
                    0.70,
                    0.25,
                    0.05
                ]
            )


        # ====================================================
        # HIGH-RISK SYMPTOMS
        # ====================================================

        # These are not diagnoses.
        # They trigger assessment/referral.

        if (
            week >= 28
            and rng.random() < 0.015
        ):

            symptoms_present = "Yes"

            symptoms = weighted_choice(

                [
                    "Severe_Headache",
                    "Visual_Disturbance",
                    "Upper_Abdominal_Pain",
                    "Vaginal_Bleeding"
                ],

                [
                    0.35,
                    0.20,
                    0.20,
                    0.25
                ]
            )

            symptom_severity = weighted_choice(

                [
                    "Moderate",
                    "Severe"
                ],

                [
                    0.35,
                    0.65
                ]
            )


        # ====================================================
        # SPO2 / OXYGEN SATURATION
        # ====================================================
        # SpO2 is recorded at EVERY ANC visit.
        # It is generated AFTER symptom assignment so the optional
        # symptom-related variation uses the actual visit symptoms.
        # This is synthetic data generation only, not a clinical
        # prediction rule.

        spo2 = rng.normal(98.0, 0.8)

        if symptoms_present == "Yes" and symptom_severity == "Severe":
            spo2 -= rng.uniform(0.5, 2.0)

        spo2 = round(
            clamp(spo2, 92.0, 100.0),
            1
        )


        # ====================================================
        # CLINICAL ASSESSMENT
        # ====================================================

        assessment_flags = []


        if sbp >= 140 or dbp >= 90:

            assessment_flags.append(
                "Elevated_BP"
            )


        if oedema == "Moderate":

            assessment_flags.append(
                "Oedema"
            )


        if (
            fetal_movement
            == "Reduced"
        ):

            assessment_flags.append(
                "Reduced_Fetal_Movement"
            )


        if (
            symptom_severity
            == "Severe"
        ):

            assessment_flags.append(
                "Significant_Symptoms"
            )


        if (
            fetal_presentation
            in [
                "Breech",
                "Transverse"
            ]
            and week >= 36
        ):

            assessment_flags.append(
                "Abnormal_Presentation"
            )


        if assessment_flags:

            clinical_assessment = (
                ";".join(
                    assessment_flags
                )
            )

        else:

            clinical_assessment = (
                "Routine_ANC_Assessment"
            )


        # ====================================================
        # RISK LEVEL
        # ====================================================

        if (
            sbp >= 160
            or dbp >= 110
            or symptom_severity == "Severe"
            or fetal_movement == "Reduced"
            or "Vaginal_Bleeding" in symptoms
        ):

            risk_level = "High"

        elif high_risk:

            risk_level = "Moderate"

        elif (
            sbp >= 140
            or dbp >= 90
        ):

            risk_level = "Moderate"

        else:

            risk_level = "Low"


        # ====================================================
        # REFERRAL
        # ====================================================

        referral_required = "No"
        referral_reason = "None"


        referral_reasons = []


        if sbp >= 140 or dbp >= 90:

            referral_reasons.append(
                "Elevated_BP"
            )


        if (
            sbp >= 160
            or dbp >= 110
        ):

            referral_reasons.append(
                "Severe_Hypertension"
            )


        if symptom in [

            "Severe_Headache",
            "Visual_Disturbance",
            "Upper_Abdominal_Pain",
            "Vaginal_Bleeding"

        ]:

            referral_reasons.append(
                "Significant_Symptom"
            )


        if (
            fetal_movement
            == "Reduced"
        ):

            referral_reasons.append(
                "Reduced_Fetal_Movement"
            )


        if (
            fetal_presentation
            in [
                "Breech",
                "Transverse"
            ]
            and week >= 36
        ):

            referral_reasons.append(
                "Abnormal_Presentation"
            )


        if (
            referral_reasons
        ):

            referral_required = "Yes"

            referral_reason = ";".join(
                referral_reasons
            )


        # High-risk patients may have planned referral
        if (
            high_risk
            and rng.random() < 0.15
        ):

            referral_required = "Yes"

            if referral_reason == "None":

                referral_reason = (
                    "High_Risk_Pregnancy"
                )

            else:

                referral_reason += (
                    ";High_Risk_Pregnancy"
                )


        # ====================================================
        # FOLLOW-UP
        # ====================================================

        if referral_required == "Yes":

            follow_up_required = "Yes"

            follow_up_interval = 7

        elif risk_level == "Moderate":

            follow_up_required = "Yes"

            follow_up_interval = 14

        else:

            follow_up_required = "Yes"

            follow_up_interval = 28


        # ====================================================
        # FETAL STATUS
        # ====================================================

        if (
            fetal_movement
            == "Reduced"
            or fhr < 110
            or fhr > 170
        ):

            fetal_status = "Needs_Assessment"

        else:

            fetal_status = "Stable"


        # ====================================================
        # PLACENTAL CONCERN
        # ====================================================

        if (
            symptoms
            == "Vaginal_Bleeding"
        ):

            placental_concern = "Yes"

        else:

            placental_concern = "No"


        # ====================================================
        # MULTIPLE PREGNANCY MONITORING
        # ====================================================

        if (
            patient[
                "Multiple_Pregnancy"
            ]
            == "Yes"
        ):

            multiple_pregnancy_monitoring = "Yes"

        else:

            multiple_pregnancy_monitoring = "No"


        # ====================================================
        # HOSPITALISATION
        # ====================================================

        hospitalisation_required = "No"


        if (
            sbp >= 160
            or dbp >= 110
        ):

            if rng.random() < 0.35:

                hospitalisation_required = "Yes"


        if (
            symptom
            == "Vaginal_Bleeding"
            and symptom_severity == "Severe"
        ):

            hospitalisation_required = "Yes"


        # ====================================================
        # DELIVERY INDICATION
        # ====================================================

        delivery_indicated = "No"


        # If this is the final visit before an early
        # delivery, mark possible delivery indication.

        if week == delivery_week:

            delivery_indicated = "Yes"

        elif (
            delivery_week <= 37
            and week >= delivery_week - 1
        ):

            if (
                risk_level == "High"
                or hospitalisation_required == "Yes"
            ):

                delivery_indicated = "Yes"


        # ====================================================
        # VISIT OUTCOME
        # ====================================================

        if delivery_indicated == "Yes":

            visit_outcome = "Delivery_Planned_or_Indicated"

        elif hospitalisation_required == "Yes":

            visit_outcome = "Hospitalisation"

        elif referral_required == "Yes":

            visit_outcome = "Referred"

        else:

            visit_outcome = "Routine_Follow_Up"


        # ====================================================
        # NEXT VISIT DATE
        # ====================================================

        current_index = visit_number - 1


        if (
            current_index
            <
            len(visit_weeks) - 1
        ):

            next_week = visit_weeks[
                current_index + 1
            ]

            next_visit_date = (
                gestational_date(
                    lmp,
                    next_week,
                    0
                )
            )

        else:

            next_visit_date = pd.NaT


        # ====================================================
        # STORE RECORD
        # ====================================================

        visit_records.append({

            "Patient_ID":
                patient_id,

            "Pregnancy_ID":
                pregnancy_id,

            "Visit_ID":
                f"{patient_id}_V{visit_number:02d}",

            "Visit_Date":
                visit_date,

            "Gestational_Week":
                week,

            "Gestational_Days":
                gestational_days,

            "Trimester":
                trimester,

            "Visit_Type":
                visit_type,

            "Scheduled_Visit":
                scheduled_visit,

            "High_Risk_Visit":
                high_risk_visit,

            "Unscheduled_Visit":
                unscheduled_visit,

            "Weight_kg":
                weight,

            "BMI":
                bmi,

            "SBP_mmHg":
                sbp,

            "DBP_mmHg":
                dbp,

            "SpO2_percent":
                spo2,

            "Fundal_Height_cm":
                fundal_height,

            "Fetal_Heart_Rate_bpm":
                fhr,

            "Fetal_Presentation":
                fetal_presentation,

            "Fetal_Movement_Status":
                fetal_movement,

            "Oedema":
                oedema,

            "Symptoms_Present":
                symptoms_present,

            "Symptoms":
                symptoms,

            "Symptom_Severity":
                symptom_severity,

            "Clinical_Assessment":
                clinical_assessment,

            "Risk_Level":
                risk_level,

            "Referral_Required":
                referral_required,

            "Referral_Reason":
                referral_reason,

            "Follow_Up_Required":
                follow_up_required,

            "Follow_Up_Interval_Days":
                follow_up_interval,

            "Fetal_Status":
                fetal_status,

            "Placental_Concern":
                placental_concern,

            "Multiple_Pregnancy_Monitoring":
                multiple_pregnancy_monitoring,

            "Visit_Outcome":
                visit_outcome,

            "Next_Visit_Date":
                next_visit_date,

            "Hospitalisation_Required":
                hospitalisation_required,

            "Delivery_Indicated":
                delivery_indicated
        })


# ============================================================
# 10. CREATE DATAFRAME
# ============================================================

df_visits = pd.DataFrame(
    visit_records
)


# ============================================================
# 11. DATA TYPES
# ============================================================

df_visits["Visit_Date"] = pd.to_datetime(
    df_visits["Visit_Date"]
)

df_visits["Next_Visit_Date"] = pd.to_datetime(
    df_visits["Next_Visit_Date"]
)


# ============================================================
# 12. SORT DATA
# ============================================================

df_visits = df_visits.sort_values(

    [
        "Patient_ID",
        "Gestational_Week",
        "Visit_Date"
    ]

).reset_index(
    drop=True
)


# ============================================================
# 13. VALIDATION
# ============================================================

validation_errors = []


# ------------------------------------------------------------
# A. Dataset should not be empty
# ------------------------------------------------------------

if len(df_visits) == 0:

    validation_errors.append(
        "Dataset 2 contains zero visits."
    )


# ------------------------------------------------------------
# B. Every patient should have at least one visit
# ------------------------------------------------------------

patients_with_visits = set(
    df_visits["Patient_ID"]
)

patients_in_dataset1 = set(
    df_patients["Patient_ID"]
)


missing_patients = (
    patients_in_dataset1
    - patients_with_visits
)


if missing_patients:

    validation_errors.append(
        "Patients without ANC visits: "
        + ", ".join(
            sorted(
                missing_patients
            )
        )
    )


# ------------------------------------------------------------
# C. Pregnancy IDs must match Dataset 1
# ------------------------------------------------------------

valid_pregnancy_ids = set(
    df_patients[
        "Pregnancy_ID"
    ]
)


invalid_pregnancy_ids = set(
    df_visits[
        "Pregnancy_ID"
    ]
) - valid_pregnancy_ids


if invalid_pregnancy_ids:

    validation_errors.append(
        "Invalid Pregnancy_ID detected."
    )


# ------------------------------------------------------------
# D. Visit IDs must be unique
# ------------------------------------------------------------

if df_visits[
    "Visit_ID"
].duplicated().any():

    validation_errors.append(
        "Duplicate Visit_ID detected."
    )


# ------------------------------------------------------------
# E. Gestational age
# ------------------------------------------------------------

if not df_visits[
    "Gestational_Week"
].between(
    1,
    42
).all():

    validation_errors.append(
        "Gestational week outside 1-42."
    )


# ------------------------------------------------------------
# F. Trimester consistency
# ------------------------------------------------------------

for _, row in df_visits.iterrows():

    expected_trimester = (
        trimester_from_week(
            row["Gestational_Week"]
        )
    )

    if (
        row["Trimester"]
        != expected_trimester
    ):

        validation_errors.append(
            f"{row['Visit_ID']}: "
            "incorrect trimester."
        )


# ------------------------------------------------------------
# G. Weight
# ------------------------------------------------------------

if not df_visits[
    "Weight_kg"
].between(
    35,
    150
).all():

    validation_errors.append(
        "Unrealistic maternal weight."
    )


# ------------------------------------------------------------
# H. BMI
# ------------------------------------------------------------

if not df_visits[
    "BMI"
].between(
    15,
    60
).all():

    validation_errors.append(
        "Unrealistic BMI."
    )


# ------------------------------------------------------------
# I. Blood pressure
# ------------------------------------------------------------

if not df_visits[
    "SBP_mmHg"
].between(
    80,
    200
).all():

    validation_errors.append(
        "Invalid SBP."
    )


if not df_visits[
    "DBP_mmHg"
].between(
    40,
    130
).all():

    validation_errors.append(
        "Invalid DBP."
    )


# ------------------------------------------------------------
# J. SpO2
# ------------------------------------------------------------

if not df_visits[
    "SpO2_percent"
].between(
    90,
    100
).all():

    validation_errors.append(
        "Invalid SpO2 value."
    )


# ------------------------------------------------------------
# K. FHR
# ------------------------------------------------------------

if not df_visits[
    "Fetal_Heart_Rate_bpm"
].between(
    90,
    190
).all():

    validation_errors.append(
        "Invalid fetal heart rate."
    )


# ============================================================
# 14. LONGITUDINAL VALIDATION
# ============================================================

for patient_id, group in df_visits.groupby(
    "Patient_ID"
):

    group = group.sort_values(
        "Gestational_Week"
    )


    # --------------------------------------------------------
    # Gestational weeks must increase
    # --------------------------------------------------------

    weeks = group[
        "Gestational_Week"
    ].tolist()


    if weeks != sorted(
        weeks
    ):

        validation_errors.append(
            f"{patient_id}: "
            "gestational weeks not ordered."
        )


    # --------------------------------------------------------
    # No duplicate gestational-week visits
    # for routine schedule
    # --------------------------------------------------------

    duplicate_weeks = (
        group[
            "Gestational_Week"
        ]
        .duplicated()
        .any()
    )


    if duplicate_weeks:

        validation_errors.append(
            f"{patient_id}: "
            "duplicate gestational week."
        )


    # --------------------------------------------------------
    # Visit dates must increase
    # --------------------------------------------------------

    dates = group[
        "Visit_Date"
    ].tolist()


    if dates != sorted(
        dates
    ):

        validation_errors.append(
            f"{patient_id}: "
            "visit dates not ordered."
        )


    # --------------------------------------------------------
    # No visit after 41 weeks
    # --------------------------------------------------------

    if group[
        "Gestational_Week"
    ].max() > 41:

        validation_errors.append(
            f"{patient_id}: "
            "visit after 41 weeks."
        )


# ============================================================
# 15. VALIDATE PATIENT LINKAGE
# ============================================================

merged_check = df_visits.merge(

    df_patients[
        [
            "Patient_ID",
            "Pregnancy_ID",
            "LMP_Date",
            "EDD_Date"
        ]
    ],

    on=[
        "Patient_ID",
        "Pregnancy_ID"
    ],

    how="left",

    indicator=True
)


if (
    merged_check["_merge"]
    != "both"
).any():

    validation_errors.append(
        "Some Dataset 2 records "
        "cannot be linked to Dataset 1."
    )


# ============================================================
# 16. VALIDATE VISIT DATES AGAINST LMP
# ============================================================

for _, row in merged_check.iterrows():

    expected_min_date = (
        row["LMP_Date"]
        + timedelta(
            days=(
                row["Gestational_Week"]
                * 7
            )
        )
    )


    difference = abs(
        (
            row["Visit_Date"]
            - expected_min_date
        ).days
    )


    if difference > 6:

        validation_errors.append(
            f"{row['Patient_ID']} "
            f"{row['Visit_ID']}: "
            "visit date inconsistent "
            "with gestational age."
        )


# ============================================================
# 17. SAVE CSV
# ============================================================

csv_path = (
    OUTPUT_DIR
    / "anc_clinical_vitals.csv"
)


df_visits.to_csv(
    csv_path,
    index=False,
    date_format="%Y-%m-%d"
)

pd.DataFrame(delivery_plan).to_csv(
    OUTPUT_DIR / "pregnancy_delivery_plan.csv",
    index=False
)


# ============================================================
# 18. CREATE EXCEL INSPECTION COPY
# ============================================================

excel_df = df_visits.copy()


excel_df["Visit_Date"] = (
    excel_df["Visit_Date"]
    .dt.strftime(
        "%d-%b-%Y"
    )
)


excel_df["Next_Visit_Date"] = (
    excel_df["Next_Visit_Date"]
    .dt.strftime(
        "%d-%b-%Y"
    )
)


excel_path = (
    OUTPUT_DIR
    / "anc_clinical_vitals.xlsx"
)


with pd.ExcelWriter(
    excel_path,
    engine="openpyxl"
) as writer:

    excel_df.to_excel(
        writer,
        sheet_name="ANC_Clinical_Vitals",
        index=False
    )


    worksheet = writer.sheets[
        "ANC_Clinical_Vitals"
    ]


    # Freeze header
    worksheet.freeze_panes = "A2"


    # Filter
    worksheet.auto_filter.ref = (
        worksheet.dimensions
    )


    # --------------------------------------------------------
    # Column widths
    # --------------------------------------------------------

    widths = {

        "A": 13,
        "B": 16,
        "C": 16,
        "D": 16,
        "E": 18,
        "F": 18,
        "G": 13,
        "H": 20,
        "I": 17,
        "J": 18,
        "K": 18,
        "L": 13,
        "M": 10,
        "N": 13,
        "O": 13,
        "P": 20,
        "Q": 23,
        "R": 23,
        "S": 23,
        "T": 14,
        "U": 18,
        "V": 28,
        "W": 18,
        "X": 35,
        "Y": 15,
        "Z": 20,
        "AA": 18,
        "AB": 25,
        "AC": 25,
        "AD": 30,
        "AE": 30,
        "AF": 20,
        "AG": 18,
        "AH": 22,
        "AI": 22,
        "AJ": 22
    }


    for column, width in widths.items():

        worksheet.column_dimensions[
            column
        ].width = width


# ============================================================
# 19. SUMMARY STATISTICS
# ============================================================

summary_path = (
    OUTPUT_DIR
    / "dataset2_summary.txt"
)


total_visits = len(
    df_visits
)


unique_patients = (
    df_visits[
        "Patient_ID"
    ].nunique()
)


average_visits = (
    total_visits
    /
    unique_patients
)


high_risk_visits = (
    (
        df_visits[
            "High_Risk_Visit"
        ]
        == "Yes"
    )
    .sum()
)


referrals = (
    (
        df_visits[
            "Referral_Required"
        ]
        == "Yes"
    )
    .sum()
)


hospitalisations = (
    (
        df_visits[
            "Hospitalisation_Required"
        ]
        == "Yes"
    )
    .sum()
)


mean_spo2 = df_visits["SpO2_percent"].mean()
min_spo2 = df_visits["SpO2_percent"].min()
spo2_below_95 = (df_visits["SpO2_percent"] < 95).sum()


with open(
    summary_path,
    "w",
    encoding="utf-8"
) as f:

    f.write(
        "DATASET 2 SUMMARY\n"
    )

    f.write(
        "=================\n\n"
    )

    f.write(
        f"Patients              : "
        f"{unique_patients}\n"
    )

    f.write(
        f"Total ANC visits      : "
        f"{total_visits}\n"
    )

    f.write(
        f"Average visits/patient: "
        f"{average_visits:.2f}\n"
    )

    f.write(
        f"High-risk visits      : "
        f"{high_risk_visits}\n"
    )

    f.write(
        f"Referrals             : "
        f"{referrals}\n"
    )

    f.write(
        f"Hospitalisations      : "
        f"{hospitalisations}\n"
    )

    f.write(
        f"Mean SpO2 (%)         : "
        f"{mean_spo2:.2f}\n"
    )

    f.write(
        f"Minimum SpO2 (%)      : "
        f"{min_spo2:.1f}\n"
    )

    f.write(
        f"Visits with SpO2 <95% : "
        f"{spo2_below_95}\n"
    )


# ============================================================
# 20. VALIDATION REPORT
# ============================================================

validation_report_path = (
    OUTPUT_DIR
    / "dataset2_validation_report.txt"
)


with open(
    validation_report_path,
    "w",
    encoding="utf-8"
) as report:

    report.write(
        "DATASET 2 VALIDATION REPORT\n"
    )

    report.write(
        "===========================\n\n"
    )

    report.write(
        f"Dataset 1 patients : "
        f"{len(df_patients)}\n"
    )

    report.write(
        f"Dataset 2 visits   : "
        f"{len(df_visits)}\n"
    )

    report.write(
        f"Unique patients     : "
        f"{unique_patients}\n"
    )

    report.write(
        f"Validation errors   : "
        f"{len(validation_errors)}\n\n"
    )


    if validation_errors:

        report.write(
            "STATUS: FAILED\n\n"
        )

        for error in validation_errors:

            report.write(
                f"- {error}\n"
            )

    else:

        report.write(
            "STATUS: PASSED\n"
        )

        report.write(
            "All validation checks passed.\n"
        )


# ============================================================
# 21. CONSOLE OUTPUT
# ============================================================

print()
print("=" * 70)

print(
    "DATASET 2 GENERATION COMPLETE"
)

print("=" * 70)

print()

print(
    f"Patients loaded       : "
    f"{len(df_patients)}"
)

print(
    f"ANC visits generated  : "
    f"{total_visits}"
)

print(
    f"Average visits/patient: "
    f"{average_visits:.2f}"
)

print(
    f"High-risk visits      : "
    f"{high_risk_visits}"
)

print(
    f"Referrals             : "
    f"{referrals}"
)

print(
    f"Hospitalisations      : "
    f"{hospitalisations}"
)

print(
    f"Mean SpO2 (%)         : "
    f"{mean_spo2:.2f}"
)

print(
    f"Minimum SpO2 (%)      : "
    f"{min_spo2:.1f}"
)

print(
    f"Visits with SpO2 <95% : "
    f"{spo2_below_95}"
)

print(
    f"Validation errors     : "
    f"{len(validation_errors)}"
)


if validation_errors:

    print()
    print(
        "VALIDATION FAILED"
    )

    print()

    for error in validation_errors[:20]:

        print(
            "ERROR:",
            error
        )

    if len(validation_errors) > 20:

        print(
            f"... and "
            f"{len(validation_errors) - 20} "
            f"more errors."
        )

else:

    print()
    print(
        "VALIDATION PASSED"
    )


print()

print(
    "Files created:"
)

print(
    csv_path
)

print(
    excel_path
)

print(
    summary_path
)

print(
    validation_report_path
)

print()

print(
    "First 10 visits:"
)

print()

print(
    excel_df.head(
        10
    ).to_string(
        index=False
    )
)

print()
print(
    "Dataset 2 complete."
)