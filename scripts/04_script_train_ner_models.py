# scripts/script_train_ner_models.py
"""
Train two Named Entity Recognition (NER) models:
1. Institutions (10k annotations)
2. Verbs (5k annotations)

Each model is trained using its own config, train, and dev files,
and saved in the specified output directory.

Note:  the script uses spaCy's internal train() function

"""

import os
import spacy
from spacy.cli.train import train as spacy_train
from pathlib import Path


# ============================================================
# --------------------- CONFIGURATION -------------------------
# ============================================================
BASE_DIR = Path(__file__).resolve().parent.parent
MODELS_DIR = BASE_DIR / "models_files" / "NER_training"

MODELS = {
    "NER_institutions": {
        "config": MODELS_DIR / "NER_institutions" / "config.cfg",
        "train": MODELS_DIR / "NER_institutions" / "train.spacy",
        "dev": MODELS_DIR / "NER_institutions" / "dev.spacy",
        "output": BASE_DIR / "models_files" / "NER_institutions",
    },
    "NER_verbs": {
        "config": MODELS_DIR / "NER_verbs" / "config.cfg",
        "train": MODELS_DIR / "NER_verbs" / "train.spacy",
        "dev": MODELS_DIR / "NER_verbs" / "dev.spacy",
        "output": BASE_DIR / "models_files" / "NER_verbs",
    },
}


# ============================================================
# -------------------- TRAIN FUNCTION -------------------------
# ============================================================
def train_spacy_model(name: str, cfg_path: Path, train_path: Path, dev_path: Path, output_path: Path, use_gpu: bool = True):
    """Train a spaCy NER model using spaCy's internal CLI API (safe for 'My Drive')."""
    print(f"\n Training {name} ...")

    overrides = {
        "paths.train": str(train_path.resolve()),
        "paths.dev": str(dev_path.resolve()),
    }

    if use_gpu and spacy.prefer_gpu():
        overrides["gpu_id"] = 0
        print(" Using GPU (if available).")
    else:
        print(" Training on CPU.")

    try:
        spacy_train(
            config_path=str(cfg_path.resolve()),
            output_path=str(output_path.resolve()),
            overrides=overrides,
        )
        print(f"✅ {name} training complete.\n→ Saved to: {output_path}")
    except Exception as e:
        print(f"❌ Training failed for {name}: {e}")


# ============================================================
# ------------------------- MAIN ------------------------------
# ============================================================
if __name__ == "__main__":
    print("\n=== NER Model Training Script ===")

    for model_name, paths in MODELS.items():
        train_spacy_model(
            name=model_name,
            cfg_path=paths["config"],
            train_path=paths["train"],
            dev_path=paths["dev"],
            output_path=paths["output"],
            use_gpu=True,
        )

    print("\n All NER models trained successfully.")
