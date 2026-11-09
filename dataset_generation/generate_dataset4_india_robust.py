
"""
DATASET 4 - INDIA MATERNAL MEDICATION INTELLIGENCE ENGINE
==========================================================

Purpose
-------
Builds a research-grade medication knowledge base + longitudinal
medication/treatment event dataset for a synthetic maternal-health
decision-support project.

This generator DOES NOT prescribe medicines. It encodes:
1. An India-relevant maternal medication master catalogue.
2. Safety metadata: compounds, classes, formulations, contraindications,
   allergy/cross-reactivity, adverse effects, serious ADRs, interactions,
   monitoring and pregnancy/lactation notes.
3. A relational medication-event table linked to Dataset 1, 2 and 3.
4. Evidence/source provenance and confidence fields.
5. Validation reports.

Input:
  Dataset 1: patient_pregnancy.csv
  Dataset 2: anc_clinical_vitals.csv
  Dataset 3: laboratory_investigations.csv

Output:
  datasets/dataset4_medication_treatment/
      medication_master_india.csv
      medication_events.csv
      medication_treatment_india.xlsx
      dataset4_summary.txt
      dataset4_validation_report.txt

IMPORTANT
---------
Synthetic research data only. This is NOT a clinical prescribing system.
Exact treatment, dose, timing, contraindications and alternatives must
be determined by an appropriately qualified clinician using current
Indian institutional/national guidance and the product information.

Evidence architecture
---------------------
Priority:
  A = Indian Government / NHM / MoHFW / CDSCO / NLEM
  B = WHO / international authoritative guidance
  C = established pharmacology / reference knowledge used only to fill
      metadata fields not specified by an Indian guideline.

The master catalogue intentionally separates:
  - "Clinical role" from "event trigger"
  - "Reference regimen" from "patient dose"
  - "Known adverse effects" from "observed adverse effect"
  - "Allergy class" from "patient allergy"

"""

import os
import re
from datetime import datetime
import numpy as np
import pandas as pd
from openpyxl.utils import get_column_letter


# ================================================================
# PATHS
# ================================================================

PROJECT = os.environ.get("MH_PROJECT", r"D:\Maternal_Health_Project")

D1 = os.path.join(
    PROJECT, "datasets", "dataset1_patient_pregnancy",
    "patient_pregnancy.csv"
)
D2 = os.path.join(
    PROJECT, "datasets", "dataset2_anc_clinical_vitals",
    "anc_clinical_vitals.csv"
)
D3 = os.path.join(
    PROJECT, "datasets", "dataset3_laboratory_investigations",
    "laboratory_investigations.csv"
)

OUT = os.path.join(
    PROJECT, "datasets", "dataset4_medication_treatment"
)

os.makedirs(OUT, exist_ok=True)

SEED = 20261008
rng = np.random.default_rng(SEED)


# ================================================================
# HELPERS
# ================================================================

def norm(x):
    return re.sub(r"[^a-z0-9]+", "", str(x).lower())


def find_col(df, candidates, required=False):
    lookup = {norm(c): c for c in df.columns}

    for candidate in candidates:
        key = norm(candidate)
        if key in lookup:
            return lookup[key]

    if required:
        raise KeyError(
            f"Required column not found. Tried {candidates}. "
            f"Available columns: {list(df.columns)}"
        )

    return None


def txt(x):
    if pd.isna(x):
        return ""
    return str(x).strip()


def num(x):
    try:
        return float(str(x).replace(",", "").strip())
    except Exception:
        return np.nan


def truthy(x):
    if isinstance(x, bool):
        return x
    return str(x).strip().lower() in {
        "true", "1", "yes", "y", "positive"
    }


def split_terms(x):
    return [
        t.strip().lower()
        for t in re.split(r"[;,|/]+", txt(x))
        if t.strip()
    ]


# ================================================================
# MEDICATION MASTER
# ================================================================
#
# The catalogue is intentionally India-centric. It focuses on medicines
# that may be relevant to pregnancy/ANC, maternal medical comorbidity,
# obstetric emergencies, infection, supplementation and peripartum care.
#
# It is not a general pharmacy database.
# ================================================================

def medication_catalogue():

    rows = []

    def add(
        med_id,
        generic_name,
        active_ingredients,
        salt_or_compound,
        drug_class,
        therapeutic_area,
        common_indications,
        pregnancy_role,
        trimester_notes,
        routes,
        formulations_india,
        reference_regimen,
        contraindications,
        major_cautions,
        allergy_class,
        cross_reactivity,
        common_adverse_effects,
        serious_adverse_effects,
        pregnancy_specific_risks,
        monitoring,
        important_interactions,
        renal_notes,
        hepatic_notes,
        lactation_notes,
        india_relevance,
        nlem_status,
        evidence_grade,
        evidence_sources="",
        source_notes="",
        not_for_routine_use="No",
    ):

        rows.append({
            "Medication_ID": med_id,
            "Generic_Name": generic_name,
            "Active_Ingredients": active_ingredients,
            "Salt_or_Compound": salt_or_compound,
            "Drug_Class": drug_class,
            "Therapeutic_Area": therapeutic_area,
            "Common_Indications": common_indications,
            "Pregnancy_Role": pregnancy_role,
            "Trimester_Notes": trimester_notes,
            "Routes": routes,
            "Common_Indian_Formulations": formulations_india,
            "Reference_Regimen_or_Dose_Band": reference_regimen,
            "Contraindications": contraindications,
            "Major_Cautions": major_cautions,
            "Allergy_Class": allergy_class,
            "Cross_Reactivity": cross_reactivity,
            "Common_Adverse_Effects": common_adverse_effects,
            "Serious_Adverse_Effects": serious_adverse_effects,
            "Pregnancy_Specific_Risks": pregnancy_specific_risks,
            "Monitoring": monitoring,
            "Important_Interactions": important_interactions,
            "Renal_Considerations": renal_notes,
            "Hepatic_Considerations": hepatic_notes,
            "Lactation_Notes": lactation_notes,
            "India_Relevance": india_relevance,
            "NLEM_2022_Status": nlem_status,
            "Evidence_Grade": evidence_grade,
            "Evidence_Sources": evidence_sources,
            "Source_Notes": source_notes,
            "Not_for_Routine_Pregnancy_Use": not_for_routine_use,
        })

    # ------------------------------------------------------------
    # 1. IRON / FOLATE / CALCIUM / MICRONUTRIENTS
    # ------------------------------------------------------------

    add(
        "MAT-001",
        "Iron + folic acid",
        "Elemental iron + folic acid",
        "Ferrous salt + folic acid",
        "Haematinic / vitamin",
        "Anaemia prevention",
        "Routine antenatal supplementation",
        "Routine preventive therapy",
        "India AMB: daily IFA from 4th month; local programme protocol applies",
        "Oral",
        "Tablet; oral liquid",
        "India AMB: tablet containing 60 mg elemental iron + 500 micrograms folic acid daily; minimum 180 days during pregnancy",
        "Known hypersensitivity to product components",
        "Iron overload states; significant GI intolerance; evaluate cause of anaemia",
        "Iron / formulation-specific hypersensitivity",
        "Formulation-specific; no assumed penicillin-type cross-reactivity",
        "Nausea, constipation, abdominal discomfort, dark stools",
        "Severe hypersensitivity; iron toxicity in overdose",
        "Overdose is dangerous; unnecessary iron in non-anaemic iron-replete patients should be avoided",
        "Hb; adherence; tolerance; response to treatment",
        "Calcium, antacids and some antibiotics can reduce absorption; separate as appropriate",
        "Dose/formulation may need adjustment in severe renal disease",
        "No major routine hepatic adjustment; investigate unexplained anaemia",
        "Generally compatible; monitor infant if clinically indicated",
        "Core Indian ANC programme medicine",
        "NLEM 2022: ferrous salts and folic acid listed",
        "A",
        "NHM Anaemia Mukt Bharat 2026; NLEM 2022",
        "Indian national programme source gives 60 mg elemental iron + 500 mcg folic acid tablet and timing",
        "No",
    )

    add(
        "MAT-002",
        "Folic acid",
        "Folic acid",
        "Pteroylmonoglutamic acid",
        "Vitamin B9",
        "Neural tube defect prevention / folate deficiency",
        "Periconceptional and pregnancy folate supplementation; high-dose use only when indicated",
        "Preventive or deficiency-specific",
        "Dose and duration depend on indication and risk profile",
        "Oral",
        "Tablet",
        "Reference dose must be selected from the indication-specific guideline; do not infer high-dose therapy from routine ANC alone",
        "Hypersensitivity",
        "Can mask haematological manifestations of vitamin B12 deficiency",
        "Folate-related hypersensitivity is rare",
        "No major drug-class cross-reactivity",
        "Nausea, bloating, rash uncommon",
        "Rare hypersensitivity",
        "High-dose folate should not substitute for investigation of B12 deficiency",
        "Clinical indication; CBC/B12 when appropriate",
        "Some antiepileptic medicines can have folate interactions",
        "No major routine renal adjustment",
        "No major routine hepatic adjustment",
        "Compatible at usual nutritional doses",
        "Widely used in India",
        "NLEM 2022: listed",
        "A",
        "NHM / NLEM 2022",
        "High-dose folate should be encoded by indication rather than randomly assigned",
        "No",
    )

    add(
        "MAT-003",
        "Calcium carbonate + vitamin D3",
        "Elemental calcium + cholecalciferol",
        "Calcium carbonate + vitamin D3",
        "Mineral / vitamin",
        "Pregnancy calcium supplementation",
        "Routine calcium supplementation in Indian ANC",
        "Preventive therapy",
        "NHM pregnancy protocol starts around 14 weeks and continues through postpartum period; local programme applies",
        "Oral",
        "500 mg elemental calcium + vitamin D3 tablets",
        "Indian NHM training material: 500 mg elemental calcium + 250 IU vitamin D3 per tablet, commonly twice daily",
        "Hypercalcaemia; severe renal calculi depending on clinical context; hypersensitivity",
        "Kidney stones; renal impairment; hypervitaminosis D",
        "Formulation-specific",
        "No major antibiotic-type cross-reactivity",
        "Constipation, abdominal discomfort",
        "Hypercalcaemia, nephrolithiasis",
        "Excess calcium may interfere with iron absorption",
        "Serum calcium/renal function when clinically indicated; adherence",
        "Iron, levothyroxine and several antibiotics require dose separation",
        "Use caution in renal impairment",
        "Vitamin D/calcium disorders may require adjustment",
        "Compatible at recommended nutritional doses",
        "Core Indian maternal nutrition intervention",
        "National guideline supported; formulation specified in NHM material",
        "A",
        "NHM calcium supplementation guidance; NHM CEmONC 2024",
        "Separate calcium and IFA because calcium reduces iron absorption",
        "No",
    )

    add(
        "MAT-004",
        "Intravenous iron",
        "Iron preparation: formulation-specific",
        "Iron sucrose / ferric carboxymaltose / other approved formulation",
        "Parenteral haematinic",
        "Moderate/severe iron deficiency anaemia or intolerance/non-response to oral iron",
        "Treatment when clinically indicated",
        "Use depends on gestational age, severity, formulation and national protocol",
        "Intravenous",
        "Injection/infusion; formulation-specific",
        "Dose is formulation- and patient-specific; calculate iron requirement and follow current NHM IV iron protocol",
        "Previous serious hypersensitivity to the same formulation; iron overload",
        "Anaphylaxis risk; infusion reactions; infection/inflammation may complicate interpretation",
        "Iron formulation hypersensitivity",
        "Do not infer cross-reactivity between unrelated biologics; use product-specific history",
        "Headache, nausea, injection/infusion reactions",
        "Anaphylaxis, severe hypersensitivity, hypotension",
        "Use only when indicated; parenteral exposure carries acute reaction risk",
        "Hb; ferritin/iron studies when indicated; infusion monitoring",
        "Oral iron timing depends on formulation and clinical plan",
        "Dose/choice require renal and inflammatory context",
        "Evaluate cause of anaemia and liver iron overload where relevant",
        "Generally compatible after clinician assessment",
        "India has current NHM IV iron guidance",
        "NLEM 2022 includes parenteral iron formulations",
        "A",
        "NHM AMB 2026; NLEM 2022",
        "Current NHM page includes dedicated guidance note on IV iron in pregnant women",
        "No",
    )

    add(
        "MAT-005",
        "Albendazole",
        "Albendazole",
        "Benzimidazole anthelmintic",
        "Anthelmintic",
        "Deworming in pregnancy",
        "Second-trimester deworming in eligible settings/programmes",
        "Preventive/public-health intervention",
        "Avoid routine first-trimester use; follow current Indian deworming programme",
        "Oral",
        "Tablet",
        "National deworming guidance specifies programme-based use in the second trimester",
        "Hypersensitivity; severe hepatic disease requiring specialist review",
        "Liver disease; concomitant hepatotoxic medicines",
        "Benzimidazole hypersensitivity",
        "Mebendazole/other benzimidazole cross-reactivity may be relevant",
        "Abdominal pain, nausea, headache, dizziness",
        "Hepatotoxicity, severe skin reactions rare",
        "Timing in pregnancy is programme-specific",
        "Clinical symptoms; liver function when prolonged/repeated therapy",
        "Potential interaction with enzyme-inducing drugs",
        "Caution in liver disease",
        "Caution in significant hepatic impairment",
        "Short-course use generally compatible when indicated",
        "Indian ANC public-health programme relevance",
        "National guideline supported",
        "A",
        "NHM National Guidelines for Deworming in Pregnancy",
        "Use is programme-based and trimester-specific",
        "No",
    )

    # ------------------------------------------------------------
    # 2. PRE-ECLAMPSIA / HYPERTENSION
    # ------------------------------------------------------------

    add(
        "MAT-006",
        "Low-dose aspirin",
        "Acetylsalicylic acid",
        "Aspirin",
        "Antiplatelet / salicylate",
        "Pre-eclampsia prevention in high-risk pregnancy",
        "Prevention in selected high-risk patients",
        "Preventive, risk-factor driven",
        "Typically initiated in early pregnancy when indicated; stop timing follows clinician/institution protocol",
        "Oral",
        "Low-dose tablet",
        "Use guideline-defined low-dose regimen; commonly 75-150 mg once daily in high-risk pregnancy",
        "Aspirin/NSAID hypersensitivity; active bleeding; selected bleeding disorders; severe aspirin-sensitive asthma",
        "GI ulcer/bleeding; thrombocytopenia; anticoagulant use",
        "Salicylate / NSAID hypersensitivity",
        "Potential cross-reactivity with other non-selective NSAIDs in aspirin-exacerbated respiratory disease",
        "Dyspepsia, nausea, bruising",
        "GI bleeding, bronchospasm, anaphylaxis, haemorrhage",
        "Late-pregnancy use requires careful obstetric assessment",
        "Bleeding symptoms; BP/risk pathway; platelet count when indicated",
        "Anticoagulants, other antiplatelets, NSAIDs, corticosteroids may increase bleeding risk",
        "Renal caution with prolonged use",
        "Hepatic caution in significant disease",
        "Low-dose use requires clinician assessment",
        "Major Indian and international obstetric relevance",
        "NLEM 2022: aspirin listed",
        "A",
        "NICE NG133; WHO pre-eclampsia guidance; NLEM 2022",
        "Do not assign merely because pregnancy exists; require risk factors",
        "No",
    )

    add(
        "MAT-007",
        "Labetalol",
        "Labetalol",
        "Alpha-1 + beta adrenergic blocker",
        "Antihypertensive",
        "Hypertension in pregnancy",
        "Common pregnancy-compatible antihypertensive option",
        "Treatment of maternal hypertension",
        "Use throughout pregnancy when clinically indicated; monitor maternal/fetal response",
        "Oral; intravenous",
        "50/100 mg tablets; IV injection",
        "Dose is titrated to BP and clinical response; do not generate a patient dose automatically",
        "Asthma/bronchospastic disease; bradycardia; heart block; cardiogenic shock; decompensated heart failure",
        "Hypotension, bradycardia, bronchospasm",
        "Beta-blocker hypersensitivity",
        "Potential class cross-reactivity among beta-blockers is clinically relevant",
        "Fatigue, dizziness, nausea, postural symptoms",
        "Bradycardia, bronchospasm, severe hypotension, heart block",
        "Neonatal bradycardia/hypoglycaemia can occur with late exposure; monitor newborn when indicated",
        "BP; pulse; respiratory symptoms; fetal growth/assessment as clinically indicated",
        "Other BP-lowering drugs; insulin/antidiabetic therapy may mask hypoglycaemia",
        "Dose/monitoring may require adjustment in renal disease",
        "Caution in significant hepatic disease",
        "Generally compatible; monitor infant for bradycardia/hypoglycaemia if clinically indicated",
        "Listed in NLEM and used in Indian obstetric care",
        "NLEM 2022: listed",
        "A",
        "MoHFW STG; NLEM 2022; pregnancy hypertension guidance",
        "Indian NLEM lists labetalol in antihypertensive medicines",
        "No",
    )

    add(
        "MAT-008",
        "Nifedipine",
        "Nifedipine",
        "Dihydropyridine calcium-channel blocker",
        "Antihypertensive",
        "Hypertension in pregnancy; acute BP control in selected settings",
        "Pregnancy-compatible antihypertensive option",
        "Treatment",
        "Use depends on formulation and clinical setting",
        "Oral",
        "Immediate-release and modified-release formulations",
        "Dose individualized; formulation-specific",
        "Hypersensitivity; profound hypotension; caution in severe aortic stenosis",
        "Headache, flushing, tachycardia, oedema",
        "Severe hypotension, syncope",
        "No major teratogenic signal at therapeutic use; clinical context matters",
        "BP, pulse, symptoms",
        "Other antihypertensives; CYP3A4 inhibitors/inducers",
        "Caution in severe renal impairment",
        "Caution in hepatic impairment",
        "Generally compatible; monitor clinically",
        "Widely available and used in India",
        "NLEM 2022: listed",
        "A",
        "MoHFW STG; NLEM 2022; pregnancy hypertension guidance",
        "Do not confuse immediate-release and modified-release formulations",
        "No",
    )

    add(
        "MAT-009",
        "Methyldopa",
        "Methyldopa",
        "Central alpha-2 agonist precursor",
        "Antihypertensive",
        "Hypertension in pregnancy",
        "Pregnancy-compatible alternative when clinically appropriate",
        "Treatment",
        "Use based on clinician assessment; may be less favored in some modern protocols because of tolerability",
        "Oral",
        "Tablet",
        "Dose individualized and titrated",
        "Active liver disease; previous methyldopa-associated liver injury; hypersensitivity",
        "Sedation; depression; hepatic dysfunction; haemolytic anaemia",
        "Methyldopa hypersensitivity",
        "No major antibiotic cross-reactivity",
        "Drowsiness, dry mouth, headache, weakness",
        "Hepatitis, haemolytic anaemia, severe liver injury",
        "Maternal sedation can affect functioning",
        "BP; liver function if prolonged/symptomatic; CBC if haemolysis suspected",
        "Iron can reduce methyldopa absorption; separate administration",
        "Caution in renal impairment",
        "Avoid/stop if significant liver injury develops",
        "Usually compatible",
        "Still relevant as a pregnancy antihypertensive in India",
        "NLEM 2022: listed",
        "A",
        "MoHFW STG; NLEM 2022",
        "Alternative rather than automatic first choice",
        "No",
    )

    add(
        "MAT-010",
        "Magnesium sulfate",
        "Magnesium sulfate",
        "Magnesium salt",
        "Anticonvulsant / electrolyte",
        "Severe pre-eclampsia / eclampsia seizure prevention or treatment",
        "Obstetric emergency treatment",
        "Emergency/critical care",
        "Gestational-age independent emergency indication",
        "Intravenous; intramuscular",
        "Injection",
        "Regimen depends on national/institutional eclampsia protocol",
        "Heart block; severe renal failure without appropriate monitoring; hypersensitivity",
        "Respiratory depression, reduced reflexes, renal impairment",
        "Magnesium salt hypersensitivity",
        "No meaningful antibiotic-class cross-reactivity",
        "Flushing, nausea, lethargy",
        "Respiratory depression, loss of reflexes, arrhythmia, cardiac arrest in toxicity",
        "Neonatal hypotonia/respiratory depression possible with prolonged maternal exposure",
        "Respiratory rate; deep tendon reflexes; urine output; serum magnesium when indicated; calcium gluconate availability",
        "Neuromuscular blockers and other CNS depressants can potentiate effects",
        "Renal clearance is critical; reduce/withhold according to protocol in oliguria",
        "No major hepatic clearance issue",
        "Short emergency use generally compatible",
        "Core obstetric emergency medicine",
        "NLEM 2022: magnesium sulfate listed",
        "A",
        "MoHFW obstetric STG; NLEM 2022; WHO",
        "High-risk medicine requiring monitored administration",
        "No",
    )

    # ------------------------------------------------------------
    # 3. DIABETES / GDM
    # ------------------------------------------------------------

    add(
        "MAT-011",
        "Metformin",
        "Metformin",
        "Biguanide",
        "Antidiabetic",
        "Gestational diabetes / type 2 diabetes",
        "Selected GDM pharmacotherapy when lifestyle therapy is inadequate and clinician considers it appropriate",
        "Treatment",
        "Use requires individual risk/benefit assessment",
        "Oral",
        "Immediate-release / extended-release tablets",
        "Dose individualized; titrate to tolerance and glycaemic targets",
        "Severe renal impairment; metabolic acidosis; hypersensitivity",
        "GI intolerance; dehydration; hypoxia; acute severe illness",
        "Biguanide hypersensitivity",
        "No meaningful antibiotic cross-reactivity",
        "Nausea, diarrhoea, abdominal discomfort, reduced appetite",
        "Lactic acidosis rare but serious",
        "Crosses placenta; use according to current pregnancy diabetes guidance",
        "Fasting/postprandial glucose; renal function; GI tolerance",
        "Iodinated contrast in selected high-risk settings; cationic drugs affecting renal tubular secretion",
        "Renal function is central to safe use",
        "Caution in severe hepatic disease",
        "Generally compatible when clinically indicated",
        "Highly relevant to Indian diabetes care",
        "NLEM 2022: listed",
        "A",
        "NHM GDM guideline; MoHFW/NLEM; diabetes guidance",
        "Do not use as automatic response to a positive screening test",
        "No",
    )

    add(
        "MAT-012",
        "Human insulin",
        "Human insulin",
        "Regular insulin / NPH insulin",
        "Insulin",
        "GDM and pre-existing diabetes",
        "Pregnancy-compatible glucose-lowering therapy",
        "Treatment / escalation when indicated",
        "Can be used throughout pregnancy under specialist/clinician management",
        "Subcutaneous; intravenous for selected acute settings",
        "Regular human insulin; NPH/isophane insulin",
        "Individualized to glucose profile and insulin regimen",
        "Hypoglycaemia; hypersensitivity to insulin/excipients",
        "Renal/hepatic changes alter insulin requirement",
        "Insulin/excipient hypersensitivity",
        "Product-specific; recombinant human insulin has low immunogenicity but allergy remains possible",
        "Hypoglycaemia, injection-site reactions, weight gain",
        "Severe hypoglycaemia, anaphylaxis, hypokalaemia",
        "Maternal hypoglycaemia is the major safety concern",
        "Capillary glucose; hypoglycaemia; injection technique; potassium in selected settings",
        "Other glucose-lowering agents increase hypoglycaemia risk",
        "Insulin requirements may fall in renal impairment",
        "Requirements can change with hepatic disease",
        "Compatible; insulin is not orally active in infant",
        "Core Indian GDM treatment option",
        "NLEM 2022: insulin listed",
        "A",
        "NHM GDM guideline; NLEM 2022",
        "Use insulin as an individualized regimen, not a fixed synthetic dose",
        "No",
    )

    # ------------------------------------------------------------
    # 4. THYROID / EPILEPSY
    # ------------------------------------------------------------

    add(
        "MAT-013",
        "Levothyroxine",
        "Levothyroxine sodium",
        "Synthetic T4",
        "Thyroid hormone",
        "Hypothyroidism in pregnancy",
        "Treatment of maternal hypothyroidism",
        "Treatment",
        "Pregnancy increases thyroid hormone requirements in many patients; target-based monitoring is essential",
        "Oral",
        "Tablet",
        "Dose individualized to TSH/free T4 and pregnancy targets",
        "Untreated thyrotoxicosis is not an indication; hypersensitivity to excipients; caution with adrenal insufficiency",
        "Cardiac disease; overtreatment",
        "Product/excipient hypersensitivity",
        "No major pharmacologic cross-reactivity",
        "Palpitations, tremor, sweating, insomnia if over-replaced",
        "Arrhythmia, angina, severe thyrotoxicosis from excessive dosing",
        "Undertreatment harms pregnancy; overtreatment also carries risk",
        "TSH and free T4 at guideline-defined intervals",
        "Iron, calcium, antacids reduce absorption; separate dosing",
        "No routine renal adjustment",
        "No major hepatic adjustment",
        "Compatible; standard treatment for maternal hypothyroidism",
        "National Indian hypothyroidism-in-pregnancy guideline",
        "NLEM 2022: listed",
        "A",
        "NHM National Guidelines for Screening of Hypothyroidism during Pregnancy; NLEM 2022",
        "Dose should never be invented without thyroid function context",
        "No",
    )

    add(
        "MAT-014",
        "Levetiracetam",
        "Levetiracetam",
        "Pyrrolidone anticonvulsant",
        "Antiepileptic",
        "Epilepsy in pregnancy",
        "Continuation/management of pre-existing epilepsy when clinically appropriate",
        "Treatment of maternal epilepsy",
        "Do not abruptly stop antiseizure therapy; specialist management required",
        "Oral; intravenous",
        "Tablet; oral solution; injection",
        "Individualized based on seizure control and renal function",
        "Hypersensitivity",
        "Mood/behavioral effects; renal impairment",
        "Levetiracetam hypersensitivity",
        "No major structural cross-reactivity with aromatic antiseizure medicines",
        "Somnolence, dizziness, irritability, fatigue",
        "Severe psychiatric effects; hypersensitivity",
        "Avoid uncontrolled seizures; pregnancy pharmacokinetics can change",
        "Seizure control; adherence; renal function; mental state",
        "Few major CYP interactions compared with older antiseizure drugs",
        "Dose adjustment in renal impairment",
        "No major routine hepatic adjustment",
        "Generally compatible when clinically indicated",
        "India epilepsy guideline relevance",
        "NLEM 2022: listed",
        "A/B",
        "MoHFW epilepsy guideline; NLEM 2022",
        "This catalogue does not attempt to select an antiseizure drug automatically",
        "No",
    )

    # ------------------------------------------------------------
    # 5. INFECTIONS
    # ------------------------------------------------------------

    add(
        "MAT-015",
        "Benzathine penicillin G",
        "Benzathine benzylpenicillin",
        "Long-acting penicillin",
        "Beta-lactam antibiotic",
        "Syphilis in pregnancy",
        "First-line treatment of maternal syphilis",
        "Infection treatment",
        "Pregnancy-compatible and essential for fetal infection prevention",
        "Intramuscular",
        "Long-acting IM injection",
        "Early vs late/unknown syphilis regimens are different; follow current national protocol",
        "Penicillin hypersensitivity",
        "Anaphylaxis; Jarisch-Herxheimer reaction; injection-site reaction",
        "Penicillin allergy",
        "Potential cross-reactivity with other beta-lactams is clinically relevant",
        "Pain at injection site, rash",
        "Anaphylaxis, severe hypersensitivity",
        "For syphilis in pregnancy, non-penicillin alternatives may fail to treat the fetus",
        "Allergy history; treatment completion; RPR/VDRL follow-up",
        "Probenecid can alter penicillin concentrations",
        "No major dose adjustment for usual syphilis regimen; severe renal disease requires clinician review",
        "No major hepatic issue",
        "Compatible; treatment is essential when indicated",
        "Explicitly supported by Indian CEmONC/NHM material",
        "NLEM 2022: penicillins listed",
        "A",
        "NHM CEmONC 2024; NHM syphilis guidance; WHO",
        "Indian CEmONC states penicillin is the proven fetal-protective treatment",
        "No",
    )

    add(
        "MAT-016",
        "Amoxicillin",
        "Amoxicillin",
        "Aminopenicillin",
        "Beta-lactam antibiotic",
        "Bacterial infection",
        "Clinically indicated susceptible bacterial infections",
        "Treatment when culture/clinical indication supports use",
        "Use according to infection and antimicrobial guidance",
        "Oral; intravenous",
        "Capsule/tablet/suspension; injection formulation where available",
        "Infection-specific regimen; no generic pregnancy dose should be inferred",
        "Penicillin hypersensitivity; selected severe beta-lactam allergy",
        "Rash in EBV; C. difficile-associated diarrhoea; renal impairment",
        "Penicillin allergy",
        "Potential beta-lactam cross-reactivity",
        "Nausea, diarrhoea, rash",
        "Anaphylaxis, severe cutaneous reactions, C. difficile colitis",
        "Use only for an appropriate bacterial indication",
        "Culture where appropriate; allergy; renal function; response",
        "Warfarin may alter INR; probenecid increases levels",
        "Renal dose adjustment may be required",
        "No major hepatic adjustment",
        "Generally compatible when indicated",
        "Commonly available in India; stewardship important",
        "NLEM 2022: amoxicillin listed",
        "A",
        "MoHFW antimicrobial STG; NLEM 2022",
        "Not an empiric treatment for every fever",
        "No",
    )

    add(
        "MAT-017",
        "Cephalexin",
        "Cephalexin",
        "First-generation cephalosporin",
        "Beta-lactam antibiotic",
        "Bacterial infections / UTI",
        "Selected susceptible infections in pregnancy",
        "Treatment when clinically indicated",
        "Often used in pregnancy when appropriate",
        "Oral",
        "Capsule/tablet/suspension",
        "Infection-specific",
        "Severe immediate beta-lactam allergy",
        "Renal impairment; C. difficile diarrhoea",
        "Cephalosporin allergy",
        "Some cross-reactivity with penicillins; risk depends on side-chain similarity",
        "Nausea, diarrhoea, rash",
        "Anaphylaxis, severe cutaneous reaction, C. difficile",
        "Use culture-guided therapy for UTI where feasible",
        "Culture/susceptibility; allergy; renal function",
        "Anticoagulant monitoring may be needed in selected patients",
        "Renal dose adjustment",
        "No major hepatic adjustment",
        "Generally compatible",
        "Relevant to pregnancy-associated bacterial infection in India",
        "NLEM 2022: cephalosporins listed",
        "A/B",
        "MoHFW antimicrobial STG; NLEM 2022",
        "Do not treat asymptomatic bacteriuria/UTI without appropriate diagnostic context",
        "No",
    )

    add(
        "MAT-018",
        "Azithromycin",
        "Azithromycin",
        "Macrolide antibiotic",
        "Antibiotic",
        "Selected bacterial infections",
        "Selected infections including organisms requiring macrolide therapy",
        "Treatment when indicated",
        "Pregnancy use depends on infection and alternatives",
        "Oral; intravenous",
        "Tablet/capsule/suspension; injection",
        "Infection-specific",
        "Macrolide hypersensitivity; prior azithromycin-associated cholestatic jaundice/liver injury",
        "QT prolongation; hepatic disease",
        "Macrolide allergy",
        "Possible class cross-reactivity",
        "Nausea, diarrhoea, abdominal discomfort",
        "QT prolongation, severe liver injury, severe allergic reaction",
        "Use only for appropriate indication",
        "LFTs when prolonged/at risk; ECG if QT risk",
        "Other QT-prolonging medicines",
        "No major routine renal adjustment",
        "Hepatic caution",
        "Generally compatible when indicated",
        "Common in Indian practice; antimicrobial stewardship required",
        "NLEM 2022: listed",
        "A/B",
        "MoHFW antimicrobial STG; NLEM 2022; WHO",
        "Not a universal pregnancy antibiotic",
        "No",
    )

    add(
        "MAT-019",
        "Metronidazole",
        "Metronidazole",
        "Nitroimidazole",
        "Antimicrobial",
        "Anaerobic/protozoal infections",
        "Clinically indicated infections",
        "Treatment when indicated",
        "Use depends on indication and gestational context",
        "Oral; intravenous; vaginal formulations vary",
        "Tablet; injection; local formulations",
        "Infection-specific",
        "Hypersensitivity; disulfiram reaction risk; selected severe hepatic disease",
        "Peripheral neuropathy with prolonged use; alcohol interaction",
        "Nitroimidazole hypersensitivity",
        "Possible class cross-reactivity",
        "Nausea, metallic taste, diarrhoea",
        "Neuropathy, seizures rare, severe skin reactions",
        "Use according to current infection guidance",
        "Clinical response; neurological symptoms with prolonged therapy",
        "Alcohol causes disulfiram-like reaction; warfarin interaction",
        "Dose adjustment may be needed in severe renal disease depending on context",
        "Hepatic impairment may require adjustment",
        "Generally compatible when clinically indicated",
        "Common Indian antimicrobial",
        "NLEM 2022: listed",
        "A/B",
        "MoHFW antimicrobial STG; NLEM 2022",
        "Avoid indiscriminate empiric use",
        "No",
    )

    add(
        "MAT-020",
        "Erythromycin",
        "Erythromycin",
        "Macrolide",
        "Antibiotic",
        "Selected infections / syphilis alternative under specialist guidance",
        "Selected infection treatment",
        "Alternative only in specific circumstances; not a substitute for penicillin in fetal syphilis protection",
        "Oral",
        "Tablet/capsule/suspension",
        "Infection-specific",
        "Macrolide hypersensitivity; prior cholestatic hepatitis",
        "QT prolongation; hepatic disease; drug interactions",
        "Macrolide allergy",
        "Possible class cross-reactivity",
        "Nausea, abdominal pain, diarrhoea",
        "QT prolongation, cholestatic hepatitis",
        "For maternal syphilis, non-penicillin regimens do not reliably treat fetus",
        "ECG/LFTs when indicated; infection response",
        "CYP3A4 interactions; QT-prolonging drugs",
        "No major routine renal adjustment",
        "Hepatic caution",
        "Generally compatible when indicated",
        "Indian national obstetric material explicitly mentions erythromycin as a non-penicillin option when desensitization is impossible",
        "NLEM 2022: macrolides listed",
        "A",
        "NHM CEmONC 2024; NLEM 2022",
        "Syphilis use requires specialist interpretation because fetal protection differs from penicillin",
        "Yes",
    )

    # ------------------------------------------------------------
    # 6. PAIN / NAUSEA / GI
    # ------------------------------------------------------------

    add(
        "MAT-021",
        "Paracetamol",
        "Paracetamol / acetaminophen",
        "Para-aminophenol derivative",
        "Analgesic / antipyretic",
        "Pain / fever",
        "Symptomatic treatment when indicated",
        "Generally used when clinically appropriate",
        "Pregnancy use requires lowest effective dose and clinical assessment",
        "Oral; intravenous",
        "Tablet/capsule/syrup; injection",
        "Product- and indication-specific; avoid exceeding total daily dose",
        "Severe hepatic disease; hypersensitivity",
        "Alcohol use; malnutrition; hepatotoxic co-medications",
        "Paracetamol hypersensitivity",
        "No meaningful NSAID cross-reactivity",
        "Nausea, rash uncommon",
        "Acute liver failure in overdose",
        "Overdose is the key preventable hazard",
        "Total daily dose from all combination products; liver status",
        "Other paracetamol-containing products; enzyme inducers; warfarin with repeated use",
        "No routine renal adjustment for short use",
        "Hepatic function is central to safety",
        "Generally compatible at recommended doses",
        "Very common in India",
        "NLEM 2022: listed",
        "A",
        "NLEM 2022; standard pharmacology",
        "Dataset should distinguish single-agent paracetamol from combination products",
        "No",
    )

    add(
        "MAT-022",
        "Pyridoxine",
        "Pyridoxine hydrochloride / vitamin B6",
        "Vitamin B6",
        "Vitamin",
        "Nausea/vomiting in pregnancy; deficiency",
        "Symptomatic/supportive treatment",
        "May be used in pregnancy under clinical guidance",
        "Oral",
        "Tablet",
        "Indication-specific",
        "Hypersensitivity",
        "Chronic excessive dosing causes neuropathy",
        "Vitamin B6 hypersensitivity rare",
        "No major class cross-reactivity",
        "Nausea, headache uncommon",
        "Peripheral neuropathy with excessive chronic intake",
        "Avoid unnecessary high-dose chronic exposure",
        "Symptoms; dose/duration",
        "Levodopa without carbidopa can interact",
        "No major routine renal adjustment",
        "No major routine hepatic adjustment",
        "Compatible at nutritional/therapeutic doses",
        "Common vitamin used in India",
        "NLEM 2022: vitamins listed",
        "B",
        "Standard pharmacology; NLEM 2022",
        "Use is indication-specific",
        "No",
    )

    add(
        "MAT-023",
        "Doxylamine + pyridoxine",
        "Doxylamine succinate + pyridoxine",
        "Antihistamine + vitamin B6",
        "Antiemetic",
        "Nausea and vomiting of pregnancy",
        "Symptomatic treatment when clinically indicated",
        "Pregnancy-specific antiemetic option",
        "Oral",
        "Modified-release tablets where available",
        "Formulation-specific and clinician-directed",
        "Hypersensitivity; acute asthma/respiratory disease; narrow-angle glaucoma; urinary retention risk",
        "Sedation; additive CNS depression",
        "Antihistamine hypersensitivity",
        "Possible antihistamine class cross-reactivity",
        "Drowsiness, dry mouth, constipation",
        "Severe sedation, anticholinergic toxicity",
        "Sedation can affect driving and falls",
        "Symptom response; sedation; hydration",
        "Alcohol, sedatives, other anticholinergics",
        "Caution in renal impairment",
        "Caution in hepatic impairment",
        "Generally compatible when appropriately used",
        "Pregnancy-specific antiemetic relevance",
        "India availability varies by formulation",
        "B",
        "Established pregnancy pharmacology",
        "Catalogue entry supports clinician review; local formulary availability must be checked",
        "No",
    )

    # ------------------------------------------------------------
    # 7. OBSTETRIC EMERGENCY / DELIVERY / PPH
    # ------------------------------------------------------------

    add(
        "MAT-024",
        "Oxytocin",
        "Oxytocin",
        "Synthetic oxytocin",
        "Uterotonic",
        "Labour induction/augmentation; postpartum haemorrhage prevention/treatment",
        "Obstetric uterotonic",
        "Intrapartum/postpartum",
        "Not a routine antenatal medication",
        "Intravenous; intramuscular",
        "Injection/infusion",
        "Protocol-specific",
        "Situations where vaginal delivery/uterine stimulation is contraindicated; hypersensitivity",
        "Uterine hyperstimulation; water intoxication with prolonged high-dose infusion",
        "Oxytocin hypersensitivity",
        "No major pharmacologic cross-reactivity",
        "Nausea, headache, uterine cramping",
        "Uterine rupture, fetal distress, hyponatraemia, hypotension",
        "Requires monitored obstetric setting",
        "Uterine contractions, fetal heart rate, maternal vitals, fluid balance",
        "Other uterotonics; excessive IV fluids",
        "No major renal adjustment but fluid balance is critical",
        "No major hepatic issue",
        "Not relevant to routine lactation dosing; peripartum use",
        "Core Indian labour/PPH medicine",
        "NLEM 2022: listed",
        "A",
        "NHM uterotonics guidance; NLEM 2022",
        "Peripartum only; not an ANC prescription",
        "No",
    )

    add(
        "MAT-025",
        "Tranexamic acid",
        "Tranexamic acid",
        "Antifibrinolytic",
        "Haemostatic",
        "Postpartum haemorrhage treatment",
        "PPH treatment",
        "Emergency postpartum use",
        "Not routine antenatal prophylaxis",
        "Intravenous; oral",
        "Injection; tablet",
        "PPH protocol-specific; early treatment is time-sensitive",
        "Active thromboembolic disease; severe hypersensitivity; selected renal contraindications",
        "Thrombosis risk; renal impairment; visual symptoms",
        "Tranexamic acid hypersensitivity",
        "No major class cross-reactivity",
        "Nausea, diarrhoea, headache",
        "Thromboembolism, seizures at high exposure, visual disturbance",
        "Use only in appropriate haemorrhage pathway",
        "Bleeding response; thrombosis symptoms; renal function",
        "Procoagulant agents may increase thrombosis concern",
        "Renal elimination; dose adjustment required",
        "No major hepatic adjustment",
        "Short-course postpartum use generally compatible",
        "Included in Indian PPH guidance",
        "NLEM 2022: listed",
        "A",
        "NHM PPH guidance; CDSCO ADR surveillance; NLEM 2022",
        "Not an antenatal routine medication",
        "Yes",
    )

    add(
        "MAT-026",
        "Carboprost",
        "Carboprost tromethamine",
        "Prostaglandin analogue",
        "Uterotonic",
        "Refractory postpartum haemorrhage",
        "Second-line uterotonic in selected PPH",
        "Emergency postpartum",
        "Not routine pregnancy medication",
        "Intramuscular / intramyometrial depending on protocol",
        "Injection",
        "Protocol-specific",
        "Asthma/bronchospasm; hypersensitivity",
        "Bronchospasm, hypertension, GI effects",
        "Prostaglandin hypersensitivity",
        "Prostaglandin class effects",
        "Vomiting, diarrhoea, fever, bronchospasm",
        "Severe bronchospasm, pulmonary oedema, hypertension",
        "Major concern in asthma",
        "Respiratory status, BP, bleeding response",
        "Other uterotonics; asthma therapies",
        "Caution in renal disease",
        "Caution in hepatic disease",
        "Not routine lactation medication",
        "Relevant to obstetric emergency care in India",
        "India availability is protocol/formulary dependent",
        "A/B",
        "NHM PPH/uterotonic guidance; standard obstetric pharmacology",
        "Emergency use only",
        "Yes",
    )

    add(
        "MAT-027",
        "Misoprostol",
        "Misoprostol",
        "Prostaglandin E1 analogue",
        "Uterotonic",
        "PPH prevention/treatment in selected protocols; obstetric indications",
        "Obstetric uterotonic",
        "Intrapartum/postpartum depending on indication",
        "Not a routine antenatal medicine",
        "Oral; sublingual; rectal; vaginal depending on indication",
        "Tablet",
        "Indication- and protocol-specific",
        "Hypersensitivity; caution with inappropriate use outside protocol",
        "Fever, shivering, diarrhoea",
        "Prostaglandin hypersensitivity",
        "Prostaglandin class effects",
        "Shivering, fever, nausea, diarrhoea",
        "Hyperthermia, severe uterine hyperstimulation in inappropriate use",
        "Route/dose differ by indication",
        "Temperature, uterine activity, bleeding",
        "Other uterotonics may increase uterine effects",
        "No major routine adjustment",
        "No major hepatic adjustment",
        "Short postpartum use may be compatible",
        "Indian obstetric protocol relevance",
        "NLEM 2022: listed",
        "A",
        "NHM uterotonic/PPH guidance; NLEM 2022",
        "Do not use one regimen for different obstetric indications",
        "Yes",
    )

    # ------------------------------------------------------------
    # 8. RH IMMUNOPROPHYLAXIS / CORTICOSTEROID
    # ------------------------------------------------------------

    add(
        "MAT-028",
        "Anti-D immunoglobulin",
        "Human anti-D immunoglobulin",
        "Human immunoglobulin",
        "Immunoglobulin",
        "Prevention of RhD alloimmunization",
        "RhD-negative unsensitized pregnancy",
        "Preventive immunoprophylaxis",
        "Timing depends on gestational age, sensitizing event and local protocol",
        "Intramuscular; intravenous depending on product",
        "Injection",
        "Dose depends on gestational age and fetomaternal haemorrhage/event",
        "Previous severe hypersensitivity to immunoglobulin components; IgA deficiency with anti-IgA may matter depending on product",
        "Product-specific precautions; haemolysis rare",
        "Human immunoglobulin hypersensitivity",
        "Product-specific",
        "Injection-site pain, headache, fever",
        "Anaphylaxis, haemolysis, thrombosis rare",
        "Must distinguish prophylaxis from established alloimmunization",
        "Rh status, antibody screen, sensitizing events",
        "Live vaccines may require timing consideration after immunoglobulin",
        "No routine renal adjustment; hydration and product considerations",
        "No major hepatic adjustment",
        "Compatible",
        "Essential in RhD-negative obstetric pathways in India",
        "India availability/product specific",
        "A/B",
        "Obstetric transfusion/immunoprophylaxis standards",
        "Dataset should encode antibody status before assigning prophylaxis",
        "No",
    )

    add(
        "MAT-029",
        "Betamethasone",
        "Betamethasone",
        "Glucocorticoid",
        "Antenatal corticosteroid",
        "Fetal lung maturation when preterm birth is likely",
        "Antenatal corticosteroid course under obstetric protocol",
        "Time-limited fetal indication",
        "Gestational-age window and repeat-course policy are protocol-specific",
        "Intramuscular",
        "Injection",
        "Course is protocol-defined; do not invent dose from event data",
        "Systemic fungal infection; hypersensitivity; live vaccine considerations",
        "Diabetes/hyperglycaemia; infection; hypertension",
        "Corticosteroid hypersensitivity",
        "Class cross-reactivity possible",
        "Hyperglycaemia, insomnia, mood changes, injection-site pain",
        "Severe infection, hyperglycaemia, psychiatric effects rare",
        "Maternal glucose can rise; fetal benefits depend on correct timing",
        "Blood glucose in diabetes; infection; obstetric status",
        "Antidiabetic therapy; CYP3A4 modulators",
        "Dose adjustment generally not routine",
        "Caution in significant hepatic disease",
        "Short course generally compatible",
        "Relevant to Indian preterm birth management",
        "NLEM 2022: corticosteroids listed",
        "A/B",
        "WHO antenatal corticosteroid guidance; NLEM 2022",
        "Use only when preterm birth risk and gestational criteria are met",
        "Yes",
    )

    # ------------------------------------------------------------
    # 9. MEDICATIONS THAT SHOULD BE FLAGGED AS AVOID/REVIEW
    # ------------------------------------------------------------

    add(
        "MAT-030",
        "Enalapril",
        "Enalapril",
        "ACE inhibitor",
        "Antihypertensive",
        "Chronic hypertension outside pregnancy",
        "Important pre-pregnancy medication reconciliation item",
        "Pregnancy-avoid / switch-review medicine",
        "ACE inhibitors should not be continued routinely during pregnancy; clinician-directed substitution is required",
        "Oral",
        "Tablet",
        "No pregnancy regimen; replacement should be clinician-directed",
        "Pregnancy; history of angioedema; bilateral renal artery stenosis; hyperkalaemia",
        "Renal impairment, potassium elevation",
        "ACE-inhibitor hypersensitivity/angioedema",
        "ACE inhibitors as a class",
        "Cough, dizziness, hyperkalaemia",
        "Angioedema, renal failure, severe fetal toxicity",
        "Fetal renal dysfunction/oligohydramnios and other fetal toxicity",
        "BP; renal function; potassium; pregnancy exposure review",
        "Potassium supplements, potassium-sparing drugs, NSAIDs",
        "Renal function is critical",
        "No major hepatic issue",
        "Pregnancy avoidance is the key issue",
        "Highly relevant because Dataset 1 captures pre-pregnancy medication history",
        "NLEM 2022: ACE inhibitor listed",
        "A",
        "Standard pregnancy hypertension guidance; MoHFW STG",
        "Included specifically as a medication-reconciliation hazard",
        "Yes",
    )

    add(
        "MAT-031",
        "Losartan",
        "Losartan",
        "Angiotensin II receptor blocker",
        "Antihypertensive",
        "Chronic hypertension outside pregnancy",
        "Important pre-pregnancy medication reconciliation item",
        "Pregnancy-avoid / switch-review medicine",
        "ARBs should not be continued routinely during pregnancy",
        "Oral",
        "Tablet",
        "No pregnancy regimen; replacement clinician-directed",
        "Pregnancy; hypersensitivity; bilateral renal artery stenosis",
        "Renal impairment; hyperkalaemia",
        "ARB hypersensitivity",
        "ARB class",
        "Dizziness, hyperkalaemia",
        "Fetal renal toxicity, oligohydramnios, neonatal renal impairment",
        "Fetal toxicity",
        "BP; renal function; potassium; exposure review",
        "Potassium-raising agents; NSAIDs",
        "Renal function critical",
        "Hepatic metabolism; caution in liver disease",
        "Pregnancy avoidance",
        "Relevant for medication reconciliation",
        "NLEM 2022: ARB class represented",
        "A",
        "Pregnancy hypertension guidance; MoHFW STG",
        "Included as a safety flag rather than treatment option",
        "Yes",
    )

    add(
        "MAT-032",
        "Warfarin",
        "Warfarin",
        "Vitamin K antagonist",
        "Anticoagulant",
        "Thromboembolism/valvular indications outside pregnancy",
        "Pre-pregnancy medication reconciliation and specialist management",
        "Pregnancy-avoid/exception-only specialist use",
        "Pregnancy-specific anticoagulation requires specialist protocol",
        "Oral",
        "Tablet",
        "No generic pregnancy regimen",
        "Pregnancy in most indications; active bleeding; hypersensitivity",
        "Major bleeding; interactions; variable INR",
        "Coumarin hypersensitivity",
        "Coumarin class",
        "Bleeding, bruising, nausea",
        "Major haemorrhage, intracranial bleeding",
        "Embryopathy and fetal/neonatal bleeding risk",
        "INR, bleeding, indication review",
        "Extensive drug/food interactions",
        "Renal function affects overall anticoagulation risk",
        "Hepatic dysfunction strongly affects response",
        "Breastfeeding considerations are different from pregnancy",
        "Important safety flag for pre-pregnancy medication history",
        "NLEM 2022: warfarin listed",
        "A",
        "Standard anticoagulation/pregnancy guidance; NLEM 2022",
        "Included as a medication-safety reconciliation flag",
        "Yes",
    )

    return pd.DataFrame(rows)


# ================================================================
# ALLERGY / SAFETY CROSSWALK
# ================================================================

def allergy_crosswalk():

    rows = [
        ("ALG-001", "Penicillin", "Benzathine penicillin G; amoxicillin",
         "Avoid suspected culprit; specialist assessment. Penicillin is essential for maternal syphilis and desensitization may be required.",
         "Penicillins", "Possible beta-lactam cross-reactivity"),
        ("ALG-002", "Cephalosporin", "Cephalexin",
         "Assess reaction type and side-chain similarity.",
         "Cephalosporins", "Some penicillin cross-reactivity"),
        ("ALG-003", "NSAID/Aspirin", "Aspirin",
         "Avoid in true aspirin hypersensitivity; respiratory phenotype requires special caution.",
         "Non-selective NSAIDs", "Potential cross-reactivity"),
        ("ALG-004", "Beta-blocker", "Labetalol",
         "Allergy is not the main issue; asthma/bradycardia/heart block are important clinical cautions.",
         "Beta-blockers", "Class effects"),
        ("ALG-005", "Macrolide", "Azithromycin; erythromycin",
         "Avoid culprit macrolide and assess class reaction.",
         "Macrolides", "Possible class cross-reactivity"),
        ("ALG-006", "Nitroimidazole", "Metronidazole",
         "Avoid culprit and specialist review if true allergy.",
         "Nitroimidazoles", "Possible class cross-reactivity"),
        ("ALG-007", "Benzimidazole", "Albendazole",
         "Review prior reaction to albendazole/mebendazole.",
         "Benzimidazoles", "Potential class cross-reactivity"),
        ("ALG-008", "Insulin", "Human insulin",
         "Confirm product/excipient reaction; specialist assessment.",
         "Insulin products", "Product/excipient dependent"),
        ("ALG-009", "Immunoglobulin", "Anti-D immunoglobulin",
         "Review prior immunoglobulin reaction and IgA-related history where relevant.",
         "Human immunoglobulins", "Product-specific"),
        ("ALG-010", "Corticosteroid", "Betamethasone",
         "Review true corticosteroid allergy and excipients.",
         "Corticosteroids", "Possible class cross-reactivity"),
        ("ALG-011", "Prostaglandin", "Carboprost; misoprostol",
         "Review prior prostaglandin reaction and respiratory history.",
         "Prostaglandins", "Class effects"),
        ("ALG-012", "Paracetamol", "Paracetamol",
         "Avoid if true hypersensitivity or serious previous reaction.",
         "Paracetamol", "No major NSAID cross-reactivity"),
    ]

    return pd.DataFrame(
        rows,
        columns=[
            "Allergy_ID",
            "Allergy_Class",
            "Affected_Medications",
            "Safety_Action",
            "Class",
            "Cross_Reactivity_Note",
        ],
    )


# ================================================================
# INTERACTION RULES
# ================================================================

def interaction_rules():

    rows = [
        ("INT-001", "Iron", "Calcium",
         "Reduced iron absorption",
         "Separate administration; follow clinician/pharmacy timing."),
        ("INT-002", "Iron", "Levothyroxine",
         "Reduced levothyroxine absorption",
         "Separate administration."),
        ("INT-003", "Calcium", "Levothyroxine",
         "Reduced levothyroxine absorption",
         "Separate administration."),
        ("INT-004", "Methyldopa", "Iron",
         "Reduced methyldopa absorption",
         "Separate administration."),
        ("INT-005", "Aspirin", "Anticoagulants",
         "Increased bleeding risk",
         "Specialist review."),
        ("INT-006", "Aspirin", "NSAIDs",
         "Increased GI/bleeding risk",
         "Avoid unnecessary combination."),
        ("INT-007", "Labetalol", "Insulin",
         "Beta-blockade may mask hypoglycaemia symptoms",
         "Increase glucose monitoring awareness."),
        ("INT-008", "Metformin", "Iodinated contrast",
         "Renal/lactic acidosis safety consideration in selected patients",
         "Follow current contrast/renal protocol."),
        ("INT-009", "Metronidazole", "Alcohol",
         "Disulfiram-like reaction concern",
         "Avoid alcohol during therapy and appropriate interval."),
        ("INT-010", "Azithromycin", "QT-prolonging drugs",
         "Increased QT prolongation risk",
         "Review ECG/QT risk."),
        ("INT-011", "Magnesium sulfate", "Neuromuscular blockers",
         "Potentiated neuromuscular blockade",
         "Monitored setting."),
        ("INT-012", "Warfarin", "Multiple medicines/foods",
         "INR instability",
         "Close INR monitoring."),
        ("INT-013", "ACE inhibitor/ARB", "Potassium-raising drugs",
         "Hyperkalaemia",
         "Avoid/monitor; pregnancy exposure requires review."),
    ]

    return pd.DataFrame(
        rows,
        columns=[
            "Interaction_ID",
            "Drug_A",
            "Drug_B_or_Group",
            "Mechanism_or_Concern",
            "Recommended_Data_Action",
        ],
    )


# ================================================================
# GUIDELINE REFERENCE TABLE
# ================================================================

def guideline_references():

    rows = [
        ("SRC-001", "NHM", "Anaemia Mukt Bharat Operational Guidelines 2026",
         "Routine IFA; anaemia management; IV iron guidance",
         "Government of India / NHM"),
        ("SRC-002", "NHM", "National Guidelines for Calcium Supplementation During Pregnancy and Lactation",
         "Calcium formulation and maternal supplementation",
         "Government of India / NHM"),
        ("SRC-003", "NHM", "National Guidelines for Diagnosis & Management of GDM",
         "GDM screening and treatment framework",
         "Government of India / NHM"),
        ("SRC-004", "NHM", "National Guidelines for Screening of Hypothyroidism during Pregnancy",
         "Maternal hypothyroidism screening/management framework",
         "Government of India / NHM"),
        ("SRC-005", "NHM", "National Guidelines for Deworming in Pregnancy",
         "Second-trimester programme-based deworming",
         "Government of India / NHM"),
        ("SRC-006", "NHM", "Screening for Syphilis during Pregnancy",
         "Syphilis screening and treatment pathway",
         "Government of India / NHM"),
        ("SRC-007", "NHM", "Revised CEmONC Curriculum 2024",
         "Maternal emergency treatment including syphilis, calcium, obstetric care",
         "Government of India / NHM"),
        ("SRC-008", "MoHFW", "Standard Treatment Guidelines",
         "Indian clinical standard-treatment framework",
         "Government of India / MoHFW"),
        ("SRC-009", "CDSCO", "National List of Essential Medicines 2022",
         "India essential medicines and formulations",
         "Government of India / CDSCO"),
        ("SRC-010", "CDSCO", "Adverse Drug Reaction related Notifications",
         "India post-marketing ADR surveillance",
         "Government of India / CDSCO"),
        ("SRC-011", "WHO", "Antenatal care recommendations",
         "Pregnancy supplementation and maternal care evidence",
         "World Health Organization"),
        ("SRC-012", "NICE", "NG133 Hypertension in pregnancy",
         "Pregnancy hypertension prevention/treatment framework",
         "NICE"),
        ("SRC-013", "NICE", "NG3 Diabetes in pregnancy",
         "GDM medication escalation framework",
         "NICE"),
    ]

    return pd.DataFrame(
        rows,
        columns=[
            "Source_ID",
            "Organization",
            "Document",
            "Dataset_Use",
            "Authority_Type",
        ],
    )


# ================================================================
# ALLERGY ENGINE
# ================================================================

def allergy_hit(active_ingredients, patient_allergy):

    a = " ".join(split_terms(patient_allergy))
    if not a:
        return False

    med = str(active_ingredients).lower()

    class_map = {
        "penicillin": ["penicillin", "amoxicillin", "ampicillin", "benzathine"],
        "cephalosporin": ["cephalosporin", "cephalexin", "cef"],
        "aspirin": ["aspirin", "acetylsalicylic"],
        "nsaid": ["nsaid", "ibuprofen", "diclofenac", "naproxen"],
        "macrolide": ["macrolide", "azithromycin", "erythromycin"],
        "nitroimidazole": ["metronidazole", "nitroimidazole"],
        "benzimidazole": ["albendazole", "mebendazole", "benzimidazole"],
        "insulin": ["insulin"],
        "immunoglobulin": ["immunoglobulin", "anti-d"],
        "corticosteroid": ["corticosteroid", "betamethasone"],
        "prostaglandin": ["prostaglandin", "misoprostol", "carboprost"],
        "paracetamol": ["paracetamol", "acetaminophen"],
        "beta blocker": ["beta blocker", "labetalol", "metoprolol"],
    }

    for allergy_class, terms in class_map.items():

        if allergy_class in a:
            if any(term in med for term in terms):
                return True

        if any(term in a for term in terms):
            if any(term in med for term in terms):
                return True

    # Direct phrase match
    for token in a.split():
        if len(token) >= 5 and token in med:
            return True

    return False


# ================================================================
# DATASET LOADING
# ================================================================

def load_inputs():

    for path in [D1, D2, D3]:
        if not os.path.exists(path):
            raise FileNotFoundError(
                f"Missing required input:\n{path}\n\n"
                "Run and validate Dataset 1, Dataset 2 and Dataset 3 first."
            )

    d1 = pd.read_csv(D1)
    d2 = pd.read_csv(D2)
    d3 = pd.read_csv(D3)

    d1_patient = find_col(d1, ["Patient_ID"], True)
    d1_preg = find_col(d1, ["Pregnancy_ID"], True)

    d2_patient = find_col(d2, ["Patient_ID"], True)
    d2_preg = find_col(d2, ["Pregnancy_ID"], True)
    d2_visit = find_col(d2, ["Visit_ID"], True)
    d2_date = find_col(d2, ["Visit_Date"], True)

    d2[d2_date] = pd.to_datetime(
        d2[d2_date], errors="coerce"
    )

    d3_patient = find_col(d3, ["Patient_ID"], True)
    d3_preg = find_col(d3, ["Pregnancy_ID"], True)
    d3_date = find_col(
        d3,
        ["Test_Date", "Investigation_Date", "Lab_Date", "Date"],
        True,
    )
    d3_test = find_col(
        d3,
        ["Test_Name", "Investigation", "Investigation_Name", "Test"],
        True,
    )
    d3_value = find_col(
        d3,
        ["Result_Value", "Result", "Value", "Numeric_Result"],
        False,
    )
    d3_unit = find_col(
        d3,
        ["Result_Unit", "Unit", "Units"],
        False,
    )

    d3[d3_date] = pd.to_datetime(
        d3[d3_date], errors="coerce"
    )
    d3["_test_lower"] = d3[d3_test].astype(str).str.lower()
    d3["_value_num"] = (
        d3[d3_value].apply(num)
        if d3_value else np.nan
    )
    d3["_unit"] = (
        d3[d3_unit].fillna("").astype(str)
        if d3_unit else ""
    )

    return (
        d1, d2, d3,
        d1_patient, d1_preg,
        d2_patient, d2_preg, d2_visit, d2_date,
        d3_patient, d3_preg, d3_date, d3_test
    )


# ================================================================
# EVENT GENERATOR
# ================================================================

def generate_events(
    d1, d2, d3,
    d1_patient, d1_preg,
    d2_patient, d2_preg, d2_visit, d2_date,
    d3_patient, d3_preg, d3_date, d3_test,
    master
):

    events = []

    master_by_name = {
        row["Generic_Name"]: row.to_dict()
        for _, row in master.iterrows()
    }

    patients = {
        str(r[d1_patient]): r.to_dict()
        for _, r in d1.iterrows()
    }

    def visits(pid, preg):
        x = d2[
            (d2[d2_patient].astype(str) == str(pid))
            &
            (d2[d2_preg].astype(str) == str(preg))
        ].sort_values(d2_date)
        return x

    def labs(pid, preg):
        return d3[
            (d3[d3_patient].astype(str) == str(pid))
            &
            (d3[d3_preg].astype(str) == str(preg))
        ].sort_values(d3_date)

    def closest_visit(vs, date):
        if vs.empty:
            return None
        prior = vs[vs[d2_date] <= date]
        return prior.iloc[-1] if not prior.empty else vs.iloc[0]

    def add_event(
        patient,
        visit,
        med_name,
        event_type,
        indication,
        trigger_type,
        trigger_test="",
        trigger_value="",
        trigger_unit="",
        action="Started",
        response_status="Pending follow-up",
        observed_adverse_effect="None recorded",
        stop_reason="",
    ):

        if med_name not in master_by_name:
            return False

        med = master_by_name[med_name]

        allergy = patient.get(
            "Drug_Allergies", ""
        )

        hit = allergy_hit(
            med["Active_Ingredients"],
            allergy
        )

        if hit:
            return False

        event_date = pd.Timestamp(
            visit[d2_date]
        ).date()

        events.append({
            "Medication_Event_ID": (
                f"MED{len(events)+1:06d}"
            ),
            "Medication_ID": med["Medication_ID"],
            "Patient_ID": patient[d1_patient],
            "Pregnancy_ID": patient[d1_preg],
            "Visit_ID": visit[d2_visit],
            "Event_Date": event_date,
            "Gestational_Week": visit.get(
                "Gestational_Week", ""
            ),
            "Trimester": visit.get(
                "Trimester", ""
            ),

            "Generic_Name": med["Generic_Name"],
            "Active_Ingredients": med["Active_Ingredients"],
            "Drug_Class": med["Drug_Class"],
            "Therapeutic_Area": med["Therapeutic_Area"],

            "Event_Type": event_type,
            "Action": action,
            "Indication": indication,
            "Trigger_Type": trigger_type,
            "Trigger_Test": trigger_test,
            "Trigger_Value": trigger_value,
            "Trigger_Unit": trigger_unit,

            "Reference_Regimen_or_Dose_Band": (
                med["Reference_Regimen_or_Dose_Band"]
            ),
            "Route": med["Routes"],
            "Medication_Status": (
                "Active"
                if action in {
                    "Started",
                    "Continued",
                    "Dose reviewed",
                }
                else action
            ),

            "Observed_Adverse_Effect": observed_adverse_effect,
            "Response_Status": response_status,
            "Stop_Reason": stop_reason,

            "Patient_Allergy_Field": txt(
                patient.get("Drug_Allergies", "")
            ),
            "Allergy_Check": "PASSED",

            "Common_Adverse_Effects": (
                med["Common_Adverse_Effects"]
            ),
            "Serious_Adverse_Effects": (
                med["Serious_Adverse_Effects"]
            ),
            "Pregnancy_Specific_Risks": (
                med["Pregnancy_Specific_Risks"]
            ),
            "Monitoring": med["Monitoring"],
            "Important_Interactions": (
                med["Important_Interactions"]
            ),

            "Evidence_Grade": med["Evidence_Grade"],
            "Evidence_Sources": med["Evidence_Sources"],
        })

        return True

    # ------------------------------------------------------------
    # ROUTINE INDIA ANC PREVENTION
    # ------------------------------------------------------------

    for _, p in d1.iterrows():

        patient = p.to_dict()
        pid = patient[d1_patient]
        preg = patient[d1_preg]

        vs = visits(pid, preg)

        if vs.empty:
            continue

        first = vs.iloc[0]

        add_event(
            patient, first,
            "Iron + folic acid",
            "Preventive supplementation",
            "Routine pregnancy iron-folic acid supplementation",
            "Routine ANC",
            action="Started",
            response_status="Adherence monitoring",
        )

        add_event(
            patient, first,
            "Calcium carbonate + vitamin D3",
            "Preventive supplementation",
            "Routine pregnancy calcium supplementation",
            "Routine ANC",
            action="Started",
            response_status="Adherence monitoring",
        )

        # Deworming only in second trimester.
        second_trimester = vs[
            pd.to_numeric(
                vs["Gestational_Week"],
                errors="coerce"
            ).between(14, 27, inclusive="both")
        ]

        if not second_trimester.empty:
            add_event(
                patient,
                second_trimester.iloc[0],
                "Albendazole",
                "Preventive public-health treatment",
                "Pregnancy deworming in eligible programme setting",
                "Programme/gestational-age trigger",
                action="Started",
                response_status="Programme completion",
            )

        # Tetanus status review, not false administration.
        add_event(
            patient, first,
            "Tetanus-containing vaccine",
            "Immunization review",
            "Maternal/neonatal tetanus prevention",
            "Routine ANC",
            action="Vaccination status reviewed",
            response_status="Requires vaccination-history decision",
        )

        # --------------------------------------------------------
        # Aspirin high-risk prevention
        # --------------------------------------------------------

        high_risk = any(
            truthy(patient.get(x, False))
            for x in [
                "Previous_PreEclampsia",
                "Preexisting_Hypertension",
                "Preexisting_Diabetes",
                "Renal_Disease",
                "Autoimmune_Disease",
                "Multiple_Pregnancy",
            ]
        )

        if high_risk:

            eligible = vs[
                pd.to_numeric(
                    vs["Gestational_Week"],
                    errors="coerce"
                ).between(12, 20, inclusive="both")
            ]

            if not eligible.empty:
                add_event(
                    patient,
                    eligible.iloc[0],
                    "Low-dose aspirin",
                    "Pre-eclampsia prevention",
                    "High risk of pre-eclampsia",
                    "Risk-factor trigger",
                    action="Started",
                    response_status="Monitor bleeding/BP",
                )

        # --------------------------------------------------------
        # Pre-pregnancy medication reconciliation
        # --------------------------------------------------------

        current = txt(
            patient.get(
                "Current_Pre_Pregnancy_Medications", ""
            )
        )

        if current.lower() not in {
            "", "none", "no", "nan"
        }:

            # Generic reconciliation event.
            events.append({
                "Medication_Event_ID": (
                    f"MED{len(events)+1:06d}"
                ),
                "Medication_ID": "RECONCILIATION",
                "Patient_ID": pid,
                "Pregnancy_ID": preg,
                "Visit_ID": first[d2_visit],
                "Event_Date": pd.Timestamp(
                    first[d2_date]
                ).date(),
                "Gestational_Week": first.get(
                    "Gestational_Week", ""
                ),
                "Trimester": first.get(
                    "Trimester", ""
                ),
                "Generic_Name": current,
                "Active_Ingredients": (
                    "Not parsed from free-text baseline history"
                ),
                "Drug_Class": "Existing pre-pregnancy therapy",
                "Therapeutic_Area": "Medication reconciliation",
                "Event_Type": "Medication reconciliation",
                "Action": "Reviewed",
                "Indication": "Baseline medication safety review",
                "Trigger_Type": "Baseline history",
                "Trigger_Test": "",
                "Trigger_Value": "",
                "Trigger_Unit": "",
                "Reference_Regimen_or_Dose_Band": "",
                "Route": "As documented",
                "Medication_Status": "Review required",
                "Observed_Adverse_Effect": "",
                "Response_Status": "Clinician review required",
                "Stop_Reason": "",
                "Patient_Allergy_Field": txt(
                    patient.get("Drug_Allergies", "")
                ),
                "Allergy_Check": "MANUAL REVIEW",
                "Common_Adverse_Effects": "",
                "Serious_Adverse_Effects": "",
                "Pregnancy_Specific_Risks": "",
                "Monitoring": (
                    "Medication identity, dose, indication, "
                    "pregnancy compatibility and interactions"
                ),
                "Important_Interactions": "",
                "Evidence_Grade": "A",
                "Evidence_Sources": (
                    "Indian antenatal medication reconciliation principles"
                ),
            })

    # ------------------------------------------------------------
    # LAB-TRIGGERED ANAEMIA
    # ------------------------------------------------------------

    for _, p in d1.iterrows():

        patient = p.to_dict()
        pid = patient[d1_patient]
        preg = patient[d1_preg]

        vs = visits(pid, preg)
        ls = labs(pid, preg)

        if vs.empty or ls.empty:
            continue

        hb = ls[
            ls["_test_lower"].str.contains(
                r"haemoglobin|hemoglobin|\bhb\b",
                regex=True,
                na=False
            )
        ].dropna(
            subset=["_value_num"]
        )

        treated = False

        for _, lab in hb.iterrows():

            week = num(
                closest_visit(
                    vs, lab[d3_date]
                ).get("Gestational_Week", np.nan)
            )

            threshold = (
                10.5 if pd.notna(week)
                and 13 <= week < 28
                else 11.0
            )

            if lab["_value_num"] < threshold:

                visit = closest_visit(
                    vs, lab[d3_date]
                )

                if add_event(
                    patient,
                    visit,
                    "Iron + folic acid",
                    "Therapeutic supplementation",
                    "Anaemia in pregnancy",
                    "Laboratory trigger",
                    "Haemoglobin",
                    lab["_value_num"],
                    lab["_unit"],
                    action="Dose/therapy escalated",
                    response_status="Repeat Hb required",
                ):
                    treated = True
                    break

    # ------------------------------------------------------------
    # GDM
    # ------------------------------------------------------------

    for _, p in d1.iterrows():

        patient = p.to_dict()
        pid = patient[d1_patient]
        preg = patient[d1_preg]

        vs = visits(pid, preg)
        ls = labs(pid, preg)

        if vs.empty or ls.empty:
            continue

        glucose = ls[
            ls["_test_lower"].str.contains(
                r"gdm|ogtt|oral glucose|fasting glucose|"
                r"2.?hour glucose|glucose tolerance",
                regex=True,
                na=False
            )
        ].dropna(
            subset=["_value_num"]
        ).sort_values(d3_date)

        first_positive = None

        for _, lab in glucose.iterrows():

            name = lab["_test_lower"]
            val = lab["_value_num"]

            positive = (
                ("fasting" in name and val >= 5.6)
                or
                (
                    (
                        "2-hour" in name
                        or "2 hour" in name
                        or "2hr" in name
                    )
                    and val >= 7.8
                )
            )

            if positive:
                first_positive = lab
                break

        if first_positive is None:
            continue

        visit = closest_visit(
            vs, first_positive[d3_date]
        )

        add_event(
            patient,
            visit,
            "Metformin",
            "GDM treatment escalation",
            "GDM with inadequate control after lifestyle intervention",
            "Treatment pathway",
            d3_test,
            first_positive["_value_num"],
            first_positive["_unit"],
            action="Clinical option reviewed",
            response_status="Requires clinician decision",
        )

        # Insulin as escalation option, not automatic co-prescription.
        if first_positive["_value_num"] >= 7.0:
            add_event(
                patient,
                visit,
                "Human insulin",
                "GDM pharmacotherapy escalation",
                "Marked hyperglycaemia requiring insulin-based management",
                "High glucose trigger",
                d3_test,
                first_positive["_value_num"],
                first_positive["_unit"],
                action="Clinical option reviewed",
                response_status="Requires clinician decision",
            )

    # ------------------------------------------------------------
    # THYROID
    # ------------------------------------------------------------

    for _, p in d1.iterrows():

        patient = p.to_dict()

        if not truthy(
            patient.get("Thyroid_Disease", False)
        ):
            continue

        vs = visits(
            patient[d1_patient],
            patient[d1_preg]
        )
        ls = labs(
            patient[d1_patient],
            patient[d1_preg]
        )

        tsh = ls[
            ls["_test_lower"].str.contains(
                r"\btsh\b|thyroid stimulating",
                regex=True,
                na=False
            )
        ].dropna(
            subset=["_value_num"]
        )

        if not vs.empty and not tsh.empty:

            lab = tsh.iloc[0]
            visit = closest_visit(
                vs, lab[d3_date]
            )

            add_event(
                patient,
                visit,
                "Levothyroxine",
                "Continuation / dose review",
                "Maternal hypothyroidism",
                "Laboratory trigger",
                "TSH",
                lab["_value_num"],
                lab["_unit"],
                action="Dose reviewed",
                response_status="Repeat thyroid function monitoring",
            )

    # ------------------------------------------------------------
    # HYPERTENSION
    # ------------------------------------------------------------

    sbp = find_col(
        d2,
        ["SBP_mmHg", "Systolic_BP", "Systolic_BP_mmHg"]
    )
    dbp = find_col(
        d2,
        ["DBP_mmHg", "Diastolic_BP", "Diastolic_BP_mmHg"]
    )

    if sbp and dbp:

        for _, p in d1.iterrows():

            patient = p.to_dict()

            vs = visits(
                patient[d1_patient],
                patient[d1_preg]
            ).copy()

            if vs.empty:
                continue

            vs["_sbp"] = pd.to_numeric(
                vs[sbp], errors="coerce"
            )
            vs["_dbp"] = pd.to_numeric(
                vs[dbp], errors="coerce"
            )

            elevated = vs[
                (vs["_sbp"] >= 140)
                | (vs["_dbp"] >= 90)
            ]

            persistent = (
                truthy(
                    patient.get(
                        "Preexisting_Hypertension",
                        False
                    )
                )
                or len(elevated) >= 2
            )

            if not persistent or elevated.empty:
                continue

            first = elevated.iloc[0]

            # Asthma is a safety-context feature, not a diagnosis.
            if truthy(patient.get("Asthma", False)):
                med = "Nifedipine"
            else:
                med = "Labetalol"

            add_event(
                patient,
                first,
                med,
                "Antihypertensive treatment",
                "Persistent hypertension in pregnancy",
                "ANC vital-sign trigger",
                "BP",
                f"{first['_sbp']}/{first['_dbp']}",
                "mmHg",
                action="Clinical treatment initiated/reviewed",
                response_status="Repeat BP monitoring",
            )

    return pd.DataFrame(events)


# ================================================================
# VALIDATION
# ================================================================

def validate(master, events, d1, d2, d3):

    issues = []

    # Master uniqueness.
    if master["Medication_ID"].duplicated().any():
        issues.append("Duplicate Medication_ID in master")

    if master["Generic_Name"].duplicated().any():
        issues.append("Duplicate Generic_Name in master")

    # Event IDs.
    if not events.empty and events["Medication_Event_ID"].duplicated().any():
        issues.append("Duplicate Medication_Event_ID")

    # Key integrity.
    d1_pairs = set(
        zip(
            d1["Patient_ID"].astype(str),
            d1["Pregnancy_ID"].astype(str)
        )
    )

    event_pairs = set(
        zip(
            events["Patient_ID"].astype(str),
            events["Pregnancy_ID"].astype(str)
        )
    )

    orphan_pairs = event_pairs - d1_pairs

    if orphan_pairs:
        issues.append(
            f"{len(orphan_pairs)} orphan patient/pregnancy keys"
        )

    # Medication references.
    known_ids = set(master["Medication_ID"])

    bad_med_ids = set(
        events.loc[
            events["Medication_ID"] != "RECONCILIATION",
            "Medication_ID"
        ]
    ) - known_ids

    if bad_med_ids:
        issues.append(
            f"Unknown Medication_ID values: {bad_med_ids}"
        )

    # Allergy safety.
    allergy_violations = 0

    patient_map = {
        str(r["Patient_ID"]): r.to_dict()
        for _, r in d1.iterrows()
    }

    master_map = {
        r["Medication_ID"]: r.to_dict()
        for _, r in master.iterrows()
    }

    for _, e in events.iterrows():

        if e["Medication_ID"] == "RECONCILIATION":
            continue

        p = patient_map.get(
            str(e["Patient_ID"]),
            {}
        )
        m = master_map.get(
            e["Medication_ID"],
            {}
        )

        if allergy_hit(
            m.get("Active_Ingredients", ""),
            p.get("Drug_Allergies", "")
        ):
            allergy_violations += 1

    if allergy_violations:
        issues.append(
            f"{allergy_violations} medication allergy violations"
        )

    # Event dates should map to ANC dates.
    d2_dates = set(
        (
            str(r["Patient_ID"]),
            str(r["Pregnancy_ID"]),
            pd.Timestamp(r["Visit_Date"]).date()
        )
        for _, r in d2.iterrows()
        if pd.notna(r["Visit_Date"])
    )

    orphan_dates = 0

    for _, e in events.iterrows():

        key = (
            str(e["Patient_ID"]),
            str(e["Pregnancy_ID"]),
            e["Event_Date"]
        )

        if key not in d2_dates:
            orphan_dates += 1

    if orphan_dates:
        issues.append(
            f"{orphan_dates} medication events not linked to ANC visit dates"
        )

    # Required safety fields.
    safety_cols = [
        "Contraindications",
        "Major_Cautions",
        "Allergy_Class",
        "Cross_Reactivity",
        "Common_Adverse_Effects",
        "Serious_Adverse_Effects",
        "Pregnancy_Specific_Risks",
        "Monitoring",
        "Important_Interactions",
        "Evidence_Sources",
    ]

    for c in safety_cols:
        missing = (
            master[c]
            .fillna("")
            .astype(str)
            .str.strip()
            .eq("")
            .sum()
        )

        if missing:
            issues.append(
                f"Master safety field '{c}' missing in {missing} rows"
            )

    return issues, allergy_violations, orphan_dates


# ================================================================
# SAVE EXCEL
# ================================================================

def autosize(writer, sheet_name, df):

    ws = writer.book[sheet_name]
    ws.freeze_panes = "A2"

    if len(df.columns) > 0:
        ws.auto_filter.ref = ws.dimensions

    for idx, col in enumerate(df.columns, 1):

        max_len = len(str(col))

        if len(df):
            sample = df[col].astype(str).head(500)
            max_len = max(
                max_len,
                sample.map(len).max()
            )

        ws.column_dimensions[
            get_column_letter(idx)
        ].width = min(
            max(max_len + 2, 12),
            45
        )


# ================================================================
# MAIN
# ================================================================

def main():

    print("=" * 76)
    print("DATASET 4 - INDIA MATERNAL MEDICATION INTELLIGENCE ENGINE")
    print("=" * 76)

    print("\nLoading Dataset 1, Dataset 2 and Dataset 3...")
    (
        d1, d2, d3,
        d1_patient, d1_preg,
        d2_patient, d2_preg, d2_visit, d2_date,
        d3_patient, d3_preg, d3_date, d3_test
    ) = load_inputs()

    print(
        f"Dataset 1: {len(d1):,} pregnancies"
    )
    print(
        f"Dataset 2: {len(d2):,} ANC visits"
    )
    print(
        f"Dataset 3: {len(d3):,} investigations"
    )

    print("\nBuilding India medication master...")
    master = medication_catalogue()

    print(
        f"Medication master entries: "
        f"{len(master)}"
    )

    print("\nBuilding allergy crosswalk...")
    allergies = allergy_crosswalk()

    print(
        f"Allergy classes: {len(allergies)}"
    )

    print("\nBuilding interaction rules...")
    interactions = interaction_rules()

    print(
        f"Interaction rules: {len(interactions)}"
    )

    print("\nBuilding evidence register...")
    sources = guideline_references()

    print(
        f"Evidence sources: {len(sources)}"
    )

    print("\nGenerating longitudinal medication events...")

    events = generate_events(
        d1, d2, d3,
        d1_patient, d1_preg,
        d2_patient, d2_preg, d2_visit, d2_date,
        d3_patient, d3_preg, d3_date, d3_test,
        master
    )

    print(
        f"Medication events generated: "
        f"{len(events):,}"
    )

    if events.empty:
        raise RuntimeError(
            "No events generated. Check Dataset 1-3 schemas and clinical trajectories."
        )

    print("\nValidating...")
    issues, allergy_violations, orphan_dates = validate(
        master,
        events,
        d1,
        d2,
        d3
    )

    status = "PASS" if not issues else "FAIL"

    # ------------------------------------------------------------
    # CSVs
    # ------------------------------------------------------------

    master_csv = os.path.join(
        OUT, "medication_master_india.csv"
    )
    events_csv = os.path.join(
        OUT, "medication_events.csv"
    )
    allergy_csv = os.path.join(
        OUT, "medication_allergy_crosswalk.csv"
    )
    interaction_csv = os.path.join(
        OUT, "medication_interaction_rules.csv"
    )
    source_csv = os.path.join(
        OUT, "medication_evidence_register.csv"
    )

    master.to_csv(master_csv, index=False)
    events.to_csv(events_csv, index=False)
    allergies.to_csv(allergy_csv, index=False)
    interactions.to_csv(interaction_csv, index=False)
    sources.to_csv(source_csv, index=False)

    # ------------------------------------------------------------
    # Excel workbook
    # ------------------------------------------------------------

    xlsx = os.path.join(
        OUT,
        "medication_treatment_india.xlsx"
    )

    with pd.ExcelWriter(
        xlsx,
        engine="openpyxl"
    ) as writer:

        master.to_excel(
            writer,
            index=False,
            sheet_name="Medication_Master"
        )

        events.to_excel(
            writer,
            index=False,
            sheet_name="Medication_Events"
        )

        allergies.to_excel(
            writer,
            index=False,
            sheet_name="Allergy_Crosswalk"
        )

        interactions.to_excel(
            writer,
            index=False,
            sheet_name="Drug_Interactions"
        )

        sources.to_excel(
            writer,
            index=False,
            sheet_name="Evidence_Register"
        )

        autosize(
            writer,
            "Medication_Master",
            master
        )

        autosize(
            writer,
            "Medication_Events",
            events
        )

        autosize(
            writer,
            "Allergy_Crosswalk",
            allergies
        )

        autosize(
            writer,
            "Drug_Interactions",
            interactions
        )

        autosize(
            writer,
            "Evidence_Register",
            sources
        )

    # ------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------

    summary = []

    summary += [
        "DATASET 4 - INDIA MATERNAL MEDICATION INTELLIGENCE ENGINE",
        "=" * 76,
        "",
        f"Generation date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"Pregnancies in Dataset 1: {len(d1):,}",
        f"ANC visits in Dataset 2: {len(d2):,}",
        f"Investigations in Dataset 3: {len(d3):,}",
        f"Medication master entries: {len(master):,}",
        f"Medication events: {len(events):,}",
        f"Allergy crosswalk entries: {len(allergies):,}",
        f"Interaction rules: {len(interactions):,}",
        f"Evidence sources: {len(sources):,}",
        "",
        "VALIDATION",
        "-" * 76,
        f"Allergy violations: {allergy_violations}",
        f"Events without ANC-date linkage: {orphan_dates}",
        f"Validation issues: {len(issues)}",
        f"Validation status: {status}",
        "",
        "MASTER DATA CONTENT",
        "-" * 76,
        "Generic name",
        "Active ingredients",
        "Salt/compound",
        "Drug class",
        "Therapeutic area",
        "Pregnancy role",
        "Trimester notes",
        "Routes",
        "Indian formulations",
        "Reference regimen/dose band",
        "Contraindications",
        "Major cautions",
        "Allergy class",
        "Cross-reactivity",
        "Common adverse effects",
        "Serious adverse effects",
        "Pregnancy-specific risks",
        "Monitoring",
        "Drug interactions",
        "Renal considerations",
        "Hepatic considerations",
        "Lactation notes",
        "India relevance",
        "NLEM status",
        "Evidence grade",
        "Evidence sources",
        "",
        "DESIGN PRINCIPLES",
        "-" * 76,
        "1. Medication master and medication-event data are separated.",
        "2. Patient medication events reference Medication_ID.",
        "3. Drug allergies are checked before medication-event creation.",
        "4. Pre-pregnancy medication history is treated as reconciliation data.",
        "5. Pregnancy-avoid medicines are retained in the master for safety flags.",
        "6. Reference regimen fields are not interpreted as patient-specific prescriptions.",
        "7. Peripartum emergency medicines are explicitly marked as non-routine ANC.",
        "8. Evidence provenance is retained at medication level.",
        "9. Indian Government sources are prioritized where available.",
        "10. Current local/state institutional protocols should override synthetic defaults.",
        "",
        "OUTPUTS",
        "-" * 76,
        master_csv,
        events_csv,
        allergy_csv,
        interaction_csv,
        source_csv,
        xlsx,
    ]

    if issues:
        summary += [
            "",
            "ISSUES",
            "-" * 76,
        ]
        summary.extend(
            f"- {issue}"
            for issue in issues
        )

    summary_text = "\n".join(summary)

    summary_path = os.path.join(
        OUT,
        "dataset4_summary.txt"
    )

    validation_path = os.path.join(
        OUT,
        "dataset4_validation_report.txt"
    )

    with open(
        summary_path,
        "w",
        encoding="utf-8"
    ) as f:
        f.write(summary_text)

    with open(
        validation_path,
        "w",
        encoding="utf-8"
    ) as f:
        f.write(summary_text)

    print("\n" + "=" * 76)
    print("DATASET 4 GENERATION COMPLETE")
    print("=" * 76)
    print(
        f"\nMedication master: {len(master)}"
    )
    print(
        f"Medication events: {len(events):,}"
    )
    print(
        f"Allergy crosswalk: {len(allergies)}"
    )
    print(
        f"Interaction rules: {len(interactions)}"
    )
    print(
        f"Evidence sources: {len(sources)}"
    )
    print(
        f"\nAllergy violations: {allergy_violations}"
    )
    print(
        f"Validation issues: {len(issues)}"
    )
    print(
        f"Validation status: {status}"
    )

    print("\n--- Files Created ---")
    print(f"Medication master: {master_csv}")
    print(f"Medication events: {events_csv}")
    print(f"Allergy crosswalk: {allergy_csv}")
    print(f"Interaction rules: {interaction_csv}")
    print(f"Evidence register: {source_csv}")
    print(f"Excel workbook: {xlsx}")
    print(f"Summary: {summary_path}")
    print(f"Validation: {validation_path}")
    print("=" * 76)


if __name__ == "__main__":
    main()