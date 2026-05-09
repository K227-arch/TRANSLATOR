"""
train_nllb.py
=============
Fine-tune the existing local NLLB-200 models on the Runyoro-Rutooro dataset.
Always loads from the local model directory — never trains from scratch.

Usage:
    python train_nllb.py                          # both directions, 3 epochs
    python train_nllb.py --direction en2lun       # one direction only
    python train_nllb.py --epochs 5 --lr 2e-5
    python train_nllb.py --fp16                   # mixed precision (GPU)
"""

import os
import sys
import argparse
import re
import shutil
import pandas as pd
import torch
from torch.utils.data import Dataset, DataLoader, WeightedRandomSampler
from transformers import (
    NllbTokenizer,
    AutoModelForSeq2SeqLM,
    get_linear_schedule_with_warmup,
)

BASE      = os.path.dirname(__file__)
MODEL_DIR = os.path.join(BASE, "model")
DATA_DIR  = os.path.join(BASE, "data", "training")
GR4_CSV   = os.path.join(BASE, "data", "cleaned", "gr4_pairs.csv")

NLLB_LANG_EN  = "eng_Latn"
NLLB_LANG_LUN = "run_Latn"


# ── Weighted sampler (same logic as train_marian.py) ─────────────────────────

def build_weighted_sampler(df: pd.DataFrame, upweight: float = 4.0) -> WeightedRandomSampler:
    gr4_keys: set = set()
    if os.path.exists(GR4_CSV):
        try:
            gr4_df = pd.read_csv(GR4_CSV)
            for _, row in gr4_df.iterrows():
                en  = str(row.get("english", "")).strip().lower()
                lun = str(row.get("lunyoro", "")).strip().lower()
                if en and lun:
                    gr4_keys.add((en, lun))
        except Exception:
            pass

    weights = []
    for _, row in df.iterrows():
        en  = re.sub(r'\[[A-Za-z _]+\]\s*', '', str(row.get("english", ""))).strip().lower()
        lun = str(row.get("lunyoro", "")).strip().lower()
        src = str(row.get("source", "")).lower()
        if (en, lun) in gr4_keys:
            weights.append(upweight)
        elif "back_translation" in src:
            weights.append(2.0)
        else:
            weights.append(1.0)

    weights_tensor = torch.DoubleTensor(weights)
    return WeightedRandomSampler(weights_tensor, num_samples=len(weights), replacement=True)


# ── Dataset ───────────────────────────────────────────────────────────────────

class NLLBDataset(Dataset):
    def __init__(self, df: pd.DataFrame, direction: str):
        self.direction = direction
        if direction == "en2lun":
            self.src = df["english"].astype(str).tolist()
            self.tgt = df["lunyoro"].astype(str).tolist()
        else:
            self.src = df["lunyoro"].astype(str).tolist()
            self.tgt = df["english"].astype(str).tolist()

    def __len__(self):
        return len(self.src)

    def __getitem__(self, idx):
        return self.src[idx], self.tgt[idx]


def collate_fn(batch, tokenizer, src_lang, tgt_lang, max_length=256):
    srcs, tgts = zip(*batch)
    tokenizer.src_lang = src_lang
    model_inputs = tokenizer(
        list(srcs),
        text_target=list(tgts),
        max_length=max_length,
        truncation=True,
        padding=True,
        return_tensors="pt",
    )
    # Replace padding token id in labels with -100 so loss ignores them
    labels = model_inputs["labels"]
    labels[labels == tokenizer.pad_token_id] = -100
    model_inputs["labels"] = labels
    return model_inputs


# ── BLEU evaluation ───────────────────────────────────────────────────────────

def evaluate_bleu(model, tokenizer, val_df, direction, device,
                  src_lang, tgt_lang, max_samples=200, max_length=256):
    from sacrebleu.metrics import BLEU
    bleu = BLEU(effective_order=True)

    if direction == "en2lun":
        srcs = val_df["english"].astype(str).tolist()[:max_samples]
        refs = val_df["lunyoro"].astype(str).tolist()[:max_samples]
    else:
        srcs = val_df["lunyoro"].astype(str).tolist()[:max_samples]
        refs = val_df["english"].astype(str).tolist()[:max_samples]

    model.eval()
    hypotheses = []
    batch_size = 8
    tokenizer.src_lang = src_lang

    for i in range(0, len(srcs), batch_size):
        batch = srcs[i:i + batch_size]
        inputs = tokenizer(
            batch, return_tensors="pt", padding=True,
            truncation=True, max_length=max_length,
        ).to(device)
        forced_bos = tokenizer.convert_tokens_to_ids(tgt_lang)
        with torch.no_grad():
            out = model.generate(
                **inputs,
                forced_bos_token_id=forced_bos,
                num_beams=4,
                max_length=max_length,
                early_stopping=True,
            )
        decoded = tokenizer.batch_decode(out, skip_special_tokens=True)
        hypotheses.extend(decoded)

    score = bleu.corpus_score(hypotheses, [refs])
    return score.score


# ── Training ──────────────────────────────────────────────────────────────────

def train_direction(direction: str, args):
    model_path = os.path.join(MODEL_DIR, f"nllb_{direction}")
    if not os.path.isdir(model_path):
        print(f"  Model not found: {model_path}")
        print("  Run download_models.py first.")
        return

    print(f"\n{'='*55}")
    print(f"Fine-tuning NLLB: {direction}")
    print(f"  Loading from: {model_path}")
    print(f"{'='*55}")

    # Load data
    train_df = pd.read_csv(os.path.join(DATA_DIR, "train.csv")).dropna()
    val_df   = pd.read_csv(os.path.join(DATA_DIR, "val.csv")).dropna()
    print(f"  Train: {len(train_df):,}  Val: {len(val_df):,}")

    # Load tokenizer and model from local path (fine-tune, not from scratch)
    print("  Loading tokenizer and model from local checkpoint...")
    tokenizer = NllbTokenizer.from_pretrained(model_path)
    model     = AutoModelForSeq2SeqLM.from_pretrained(model_path)

    device = "cuda" if torch.cuda.is_available() else "cpu"
    model.to(device)
    print(f"  Device: {device}")

    src_lang = NLLB_LANG_EN  if direction == "en2lun" else NLLB_LANG_LUN
    tgt_lang = NLLB_LANG_LUN if direction == "en2lun" else NLLB_LANG_EN

    # Dataset
    train_dataset = NLLBDataset(train_df, direction)

    def _collate(batch):
        return collate_fn(batch, tokenizer, src_lang, tgt_lang,
                          max_length=args.max_length)

    # Weighted sampler: gr4 pairs 4x, back-translated 2x, rest 1x
    sampler = build_weighted_sampler(train_df)
    train_loader = DataLoader(
        train_dataset, batch_size=args.batch_size,
        sampler=sampler, collate_fn=_collate, num_workers=0,
    )

    # Optimizer — lower LR than MarianMT since NLLB is larger
    optimizer = torch.optim.AdamW(
        model.parameters(), lr=args.lr, weight_decay=0.01
    )
    total_steps  = len(train_loader) * args.epochs
    warmup_steps = total_steps // 10
    scheduler = get_linear_schedule_with_warmup(
        optimizer, num_warmup_steps=warmup_steps,
        num_training_steps=total_steps,
    )

    scaler = torch.cuda.amp.GradScaler() if device == "cuda" and args.fp16 else None

    best_bleu = 0.0
    best_ckpt = os.path.join(model_path, "best_checkpoint")

    print(f"  Epochs: {args.epochs}  Batch: {args.batch_size}  "
          f"LR: {args.lr}  FP16: {args.fp16}")
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
                print(f"  Epoch {epoch} step {steps}/{len(train_loader)} "
                      f"loss={total_loss/steps:.4f}")

        avg_loss = total_loss / max(steps, 1)

        # Evaluate
        bleu = evaluate_bleu(
            model, tokenizer, val_df, direction, device,
            src_lang, tgt_lang, max_length=args.max_length,
        )
        print(f"  Epoch {epoch}/{args.epochs} — loss={avg_loss:.4f}  BLEU={bleu:.2f}")

        # Save best checkpoint
        if bleu > best_bleu:
            best_bleu = bleu
            if os.path.exists(best_ckpt):
                shutil.rmtree(best_ckpt)
            model.save_pretrained(best_ckpt)
            tokenizer.save_pretrained(best_ckpt)
            print(f"  ✓ New best BLEU={bleu:.2f} — saved to {best_ckpt}")

    # Promote best checkpoint to model root
    if os.path.exists(best_ckpt):
        print(f"\n  Promoting best checkpoint (BLEU={best_bleu:.2f}) to {model_path}")
        for fname in os.listdir(best_ckpt):
            src = os.path.join(best_ckpt, fname)
            dst = os.path.join(model_path, fname)
            shutil.copy2(src, dst)
        print(f"  ✓ nllb_{direction} updated")
    else:
        print("  No best checkpoint found — saving final model")
        model.save_pretrained(model_path)
        tokenizer.save_pretrained(model_path)

    print(f"\n  nllb_{direction} fine-tuning complete. Best BLEU: {best_bleu:.2f}")


# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Fine-tune local NLLB models on Runyoro-Rutooro data"
    )
    parser.add_argument("--direction", type=str, default="both",
                        choices=["en2lun", "lun2en", "both"])
    parser.add_argument("--epochs",     type=int,   default=3)
    parser.add_argument("--batch-size", type=int,   default=8,
                        help="Keep low (8-16) — NLLB is large")
    parser.add_argument("--lr",         type=float, default=1e-5,
                        help="Lower LR than MarianMT (default 1e-5)")
    parser.add_argument("--max-length", type=int,   default=256)
    parser.add_argument("--fp16",       action="store_true", default=True,
                        help="Mixed precision (GPU only)")
    parser.add_argument("--no-fp16",    dest="fp16", action="store_false")
    args = parser.parse_args()

    print("=== NLLB Fine-tuning (from local checkpoint) ===\n")

    directions = ["en2lun", "lun2en"] if args.direction == "both" else [args.direction]
    for direction in directions:
        train_direction(direction, args)

    print("\nFine-tuning complete.")
    print("To push updated models to HuggingFace, run: python upload_models_to_hf.py")


if __name__ == "__main__":
    main()
