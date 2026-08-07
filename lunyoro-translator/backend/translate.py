"""
Translation logic:
  Primary  — fine-tuned NLLB-200 models (nllb_en2lun / nllb_lun2en) trained locally
  Secondary — fine-tuned MarianMT models (en2lun / lun2en) as fallback
  Fallback — semantic similarity retrieval + dictionary lookup
"""

import os
import pickle
import re
import unicodedata
import numpy as np
from sentence_transformers import SentenceTransformer, util
from rapidfuzz import fuzz, process

INDEX_PATH = os.path.join(os.path.dirname(__file__), "model", "translation_index.pkl")
MODEL_DIR = os.path.join(os.path.dirname(__file__), "model")
SEM_MODEL_DIR = os.path.join(MODEL_DIR, "sem_model")

# HuggingFace model repositories
HF_USERNAME = os.getenv("HF_USERNAME", "keithtwesigye")
HF_MODELS = {
    "en2lun": f"{HF_USERNAME}/lunyoro-en2lun",
    "lun2en": f"{HF_USERNAME}/lunyoro-lun2en",
    "nllb_en2lun": f"{HF_USERNAME}/lunyoro-nllb-en2lun",
    "nllb_lun2en": f"{HF_USERNAME}/lunyoro-nllb-lun2en",
    "sem_model": f"{HF_USERNAME}/lunyoro-sentence-embeddings",
}

# Allow HuggingFace downloads (models are cached locally after first download)
# Remove offline mode to enable model downloads from HF Hub
if "TRANSFORMERS_OFFLINE" in os.environ:
    del os.environ["TRANSFORMERS_OFFLINE"]
if "HF_DATASETS_OFFLINE" in os.environ:
    del os.environ["HF_DATASETS_OFFLINE"]
if "HF_HUB_OFFLINE" in os.environ:
    del os.environ["HF_HUB_OFFLINE"]

_APOSTROPHE_MAP = str.maketrans(
    {
        "\u2018": "'",
        "\u2019": "'",
        "\u201c": '"',
        "\u201d": '"',
        "\u02bc": "'",
        "\u0060": "'",
    }
)


def _normalise(text: str) -> str:
    """NFC normalise + apostrophe standardisation for consistent matching."""
    text = unicodedata.normalize("NFC", text)
    return text.translate(_APOSTROPHE_MAP)


# ── Language rule integration ─────────────────────────────────────────────────
# Lazy-import so the module loads even if language_rules has a syntax error.
_rules_loaded = False
_apply_rl = None
_apply_nasal = None
_apply_ni = None
_apply_apostrophe = None
_apply_semi_vowel = None
_apply_cons_suffix = None
_apply_reflexive = None
_apply_init_vowel = None

# ── Grammar Pipeline / Rule Engine (optional enhancements) ──
# These provide rule orchestration, statistics, and selective application
# Usage: from language_rules import GrammarPipeline, RuleEngine
#        pipeline = GrammarPipeline(strictness="high")
#        result = pipeline.fix(text)


def _load_rules():
    global \
        _rules_loaded, \
        _apply_rl, \
        _apply_nasal, \
        _apply_ni, \
        _apply_apostrophe, \
        _apply_semi_vowel, \
        _apply_cons_suffix, \
        _apply_reflexive, \
        _apply_init_vowel
    if _rules_loaded:
        return
    try:
        from language_rules import (
            apply_rl_rule_to_text,
            apply_nasal_assimilation,
            apply_ni_prefix_change,
            apply_apostrophe_elision,
            apply_particle_elision,
            apply_semi_vowel_substitution,
            apply_consonant_suffix_mutations,
            apply_reflexive_imperative_correction,
            apply_initial_vowel_rule,
        )

        _apply_rl = apply_rl_rule_to_text
        _apply_nasal = apply_nasal_assimilation
        _apply_ni = apply_ni_prefix_change
        _apply_apostrophe = apply_particle_elision
        _apply_semi_vowel = apply_semi_vowel_substitution
        _apply_cons_suffix = apply_consonant_suffix_mutations
        _apply_reflexive = apply_reflexive_imperative_correction
        _apply_init_vowel = apply_initial_vowel_rule
    except Exception as e:
        print(f"[translate] language_rules not available: {e}")
    _rules_loaded = True
    # Optional: Load GrammarPipeline for statistics-enabled processing
    # try:
    #     from language_rules import GrammarPipeline
    #     _grammar_pipeline = GrammarPipeline(strictness="high")
    # except Exception:
    #     _grammar_pipeline = None


def _postprocess_lunyoro(text: str) -> str:
    """
    Apply Runyoro-Rutooro orthographic rules to en→lun MT output.

    Order matters:
      1. Nasal assimilation       (nb→mb, np→mp, nr→nd, nl→nd)
      2. ni→nu prefix change      (nimugenda→numugenda before u-class concords)
      3. Consonant+suffix changes (r/t/j/nd/nt + -ire/-i/-ya mutations)
      4. Reflexive imperative fix (okwesereka → weesereke)
      5. Initial vowel rule       (prefix-based initial vowel correction)
      6. Semi-vowel substitution  (i→y, u→w at prefix boundaries)
      7. Particle elision         (na ente→n'ente, habwa okugonza→habw'okugonza)
      8. R/L rule                 (L→R except adjacent to e/i)
      9. Grammar Rules 4          (copula, kinship, enumeratives, ka particle)
    """
    if not text:
        return text
    _load_rules()
    if _apply_nasal:
        text = _apply_nasal(text)
    if _apply_ni:
        text = _apply_ni(text)
    if _apply_cons_suffix:
        text = _apply_cons_suffix(text)
    if _apply_reflexive:
        text = _apply_reflexive(text)
    if _apply_init_vowel:
        text = _apply_init_vowel(text)
    if _apply_semi_vowel:
        text = _apply_semi_vowel(text)
    if _apply_apostrophe:
        text = _apply_apostrophe(text)
    if _apply_rl:
        text = _apply_rl(text)
    # Grammar Rules 4 corrections
    try:
        from language_rules_gr4 import apply_gr4_rules

        text = apply_gr4_rules(text, direction="en->lun")
    except Exception:
        pass
    # Grammar Rules 5 corrections
    try:
        from language_rules_gr5 import apply_gr5_rules

        text = apply_gr5_rules(text, direction="en->lun")
    except Exception:
        pass
    # Dialect normalisation: Rutooro → Runyoro standard forms
    text = _normalise_dialect(text)
    return text


# Rutooro → Runyoro dialect mappings (case-insensitive word substitutions)
_DIALECT_MAP = [
    # Days of the week
    (r"\bkiro\s+kinu\b", "leero"),  # today
    (r"\bkiro\s+ekindi\b", "leero"),
    (r"\bkyakabizi\b", "n'Orwokasatu"),  # Tuesday
    (r"\bkya\s+kabizi\b", "n'Orwokasatu"),
    (r"\bkya\s+kasatu\b", "n'Orwokasatu"),
    (r"\bkya\s+kana\b", "n'Orwokana"),  # Thursday
    (r"\bkya\s+kataano\b", "n'Orwokataano"),  # Friday
    (r"\bkya\s+mukaaga\b", "n'Orwomukaaga"),  # Saturday
    (r"\bkya\s+sande\b", "n'Orwosande"),  # Sunday
    (r"\bkya\s+banza\b", "n'Orwobanza"),  # Monday
    # Common Rutooro→Runyoro word swaps
    (r"\bkiro\b", "leero"),  # today (standalone)
    (r"\bkinu\s+kizi\b", "kinu"),  # this (demonstrative cleanup)
]


def _normalise_dialect(text: str) -> str:
    """Normalise Rutooro dialect forms to standard Runyoro forms."""
    import re

    result = text
    for pattern, replacement in _DIALECT_MAP:
        result = re.sub(pattern, replacement, result, flags=re.IGNORECASE)
    return result


def _preprocess_lunyoro_input(text: str) -> str:
    """
    Normalise lun→en input before feeding to the model.
    - Nasal assimilation (canonical consonant clusters)
    - Apostrophe elision expansion (n'ente → na ente)
    - Dialect variant normalisation (kiro → leero, etc.)
    Does NOT apply R/L rule on input — the model was trained on real text.
    """
    if not text:
        return text
    _load_rules()
    # 1. Nasal assimilation
    if _apply_nasal:
        text = _apply_nasal(text)
    # 2. Expand apostrophe elisions so model sees canonical forms
    # e.g. n'ente → na ente, habw'okugonza → habwa okugonza
    import re as _re_pre
    text = _re_pre.sub(r"\bn'([aeiouAEIOU])", r"na \1", text)
    text = _re_pre.sub(r"\bw'([aeiouAEIOU])", r"wa \1", text)
    text = _re_pre.sub(r"\by'([aeiouAEIOU])", r"ya \1", text)
    text = _re_pre.sub(r"\bk'([aeiouAEIOU])", r"ka \1", text)
    # 3. Common spelling variants → canonical forms
    _VARIANT_MAP = [
        (r"\bkiro\b", "leero"),       # today (Rutooro → Runyoro)
        (r"\beky([aeiou])", r"eki\1"),  # eky- → eki- prefix variant
        (r"\boky([aeiou])", r"oki\1"),  # oky- prefix
        (r"\baky([aeiou])", r"aki\1"),  # aky- prefix
    ]
    for pat, rep in _VARIANT_MAP:
        text = _re_pre.sub(pat, rep, text, flags=_re_pre.IGNORECASE)
    return text


# ── cached singletons ────────────────────────────────────────────────────────
_index = None
_sem_model = None
_dictionary = None
_corpus_vocab = None
_dict_word_map: dict = {}  # lowercase word → entry, for O(1) lookup

_mt_models = {}  # {"en2lun": (tokenizer, model), "lun2en": (tokenizer, model)}
_mt_available = {}  # {"en2lun": bool, "lun2en": bool}
_mt_onnx = {}  # {"en2lun": bool, "lun2en": bool} — True if using ONNX
_nllb_models = {}  # {"en2lun": (tokenizer, model, device), "lun2en": ...}
_nllb_available = {}  # {"en2lun": bool, "lun2en": bool}
_nllb_whitelist: list | None = None  # token ID whitelist loaded once

NLLB_LANG_EN = "eng_Latn"
NLLB_LANG_LUN = "run_Latn"  # Rundi — proxy Bantu language for Runyoro-Rutooro


def _load_nllb_whitelist() -> list | None:
    """Load the Lunyoro token whitelist, build it if missing."""
    global _nllb_whitelist
    if _nllb_whitelist is not None:
        return _nllb_whitelist
    whitelist_path = os.path.join(MODEL_DIR, "lunyoro_token_whitelist.json")
    if os.path.exists(whitelist_path):
        import json

        with open(whitelist_path) as f:
            _nllb_whitelist = json.load(f)
        print(
            f"[translate] Loaded token whitelist: {len(_nllb_whitelist):,} allowed tokens"
        )
    else:
        print(
            "[translate] Token whitelist not found — run build_lunyoro_vocab.py to generate it"
        )
        _nllb_whitelist = []
    return _nllb_whitelist


# ── loaders ──────────────────────────────────────────────────────────────────


def _load_retrieval():
    global _index, _sem_model, _dictionary, _corpus_vocab, _dict_word_map
    if _index is not None:
        return
    if not os.path.exists(INDEX_PATH):
        raise FileNotFoundError("Translation index not found. Run train.py first.")
    with open(INDEX_PATH, "rb") as f:
        _index = pickle.load(f)
    sem_path = _index["model_name"]

    # Prefer local sem_model dir (always present when downloaded by download_models.py)
    # But verify tokenizer.json is valid (not an LFS pointer)
    local_sem_ok = False
    if os.path.isdir(SEM_MODEL_DIR) and any(
        f.endswith((".json", ".safetensors", ".bin", ".pt"))
        for f in os.listdir(SEM_MODEL_DIR)
    ):
        # Check that tokenizer.json is actually valid JSON (not an LFS pointer)
        tok_path = os.path.join(SEM_MODEL_DIR, "tokenizer.json")
        if os.path.exists(tok_path):
            try:
                import json
                with open(tok_path, "r") as tf:
                    first_char = tf.read(1)
                    if first_char in ("{", "["):
                        local_sem_ok = True
                    else:
                        print(f"[translate] tokenizer.json appears to be an LFS pointer, skipping local")
            except Exception:
                pass
        else:
            local_sem_ok = True  # no tokenizer.json but other files exist

    if local_sem_ok:
        sem_path = SEM_MODEL_DIR
        print(f"[translate] Loading sem_model from local path: {SEM_MODEL_DIR}")
    else:
        # Fall back to HuggingFace Hub
        hf_sem = HF_MODELS.get("sem_model", "keithtwesigye/lunyoro-sentence-embeddings")
        sem_path = hf_sem
        print(f"[translate] Loading sem_model from HF Hub: {sem_path}")

    _sem_model = SentenceTransformer(sem_path)
    _dictionary = _index["dictionary"]
    # build O(1) lookup map
    _dict_word_map = {d["word"].lower(): d for d in _dictionary}
    # also map by lowercased definitionEnglish for en→lun searches
    _dict_def_map: dict = {}
    for d in _dictionary:
        key = (d.get("definitionEnglish") or "").lower()
        if key:
            _dict_def_map[key] = d
    _index["_dict_def_map"] = _dict_def_map


def _load_mt(direction: str):
    """Lazy-load a fine-tuned MarianMT model. Prefers ONNX if available."""
    if direction in _mt_available:
        return _mt_available[direction]

    # Respect DISABLE_MARIAN flag — used on NLLB-only deployments
    if os.getenv("DISABLE_MARIAN", "0").strip() in ("1", "true", "yes"):
        _mt_available[direction] = False
        return False

    path = os.path.join(MODEL_DIR, direction)
    onnx_path = os.path.join(MODEL_DIR, f"{direction}_onnx")

    # ── Try ONNX first (faster inference) ────────────────────────────────────
    if os.path.isdir(onnx_path) and any(
        f.endswith(".onnx") for f in os.listdir(onnx_path)
    ):
        try:
            from optimum.onnxruntime import ORTModelForSeq2SeqLM
            from transformers import MarianTokenizer
            import torch

            print(f"[translate] Loading ONNX model: {direction}")
            tokenizer = MarianTokenizer.from_pretrained(onnx_path)

            # Determine available ONNX providers — prefer CPU (no onnxruntime-gpu needed)
            import onnxruntime as _ort

            available_providers = _ort.get_available_providers()
            if "CUDAExecutionProvider" in available_providers:
                provider = "CUDAExecutionProvider"
            else:
                provider = "CPUExecutionProvider"

            # Newer optimum expects decoder_model_merged.onnx; fall back to
            # decoder_model.onnx (which is what our export_to_onnx.py produced).
            onnx_files = os.listdir(onnx_path)
            if "decoder_model_merged.onnx" in onnx_files:
                decoder_file = "decoder_model_merged.onnx"
            elif "decoder_model.onnx" in onnx_files:
                decoder_file = "decoder_model.onnx"
            else:
                raise FileNotFoundError(f"No decoder ONNX file found in {onnx_path}")

            model = ORTModelForSeq2SeqLM.from_pretrained(
                onnx_path,
                provider=provider,
                decoder_file_name=decoder_file,
                use_cache=False,  # use_cache=True requires decoder_with_past model
            )
            device = "cuda" if "CUDA" in provider else "cpu"
            _mt_models[direction] = (tokenizer, model, device)
            _mt_available[direction] = True
            _mt_onnx[direction] = True
            print(f"[translate] Loaded ONNX model: {direction} on {provider}")
            return True
        except Exception as e:
            print(f"[translate] ONNX load failed ({e}), falling back to PyTorch")

    # ── PyTorch fallback ──────────────────────────────────────────────────────
    # Auto-download from HuggingFace if not present locally
    if not os.path.isdir(path) or not any(
        f.endswith((".safetensors", ".bin"))
        for f in os.listdir(path)
        if os.path.isdir(path)
    ):
        hf_repos = {
            "en2lun": "keithtwesigye/lunyoro-en2lun",
            "lun2en": "keithtwesigye/lunyoro-lun2en",
        }
        repo_id = hf_repos.get(direction)
        if repo_id:
            try:
                print(f"[translate] Downloading {repo_id} from HuggingFace...")
                from huggingface_hub import snapshot_download

                snapshot_download(
                    repo_id=repo_id,
                    local_dir=path,
                    ignore_patterns=["*.msgpack", "flax_model*", "tf_model*"],
                )
                print(f"[translate] Downloaded {direction} model.")
            except Exception as e:
                print(
                    f"[translate] Could not download {direction} from HuggingFace: {e}"
                )
                _mt_available[direction] = False
                return False

    try:
        from transformers import MarianMTModel, MarianTokenizer
        import torch

        tokenizer = MarianTokenizer.from_pretrained(path)
        model = MarianMTModel.from_pretrained(path)
        model.eval()
        device = "cuda" if torch.cuda.is_available() else "cpu"
        model.to(device)
        _mt_models[direction] = (tokenizer, model, device)
        _mt_available[direction] = True
        _mt_onnx[direction] = False
        print(f"[translate] Loaded PyTorch model: {direction}")
        return True
    except Exception as e:
        print(f"[translate] Could not load {direction} model: {e}")
        _mt_available[direction] = False
        return False


def _mt_translate(text: str, direction: str, context: str = "") -> str | None:
    """Run inference with a fine-tuned MarianMT model."""
    if not _load_mt(direction):
        return None
    import torch

    tokenizer, model, device = _mt_models[direction]

    # Pre-process lun→en input: normalise nasal clusters
    if direction == "lun2en":
        text = _preprocess_lunyoro_input(text)

    input_text = f"{context} ||| {text}" if context else text
    inputs = tokenizer(
        input_text, return_tensors="pt", truncation=True, max_length=256
    )
    # ONNX models (ORTModelForSeq2SeqLM) handle device internally — don't call .to()
    if not _mt_onnx.get(direction, False):
        inputs = inputs.to(device)
    with torch.no_grad():
        output_ids = model.generate(
            **inputs,
            num_beams=8,
            max_length=512,
            early_stopping=True,
            no_repeat_ngram_size=3,
            repetition_penalty=1.3,
            length_penalty=1.2,
        )
    result = tokenizer.decode(output_ids[0], skip_special_tokens=True)

    # Strip any domain tags the model may have reproduced from training data
    import re as _re2

    result = _re2.sub(r"^\s*\[[A-Za-z _]+\]\s*", "", result).strip()

    # Strip source-copy artifact: model sometimes appends the English source
    if text and len(text) > 8 and direction == "en2lun":
        src_lower = text.lower().strip()
        out_lower = result.lower()
        idx = out_lower.find(src_lower[:20])
        if idx > 5:
            result = result[:idx].strip().rstrip("?.,;: ")
        # Also strip trailing English sentences
        result = _re2.sub(r"\s+[A-Z][a-z]+(?:\s+[a-z]+){3,}\??\s*$", "", result).strip()

    # Post-process en→lun output: apply orthographic rules
    if direction == "en2lun" and result:
        result = _postprocess_lunyoro(result)

    # Detect degenerate/hallucinated output (repetitive tokens like "Bi Bi Bi...")
    if result:
        import re as _re_deg
        words = result.split()
        if len(words) >= 5:
            # Check if any single token makes up >40% of the output
            from collections import Counter as _Counter
            freq = _Counter(w.lower() for w in words)
            most_common_word, most_common_count = freq.most_common(1)[0]
            if most_common_count / len(words) > 0.4:
                return None  # garbage — too repetitive
            # Check for repeated bigrams (e.g. "Bi Bi Bi Bi")
            bigrams = [f"{words[i]} {words[i+1]}" for i in range(len(words)-1)]
            if bigrams:
                bg_freq = _Counter(bigrams)
                top_bg, top_bg_count = bg_freq.most_common(1)[0]
                if top_bg_count / len(bigrams) > 0.35:
                    return None  # garbage — repeated bigrams

    return result


def _load_nllb(direction: str) -> bool:
    """Lazy-load a fine-tuned NLLB model.
    On HF Space cpu-basic: downloads to HF Hub cache (/root/.cache), not /app/model.
    This bypasses the 1GB Space repo storage limit — HF Hub cache is unlimited."""
    if direction in _nllb_available:
        return _nllb_available[direction]

    # Hard disable flag — only use when RAM is critically low
    if os.getenv("DISABLE_NLLB", "0").strip() in ("1", "true", "yes"):
        print(f"[translate] NLLB disabled via DISABLE_NLLB env flag — skipping {direction}")
        _nllb_available[direction] = False
        return False

    # Prefer the freshly trained model dir (nllb_en2lun / nllb_lun2en).
    # Fall back to the legacy _pre_nyo checkpoint if the primary doesn't exist.
    path_primary = os.path.join(MODEL_DIR, f"nllb_{direction}")
    path_legacy  = os.path.join(MODEL_DIR, f"nllb_{direction}_pre_nyo")

    def _dir_has_weights(p: str) -> bool:
        return os.path.isdir(p) and any(
            f.endswith((".safetensors", ".bin"))
            for f in os.listdir(p)
            if os.path.isfile(os.path.join(p, f))
        )

    if _dir_has_weights(path_primary):
        path = path_primary
        print(f"[translate] Using trained NLLB model: {path_primary}")
    elif _dir_has_weights(path_legacy):
        path = path_legacy
        print(f"[translate] Falling back to legacy NLLB model: {path_legacy}")
    else:
        path = path_primary  # will trigger HF download below

    # ── Try ONNX INT8 first (fastest), then ONNX FP32, then PyTorch ────────────
    int8_path = os.path.join(MODEL_DIR, f"nllb_{direction}_int8")
    onnx_path = os.path.join(MODEL_DIR, f"nllb_{direction}_onnx")

    def _dir_has_onnx(p: str) -> bool:
        return os.path.isdir(p) and any(
            f.endswith(".onnx") for f in os.listdir(p)
            if os.path.isfile(os.path.join(p, f))
        )

    def _try_load_onnx(load_path: str, label: str) -> bool:
        """Attempt to load an ONNX model from load_path. Returns True on success."""
        try:
            from optimum.onnxruntime import ORTModelForSeq2SeqLM
            from transformers import AutoTokenizer
            import onnxruntime as _ort

            print(f"[translate] Loading NLLB {label}: {direction} from {load_path}")
            # Suppress the spurious Mistral regex warning — only relevant for Mistral models
            import warnings as _warn
            with _warn.catch_warnings():
                _warn.simplefilter("ignore")
                tokenizer = AutoTokenizer.from_pretrained(load_path)
            providers = _ort.get_available_providers()
            provider = "CUDAExecutionProvider" if "CUDAExecutionProvider" in providers else "CPUExecutionProvider"
            # ONNX models run on CPU via ORT — device label is "cpu" regardless of provider
            device = "cpu"

            onnx_files = os.listdir(load_path)
            if "decoder_model_merged.onnx" in onnx_files:
                decoder_file = "decoder_model_merged.onnx"
                use_cache = True
            elif "decoder_model.onnx" in onnx_files:
                decoder_file = "decoder_model.onnx"
                use_cache = False
            else:
                raise FileNotFoundError(f"No decoder ONNX file in {load_path}")

            model = ORTModelForSeq2SeqLM.from_pretrained(
                load_path,
                provider=provider,
                decoder_file_name=decoder_file,
                use_cache=use_cache,
            )
            _nllb_models[direction] = (tokenizer, model, device)
            _nllb_available[direction] = True
            print(f"[translate] Loaded NLLB {label}: {direction} on {provider}")
            return True
        except Exception as e:
            print(f"[translate] NLLB {label} load failed ({e}), trying next option")
            return False

    # Priority: INT8 > FP32 ONNX > PyTorch
    if _dir_has_onnx(int8_path) and _try_load_onnx(int8_path, "ONNX INT8"):
        return True
    if _dir_has_onnx(onnx_path) and _try_load_onnx(onnx_path, "ONNX FP32"):
        return True

    # On HF Space cpu-basic: /app/model has 1GB limit so NLLB can't be stored there.
    # Instead, stream from HF Hub cache (/root/.cache/huggingface) which is unlimited.
    # Detect Space environment: no GPU + /app exists but model path is missing/tiny.
    import torch as _torch_check
    is_cpu_only = not _torch_check.cuda.is_available()
    local_model_ok = _dir_has_weights(path)

    if not local_model_ok:
        hf_repos = {
            "en2lun": "keithtwesigye/lunyoro-nllb-en2lun",
            "lun2en": "keithtwesigye/lunyoro-nllb-lun2en",
        }
        repo_id = hf_repos.get(direction)
        if repo_id:
            try:
                from huggingface_hub import snapshot_download
                if is_cpu_only:
                    # On cpu-basic: use HF Hub cache (don't write to /app/model)
                    print(f"[translate] CPU-only: caching {repo_id} to HF Hub cache...")
                    local_path = snapshot_download(
                        repo_id=repo_id,
                        ignore_patterns=["*.msgpack", "flax_model*", "tf_model*"],
                    )
                    path = local_path
                    print(f"[translate] Cached NLLB {direction} at {path}")
                else:
                    # GPU machine: download to /app/model as before
                    print(f"[translate] Downloading {repo_id} -> {path}")
                    os.makedirs(path, exist_ok=True)
                    snapshot_download(
                        repo_id=repo_id,
                        local_dir=path,
                        ignore_patterns=["*.msgpack", "flax_model*", "tf_model*"],
                    )
                    print(f"[translate] Downloaded nllb_{direction} model.")
            except Exception as e:
                print(f"[translate] Could not download nllb_{direction}: {e}")
                _nllb_available[direction] = False
                return False

    try:
        from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
        import torch

        import warnings as _warn
        with _warn.catch_warnings():
            _warn.simplefilter("ignore")
            tokenizer = AutoTokenizer.from_pretrained(path, fix_mistral_regex=True)
        # Load in float16 on CPU to halve memory usage (2.3GB → ~1.2GB)
        # On GPU, float16 is natively fast; on CPU it's slower but avoids OOM
        import torch
        load_dtype = torch.float16 if not torch.cuda.is_available() else torch.float32
        model = AutoModelForSeq2SeqLM.from_pretrained(path, torch_dtype=load_dtype)
        model.eval()
        if torch.cuda.device_count() >= 2:
            device = "cuda:1"
        elif torch.cuda.is_available():
            device = "cuda:0"
        else:
            device = "cpu"
        model.to(device)
        _nllb_models[direction] = (tokenizer, model, device)
        _nllb_available[direction] = True
        print(f"[translate] Loaded NLLB model: {direction} on {device}")
        return True
    except Exception as e:
        print(f"[translate] Could not load NLLB {direction}: {e}")
        _nllb_available[direction] = False
        return False


def _nllb_translate_via_api(text: str, direction: str) -> str | None:
    """
    Call HF Inference API using kathay's NLLB model repos.
    Used when DISABLE_NLLB=1 (cpu-basic Space) — zero local RAM needed.
    Tries router.huggingface.co first (works inside HF infra), then
    api-inference.huggingface.co as fallback.
    Falls back silently on any error.
    """
    import requests as _req
    import re as _re

    # Use kathay read token for kathay's model repos; fall back to main HF_TOKEN
    hf_token = os.getenv("HF_KATHAY_TOKEN", os.getenv("HF_TOKEN", ""))
    if not hf_token:
        return None

    # NLLB model repos on HuggingFace
    hf_repos = {
        "en2lun": "keithtwesigye/lunyoro-nllb-en2lun",
        "lun2en": "keithtwesigye/lunyoro-nllb-lun2en",
    }
    repo_id = hf_repos.get(direction)
    if not repo_id:
        return None

    # Pre-process lun→en input
    if direction == "lun2en":
        text = _preprocess_lunyoro_input(text)

    src_lang = NLLB_LANG_EN if direction == "en2lun" else NLLB_LANG_LUN
    tgt_lang = NLLB_LANG_LUN if direction == "en2lun" else NLLB_LANG_EN

    payload = {
        "inputs": text,
        "parameters": {
            "src_lang": src_lang,
            "tgt_lang": tgt_lang,
            "num_beams": 6,
            "max_length": 512,
            "no_repeat_ngram_size": 3,
        },
    }
    auth_headers = {
        "Authorization": f"Bearer {hf_token}",
        "Content-Type": "application/json",
    }

    # Try both endpoints — router.huggingface.co works inside HF Space infra
    endpoints = [
        f"https://router.huggingface.co/hf-inference/models/{repo_id}",
        f"https://api-inference.huggingface.co/models/{repo_id}",
    ]

    for url in endpoints:
        try:
            resp = _req.post(url, headers=auth_headers, json=payload, timeout=35)
            if resp.status_code == 503:
                # Model cold-starting — wait and retry once
                import time as _t

                print(
                    f"[translate] NLLB API model loading ({url[:50]}...), retrying in 20s"
                )
                _t.sleep(20)
                resp = _req.post(url, headers=auth_headers, json=payload, timeout=45)
            if resp.status_code == 200:
                data = resp.json()
                if isinstance(data, list) and data:
                    result = data[0].get("translation_text", "")
                elif isinstance(data, dict):
                    result = data.get("translation_text", "")
                else:
                    continue
                if not result or not result.strip():
                    continue
                # Clean lang-code prefix artifacts
                result = _re.sub(
                    r"^\s*(?:\[[A-Za-z _]+\]|[A-Za-z]+_[A-Za-z]+)\s*", "", result
                ).strip()
                if _is_notation_garbage(result):
                    continue
                # Passthrough check
                _src_n = _re.sub(r"\s+", " ", text.strip().lower())
                _out_n = _re.sub(r"\s+", " ", result.strip().lower())
                if _out_n == _src_n:
                    continue
                # English passthrough check for en→lun
                if direction == "en2lun" and result:
                    common_en = {
                        "the",
                        "a",
                        "an",
                        "is",
                        "are",
                        "was",
                        "were",
                        "be",
                        "been",
                        "have",
                        "has",
                        "had",
                        "do",
                        "does",
                        "did",
                        "will",
                        "would",
                        "could",
                        "should",
                        "to",
                        "of",
                        "in",
                        "on",
                        "at",
                        "for",
                        "with",
                        "and",
                        "or",
                        "but",
                        "not",
                        "this",
                        "that",
                        "it",
                        "he",
                        "she",
                        "they",
                        "we",
                        "you",
                        "i",
                        "my",
                        "your",
                        "his",
                        "her",
                        "their",
                        "its",
                        "our",
                    }
                    words = _re.findall(r"[a-z]+", result.lower())
                    if (
                        words
                        and sum(1 for w in words if w in common_en) / len(words) > 0.5
                    ):
                        continue
                    result = _postprocess_lunyoro(result)
                print(
                    f"[translate] NLLB API ({direction}) via {url[:40]}: {result[:60]}"
                )
                return result
            else:
                print(
                    f"[translate] NLLB API {resp.status_code} from {url[:50]}: {resp.text[:100]}"
                )
        except Exception as e:
            print(f"[translate] NLLB API failed ({url[:40]}): {e}")
            continue

    return None


def _nllb_translate(text: str, direction: str, context: str = "") -> str | None:
    """Run inference with a fine-tuned NLLB model.
    Falls back to HF Inference API when local model is unavailable."""
    # ── Remote API path (explicitly requested or local model unavailable) ────
    if os.getenv("DISABLE_NLLB", "").strip() in ("1", "true", "yes"):
        return _nllb_translate_via_api(text, direction)

    # ── Local inference path ─────────────────────────────────────────────────
    if not _load_nllb(direction):
        return _nllb_translate_via_api(text, direction)
    import torch

    tokenizer, model, device = _nllb_models[direction]

    # Pre-process lun→en input: normalise nasal clusters
    if direction == "lun2en":
        text = _preprocess_lunyoro_input(text)

    src_lang = NLLB_LANG_EN if direction == "en2lun" else NLLB_LANG_LUN
    tgt_lang = NLLB_LANG_LUN if direction == "en2lun" else NLLB_LANG_EN
    tokenizer.src_lang = src_lang
    input_text = f"{context} ||| {text}" if context else text
    inputs = tokenizer(
        input_text, return_tensors="pt", truncation=True, max_length=256
    )
    # ONNX models expect CPU tensors — only move to device for PyTorch models
    from optimum.onnxruntime import ORTModelForSeq2SeqLM as _ORT_cls
    if not isinstance(model, _ORT_cls):
        inputs = inputs.to(device)

    generate_kwargs: dict = dict(
        num_beams=8,
        max_length=512,
        early_stopping=True,
        no_repeat_ngram_size=3,
        repetition_penalty=1.3,
        length_penalty=1.2,
    )
    generate_kwargs["forced_bos_token_id"] = tokenizer.convert_tokens_to_ids(tgt_lang)

    # Whitelist disabled — it suppresses valid Bantu tokens and hurts quality
    # if direction == "en2lun":
    #     whitelist = _load_nllb_whitelist()
    #     if whitelist:
    #         vocab_size = getattr(getattr(model, "module", model).config, "vocab_size", 256204)
    #         allowed_set = set(whitelist)
    #         suppress = [i for i in range(vocab_size) if i not in allowed_set]
    #         if suppress:
    #             generate_kwargs["suppress_tokens"] = suppress

    with torch.no_grad():
        output_ids = model.generate(**inputs, **generate_kwargs)
    nllb_result = tokenizer.decode(output_ids[0], skip_special_tokens=True)

    # Clean SentencePiece/NLLB decode artifacts immediately after decode
    # 1. Strip ▁ (U+2581) SentencePiece boundary markers that sometimes leak through
    nllb_result = nllb_result.replace("\u2581", " ").strip()
    # 2. Collapse multiple spaces left by ▁ stripping
    nllb_result = re.sub(r"  +", " ", nllb_result)
    # 3. Fix L→I: NLLB run_Latn proxy confuses capital I with L in lun→en output
    if direction == "lun2en":
        nllb_result = re.sub(r"(?<![A-Za-z])L(?![A-Za-z])", "I", nllb_result)

    if _is_notation_garbage(nllb_result):
        return None

    # Detect passthrough: NLLB returned the source text unchanged (common failure
    # mode for short phrases with low-resource language codes like run_Latn).
    # Normalise both sides before comparing to catch case/whitespace differences.
    import re as _re2

    _src_norm = _re2.sub(r"\s+", " ", text.strip().lower())
    _out_norm = _re2.sub(r"\s+", " ", nllb_result.strip().lower())
    if _out_norm == _src_norm:
        return None  # fall back to MarianMT
    nllb_result = _re2.sub(
        r"^\s*(?:\[[A-Za-z _]+\]|[A-Za-z]+_[A-Za-z]+)\s*", "", nllb_result
    ).strip()

    # Strip source-copy artifact: NLLB sometimes appends the English source
    # after the Lunyoro translation, e.g. "Bantu baingaha leero? How many people..."
    # Detect by finding the original English text appearing in the output
    if text and len(text) > 8:
        # Check if the source text (or a close variant) appears in the output
        src_lower = text.lower().strip()
        out_lower = nllb_result.lower()
        idx = out_lower.find(src_lower[:20])  # match on first 20 chars of source
        if idx > 5:  # found source text after some Lunyoro content
            nllb_result = nllb_result[:idx].strip().rstrip("?.,;: ")

    # Also strip trailing English sentences (Latin script words after Lunyoro)
    # Pattern: Lunyoro text followed by a sentence that looks like English
    nllb_result = _re2.sub(
        r"\s+[A-Z][a-z]+(?:\s+[a-z]+){3,}\??\s*$", "", nllb_result
    ).strip()

    # Post-process en→lun output: apply orthographic rules
    if direction == "en2lun" and nllb_result:
        # Detect if NLLB output is English (passthrough) — reject it
        # Heuristic: if output has >60% common English words, it's a passthrough
        import re as _re3

        common_en = {
            "the",
            "a",
            "an",
            "is",
            "are",
            "was",
            "were",
            "be",
            "been",
            "have",
            "has",
            "had",
            "do",
            "does",
            "did",
            "will",
            "would",
            "could",
            "should",
            "may",
            "might",
            "shall",
            "can",
            "to",
            "of",
            "in",
            "on",
            "at",
            "for",
            "with",
            "and",
            "or",
            "but",
            "not",
            "this",
            "that",
            "it",
            "he",
            "she",
            "they",
            "we",
            "you",
            "i",
            "my",
            "your",
            "his",
            "her",
            "their",
            "its",
            "our",
        }
        words = _re3.findall(r"[a-z]+", nllb_result.lower())
        if words:
            en_ratio = sum(1 for w in words if w in common_en) / len(words)
            if en_ratio > 0.5:
                return None  # NLLB returned English — discard, fall back to MarianMT
        nllb_result = _postprocess_lunyoro(nllb_result)

    return nllb_result


def _is_notation_garbage(text: str) -> bool:
    """Return True if the text looks like raw dictionary notation, not a real translation."""
    if not text:
        return True
    import re

    t = text.strip()
    # Patterns that indicate dictionary notation artifacts
    notation_patterns = [
        r"\bn\.\s*(cl\.|v\.|adj\.)",  # "n. cl.", "n. v."
        r"\(pl\.\s*(nil|same|\w+)\)",  # "(pl. nil)", "(pl. same)"
        r",\s*o-\s*,",  # ", o-,"  (noun class marker)
        r"\bcl\.\s*\d+",  # "cl. 11"
        r"^\s*[a-z]{1,3}\.\s*\(",  # starts with "n. (" or "v. ("
        r"\(pl\.\s*\w*\)\s*$",  # ends with "(pl. X)"
    ]
    for pat in notation_patterns:
        if re.search(pat, t, re.IGNORECASE):
            return True
    # Reject if output is just punctuation/numbers with no letters at all
    if not re.search(r"[a-zA-Z]", t):
        return True
    # Reject if output is extremely short (1-2 chars) — likely a tokenizer artifact
    if len(t.strip()) < 3:
        return True
    return False


# ── Selective RAG ────────────────────────────────────────────────────────────
# Thresholds:
#   >= 0.92  → use retrieved translation directly (very high confidence)
#   0.70-0.91 → inject as context hint to MT model
#   < 0.70   → pure neural MT, no retrieval
_RAG_DIRECT_THRESHOLD = 0.92  # use retrieved translation as-is
_RAG_HINT_THRESHOLD = 0.70  # inject as context hint
_RAG_LENGTH_TOLERANCE = 0.25  # max 25% length difference to use direct retrieval


def _selective_rag(text: str, direction: str = "en2lun", top_k: int = 3) -> dict | None:
    """
    Selective RAG: check corpus for high-confidence matches before neural MT.

    Returns a translation dict if a good match is found, None otherwise.
    - Score >= 0.92 AND length within 25%: return retrieved translation directly
    - Score 0.70-0.91: return None but store hint for MT context (future use)
    - Score < 0.70: return None (pure neural MT)

    Skips retrieval for:
    - Very short inputs (< 4 words) — poor semantic matches
    - Single words — handled by dictionary lookup
    """
    # For very short inputs (< 4 words), only allow exact matches from the index
    # — semantic similarity is unreliable for short phrases but exact matches are valid
    word_count = len(text.split())
    if word_count < 4:
        # Still do exact-match lookup for 1–3 word inputs
        try:
            _load_retrieval()
        except Exception:
            return None
        if direction == "en2lun":
            query_sentences = _index["english_sentences"]
            target_sentences = _index["lunyoro_sentences"]
        else:
            query_sentences = _index["lunyoro_sentences"]
            target_sentences = _index["english_sentences"]
        lower = text.strip().lower()
        for i, sent in enumerate(query_sentences):
            if sent.strip().lower() == lower:
                translation = target_sentences[i]
                if direction == "en2lun":
                    translation = _postprocess_lunyoro(translation)
                else:
                    translation = _postprocess_english(translation)
                return {
                    "translation": translation,
                    "translation_nllb": None,
                    "translation_marian": None,
                    "method": "exact_match",
                    "confidence": 1.0,
                    "matched_source": sent,
                    "alternatives": [],
                }
        return None  # no exact match — fall through to neural MT

    try:
        _load_retrieval()
    except Exception:
        return None

    # Guard: sem_model must be loaded to run semantic search
    if _sem_model is None:
        return None

    if direction == "en2lun":
        query_sentences = _index["english_sentences"]
        target_sentences = _index["lunyoro_sentences"]
        embeddings = _index["embeddings"]
    else:
        if "lunyoro_embeddings" not in _index:
            _index["lunyoro_embeddings"] = _sem_model.encode(
                _index["lunyoro_sentences"],
                show_progress_bar=False,
                batch_size=64,
                convert_to_numpy=True,
            )
        query_sentences = _index["lunyoro_sentences"]
        target_sentences = _index["english_sentences"]
        embeddings = _index["lunyoro_embeddings"]

    q_emb = _sem_model.encode(text, convert_to_numpy=True)
    scores = util.cos_sim(q_emb, embeddings)[0].numpy()
    top_idx = np.argsort(scores)[::-1][:top_k]
    best_idx = top_idx[0]
    best_score = float(scores[best_idx])

    if best_score < _RAG_HINT_THRESHOLD:
        return None  # too low — pure neural MT

    matched_src = query_sentences[best_idx]
    matched_tgt = target_sentences[best_idx]

    # Length sanity check: reject if retrieved sentence is very different in length
    input_len = len(text.split())
    retrieved_len = len(matched_src.split())
    length_ratio = abs(input_len - retrieved_len) / max(input_len, retrieved_len)

    if best_score >= _RAG_DIRECT_THRESHOLD and length_ratio <= _RAG_LENGTH_TOLERANCE:
        # High confidence + similar length → use retrieved translation directly
        translation = matched_tgt
        if direction == "en2lun":
            translation = _postprocess_lunyoro(translation)
        elif direction == "lun2en":
            translation = _postprocess_english(translation)
        alternatives = [
            {
                "score": round(float(scores[i]), 3),
                "source": query_sentences[i],
                "translation": target_sentences[i],
            }
            for i in top_idx[1:]
            if float(scores[i]) > 0.5
        ]
        return {
            "translation": translation,
            "translation_nllb": None,
            "translation_marian": None,
            "method": "selective_rag",
            "confidence": round(best_score, 3),
            "matched_source": matched_src,
            "alternatives": alternatives,
        }

    # Medium confidence (0.70-0.91): return None, MT will handle it
    # The matched translation could be used as a hint in future
    return None


# ── public API ───────────────────────────────────────────────────────────────


def _mirror_punctuation(source: str, translation: str) -> str:
    """
    Intelligently apply punctuation to translations based on:
    1. What the source input punctuation says (user intent)
    2. Whether the translation already has appropriate punctuation
    3. Whether the translation is a complete sentence or a phrase/fragment

    Rules:
    - Source has '?' → translation ends with '?' (always — it's a question)
    - Source has '!' → translation ends with '!' (always — it's an exclamation)
    - Source has '.' → add '.' only if translation looks like a full sentence
    - Source has no terminal punct → don't add any (user typed a fragment/phrase)
    - Never double-punctuate (if translation already ends with correct punct, leave it)
    - Single words or very short phrases don't get periods
    """
    if not translation or not source:
        return translation

    src = source.strip()
    tgt = translation.strip()

    if not src or not tgt:
        return tgt

    # Detect source terminal punctuation
    src_end = src[-1]
    tgt_end = tgt[-1]

    # Already has correct punctuation — don't touch it
    if tgt_end in ".?!":
        # But fix wrong type: if source is ? and translation ends with . swap it
        if src_end == "?" and tgt_end != "?":
            return tgt.rstrip(".!") + "?"
        if src_end == "!" and tgt_end != "!":
            return tgt.rstrip(".?") + "!"
        return tgt  # already punctuated correctly

    # Translation has no terminal punctuation yet — decide whether to add
    tgt_words = tgt.split()
    tgt_word_count = len(tgt_words)

    # Question mark — always if source is a question
    if src_end == "?":
        return tgt + "?"

    # Exclamation — always if source is exclamatory
    if src_end == "!":
        return tgt + "!"

    # Period — only if source has one AND translation looks like a full sentence
    # (more than 2 words and doesn't end mid-construction)
    if src_end == ".":
        if tgt_word_count >= 3:
            # Check the translation isn't ending on a preposition, conjunction or particle
            _incomplete_endings = {
                "omu", "ha", "na", "ni", "ne", "aha", "ku", "mu", "nga",
                "ngu", "kandi", "baitu", "kuba", "of", "in", "on", "at",
                "and", "or", "but", "the", "a", "an",
            }
            last_word = tgt_words[-1].lower().rstrip(".,;:")
            if last_word not in _incomplete_endings:
                return tgt + "."
        return tgt  # short or incomplete — no period

    # Source has no terminal punctuation (user typed a word/phrase)
    # Don't add anything — respect that it's a fragment
    return tgt


def translate(text: str, top_k: int = 3, context: str = "") -> dict:
    """English → Lunyoro/Rutooro — always runs both MarianMT and NLLB."""
    text = _normalise(text.strip())

    # Longer context window: trim context to last sentence if too long
    if context:
        import re as _re_ctx
        ctx_sentences = _re_ctx.split(r"(?<=[.!?])\s+", context.strip())
        context = ctx_sentences[-1] if ctx_sentences else context
        if len(context) > 150:
            context = context[-150:]

    # ── Always run both neural MT models first ────────────────────────────────
    marian = _mt_translate(text, "en2lun", context=context)
    nllb   = _nllb_translate(text, "en2lun", context=context)

    def _is_garbage(s: str | None) -> bool:
        if not s or not s.strip():
            return True
        words = s.split()
        if not words:
            return True
        short_count = sum(1 for w in words if 2 <= len(w) <= 3)
        return short_count / len(words) > 0.5

    # Apply punctuation mirroring to both
    if nllb:    nllb    = _mirror_punctuation(text, nllb)
    if marian:  marian  = _mirror_punctuation(text, marian)

    # Primary = NLLB if valid, else MarianMT
    neural_best = nllb if not _is_garbage(nllb) else marian

    # ── Selective RAG: try retrieval for high-confidence matches ─────────────
    rag_result = _selective_rag(text, direction="en2lun", top_k=top_k)
    if rag_result:
        rag_result["translation_nllb"]   = nllb
        rag_result["translation_marian"] = marian
        # If NLLB is valid, use it as primary translation even for RAG hits
        if not _is_garbage(nllb):
            rag_result["translation"] = nllb
        return rag_result

    # ── Corpus exact-match for short inputs ──────────────────────────────────
    if len(text.split()) <= 3:
        try:
            _load_retrieval()
            lower = text.lower()
            for i, sent in enumerate(_index.get("english_sentences", [])):
                if sent.strip().lower() == lower:
                    translation = _postprocess_lunyoro(_index["lunyoro_sentences"][i])
                    best = nllb if not _is_garbage(nllb) else translation
                    return {
                        "translation":         best,
                        "translation_nllb":    nllb,
                        "translation_marian":  marian,
                        "method": "exact_match",
                        "confidence": 1.0,
                        "alternatives": [],
                    }
        except Exception:
            pass

    if marian or nllb:
        return {
            "translation":         neural_best,
            "translation_nllb":    nllb,
            "translation_marian":  marian,
            "method": "neural_mt",
            "confidence": 1.0,
            "alternatives": [],
        }

    # 2. Retrieval fallback
    _load_retrieval()
    english_sentences = _index["english_sentences"]
    lunyoro_sentences = _index["lunyoro_sentences"]

    lower = text.lower()
    for i, sent in enumerate(english_sentences):
        if sent.lower() == lower:
            return {
                "translation": _postprocess_lunyoro(lunyoro_sentences[i]),
                "method": "exact_match",
                "confidence": 1.0,
                "alternatives": [],
            }

    q_emb = _sem_model.encode(text, convert_to_numpy=True)
    scores = util.cos_sim(q_emb, _index["embeddings"])[0].numpy()
    top_idx = np.argsort(scores)[::-1][:top_k]
    best, best_score = top_idx[0], float(scores[top_idx[0]])

    alternatives = [
        {
            "english": english_sentences[i],
            "lunyoro": lunyoro_sentences[i],
            "score": round(float(scores[i]), 3),
        }
        for i in top_idx[1:]
    ]

    if best_score > 0.5:
        return {
            "translation": _postprocess_lunyoro(lunyoro_sentences[best]),
            "method": "semantic_match",
            "confidence": round(best_score, 3),
            "matched_english": english_sentences[best],
            "alternatives": alternatives,
        }

    return _dict_fallback(
        text, best_score, english_sentences[best], alternatives, "en→lun"
    )


def _postprocess_english(text: str) -> str:
    """
    Post-process lun→en NLLB/Marian output for natural English.

    Fixes:
    1. Strip NLLB language-code prefix artifacts (run_Latn: ...)
    2. Double-subject removal ("The man he went" → "The man went")
    3. Redundant pronoun after noun ("My father he said" → "My father said")
    4. Over-capitalisation of common words mid-sentence
    5. Sentence capitalisation + punctuation cleanup
    6. Strip leading/trailing whitespace and repeated spaces
    """
    if not text or not text.strip():
        return text

    import re as _re

    # 1. Strip language-code prefix artifacts from NLLB
    text = _re.sub(r"^\s*[a-z]{2,3}_[A-Za-z]{3,4}\s*:\s*", "", text).strip()
    text = _re.sub(r"^\s*\[[A-Za-z _]+\]\s*", "", text).strip()

    # 1b. Fix NLLB Latin-script artifact: standalone "L" used as first-person pronoun
    # NLLB sometimes outputs "L" instead of "I" (character confusion in run_Latn)
    # Use lookahead/lookbehind instead of \b to handle edge cases
    text = _re.sub(r"(?<![A-Za-z])L(?![A-Za-z])", "I", text)

    # 2. Double-subject: noun phrase + pronoun ("The child he ...", "My mother she ...")
    # Pattern: (determiner + noun [+ adj]) followed immediately by he/she/they/it
    text = _re.sub(
        r"\b((?:the|a|an|my|your|his|her|our|their|this|that)\s+\w+(?:\s+\w+)?)\s+(he|she|they|it)\s+",
        r"\1 ",
        text,
        flags=_re.IGNORECASE,
    )

    # 3. Proper name + pronoun ("John he said" → "John said")
    text = _re.sub(
        r"\b([A-Z][a-z]+)\s+(he|she|they)\s+",
        r"\1 ",
        text,
    )

    # 4. Fix common over-translations of Runyoro copula constructions
    # "is is" / "are are" deduplication
    text = _re.sub(r"\b(is|are|was|were|has|have|had)\s+\1\b", r"\1", text, flags=_re.IGNORECASE)

    # 5. Strip NLLB hallucination artifacts — repeated short fragments at end
    # e.g. "I went to the market. I went to the market."
    sentences = _re.split(r"(?<=[.!?])\s+", text.strip())
    if len(sentences) > 1 and sentences[-1].strip().lower() == sentences[-2].strip().lower():
        sentences = sentences[:-1]
    text = " ".join(sentences)

    # 6. Capitalise first letter of each sentence
    # Only capitalise a–z at sentence start, not mid-word
    text = _re.sub(r"((?:^|(?<=[.!?]\s))([a-z]))", lambda m: m.group(0).upper(), text)

    # 7. Preserve existing terminal punctuation — don't add period blindly
    # (_mirror_punctuation handles this based on source input)
    text = text.strip()

    # 8. Collapse multiple spaces
    text = _re.sub(r"  +", " ", text)

    return text.strip()


def translate_to_english(text: str, top_k: int = 3, context: str = "") -> dict:
    """Lunyoro/Rutooro → English — always runs both MarianMT and NLLB."""
    text = _normalise(text.strip())

    if context:
        import re as _re_ctx
        ctx_sentences = _re_ctx.split(r"(?<=[.!?])\s+", context.strip())
        context = ctx_sentences[-1] if ctx_sentences else context
        if len(context) > 150:
            context = context[-150:]

    # ── Always run both neural MT models first ────────────────────────────────
    marian = _mt_translate(text, "lun2en", context=context)
    nllb   = _nllb_translate(text, "lun2en", context=context)

    if nllb:    nllb    = _postprocess_english(_mirror_punctuation(text, nllb))
    if marian:  marian  = _postprocess_english(_mirror_punctuation(text, marian))

    neural_best = nllb or marian

    # ── Selective RAG ─────────────────────────────────────────────────────────
    rag_result = _selective_rag(text, direction="lun2en", top_k=top_k)
    if rag_result:
        rag_result["translation_nllb"]   = nllb
        rag_result["translation_marian"] = marian
        if nllb:
            rag_result["translation"] = nllb
        return rag_result

    # ── Corpus exact-match ────────────────────────────────────────────────────
    if len(text.split()) <= 3:
        try:
            _load_retrieval()
            lower = text.lower()
            for i, sent in enumerate(_index.get("lunyoro_sentences", [])):
                if sent.strip().lower() == lower:
                    best = nllb if nllb else _postprocess_english(_index["english_sentences"][i])
                    return {
                        "translation":         best,
                        "translation_nllb":    nllb,
                        "translation_marian":  marian,
                        "method": "exact_match",
                        "confidence": 1.0,
                        "alternatives": [],
                    }
        except Exception:
            pass

    if marian or nllb:
        return {
            "translation":         neural_best,
            "translation_nllb":    nllb,
            "translation_marian":  marian,
            "method": "neural_mt",
            "confidence": 1.0,
            "alternatives": [],
        }

    _load_retrieval()
    english_sentences = _index["english_sentences"]
    lunyoro_sentences = _index["lunyoro_sentences"]

    lower = text.lower()
    for i, sent in enumerate(lunyoro_sentences):
        if sent.lower() == lower:
            return {
                "translation": _postprocess_english(english_sentences[i]),
                "method": "exact_match",
                "confidence": 1.0,
                "alternatives": [],
            }

    if "lunyoro_embeddings" not in _index:
        _index["lunyoro_embeddings"] = _sem_model.encode(
            lunyoro_sentences,
            show_progress_bar=False,
            batch_size=64,
            convert_to_numpy=True,
        )

    q_emb = _sem_model.encode(text, convert_to_numpy=True)
    scores = util.cos_sim(q_emb, _index["lunyoro_embeddings"])[0].numpy()
    top_idx = np.argsort(scores)[::-1][:top_k]
    best, best_score = top_idx[0], float(scores[top_idx[0]])

    alternatives = [
        {
            "lunyoro": lunyoro_sentences[i],
            "english": english_sentences[i],
            "score": round(float(scores[i]), 3),
        }
        for i in top_idx[1:]
    ]

    if best_score > 0.5:
        return {
            "translation": _postprocess_english(english_sentences[best]),
            "method": "semantic_match",
            "confidence": round(best_score, 3),
            "matched_lunyoro": lunyoro_sentences[best],
            "alternatives": alternatives,
        }

    return _dict_fallback_reverse(
        text, best_score, lunyoro_sentences[best], alternatives
    )


def _dict_fallback(text, best_score, matched_english, alternatives, direction):
    _load_retrieval()
    words = re.findall(r"[a-zA-Z']+", text.lower())
    dict_words = [d["word"] for d in _dictionary]
    found = []
    for word in words:
        # Check static web entries first
        from web_fallback import lookup_static

        static = lookup_static(word, "en→lun")
        if static:
            found.append(
                {"english_word": word, "lunyoro_word": static, "definition": ""}
            )
            continue
        match = process.extractOne(word, dict_words, scorer=fuzz.ratio, score_cutoff=80)
        if match:
            entry = next((d for d in _dictionary if d["word"] == match[0]), None)
            if entry:
                found.append(
                    {
                        "english_word": word,
                        "lunyoro_word": entry["word"],
                        "definition": entry.get("definitionNative", ""),
                    }
                )

    # If still nothing found, try web fallback for the full phrase
    if not found:
        from web_fallback import web_search_fallback

        web_result = web_search_fallback(text, "en→lun")
        if web_result:
            return {
                "translation": _postprocess_lunyoro(web_result),
                "method": "web_fallback",
                "confidence": 0.4,
                "alternatives": alternatives,
            }

    return {
        "translation": None,
        "method": "dictionary_fallback",
        "confidence": round(best_score, 3),
        "matched_english": matched_english,
        "alternatives": alternatives,
        "dictionary_matches": found,
        "message": "No close translation found. Showing closest matches.",
    }


def _dict_fallback_reverse(text, best_score, matched_lunyoro, alternatives):
    _load_retrieval()
    words = re.findall(r"[a-zA-Z']+", text.lower())
    dict_words = [d["word"] for d in _dictionary]
    found = []
    for word in words:
        match = process.extractOne(word, dict_words, scorer=fuzz.ratio, score_cutoff=75)
        if match:
            entry = next((d for d in _dictionary if d["word"] == match[0]), None)
            if entry and entry.get("definitionEnglish"):
                found.append(
                    {
                        "lunyoro_word": entry["word"],
                        "english_definition": entry["definitionEnglish"],
                    }
                )
    return {
        "translation": None,
        "method": "dictionary_fallback",
        "confidence": round(best_score, 3),
        "matched_lunyoro": matched_lunyoro,
        "alternatives": alternatives,
        "dictionary_matches": found,
        "message": "No close translation found. Showing closest matches.",
    }


def _infer_pos(word: str) -> str | None:
    """
    Heuristically infer the likely POS of a Lunyoro/Rutooro word from its prefix.
    Based on Bantu noun class and verb prefix patterns in the corpus.
    """
    w = word.lower().strip()
    if w.startswith(("oku", "okw", "ok-")):
        return "V"
    noun_prefixes = (
        "om",
        "ab",
        "ob",
        "eb",
        "ek",
        "ak",
        "en",
        "em",
        "in",
        "im",
        "oru",
        "ama",
        "obu",
        "otu",
        "oku",
        "eri",
        "aga",
        "ege",
    )
    if any(w.startswith(p) for p in noun_prefixes):
        return "N"
    if w.startswith(("nk", "ng", "mbi", "ndi", "nge")):
        return "ADJ"
    return None


def lookup_word(word: str, direction: str = "en→lun") -> list:
    """
    Dictionary lookup: exact match → fuzzy dictionary → neural MT → corpus.
    """
    _load_retrieval()
    word = _normalise(word.strip())
    word_lower = word.lower()
    results: list = []
    seen_words: set[str] = set()

    def clean_mt(text: str | None) -> str | None:
        """Strip domain tags and notation garbage from MT output."""
        if not text:
            return None
        import re as _re

        t = _re.sub(r"^\[.*?\]\s*", "", text).strip()  # remove [GENERAL] etc.
        t = _re.sub(
            r",\s*[a-z]-\s*,.*$", "", t, flags=_re.I
        ).strip()  # ", o-, n. cl..."
        t = _re.sub(r"\(pl\.\s*\w*\)", "", t).strip()  # (pl. nil)
        t = _re.sub(r"\bn\.\s*cl\.\s*\d+.*$", "", t, flags=_re.I).strip()
        t = _re.sub(r",\s*n\.\s*,.*$", "", t, flags=_re.I).strip()  # ", n., ekisisani"
        t = _re.sub(r",\s*v\.\s*,.*$", "", t, flags=_re.I).strip()  # ", v., ..."
        t = _re.sub(r",\s*adj\.\s*,.*$", "", t, flags=_re.I).strip()
        t = _re.sub(
            r"\s*,\s*ekisisani.*$", "", t, flags=_re.I
        ).strip()  # ", ekisisani" suffix
        t = t.strip(".,; ")
        if not t or len(t) < 2:
            return None
        return t

    mt_direction = "en2lun" if direction == "en→lun" else "lun2en"
    raw_mt = _mt_translate(word, mt_direction)
    mt_translation = clean_mt(raw_mt)

    # ── 1. Exact dictionary match (highest priority) ──────────────────────
    if direction == "en→lun":
        exact = [
            d
            for d in _dictionary
            if word_lower == (d.get("definitionEnglish") or "").lower().strip()
            or word_lower in (d.get("definitionEnglish") or "").lower().split()
        ]
    else:
        exact = [
            d
            for d in _dictionary
            if word_lower == d["word"].lower() or d["word"].lower() == word_lower
        ]

    for d in exact:
        if d["word"] not in seen_words:
            seen_words.add(d["word"])
            results.append(
                {**d, "source": "dictionary", "confidence": 1.0, "pos_matched": False}
            )

    # ── 2. Fuzzy dictionary match ─────────────────────────────────────────
    if direction == "en→lun":
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
                )
    else:
        dict_words_lower = [d["word"].lower() for d in _dictionary]
        fuzzy_raw = process.extract(
            word_lower,
            dict_words_lower,
            scorer=fuzz.ratio,  # stricter scorer for Lunyoro words
            limit=10,
            score_cutoff=80,  # higher threshold — Lunyoro words are similar-looking
        )
        for match_text, score, _ in fuzzy_raw:
            entry = _dict_word_map.get(match_text)
            if entry and entry["word"] not in seen_words:
                seen_words.add(entry["word"])
                results.append(
                    {
                        **entry,
                        "source": "dictionary",
                        "confidence": round(score / 100, 3),
                        "pos_matched": False,
                    }
                )

    # ── 3. Neural MT result ───────────────────────────────────────────────
    if mt_translation and mt_translation.lower() not in seen_words:
        seen_words.add(mt_translation.lower())
        # Try to enrich with dictionary entry for the MT word
        mt_dict = _dict_word_map.get(mt_translation.lower())
        results.append(
            {
                "word": mt_translation if direction == "en→lun" else word,
                "definitionEnglish": word if direction == "en→lun" else mt_translation,
                "definitionNative": mt_dict.get("definitionNative", "")
                if mt_dict
                else "",
                "exampleSentence1": mt_dict.get("exampleSentence1", "")
                if mt_dict
                else "",
                "exampleSentence1English": mt_dict.get("exampleSentence1English", "")
                if mt_dict
                else "",
                "dialect": mt_dict.get("dialect", "") if mt_dict else "",
                "pos": mt_dict.get("pos", "") if mt_dict else "",
                "source": "neural_mt",
                "confidence": 0.95,
                "pos_matched": False,
            }
        )

    # ── 4. Corpus semantic search (only for multi-word queries) ──────────────
    # Single words get poor corpus matches — skip unless query is a phrase
    is_phrase = len(word.split()) > 1
    if is_phrase:
        q_emb = _sem_model.encode(word, convert_to_numpy=True)
        if direction == "en→lun":
            scores = util.cos_sim(q_emb, _index["embeddings"])[0].numpy()
        else:
            if "lunyoro_embeddings" not in _index:
                _index["lunyoro_embeddings"] = _sem_model.encode(
                    _index["lunyoro_sentences"],
                    show_progress_bar=False,
                    batch_size=64,
                    convert_to_numpy=True,
                )
            scores = util.cos_sim(q_emb, _index["lunyoro_embeddings"])[0].numpy()

        top_idx = np.argsort(scores)[::-1][:5]
        for i in top_idx:
            score = float(scores[i])
            if score < 0.45:
                break
            lun = _index["lunyoro_sentences"][i]
            en = _index["english_sentences"][i]
            if _is_notation_garbage(lun) or _is_notation_garbage(en):
                continue
            display_word = lun if direction == "en→lun" else en
            if display_word not in seen_words:
                seen_words.add(display_word)
                results.append(
                    {
                        "word": display_word,
                        "definitionEnglish": en if direction == "en→lun" else lun,
                        "definitionNative": "",
                        "exampleSentence1": lun,
                        "exampleSentence1English": en,
                        "dialect": "",
                        "pos": "",
                        "source": "corpus",
                        "confidence": round(score, 3),
                        "pos_matched": False,
                    }
                )

    # Sort: exact dict first, then by confidence
    results.sort(
        key=lambda x: (
            0
            if (x["source"] == "dictionary" and x["confidence"] == 1.0)
            else 1
            if x["source"] == "dictionary"
            else 2
            if x["source"] == "neural_mt"
            else 3,
            -x.get("confidence", 0),
        )
    )
    return results[:8]


def get_index_and_model():
    _load_retrieval()
    return _index, _sem_model


def _build_corpus_vocab() -> set:
    """Build vocabulary of known Lunyoro/Rutooro words from corpus, tokenizer, and dictionary."""
    _load_retrieval()
    known: set[str] = set()

    for sent in _index["lunyoro_sentences"]:
        for w in re.findall(r"[a-zA-Z']+", sent):
            if len(w) >= 2:
                known.add(w.lower())

    # Only add tokenizer vocab for words that look Bantu (not English)
    # Filter: must contain at least one of the Bantu vowel patterns and no English-only patterns
    lun2en_path = os.path.join(MODEL_DIR, "lun2en")
    if os.path.isdir(lun2en_path):
        try:
            from transformers import MarianTokenizer

            tok = MarianTokenizer.from_pretrained(lun2en_path)
            _BANTU_STARTS = ("ok", "om", "ab", "ob", "eb", "ek", "ak", "ag",
                             "or", "en", "em", "ni", "ba", "ka", "ku", "mu",
                             "bu", "tu", "bi", "ki", "ga", "rw", "nt", "mb")
            for token in tok.get_vocab().keys():
                clean = token.lstrip("▁").lower()
                if (clean.isalpha() and len(clean) >= 3
                        and any(clean.startswith(p) for p in _BANTU_STARTS)):
                    known.add(clean)
        except Exception:
            pass

    # Common English words that leak into the dictionary — exclude them from known vocab
    _EN_STOPLIST = frozenset({
        "agonizing", "ago", "age", "able", "about", "above", "after", "again",
        "against", "all", "also", "although", "always", "among", "another",
        "any", "back", "because", "before", "between", "both", "came", "come",
        "day", "does", "done", "down", "each", "even", "every", "find", "first",
        "from", "get", "give", "go", "good", "great", "help", "here", "high",
        "home", "how", "into", "just", "keep", "know", "large", "last", "life",
        "like", "little", "long", "look", "made", "make", "man", "many", "men",
        "might", "more", "most", "much", "must", "name", "need", "never", "new",
        "now", "old", "one", "only", "other", "out", "over", "own", "part",
        "people", "place", "put", "right", "said", "same", "say", "see", "seem",
        "so", "some", "still", "such", "take", "than", "then", "there", "these",
        "think", "those", "though", "through", "time", "too", "two", "under",
        "until", "up", "upon", "use", "very", "want", "way", "well", "what",
        "when", "where", "which", "while", "who", "why", "work", "world",
        "year", "yet", "your", "their", "have", "been", "will", "would",
        "could", "should", "shall", "being", "were", "had", "has", "did",
    })
    for d in _dictionary:
        if d.get("word"):
            w = d["word"].lower()
            if w not in _EN_STOPLIST:
                known.add(w)

    return known


_corpus_vocab: set | None = None


def spellcheck(text: str) -> list:
    global _corpus_vocab
    _load_retrieval()

    text = _normalise(text)

    if _corpus_vocab is None:
        _corpus_vocab = _build_corpus_vocab()
        # Add interjections as known valid words
        from language_rules import INTERJECTIONS, IDIOMS

        for word in INTERJECTIONS:
            for w in word.split():
                if len(w) >= 2:
                    _corpus_vocab.add(w.lower())
        for phrase in IDIOMS:
            for w in phrase.split():
                if len(w) >= 2:
                    _corpus_vocab.add(w.lower())

    vocab_list = list(_corpus_vocab)
    tokens = re.findall(r"[a-zA-Z']+", text)
    misspelled = []

    # Common English words that appear in code-switched Runyoro text — never flag
    _SKIP_ENGLISH = frozenset({
        "the", "a", "an", "is", "are", "was", "were", "and", "or", "of",
        "in", "to", "it", "he", "she", "we", "you", "i", "my", "his", "her",
    })

    for token in tokens:
        lower = token.lower()

        # Skip common English function words
        if lower in _SKIP_ENGLISH:
            continue

        # Skip very short tokens
        if len(lower) < 3:
            continue

        # Already known — no issue
        if lower in _corpus_vocab:
            continue

        # ── Bantu prefix check: skip words that look like valid formed Runyoro words
        # BUT always check words with suspicious double vowels (aa, ee, oo, ii, uu)
        # since doubled vowels are almost always a typo in Runyoro
        import re as _re_dbl
        has_suspicious_double = bool(_re_dbl.search(r"[aeiou]{3,}|([aeiou])\1{1,}", lower))

        if not has_suspicious_double:
            _BANTU_PREFIXES = (
                "oku", "okw", "omu", "aba", "obu", "otu", "ama", "eri",
                "ebi", "eki", "aka", "aga", "oru",
            )
            _SHORT_PREFIXES = ("en", "em", "ni", "ba", "ka", "ku", "mu", "bu",
                               "tu", "bi", "ki", "ga", "in", "im")
            if any(lower.startswith(p) for p in _BANTU_PREFIXES) and len(lower) >= 6:
                continue
            if any(lower.startswith(p) for p in _SHORT_PREFIXES) and len(lower) >= 9:
                continue

        # ── Tokenizer check: does the MarianMT model know this word as a single token?
        lun2en_path = os.path.join(MODEL_DIR, "lun2en")
        model_knows = False
        if os.path.isdir(lun2en_path) and _load_mt("lun2en"):
            try:
                tokenizer, _, _ = _mt_models["lun2en"]
                pieces = tokenizer.tokenize(lower)
                if pieces and "<unk>" not in pieces and len(pieces) == 1:
                    model_knows = True
            except Exception:
                pass

        if model_knows:
            continue

        # ── Fuzzy suggestion search ──
        # Use both fuzz.ratio AND fuzz.partial_ratio for better Bantu stem matching
        prefix = lower[:4]  # 4-char prefix for better pool narrowing
        prefix_words = [w for w in vocab_list if w.startswith(prefix[:3])]
        candidate_pool = prefix_words if len(prefix_words) >= 5 else vocab_list

        # Score with WRatio which combines multiple fuzzy strategies
        suggestions_ratio = process.extract(
            lower, candidate_pool, scorer=fuzz.WRatio, limit=8, score_cutoff=70,
        )
        # Also try token_sort for morphological variants
        suggestions_sort = process.extract(
            lower, candidate_pool, scorer=fuzz.token_sort_ratio, limit=5, score_cutoff=72,
        )

        # Merge, dedupe, sort by score — filter out English-looking words
        all_suggestions = {s[0]: s[1] for s in suggestions_ratio}
        for s in suggestions_sort:
            if s[0] not in all_suggestions or s[1] > all_suggestions[s[0]]:
                all_suggestions[s[0]] = s[1]

        # Filter suggestions: keep only words that are in the Runyoro corpus vocab
        # This removes any English words that leaked into the candidate pool
        def _is_runyoro_word(w: str) -> bool:
            """True if word looks like a valid Runyoro/Rutooro word."""
            if w in _corpus_vocab:
                return True
            # Must start with a known multi-char Bantu prefix (3+ chars)
            # and be long enough to be a real word
            _BANTU_P3 = ("oku", "okw", "omu", "aba", "obu", "otu", "ama",
                         "eri", "ebi", "eki", "aka", "aga", "oru", "eng",
                         "emb", "ngo", "nka", "nkug", "nin", "wee", "ree",
                         "bwa", "kwa", "twa", "mwa", "nya", "nyi")
            return (any(w.startswith(p) for p in _BANTU_P3) and len(w) >= 5)

        top = [w for w, _ in sorted(all_suggestions.items(), key=lambda x: -x[1])
               if w != lower and _is_runyoro_word(w)][:3]

        misspelled.append({"word": token, "suggestions": top})

    return misspelled
