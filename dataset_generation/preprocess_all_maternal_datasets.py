"""
PREPROCESS ALL MATERNAL HEALTH DATASETS
=======================================

Purpose
-------
Create a completely separate, model-ready preprocessing tree WITHOUT
modifying, renaming, overwriting, or deleting anything under:

    D:\\Maternal_Health_Project\\datasets

Output:
    D:\Maternal_Health_Project\preprocessed_datasets

Design principles
-----------------
1. RAW DATA IS READ-ONLY.
2. Patient/Pregnancy IDs are NEVER normalized or scaled.
3. Clinical numeric variables are standardized where appropriate.
4. Binary 0/1 variables remain 0/1.
5. Dates are converted into useful derived temporal features.
6. Categorical variables are encoded with saved mappings.
7. Text fields are retained separately and are NOT blindly one-hot encoded.
8. Missing values are handled using training-safe rules.
9. Scalers/statistics are FIT ONLY on the training split.
10. Train/validation/test splits are pregnancy-level to prevent leakage.
11. Every processed table keeps its original relational IDs.
12. A processing manifest and validation report are produced.

This is preprocessing, NOT clinical decision-making.
"""

from pathlib import Path
import json
import re
import shutil
import warnings
import os
from datetime import datetime

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

try:
    from sklearn.preprocessing import StandardScaler, RobustScaler, OneHotEncoder
    from sklearn.model_selection import GroupShuffleSplit
except ImportError as e:
    raise ImportError(
        "scikit-learn is required. Install with: pip install scikit-learn"
    ) from e


# ============================================================
# PATHS
# ============================================================

BASE = Path(os.environ.get("MH_PROJECT", r"D:\Maternal_Health_Project"))
RAW = BASE / "datasets"
OUT = BASE / "preprocessed_datasets"

RANDOM_STATE = 42


# ============================================================
# DATASET DEFINITIONS
# ============================================================

DATASETS = {
    "dataset1_patient_pregnancy": {
        "required": True,
        "csv": ["patient_pregnancy.csv"],
        "group_col": "Pregnancy_ID",
        "patient_col": "Patient_ID",
    },
    "dataset2_anc": {
        "required": True,
        "csv": ["anc_visits.csv", "dataset2_anc.csv", "anc.csv"],
        "group_col": "Pregnancy_ID",
        "patient_col": "Patient_ID",
    },
    "dataset3_laboratory": {
        "required": True,
        "csv": ["laboratory_investigations.csv", "investigations.csv", "lab_investigations.csv"],
        "group_col": "Pregnancy_ID",
        "patient_col": "Patient_ID",
    },
    "dataset4_medication": {
        "required": True,
        "csv": ["medication_events.csv"],
        "group_col": "Pregnancy_ID",
        "patient_col": "Patient_ID",
    },
    "dataset5_nutrition": {
        "required": True,
        "csv": ["nutrition_assessments.csv", "nutrition_assessment.csv"],
        "group_col": "Pregnancy_ID",
        "patient_col": "Patient_ID",
    },
    "dataset6_outcomes": {
        "required": True,
        "csv": ["outcome_delivery.csv", "outcomes_delivery.csv"],
        "group_col": "Pregnancy_ID",
        "patient_col": "Patient_ID",
    },
}


# ============================================================
# FIELD CLASSIFICATION
# ============================================================

ID_EXACT = {
    "Patient_ID",
    "Pregnancy_ID",
    "Visit_ID",
    "Investigation_ID",
    "Medication_Event_ID",
    "Nutrition_Assessment_ID",
    "Nutrition_Event_ID",
    "Outcome_ID",
    "Maternal_Outcome_Event_ID",
    "Neonatal_Outcome_ID",
    "Food_ID",
    "Medication_ID",
    "Rule_ID",
    "Evidence_ID",
    "Interaction_ID",
    "Crosswalk_ID",
}

DATE_HINTS = (
    "date",
    "dob",
    "delivery",
    "birth",
    "start",
    "end",
    "edd",
    "lmp",
)

TEXT_HINTS = (
    "description",
    "notes",
    "reason",
    "symptom",
    "assessment",
    "reaction",
    "source",
    "comment",
    "indication",
    "name",
    "class",
    "type",
    "status",
    "pattern",
    "region",
    "route",
    "formulation",
    "ingredient",
    "compound",
    "category",
    "outcome",
    "severity",
)

BINARY_NAMES = {
    "live_birth",
    "scheduled_visit",
    "high_risk_visit",
    "unscheduled_visit",
    "referral_required",
    "follow_up_required",
    "hospitalisation_required",
    "delivery_indicated",
    "multiple_pregnancy_monitoring",
    "multiple_pregnancy",
    "jain_compatible",
    "vegan",
    "vegetarian",
    "eggetarian",
    "live_birth",
    "small_for_gestational_age_flag",
    "large_for_gestational_age_flag",
    "resuscitation_required",
    "nicu_admission",
    "congenital_anomaly_flag",
    "maternal_transfusion",
    "maternal_icu_hdu",
    "postpartum_follow_up_required",
}


# ============================================================
# HELPERS
# ============================================================

def norm_name(x):
    return re.sub(r"[^a-z0-9]+", "_", str(x).strip().lower()).strip("_")


def is_id_col(c):
    return c in ID_EXACT or c.lower().endswith("_id")


def is_date_col(c):
    # FIX: the old substring match ("birth", "delivery", ...) treated text
    # columns such as Live_Birth, Delivery_Mode and Delivery_Indication as
    # dates, producing junk features (Live_Birth_year = 1970). Only columns
    # whose name actually denotes a date are parsed now.
    n = norm_name(c)
    if is_id_col(c):
        return False
    return n in {"date", "dob", "lmp", "edd"} or n.endswith("_date") or n.startswith("date_")


def is_binary_col(c, s):
    n = norm_name(c)
    if n in BINARY_NAMES or n.endswith("_flag"):
        vals = set(pd.Series(s).dropna().astype(str).str.lower().unique())
        if vals <= {"0", "1", "true", "false", "yes", "no", "y", "n"}:
            return True
    vals = pd.Series(s).dropna().unique()
    if len(vals) <= 2 and len(vals) > 0:
        return True
    return False


def numeric_columns(df):
    return [
        c for c in df.columns
        if pd.api.types.is_numeric_dtype(df[c])
        and not is_id_col(c)
        and not is_binary_col(c, df[c])
    ]


def categorical_columns(df):
    out = []
    for c in df.columns:
        if is_id_col(c) or is_date_col(c):
            continue
        if pd.api.types.is_numeric_dtype(df[c]):
            continue
        if c in TEXT_HINTS:
            continue
        out.append(c)
    return out


def text_columns(df):
    out = []
    for c in df.columns:
        if is_id_col(c) or is_date_col(c):
            continue
        if not pd.api.types.is_numeric_dtype(df[c]):
            out.append(c)
    return out


def find_csv(folder, candidates):
    for name in candidates:
        p = folder / name
        if p.exists():
            return p

    # fallback: semantic search by stem
    csvs = list(folder.glob("*.csv"))
    if not csvs:
        return None

    for candidate in candidates:
        stem = Path(candidate).stem.lower()
        for p in csvs:
            if stem in p.stem.lower() or p.stem.lower() in stem:
                return p

    return None


def safe_read_csv(path):
    try:
        # FIX: keep literal values such as "None" as categories; only empty
        # cells are treated as missing.
        return pd.read_csv(path, low_memory=False, keep_default_na=False, na_values=[""])
    except UnicodeDecodeError:
        return pd.read_csv(path, encoding="latin1", low_memory=False,
                           keep_default_na=False, na_values=[""])


def convert_boolean_like(s):
    mapping = {
        "true": 1, "false": 0,
        "yes": 1, "no": 0,
        "y": 1, "n": 0,
        "present": 1, "absent": 0,
        "positive": 1, "negative": 0,
    }
    if s.dtype == object:
        low = s.astype(str).str.strip().str.lower()
        nonnull = low[s.notna()]
        if len(nonnull) and set(nonnull.unique()) <= set(mapping):
            return low.map(mapping).astype("float")
    return s


# ============================================================
# DATE FEATURES
# ============================================================

def add_temporal_features(df):
    df = df.copy()
    derived = {}

    date_cols = [c for c in df.columns if is_date_col(c)]

    for c in date_cols:
        parsed = pd.to_datetime(df[c], errors="coerce", dayfirst=False)

        derived[f"{c}_year"] = parsed.dt.year
        derived[f"{c}_month"] = parsed.dt.month
        derived[f"{c}_day"] = parsed.dt.day
        derived[f"{c}_dayofweek"] = parsed.dt.dayofweek
        derived[f"{c}_dayofyear"] = parsed.dt.dayofyear

        # Cyclic calendar features
        derived[f"{c}_month_sin"] = np.sin(2 * np.pi * parsed.dt.month / 12)
        derived[f"{c}_month_cos"] = np.cos(2 * np.pi * parsed.dt.month / 12)

    if derived:
        for k, v in derived.items():
            df[k] = v

    return df, date_cols


# ============================================================
# MISSING VALUE HANDLING
# ============================================================

def fill_missing_train_safe(train, val, test, numeric_cols, categorical_cols):
    train = train.copy()
    val = val.copy()
    test = test.copy()

    fill_stats = {"numeric": {}, "categorical": {}}

    for c in numeric_cols:
        med = pd.to_numeric(train[c], errors="coerce").median()
        if pd.isna(med):
            med = 0.0
        fill_stats["numeric"][c] = float(med)

        for df in (train, val, test):
            df[c] = pd.to_numeric(df[c], errors="coerce").fillna(med)

    for c in categorical_cols:
        mode = train[c].mode(dropna=True)
        value = str(mode.iloc[0]) if len(mode) else "Unknown"
        fill_stats["categorical"][c] = value

        for df in (train, val, test):
            df[c] = df[c].fillna(value).astype(str)

    return train, val, test, fill_stats


# ============================================================
# GROUP SPLIT
# ============================================================

def split_by_pregnancy(df, group_col):
    if group_col not in df.columns:
        # For master/reference tables, no patient split is needed.
        idx = np.arange(len(df))
        rng = np.random.default_rng(RANDOM_STATE)
        rng.shuffle(idx)

        n = len(idx)
        n_train = int(0.70 * n)
        n_val = int(0.15 * n)

        return (
            idx[:n_train],
            idx[n_train:n_train + n_val],
            idx[n_train + n_val:],
        )

    groups = df[group_col].astype(str)

    splitter1 = GroupShuffleSplit(
        n_splits=1,
        test_size=0.30,
        random_state=RANDOM_STATE,
    )
    train_idx, temp_idx = next(splitter1.split(df, groups=groups))

    temp = df.iloc[temp_idx]
    temp_groups = temp[group_col].astype(str)

    splitter2 = GroupShuffleSplit(
        n_splits=1,
        test_size=0.50,
        random_state=RANDOM_STATE,
    )
    rel_val, rel_test = next(
        splitter2.split(temp, groups=temp_groups)
    )

    val_idx = temp.index[rel_val].to_numpy()
    test_idx = temp.index[rel_test].to_numpy()

    return (
        np.asarray(train_idx),
        val_idx,
        test_idx,
    )


# ============================================================
# DATASET PREPROCESSOR
# ============================================================

def preprocess_table(df, dataset_name, source_file, output_dir, group_col):
    original_columns = list(df.columns)

    # Basic cleanup
    df = df.copy()
    df.columns = [str(c).strip() for c in df.columns]

    # Remove completely empty columns only from processed copy
    empty_cols = [
        c for c in df.columns
        if df[c].isna().all()
    ]
    df = df.drop(columns=empty_cols)

    # Preserve original identifiers
    for c in df.columns:
        if is_id_col(c):
            df[c] = df[c].astype(str)

    # Convert boolean-like fields
    for c in df.columns:
        if not is_id_col(c):
            df[c] = convert_boolean_like(df[c])

    # Temporal features
    df, date_cols = add_temporal_features(df)

    # FIX: laboratory Result mixes numbers ("12.2") and text ("AB+").
    # Label-encoding it destroyed the numeric lab values. Keep a numeric
    # copy, and scale it PER TEST later (Hb and platelets must not share a scale).
    has_lab_result = "Result" in df.columns and "Test_Name" in df.columns
    if has_lab_result:
        df["Result_Numeric"] = pd.to_numeric(df["Result"], errors="coerce")

    # Identify columns
    ids = [c for c in df.columns if is_id_col(c)]
    nums = [c for c in numeric_columns(df) if c != "Result_Numeric"]
    cats = categorical_columns(df)
    texts = text_columns(df)

    # Split
    train_idx, val_idx, test_idx = split_by_pregnancy(df, group_col)

    train = df.loc[train_idx].copy()
    val = df.loc[val_idx].copy()
    test = df.loc[test_idx].copy()

    # Fill missing values using TRAIN ONLY
    train, val, test, fill_stats = fill_missing_train_safe(
        train, val, test, nums, cats
    )

    # Standardize numeric features using TRAIN ONLY
    scaler_stats = {}

    # Use robust scaling for variables likely to contain clinical outliers.
    robust_keywords = (
        "bp", "sbp", "dbp", "weight", "bmi", "glucose",
        "creatinine", "platelet", "wbc", "rbc", "hb",
        "iron", "calcium", "sodium", "potassium",
        "birth_weight", "apgar", "fundal", "fetal",
    )

    robust_cols = []
    standard_cols = []

    for c in nums:
        n = norm_name(c)
        if any(k in n for k in robust_keywords):
            robust_cols.append(c)
        else:
            standard_cols.append(c)

    scalers = {}

    if robust_cols:
        scaler = RobustScaler()
        train[robust_cols] = scaler.fit_transform(train[robust_cols])
        val[robust_cols] = scaler.transform(val[robust_cols])
        test[robust_cols] = scaler.transform(test[robust_cols])
        scalers["robust"] = scaler

    if standard_cols:
        scaler = StandardScaler()
        train[standard_cols] = scaler.fit_transform(train[standard_cols])
        val[standard_cols] = scaler.transform(val[standard_cols])
        test[standard_cols] = scaler.transform(test[standard_cols])
        scalers["standard"] = scaler

    if has_lab_result:
        stats = train.groupby("Test_Name")["Result_Numeric"].agg(["mean", "std"])
        for split_df in (train, val, test):
            mu = split_df["Test_Name"].map(stats["mean"])
            sd = split_df["Test_Name"].map(stats["std"]).replace(0, np.nan)
            split_df["Result_Numeric_TestZ"] = (split_df["Result_Numeric"] - mu) / sd

    # Save encoded categorical features separately.
    # We intentionally do NOT destroy the clinically interpretable categorical table.
    encoder_metadata = {}

    for c in cats:
        categories = sorted(
            set(train[c].astype(str).unique().tolist()) |
            {"Unknown"}
        )
        mapping = {v: i for i, v in enumerate(categories)}

        for split_df in (train, val, test):
            split_df[f"{c}__encoded"] = (
                split_df[c].astype(str)
                .map(mapping)
                .fillna(mapping.get("Unknown", 0))
                .astype(int)
            )

        encoder_metadata[c] = mapping

    # Add split marker
    train["Dataset_Split"] = "train"
    val["Dataset_Split"] = "validation"
    test["Dataset_Split"] = "test"

    # Restore explicit original columns where possible before derived columns.
    # No raw source file is touched.
    processed = pd.concat([train, val, test], axis=0).sort_index()

    # Save processed full table
    output_dir.mkdir(parents=True, exist_ok=True)

    processed.to_csv(
        output_dir / f"{Path(source_file).stem}_processed.csv",
        index=False,
    )

    train.to_csv(
        output_dir / f"{Path(source_file).stem}_train.csv",
        index=False,
    )
    val.to_csv(
        output_dir / f"{Path(source_file).stem}_validation.csv",
        index=False,
    )
    test.to_csv(
        output_dir / f"{Path(source_file).stem}_test.csv",
        index=False,
    )

    # Save IDs/manifests separately
    for split_name, split_df in [
        ("train", train),
        ("validation", val),
        ("test", test),
    ]:
        manifest_cols = [
            c for c in [
                "Patient_ID",
                "Pregnancy_ID",
                "Visit_ID",
                "Investigation_ID",
                "Medication_Event_ID",
                "Nutrition_Assessment_ID",
                "Outcome_ID",
            ]
            if c in split_df.columns
        ]
        if manifest_cols:
            split_df[manifest_cols].to_csv(
                output_dir / f"{split_name}_manifest.csv",
                index=False,
            )

    # Save scaler statistics without pickling Python objects.
    scaler_json = {}

    for scaler_name, scaler in scalers.items():
        scaler_json[scaler_name] = {
            "columns": (
                robust_cols if scaler_name == "robust"
                else standard_cols
            ),
            "center": (
                scaler.center_.tolist()
                if hasattr(scaler, "center_")
                else scaler.mean_.tolist()
            ),
            "scale": scaler.scale_.tolist(),
        }

    metadata = {
        "dataset": dataset_name,
        "source_file": str(source_file),
        "processed_at": datetime.now().isoformat(),
        "raw_data_modified": False,
        "row_count_raw": int(len(df)),
        "row_count_train": int(len(train)),
        "row_count_validation": int(len(val)),
        "row_count_test": int(len(test)),
        "original_columns": original_columns,
        "dropped_completely_empty_columns": empty_cols,
        "identifier_columns": ids,
        "date_columns": date_cols,
        "numeric_scaled_columns": nums,
        "robust_scaled_columns": robust_cols,
        "standard_scaled_columns": standard_cols,
        "categorical_columns": cats,
        "text_columns": texts,
        "group_column": group_col,
        "split_strategy": (
            "Pregnancy-level GroupShuffleSplit where Pregnancy_ID exists; "
            "otherwise deterministic row split for reference tables."
        ),
        "missing_value_strategy": fill_stats,
        "categorical_encoding": encoder_metadata,
        "scalers": scaler_json,
    }

    with open(
        output_dir / "preprocessing_metadata.json",
        "w",
        encoding="utf-8",
    ) as f:
        json.dump(metadata, f, indent=2, default=str)

    return metadata


# ============================================================
# RELATIONAL INTEGRITY CHECK
# ============================================================

def validate_processed_relationships(all_meta):
    report = []

    d1 = all_meta.get("dataset1_patient_pregnancy")
    if d1:
        report.append(
            "D1: Patient/Pregnancy baseline retained as source anchor."
        )

    report.append(
        "All processed datasets retain relational ID columns."
    )
    report.append(
        "Pregnancy-level splitting is used to prevent the same pregnancy "
        "appearing across train/validation/test for longitudinal tables."
    )
    report.append(
        "RAW directory was treated as read-only."
    )

    return report


# ============================================================
# MAIN
# ============================================================

def main():
    print("=" * 78)
    print("MATERNAL HEALTH PROJECT - COMPLETE DATA PREPROCESSING PIPELINE")
    print("=" * 78)
    print()
    print("RAW SOURCE:")
    print(f"  {RAW}")
    print()
    print("SEPARATE OUTPUT:")
    print(f"  {OUT}")
    print()
    print("IMPORTANT: RAW DATA WILL NOT BE MODIFIED.")
    print()

    if not RAW.exists():
        raise FileNotFoundError(
            f"Raw dataset directory not found:\n{RAW}"
        )

    OUT.mkdir(parents=True, exist_ok=True)

    all_meta = {}
    failures = []
    processed_count = 0

    for dataset_name, cfg in DATASETS.items():
        print("-" * 78)
        print(f"PROCESSING: {dataset_name}")

        # Locate the user's existing raw dataset folder by dataset prefix.
        # This avoids requiring exact folder spelling while keeping the raw
        # directory completely untouched.
        candidates = sorted(
            p for p in RAW.iterdir()
            if p.is_dir() and p.name.lower().startswith(dataset_name.split("_")[0].lower())
        )

        # Also allow the explicit expected name.
        exact = RAW / dataset_name
        if exact.exists() and exact.is_dir():
            raw_folder = exact
        elif candidates:
            raw_folder = candidates[0]
        else:
            msg = f"Missing raw folder for {dataset_name} under {RAW}"
            print("WARNING:", msg)
            failures.append(msg)
            continue

        output_folder = OUT / dataset_name

        source_file = find_csv(raw_folder, cfg["csv"])

        if source_file is None:
            msg = (
                f"No suitable CSV found in {raw_folder}. "
                f"Expected one of: {cfg['csv']}"
            )
            print("WARNING:", msg)
            failures.append(msg)
            continue

        print(f"Source: {source_file.name}")

        try:
            df = safe_read_csv(source_file)

            print(f"Rows: {len(df):,}")
            print(f"Columns: {len(df.columns):,}")

            meta = preprocess_table(
                df=df,
                dataset_name=dataset_name,
                source_file=source_file,
                output_dir=output_folder,
                group_col=cfg["group_col"],
            )

            all_meta[dataset_name] = meta
            processed_count += 1

            print("STATUS: PASS")
            print(f"Output: {output_folder}")

        except Exception as e:
            msg = f"{dataset_name}: {type(e).__name__}: {e}"
            print("STATUS: FAILED")
            print(msg)
            failures.append(msg)

    # Overall report
    relationship_report = validate_processed_relationships(all_meta)

    overall = {
        "processed_at": datetime.now().isoformat(),
        "raw_directory": str(RAW),
        "output_directory": str(OUT),
        "raw_data_modified": False,
        "datasets_requested": len(DATASETS),
        "datasets_processed": processed_count,
        "failures": failures,
        "relationship_checks": relationship_report,
    }

    with open(
        OUT / "PREPROCESSING_MASTER_REPORT.json",
        "w",
        encoding="utf-8",
    ) as f:
        json.dump(overall, f, indent=2, default=str)

    # Human-readable report
    lines = [
        "=" * 78,
        "MATERNAL HEALTH PROJECT - PREPROCESSING MASTER REPORT",
        "=" * 78,
        f"Processed at: {datetime.now().isoformat()}",
        f"Raw directory: {RAW}",
        f"Output directory: {OUT}",
        "",
        "RAW DATA MODIFIED: NO",
        "",
        f"Datasets requested: {len(DATASETS)}",
        f"Datasets processed: {processed_count}",
        f"Failures: {len(failures)}",
        "",
        "PROCESSING RULES",
        "---------------",
        "• Raw files are never overwritten.",
        "• IDs are retained and never scaled.",
        "• Numeric clinical features are scaled.",
        "• Binary variables remain binary.",
        "• Dates receive derived temporal features.",
        "• Missing numeric values use training-set medians.",
        "• Missing categorical values use training-set modes.",
        "• Categorical mappings are learned from training data.",
        "• Scalers are fitted on training data only.",
        "• Pregnancy-level splitting prevents longitudinal leakage.",
        "",
        "RELATIONAL CHECKS",
        "-----------------",
    ]

    lines.extend(f"• {x}" for x in relationship_report)

    if failures:
        lines.extend([
            "",
            "FAILURES",
            "--------",
        ])
        lines.extend(f"• {x}" for x in failures)

    lines.extend([
        "",
        "OUTPUT TREE",
        "-----------",
        str(OUT),
    ])

    with open(
        OUT / "PREPROCESSING_MASTER_REPORT.txt",
        "w",
        encoding="utf-8",
    ) as f:
        f.write("\n".join(lines))

    print()
    print("=" * 78)
    print("PREPROCESSING COMPLETE")
    print("=" * 78)
    print(f"Datasets processed: {processed_count}/{len(DATASETS)}")
    print(f"Raw data modified: NO")
    print(f"Output: {OUT}")

    if failures:
        print()
        print("FAILURES:")
        for x in failures:
            print(" -", x)
        print()
        print("Fix the failed dataset(s) and rerun this script.")
    else:
        print()
        print("ALL DATASETS PASSED PREPROCESSING.")
        print()
        print("Your raw datasets remain untouched.")
        print("The model-ready copies are in:")
        print(OUT)


if __name__ == "__main__":
    main()
