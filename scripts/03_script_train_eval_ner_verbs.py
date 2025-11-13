# scripts/03_script_train_eval_ner_verbs.py
import sys, os, json, csv, spacy
from pathlib import Path
from spacy.training import Example
from spacy.cli.train import train as spacy_train
from spacy.scorer import Scorer
from tabulate import tabulate

# --- LOCAL IMPORTS ---
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'replication_src')))
import config

# === PARAMETERS ===
base_path = config.MODELS_DIR / "NER_validation" / "NER_verbs"
base_path.mkdir(parents=True, exist_ok=True)

# use your actual file names
train_file = base_path / "train.spacy"
dev_file   = base_path / "dev.spacy"
cfg_path   = base_path / "config.cfg"
output_dir = base_path
all_scores_path = base_path / "scores"
all_scores_path.mkdir(parents=True, exist_ok=True)

# === TRAIN MODEL ===
def train_model():
    overrides = {
        "paths.train": str(train_file.resolve()),
        "paths.dev": str(dev_file.resolve()),
    }

    print("\n Training NER_verbs model ...")
    spacy_train(config_path=str(cfg_path), output_path=str(output_dir), overrides=overrides)
    print("✅ Training complete for NER_verbs")

# === EVALUATE MODEL ===
def evaluate_model():
    model_dir = output_dir / "model-last"
    jsonl_file = next(base_path.glob("verbs_annotated_20_perc.jsonl"))
    print(f"Evaluating model on {jsonl_file.name}")

    # Load JSONL evaluation data
    TEST_DATA = []
    with open(jsonl_file, "r", encoding="utf-8") as f:
        for line in f:
            data = json.loads(line)
            text = data["text"]
            spans = data["spans"]
            entities = [(s["start"], s["end"], s["label"]) for s in spans]
            TEST_DATA.append((text, {"entities": entities}))

    # Evaluate
    nlp = spacy.load(model_dir)
    scorer = Scorer()
    examples = []
    for text, annotations in TEST_DATA:
        doc_pred = nlp(text)
        example = Example.from_dict(doc_pred, annotations)
        examples.append(example)

    scores = scorer.score_spans(examples, "ents")
    overall = {
        "ents_p": scores["ents_p"],
        "ents_r": scores["ents_r"],
        "ents_f": scores["ents_f"],
    }
    per_label = scores["ents_per_type"]

    # Save results
    out_file = all_scores_path / "validation_scores.json"
    with open(out_file, "w", encoding="utf-8") as jf:
        json.dump({"overall": overall, "per_label": per_label}, jf, indent=4)
    print(f"✅ Scores saved → {out_file.name}")

    # Print and export summary table
    table_data = [["Overall", overall["ents_p"], overall["ents_r"], overall["ents_f"]]]
    for label, s in per_label.items():
        table_data.append([label, s["p"], s["r"], s["f"]])

    headers = ["Label", "Precision", "Recall", "F-score"]
    print("\n Validation Scores (NER_verbs)")
    print(tabulate(table_data, headers=headers, tablefmt="pipe"))

    csv_out = config.OUTPUT_TABLES_DIR / "table_A3.csv"
    with open(csv_out, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerows(table_data)
    print(f"\n✅ Saved aggregated results → {csv_out}")

# === MAIN PIPELINE ===
if __name__ == "__main__":
    train_model()
    evaluate_model()
