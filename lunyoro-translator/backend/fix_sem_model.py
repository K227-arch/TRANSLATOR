"""
Fix _load_retrieval so it always loads the sem_model whose name is stored
in the index, not the local sem_model dir (which may be a different model).
"""
path = "translate.py"

with open(path, "r", encoding="utf-8") as f:
    content = f.read()

old = """    # Prefer local sem_model dir (always present when downloaded by download_models.py)
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
                        logger.warning("tokenizer.json appears to be an LFS pointer, skipping local")
            except Exception:
                pass
        else:
            local_sem_ok = True  # no tokenizer.json but other files exist

    if local_sem_ok:
        sem_path = SEM_MODEL_DIR
        logger.info("Loading sem_model from local path: %s", SEM_MODEL_DIR)
    else:
        # Fall back to HuggingFace Hub
        hf_sem = HF_MODELS.get("sem_model", "keithtwesigye/lunyoro-sentence-embeddings")
        sem_path = hf_sem
        logger.info("Loading sem_model from HF Hub: %s", sem_path)"""

new = """    # Always use the model name stored in the index so embeddings stay consistent.
    # The local sem_model dir may contain a DIFFERENT model — only use it if its
    # name matches what the index was built with.
    index_model_name = _index.get("model_name", "paraphrase-multilingual-MiniLM-L12-v2")
    local_model_name_file = os.path.join(SEM_MODEL_DIR, "sentence_bert_config.json")
    local_matches = False
    if os.path.isdir(SEM_MODEL_DIR) and os.path.exists(local_model_name_file):
        try:
            import json as _json
            with open(local_model_name_file) as _lf:
                _lcfg = _json.load(_lf)
            if index_model_name in str(_lcfg):
                local_matches = True
        except Exception:
            pass

    if local_matches:
        sem_path = SEM_MODEL_DIR
        logger.info("Loading sem_model from local path (matches index): %s", SEM_MODEL_DIR)
    else:
        # Use the exact model the index was built with — download from HF Hub if needed
        sem_path = index_model_name
        logger.info("Loading sem_model from HF Hub (index model): %s", sem_path)"""

if old in content:
    content = content.replace(old, new, 1)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print("Fix applied successfully")
else:
    print("ERROR: pattern not found")
