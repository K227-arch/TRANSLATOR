"""
add_runyoro_token.py
====================
Adds 'nyo_Latn' (Runyoro-Rutooro) as a custom language token to the NLLB tokenizer
and resizes model embeddings accordingly.

This allows NLLB to use proper Runyoro/Rutooro language guidance instead of
relying on Luganda (lug_Latn) or the previous invalid nyn_Latn (which mapped to UNK).

After running this:
  - train_nllb.py will use 'nyo_Latn' as the target language token
  - The model will learn Runyoro-Rutooro as its own language identity
  - No more proxy language code needed

Usage:
    python add_runyoro_token.py                 # updates both nllb_en2lun + nllb_lun2en
    python add_runyoro_token.py --verify        # check token was added correctly
"""

import os
import argparse
import torch
from pathlib import Path

BASE      = Path(__file__).parent
MODEL_DIR = BASE / "model"
NEW_LANG_TOKEN = "nyo_Latn"   # Runyoro-Rutooro custom language code


def add_token_to_model(direction: str, verify: bool = False):
    """Add nyo_Latn token to NLLB tokenizer + resize model embeddings."""
    from transformers import NllbTokenizer, AutoModelForSeq2SeqLM

    model_path = MODEL_DIR / f"nllb_{direction}"
    if not model_path.is_dir():
        print(f"  Model not found: {model_path}")
        return False

    print(f"\n  Loading nllb_{direction} from {model_path}...")
    tokenizer = NllbTokenizer.from_pretrained(str(model_path))

    # Check if token already exists
    existing_id = tokenizer.convert_tokens_to_ids(NEW_LANG_TOKEN)
    unk_id = tokenizer.unk_token_id

    if existing_id != unk_id:
        print(f"  '{NEW_LANG_TOKEN}' already in vocab (ID={existing_id}) - skipping add")
        if verify:
            _verify(tokenizer, model_path, direction)
        return True

    print(f"  '{NEW_LANG_TOKEN}' not in vocab (maps to UNK={unk_id}) - adding now...")

    # Add the new language token
    tokenizer.add_special_tokens({"additional_special_tokens": [NEW_LANG_TOKEN]})
    new_id = tokenizer.convert_tokens_to_ids(NEW_LANG_TOKEN)
    print(f"  Added '{NEW_LANG_TOKEN}' with ID={new_id}")

    # Load model and resize embeddings
    print(f"  Loading model and resizing embeddings ({tokenizer.vocab_size} -> {len(tokenizer)})...")
    model = AutoModelForSeq2SeqLM.from_pretrained(str(model_path))
    old_vocab_size = model.config.vocab_size
    model.resize_token_embeddings(len(tokenizer))
    model.config.vocab_size = len(tokenizer)
    print(f"  Embeddings resized: {old_vocab_size} -> {model.config.vocab_size}")

    # Initialize the new token embedding as the average of related language tokens
    # Use run_Latn (Rundi) and lug_Latn (Luganda) as reference — both Bantu
    with torch.no_grad():
        run_id = tokenizer.convert_tokens_to_ids("run_Latn")
        lug_id = tokenizer.convert_tokens_to_ids("lug_Latn")
        kin_id = tokenizer.convert_tokens_to_ids("kin_Latn")

        # Average embedding of 3 related Bantu language tokens
        ref_ids = [x for x in [run_id, lug_id, kin_id] if x != unk_id]
        if ref_ids:
            shared_emb = model.model.shared.weight
            ref_emb = shared_emb[ref_ids].mean(dim=0)
            model.model.shared.weight[new_id] = ref_emb
            # Also initialize encoder/decoder embed_tokens if separate
            if hasattr(model.model.encoder, 'embed_tokens'):
                model.model.encoder.embed_tokens.weight[new_id] = ref_emb
            if hasattr(model.model.decoder, 'embed_tokens'):
                model.model.decoder.embed_tokens.weight[new_id] = ref_emb
            print(f"  Initialized '{NEW_LANG_TOKEN}' embedding as avg of "
                  f"run_Latn({run_id}), lug_Latn({lug_id}), kin_Latn({kin_id})")
        else:
            print(f"  Warning: no reference tokens found, using random init")

    # Save updated tokenizer and model
    print(f"  Saving updated tokenizer + model to {model_path}...")
    import shutil
    backup = str(model_path) + "_pre_nyo"
    if not Path(backup).exists():
        shutil.copytree(str(model_path), backup,
                        ignore=shutil.ignore_patterns("best_checkpoint"))
        print(f"  Backup saved to {backup}")

    tokenizer.save_pretrained(str(model_path))
    model.save_pretrained(str(model_path))
    print(f"  Saved successfully.")

    if verify:
        _verify(tokenizer, model_path, direction)
    return True


def _verify(tokenizer, model_path, direction):
    """Verify the token was added correctly."""
    print(f"\n  Verifying nllb_{direction}...")
    tok_id = tokenizer.convert_tokens_to_ids(NEW_LANG_TOKEN)
    unk_id = tokenizer.unk_token_id
    status = "VALID" if tok_id != unk_id else "STILL UNK - FAILED"
    print(f"  '{NEW_LANG_TOKEN}' ID={tok_id}  UNK={unk_id}  Status={status}")
    print(f"  Vocab size: {len(tokenizer):,}")

    # Test generation
    try:
        from transformers import AutoModelForSeq2SeqLM
        model = AutoModelForSeq2SeqLM.from_pretrained(str(model_path)).eval()
        src_text = "I go to school"
        tokenizer.src_lang = "eng_Latn"
        inputs = tokenizer(src_text, return_tensors="pt")
        forced_bos = tokenizer.convert_tokens_to_ids(NEW_LANG_TOKEN)
        with torch.no_grad():
            out = model.generate(**inputs, forced_bos_token_id=forced_bos,
                                 num_beams=4, max_length=64)
        decoded = tokenizer.decode(out[0], skip_special_tokens=True)
        print(f"  Test: '{src_text}' -> '{decoded}'")
    except Exception as e:
        print(f"  Test generation failed: {e}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--verify", action="store_true",
                        help="Verify token was added and test generation")
    parser.add_argument("--direction", type=str, default="both",
                        choices=["en2lun", "lun2en", "both"])
    args = parser.parse_args()

    print(f"\n{'='*60}")
    print(f"  ADDING '{NEW_LANG_TOKEN}' (Runyoro-Rutooro) TO NLLB TOKENIZER")
    print(f"{'='*60}")
    print(f"\nThis replaces the invalid nyn_Latn (UNK) with a proper")
    print(f"Runyoro-Rutooro language token initialized from related Bantu languages.")

    directions = ["en2lun", "lun2en"] if args.direction == "both" else [args.direction]
    for direction in directions:
        add_token_to_model(direction, verify=args.verify)

    print(f"\n{'='*60}")
    print(f"  DONE. Update train_nllb.py and translate.py:")
    print(f"  NLLB_LANG_LUN = '{NEW_LANG_TOKEN}'")
    print(f"{'='*60}")
    print(f"\nNext: retrain NLLB with --resize-embeddings flag to fine-tune")
    print(f"the new token embedding on actual Runyoro-Rutooro data.")
    print(f"  python train_nllb.py --direction both --epochs 5 --resize-embeddings")


if __name__ == "__main__":
    main()
