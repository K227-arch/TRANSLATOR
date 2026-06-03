"""
fix_nllb_embeddings.py
======================
Fixes the NLLB embedding size mismatch between the saved checkpoint (256206)
and the tokenizer (256205 after adding nyo_Latn).

The issue: when nyo_Latn was added, the original model had vocab_size=256206
(from a previous resize), but the new tokenizer has 256205.
This script resizes the model to exactly match the tokenizer.
"""
import torch
from pathlib import Path
from transformers import NllbTokenizer, AutoModelForSeq2SeqLM

BASE = Path(__file__).parent
MODEL_DIR = BASE / "model"

for direction in ["en2lun", "lun2en"]:
    model_path = MODEL_DIR / f"nllb_{direction}"
    print(f"\nFixing nllb_{direction}...")

    tokenizer = NllbTokenizer.from_pretrained(str(model_path))
    tok_vocab  = len(tokenizer)
    print(f"  Tokenizer vocab size: {tok_vocab}")

    model = AutoModelForSeq2SeqLM.from_pretrained(
        str(model_path), ignore_mismatched_sizes=True
    )
    old_size = model.config.vocab_size
    print(f"  Model vocab size:     {old_size}")

    if old_size == tok_vocab:
        print(f"  Already correct — skipping")
        continue

    print(f"  Resizing {old_size} -> {tok_vocab}...")
    model.resize_token_embeddings(tok_vocab)
    model.config.vocab_size = tok_vocab

    # Re-initialize the nyo_Latn embedding from Bantu language average
    nyo_id = tokenizer.convert_tokens_to_ids("nyo_Latn")
    run_id = tokenizer.convert_tokens_to_ids("run_Latn")
    lug_id = tokenizer.convert_tokens_to_ids("lug_Latn")
    kin_id = tokenizer.convert_tokens_to_ids("kin_Latn")
    unk_id = tokenizer.unk_token_id

    ref_ids = [x for x in [run_id, lug_id, kin_id] if x != unk_id]
    if nyo_id != unk_id and ref_ids:
        with torch.no_grad():
            shared_emb = model.model.shared.weight
            ref_emb = shared_emb[ref_ids].mean(dim=0)
            model.model.shared.weight[nyo_id] = ref_emb
        print(f"  nyo_Latn (ID={nyo_id}) embedding set from avg of {ref_ids}")

    import shutil
    backup = str(model_path) + "_pre_fix"
    if not Path(backup).exists():
        shutil.copytree(str(model_path), backup,
                        ignore=shutil.ignore_patterns("best_checkpoint", "*_pre_*"))
        print(f"  Backup: {backup}")

    tokenizer.save_pretrained(str(model_path))
    model.save_pretrained(str(model_path))
    print(f"  Saved. vocab_size={tok_vocab}")

print("\nAll NLLB models fixed. Run training with --resize-embeddings flag.")
