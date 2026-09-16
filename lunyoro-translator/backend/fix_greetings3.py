"""Hook greeting correction into _nllb_translate using line-based replacement."""
path = "translate.py"
with open(path, "r", encoding="utf-8") as f:
    lines = f.readlines()

# Find line: '    Falls back to HF Inference API when local model is unavailable."""'
# and insert greeting hook right after it
insert_idx = None
for i, line in enumerate(lines):
    if "Falls back to HF Inference API when local model is unavailable" in line:
        insert_idx = i + 1
        break

if insert_idx is None:
    print("ERROR: marker line not found")
else:
    hook_lines = [
        "    # Greeting shortcut — return hardcoded answer for common phrases\n",
        "    _greeting = _apply_greeting_correction(text, direction)\n",
        "    if _greeting:\n",
        "        return _greeting\n",
    ]
    lines = lines[:insert_idx] + hook_lines + lines[insert_idx:]
    with open(path, "w", encoding="utf-8") as f:
        f.writelines(lines)
    print(f"Hook inserted after line {insert_idx}")

# Verify syntax
import ast
with open(path, "r", encoding="utf-8") as f:
    src = f.read()
ast.parse(src)
print("Syntax OK")
