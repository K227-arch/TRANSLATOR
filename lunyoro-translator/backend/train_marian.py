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
from sacrebleu.metrics import BLEU

BASE      = os.path.dirname(__file__)
MODEL_DIR = os.path.join(BASE, "model")
DATA_DIR  = os.path.join(BASE, "data", "training")


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

def evaluate_bleu(model, tokenizer, val_df: pd.DataFrame,
                  direction: str, device: str, n_samples: int = 500) -> float:
    """Compute BLEU on a sample of the validation set."""
    model.eval()
    bleu = BLEU(effective_order=True)

    def clean(text: str) -> str:
        return re.sub(r'\[[A-Za-z _]+\]\s*', '', str(text)).strip()

    if direction == "en2lun":
        src_col, tgt_col = 'english', 'lunyoro'
    else:
        src_col, tgt_col = 'lunyoro', 'english'

    sample = val_df.sample(min(n_samples, len(val_df)), random_state=42)
    hypotheses, references = [], []

    for _, row in sample.iterrows():
        src = clean(row[src_col])
        ref = clean(row[tgt_col])
        inputs = tokenizer(src, return_tensors="pt",
                           truncation=True, max_length=256).to(device)
        with torch.no_grad():
            out = model.generate(**inputs, num_beams=4, max_length=256,
                                 early_stopping=True)
        hyp = tokenizer.decode(out[0], skip_special_tokens=True)
        hypotheses.append(hyp)
        references.append(ref)

    score = bleu.corpus_score(hypotheses, [references])
    return score.score


def train_direction(direction: str, args):
    model_dir = os.path.join(MODEL_DIR, direction)
    if not os.path.isdir(model_dir):
        print(f"  Model not found: {model_dir}")
        return

    print(f"\n{'='*50}")
    print(f"Training: {direction}")
    print(f"{'='*50}")

    # Load data
    train_df = pd.read_csv(os.path.join(DATA_DIR, "train.csv")).dropna()
    val_df   = pd.read_csv(os.path.join(DATA_DIR, "val.csv")).dropna()
    print(f"  Train: {len(train_df):,}  Val: {len(val_df):,}")

    # Load tokenizer and model
    print("  Loading tokenizer and model...")
    tokenizer = MarianTokenizer.from_pretrained(model_dir)
    model     = MarianMTModel.from_pretrained(model_dir)

    # Resize embeddings if tokenizer vocab changed
    if args.resize_embeddings:
        old_size = model.config.vocab_size
        new_size = len(tokenizer)
        if old_size != new_size:
            print(f"  Resizing embeddings: {old_size} → {new_size}")
            model.resize_token_embeddings(new_size)
            model.config.vocab_size = new_size

    device = "cuda" if torch.cuda.is_available() else "cpu"
    model.to(device)

    # Enable gradient checkpointing to save memory
    if args.gradient_checkpointing:
        model.gradient_checkpointing_enable()

    # Dataset and dataloader
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

    train_loader = DataLoader(
        train_dataset, batch_size=args.batch_size,
        shuffle=True, collate_fn=_collate, num_workers=0,
    )

    # Optimizer and scheduler
    optimizer = torch.optim.AdamW(
        model.parameters(), lr=args.lr, weight_decay=0.01
    )
    total_steps   = len(train_loader) * args.epochs
    warmup_steps  = total_steps // 10
    scheduler = get_linear_schedule_with_warmup(
        optimizer, num_warmup_steps=warmup_steps,
        num_training_steps=total_steps
    )

    # Mixed precision scaler
    scaler = torch.cuda.amp.GradScaler() if device == "cuda" and args.fp16 else None

    best_bleu = 0.0
    best_ckpt = os.path.join(model_dir, "best_checkpoint")

    print(f"  Device: {device}  Epochs: {args.epochs}  "
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

            if scaler:
                with torch.cuda.amp.autocast():
                    outputs = model(**batch)
                    loss = outputs.loss
                scaler.scale(loss).backward()
                scaler.unscale_(optimizer)
                torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
                scaler.step(optimizer)
                scaler.update()
            else:
                outputs = model(**batch)
                loss = outputs.loss
                loss.backward()
                torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
                optimizer.step()

            scheduler.step()
            total_loss += loss.item()
            steps += 1

            if steps % 200 == 0:
                avg = total_loss / steps
                print(f"  Epoch {epoch} step {steps}/{len(train_loader)} "
                      f"loss={avg:.4f}")

        avg_loss = total_loss / steps
        print(f"\n  Epoch {epoch} complete — avg loss: {avg_loss:.4f}")

        # Evaluate BLEU
        bleu_score = evaluate_bleu(model, tokenizer, val_df, direction, device)
        print(f"  Validation BLEU: {bleu_score:.2f}")

        # Save best checkpoint
        if bleu_score > best_bleu:
            best_bleu = bleu_score
            model.save_pretrained(best_ckpt)
            tokenizer.save_pretrained(best_ckpt)
            print(f"  ✓ New best BLEU={best_bleu:.2f} — saved to {best_ckpt}")

    # Copy best checkpoint back to model dir
    if os.path.isdir(best_ckpt):
        import shutil
        # Backup current model
        backup = model_dir + "_backup"
        if os.path.isdir(backup):
            shutil.rmtree(backup)
        shutil.copytree(model_dir, backup)
        # Copy best checkpoint files
        for fname in os.listdir(best_ckpt):
            shutil.copy(os.path.join(best_ckpt, fname), model_dir)
        shutil.rmtree(best_ckpt)
        print(f"\n  Best model (BLEU={best_bleu:.2f}) saved to {model_dir}")
        print(f"  Previous model backed up to {backup}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--direction",    type=str, default="both",
                        choices=["en2lun", "lun2en", "both"])
    parser.add_argument("--epochs",       type=int,   default=5)
    parser.add_argument("--batch-size",   type=int,   default=32)
    parser.add_argument("--lr",           type=float, default=5e-5)
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
    parser.add_argument("--fp16",         action="store_true", default=True,
                        help="Use mixed precision (GPU only)")
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
