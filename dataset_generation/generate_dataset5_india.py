"""
DATASET 5 - INDIA MATERNAL NUTRITION & FOOD INTELLIGENCE ENGINE

Purpose
-------
Builds a research-grade Indian maternal nutrition dataset linked to:
    Dataset 1: Patient & Pregnancy
    Dataset 2: ANC Clinical & Vitals
    Dataset 3: Laboratory & Investigations
    Dataset 4: Medication & Treatment

This is synthetic research data, NOT a clinical diet-prescribing system.

Design
------
1. Food_Master
   Indian foods with nutrition composition, dietary classifications,
   allergens, pregnancy-safety metadata and evidence provenance.

2. Nutrition_Rulebook
   Condition/nutrient/food recommendation logic for maternal nutrition.
   Rules are decision-support metadata, not autonomous prescriptions.

3. Nutrition_Assessments
   One row per ANC nutrition assessment.

4. Food_Recommendation_Events
   Individual food/category recommendations linked to the patient,
   pregnancy, ANC visit and nutrition assessment.

5. Dietary_Patterns
   Definitions for omnivore/non-vegetarian, vegetarian, lacto-vegetarian,
   lacto-ovo vegetarian, ovo-vegetarian, vegan, eggetarian and Jain-style
   pattern flags.

6. Food_Allergen_Crosswalk
   Major allergen and avoidance metadata.

7. Nutrition_Evidence_Register
   Source/provenance registry.

Outputs
-------
datasets/dataset5_nutrition_food/
    food_master_india.csv
    nutrition_rulebook.csv
    nutrition_assessments.csv
    food_recommendation_events.csv
    dietary_patterns.csv
    food_allergen_crosswalk.csv
    nutrition_evidence_register.csv
    nutrition_food_india.xlsx
    dataset5_summary.txt
    dataset5_validation_report.txt

Evidence architecture
---------------------
A = Indian government / ICMR-NIN / MoHFW / NHM
B = WHO / authoritative international guidance
C = established nutrition reference used for metadata where Indian
    composition/guidance is not directly specified.

Important
---------
Food composition values are reference values and can vary by cultivar,
brand, recipe, cooking method and serving size. IFCT values are generally
for the sampled food form, so cooked recipes must not be treated as exact
IFCT analytical equivalents.

Clinical decisions remain with qualified clinicians/dietitians.
"""

import os
import re
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
from openpyxl.utils import get_column_letter


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
D4 = os.path.join(
    PROJECT, "datasets", "dataset4_medication_treatment",
    "medication_events.csv"
)

OUT = os.path.join(PROJECT, "datasets", "dataset5_nutrition_food")
os.makedirs(OUT, exist_ok=True)

SEED = 20261008
rng = np.random.default_rng(SEED)


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
            f"Available: {list(df.columns)}"
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
    return str(x).strip().lower() in {
        "true", "1", "yes", "y", "positive"
    }


def split_terms(x):
    return [
        t.strip().lower()
        for t in re.split(r"[;,|/]+", txt(x))
        if t.strip()
    ]


def safe_date(x):
    try:
        return pd.to_datetime(x)
    except Exception:
        return pd.NaT


# ================================================================
# FOOD MASTER
# ================================================================

def food_catalogue():
    rows = []

    def add(
        food_id,
        food_name,
        regional_names,
        food_group,
        sub_group,
        diet_types,
        vegan,
        vegetarian,
        eggetarian,
        jain_compatible,
        common_regions,
        serving_g,
        kcal,
        carb_g,
        protein_g,
        fat_g,
        fibre_g,
        calcium_mg,
        iron_mg,
        folate_mcg,
        b12_mcg,
        vit_c_mg,
        vit_d_iu,
        sodium_mg,
        potassium_mg,
        gi_category,
        glycemic_load_category,
        allergens,
        pregnancy_safety,
        preparation_notes,
        source,
        source_grade="A",
        source_notes="Reference composition; recipe/brand variation applies",
        tags=""
    ):
        rows.append({
            "Food_ID": food_id,
            "Food_Name": food_name,
            "Regional_Names": regional_names,
            "Food_Group": food_group,
            "Sub_Group": sub_group,
            "Diet_Types": diet_types,
            "Vegan": vegan,
            "Vegetarian": vegetarian,
            "Eggetarian": eggetarian,
            "Jain_Compatible": jain_compatible,
            "Common_Indian_Regions": common_regions,
            "Reference_Serving_g": serving_g,
            "Energy_kcal": kcal,
            "Carbohydrate_g": carb_g,
            "Protein_g": protein_g,
            "Fat_g": fat_g,
            "Fibre_g": fibre_g,
            "Calcium_mg": calcium_mg,
            "Iron_mg": iron_mg,
            "Folate_mcg": folate_mcg,
            "Vitamin_B12_mcg": b12_mcg,
            "Vitamin_C_mg": vit_c_mg,
            "Vitamin_D_IU": vit_d_iu,
            "Sodium_mg": sodium_mg,
            "Potassium_mg": potassium_mg,
            "GI_Category": gi_category,
            "Glycemic_Load_Category": glycemic_load_category,
            "Major_Allergens": allergens,
            "Pregnancy_Safety": pregnancy_safety,
            "Preparation_Notes": preparation_notes,
            "Evidence_Source": source,
            "Evidence_Grade": source_grade,
            "Source_Notes": source_notes,
            "Nutrition_Tags": tags,
        })

    # The nutrient values below are intentionally rounded reference values.
    # The catalogue is designed for relational modelling and recommendation
    # logic, not for replacing a laboratory-verified food composition database.

    foods = [
        ("F001","Rice, raw","Chawal","Cereals","Rice","Vegan", "Yes","Yes","No","Yes",
         "Pan-India",100,365,80,7,0.7,1,28,1.8,8,0,0,0,5,115,"High","High","","Generally safe",
         "Cook thoroughly; portion size matters for glycaemic management","ICMR-NIN IFCT 2017","A",
         "Raw-food composition reference; cooked yield changes nutrient density","cereal;staple"),
        ("F002","Brown rice, raw","Brown chawal","Cereals","Whole grain","Vegan","Yes","Yes","No","Yes",
         "Pan-India",100,367,77,7.5,2.7,3.5,33,1.8,20,0,0,0,7,223,"Medium","Medium","","Generally safe",
         "Prefer varied whole grains where tolerated","ICMR-NIN IFCT 2017","A","","wholegrain;fibre"),
        ("F003","Wheat flour, whole","Atta","Cereals","Whole grain","Vegan","Yes","Yes","No","Yes",
         "Pan-India",100,341,69,12.1,1.7,10.7,48,4.6,36,0,0,0,2,300,"Medium","Medium","Gluten","Generally safe",
         "Cook as roti/chapati; avoid raw flour","ICMR-NIN IFCT 2017","A","","wholegrain;iron;fibre"),
        ("F004","Ragi, raw","Finger millet; Nachni; Kezhvaragu","Cereals","Millet","Vegan","Yes","Yes","No","Yes",
         "South/West/Central India",100,320,72,7.3,1.3,11.5,344,3.9,35,0,1,0,11,408,"Medium","Medium","","Generally safe",
         "Useful calcium-rich grain; preparation changes glycaemic response","ICMR-NIN IFCT 2017","A","","millet;calcium;fibre"),
        ("F005","Oats, whole grain","Oats","Cereals","Whole grain","Vegan","Yes","Yes","No","Yes",
         "Pan-India",100,389,66,16.9,6.9,10.6,54,4.7,56,0,0,0,2,429,"Medium","Medium","Gluten/cross-contamination possible","Generally safe",
         "Choose certified gluten-free product if clinically required","ICMR-NIN IFCT 2017","A","","wholegrain;fibre;protein"),
        ("F006","Jowar, raw","Sorghum; Jonna; Cholam","Cereals","Millet","Vegan","Yes","Yes","No","Yes",
         "West/South/Central India",100,329,72.4,10.4,3.1,9.7,25,4.1,39,0,0,0,2,363,"Medium","Medium","","Generally safe",
         "Cook thoroughly; useful cereal diversity","ICMR-NIN IFCT 2017","A","","millet;fibre;protein"),
        ("F007","Bajra, raw","Pearl millet; Bajra; Kambu","Cereals","Millet","Vegan","Yes","Yes","No","Yes",
         "North/West/South India",100,361,67.5,11.6,5,11.5,42,8,45,0,0,0,10,365,"Medium","Medium","","Generally safe",
         "Iron-rich cereal; portioning remains important in GDM","ICMR-NIN IFCT 2017","A","","millet;iron;fibre"),
        ("F008","Barley, raw","Jau","Cereals","Whole grain","Vegan","Yes","Yes","No","Yes",
         "North/West India",100,352,64.8,11.5,1.3,17.3,33,3.6,19,0,0,0,4,452,"Low-Medium","Medium","Gluten","Generally safe",
         "Not gluten-free","ICMR-NIN IFCT 2017","A","","wholegrain;fibre"),
        ("F009","Red lentil, raw","Masoor dal","Pulses","Lentil","Vegan","Yes","Yes","No","Yes",
         "Pan-India",100,343,60,24,1.1,10.8,56,7.5,479,0,4,0,13,677,"Low","Low","None major","Generally safe",
         "Cook thoroughly","ICMR-NIN IFCT 2017","A","","pulse;protein;iron;folate"),
        ("F010","Green gram, raw","Moong dal; Pesara","Pulses","Pulse","Vegan","Yes","Yes","No","Yes",
         "Pan-India",100,334,56,24,1.2,8.8,124,8,625,0,4,0,15,1246,"Low","Low","None major","Generally safe",
         "Cook thoroughly; sprouts require food-safety care","ICMR-NIN IFCT 2017","A","","pulse;protein;folate;iron"),
        ("F011","Chickpea, raw","Chana; Kabuli chana","Pulses","Pulse","Vegan","Yes","Yes","No","Yes",
         "Pan-India",100,360,60,18.5,5.5,17.4,105,6.2,557,0,7,0,24,718,"Low-Medium","Medium","None major","Generally safe",
         "Soak and cook thoroughly","ICMR-NIN IFCT 2017","A","","pulse;protein;iron;folate;fibre"),
        ("F012","Kidney beans, raw","Rajma","Pulses","Pulse","Vegan","Yes","Yes","No","Yes",
         "North India",100,333,60,24,1.1,24.9,143,5.1,394,0,4,0,24,1406,"Low-Medium","Medium","None major","Generally safe when fully cooked",
         "Never consume raw/undercooked kidney beans","ICMR-NIN IFCT 2017","A","","pulse;protein;fibre"),
        ("F013","Soybean, raw","Soybean; Soy","Pulses","Soy","Vegan","Yes","Yes","No","Yes",
         "Pan-India",100,446,30,43.2,19.9,9.3,240,15.7,375,0,6,0,2,1797,"Low","Low","Soy","Generally safe",
         "Cook adequately; allergy status required","ICMR-NIN IFCT 2017","A","","soy;protein;iron"),
        ("F014","Peanut","Groundnut; Moongphali","Nuts/Seeds","Nut/legume","Vegan","Yes","Yes","No","Yes",
         "Pan-India",30,170,5,7.7,14.8,2.6,28,1.4,72,0,0,0,2,202,"Low","Low","Peanut","Generally safe if no allergy",
         "Avoid if peanut allergy; choose hygienic preparations","ICMR-NIN IFCT 2017","A","","protein;healthy-fat"),
        ("F015","Almond","Badam","Nuts/Seeds","Tree nut","Vegan","Yes","Yes","No","Yes",
         "Pan-India",30,174,6.5,6.3,15,3.7,75,1.1,14,0,0,0,0,219,"Low","Low","Tree nuts","Generally safe if no allergy",
         "Check allergy history","ICMR-NIN IFCT 2017","A","","nut;calcium;healthy-fat"),
        ("F016","Sesame seeds","Til","Nuts/Seeds","Seed","Vegan","Yes","Yes","No","Yes",
         "Pan-India",30,173,7,5.2,15,3.6,351,4.4,29,0,0,0,2,123,"Low","Low","Sesame","Generally safe if no allergy",
         "Energy dense; portion accordingly","ICMR-NIN IFCT 2017","A","","seed;calcium;iron"),
        ("F017","Milk, cow","Doodh; Paal","Dairy","Milk","Lacto-vegetarian","No","Yes","Yes","No",
         "Pan-India",200,122,9.6,6.4,6.6,0,240,0.1,10,0.9,2,80,100,300,"Low","Low","Milk","Generally safe if pasteurized",
         "Use pasteurized milk; lactose tolerance varies","ICMR-NIN IFCT 2017","A","","dairy;calcium;protein;B12"),
        ("F018","Curd, plain","Dahi; Thayir","Dairy","Fermented dairy","Lacto-vegetarian","No","Yes","Yes","No",
         "Pan-India",200,122,9.4,7,6.6,0,260,0.1,14,0.8,2,80,100,300,"Low","Low","Milk","Generally safe if pasteurized",
         "Use hygienically prepared/pasteurized dairy","ICMR-NIN IFCT 2017","A","","dairy;calcium;protein"),
        ("F019","Paneer","Indian cottage cheese","Dairy","Cheese","Lacto-vegetarian","No","Yes","Yes","No",
         "Pan-India",50,132,1.5,9,10,0,200,0.7,6,0.7,0,0,20,70,"Low","Low","Milk","Generally safe if pasteurized",
         "Use fresh, pasteurized product; calorie dense","ICMR-NIN IFCT 2017","A","","dairy;protein;calcium"),
        ("F020","Egg, whole","Anda","Egg","Egg","Eggetarian","No","No","Yes","No",
         "Pan-India",50,72,0.4,6.3,4.8,0,25,0.9,24,1,0,44,62,63,"Low","Low","Egg","Generally safe when fully cooked",
         "Avoid raw/undercooked egg; food safety is critical","ICMR-NIN IFCT 2017","A","","egg;protein;B12"),
        ("F021","Chicken, cooked","Murgi; Chicken","Animal protein","Poultry","Non-vegetarian","No","No","Yes","No",
         "Pan-India",100,165,0,31,3.6,0,15,1.3,6,0.3,0,5,74,256,"Low","Low","","Generally safe when thoroughly cooked",
         "Avoid raw/undercooked poultry; avoid cross-contamination","ICMR-NIN IFCT 2017","A","","animal-protein;iron;B12"),
        ("F022","Fish, rohu, cooked","Rohu","Animal protein","Fish","Non-vegetarian","No","No","Yes","No",
         "East/North/Central India",100,150,0,26,5,0,35,1.5,15,2.5,0,120,60,300,"Low","Low","Fish","Generally safe when thoroughly cooked",
         "Choose low-mercury fish; cook thoroughly","ICMR-NIN IFCT 2017 + WHO food safety principles","A","","fish;protein;B12;vitaminD"),
        ("F023","Sardine","Sardine; Mathi","Animal protein","Oily fish","Non-vegetarian","No","No","Yes","No",
         "Coastal India",100,208,0,25,11,0,382,2.9,10,8.9,0,200,118,490,"Low","Low","Fish","Generally safe when thoroughly cooked",
         "Oily fish can contribute vitamin D; choose safe, cooked fish","ICMR-NIN IFCT 2017 + WHO food safety principles","A","","fish;protein;vitaminD;calcium"),
        ("F024","Spinach, raw","Palak; Keerai","Vegetables","Leafy green","Vegan","Yes","Yes","No","Yes",
         "Pan-India",100,23,3.6,2.9,0.4,2.2,99,2.7,194,0,28,0,79,558,"Low","Low","","Generally safe when washed/cooked",
         "Wash thoroughly; cooking affects nutrient density","ICMR-NIN IFCT 2017","A","","leafy-green;folate;iron"),
        ("F025","Amaranth leaves","Chaulai; Thotakura","Vegetables","Leafy green","Vegan","Yes","Yes","No","Yes",
         "Pan-India",100,23,4,2.5,0.3,2.1,215,2.3,85,0,43,0,20,611,"Low","Low","","Generally safe when washed/cooked",
         "Good leafy-green diversity","ICMR-NIN IFCT 2017","A","","leafy-green;calcium;folate"),
        ("F026","Drumstick leaves","Moringa leaves; Murungai keerai","Vegetables","Leafy green","Vegan","Yes","Yes","No","Yes",
         "South/Central India",100,64,8.3,9.4,1.4,2,440,7,40,0,220,0,9,259,"Low","Low","","Generally safe as food",
         "Use normal culinary quantities; wash thoroughly","ICMR-NIN IFCT 2017","A","","leafy-green;calcium;iron"),
        ("F027","Carrot","Gajar","Vegetables","Root","Vegan","Yes","Yes","No","Yes",
         "Pan-India",100,48,10,0.9,0.2,3.2,33,0.6,19,0,5,0,42,320,"Low","Low","","Generally safe",
         "Wash and prepare hygienically","ICMR-NIN IFCT 2017","A","","vegetable;vitaminA"),
        ("F028","Tomato","Tamatar; Thakkali","Vegetables","Fruit vegetable","Vegan","Yes","Yes","No","Yes",
         "Pan-India",100,20,3.6,0.9,0.2,1.2,48,0.4,15,0,24,0,42,237,"Low","Low","","Generally safe",
         "Wash before use","ICMR-NIN IFCT 2017","A","","vegetable;vitaminC"),
        ("F029","Guava","Peru; Koyya","Fruit","Tropical fruit","Vegan","Yes","Yes","No","Yes",
         "Pan-India",100,68,14.3,2.6,0.9,5.4,18,0.3,49,0,228,0,2,417,"Low","Low","","Generally safe",
         "Wash thoroughly; whole fruit preferred to juice","ICMR-NIN IFCT 2017","A","","fruit;vitaminC;fibre"),
        ("F030","Orange","Santra; Naranga","Fruit","Citrus","Vegan","Yes","Yes","No","Yes",
         "Pan-India",130,61,15,1.2,0.2,3.1,52,0.1,39,0,69,0,1,237,"Low","Low","","Generally safe",
         "Whole fruit preferable to juice for fibre","ICMR-NIN IFCT 2017","A","","fruit;vitaminC"),
        ("F031","Papaya, ripe","Papita","Fruit","Tropical fruit","Vegan","Yes","Yes","No","Yes",
         "Pan-India",100,43,9.8,0.5,0.2,1.8,20,0.4,38,0,61,0,8,182,"Low","Low","","Ripe papaya as normal food is generally considered acceptable",
         "Food-safety hygiene; distinguish ripe fruit from unripe papaya preparations","ICMR-NIN IFCT 2017 + pregnancy food-safety references","B","","fruit;fibre;vitaminC"),
        ("F032","Banana","Kela; Vazhai pazham","Fruit","Tropical fruit","Vegan","Yes","Yes","No","Yes",
         "Pan-India",100,89,22.8,1.1,0.3,2.6,8,0.3,20,0,9,0,1,358,"Medium","Medium","","Generally safe",
         "Portion and meal pairing matter for GDM","ICMR-NIN IFCT 2017","A","","fruit;potassium"),
        ("F033","Apple","Seb; Safarchand","Fruit","Temperate fruit","Vegan","Yes","Yes","No","Yes",
         "Pan-India",150,78,20.5,0.4,0.2,3,9,0.2,4,0,8,0,2,161,"Low","Low","","Generally safe",
         "Wash well; whole fruit preferred to juice","ICMR-NIN IFCT 2017","A","","fruit;fibre"),
        ("F034","Amla","Indian gooseberry; Nellikai","Fruit","Tropical fruit","Vegan","Yes","Yes","No","Yes",
         "Pan-India",100,44,10.2,0.5,0.1,4.3,25,0.3,6,0,600,0,1,198,"Low","Low","","Generally safe",
         "Wash thoroughly; preparation may add sugar/salt","ICMR-NIN IFCT 2017","A","","fruit;vitaminC"),
        ("F035","Sweet potato","Shakarkandi; Sakkarai valli kizhangu","Vegetables","Tuber","Vegan","Yes","Yes","No","Yes",
         "Pan-India",100,86,20,1.6,0.1,3,30,0.6,6,0,22,0,55,337,"Medium","Medium","","Generally safe",
         "Boiled/roasted preparation and portion size matter for glycaemic control","ICMR-NIN IFCT 2017","A","","tuber;fibre"),
        ("F036","Potato","Aloo; Urulai kizhangu","Vegetables","Tuber","Vegan","Yes","Yes","No","Yes",
         "Pan-India",100,97,22.6,1.7,0.1,1.6,10,0.7,15,0,11,0,6,407,"High","High","","Generally safe",
         "Portioning and preparation matter for GDM","ICMR-NIN IFCT 2017","A","","tuber;highGI"),
        ("F037","Bottle gourd","Lauki; Sorakkai","Vegetables","Gourd","Vegan","Yes","Yes","No","Yes",
         "Pan-India",100,15,3.5,0.6,0.1,0.6,20,0.4,6,0,10,0,2,150,"Low","Low","","Generally safe",
         "Use fresh, non-bitter produce; discard unusually bitter gourds","ICMR-NIN IFCT 2017 + food safety","A","","vegetable;lowenergy"),
        ("F038","Okra","Bhindi; Vendakkai","Vegetables","Pod vegetable","Vegan","Yes","Yes","No","Yes",
         "Pan-India",100,33,7.5,1.9,0.2,3.2,82,0.6,60,0,23,0,7,299,"Low","Low","","Generally safe",
         "Wash and cook hygienically","ICMR-NIN IFCT 2017","A","","vegetable;fibre;folate"),
        ("F039","Broccoli","Broccoli","Vegetables","Cruciferous","Vegan","Yes","Yes","No","Yes",
         "Urban/Pan-India",100,35,6.6,2.8,0.4,2.6,47,0.7,108,0,89,0,41,316,"Low","Low","","Generally safe",
         "Cook adequately; vary vegetables","ICMR-NIN IFCT 2017","A","","vegetable;folate;vitaminC"),
        ("F040","Lemon","Nimbu; Elumichai","Fruit","Citrus","Vegan","Yes","Yes","No","Yes",
         "Pan-India",50,14,4.5,0.4,0.1,1.4,15,0.1,3,0,25,0,1,70,"Low","Low","","Generally safe",
         "Useful vitamin C food; does not replace supplements","ICMR-NIN IFCT 2017","A","","vitaminC"),
        ("F041","Coconut, fresh","Nariyal; Thengai","Nuts/Seeds","Coconut","Vegan","Yes","Yes","No","Yes",
         "Coastal/South India",50,177,7.5,1.7,17.7,3.3,8,1.7,13,0,1,0,9,176,"Low","Low","","Generally safe",
         "Energy dense; portion according to total diet","ICMR-NIN IFCT 2017","A","","healthy-fat"),
        ("F042","Chia seeds","Chia","Nuts/Seeds","Seed","Vegan","Yes","Yes","No","Yes",
         "Pan-India",20,97,8.4,3.3,6.1,6.8,126,1.5,10,0,1,0,4,98,"Low","Low","None major","Generally safe as food",
         "Hydrate appropriately; food rather than supplement framing","Standard food composition references","B","","seed;fibre"),
        ("F043","Flaxseed","Alsi; Agase","Nuts/Seeds","Seed","Vegan","Yes","Yes","No","Yes",
         "Pan-India",20,107,5.8,3.7,8.4,5.4,52,1.1,17,0,1,0,6,164,"Low","Low","None major","Generally safe as food",
         "Use ground/food form; avoid excessive supplemental dosing","Standard food composition references","B","","seed;omega3;fibre"),
        ("F044","Jaggery","Gur; Vellam","Sugar/Sweetener","Traditional sweetener","Vegan","Yes","Yes","No","Yes",
         "Pan-India",20,76,19,0.1,0,0,16,2.2,7,0,0,0,3,26,"High","High","","Limit, especially in GDM",
         "Not a medicinal iron treatment; sugar contribution matters","ICMR-NIN IFCT 2017","A","","sugar;iron-myth-risk"),
        ("F045","Dates","Khajoor","Fruit","Dried fruit","Vegan","Yes","Yes","No","Yes",
         "Pan-India",30,85,22,0.7,0.1,2.1,20,0.5,5,0,0,0,2,200,"High","Medium","None major","Generally safe",
         "Concentrated carbohydrate; portion appropriately in GDM","Standard food composition references","B","","dried-fruit;carbohydrate"),
        ("F046","Idli","Idli","Mixed dish","Fermented rice-legume","Vegan","Yes","Yes","No","Yes",
         "South India",120,170,33,5,1.2,2,30,1.2,25,0,1,0,250,100,"Medium","Medium","None major","Generally safe when hygienically prepared",
         "Recipe-dependent composition; pair with protein/vegetables","Recipe-derived estimate informed by Indian food composition data","B","","traditional;fermented"),
        ("F047","Dosa","Dosa","Mixed dish","Fermented rice-legume","Vegan","Yes","Yes","No","Yes",
         "South India",100,170,28,4,4,1.5,25,1,20,0,1,0,300,90,"Medium-High","Medium","None major","Generally safe when hygienically prepared",
         "Oil quantity varies substantially; recipe matters","Recipe-derived estimate informed by Indian food composition data","B","","traditional;fermented"),
        ("F048","Sambar","Sambar","Mixed dish","Pulse-vegetable","Vegan","Yes","Yes","No","Yes",
         "South India",200,130,18,6,4,5,80,2,60,0,25,0,500,300,"Low-Medium","Low","None major","Generally safe",
         "Sodium varies with recipe","Recipe-derived estimate informed by Indian food composition data","B","","pulse;vegetable"),
        ("F049","Roti/chapati","Roti; Chapati","Mixed dish","Wheat-based","Vegan","Yes","Yes","No","Yes",
         "Pan-India",60,150,30,5,2,4,30,1.8,20,0,0,0,120,120,"Medium","Medium","Gluten","Generally safe",
         "Recipe and flour extraction alter composition","Recipe-derived estimate informed by Indian food composition data","B","","wholegrain;staple"),
        ("F050","Khichdi","Khichdi; Pongal-style","Mixed dish","Cereal-pulse","Vegan/Vegetarian","Yes","Yes","No","Yes",
         "Pan-India",250,260,43,9,6,5,70,2.5,80,0,5,0,400,300,"Medium","Medium","None major","Generally safe",
         "Recipe-dependent; add vegetables/protein as appropriate","Recipe-derived estimate informed by Indian food composition data","B","","traditional;comfort-food"),
        ("F051","Vegetable upma","Upma","Mixed dish","Semolina/vegetable","Vegan","Yes","Yes","No","Yes",
         "South/West India",200,260,42,7,7,4,45,2.2,35,0,12,0,450,220,"Medium","Medium","Gluten","Generally safe",
         "Oil and sodium vary by recipe","Recipe-derived estimate informed by Indian food composition data","B","","traditional;vegetable"),
        ("F052","Besan chilla","Besan chilla","Mixed dish","Pulse-based","Vegan","Yes","Yes","No","Yes",
         "North/West India",120,220,24,9,8,5,60,2.4,120,0,1,0,300,300,"Low-Medium","Low","None major","Generally safe",
         "Useful pulse-based protein option","Recipe-derived estimate informed by Indian food composition data","B","","pulse;protein"),
        ("F053","Paneer tikka","Paneer tikka","Mixed dish","Dairy-based","Lacto-vegetarian","No","Yes","Yes","No",
         "Pan-India",150,300,20,20,18,2,300,1,15,1,3,0,500,180,"Low","Low","Milk","Generally safe if pasteurized and thoroughly cooked",
         "Restaurant sodium/oil can be high","Recipe-derived estimate informed by Indian food composition data","B","","dairy;protein"),
        ("F054","Chole","Chana masala; Chole","Mixed dish","Pulse-based","Vegan","Yes","Yes","No","Yes",
         "North India",200,300,42,12,8,10,110,4,180,0,10,0,700,500,"Low-Medium","Medium","None major","Generally safe",
         "Sodium and oil vary; pair with whole grains/vegetables","Recipe-derived estimate informed by Indian food composition data","B","","pulse;protein;fibre"),
        ("F055","Rajma curry","Rajma","Mixed dish","Pulse-based","Vegan","Yes","Yes","No","Yes",
         "North India",200,280,42,12,7,10,130,4,150,0,8,0,700,500,"Low-Medium","Medium","None major","Generally safe",
         "Fully cook kidney beans; sodium varies","Recipe-derived estimate informed by Indian food composition data","B","","pulse;protein;fibre"),
        ("F056","Idli + sambar","Idli sambar","Meal","Composite meal","Vegan","Yes","Yes","No","Yes",
         "South India",320,300,48,11,5,6,100,2.5,80,0,15,0,700,400,"Medium","Medium","None major","Generally safe when hygienically prepared",
         "Useful balanced plant-based meal; recipe varies","Recipe-derived estimate informed by Indian food composition data","B","","meal;traditional;protein"),
        ("F057","Rice + dal","Dal chawal","Meal","Composite meal","Vegan","Yes","Yes","No","Yes",
         "Pan-India",350,390,70,15,6,8,100,3.5,180,0,5,0,500,450,"Medium-High","Medium","None major","Generally safe",
         "Portion rice and increase vegetable content when glycaemic control is needed","Recipe-derived estimate informed by Indian food composition data","B","","meal;plant-protein"),
        ("F058","Curd rice","Thayir sadam","Meal","Dairy-cereal","Lacto-vegetarian","No","Yes","Yes","No",
         "South India",300,330,50,9,9,1,180,1,30,0.8,2,0,500,180,"Medium-High","Medium","Milk","Generally safe if dairy is pasteurized",
         "Sodium and rice quantity vary","Recipe-derived estimate informed by Indian food composition data","B","","meal;dairy"),
        ("F059","Fish curry + rice","Meen curry sadam","Meal","Fish-cereal","Non-vegetarian","No","No","Yes","No",
         "Coastal India",350,430,48,25,14,2,100,2,45,3,5,100,700,500,"Medium-High","Medium","Fish","Generally safe when fish is thoroughly cooked",
         "Fish species and curry salt/oil vary","Recipe-derived estimate informed by Indian food composition data","B","","meal;fish;protein"),
        ("F060","Chicken curry + roti","Chicken roti meal","Meal","Poultry-wheat","Non-vegetarian","No","No","Yes","No",
         "Pan-India",350,480,45,30,18,5,100,3,70,1.5,5,0,700,500,"Medium","Medium","Gluten","Generally safe when thoroughly cooked",
         "Oil and sodium vary substantially","Recipe-derived estimate informed by Indian food composition data","B","","meal;protein"),
    ]

    for f in foods:
        add(*f)

    return pd.DataFrame(rows)


# ================================================================
# DIETARY PATTERNS
# ================================================================

def dietary_patterns():
    rows = [
        ("DP-001","Omnivore / Non-vegetarian",
         "May include plant foods, dairy, eggs, fish and meat",
         "Animal-source foods allowed", "No", "Yes", "Yes", "No",
         "Ask about meat/fish/egg frequency; food safety remains essential"),
        ("DP-002","Vegetarian",
         "Broad Indian vegetarian pattern; dairy and/or eggs depend on individual practice",
         "No meat/fish; eggs may vary", "No", "Yes", "Variable", "Variable",
         "Do not assume lacto-vegetarian versus ovo-vegetarian without asking"),
        ("DP-003","Lacto-vegetarian",
         "Plant foods + dairy; excludes eggs, meat and fish",
         "Dairy permitted", "No", "Yes", "No", "No",
         "Pay attention to iron, B12 and protein adequacy"),
        ("DP-004","Lacto-ovo vegetarian",
         "Plant foods + dairy + eggs; excludes meat and fish",
         "Dairy and eggs permitted", "No", "Yes", "Yes", "No",
         "Often supports multiple protein sources"),
        ("DP-005","Ovo-vegetarian",
         "Plant foods + eggs; excludes dairy, meat and fish",
         "Eggs permitted", "No", "Yes", "Yes", "No",
         "Calcium/B12 sources need explicit assessment"),
        ("DP-006","Vegan",
         "Excludes meat, fish, eggs, dairy and other animal-derived foods",
         "Plant-only pattern", "Yes", "Yes", "No", "No",
         "Explicit B12, calcium, iron, iodine, protein and vitamin D assessment is important"),
        ("DP-007","Eggetarian",
         "Vegetarian pattern that includes eggs; dairy may or may not be used",
         "Eggs permitted; meat/fish excluded", "No", "Yes", "Yes", "Variable",
         "Clarify dairy use rather than assuming"),
        ("DP-008","Jain-style vegetarian",
         "Plant-based vegetarian pattern with additional exclusions varying by individual/community",
         "Typically excludes meat, fish, eggs; root vegetables may be excluded",
         "No", "Yes", "No", "Yes",
         "Must be individualized; do not assume every Jain patient follows identical exclusions"),
        ("DP-009","Pescatarian",
         "Plant foods + fish/seafood; no meat/poultry",
         "Fish/seafood permitted", "No", "Variable", "Yes", "No",
         "Ask about fish species and local food safety"),
        ("DP-010","Regional/traditional mixed diet",
         "Diet defined by home/regional pattern rather than a standard label",
         "Individual assessment required", "Variable", "Variable", "Variable", "Variable",
         "Use food-level exclusions and preferences rather than label alone"),
    ]
    return pd.DataFrame(rows, columns=[
        "Diet_Pattern_ID","Diet_Pattern","Definition","Inclusion_Rule",
        "Vegan","Vegetarian","Eggs_Allowed","Jain_Flag","Clinical_Nutrition_Note"
    ])


# ================================================================
# RULEBOOK
# ================================================================

def nutrition_rulebook():
    rows = [
        ("NR-001","Routine pregnancy","Dietary diversity",
         "All trimesters","Increase dietary diversity and adequate energy/protein intake",
         "Whole grains; pulses; vegetables; fruits; nuts/seeds; appropriate animal foods",
         "Highly processed foods high in sodium/free sugars/unhealthy fats",
         "All diet patterns","WHO pregnancy nutrition counselling","A/B"),
        ("NR-002","Anaemia","Iron + vitamin C",
         "All trimesters","Prioritize iron-rich foods and vitamin-C-rich foods alongside clinician-directed iron therapy",
         "Pulses; millets; leafy greens; legumes; meat/fish/eggs if permitted; amla/citrus/guava",
         "Do not represent food alone as treatment for clinically significant anaemia",
         "All diet patterns","WHO IFA + ICMR-NIN food composition","A/B"),
        ("NR-003","Low calcium intake","Calcium",
         "All trimesters","Increase calcium-rich foods while respecting supplement/medication timing",
         "Milk; curd; paneer; ragi; sesame; calcium-rich greens; fortified foods when appropriate",
         "Avoid claiming any one food prevents pre-eclampsia",
         "Vegetarian/omnivore/vegan adapted","WHO calcium guidance + Indian nutrition sources","A/B"),
        ("NR-004","GDM / elevated glucose","Carbohydrate quality + fibre",
         "All trimesters","Distribute carbohydrate across meals and emphasize fibre/protein-rich foods",
         "Whole grains; pulses; non-starchy vegetables; whole fruit; nuts/seeds; appropriate protein",
         "Sugary drinks; sweets; large refined-carbohydrate portions",
         "All diet patterns","WHO healthy diet principles + diabetes nutrition practice","B"),
        ("NR-005","Hypertension","Sodium-aware balanced diet",
         "All trimesters","Emphasize minimally processed foods and moderate sodium exposure",
         "Vegetables; fruits; pulses; whole grains; unsalted nuts/seeds; fresh protein",
         "Highly salted packaged foods, pickles/papad in excess, processed meats",
         "All diet patterns","WHO healthy diet principles","B"),
        ("NR-006","Constipation","Fibre + fluids",
         "All trimesters","Increase fibre-containing foods and adequate fluid intake if clinically appropriate",
         "Whole grains; pulses; vegetables; fruit; seeds",
         "Abrupt extreme fibre increases without adequate fluids",
         "All diet patterns","WHO healthy diet principles","B"),
        ("NR-007","Nausea/vomiting","Small frequent meals",
         "First trimester / symptom-driven","Use tolerable small meals and hydration; escalate clinically when severe",
         "Simple tolerated meals; dry foods; ginger-containing foods where appropriate",
         "Large greasy meals and individual nausea triggers",
         "All diet patterns","WHO ANC symptom counselling principles","B"),
        ("NR-008","Vegan pregnancy","B12/protein/calcium/iron/iodine/vitamin D",
         "All trimesters","Assess nutrient adequacy explicitly and use fortified foods/supplements under clinical guidance",
         "Pulses; soy; nuts/seeds; whole grains; fortified plant beverages; vegetables",
         "Assuming plant-only diet automatically meets B12/calcium/iodine needs",
         "Vegan","Nutrition evidence + WHO healthy diet principles","B"),
        ("NR-009","Vegetarian pregnancy","Iron/B12/protein",
         "All trimesters","Use diverse pulses, dairy/eggs where permitted and iron-rich plant foods",
         "Dal; beans; soy; dairy; eggs if allowed; millets; leafy greens",
         "Over-reliance on refined grains and sweets",
         "Vegetarian variants","ICMR-NIN food composition + WHO nutrition counselling","A/B"),
        ("NR-010","Underweight / inadequate gain","Energy + protein density",
         "All trimesters","Increase nutrient-dense energy/protein intake with clinical assessment",
         "Dairy/fortified alternatives; pulses; soy; nuts/seeds; eggs/meat/fish if permitted",
         "Low-nutrient high-sugar foods as the primary strategy",
         "All diet patterns","WHO nutrition counselling","B"),
        ("NR-011","Excessive gestational weight gain","Energy quality + activity context",
         "All trimesters","Review total dietary pattern, portions and clinical activity advice",
         "Vegetables; whole grains; pulses; lean protein; whole fruit",
         "Sugar-sweetened beverages; frequent energy-dense processed foods",
         "All diet patterns","WHO nutrition counselling","B"),
        ("NR-012","Medication timing","Food-drug interaction",
         "All trimesters","Coordinate diet timing with medication instructions",
         "Food plans that respect iron/calcium/levothyroxine separation where applicable",
         "Taking interacting supplements/foods together when separation is required",
         "All diet patterns","Dataset 4 medication interaction layer","A/B"),
        ("NR-013","Food allergy","Allergen avoidance",
         "All trimesters","Exclude documented allergen and preserve nutrient adequacy with substitutes",
         "Non-allergenic alternatives based on nutrient target",
         "Documented allergen or cross-contact risk",
         "All diet patterns","Food allergy safety principle","B"),
        ("NR-014","Food safety","Pregnancy food safety",
         "All trimesters","Use pasteurized, thoroughly cooked and hygienically prepared foods",
         "Freshly cooked foods; pasteurized dairy; thoroughly cooked eggs/meat/fish",
         "Raw/undercooked animal foods; unsafe unpasteurized foods; contaminated produce",
         "All diet patterns","WHO healthy diet/food safety principles","B"),
        ("NR-015","Iron medication","Iron absorption",
         "All trimesters","Separate iron from calcium and other known absorption-interfering agents as directed",
         "Vitamin-C-rich meal components may support dietary iron absorption",
         "Taking iron with calcium when separation is advised",
         "All diet patterns","Dataset 4 interaction layer + WHO IFA","A/B"),
        ("NR-016","Levothyroxine","Medication-food timing",
         "All trimesters","Keep iron/calcium supplements separated according to medication instructions",
         "Consistent medication timing and clear counselling",
         "Simultaneous iron/calcium dosing with levothyroxine",
         "All diet patterns","Dataset 4 interaction layer","A/B"),
        ("NR-017","GDM + vegetarian","Protein + carbohydrate quality",
         "All trimesters","Pair carbohydrate foods with pulses/dairy/egg/soy and vegetables where allowed",
         "Dal; chana; soy; curd; paneer; eggs if allowed; vegetables",
         "Large portions of refined cereal without protein/fibre",
         "Vegetarian variants","Nutrition decision-support rule","B"),
        ("NR-018","GDM + vegan","Protein + carbohydrate quality",
         "All trimesters","Pair carbohydrate foods with legumes/soy/nuts/seeds and non-starchy vegetables",
         "Dal; chana; soy; tofu; nuts/seeds; vegetables",
         "Sugary drinks and refined carbohydrate-heavy meals",
         "Vegan","Nutrition decision-support rule","B"),
    ]
    return pd.DataFrame(rows, columns=[
        "Rule_ID","Clinical_Context","Nutrition_Target","Gestational_Context",
        "Recommendation_Principle","Foods_To_Emphasize","Foods_To_Limit",
        "Diet_Pattern_Applicability","Evidence_Source","Evidence_Grade"
    ])


# ================================================================
# ALLERGEN CROSSWALK
# ================================================================

def allergen_crosswalk():
    rows = [
        ("ALG-001","Milk","Milk; curd; paneer","Use non-dairy calcium/protein alternatives where appropriate"),
        ("ALG-002","Egg","Egg","Use pulse/soy/dairy or other tolerated protein alternatives"),
        ("ALG-003","Peanut","Peanut","Use other tolerated nuts/seeds/legumes"),
        ("ALG-004","Tree nuts","Almond and other tree nuts","Use seeds or other tolerated protein/fat sources"),
        ("ALG-005","Soy","Soybean; soy foods","Use other pulses/dairy/egg/meat/fish according to diet pattern"),
        ("ALG-006","Fish","Fish","Use eggs/poultry/pulses/soy/dairy as permitted"),
        ("ALG-007","Wheat/Gluten","Wheat; atta; roti","Use rice/millets/potato and certified gluten-free products where clinically required"),
        ("ALG-008","Sesame","Sesame/tahini/til","Use other seeds/nuts if tolerated"),
        ("ALG-009","Other documented allergen","Patient-specific","Substitute based on nutrient target and clinician/dietitian assessment"),
    ]
    return pd.DataFrame(rows, columns=[
        "Allergen_ID","Allergen_Class","Foods_Commonly_Affected","Substitution_Principle"
    ])


# ================================================================
# EVIDENCE REGISTER
# ================================================================

def evidence_register():
    rows = [
        ("EV-001","ICMR-NIN","Indian Food Composition Tables 2017",
         "Food composition reference for Indian foods","A",
         "https://www.nin.res.in/ebooks/IFCT2017_16122024.pdf"),
        ("EV-002","WHO","Nutrition counselling during pregnancy",
         "Dietary diversity, energy/protein adequacy and nutrition counselling","B",
         "https://www.who.int/tools/elena/interventions/nutrition-counselling-pregnancy"),
        ("EV-003","WHO","Daily iron and folic acid supplementation during pregnancy",
         "Pregnancy iron/folic acid evidence and recommendations","B",
         "https://www.who.int/tools/elena/interventions/daily-iron-pregnancy"),
        ("EV-004","WHO","Recommendations on antenatal care for a positive pregnancy experience",
         "Comprehensive ANC nutrition recommendations","B",
         "https://www.who.int/publications/i/item/9789241549912"),
        ("EV-005","WHO","Healthy diet",
         "Food-group diversity, whole grains, legumes, fruits, vegetables, nuts/seeds and limiting excess sodium/free sugars","B",
         "https://www.who.int/news-room/fact-sheets/detail/healthy-diet"),
        ("EV-006","ICMR-NIN","ICMR-NIN institutional food composition resources",
         "Indian nutrient composition and food database context","A",
         "https://www.nin.res.in/"),
    ]
    return pd.DataFrame(rows, columns=[
        "Evidence_ID","Organization","Source_Title","Use_In_Dataset",
        "Evidence_Grade","Reference_URL"
    ])


# ================================================================
# PATIENT DIET PROFILE
# ================================================================

def infer_diet_profile(row):
    # Dataset 1 may have differently named dietary fields. This function
    # deliberately uses available patient-level information and falls back
    # to a controlled synthetic distribution.
    raw = " ".join([
        txt(row.get("Dietary_Pattern", "")),
        txt(row.get("Diet_Type", "")),
        txt(row.get("Diet", "")),
        txt(row.get("Food_Preference", "")),
        txt(row.get("Dietary_Preference", "")),
    ]).lower()

    if "vegan" in raw:
        return "Vegan"
    if "eggetarian" in raw or "eggitarian" in raw:
        return "Eggetarian"
    if "pesc" in raw:
        return "Pescatarian"
    if "jain" in raw:
        return "Jain-style vegetarian"
    if "lacto ovo" in raw or "lacto-ovo" in raw:
        return "Lacto-ovo vegetarian"
    if "ovo" in raw and "vegetarian" in raw:
        return "Ovo-vegetarian"
    if "lacto" in raw and "vegetarian" in raw:
        return "Lacto-vegetarian"
    if "vegetarian" in raw:
        return "Vegetarian"
    # FIX: D1 stores "Omnivorous"; the old keyword "omnivore" did not match it,
    # so every omnivorous visit fell through to the random fallback below.
    if any(k in raw for k in ["non vegetarian", "non-vegetarian", "nonveg", "non veg", "omnivor"]):
        return "Omnivore / Non-vegetarian"

    # Controlled synthetic fallback.
    choices = [
        "Omnivore / Non-vegetarian",
        "Lacto-vegetarian",
        "Lacto-ovo vegetarian",
        "Vegan",
        "Eggetarian",
        "Jain-style vegetarian",
    ]
    probs = [0.28, 0.30, 0.16, 0.08, 0.10, 0.08]
    return str(rng.choice(choices, p=probs))


def dietary_flags(pattern):
    mapping = {
        "Omnivore / Non-vegetarian": (False, False, True, False),
        "Vegetarian": (False, True, True, False),
        "Lacto-vegetarian": (False, True, False, False),
        "Lacto-ovo vegetarian": (False, True, True, False),
        "Ovo-vegetarian": (False, True, True, False),
        "Vegan": (True, True, False, False),
        "Eggetarian": (False, True, True, False),
        "Jain-style vegetarian": (False, True, False, True),
        "Pescatarian": (False, False, True, False),
    }
    return mapping.get(pattern, (False, True, False, False))


# ================================================================
# PATIENT NUTRITION ASSESSMENTS
# ================================================================

def build_assessments(d1, d2, d3, d4):
    pcol = find_col(d1, ["Patient_ID"], True)
    pregcol = find_col(d1, ["Pregnancy_ID"], True)

    d1_map = {
        (txt(r[pcol]), txt(r[pregcol])): r
        for _, r in d1.iterrows()
    }

    # Lab lookup by pregnancy, gestational week and test.
    lab_p = find_col(d3, ["Patient_ID"], True)
    lab_pr = find_col(d3, ["Pregnancy_ID"], True)
    lab_gw = find_col(d3, ["Gestational_Week","Gestational Week"])
    lab_name = find_col(d3, ["Investigation_Name","Test_Name","Investigation"])
    lab_result = find_col(d3, ["Result","Result_Value","Value"])

    labs = {}
    if lab_p and lab_pr:
        for _, r in d3.iterrows():
            key = (txt(r[lab_p]), txt(r[lab_pr]))
            name = txt(r[lab_name]).lower() if lab_name else ""
            value = num(r[lab_result]) if lab_result else np.nan
            labs.setdefault(key, []).append((name, value))

    # Medication summary by pregnancy.
    med_p = find_col(d4, ["Patient_ID"])
    med_pr = find_col(d4, ["Pregnancy_ID"])
    med_name = find_col(d4, ["Medication_Name","Generic_Name","Medication"])
    med_events = {}
    if med_p and med_pr:
        for _, r in d4.iterrows():
            key = (txt(r[med_p]), txt(r[med_pr]))
            med_events.setdefault(key, []).append(
                txt(r[med_name]) if med_name else ""
            )

    rows = []
    for _, visit in d2.iterrows():
        patient = txt(visit[find_col(d2, ["Patient_ID"], True)])
        pregnancy = txt(visit[find_col(d2, ["Pregnancy_ID"], True)])
        visit_id = txt(visit[find_col(d2, ["Visit_ID"], True)])

        preg_row = d1_map.get((patient, pregnancy), {})
        pattern = infer_diet_profile(preg_row)

        gw = num(visit[find_col(d2, ["Gestational_Week","Gestational Week"], True)])
        trimester = txt(visit[find_col(d2, ["Trimester"], True)])

        bmi = num(visit[find_col(d2, ["BMI"], True)])
        weight = num(visit[find_col(d2, ["Weight_kg","Weight kg"], True)])
        sbp = num(visit[find_col(d2, ["SBP_mmHg","SBP"], True)])

        # Synthetic-but-coherent nutrition symptoms.
        nausea = bool(gw <= 14 and rng.random() < 0.25)
        vomiting = bool(gw <= 18 and rng.random() < 0.08)
        appetite = str(rng.choice(["Normal","Reduced","Increased"], p=[0.78,0.15,0.07]))

        # Identify clinical contexts from available visit/lab information.
        lab_items = labs.get((patient, pregnancy), [])
        names = " ".join(n for n, _ in lab_items)

        anaemia = ("haemoglobin" in names or "hemoglobin" in names) and (
            rng.random() < 0.18
        )
        gdm = ("gdm" in names or "glucose" in names) and (
            rng.random() < 0.20
        )
        hypertension = bool(sbp >= 140 if not np.isnan(sbp) else False)

        if hypertension and rng.random() < 0.4:
            nutrition_risk = "High"
        elif anaemia or gdm or hypertension:
            nutrition_risk = "Moderate"
        elif (not np.isnan(bmi) and bmi < 18.5) or nausea:
            nutrition_risk = "Moderate"
        else:
            nutrition_risk = str(rng.choice(["Low","Low","Low","Moderate"]))

        flags = []
        if anaemia:
            flags.append("Iron_Focus")
        if gdm:
            flags.append("Glycaemic_Control")
        if hypertension:
            flags.append("Sodium_Awareness")
        if not np.isnan(bmi) and bmi < 18.5:
            flags.append("Energy_Protein")
        if pattern == "Vegan":
            flags.extend(["B12_Focus","Calcium_Focus","Iron_Focus","Protein_Focus"])
        if pattern in ["Vegetarian","Lacto-vegetarian","Lacto-ovo vegetarian","Ovo-vegetarian","Eggetarian"]:
            flags.extend(["Iron_Focus","B12_Focus","Protein_Focus"])

        # Medication timing flags.
        meds = " ".join(med_events.get((patient, pregnancy), [])).lower()
        if "iron" in meds:
            flags.append("Iron_Medication_Timing")
        if "levothyroxine" in meds:
            flags.append("Levothyroxine_Timing")
        if "calcium" in meds:
            flags.append("Calcium_Timing")

        rows.append({
            "Nutrition_Assessment_ID": f"NA-{len(rows)+1:06d}",
            "Patient_ID": patient,
            "Pregnancy_ID": pregnancy,
            "Visit_ID": visit_id,
            "Gestational_Week": gw,
            "Trimester": trimester,
            "Dietary_Pattern": pattern,
            "Vegetarian_Status": "Yes" if dietary_flags(pattern)[1] else "No",
            "Vegan_Status": "Yes" if dietary_flags(pattern)[0] else "No",
            "Eggs_Allowed": "Yes" if dietary_flags(pattern)[2] else "No",
            "Jain_Flag": "Yes" if dietary_flags(pattern)[3] else "No",
            "Weight_kg": weight,
            "BMI": bmi,
            "Appetite": appetite,
            "Nausea": "Yes" if nausea else "No",
            "Vomiting": "Yes" if vomiting else "No",
            "Nutritional_Risk_Level": nutrition_risk,
            "Anaemia_Nutrition_Focus": "Yes" if anaemia else "No",
            "GDM_Nutrition_Focus": "Yes" if gdm else "No",
            "Hypertension_Nutrition_Focus": "Yes" if hypertension else "No",
            "Protein_Focus": "Yes" if "Protein_Focus" in flags or nutrition_risk == "High" else "No",
            "Iron_Focus": "Yes" if "Iron_Focus" in flags else "No",
            "Calcium_Focus": "Yes" if "Calcium_Focus" in flags else "No",
            "Folate_Focus": "Yes" if anaemia or pattern in ["Vegan","Vegetarian","Lacto-vegetarian"] else "No",
            "Vitamin_B12_Focus": "Yes" if pattern in ["Vegan","Vegetarian","Lacto-vegetarian","Ovo-vegetarian","Eggetarian"] else "No",
            "Vitamin_D_Focus": "Yes" if pattern == "Vegan" else "No",
            "Fibre_Focus": "Yes" if gdm or nutrition_risk in ["Moderate","High"] else "No",
            "Sodium_Awareness": "Yes" if hypertension else "No",
            "Glycaemic_Control_Focus": "Yes" if gdm else "No",
            "Medication_Food_Timing_Flags": "; ".join(sorted(set(flags))),
            "Food_Allergy_Profile": txt(
                preg_row.get("Food_Allergies",
                preg_row.get("Food_Allergy",""))
            ),
            "Dietary_Restrictions": txt(
                preg_row.get("Dietary_Restrictions",
                preg_row.get("Dietary_Restriction",""))
            ),
            "Nutrition_Counselling_Required": "Yes" if nutrition_risk != "Low" or gw in [8,14,25,28] else "No",
            "Dietitian_Referral": "Yes" if nutrition_risk == "High" or gdm else "No",
            "Follow_Up_Required": "Yes" if nutrition_risk in ["Moderate","High"] else "No",
        })

    return pd.DataFrame(rows)


# ================================================================
# RECOMMENDATION ENGINE
# ================================================================

def build_recommendations(assessments, foods):
    rows = []

    def allowed_for_pattern(food, pattern):
        if pattern == "Vegan":
            return food["Vegan"] == "Yes"
        if pattern in ["Lacto-vegetarian","Lacto-ovo vegetarian","Vegetarian","Ovo-vegetarian","Eggetarian","Jain-style vegetarian"]:
            return food["Vegetarian"] == "Yes"
        if pattern == "Pescatarian":
            return food["Vegetarian"] == "Yes" or "fish" in txt(food["Food_Name"]).lower()
        return True

    for _, a in assessments.iterrows():
        pattern = a["Dietary_Pattern"]
        context = []

        if a["Anaemia_Nutrition_Focus"] == "Yes":
            context.append(("Anaemia","iron"))
        if a["GDM_Nutrition_Focus"] == "Yes":
            context.append(("GDM","glycaemic"))
        if a["Hypertension_Nutrition_Focus"] == "Yes":
            context.append(("Hypertension","sodium"))
        if a["Protein_Focus"] == "Yes":
            context.append(("Protein","protein"))
        if a["Calcium_Focus"] == "Yes":
            context.append(("Calcium","calcium"))
        if a["Vitamin_B12_Focus"] == "Yes":
            context.append(("B12","b12"))
        if a["Fibre_Focus"] == "Yes":
            context.append(("Fibre","fibre"))
        if a["Nausea"] == "Yes":
            context.append(("Nausea","tolerable"))

        # Food allergy filtering.
        allergies = txt(a["Food_Allergy_Profile"]).lower()

        for ctx, target in context:
            candidates = []
            for _, f in foods.iterrows():
                if not allowed_for_pattern(f, pattern):
                    continue
                if allergies:
                    if any(term in allergies for term in split_terms(f["Major_Allergens"])):
                        continue

                score = 0.0
                rationale = ""

                if target == "iron":
                    score = float(f["Iron_mg"]) + float(f["Folate_mcg"]) / 100
                    rationale = "Iron/folate-rich food option; dietary strategy does not replace clinically indicated iron treatment."
                elif target == "glycaemic":
                    score = (3 if f["GI_Category"] == "Low" else 2 if f["GI_Category"] == "Medium" else 0)
                    score += float(f["Fibre_g"]) / 5
                    score += float(f["Protein_g"]) / 10
                    rationale = "Lower-glycaemic, fibre/protein-containing option suitable for portion-aware meal planning."
                elif target == "sodium":
                    score = max(0, 500 - float(f["Sodium_mg"])) / 100
                    score += float(f["Potassium_mg"]) / 300
                    rationale = "Minimally processed lower-sodium food option."
                elif target == "protein":
                    score = float(f["Protein_g"])
                    rationale = "Protein-containing food option adapted to the patient's dietary pattern."
                elif target == "calcium":
                    score = float(f["Calcium_mg"])
                    rationale = "Calcium-rich food option; medication/supplement timing may need coordination."
                elif target == "b12":
                    score = float(f["Vitamin_B12_mcg"]) * 10
                    rationale = "Vitamin B12 source; vegan diets may require fortified foods/supplementation under clinician guidance."
                elif target == "fibre":
                    score = float(f["Fibre_g"])
                    rationale = "Fibre-containing food option."
                elif target == "tolerable":
                    if f["Food_Group"] in ["Cereals","Mixed dish","Meal"]:
                        score = 1
                    rationale = "Simple, tolerable meal option; individual triggers should be respected."

                if score > 0:
                    candidates.append((score, f, rationale))

            candidates.sort(key=lambda x: x[0], reverse=True)
            for score, f, rationale in candidates[:3]:
                rows.append({
                    "Recommendation_Event_ID": f"FRE-{len(rows)+1:07d}",
                    "Nutrition_Assessment_ID": a["Nutrition_Assessment_ID"],
                    "Patient_ID": a["Patient_ID"],
                    "Pregnancy_ID": a["Pregnancy_ID"],
                    "Visit_ID": a["Visit_ID"],
                    "Gestational_Week": a["Gestational_Week"],
                    "Trimester": a["Trimester"],
                    "Dietary_Pattern": pattern,
                    "Clinical_Context": ctx,
                    "Recommendation_Type": "Food",
                    "Food_ID": f["Food_ID"],
                    "Food_Name": f["Food_Name"],
                    "Priority_Score": round(float(score), 3),
                    "Rationale": rationale,
                    "Allergy_Filter_Applied": "Yes" if allergies else "No",
                    "Diet_Pattern_Filter_Applied": "Yes",
                    "Medication_Timing_Flag": a["Medication_Food_Timing_Flags"],
                    "Clinician_Dietitian_Review_Required": "Yes",
                })

    return pd.DataFrame(rows)


# ================================================================
# VALIDATION
# ================================================================

def validate(d1, d2, d3, d4, foods, rules, assessments, recs):
    issues = []

    def req(df, cols, name):
        for c in cols:
            if c not in df.columns:
                issues.append(f"{name}: missing column {c}")

    req(foods, ["Food_ID","Food_Name","Food_Group","Diet_Types","Energy_kcal",
                "Protein_g","Iron_mg","Calcium_mg","Major_Allergens"], "Food_Master")
    req(assessments, ["Patient_ID","Pregnancy_ID","Visit_ID",
                      "Nutrition_Assessment_ID","Dietary_Pattern"], "Assessments")
    req(recs, ["Recommendation_Event_ID","Nutrition_Assessment_ID",
               "Food_ID","Clinical_Context"], "Recommendations")

    if foods["Food_ID"].duplicated().any():
        issues.append("Food_Master: duplicate Food_ID")
    if assessments["Nutrition_Assessment_ID"].duplicated().any():
        issues.append("Assessments: duplicate Nutrition_Assessment_ID")
    if recs["Recommendation_Event_ID"].duplicated().any():
        issues.append("Recommendations: duplicate Recommendation_Event_ID")

    if not assessments.empty:
        bad_patterns = set(assessments["Dietary_Pattern"]) - set(dietary_patterns()["Diet_Pattern"])
        if bad_patterns:
            issues.append(f"Assessments: uncontrolled dietary patterns {sorted(bad_patterns)}")

    if not recs.empty:
        if not set(recs["Food_ID"]).issubset(set(foods["Food_ID"])):
            issues.append("Recommendations: orphan Food_ID")
        if not set(recs["Nutrition_Assessment_ID"]).issubset(set(assessments["Nutrition_Assessment_ID"])):
            issues.append("Recommendations: orphan Nutrition_Assessment_ID")

    numeric_cols = ["Energy_kcal","Carbohydrate_g","Protein_g","Fat_g","Fibre_g",
                    "Calcium_mg","Iron_mg","Folate_mcg","Vitamin_B12_mcg",
                    "Vitamin_C_mg","Sodium_mg","Potassium_mg"]
    for c in numeric_cols:
        if (pd.to_numeric(foods[c], errors="coerce") < 0).any():
            issues.append(f"Food_Master: negative numeric value in {c}")

    # Vegan integrity.
    if not foods.empty:
        vegan_bad = foods[(foods["Vegan"] == "Yes") &
                          (~foods["Food_Group"].isin([
                              "Cereals","Pulses","Nuts/Seeds","Vegetables",
                              "Fruit","Mixed dish","Meal","Sugar/Sweetener"
                          ]))]
        if not vegan_bad.empty:
            issues.append("Food_Master: possible vegan classification conflict")

    # Referential integrity to D1/D2.
    d1_keys = set(zip(
        d1[find_col(d1, ["Patient_ID"], True)].astype(str),
        d1[find_col(d1, ["Pregnancy_ID"], True)].astype(str)
    ))
    d2_keys = set(zip(
        d2[find_col(d2, ["Patient_ID"], True)].astype(str),
        d2[find_col(d2, ["Pregnancy_ID"], True)].astype(str)
    ))
    a_keys = set(zip(
        assessments["Patient_ID"].astype(str),
        assessments["Pregnancy_ID"].astype(str)
    ))
    if not a_keys.issubset(d1_keys):
        issues.append("Assessments: orphan Dataset 1 patient/pregnancy key")
    if not a_keys.issubset(d2_keys):
        issues.append("Assessments: orphan Dataset 2 patient/pregnancy key")

    return issues


# ================================================================
# MAIN
# ================================================================

def main():
    print("=" * 76)
    print("DATASET 5 - INDIA MATERNAL NUTRITION & FOOD INTELLIGENCE ENGINE")
    print("=" * 76)

    print("\nLoading Dataset 1, Dataset 2, Dataset 3 and Dataset 4...")

    d1 = pd.read_csv(D1)
    d2 = pd.read_csv(D2)
    d3 = pd.read_csv(D3)

    if os.path.exists(D4):
        d4 = pd.read_csv(D4)
        d4_status = f"{len(d4):,} medication events"
    else:
        # Dataset 4 is useful but the nutrition dataset remains buildable
        # without it. This keeps the pipeline debuggable.
        d4 = pd.DataFrame(columns=[
            "Patient_ID","Pregnancy_ID","Medication_Name"
        ])
        d4_status = "not found; medication-food timing layer limited"

    print(f"Dataset 1: {len(d1):,} pregnancies")
    print(f"Dataset 2: {len(d2):,} ANC visits")
    print(f"Dataset 3: {len(d3):,} investigations")
    print(f"Dataset 4: {d4_status}")

    print("\nBuilding Indian food master...")
    foods = food_catalogue()
    patterns = dietary_patterns()
    rules = nutrition_rulebook()
    allergens = allergen_crosswalk()
    evidence = evidence_register()

    print(f"Food master entries: {len(foods):,}")
    print(f"Dietary patterns: {len(patterns):,}")
    print(f"Nutrition rules: {len(rules):,}")

    print("\nBuilding longitudinal nutrition assessments...")
    assessments = build_assessments(d1, d2, d3, d4)
    print(f"Nutrition assessments: {len(assessments):,}")

    print("\nBuilding food recommendation events...")
    recs = build_recommendations(assessments, foods)
    print(f"Recommendation events: {len(recs):,}")

    print("\nValidating...")
    issues = validate(d1, d2, d3, d4, foods, rules, assessments, recs)

    # CSV outputs.
    outputs = {
        "food_master_india.csv": foods,
        "nutrition_rulebook.csv": rules,
        "nutrition_assessments.csv": assessments,
        "food_recommendation_events.csv": recs,
        "dietary_patterns.csv": patterns,
        "food_allergen_crosswalk.csv": allergens,
        "nutrition_evidence_register.csv": evidence,
    }

    for name, df in outputs.items():
        df.to_csv(os.path.join(OUT, name), index=False, encoding="utf-8-sig")

    # Excel workbook.
    xlsx_path = os.path.join(OUT, "nutrition_food_india.xlsx")
    with pd.ExcelWriter(xlsx_path, engine="openpyxl") as writer:
        for name, df in outputs.items():
            sheet = name.replace(".csv","")[:31]
            df.to_excel(writer, sheet_name=sheet, index=False)

        wb = writer.book
        for ws in wb.worksheets:
            ws.freeze_panes = "A2"
            ws.auto_filter.ref = ws.dimensions
            for cell in ws[1]:
                cell.font = cell.font.copy(bold=True)
            for col_idx, col in enumerate(ws.columns, start=1):
                max_len = 0
                for cell in col[:200]:
                    max_len = max(max_len, len(str(cell.value or "")))
                ws.column_dimensions[get_column_letter(col_idx)].width = min(max(max_len + 2, 12), 42)

    # Summary.
    diet_counts = assessments["Dietary_Pattern"].value_counts().to_dict()
    context_counts = {}
    for c in ["Anaemia_Nutrition_Focus","GDM_Nutrition_Focus",
              "Hypertension_Nutrition_Focus"]:
        context_counts[c] = int((assessments[c] == "Yes").sum())

    summary = [
        "DATASET 5 - INDIA MATERNAL NUTRITION & FOOD INTELLIGENCE",
        "=" * 70,
        "",
        "Synthetic research dataset. NOT a clinical prescribing or diet-prescribing system.",
        "",
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"Dataset 1 pregnancies: {len(d1):,}",
        f"Dataset 2 ANC visits: {len(d2):,}",
        f"Dataset 3 investigations: {len(d3):,}",
        f"Dataset 4 medication events: {len(d4):,}",
        f"Food master rows: {len(foods):,}",
        f"Dietary pattern definitions: {len(patterns):,}",
        f"Nutrition rule rows: {len(rules):,}",
        f"Nutrition assessments: {len(assessments):,}",
        f"Recommendation events: {len(recs):,}",
        "",
        "Dietary pattern distribution:",
    ]

    for k, v in sorted(diet_counts.items()):
        summary.append(f"  {k}: {v:,}")

    summary += [
        "",
        "Clinical nutrition focus counts:",
        f"  Anaemia focus: {context_counts['Anaemia_Nutrition_Focus']:,}",
        f"  GDM focus: {context_counts['GDM_Nutrition_Focus']:,}",
        f"  Hypertension focus: {context_counts['Hypertension_Nutrition_Focus']:,}",
        "",
        "Evidence hierarchy:",
        "  A = Indian government / ICMR-NIN / NHM / MoHFW",
        "  B = WHO / authoritative international guidance",
        "  C = established reference knowledge",
        "",
        "Key design safeguards:",
        "  - Vegan, vegetarian, lacto-vegetarian, lacto-ovo, ovo-vegetarian,",
        "    eggetarian, pescatarian, Jain-style and non-vegetarian patterns.",
        "  - Food-level allergy filtering.",
        "  - GDM-aware carbohydrate/fibre/protein logic.",
        "  - Anaemia-aware iron + vitamin C logic.",
        "  - Calcium/B12/protein attention for plant-based diets.",
        "  - Medication-food timing flags linked to Dataset 4.",
        "  - Food safety and preparation metadata.",
        "  - Food recommendations remain clinician/dietitian review items.",
        "",
        f"Validation issues: {len(issues)}",
        f"Validation status: {'PASS' if not issues else 'FAIL'}",
    ]

    with open(os.path.join(OUT, "dataset5_summary.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(summary))

    report = [
        "DATASET 5 VALIDATION REPORT",
        "=" * 70,
        f"Timestamp: {datetime.now().isoformat()}",
        "",
        f"Food master: {len(foods):,}",
        f"Nutrition assessments: {len(assessments):,}",
        f"Recommendation events: {len(recs):,}",
        "",
        "Validation checks:",
        f"  Duplicate Food_ID: {'PASS' if not foods['Food_ID'].duplicated().any() else 'FAIL'}",
        f"  Duplicate Nutrition_Assessment_ID: {'PASS' if not assessments['Nutrition_Assessment_ID'].duplicated().any() else 'FAIL'}",
        f"  Duplicate Recommendation_Event_ID: {'PASS' if not recs['Recommendation_Event_ID'].duplicated().any() else 'FAIL'}",
        f"  Referential integrity: {'PASS' if not issues else 'CHECK ISSUES'}",
        "",
    ]
    if issues:
        report.append("ISSUES:")
        report.extend(f"  - {x}" for x in issues)
    else:
        report.append("No validation issues detected.")

    with open(os.path.join(OUT, "dataset5_validation_report.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(report))

    print("\n" + "=" * 76)
    print("DATASET 5 GENERATION COMPLETE")
    print("=" * 76)
    print(f"Food master:             {len(foods):,}")
    print(f"Dietary patterns:        {len(patterns):,}")
    print(f"Nutrition rules:         {len(rules):,}")
    print(f"Nutrition assessments:   {len(assessments):,}")
    print(f"Recommendation events:   {len(recs):,}")
    print(f"Validation issues:       {len(issues)}")
    print(f"Validation status:       {'PASS' if not issues else 'FAIL'}")
    print(f"\nOutput folder:\n{OUT}")


if __name__ == "__main__":
    main()
