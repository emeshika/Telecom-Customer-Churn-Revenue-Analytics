"""
Build excel/churn_analysis.xlsx with openpyxl.

Sheets
------
1. Data            – full dim_customer table, styled, filtered
2. Churn_Summary   – COUNTIFS/SUMIFS pivot-style tables by segment
3. Revenue_Analysis– SUMIFS + INDEX/MATCH formula examples
4. What_If         – price-change scenario with live formula chain
5. Dashboard       – BarChart + PieChart driven from Churn_Summary
"""

import pandas as pd
import numpy as np
from pathlib import Path
from openpyxl import Workbook
from openpyxl.styles import (
    Font, PatternFill, Alignment, Border, Side, GradientFill,
    numbers,
)
from openpyxl.styles.numbers import FORMAT_PERCENTAGE_00, FORMAT_NUMBER_COMMA_SEPARATED1
from openpyxl.utils import get_column_letter, quote_sheetname
from openpyxl.utils.dataframe import dataframe_to_rows
from openpyxl.formatting.rule import (
    ColorScaleRule, DataBarRule, CellIsRule, FormulaRule,
)
from openpyxl.chart import BarChart, PieChart, Reference
from openpyxl.chart.series import DataPoint
from openpyxl.worksheet.datavalidation import DataValidation

PROCESSED = Path(__file__).parent.parent / "data" / "processed"
EXCEL_DIR = Path(__file__).parent.parent / "excel"

# ── colour palette ────────────────────────────────────────────────────────────
C_HEADER     = "1F3864"   # dark navy
C_HEADER_TXT = "FFFFFF"
C_ALT_ROW    = "EBF0FA"   # light blue-grey
C_CHURN_RED  = "F8CECC"
C_CHURN_GRN  = "D5E8D4"
C_ACCENT     = "2E75B6"
C_GOLD       = "FFC000"
C_LIGHT_GOLD = "FFF2CC"

# ── helpers ───────────────────────────────────────────────────────────────────
def hdr_font():  return Font(bold=True, color=C_HEADER_TXT, size=11)
def hdr_fill():  return PatternFill("solid", fgColor=C_HEADER)
def alt_fill():  return PatternFill("solid", fgColor=C_ALT_ROW)
def accent_fill(): return PatternFill("solid", fgColor=C_ACCENT)
def gold_fill():   return PatternFill("solid", fgColor=C_GOLD)
def thin_border():
    s = Side(style="thin", color="BFBFBF")
    return Border(left=s, right=s, top=s, bottom=s)
def center(): return Alignment(horizontal="center", vertical="center", wrap_text=True)
def right():  return Alignment(horizontal="right", vertical="center")

def style_header_row(ws, row_num, max_col):
    for col in range(1, max_col + 1):
        cell = ws.cell(row=row_num, column=col)
        cell.font  = hdr_font()
        cell.fill  = hdr_fill()
        cell.alignment = center()
        cell.border = thin_border()

def set_col_widths(ws, widths: dict):
    for col_letter, w in widths.items():
        ws.column_dimensions[col_letter].width = w


# ═════════════════════════════════════════════════════════════════════════════
# SHEET 1 – Data
# ═════════════════════════════════════════════════════════════════════════════
def build_data_sheet(wb: Workbook, df: pd.DataFrame):
    ws = wb.active
    ws.title = "Data"

    display_cols = [
        "customer_id", "gender", "SeniorCitizen", "Partner", "Dependents",
        "tenure", "InternetService", "Contract", "PaymentMethod",
        "MonthlyCharges", "TotalCharges", "PEOTV_Subscription",
        "complaint_tickets", "region", "Churn",
    ]
    data = df[display_cols].copy()
    data.rename(columns={
        "customer_id": "Customer ID", "SeniorCitizen": "Senior",
        "InternetService": "Internet", "MonthlyCharges": "Monthly ($)",
        "TotalCharges": "Total ($)", "PEOTV_Subscription": "PEOTV",
        "complaint_tickets": "Complaints",
    }, inplace=True)

    headers = list(data.columns)
    ws.append(headers)
    style_header_row(ws, 1, len(headers))
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = f"A1:{get_column_letter(len(headers))}1"

    for r_idx, row in enumerate(data.itertuples(index=False), start=2):
        for c_idx, val in enumerate(row, start=1):
            cell = ws.cell(row=r_idx, column=c_idx, value=val)
            cell.border = thin_border()
            cell.alignment = Alignment(vertical="center")
            if r_idx % 2 == 0:
                cell.fill = alt_fill()

    # Conditional formatting: Churn column (column O = 15)
    churn_col = get_column_letter(len(headers))
    ws.conditional_formatting.add(
        f"{churn_col}2:{churn_col}{len(data)+1}",
        CellIsRule(operator="equal", formula=["1"],
                   fill=PatternFill("solid", fgColor=C_CHURN_RED)),
    )
    ws.conditional_formatting.add(
        f"{churn_col}2:{churn_col}{len(data)+1}",
        CellIsRule(operator="equal", formula=["0"],
                   fill=PatternFill("solid", fgColor=C_CHURN_GRN)),
    )

    # Color scale on Monthly ($) column
    mc_col = headers.index("Monthly ($)") + 1
    mc_letter = get_column_letter(mc_col)
    ws.conditional_formatting.add(
        f"{mc_letter}2:{mc_letter}{len(data)+1}",
        ColorScaleRule(
            start_type="min", start_color="FFFFFF",
            end_type="max",   end_color="2E75B6",
        ),
    )

    col_widths = {
        "A": 14, "B": 8, "C": 7, "D": 8, "E": 11,
        "F": 8,  "G": 14, "H": 17, "I": 22,
        "J": 12, "K": 12, "L": 7, "M": 12, "N": 14, "O": 7,
    }
    set_col_widths(ws, col_widths)
    ws.row_dimensions[1].height = 30

    return ws, len(data)


# ═════════════════════════════════════════════════════════════════════════════
# SHEET 2 – Churn_Summary  (COUNTIFS / SUMIFS formulas)
# ═════════════════════════════════════════════════════════════════════════════
def build_churn_summary(wb: Workbook, df: pd.DataFrame, data_rows: int):
    ws = wb.create_sheet("Churn_Summary")
    DATA = "Data"
    MAX_ROW = data_rows + 1  # +1 for header

    # Helper: column letters on Data sheet (1-based → letter)
    col_map = {
        "Contract": "H", "Internet": "G", "PaymentMethod": "I",
        "Churn": "O", "Monthly": "J", "Region": "N",
        "Tenure": "F", "Senior": "C",
    }

    def countifs_churn(seg_col, seg_val):
        return (
            f"=COUNTIFS('{DATA}'!{seg_col}$2:{seg_col}${MAX_ROW},"
            f"\"{seg_val}\","
            f"'{DATA}'!{col_map['Churn']}$2:{col_map['Churn']}${MAX_ROW},1)"
        )

    def countifs_total(seg_col, seg_val):
        return (
            f"=COUNTIFS('{DATA}'!{seg_col}$2:{seg_col}${MAX_ROW},"
            f"\"{seg_val}\")"
        )

    def sumifs_rev(seg_col, seg_val, churn=1):
        churn_clause = (
            f",'{DATA}'!{col_map['Churn']}$2:{col_map['Churn']}${MAX_ROW},{churn}"
            if churn is not None else ""
        )
        return (
            f"=SUMIFS('{DATA}'!{col_map['Monthly']}$2:{col_map['Monthly']}${MAX_ROW},"
            f"'{DATA}'!{seg_col}$2:{seg_col}${MAX_ROW},"
            f"\"{seg_val}\"{churn_clause})"
        )

    # ── Section titles ────────────────────────────────────────────────────────
    sections = [
        ("Contract Type",  col_map["Contract"],     ["Month-to-month", "One year", "Two year"]),
        ("Internet Service", col_map["Internet"],   ["Fiber optic", "DSL", "No"]),
        ("Payment Method", col_map["PaymentMethod"],
            ["Electronic check", "Mailed check", "Bank transfer (automatic)", "Credit card (automatic)"]),
        ("Region",         col_map["Region"],
            ["Western", "Central", "Southern", "Northern",
             "Eastern", "North-Western", "North-Central", "Uva", "Sabaragamuwa"]),
    ]

    headers = ["Segment", "Category", "Total Customers", "Churned",
               "Churn Rate", "Total Revenue ($)", "Revenue at Risk ($)", "ARPU ($)"]
    ws.append(headers)
    style_header_row(ws, 1, len(headers))
    ws.freeze_panes = "A2"

    row = 2
    for seg_label, seg_col, categories in sections:
        for i, cat in enumerate(categories):
            total_formula   = countifs_total(seg_col, cat)
            churned_formula = countifs_churn(seg_col, cat)
            total_rev_f     = sumifs_rev(seg_col, cat, churn=None)
            risk_rev_f      = sumifs_rev(seg_col, cat, churn=1)
            churn_rate_f    = f"=IF(C{row}=0,0,D{row}/C{row})"
            arpu_f          = f"=IF(C{row}=0,0,F{row}/C{row})"

            ws.cell(row=row, column=1, value=seg_label if i == 0 else "")
            ws.cell(row=row, column=2, value=cat)
            ws.cell(row=row, column=3, value=total_formula)
            ws.cell(row=row, column=4, value=churned_formula)
            ws.cell(row=row, column=5, value=churn_rate_f)
            ws.cell(row=row, column=6, value=total_rev_f)
            ws.cell(row=row, column=7, value=risk_rev_f)
            ws.cell(row=row, column=8, value=arpu_f)

            # Formatting
            ws.cell(row=row, column=5).number_format = "0.0%"
            ws.cell(row=row, column=6).number_format = "#,##0"
            ws.cell(row=row, column=7).number_format = "#,##0"
            ws.cell(row=row, column=8).number_format = "#,##0.00"

            if row % 2 == 0:
                for c in range(1, 9):
                    ws.cell(row=row, column=c).fill = alt_fill()
            for c in range(1, 9):
                ws.cell(row=row, column=c).border = thin_border()
                ws.cell(row=row, column=c).alignment = Alignment(vertical="center")
            row += 1

        # Blank separator row
        ws.row_dimensions[row].height = 6
        row += 1

    # Conditional formatting on Churn Rate column (E)
    ws.conditional_formatting.add(
        f"E2:E{row}",
        ColorScaleRule(
            start_type="min", start_color="D5E8D4",
            mid_type="percentile", mid_value=50, mid_color="FFF2CC",
            end_type="max", end_color="F8CECC",
        ),
    )
    # Data bar on Revenue at Risk (G)
    ws.conditional_formatting.add(
        f"G2:G{row}",
        DataBarRule(start_type="min", start_value=0,
                    end_type="max", end_value=None,
                    color="2E75B6"),
    )

    col_widths = {"A": 18, "B": 32, "C": 16, "D": 10, "E": 12,
                  "F": 20, "G": 20, "H": 12}
    set_col_widths(ws, col_widths)
    ws.row_dimensions[1].height = 30
    return ws


# ═════════════════════════════════════════════════════════════════════════════
# SHEET 3 – Revenue_Analysis  (SUMIFS + INDEX/MATCH)
# ═════════════════════════════════════════════════════════════════════════════
def build_revenue_analysis(wb: Workbook, data_rows: int):
    ws = wb.create_sheet("Revenue_Analysis")
    DATA = "Data"
    MAX_ROW = data_rows + 1
    H, G, J, O, N = "H", "G", "J", "O", "N"  # Contract, Internet, Monthly, Churn, Region

    def title_row(ws, row, text):
        ws.cell(row=row, column=1, value=text)
        ws.cell(row=row, column=1).font = Font(bold=True, size=12, color=C_HEADER)
        ws.cell(row=row, column=1).fill = PatternFill("solid", fgColor=C_LIGHT_GOLD)

    # ── Section 1: Revenue by Contract × Internet ─────────────────────────────
    title_row(ws, 1, "Monthly Revenue by Contract × Internet Service")
    row = 2
    contracts = ["Month-to-month", "One year", "Two year"]
    internets = ["Fiber optic", "DSL", "No"]

    # Sub-headers
    ws.cell(row=row, column=1, value="Contract \\ Internet")
    for c_idx, inet in enumerate(internets, start=2):
        ws.cell(row=row, column=c_idx, value=inet)
    ws.cell(row=row, column=5, value="Row Total")
    style_header_row(ws, row, 5)
    row += 1

    for con in contracts:
        ws.cell(row=row, column=1, value=con).font = Font(bold=True)
        for c_idx, inet in enumerate(internets, start=2):
            f = (
                f"=SUMIFS('{DATA}'!{J}$2:{J}${MAX_ROW},"
                f"'{DATA}'!{H}$2:{H}${MAX_ROW},\"{con}\","
                f"'{DATA}'!{G}$2:{G}${MAX_ROW},\"{inet}\")"
            )
            ws.cell(row=row, column=c_idx, value=f).number_format = "#,##0"
        ws.cell(row=row, column=5,
                value=f"=SUM(B{row}:D{row})").number_format = "#,##0"
        if row % 2 == 0:
            for c in range(1, 6):
                ws.cell(row=row, column=c).fill = alt_fill()
        for c in range(1, 6):
            ws.cell(row=row, column=c).border = thin_border()
        row += 1

    # Column totals
    ws.cell(row=row, column=1, value="Column Total").font = Font(bold=True)
    for c_idx in range(2, 6):
        start = row - len(contracts)
        ws.cell(row=row, column=c_idx,
                value=f"=SUM({get_column_letter(c_idx)}{start}:{get_column_letter(c_idx)}{row-1})"
                ).number_format = "#,##0"
        ws.cell(row=row, column=c_idx).font = Font(bold=True)
        ws.cell(row=row, column=c_idx).fill = gold_fill()
    ws.cell(row=row, column=1).fill = gold_fill()
    row += 2

    # ── Section 2: INDEX/MATCH example ───────────────────────────────────────
    title_row(ws, row, "INDEX / MATCH – Lookup a Customer's Plan Details")
    row += 1
    ws.cell(row=row, column=1, value="Lookup Customer ID:")
    ws.cell(row=row, column=1).font = Font(bold=True)
    ws.cell(row=row, column=2, value="0002-ORFBO")   # example id from dataset
    ws.cell(row=row, column=2).fill = PatternFill("solid", fgColor="FFFDE7")
    ws.cell(row=row, column=2).font = Font(bold=True, color="C55A11")
    ws.cell(row=row, column=2).border = thin_border()
    lookup_row = row
    row += 1

    fields = [
        ("Contract",        H, "Contract Type"),
        ("Internet Service",G, "Internet"),
        ("Monthly Charge",  J, "Monthly ($)"),
        ("Region",          N, "Region"),
        ("Churned?",        O, "Churn (1=Yes)"),
    ]
    data_id_col = "A"  # Customer ID is col A on Data sheet

    for field_label, data_col, _ in fields:
        ws.cell(row=row, column=1, value=field_label)
        formula = (
            f"=IFERROR(INDEX('{DATA}'!{data_col}$2:{data_col}${MAX_ROW},"
            f"MATCH($B${lookup_row},'{DATA}'!{data_id_col}$2:{data_id_col}${MAX_ROW},0)),\"Not found\")"
        )
        ws.cell(row=row, column=2, value=formula)
        ws.cell(row=row, column=2).border = thin_border()
        ws.cell(row=row, column=2).fill = PatternFill("solid", fgColor="F0F7FF")
        row += 1

    row += 1

    # ── Section 3: Revenue at risk summary ────────────────────────────────────
    title_row(ws, row, "Revenue at Risk Summary by Region")
    row += 1
    ws.cell(row=row, column=1, value="Region").font = Font(bold=True)
    ws.cell(row=row, column=2, value="Total Revenue ($)").font = Font(bold=True)
    ws.cell(row=row, column=3, value="Revenue at Risk ($)").font = Font(bold=True)
    ws.cell(row=row, column=4, value="% at Risk").font = Font(bold=True)
    style_header_row(ws, row, 4)
    row += 1

    regions = ["Western","Central","Southern","Northern","Eastern",
               "North-Western","North-Central","Uva","Sabaragamuwa"]
    for reg in regions:
        ws.cell(row=row, column=1, value=reg)
        ws.cell(row=row, column=2,
                value=f"=SUMIFS('{DATA}'!{J}$2:{J}${MAX_ROW},'{DATA}'!{N}$2:{N}${MAX_ROW},\"{reg}\")"
                ).number_format = "#,##0"
        ws.cell(row=row, column=3,
                value=f"=SUMIFS('{DATA}'!{J}$2:{J}${MAX_ROW},'{DATA}'!{N}$2:{N}${MAX_ROW},\"{reg}\",'{DATA}'!{O}$2:{O}${MAX_ROW},1)"
                ).number_format = "#,##0"
        ws.cell(row=row, column=4,
                value=f"=IF(B{row}=0,0,C{row}/B{row})"
                ).number_format = "0.0%"
        if row % 2 == 0:
            for c in range(1, 5):
                ws.cell(row=row, column=c).fill = alt_fill()
        for c in range(1, 5):
            ws.cell(row=row, column=c).border = thin_border()
        row += 1

    col_widths = {"A": 26, "B": 22, "C": 22, "D": 12, "E": 14}
    set_col_widths(ws, col_widths)
    return ws


# ═════════════════════════════════════════════════════════════════════════════
# SHEET 4 – What_If
# ═════════════════════════════════════════════════════════════════════════════
def build_what_if(wb: Workbook, df: pd.DataFrame, data_rows: int):
    ws = wb.create_sheet("What_If")
    DATA = "Data"
    MAX_ROW = data_rows + 1
    J, O = "J", "O"  # Monthly charges, Churn

    total_customers = len(df)
    current_churners = int(df["Churn"].sum())
    current_arpu = float(df["MonthlyCharges"].mean())
    total_monthly_rev = float(df["MonthlyCharges"].sum())
    churn_rate = df["Churn"].mean()

    # Title
    ws.cell(row=1, column=1, value="💡 Price Change Impact – What-If Analysis").font = Font(
        bold=True, size=14, color=C_HEADER
    )
    ws.merge_cells("A1:F1")
    ws.cell(row=1, column=1).alignment = center()
    ws.cell(row=1, column=1).fill = PatternFill("solid", fgColor=C_LIGHT_GOLD)

    ws.cell(row=2, column=1, value=(
        "Change the price adjustment % in cell C5 to model the revenue and churn impact."
    )).font = Font(italic=True, color="595959", size=10)
    ws.merge_cells("A2:F2")

    # ── Input section ─────────────────────────────────────────────────────────
    ws.cell(row=4, column=2, value="INPUT").font = Font(bold=True, color=C_HEADER_TXT)
    ws.cell(row=4, column=2).fill = hdr_fill()
    ws.cell(row=4, column=2).alignment = center()
    ws.merge_cells("B4:C4")

    ws.cell(row=5, column=2, value="Price Change (%):")
    ws.cell(row=5, column=2).font = Font(bold=True)
    ws.cell(row=5, column=3, value=0.05)   # default: +5%
    ws.cell(row=5, column=3).number_format = "0%"
    ws.cell(row=5, column=3).fill = PatternFill("solid", fgColor="FFFDE7")
    ws.cell(row=5, column=3).font = Font(bold=True, size=12, color="C55A11")
    ws.cell(row=5, column=3).border = Border(
        left=Side(style="medium", color="C55A11"),
        right=Side(style="medium", color="C55A11"),
        top=Side(style="medium", color="C55A11"),
        bottom=Side(style="medium", color="C55A11"),
    )
    # Named range hint
    ws.cell(row=5, column=4, value="← edit this cell (e.g. 0.05 = +5%, -0.10 = -10%)")
    ws.cell(row=5, column=4).font = Font(italic=True, color="595959", size=9)
    ws.merge_cells("D5:F5")

    # Add data validation: -50% to +50%
    dv = DataValidation(type="decimal", operator="between",
                        formula1="-0.5", formula2="0.5",
                        error="Enter a value between -0.50 and 0.50",
                        errorTitle="Out of range",
                        prompt="Enter price change as decimal (e.g. 0.05 for 5%)",
                        promptTitle="Price change %")
    ws.add_data_validation(dv)
    dv.add("C5")

    # ── Assumptions ───────────────────────────────────────────────────────────
    ws.cell(row=7, column=2, value="ASSUMPTIONS").font = Font(bold=True, color=C_HEADER_TXT)
    ws.cell(row=7, column=2).fill = hdr_fill()
    ws.merge_cells("B7:C7")

    assumptions = [
        ("Price elasticity of churn", 0.5,
         "Each 1% price rise → 0.5% extra churn (industry estimate)"),
        ("Current customers",  total_customers, ""),
        ("Current churn rate", churn_rate,      "Actual from dataset"),
        ("Current ARPU ($/mo)", round(current_arpu, 2), "Average Monthly Charges"),
        ("Current total revenue ($/mo)", round(total_monthly_rev, 2), ""),
    ]
    for i, (lbl, val, note) in enumerate(assumptions, start=8):
        ws.cell(row=i, column=2, value=lbl)
        cell_val = ws.cell(row=i, column=3, value=val)
        if "rate" in lbl.lower():
            cell_val.number_format = "0.0%"
        elif "revenue" in lbl.lower() or "ARPU" in lbl:
            cell_val.number_format = "#,##0.00"
        ws.cell(row=i, column=4, value=note).font = Font(italic=True, color="595959", size=9)
        ws.merge_cells(f"D{i}:F{i}")
        if i % 2 == 0:
            for c in [2, 3]:
                ws.cell(row=i, column=c).fill = alt_fill()

    # Row references for formulas
    price_chg_row = 5
    elasticity_row = 8
    curr_cust_row  = 9
    curr_churn_row = 10
    curr_arpu_row  = 11
    curr_rev_row   = 12

    # ── Results section ───────────────────────────────────────────────────────
    ws.cell(row=14, column=2, value="SCENARIO RESULTS").font = Font(bold=True, color=C_HEADER_TXT)
    ws.cell(row=14, column=2).fill = accent_fill()
    ws.merge_cells("B14:E14")
    ws.cell(row=14, column=2).alignment = center()

    results = [
        ("New ARPU ($/mo)",
         f"=C{curr_arpu_row}*(1+C{price_chg_row})", "#,##0.00",
         "ARPU after price change"),
        ("Additional churn from price change",
         f"=C{curr_churn_row}*C{curr_cust_row}*C{elasticity_row}*ABS(C{price_chg_row})", "0",
         "Extra churners (elasticity model)"),
        ("New churn rate",
         f"=(C{curr_churn_row}*C{curr_cust_row}+C16)/C{curr_cust_row}", "0.0%",
         "Original + additional churn"),
        ("New total customers",
         f"=C{curr_cust_row}*(1-C17)", "#,##0",
         "After churn"),
        ("New total revenue ($/mo)",
         f"=C18*C15", "#,##0",
         "New customers × new ARPU"),
        ("Revenue change vs current ($/mo)",
         f"=C19-C{curr_rev_row}", "#,##0",
         "Δ revenue from price change"),
        ("Revenue change (%)",
         f"=IF(C{curr_rev_row}=0,0,(C19-C{curr_rev_row})/C{curr_rev_row})", "0.0%",
         ""),
    ]

    for i, (lbl, formula, fmt, note) in enumerate(results, start=15):
        ws.cell(row=i, column=2, value=lbl).font = Font(bold=True)
        cell = ws.cell(row=i, column=3, value=formula)
        cell.number_format = fmt
        cell.fill = PatternFill("solid", fgColor="F0F7FF")
        cell.border = thin_border()
        ws.cell(row=i, column=4, value=note).font = Font(italic=True, color="595959", size=9)
        ws.merge_cells(f"D{i}:F{i}")
        ws.cell(row=i, column=2).border = thin_border()

    # Highlight revenue change row
    ws.cell(row=20, column=2).fill = PatternFill("solid", fgColor=C_LIGHT_GOLD)
    ws.cell(row=20, column=3).fill = PatternFill("solid", fgColor=C_LIGHT_GOLD)
    ws.cell(row=20, column=2).font = Font(bold=True, size=12)
    ws.cell(row=20, column=3).font = Font(bold=True, size=12)

    # Conditional formatting: revenue change green if positive, red if negative
    ws.conditional_formatting.add(
        "C20",
        CellIsRule(operator="greaterThan", formula=["0"],
                   fill=PatternFill("solid", fgColor=C_CHURN_GRN),
                   font=Font(bold=True, color="375623")),
    )
    ws.conditional_formatting.add(
        "C20",
        CellIsRule(operator="lessThan", formula=["0"],
                   fill=PatternFill("solid", fgColor=C_CHURN_RED),
                   font=Font(bold=True, color="9C0006")),
    )

    col_widths = {"A": 4, "B": 34, "C": 20, "D": 38, "E": 10, "F": 10}
    set_col_widths(ws, col_widths)
    ws.row_dimensions[1].height = 30
    return ws


# ═════════════════════════════════════════════════════════════════════════════
# SHEET 5 – Dashboard  (charts from Churn_Summary)
# ═════════════════════════════════════════════════════════════════════════════
def build_dashboard(wb: Workbook, df: pd.DataFrame):
    ws = wb.create_sheet("Dashboard")
    ws.sheet_view.showGridLines = False

    ws.cell(row=1, column=1, value="Telecom Churn Analytics – Executive Dashboard")
    ws.cell(row=1, column=1).font = Font(bold=True, size=16, color=C_HEADER)
    ws.merge_cells("A1:P1")
    ws.cell(row=1, column=1).fill = PatternFill("solid", fgColor=C_LIGHT_GOLD)
    ws.cell(row=1, column=1).alignment = center()

    summary_ws = wb["Churn_Summary"]

    # ── Chart 1: Churn Rate by Contract (rows 2–4 in Churn_Summary) ───────────
    chart1 = BarChart()
    chart1.type = "col"
    chart1.grouping = "clustered"
    chart1.title = "Churn Rate by Contract Type"
    chart1.y_axis.title = "Churn Rate"
    chart1.y_axis.numFmt = "0%"
    chart1.x_axis.title = "Contract"
    chart1.style = 10
    chart1.width = 14
    chart1.height = 10

    # Churn rate is col E (5), categories in col B (2), rows 2–4
    data_ref   = Reference(summary_ws, min_col=5, max_col=5, min_row=1, max_row=4)
    cats_ref   = Reference(summary_ws, min_col=2, max_col=2, min_row=2, max_row=4)
    chart1.add_data(data_ref, titles_from_data=True)
    chart1.set_categories(cats_ref)
    chart1.series[0].graphicalProperties.solidFill = C_ACCENT
    ws.add_chart(chart1, "A3")

    # ── Chart 2: Revenue at Risk by Internet Service (rows 6–8) ────────────────
    chart2 = BarChart()
    chart2.type = "bar"
    chart2.grouping = "clustered"
    chart2.title = "Revenue at Risk by Internet Service"
    chart2.y_axis.title = "Revenue ($)"
    chart2.y_axis.numFmt = "#,##0"
    chart2.style = 10
    chart2.width = 14
    chart2.height = 10

    data_ref2 = Reference(summary_ws, min_col=7, max_col=7, min_row=5, max_row=8)
    cats_ref2 = Reference(summary_ws, min_col=2, max_col=2, min_row=6, max_row=8)
    chart2.add_data(data_ref2, titles_from_data=True)
    chart2.set_categories(cats_ref2)
    chart2.series[0].graphicalProperties.solidFill = "ED7D31"
    ws.add_chart(chart2, "I3")

    # ── Chart 3: Churn Distribution Pie (build small helper table) ─────────────
    ws.cell(row=22, column=1, value="Retained").font = Font(size=9)
    ws.cell(row=22, column=2, value=int((df["Churn"] == 0).sum()))
    ws.cell(row=23, column=1, value="Churned").font = Font(size=9)
    ws.cell(row=23, column=2, value=int(df["Churn"].sum()))

    chart3 = PieChart()
    chart3.title = "Churn Distribution"
    chart3.style = 10
    chart3.width = 14
    chart3.height = 10
    data_ref3 = Reference(ws, min_col=2, max_col=2, min_row=22, max_row=23)
    cats_ref3 = Reference(ws, min_col=1, max_col=1, min_row=22, max_row=23)
    chart3.add_data(data_ref3)
    chart3.set_categories(cats_ref3)
    # Colour the slices
    chart3.series[0].dPt = [
        DataPoint(idx=0, spPr=None),
        DataPoint(idx=1, spPr=None),
    ]
    chart3.series[0].dPt[0].graphicalProperties.solidFill = "2196F3"  # Retained
    chart3.series[0].dPt[1].graphicalProperties.solidFill = "F44336"  # Churned
    ws.add_chart(chart3, "A21")

    # ── Chart 4: Revenue at Risk by Region ─────────────────────────────────────
    chart4 = BarChart()
    chart4.type = "bar"
    chart4.title = "Revenue at Risk by Region"
    chart4.y_axis.numFmt = "#,##0"
    chart4.style = 10
    chart4.width = 14
    chart4.height = 10
    # rows 11–19 in Churn_Summary are Region rows (after the separator rows)
    # Contract rows 2–4, sep 5, Internet rows 6–8, sep 9, Payment rows 10–13, sep 14, Region rows 15–23
    # Actually we'll use rows 16–24 based on the build logic (4 sections, separators after each)
    # Sections: Contract(3), +sep=row5, Internet(3), +sep=row9, Payment(4), +sep=row14, Region(9) → rows 15–23
    data_ref4 = Reference(summary_ws, min_col=7, max_col=7, min_row=15, max_row=23)
    cats_ref4 = Reference(summary_ws, min_col=2, max_col=2, min_row=15, max_row=23)
    chart4.add_data(data_ref4)
    chart4.set_categories(cats_ref4)
    chart4.series[0].graphicalProperties.solidFill = "A9D18E"
    ws.add_chart(chart4, "I21")

    # KPI tiles
    kpis = [
        ("Total Customers",   f"{len(df):,}",          C_ACCENT),
        ("Churned",           f"{df['Churn'].sum():,}", "E53935"),
        ("Churn Rate",        f"{df['Churn'].mean():.1%}", "FF6D00"),
        ("Monthly Revenue",   f"${df['MonthlyCharges'].sum():,.0f}", "2E7D32"),
        ("Revenue at Risk",   f"${df.loc[df['Churn']==1,'MonthlyCharges'].sum():,.0f}", "B71C1C"),
        ("Avg ARPU",          f"${df['MonthlyCharges'].mean():.2f}", "1565C0"),
    ]
    for i, (label, value, color) in enumerate(kpis):
        col = 17 + i * 2
        ws.cell(row=3, column=col, value=label)
        ws.cell(row=3, column=col).font = Font(bold=True, size=9, color="595959")
        ws.cell(row=3, column=col).alignment = center()
        ws.cell(row=4, column=col, value=value)
        ws.cell(row=4, column=col).font = Font(bold=True, size=14, color=color)
        ws.cell(row=4, column=col).alignment = center()
        ws.cell(row=4, column=col).fill = PatternFill("solid", fgColor="F5F5F5")
        ws.column_dimensions[get_column_letter(col)].width = 16

    ws.row_dimensions[1].height = 36
    return ws


# ═════════════════════════════════════════════════════════════════════════════
# MAIN
# ═════════════════════════════════════════════════════════════════════════════
def main():
    EXCEL_DIR.mkdir(parents=True, exist_ok=True)
    df = pd.read_csv(PROCESSED / "dim_customer.csv")

    wb = Workbook()

    print("Building Data sheet...")
    _, data_rows = build_data_sheet(wb, df)

    print("Building Churn_Summary sheet...")
    build_churn_summary(wb, df, data_rows)

    print("Building Revenue_Analysis sheet...")
    build_revenue_analysis(wb, data_rows)

    print("Building What_If sheet...")
    build_what_if(wb, df, data_rows)

    print("Building Dashboard sheet...")
    build_dashboard(wb, df)

    out = EXCEL_DIR / "churn_analysis.xlsx"
    wb.save(out)
    size_kb = out.stat().st_size / 1024
    print(f"\nSaved: {out}  ({size_kb:.0f} KB)")
    print("Sheets: Data | Churn_Summary | Revenue_Analysis | What_If | Dashboard")


if __name__ == "__main__":
    main()
