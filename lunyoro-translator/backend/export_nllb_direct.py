"""
export_nllb_direct.py
=====================
Direct ONNX export for NLLB (M2M100) models using torch.onnx.export,
bypassing the broken optimum library on Python 3.14.

Produces encoder_model.onnx and decoder_model.onnx in model/<direction>_onnx/,
compatible with the Pi's C++ onnxruntime backend.

Usage:
    python export_nllb_direct.py                        # both directions
    python export_nllb_direct.py --direction nllb_en2lun
"""

import argparse
import shutil
import time
from pathlib import Path

import torch
from transformers import M2M100ForConditionalGeneration, AutoTokenizer

BASE = Path(__file__).parent
MODEL_DIR = BASE / "model"

NLLB_DIRECTIONS = ["nllb_en2lun", "nllb_lun2en"]

SIDECAR_FILES = [
    "sentencepiece.bpe.model",
    "tokenizer.json",
    "tokenizer_config.json",
    "special_tokens_map.json",
    "vocab.json",
    "config.json",
    "generation_config.json",
]


def export_encoder(model, dst: Path, seq_len: int = 32):
    """Export the encoder subgraph."""
    dst.mkdir(parents=True, exist_ok=True)
    out_path = dst / "encoder_model.onnx"

    if out_path.exists():
        print(f"    [OK] encoder_model.onnx already exists")
        return

    print(f"    Exporting encoder ...", flush=True)
    encoder = model.get_encoder()
    encoder.eval()

    # Dummy inputs
    input_ids = torch.ones(1, seq_len, dtype=torch.long)
    attention_mask = torch.ones(1, seq_len, dtype=torch.long)

    with torch.no_grad():
        torch.onnx.export(
            encoder,
            (input_ids, attention_mask),
            str(out_path),
            input_names=["input_ids", "attention_mask"],
            output_names=["last_hidden_state"],
            dynamic_axes={
                "input_ids": {0: "batch_size", 1: "sequence_length"},
                "attention_mask": {0: "batch_size", 1: "sequence_length"},
                "last_hidden_state": {0: "batch_size", 1: "sequence_length"},
            },
            opset_version=14,
            do_constant_folding=True,
            dynamo=False,  # Force legacy TorchScript exporter
        )

    size_mb = out_path.stat().st_size / 1e6
    print(f"    [OK] encoder_model.onnx: {size_mb:.0f}MB", flush=True)


def export_decoder(model, dst: Path, enc_seq_len: int = 32, dec_seq_len: int = 1):
    """Export the decoder subgraph (no KV cache / past)."""
    dst.mkdir(parents=True, exist_ok=True)
    out_path = dst / "decoder_model.onnx"

    if out_path.exists():
        print(f"    [OK] decoder_model.onnx already exists")
        return

    print(f"    Exporting decoder ...", flush=True)
    decoder = model.get_decoder()
    decoder.eval()

    # Dummy inputs
    decoder_input_ids = torch.ones(1, dec_seq_len, dtype=torch.long)
    encoder_hidden_states = torch.randn(1, enc_seq_len, model.config.d_model)
    encoder_attention_mask = torch.ones(1, enc_seq_len, dtype=torch.long)

    class DecoderWrapper(torch.nn.Module):
        """Wrapper to match the expected ONNX output format."""
        def __init__(self, decoder, lm_head, final_logits_bias=None):
            super().__init__()
            self.decoder = decoder
            self.lm_head = lm_head
            self.final_logits_bias = final_logits_bias

        def forward(self, input_ids, encoder_hidden_states, encoder_attention_mask):
            decoder_out = self.decoder(
                input_ids=input_ids,
                encoder_hidden_states=encoder_hidden_states,
                encoder_attention_mask=encoder_attention_mask,
                return_dict=True,
            )
            logits = self.lm_head(decoder_out.last_hidden_state)
            if self.final_logits_bias is not None:
                logits = logits + self.final_logits_bias
            return logits

    # Get lm_head - for M2M100/NLLB with tied embeddings, it's the shared embedding
    if hasattr(model, 'lm_head'):
        lm_head = model.lm_head
    else:
        lm_head = model.model.shared  # tied embeddings

    final_logits_bias = getattr(model, 'final_logits_bias', None)

    wrapper = DecoderWrapper(decoder, lm_head, final_logits_bias)
    wrapper.eval()

    with torch.no_grad():
        torch.onnx.export(
            wrapper,
            (decoder_input_ids, encoder_hidden_states, encoder_attention_mask),
            str(out_path),
            input_names=["input_ids", "encoder_hidden_states", "encoder_attention_mask"],
            output_names=["logits"],
            dynamic_axes={
                "input_ids": {0: "batch_size", 1: "decoder_sequence_length"},
                "encoder_hidden_states": {0: "batch_size", 1: "encoder_sequence_length"},
                "encoder_attention_mask": {0: "batch_size", 1: "encoder_sequence_length"},
                "logits": {0: "batch_size", 1: "decoder_sequence_length"},
            },
            opset_version=14,
            do_constant_folding=True,
            dynamo=False,  # Force legacy TorchScript exporter
        )

    size_mb = out_path.stat().st_size / 1e6
    # Check for external data file too
    data_file = dst / "decoder_model.onnx_data"
    if data_file.exists():
        size_mb += data_file.stat().st_size / 1e6
    print(f"    [OK] decoder_model.onnx: {size_mb:.0f}MB", flush=True)


def export_direction(direction: str) -> Path | None:
    src = MODEL_DIR / direction
    dst = MODEL_DIR / f"{direction}_onnx"

    if not src.is_dir():
        print(f"  [SKIP] source model not found: {src}")
        return None

    print(f"  Loading {direction} ...", flush=True)
    t0 = time.time()
    model = M2M100ForConditionalGeneration.from_pretrained(
        str(src), torch_dtype=torch.float32
    )
    model.eval()
    print(f"  Loaded in {time.time() - t0:.1f}s", flush=True)

    export_encoder(model, dst)
    export_decoder(model, dst)

    # Copy sidecar files
    for name in SIDECAR_FILES:
        f = src / name
        if f.is_file():
            shutil.copy2(f, dst / name)

    total_mb = sum(f.stat().st_size for f in dst.rglob("*") if f.is_file()) / 1e6
    print(f"  [OK] {dst.name}: {total_mb:.0f}MB total", flush=True)

    # Clean up memory
    del model
    if torch.cuda.is_available():
        torch.cuda.empty_cache()

    return dst


def verify(direction: str, onnx_dir: Path, text: str):
    """Quick sanity check using onnxruntime."""
    import onnxruntime as ort
    import numpy as np

    tokenizer = AutoTokenizer.from_pretrained(str(MODEL_DIR / direction))

    enc_sess = ort.InferenceSession(str(onnx_dir / "encoder_model.onnx"))
    dec_sess = ort.InferenceSession(str(onnx_dir / "decoder_model.onnx"))

    inputs = tokenizer(text, return_tensors="np")
    input_ids = inputs["input_ids"]
    attention_mask = inputs["attention_mask"]

    # Encode
    enc_out = enc_sess.run(None, {
        "input_ids": input_ids,
        "attention_mask": attention_mask,
    })
    encoder_hidden_states = enc_out[0]

    # Greedy decode
    decoder_input_ids = np.array([[2]], dtype=np.int64)  # decoder_start_token_id
    max_tokens = 64
    output_ids = [2]

    for _ in range(max_tokens):
        logits = dec_sess.run(None, {
            "input_ids": decoder_input_ids,
            "encoder_hidden_states": encoder_hidden_states,
            "encoder_attention_mask": attention_mask,
        })[0]
        next_token = int(np.argmax(logits[0, -1, :]))
        if next_token == 2:  # eos
            break
        output_ids.append(next_token)
        decoder_input_ids = np.array([output_ids], dtype=np.int64)

    result = tokenizer.decode(output_ids, skip_special_tokens=True)
    print(f"    [{direction}] {text!r} -> {result!r}", flush=True)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--direction", help="Export a single direction only")
    ap.add_argument("--verify", action="store_true", help="Run a test translation after export")
    ap.add_argument("--force", action="store_true", help="Re-export even if ONNX files exist")
    args = ap.parse_args()

    directions = [args.direction] if args.direction else NLLB_DIRECTIONS

    print(f"=== Direct ONNX export (fp32): {', '.join(directions)} ===")
    for d in directions:
        print(f"\n[{d}]")
        if args.force:
            dst = MODEL_DIR / f"{d}_onnx"
            if dst.exists():
                shutil.rmtree(dst)
        onnx_dir = export_direction(d)
        if onnx_dir and args.verify:
            probe = "Oli ota" if "lun2en" in d else "Good morning, my friend."
            verify(d, onnx_dir, probe)

    print("\nDone.")
