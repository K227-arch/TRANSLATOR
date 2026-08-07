"""
verify_pi_models.py
===================
Reference implementation of the inference path the Raspberry Pi C++ backend
uses, run against the quantized ONNX models before they ship.

Deliberately mirrors the C++ constraints rather than using optimum/generate():
  - two sessions per direction (encoder + decoder), no decoder_with_past
  - greedy decoding, no KV cache (the full decoder re-runs each step)
  - sequence cap, as in translator_v2.cpp

If this produces sane translations, the C++ port has a correct target to match.
Any divergence here is a model/export problem, not a C++ bug — which is exactly
the distinction worth establishing before writing the C++.

Usage:
    python verify_pi_models.py --model-dir model/nllb_en2lun_pi --src eng_Latn --tgt nyk_Latn
    python verify_pi_models.py --all
"""

import argparse
import time
from pathlib import Path

import numpy as np
import onnxruntime as ort
from transformers import AutoTokenizer

BASE = Path(__file__).parent
MODEL_DIR = BASE / "model"

MAX_LENGTH = 200  # matches max_length_ in translator_v2.cpp

# (model dir, source lang, target lang, probe sentence)
SUITE = [
    ("nllb_en2lun_pi", "eng_Latn", "nyk_Latn", "Good morning, my friend."),
    ("nllb_lun2en_pi", "nyk_Latn", "eng_Latn", "Oli ota"),
]


def make_session(path: Path, threads: int = 4) -> ort.InferenceSession:
    opts = ort.SessionOptions()
    opts.intra_op_num_threads = threads
    opts.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
    return ort.InferenceSession(str(path), opts, providers=["CPUExecutionProvider"])


def greedy_translate(model_dir: Path, src_lang: str, tgt_lang: str, text: str) -> tuple[str, float]:
    tok = AutoTokenizer.from_pretrained(str(model_dir), src_lang=src_lang)
    encoder = make_session(model_dir / "encoder_model_quantized.onnx")
    decoder = make_session(model_dir / "decoder_model_quantized.onnx")

    enc_inputs = {i.name for i in encoder.get_inputs()}
    dec_inputs = {i.name for i in decoder.get_inputs()}

    batch = tok(text, return_tensors="np")
    input_ids = batch["input_ids"].astype(np.int64)
    attention_mask = batch["attention_mask"].astype(np.int64)

    t0 = time.time()

    feed = {"input_ids": input_ids, "attention_mask": attention_mask}
    hidden = encoder.run(None, {k: v for k, v in feed.items() if k in enc_inputs})[0]

    # NLLB starts generation with </s> then the target language token.
    tgt_id = tok.convert_tokens_to_ids(tgt_lang)
    generated = [tok.eos_token_id, tgt_id]

    for _ in range(MAX_LENGTH):
        dec_feed = {
            "input_ids": np.array([generated], dtype=np.int64),
            "encoder_hidden_states": hidden,
            "encoder_attention_mask": attention_mask,
        }
        logits = decoder.run(None, {k: v for k, v in dec_feed.items() if k in dec_inputs})[0]
        next_id = int(np.argmax(logits[0, -1]))
        if next_id == tok.eos_token_id:
            break
        generated.append(next_id)

    elapsed = time.time() - t0
    # Drop the two forced prefix tokens before decoding.
    out = tok.decode(generated[2:], skip_special_tokens=True)
    return out, elapsed


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--model-dir")
    ap.add_argument("--src")
    ap.add_argument("--tgt")
    ap.add_argument("--text")
    ap.add_argument("--all", action="store_true", help="Run the built-in probe suite")
    args = ap.parse_args()

    if args.all:
        cases = SUITE
    else:
        if not (args.model_dir and args.src and args.tgt):
            ap.error("--model-dir, --src and --tgt are required unless --all is given")
        cases = [(args.model_dir, args.src, args.tgt, args.text or "Good morning, my friend.")]

    for name, src, tgt, probe in cases:
        # Accept a bare model name, a repo-relative path, or an absolute one.
        path = Path(name)
        if not path.is_dir():
            path = MODEL_DIR / name
        if not path.is_dir():
            print(f"[SKIP] {name} not found")
            continue
        print(f"\n[{path.name}] {src} -> {tgt}")
        try:
            out, elapsed = greedy_translate(path, src, tgt, probe)
            print(f"  {probe!r}\n  -> {out!r}  ({elapsed:.2f}s, greedy, no KV cache)")
        except Exception as e:
            print(f"  [FAIL] {type(e).__name__}: {e}")
