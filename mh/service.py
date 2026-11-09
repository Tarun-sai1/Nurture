"""
Service layer for the web app: turns the data, clinical rules and ML models
into JSON-ready dictionaries.

Speed
- Everything is loaded ONCE at start-up.
- Risk probabilities for all 2,048 visits are computed in one vectorised pass.
- "Why this score" explanations are cached and pre-warmed in a background thread.
- The static part of each visit record is cached; only the parts people change
  (reviews, appointments, notes) are rebuilt per request.
"""
from __future__ import annotations

import json
import threading
from functools import lru_cache

import numpy as np
import pandas as pd

from . import appointments, reviews
from .clinical import (active_medications, alerts, drug_profile, latest_numeric, milestones_table,
                       record_as_of, safety_check, suggestions, test_plan, weight_gain_target)
from .data import load_data
from .features import FEATURE_LABELS, FEATURES, build_visit_features
from .model import MODEL_DIR, TARGETS, load_models
from .text import CONSEQUENCE, PATIENT_RISK_TEXT, TIMING_TEXT

GLUCOSE_TESTS = ["GDM_Screening", "Two_Hour_Glucose", "Fasting_Glucose"]
RISK_ORDER = {"High": 0, "Moderate": 1, "Low": 2}


# ------------------------------------------------------------------ JSON helpers
def _val(v):
    if v is None:
        return None
    if isinstance(v, pd.Timestamp):
        return None if pd.isna(v) else v.strftime("%Y-%m-%d")
    if isinstance(v, (np.integer,)):
        return int(v)
    if isinstance(v, (np.floating, float)):
        return None if np.isnan(v) else round(float(v), 3)
    if isinstance(v, (np.bool_,)):
        return bool(v)
    try:
        if pd.isna(v):
            return None
    except (TypeError, ValueError):
        pass
    return v


def records(df: pd.DataFrame, cols: dict) -> list[dict]:
    """cols: {output_key: source_column}"""
    if df is None or df.empty:
        return []
    sub = df[list(cols.values())]
    keys = list(cols.keys())
    return [{k: _val(v) for k, v in zip(keys, row)} for row in sub.itertuples(index=False, name=None)]


def pretty(s) -> str:
    return str(s).replace("_", " ")


# ------------------------------------------------------------------ service
class Service:
    def __init__(self):
        self.data = load_data()
        self.feats = build_visit_features(self.data).set_index("Visit_ID", drop=False)
        self.models = load_models()
        for m in self.models.values():          # single-row predictions: threads only add overhead
            for fm in m.fold_models:
                try:
                    fm.set_params(randomforestclassifier__n_jobs=1)
                except ValueError:
                    pass
        rep = MODEL_DIR / "model_report.json"
        self.report = json.loads(rep.read_text()) if rep.exists() else {}
        self._predict_all()
        self._expl: dict = {}
        self._expl_lock = threading.Lock()
        self.write_lock = threading.Lock()
        self.visit_index = self.data.visits.set_index("Visit_ID")
        self.drugs = sorted(self.data.med_master.Generic_Name.tolist())

    # ---------------------------------------------------------- predictions
    def _predict_all(self):
        f = self.feats
        X = f[FEATURES].astype(float)
        for t, m in self.models.items():
            fold = f["Pregnancy_ID"].map(m.fold_of).fillna(0).astype(int).to_numpy()
            p = np.zeros(len(f))
            for k, fm in enumerate(m.fold_models):
                idx = fold == k
                if idx.any():
                    p[idx] = fm.predict_proba(X[idx])[:, 1]
            f[f"p_{t}"] = p

    def explain(self, visit_id: str, t: str):
        key = (visit_id, t)
        with self._expl_lock:
            if key in self._expl:
                return self._expl[key]
        prob, up, down = self.models[t].explain_row(self.feats.loc[visit_id])
        out = {"up": records(up, {"label": "label", "value": "value", "typical": "typical", "effect": "effect"}),
               "down": records(down, {"label": "label", "value": "value", "typical": "typical", "effect": "effect"})}
        with self._expl_lock:
            self._expl[key] = out
        return out

    def warm_explanations(self):
        """Background thread: pre-compute every explanation so clicks are instant."""
        order = self.feats.sort_values("Visit_Date", ascending=False)
        latest = order.groupby("Pregnancy_ID").head(1).index.tolist()
        for vid in latest + [v for v in order.index if v not in set(latest)]:
            for t in self.models:
                try:
                    self.explain(vid, t)
                except Exception:
                    pass

    # ---------------------------------------------------------- lists
    def meta(self) -> dict:
        p = self.data.patients.sort_values("Patient_ID")
        v = self.data.visits
        days = v.groupby("Visit_Date").agg(n=("Visit_ID", "size"),
                                           high=("Risk_Level", lambda s: int((s == "High").sum())))
        b = appointments.load()
        booked = b[b.Status == "Booked"].groupby("Date").size() if not b.empty else pd.Series(dtype=int)
        clinic = []
        for d, r in days.iterrows():
            ds = d.strftime("%Y-%m-%d")
            if r.n >= 3 or ds in booked.index:
                clinic.append({"date": ds, "n": int(r.n), "high": int(r.high), "booked": int(booked.get(ds, 0))})
        for ds, n in booked.items():
            if ds not in {c["date"] for c in clinic}:
                clinic.append({"date": ds, "n": 0, "high": 0, "booked": int(n)})
        clinic.sort(key=lambda c: c["date"])
        demo = [c for c in clinic if c["high"] >= 1 and c["n"] >= 3]
        return {
            "patients": records(p, {"patient_id": "Patient_ID", "pregnancy_id": "Pregnancy_ID"}),
            "clinic_days": clinic,
            "default_day": (demo[len(demo) // 2] if demo else clinic[0])["date"],
            "drugs": self.drugs,
        }

    def visits(self, preg: str) -> list[dict]:
        v = self.data.visits[self.data.visits.Pregnancy_ID == preg].sort_values("Visit_Date")
        return records(v, {"visit_id": "Visit_ID", "no": "Visit_No", "date": "Visit_Date",
                           "ga_w": "Gestational_Week", "ga_d": "Gestational_Days", "risk": "Risk_Level"})

    def clinic(self, day: str) -> list[dict]:
        d = pd.Timestamp(day)
        v = self.data.visits
        today = v[v.Visit_Date == d].copy()
        today["r"] = today.Risk_Level.map(RISK_ORDER)
        today = today.sort_values("r")
        abn = set(self.data.labs[self.data.labs.Is_Abnormal & self.data.labs.Visit_ID.isin(today.Visit_ID)].Visit_ID)
        reviewed = set(reviews.load().Visit_ID)
        out = []
        for r in today.itertuples():
            flag = "reviewed" if r.Visit_ID in reviewed else (
                "review" if (r.Visit_ID in abn or r.Risk_Level == "High") else "")
            out.append({"visit_id": r.Visit_ID, "pregnancy_id": r.Pregnancy_ID, "patient_id": r.Patient_ID,
                        "ga_w": int(r.Gestational_Week), "risk": r.Risk_Level, "type": pretty(r.Visit_Type),
                        "flag": flag, "booked_time": None, "abnormal_labs": r.Visit_ID in abn})
        for b in appointments.for_day(d).itertuples():
            pv = v[(v.Pregnancy_ID == b.Pregnancy_ID) & (v.Visit_Date <= d)]
            if pv.empty:
                pv = v[v.Pregnancy_ID == b.Pregnancy_ID].head(1)
            last = pv.iloc[-1]
            out.append({"visit_id": last.Visit_ID, "pregnancy_id": b.Pregnancy_ID, "patient_id": b.Patient_ID,
                        "ga_w": int(last.Gestational_Week), "risk": last.Risk_Level, "type": b.Type,
                        "flag": "", "booked_time": b.Time, "abnormal_labs": False, "reason": b.Reason})
        return out

    def worklist(self) -> list[dict]:
        n = self.data.nutrition.sort_values("Visit_Date").groupby("Pregnancy_ID").tail(1).copy()
        focus_cols = ["Anaemia_Nutrition_Focus", "GDM_Nutrition_Focus", "Hypertension_Nutrition_Focus"]
        n["focus"] = n[focus_cols].apply(
            lambda r: ", ".join(c.split("_")[0] for c in focus_cols if r[c] == "Yes") or "Routine", axis=1)
        notes = _notes()
        referred = set(notes[notes.Kind == "referral"].Pregnancy_ID) if not notes.empty else set()
        n["referred"] = n.Pregnancy_ID.isin(referred)
        n["r"] = n.Nutritional_Risk_Level.map(RISK_ORDER)
        n = n.sort_values(["referred", "r"], ascending=[False, True])
        return records(n, {"pregnancy_id": "Pregnancy_ID", "patient_id": "Patient_ID", "visit_id": "Visit_ID",
                           "risk": "Nutritional_Risk_Level", "focus": "focus", "referred": "referred",
                           "pattern": "Dietary_Pattern", "ga_w": "Gestational_Week"})

    # ---------------------------------------------------------- one visit
    def record(self, preg: str, visit_id: str) -> dict:
        out = dict(self._static_record(preg, visit_id))
        out.update(self._dynamic_record(preg, visit_id, out))
        return out

    @lru_cache(maxsize=4096)
    def _static_record(self, preg: str, visit_id: str) -> dict:
        d = self.data
        rec = record_as_of(d, preg, visit_id)
        p, v = rec.patient, rec.visit
        ga = rec.ga_weeks + rec.ga_days / 7

        risk_cols = {
            "Preexisting_Hypertension": "Pre-existing hypertension", "Preexisting_Diabetes": "Pre-existing diabetes",
            "Thyroid_Disease": "Thyroid disease", "Renal_Disease": "Renal disease", "Cardiac_Disease": "Cardiac disease",
            "Epilepsy": "Epilepsy", "Asthma": "Asthma", "Autoimmune_Disease": "Autoimmune disease",
            "Previous_PreEclampsia": "Previous pre-eclampsia", "Previous_GDM": "Previous GDM",
            "Previous_Preterm_Birth": "Previous preterm birth", "Previous_C_Section": "Previous C-section",
            "Previous_Stillbirth": "Previous stillbirth", "Multiple_Pregnancy": "Twins / multiple pregnancy",
            "Known_Haemoglobinopathy": "Known haemoglobinopathy",
        }
        rf = [lbl for col, lbl in risk_cols.items() if str(p[col]) == "Yes"]
        if p.Age_Years >= 35:
            rf.append("Age 35 or over")
        if p.Pre_Pregnancy_BMI >= 30:
            rf.append(f"BMI {p.Pre_Pregnancy_BMI}")
        if p.Smoking_Status != "Never":
            rf.append(f"Smoking ({p.Smoking_Status.lower()})")

        allergy = p.Drug_Allergies if p.Drug_Allergies not in ("", "None") else None
        patient = {
            "patient_id": p.Patient_ID, "pregnancy_id": preg, "age": int(p.Age_Years), "gravida": int(p.Gravida),
            "para": int(p.Para), "bmi": float(p.Pre_Pregnancy_BMI), "blood_group": f"{p.ABO_Group} {p.RhD_Status}",
            "drug_allergy": allergy, "allergy_reaction": p.Drug_Allergy_Reaction if allergy else None,
            "food_allergy": p.Food_Allergies if p.Food_Allergies not in ("", "None") else None,
            "diet_pattern": p.Dietary_Pattern, "edd": _val(p.EDD_Date), "lmp": _val(p.LMP_Date),
            "risk_factors": rf,
        }
        visit = {
            "visit_id": v.Visit_ID, "no": int(v.Visit_No), "date": _val(v.Visit_Date), "ga_w": rec.ga_weeks,
            "ga_d": rec.ga_days, "ga": round(ga, 2), "trimester": v.Trimester, "sbp": int(v.SBP_mmHg),
            "dbp": int(v.DBP_mmHg), "spo2": float(v.SpO2_percent), "weight": float(v.Weight_kg),
            "fhr": _val(v.Fetal_Heart_Rate_bpm), "risk": v.Risk_Level, "assessment": pretty(v.Clinical_Assessment),
            "symptoms": pretty(v.Symptoms), "severity": v.Symptom_Severity, "oedema": v.Oedema,
            "presentation": pretty(v.Fetal_Presentation), "fetal_movement": pretty(v.Fetal_Movement_Status),
            "next_visit": _val(v.Next_Visit_Date), "follow_up_days": _val(v.Follow_Up_Interval_Days),
            "days_to_edd": int((p.EDD_Date - v.Visit_Date).days),
        }
        visits = records(rec.visits, {"visit_id": "Visit_ID", "date": "Visit_Date", "ga": "GA_Weeks",
                                      "ga_w": "Gestational_Week", "sbp": "SBP_mmHg", "dbp": "DBP_mmHg",
                                      "weight": "Weight_kg", "spo2": "SpO2_percent", "risk": "Risk_Level",
                                      "assessment": "Clinical_Assessment", "referral": "Referral_Reason",
                                      "type": "Visit_Type", "outcome": "Visit_Outcome"})
        for x in visits:
            for k in ("assessment", "referral", "type", "outcome"):
                x[k] = pretty(x[k])

        labs = rec.labs.sort_values(["Investigation_Date", "Test_Category"])
        lab_list = records(labs, {"visit_id": "Visit_ID", "date": "Investigation_Date", "ga_w": "Gestational_Week",
                                  "test": "Test_Name", "category": "Test_Category", "result": "Result",
                                  "num": "Result_Num", "unit": "Unit", "ref": "Reference_Range",
                                  "flag": "Abnormal_Flag", "abnormal": "Is_Abnormal", "reason": "Performed_Reason"})
        for x in lab_list:
            x["test_label"] = pretty(x["test"])

        act = active_medications(rec)
        meds_active = []
        for m in act.itertuples():
            prof = drug_profile(d, m.Generic_Name)
            meds_active.append({
                "name": m.Generic_Name, "indication": m.Indication, "regimen": m.Reference_Regimen_or_Dose_Band,
                "route": m.Route, "started": _val(m.Started_On), "ga_w": int(m.Gestational_Week),
                "monitoring": m.Response_Status, "allergy_check": m.Allergy_Check,
                "interactions": prof.get("Important_Interactions", ""),
                "common_ae": prof.get("Common_Adverse_Effects", ""), "serious_ae": prof.get("Serious_Adverse_Effects", ""),
            })
        current = [m["name"] for m in meds_active]
        sug = []
        for drug, why in suggestions(d, rec):
            issues = safety_check(d, rec, current + [drug])
            issues = issues[issues.Medicine.str.contains(drug, regex=False)]
            sug.append({"drug": drug, "why": why, "issues": _findings(issues)})

        hb, hb_date = latest_numeric(rec.labs, "Haemoglobin")
        lo, hi, cat = weight_gain_target(float(p.Pre_Pregnancy_BMI))

        return {
            "patient": patient, "visit": visit, "visits": visits, "labs": lab_list,
            "latest_hb": None if hb is None else {"value": hb, "date": _val(hb_date)},
            "meds_active": meds_active,
            "meds_history": records(rec.meds.sort_values("Event_Date"),
                                    {"date": "Event_Date", "ga_w": "Gestational_Week", "name": "Generic_Name",
                                     "action": "Action", "indication": "Indication"}),
            "meds_today": records(rec.meds_today, {"name": "Generic_Name", "action": "Action",
                                                   "trigger": "Trigger_Type", "trigger_test": "Trigger_Test",
                                                   "trigger_value": "Trigger_Value", "indication": "Indication"}),
            "alerts": [{"sev": s, "title": t, "body": b} for s, t, b in alerts(rec)],
            "suggestions": sug,
            "regimen_safety": _findings(safety_check(d, rec, current)),
            "test_plan": records(test_plan(rec), {"test": "Test", "window": "Window", "reason": "Reason",
                                                  "status": "Status"}),
            "milestones": records(milestones_table(ga), {"window": "Window", "text": "Milestone", "status": "Status"}),
            "weight": {"lo": lo, "hi": hi, "category": cat,
                       "gain": round(float(rec.visits.Weight_kg.iloc[-1] - rec.visits.Weight_kg.iloc[0]), 1)},
            "nutrition": self._nutrition(rec),
            "risk": self._risk(rec),
        }

    def _nutrition(self, rec) -> dict:
        d = self.data
        nut = rec.nutrition.sort_values("Visit_Date")
        focus_cols = [c for c in nut.columns if c.endswith("_Focus")]
        assess = []
        for a in nut.itertuples():
            row = a._asdict()
            flags = [x.strip() for x in str(a.Medication_Food_Timing_Flags).split(";") if x.strip()]
            assess.append({
                "visit_id": a.Visit_ID, "date": _val(a.Visit_Date), "ga_w": int(a.Gestational_Week),
                "weight": float(a.Weight_kg), "bmi": float(a.BMI), "risk": a.Nutritional_Risk_Level,
                "appetite": a.Appetite, "nausea": a.Nausea, "pattern": a.Dietary_Pattern,
                "restrictions": a.Dietary_Restrictions, "food_allergy": a.Food_Allergy_Profile,
                "referral": a.Dietitian_Referral,
                "focus": [c.replace("_Nutrition_Focus", "").replace("_Focus", "").replace("_", " ")
                          for c in focus_cols if row[c] == "Yes"],
                "tips": [{"flag": pretty(f), "text": TIMING_TEXT[f]} for f in flags if f in TIMING_TEXT],
            })
        recs = d.food_recs[(d.food_recs.Pregnancy_ID == rec.patient.Pregnancy_ID)
                           & (d.food_recs.Visit_Date <= rec.visit.Visit_Date)]
        foods, rec_date, rules = [], None, []
        if not recs.empty:
            rec_date = recs.Visit_Date.max()
            r = recs[recs.Visit_Date == rec_date]
            fm = d.food_master.set_index("Food_ID")
            r = r.merge(fm[["Reference_Serving_g", "Energy_kcal", "Protein_g", "Iron_mg", "Calcium_mg",
                            "GI_Category", "Major_Allergens"]], left_on="Food_ID", right_index=True, how="left")
            r = r.sort_values("Priority_Score", ascending=False).drop_duplicates(["Clinical_Context", "Food_Name"])
            foods = records(r, {"context": "Clinical_Context", "food": "Food_Name", "serving": "Reference_Serving_g",
                                "kcal": "Energy_kcal", "protein": "Protein_g", "iron": "Iron_mg",
                                "calcium": "Calcium_mg", "gi": "GI_Category", "allergens": "Major_Allergens",
                                "why": "Rationale"})
            for f in foods:
                f["food"] = f["food"].replace(", raw", "")
            ctx_map = {"Anaemia": "Anaemia", "GDM": "GDM / elevated glucose", "Hypertension": "Hypertension",
                       "Nausea": "Nausea/vomiting", "Calcium": "Low calcium intake"}
            active = [ctx_map[c] for c in r.Clinical_Context.unique() if c in ctx_map]
            if str(rec.patient.Dietary_Pattern).startswith("Vegan"):
                active.append("Vegan pregnancy")
            rl = d.nutrition_rules[d.nutrition_rules.Clinical_Context.isin(active + ["Routine pregnancy"])]
            rules = records(rl, {"context": "Clinical_Context", "principle": "Recommendation_Principle",
                                 "emphasize": "Foods_To_Emphasize", "limit": "Foods_To_Limit",
                                 "source": "Evidence_Source"})
        glu = rec.labs[rec.labs.Test_Name.isin(GLUCOSE_TESTS)]
        return {"assessments": assess, "foods": foods, "foods_date": _val(rec_date), "rules": rules,
                "glucose": "Abnormal" if glu.Is_Abnormal.any() else ("Normal" if len(glu) else "Not done")}

    def _risk(self, rec) -> dict:
        if not self.models:
            return {"available": False}
        f = self.feats
        rows = f[(f.Pregnancy_ID == rec.patient.Pregnancy_ID) & (f.Visit_Date <= rec.visit.Visit_Date)]
        row = rows.iloc[-1]
        results = {}
        for t, m in self.models.items():
            base = {"title": TARGETS[t]["title"], "model": m.model_name,
                    "thresholds": m.thresholds,
                    "base_rate": m.metrics["visit_level_at_high"]["prevalence"]}
            use, note = row, ""
            if t == "preterm" and row.ga_weeks >= 37:
                results[t] = {**base, "prob": None, "band": None,
                              "note": "Pregnancy has reached 37 weeks, so it is no longer at risk of preterm birth."}
                continue
            if t == "gdm":
                glu = rec.labs[rec.labs.Test_Name.isin(GLUCOSE_TESTS)]
                if len(glu):
                    abn = bool(glu.Is_Abnormal.any())
                    dt = glu.Investigation_Date.min()
                    results[t] = {**base, "prob": None, "band": "High" if abn else "Low", "measured": True,
                                  "note": f"Glucose test done on {dt:%d %b %Y}: "
                                          + ("abnormal — GDM diagnosed." if abn else "normal — no GDM.")}
                    continue
                pre = rows[rows.ga_weeks < 24]
                if pre.empty:
                    continue
                use = pre.iloc[-1]
                if row.ga_weeks >= 24:
                    note = "Prediction from the last visit before 24 weeks. The glucose test is due now."
            prob = float(use[f"p_{t}"])
            band = m.band(prob)
            results[t] = {**base, "prob": prob, "band": band, "note": note, "visit_used": use.Visit_ID,
                          "action": CONSEQUENCE[t][band]}
        traj = [{"ga": round(float(r.ga_weeks), 2), "preterm": _val(r.p_preterm) if "p_preterm" in r else None,
                 "nicu": _val(r.p_nicu) if "p_nicu" in r else None,
                 "gdm": _val(r.p_gdm) if ("p_gdm" in r and r.ga_weeks < 24) else None} for _, r in rows.iterrows()]
        return {"available": True, "results": results, "trajectory": traj}

    def _dynamic_record(self, preg: str, visit_id: str, static: dict) -> dict:
        v = static["visit"]
        res = static["risk"].get("results", {})
        model_bands = {t: r["band"] for t, r in res.items() if r.get("band") and not r.get("measured")}
        rec = record_as_of(self.data, preg, visit_id)
        reasons = reviews.review_reasons(rec, model_bands, [(a["sev"], a["title"], a["body"])
                                                             for a in static["alerts"]])
        conf = reviews.confirmed(preg, v["date"])
        done = reviews.for_visit(visit_id)
        hist = reviews.load()
        hist = hist[hist.Pregnancy_ID == preg].sort_values("Timestamp", ascending=False)
        notes = _notes()
        notes = notes[notes.Pregnancy_ID == preg] if not notes.empty else notes
        appts = appointments.for_patient(preg)
        risk_overall = conf.get("overall", {}).get("band") or v["risk"]
        today = pd.Timestamp(v["date"]).date()
        nv = pd.Timestamp(v["next_visit"]).date() if v["next_visit"] else None
        lo, ideal, hi = appointments.recommended_window(today, v["ga"], risk_overall, nv)
        for t in res:
            if t in conf and res[t].get("prob") is not None:
                res[t]["action"] = CONSEQUENCE[t][conf[t]["band"]]
        return {
            "review": {
                "reasons": reasons, "done_this_visit": not done.empty,
                "done_at": done.Timestamp.iloc[-1] if not done.empty else None,
                "confirmed": {k: {"band": c["band"], "date": _val(c["date"]), "reason": c["reason"],
                                  "changed": bool(c["changed"])} for k, c in conf.items()},
                "history": records(hist, {"timestamp": "Timestamp", "visit_date": "Visit_Date", "outcome": "Outcome",
                                          "model_band": "Model_Band", "model_prob": "Model_Prob",
                                          "final_band": "Final_Band", "changed": "Changed", "reason": "Reason"}),
                "patient_text": PATIENT_RISK_TEXT.get(conf.get("overall", {}).get("band", ""), None),
            },
            "notes": records(notes.iloc[::-1] if len(notes) else notes,
                             {"timestamp": "Timestamp", "role": "Role", "visit_id": "Visit_ID", "kind": "Kind",
                              "text": "Text"}),
            "appointments": {
                "list": records(appts.iloc[::-1] if len(appts) else appts,
                                {"id": "Booking_ID", "date": "Date", "time": "Time", "type": "Type",
                                 "reason": "Reason", "status": "Status"}),
                "today": today.isoformat(), "risk_used": risk_overall,
                "interval_days": appointments.recommended_interval_days(v["ga"], risk_overall),
                "window": [lo.isoformat(), ideal.isoformat(), hi.isoformat()],
                "types": appointments.VISIT_TYPES, "danger_signs": appointments.DANGER_SIGNS,
            },
        }

    # ---------------------------------------------------------- actions
    def drug_check(self, preg: str, visit_id: str, drug: str) -> dict:
        rec = record_as_of(self.data, preg, visit_id)
        current = active_medications(rec).Generic_Name.tolist() if True else []
        res = safety_check(self.data, rec, current + [drug])
        res = res[res.Medicine.str.contains(drug, regex=False)]
        prof = drug_profile(self.data, drug)
        keep = ["Pregnancy_Specific_Risks", "Trimester_Notes", "Contraindications", "Common_Adverse_Effects",
                "Serious_Adverse_Effects", "Monitoring", "Reference_Regimen_or_Dose_Band", "Evidence_Grade",
                "Evidence_Sources"]
        return {"drug": drug, "findings": _findings(res), "profile": {k: prof.get(k, "") for k in keep}}

    def slots(self, day: str) -> dict:
        d = pd.Timestamp(day).date()
        return {"day": d.isoformat(), "closed": d.weekday() == 6,
                "free": appointments.free_slots(d, self.data.visits), "all": appointments.all_slots()}

    def book(self, preg, day, slot, vtype, reason) -> dict:
        pid = self.data.patients.set_index("Pregnancy_ID").loc[preg, "Patient_ID"]
        with self.write_lock:
            ok, msg = appointments.book(preg, pid, pd.Timestamp(day).date(), slot, vtype, reason, self.data.visits)
        return {"ok": ok, "message": msg}

    def cancel(self, booking_id) -> dict:
        with self.write_lock:
            appointments.cancel(booking_id)
        return {"ok": True}

    def save_review(self, preg, visit_id, decisions, reason) -> dict:
        changed = [x for x in decisions if x["Outcome"] != "overall" and x["Model_Band"]
                   and x["Model_Band"] != x["Final_Band"]]
        if changed and not reason.strip():
            names = ", ".join(reviews.OUTCOME_LABELS[x["Outcome"]] for x in changed)
            return {"ok": False, "message": f"Add your clinical reasoning — you changed: {names}."}
        v = self.visit_index.loc[visit_id]
        with self.write_lock:
            reviews.save(preg, visit_id, v.Visit_Date, decisions, reason.strip() or "Agreed with model")
        return {"ok": True}

    def add_note(self, role, preg, visit_id, kind, text) -> dict:
        from datetime import datetime
        with self.write_lock:
            n = _notes()
            row = {"Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"), "Role": role, "Pregnancy_ID": preg,
                   "Visit_ID": visit_id, "Kind": kind, "Text": text}
            NOTES.parent.mkdir(exist_ok=True)
            pd.concat([n, pd.DataFrame([row])], ignore_index=True).to_csv(NOTES, index=False)
        return {"ok": True}

    def model_report(self) -> dict:
        out = []
        for t, m in self.models.items():
            lm = m.metrics.get("landmark") or m.metrics["visit_level_balanced"]
            out.append({
                "target": t, "title": TARGETS[t]["title"], "model": m.model_name,
                "roc_auc": m.comparison[m.model_name]["roc_auc"],
                "ceiling": self.report.get(f"{t}_oracle_roc_auc"),
                "comparison": [{"model": k, "roc_auc": v["roc_auc"], "pr_auc": v["pr_auc"]}
                               for k, v in m.comparison.items()],
                "landmark": {k: lm.get(k) for k in ["accuracy", "baseline_accuracy", "balanced_accuracy",
                                                    "sensitivity", "specificity", "f1", "ppv", "npv", "tp", "fp",
                                                    "tn", "fn", "n_pregnancies", "ga"]},
                "importance": [{"label": FEATURE_LABELS[k], "value": v} for k, v in list(m.importance.items())[:10]],
            })
        return {"models": out}


def _findings(df: pd.DataFrame) -> list[dict]:
    return records(df, {"medicine": "Medicine", "check": "Check", "severity": "Severity", "finding": "Finding"})


from .data import ROOT as _ROOT  # noqa: E402

NOTES = _ROOT / "app_data" / "notes.csv"


def _notes() -> pd.DataFrame:
    if NOTES.exists():
        return pd.read_csv(NOTES, keep_default_na=False, dtype=str)
    return pd.DataFrame(columns=["Timestamp", "Role", "Pregnancy_ID", "Visit_ID", "Kind", "Text"])
