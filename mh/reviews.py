"""
Doctor review of risk classification (human-in-the-loop).

The ML models only PROPOSE a risk band. When something looks off (abnormal
labs today, serious alerts, or the model disagreeing with the visit's risk
level) the visit is flagged "Review required". The doctor confirms or
overrides each band with a reason; every decision is appended to an audit
trail (app_data/risk_reviews.csv) and the confirmed band is what the
patient and dietician see.
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
STORE = ROOT / "app_data" / "risk_reviews.csv"
COLS = ["Timestamp", "Pregnancy_ID", "Visit_ID", "Visit_Date", "Outcome", "Model_Band", "Model_Prob",
        "Final_Band", "Changed", "Reason", "Reviewed_By"]
BANDS = ["Low", "Moderate", "High"]
RANK = {b: i for i, b in enumerate(BANDS)}

OUTCOME_LABELS = {"overall": "Overall pregnancy risk", "preterm": "Preterm birth",
                  "nicu": "NICU admission", "gdm": "Gestational diabetes"}


def load() -> pd.DataFrame:
    if STORE.exists():
        df = pd.read_csv(STORE, keep_default_na=False)
        df["Visit_Date"] = pd.to_datetime(df["Visit_Date"], errors="coerce")
        return df
    return pd.DataFrame(columns=COLS)


def save(pregnancy_id: str, visit_id: str, visit_date, decisions: list[dict], reason: str,
         reviewer: str = "Doctor"):
    """decisions: [{Outcome, Model_Band, Model_Prob, Final_Band}]"""
    STORE.parent.mkdir(exist_ok=True)
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    rows = [{**d, "Timestamp": ts, "Pregnancy_ID": pregnancy_id, "Visit_ID": visit_id,
             "Visit_Date": pd.Timestamp(visit_date).date().isoformat(),
             "Changed": "Yes" if d["Model_Band"] and d["Model_Band"] != d["Final_Band"] else "No",
             "Reason": reason, "Reviewed_By": reviewer} for d in decisions]
    old = load()
    if not old.empty:
        old["Visit_Date"] = old["Visit_Date"].dt.date.astype(str)
    pd.concat([old, pd.DataFrame(rows)], ignore_index=True)[COLS].to_csv(STORE, index=False)


def for_visit(visit_id: str) -> pd.DataFrame:
    r = load()
    return r[r.Visit_ID == visit_id]


def confirmed(pregnancy_id: str, as_of=None) -> dict:
    """Latest doctor-confirmed band per outcome, up to a date. {} if never reviewed."""
    r = load()
    r = r[r.Pregnancy_ID == pregnancy_id]
    if as_of is not None:
        r = r[r.Visit_Date <= pd.Timestamp(as_of)]
    if r.empty:
        return {}
    last = r.sort_values("Timestamp").groupby("Outcome").tail(1).set_index("Outcome")
    return {o: {"band": last.loc[o, "Final_Band"], "date": last.loc[o, "Visit_Date"],
                "reason": last.loc[o, "Reason"], "changed": last.loc[o, "Changed"] == "Yes"}
            for o in last.index}


def review_reasons(rec, model_bands: dict, alerts: list) -> list[str]:
    """Why this visit needs a doctor to look at the risk classification."""
    reasons = []
    abn = rec.labs_today[rec.labs_today.Is_Abnormal]
    if len(abn):
        names = ", ".join(sorted(abn.Test_Name.str.replace("_", " ").unique())[:4])
        reasons.append(f"{len(abn)} abnormal lab result(s) at this visit ({names})")
    serious = [t for s, t, _ in alerts if s in ("critical", "serious")]
    if serious:
        reasons.append("Serious alert(s): " + "; ".join(serious[:3]))
    visit_level = rec.visit.Risk_Level
    for o, b in model_bands.items():
        if b and abs(RANK[b] - RANK.get(visit_level, 0)) >= 2:
            reasons.append(f"Model says {b} risk for {OUTCOME_LABELS[o]} but the visit was graded {visit_level}")
        elif b == "High":
            reasons.append(f"Model flags High risk for {OUTCOME_LABELS[o]}")
    return reasons
