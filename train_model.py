"""
train_model.py — Fake News Detector
Combines:
  1. ISOT Dataset     → True.csv + Fake.csv  (title, text, subject, date)
  2. BharatKosh       → bharatkosh.csv        (India-specific, multilingual)
"""

import pickle, json, re, os
import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, confusion_matrix, roc_auc_score
from sklearn.pipeline import Pipeline

# ── Stopwords ─────────────────────────────────────────────────
STOP_WORDS = {
    'the','a','an','and','or','but','in','on','at','to','for','of','with',
    'by','from','is','are','was','were','be','been','have','has','had','do',
    'does','did','will','would','could','should','this','that','these','those',
    'it','its','i','me','my','we','our','you','your','he','him','his','she',
    'her','they','them','their','what','which','who','when','where','why',
    'how','all','each','also','said','says','according','told','report',
    'news','today','new','reuters',
}

def preprocess(text: str) -> str:
    if not isinstance(text, str): return ""
    text = text.lower()
    text = re.sub(r'http\S+|www\S+', '', text)
    text = re.sub(r'<[^>]+>', '', text)
    text = re.sub(r'\(reuters\).*?-', '', text)
    text = re.sub(r'[^a-z\s]', ' ', text)
    tokens = [t for t in text.split() if t not in STOP_WORDS and len(t) > 2]
    return ' '.join(tokens)


# ════════════════════════════════════════════════════════
# DATASET 1 — ISOT (True.csv + Fake.csv)
# Columns: title, text, subject, date
# ════════════════════════════════════════════════════════
print("[INFO] Loading ISOT dataset...")

true_df = pd.read_csv('data/News_dataset/True.csv')
fake_df = pd.read_csv('data/News_dataset/Fake.csv')
true_df['label'] = 1
fake_df['label'] = 0

# Combine title + text
for d in [true_df, fake_df]:
    d['content'] = d['title'].fillna('') + ' ' + d['text'].fillna('')

isot_df = pd.concat([true_df, fake_df], ignore_index=True)[['content', 'label']]
print(f"  ISOT → {len(isot_df)} samples")


# ════════════════════════════════════════════════════════
# DATASET 2 — BharatKosh
# Columns: id, author_name, fact_check_source, source_type,
#          statement, eng_trans_statement,
#          news_body, eng_trans_news_body,
#          media_link, publish_date, fact_check_link,
#          news_category, language, region, platform,
#          text, video, image, label
# ════════════════════════════════════════════════════════
print("[INFO] Loading BharatKosh dataset...")

bk = pd.read_excel('data/News_dataset/bharatkosh.xlsx')

print(f"  Columns : {bk.columns.tolist()}")
print(f"  Shape   : {bk.shape}")
print(f"  Labels  : {bk['Label'].value_counts().to_dict()}")

# ── Label mapping: TRUE=1 (real), FALSE=0 (fake) ─────────
bk['label'] = bk['Label'].astype(str).str.strip().str.upper()
bk['label'] = bk['label'].map({
    'TRUE' : 1,
    'FALSE': 0,
})

# ── Build content from English columns only ───────────────
bk['content'] = (
    bk['Eng_Trans_Statement'].fillna('') + ' ' +
    bk['Eng_Trans_News_Body'].fillna('')
).str.strip()

# ── Drop bad rows ─────────────────────────────────────────
bk = bk[['content', 'label']].dropna()
bk = bk[bk['label'].isin([0, 1])]
bk = bk[bk['content'].str.len() > 20]

print(f"  BharatKosh → {len(bk)} usable samples")
print(f"  Real: {(bk['label']==1).sum()} | Fake: {(bk['label']==0).sum()}")


# ════════════════════════════════════════════════════════
# COMBINE BOTH DATASETS
# ════════════════════════════════════════════════════════
print("\n[INFO] Combining datasets...")

df = pd.concat([isot_df, bk], ignore_index=True)
df = df.dropna()
df = df.sample(frac=1, random_state=42).reset_index(drop=True)

print(f"  Total samples : {len(df)}")
print(f"  Real news     : {df['label'].sum()}")
print(f"  Fake news     : {(df['label']==0).sum()}")


# ── Preprocess ────────────────────────────────────────────────
print("\n[INFO] Preprocessing (may take 1-2 minutes for large dataset)...")
df['processed'] = df['content'].apply(preprocess)

# Remove empty after preprocessing
df = df[df['processed'].str.len() > 5]
print(f"[INFO] After preprocessing: {len(df)} samples")


# ── Train / Test Split ────────────────────────────────────────
X = df['processed']
y = df['label']

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)
print(f"[INFO] Train: {len(X_train)} | Test: {len(X_test)}")


# ── Pipeline ──────────────────────────────────────────────────
pipeline = Pipeline([
    ('tfidf', TfidfVectorizer(
        max_features=80000,
        ngram_range=(1, 3),
        sublinear_tf=True,
        min_df=2,
        strip_accents='unicode',
        analyzer='word',
    )),
    ('clf', LogisticRegression(
        C=10.0,
        max_iter=2000,
        solver='saga',
        class_weight='balanced',
        random_state=42,
        n_jobs=-1,
    ))
])


# ── Train ─────────────────────────────────────────────────────
print("[INFO] Training model...")
pipeline.fit(X_train, y_train)


# ── Evaluate ──────────────────────────────────────────────────
print("[INFO] Evaluating...")
y_pred = pipeline.predict(X_test)
y_prob = pipeline.predict_proba(X_test)[:, 1]

acc = accuracy_score(y_test, y_pred)
auc = roc_auc_score(y_test, y_prob)
cm  = confusion_matrix(y_test, y_pred)

print(f"\n{'='*45}")
print(f"  Accuracy   : {acc*100:.2f}%")
print(f"  ROC-AUC    : {auc*100:.2f}%")
print(f"  Confusion Matrix:")
print(f"    TN={cm[0,0]}  FP={cm[0,1]}")
print(f"    FN={cm[1,0]}  TP={cm[1,1]}")
print(f"{'='*45}\n")


# ── Save Metrics ──────────────────────────────────────────────
os.makedirs('models', exist_ok=True)

metrics = {
    "accuracy"        : round(acc * 100, 2),
    "roc_auc"         : round(auc * 100, 2),
    "precision_fake"  : round(float(cm[0,0]) / max(float(cm[0,0]+cm[1,0]), 1) * 100, 2),
    "recall_fake"     : round(float(cm[0,0]) / max(float(cm[0,0]+cm[0,1]), 1) * 100, 2),
    "precision_real"  : round(float(cm[1,1]) / max(float(cm[1,1]+cm[0,1]), 1) * 100, 2),
    "recall_real"     : round(float(cm[1,1]) / max(float(cm[1,1]+cm[1,0]), 1) * 100, 2),
    "confusion_matrix": cm.tolist(),
    "total_samples"   : len(df),
    "train_samples"   : len(X_train),
    "test_samples"    : len(X_test),
}

with open('models/metrics.json', 'w') as f:
    json.dump(metrics, f, indent=2)

with open('models/model.pkl', 'wb') as f:
    pickle.dump(pipeline, f)

print("[INFO] models/model.pkl  saved ✓")
print("[INFO] models/metrics.json saved ✓")
print("[INFO] All done! Run: python app.py")
