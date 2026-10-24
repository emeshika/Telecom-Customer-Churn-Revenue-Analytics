"""
Reusable model training, evaluation, and SHAP explanation utilities.
Saves model artefacts to models/ and figures to reports/figures/.
"""

import warnings
warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns
import joblib
from pathlib import Path

from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.metrics import (
    classification_report,
    confusion_matrix,
    roc_auc_score,
    roc_curve,
    precision_recall_curve,
    f1_score,
    recall_score,
    precision_score,
)
from xgboost import XGBClassifier
import shap

PROCESSED_PATH = Path(__file__).parent.parent / "data" / "processed"
MODELS_PATH = Path(__file__).parent.parent / "models"
FIGURES_PATH = Path(__file__).parent.parent / "reports" / "figures"

plt.rcParams.update(
    {
        "figure.facecolor": "white",
        "axes.facecolor": "white",
        "axes.spines.top": False,
        "axes.spines.right": False,
        "font.family": "DejaVu Sans",
        "axes.labelsize": 11,
        "axes.titlesize": 13,
    }
)

CAT_FEATURES = [
    "gender", "Partner", "Dependents", "PhoneService", "MultipleLines",
    "InternetService", "OnlineSecurity", "OnlineBackup", "DeviceProtection",
    "TechSupport", "StreamingTV", "StreamingMovies", "Contract",
    "PaperlessBilling", "PaymentMethod", "region",
]
NUM_FEATURES = [
    "SeniorCitizen", "tenure", "MonthlyCharges", "TotalCharges",
    "PEOTV_Subscription", "complaint_tickets",
]


def load_and_prepare() -> tuple[pd.DataFrame, pd.Series, list[str]]:
    df = pd.read_csv(PROCESSED_PATH / "dim_customer.csv")

    # Encode categoricals
    df_enc = df[CAT_FEATURES + NUM_FEATURES].copy()
    le = LabelEncoder()
    for col in CAT_FEATURES:
        df_enc[col] = le.fit_transform(df_enc[col].astype(str))

    feature_cols = CAT_FEATURES + NUM_FEATURES
    X = df_enc[feature_cols]
    y = df["Churn"]
    return X, y, feature_cols


def plot_confusion_matrix(cm: np.ndarray, title: str, fname: str):
    fig, ax = plt.subplots(figsize=(5, 4))
    sns.heatmap(
        cm, annot=True, fmt="d", cmap="Blues", ax=ax,
        xticklabels=["Retained", "Churned"],
        yticklabels=["Retained", "Churned"],
        linewidths=0.5, linecolor="white",
    )
    ax.set_xlabel("Predicted")
    ax.set_ylabel("Actual")
    ax.set_title(title)
    fig.tight_layout()
    fig.savefig(FIGURES_PATH / fname, dpi=150, bbox_inches="tight")
    plt.close(fig)


def plot_roc_curves(models_dict: dict, X_test: pd.DataFrame, y_test: pd.Series):
    """models_dict: {label: fitted_model}"""
    fig, ax = plt.subplots(figsize=(7, 5))
    colors = {"Logistic Regression": "#4472C4", "XGBoost": "#ED7D31"}
    for label, model in models_dict.items():
        proba = model.predict_proba(X_test)[:, 1]
        fpr, tpr, _ = roc_curve(y_test, proba)
        auc = roc_auc_score(y_test, proba)
        ax.plot(fpr, tpr, label=f"{label} (AUC={auc:.3f})", color=colors.get(label, "#666"), linewidth=2)
    ax.plot([0, 1], [0, 1], "k--", linewidth=1, label="Random (AUC=0.500)")
    ax.set_xlabel("False Positive Rate")
    ax.set_ylabel("True Positive Rate")
    ax.set_title("ROC Curves – Logistic Regression vs XGBoost")
    ax.legend(fontsize=10)
    fig.tight_layout()
    fig.savefig(FIGURES_PATH / "roc_curves.png", dpi=150, bbox_inches="tight")
    plt.close(fig)


def evaluate_model(model, X_test: pd.DataFrame, y_test: pd.Series, label: str) -> dict:
    y_pred = model.predict(X_test)
    y_proba = model.predict_proba(X_test)[:, 1]
    return {
        "model": label,
        "recall": round(recall_score(y_test, y_pred), 4),
        "precision": round(precision_score(y_test, y_pred), 4),
        "f1": round(f1_score(y_test, y_pred), 4),
        "roc_auc": round(roc_auc_score(y_test, y_proba), 4),
    }


def train_models() -> dict:
    MODELS_PATH.mkdir(parents=True, exist_ok=True)
    FIGURES_PATH.mkdir(parents=True, exist_ok=True)

    X, y, feature_cols = load_and_prepare()
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    # Scale for logistic regression
    scaler = StandardScaler()
    X_train_sc = scaler.fit_transform(X_train)
    X_test_sc = scaler.transform(X_test)

    print("Training Logistic Regression...")
    lr = LogisticRegression(class_weight="balanced", max_iter=1000, random_state=42)
    lr.fit(X_train_sc, y_train)

    print("Training XGBoost...")
    # scale_pos_weight handles class imbalance: ratio of negative to positive
    neg, pos = (y_train == 0).sum(), (y_train == 1).sum()
    xgb = XGBClassifier(
        scale_pos_weight=neg / pos,
        n_estimators=300,
        max_depth=4,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        random_state=42,
        eval_metric="logloss",
        verbosity=0,
    )
    xgb.fit(X_train, y_train)

    # Evaluation
    metrics = [
        evaluate_model(lr, X_test_sc, y_test, "Logistic Regression"),
        evaluate_model(xgb, X_test, y_test, "XGBoost"),
    ]
    metrics_df = pd.DataFrame(metrics)
    print("\n--- Model Comparison ---")
    print(metrics_df.to_string(index=False))

    # Confusion matrices
    plot_confusion_matrix(
        confusion_matrix(y_test, lr.predict(X_test_sc)),
        "Logistic Regression – Confusion Matrix",
        "cm_logistic_regression.png",
    )
    plot_confusion_matrix(
        confusion_matrix(y_test, xgb.predict(X_test)),
        "XGBoost – Confusion Matrix",
        "cm_xgboost.png",
    )

    # ROC curves
    # Wrap LR to handle scaled vs unscaled X_test
    class ScaledModel:
        def __init__(self, model, scaler):
            self.model = model
            self.scaler = scaler
        def predict_proba(self, X):
            return self.model.predict_proba(self.scaler.transform(X))

    plot_roc_curves(
        {"Logistic Regression": ScaledModel(lr, scaler), "XGBoost": xgb},
        X_test, y_test,
    )

    # SHAP for XGBoost (more interpretable)
    print("\nComputing SHAP values...")
    explainer = shap.TreeExplainer(xgb)
    shap_values = explainer.shap_values(X_test)

    # Global summary plot
    fig, ax = plt.subplots(figsize=(10, 7))
    shap.summary_plot(shap_values, X_test, feature_names=feature_cols, show=False, plot_size=None)
    plt.title("SHAP Feature Importance (XGBoost)", fontsize=13)
    plt.tight_layout()
    plt.savefig(FIGURES_PATH / "shap_summary.png", dpi=150, bbox_inches="tight")
    plt.close()

    # Individual explanation – highest-risk customer in test set
    xgb_probas = xgb.predict_proba(X_test)[:, 1]
    high_risk_idx = int(np.argmax(xgb_probas))
    fig, ax = plt.subplots(figsize=(10, 4))
    shap.waterfall_plot(
        shap.Explanation(
            values=shap_values[high_risk_idx],
            base_values=explainer.expected_value,
            data=X_test.iloc[high_risk_idx].values,
            feature_names=feature_cols,
        ),
        show=False,
    )
    plt.title(f"SHAP Waterfall – Highest-Risk Customer (p={xgb_probas[high_risk_idx]:.2f})", fontsize=11)
    plt.tight_layout()
    plt.savefig(FIGURES_PATH / "shap_waterfall_high_risk.png", dpi=150, bbox_inches="tight")
    plt.close()

    # Save artefacts
    joblib.dump(xgb, MODELS_PATH / "xgboost_churn.joblib")
    joblib.dump(lr, MODELS_PATH / "logistic_regression_churn.joblib")
    joblib.dump(scaler, MODELS_PATH / "scaler.joblib")
    metrics_df.to_csv(MODELS_PATH / "model_metrics.csv", index=False)
    print("\nModels saved to models/")

    return {
        "xgb": xgb,
        "lr": lr,
        "scaler": scaler,
        "metrics": metrics_df,
        "X_test": X_test,
        "y_test": y_test,
        "feature_cols": feature_cols,
    }


if __name__ == "__main__":
    train_models()
