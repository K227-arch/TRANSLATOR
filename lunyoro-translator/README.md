# AI Stick — Runyoro / Rutooro Translator

**Version 2.9** - AI Stick Lens

A neural machine translation system for Runyoro-Rutooro ↔ English with:
- Fine-tuned MarianMT + NLLB-200 models
- Semantic search fallback with 80k+ sentence pairs
- Grammar rule post-processing (R/L rule, nasal assimilation, etc.)
- Human feedback loop for continuous improvement
- Chat assistant powered by Qwen 2.5 7B

**Live Demo:** [frontend-six-phi-25.vercel.app](https://frontend-six-phi-25.vercel.app)  
**API:** [keithtwesigye-runyoro-translator-api.hf.space](https://keithtwesigye-runyoro-translator-api.hf.space)

---

## Features

### Translation
- **Dual neural models:** NLLB-200 (primary for both directions) + MarianMT (fallback/comparison); the best available translation is shown as a single output
- **HuggingFace Hub integration:** Models loaded automatically from HF Hub on first use and cached locally
- **Context-aware:** Uses previous sentence for better coherence
- **Grammar rules:** Automatic R/L rule, apostrophe elision, nasal assimilation, initial vowel rule (ensures each word carries the correct class vowel before its prefix; skips a known exception list of verb infinitives and derived nouns whose internal vowels must not be altered — e.g. `okulya`, `ebyokulya`, `okunywa`, `okugenda`), Grammar Rules 4 (copula, kinship, enumeratives, ka particle, demonstratives, dara presentative, verb-noun derivation)
- **Hallucination guard:** Detects and rejects degenerate MT output (repetitive tokens or bigrams exceeding 40%/35% thresholds) — falls back to the next translation method automatically
- **Translation chain (en→lun):** Curated phrase override (idiomatic translations for common expressions) → **Neural MT runs first** (both NLLB and MarianMT are always invoked before any retrieval step) → Selective RAG (high-confidence corpus match; NLLB output is injected into the RAG response when valid, overriding the corpus translation as primary) → Corpus exact-match (for short inputs of 1–3 words, scans the full sentence corpus for a case-insensitive exact match; NLLB used as primary when valid) → Semantic search → Dictionary lookup. All response paths (`rag`, `exact_match`, `neural_mt`) now include `translation_nllb` and `translation_marian` fields alongside the primary `translation`.
- **lun→en input preprocessing:** Before the Lunyoro source is fed to the model, three normalisation passes run in sequence: (1) nasal assimilation (nb→mb, np→mp, etc.) for canonical consonant clusters; (2) apostrophe elision expansion so contracted particles reach the model in their full form (`n'ente` → `na ente`, `w'okugonza` → `wa okugonza`, etc.); (3) common spelling-variant normalisation (`kiro` → `leero`, `eky-` → `eki-` prefix variants, etc.). The R/L rule is intentionally **not** applied to input — the model was trained on real speaker text.
- **lun→en output post-processing:** Every lun→en translation (regardless of model path) goes through two cleaning stages before being shown. **Stage 1 — decode-time artefact cleaning** (applied immediately after `tokenizer.decode()`, NLLB only): (1) SentencePiece word-boundary markers (`▁`, U+2581) that occasionally leak through the NLLB `run_Latn` decoder are stripped and excess whitespace collapsed; (2) isolated `L` → `I` substitution — NLLB occasionally confuses the Latin letter `L` with the first-person pronoun `I` due to character-level ambiguity in the `run_Latn` script mapping; the regex (`(?<![A-Za-z])L(?![A-Za-z])`) uses lookahead/lookbehind rather than `\b` so it correctly handles punctuation-adjacent occurrences. **Stage 2 — `_postprocess_english` (applied universally in `POST /translate-reverse`)**: runs on the final translation regardless of which model produced it — (1) language-code prefix stripping (e.g. `run_Latn:` or `[GENERAL]` prefixes); (2) double-subject removal (e.g. `The child he went` → `The child went`); (3) redundant pronoun removal after proper nouns; (4) duplicate copula deduplication (`is is` → `is`); (5) repeated trailing sentence removal; (6) sentence capitalisation and terminal punctuation enforcement. The Qwen LLM refinement pass runs on top of both stages as a best-effort fluency improvement.
- **Spellcheck:** Real-time Lunyoro spellcheck with suggestions; the known-word vocabulary is built from the sentence corpus, the dictionary, and the MarianMT tokenizer — tokenizer tokens are filtered to Bantu-prefix patterns only — the filter now requires a 3-character prefix match (e.g. `oku`, `omu`, `aba`, `eki`, `ebi`, `eri`, `oru`, `eng`, `emb`, `ngo`, `nka`, `wee`, `ree`) and a minimum word length of 5 characters, so short sub-word fragments and 2-char English noise tokens are excluded; this stricter filter reduces false negatives in the spellchecker; dictionary entries are additionally filtered through an English stoplist (~70 common English words such as `ago`, `down`, `from`, `people`, `world`, etc.) to exclude English words that leak into the dictionary from being registered as known Runyoro vocabulary

### Navigation

The app uses a fixed **BottomNav** bar with five tabs:

| Tab | Component | Description |
|-----|-----------|-------------|
| Home | `HomeDashboard` | Landing page with feature cards |
| Translate | `Translator` | English ↔ Lunyoro translation |
| Camera | `CameraTranslator` | Camera OCR translation (Google Lens-like) |
| Chat | `ChatPage` | AI language assistant |
| Help | `Help` | Help & usage guide |

Additional pages accessible from Home dashboard cards:

| Tab | Component | Description |
|-----|-----------|-------------|
| Editor | `DocumentEditor` | Write (RunyoroEditor) and PDF Translate sub-tabs |
| History | `History` | Translation history log |
| Voice | `VoiceTranslator` | Voice input translation |

Inner pages (Editor, Dictionary, History, Voice, Camera, Help) display a section title in the **TopBar** and a back button that returns to Home.

- **Page transitions:** Tab switches remount the content area (`key={tab}`) and wrap pages in a `.page-enter` CSS animation for a smooth fade/slide-in effect
- **Offline banner (`OfflineBanner.tsx`):** Fixed top-of-screen strip that appears automatically when the device loses network connectivity; shows a red `wifi_off` banner with the message "You're offline — showing cached translations"; when connectivity is restored, switches to a green `wifi` banner ("Back online") that auto-dismisses after 3 seconds; renders nothing when the connection is stable

### Dictionary (`Dictionary.tsx`)
- **Direction toggle:** Segmented control switches between English → Runyoro and Runyoro → English; resets query and results on change
- **Search bar:** Icon-prefixed input with rounded Material Design styling; submits on Enter or the Search button
- **POS filter chips:** Noun / Verb / Adjective filter pills appear above results once a search returns entries; active pill uses the primary theme colour; chips with zero matches are hidden automatically
- **Result cards:** Each entry displays the target-language word, source label (Runyoro / Rutooro or English), POS badge, dialect badge, AI/corpus source tag, and confidence percentage; primary-matched entries receive a highlighted border
- **Example sentences:** Shown in a separated section at the bottom of each card when available
- **Language rule hints:** Inline banner surfaces interjection/idiom annotations and the R/L rule reminder for Runyoro input searches
- **Empty state:** Illustrated "no results" message with a search-off icon when a query returns nothing
- **Styling:** Uses Material Design 3 colour tokens (`bg-primary`, `text-on-surface`, `bg-surface-container-*`, etc.) and `premium-shadow` utility for consistent theming with the rest of the app

### Runyoro-Rutooro Writing Editor (`RunyoroEditor.tsx`)
- **Contenteditable canvas:** Rich-text editor with caret preservation across spellcheck re-renders
- **Real-time spellcheck:** Wavy underlines on misspelled words; hover tooltip with suggestions or ignore option; debounced 800ms after typing stops
- **Grammar hints panel:** Six collapsible reference cards covering R/L Rule, Noun Classes, Verb Infinitives, Tense Markers, Apostrophe elision, and Long Vowels
- **Formatting toolbar:** Bold, italic, underline, ordered/unordered lists, and left/center/right alignment via `execCommand`
- **AI grammar review:** Sends editor text to `/chat` endpoint for Qwen-powered grammar feedback
- **Bidirectional translate button:** Auto-detects whether the editor content is English or Runyoro based on the proportion of common English function words (threshold: >15% match score):
  - **English input (en→lun):** Calls `POST /translate`; the returned Runyoro translation *replaces* the editor content in-place and triggers an automatic spellcheck pass on the new text
  - **Runyoro input (lun→en):** Calls `POST /translate-reverse`; the English translation is displayed in a dedicated panel below the editor; shows NLLB-200 (always labeled "Primary ✓") and MarianMT side-by-side only when both outputs are available **and meaningfully differ** (compared after lowercasing and stripping punctuation/whitespace — identical or near-identical outputs show only the primary NLLB result to avoid redundancy)
- **Save to file:** Downloads editor content as a `.txt` file with a datestamped filename
- **Word count:** Live word count displayed in the editor footer

### Chat Assistant
- **LLM-powered:** Qwen 2.5 7B via HuggingFace Router
- **Domain-aware:** Sector-specific vocabulary across 8 domains (Daily Life, Storytelling, Spirituality, Agriculture, Education, Culture, Health, All Sectors)
- **Grammar context:** Runyoro-Rutooro grammar rules injected into system prompt — assembled at startup from `get_grammar_context()`, `get_gr4_grammar_context()`, and `get_gr5_grammar_context()` with per-section budgets (core: 2000 chars, gr4: 1800 chars, gr5: 2200 chars) for richer, balanced rule coverage
- **Detailed replies:** System prompt instructs the model to reply in plain English prose, 2–4 well-explained paragraphs, with the grammar rule behind every concept explained
- **Corpus-grounded:** Up to 2 relevant sentence pairs from the training corpus are retrieved and included as examples
- **Conversation mode:** Type in Runyoro-Rutooro for immersive practice
- **Multi-line input:** Auto-growing textarea (up to 72px); submit with Enter, Shift+Enter for newline; rounded pill-shaped input bar
- **Quick topic chips:** Horizontally scrollable topic buttons (Greetings, Directions, Food, Emergency, Numbers) for one-tap phrase discovery
- **Welcome card:** Centered intro card on empty state with translate icon and prompt to begin
- **Message avatars:** Bot (translate icon) and user (person icon) avatars alongside each message bubble
- **Message actions:** Speak (text-to-speech) and copy-to-clipboard buttons below each assistant reply
- **Mic button:** Speech input button in the input bar (placeholder for voice-to-text integration)
- **Typing indicator:** Animated bouncing dots while awaiting a response
- **Auto-scroll:** Chat viewport scrolls to the latest message on every update
- **Rate-limit handling:** Displays a friendly message when the backend returns HTTP 429

### Human Feedback
- **Inline thumbs up/down:** Thumbs-up and thumbs-down buttons appear directly in the translation output header alongside the copy button; filled icon + colour highlight (primary/error) indicates selected state; buttons hide after submission and display a "Thanks!" confirmation
- **Correction flow:** Thumbs-down opens a correction input so users can submit a better translation
- **Multi-select error categorization:** Select multiple issue types (grammar, spelling, context, vocabulary, other)
- **Model comparison:** 2x2 grid interface to choose between MarianMT, NLLB-200, both correct, or both wrong; appears only when both models return output
- **Model preference learning:** When a user selects a preferred model, the translation immediately updates to show that model's output, and future translations automatically use that model as primary; the preferred model badge displays as "NLLB" or "MarianMT"
- **Corrections:** Submit better translations with optional error details
- **Separate feedback flows:** Primary quality feedback and model comparison feedback tracked independently
- **Continuous learning:** Approved pairs feed back into training

### Camera OCR Translation
- **Google Lens-like:** Point camera at text, get instant translations overlaid on the image
- **File upload:** Upload an image with text for OCR detection and translation via `POST /ocr-translate`
- **Real-time camera:** Send base64-encoded camera frames for live translation via `POST /ocr-translate-base64`
- **Bounding box overlay:** Returns normalized coordinates (0–1) for responsive text overlay on any screen size
- **Bidirectional:** Supports both English → Lunyoro and Lunyoro → English directions
- **Confidence filtering:** Low-confidence detections (< 0.3) are automatically excluded
- **GPU acceleration:** EasyOCR automatically uses CUDA GPU when available for faster text detection; falls back to CPU otherwise
- **Requires:** `easyocr` (Python < 3.12 only), `pytesseract`, `opencv-python-headless`

### Image Classification & Translation
- **Object recognition:** MobileNetV2 (`google/mobilenet_v2_1.0_224`) classifies objects in uploaded images into English labels, which are then translated to Runyoro via the existing translation pipeline
- **Supported formats:** JPEG, PNG, WebP — validated via magic byte detection (not Content-Type header)
- **File size limit:** 10 MB maximum
- **Top-K results:** Returns up to 5 predictions (configurable) sorted by confidence descending; labels are cleaned ImageNet categories (lowercased, first synonym only)
- **Singleton model:** Loaded once at startup in a background thread; `image_classifier.is_ready()` reports availability
- **Validation utility:** `validate_image_upload()` checks for empty files, unsupported formats, and oversized uploads before classification

### Camera Translator (`CameraTranslator.tsx`)
- **Full-screen camera mode:** When active, the camera fills the viewport above the bottom navigation bar (`fixed inset-0 z-40`, height `calc(100vh - 80px)`) for an immersive Google Lens-like experience while keeping the nav accessible; inactive state shows upload and launch UI
- **Live camera feed:** Accesses device camera via `getUserMedia` with environment (rear) or user (front) facing mode; 1280×720 ideal resolution; pre-checks `navigator.mediaDevices.getUserMedia` availability and displays a clear error if the browser lacks support (requires HTTPS or localhost)
- **Viewfinder overlay:** Corner brackets and animated scan-line provide visual feedback that the camera is actively scanning
- **Auto-scan mode:** Captures and translates frames every 3 seconds while the camera is active; pause/resume pill toggle in the bottom control row
- **Manual capture:** Large circular shutter button for on-demand frame translation; disabled while a scan is in progress to prevent duplicate requests
- **Direction pill:** Compact top-bar toggle showing current direction (EN ↔ LUN) with swap icon
- **Translation overlay:** Bounding boxes with translated text overlaid on the captured image using normalized coordinates; dark background with backdrop blur for readability; green text with font size clamped and scaled to region height; **only rendered on the OCR tab and only when the original image view is active** (`showOriginal === true`) — the Identify tab never shows bounding-box overlays, and the overlay is hidden when the canvas-painted translated image is displayed
- **Canvas-painted translated image:** After OCR results arrive — whether from a file upload or a camera capture — translated text is rendered in-place directly on top of the source image rather than in a separate card. For each detected region the renderer samples all pixels in the bounding box and separates them into three brightness bands (dark < 35%, light > 65%, mid-tone). The majority band determines the background colour (used to erase the original text), while the minority band determines the text colour — so dark text on a light background and light text on a dark background are both handled correctly without a fixed luminance threshold. Font size is initialised at `0.78 × bbox height` (accounting for ascenders/descenders) and shrunk one pixel at a time until the translated text fits within 98% of the region width; no bold weight is applied so the rendered font better matches typical body text. Long translations are word-wrapped using the same 98% width budget, and the resulting text block is centred vertically within the bounding box using `alphabetic` baseline alignment. The canvas retains the original image dimensions and is exported as JPEG at 0.95 quality. The result is stored as `renderedOcrImage` and shown by default in place of the original photo; any previously rendered canvas image is cleared at the start of each new upload so stale results never persist; on each new file upload the view state is also reset (`showOriginal → false`) so the translated canvas view is always shown immediately for the new image; **translations are displayed exclusively on the canvas image — there is no separate text list panel**
- **Original / Translated toggle:** A pill button (top-right of the image preview, visible only after the canvas-painted image is ready) switches between the canvas-painted translated view and the unmodified original image (`showOriginal` state); when showing the original, the bounding-box overlay is also re-displayed; toggling does not re-run OCR — both images are kept in memory
- **Results panel:** Slide-up bottom sheet displaying detected translations in a compact paragraph layout — regions are grouped in pairs per line as "original → translated · original → translated"; toggled via a "Results" pill with a close button
- **Camera switch:** Flip between front and rear cameras via a bottom-bar icon button
- **Per-tab state persistence:** OCR and Identify tabs maintain independent image previews (`ocrImage` / `classifyImage`) and independent results (`regions` / `classifications`); switching tabs preserves both the image and results of each tab so users can compare outputs without re-scanning; starting the camera clears both image previews so neither tab shows a stale image from a previous session; the loading spinner is also tab-scoped (`loading` for OCR, `classifyLoading` for Identify) so activity on one tab never bleeds into the other's UI
- **Image upload:** Gallery icon button in the bottom controls; also available as a card in the inactive state; sends image as `FormData` to `/ocr-translate`
- **Inactive state:** Full-height layout (`minHeight: calc(100vh - 160px)`) with instructions pinned to the bottom via `marginTop: auto`; two action cards (Open Camera / Upload Text Image) with direction toggle; a Material Symbols icon strip (📷 → 🔤 → 🌐) above the instruction text visually illustrates the capture → detect → translate workflow; results from uploaded images display with the same overlay system
- **Error handling:** Checks for camera API availability before attempting access (catches insecure-context / unsupported-browser scenarios); displays camera permission errors and server connection failures in a centred styled error banner
- **Styling:** Full-screen mode uses glassmorphic controls (`bg-white/15 backdrop-blur-md`), gradient status/control bars, and scanline keyframe animation; inactive state uses Material Design 3 tokens with rounded pill buttons and surface containers

---

## Quick Start

### Frontend (Next.js)
```bash
cd lunyoro-translator/frontend
npm install
npm run dev
# → http://localhost:3002
```

### Backend (FastAPI)
```bash
cd lunyoro-translator/backend
pip install -r requirements.txt
# For Camera OCR with pytesseract, install Tesseract system binary:
#   Ubuntu/Debian: sudo apt-get install tesseract-ocr
#   macOS: brew install tesseract
#   Windows: download from https://github.com/UB-Mannheim/tesseract/wiki
# Note: easyocr is only installed on Python < 3.12 (incompatible with 3.12+)
# Models are automatically downloaded from HuggingFace Hub on first use (~2GB)
# Or pre-download with: python download_models.py
python main.py
# → http://localhost:8000
```

---

## Model Improvement Pipeline

See **[TRAINING_GUIDE.md](TRAINING_GUIDE.md)** for full details.

### 0. Download Models and Dataset
```bash
python backend/download_models.py           # download all models + dataset CSVs
python backend/download_models.py --force   # re-download even if files already exist
```

Downloads fine-tuned MarianMT and NLLB-200 models from HuggingFace Hub, the sentence-transformer semantic search model, and training dataset CSVs from `keithtwesigye/lunyoro-dataset` into `data/cleaned/`, `data/training/`, and `data/raw/`. Skips files that already exist unless `--force` is passed.

### 1. Build Translation Index
```bash
python backend/build_index.py
# Builds semantic search index from dictionary data + training corpus
# Loads word_entries_clean.csv and rutooro_dictionary_clean.csv (dictionary entries)
# Loads data/training/train.csv (sentence pairs for semantic search)
# Encodes English sentences with all-MiniLM-L6-v2 into dense embeddings
# Creates model/translation_index.pkl containing:
#   - dictionary entries
#   - english_sentences / lunyoro_sentences arrays
#   - embeddings matrix for cosine-similarity retrieval
```

### 2. Clean Training Data
```bash
python backend/clean_training_data.py
# Removes 13,899 noisy rows (domain tags, OCR garbage, duplicates)
# 80,733 → 66,834 clean pairs
```

### 2b. Clean OCR Pairs
```bash
python backend/clean_ocr_pairs.py
# Removes noisy/truncated rows from data/cleaned/ocr_pairs_extracted.csv
# Filters out rows where:
#   - English side starts with a lowercase letter (truncated left margin)
#   - English side starts with truncation punctuation (', ", >, \, etc.)
#   - Either side is empty or < 4 characters
#   - English side contains grammar meta-notation (e.g., "e.g.", "formative", "tense prefix")
#   - English side matches a page-header pattern (e.g. "Conditions expressed by verbs 279")
#   - Either side contains LaTeX/notation artifacts (\varphi, c/.14, pl. nil, n. cl)
#   - Lunyoro side starts with a grammar label (e.g. "ru ya:", "aba:", "na:")
#   - Lunyoro side starts lowercase and contains an inline colon label with a capitalised continuation
#     (e.g. "okuruga ... okuhikya: From morning till evening")
#   - Lunyoro side matches a short label pattern like "in'ekindi:" (up to 15 chars ending in colon)
# Backs up the original file to ocr_pairs_extracted.csv.bak before overwriting
```

### 2c. Clean Newly Added Training Pairs
```bash
python backend/clean_new_training_data.py
# Cleans train.csv and val.csv after any data merge step:
#   1. Fixes malformed/stacked domain tags (e.g. [AGICAL], [REERAL] → stripped or corrected)
#   2. Removes pairs where either side is < 3 characters
#   3. Removes identical pairs (English == Lunyoro after lowercasing)
#   4. Removes English-passthrough pairs in the Lunyoro column
#      (detected when > 50% of words are common English function words)
#   5. Removes very long pairs (> 500 characters on either side)
#   6. Removes pairs containing HTML/entity artifacts (<tag>, &amp;, etc.)
#   7. Drops rows with NaN or empty values
# Backs up both files (.bak2) before overwriting.
# Run this after merge_untrained_data.py or any step that appends new pairs.
```

### 2e. Fix Malformed Domain Tags
```bash
python backend/fix_malformed_tags.py
# Fixes malformed domain tags in train.csv and val.csv, then removes garbage pairs.
#
# Tag corrections applied (example misspellings → canonical form):
#   [AGRCULTURE)  → [AGRICULTURE]
#   [MIDICAL)     → [MEDICAL]
#   [REERAL]      → [GENERAL]
#   [EDUCAION]    → [EDUCATION]
#   [GOVERMENT]   → [GOVERNANCE]
#   [ENVIROMENT]  → [NATURE_AND_ENVIRONMENT]
#   ... and several other common misspellings
#
# Also removes pairs where the English side is clearly garbage after stripping the tag:
#   - Cleaned English side is < 4 characters
#   - Cleaned English side starts with a 1–2-letter artifact prefix (e.g. "en do not...")
#
# Backs up both files (.bak_tagfix) before overwriting.
# Run this before clean_new_training_data.py or after any data merge that may
# have introduced tag typos.
```

### 2d. Merge Untrained Data
```bash
python backend/merge_untrained_data.py
# Finds all clean data not yet in train.csv / val.csv and merges it in.
# Sources scanned:
#   - data/cleaned/*.csv          (any file with english + lunyoro columns)
#   - data/raw/proverbs_pairs.csv
#   - data/raw/english_nyoro.csv / english_nyoro_root.csv
#   - feedback/approved_pairs.csv (human-approved pairs)
# Deduplicates against existing train + val keys before adding.
# Splits new pairs 90/10 into train.csv / val.csv.
# Backs up both files (.bak) before writing.
# Prints a per-source breakdown of new pairs added.
# Run after any data cleaning step to ensure nothing is left out of training.
```

### 3. Back-Translation (Data Augmentation)
```bash
python backend/back_translate.py --max 5000 --bleu-threshold 0.25
# Generates 2,000-3,000 synthetic pairs via round-trip translation
python backend/merge_back_translated.py
```

### 3b. Augment Back-Translated Data
```bash
python backend/augment_bt_data.py                    # generate augmented pairs
python backend/augment_bt_data.py --merge            # also merge into training data
python backend/augment_bt_data.py --max-per-pair 3   # max augmentations per pair
```

Generates additional English variants from the back-translated lun→en pairs using six augmentation techniques:

| Technique | Description |
|-----------|-------------|
| **Tense variation** | Present simple → past tense or present continuous (e.g. *I go* → *I went* / *I am going*) |
| **Pronoun swap** | Substitutes subject pronouns (e.g. *I am* → *he/she is* or *we are*) |
| **Negation** | Adds negation to positive constructions (e.g. *I know* → *I do not know*) |
| **Synonym substitution** | Replaces common English words with synonyms from a Runyoro-safe synonym table (70+ entries) |
| **Sentence truncation** | Extracts sub-sentences from longer pairs |
| **Number variation** | Singular ↔ plural using Runyoro grammar rules |

**Input:** `data/cleaned/back_translated_lun2en.csv`  
**Output:** `data/cleaned/augmented_bt_lun2en.csv`  
Use `--merge` to append the output directly to `data/training/train.csv` and `val.csv`.

### 4. Retrain Tokenizer (Better OOV Handling)
```bash
python backend/retrain_tokenizer.py --vocab-size 65000 --direction both
# Expands vocab from 64k → 65k tokens with subword regularization
```

### 5. Fine-Tune Models
```bash
python backend/train_marian.py --direction both --epochs 5 --resize-embeddings
# Features:
#   - Subword regularization (SPM sampling, alpha=0.1)
#   - Longer context window (prepends previous sentence)
#   - Mixed precision (fp16) on GPU
#   - Multi-GPU training: automatically uses all available GPUs via DataParallel
#   - BLEU-based checkpoint selection
#   - Weighted sampler: gr4 pairs get 4x weight, back-translated pairs 2x
```

### 6. Fine-Tune NLLB-200 Models
```bash
python backend/train_nllb.py                          # both directions, 5 epochs
python backend/train_nllb.py --direction en2lun       # one direction only
python backend/train_nllb.py --epochs 5 --lr 2e-5
python backend/train_nllb.py --fp16                   # mixed precision (GPU)
python backend/train_nllb.py --new-only               # train only on new (untrained) pairs
```

**Options:**

| Flag | Default | Description |
|------|---------|-------------|
| `--direction` | `both` | `en2lun`, `lun2en`, or `both` |
| `--epochs` | `5` | Number of training epochs |
| `--batch-size` | `8` | Keep low (8–16) — NLLB is large |
| `--lr` | `1e-5` | Learning rate (lower than MarianMT) |
| `--max-length` | `256` | Max token length |
| `--fp16` / `--no-fp16` | enabled | Mixed precision (GPU only) |
| `--min-lun-words` | `3` | (`lun2en` only) Filter out pairs where the Lunyoro side has fewer than N words. Removes single-word dictionary entries that hurt lun→en BLEU. Set to `0` to disable. |
| `--new-only` | `false` | Train only on pairs not yet seen by the model (`data/training/new_only_train.csv` / `new_only_val.csv`). Falls back to the full `train.csv` / `val.csv` if those files don't exist. Note: `train_marian.py --new-only` always validates on the full `val.csv` regardless of this flag. |

**Notes:**
- Always fine-tunes from the existing local checkpoint in `model/nllb_{direction}/` — never trains from scratch
- Best checkpoint (by validation BLEU) is saved to `model/nllb_{direction}/best_checkpoint/` and promoted to the model root at the end
- Requires `model/nllb_en2lun/` and/or `model/nllb_lun2en/` to exist — run `python download_models.py` first if needed
- Uses a weighted sampler: Grammar Rules 4 and Grammar Rules 5 pairs get 4× weight, back-translated pairs 2×, all others 1× (same strategy as `train_marian.py`); seed vocabulary CSVs (medical, education, daily life, low-frequency, agriculture) are also loaded and deduplicated against the main training set
- Multi-GPU training: automatically uses all available GPUs via `DataParallel` when more than one GPU is detected (prints device names at startup)
- **lun→en data fixes (applied automatically):** Before training the `lun2en` direction, two preprocessing steps run in sequence: (1) domain tags (e.g. `[MEDICAL]`, `[GENERAL]`) are stripped from the English target column — these tags are en→lun artefacts that corrupt lun→en targets; (2) pairs where the Lunyoro source has fewer than `--min-lun-words` words are dropped, removing single-word dictionary entries that degrade sentence-level BLEU

### 6a. Fix NLLB Embedding Size Mismatch
```bash
python backend/fix_nllb_embeddings.py
# Resolves the vocab_size mismatch between a saved NLLB checkpoint and its tokenizer.
# This can occur after adding the custom nyo_Latn token when the previous checkpoint
# was already resized (e.g. 256206 vs. the tokenizer's 256205).
#
# For each direction (en2lun and lun2en):
#   1. Loads the tokenizer and model from model/nllb_{direction}/
#   2. Compares tokenizer vocab size against model.config.vocab_size
#   3. Resizes model embeddings to match the tokenizer (resize_token_embeddings)
#   4. Re-initialises the nyo_Latn embedding as the average of Bantu language
#      embeddings (run_Latn + lug_Latn + kin_Latn)
#   5. Backs up the original checkpoint to model/nllb_{direction}_pre_fix/
#      (only on first run — will not overwrite an existing backup)
#   6. Saves the corrected tokenizer and model in place
#
# Run this before training if you see a size mismatch error like:
#   "size mismatch for shared.weight: copying a param with shape torch.Size([256206, 1024])
#    from checkpoint, the shape in current model is torch.Size([256205, 1024])"
# After running, retrain with: python backend/train_nllb.py --direction both
```

### 6a-2. Fix nyo_Latn Token Registration (Tokenizer-Only)
```bash
python backend/fix_nllb_token_properly.py
# Correct approach for registering the nyo_Latn language token in the NLLB
# tokenizer without touching model weights.
#
# Background: some NLLB checkpoints end up with a vocab_size of 256206 (one
# extra embedding row added by a previous resize) while the tokenizer still
# has 256205 entries and nyo_Latn is unregistered (maps to <unk>).
#
# Strategy (tokenizer-only — model weights are never modified):
#   1. Reads the actual embedding size directly from the safetensors file
#      (model.shared.weight shape) without loading the full model into memory
#   2. Compares that against the tokenizer's current vocab size
#   3. If the tokenizer is short, adds placeholder tokens to fill the gap and
#      appends nyo_Latn as the final token (maps to the existing extra slot)
#   4. Backs up the tokenizer files to model/nllb_{direction}_tok_backup/
#      (only on first run — will not overwrite an existing backup)
#   5. Saves the corrected tokenizer in place; model.safetensors is untouched
#
# When to use instead of fix_nllb_embeddings.py:
#   - Use this script when the model weights are already the right size and you
#     only need the tokenizer to recognise nyo_Latn
#   - Use fix_nllb_embeddings.py when the embedding matrix itself needs to be
#     resized (e.g. the model was saved before the custom token was added)
#
# After running, verify with:
#   python -c "from transformers import NllbTokenizer; t = NllbTokenizer.from_pretrained('model/nllb_en2lun'); print(t.convert_tokens_to_ids('nyo_Latn'))"
# The printed ID should be 256205 (not 3 / <unk>).
# Then retrain with: python backend/train_nllb.py --direction both
```

### 6b. Augment Data + Full Training Pipeline (CI/CD)
```bash
python backend/augment_and_train.py                  # full pipeline (augment → train → push)
python backend/augment_and_train.py --augment-only   # only generate + clean augmented data
python backend/augment_and_train.py --train-only     # skip augmentation, just train
python backend/augment_and_train.py --no-push        # skip all pushes
python backend/augment_and_train.py --epochs 3       # set training epochs
python backend/augment_and_train.py --marian-only    # skip NLLB
python backend/augment_and_train.py --nllb-only      # skip MarianMT
```

End-to-end CI/CD pipeline that combines data augmentation with training and deployment:

1. **Augment** — generates new training pairs from the domain dictionary POS data:
   - POS-tagged pairs (`[NOUN]` / `[VERB]` / `[ADJ]` prefixed English entries)
   - Plural augmentation using noun class rules (omu-→aba-, eki-→ebi-, eri-→ama-, etc.); English side strips leading articles (a/an/the) and applies correct suffix rules: `-s`/`-x`/`-z`/`-sh`/`-ch` endings → `+es`, consonant+`y` endings → `-y+ies`, all others → `+s`
   - Verb conjugation pairs (present 1sg/3sg, perfect 1sg, imperative, negative present)
2. **Clean** — applies the same orthographic pipeline as all other data (nasal assimilation, R/L rule)
3. **Merge** — deduplicates and appends new pairs into `train.csv` / `val.csv`
4. **Train** — fine-tunes MarianMT en2lun + lun2en, then NLLB en2lun + lun2en
5. **Push** — uploads models to HuggingFace Hub and backend to HF Space
6. **GitHub** — pushes code to both repos

**Noun class plural rules supported:**

| Singular prefix | Plural prefix | Example |
|-----------------|---------------|---------|
| `omu-` / `omw-` | `aba-` / `ab-` | omuntu → abantu |
| `eki-` / `eky-` | `ebi-` / `eby-` | ekitabu → ebitabu |
| `eri-` / `ery-` | `ama-` | eriiso → amaiso |
| `aka-` / `akw-` | `utu-` / `utw-` | akana → utunana |
| `oru-` / `orw-` | `en-` / `em-` | orulimi → endimi |

**Verb conjugation pairs generated per infinitive:**
- Present 1sg: `n` + stem (I do X)
- Present 3sg: `a` + stem (he/she does X)
- Perfect 1sg: `n` + mutated root + `ire` (I have done X)
- Imperative: stem alone (do X!)
- Negative present: `tin` + stem (I don't do X)

### 6c. Run Full Training Pipeline (MarianMT + NLLB)
```bash
python backend/train_all.py                          # 3 epochs each, both directions
python backend/train_all.py --epochs 5               # 5 epochs each
python backend/train_all.py --marian-only            # skip NLLB
python backend/train_all.py --nllb-only              # skip MarianMT
python backend/train_all.py --no-push                # skip HuggingFace push
python backend/train_all.py --direction en2lun       # one direction only
```

Runs `train_marian.py` and `train_nllb.py` sequentially, then pushes both models to HuggingFace automatically. Reads `HF_TOKEN` from the environment or from `backend/.env`.

**Options:**

| Flag | Default | Description |
|------|---------|-------------|
| `--epochs` | `3` | Number of training epochs for both models |
| `--batch-marian` | `64` | Batch size for MarianMT |
| `--batch-nllb` | `8` | Batch size for NLLB-200 |
| `--direction` | `both` | `en2lun`, `lun2en`, or `both` |
| `--marian-only` | — | Skip NLLB fine-tuning |
| `--nllb-only` | — | Skip MarianMT fine-tuning |
| `--no-push` | — | Skip HuggingFace push after training |

**Notes:**
- HF push is skipped automatically if any training step fails
- If `HF_TOKEN` is not set and `--no-push` is not passed, a warning is printed and the push is skipped silently
- Exit code is non-zero if any step fails

### 6c-2. Export MarianMT Models to ONNX (Faster Inference)
```bash
python backend/export_to_onnx.py                     # export both directions
python backend/export_to_onnx.py --direction en2lun  # one direction only
python backend/export_to_onnx.py --verify            # export + compare PyTorch vs ONNX speed
```

Converts the fine-tuned MarianMT models to ONNX format using [Hugging Face Optimum](https://github.com/huggingface/optimum). ONNX inference is 2–5× faster than PyTorch on CPU, making it well-suited for the HF Space CPU tier where OOM errors are common with the full PyTorch runtime.

**Output directories:**

| Direction | Output path |
|-----------|-------------|
| en2lun | `model/en2lun_onnx/` |
| lun2en | `model/lun2en_onnx/` |

**Options:**

| Flag | Default | Description |
|------|---------|-------------|
| `--direction` | `both` | `en2lun`, `lun2en`, or `both` |
| `--verify` | — | After export, run a side-by-side comparison of PyTorch vs ONNX output and latency for 3 test sentences |

**Notes:**
- Exports MarianMT only — for NLLB-200 ONNX export see section 6c-4 (`export_nllb_onnx.py`)
- Provider selection uses `onnxruntime.get_available_providers()` at runtime — prefers `CUDAExecutionProvider` when available, otherwise falls back to `CPUExecutionProvider`
- Decoder file auto-detected: `decoder_model_merged.onnx` (newer Optimum) takes priority over `decoder_model.onnx` (older export); a clear error is raised if neither is found
- `use_cache=False` is set on `ORTModelForSeq2SeqLM` — `use_cache=True` requires a separate `decoder_with_past` model that is not always exported
- `translate.py` automatically loads `ORTModelForSeq2SeqLM` from `model/{direction}_onnx/` when that directory exists — no manual changes needed after export
- Tokenizer files (`.json`, `.spm`, `.model`, `.txt`) are copied alongside the ONNX model
- `optimum[onnxruntime]` and `onnxruntime` are included in `requirements.txt` — no separate install needed

### 6c-3. Export MarianMT Models to ONNX with INT8 Quantization (Fastest Inference)
```bash
python backend/export_onnx_int8.py    # exports both directions with INT8 quantization
```

Exports MarianMT models to ONNX with INT8 dynamic quantization using [Optimum](https://github.com/huggingface/optimum). Provides ~3× faster inference on CPU and ~75% smaller model size compared to the full PyTorch models. Output is deterministic and compatible with the existing ONNX loading path in `translate.py`.

**Output directories:**

| Direction | Output path |
|-----------|-------------|
| en2lun | `model/en2lun_onnx/` |
| lun2en | `model/lun2en_onnx/` |

**Pipeline steps (per direction):**
1. Export PyTorch MarianMT model from `model/{direction}/` to ONNX via `ORTModelForSeq2SeqLM.from_pretrained(export=True)`
2. Apply INT8 dynamic quantization (AVX-512 VNNI, per-channel) to all ONNX files using `ORTQuantizer`
3. Copy tokenizer and config files alongside the quantized models
4. Validate: run a test translation to confirm the exported model works and report compression ratio

**Notes:**
- Always exports both directions (`en2lun` and `lun2en`) — skips any direction where `model/{direction}/` doesn't exist
- Overwrites the existing `model/{direction}_onnx/` directory — use `export_to_onnx.py` (section 6c-2) if you prefer FP32 ONNX without quantization
- Uses `AutoQuantizationConfig.avx512_vnni(is_static=False, per_channel=True)` for broad CPU compatibility
- `translate.py` auto-detects ONNX models at load time — no code changes needed after export
- Reports PyTorch vs INT8 model sizes and compression percentage after export
- Requires `optimum[onnxruntime]` (already in `requirements.txt`)

### 6c-4. Export NLLB-200 Models to ONNX (Faster CPU Inference)
```bash
python backend/export_nllb_onnx.py
```

Converts the fine-tuned NLLB-200 models to ONNX format using [Hugging Face Optimum](https://github.com/huggingface/optimum). Provides ~3× faster inference on CPU and is particularly useful on the HF Space CPU tier where loading the full PyTorch NLLB model (~2.3 GB) can cause OOM errors.

**Output directories:**

| Direction | Source path | Output path |
|-----------|-------------|-------------|
| en2lun | `model/nllb_en2lun/` | `model/nllb_en2lun_onnx/` |
| lun2en | `model/nllb_lun2en/` | `model/nllb_lun2en_onnx/` |

**Export options used:**
- Task: `text2text-generation-with-past` (seq2seq with KV cache for decoder)
- ONNX opset: 14
- Optimization: `O2` (basic optimizations, safe for all runtimes)
- Encoder and decoder kept separate (`monolith=False`) for memory efficiency

**Post-export verification:** After each export, a smoke-test translation runs automatically (`"Hello"` for en→lun, `"ningenda"` for lun→en) to confirm the ONNX runtime loads and produces output correctly.

**Notes:**
- The old ONNX directory is deleted and recreated on each run — re-export after retraining to keep ONNX models in sync
- Provider selection uses `onnxruntime.get_available_providers()` at runtime — prefers `CUDAExecutionProvider` when available, otherwise `CPUExecutionProvider`
- `translate.py` automatically selects the best available NLLB backend at load time using this priority order:
  1. **INT8 ONNX** — `model/nllb_{direction}_int8/` (fastest; produced by `export_nllb_onnx_int8.py`)
  2. **FP32 ONNX** — `model/nllb_{direction}_onnx/` (produced by `export_nllb_onnx.py`)
  3. **PyTorch** — `model/nllb_{direction}/` (fallback; loads in `float16` on CPU to reduce memory)
- Decoder file auto-detected in priority order: `decoder_model_merged.onnx` (newer Optimum, `use_cache=True`) → `decoder_model.onnx` (`use_cache=False`); a clear error is raised if neither is found
- Requires `optimum[onnxruntime]` (already in `requirements.txt`); install with `pip install optimum[onnxruntime]` if missing

### 6d. Run Full Training Pipeline with New-Only Data + Full Deploy
```bash
python backend/run_full_training.py                                  # full pipeline (5 epochs each)
python backend/run_full_training.py --skip-marian                    # NLLB only, then MarianMT retrain
python backend/run_full_training.py --skip-nllb                      # MarianMT only
python backend/run_full_training.py --no-push                        # skip all pushes after training
python backend/run_full_training.py --retrain-marian-only            # just run the MarianMT retrain step
python backend/run_full_training.py --marian-en2lun-epochs 3         # custom epoch count for MarianMT en→lun
python backend/run_full_training.py --marian-lun2en-epochs 3         # custom epoch count for MarianMT lun→en
python backend/run_full_training.py --nllb-en2lun-epochs 8           # custom epoch count for NLLB en→lun
python backend/run_full_training.py --nllb-lun2en-epochs 8           # custom epoch count for NLLB lun→en
python backend/run_full_training.py --retrain-en2lun-epochs 3        # epochs for MarianMT retrain en→lun
python backend/run_full_training.py --retrain-lun2en-epochs 3        # epochs for MarianMT retrain lun→en
```

A focused alternative to `train_all.py` that trains on **new-only data** (pairs not yet seen by the models) and handles the full deploy chain in one command: HuggingFace Hub push → HF Space push → git push to both repos.

Each direction is trained as a separate step, so you can tune epoch counts independently for en→lun and lun→en without affecting the other direction.

**Options:**

| Flag | Default | Description |
|------|---------|-------------|
| `--marian-en2lun-epochs` | `5` | Training epochs for initial MarianMT English → Lunyoro (new-only data) |
| `--marian-lun2en-epochs` | `5` | Training epochs for initial MarianMT Lunyoro → English (new-only data) |
| `--nllb-en2lun-epochs` | `5` | Training epochs for NLLB-200 English → Lunyoro |
| `--nllb-lun2en-epochs` | `5` | Training epochs for NLLB-200 Lunyoro → English |
| `--retrain-en2lun-epochs` | `5` | Epochs for MarianMT retrain en→lun (validates on full val set) |
| `--retrain-lun2en-epochs` | `5` | Epochs for MarianMT retrain lun→en (validates on full val set) |
| `--skip-marian` | — | Skip initial MarianMT fine-tuning (retrain step still runs after NLLB) |
| `--skip-nllb` | — | Skip both NLLB fine-tuning steps |
| `--no-push` | — | Skip all post-training pushes (HF Hub, HF Space, git) |
| `--retrain-marian-only` | — | Skip all initial training; only run the MarianMT retrain step |

**Pipeline steps (in order):**
1. **MarianMT en2lun** — `train_marian.py --direction en2lun --new-only` *(skipped with `--skip-marian` or `--retrain-marian-only`)*
2. **MarianMT lun2en** — `train_marian.py --direction lun2en --new-only` *(skipped with `--skip-marian` or `--retrain-marian-only`)*
3. **NLLB en2lun** — `train_nllb.py --direction en2lun --new-only` *(skipped with `--skip-nllb` or `--retrain-marian-only`)*
4. **NLLB lun2en** — `train_nllb.py --direction lun2en --new-only` *(skipped with `--skip-nllb` or `--retrain-marian-only`)*
5. **MarianMT retrain en2lun** — `train_marian.py --direction en2lun --new-only` on new-only data, validated against the **full `val.csv`** *(always runs)*
6. **MarianMT retrain lun2en** — same as above for lun→en *(always runs)*
7. **HF Hub push** — `push_models.py --all`
8. **HF Space push** — `push_to_hf_space.py`
9. **Git push** — stages training CSVs + pipeline scripts (including `language_rules_gr4.py`, `language_rules_gr5.py`, `translate.py`, `generate_grammar_pairs.py`), commits with a datestamped message, and pushes to both `origin` and `k227` remotes

**Notes:**
- Steps 7–9 are skipped automatically if any training step fails
- `--new-only` trains only on `data/training/new_only_train.csv` (generated by `merge_untrained_data.py`); falls back to the full `train.csv` if that file doesn't exist. **MarianMT always validates on the full `val.csv`** regardless of `--new-only`, so BLEU scores are comparable across runs. NLLB also falls back to `val.csv` if `new_only_val.csv` doesn't exist.
- The MarianMT retrain step (steps 5–6) **always runs** unless `--skip-nllb` is also set; use `--retrain-marian-only` to run only those steps without any initial training.
- Each step prints a timestamped start/end line for easy progress tracking
- Exit code is non-zero if any training step fails
- Use `train_all.py` instead if you want to train on the full dataset or need per-batch-size control

### 6e. Tense Pairs Training Pipeline
```bash
python backend/train_tense_pipeline.py
# End-to-end pipeline for tense_pairs_100.csv:
#   1. Clean: remove empty rows, normalize whitespace, deduplicate, filter short Lunyoro (< 3 words)
#   2. Augment: inject domain tags ([GOVERNMENT], [AGRICULTURE], [CULTURE]) for domain awareness
#   3. Back-translate: translate Lunyoro → English via NLLB to create synthetic pairs
#   4. Merge: combine clean + augmented + back-translated into new_only_train.csv + new_only_val.csv
#   5. Train: fine-tune both MarianMT (both directions) and NLLB (en2lun + lun2en), 5 epochs each
```

**Input:** `data/cleaned/tense_pairs_100.csv` (100 hand-curated tense sentence pairs)

**Pipeline steps:**

| Step | Output | Description |
|------|--------|-------------|
| 1. Clean | `tense_pairs_clean.csv` | Remove empty/short rows, normalize whitespace, deduplicate |
| 2. Augment | `tense_pairs_augmented.csv` | Add 3 domain-tagged variants per pair for domain awareness |
| 3. Back-translate | `tense_pairs_backtranslated.csv` | NLLB lun→en round-trip creates synthetic English variants |
| 4. Merge | `new_only_train.csv` + `new_only_val.csv` | Combine all, shuffle, 90/10 train/val split |
| 5. Train | Model checkpoints | MarianMT both directions + NLLB en2lun + lun2en (5 epochs, `--new-only`) |

**Notes:**
- Uses `--new-only` flag so models train only on the tense pairs without re-training on the full dataset
- NLLB lun→en training applies `--min-lun-words 3` to filter single-word entries
- Back-translation step requires NLLB lun2en model to be available (run `python download_models.py` first)
- All intermediate files are saved to `data/cleaned/` for inspection

### 6f. Sentence Variations Training Pipeline
```bash
python backend/train_sentence_variations_pipeline.py                 # full pipeline (5 epochs)
python backend/train_sentence_variations_pipeline.py --skip-bt       # skip back-translation step
python backend/train_sentence_variations_pipeline.py --skip-train    # only prep data, skip training
python backend/train_sentence_variations_pipeline.py --epochs 3      # fewer training epochs
```

End-to-end pipeline for `sentence variations (2).xlsx` (tense variation pairs):

**Input:** `data/raw/sentence variations (2).xlsx`

**Pipeline steps:**

| Step | Output | Description |
|------|--------|-------------|
| 1. Load Excel | `sentence_variations_batch2_clean.csv` | Load raw Excel file from `data/raw/`, extract english-lunyoro pairs |
| 2. Clean | `sentence_variations_batch2_clean.csv` | Remove empty rows, normalize whitespace, lowercase Lunyoro, deduplicate, filter short Lunyoro (< 3 words) |
| 3. Augment | `sentence_variations_batch2_augmented.csv` | Add 3 domain-tagged variants per pair (`[CULTURE]`, `[DAILY_LIFE]`, `[RELIGION]`) |
| 4. Back-translate | `sentence_variations_batch2_bt.csv` | NLLB lun→en round-trip creates synthetic English variants (optional, skip with `--skip-bt`) |
| 5. Merge | `sv_batch2_train.csv` + `sv_batch2_val.csv` | Combine clean + augmented + back-translated, shuffle, 90/10 train/val split |
| 6. Train | Model checkpoints | Copies merged data to `new_only_train.csv`; trains MarianMT both directions + NLLB en2lun + lun2en (5 epochs, `--new-only`) |

**Options:**

| Flag | Default | Description |
|------|---------|-------------|
| `--skip-bt` | — | Skip back-translation step (useful when NLLB is unavailable) |
| `--skip-train` | — | Only prepare data, skip model training |
| `--epochs` | `5` | Number of training epochs for both MarianMT and NLLB |

**Notes:**
- Input is a raw Excel file (`data/raw/sentence variations (2).xlsx`) — the pipeline extracts english-lunyoro pairs automatically
- Uses `--new-only` flag so models train only on the sentence variation pairs without re-training on the full dataset
- The merged data is copied to `data/training/new_only_train.csv` before training — this is the file the `--new-only` flag in `train_marian.py` and `train_nllb.py` reads from
- NLLB lun→en training applies `--min-lun-words 3` to filter single-word entries
- Lunyoro side is lowercased during cleaning (consistent with training data conventions)
- Back-translation step loads the NLLB lun2en model directly via `transformers` (avoids importing `sentence_transformers`); requires the model locally or on HuggingFace Hub (run `python download_models.py` first)
- All intermediate files are saved to `data/cleaned/` for inspection

### 6g. Incremental Training Pipeline
```bash
python backend/train_incremental.py --new-data "data/raw/new_batch.csv"
python backend/train_incremental.py --new-data "data/raw/sentence variations (2).xlsx"
python backend/train_incremental.py                    # retrain on all existing data (no new file)
python backend/train_incremental.py --epochs 7         # more epochs
python backend/train_incremental.py --eval-only        # just evaluate current model
python backend/train_incremental.py --no-train         # only prepare data, skip training
python backend/train_incremental.py --no-push          # skip HuggingFace push
```

A unified incremental training pipeline that loads **human-verified** cleaned data (skipping augmented/back-translated files), merges in new data (CSV or Excel), and continues training from the current checkpoint — never from scratch. Designed for iteratively improving models as new batches of data arrive.

**Pipeline steps:**

| Step | Description |
|------|-------------|
| 1. Load existing | Scans `data/cleaned/*.csv` files for english + lunyoro columns, **skipping** files containing `augmented`, `bt_`, `back_translated`, or `backtranslated` in their name |
| 2. Load new data | Reads the `--new-data` file (CSV or Excel); auto-detects column layout |
| 3. Clean & validate | Removes empty/short pairs, normalizes whitespace, lowercases Lunyoro, deduplicates, filters pairs with < 2 words or > 200 words |
| 4. Merge & shuffle | Combines existing + new data, deduplicates, shuffles (seed=42) |
| 5. Save | Writes merged dataset to `data/training/full_train.csv` and `train.csv` |
| 6. Train | Continues training MarianMT (both directions) + NLLB (en2lun + lun2en) |
| 7. Evaluate | Runs `eval_bleu.py` on the fixed validation set |
| 8. Push | Uploads updated models to HuggingFace Hub |

**Options:**

| Flag | Default | Description |
|------|---------|-------------|
| `--new-data` | — | Path to new data file (CSV or Excel). If omitted, retrains on all existing data |
| `--epochs` | `5` | Number of training epochs |
| `--direction` | `both` | `en2lun`, `lun2en`, or `both` |
| `--eval-only` | — | Only evaluate current models, skip everything else |
| `--no-train` | — | Only prepare/merge data, skip training |
| `--no-push` | — | Skip pushing to HuggingFace after training |

**Notes:**
- Excel files are auto-detected: 8+ column format (sentence variations layout) extracts columns 2,4 and 6,7; 2-column format maps directly to english/lunyoro
- Cleaned new data is saved to `data/cleaned/incremental_{timestamp}.csv` for traceability
- Training log is appended to `logs/training_history.log`
- Uses the fixed validation set (`data/training/val.csv.bak`) for consistent evaluation across runs
- Always continues from the current model checkpoint — no cold-start resets
- Only human-verified data is loaded as the base dataset; augmented/back-translated CSVs (`augmented*`, `bt_*`, `back_translated*`, `backtranslated*`) are excluded to keep the training signal clean

### 7. Grammar Rules 4 Full Pipeline (Automated)
```bash
python backend/gr4_full_pipeline.py
# Complete automated pipeline for Grammar Rules 4 training data:
#   1. Extract clean pairs from language_rules_gr4.py
#   2. Back-translate for data augmentation
#   3. Clean and deduplicate
#   4. Merge into training data
#   5. Rebuild semantic index
#   6. Fine-tune MarianMT models (both directions, 5 epochs)
#   7. Fine-tune NLLB-200 models (both directions, 5 epochs)
# Estimated time: 1-3 hours (depending on hardware)
```

**Features:**
- Fully automated end-to-end pipeline (runs non-interactively, no confirmation prompt)
- Error handling with recovery options
- Summary report of completed/failed steps
- Orchestrates 7 pipeline steps sequentially

**Manual alternative** (run steps individually):
```bash
# Step 1: Extract GR4 pairs
python backend/extract_gr4_training_pairs.py

# Step 2: Back-translate for augmentation
python backend/back_translate.py --input data/cleaned/gr4_pairs.csv --output data/training/gr4_back_translated.csv

# Step 3: Merge back-translations
python backend/merge_back_translated.py --source data/training/gr4_back_translated.csv

# Step 4: Clean training data
python backend/clean_training_data.py

# Step 5: Rebuild semantic index
python backend/build_index.py

# Step 6: Fine-tune MarianMT
python backend/train_marian.py --direction both --epochs 5 --batch-size 32

# Step 7: Fine-tune NLLB-200
python backend/train_nllb.py --direction both --epochs 5 --batch-size 8
```

### 7b. Extract Grammar Rules 5 Training Pairs
```bash
python backend/extract_gr5_training_pairs.py
# Extracts clean English <-> Runyoro-Rutooro training pairs from grammar rules 5.docx
# (Chapters 5, 6, 7: locatives, sentences, noun classes 1a/2a/9a/10a)
# Writes pairs to data/cleaned/gr5_pairs.csv
# Merges 90% into train.csv and 10% into val.csv (skips duplicates)
```

**Coverage (~300 pairs across):**
- Chapter 5: locative agreement, locative demonstratives, genitive locatives, locative possessives, adverbial suffixes (-mu/-ho/-yo), concord prefix ha-, hamu/handi, ho + enumerative roots, dara + locative, copula ni- + locatives
- Chapter 6: sentence types, reversed-object sentences
- Chapter 7: noun class examples (classes 1/2/1a/2a/9/9a/10a), colour names, augmentative/pejorative forms, negative nouns, class 9 professional nouns, twin names, kinship terms

### 7c. Generate Grammar Training Pairs (Bulk)
```bash
python backend/generate_grammar_pairs.py
# Generates 8,000+ grammar training pairs from the rule tables in
# language_rules_gr4.py and language_rules_gr5.py.
# Output: data/cleaned/gr_grammar_pairs.csv  (english, lunyoro columns)
#
# On completion, prints:
#   - Total pair count
#   - Per-category breakdown (LOCATIVE, COPULA, KINSHIP, VERB_CONJ, etc.)
#   - Suggested next steps
```

**Coverage:**
- Locative constructions (all prefixes × nouns, + 15 sentence examples)
- Locative demonstratives (munu/muli/hanu/hali/kunu/kuli, + copula forms)
- Adverbial suffixes (-mu/-ho/-yo in sentence context)
- Locative possessives (omwange/owaawe/omwaitu etc., all 6 persons × omwa-/owa- types, + sentence examples)
- Enumerative pronouns (exclusive -enka/-onka, inclusive -ena/-ona, reflexive -enyini/-onyini, dual -embi/-ombi, all persons + sentence examples)
- Copula ni- + locatives (nihanu/nuho/numwo etc.)
- Dara presentative (all persons + noun classes)
- Demonstratives near/far (all 15 classes)
- Copula ni-/n- distribution (all 15 classes)
- Ka particle (emphatic + permissive, + sentence examples)
- Kinship terms (father/mother/grandparents/other relations × all persons, + sentence examples)
- Fractions and distributives
- Verb-to-noun derivation (agent/action/method)
- Colour names (all colours in sentence context)
- Negative nouns (omu-ta- pattern)
- Class 9 professional nouns
- Objectival concord sentences
- Verb conjugation tables (all 6 persons × tenses)

All pairs are tagged with a `[GRAMMAR]` prefix on the English side, NFC-normalised, and deduplicated before writing. After running, merge the output into training data and retrain:

```bash
python backend/merge_untrained_data.py
python backend/run_full_training.py --marian-epochs 5 --nllb-epochs 5
```

### 8. Upload Models to HuggingFace Hub
```bash
# Upload all models
python backend/upload_models_to_hf.py --token YOUR_HF_TOKEN

# Upload specific models
python backend/upload_models_to_hf.py --token YOUR_HF_TOKEN --models en2lun lun2en

# Use custom username/organization
python backend/upload_models_to_hf.py --token YOUR_HF_TOKEN --username your-username

# Available models: en2lun, lun2en, nllb_en2lun, nllb_lun2en, sem_model
```

**Features:**
- Uploads models directly to HuggingFace Hub (no Git LFS needed)
- Creates repositories automatically if they don't exist
- Supports selective model upload
- Configurable username/organization

### 9. Retrain from Human Feedback
```bash
python backend/retrain_from_feedback.py --epochs 5 --push
# Exports thumbs-up pairs → merges into train.csv → fine-tunes → pushes to HF
```

### 10. Automated Retraining (Background Service)
```bash
# Check current feedback stats
python backend/auto_retrain.py --stats

# Run single check (triggers retrain if threshold met)
python backend/auto_retrain.py --check

# Run as continuous monitoring service (checks every hour)
python backend/auto_retrain.py --monitor --interval 3600

# Custom threshold (overrides default of 100 new pairs)
python backend/auto_retrain.py --monitor --threshold 200
python backend/auto_retrain.py --check --threshold 50
```

### 11. Check Backend Syntax
```bash
python check_syntax.py
# Runs a quick AST parse over the core backend Python files to catch syntax
# errors before pushing or retraining.  Run from the project root
# (TRANSLATOR/).
#
# Files checked:
#   train_marian.py, train_nllb.py, back_translate_lun2en.py,
#   knowledge_graph.py, main.py, translate.py, eval_bleu.py,
#   run_full_training.py, run_k227_pipeline.py,
#   language_rules_gr4.py, language_rules_gr5.py
#
# Output:
#   OK  <filename>   — file parsed without errors
#   ERR <filename>: <SyntaxError message>  — file has a syntax error
#   "All OK" or "ERRORS FOUND - fix before pushing" summary line
```

### 11c. Inspect Benchmark Scores
```bash
python show_benchmarks.py
# Prints a formatted view of both benchmark score files:
#   - benchmark_scores.csv  — tabular dump of all benchmark entries
#   - benchmark_scores.json — per-entry breakdown showing:
#       Source text, domain, SQS score + band, and all eight
#       sub-scores (MNG, GRM, TNS, VCB, ORT, CTX, FLU, CUL)
# Run from the lunyoro-translator/ root directory.
```

### 11c-2. Benchmark ONNX Translation Speed
```bash
python backend/benchmark_onnx.py
# Requires the backend to be running on http://localhost:8000
#
# Sends 8 test sentences (4 EN→LUN + 4 LUN→EN) to the live API and
# measures wall-clock latency per call.  Reports:
#   - Per-call direction, elapsed time, source text, translation, and model used
#   - Total time + average time per call
#
# To compare ONNX FP32 (current) against INT8 quantized models:
#   1. Run: python backend/quantize_onnx_int8.py
#   2. Restart the backend
#   3. Run this benchmark again to see the INT8 latency improvement
```

### 11c-3. Grammar and Translation Quality Test
```bash
python backend/quality_test.py
# Requires the backend to be running on http://localhost:8000
#
# Evaluates the primary translation model (NLLB-200 INT8 ONNX) across key
# Runyoro-Rutooro linguistic features, grouped into four categories:
#
#   TENSES
#     — Present, past, future, and continuous forms for 1sg, 3sg, and 1pl
#       (e.g. "I eat food" / "He went to the market" / "I will go to school")
#
#   GRAMMAR AGREEMENT
#     — Subject-verb concord (noun classes 2, 8, 9), possession,
#       and object markers (ku-, m-)
#
#   COMPLEX SENTENCES
#     — Conditional clauses, relative clauses, object-in-relative,
#       negation, and perfect negation
#
#   REVERSE (LUN→EN)
#     — Six Lunyoro sentences covering past tense, future tense,
#       plural agreement, reported speech, universal statements,
#       and negation
#
# For each test case the script prints:
#   - Direction (EN→LUN or LUN→EN), source text
#   - Model translation and method used (e.g. "nllb", "marian", "retrieval")
#   - Expected linguistic form or gloss for manual evaluation
#
# Usage:
#   1. Start the backend: python backend/main.py
#   2. In another terminal: python backend/quality_test.py
```

### 11b. Inspect Training Data Composition
```bash
python backend/check_weights.py
# Prints a breakdown of training data by source:
#   - Total pairs in train.csv
#   - Domain-tagged pairs (e.g. [MEDICAL], [EDUCATION]) and their counts
#   - Pair counts per seed vocabulary file (medical, education, daily_life, low_freq, agriculture)
#   - gr4_pairs.csv and gr5_pairs.csv counts
#   - back_translated.csv and gr4_back_translated.csv counts
#   - english_nyoro_clean.csv (main corpus) count
# Run this after any data pipeline step to verify the training set composition.
```

### 11c. Inspect Dictionary POS Coverage
```bash
python backend/check_dict_pos.py
# Audits POS (part-of-speech) data in the cleaned dictionary and training set:
#   - Column listing and total entry count for runyoro_domain_dictionary_clean.csv
#   - POS value distribution (top 20 values, entries with/without POS data)
#   - 15 random sample entries that have POS annotations
#   - Count of domain-tagged pairs in train.csv (e.g. [MEDICAL], [EDUCATION])
#   - 10 random sample domain-tagged pairs (English + Lunyoro)
#   - Count of pairs with plural indicators (aba-/ebi-/emi-/ama-/en-/em-/utu-/zaa- prefixes)
#   - Count of POS-tagged training pairs ([NOUN]/[VERB]/[ADJ] in English column)
# Useful for verifying that POS and plural data from the domain dictionary
# were correctly propagated into the training set.
```

### 11d. Inspect lun→en Training Data Quality
```bash
python backend/check_lun2en_data.py
# Analyses the Lunyoro-side word count distribution across train.csv + val.csv
# to diagnose why the lun→en model may underperform:
#   - Word count statistics (min, max, mean, percentiles) for the Lunyoro column
#   - Pair counts split into three buckets:
#       lun_words <= 2  — single-word / two-word dictionary entries (hurt lun→en)
#       lun_words 3–4   — short phrases
#       lun_words >= 5  — full sentences (the useful signal for lun→en)
#   - Total pair count
#   - Count of [DOMAIN]-tagged pairs (en→lun format only; useless as lun→en source)
#   - Percentage of sentence-level pairs (lun_words >= 5) vs total
# Use this to decide whether to filter short pairs before lun→en training
# (e.g. pass --min-lun-words 3 to train_marian.py / train_nllb.py).
```

### 11e. Inspect Back-Translation Candidates
```bash
python backend/check_bt_candidates.py
# Analyses train.csv + val.csv to identify which pairs are useful candidates
# for back-translation augmentation and which are redundant:
#   - Tagged pairs (en→lun-only format, e.g. [MEDICAL] prefix):
#       The lun→en model never saw these as source — back-translating their
#       English produces genuinely new lun→en training data.
#   - Short dict pairs (lun_words <= 2):
#       Filtered out of lun→en training by --min-lun-words; their English side
#       is valid but the Runyoro side is too short to be useful as source.
#   - Good sentence pairs (lun_words >= 3, no tag):
#       Already in lun→en training — back-translating these is redundant.
#   - Back-translation candidates (useful):
#       Union of tagged pairs + short dict pairs where en_words >= 5,
#       so the back-translation produces a real sentence rather than a fragment.
#   - Remaining candidates after subtracting already-back-translated pairs (~10,928).
# Use this to gauge how many new lun→en pairs a back-translation run can yield
# before deciding whether to run back_translate.py again.
```

**Features:**
- Monitors `feedback.jsonl` for approved pairs
- Auto-cleans and validates feedback (length, repetition, language detection)
- Triggers retraining when 100+ new clean pairs collected (configurable via `--threshold`)
- Runs as background service or scheduled task
- Logs to `auto_retrain.log`

**Expected improvements:** +5-10 BLEU after full pipeline

### 11f. Analyze Back-Translation Coverage Across All Sources
```bash
python backend/analyze_bt_coverage.py
# Scans every CSV in data/cleaned/ and the training set to identify which
# English sentences have NOT been back-translated yet.
#
# Reports:
#   - Already back-translated: count from back_translated_lun2en.csv
#   - Per-source breakdown: total rows, BT-able (en_words >= 5, not in training),
#     already done, and remaining — printed as an aligned table
#   - Tagged training pairs (en2lun-only format) not yet back-translated
#   - Grand total remaining candidates
#   - Top 10 sources by remaining candidate count
#
# Output:
#   data/cleaned/bt_remaining_candidates.csv
#     Columns: source (filename), english (sentence)
#     Contains all remaining candidates, deduplicated.
#
# Suggested next step printed at the end:
#   python back_translate_lun2en.py --max-sentences N --merge
```

**When to run:**
- Before a back-translation run to gauge how many new lun→en pairs are available
- After `merge_untrained_data.py` to see which newly merged sources still need back-translation
- To prioritise which source files to target in the next `back_translate_lun2en.py` run

### 11g. Deep-Analyze Back-Translation Quality and Untapped Sources
```bash
python backend/analyze_bt_quality.py
# Deep analysis of why BT candidates are being rejected and whether
# there are untapped data sources not yet covered by back-translation.
#
# Reports:
#   - Already back-translated: count from back_translated_lun2en.csv
#   - Breakdown of remaining 22,865 tagged pairs (en_words >= 5):
#       how many are already BT'd vs still remaining, word-length
#       distribution of remaining pairs, and 5 sample sentences
#   - Raw data files (data/raw/*.csv): per-file totals and count of
#       new BT-able sentences (en_words >= 5, not in training, not
#       already back-translated)
#   - Cleaned data files (data/cleaned/*.csv): same per-file breakdown,
#       skipping already-processed files (back_translated_lun2en.csv,
#       bt_remaining_candidates.csv, dictionary_lookup.csv)
#   - dictionary_lookup.csv: dedicated check for BT-able entries
#       (en_words >= 5, not in training or already BT'd)
#   - Grand total of new untapped BT candidates across all sources
#
# Conclusion section:
#   - If total_new < 1,000: confirms all major sources are covered and
#     recommends lowering --min-lun-words to 4 or using more beam search
#     with the NLLB model (BLEU=73.97) to recover more pairs from the
#     existing 22,865 tagged candidates
#   - If total_new >= 1,000: prints the exact count and suggests:
#       python back_translate_lun2en.py --max-sentences N --merge
```

**When to run:**
- Before deciding whether to lower `--min-lun-words` in a back-translation run
- To confirm there are no overlooked CSV sources before starting a long BT job
- After adding new raw/cleaned data files to check if they contain BT candidates

---

## Project Structure

```
lunyoro-translator/
├── backend/
│   ├── main.py                      # FastAPI server
│   ├── translate.py                 # Translation logic (MT + retrieval)
│   ├── language_rules.py            # Runyoro grammar rules (3200+ lines)
│   ├── language_rules_gr4.py        # Grammar Rules 4: copula, kinship, enumeratives, ka particle, demonstratives, dara presentative, verb-noun derivation
│   ├── language_rules_gr5.py        # Grammar Rules 5: locatives, demonstratives, noun classes 1a/2a/9a/10a, colours, augmentatives
│   ├── build_index.py               # Build semantic search index from dictionary
│   ├── clean_training_data.py       # Data cleaning script
│   ├── clean_ocr_pairs.py           # Remove noisy/truncated rows from ocr_pairs_extracted.csv
│   ├── back_translate.py            # Back-translation augmentation
│   ├── retrain_tokenizer.py         # SentencePiece retraining
│   ├── export_to_onnx.py            # Export MarianMT models to ONNX for 2-5x faster CPU inference (en2lun_onnx/ + lun2en_onnx/)
│   ├── benchmark_onnx.py            # Benchmark ONNX FP32 vs INT8 translation speed and quality against the live API
│   ├── quality_test.py              # Grammar and translation quality evaluation: tenses, agreement, complex sentences, lun→en — prints model output alongside expected linguistic forms for manual review
│   ├── train_all.py                 # Unified pipeline: MarianMT + NLLB sequentially, then HF push
│   ├── run_full_training.py         # New-only data pipeline: MarianMT (initial) + NLLB + MarianMT retrain on full val → HF Hub + HF Space + git push; supports --retrain-marian-only to run only the retrain step
│   ├── train_marian.py              # MarianMT fine-tuning
│   ├── train_nllb.py                # NLLB-200 fine-tuning
│   ├── extract_gr4_training_pairs.py # Extract GR4 training pairs
│   ├── extract_gr5_training_pairs.py # Extract GR5 training pairs (locatives, sentences, noun classes)
│   ├── generate_grammar_pairs.py    # Generate 8,000+ grammar pairs from GR4/GR5 rule tables → data/cleaned/gr_grammar_pairs.csv
│   ├── gr4_full_pipeline.py         # Complete GR4 training pipeline (automated)
│   ├── upload_models_to_hf.py       # Upload models to HuggingFace Hub
│   ├── push_to_hf_space.py          # Push full backend to HF Space (skips unchanged files)
│   ├── push_to_kathay.py            # Push NLLB models + backend to the kathay HF account (separate Space with NLLB as primary)
│   ├── push_kathay_onemodel.py      # Update kathay Space to load only NLLB en2lun (saves ~2.3GB RAM, fits cpu-basic 16GB limit)
│   ├── push_kathay_nllb_only.py     # Update kathay Space: both NLLB directions, no MarianMT — pushes translate.py + main.py alongside config
│   ├── push_kathay_dockerfile.py   # Force-update kathay Space Dockerfile only (re-downloads NLLB on startup to fix missing sentencepiece.bpe.model)
│   ├── push_kathay_update.py       # Update kathay Space: switch download_models.py to use kathay/ NLLB repos (with sentencepiece) + force re-download Dockerfile
│   ├── push_kathay_both.py         # Enable both NLLB + MarianMT on kathay Space with T4 GPU — downloads from kathay/ (NLLB) and keithtwesigye/ (MarianMT) repos
│   ├── force_push_space.py          # Force-commit specific files to HF Space via create_commit (always triggers rebuild)
│   ├── feedback_store.py            # Human feedback storage + auto-export
│   ├── retrain_from_feedback.py     # End-to-end feedback retraining
│   ├── auto_retrain.py              # Automated retraining service
│   ├── view_analytics.py            # View feedback analytics in terminal
│   ├── export_analytics.py          # Export analytics to Excel/CSV
│   ├── merge_untrained_data.py      # Merge all clean data not yet in train/val into training splits
│   ├── check_weights.py             # Inspect training data composition (pair counts by source)
│   ├── check_lun2en_data.py         # Analyse lun→en data quality: word-count distribution, sentence vs dict-entry ratio, [DOMAIN]-tag count
│   ├── check_bt_candidates.py       # Identify useful back-translation candidates: tagged pairs + short dict pairs with en_words >= 5
│   ├── check_dict_pos.py            # Audit POS coverage in domain dictionary and training set
│   ├── analyze_bt_coverage.py       # Scan all CSVs for sentences not yet back-translated; outputs bt_remaining_candidates.csv
│   ├── analyze_bt_quality.py        # Deep analysis of BT rejection reasons + untapped data sources; recommends next steps
│   ├── feedback/                    # Auto-exported feedback files
│   │   ├── all_feedback.csv         # Raw feedback data (auto-updated)
│   │   ├── feedback_analytics.xlsx  # Multi-sheet analytics (auto-updated)
│   │   ├── benchmark_scores.csv     # Benchmark entries with SQS scores (GitHub-synced)
│   │   └── benchmark_scores.json    # Same benchmark data in JSON (GitHub-synced)
│   ├── model/
│   │   ├── en2lun/                  # MarianMT English→Lunyoro
│   │   ├── lun2en/                  # MarianMT Lunyoro→English
│   │   ├── en2lun_onnx/             # ONNX export of MarianMT en2lun (generated by export_to_onnx.py)
│   │   ├── lun2en_onnx/             # ONNX export of MarianMT lun2en (generated by export_to_onnx.py)
│   │   ├── nllb_en2lun/             # NLLB-200 English→Lunyoro
│   │   ├── nllb_lun2en/             # NLLB-200 Lunyoro→English
│   │   └── translation_index.pkl    # Semantic search index (80k pairs)
│   └── data/
│       ├── training/
│       │   ├── train.csv            # 80k training pairs
│       │   ├── val.csv              # 4.5k validation pairs
│       │   ├── test.csv             # 4.5k test pairs
│       │   ├── new_only_train.csv   # Pairs not yet trained on (train split, generated by merge_untrained_data.py)
│       │   ├── new_only_val.csv     # Pairs not yet trained on (val split, generated by merge_untrained_data.py)
│       │   ├── sv_batch2_train.csv   # Sentence variations pipeline output (train split)
│       │   └── sv_batch2_val.csv    # Sentence variations pipeline output (val split)
│       ├── cleaned/                 # Cleaned dictionary/corpus
│       └── raw/                     # Raw seed vocabulary
├── frontend/
│   ├── components/Translator.tsx    # Main translation UI
│   ├── components/ChatPage.tsx      # Chat assistant UI
│   ├── components/RunyoroEditor.tsx # Runyoro-Rutooro writing editor (spellcheck, grammar hints, AI review, formatting)
│   ├── components/Dictionary.tsx    # Dictionary lookup UI
│   ├── components/History.tsx       # Translation history UI
│   ├── components/VoiceTranslator.tsx # Voice input translation UI
│   ├── components/TopBar.tsx        # Top navigation bar (shows section title + back button for inner pages)
│   ├── components/BottomNav.tsx     # Fixed bottom navigation bar (Home, Translate, Chat, Editor, Dictionary, History, Voice)
│   └── app/                         # Next.js app router
├── TRAINING_GUIDE.md                # Model improvement guide
├── PIPELINE_GUIDE.md                # Data pipeline guide
├── show_benchmarks.py               # Print benchmark_scores.csv + .json to terminal
└── push_benchmark_files.py          # Push benchmark_scores.csv + .json to GitHub repos
```

---

## API Endpoints

### Translation
- `POST /translate` — English → Lunyoro
  - Parameters: `text` (required), `context` (optional, previous sentence for coherence), `refine` (optional bool, default `false` — when `true` and `HF_TOKEN` is set, runs a Qwen 2.5 7B pass to improve grammar, noun-class agreement, R/L rule, apostrophe elision, and kinship terms before returning the result), `direction` (optional string, default `"en->lun"` — accepted for API compatibility but ignored; the endpoint itself determines the translation direction)
- `POST /translate-reverse` — Lunyoro → English
  - Parameters: `text` (required), `context` (optional), `refine` (optional bool, default `false` — when `true` and `HF_TOKEN` is set, runs a Qwen 2.5 7B pass to improve fluency, accuracy, and natural phrasing of the English output before returning the result), `direction` (optional string — accepted for API compatibility but ignored; use `/translate` for en→lun and `/translate-reverse` for lun→en)
- `POST /lookup` — Dictionary word lookup
- `POST /spellcheck` — Lunyoro spellcheck

### Chat
- `POST /chat` — AI language assistant (Qwen 2.5 7B). Replies in English only, plain prose, 2–4 paragraphs. System prompt includes the startup grammar context (built from `get_grammar_context()`, `get_gr4_grammar_context()`, and `get_gr5_grammar_context()` with per-section budgets totalling ~6000 chars) and up to 2 corpus examples retrieved by semantic similarity. Rate-limited to 5 requests per 60 seconds per IP.

### Feedback
- `POST /feedback` — Submit translation rating with optional error categorization and corrections
  - Parameters: `source_text`, `translation`, `direction`, `rating` (1/-1), `correction` (optional), `error_type` (optional - comma-separated list for multiple error types), `model_used` (optional - "marian", "nllb", "both", "none"), `refined` (optional boolean - whether AI refinement was applied to the translation)
  - **Auto-export:** Automatically exports feedback to `backend/feedback/` folder after each submission
    - `all_feedback.csv` — Complete feedback log in CSV format
    - `feedback_analytics.xlsx` — Multi-sheet Excel workbook with analytics
- `GET /feedback/stats` — Feedback statistics
- `GET /feedback/export` — Export approved (thumbs-up) pairs to `backend/feedback/approved_pairs.csv`
  - Returns: `count`, `files`, `path` to exported CSV

### Analytics
Feedback is automatically exported to `backend/feedback/` after each submission. You can also generate comprehensive reports on-demand:

```bash
# View analytics in terminal
python backend/view_analytics.py

# Export to Excel (single file with multiple sheets)
python backend/export_analytics.py

# Export to CSV files (separate files per report)
python backend/export_analytics.py --csv

# Custom output path
python backend/export_analytics.py --output reports/feedback_report.xlsx
python backend/export_analytics.py --csv --output reports/csv_export/
```

**Auto-exported files** (in `backend/feedback/`):
- `all_feedback.csv` — Raw feedback data with all fields
- `benchmark_scores.csv` — Benchmark entries with SQS scores (synced to GitHub via `push_benchmark_files_to_github()`)
- `benchmark_scores.json` — Same benchmark data in JSON format (synced to GitHub alongside the CSV)
- `feedback_analytics.xlsx` — Excel workbook with up to 6 sheets:
  - **All Feedback:** Complete feedback log with readable labels
  - **Summary:** Total feedback, approval rates, unique users
  - **Model Usage:** Usage statistics by model (MarianMT, NLLB-200, both, none)
  - **Error Types:** Breakdown of reported error categories
  - **Daily Activity:** Feedback timeline by date
  - **Refined vs Unrefined:** Approval rates comparing AI-refined translations against unrefined MT output (only present when `refined` field is available in feedback data)
- `approved_pairs.csv` — Approved (thumbs-up) translation pairs ready for retraining (exported via `/feedback/export` endpoint)

**On-demand reports** (via `export_analytics.py`):
- **Summary Statistics:** Total feedback, approval rates, correction rates, unique users
- **Model Performance:** MarianMT vs NLLB-200 comparison with winner determination
- **Error Analysis:** Breakdown of error types (grammar, spelling, context, vocabulary, etc.)
- **Direction Statistics:** Performance by translation direction (en→lun vs lun→en)
- **Daily Activity:** Feedback timeline with day-of-week analysis
- **User Engagement:** Anonymized user activity and engagement scores
- **Raw Feedback Data:** Complete feedback log with all fields

### Knowledge Graph
A structured graph of Runyoro-Rutooro grammar knowledge (noun classes, tenses, derivations, rules) that powers explainable AI translation and grammar tutoring.

- `GET /knowledge-graph/stats` — Node and edge counts by type
- `GET /knowledge-graph/noun-class/{class_num}` — Full info for a noun class (concords, plural class, example words). Accepts integers 1–15 or string keys `1a`, `2a`, `9a`, `10a`
- `GET /knowledge-graph/explain/{word}` — Explain a word: its noun class, derivation chain, plural/singular forms, and applicable grammar rules (explainable AI)
- `GET /knowledge-graph/related/{word}` — Find nodes related to a word. Optional query params: `rel` (relationship filter, e.g. `DERIVES_FROM`, `PLURAL_IS`, `BELONGS_TO`) and `direction` (`out`, `in`, or `both`)
- `GET /knowledge-graph/path?word_a=X&word_b=Y` — Find the grammatical relationship path between two words (e.g. `okulima` → `omulimi` → `nc_1`)
- `GET /knowledge-graph/correct?word=X&target=Y` — Get the correct grammatical form of a word. `target`: `plural`, `singular`, `agent_noun`, `action_noun`, `source_verb`
- `POST /knowledge-graph/tutor` — Answer a natural-language grammar question. Body: `{ "question": "..." }`. Supports questions like *"What is the plural of omuntu?"*, *"What class is ekitabu?"*, *"What is the agent noun of okulima?"*
- `GET /knowledge-graph/search?q=X` — Search nodes by label (case-insensitive substring). Optional `node_type` filter (`WORD`, `NOUN_CLASS`, `TENSE`, `RULE`, `DERIVATION`, etc.). Returns up to 50 results
- `GET /knowledge-graph/export` — Export the full knowledge graph as JSON (all nodes and edges — for frontend graph visualisation)
- `GET /knowledge-graph/tenses` — All tense nodes with their markers and examples
- `GET /knowledge-graph/derivations` — All verb derivation types with their suffixes

### Camera OCR Translation
- `POST /ocr-translate` — Upload an image file, run OCR to detect text regions, translate each region, and return bounding boxes with original + translated text for overlay rendering
  - Parameters: `file` (image upload, required), `direction` (query param, default `"en->lun"`)
  - Returns: `regions` (array of detected text with translations and bounding boxes), `image_size`, `direction`, `total_detected`, `total_translated`
  - Each region includes: `original`, `translated`, `confidence`, `bbox` (pixel coordinates), `bbox_norm` (0–1 normalized coordinates for responsive overlay)
  - Requires: `easyocr` (Python < 3.12 only), `pytesseract`, `opencv-python-headless`
- `POST /ocr-translate-base64` — Accept a base64-encoded image frame (from camera feed), run OCR + translate. Optimized for real-time camera usage with a cached EasyOCR reader instance
  - Body: `{ "image": "<base64 string or data URL>", "direction": "en->lun" }`
  - Returns: `regions` (array with `original`, `translated`, `confidence`, `bbox_norm`), `image_size`, `direction`
  - Low-confidence detections (< 0.3) are filtered out automatically

### Utilities
- `POST /summarize-pdf` — Extract + translate + summarize documents. When a Lunyoro document is detected, grammar rules (nasal assimilation, particle elision, kinship correction, copula normalization) are applied to each sentence before translation. Qwen 2.5 7B (if `HF_TOKEN` is set) refines **both** the MarianMT and NLLB-200 drafts independently, with Grammar Rules 4 post-processing applied to each refined output. The best result (NLLB-refined preferred, Marian-refined as fallback) is returned as `summary_lunyoro`. All four variants are included in the response: `summary_lunyoro` (best), `summary_lunyoro_marian` (Marian-refined), `summary_lunyoro_nllb` (NLLB-refined). Falls back to the MT draft per model if Qwen is unavailable.
- `GET /language-rules` — Full grammar rules JSON
- `POST /language-rules/apply` — Apply specific grammar rule
- `GET /history` — Translation history
- `GET /health` — Health check

---

## Models

All models are automatically loaded from HuggingFace Hub on first use and cached locally:

- **MarianMT en2lun:** [keithtwesigye/lunyoro-en2lun](https://huggingface.co/keithtwesigye/lunyoro-en2lun)
- **MarianMT lun2en:** [keithtwesigye/lunyoro-lun2en](https://huggingface.co/keithtwesigye/lunyoro-lun2en)
- **NLLB en2lun:** [keithtwesigye/lunyoro-nllb_en2lun](https://huggingface.co/keithtwesigye/lunyoro-nllb_en2lun)
- **NLLB lun2en:** [keithtwesigye/lunyoro-nllb_lun2en](https://huggingface.co/keithtwesigye/lunyoro-nllb_lun2en)
- **Semantic search:** [sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2](https://huggingface.co/sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2)
- **Image classification:** [google/mobilenet_v2_1.0_224](https://huggingface.co/google/mobilenet_v2_1.0_224) — lightweight ImageNet classifier for object recognition in uploaded images
- **Chat:** [Qwen/Qwen2.5-7B-Instruct](https://huggingface.co/Qwen/Qwen2.5-7B-Instruct) via HF Router

**Note:** Models are downloaded automatically on first translation request. To pre-download all models, run `python backend/download_models.py`.

---

## Grammar Rules

Comprehensive Runyoro-Rutooro grammar implementation (3200+ lines):

- **R/L Rule:** L → R except adjacent to e/i
- **Nasal assimilation:** nb→mb, np→mp, nr→nd, nl→nd
- **Apostrophe elision:** na ente → n'ente, habwa okugonza → habw'okugonza; also corrects merged model outputs — both cases where the particle vowel is retained but not elided (e.g. `nomuntu` → `n'omuntu`) and cases where it is dropped entirely (e.g. `nente` → `n'ente`)
- **Consonant+suffix mutations:** r/t/j + -ire → z/s/z + -ire
- **Noun class system:** 15 classes with concordial agreement
- **Verb conjugation:** 10+ tenses, derivative suffixes (causative, passive, etc.)
- **Pronominal system:** Subject/object concords, demonstratives, possessives
- **Numbers & ordinals:** Cardinals 1-1M, ordinal formation rules
- **Particles:** Genitive, copula, conditional, coordinating
- **Grammar Rules 4** (`language_rules_gr4.py`): copula constructions, kinship terms, enumeratives, and the *ka* diminutive/adverbial particle; also corrects split demonstrative forms (`o nu` → `onu`, `ba li` → `bali`, etc.), merges split *dara* presentative constructions (`dara nyowe` → `daranyowe`, `dara bo` → `darabo`, etc.), and fixes space-separated verb-derived nouns (`omu limi` → `omulimi`, `en dima` → `endima`, etc.) — applied as a final post-processing pass on en→lun output via `apply_gr4_rules()`
- **Grammar Rules 5** (`language_rules_gr5.py`): locative adverbial prefixes (omu-/ha-/ku-/owa-/omba), locative demonstratives (munu/muli/hanu/hali/kunu/kuli), self-standing adverbials (-o of reference), adverbial suffixes (-mu/-ho/-yo), locative possessives, copula ni- + locatives, *dara* + locative, *ho* + enumerative roots, objectival concord, noun classes 1a/2a/9a/10a (names, foreign words, colours), negative nouns (omu-ta-), class 9 professional nouns, and augmentative/pejorative forms — wired into `translate.py` post-processing via `apply_gr5_rules()`

**Grammar context functions** (used to inject rules into LLM prompts):

| Function | Module | Description |
|----------|--------|-------------|
| `get_grammar_context()` | `language_rules.py` | Compact (~1 KB) summary covering the R/L rule, nasal assimilation, apostrophe elision, noun classes 1–14, verb subject concords, tense markers, kinship terms, negation, and copula. Used as the base layer in the startup grammar context cache. |
| `get_extended_grammar_context()` | `language_rules.py` | Extended context that wraps `get_grammar_context()` with additional OCR-derived rules for chat/translation prompts. |
| `get_gr4_grammar_context()` | `language_rules_gr4.py` | GR4 rules: copula, kinship, enumeratives, ka particle. |
| `get_gr5_grammar_context()` | `language_rules_gr5.py` | GR5 rules: locatives, colours, augmentatives, negative nouns. |

At startup, `main.py` assembles a prioritised context cache (`_GRAMMAR_CONTEXT_CACHE`) by slicing each function's output to a fixed budget (core: 2000 chars, gr4: 1800 chars, gr5: 2200 chars) and concatenating them, keeping the total well within the LLM's context window.

See `backend/language_rules.py`, `backend/language_rules_gr4.py`, and `backend/language_rules_gr5.py` for full implementation.

---

## Data Sources

- **Dictionary:** Runyoro-Rutooro Dictionary (OCR + manual entry)
- **Corpus:** 80k+ sentence pairs from:
  - Bible translations
  - Seed vocabulary (medical, agriculture, education, daily life)
  - Community submissions
  - Grammar examples
- **Grammar:** *A Grammar of Runyoro-Rutooro* + Orthography Guide (1995)

---

## Deployment

### Upload Models to HuggingFace Hub
```bash
# Set your HuggingFace token
export HF_TOKEN=hf_...

# Upload all models
python backend/upload_models_to_hf.py --token $HF_TOKEN

# Or use environment variable
python backend/upload_models_to_hf.py
```

This uploads models to HuggingFace Hub, removing the need for Git LFS storage. Models are then downloaded on-demand via `download_models.py`.

### HuggingFace Space (Backend)
```bash
python backend/push_to_hf_space.py
# Pushes to: keithtwesigye-runyoro-translator-api.hf.space
```

#### Push to the kathay HuggingFace account (secondary Space)
```bash
# Requires HF_KATHAY_TOKEN env var (or edit the default token in the script)
python backend/push_to_kathay.py
# Pushes to: kathay/runyoro-translator-api (https://huggingface.co/spaces/kathay/runyoro-translator-api)
```

Uploads the NLLB fine-tuned models to the `kathay` HuggingFace account and configures a Docker Space that uses them:

1. **NLLB models pushed:**
   - `model/nllb_en2lun_pre_nyo` → `kathay/lunyoro-nllb-en2lun`
   - `model/nllb_lun2en_pre_nyo` → `kathay/lunyoro-nllb-lun2en`
2. **Backend files uploaded** to `kathay/runyoro-translator-api` Space (same exclusion rules as `push_to_hf_space.py`)
3. **kathay-specific Dockerfile** committed to the Space — sets `HF_USERNAME=kathay` so models are loaded from `kathay/` repos; enables both NLLB and MarianMT (`DISABLE_NLLB=0`, `DISABLE_MARIAN=0`); configures CORS for `horizonx.kathay.tech`
4. **README.md** committed to the Space with Space metadata (emoji, SDK, pinned, model list)

Upload retries automatically (up to 3 attempts per file with a 5-second back-off).

**Notes:**
- The token is read from `HF_KATHAY_TOKEN` env var; a default value is embedded in the script as a fallback — replace it or set the env var before sharing the file
- Upgrade the Space hardware to `cpu-upgrade` or `t4-small` after the first push — `cpu-basic` does not have enough RAM to load NLLB-200 (2.3 GB per model)
- MarianMT models are still loaded from `keithtwesigye/` repos (unchanged)
- CORS is pre-configured for `https://horizonx.kathay.tech` and `https://frontend-six-phi-25.vercel.app`

#### Reduce kathay Space RAM usage (single NLLB model)
```bash
python push_kathay_onemodel.py
# Updates kathay/runyoro-translator Space to load only NLLB en2lun
# Saves ~2.3GB RAM by skipping NLLB lun2en — fits within cpu-basic 16GB limit
# lun→en direction uses MarianMT only (still good quality)
```

Commits an updated `download_models.py` to the `kathay/runyoro-translator` Space that downloads only NLLB en2lun (not both directions). This reduces peak RAM from ~18GB to ~16GB, allowing the Space to run on `cpu-basic` hardware without OOM errors.

**Trade-off:** The lun→en direction loses NLLB-200 (uses MarianMT only). To restore both NLLB directions, upgrade hardware:
```python
api.request_space_hardware("kathay/runyoro-translator", "cpu-upgrade")
```

#### Deploy kathay Space with both NLLB directions (no MarianMT)
```bash
python push_kathay_nllb_only.py
# Updates kathay/runyoro-translator Space to run NLLB en2lun + lun2en only
# MarianMT is disabled (DISABLE_MARIAN=1) — saves ~600MB RAM
# Pushes translate.py and main.py alongside the NLLB-only config
```

Commits an updated `download_models.py`, `Dockerfile`, `translate.py`, and `main.py` to the `kathay/runyoro-translator` Space. The Dockerfile sets `DISABLE_MARIAN=1` so only NLLB models are loaded at startup.

**Files committed:**

| File | Purpose |
|------|---------|
| `download_models.py` | NLLB-only download script (skips MarianMT) |
| `Dockerfile` | Docker config with `DISABLE_MARIAN=1` and CORS for `horizonx.kathay.tech` |
| `translate.py` | Latest translation logic (grammar rules, post-processing) |
| `main.py` | Latest FastAPI server (endpoints, feedback, chat) |

**Notes:**
- Both NLLB directions (en→lun and lun→en) are loaded — requires `cpu-upgrade` hardware or higher
- `translate.py` and `main.py` are pushed from the local backend to keep the kathay Space in sync with the latest code
- MarianMT is fully disabled; all translation goes through NLLB with retrieval/dictionary fallback

#### Force re-download NLLB models on kathay Space (Dockerfile-only push)
```bash
python push_kathay_dockerfile.py
# Commits only a Dockerfile to kathay/runyoro-translator Space
# Forces NLLB model re-download at container start (fixes missing sentencepiece.bpe.model)
# MarianMT disabled (DISABLE_MARIAN=1) — NLLB only
```

Pushes a standalone Dockerfile to the `kathay/runyoro-translator` Space that wipes cached NLLB model files and re-downloads them from HuggingFace Hub on startup. Use this when the Space has a corrupted or incomplete model cache (e.g. missing `sentencepiece.bpe.model`).

**Dockerfile behaviour:**
- Removes any existing `/app/model/nllb_*` directories at container start
- Runs `download_models.py --force` to fetch fresh copies
- Sets `FORCE_OFFLINE=1` after download (fully offline inference via `TRANSFORMERS_OFFLINE=1`)
- MarianMT disabled (`DISABLE_MARIAN=1`), NLLB enabled (`DISABLE_NLLB=0`)
- CORS configured for `horizonx.kathay.tech` and `frontend-six-phi-25.vercel.app`

**Notes:**
- Only the Dockerfile is committed — no other backend files are modified
- Triggers a full Space rebuild which takes ~5–10 minutes (model download included)
- After the first successful boot, subsequent restarts use the Docker layer cache

#### Update kathay Space to use kathay NLLB repos (with sentencepiece)
```bash
python push_kathay_update.py
# Commits download_models.py + Dockerfile to kathay/runyoro-translator Space
# Switches NLLB model source to kathay/ repos (which include sentencepiece.bpe.model)
# Forces re-download on every container start to ensure fresh, complete models
# MarianMT disabled (DISABLE_MARIAN=1) — NLLB only
```

Pushes an updated `download_models.py` and `Dockerfile` to the `kathay/runyoro-translator` Space. The key change is that `download_models.py` now downloads NLLB models from `kathay/lunyoro-nllb-en2lun` and `kathay/lunyoro-nllb-lun2en` (which include the `sentencepiece.bpe.model` file) instead of the `keithtwesigye/` repos.

**Files committed:**

| File | Purpose |
|------|---------|
| `download_models.py` | NLLB-only download script pointing to `kathay/` repos |
| `Dockerfile` | Docker config with forced re-download, `DISABLE_MARIAN=1`, CORS for `horizonx.kathay.tech` and `frontend-six-phi-25.vercel.app` |

**Dockerfile behaviour:**
- Removes any existing `/app/model/nllb_*` directories at container start (`rm -rf`)
- Runs `download_models.py --force` to fetch fresh copies from `kathay/` repos
- Sets `FORCE_OFFLINE=1` after download (fully offline inference via `TRANSFORMERS_OFFLINE=1`)
- MarianMT disabled (`DISABLE_MARIAN=1`), NLLB enabled (`DISABLE_NLLB=0`)
- CORS configured for `horizonx.kathay.tech` and `frontend-six-phi-25.vercel.app`

**Notes:**
- Use this when the kathay Space fails with missing `sentencepiece.bpe.model` errors — the kathay repos include this file while the keithtwesigye repos may not
- Triggers a full Space rebuild (~5–10 minutes including model download)
- The `download_models.py` also downloads the sentence-transformer semantic model (`paraphrase-multilingual-MiniLM-L12-v2`)

#### Enable both NLLB + MarianMT on kathay Space (T4 GPU)
```bash
python push_kathay_both.py
# Commits download_models.py + Dockerfile to kathay/runyoro-translator Space
# Enables both NLLB and MarianMT models (requires T4 GPU hardware)
# NLLB downloaded from kathay/ repos, MarianMT from keithtwesigye/ repos
```

Pushes an updated `download_models.py` and `Dockerfile` to the `kathay/runyoro-translator` Space that loads **both** model families at startup. Unlike `push_kathay_nllb_only.py` (which disables MarianMT), this configuration runs the full dual-model pipeline for maximum translation quality.

**Files committed:**

| File | Purpose |
|------|---------|
| `download_models.py` | Downloads both NLLB (from `kathay/`) and MarianMT (from `keithtwesigye/`) repos, plus the sentence-transformer semantic model |
| `Dockerfile` | Docker config with `DISABLE_NLLB=0` and `DISABLE_MARIAN=0`; CORS for `horizonx.kathay.tech` and `frontend-six-phi-25.vercel.app` |

**Dockerfile behaviour:**
- Downloads all models at container start via `download_models.py`
- Sets `FORCE_OFFLINE=1` after download (fully offline inference via `TRANSFORMERS_OFFLINE=1`)
- Both NLLB and MarianMT enabled (`DISABLE_NLLB=0`, `DISABLE_MARIAN=0`)
- CORS configured for `horizonx.kathay.tech`, `frontend-six-phi-25.vercel.app`, and `localhost:3002`
- Runs on port 7860 (HF Spaces default)

**Notes:**
- Requires T4 GPU hardware on the Space — both model families need ~6GB+ combined VRAM/RAM
- Unlike `push_kathay_update.py`, this does NOT force-delete cached models — relies on `download_models.py` skipping already-cached files for faster restarts
- MarianMT models are loaded from `keithtwesigye/lunyoro-en2lun` and `keithtwesigye/lunyoro-lun2en`
- NLLB models are loaded from `kathay/lunyoro-nllb-en2lun` and `kathay/lunyoro-nllb-lun2en`

#### Force-push specific files (bypass dedup, trigger rebuild)
```bash
python backend/force_push_space.py
# Uses create_commit to force a new commit even when file content hasn't changed,
# guaranteeing the Space detects a change and triggers a Docker rebuild.
# Useful after hotfixes where push_to_hf_space.py would skip unchanged files.
#
# Files staged by default:
#   - translate.py
#   - main.py
#   - Dockerfile  (from hf-space/)
#
# Edit the files_to_force list at the top of the script to target different files.
# Requires HF_TOKEN to be set in the environment.
```

### Push Benchmark Files to GitHub
```bash
python push_benchmark_files.py
# Pushes backend/feedback/benchmark_scores.csv and benchmark_scores.json
# to both GitHub repos (chriskagenda/TRANSLATOR and K227-arch/TRANSLATOR).
# Reads GITHUB_TOKEN from backend/.env.
# Creates the file if it doesn't exist in the repo; updates it (with SHA) if it does.
# Run from the lunyoro-translator/ root directory.
```

### Vercel (Frontend)
```bash
cd frontend
vercel --prod
# Deployed to: frontend-six-phi-25.vercel.app
```

---

## Environment Variables

### Backend (.env)
```bash
HF_TOKEN=hf_...                    # HuggingFace API token (optional, for private models)
HF_USERNAME=keithtwesigye          # HuggingFace username for model repositories
HF_CHAT_MODEL=Qwen/Qwen2.5-7B-Instruct
CORS_ORIGINS=http://localhost:3002,http://localhost:3000,https://horizonx.kathay.tech,https://runyoro-rutooro-translator.vercel.app
FEEDBACK_FILE=feedback.jsonl       # Feedback storage path
AUTO_RETRAIN_THRESHOLD=100         # Min new pairs to trigger auto-retrain
GITHUB_TOKEN=ghp_...               # GitHub token for sync_feedback.py (required)
HF_KATHAY_TOKEN=hf_...             # HuggingFace read token for the kathay account — used by _nllb_translate_via_api when DISABLE_NLLB=1. Falls back to HF_TOKEN if unset
DISABLE_NLLB=1                     # Set to 1/true/yes to skip loading NLLB-200 locally — use on CPU-only deployments (e.g. HF Space cpu-basic) to avoid OOM errors. With float16 loading (default on CPU), each NLLB direction uses ~1.2GB RAM (down from 2.3GB). When set, NLLB inference is routed to the HF Inference API using kathay's fine-tuned repos (kathay/lunyoro-nllb-en2lun and kathay/lunyoro-nllb-lun2en) via HF_KATHAY_TOKEN (falls back to HF_TOKEN). Tries router.huggingface.co first (preferred inside HF Space infra), then api-inference.huggingface.co; MarianMT is the final fallback if both API calls fail or no token is set
DISABLE_MARIAN=0                   # Set to 1/true/yes to skip loading MarianMT models at startup — useful when running NLLB-only deployments or on memory-constrained environments where loading both model families would cause OOM. Translation falls back to NLLB (or retrieval/dictionary) when MarianMT is disabled
FORCE_OFFLINE=0                    # Set to 1/true/yes to force fully offline mode (sets TRANSFORMERS_OFFLINE=1, HF_DATASETS_OFFLINE=1, HF_HUB_OFFLINE=1). By default, HuggingFace Hub downloads are allowed so models can be fetched on first use and cached locally
```

### Frontend (.env.local)
```bash
NEXT_PUBLIC_API_URL=https://keithtwesigye-runyoro-translator-api.hf.space
```

---

## PWA & Service Worker Caching

The frontend is a Progressive Web App (PWA) powered by `next-pwa` / Workbox (`next.config.ts`). The service worker is **enabled in all environments** (including development) to support offline usage.

### Cache strategy by resource type

| URL pattern | Strategy | Cache name | TTL |
|---|---|---|---|
| `/_next/static/*` | CacheFirst | `next-static` | 30 days |
| `/_next/image?*` | CacheFirst | `next-images` | 7 days |
| `*/translate*` | StaleWhileRevalidate | `translation-api` | 30 days / 500 entries |
| `*/(dictionary\|spellcheck\|lookup)*` | StaleWhileRevalidate | `dictionary-api` | 30 days / 1 000 entries |
| All other `https://` requests | NetworkFirst | `runyoro-general` | 7 days / 200 entries, 5 s timeout |

**StaleWhileRevalidate** on the translation and dictionary endpoints means a cached response is returned immediately while a fresh response is fetched in the background — the app stays responsive even on slow or offline connections.

The `OfflineBanner` component provides visible feedback for connectivity state changes: a red banner when offline and a brief green banner on reconnection (auto-dismisses after 3 s). It is rendered at the app root so it overlays all pages.

**CacheFirst** on Next.js static assets is safe because those files carry content-hash filenames and never change after a build.

---

## Contributing

Contributions welcome! Priority areas:

1. **More training data** — native speaker corrections, domain-specific pairs
2. **Grammar rule refinements** — edge cases, dialect variations
3. **UI improvements** — mobile responsiveness, accessibility
4. **Model optimizations** — quantization, distillation, faster inference

---

## License

MIT License — see LICENSE file

---

## Citation

If you use this work, please cite:

```bibtex
@software{lunyoro_translator_2024,
  author = {Twesigye, Keith},
  title = {Lunyoro-Rutooro Neural Machine Translation System},
  year = {2024},
  url = {https://github.com/keithtwesigye/lunyoro-translator}
}
```

---

## Acknowledgments

- Runyoro-Rutooro Dictionary contributors
- Bible translation teams
- Grammar documentation authors
- HuggingFace for model hosting
- Vercel for frontend hosting

---

## Version History

### v2.9 - Grammar Rules 5: Adverbial Suffix, Objectival Concord, Negative Nouns, Class 9 Professional Nouns & Augmentatives (Current)
- **`translate.py`:** NLLB models are now loaded in float16 on CPU to halve memory usage (~2.3GB → ~1.2GB per direction). On GPU, float32 is used for maximum speed. This reduces OOM risk on memory-constrained deployments (e.g. HF Space cpu-basic) without requiring `DISABLE_NLLB=1`.
- **`main.py`:** NLLB model loading at startup is now wrapped in error handling — if an NLLB model fails to load (e.g. OOM on memory-constrained hardware), the server logs the error and continues startup with MarianMT and retrieval-based translation still available. Previously, an OOM during NLLB loading would crash the entire server.
- **`translate.py`:** Semantic search now guards against `_sem_model` being `None` — if the sentence-transformer model failed to load at startup, semantic search returns `None` immediately and the pipeline falls back to dictionary lookup, rather than raising an AttributeError. This mirrors the existing NLLB load-failure handling.
- **`main.py`:** Semantic retrieval index (`get_index_and_model()`) is loaded synchronously at startup, ensuring the retrieval-based translation is available immediately when the server starts accepting requests. This guarantees consistent translation quality from the first request onward.
- **`train_nllb.py`:** Added multi-GPU support via `torch.nn.DataParallel` — when more than one CUDA GPU is available, the NLLB model is automatically wrapped and training is distributed across all GPUs. Device names are printed at startup. Mirrors the existing multi-GPU behaviour in `train_marian.py`.
- **`language_rules_gr5.py`:** Implemented `apply_adverbial_suffix(verb, locative_prefix)` — appends the correct locative suffix (`-mu`, `-ho`, or `-yo`) to a verb based on its accompanying locative prefix (`omu-`/`omw-` → `-mu`, `ha-` → `-ho`, `owa-`/`omba`/`ku-` → `-yo`).
- **`language_rules_gr5.py`:** Implemented `apply_adverbial_suffix_correction(text)` — regex-based post-processing pass that corrects common MT errors where adverbial suffixes are missing (e.g. `genda owaitu` → `gendayo owaitu`, `ikara hansi` → `ikaraho hansi`, `ikara omunsi` → `ikaramu omunsi`).
- **`language_rules_gr5.py`:** Added `OBJECTIVAL_CONCORDS` — mapping of noun classes 1–15 to their objectival concord prefixes (e.g. class 3 → `gu`, class 7 → `ki`), used when the object is fronted in a reversed-object sentence.
- **`language_rules_gr5.py`:** Implemented `get_objectival_concord(noun_class)` — returns the objectival concord string for a given noun class.
- **`language_rules_gr5.py`:** Implemented `build_reversed_object_sentence(subject, subject_class, object_noun, object_class, verb_stem, tense_prefix)` — constructs a reversed-object sentence by combining the subject concord, objectival concord, verb stem, and perfect suffix (e.g. `build_reversed_object_sentence('omukazi', 1, 'omusiri', 3, 'lima', 'a')` → `'omusiri omukazi agulimire'`).
- **`language_rules_gr5.py`:** Added `NEGATIVE_NOUNS` dictionary and `build_negative_noun(verb_stem)` — derives Class 1 negative nouns using the `omu-ta-` prefix pattern (e.g. `build_negative_noun('seka')` → `'omutaseka'`, meaning "one who does not laugh").
- **`language_rules_gr5.py`:** Added `CLASS9_PROFESSIONAL_NOUNS` dictionary and `derive_class9_professional(verb_stem)` — derives Class 9 professional/habitual nouns using `en-` before consonants and `em-` before bilabials (e.g. `derive_class9_professional('lima')` → `'endima'`; `derive_class9_professional('baza')` → `'embaza'`).
- **`language_rules_gr5.py`:** Added `AUGMENTATIVE_EXAMPLES` dictionary and `build_augmentative(base_noun, aug_class)` — builds augmentative/pejorative forms by substituting the noun class prefix: class `'5'` (eri-/i-) for magnitude/pejorative (e.g. `'omusaija'` → `'isaija'`), class `'7'` (eki-) for magnitude/affection/contempt (e.g. `'omusaija'` → `'ekisaija'`). Strips common class 1/3/5/7 prefixes before applying the substitution.
- **`extract_gr5_training_pairs.py`:** New script that extracts ~300 clean English ↔ Runyoro-Rutooro training pairs from grammar rules 5.docx (Chapters 5–7). Covers locative agreement, locative demonstratives, genitive/possessive locatives, adverbial suffixes (-mu/-ho/-yo), ho + enumerative roots, dara + locative, copula ni- + locatives, reversed-object sentences, noun class examples (1a/2a/9a/10a), colour names, augmentative/pejorative forms, negative nouns, class 9 professional nouns, twin names, and kinship terms. Writes to `data/cleaned/gr5_pairs.csv` and merges into `train.csv`/`val.csv` (90/10 split, deduplication-safe).

### v2.8 - Qwen Refinement for `/translate-reverse`
- **`/translate-reverse` improvement:** Added optional `refine: bool` parameter (default `false`). When `true` and `HF_TOKEN` is set, a Qwen 2.5 7B pass refines the lun→en MT draft for fluency, accuracy, and natural English phrasing before the response is returned. Falls back silently to the MT draft if Qwen is unavailable. The refined output is also recorded in translation history with a `+refined` method suffix.

### v2.7 - Qwen Refinement for `/translate`
- **`/translate` improvement:** Added optional `refine: bool` parameter (default `false`). When `true` and `HF_TOKEN` is set, a Qwen 2.5 7B pass refines the MT draft — fixing noun-class prefixes, concordial agreement, R/L rule, apostrophe elision, and kinship terms — before the response is returned. Grammar Rules 4 post-processing is applied on top of the LLM output. Falls back silently to the MT draft if Qwen is unavailable.

### v2.6 - Particle Elision Correction Fix
- **`language_rules.py` bugfix:** `_MERGED_ELISION` patterns for `no/zo/yo/wo + vowel-initial word` now correctly preserve the leading vowel in the replacement (e.g. `nomuntu` → `n'omuntu` instead of the previous incorrect `n'muntu`). The patterns are now word-specific rather than a generic vowel-class match, preventing false positives. Fully-merged forms where the particle vowel is dropped entirely (e.g. `nente` → `n'ente`, `zomuntu` → `z'omuntu`) are handled by a separate set of patterns covering common Runyoro-Rutooro nouns.

### v2.5 - Dual-Model Qwen Refinement for Document Summarization
- **`/summarize-pdf` improvement:** Qwen 2.5 7B (via HuggingFace Router) now refines the MarianMT and NLLB-200 summary drafts **independently** when `HF_TOKEN` is set. Each model's draft is sent to Qwen separately with the English source and grammar rules as context. Grammar Rules 4 post-processing is applied to each refined output. The response now includes `summary_lunyoro` (best output — NLLB-refined preferred), `summary_lunyoro_marian` (Marian-refined), and `summary_lunyoro_nllb` (NLLB-refined). Falls back silently to the respective MT draft per model if Qwen is unavailable or times out.

### v2.4 - Grammar Pre-Processing for Document Summarization
- **`/summarize-pdf` improvement:** When a Lunyoro document is detected, grammar rules (nasal assimilation, particle elision, kinship correction, copula normalization) are now applied to each sentence before Lunyoro→English translation, improving summary quality for Runyoro-Rutooro input documents

### v2.4 - DocumentEditor Tab Simplification
- **Dictionary and History sub-tabs removed** from `DocumentEditor` — those pages are accessible as dedicated bottom-nav tabs and no longer duplicated inside the editor
- `DocumentEditor` now contains two sub-tabs only: **Write** (`RunyoroEditor`) and **PDF Translate** (`PdfTranslator`)
- Tab bar restyled: pill-style segmented control (`bg-surface-container` + `rounded-xl`) replaces the previous scrollable underline tabs; active tab gets a raised card (`bg-surface-container-lowest` + `premium-shadow`)
- Removed outer white card wrapper — `RunyoroEditor` and `PdfTranslator` render directly inside the layout

### v2.3 - Grammar Rules 4 Post-Processing
- **Grammar Rules 4** (`language_rules_gr4.py`) integrated as a final post-processing step in `translate.py` for en→lun output
- Covers copula constructions, kinship term agreement, enumerative patterns, and the *ka* diminutive/adverbial particle
- Applied after all existing rules (R/L, nasal assimilation, apostrophe elision) in the normalisation pipeline

### v2.2 - Document Editor Mobile Responsiveness
- **Document Editor toolbar removed** — the formatting toolbar (bold, italic, underline, lists, alignment, spellcheck, save) has been removed from `DocumentEditor.tsx`. Formatting controls remain available in the dedicated `RunyoroEditor.tsx` component.

### v2.1 - Rebranding & UI Refresh
- **App renamed** to "AI Stick — Runyoro / Rutooro Translator"
- **Theme color** updated to `#070235` (deep navy)
- **Typography:** Inter font (400/600/700/800) loaded via Google Fonts
- **Icons:** Material Symbols Outlined added via Google Fonts
- **PWA title** updated to "AI Stick"
- **Bottom navigation bar** (`BottomNav.tsx`) — fixed mobile nav with Home, Translate, Chat, and Editor tabs; active tab uses filled icon + secondary-container highlight
- **Chat UI redesign** — migrated to Material Design 3 tokens; input upgraded to multi-line textarea with mic button; language switcher (English / Runyoro-Rutooro) added at top; sector list consolidated to 8 domains

### v2.0 - Enhanced Feedback & Model Comparison
- **Enhanced feedback system:** Multi-select error categorization (grammar, spelling, context, vocabulary, other)
- **Model comparison interface:** 2x2 grid to choose between MarianMT, NLLB-200, both correct, or both wrong; visible only when both models produce output
- **Model preference learning:** Selected model becomes primary for future translations
- **Separate feedback flows:** Independent tracking for quality feedback and model comparison
- **Improved UX:** Immediate translation updates when model preference is selected

### v1.0 - Initial Release
- Dual neural models (MarianMT + NLLB-200)
- Semantic search fallback
- Grammar rule post-processing
- Basic feedback system
- Chat assistant integration
