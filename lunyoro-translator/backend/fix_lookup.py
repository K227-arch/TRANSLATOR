"""Patch lookup_word to use NLLB as primary model."""
path = "translate.py"

with open(path, "r", encoding="utf-8") as f:
    content = f.read()

# Find the block to replace
marker = "raw_mt = _mt_translate(word, mt_direction)\n    mt_translation = clean_mt(raw_mt)"

replacement = (
    "# Use NLLB as primary (consistent with /translate), Marian as fallback\n"
    "    raw_nllb = _nllb_translate(word, mt_direction)\n"
    "    raw_mt   = _mt_translate(word, mt_direction)\n"
    "    raw_primary = raw_nllb if (raw_nllb and not _is_garbage(raw_nllb)) else raw_mt\n"
    "    mt_translation = clean_mt(raw_primary)"
)

if marker in content:
    content = content.replace(marker, replacement, 1)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print("OK — lookup_word now uses NLLB as primary")
else:
    print("ERROR — marker not found")
    idx = content.find("_mt_translate(word, mt_direction)")
    print("Found at:", idx)
    print(repr(content[idx-50:idx+80]))
