"""
Reusable EDA functions for the Telecom Churn project.
All chart functions save figures to reports/figures/ and return the Axes object.
"""

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")  # non-interactive backend for script execution
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import seaborn as sns
from pathlib import Path

FIGURES_PATH = Path(__file__).parent.parent / "reports" / "figures"
PROCESSED_PATH = Path(__file__).parent.parent / "data" / "processed"

PALETTE_CHURN = {"Retained": "#2196F3", "Churned": "#F44336"}
PALETTE_BAR = "#4472C4"
PALETTE_RISK = "#E53935"

plt.rcParams.update(
    {
        "figure.facecolor": "white",
        "axes.facecolor": "white",
        "axes.spines.top": False,
        "axes.spines.right": False,
        "font.family": "DejaVu Sans",
        "axes.labelsize": 11,
        "axes.titlesize": 13,
        "xtick.labelsize": 10,
        "ytick.labelsize": 10,
    }
)


def load_data() -> pd.DataFrame:
    df = pd.read_csv(PROCESSED_PATH / "dim_customer.csv")
    return df


def churn_rate_by(df: pd.DataFrame, col: str, label: str, fname: str, figsize=(9, 5), rotate=0):
    rates = (
        df.groupby(col)["Churn"]
        .agg(["mean", "sum", "count"])
        .rename(columns={"mean": "churn_rate", "sum": "churned", "count": "total"})
        .sort_values("churn_rate", ascending=False)
        .reset_index()
    )
    rates["churn_rate_pct"] = rates["churn_rate"] * 100

    fig, ax = plt.subplots(figsize=figsize)
    bars = ax.bar(rates[col], rates["churn_rate_pct"], color=PALETTE_BAR, edgecolor="white")
    ax.axhline(df["Churn"].mean() * 100, color="#E53935", linestyle="--", linewidth=1.5, label=f"Overall avg ({df['Churn'].mean()*100:.1f}%)")
    for bar, row in zip(bars, rates.itertuples()):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.5, f"{row.churn_rate_pct:.1f}%", ha="center", va="bottom", fontsize=9, color="#333")
    ax.set_xlabel(label)
    ax.set_ylabel("Churn Rate (%)")
    ax.set_title(f"Churn Rate by {label}")
    ax.legend(fontsize=9)
    if rotate:
        plt.xticks(rotation=rotate, ha="right")
    fig.tight_layout()
    FIGURES_PATH.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIGURES_PATH / fname, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return rates


def churn_by_tenure(df: pd.DataFrame):
    bins = [0, 12, 24, 36, 48, 60, 72]
    labels = ["0–12m", "13–24m", "25–36m", "37–48m", "49–60m", "61–72m"]
    df = df.copy()
    df["tenure_bucket"] = pd.cut(df["tenure"], bins=bins, labels=labels, right=True)
    rates = (
        df.groupby("tenure_bucket", observed=True)["Churn"]
        .agg(["mean", "count"])
        .rename(columns={"mean": "churn_rate", "count": "total"})
        .reset_index()
    )
    rates["churn_rate_pct"] = rates["churn_rate"] * 100

    fig, ax = plt.subplots(figsize=(9, 5))
    bars = ax.bar(rates["tenure_bucket"].astype(str), rates["churn_rate_pct"], color=PALETTE_BAR, edgecolor="white")
    ax.axhline(df["Churn"].mean() * 100, color="#E53935", linestyle="--", linewidth=1.5, label=f"Overall avg ({df['Churn'].mean()*100:.1f}%)")
    for bar, row in zip(bars, rates.itertuples()):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.5, f"{row.churn_rate_pct:.1f}%", ha="center", va="bottom", fontsize=9)
    ax.set_xlabel("Tenure Bucket")
    ax.set_ylabel("Churn Rate (%)")
    ax.set_title("Churn Rate by Tenure")
    ax.legend(fontsize=9)
    fig.tight_layout()
    fig.savefig(FIGURES_PATH / "churn_by_tenure.png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    return rates


def revenue_at_risk(df: pd.DataFrame) -> pd.DataFrame:
    """Monthly revenue at risk = MonthlyCharges * Churn for churned customers per segment."""
    segments = ["Contract", "InternetService", "PaymentMethod"]
    results = []
    for seg in segments:
        r = (
            df.groupby(seg)
            .apply(
                lambda g: pd.Series(
                    {
                        "total_monthly_revenue": g["MonthlyCharges"].sum(),
                        "at_risk_revenue": g.loc[g["Churn"] == 1, "MonthlyCharges"].sum(),
                        "churn_rate": g["Churn"].mean(),
                    }
                ),
                include_groups=False,
            )
            .reset_index()
            .rename(columns={seg: "segment_value"})
        )
        r["segment"] = seg
        results.append(r)
    risk_df = pd.concat(results, ignore_index=True)

    fig, ax = plt.subplots(figsize=(11, 6))
    colors = {"Contract": "#4472C4", "InternetService": "#ED7D31", "PaymentMethod": "#A9D18E"}
    for _, grp in risk_df.groupby("segment"):
        seg_name = grp["segment"].iloc[0]
        x = grp["segment_value"].astype(str)
        ax.barh(x, grp["at_risk_revenue"], color=colors.get(seg_name, PALETTE_RISK), alpha=0.85, label=seg_name)
    ax.set_xlabel("Monthly Revenue at Risk ($)")
    ax.set_title("Monthly Revenue at Risk by Segment")
    ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"${x:,.0f}"))
    ax.legend(fontsize=9)
    fig.tight_layout()
    fig.savefig(FIGURES_PATH / "revenue_at_risk.png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    return risk_df


def monthly_revenue_trend(fact_billing: pd.DataFrame, dim_date: pd.DataFrame):
    merged = fact_billing.merge(dim_date, on="month_offset")
    monthly = (
        merged.groupby("period_label")["revenue"]
        .sum()
        .reset_index()
        .sort_values("period_label")
    )
    fig, ax = plt.subplots(figsize=(12, 5))
    ax.plot(monthly["period_label"], monthly["revenue"], marker="o", color=PALETTE_BAR, linewidth=2)
    ax.fill_between(monthly["period_label"], monthly["revenue"], alpha=0.15, color=PALETTE_BAR)
    ax.set_xlabel("Month")
    ax.set_ylabel("Total Revenue ($)")
    ax.set_title("Monthly Revenue Trend (Synthetic History)")
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"${x:,.0f}"))
    plt.xticks(rotation=45, ha="right")
    fig.tight_layout()
    fig.savefig(FIGURES_PATH / "monthly_revenue_trend.png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    return monthly


def churn_distribution_pie(df: pd.DataFrame):
    counts = df["Churn"].value_counts()
    labels = ["Retained", "Churned"]
    sizes = [counts.get(0, 0), counts.get(1, 0)]
    colors = [PALETTE_CHURN["Retained"], PALETTE_CHURN["Churned"]]

    fig, ax = plt.subplots(figsize=(6, 6))
    wedges, texts, autotexts = ax.pie(
        sizes, labels=labels, colors=colors, autopct="%1.1f%%",
        startangle=90, pctdistance=0.75,
        wedgeprops={"edgecolor": "white", "linewidth": 2},
    )
    for at in autotexts:
        at.set_fontsize(12)
        at.set_fontweight("bold")
    ax.set_title("Overall Churn Distribution", fontsize=14)
    fig.tight_layout()
    fig.savefig(FIGURES_PATH / "churn_distribution.png", dpi=150, bbox_inches="tight")
    plt.close(fig)


def run_all_eda():
    FIGURES_PATH.mkdir(parents=True, exist_ok=True)
    df = load_data()
    fact_billing = pd.read_csv(PROCESSED_PATH / "fact_billing.csv")
    dim_date = pd.read_csv(PROCESSED_PATH / "dim_date.csv")

    print("Generating churn distribution...")
    churn_distribution_pie(df)

    print("Generating churn by contract...")
    churn_rate_by(df, "Contract", "Contract Type", "churn_by_contract.png")

    print("Generating churn by tenure...")
    churn_by_tenure(df)

    print("Generating churn by payment method...")
    churn_rate_by(df, "PaymentMethod", "Payment Method", "churn_by_payment.png", rotate=30)

    print("Generating churn by internet service...")
    churn_rate_by(df, "InternetService", "Internet Service", "churn_by_internet.png")

    print("Generating churn by region...")
    churn_rate_by(df, "region", "Region", "churn_by_region.png", rotate=30)

    print("Generating revenue at risk...")
    risk_df = revenue_at_risk(df)
    total_risk = risk_df["at_risk_revenue"].sum()
    print(f"  Total monthly revenue at risk: ${total_risk:,.0f}")

    print("Generating monthly revenue trend...")
    monthly_revenue_trend(fact_billing, dim_date)

    print(f"\nAll figures saved to {FIGURES_PATH}")
    return df


if __name__ == "__main__":
    run_all_eda()
