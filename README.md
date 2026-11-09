# Nurture — Maternal Health Intelligence & Decision Support System

ML risk prediction + a web app with three role-based views (Patient, Doctor, Dietician), built
on the six linked synthetic maternal-health datasets (D1–D6, 200 pregnancies).

## Run it

```bash
python -m pip install -r requirements.txt
python train_models.py        # ~1 min; only needed if the Risk tab says models are missing
python server.py              # opens http://localhost:8000 in your browser
```

Keep the terminal open while using the app; press Ctrl+C to stop. Start-up takes about 10 seconds.
Interactive API documentation is at http://localhost:8000/api/docs.

Choose *For patients*, *For doctors* or *For dieticians* in the top bar. Demo views need no login.

| View | How to pick a patient | Good demo cases |
|---|---|---|
| Patient | "Viewing as" patient ID + "on" date (time travel through the pregnancy) | P0029 (anaemia, thyroid, GDM) |
| Doctor | Clinic day list (review-needed first) or "Or find any patient" | P0119 (anaemia + reduced fetal movement), P0144 (NSAID allergy on aspirin), P0100 (iron allergy on iron) |
| Dietician | Worklist filtered by nutrition risk, doctor referrals first | top of the list |

## Deploy it online (free) — Render

Hugging Face moved Docker Spaces to paid plans in 2026, so the free route is **Render**, which runs
Python directly from a GitHub repository.

1. Put this folder in a GitHub repository (github.com → **New repository** → *uploading an existing file*
   → drag in everything inside this folder → **Commit changes**).
2. On render.com sign in with GitHub → **New → Web Service** → choose the repository.
3. Settings: Runtime **Python 3**, Build command `pip install -r requirements.txt && python train_models.py`,
   Start command `python server.py`, Instance type **Free**. Under *Environment* add
   `PYTHON_VERSION = 3.12.7` and `NURTURE_WARM = 0`. Click **Deploy Web Service**.
   (Or use **New → Blueprint**, which reads `render.yaml` and fills all of this in.)
4. After the build (about 5 minutes) the app is live at `https://<name>.onrender.com`.

Free-tier notes: 512 MB RAM (the app uses ~300 MB) and a slow shared CPU; the service sleeps after
15 minutes without visitors and takes about a minute to wake, so open it before a demo. Bookings,
reviews and notes are stored in files that reset on every restart — fine for a demo; a real
deployment would use a database. There is no login, so share only synthetic data like this.

## Architecture and speed

```
browser (static/index.html + app.css + app.js, no framework)
   │  JSON over HTTP, gzip
   ▼
server.py  (FastAPI)  ──►  mh/service.py  ──►  mh/clinical.py, mh/model.py, mh/reviews.py, mh/appointments.py
                                              └─►  datasets/ (D1–D6)  +  models/*.joblib
```

* Data, features and models load **once** at start-up; risk probabilities for all 2,048 visits are
  computed in one vectorised pass, and "why this score" explanations are pre-computed in a background thread.
* Each screen needs **one** API call (~10–130 ms, 1–6 KB gzipped); responses are cached in the browser, and
  the other patients in the clinic list are pre-loaded, so switching patients takes ~70–100 ms.
* The front end is plain HTML/CSS/JS (~20 KB) with hand-drawn SVG charts and bundled fonts, so it
  also works without internet. Page state lives in the URL, so refresh and back/forward keep your place.

## What each dashboard does

**Patient** – reports by date or by test (with trend charts), current medicines with
purpose/how to take/side effects, diet plan per visit with food–medicine timing tips and
the dietician's approved note, pregnancy journey (milestones, weight gain vs IOM range, visit history),
the doctor-confirmed risk in plain language, and **appointment booking**:
* recommended next-visit window from gestational age + doctor-confirmed risk
  (< 28 wk every 4 weeks, 28–36 every 2, ≥ 36 weekly; high risk halves it; moderate caps at 3 weeks)
* Mon–Sat 09:00–13:00, 20-minute slots; no double-booking of a slot, one booking per patient per day
* danger-sign checklist → "go to hospital now / call 108 or 102" and a same-day urgent slot
* cancel; bookings appear in the doctor's clinic list (📅)

**Doctor** – everything needed when the patient walks in:
* alert strip (BP, proteinuria, anaemia, glucose, SpO2, fetal movement, presentation)
* overview: vitals vs last visit, BP and Hb trends, baseline risk factors, visit history
* medications: current list, changes made at this visit, **rule-based suggested changes**
  each with an automatic safety check, and a **"what would this medicine do to this patient"** checker
  (allergy, drug interactions, pregnancy-avoid flag, renal caution, pregnancy-specific risks, side effects)
* tests: done at this visit, **due next / overdue** by gestational age, abnormal results history
* **risk & review**: ML risk for preterm birth, NICU admission and **GDM** (predicted before the
  24–28 wk glucose test; after the test the measured result is shown), each with "why this score"
  and what to do. Visits are flagged **⚑ Risk review required** when there are abnormal labs at the
  visit, serious alerts, or the model disagrees with the visit grade. The doctor confirms or overrides
  each band (reason required for any change); decisions go to an audit trail
  (`app_data/risk_reviews.csv`) and the confirmed band drives the patient message, the dietician
  view and the appointment interval. The model proposes, the doctor decides.
* nutrition summary + "refer to dietician", clinical notes, model performance

**Dietician** – worklist, clinical drivers (Hb, glucose, BP, weight gain vs target),
medicines with food-timing implications, editable food plan with nutrient values, guidance
rules applied, approve-and-share to patient.

Notes, approved plans, reviews and bookings are stored in `app_data/` (created on first use);
delete that folder to reset the demo.

## ML design (what to say in the viva)

* **Unit of prediction = one ANC visit.** Features use only data available *up to that visit*
  (`mh/features.py`) – no future visits, no delivery data. 48 features: baseline history,
  current vitals, cumulative BP/visit history, labs so far, medications so far.
* **Grouped cross-validation by pregnancy** (5-fold StratifiedGroupKFold) – the same woman
  never appears in both train and test.
* Preterm model is trained only on visits **before 37 weeks** (after that the label is trivial).
* 3 models compared (Logistic Regression, Random Forest, Gradient Boosting); best by ROC-AUC.
* The dashboard shows **out-of-fold** predictions: each patient is scored by the fold model that
  never saw her.
* Explanations: occlusion – each feature is reset to the cohort median and the change in risk is shown.
* Risk bands: Moderate = 75 % specificity, High = 90 % specificity (from out-of-fold predictions).

| Outcome | Model | ROC-AUC | Best possible | Accuracy | Always-"No" accuracy | Balanced acc. | Sens. | Spec. |
|---|---|---|---|---|---|---|---|---|
| Preterm birth (35/200) | Random Forest | 0.682 | 0.696 | 0.63 | 0.82 | 0.65 | 0.69 | 0.62 |
| NICU admission (14/200) | Random Forest | 0.706 | – | 0.71 | 0.93 | 0.71 | 0.71 | 0.72 |
| GDM, before 24 wk (55/200) | Logistic Regression | 0.765 | 0.801 | 0.81 | 0.72 | 0.74 | 0.60 | 0.88 |

Accuracy-type metrics: one prediction per pregnancy (last visit ≤ 28 wk; ≤ 24 wk for GDM) at the
balanced (Youden) threshold. **Why accuracy looks "low":** outcomes are rare, so a useless model that
always says "No" already gets 82 % (preterm) or 93 % (NICU). Judge the models by ROC-AUC, balanced
accuracy and sensitivity/specificity instead.

**Ceiling check ("Best possible"):** scoring every pregnancy with the data generator's own *true*
probabilities gives ROC-AUC 0.696 for preterm and 0.801 for GDM. Our models reach 0.682 and 0.765 –
close to the limit of what this synthetic data contains. A much higher score would indicate leakage.

Safety checks, test schedules, alerts and suggestions are **rule-based on purpose** – an allergy
conflict must be caught every time and be traceable to a source table (D4 crosswalks).

## Data bugs fixed (generators re-run with the same seed)

| # | Where | Bug | Fix |
|---|---|---|---|
| 1 | D2 → D6 | D2 decided each delivery week but never saved it; D6 guessed delivery from the **last ANC visit**, so a 38-week birth whose last check-up was at 36 weeks became "preterm" (31 % preterm, nothing after 39 weeks) | D2 now writes `pregnancy_delivery_plan.csv`; D6 uses it → 17.5 % preterm, 32–40 weeks. D2 visit table is byte-identical. |
| 2 | D6 | `Gestational_Diabetes_Outcome = Yes` for all 200 – GDM was set when a GDM test merely *existed* | GDM requires an abnormal/high result → 55/200 |
| 3 | D6 | `Final_Gestational_Days` always 0 | days 0–6 from a separate RNG |
| 4 | D5 | "Omnivorous" in D1 didn't match keyword "omnivore", so diet pattern was re-randomised every visit (omnivores labelled Vegan/Jain) | keyword `omnivor` → one pattern per pregnancy |
| 5 | preprocessing | `Live_Birth`, `Delivery_Mode`, `Delivery_Indication` parsed as dates (`Live_Birth_year = 1970`) | only real date columns parsed |
| 6 | preprocessing | lab `Result` label-encoded → Hb values destroyed | `Result_Numeric` + per-test z-score |
| 7 | preprocessing | "None" read as missing | `keep_default_na=False` |

Also found but not changed (analysis scripts, not used by the app):
`maternal_health_correlation_analysis.py` looks for `anc_visits_processed.csv` (real file:
`anc_clinical_vitals_processed.csv`), so D2 was silently skipped; the test-case sweep looks for
column `Investigation_Name` (real: `Test_Name`), so every lab count in the test-case report is 0.
The safety checker also shows that D4 marked "PASSED" for PRG0100 (iron allergy, on iron) and
PRG0144 (NSAID allergy, on aspirin).

## Project layout

```
server.py              web server (FastAPI) – run this
static/                index.html, app.css, app.js, fonts/ (the whole front end)
train_models.py        trains and saves the three models
mh/data.py             loads and type-cleans D1–D6
mh/features.py         leakage-free visit-level features
mh/model.py            training, CV, risk bands, explanations
mh/service.py          builds the JSON for each screen; caching and pre-computation
mh/clinical.py         gestational tracking, safety checks, test plan, alerts, suggestions
mh/reviews.py          doctor risk review / override + audit trail
mh/appointments.py     booking rules, slots, recommended visit interval
mh/text.py             plain-language patient and clinical text
datasets/              regenerated D1–D6
preprocessed_datasets/ re-run preprocessing output
dataset_generation/    the patched generator and preprocessing scripts
models/                trained models + model_report.json + training_log.txt
```

Synthetic research data. Decision support only – not medical advice.
