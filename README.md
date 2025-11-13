# Replication Package  
### *Identifying Delegation and Constraints in Legislative Texts: A Computational Method Applied to the European Union*  
**Fabio Franchino, Marta Migliorati, Giovanni Pagano, Valerio Vignoli**

---

## 📘 Overview

This repository contains the replication materials for the NLP pipeline employed in the article  
*“Identifying Delegation and Constraints in Legislative Texts: A Computational Method Applied to the European Union”* (European Union Politics).

The package reproduces all preprocessing, model training, and classification steps implemented in **Python**, as well as the statistical analyses provided in **Stata**.  
All Python scripts are cross-platform and reproducible using the included `environment.yml` file.

---

## Folder Structure

```

EUP_replication/
│
├── replication_src/           # Source code for helper functions and configuration
│   ├── config.py
│   ├── text_utils.py
│   └── eurlex_functions.py
│
├── scripts/                   # Executable replication scripts
│   ├── 01_script_preprocess_eurlex.py
│   ├── 02_script_train_eval_ner_institutions.py
│   ├── 03_script_train_eval_ner_verbs.py
│   ├── 04_script_train_ner_models.py
│   ├── 05_eurlex_pipeline_main.py
│   └── 06_script_train_eval_transformers.py
│
├── source_files/              # Input data (EurLex CSVs, annotations, CELEX list)
├── corpus_files/              # Intermediate preprocessed texts
├── models_files/              # Training sets, trained spaCy NER models and Transformer checkpoints
├── output_files/              # Final JSON/CSV results
├── output_tables/             # Tables corresponding to the article and appendix
├── environment.yml            # Conda environment specification
└── README.md                  # This file

````

---

## Environment Setup

All scripts were executed in a controlled conda environment using **spaCy 3.6.1**.  
The environment can be recreated as follows:

```bash
conda env create -f environment.yml
conda activate spacy36
````

**Key dependencies:**

* spaCy 3.6.1
* Pandas 2.1.4
* NumPy 1.26.4
* Scikit-learn 1.7.2
* Tabulate, tqdm, jsonlines

---

## Replication Workflow

### **Step 1 — Preprocessing EurLex Texts**

Extract and clean the full text of EU secondary legislation.

```bash
python scripts/01_script_preprocess_eurlex.py
```

This script merges all `EurLex_*.csv` files in `source_files/`, removes preambles and signatures, and generates a JSONL file of processed sentences (`corpus_files/EurLex_sentences.jsonl`).
The full EurLex corpus —used in the article— can be downloaded from the Harvard Dataverse at https://dataverse.harvard.edu/dataset.xhtml?persistentId=doi:10.7910/DVN/0EGYWY
The complete dataset consists of the following four CSV files:
EurLex_directives.csv
EurLex_regulations_1952_1990.csv
EurLex_regulations_1990_2000.csv
EurLex_regulations_2000_2019.csv

Place these files in the source_files/ directory before running the preprocessing script.

---

### **Step 2 — Named Entity Recognition (NER)**

Train and evaluate two custom spaCy NER models:

* **Institutions** → *Table A2*
* **Verbs** → *Table A3*

```bash
python scripts/02_script_train_eval_ner_institutions.py
python scripts/03_script_train_eval_ner_verbs.py
```

Each script performs multi-fold training and validation and saves results in `output_tables/`
(`table_A2.csv`, `table_A3.csv`). The training process relies on configuration (`config.cfg`), training (`train.spacy`), and development (`dev.spacy`) files located in the respective subfolders of `models_files/NER_training/`.
These files are provided in the replication package and ensure full reproducibility of the NER training setup for both the Institutions and Verbs models.

---

### **Step 3 — Full Classification Pipeline**

Annotate sentences with NER entities and classify provisions into **delegation**, **soft obligation**, or **constraint** categories for each actor.

```bash
python scripts/05_script_pipeline_main.py
```

This script takes the preprocessed sentences produced in Step 1, and processes them via a NLP pipeline (matching functions, the custom NER model for institutional actors trained in Step 2, syntactic parsing). It applies the syntactic extraction and rule-based classification functions defined in `replication_src/eurlex_functions.py` to identify the grammatical and semantic roles of actors, verbs, and objects within each sentence.
Using these extracted components, the pipeline assigns each sentence to one or more substantive categories—delegation, soft obligation, or constraint—for the relevant institutional actor (Member States, National Competent Authorities, Commission, or Agencies). The resulting outputs form the basis for the sentece-level classification used in the article.

---

### **Step 4 — Transformer Fine-Tuning (Tables A7–A10)**

Fine-tune four Transformer models on annotated sentences to benchmark classification performance:

| Model          | Hugging Face ID                    | Table | Output File                |
| -------------- | ---------------------------------- | ----- | -------------------------- |
| **BERT**       | `bert-base-uncased`                | A7    | `BERT_metrics.csv`         |
| **RoBERTa**    | `roberta-base`                     | A8    | `RoBERTa_metrics.csv`      |
| **DistilBERT** | `distilbert-base-uncased`          | A9    | `DistilBERT_metrics.csv`   |
| **EurLexBERT** | `nlpaueb/bert-base-uncased-eurlex` | A10   | `LegalBERT_EU_metrics.csv` |

Run:

```bash
python scripts/06_script_train_eval_transformers.py
```

Each model is fine-tuned with 5-fold cross-validation, and the mean precision, recall, F1, and MCC are exported to `output_tables/`.

---

## Output Summary

| Output Table               | Description                          | Script                                     |
| -------------------------- | ------------------------------------ | ------------------------------------------ |
| `table_A2.csv`             | NER model performance (Institutions) | `02_script_train_eval_ner_institutions.py` |
| `table_A3.csv`             | NER model performance (Verbs)        | `03_script_train_eval_ner_verbs.py`        |
| `BERT_metrics.csv`         | Transformer classifier (BERT)        | `06_script_train_eval_transformers.py`     |
| `RoBERTa_metrics.csv`      | Transformer classifier (RoBERTa)     | `06_script_train_eval_transformers.py`     |
| `DistilBERT_metrics.csv`   | Transformer classifier (DistilBERT)  | `06_script_train_eval_transformers.py`     |
| `LegalBERT_EU_metrics.csv` | Transformer classifier (EurLexBERT)  | `06_script_train_eval_transformers.py`     |

All outputs are saved in the `output_tables/` directory and correspond to Tables A2–A10 in the Online Appendix.

---

##  Technical Notes

* Scripts automatically detect GPU availability (CUDA) for faster training.
* All paths are managed through `replication_src/config.py`, ensuring cross-platform compatibility.
* No file overwriting occurs; intermediate results are written to designated folders.


---

## Citation

If using this material, please cite:

> Franchino, Fabio, Marta Migliorati, Giovanni Pagano, and Valerio Vignoli.
> *“Identifying Delegation and Constraints in Legislative Texts: A Computational Method Applied to the European Union.”*
> **European Union Politics** (forthcoming).

---

##  Contact

**Giovanni Pagano**
University of Milan
📧 [giovanni.pagano@unimi.it](mailto:giovanni.pagano@unimi.it)
