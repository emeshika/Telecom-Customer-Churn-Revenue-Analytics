"""
Generate synthetic supplementary data for the IBM Telco Customer Churn dataset.

Assumptions
-----------
- Billing history: 12–24 months per customer. Customers with tenure < 12 months
  get history equal to their tenure months only.
- Monthly charge variation: ±5% random noise around the customer's MonthlyCharges.
- Payment delays: Modelled as a Bernoulli draw. Month-to-month customers have a
  10% chance of delay per month; one-year contracts 5%; two-year contracts 2%.
- Complaint tickets: Poisson(λ) over the history window. Churned customers have
  λ=0.3/month; non-churned have λ=0.05/month. Reflects real telco complaint patterns.
- Data usage (GB/month): Normal(μ, σ). Fiber optic customers: μ=45 GB; DSL: μ=20 GB;
  No internet: μ=0 GB (set to 0). σ = μ * 0.3. Clipped at 0.
- Call minutes/month: Uniform[50, 600] for all customers, independent of plan.
- PEOTV subscription flag: 20% of customers subscribe (reflects SLT-PEOTV-style
  bundled TV). Customers without internet service cannot have PEOTV (set to 0).
- Random seed: 42 throughout for full reproducibility.
"""

import numpy as np
import pandas as pd
from pathlib import Path

SEED = 42
rng = np.random.default_rng(SEED)

RAW_PATH = Path(__file__).parent.parent / "data" / "raw" / "Telco-Customer-Churn.csv"
PROCESSED_PATH = Path(__file__).parent.parent / "data" / "processed"


def load_base() -> pd.DataFrame:
    df = pd.read_csv(RAW_PATH)
    df.columns = df.columns.str.strip()
    df["TotalCharges"] = pd.to_numeric(df["TotalCharges"], errors="coerce")
    df["TotalCharges"] = df["TotalCharges"].fillna(df["MonthlyCharges"])
    df["Churn"] = (df["Churn"] == "Yes").astype(int)
    return df


def add_peotv(df: pd.DataFrame) -> pd.DataFrame:
    has_internet = df["InternetService"] != "No"
    draw = rng.random(len(df)) < 0.20
    df["PEOTV_Subscription"] = (has_internet & draw).astype(int)
    return df


def build_billing_history(df: pd.DataFrame) -> pd.DataFrame:
    """Return long-format billing history: one row per (customer, month)."""
    rows = []
    delay_prob = {"Month-to-month": 0.10, "One year": 0.05, "Two year": 0.02}

    for _, cust in df.iterrows():
        n_months = min(
            int(rng.integers(12, 25)),
            max(int(cust["tenure"]), 1),
        )
        base_charge = float(cust["MonthlyCharges"])
        d_prob = delay_prob.get(cust["Contract"], 0.05)

        noise = rng.normal(1.0, 0.05, n_months)
        charges = np.clip(base_charge * noise, 0, None)
        delays = rng.random(n_months) < d_prob
        # Month index 1 = most recent month
        for i in range(1, n_months + 1):
            rows.append(
                {
                    "customerID": cust["customerID"],
                    "month_offset": i,
                    "monthly_charge": round(charges[i - 1], 2),
                    "payment_delayed": int(delays[i - 1]),
                }
            )

    return pd.DataFrame(rows)


def build_usage_history(df: pd.DataFrame) -> pd.DataFrame:
    """Return long-format usage: one row per (customer, month)."""
    data_means = {"Fiber optic": 45.0, "DSL": 20.0, "No": 0.0}
    rows = []

    for _, cust in df.iterrows():
        n_months = min(
            int(rng.integers(12, 25)),
            max(int(cust["tenure"]), 1),
        )
        internet = cust["InternetService"]
        mu = data_means.get(internet, 0.0)
        sigma = mu * 0.3 if mu > 0 else 0.0

        data_gb = (
            np.clip(rng.normal(mu, sigma, n_months), 0, None)
            if mu > 0
            else np.zeros(n_months)
        )
        call_mins = rng.uniform(50, 600, n_months)

        for i in range(1, n_months + 1):
            rows.append(
                {
                    "customerID": cust["customerID"],
                    "month_offset": i,
                    "data_gb": round(data_gb[i - 1], 2),
                    "call_minutes": round(call_mins[i - 1], 1),
                }
            )

    return pd.DataFrame(rows)


def build_complaints(df: pd.DataFrame) -> pd.DataFrame:
    """Return one row per customer with total complaint tickets."""
    lam_map = {1: 0.30, 0: 0.05}  # churned → higher complaint rate
    rows = []
    for _, cust in df.iterrows():
        n_months = min(
            int(rng.integers(12, 25)),
            max(int(cust["tenure"]), 1),
        )
        lam = lam_map.get(int(cust["Churn"]), 0.05) * n_months
        tickets = int(rng.poisson(lam))
        rows.append({"customerID": cust["customerID"], "complaint_tickets": tickets})
    return pd.DataFrame(rows)


def main():
    PROCESSED_PATH.mkdir(parents=True, exist_ok=True)
    print("Loading base dataset...")
    df = load_base()
    df = add_peotv(df)
    print(f"  {len(df):,} customers loaded.")

    print("Generating billing history...")
    billing_hist = build_billing_history(df)
    billing_hist.to_csv(PROCESSED_PATH / "billing_history.csv", index=False)
    print(f"  {len(billing_hist):,} billing rows written.")

    print("Generating usage history...")
    usage_hist = build_usage_history(df)
    usage_hist.to_csv(PROCESSED_PATH / "usage_history.csv", index=False)
    print(f"  {len(usage_hist):,} usage rows written.")

    print("Generating complaint data...")
    complaints = build_complaints(df)

    # Merge complaints back onto main df
    df = df.merge(complaints, on="customerID", how="left")

    # Save enriched base for downstream processing
    df.to_csv(PROCESSED_PATH / "customers_enriched.csv", index=False)
    print(f"  Enriched customer file saved ({len(df):,} rows).")
    print("Done. Run src/process_data.py next to build star schema tables.")


if __name__ == "__main__":
    main()
