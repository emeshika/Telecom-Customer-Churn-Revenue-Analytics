# DAX Measures – Telecom Churn Analytics

All measures go into a dedicated **Measures** table (an empty calculated table) so they stay separate from the dimension/fact tables. To create one: **Modeling → New Table** → `Measures = {}`

---

## 1. Active Customers

```dax
Active Customers =
CALCULATE(
    DISTINCTCOUNT( dim_customer[customer_id] ),
    dim_customer[Churn] = 0
)
```

**What it does:** Counts unique customer IDs where the customer has not churned.

**Why CALCULATE:** We need to apply a row-level filter (`Churn = 0`) on top of whatever slicer context is already active on the page. `CALCULATE` modifies the filter context; a plain `COUNTROWS` would ignore that condition.

**Interview point:** Unlike `COUNT`, `DISTINCTCOUNT` is safe if a customer could appear more than once (e.g. after a future model update brings in transaction-level data).

---

## 2. Churn Rate

```dax
Churn Rate =
DIVIDE(
    COUNTROWS( FILTER( dim_customer, dim_customer[Churn] = 1 ) ),
    COUNTROWS( dim_customer ),
    0
)
```

**What it does:** `Churned customers ÷ Total customers`. Returns 0 when the denominator is 0 (third argument to `DIVIDE`) — avoids blank-vs-zero confusion in visuals.

**Why DIVIDE not `/`:** `DIVIDE` handles zero-division gracefully and is the Power BI best practice.

**Format:** Apply `0.0%` format to the measure. In interviews, note that this is a *static* churn rate on the snapshot; a production measure would compare two time periods using time intelligence functions.

---

## 3. ARPU (Average Revenue Per User)

```dax
ARPU =
DIVIDE(
    SUM( dim_customer[MonthlyCharges] ),
    COUNTROWS( dim_customer ),
    0
)
```

**What it does:** Average Monthly Charges per customer in the current filter context.

**Why this matters:** ARPU is the headline KPI for any telco. When sliced by `Contract` or `InternetService`, it shows which plan types are most valuable — driving upsell and pricing strategy.

**Variant – ARPU for active customers only:**

```dax
ARPU (Active) =
DIVIDE(
    CALCULATE( SUM( dim_customer[MonthlyCharges] ), dim_customer[Churn] = 0 ),
    [Active Customers],
    0
)
```

---

## 4. Revenue at Risk

```dax
Revenue at Risk =
CALCULATE(
    SUM( dim_customer[MonthlyCharges] ),
    dim_customer[Churn] = 1
)
```

**What it does:** Sum of monthly charges for customers who have already churned. This is the **monthly revenue already lost** — and the minimum business case for a retention programme.

**Paired measure – Revenue at Risk %:**

```dax
Revenue at Risk % =
DIVIDE( [Revenue at Risk], SUM( dim_customer[MonthlyCharges] ), 0 )
```

**Interview point:** In a real deployment, "at risk" would be *predicted* churners (scored by the ML model), not confirmed churners. Frame this measure as the baseline; the ML model then ranks who to call *before* they leave.

---

## 5. CLV (Customer Lifetime Value)

```dax
CLV =
AVERAGEX(
    dim_customer,
    dim_customer[MonthlyCharges] * dim_customer[tenure]
)
```

**What it does:** For each customer, multiplies their monthly charge by how many months they have been a customer (a simple historical CLV). `AVERAGEX` iterates row-by-row then takes the average across all customers in the filter context.

**Why AVERAGEX not `AVERAGE(dim_customer[TotalCharges])`:** `TotalCharges` in the dataset has some nulls (new customers with zero tenure). Using `MonthlyCharges × tenure` is more robust and exposes the calculation logic clearly in an interview.

**More sophisticated version (with assumed churn probability):**

```dax
CLV (Probabilistic) =
AVERAGEX(
    dim_customer,
    DIVIDE(
        dim_customer[MonthlyCharges],
        [Churn Rate],   -- approximates discount rate via churn probability
        0
    )
)
```
This is the standard telco CLV formula: `Monthly Margin ÷ Churn Rate`. Present this version if the interviewer asks for a forward-looking CLV.

---

## 6. MoM Revenue Growth

This measure uses the `dim_date` table, which has `period_label` (YYYY-MM), `year`, `month`, and `month_offset`.

```dax
Total Revenue (Monthly) =
SUMX(
    fact_billing,
    fact_billing[monthly_charge]
)
```

```dax
Revenue Previous Month =
CALCULATE(
    [Total Revenue (Monthly)],
    DATEADD( dim_date[period_label], -1, MONTH )
)
```

> **Note:** `DATEADD` requires a proper Date column. If `period_label` is text, create a calculated column first:
> ```dax
> dim_date[Date] = DATE( dim_date[year], dim_date[month], 1 )
> ```
> Then mark `dim_date` as a **Date Table** (Table Tools → Mark as Date Table → `Date` column).

```dax
MoM Revenue Growth =
DIVIDE(
    [Total Revenue (Monthly)] - [Revenue Previous Month],
    [Revenue Previous Month],
    0
)
```

**What it does:** Shows how total monthly billing revenue changed versus the prior month.

**Format:** `+0.0%;-0.0%;0.0%` — the three-segment format code shows a `+` sign for positive growth, `-` for decline, and `0.0%` for flat, which reads clearly in a KPI card.

**Interview point:** Time intelligence functions like `DATEADD`, `SAMEPERIODLASTYEAR`, and `PREVIOUSMONTH` only work when Power BI's calendar is activated via a proper Date table. Always explain this step.

---

## Quick Reference Table

| Measure | Formula pattern | Key function |
|---|---|---|
| Active Customers | Filter + DISTINCTCOUNT | `CALCULATE` |
| Churn Rate | Filtered count ÷ total | `DIVIDE`, `FILTER` |
| ARPU | SUM ÷ COUNTROWS | `DIVIDE` |
| Revenue at Risk | Filtered SUM | `CALCULATE` |
| CLV | Row-level multiply, then average | `AVERAGEX` |
| MoM Revenue Growth | Current − Prior ÷ Prior | `DATEADD`, `CALCULATE` |

---

## Formatting Conventions

| Measure type | Format string |
|---|---|
| Percentage | `0.0%` |
| Currency | `$#,##0` or `$#,##0.00` |
| Growth with sign | `+0.0%;-0.0%;0.0%` |
| Integer count | `#,##0` |
