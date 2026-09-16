"""Hook greeting correction into _nllb_translate."""
path = "translate.py"
with open(path, "rb") as f:
    raw = f.read()

# Find the docstring + first line of _nllb_translate
marker = b'    """Run inference with a fine-tuned NLLB model.\n    Falls back to HF Inference API when local model is unavailable."""'
replacement = b'    """Run inference with a fine-tuned NLLB model.\n    Falls back to HF Inference API when local model is unavailable."""\n    # \xe2\x94\x80\xe2\x94\x80 Greeting shortcut \xe2\x80\x94 skip neural model for common phrases \xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\n    _greeting = _apply_greeting_correction(text, direction)\n    if _greeting:\n        return _greeting'

if marker in raw:
    raw = raw.replace(marker, replacement, 1)
    with open(path, "wb") as f:
        f.write(raw)
    print("Hook added to _nllb_translate")
else:
    print("marker not found")
