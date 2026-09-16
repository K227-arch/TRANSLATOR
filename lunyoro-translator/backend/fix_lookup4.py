"""Patch lookup_word fuzzy search to only use entries with English definitions."""
path = "translate.py"

with open(path, "r", encoding="utf-8") as f:
    content = f.read()

# The arrow in the file is the mojibake sequence â†' which in UTF-8 is \xe2\x86\x92
# but when read as UTF-8 string it becomes the single char â†' (3 bytes decoded wrong)
# Let's just find by the process.extract call and replace the whole block

marker_start = '    if direction == "en\u00e2\u0086\x92lun":\n        fuzzy_raw = process.extract(\n            word_lower,\n            [(d.get("definitionEnglish") or "").lower() for d in _dictionary],'
marker_end = '                ))\n    else:'

# Find actual content between markers
start_idx = content.find('fuzzy_raw = process.extract(\n            word_lower,\n            [(d.get("definitionEnglish") or "").lower() for d in _dictionary],')
if start_idx == -1:
    # Try finding by unique substring
    start_idx = content.find('[(d.get("definitionEnglish") or "").lower() for d in _dictionary],\n            scorer=fuzz.token_sort_ratio,')
    print('Found at:', start_idx)
else:
    print('Found at:', start_idx)

if start_idx != -1:
    # Replace _dictionary with _def_entries and add the filter
    old_chunk = '[(d.get("definitionEnglish") or "").lower() for d in _dictionary],\n            scorer=fuzz.token_sort_ratio,\n            limit=10,\n            score_cutoff=70,\n        )\n        for match_text, score, _ in fuzzy_raw:\n            entry = _index["_dict_def_map"].get(match_text)\n            if entry and entry["word"] not in seen_words:\n                seen_words.add(entry["word"])\n                results.append(\n                    {\n                        **entry,\n                        "source": "dictionary",\n                        "confidence": round(score / 100, 3),\n                        "pos_matched": False,\n                    }\n                )'

    new_chunk = '# Only match entries that actually have an English definition\n        _def_entries = [d for d in _dictionary if (d.get("definitionEnglish") or "").strip()]\n        [(d.get("definitionEnglish") or "").lower() for d in _def_entries],\n            scorer=fuzz.token_sort_ratio,\n            limit=10,\n            score_cutoff=65,\n        )\n        for match_text, score, idx_i in fuzzy_raw:\n            entry = _def_entries[idx_i] if idx_i < len(_def_entries) else _index.get("_dict_def_map", {}).get(match_text)\n            if entry and entry["word"] not in seen_words:\n                seen_words.add(entry["word"])\n                results.append(\n                    {\n                        **entry,\n                        "source": "dictionary",\n                        "confidence": round(score / 100, 3),\n                        "pos_matched": False,\n                    }\n                )'

    if old_chunk in content:
        content = content.replace(old_chunk, new_chunk, 1)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        print("Fix applied!")
    else:
        print("old_chunk not found, searching for partial match...")
        sub = '[(d.get("definitionEnglish") or "").lower() for d in _dictionary],'
        if sub in content:
            content = content.replace(sub, '# Only match entries with English definitions\n        _def_entries = [d for d in _dictionary if (d.get("definitionEnglish") or "").strip()]\n        [(d.get("definitionEnglish") or "").lower() for d in _def_entries],', 1)
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
            print("Partial fix applied — filtered to entries with definitions")
        else:
            print("Nothing found")
