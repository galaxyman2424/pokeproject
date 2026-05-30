"""
ml/matchup_predictor.py

Matchup predictor — given two teams, predict which side wins.
Constructs paired feature vectors (difference and concatenation) from
the team_features.csv data, linked back to battles via PostgreSQL.

Run with:
    cd ~/pokeproject
    python3 ml/matchup_predictor.py
"""

import sys
import json
import pickle
import numpy as np
import pandas as pd
import psycopg2
from pathlib import Path

from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import accuracy_score, roc_auc_score, classification_report
from xgboost import XGBClassifier

sys.path.append(str(Path(__file__).parent.parent))
from config import DB_CONFIG

OUTPUT_DIR = Path(__file__).parent.parent / "output"
ML_DIR     = Path(__file__).parent.parent / "ml"


def load_team_features():
    df = pd.read_csv(OUTPUT_DIR / "team_features.csv")
    drop_cols    = ["result", "team_size", "team_id"]
    feature_cols = [c for c in df.columns if c not in drop_cols]
    return df.set_index("team_id"), feature_cols


def fetch_battle_pairs():
    conn   = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT
            t1.battle_id,
            t1.team_id AS team_a_id,
            t2.team_id AS team_b_id,
            CASE WHEN t1.result = 'win' THEN 1 ELSE 0 END AS team_a_won
        FROM teams t1
        JOIN teams t2
            ON t1.battle_id = t2.battle_id
            AND t1.player = 'p1'
            AND t2.player = 'p2'
        ORDER BY t1.battle_id
    """)
    rows = cursor.fetchall()
    conn.close()
    return rows


def build_matchup_dataset(pairs, features_df, feature_cols):
    diff_rows   = []
    concat_rows = []
    labels      = []
    valid       = 0
    skipped     = 0

    for battle_id, team_a_id, team_b_id, team_a_won in pairs:
        if team_a_id not in features_df.index or team_b_id not in features_df.index:
            skipped += 1
            continue

        a = features_df.loc[team_a_id][feature_cols].values.astype(float)
        b = features_df.loc[team_b_id][feature_cols].values.astype(float)

        diff_rows.append(a - b)
        concat_rows.append(np.concatenate([a, b]))
        labels.append(team_a_won)
        valid += 1

    print(f"  Valid pairs : {valid}")
    print(f"  Skipped     : {skipped} (team_id not in features)")

    X_diff   = np.array(diff_rows)
    X_concat = np.array(concat_rows)
    y        = np.array(labels)

    return X_diff, X_concat, y


def evaluate_model(name, model, X_train, X_test, y_train, y_test, feature_labels=None):
    model.fit(X_train, y_train)
    y_pred  = model.predict(X_test)
    y_proba = model.predict_proba(X_test)[:, 1]

    acc = accuracy_score(y_test, y_pred)
    auc = roc_auc_score(y_test, y_proba)

    cv_scores = cross_val_score(
        model,
        np.vstack([X_train, X_test]),
        np.concatenate([y_train, y_test]),
        cv=5,
        scoring="roc_auc",
    )

    print(f"\n{'='*50}")
    print(f"  {name}")
    print(f"{'='*50}")
    print(f"  Test Accuracy : {acc:.4f}")
    print(f"  Test ROC-AUC  : {auc:.4f}")
    print(f"  CV ROC-AUC    : {cv_scores.mean():.4f} +/- {cv_scores.std():.4f}")
    print()
    print(classification_report(y_test, y_pred, target_names=["p2 wins", "p1 wins"]))

    if feature_labels and hasattr(model, "feature_importances_"):
        importances = model.feature_importances_
        ranked = sorted(zip(feature_labels, importances), key=lambda x: x[1], reverse=True)
        print(f"  Top 10 Features:")
        for feat, imp in ranked[:10]:
            print(f"    {feat:40} {imp:.4f}")

    return auc, model


def main():
    print("Loading team features...")
    features_df, feature_cols = load_team_features()
    print(f"  {len(features_df)} team vectors loaded, {len(feature_cols)} features each")

    print("\nFetching battle pairs from database...")
    pairs = fetch_battle_pairs()
    print(f"  {len(pairs)} battles fetched")

    print("\nBuilding matchup dataset...")
    X_diff, X_concat, y = build_matchup_dataset(pairs, features_df, feature_cols)
    print(f"  Diff vector shape   : {X_diff.shape}")
    print(f"  Concat vector shape : {X_concat.shape}")
    print(f"  Class balance       : {y.sum()} p1 wins / {(1-y).sum()} p2 wins")

    # --- Difference vector models ---
    print("\n\n--- DIFFERENCE VECTORS (A - B) ---")
    diff_labels = [f"diff_{c}" for c in feature_cols]

    X_tr, X_te, y_tr, y_te = train_test_split(
        X_diff, y, test_size=0.2, random_state=42, stratify=y
    )

    rf_diff = RandomForestClassifier(
        n_estimators=200, max_depth=6, min_samples_leaf=5,
        random_state=42, n_jobs=-1
    )
    rf_diff_auc, rf_diff_model = evaluate_model(
        "Random Forest (diff)", rf_diff, X_tr, X_te, y_tr, y_te, diff_labels
    )

    xgb_diff = XGBClassifier(
        n_estimators=200, max_depth=4, learning_rate=0.05,
        subsample=0.8, colsample_bytree=0.8,
        eval_metric="logloss", random_state=42, verbosity=0
    )
    xgb_diff_auc, xgb_diff_model = evaluate_model(
        "XGBoost (diff)", xgb_diff, X_tr, X_te, y_tr, y_te, diff_labels
    )

    # --- Concatenation vector models ---
    print("\n\n--- CONCATENATION VECTORS (A || B) ---")
    concat_labels = [f"a_{c}" for c in feature_cols] + [f"b_{c}" for c in feature_cols]

    X_tr2, X_te2, y_tr2, y_te2 = train_test_split(
        X_concat, y, test_size=0.2, random_state=42, stratify=y
    )

    rf_concat = RandomForestClassifier(
        n_estimators=200, max_depth=6, min_samples_leaf=5,
        random_state=42, n_jobs=-1
    )
    rf_concat_auc, rf_concat_model = evaluate_model(
        "Random Forest (concat)", rf_concat, X_tr2, X_te2, y_tr2, y_te2, concat_labels
    )

    xgb_concat = XGBClassifier(
        n_estimators=200, max_depth=4, learning_rate=0.05,
        subsample=0.8, colsample_bytree=0.8,
        eval_metric="logloss", random_state=42, verbosity=0
    )
    xgb_concat_auc, xgb_concat_model = evaluate_model(
        "XGBoost (concat)", xgb_concat, X_tr2, X_te2, y_tr2, y_te2, concat_labels
    )

    # --- Save best model ---
    results = [
        ("RF diff",     rf_diff_auc,     rf_diff_model,     "diff"),
        ("XGB diff",    xgb_diff_auc,    xgb_diff_model,    "diff"),
        ("RF concat",   rf_concat_auc,   rf_concat_model,   "concat"),
        ("XGB concat",  xgb_concat_auc,  xgb_concat_model,  "concat"),
    ]
    best_name, best_auc, best_model, best_mode = max(results, key=lambda x: x[1])

    print(f"\n{'='*50}")
    print(f"  Best: {best_name} (AUC {best_auc:.4f}, mode={best_mode})")
    print(f"{'='*50}")

    model_path = ML_DIR / "matchup_predictor.pkl"
    meta_path  = ML_DIR / "matchup_predictor_meta.json"

    with open(model_path, "wb") as f:
        pickle.dump(best_model, f)

    with open(meta_path, "w") as f:
        json.dump({
            "model":        best_name,
            "auc":          round(best_auc, 4),
            "mode":         best_mode,
            "feature_cols": feature_cols,
            "n_features":   len(feature_cols),
            "n_samples":    len(y),
        }, f, indent=2)

    print(f"\n  Saved model → ml/matchup_predictor.pkl")
    print(f"  Saved meta  → ml/matchup_predictor_meta.json")


if __name__ == "__main__":
    main()