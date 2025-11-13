# scripts/script_preprocess_eurlex.py

# --- STEP 1: SETUP & IMPORTS -----
import sys, os, csv, glob, re, random, pandas as pd, spacy, jsonlines
from tqdm import tqdm

# add replication_src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'replication_src')))
import config
from text_utils import *

# safely increase CSV field size limit (Windows fix)
max_int = sys.maxsize
while True:
    try:
        csv.field_size_limit(max_int)
        break
    except OverflowError:
        max_int = int(max_int / 10)

nlp = spacy.load("en_core_web_lg")
nlp.max_length = 2_000_000

print("✅ Environment ready")
print("ROOT:", config.ROOT)
print("SOURCE_TEXT_DIR:", config.SOURCE_TEXT_DIR)
print("CORPUS_DIR:", config.CORPUS_DIR)


# --- STEP 2: LOAD EURLEX CSV FILES ---
from pathlib import Path

# find all EurLex CSVs in source_files
csv_files = glob.glob(str(config.SOURCE_TEXT_DIR / "EurLex*.csv"))

if not csv_files:
    print("No EurLex CSV files found in", config.SOURCE_TEXT_DIR)
    sys.exit(0)

print(f"✅ Found {len(csv_files)} EurLex file(s):")
for f in csv_files:
    print("   -", f)

# merge into one DataFrame
df_list = [pd.read_csv(f) for f in csv_files]
eurlex_df = pd.concat(df_list, ignore_index=True)

print("✅ Merged DataFrame shape:", eurlex_df.shape)
print("✅ Columns:", list(eurlex_df.columns))


# --- STEP 3: LOAD SECONDARY LEGISLATION CELEX LIST ---

celex_numbers_secondary_leg = set()
celex_file = config.SOURCE_TEXT_DIR / "secondary_leg_def.csv"

if not celex_file.exists():
    print(f"⚠️ File not found: {celex_file}")
else:
    with open(celex_file, "r", encoding="utf-8") as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            # adjust column name if different
            key = row.get("celex") or row.get("CELEX") or list(row.values())[0]
            celex_numbers_secondary_leg.add(key)
    print(f"✅ Loaded {len(celex_numbers_secondary_leg)} CELEX codes from {celex_file}")



# --- STEP 4: SENTENCE EXTRACTION & JSONL OUTPUT (FULL MATCH) ---
output_file = config.CORPUS_DIR / "EurLex_sentences.jsonl"
sentences = []

print(f"\n⏳ Processing {len(eurlex_df)} texts with spaCy...")

for idx, row in tqdm(eurlex_df.iterrows(), total=len(eurlex_df)):
    celex = str(row["CELEX"])
    text = str(row["act_raw_text"])

    # process only CELEX numbers that belong to secondary legislation
    if celex not in celex_numbers_secondary_leg:
        continue

    # --- trim text after stop formulas ---
    for stop_formula in stop_formulas:
        end_idx = text.find(stop_formula)
        if end_idx != -1:
            text = text[:end_idx]
            break

    # --- trim text before start formulas ---
    for start_formula in start_formulas:
        start_idx = text.find(start_formula)
        if start_idx != -1:
            text = text[start_idx:]
            break

    # --- process with spaCy ---
    doc = nlp(text)
    length = len(text)

    for i, sentence in enumerate(doc.sents, start=1):
        if len(sentence.text) < 40:
            continue

        filtered_sentence = filter_sentence(sentence.text)
        if filtered_sentence is None:
            continue

        cleaned_sentence = remove_elements_beginning(filtered_sentence)

        if is_mostly_uppercase(cleaned_sentence):
            cleaned_sentence = lowercase_text(cleaned_sentence)

        split_results = split_lists(cleaned_sentence)

        # ---- CASE 1: split_results is a single string ----
        if isinstance(split_results, str):
            for j, chunk in enumerate(segment_sentence_into_chunks(split_results, nlp), start=1):
                for l, subsub in enumerate(semicolon_splitting(chunk), start=1):
                    if len(subsub) < 40:
                        continue
                    subsub = remove_elements_beginning(subsub)
                    sentence_data = {
                        "text": subsub,
                        "metadata": {
                            "CELEX_number": celex,
                            "sentence_id": f"{celex}_{i}",
                            "sub_sentence_id": f"{celex}_{i}_{j}_0_{l}",
                            "length_celex": length,
                            "length_sentence": len(subsub),
                            "list_item": 0,
                        },
                    }
                    sentences.append(sentence_data)

        # ---- CASE 2: split_results is a list ----
        elif isinstance(split_results, list):
            for k, sub_sentence in enumerate(split_results, start=1):
                for j, chunk in enumerate(segment_sentence_into_chunks(sub_sentence, nlp), start=1):
                    for l, subsub in enumerate(semicolon_splitting(chunk), start=1):
                        if len(subsub) < 40:
                            continue
                        subsub = remove_elements_beginning(subsub)
                        sentence_data = {
                            "text": subsub,
                            "metadata": {
                                "CELEX_number": celex,
                                "sentence_id": f"{celex}_{i}",
                                "sub_sentence_id": f"{celex}_{i}_{j}_{k}_{l}",
                                "length_celex": length,
                                "length_sentence": len(subsub),
                                "list_item": 1,
                            },
                        }
                        sentences.append(sentence_data)

        # ---- CASE 3: other result type ----
        else:
            continue

# --- write output ---
if sentences:
    with jsonlines.open(output_file, "w") as writer:
        writer.write_all(sentences)
    print(f"✅ Wrote {len(sentences)} sentences to {output_file}")
else:
    print("⚠️ No sentences extracted.")
