# scripts/06_script_train_eval_transformers.py
"""
Fine-tunes four Transformer classifiers (BERT, RoBERTa, DistilBERT, LegalBERT_EU)
on multilabel annotations over 13 categories using 5-fold cross-validation.

"""

import os, sys, random, numpy as np, pandas as pd, torch
from pathlib import Path
from sklearn.model_selection import KFold, train_test_split
from sklearn.metrics import precision_score, recall_score, f1_score, matthews_corrcoef
from torch.utils.data import Dataset, DataLoader
from torch import nn
from tqdm import tqdm
from transformers import AutoTokenizer, AutoModel

# Local imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "replication_src")))
import config


# ============================================================
# ------------------------ SETTINGS ---------------------------
# ============================================================
QUICK_TEST = False  # ⚡ Set to True for fast local run
NUM_FOLDS = 5
EPOCHS = 1 if QUICK_TEST else 10
MAX_LEN = 64 if QUICK_TEST else 200
TRAIN_BATCH_SIZE = 4
VALID_BATCH_SIZE = 4
LEARNING_RATE = 1e-5
SEED = 42

MODELS = {
    "BERT": "bert-base-uncased",
    "RoBERTa": "roberta-base",
    "DistilBERT": "distilbert-base-uncased",
    "LegalBERT_EU": "nlpaueb/bert-base-uncased-eurlex"
    }

device = "cuda" if torch.cuda.is_available() else "cpu"
print(f"🧠 Using device: {device.upper()}")

random.seed(SEED)
np.random.seed(SEED)
torch.manual_seed(SEED)


# ============================================================
# ------------------------ DATASET ----------------------------
# ============================================================
class CustomDataset(Dataset):
    def __init__(self, df, tokenizer, max_len):
        self.texts = df["comment_text"].tolist()
        self.targets = df["list"].tolist()
        self.tokenizer = tokenizer
        self.max_len = max_len

    def __len__(self):
        return len(self.texts)

    def __getitem__(self, idx):
        text = str(self.texts[idx])
        inputs = self.tokenizer.encode_plus(
            text,
            None,
            add_special_tokens=True,
            max_length=self.max_len,
            padding="max_length",
            truncation=True,
            return_token_type_ids=True,
        )
        return {
            "ids": torch.tensor(inputs["input_ids"], dtype=torch.long),
            "mask": torch.tensor(inputs["attention_mask"], dtype=torch.long),
            "token_type_ids": torch.tensor(inputs.get("token_type_ids", [0]*self.max_len), dtype=torch.long),
            "targets": torch.tensor(self.targets[idx], dtype=torch.float),
        }


# ============================================================
# ------------------------- MODEL -----------------------------
# ============================================================
class TransformerClassifier(nn.Module):
    def __init__(self, model_name, num_labels):
        super().__init__()
        self.model_name = model_name 
        self.transformer = AutoModel.from_pretrained(model_name)
        self.dropout = nn.Dropout(0.3)
        hidden_size = self.transformer.config.hidden_size
        self.classifier = nn.Linear(hidden_size, num_labels)

    def forward(self, ids, mask, token_type_ids):
        if "distilbert" in self.model_name.lower():
            outputs = self.transformer(ids, attention_mask=mask, return_dict=False)
        else:
            outputs = self.transformer(ids, attention_mask=mask, token_type_ids=token_type_ids, return_dict=False)
        pooled_output = outputs[1] if len(outputs) > 1 else outputs[0][:, 0, :]
        output = self.dropout(pooled_output)
        return self.classifier(output)


# ============================================================
# ---------------------- TRAINING LOOP ------------------------
# ============================================================
def loss_fn(outputs, targets):
    return nn.BCEWithLogitsLoss()(outputs, targets)


def train_one_epoch(model, loader, optimizer):
    model.train()
    total_loss = 0
    for data in loader:
        ids = data["ids"].to(device)
        mask = data["mask"].to(device)
        token_type_ids = data["token_type_ids"].to(device)
        targets = data["targets"].to(device)

        optimizer.zero_grad()
        outputs = model(ids, mask, token_type_ids)
        loss = loss_fn(outputs, targets)
        loss.backward()
        optimizer.step()
        total_loss += loss.item()
    return total_loss / len(loader)


def validate(model, loader):
    model.eval()
    total_loss = 0
    preds, trues = [], []
    with torch.no_grad():
        for data in loader:
            ids = data["ids"].to(device)
            mask = data["mask"].to(device)
            token_type_ids = data["token_type_ids"].to(device)
            targets = data["targets"].to(device)
            outputs = model(ids, mask, token_type_ids)
            loss = loss_fn(outputs, targets)
            total_loss += loss.item()
            preds.append(torch.sigmoid(outputs).cpu().numpy())
            trues.append(targets.cpu().numpy())
    return total_loss / len(loader), np.vstack(preds), np.vstack(trues)


# ============================================================
# ------------------------ PIPELINE ---------------------------
# ============================================================
def run_model(model_name, model_path):
    print(f"\n🔹 Running {model_name} ({model_path})")

    # Load and prepare data
    df = pd.read_csv(config.SOURCE_TEXT_DIR / "authors_annotation.csv")
    df = df.rename(columns={"text": "comment_text"})
    df.iloc[:, 2:] = (df.iloc[:, 2:] > 0).astype(int)  # binarize any non-zero to 1
    df["list"] = df.iloc[:, 2:].values.tolist()
    df = df[["comment_text", "list"]]

    if QUICK_TEST:
        df = df.sample(100, random_state=SEED).reset_index(drop=True)

    num_labels = len(df["list"][0])

    # preserve original class names (columns after 'text')
    class_names = pd.read_csv(config.SOURCE_TEXT_DIR / "authors_annotation.csv").columns.tolist()[2:]  
    tokenizer = AutoTokenizer.from_pretrained(model_path)
    
    # === initialize containers for all folds ===
    accuracy_all_folds = []
    precision_all_folds = []
    recall_all_folds = []
    f1_all_folds = []
    mcc_all_folds = []

    kf = KFold(n_splits=NUM_FOLDS, shuffle=True, random_state=SEED)
    metrics_list = []

    for fold, (train_idx, test_idx) in enumerate(kf.split(df), 1):
        print(f"\n🧩 Fold {fold}/{NUM_FOLDS}")
        train_df, test_df = df.iloc[train_idx], df.iloc[test_idx]
        train_df, val_df = train_test_split(train_df, test_size=0.2, random_state=SEED)

        train_ds = CustomDataset(train_df, tokenizer, MAX_LEN)
        val_ds = CustomDataset(val_df, tokenizer, MAX_LEN)
        test_ds = CustomDataset(test_df, tokenizer, MAX_LEN)

        train_loader = DataLoader(train_ds, batch_size=TRAIN_BATCH_SIZE, shuffle=True)
        val_loader = DataLoader(val_ds, batch_size=VALID_BATCH_SIZE, shuffle=False)
        test_loader = DataLoader(test_ds, batch_size=VALID_BATCH_SIZE, shuffle=False)

        model = TransformerClassifier(model_path, num_labels).to(device)
        optimizer = torch.optim.Adam(model.parameters(), lr=LEARNING_RATE)

        best_val_loss = float("inf")
        patience, counter = 2, 0

        for epoch in range(EPOCHS):
            train_loss = train_one_epoch(model, train_loader, optimizer)
            val_loss, _, _ = validate(model, val_loader)
            print(f"Epoch {epoch+1}/{EPOCHS} | Train {train_loss:.4f} | Val {val_loss:.4f}")

            if val_loss < best_val_loss:
                best_val_loss = val_loss
                counter = 0
            else:
                counter += 1
            if counter >= patience:
                print("Early stopping.")
                break

        test_loss, preds, trues = validate(model, test_loader)
        preds_bin = (preds > 0.5).astype(int)

        print("\n[DEBUG] trues type:", type(trues))

         
        trues = np.asarray(trues, dtype=int)
        preds_bin = np.asarray(preds_bin, dtype=int)

        print("[DEBUG] unique values in trues:", np.unique(trues))
        print("[DEBUG] unique values in preds_bin:", np.unique(preds_bin))
 
        precision = precision_score(trues, preds_bin, average=None, zero_division=0)
        recall = recall_score(trues, preds_bin, average=None, zero_division=0)
        f1 = f1_score(trues, preds_bin, average=None, zero_division=0)
        mcc = [matthews_corrcoef(trues[:, i], preds_bin[:, i]) for i in range(num_labels)]

        fold_metrics = pd.DataFrame({
            "Label": class_names,   # use the real names
            "Precision": precision,
            "Recall": recall,
            "F1": f1,
            "MCC": mcc,
        })
        metrics_list.append(fold_metrics)

    # === Aggregate results across folds ===
    all_metrics = pd.concat(metrics_list).groupby("Label").mean().reset_index()
    all_metrics[["Precision", "Recall", "F1", "MCC"]] *= 100
    all_metrics = all_metrics.round(2)

    print("\n✅ Final average metrics across folds:")
    print(all_metrics)

    # Save results to /output_tables
    output_path = config.OUTPUT_TABLES_DIR / f"{model_name}_metrics.csv"
    all_metrics.to_csv(output_path, index=False)
    print(f"\n Saved metrics to: {output_path}")



# ============================================================
# ------------------------- MAIN ------------------------------
# ============================================================
if __name__ == "__main__":
    print("\n=== Transformer Fine-Tuning Script ===")
    for model_name, model_path in MODELS.items():
        run_model(model_name, model_path)
    print("\n All models completed successfully.")
