"""
ml/win_predictor.py

Win prediction classifier — predicts win/loss from team feature vectors.
Trains XGBoost and Random Forest, compares performance, saves best model.

Run with:
    cd ~/pokeproject
    python3 ml/win_predictor.py
"""

import sys
import json
import pickle
import numpy as np
import pandas as pd
from pathlib import Path

from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import accuracy_score, roc_auc_score, classification_report
from xgboost import XGBClassifier

sys.path.append(str(Path(__file__).parent.parent))

OUTPUT_DIR = Path(__file__).parent.parent / "output"
ML_DIR     = Path(__file__).parent.parent / "ml"


def load_data() -> tuple[np.ndarray, np.ndarray, list[str]]:
    path = OUTPUT_DIR / "team_features.csv"
    df   = pd.read_csv(path)

    drop_cols = ["team_id", "result", "team_size"]
    feature_cols = [c for c in df.columns if c not in drop_cols]

    X = df[feature_cols].values.astype(float)
    y = (df["result"] == "win").astype(int).values

    return X, y, feature_cols


def evaluate_model(name, model, X_train, X_test, y_train, y_test, feature_cols):
    model.fit(X_train, y_train)
    y_pred  = model.predict(X_test)
    y_proba = model.predict_proba(X_test)[:, 1]

    acc = accuracy_score(y_test, y_pred)
    auc = roc_auc_score(y_test, y_proba)

    # 5-fold cross-validation on full dataset
    cv_scores = cross_val_score(model, 
                                np.vstack([X_train, X_test]),
                                np.concatenate([y_train, y_test]),
                                cv=5, scoring="roc_auc")

    print(f"\n{'='*50}")
    print(f"  {name}")
    print(f"{'='*50}")
    print(f"  Test Accuracy : {acc:.4f}")
    print(f"  Test ROC-AUC  : {auc:.4f}")
    print(f"  CV ROC-AUC    : {cv_scores.mean():.4f} ± {cv_scores.std():.4f}")
    print(f"\n{classification_report(y_test, y_pred, target_names=['loss','win'])}")

    # Feature importances
    if hasattr(model, "feature_importances_"):
        importances = model.feature_importances_
        ranked = sorted(zip(feature_cols, importances), key=lambda x: x[1], reverse=True)
        print(f"  Top 10 Features:")
        for feat, imp in ranked[:10]:
            print(f"    {feat:35} {imp:.4f}")

    return auc, model


def main():
    print("Loading team_features.csv...")
    X, y, feature_cols = load_data()
    print(f"Dataset: {X.shape[0]} teams, {X.shape[1]} features")
    print(f"Class balance: {y.sum()} wins / {(1-y).sum()} losses")

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    # --- Random Forest ---
    rf = RandomForestClassifier(
        n_estimators=200,
        max_depth=6,
        min_samples_leaf=5,
        random_state=42,
        n_jobs=-1,
    )
    rf_auc, rf_model = evaluate_model(
        "Random Forest", rf, X_train, X_test, y_train, y_test, feature_cols
    )

    # --- XGBoost ---
    xgb = XGBClassifier(
        n_estimators=200,
        max_depth=4,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        eval_metric="logloss",
        random_state=42,
        verbosity=0,
    )
    xgb_auc, xgb_model = evaluate_model(
        "XGBoost", xgb, X_train, X_test, y_train, y_test, feature_cols
    )

    # --- Save best model ---
    best_name  = "XGBoost" if xgb_auc >= rf_auc else "Random Forest"
    best_model = xgb_model if xgb_auc >= rf_auc else rf_model
    print(f"\n{'='*50}")
    print(f"  Best model: {best_name} (AUC {max(xgb_auc, rf_auc):.4f})")
    print(f"{'='*50}")

    model_path = ML_DIR / "win_predictor.pkl"
    meta_path  = ML_DIR / "win_predictor_meta.json"

    with open(model_path, "wb") as f:
        pickle.dump(best_model, f)

    with open(meta_path, "w") as f:
        json.dump({
            "model":        best_name,
            "auc":          round(max(xgb_auc, rf_auc), 4),
            "feature_cols": feature_cols,
            "n_features":   len(feature_cols),
            "n_samples":    X.shape[0],
        }, f, indent=2)

    print(f"\n  Saved model → ml/win_predictor.pkl")
    print(f"  Saved meta  → ml/win_predictor_meta.json")


if __name__ == "__main__":
    main()