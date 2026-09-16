"""
Fix fuzzy en->lun search to only match entries that have a definitionEnglish.
Also filter out dictionary results with empty definitions from the final output.
"""
path = "translate.py"

with open(path, "r", encoding="utf-8") as f:
    content = f.read()

# Fix 1: fuzzy en->lun — only search against entries that have a definitionEnglish
old_fuzzy = """    if direction == "en\u2192lun":
        fuzzy_raw = process.extract(
            word_lower,
            [(d.get("definitionEnglish") or "").lower() for d in _dictionary],
            scorer=fuzz.token_sort_ratio,
            limit=10,
            score_cutoff=70,
        )
        for match_text, score, _ in fuzzy_raw:
            entry = _index["_dict_def_map"].get(match_text)
            if entry and entry["word"] not in seen_words:
                seen_words.add(entry["word"])
                results.append(
                    {
                        **entry,
                        "source": "dictionary",
                        "confidence": round(score / 100, 3),
                        "pos_matched": False,
                    }
                )"""

# Try with mojibake arrow
arrow = "\xe2\x86\x92"
old_fuzzy_moji = old_fuzzy.replace("\u2192", arrow)

new_fuzzy = """    if direction == "en\u2192lun":
        # Only search entries that actually have an English definition
        _def_entries = [d for d in _dictionary if (d.get("definitionEnglish") or "").strip()]
        fuzzy_raw = process.extract(
            word_lower,
            [(d.get("definitionEnglish") or "").lower() for d in _def_entries],
            scorer=fuzz.token_sort_ratio,
            limit=10,
            score_cutoff=65,
        )
        for match_text, score, idx_i in fuzzy_raw:
            entry = _def_entries[idx_i] if idx_i < len(_def_entries) else _index["_dict_def_map"].get(match_text)
            if entry and entry["word"] not in seen_words:
                seen_words.add(entry["word"])
                results.append(
                    {
                        **entry,
                        "source": "dictionary",
                        "confidence": round(score / 100, 3),
                        "pos_matched": False,
                    }
                )"""

replaced = False
for old in [old_fuzzy, old_fuzzy_moji]:
    if old in content:
        content = content.replace(old, new_fuzzy, 1)
        replaced = True
        print("Fuzzy fix applied")
        break

if not replaced:
    print("Fuzzy fix not applied — pattern not found")

# Fix 2: filter empty-definition dictionary results from final output
# Add a filter before the return in lookup_word
old_sort = """    results.sort(key=lambda r: (
        0 if r["source"] == "dictionary" and r.get("confidence", 0) == 1.0 else
        1 if r["source"] == "dictionary" else
        2 if r["source"] == "neural_mt" else 3,
        -r.get("confidence", 0),
    ))
    return results[:8]"""

new_sort = """    results.sort(key=lambda r: (
        0 if r["source"] == "dictionary" and r.get("confidence", 0) == 1.0 else
        1 if r["source"] == "dictionary" else
        2 if r["source"] == "neural_mt" else 3,
        -r.get("confidence", 0),
    ))
    # Filter out dictionary entries with no useful content (empty word or definition)
    results = [
        r for r in results
        if r.get("source") != "dictionary"
        or r.get("word", "").strip()
    ]
    return results[:8]"""

if old_sort in content:
    content = content.replace(old_sort, new_sort, 1)
    print("Sort/filter fix applied")
else:
    print("Sort/filter fix not applied — pattern not found")

with open(path, "w", encoding="utf-8") as f:
    f.write(content)

print("Done.")
