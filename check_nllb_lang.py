from transformers import NllbTokenizer
tok = NllbTokenizer.from_pretrained('lunyoro-translator/backend/model/nllb_en2lun')
unk_id = tok.unk_token_id

tests = {
    'nyn_Latn': 'Nyankore (current)',
    'run_Latn': 'Rundi (previous)',
    'lug_Latn': 'Luganda',
    'kin_Latn': 'Kinyarwanda',
    'nya_Latn': 'Chichewa/Nyanja',
    'tum_Latn': 'Tumbuka',
}
print("NLLB language code validity check:")
print(f"{'Code':<15} {'ID':>8} {'Status':<12} {'Language'}")
print("-" * 55)
for code, name in tests.items():
    tid = tok.convert_tokens_to_ids(code)
    status = "UNKNOWN/UNK" if tid == unk_id else "VALID"
    print(f"{code:<15} {tid:>8} {status:<12} {name}")

print()
print("Recommendation:")
print("  nyn_Latn is NOT in NLLB-200 vocab -> maps to UNK token")
print("  run_Latn (Rundi) IS valid but linguistically distant")
print("  lug_Latn (Luganda) IS valid AND geographically closest Uganda language")
print("  kin_Latn (Kinyarwanda) IS valid, closely related to Rundi/Runyoro")
print()
print("Best option: lug_Latn (Luganda) - same country, Bantu, NLLB was trained on it")
print("Second best: kin_Latn (Kinyarwanda) - close Niger-Congo branch")
