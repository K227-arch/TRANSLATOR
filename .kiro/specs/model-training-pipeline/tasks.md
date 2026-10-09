# Model Training Pipeline — Tasks

Tasks are ordered to follow the actual pipeline execution sequence:
**Data → Clean → Augment → Train → Evaluate → Export → Deploy**.

Each task references the script(s) that implement it and the inputs/outputs.

---

## Phase 1: Data Collection

- [ ] 1. Load and merge all raw sentence pair Excel files from `data/raw/sentence pair*.xlsx` (18 files) into a unified DataFrame
  - Run `train_incremental.py` against any new Excel files
  - Output: updated `data/training/train.csv` and `data/training/val.csv`

- [ ] 2. Load domain seed vocabularies (5 files) from `data/raw/*_seed_vocabulary.csv`
  - Verify all 5 files are present: medical, education, daily life, agriculture, low-frequency
  - These become the **8× weight** priority pairs during training

- [ ] 3. Verify the domain dictionary is clean and present
  - Check `data/cleaned/runyoro_domain_dictionary_clean.csv` exists and has POS column
  - Required for augmentation in Phase 3

---

## Phase 2: Data Cleaning

- [ ] 4. Run primary cleaner on all training splits
  ```bash
  python clean_training_data.py
  ```
  - Input: `data/training/train.csv`, `val.csv`, `test.csv`
  - Output: cleaned in-place; originals backed up as `.bak`
  - Verify: row counts should drop by ~15–20% (noise removal)

- [ ] 5. Fix malformed domain tags
  ```bash
  python fix_malformed_tags.py
  ```
  - Corrects: `AGRCULTURE→AGRICULTURE`, `MIDICAL→MEDICAL`, `REERAL→GENERAL`, etc.
  - Run before `clean_new_training_data.py`

- [ ] 6. Clean newly added training pairs
  ```bash
  python clean_new_training_data.py
  ```
  - Input: `data/training/train.csv` and `val.csv` after any merge step
  - Validates tags against the 45-entry VALID_TAGS enumeration
  - Removes: too-short, identical pairs, English passthrough, HTML artifacts

- [ ] 7. Clean OCR-sourced pairs
  ```bash
  python clean_ocr_pairs.py
  ```
  - Input: `data/cleaned/ocr_pairs_extracted.csv`
  - Output: cleaned in-place; original backed up as `.bak`

---

## Phase 3: Data Augmentation

- [ ] 8. Generate POS-tagged augmented pairs from dictionary
  ```bash
  python augment_and_train.py --augment-only
  ```
  - Input: `data/cleaned/runyoro_domain_dictionary_clean.csv`
  - Output: `data/cleaned/augmented_pos_pairs.csv`
  - Generates: POS-tagged pairs, plural forms (noun class rules), verb conjugations (5 forms each)
  - Applies: R/L rule, nasal assimilation to all Runyoro forms

- [ ] 9. Generate synthetic lun→en pairs via NLLB back-translation
  ```bash
  python back_translate_lun2en.py --max-sentences 10000 --merge
  ```
  - Input: existing `train.csv` tagged pairs + short dictionary entries
  - Output: `data/cleaned/back_translated_lun2en.csv`
  - Filter: keep only if Runyoro output ≥ 5 words, <30% English words
  - `--merge` flag appends to `train.csv` / `val.csv` (90/10 split)

- [ ] 10. Generate round-trip back-translations for en→lun
  ```bash
  python back_translate.py --max-sentences 5000 --merge
  ```
  - Uses current MarianMT en→lun + lun→en for round-trip
  - Keeps only pairs with round-trip BLEU ≥ 0.25
  - Output: `data/training/back_translated.csv`

- [ ] 11. Clean all newly merged data
  ```bash
  python clean_new_training_data.py
  ```
  - Re-run after any merge step to catch any noise introduced by augmentation

---

## Phase 4: Model Training

- [ ] 12. Train MarianMT en→lun
  ```bash
  python train_marian.py --direction en2lun --epochs 7 --lr 3e-5 --new-only
  ```
  - Input: `data/training/new_only_train.csv` (new pairs) + `val.csv.bak` (stable eval)
  - Output: updated `model/en2lun/`
  - Saves best checkpoint by validation BLEU per epoch

- [ ] 13. Train MarianMT lun→en
  ```bash
  python train_marian.py --direction lun2en --epochs 7 --lr 3e-5 --min-lun-words 3 --new-only
  ```
  - Input: same as above, filtered to lun_words ≥ 3
  - Output: updated `model/lun2en/`

- [ ] 14. Train NLLB en→lun
  ```bash
  python train_nllb.py --direction en2lun --epochs 5 --lr 8e-6 --new-only
  ```
  - Input: `data/training/new_only_train.csv` + stable val
  - Output: updated `model/nllb_en2lun/`
  - Uses `forced_bos_token_id = nyo_Latn` during generation

- [ ] 15. Train NLLB lun→en
  ```bash
  python train_nllb.py --direction lun2en --epochs 5 --lr 8e-6 --min-lun-words 3 --new-only
  ```
  - Output: updated `model/nllb_lun2en/`

- [ ] 16. Retrain MarianMT on full validation set (regularisation step)
  ```bash
  python run_full_training.py --retrain-marian-only --no-push
  ```
  - Re-runs MarianMT both directions with full val.csv for final BLEU measurement
  - Catches any regression from NLLB training changes to shared data

**Alternative — run all steps 12–16 in one command:**
```bash
python run_full_training.py --no-push
```

---

## Phase 5: Evaluation

- [ ] 17. Run full BLEU + chrF evaluation on all four models
  ```bash
  python eval_bleu.py --all
  ```
  - Evaluates all four model/direction combinations on full `val.csv`
  - Runs MarianMT on `cuda:0` and NLLB on `cuda:1` in parallel
  - Output: `bleu_results.json`

- [ ] 18. Verify quantitative thresholds before deployment:
  - MarianMT en→lun BLEU ≥ 60.0
  - MarianMT lun→en BLEU ≥ 50.0
  - NLLB en→lun BLEU ≥ 70.0
  - NLLB lun→en BLEU ≥ 60.0

- [ ] 19. Run probe suite to verify qualitative output
  ```bash
  python verify_pi_models.py --all
  ```
  - Known-good probes: `"Good morning, my friend."` → `"Oraire ota mugenziwe."` (NLLB)
  - Known-good: `"Webale muno"` → `"Thank you very much"` (NLLB)

---

## Phase 6: Export

- [ ] 20. Export MarianMT to ONNX FP32
  ```bash
  python export_to_onnx.py --verify
  ```
  - Output: `model/en2lun_onnx/` and `model/lun2en_onnx/`
  - `--verify` runs side-by-side PyTorch vs ONNX speed comparison

- [ ] 21. Export NLLB to ONNX FP32
  ```bash
  python export_nllb_onnx.py
  ```
  - Output: `model/nllb_en2lun_onnx/` and `model/nllb_lun2en_onnx/`
  - Runs smoke-test translation after each export

- [ ] 22. Quantize NLLB to INT8 for Raspberry Pi
  ```bash
  python export_onnx_int8.py --prune-fp32
  ```
  - Input: `model/nllb_en2lun_onnx/` and `model/nllb_lun2en_onnx/`
  - Output: `model/nllb_en2lun_pi/` and `model/nllb_lun2en_pi/`
  - `--prune-fp32` deletes the FP32 ONNX source after quantization (frees ~13.6 GB)

- [ ] 23. Verify INT8 models produce correct output
  ```bash
  python verify_pi_models.py --all
  ```
  - Loads `encoder_model_quantized.onnx` + `decoder_model_quantized.onnx` from `*_pi/` dirs
  - Runs greedy decode (no KV cache) matching C++ backend behaviour

---

## Phase 7: Deployment

- [ ] 24. Push all models to HuggingFace Hub
  ```bash
  python push_models.py --all-variants
  ```
  - Uploads: PyTorch FP32 + ONNX FP32 + ONNX INT8 for all four model/direction combinations

- [ ] 25. Push backend code to HF Space
  ```bash
  python push_to_hf_space.py
  ```
  - Uploads Python backend files to `keithtwesigye/runyoro-translator-api`
  - Space rebuilds Docker container automatically

- [ ] 26. Deploy Pi models to device
  ```bash
  # From project root
  rsync -a model/en2lun_onnx/   pi@<ip>:~/lunyoro-translator-cpp/models/v3/marian_en2lun/
  rsync -a model/lun2en_onnx/   pi@<ip>:~/lunyoro-translator-cpp/models/v3/marian_lun2en/
  rsync -a model/nllb_en2lun_pi/ pi@<ip>:~/lunyoro-translator-cpp/models/v3/nllb_en2lun/
  rsync -a model/nllb_lun2en_pi/ pi@<ip>:~/lunyoro-translator-cpp/models/v3/nllb_lun2en/
  ```
  - Then restart the C++ service on the Pi (requires sudo)

- [ ] 27. Verify live deployment
  ```bash
  curl -s $SPACE_URL/health
  curl -s -X POST $SPACE_URL/translate -d '{"text":"Good morning, my friend."}'
  curl -s -X POST $SPACE_URL/translate-reverse -d '{"text":"Webale muno"}'
  ```
  - Expected: `nllb_en2lun=true`, `marian_en2lun=true` in `/system-info`

---

## Ongoing: Auto-Retraining from User Feedback

- [ ] 28. Monitor feedback accumulation
  ```bash
  python auto_retrain.py --stats
  ```
  - Shows: total clean pairs, pairs since last retrain, threshold progress %

- [ ] 29. Trigger retraining when threshold reached (100 new pairs)
  ```bash
  python auto_retrain.py --check
  ```
  - Or runs automatically in background from the FastAPI `/feedback` endpoint
  - Logs to `auto_retrain.log`
  - Saves retrain record to `.last_retrain`

---

## Estimated Runtimes (GPU: RTX 3080)

| Task | Approximate time |
|------|-----------------|
| Augmentation (task 8) | 2–5 min |
| Back-translation 10k sentences (task 9) | 15–30 min |
| MarianMT 7 epochs, new-only (task 12–13) | 5–15 min each |
| NLLB 5 epochs, new-only (task 14–15) | 30–90 min each |
| MarianMT retrain (task 16) | 10–20 min each |
| BLEU evaluation (task 17) | 5–10 min |
| ONNX export MarianMT (task 20) | 2–5 min |
| NLLB ONNX export (task 21) | 10–20 min |
| NLLB INT8 quantization (task 22) | 5–10 min |
| Full pipeline run_full_training.py | ~3–4 hours |
