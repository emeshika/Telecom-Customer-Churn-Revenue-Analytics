# Excel Skills Guide – Telecom Churn Analysis

This guide walks through how to rebuild the analysis **manually in Excel** using Power Query, PivotTables, slicers, XLOOKUP, and real pivot charts — so you can demonstrate these skills confidently in interviews.

---

## Part 1 – Power Query: Clean the Raw Data

Power Query is Excel's built-in ETL tool. It records every cleaning step so the workbook is refreshable.

### 1.1 Load the CSV

1. Open a new Excel workbook.  
2. **Data → Get Data → From File → From Text/CSV**  
3. Navigate to `data/processed/dim_customer.csv` → **Load** → choose **Transform Data** (opens Power Query Editor).

### 1.2 Clean column types

In the Power Query Editor:

| Column | Action |
|---|---|
| `tenure`, `SeniorCitizen`, `Churn`, `PEOTV_Subscription`, `complaint_tickets` | Right-click column header → **Change Type → Whole Number** |
| `MonthlyCharges`, `TotalCharges` | Change Type → **Decimal Number** |
| All text columns | Confirm type is **Text** |

### 1.3 Add a Tenure Bucket column

1. **Add Column → Custom Column**, name it `Tenure Bucket`.  
2. Formula:
   ```
   if [tenure] <= 12 then "0–12m"
   else if [tenure] <= 24 then "13–24m"
   else if [tenure] <= 36 then "25–36m"
   else if [tenure] <= 48 then "37–48m"
   else if [tenure] <= 60 then "49–60m"
   else "61–72m"
   ```

### 1.4 Add a Churn Label column

**Add Column → Custom Column**, name it `Churn Label`:
```
if [Churn] = 1 then "Churned" else "Retained"
```

### 1.5 Add Revenue Tier column

```
if [MonthlyCharges] < 30 then "Low (<$30)"
else if [MonthlyCharges] < 70 then "Mid ($30–70)"
else "High (>$70)"
```

### 1.6 Close & Load

**Home → Close & Load To** → choose **Table** → new sheet named `PQ_Data`.

> Every time the source CSV changes, click **Data → Refresh All** and the whole workbook updates automatically.

---

## Part 2 – PivotTables and Slicers

PivotTables summarise data without any formulas — you just drag fields.

### 2.1 Create the first PivotTable: Churn by Contract

1. Click anywhere inside the `PQ_Data` table.  
2. **Insert → PivotTable → New Worksheet** → name the sheet `Pivot_Contract`.  
3. Drag fields:
   - **Rows**: `Contract`
   - **Values**: `customer_id` (Count) → rename to *Total Customers*
   - **Values**: `Churn` (Sum) → rename to *Churned*
4. Add a **Calculated Field** for churn rate:  
   PivotTable Analyze → Fields, Items & Sets → **Calculated Field**  
   Name: `Churn Rate`  
   Formula: `= Churn / customer_id`  
   → Format the result column as Percentage.

### 2.2 Add a Revenue at Risk column

In the same PivotTable, add another value:
- **Values**: `MonthlyCharges` (Sum) → rename to *Total Revenue*
- Create a second Calculated Field named `Revenue at Risk`:  
  *(You can't multiply two fields in a calculated field directly — instead, create a helper column in Power Query: `Revenue_If_Churned = if [Churn] = 1 then [MonthlyCharges] else 0`, then sum that field here.)*

### 2.3 Second PivotTable: Churn by Tenure Bucket

1. **Insert → PivotTable** from `PQ_Data` → new sheet `Pivot_Tenure`.  
2. Rows: `Tenure Bucket` | Values: Count of `customer_id`, Sum of `Churn`.  
3. Right-click the `Tenure Bucket` row labels → **Sort → A to Z** to get chronological order.

### 2.4 Third PivotTable: Revenue Matrix (Contract × Internet)

1. New sheet `Pivot_Revenue_Matrix`.  
2. Rows: `Contract` | Columns: `InternetService` | Values: Sum of `MonthlyCharges`.  
3. This creates the same cross-tab that the `Revenue_Analysis` sheet builds with SUMIFS.

### 2.5 Add Slicers

1. Click any PivotTable → **PivotTable Analyze → Insert Slicer**.  
2. Add slicers for: `Contract`, `InternetService`, `region`, `Churn Label`.  
3. To connect a slicer to **all** PivotTables at once:  
   Right-click the slicer → **Report Connections** → tick every PivotTable.  
4. Now clicking a slicer value filters every table and chart simultaneously.

### 2.6 Pivot Chart

1. Click `Pivot_Contract` PivotTable → **PivotTable Analyze → PivotChart → Clustered Column**.  
2. Format: remove gridlines, add data labels, match brand colours (navy header = `#1F3864`).  
3. The chart updates live when you use the slicers.

---

## Part 3 – XLOOKUP (modern replacement for INDEX/MATCH)

The `Revenue_Analysis` sheet uses `INDEX/MATCH`. Here is the XLOOKUP equivalent.

### Scenario: Look up a customer's contract and monthly charge by Customer ID

**Old formula (INDEX/MATCH):**
```excel
=INDEX(Data!H:H, MATCH(A2, Data!A:A, 0))
```

**New formula (XLOOKUP):**
```excel
=XLOOKUP(A2, Data!A:A, Data!H:H, "Not found")
```

**Return multiple columns at once (XLOOKUP advantage):**
```excel
=XLOOKUP(A2, Data!A:A, Data!H:K, "Not found")
```
This spills Contract, Monthly Charges, Total Charges, PEOTV — four columns — from one formula. You cannot do this with a single INDEX/MATCH.

### Scenario: Fuzzy / approximate match by tenure bucket

```excel
=XLOOKUP(B2, {0,13,25,37,49,61}, {"0–12m","13–24m","25–36m","37–48m","49–60m","61–72m"}, , 1)
```
The `1` at the end means "match next smaller item" — equivalent to INDEX/MATCH with match_type `-1`.

---

## Part 4 – SUMIFS and COUNTIFS (manual versions)

These formulas power the `Churn_Summary` sheet. In a manual workbook you'd type them directly.

### Count churned month-to-month customers
```excel
=COUNTIFS(Data!H:H, "Month-to-month", Data!O:O, 1)
```

### Sum monthly revenue for fiber optic churners
```excel
=SUMIFS(Data!J:J, Data!G:G, "Fiber optic", Data!O:O, 1)
```

### Churn rate for a segment (combine COUNTIFS)
```excel
=COUNTIFS(Data!H:H,"Month-to-month",Data!O:O,1)
 / COUNTIFS(Data!H:H,"Month-to-month")
```

**Tip for interviews:** Always wrap the denominator in `IF(...=0, 0, ...)` or `IFERROR(...)` to avoid division-by-zero errors when a filter produces zero rows.

---

## Part 5 – What-If with Data Tables (Excel native)

The `What_If` sheet uses a formula chain. Excel's built-in **Data Table** does the same thing for a range of inputs automatically.

1. Set up a column of price-change scenarios: `B2:B12` = -20%, -15%, ... +20%.  
2. In `C1` put the formula that calculates new revenue (referencing the single input cell).  
3. Select `B1:C12` → **Data → What-If Analysis → Data Table**  
   - Column input cell: the price-change input cell (e.g. `$C$5`).  
4. Excel fills the table with the revenue for every scenario instantly — no macros needed.

---

## Quick Checklist for Interview Demos

| Skill | Where to find it |
|---|---|
| Power Query refresh + custom column | PQ_Data sheet or a fresh load |
| PivotTable with calculated field | Pivot_Contract sheet |
| Slicers connected to multiple pivots | Any Pivot sheet |
| XLOOKUP multi-column spill | Revenue_Analysis or a new helper sheet |
| SUMIFS / COUNTIFS | Churn_Summary sheet |
| INDEX/MATCH | Revenue_Analysis sheet |
| What-If formula chain | What_If sheet |
| Conditional formatting (color scale, data bar) | Churn_Summary, Data sheets |
| Pivot Chart | Pivot_Contract sheet |
