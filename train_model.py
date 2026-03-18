"""
EcoShield ML Training Script
=============================
Run this script to:
1. Generate 10,000 realistic transaction records
2. Train a Random Forest fraud detection model
3. Evaluate the model (accuracy, precision, recall)
4. Save the model as model.pkl
"""

import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import (accuracy_score, precision_score,
                             recall_score, f1_score, confusion_matrix,
                             classification_report)
import joblib
import random

print("=" * 50)
print("  EcoShield Fraud Detection - ML Training")
print("=" * 50)

# ── Step 1: Generate training data ────────────────────────────────────────
print("\n[1/4] Generating 10,000 transaction records...")

random.seed(42)
np.random.seed(42)

records = []

for i in range(10000):
    # Randomly decide if this is a fraud transaction (15% fraud rate)
    is_fraud = 1 if random.random() < 0.15 else 0

    if is_fraud:
        # Fraud transactions have suspicious patterns
        amount       = random.uniform(3000, 10000)
        hour         = random.choice([0, 1, 2, 3, 4, 23, 22, 21])
        is_new_recip = random.choices([0, 1], weights=[0.2, 0.8])[0]
        rapid_fire   = random.choices([0, 1], weights=[0.2, 0.8])[0]
        foreign_ip   = random.choices([0, 1], weights=[0.3, 0.7])[0]
        tx_type      = random.choice([0, 1, 2, 3])  # 0=send,1=receive,2=withdraw,3=payment
    else:
        # Legitimate transactions look normal
        amount       = random.uniform(10, 3000)
        hour         = random.randint(7, 20)
        is_new_recip = random.choices([0, 1], weights=[0.8, 0.2])[0]
        rapid_fire   = random.choices([0, 1], weights=[0.9, 0.1])[0]
        foreign_ip   = random.choices([0, 1], weights=[0.95, 0.05])[0]
        tx_type      = random.choice([0, 1, 2, 3])

    records.append({
        "amount":       round(amount, 2),
        "hour":         hour,
        "is_new_recip": is_new_recip,
        "rapid_fire":   rapid_fire,
        "foreign_ip":   foreign_ip,
        "tx_type":      tx_type,
        "is_fraud":     is_fraud,
    })

df = pd.DataFrame(records)
print(f"    Total records:     {len(df)}")
print(f"    Legitimate:        {(df.is_fraud == 0).sum()}")
print(f"    Fraudulent:        {(df.is_fraud == 1).sum()}")

# ── Step 2: Prepare features ──────────────────────────────────────────────
print("\n[2/4] Preparing features and splitting data...")

FEATURES = ["amount", "hour", "is_new_recip", "rapid_fire", "foreign_ip", "tx_type"]

X = df[FEATURES]
y = df["is_fraud"]

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)

print(f"    Training samples:  {len(X_train)}")
print(f"    Testing samples:   {len(X_test)}")

# ── Step 3: Train the model ───────────────────────────────────────────────
print("\n[3/4] Training Random Forest model...")

model = RandomForestClassifier(
    n_estimators=100,
    max_depth=10,
    random_state=42,
    class_weight="balanced",
)

model.fit(X_train, y_train)
print("    Model trained successfully!")

# ── Step 4: Evaluate the model ────────────────────────────────────────────
print("\n[4/4] Evaluating model performance...")

y_pred = model.predict(X_test)

accuracy  = accuracy_score(y_test, y_pred)
precision = precision_score(y_test, y_pred)
recall    = recall_score(y_test, y_pred)
f1        = f1_score(y_test, y_pred)

print("\n" + "=" * 50)
print("  MODEL EVALUATION RESULTS")
print("=" * 50)
print(f"  Accuracy:   {accuracy  * 100:.2f}%")
print(f"  Precision:  {precision * 100:.2f}%")
print(f"  Recall:     {recall    * 100:.2f}%")
print(f"  F1 Score:   {f1        * 100:.2f}%")

print("\n  Confusion Matrix:")
cm = confusion_matrix(y_test, y_pred)
print(f"  True Negatives  (correct legit):   {cm[0][0]}")
print(f"  False Positives (wrong fraud flag): {cm[0][1]}")
print(f"  False Negatives (missed fraud):     {cm[1][0]}")
print(f"  True Positives  (correct fraud):    {cm[1][1]}")

print("\n  Full Classification Report:")
print(classification_report(y_test, y_pred, target_names=["Legitimate", "Fraud"]))

print("\n  Feature Importance (what matters most):")
for feat, imp in sorted(zip(FEATURES, model.feature_importances_), key=lambda x: -x[1]):
    bar = "█" * int(imp * 50)
    print(f"  {feat:<15} {bar} {imp:.4f}")

# ── Save the model ────────────────────────────────────────────────────────
joblib.dump(model, "model.pkl")
print("\n" + "=" * 50)
print("  model.pkl saved successfully!")
print("  Your ML model is ready to use in EcoShield.")
print("=" * 50)
