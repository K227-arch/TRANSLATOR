"""
train_marian.py
===============
Fine-tunes (or continues fine-tuning) a MarianMT model on the cleaned corpus.

Features:
  - Subword regularization via SentencePiece sampling (alpha=0.1)
  - Longer context window: prepends previous sentence as context
  - Handles resized embedding matrix after tokenizer retraining
  - Mixed precision (fp16) on GPU
  - Gradient checkpointing to fit larger batches
  - Saves best checkpoint by validation BLEU

Usage:
    # Continue fine-tuning existing model
    python train_marian.py --direction en2lun --epochs 5

    # After tokenizer retraining (resizes embeddings)
    python train_marian.py --direction en2lun --epochs 10 --resize-embeddings

    # Both directions
    python train_marian.py --direction both --epochs 5

Requirements:
    pip install transformers datasets sacrebleu torch sentencepiece
"""
import os
import sys
import re
import json
import argparse
import random
import numpy as np
import pandas as pd
import torch
from torch.utils.data import Dataset, DataLoader
from transformers import (
    MarianMTModel, MarianTokenizer,
    get_linear_schedule_with_warmup,
)
from sacrebleu.metrics import BLEU, CHRF
from torch.utils.data import WeightedRandomSampler


def _compute_metrics(hypotheses: list, references: list) -> dict:
    """Compute BLEU + chrF on a set of hypotheses and references."""
    bleu_metric = BLEU(effective_order=True)
    chrf_metric = CHRF()
    return {
        "bleu": round(bleu_metric.corpus_score(hypotheses, [references]).score, 2),
        "chrf": round(chrf_metric.corpus_score(hypotheses, [references]).score, 2),
    }


BASE      = os.path.dirname(__file__)
MODEL_DIR = os.path.join(BASE, "model")
DATA_DIR  = os.path.join(BASE, "data", "training")
GR4_CSV   = os.path.join(BASE, "data", "cleaned", "gr4_pairs.csv")
GR5_CSV   = os.path.join(BASE, "data", "cleaned", "gr5_pairs.csv")

GR5_UNC_CSV = os.path.join(BASE, "data", "cleaned", "gr5_uncovered_pairs.csv")

# New-only training files (pairs not yet trained on)
NEW_TRAIN_CSV = os.path.join(DATA_DIR, "new_only_train.csv")
NEW_VAL_CSV   = os.path.join(DATA_DIR, "new_only_val.csv")

# Seed vocabulary files - these are the highest-priority pairs
SEED_CSVS = [
    os.path.join(BASE, "data", "raw", "medical_seed_vocabulary.csv"),
    os.path.join(BASE, "data", "raw", "education_seed_vocabulary.csv"),
    os.path.join(BASE, "data", "raw", "daily_life_seed_vocabulary.csv"),
    os.path.join(BASE, "data", "raw", "low_freq_seed_vocabulary.csv"),
    os.path.join(BASE, "data", "raw", "agriculture_seed_vocabulary.csv"),
]


# ── Weighted sampler for low-frequency pairs ──────────────────────────────────

def _load_pair_keys(csv_path: str) -> set:
    """Load (english, lunyoro) key pairs from a CSV file."""
    keys = set()
    if not os.path.exists(csv_path):
        return keys
    try:
        df = pd.read_csv(csv_path)
        for _, row in df.iterrows():
            en  = re.sub(r'\[[A-Za-z _]+\]\s*', '', str(row.get("english", ""))).strip().lower()
            lun = str(row.get("lunyoro", "")).strip().lower()
            if en and lun:
                keys.add((en, lun))
    except Exception:
        pass
    return keys


def build_weighted_sampler(df: pd.DataFrame, direction: str = "en2lun") -> WeightedRandomSampler:
    """
    Direction-aware weighted sampler.

    Base weights:
      seed vocabulary pairs:        8x  (domain expert translations)
      gr4 + gr5 + gr5_uncovered:    6x  (grammar rules must be reinforced)
      back_translated pairs:        2x  (synthetic, lower priority)
      all other pairs:              1x

    Direction-specific boosts:
      lun2en + lun_words >= 5:      3x  (sentence-level pairs are gold for lun2en)
      lun2en + lun_words >= 3:      1.5x
      lun2en + lun_words <= 2:      0.3x (dictionary entries hurt lun2en BLEU)
      en2lun + en_words >= 8:       1.5x (longer English = more morphology to learn)
    """
    gr4_keys   = _load_pair_keys(GR4_CSV)
    gr5_keys   = _load_pair_keys(GR5_CSV)
    gr5u_keys  = _load_pair_keys(GR5_UNC_CSV)
    grammar_keys = gr4_keys | gr5_keys | gr5u_keys

    seed_keys: set = set()
    for csv_path in SEED_CSVS:
        seed_keys |= _load_pair_keys(csv_path)

    print(f"  [sampler] seed={len(seed_keys)} grammar={len(grammar_keys)} "
          f"direction={direction}")

    weights = []
    for _, row in df.iterrows():
        en  = re.sub(r'\[[A-Za-z _]+\]\s*', '', str(row.get("english", ""))).strip().lower()
        lun = str(row.get("lunyoro", "")).strip().lower()
        src = str(row.get("source", "")).lower()

        if (en, lun) in seed_keys:
            w = 8.0
        elif (en, lun) in grammar_keys:
            w = 6.0
        elif "back_translation" in src:
            w = 2.0
        else:
            w = 1.0

        # Direction-specific boosts
        lun_words = len(lun.split())
        en_words  = len(en.split())

        if direction == "lun2en":
            if lun_words >= 5:
                w *= 3.0    # sentence-level pairs are gold for lun2en
            elif lun_words >= 3:
                w *= 1.5
            elif lun_words <= 2:
                w *= 0.3    # dictionary entries hurt lun2en BLEU
        elif direction == "en2lun" and en_words >= 8:
            w *= 1.5        # longer English = more morphology to learn

        weights.append(w)

    weights_tensor = torch.DoubleTensor(weights)
    return WeightedRandomSampler(weights_tensor, num_samples=len(weights), replacement=True)


# ── Dataset ───────────────────────────────────────────────────────────────────

class TranslationDataset(Dataset):
    """
    Translation dataset with optional context window.
    When context_window=True, prepends the previous sentence as context:
        "prev_sentence ||| current_sentence"
    """
    def __init__(self, df: pd.DataFrame, direction: str,
                 context_window: bool = True,
                 subword_regularization: bool = True,
                 alpha: float = 0.1):
        self.direction = direction
        self.context_window = context_window
        self.subword_reg = subword_regularization
        self.alpha = alpha  # SPM sampling alpha

        # Clean domain tags
        def clean(text: str) -> str:
            return re.sub(r'\[[A-Za-z _]+\]\s*', '', str(text)).strip()

        self.src = [clean(x) for x in df['english'].tolist()]
        self.tgt = [clean(x) for x in df['lunyoro'].tolist()]

        if direction == "lun2en":
            self.src, self.tgt = self.tgt, self.src

    def __len__(self):
        return len(self.src)

    def __getitem__(self, idx):
        src = self.src[idx]
        tgt = self.tgt[idx]

        # Context window: prepend previous sentence
        if self.context_window and idx > 0:
            prev_src = self.src[idx - 1]
            # Only use context if it's reasonably short
            if len(prev_src) < 100:
                src = f"{prev_src} ||| {src}"

        return {"src": src, "tgt": tgt}


def collate_fn(batch, tokenizer, max_length: int = 256,
               subword_reg: bool = True, alpha: float = 0.1):
    """Tokenize a batch, optionally with subword regularization."""
    src_texts = [b["src"] for b in batch]
    tgt_texts = [b["tgt"] for b in batch]

    # Subword regularization: use SPM sampling instead of greedy tokenization
    # This makes the model robust to different segmentations of the same word
    if subword_reg and hasattr(tokenizer, 'sp_model'):
        # Enable sampling in SentencePiece
        try:
            tokenizer.sp_model.SetEncodeExtraOptions(f"alpha:{alpha}")
        except:
            pass  # Fallback to greedy if sampling not supported

    # Tokenize source
    src_enc = tokenizer(
        src_texts,
        max_length=max_length,
        padding="longest",
        truncation=True,
        return_tensors="pt",
    )

    # Tokenize target - use the same tokenizer without context manager
    tgt_enc = tokenizer(
        tgt_texts,
        max_length=max_length,
        padding="longest",
        truncation=True,
        return_tensors="pt",
    )

    # Reset SPM sampling
    if subword_reg and hasattr(tokenizer, 'sp_model'):
        try:
            tokenizer.sp_model.SetEncodeExtraOptions("")
        except:
            pass

    return {
        "input_ids": src_enc["input_ids"],
        "attention_mask": src_enc["attention_mask"],
        "labels": tgt_enc["input_ids"],
    }


# ── Training loop ─────────────────────────────────────────────────────────────

def evaluate_metrics(model, tokenizer, val_df: pd.DataFrame,
                     direction: str, device: str, n_samples: int = 500,
                     min_lun_words: int = 0) -> dict:
    """
    Compute BLEU + chrF + validation loss on a sample of the validation set.
    For lun2en, filters short Lunyoro pairs to match training distribution.
    Returns dict with keys: bleu, chrf, val_loss
    """
    model.eval()

    def clean(text: str) -> str:
        return re.sub(r'\[[A-Za-z _]+\]\s*', '', str(text)).strip()

    src_col, tgt_col = ('english', 'lunyoro') if direction == "en2lun" else ('lunyoro', 'english')

    eval_df = val_df
    if direction == "lun2en" and min_lun_words > 0:
        eval_df = val_df[val_df["lunyoro"].astype(str).str.split().str.len() >= min_lun_words]

    sample = eval_df.sample(min(n_samples, len(eval_df)), random_state=42)
    hypotheses, references = [], []
    total_val_loss = 0.0
    val_steps = 0

    for _, row in sample.iterrows():
        src = clean(row[src_col])
        ref = clean(row[tgt_col])
        inputs = tokenizer(src, return_tensors="pt",
                           truncation=True, max_length=256).to(device)
        tgt_enc = tokenizer(ref, return_tensors="pt",
                            truncation=True, max_length=256).to(device)
        with torch.no_grad():
            # Validation loss
            out_loss = model(input_ids=inputs["input_ids"],
                             attention_mask=inputs["attention_mask"],
                             labels=tgt_enc["input_ids"])
            loss_val = out_loss.loss
            if hasattr(loss_val, 'mean'):
                loss_val = loss_val.mean()
            total_val_loss += loss_val.item()
            val_steps += 1
            # Translation for BLEU/chrF
            out = model.generate(**inputs, num_beams=4, max_length=256, early_stopping=True)
        hyp = tokenizer.decode(out[0], skip_special_tokens=True)
        hypotheses.append(hyp)
        references.append(ref)

    metrics = _compute_metrics(hypotheses, references)
    metrics["val_loss"] = round(total_val_loss / max(val_steps, 1), 4)
    return metrics


# Keep backward-compatible alias
def evaluate_bleu(model, tokenizer, val_df, direction, device,
                  n_samples=500, min_lun_words=0):
    m = evaluate_metrics(model, tokenizer, val_df, direction, device,
                         n_samples=n_samples, min_lun_words=min_lun_words)
    return m["bleu"], m["chrf"], m["val_loss"]


def train_direction(direction: str, args):
    model_dir = os.path.join(MODEL_DIR, direction)
    if not os.path.isdir(model_dir):
        print(f"  Model not found: {model_dir}")
        return

    print(f"\n{'='*50}")
    print(f"Training: {direction}")
    print(f"{'='*50}")

    # Load data
    if args.new_only and os.path.exists(NEW_TRAIN_CSV):
        train_df = pd.read_csv(NEW_TRAIN_CSV).dropna()
        print(f"  [NEW-ONLY] Train: {len(train_df):,} (new pairs only)")
    else:
        train_df = pd.read_csv(os.path.join(DATA_DIR, "train.csv")).dropna()
        print(f"  Train: {len(train_df):,}")

    # Validation strategy:
    # - During training: use only the STABLE val set (original pairs the model was
    #   trained on before this session) → gives honest BLEU without new-data dip
    # - After training: full val.csv reflects complete performance
    STABLE_VAL_CSV = os.path.join(DATA_DIR, "val.csv.bak")
    if args.new_only and os.path.exists(STABLE_VAL_CSV):
        val_df = pd.read_csv(STABLE_VAL_CSV).dropna()
        print(f"  Val:   {len(val_df):,} (stable val — original pairs, no new-data dip)")
    else:
        val_df = pd.read_csv(os.path.join(DATA_DIR, "val.csv")).dropna()
        print(f"  Val:   {len(val_df):,} (full val set)")

    # ── Fix 1: Strip domain tags from English targets for lun2en ─────────────
    # Pairs like "[GENERAL_NOUN] cultivator -> omulimi" are en2lun-only format.
    # For lun2en the model must produce clean English — strip the tags first.
    if direction == "lun2en":
        train_df = train_df.copy()
        val_df   = val_df.copy()
        train_df["english"] = train_df["english"].astype(str).str.replace(
            r'^\[[A-Za-z0-9_ ]+\]\s*', '', regex=True).str.strip()
        val_df["english"] = val_df["english"].astype(str).str.replace(
            r'^\[[A-Za-z0-9_ ]+\]\s*', '', regex=True).str.strip()
        # Drop pairs where stripping left an empty English side
        train_df = train_df[train_df["english"].str.len() >= 2]
        val_df   = val_df[val_df["english"].str.len() >= 2]
        print(f"  [Fix1] Stripped domain tags from English targets for lun2en")

    # ── Fix 2: Filter short/dict pairs for lun2en ─────────────────────────────
    if direction == "lun2en" and args.min_lun_words > 0:
        before = len(train_df)
        train_df = train_df[train_df["lunyoro"].astype(str).str.split().str.len() >= args.min_lun_words]
        print(f"  [Fix2] lun2en: kept {len(train_df):,}/{before:,} sentence pairs "
              f"(lun_words >= {args.min_lun_words})")

    print("  Loading tokenizer and model...")
    tokenizer = MarianTokenizer.from_pretrained(model_dir)
    model     = MarianMTModel.from_pretrained(model_dir)

    if args.resize_embeddings:
        old_size = model.config.vocab_size
        new_size = len(tokenizer)
        if old_size != new_size:
            print(f"  Resizing embeddings: {old_size} -> {new_size}")
            model.resize_token_embeddings(new_size)
            model.config.vocab_size = new_size

    device = "cuda" if torch.cuda.is_available() else "cpu"
    # fp32 — more stable training, avoids precision loss on low-resource language
    model = model.float()
    model.to(device)

    n_gpus = torch.cuda.device_count()
    if n_gpus > 1:
        print(f"  Using {n_gpus} GPUs: {[torch.cuda.get_device_name(i) for i in range(n_gpus)]}")
        model = torch.nn.DataParallel(model)

    if args.gradient_checkpointing:
        model.gradient_checkpointing_enable()

    train_dataset = TranslationDataset(
        train_df, direction,
        context_window=args.context_window,
        subword_regularization=args.subword_reg,
        alpha=args.spm_alpha,
    )

    def _collate(batch):
        return collate_fn(batch, tokenizer,
                          max_length=args.max_length,
                          subword_reg=args.subword_reg,
                          alpha=args.spm_alpha)

    sampler = build_weighted_sampler(train_df, direction=direction)
    train_loader = DataLoader(
        train_dataset, batch_size=args.batch_size,
        sampler=sampler, collate_fn=_collate, num_workers=0,
    )

    optimizer = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=0.01)
    total_steps  = len(train_loader) * args.epochs
    warmup_steps = total_steps // 10
    scheduler = get_linear_schedule_with_warmup(
        optimizer, num_warmup_steps=warmup_steps, num_training_steps=total_steps
    )

    # fp32 — no mixed precision scaler needed
    best_bleu = 0.0
    best_ckpt = os.path.join(model_dir, "best_checkpoint")

    print(f"  Device: {device}  Precision: fp32  Epochs: {args.epochs}  "
          f"Batch: {args.batch_size}  LR: {args.lr}")
    print(f"  Context window: {args.context_window}  "
          f"Subword reg: {args.subword_reg} (alpha={args.spm_alpha})")
    print(f"  Max length: {args.max_length}\n")

    for epoch in range(1, args.epochs + 1):
        model.train()
        total_loss = 0.0
        steps = 0

        for batch in train_loader:
            batch = {k: v.to(device) for k, v in batch.items()}
            optimizer.zero_grad()
            outputs = model(**batch)
            loss = outputs.loss
            if hasattr(loss, 'mean'):
                loss = loss.mean()
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
            scheduler.step()
            total_loss += loss.item()
            steps += 1

            if steps % 200 == 0:
                print(f"  Epoch {epoch} step {steps}/{len(train_loader)} "
                      f"loss={total_loss/steps:.4f}")

        avg_loss = total_loss / steps

        # Evaluate BLEU + chrF + validation loss
        raw_model = model.module if isinstance(model, torch.nn.DataParallel) else model
        bleu_score, chrf_score, val_loss = evaluate_bleu(
            raw_model, tokenizer, val_df, direction, device,
            min_lun_words=args.min_lun_words
        )
        print(f"\n  Epoch {epoch}/{args.epochs} -- "
              f"train_loss={avg_loss:.4f}  val_loss={val_loss:.4f}  "
              f"BLEU={bleu_score:.2f}  chrF={chrf_score:.2f}")

        if bleu_score > best_bleu:
            best_bleu = bleu_score
            raw_model.save_pretrained(best_ckpt)
            tokenizer.save_pretrained(best_ckpt)
            print(f"  [OK] New best BLEU={best_bleu:.2f} chrF={chrf_score:.2f} -- saved")

    # Copy best checkpoint back to model dir
    if os.path.isdir(best_ckpt):
        import shutil
        # Backup current model (skip if backup already exists - avoids Windows permission errors)
        backup = model_dir + "_backup"
        if not os.path.isdir(backup):
            try:
                shutil.copytree(model_dir, backup, ignore=shutil.ignore_patterns("best_checkpoint"))
            except Exception as e:
                print(f"  Warning: could not create backup: {e}")
        # Copy best checkpoint files into model dir
        for fname in os.listdir(best_ckpt):
            try:
                shutil.copy2(os.path.join(best_ckpt, fname), model_dir)
            except Exception as e:
                print(f"  Warning: could not copy {fname}: {e}")
        # Remove best_checkpoint dir (ignore errors on Windows/OneDrive)
        try:
            shutil.rmtree(best_ckpt)
        except Exception:
            pass
        print(f"\n  Best model (BLEU={best_bleu:.2f}) saved to {model_dir}")
        print(f"  Previous model backed up to {backup}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--new-only",     action="store_true", default=False,
                        help="Train only on new (untrained) pairs from new_only_train.csv")
    parser.add_argument("--min-lun-words", type=int, default=3,
                        help="Filter pairs where Lunyoro has fewer than N words "
                             "(lun2en only). Removes dictionary entries that hurt BLEU. "
                             "Default 3. Set 0 to disable.")
    parser.add_argument("--direction",    type=str, default="both",
                        choices=["en2lun", "lun2en", "both"])
    parser.add_argument("--epochs",       type=int,   default=7,
                        help="Number of training epochs (default: 7 for better convergence)")
    parser.add_argument("--batch-size",   type=int,   default=32)
    parser.add_argument("--lr",           type=float, default=3e-5,
                        help="Learning rate (default: 3e-5 for better convergence)")
    parser.add_argument("--max-length",   type=int,   default=256,
                        help="Max token length (use 384 for longer context)")
    parser.add_argument("--context-window", action="store_true", default=True,
                        help="Prepend previous sentence as context")
    parser.add_argument("--no-context-window", dest="context_window",
                        action="store_false")
    parser.add_argument("--subword-reg",  action="store_true", default=True,
                        help="Enable SentencePiece subword regularization")
    parser.add_argument("--no-subword-reg", dest="subword_reg",
                        action="store_false")
    parser.add_argument("--spm-alpha",    type=float, default=0.1,
                        help="SPM sampling alpha for subword regularization")
    parser.add_argument("--fp16",         action="store_true", default=False,
                        help="Use mixed precision (disabled by default — fp32 is more stable)")
    parser.add_argument("--gradient-checkpointing", action="store_true",
                        default=False)
    parser.add_argument("--resize-embeddings", action="store_true",
                        default=False,
                        help="Resize embedding matrix after tokenizer retraining")
    args = parser.parse_args()

    print("=== MarianMT Fine-tuning ===\n")

    directions = ["en2lun", "lun2en"] if args.direction == "both" else [args.direction]
    for direction in directions:
        train_direction(direction, args)

    print("\nTraining complete.")
    print("To push updated models to HuggingFace, run: python push_models.py")


if __name__ == "__main__":
    main()
