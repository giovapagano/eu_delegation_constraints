# replication_src/config.py
from pathlib import Path
import os

# Resolve project ROOT whether running as a script or inside a notebook
if "__file__" in globals():
    ROOT = Path(__file__).resolve().parents[1]   # one level above replication_src/
else:
    ROOT = Path.cwd()

# Your actual data/output folders (do NOT rename them)
SOURCE_TEXT_DIR    = Path(os.getenv("SOURCE_TEXT_DIR",    ROOT / "source_files"))
CORPUS_DIR         = Path(os.getenv("CORPUS_DIR",         ROOT / "corpus_files"))
MODELS_DIR         = Path(os.getenv("MODELS_DIR",         ROOT / "models_files"))
OUTPUT_FILES_DIR   = Path(os.getenv("OUTPUT_FILES_DIR",   ROOT / "output_files"))
OUTPUT_TABLES_DIR  = Path(os.getenv("OUTPUT_TABLES_DIR",  ROOT / "output_tables"))

# Make sure common outputs exist (non-destructive)
for d in [CORPUS_DIR, MODELS_DIR, OUTPUT_FILES_DIR, OUTPUT_TABLES_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# Optional shared constants
#SEED = int(os.getenv("SEED", 123))
