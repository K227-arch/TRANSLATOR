"""
Build translation index from cleaned dictionary data.
"""
import os
import pickle
import pandas as pd
from sentence_transformers import SentenceTransformer

BASE_DIR = os.path.dirname(__file__)
CLEAN_DIR = os.path.join(BASE_DIR, "data", "cleaned")
MODEL_DIR = os.path.join(BASE_DIR, "model")
INDEX_PATH = os.path.join(MODEL_DIR, "translation_index.pkl")

def build_index():
    print("Building translation index...")
    
    # Load dictionary data
    dict_files = [
        "word_entries_clean.csv",
        "rutooro_dictionary_clean.csv",
    ]
    
    dictionary = []
    for fname in dict_files:
        fpath = os.path.join(CLEAN_DIR, fname)
        if os.path.exists(fpath):
            df = pd.read_csv(fpath)
            for _, row in df.iterrows():
                word = row.get("word", row.get("runyoro", ""))
                definition = row.get("definitionEnglish", row.get("english", ""))
                pos = row.get("partOfSpeech", "")
                example = row.get("exampleSentence", "")
                
                # Convert to string and handle NaN/None
                word = str(word) if pd.notna(word) else ""
                definition = str(definition) if pd.notna(definition) else ""
                pos = str(pos) if pd.notna(pos) else ""
                example = str(example) if pd.notna(example) else ""
                
                entry = {
                    "word": word,
                    "definitionEnglish": definition,
                    "partOfSpeech": pos,
                    "exampleSentence": example,
                }
                if entry["word"] and entry["definitionEnglish"]:
                    dictionary.append(entry)
    
    print(f"Loaded {len(dictionary)} dictionary entries")
    
    # Load sentence transformer model
    print("Loading sentence transformer model...")
    model_name = "sentence-transformers/all-MiniLM-L6-v2"
    sem_model = SentenceTransformer(model_name)
    
    # Build index
    index = {
        "model_name": model_name,
        "dictionary": dictionary,
    }
    
    # Save index
    os.makedirs(MODEL_DIR, exist_ok=True)
    with open(INDEX_PATH, "wb") as f:
        pickle.dump(index, f)
    
    print(f"✓ Translation index saved to {INDEX_PATH}")

if __name__ == "__main__":
    build_index()
