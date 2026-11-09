"""Plain-language text used across the app (patient tips, clinical guidance)."""

TIMING_TEXT = {
    "Iron_Medication_Timing": "Take the iron tablet on an empty stomach or with a vitamin-C food (lemon, amla, orange, guava). "
                              "Avoid tea, coffee and milk for 1 hour before and after.",
    "Calcium_Timing": "Take calcium at a different time from iron — for example iron in the morning, calcium after lunch "
                      "or dinner, at least 2 hours apart.",
    "Levothyroxine_Timing": "Take the thyroid tablet first thing in the morning on an empty stomach; keep iron and calcium "
                            "4 hours away.",
    "Glycaemic_Control": "Spread carbohydrates over 3 small meals and 2–3 snacks; prefer whole grains, millets and dal over "
                         "white rice and maida.",
    "Iron_Focus": "Eat iron-rich foods daily: green leafy vegetables, rajma, chana, jaggery, dates, ragi; meat, fish or egg "
                  "if you eat them.",
    "Calcium_Focus": "Have 3 servings of calcium foods a day: milk, curd, paneer, ragi, sesame or fortified alternatives.",
    "B12_Focus": "Include milk, curd, eggs or B12-fortified foods every day; vegans usually need a B12 supplement.",
    "Protein_Focus": "Add a protein food to every meal: dal, sprouts, paneer, curd, soy, eggs, fish or chicken.",
    "Energy_Protein": "Eat small, energy-dense meals more often: nuts, groundnut chikki, milk-based foods.",
    "Sodium_Awareness": "Limit pickles, papad, namkeen, packaged snacks and extra salt at the table.",
}

CONSEQUENCE = {
    "preterm": {
        "High": "Plan closer surveillance (2-weekly visits, cervical length if available), counsel on warning signs of "
                "preterm labour, and confirm delivery at a facility with newborn care. Antenatal steroids if preterm "
                "birth becomes imminent before 34 weeks.",
        "Moderate": "Review risk factors at every visit and counsel on warning signs of preterm labour.",
        "Low": "Continue the routine ANC schedule.",
    },
    "nicu": {
        "High": "Plan delivery at a centre with SNCU/NICU, alert the paediatric team, and review fetal growth.",
        "Moderate": "Note it in the birth plan and make sure paediatric support is available at delivery.",
        "Low": "Routine newborn care expected.",
    },
    "gdm": {
        "High": "Consider early glucose testing before 24 weeks, start diet counselling now and refer to the dietician.",
        "Moderate": "Make sure the 24–28 week glucose test (OGTT) is done on time; give diet and activity advice.",
        "Low": "Routine glucose test (OGTT) at 24–28 weeks.",
    },
}

PATIENT_RISK_TEXT = {
    "High": "Your doctor has marked your pregnancy as high risk. That means closer check-ups — please keep every "
            "appointment and know the danger signs.",
    "Moderate": "Your doctor has marked your pregnancy as moderate risk. Keep your appointments and follow your "
                "medicine and diet plan.",
    "Low": "Your doctor has reviewed your pregnancy as low risk. Keep up your routine check-ups.",
}
