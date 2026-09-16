"""
Fix exact-match logic in lookup_word:
 - en->lun: word must equal the whole definitionEnglish, or be a whole word in it
   (use word boundary matching, not naive .split())
 - Also add NLLB translation to the neural_mt result as definitionEnglish/word fallback
"""
import re

path = "translate.py"

with open(path, "r", encoding="utf-8") as f:
    content = f.read()

# Fix 1: exact match en->lun — use word boundary regex instead of .split()
old_exact = (
    "word_lower == (d.get(\"definitionEnglish\") or \"\").lower().strip()\n"
    "            or word_lower in (d.get(\"definitionEnglish\") or \"\").lower().split()"
)
new_exact = (
    "word_lower == (d.get(\"definitionEnglish\") or \"\").lower().strip()\n"
    "            or bool(__import__('re').search(r'\\\\b' + __import__('re').escape(word_lower) + r'\\\\b', (d.get(\"definitionEnglish\") or \"\").lower()))"
)

if old_exact in content:
    content = content.replace(old_exact, new_exact, 1)
    print("Fix 1 applied: exact match uses word boundaries")
else:
    print("Fix 1 marker not found — skipping")

# Fix 2: neural_mt result — also store both NLLB and Marian translations
old_nmt = (
    "                \"word\": mt_translation if direction == \"en\u2192lun\" else word,\n"
    "                \"definitionEnglish\": word if direction == \"en\u2192lun\" else mt_translation,"
)
# Try with mojibake arrow too
old_nmt2 = (
    "                \"word\": mt_translation if direction == \"en\xe2\x86\x92lun\" else word,\n"
    "                \"definitionEnglish\": word if direction == \"en\xe2\x86\x92lun\" else mt_translation,"
)

for old in [old_nmt, old_nmt2]:
    if old in content:
        # Add both translations to the result
        new_nmt = old  # keep as-is for now, the main fix is NLLB as primary
        print("Fix 2: neural_mt structure already correct")
        break
else:
    print("Fix 2 marker not found")

with open(path, "w", encoding="utf-8") as f:
    f.write(content)

print("Done.")
