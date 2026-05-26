import pandas as pd

train = pd.read_csv('data/training/train.csv')
print(f"train.csv total: {len(train):,}")

tagged = train[train['english'].str.match(r'^\[', na=False)]
print(f"Domain-tagged pairs: {len(tagged):,}")

if len(tagged) > 0:
    print("\nSample tagged pairs:")
    for _, r in tagged.sample(min(8, len(tagged)), random_state=1).iterrows():
        en = str(r['english'])[:65]
        lun = str(r['lunyoro'])
        print(f"  EN:  {en}")
        print(f"  LUN: {lun}")
        print()
else:
    print("\nNo domain-tagged pairs found in train.csv")
    print("Last 5 rows of train.csv:")
    print(train.tail(5).to_string())
