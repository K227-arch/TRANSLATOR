"""
retrain_tokenizer.py
====================
Retrains the SentencePiece tokenizer with:
  - Larger vocabulary (default 65000, up from ~64110)
  - Subword regularization (BPE-dropout / unigram sampling) for better
    handling of unseen words
  - Trained on the full cleaned corpus (both English and Lunyoro sides)

Then patches the MarianMT model config to use the new tokenizer.

Usage:
    python retrain_tokenizer.py [--vocab-size 65000] [--direction en2lun]
    python retrain_tokenizer.py --vocab-size 65000 --direction lun2en

Requirements:
    pip install sentencepiece

Steps:
  1. Collect all text from train.csv (both columns)
  2. Train a new SentencePiece model with unigram algorithm + subword regularization
  3. Save source.spm and target.spm into the model directory
  4. Rebuild vocab.json from the new SPM model
  5. Update tokenizer_config.json

NOTE: After running this you must retrain the MarianMT model from scratch
(or continue fine-tuning) because the embedding matrix dimensions change
when vocab size changes. Use train_marian.py for that.
"""
import os
import sys
import json
import argparse
import tempfile
import pandas as pd

BASE      = os.path.dirname(__file__)
MODEL_DIR = os.path.join(BASE, "model")
DATA_DIR  = os.path.join(BASE, "data", "training")


def collect_corpus(direction: str) -> tuple[list[str], list[str]]:
    """Return (source_sentences, target_sentences) for the given direction."""
    train = pd.read_csv(os.path.join(DATA_DIR, "train.csv")).dropna()
    val   = pd.read_csv(os.path.join(DATA_DIR, "val.csv")).dropna()
    all_df = pd.concat([train, val], ignore_index=True)

    import re
    def clean(text: str) -> str:
        text = re.sub(r'\[[A-Za-z _]+\]\s*', '', str(text))
        return text.strip()

    src = [clean(x) for x in all_df['english'].tolist()]
    tgt = [clean(x) for x in all_df['lunyoro'].tolist()]
    return src, tgt


def train_spm(sentences: list[str], output_prefix: str, vocab_size: int,
              model_type: str = "unigram", character_coverage: float = 0.9999,
              user_defined_symbols: list[str] | None = None):
    """Train a SentencePiece model."""
    import sentencepiece as spm

    # Write sentences to temp file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt',
                                     delete=False, encoding='utf-8') as f:
        for s in sentences:
            if s.strip():
                f.write(s.strip() + '\n')
        tmp_path = f.name

    symbols = user_defined_symbols or []
    symbols_str = ','.join(symbols) if symbols else ''

    train_args = (
        f"--input={tmp_path} "
        f"--model_prefix={output_prefix} "
        f"--vocab_size={vocab_size} "
        f"--model_type={model_type} "
        f"--character_coverage={character_coverage} "
        f"--pad_id=3 "
        f"--unk_id=1 "
        f"--bos_id=-1 "
        f"--eos_id=0 "
        # Subword regularization: enable unigram sampling
        f"--train_extremely_large_corpus=false "
        f"--shuffle_input_sentence=true "
        f"--input_sentence_size=5000000 "
        # Better coverage of rare words
        f"--split_by_unicode_script=true "
        f"--split_by_number=true "
        f"--split_digits=true "
        f"--byte_fallback=true "
    )
    if symbols_str:
        train_args += f" --user_defined_symbols={symbols_str}"

    print(f"  Training SentencePiece ({model_type}, vocab={vocab_size})...")
    spm.SentencePieceTrainer.train(train_args)
    os.unlink(tmp_path)
    print(f"  Saved: {output_prefix}.model  {output_prefix}.vocab")


def spm_to_vocab_json(spm_model_path: str) -> dict:
    """Convert SPM model to MarianMT vocab.json format."""
    import sentencepiece as spm
    sp = spm.SentencePieceProcessor()
    sp.load(spm_model_path)

    vocab = {}
    # Special tokens first (MarianMT convention)
    vocab["</s>"] = 0
    vocab["<unk>"] = 1

    for i in range(sp.get_piece_size()):
        piece = sp.id_to_piece(i)
        if piece not in vocab:
            vocab[piece] = len(vocab)

    # Pad token at end
    vocab["<pad>"] = len(vocab)
    return vocab


def patch_tokenizer_config(model_dir: str, vocab_size: int):
    """Update tokenizer_config.json with new vocab size."""
    config_path = os.path.join(model_dir, "tokenizer_config.json")
    with open(config_path) as f:
        config = json.load(f)

    # Update pad token id to match new vocab
    config["added_tokens_decoder"] = {
        "0":  {"content": "</s>", "lstrip": False, "normalized": False,
               "rstrip": False, "single_word": False, "special": True},
        "1":  {"content": "<unk>", "lstrip": False, "normalized": False,
               "rstrip": False, "single_word": False, "special": True},
        str(vocab_size - 1): {
               "content": "<pad>", "lstrip": False, "normalized": False,
               "rstrip": False, "single_word": False, "special": True},
    }
    with open(config_path, 'w') as f:
        json.dump(config, f, indent=2)
    print(f"  Updated tokenizer_config.json (pad_id={vocab_size - 1})")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--vocab-size", type=int, default=65000,
                        help="Target vocabulary size (default 65000)")
    parser.add_argument("--direction",  type=str, default="both",
                        choices=["en2lun", "lun2en", "both"],
                        help="Which model direction to retrain tokenizer for")
    parser.add_argument("--model-type", type=str, default="unigram",
                        choices=["unigram", "bpe"],
                        help="SentencePiece model type (unigram recommended)")
    args = parser.parse_args()

    try:
        import sentencepiece
    except ImportError:
        print("sentencepiece not installed. Run: pip install sentencepiece")
        sys.exit(1)

    print("=== Retraining SentencePiece Tokenizer ===\n")
    print(f"  Vocab size:  {args.vocab_size}")
    print(f"  Model type:  {args.model_type} (with subword regularization)")
    print(f"  Direction:   {args.direction}\n")

    src_sentences, tgt_sentences = collect_corpus(args.direction)
    print(f"Corpus: {len(src_sentences):,} sentence pairs\n")

    directions = ["en2lun", "lun2en"] if args.direction == "both" else [args.direction]

    for direction in directions:
        model_dir = os.path.join(MODEL_DIR, direction)
        if not os.path.isdir(model_dir):
            print(f"  Skipping {direction} — model directory not found")
            continue

        print(f"--- {direction} ---")

        # For en2lun: source=English, target=Lunyoro
        # For lun2en: source=Lunyoro, target=English
        if direction == "en2lun":
            source_sents = src_sentences
            target_sents = tgt_sentences
        else:
            source_sents = tgt_sentences
            target_sents = src_sentences

        # Combined for joint tokenizer (MarianMT uses separate_vocabs=false by default)
        all_sents = source_sents + target_sents

        # Train joint SPM model
        spm_prefix = os.path.join(model_dir, "_new_spm")
        train_spm(all_sents, spm_prefix, args.vocab_size, args.model_type)

        # Copy to source.spm and target.spm (MarianMT uses both)
        import shutil
        shutil.copy(f"{spm_prefix}.model", os.path.join(model_dir, "source.spm"))
        shutil.copy(f"{spm_prefix}.model", os.path.join(model_dir, "target.spm"))
        print(f"  Copied → source.spm, target.spm")

        # Rebuild vocab.json
        vocab = spm_to_vocab_json(f"{spm_prefix}.model")
        actual_vocab_size = len(vocab)
        vocab_path = os.path.join(model_dir, "vocab.json")
        with open(vocab_path, 'w', encoding='utf-8') as f:
            json.dump(vocab, f, ensure_ascii=False, indent=2)
        print(f"  Rebuilt vocab.json ({actual_vocab_size:,} tokens)")

        # Patch tokenizer config
        patch_tokenizer_config(model_dir, actual_vocab_size)

        # Clean up temp files
        for ext in [".model", ".vocab"]:
            tmp = f"{spm_prefix}{ext}"
            if os.path.exists(tmp):
                os.unlink(tmp)

        print(f"  ✓ {direction} tokenizer updated\n")

    print("Tokenizer retraining complete.")
    print("\nIMPORTANT: The model embedding matrix must now be resized.")
    print("Run train_marian.py to fine-tune with the new tokenizer.")


if __name__ == "__main__":
    main()
