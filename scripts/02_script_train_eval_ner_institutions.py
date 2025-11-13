# scripts/script_train_eval_ner_institutions.py
import sys, os, json, random, subprocess, spacy, csv
from pathlib import Path
from spacy.scorer import Scorer
from spacy.training import Example
from tabulate import tabulate

# make local imports work
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'replication_src')))
import config

# --- PARAMETERS ---
base_path = config.MODELS_DIR / "NER_validation" / "NER_institutions"
folds = ["fold_a", "fold_b", "fold_c", "fold_d", "fold_e"]
all_scores_path = base_path / "all_folds_scores"
all_scores_path.mkdir(parents=True, exist_ok=True)

# --- FUNCTION: TRAIN MODEL ---
def train_fold(fold_dir):
    from spacy.cli.train import train as spacy_train

    cfg_path = (fold_dir / "config.cfg").resolve()
    output_dir = (fold_dir).resolve()
    overrides = {
        "paths.train": str((fold_dir / "train.spacy").resolve()),
        "paths.dev": str((fold_dir / "dev.spacy").resolve()),
    }

    print(f"\n Training model for {fold_dir.name} ...")
    spacy_train(config_path=str(cfg_path), output_path=str(output_dir), overrides=overrides)
    print(f"✅ Training complete for {fold_dir.name}")



# --- FUNCTION: EVALUATE MODEL ---
def evaluate_fold(fold_dir):
    fold_name = fold_dir.name
    model_dir = fold_dir / "model-last"
    jsonl_file = next(fold_dir.glob("annotations_institutions_2k_*.jsonl"))
    print(f"Evaluating {fold_name} on {jsonl_file.name}")

    # Load evaluation data
    with open(jsonl_file, "r", encoding="utf-8") as f:
        lines = f.readlines()

    TEST_DATA = []
    for line in lines:
        data = json.loads(line)
        text = data["text"]
        spans = data["spans"]
        entities = [(s["start"], s["end"], s["label"]) for s in spans]
        TEST_DATA.append((text, {"entities": entities}))

    # Evaluate model
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

    # Save per-fold scores
    out_file = all_scores_path / f"{fold_name}_validation_scores.json"
    with open(out_file, "w", encoding="utf-8") as jf:
        json.dump({"overall": overall, "per_label": per_label}, jf, indent=4)
    print(f"✅ Scores saved for {fold_name} → {out_file.name}")
    return overall, per_label

# --- LOOP OVER FOLDS ---
all_overall = []
all_per_label = {}
for fold in folds:
    fold_dir = base_path / fold
    train_fold(fold_dir)
    overall, per_label = evaluate_fold(fold_dir)
    all_overall.append(overall)
    for label, label_scores in per_label.items():
        if label not in all_per_label:
            all_per_label[label] = {"p": [], "r": [], "f": []}
        all_per_label[label]["p"].append(label_scores["p"])
        all_per_label[label]["r"].append(label_scores["r"])
        all_per_label[label]["f"].append(label_scores["f"])

# --- AGGREGATE SCORES ---
avg_overall = {
    "ents_p": sum(d["ents_p"] for d in all_overall) / len(all_overall),
    "ents_r": sum(d["ents_r"] for d in all_overall) / len(all_overall),
    "ents_f": sum(d["ents_f"] for d in all_overall) / len(all_overall),
}
avg_per_label = {
    label: {
        "p": sum(v["p"]) / len(v["p"]),
        "r": sum(v["r"]) / len(v["r"]),
        "f": sum(v["f"]) / len(v["f"]),
    }
    for label, v in all_per_label.items()
}

# --- PRINT AND SAVE SUMMARY TABLE ---
table_data = [
    ["Overall", avg_overall["ents_p"], avg_overall["ents_r"], avg_overall["ents_f"]]
]
for label, s in avg_per_label.items():
    table_data.append([label, s["p"], s["r"], s["f"]])

headers = ["Label", "Precision", "Recall", "F-score"]
print("\n Average Validation Scores Across All Folds")
print(tabulate(table_data, headers=headers, tablefmt="pipe"))

csv_out = config.OUTPUT_TABLES_DIR / "table_A2.csv"
with open(csv_out, "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(headers)
    writer.writerows(table_data)
print(f"\n✅ Saved aggregated results → {csv_out}")
