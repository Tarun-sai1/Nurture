"""
Risk models: preterm birth and NICU admission.

Design
- Unit of prediction: one ANC visit ("risk as of this visit").
- Cross-validation groups by Pregnancy_ID, so no pregnancy is ever in both
  the training and validation folds (prevents longitudinal leakage).
- Preterm model is trained/evaluated only on visits before 37 weeks;
  after 37 weeks a pregnancy cannot become preterm, so those rows would
  be trivially easy and inflate the scores.
- Every pregnancy is scored by the fold model that did NOT see it in
  training (out-of-fold). The dashboard uses exactly these models, so
  the risk shown for any patient is an honest held-out prediction.
- Explanations: occlusion. Each feature is reset to a "typical" value
  (training median) and the change in predicted risk is measured.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (accuracy_score, average_precision_score, balanced_accuracy_score,
                             brier_score_loss, confusion_matrix, f1_score, roc_auc_score, roc_curve)
from sklearn.model_selection import StratifiedGroupKFold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from .features import FEATURE_LABELS, FEATURES

ROOT = Path(__file__).resolve().parents[1]
MODEL_DIR = ROOT / "models"
SEED = 42
N_FOLDS = 5

TARGETS = {
    "preterm": {"title": "Preterm birth (< 37 weeks)", "max_ga": 37.0},
    "nicu": {"title": "NICU admission of the newborn", "max_ga": None},
    # GDM is diagnosed by the 24-28 week glucose test. Predicting it AFTER the
    # test is trivial, so the model only learns from visits before 24 weeks:
    # "who should we watch closely before the test?"
    "gdm": {"title": "Gestational diabetes (predicted before the 24–28 wk glucose test)", "max_ga": 24.0},
}


def candidate_models():
    return {
        "Logistic Regression": make_pipeline(
            SimpleImputer(strategy="median"), StandardScaler(),
            LogisticRegression(class_weight="balanced", C=0.3, max_iter=2000)),
        "Random Forest": make_pipeline(
            SimpleImputer(strategy="median"),
            RandomForestClassifier(n_estimators=400, min_samples_leaf=8, max_features="sqrt",
                                   class_weight="balanced_subsample", random_state=SEED, n_jobs=-1)),
        "Gradient Boosting": HistGradientBoostingClassifier(
            max_depth=3, learning_rate=0.05, max_iter=250, l2_regularization=1.0,
            class_weight="balanced", random_state=SEED),
    }


def _rows_for(target: str, feats: pd.DataFrame, labels: pd.DataFrame) -> pd.DataFrame:
    df = feats.merge(labels[["Pregnancy_ID", target]], on="Pregnancy_ID", how="inner")
    max_ga = TARGETS[target]["max_ga"]
    if max_ga is not None:
        df = df[df["ga_weeks"] < max_ga]
    return df.reset_index(drop=True)


def _folds(df: pd.DataFrame, target: str):
    preg = df.groupby("Pregnancy_ID")[target].first()
    sgkf = StratifiedGroupKFold(n_splits=N_FOLDS, shuffle=True, random_state=SEED)
    # Split at pregnancy level, then map back to rows.
    pid = preg.index.to_numpy()
    fold_of = {}
    for k, (_, te) in enumerate(sgkf.split(pid, preg.to_numpy(), groups=pid)):
        for p in pid[te]:
            fold_of[p] = k
    return fold_of


def _metrics(y, p, thr):
    pred = (p >= thr).astype(int)
    tn, fp, fn, tp = confusion_matrix(y, pred, labels=[0, 1]).ravel()
    return {
        "threshold": float(thr),
        "accuracy": float(accuracy_score(y, pred)),
        "baseline_accuracy": float(max(np.mean(y), 1 - np.mean(y))),   # always predict majority class
        "balanced_accuracy": float(balanced_accuracy_score(y, pred)),
        "f1": float(f1_score(y, pred, zero_division=0)),
        "npv": float(tn / (tn + fn)) if tn + fn else 0.0,
        "roc_auc": float(roc_auc_score(y, p)),
        "pr_auc": float(average_precision_score(y, p)),
        "brier": float(brier_score_loss(y, p)),
        "sensitivity": float(tp / (tp + fn)) if tp + fn else 0.0,
        "specificity": float(tn / (tn + fp)) if tn + fp else 0.0,
        "ppv": float(tp / (tp + fp)) if tp + fp else 0.0,
        "tp": int(tp), "fp": int(fp), "tn": int(tn), "fn": int(fn),
        "prevalence": float(np.mean(y)),
    }


@dataclass
class RiskModel:
    target: str
    model_name: str
    fold_models: list
    fold_of: dict
    medians: dict
    thresholds: dict            # {"moderate": t1, "high": t2}
    metrics: dict = field(default_factory=dict)
    comparison: dict = field(default_factory=dict)
    importance: dict = field(default_factory=dict)

    # -------- prediction for one visit
    def _model_for(self, pregnancy_id: str):
        k = self.fold_of.get(pregnancy_id)
        return self.fold_models[k] if k is not None else self.fold_models[0]

    def predict_row(self, row: pd.Series) -> float:
        x = pd.DataFrame([row[FEATURES].astype(float).to_numpy()], columns=FEATURES)
        return float(self._model_for(row["Pregnancy_ID"]).predict_proba(x)[0, 1])

    def band(self, p: float) -> str:
        if p >= self.thresholds["high"]:
            return "High"
        if p >= self.thresholds["moderate"]:
            return "Moderate"
        return "Low"

    def explain_row(self, row: pd.Series, top: int = 5):
        """Occlusion explanation: risk change when each feature is set to typical."""
        model = self._model_for(row["Pregnancy_ID"])
        base = pd.DataFrame([row[FEATURES].astype(float).to_numpy()], columns=FEATURES)
        p0 = float(model.predict_proba(base)[0, 1])
        variants = pd.concat([base] * len(FEATURES), ignore_index=True)
        for i, f in enumerate(FEATURES):
            variants.loc[i, f] = self.medians[f]
        p = model.predict_proba(variants)[:, 1]
        contrib = pd.DataFrame({
            "feature": FEATURES,
            "label": [FEATURE_LABELS[f] for f in FEATURES],
            "value": base.iloc[0].to_numpy(),
            "typical": [self.medians[f] for f in FEATURES],
            "effect": p0 - p,          # +ve = this feature raises risk
        })
        contrib = contrib[contrib["effect"].abs() > 0.005]
        up = contrib.sort_values("effect", ascending=False).head(top)
        up = up[up["effect"] > 0]
        down = contrib.sort_values("effect").head(3)
        down = down[down["effect"] < 0]
        return p0, up, down


def train_target(target: str, feats: pd.DataFrame, labels: pd.DataFrame, log=print) -> RiskModel:
    df = _rows_for(target, feats, labels)
    X, y = df[FEATURES].astype(float), df[target].to_numpy()
    fold_of = _folds(df, target)
    fold = df["Pregnancy_ID"].map(fold_of).to_numpy()
    log(f"\n=== {TARGETS[target]['title']} ===")
    log(f"rows={len(df)}  pregnancies={df.Pregnancy_ID.nunique()}  "
        f"positive pregnancies={int(df.groupby('Pregnancy_ID')[target].first().sum())}")

    comparison, oof_all, models_all = {}, {}, {}
    for name, proto in candidate_models().items():
        oof = np.zeros(len(df))
        fitted = []
        for k in range(N_FOLDS):
            tr, te = fold != k, fold == k
            m = clone(proto)
            m.fit(X[tr], y[tr])
            oof[te] = m.predict_proba(X[te])[:, 1]
            fitted.append(m)
        comparison[name] = {"roc_auc": float(roc_auc_score(y, oof)),
                            "pr_auc": float(average_precision_score(y, oof))}
        oof_all[name], models_all[name] = oof, fitted
        log(f"  {name:20s} ROC-AUC={comparison[name]['roc_auc']:.3f}  PR-AUC={comparison[name]['pr_auc']:.3f}")

    best = max(comparison, key=lambda n: (round(comparison[n]["roc_auc"], 3), comparison[n]["pr_auc"]))
    oof = oof_all[best]
    log(f"  -> selected: {best}")

    # Risk bands from out-of-fold predictions:
    #   moderate threshold = 75% specificity (top quarter of non-cases)
    #   high threshold     = 90% specificity (top tenth of non-cases)
    fpr, tpr, thr = roc_curve(y, oof)
    t_mod = float(thr[np.where(fpr <= 0.25)[0][-1]])
    t_high = float(thr[np.where(fpr <= 0.10)[0][-1]])
    t_high = max(t_high, t_mod)

    # Balanced operating point (Youden J = sensitivity + specificity - 1).
    t_bal = float(thr[np.argmax(tpr - fpr)])

    metrics = {"visit_level_at_high": _metrics(y, oof, t_high),
               "visit_level_at_moderate": _metrics(y, oof, t_mod),
               "visit_level_balanced": _metrics(y, oof, t_bal)}

    # Landmark evaluation: one prediction per pregnancy, at the last visit
    # on or before 28 weeks (a realistic clinical decision point).
    # For GDM the landmark is the last visit before 24 weeks.
    lm_ga = min(28.0, (TARGETS[target]["max_ga"] or 99.0) - 0.01)
    lm = df.assign(p=oof)[df["ga_weeks"] <= lm_ga].groupby("Pregnancy_ID").tail(1)
    if lm[target].nunique() == 2:
        metrics["landmark"] = _metrics(lm[target].to_numpy(), lm["p"].to_numpy(), t_bal)
        metrics["landmark"]["ga"] = round(lm_ga)
        metrics["landmark"]["n_pregnancies"] = int(len(lm))
        m = metrics["landmark"]
        log(f"  one prediction per pregnancy (<= {round(lm_ga)} wk, n={len(lm)}): ROC-AUC={m['roc_auc']:.3f} "
            f"accuracy={m['accuracy']:.2f} (baseline {m['baseline_accuracy']:.2f}) "
            f"balanced acc={m['balanced_accuracy']:.2f} sens={m['sensitivity']:.2f} spec={m['specificity']:.2f}")

    # Permutation-style importance on held-out folds (mean drop in ROC-AUC).
    rng = np.random.default_rng(SEED)
    base_auc = roc_auc_score(y, oof)
    imp = {}
    for f in FEATURES:
        p_perm = np.zeros(len(df))
        for k in range(N_FOLDS):
            te = fold == k
            Xp = X[te].copy()
            Xp[f] = rng.permutation(Xp[f].to_numpy())
            p_perm[te] = models_all[best][k].predict_proba(Xp)[:, 1]
        imp[f] = float(base_auc - roc_auc_score(y, p_perm))

    return RiskModel(
        target=target, model_name=best, fold_models=models_all[best], fold_of=fold_of,
        medians={f: float(np.nanmedian(X[f])) if X[f].notna().any() else 0.0 for f in FEATURES},
        thresholds={"moderate": t_mod, "high": t_high},
        metrics=metrics, comparison=comparison,
        importance=dict(sorted(imp.items(), key=lambda kv: -kv[1])),
    )


def save_models(models: dict[str, RiskModel], extra: dict | None = None):
    MODEL_DIR.mkdir(exist_ok=True)
    for t, m in models.items():
        joblib.dump(m, MODEL_DIR / f"{t}_model.joblib", compress=3)
    summary = {t: {"model": m.model_name, "thresholds": m.thresholds, "metrics": m.metrics,
                   "comparison": m.comparison,
                   "top_features": {FEATURE_LABELS[k]: v for k, v in list(m.importance.items())[:12]}}
               for t, m in models.items()}
    summary.update(extra or {})
    (MODEL_DIR / "model_report.json").write_text(json.dumps(summary, indent=2))


def load_models() -> dict[str, RiskModel]:
    """Load saved models. Returns {} if they are missing or were saved with an
    incompatible scikit-learn version (then run: python train_models.py)."""
    out = {}
    for t in TARGETS:
        path = MODEL_DIR / f"{t}_model.joblib"
        if not path.exists():
            continue
        try:
            out[t] = joblib.load(path)
        except Exception:  # version mismatch etc.
            return {}
    return out
