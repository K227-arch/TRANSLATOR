"""
Preprocess CSV data for training and lookup.
Outputs cleaned sentence pairs and dictionary entries.
"""
import pandas as pd
import re
import os

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")


def clean_text(text: str) -> str:
    if not isinstance(text, str):
        return ""
    text = text.strip().strip('"').strip()
    text = re.sub(r'\s+', ' ', text)
    return text


def load_sentence_pairs() -> pd.DataFrame:
    path = os.path.join(DATA_DIR, "english_nyoro.csv")
    df = pd.read_csv(path)
    df.columns = [c.strip() for c in df.columns]
    df = df.rename(columns={"English": "english", "Nyoro": "lunyoro"})
    df["english"] = df["english"].apply(clean_text)
    df["lunyoro"] = df["lunyoro"].apply(clean_text)
    # drop empty or too short rows
    df = df[(df["english"].str.len() > 3) & (df["lunyoro"].str.len() > 3)]
    df = df.drop_duplicates(subset=["english"])
    df = df.reset_index(drop=True)
    return df


def load_dictionary() -> pd.DataFrame:
    frames = []
    for fname in ["word_entries_rows.csv", "word_entries_rows (1).csv"]:
        path = os.path.join(DATA_DIR, fname)
        if os.path.exists(path):
            frames.append(pd.read_csv(path))
    df = pd.concat(frames, ignore_index=True)
    df = df[["word", "definitionEnglish", "definitionNative",
             "exampleSentence1", "exampleSentence1English",
             "exampleSentence2", "exampleSentence2English", "dialect", "pos"]].copy()
    for col in df.columns:
        df[col] = df[col].apply(clean_text)
    df = df[df["word"].str.len() > 0]
    df = df.drop_duplicates(subset=["word"])
    df = df.reset_index(drop=True)
    return df


if __name__ == "__main__":
    pairs = load_sentence_pairs()
    print(f"Sentence pairs loaded: {len(pairs)}")
    print(pairs.head(3))

    dictionary = load_dictionary()
    print(f"\nDictionary entries loaded: {len(dictionary)}")
    print(dictionary.head(3))
