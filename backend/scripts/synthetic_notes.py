"""Synthetic NHS-style clinical notes for the demo notes database.

These notes are entirely fictional. No real patient data has ever been used in
this project — see the README's note on data. Names, NHS numbers, dates and
clinicians are invented; the clinical content is written to be plausible rather
than to describe any real episode of care.

They are deliberately written to contain the things that make free-text
extraction hard, so a demo shows something a keyword search could not do:

  * **Negation** — "denies orthopnoea", "no red flags", "not on anticoagulation"
  * **Temporality** — ex-smoker who quit in 2019 is not a current smoker; an MI
    in 2018 is history, not the presenting problem
  * **Attribution** — family history and collateral history describe someone
    other than the patient
  * **Hedging** — "query PE", "cannot exclude", "likely" carry different
    diagnostic weight from a confirmed diagnosis
  * **UK abbreviations** — BD/OD/TDS/QDS/PRN/PO/IV/SC/NBM, and drug names that
    differ from US usage (paracetamol, adrenaline, salbutamol)
  * **Units and reference ranges** — mg vs microgram, mmol/L vs mg/dL, eGFR
  * **Medication state** — started vs stopped vs continued vs withheld
"""

from __future__ import annotations

from datetime import date

# Each entry becomes one row in `medical_notes`.
NOTES: list[dict] = [
    # ── Cardiology ──────────────────────────────────────────────────────────
    {
        "patient_id": "SYN-0001",
        "note_date": date(2026, 3, 14),
        "author": "Dr A. Okonkwo, ST5 Cardiology",
        "specialty": "Cardiology",
        "note_text": (
            "CARDIOLOGY WARD REVIEW — Ward 12\n"
            "68y gentleman, day 2 of admission.\n"
            "History: 3-day history of worsening exertional dyspnoea and bilateral ankle "
            "swelling. Known ischaemic heart disease with anterior MI in 2019, treated with "
            "primary PCI to LAD. Ex-smoker, 30 pack-years, stopped 2020. Denies chest pain "
            "throughout this admission. No syncope.\n"
            "O/E: BP 148/92, HR 96 irregularly irregular, sats 91% on air, RR 22. JVP raised "
            "5cm. Bibasal crepitations to mid-zones. Pitting oedema to mid-shin bilaterally.\n"
            "Ix: NT-proBNP 3,240 ng/L. ECG — AF with rapid ventricular response, no acute "
            "ischaemic change. TTE: LVEF 34%, moderate MR, dilated LA. U&E: Na 136, K 4.1, "
            "creatinine 108, eGFR 62.\n"
            "Impression: Decompensated heart failure with reduced ejection fraction, "
            "precipitated by new-onset AF.\n"
            "Plan: Furosemide 40mg IV BD. Bisoprolol 2.5mg PO OD started. Apixaban 5mg PO BD "
            "started — CHA2DS2-VASc 4. Daily weights and strict fluid balance. Was on "
            "ibuprofen PRN at home, now stopped. Consultant review tomorrow."
        ),
    },
    {
        "patient_id": "SYN-0002",
        "note_date": date(2026, 3, 2),
        "author": "Dr M. Fairbairn, Consultant Cardiologist",
        "specialty": "Cardiology",
        "note_text": (
            "CARDIOLOGY OUTPATIENT CLINIC\n"
            "54y woman, first appointment, referred by GP with palpitations.\n"
            "Describes intermittent episodes of rapid regular palpitations lasting 10-20 "
            "minutes, self-terminating, occurring roughly twice a month for the past year. "
            "No association with exertion. No chest pain, no dyspnoea, no presyncope. She is "
            "a lifelong non-smoker. Drinks approximately 6 units per week.\n"
            "Family history: father died suddenly aged 49, cause never established. Mother "
            "alive with type 2 diabetes.\n"
            "O/E: BP 118/74, HR 68 regular. Heart sounds normal, no murmur. Chest clear.\n"
            "Ix: Resting ECG normal sinus rhythm, QTc 410ms, no pre-excitation. TFTs normal. "
            "FBC normal. 24h tape from GP showed occasional SVEs only.\n"
            "Impression: Likely paroxysmal SVT — not yet captured. Given the family history "
            "of sudden cardiac death, cannot exclude an inherited arrhythmia syndrome at this "
            "stage.\n"
            "Plan: 14-day event monitor. Echo requested. Bisoprolol 1.25mg OD PRN for "
            "symptoms. Not for anticoagulation. Review with results in 3 months."
        ),
    },
    {
        "patient_id": "SYN-0003",
        "note_date": date(2026, 2, 20),
        "author": "Dr P. Nair, CT2",
        "specialty": "Cardiology",
        "note_text": (
            "AMU CLERKING\n"
            "72y man brought in by ambulance with central crushing chest pain, onset 2 hours "
            "prior, radiating to left arm, associated with sweating and nausea.\n"
            "PMH: Hypertension, hypercholesterolaemia, type 2 diabetes (diet controlled). No "
            "previous cardiac events. Current smoker, 15/day for 50 years.\n"
            "DH: Amlodipine 10mg OD, atorvastatin 20mg ON, ramipril 5mg OD. NKDA.\n"
            "O/E: Distressed, clammy. BP 156/88 right arm, HR 88 regular, sats 96% on air.\n"
            "Ix: ECG — 2mm ST elevation V2-V4 with reciprocal inferior change. Troponin T "
            "pending at time of writing. CXR unremarkable.\n"
            "Impression: Anterior STEMI.\n"
            "Plan: Aspirin 300mg PO stat given, ticagrelor 180mg PO stat given, morphine 5mg "
            "IV. Cath lab activated, transferred for primary PCI. Atorvastatin increased to "
            "80mg ON. Smoking cessation referral on discharge."
        ),
    },
    # ── Respiratory ─────────────────────────────────────────────────────────
    {
        "patient_id": "SYN-0004",
        "note_date": date(2026, 3, 11),
        "author": "Dr S. Whitcombe, ST4 Respiratory",
        "specialty": "Respiratory",
        "note_text": (
            "RESPIRATORY REVIEW — AMU\n"
            "64y woman with known COPD (GOLD stage 3), admitted with 4-day history of "
            "increased breathlessness, increased sputum volume and change in sputum colour to "
            "green.\n"
            "PMH: COPD, osteoporosis, previous PE in 2021 (provoked, post-surgical) — "
            "completed 6 months of anticoagulation and is not currently on any. Ex-smoker, "
            "quit 8 years ago, 40 pack-year history.\n"
            "DH: Seretide 500 BD, tiotropium 18 microgram OD, salbutamol PRN, alendronic acid "
            "70mg weekly.\n"
            "O/E: Tachypnoeic RR 26, sats 88% on air improving to 92% on 28% Venturi. Diffuse "
            "expiratory wheeze, no focal crepitations. Afebrile at 37.4.\n"
            "Ix: ABG on 28%: pH 7.34, pCO2 6.8, pO2 8.1, HCO3 28 — compensated respiratory "
            "acidosis. CRP 68. WCC 13.2. CXR: hyperinflation, no consolidation.\n"
            "Impression: Infective exacerbation of COPD with type 2 respiratory failure. No "
            "evidence of pneumonia. PE considered but Wells score low and this presentation "
            "fits her usual exacerbation pattern.\n"
            "Plan: Prednisolone 30mg PO OD for 5 days. Amoxicillin 500mg PO TDS for 5 days. "
            "Nebulised salbutamol 5mg QDS and ipratropium 500 microgram QDS. Target sats "
            "88-92%. Repeat ABG in 1 hour. If deteriorates, consider NIV."
        ),
    },
    {
        "patient_id": "SYN-0005",
        "note_date": date(2026, 3, 8),
        "author": "Dr L. Barrett, Consultant Respiratory Physician",
        "specialty": "Respiratory",
        "note_text": (
            "RESPIRATORY CLINIC — asthma review\n"
            "29y woman, difficult asthma, reviewed 6-monthly.\n"
            "Since last visit she has had two courses of oral steroids, most recently in "
            "January. No hospital admissions this year — last admission was 2023. Reports "
            "night-time waking with cough approximately twice weekly. Salbutamol use "
            "approximately 4 times per week.\n"
            "She has a cat at home and is aware of the trigger but does not wish to rehome it. "
            "Non-smoker, never smoked. No vaping.\n"
            "DH: Fostair 100/6 two puffs BD, montelukast 10mg ON, salbutamol PRN.\n"
            "Ix: FEV1 2.1L (68% predicted), FEV1/FVC 0.66. FeNO 54 ppb. Eosinophils 0.62. "
            "Total IgE 340. Skin prick positive to cat and house dust mite.\n"
            "Impression: Partially controlled eosinophilic asthma. ACQ score suggests ongoing "
            "symptom burden despite adherence — inhaler technique checked and satisfactory, "
            "and prescription records support good adherence.\n"
            "Plan: Continue Fostair, increase to 200/6 BD. Continue montelukast. Refer to "
            "severe asthma MDT to consider biologic therapy. Annual flu vaccine advised. "
            "Review in 3 months."
        ),
    },
    {
        "patient_id": "SYN-0006",
        "note_date": date(2026, 2, 28),
        "author": "Dr H. Osei, ST3",
        "specialty": "Respiratory",
        "note_text": (
            "ED REFERRAL — query PE\n"
            "41y woman, 12 days post right total knee replacement, presents with sudden onset "
            "pleuritic right-sided chest pain and breathlessness since this morning.\n"
            "No haemoptysis. No calf pain or swelling. No fever. She was discharged on "
            "enoxaparin prophylaxis but admits she stopped it after 5 days because the "
            "injections were painful.\n"
            "PMH: Nil of note. Non-smoker. Combined oral contraceptive pill, ongoing.\n"
            "O/E: HR 108, BP 124/78, sats 94% on air, RR 24, temp 37.1. Chest clear. Right "
            "calf soft, non-tender, no asymmetry.\n"
            "Ix: Wells score 6 (PE likely). D-dimer not indicated given high pre-test "
            "probability. ECG sinus tachycardia. CXR clear.\n"
            "Impression: High clinical suspicion of pulmonary embolism, provoked — recent "
            "surgery, interrupted thromboprophylaxis, and oestrogen-containing contraception.\n"
            "Plan: Treatment-dose apixaban 10mg BD commenced pending imaging. CTPA requested "
            "urgently. COCP stopped, alternative contraception to be discussed. Admit to AMU."
        ),
    },
    # ── Endocrinology ───────────────────────────────────────────────────────
    {
        "patient_id": "SYN-0007",
        "note_date": date(2026, 3, 6),
        "author": "Dr R. Villanueva, Consultant Diabetologist",
        "specialty": "Endocrinology",
        "note_text": (
            "DIABETES CLINIC\n"
            "58y man with type 2 diabetes diagnosed 2016, attending annual review.\n"
            "Reports good adherence. Diet has slipped over the winter. No hypoglycaemic "
            "episodes. No symptoms of neuropathy — specifically denies burning or numbness in "
            "the feet. No visual disturbance.\n"
            "PMH: T2DM, hypertension, NAFLD. Ex-smoker, quit 2014.\n"
            "DH: Metformin 1g BD, gliclazide 80mg OD, ramipril 10mg OD, atorvastatin 20mg ON.\n"
            "O/E: Weight 96.4kg (up 3.1kg from last year), BMI 31.4. BP 142/86. Foot check: "
            "pedal pulses present bilaterally, monofilament sensation intact at all sites, no "
            "ulceration, no deformity.\n"
            "Ix: HbA1c 68 mmol/mol (was 58 last year). eGFR 78. ACR 4.2 mg/mmol. Total "
            "cholesterol 4.6, LDL 2.4. Retinal screening January 2026: background "
            "retinopathy, no maculopathy, routine recall.\n"
            "Impression: Deteriorating glycaemic control with weight gain. Early diabetic "
            "nephropathy not established — ACR borderline.\n"
            "Plan: Add empagliflozin 10mg OD for cardiorenal benefit. Continue metformin. "
            "Stop gliclazide given weight gain. Increase ramipril to 10mg — already at max, "
            "so add amlodipine 5mg OD instead. Dietitian referral. Repeat HbA1c in 3 months."
        ),
    },
    {
        "patient_id": "SYN-0008",
        "note_date": date(2026, 2, 25),
        "author": "Dr K. Ashworth, ST6 Endocrinology",
        "specialty": "Endocrinology",
        "note_text": (
            "ENDOCRINE CLINIC — thyroid\n"
            "34y woman referred with weight loss, heat intolerance and palpitations over "
            "3 months. Has lost approximately 7kg without trying. Reports anxiety and tremor. "
            "Periods have become lighter. No neck pain. No diplopia or eye discomfort.\n"
            "Family history: sister has coeliac disease; mother has hypothyroidism.\n"
            "O/E: HR 104 regular, BP 128/70. Fine tremor of outstretched hands. Smooth, "
            "diffusely enlarged goitre, non-tender, no bruit. No lid lag, no proptosis, eye "
            "movements full.\n"
            "Ix: TSH <0.01 mU/L, free T4 38.2 pmol/L, free T3 14.1 pmol/L. TSH receptor "
            "antibodies positive at 8.4 U/L. FBC and LFTs normal.\n"
            "Impression: Graves' disease. No clinical thyroid eye disease at present.\n"
            "Plan: Carbimazole 20mg OD started, block and replace to be considered. "
            "Propranolol 40mg TDS for symptom control. Counselled on agranulocytosis — advised "
            "to seek urgent FBC if sore throat or fever. Warned against pregnancy while on "
            "carbimazole; contraception discussed. TFTs in 6 weeks."
        ),
    },
    {
        "patient_id": "SYN-0009",
        "note_date": date(2026, 2, 14),
        "author": "Dr J. Mbeki, CT1",
        "specialty": "Endocrinology",
        "note_text": (
            "AMU — diabetic emergency\n"
            "19y woman with type 1 diabetes since age 11, brought in with 2-day history of "
            "vomiting, abdominal pain and drowsiness. Had a viral illness last week. She "
            "reports reducing her insulin because she was not eating.\n"
            "O/E: Drowsy but rousable, GCS 14. Dehydrated, dry mucous membranes. Kussmaul "
            "breathing. HR 122, BP 98/56, temp 37.8, CBG 27.4 mmol/L.\n"
            "Ix: VBG pH 7.12, bicarbonate 9, base excess -18. Ketones 5.8 mmol/L. Na 132, "
            "K 5.4, urea 11.2, creatinine 96. WCC 16.1 (likely stress response). Urine dip: "
            "ketones 4+, no nitrites, no leucocytes.\n"
            "Impression: Diabetic ketoacidosis, precipitated by insulin omission during "
            "intercurrent illness. No clear source of sepsis.\n"
            "Plan: DKA pathway commenced. 0.9% sodium chloride 1L over 1 hour then per "
            "protocol. Fixed rate insulin infusion 0.1 units/kg/hr. Long-acting insulin "
            "(Lantus 18 units ON) continued — short-acting withheld. Hourly CBG and ketones. "
            "Potassium replacement once K <5.5. Diabetes specialist nurse to review re: sick "
            "day rules before discharge."
        ),
    },
    # ── Care of the Elderly ─────────────────────────────────────────────────
    {
        "patient_id": "SYN-0010",
        "note_date": date(2026, 3, 12),
        "author": "Dr E. Thornbury, Consultant Geriatrician",
        "specialty": "Care of the Elderly",
        "note_text": (
            "COMPREHENSIVE GERIATRIC ASSESSMENT\n"
            "87y woman admitted following a mechanical fall at home. Lives alone in a "
            "bungalow, has a care package twice daily. Normally mobilises with a Zimmer frame "
            "indoors.\n"
            "Collateral from daughter: says her mother has become more forgetful over the past "
            "year, occasionally leaves the gas on. Daughter also reports she has had three "
            "falls in the past six months, only one of which was reported to the GP.\n"
            "PMH: Hypertension, osteoarthritis, previous left hip fracture 2023 (DHS), mild "
            "cognitive impairment. Never smoked.\n"
            "DH: Amlodipine 5mg OD, co-codamol 30/500 PRN, omeprazole 20mg OD, zopiclone "
            "7.5mg ON, furosemide 20mg OD. \n"
            "O/E: AMTS 7/10. Lying BP 142/80, standing BP 108/62 with dizziness — postural "
            "drop. No focal neurology. Bruising to right hip, no shortening or rotation. Gait "
            "unsteady, wide-based.\n"
            "Ix: X-ray right hip and pelvis: no fracture. FBC, U&E, bone profile, B12, folate "
            "and TFTs all within normal limits. Vitamin D 28 nmol/L — insufficient. ECG sinus "
            "rhythm.\n"
            "Impression: Multifactorial falls. Contributors: postural hypotension, "
            "polypharmacy with two culprit drugs, vitamin D insufficiency, and unaddressed "
            "cognitive impairment. No acute injury.\n"
            "Plan: Stop zopiclone. Reduce amlodipine to 2.5mg OD and review furosemide with "
            "GP — no clear ongoing indication. Colecalciferol 800 units OD. Falls team and OT "
            "home assessment. Memory clinic referral. DNACPR discussed with patient and "
            "daughter and agreed, form completed."
        ),
    },
    {
        "patient_id": "SYN-0011",
        "note_date": date(2026, 3, 5),
        "author": "Dr N. Halloran, ST4",
        "specialty": "Care of the Elderly",
        "note_text": (
            "WARD ROUND — delirium\n"
            "91y man, day 4 post admission with urinary sepsis. Background of vascular "
            "dementia.\n"
            "Overnight he was agitated, attempted to leave the ward twice, and pulled out his "
            "cannula. Nursing staff report he was calmer this morning. He is disorientated to "
            "time and place but recognises his son.\n"
            "PMH: Vascular dementia, AF on apixaban, CKD stage 3b, BPH, previous TIA 2022.\n"
            "O/E: Temp 37.2 (was 38.9 on admission), HR 84 irregular, BP 118/68. Chest clear. "
            "Abdomen soft, no suprapubic tenderness. Catheter in situ draining clear urine.\n"
            "Ix: CRP 42, down from 186. WCC 8.9, normalised. Creatinine 148, baseline 132. "
            "Urine culture: E. coli, sensitive to co-amoxiclav. Repeat CXR clear.\n"
            "Impression: Resolving urinary sepsis with hyperactive delirium on a background of "
            "vascular dementia. No new focal neurology to suggest stroke.\n"
            "Plan: Continue co-amoxiclav 625mg PO TDS, day 4 of 7. Non-pharmacological "
            "delirium measures: side room, familiar objects, family presence, clock and "
            "calendar in view, avoid night-time disturbance. No antipsychotic — the "
            "haloperidol prescribed on admission has been stopped. TWOC tomorrow. Discharge "
            "planning meeting Friday."
        ),
    },
    {
        "patient_id": "SYN-0012",
        "note_date": date(2026, 2, 22),
        "author": "Dr F. Delacroix, Consultant",
        "specialty": "Care of the Elderly",
        "note_text": (
            "FRAILTY CLINIC\n"
            "79y woman attending with her husband. Referred by GP for polypharmacy review.\n"
            "She reports fatigue, poor appetite and intermittent dizziness. Weight has fallen "
            "from 62kg to 55kg over eight months. She denies low mood and specifically denies "
            "any suicidal ideation. Sleep is poor. No falls in the last year.\n"
            "PMH: Type 2 diabetes, hypertension, hypothyroidism, osteoarthritis, previous "
            "breast cancer (2014, completed treatment, discharged from follow-up 2019).\n"
            "DH: fourteen regular medications including metformin 1g BD, gliclazide 40mg BD, "
            "levothyroxine 100 microgram OD, bisoprolol 5mg OD, doxazosin 4mg OD, amitriptyline "
            "25mg ON, lansoprazole 30mg OD.\n"
            "O/E: Clinical Frailty Scale 5. BP 126/72 lying, 104/60 standing. HR 58. Weight "
            "55.2kg, BMI 21.1.\n"
            "Ix: HbA1c 46 mmol/mol — overtreated for her frailty. TSH 0.3, free T4 22 — "
            "slightly over-replaced. B12 210, folate normal. eGFR 51. Albumin 33.\n"
            "Impression: Frailty with unintentional weight loss and probable overtreatment of "
            "both diabetes and hypothyroidism. Symptomatic postural hypotension likely "
            "iatrogenic.\n"
            "Plan: Deprescribing. Stop gliclazide and doxazosin. Reduce levothyroxine to 75 "
            "microgram OD. Reduce amitriptyline with a view to stopping. Relax HbA1c target to "
            "58-64. Dietitian referral for oral nutritional supplements. Repeat bloods and "
            "review in 6 weeks."
        ),
    },
    # ── Gastroenterology ────────────────────────────────────────────────────
    {
        "patient_id": "SYN-0013",
        "note_date": date(2026, 3, 9),
        "author": "Dr T. Iwasaki, ST5 Gastroenterology",
        "specialty": "Gastroenterology",
        "note_text": (
            "IBD CLINIC\n"
            "26y man with ileocolonic Crohn's disease diagnosed 2022, on maintenance therapy.\n"
            "Reports 5-6 loose stools daily for the past three weeks, with urgency but no "
            "blood. Abdominal cramping before defecation. No fever, no vomiting. No mouth "
            "ulcers, no joint pains, no eye symptoms. Weight stable.\n"
            "He admits he has not been taking his azathioprine for about two months because he "
            "ran out and did not reorder.\n"
            "PMH: Crohn's disease. Appendicectomy 2018. Non-smoker — important given the "
            "disease.\n"
            "DH: Azathioprine 150mg OD (non-adherent as above), loperamide PRN.\n"
            "O/E: Afebrile. Abdomen soft, mild right iliac fossa tenderness, no guarding, no "
            "mass. Perianal inspection normal, no fistula or tags.\n"
            "Ix: CRP 32. Faecal calprotectin 640 microgram/g. Hb 118 (microcytic), ferritin "
            "18. Albumin 36. Stool culture and C. difficile toxin both negative.\n"
            "Impression: Flare of ileocolonic Crohn's disease, driven by non-adherence to "
            "immunomodulator. Infective cause excluded. Iron deficiency anaemia secondary to "
            "chronic inflammation and likely poor intake.\n"
            "Plan: Prednisolone 40mg OD with reducing regimen over 8 weeks. Restart "
            "azathioprine 150mg OD — TPMT previously normal, recheck FBC in 2 weeks. Ferrous "
            "fumarate 210mg BD. MRI small bowel to reassess disease extent. Discuss biologic "
            "escalation at IBD MDT if no response."
        ),
    },
    {
        "patient_id": "SYN-0014",
        "note_date": date(2026, 3, 1),
        "author": "Dr G. Rasmussen, Consultant Hepatologist",
        "specialty": "Gastroenterology",
        "note_text": (
            "HEPATOLOGY CLINIC\n"
            "47y man referred with abnormal LFTs found incidentally on an insurance medical.\n"
            "Asymptomatic. No jaundice, no pruritus, no abdominal swelling, no confusion. "
            "Alcohol history: he initially reported 'a few beers at the weekend' but on "
            "detailed questioning describes 4-5 pints most evenings, approximately 60 units "
            "per week, for the last decade. No IV drug use. No tattoos. No blood transfusions.\n"
            "PMH: Type 2 diabetes diagnosed last year, hypertension. BMI 33.\n"
            "O/E: No stigmata of chronic liver disease. No spider naevi, no palmar erythema. "
            "Liver edge palpable 2cm below costal margin, smooth. No splenomegaly. No ascites, "
            "no asterixis.\n"
            "Ix: ALT 96, AST 142, AST:ALT ratio 1.48. GGT 310. ALP 118. Bilirubin 18. "
            "Albumin 41. INR 1.1. Platelets 148. Ferritin 620 with transferrin saturation 32%. "
            "Hepatitis B and C serology negative. Autoimmune screen negative. USS: coarse "
            "echotexture, mildly enlarged liver, no focal lesion, patent portal vein. "
            "FibroScan 11.4 kPa.\n"
            "Impression: Alcohol-related liver disease with probable significant fibrosis "
            "(F3), with a co-existing metabolic contribution from diabetes and obesity. Not "
            "cirrhotic on current evidence but at high risk. Raised ferritin is reactive — "
            "haemochromatosis unlikely with this transferrin saturation.\n"
            "Plan: Absolute alcohol abstinence — the single most important intervention. "
            "Referral to community alcohol service. Thiamine 100mg TDS. Pabrinex not "
            "indicated as an outpatient. Repeat FibroScan and bloods in 6 months. If "
            "abstinence achieved, fibrosis may regress."
        ),
    },
    {
        "patient_id": "SYN-0015",
        "note_date": date(2026, 2, 18),
        "author": "Dr C. Adeyemi, ST3",
        "specialty": "Gastroenterology",
        "note_text": (
            "SURGICAL ASSESSMENT UNIT\n"
            "63y woman with 6-week history of altered bowel habit and intermittent dark red "
            "rectal bleeding mixed with stool. Reports unintentional weight loss of 5kg. No "
            "abdominal pain. No vomiting.\n"
            "Family history: mother diagnosed with bowel cancer aged 71; no other affected "
            "relatives.\n"
            "PMH: Hypertension. Never smoked. No previous endoscopy.\n"
            "O/E: Pale conjunctivae. Abdomen soft and non-tender, no palpable mass. PR "
            "examination: no mass within reach, dark blood on glove finger.\n"
            "Ix: Hb 94 g/L, MCV 72, ferritin 8. CEA 6.8. Faecal immunochemical test 340 "
            "microgram Hb/g. CT chest/abdomen/pelvis: 4cm sigmoid mass with local nodal "
            "involvement, no liver or lung metastases.\n"
            "Impression: Sigmoid colorectal carcinoma with iron deficiency anaemia. Radiological "
            "staging suggests locally advanced disease without distant spread; histology "
            "awaited.\n"
            "Plan: Urgent colonoscopy with biopsy. Discussed at colorectal MDT this week. "
            "Ferrous sulfate 200mg BD started. Transfusion not required at present. Patient "
            "informed of the likely diagnosis and CNS support offered."
        ),
    },
    # ── Renal ───────────────────────────────────────────────────────────────
    {
        "patient_id": "SYN-0016",
        "note_date": date(2026, 3, 10),
        "author": "Dr V. Kaur, Consultant Nephrologist",
        "specialty": "Renal",
        "note_text": (
            "RENAL CLINIC\n"
            "61y man with CKD stage 4, reviewed 3-monthly.\n"
            "Feels reasonably well. Reports mild ankle swelling in the evenings. No "
            "breathlessness, no orthopnoea. Appetite good. No nausea, no pruritus, no "
            "restless legs.\n"
            "PMH: CKD secondary to hypertensive nephrosclerosis, hypertension, gout. "
            "Ex-smoker, quit 2005.\n"
            "DH: Ramipril 10mg OD, furosemide 40mg OD, allopurinol 300mg OD, atorvastatin "
            "20mg ON, sodium bicarbonate 500mg TDS.\n"
            "O/E: BP 148/88 — above target. Weight stable. Mild bilateral pitting ankle "
            "oedema. Chest clear. No pericardial rub.\n"
            "Ix: Creatinine 268, eGFR 22 (was 25 three months ago). Potassium 5.2. Bicarbonate "
            "19. Haemoglobin 102, ferritin 88, transferrin saturation 17%. Corrected calcium "
            "2.28, phosphate 1.62, PTH 34 pmol/L. ACR 88 mg/mmol.\n"
            "Impression: Progressive CKD 4 with anaemia of chronic kidney disease, metabolic "
            "acidosis, and secondary hyperparathyroidism. Not yet requiring dialysis.\n"
            "Plan: Increase sodium bicarbonate to 1g TDS. IV iron (Ferinject) to be arranged — "
            "iron deficient by saturation despite adequate ferritin. Consider ESA once iron "
            "replete. Add dapagliflozin 10mg OD for renoprotection. Continue ramipril, recheck "
            "U&E in 2 weeks. Begin discussion about renal replacement therapy modalities and "
            "refer for transplant workup assessment. Avoid NSAIDs — reiterated."
        ),
    },
    {
        "patient_id": "SYN-0017",
        "note_date": date(2026, 2, 26),
        "author": "Dr O. Lindqvist, ST5",
        "specialty": "Renal",
        "note_text": (
            "ACUTE KIDNEY INJURY REVIEW\n"
            "75y woman, day 2 on the medical ward, admitted with diarrhoea and vomiting for "
            "4 days after a family gathering.\n"
            "PMH: Hypertension, type 2 diabetes, osteoarthritis.\n"
            "DH on admission: Ramipril 5mg OD, metformin 500mg BD, naproxen 500mg BD (taken "
            "regularly for knee pain), indapamide 2.5mg OD.\n"
            "O/E: Clinically dehydrated on admission, now improving. BP 112/68 (was 96/54), HR "
            "78. Urine output improved to 0.7ml/kg/hr overnight. No palpable bladder.\n"
            "Ix: Creatinine 284 on admission, baseline 82 from six months ago — AKI stage 3. "
            "Today 196, improving. Potassium 5.8 on admission, now 4.6. Bicarbonate 18. "
            "Urinalysis: no blood, no protein. USS kidneys: normal size, no hydronephrosis, "
            "no obstruction.\n"
            "Impression: Pre-renal AKI stage 3 secondary to volume depletion, compounded by "
            "the triple insult of ACE inhibitor, diuretic and NSAID. No evidence of "
            "obstruction or intrinsic renal disease.\n"
            "Plan: Continue IV fluids, reassess balance twice daily. Ramipril, indapamide, "
            "naproxen and metformin all withheld. Ramipril and indapamide to be restarted at "
            "reduced dose once creatinine within 20% of baseline. Naproxen to be stopped "
            "permanently — alternative analgesia with paracetamol and topical NSAID discussed. "
            "GP letter to flag sick day rules."
        ),
    },
    # ── Neurology ───────────────────────────────────────────────────────────
    {
        "patient_id": "SYN-0018",
        "note_date": date(2026, 3, 13),
        "author": "Dr B. Ferreira, Stroke Registrar",
        "specialty": "Neurology",
        "note_text": (
            "HYPERACUTE STROKE UNIT — admission\n"
            "70y woman, witnessed onset of right-sided weakness and speech disturbance at "
            "08:40, arrived in ED 09:25.\n"
            "PMH: AF diagnosed 2023 — she was prescribed apixaban but stopped it herself after "
            "six months due to bruising, and this was not known to her GP. Hypertension. "
            "Hypercholesterolaemia. Ex-smoker, quit 1998.\n"
            "O/E on arrival: NIHSS 14. Right facial droop, right arm 1/5, right leg 3/5, "
            "expressive dysphasia, right homonymous hemianopia. BP 178/96, HR 92 irregular, "
            "CBG 6.4.\n"
            "Ix: CT head — no haemorrhage, early ischaemic change in left MCA territory, ASPECTS "
            "8. CT angiogram: left M1 occlusion. Bloods: INR 1.0, platelets 244.\n"
            "Impression: Acute left MCA territory ischaemic stroke secondary to cardioembolism "
            "from untreated atrial fibrillation.\n"
            "Plan: Thrombolysed with alteplase at 09:58 (door-to-needle 33 minutes). Referred "
            "for mechanical thrombectomy, accepted by the regional centre, transferred 10:20. "
            "Anticoagulation to be restarted after 14 days per protocol, with a discussion "
            "about why the original prescription was stopped. Swallow screen failed — NBM, "
            "IV fluids. SALT and physiotherapy referrals made."
        ),
    },
    {
        "patient_id": "SYN-0019",
        "note_date": date(2026, 3, 3),
        "author": "Dr I. Novak, Consultant Neurologist",
        "specialty": "Neurology",
        "note_text": (
            "NEUROLOGY CLINIC — first seizure\n"
            "23y man referred following a witnessed generalised tonic-clonic seizure at work.\n"
            "Collateral from a colleague: he became unresponsive, fell, had rhythmic jerking "
            "of all four limbs lasting around 90 seconds, followed by 20 minutes of confusion. "
            "Tongue biting on the lateral border. Urinary incontinence.\n"
            "He had been awake for 26 hours before a deadline and had drunk four energy drinks. "
            "He reports two previous episodes of brief early-morning limb jerking which he had "
            "dismissed as clumsiness. No previous full seizure. No head injury. No family "
            "history of epilepsy — his uncle has Parkinson's disease.\n"
            "O/E: Neurological examination entirely normal. No focal deficit.\n"
            "Ix: MRI brain normal. EEG: generalised 4Hz polyspike and wave discharges, "
            "photosensitive response present. ECG normal, QTc 408. Bloods including glucose, "
            "calcium and magnesium normal. Urine toxicology negative.\n"
            "Impression: Juvenile myoclonic epilepsy. The previous morning myoclonic jerks are "
            "the key feature — this is not a first seizure in the sense of an isolated event.\n"
            "Plan: Levetiracetam 250mg BD, titrating to 500mg BD. Sodium valproate avoided "
            "given age and childbearing considerations are not relevant here, but "
            "levetiracetam is preferred first line. Sleep hygiene and alcohol advice. DVLA "
            "notification — must not drive, patient's responsibility, explained and documented. "
            "Review in 8 weeks."
        ),
    },
    {
        "patient_id": "SYN-0020",
        "note_date": date(2026, 2, 16),
        "author": "Dr Y. Al-Rashid, ST4 Neurology",
        "specialty": "Neurology",
        "note_text": (
            "NEUROLOGY CLINIC — headache\n"
            "36y woman with a 4-year history of headache, referred with a query of medication "
            "overuse.\n"
            "Describes two distinct headache types. Type one: unilateral throbbing, "
            "photophobia, phonophobia, nausea, lasting up to a day, roughly twice a month, "
            "sometimes preceded by visual zigzags. Type two: a daily band-like pressure "
            "headache, present on waking, present more days than not.\n"
            "She takes co-codamol 30/500 on most days, and has done for over two years, plus "
            "sumatriptan around 12 days a month.\n"
            "No red flags: no thunderclap onset, no positional change, no fever, no neck "
            "stiffness, no weight loss, no visual loss, no new neurology, no seizures.\n"
            "O/E: Fundoscopy normal, no papilloedema. Cranial nerves intact. No focal deficit. "
            "BP 118/72.\n"
            "Ix: No neuroimaging indicated on current findings — explained to the patient why "
            "a scan is not required and this was accepted.\n"
            "Impression: Migraine with aura, plus medication overuse headache from combined "
            "analgesic and triptan use.\n"
            "Plan: Withdraw co-codamol abruptly, with clear warning of a 1-2 week worsening "
            "before improvement. Limit triptan to no more than 8 days per month. Start "
            "propranolol 40mg BD as prophylaxis. Headache diary. Review in 3 months. If no "
            "improvement, consider candesartan or amitriptyline."
        ),
    },
    # ── Rheumatology ────────────────────────────────────────────────────────
    {
        "patient_id": "SYN-0021",
        "note_date": date(2026, 3, 7),
        "author": "Dr W. Sandhu, Consultant Rheumatologist",
        "specialty": "Rheumatology",
        "note_text": (
            "EARLY ARTHRITIS CLINIC\n"
            "44y woman with 10-week history of symmetrical small joint pain and swelling "
            "affecting the MCPs and PIPs of both hands and the MTPs of both feet.\n"
            "Early morning stiffness lasting around 2 hours. Fatigue. No rash, no oral or "
            "genital ulceration, no dry eyes or mouth, no Raynaud's. No psoriasis — and no "
            "family history of psoriasis. No recent gastrointestinal or genitourinary "
            "infection.\n"
            "Current smoker, 10/day.\n"
            "O/E: Synovitis of bilateral 2nd and 3rd MCPs, right wrist, and bilateral 3rd and "
            "4th MTPs. DAS28 5.9 — high disease activity. No nodules. No nail changes.\n"
            "Ix: Rheumatoid factor 148 IU/mL. Anti-CCP >340 U/mL (strongly positive). ESR 58, "
            "CRP 41. ANA negative. Hand and foot X-rays: periarticular osteopenia, no erosions "
            "yet. Hepatitis screen negative, chest X-ray clear, TB screen negative.\n"
            "Impression: Seropositive rheumatoid arthritis, high disease activity, no "
            "radiographic erosions at presentation. Smoking is a modifiable risk factor for "
            "both disease severity and treatment response.\n"
            "Plan: Methotrexate 15mg weekly PO with folic acid 5mg weekly on a different day. "
            "Prednisolone 20mg OD as a bridging course, reducing over 6 weeks. Baseline FBC, "
            "LFT and U&E, then fortnightly monitoring. Counselled on alcohol limits and the "
            "absolute need for contraception. Strongly advised smoking cessation and referred. "
            "Review in 6 weeks with a view to escalating to combination DMARDs."
        ),
    },
    {
        "patient_id": "SYN-0022",
        "note_date": date(2026, 2, 12),
        "author": "Dr D. Achterberg, ST6",
        "specialty": "Rheumatology",
        "note_text": (
            "URGENT RHEUMATOLOGY REVIEW\n"
            "68y man referred by GP with 3-week history of bilateral shoulder and hip girdle "
            "pain with profound early morning stiffness lasting more than an hour. Struggles "
            "to get out of bed and to raise his arms to comb his hair.\n"
            "Importantly: no jaw claudication, no scalp tenderness, no temporal headache, and "
            "no visual symptoms. He has had some weight loss, around 3kg, and night sweats.\n"
            "PMH: Hypertension, BPH. Ex-smoker, quit 1994.\n"
            "O/E: Restricted active shoulder abduction bilaterally, limited by pain rather "
            "than weakness. Power 5/5 when tested passively. No synovitis of small joints. "
            "Temporal arteries non-tender, pulsatile, no thickening.\n"
            "Ix: ESR 88, CRP 64. FBC: normocytic anaemia Hb 116. ALP mildly raised at 148. "
            "Rheumatoid factor negative, anti-CCP negative. CK normal — argues against an "
            "inflammatory myopathy. Urine dip negative.\n"
            "Impression: Polymyalgia rheumatica. No clinical features of giant cell arteritis "
            "at present, but the patient has been explicitly counselled on the symptoms that "
            "would require emergency assessment.\n"
            "Plan: Prednisolone 15mg OD — expect a dramatic response within 72 hours; if not, "
            "the diagnosis must be revisited. Reducing regimen thereafter. Bone protection: "
            "alendronic acid 70mg weekly plus calcium and vitamin D, started today. PPI cover. "
            "Steroid card issued. Review in 3 weeks."
        ),
    },
    # ── Oncology ────────────────────────────────────────────────────────────
    {
        "patient_id": "SYN-0023",
        "note_date": date(2026, 3, 4),
        "author": "Dr Q. Mensah, Consultant Oncologist",
        "specialty": "Oncology",
        "note_text": (
            "ONCOLOGY CLINIC — treatment review\n"
            "59y woman with stage IIIA non-small cell lung cancer (adenocarcinoma), attending "
            "after cycle 3 of carboplatin and pemetrexed.\n"
            "Tolerating treatment reasonably. Reports grade 2 fatigue and mild peripheral "
            "neuropathy in the fingertips, grade 1. Nausea well controlled on ondansetron. No "
            "mucositis. No diarrhoea. Appetite reduced but weight stable at 61kg.\n"
            "She had one episode of fever to 38.2 at home last week which settled without "
            "treatment; she did not attend and did not call the acute oncology line. This has "
            "been discussed at length and the neutropenic sepsis pathway re-explained.\n"
            "PMH: Ex-smoker, 25 pack-years, quit at diagnosis in 2025. COPD, mild.\n"
            "O/E: Performance status 1. Chest: reduced air entry right upper zone. No "
            "lymphadenopathy. No signs of infection today, temp 36.8.\n"
            "Ix: Pre-cycle bloods: Hb 106, neutrophils 1.4, platelets 178. Creatinine 78, "
            "eGFR 74. LFTs normal. Interim CT after cycle 2: partial response, primary reduced "
            "from 52mm to 34mm, nodal disease reduced. No new lesions. EGFR wild type, ALK "
            "negative, PD-L1 TPS 60%.\n"
            "Impression: Partial radiological response after 2 cycles. Neutropenia borderline "
            "but above treatment threshold.\n"
            "Plan: Proceed with cycle 4 today at full dose. Continue ondansetron and "
            "dexamethasone premedication. Repeat CT after cycle 4 to assess suitability for "
            "consolidation. Given PD-L1 60%, discuss durvalumab consolidation at lung MDT. "
            "Acute oncology card reissued and contact number confirmed with the patient."
        ),
    },
    {
        "patient_id": "SYN-0024",
        "note_date": date(2026, 2, 10),
        "author": "Dr Z. Petrakis, Palliative Medicine Consultant",
        "specialty": "Palliative Care",
        "note_text": (
            "SPECIALIST PALLIATIVE CARE — first assessment\n"
            "82y man with metastatic prostate cancer, bone and liver metastases, now off "
            "active oncological treatment following progression on abiraterone.\n"
            "Main problem is pain: constant background ache in the lower back and right hip, "
            "scored 7/10, with incident pain on transferring scored 9/10. Currently on "
            "morphine sulfate modified release 30mg BD with immediate-release 10mg PRN, using "
            "around 5 breakthrough doses daily.\n"
            "Also reports constipation — bowels last opened 4 days ago. No nausea. Appetite "
            "poor. Sleep disturbed by pain. No confusion. No new weakness in the legs, no "
            "saddle anaesthesia, no bladder or bowel incontinence — specifically asked about "
            "and absent.\n"
            "He is aware of his prognosis and has expressed a clear wish to die at home. His "
            "wife is the main carer and is coping but tired.\n"
            "O/E: Cachectic. Tender over L3 and the right greater trochanter. Neurological "
            "examination of the lower limbs normal, power 5/5, reflexes normal, plantars "
            "downgoing.\n"
            "Ix: Corrected calcium 2.68 — mild hypercalcaemia of malignancy. eGFR 44. Recent "
            "MRI spine (3 weeks ago): metastatic deposits at L3 and L5, no cord or cauda "
            "equina compression.\n"
            "Impression: Uncontrolled mixed background and incident cancer pain, with "
            "constipation secondary to opioids and mild hypercalcaemia contributing.\n"
            "Plan: Increase MST to 50mg BD, breakthrough dose to 15mg. Add regular macrogol "
            "two sachets BD and senna 15mg ON. IV zoledronic acid, dose adjusted for renal "
            "function. Consider single-fraction palliative radiotherapy to L3 and right hip. "
            "Community palliative care nurse referral. Anticipatory medicines to be prescribed "
            "and left in the home. DNACPR in place and ReSPECT form completed. Carer support "
            "assessment offered to his wife."
        ),
    },
]
