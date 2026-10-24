# Power BI Build Guide – Telecom Churn Analytics

Follow these steps in order to build the full `.pbix` report from the star schema CSVs.  
Estimated time: 60–90 minutes for a first build.

---

## Step 1 – Load the CSV Files

1. Open **Power BI Desktop** → **Get Data → Text/CSV**.
2. Load each file from `data/processed/`:

| File | Table name to use |
|---|---|
| `dim_customer.csv` | `dim_customer` |
| `dim_plan.csv` | `dim_plan` |
| `dim_date.csv` | `dim_date` |
| `fact_billing.csv` | `fact_billing` |
| `fact_usage.csv` | `fact_usage` |

3. After loading each file, click **Transform Data** and verify:
   - `customer_id`, `plan_id`, `month_offset` → **Whole Number**
   - `MonthlyCharges`, `TotalCharges`, `monthly_charge`, `data_gb` → **Decimal Number**
   - `Churn`, `SeniorCitizen`, `PEOTV_Subscription`, `payment_delayed` → **Whole Number**
   - All text columns → **Text**
4. Click **Close & Apply**.

---

## Step 2 – Build the Data Model (Star Schema)

Go to the **Model view** (third icon on the left rail).

### Relationships to create

| From (many side) | Column | To (one side) | Column | Cardinality | Direction |
|---|---|---|---|---|---|
| `fact_billing` | `customer_id` | `dim_customer` | `customer_id` | Many-to-one | Single |
| `fact_billing` | `plan_id` | `dim_plan` | `plan_id` | Many-to-one | Single |
| `fact_billing` | `month_offset` | `dim_date` | `month_offset` | Many-to-one | Single |
| `fact_usage` | `customer_id` | `dim_customer` | `customer_id` | Many-to-one | Single |
| `fact_usage` | `month_offset` | `dim_date` | `month_offset` | Many-to-one | Single |

**How to create each:** Drag the column from the fact table onto the matching column in the dimension table. A line appears — click it to verify the cardinality and direction.

> **Why single direction?** Bidirectional cross-filtering can cause ambiguous paths and unexpected results in DAX measures. Only switch to bidirectional when you have a specific reason (e.g. a many-to-many bridge table).

### Mark dim_date as a Date Table

1. In Model view, click `dim_date`.
2. **Table Tools → Mark as Date Table → Date column: `Date`**.  
   *(If `Date` column doesn't exist: **New Column** → `Date = DATE(dim_date[year], dim_date[month], 1)`)*
3. This activates time intelligence functions (`DATEADD`, `SAMEPERIODLASTYEAR`, etc.).

---

## Step 3 – Add the Measures Table

1. **Modeling → New Table** → paste: `Measures = {}`
2. Delete the auto-created column.
3. Right-click `Measures` in the Fields pane → **New Measure** for each measure in `DAX_measures.md`.
4. Add them in this order (later measures reference earlier ones):
   1. Active Customers
   2. Churn Rate
   3. ARPU
   4. ARPU (Active)
   5. Revenue at Risk
   6. Revenue at Risk %
   7. CLV
   8. Total Revenue (Monthly)
   9. Revenue Previous Month
   10. MoM Revenue Growth

---

## Step 4 – Page 1: Overview

**Purpose:** Single-glance executive summary — what is the churn situation right now?

### Layout (1280 × 720 canvas)

```
┌─────────────────────────────────────────────────────┐
│  [Title: Telecom Churn Analytics – Overview]        │
├─────────┬────────────┬───────────┬──────────┬───────┤
│ Active  │ Churn Rate │   ARPU    │  Rev at  │  CLV  │
│ Cust.   │            │           │  Risk    │       │
│  KPI    │    KPI     │    KPI    │   KPI    │  KPI  │
├─────────┴────────────┴───────────┴──────────┴───────┤
│                                                     │
│   Churn Rate by Contract      Churn by Tenure       │
│   (Clustered Bar)             (Clustered Bar)       │
│                                                     │
├─────────────────────────────────────────────────────┤
│   Revenue at Risk by          Churn Distribution    │
│   Internet Service (Bar)      (Donut chart)         │
└─────────────────────────────────────────────────────┘
```

### Visuals

| Visual | Type | Fields |
|---|---|---|
| Active Customers | KPI card | Value: `[Active Customers]` |
| Churn Rate | KPI card | Value: `[Churn Rate]` → format `0.0%` |
| ARPU | KPI card | Value: `[ARPU]` → format `$#,##0.00` |
| Revenue at Risk | KPI card | Value: `[Revenue at Risk]` → format `$#,##0` |
| CLV | KPI card | Value: `[CLV]` → format `$#,##0` |
| Churn Rate by Contract | Clustered bar | Axis: `dim_customer[Contract]`, Values: `[Churn Rate]` |
| Churn Rate by Tenure | Clustered bar | Axis: `dim_customer[tenure]` (binned 0–12, 13–24 …), Values: `[Churn Rate]` |
| Revenue at Risk by Internet | Bar chart | Axis: `dim_customer[InternetService]`, Values: `[Revenue at Risk]` |
| Churn Distribution | Donut | Legend: `dim_customer[Churn]` (format as Yes/No via conditional column in PQ), Values: COUNTROWS |

### Slicers (top-right corner)
- `dim_customer[Contract]` — dropdown slicer
- `dim_customer[region]` — dropdown slicer
- `dim_date[period_label]` — between slicer (date range)

---

## Step 5 – Page 2: Churn Drivers

**Purpose:** Drill into which factors drive churn — for the retention team and analysts.

### Layout

```
┌───────────────────────────────────────────────────────┐
│  [Title: Churn Drivers]         [Slicers panel]       │
├──────────────────────┬────────────────────────────────┤
│  Churn by Payment    │  Churn Rate Heatmap            │
│  Method (Bar)        │  (Matrix: Contract × Internet) │
├──────────────────────┼────────────────────────────────┤
│  SHAP Feature        │  Complaint Tickets vs Churn    │
│  Importance (image)  │  (Scatter: complaint_tickets   │
│                      │   vs Churn, sized by ARPU)     │
├──────────────────────┴────────────────────────────────┤
│  Top 10 At-Risk Customers (Table with row-level data) │
└───────────────────────────────────────────────────────┘
```

### Visuals

| Visual | Type | Fields |
|---|---|---|
| Churn by Payment Method | Clustered bar | Axis: `dim_customer[PaymentMethod]`, Values: `[Churn Rate]`, sort descending |
| Churn Rate Heatmap | Matrix | Rows: `Contract`, Columns: `InternetService`, Values: `[Churn Rate]`, conditional formatting → color scale |
| SHAP Feature Importance | Image | Insert → Image → `reports/figures/shap_summary.png` |
| Complaint Tickets vs Churn | Scatter | X: `dim_customer[complaint_tickets]`, Y: `[Churn Rate]`, Size: `[ARPU]`, Legend: `dim_customer[Contract]` |
| Top 10 At-Risk Customers | Table | Columns: customer_id, Contract, MonthlyCharges, tenure, complaint_tickets, Churn |

**Setting up the Matrix conditional formatting:**
1. Click the Matrix → select Values field → **Format → Conditional formatting → Background color**.
2. Style: **Color scale** → Minimum = white, Maximum = red (`#C00000`).
3. This creates a heatmap showing which Contract × Internet combinations have the highest churn — the darkest cell is your priority retention segment.

### Slicers
- `dim_customer[InternetService]` — vertical list
- `dim_customer[SeniorCitizen]` — toggle (0/1 or Yes/No)
- `dim_customer[PEOTV_Subscription]` — toggle

---

## Step 6 – Page 3: Revenue

**Purpose:** Revenue trends, ARPU analysis, MoM growth — for the finance/commercial audience.

### Layout

```
┌───────────────────────────────────────────────────────┐
│  [Title: Revenue Analytics]                           │
├──────────────┬──────────────┬───────────────────────  │
│  Total Rev   │  MoM Growth  │  Rev at Risk %          │
│  (KPI card)  │  (KPI card)  │  (KPI card)             │
├──────────────┴──────────────┴───────────────────────  │
│  Monthly Revenue Trend (Line chart)                   │
│  (dim_date[period_label] on axis, Total Revenue)      │
├──────────────────────┬────────────────────────────────┤
│  Revenue by Contract │  ARPU by Internet Service      │
│  + Plan (Stacked bar)│  (Clustered bar)               │
├──────────────────────┴────────────────────────────────┤
│  Revenue at Risk by Region (Filled map or bar)        │
└───────────────────────────────────────────────────────┘
```

### Visuals

| Visual | Type | Fields |
|---|---|---|
| Total Revenue | KPI card | `SUM(fact_billing[monthly_charge])` |
| MoM Revenue Growth | KPI card | `[MoM Revenue Growth]`, format `+0.0%;-0.0%;0.0%` |
| Revenue at Risk % | KPI card | `[Revenue at Risk %]` |
| Monthly Revenue Trend | Line chart | X: `dim_date[period_label]`, Y: `[Total Revenue (Monthly)]`, add constant line for average |
| Revenue by Contract | Stacked bar | Axis: `dim_date[year]`, Legend: `dim_plan[Contract]`, Values: `SUM(fact_billing[monthly_charge])` |
| ARPU by Internet | Bar chart | Axis: `dim_customer[InternetService]`, Values: `[ARPU]` |
| Revenue at Risk by Region | Clustered bar | Axis: `dim_customer[region]`, Values: `[Revenue at Risk]`, sort descending |

**Monthly Revenue Trend tip:**  
Right-click the line chart → **Add further analyses → Average line**. This shows whether revenue is trending above or below the long-run average at a glance.

### Slicers
- `dim_date[year]` — slicer
- `dim_date[quarter]` — slicer
- `dim_plan[Contract]` — dropdown

---

## Step 7 – Page 4: Customer Drill-Through

**Purpose:** Analyst looks up an individual customer to understand their risk profile. Accessible by right-clicking any customer row on the Churn Drivers page → **Drill through → Customer Detail**.

### Setup

1. Create a new page named `Customer Detail`.
2. On this page, in the **Visualizations pane → Drill through** well, drag `dim_customer[customer_id]`.  
   This makes every other page's visuals have a right-click drill-through option to this page.
3. A **Back button** is auto-inserted — keep it.

### Layout

```
┌────────────────────────────────────────────────────────┐
│  [← Back]  Customer Detail                            │
├───────────────────┬────────────────────────────────────┤
│  Customer Profile │  Billing History                   │
│  (Card multi-row) │  (Line chart: month_offset vs      │
│  ID, Contract,    │   monthly_charge)                  │
│  Tenure, Region   │                                    │
├───────────────────┼────────────────────────────────────┤
│  Usage History    │  Risk Summary                      │
│  (Line: data_gb + │  Churn: Yes/No (large card)        │
│   call_minutes)   │  Complaints, PEOTV flag            │
│                   │  Payment delay count               │
└───────────────────┴────────────────────────────────────┘
```

### Visuals

| Visual | Type | Fields |
|---|---|---|
| Customer Profile | Multi-row card | customer_id, Contract, tenure, region, PaymentMethod, MonthlyCharges |
| Billing History | Line chart | X: `dim_date[period_label]` (via fact_billing → dim_date), Y: `SUM(fact_billing[monthly_charge])` |
| Usage History | Line chart with dual axis | X: `dim_date[period_label]`, Y1: `SUM(fact_usage[data_gb])`, Y2: `SUM(fact_usage[call_minutes])` |
| Churn status | Card | `dim_customer[Churn]` — use a conditional column in PQ: `if Churn = 1 then "CHURNED ⚠️" else "Active ✓"` |
| Complaint tickets | Card | `dim_customer[complaint_tickets]` |

---

## Step 8 – Publish and Share

1. **File → Save As** → `powerbi/telecom_churn.pbix`.
2. **Home → Publish** → select your Power BI workspace.
3. On powerbi.com: **Share → Copy link** for a read-only audience link.

---

## Checklist for Interview Demo

Walk through these four talking points when presenting the dashboard:

1. **Data model** — open Model view and trace the star schema. Explain why facts are many-to-one with dimensions and why filters flow from dim → fact (not the reverse).

2. **A DAX measure** — click a KPI card, show the DAX formula bar, and explain one measure (Churn Rate or Revenue at Risk are the best choices — simple but clearly business-linked).

3. **A slicer interaction** — change the Contract slicer and watch all visuals update. Explain this is cross-filtering driven by the data model relationships, not manual filter steps.

4. **Drill-through** — right-click a customer row on Page 2, drill through to Page 4. Explain that this page is context-aware: it shows only that customer's billing and usage history because the drill-through filter propagates through the star schema.
