"""
export_marian_direct.py
=======================
Direct ONNX export for MarianMT models using torch.onnx.export,
bypassing the broken optimum library on Python 3.14.

Usage:
    python export_marian_direct.py                  # both directions
    python export_marian_direct.py --direction en2lun
    python export_marian_direct.py --force          # re-export even if exists
"""
import argparse
import shutil
import time
from pathlib import Path

import torch
from transformers import MarianMTModel, MarianTokenizer

BASE = Path(__file__).parent
MODEL_DIR = BASE / "model"
DIRECTIONS = ["en2lun", "lun2en"]

SIDECAR_FILES = [
    "source.spm", "target.spm", "tokenizer.json", "tokenizer_config.json",
    "special_tokens_map.json", "vocab.json", "config.json", "generation_config.json",
]


def export_encoder(model, dst: Path, seq_len: int = 32):
    out_path = dst / "encoder_model.onnx"
    if out_path.exists():
        print(f"    [OK] encoder_model.onnx already exists")
        return
    print(f"    Exporting encoder ...", flush=True)
    encoder = model.get_encoder()
    encoder.eval()
    input_ids = torch.ones(1, seq_len, dtype=torch.long)
    attention_mask = torch.ones(1, seq_len, dtype=torch.long)
    with torch.no_grad():
        torch.onnx.export(
            encoder, (input_ids, attention_mask), str(out_path),
            input_names=["input_ids", "attention_mask"],
            output_names=["last_hidden_state"],
            dynamic_axes={
                "input_ids": {0: "batch_size", 1: "sequence_length"},
                "attention_mask": {0: "batch_size", 1: "sequence_length"},
                "last_hidden_state": {0: "batch_size", 1: "sequence_length"},
            },
            opset_version=14, do_constant_folding=True, dynamo=False,
        )
    print(f"    [OK] encoder_model.onnx: {out_path.stat().st_size/1e6:.0f}MB", flush=True)


def export_decoder(model, dst: Path, enc_seq_len: int = 32):
    out_path = dst / "decoder_model.onnx"
    if out_path.exists():
        print(f"    [OK] decoder_model.onnx already exists")
        return
    print(f"    Exporting decoder ...", flush=True)
    decoder = model.get_decoder()
    decoder.eval()
    d_model = model.config.d_model

    class DecoderWrapper(torch.nn.Module):
        def __init__(self, decoder, lm_head):
            super().__init__()
            self.decoder = decoder
            self.lm_head = lm_head

        def forward(self, input_ids, encoder_hidden_states, encoder_attention_mask):
            out = self.decoder(
                input_ids=input_ids,
                encoder_hidden_states=encoder_hidden_states,
                encoder_attention_mask=encoder_attention_mask,
                return_dict=True,
            )
            return self.lm_head(out.last_hidden_state)

    wrapper = DecoderWrapper(decoder, model.lm_head).eval()
    decoder_input_ids = torch.ones(1, 1, dtype=torch.long)
    encoder_hidden_states = torch.randn(1, enc_seq_len, d_model)
    encoder_attention_mask = torch.ones(1, enc_seq_len, dtype=torch.long)

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
            opset_version=14, do_constant_folding=True, dynamo=False,
        )
    print(f"    [OK] decoder_model.onnx: {out_path.stat().st_size/1e6:.0f}MB", flush=True)


def export_direction(direction: str, force: bool = False) -> Path:
    src = MODEL_DIR / direction
    dst = MODEL_DIR / f"{direction}_onnx"

    if not src.is_dir():
        print(f"  [SKIP] source not found: {src}")
        return None

    if force and dst.exists():
        shutil.rmtree(dst)
        print(f"  Cleared old {dst.name}")

    dst.mkdir(parents=True, exist_ok=True)

    print(f"  Loading {direction} ...", flush=True)
    t0 = time.time()
    model = MarianMTModel.from_pretrained(str(src))
    model.eval()
    print(f"  Loaded in {time.time()-t0:.1f}s", flush=True)

    export_encoder(model, dst)
    export_decoder(model, dst)

    for name in SIDECAR_FILES:
        f = src / name
        if f.is_file():
            shutil.copy2(f, dst / name)

    total = sum(f.stat().st_size for f in dst.rglob("*") if f.is_file()) / 1e6
    print(f"  [OK] {dst.name}: {total:.0f}MB total", flush=True)

    del model
    if torch.cuda.is_available():
        torch.cuda.empty_cache()

    return dst


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--direction", help="Export single direction only")
    ap.add_argument("--force", action="store_true", help="Re-export even if exists")
    args = ap.parse_args()

    directions = [args.direction] if args.direction else DIRECTIONS
    print(f"=== Marian ONNX export: {', '.join(directions)} ===")
    for d in directions:
        print(f"\n[{d}]")
        export_direction(d, force=args.force)
    print("\nDone.")
