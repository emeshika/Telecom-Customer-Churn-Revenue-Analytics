"""
Build a star schema from the enriched Telco customer data.

Schema
------
dim_customer   – one row per customer (demographics + plan info)
dim_plan       – one row per unique plan combination
dim_date       – one row per calendar month in the history window
fact_billing   – monthly billing facts per customer
fact_usage     – monthly usage facts per customer

All tables saved to data/processed/ as UTF-8 CSVs.
Run after src/generate_synthetic.py has been executed.
"""

import pandas as pd
from pathlib import Path

PROCESSED_PATH = Path(__file__).parent.parent / "data" / "processed"


def load_inputs():
    customers = pd.read_csv(PROCESSED_PATH / "customers_enriched.csv")
    billing_hist = pd.read_csv(PROCESSED_PATH / "billing_history.csv")
    usage_hist = pd.read_csv(PROCESSED_PATH / "usage_history.csv")
    return customers, billing_hist, usage_hist


def build_dim_customer(customers: pd.DataFrame) -> pd.DataFrame:
    cols = [
        "customerID",
        "gender",
        "SeniorCitizen",
        "Partner",
        "Dependents",
        "tenure",
        "PhoneService",
        "MultipleLines",
        "InternetService",
        "OnlineSecurity",
        "OnlineBackup",
        "DeviceProtection",
        "TechSupport",
        "StreamingTV",
        "StreamingMovies",
        "PEOTV_Subscription",
        "Contract",
        "PaperlessBilling",
        "PaymentMethod",
        "MonthlyCharges",
        "TotalCharges",
        "Churn",
        "complaint_tickets",
    ]
    dim = customers[cols].copy()
    dim.rename(columns={"customerID": "customer_id"}, inplace=True)
    # Derive region as a synthetic field (not in original data)
    # Assign regions proportionally to simulate a Sri Lanka-style telco footprint
    regions = [
        "Western", "Central", "Southern", "Northern",
        "Eastern", "North-Western", "North-Central",
        "Uva", "Sabaragamuwa",
    ]
    weights = [0.30, 0.12, 0.12, 0.08, 0.08, 0.10, 0.07, 0.07, 0.06]
    rng = pd.core.common.np.random.default_rng(42)
    dim["region"] = rng.choice(regions, size=len(dim), p=weights)
    return dim


def build_dim_plan(customers: pd.DataFrame) -> pd.DataFrame:
    plan_cols = ["Contract", "InternetService", "PhoneService", "PEOTV_Subscription"]
    dim = (
        customers[plan_cols]
        .drop_duplicates()
        .reset_index(drop=True)
        .reset_index()
        .rename(columns={"index": "plan_id"})
    )
    dim["plan_id"] = dim["plan_id"] + 1  # 1-based
    # Derive a human-readable plan name
    def plan_name(row):
        parts = [row["Contract"], row["InternetService"]]
        if row["PEOTV_Subscription"] == 1:
            parts.append("PEOTV")
        return " | ".join(parts)

    dim["plan_name"] = dim.apply(plan_name, axis=1)
    return dim


def build_dim_date(billing_hist: pd.DataFrame) -> pd.DataFrame:
    """
    month_offset 1 = most recent month (Oct 2024).
    We backfill from a reference date so the calendar makes sense.
    """
    import calendar

    reference_year, reference_month = 2024, 10
    max_offset = billing_hist["month_offset"].max()

    rows = []
    for offset in range(1, max_offset + 1):
        # offset 1 → Oct 2024, offset 2 → Sep 2024, ...
        total_months_back = offset - 1
        year = reference_year
        month = reference_month - total_months_back
        while month <= 0:
            month += 12
            year -= 1
        rows.append(
            {
                "month_offset": offset,
                "year": year,
                "month": month,
                "month_name": calendar.month_abbr[month],
                "quarter": (month - 1) // 3 + 1,
                "period_label": f"{year}-{month:02d}",
            }
        )
    return pd.DataFrame(rows)


def build_fact_billing(
    customers: pd.DataFrame,
    billing_hist: pd.DataFrame,
    dim_plan: pd.DataFrame,
) -> pd.DataFrame:
    plan_lookup = customers[
        ["customerID", "Contract", "InternetService", "PhoneService", "PEOTV_Subscription"]
    ].merge(dim_plan, on=["Contract", "InternetService", "PhoneService", "PEOTV_Subscription"])

    fact = billing_hist.merge(
        plan_lookup[["customerID", "plan_id"]],
        on="customerID",
        how="left",
    )
    fact.rename(columns={"customerID": "customer_id"}, inplace=True)
    fact = fact[["customer_id", "plan_id", "month_offset", "monthly_charge", "payment_delayed"]]
    fact["revenue"] = fact["monthly_charge"]  # alias for clarity in dashboards
    return fact


def build_fact_usage(usage_hist: pd.DataFrame) -> pd.DataFrame:
    fact = usage_hist.rename(columns={"customerID": "customer_id"})
    return fact[["customer_id", "month_offset", "data_gb", "call_minutes"]]


def main():
    print("Loading processed inputs...")
    customers, billing_hist, usage_hist = load_inputs()

    print("Building dim_customer...")
    dim_customer = build_dim_customer(customers)
    dim_customer.to_csv(PROCESSED_PATH / "dim_customer.csv", index=False)
    print(f"  {len(dim_customer):,} rows")

    print("Building dim_plan...")
    dim_plan = build_dim_plan(customers)
    dim_plan.to_csv(PROCESSED_PATH / "dim_plan.csv", index=False)
    print(f"  {len(dim_plan):,} plan combinations")

    print("Building dim_date...")
    dim_date = build_dim_date(billing_hist)
    dim_date.to_csv(PROCESSED_PATH / "dim_date.csv", index=False)
    print(f"  {len(dim_date):,} date periods")

    print("Building fact_billing...")
    fact_billing = build_fact_billing(customers, billing_hist, dim_plan)
    fact_billing.to_csv(PROCESSED_PATH / "fact_billing.csv", index=False)
    print(f"  {len(fact_billing):,} billing rows")

    print("Building fact_usage...")
    fact_usage = build_fact_usage(usage_hist)
    fact_usage.to_csv(PROCESSED_PATH / "fact_usage.csv", index=False)
    print(f"  {len(fact_usage):,} usage rows")

    print("\nStar schema tables written to data/processed/")
    print("Tables: dim_customer, dim_plan, dim_date, fact_billing, fact_usage")


if __name__ == "__main__":
    main()
