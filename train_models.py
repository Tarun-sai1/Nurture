"""
Train the preterm-birth and NICU-admission risk models.

    python train_models.py

Writes models/preterm_model.joblib, models/nicu_model.joblib,
models/model_report.json and models/training_log.txt.
"""
import numpy as np
from sklearn.metrics import roc_auc_score

from mh.data import load_data, targets
from mh.features import build_visit_features
from mh.model import MODEL_DIR, TARGETS, save_models, train_target

lines = []


def log(msg=""):
    print(msg)
    lines.append(str(msg))


def preterm_ceiling(data, labels) -> float:
    """Best achievable ROC-AUC: score each pregnancy with the exact preterm
    probability used by generate_dataset2 (determine_delivery_week)."""
    p = data.patients
    y_ = lambda c: (p[c] == "Yes").astype(int)
    score = (2 * y_("Preexisting_Hypertension") + 2 * y_("Preexisting_Diabetes") + y_("Previous_PreEclampsia")
             + y_("Previous_GDM") + 2 * y_("Renal_Disease") + 2 * y_("Cardiac_Disease")
             + 3 * y_("Multiple_Pregnancy") + (p.Age_Years >= 35) + (p.Pre_Pregnancy_BMI >= 30))
    early = np.where(score >= 3, 0.28, 0.12)
    # Multiples that are not "early" deliver at 36, 37 or 38 weeks -> 1/3 preterm.
    prob = np.where(p.Multiple_Pregnancy == "Yes", early + (1 - early) / 3, early)
    y = labels.set_index("Pregnancy_ID").loc[p.Pregnancy_ID, "preterm"].to_numpy()
    return float(roc_auc_score(y, prob))


def gdm_ceiling(data, labels) -> float:
    """Best achievable ROC-AUC for GDM: generate_dataset3 draws the screening
    glucose from a higher mean (150 vs 115 mg/dL) only when the woman has
    pre-existing diabetes or previous GDM, so that flag is all a model can know
    before the test."""
    p = data.patients
    risk = ((p.Preexisting_Diabetes == "Yes") | (p.Previous_GDM == "Yes")).astype(float).to_numpy()
    y = labels.set_index("Pregnancy_ID").loc[p.Pregnancy_ID, "gdm"].to_numpy()
    return float(roc_auc_score(y, risk))


def main():
    data = load_data()
    feats = build_visit_features(data)
    labels = targets(data)
    log(f"Visit-level feature table: {feats.shape[0]} visits x {feats.shape[1]} columns")
    models = {t: train_target(t, feats, labels, log=log) for t in TARGETS}
    oracle = preterm_ceiling(data, labels)
    log(f"\nPreterm ceiling: a model that knew the generator's TRUE probabilities would score "
        f"ROC-AUC {oracle:.3f}. Ours: {models['preterm'].comparison[models['preterm'].model_name]['roc_auc']:.3f}")
    g_or = gdm_ceiling(data, labels)
    log(f"GDM ceiling: {g_or:.3f}. Ours: {models['gdm'].comparison[models['gdm'].model_name]['roc_auc']:.3f}")
    save_models(models, extra={"preterm_oracle_roc_auc": oracle, "gdm_oracle_roc_auc": g_or})
    (MODEL_DIR / "training_log.txt").write_text("\n".join(lines))
    log(f"\nSaved to {MODEL_DIR}")


if __name__ == "__main__":
    main()
