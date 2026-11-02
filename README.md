# 🇮🇳 Dynamic Indian Salary & TDS Calculator (New Tax Regime)

> **Section 192 Compliant Month-by-Month Payroll Simulator**  
> Tailored for the **New Tax Regime** (Budget 2024 / FY 2024-25 & FY 2025-26 rules under Section 115BAC).

Unlike standard online calculators that naively divide your annual tax by 12, this application simulates **real-world Indian payroll mechanics**:
TDS is dynamically recomputed each month based on your accumulated earnings, upcoming months' projected salary, one-time bonuses, mid-year appraisal hikes, and changing statutory deductions (EPF & Professional Tax).

---

## 🌟 Key Features

1. **Full Month-on-Month Editable Input Grid**:
   - An interactive `st.data_editor` table where **every single cell is editable** for all 12 months (April to March):
     - `Annual CTC`: Adjust CTC for any month (e.g., 22 LPA April–Dec, 26.4 LPA from Jan).
     - `Employer PF`: Adjust employer contribution per month (e.g. ₹1,800 Apr–Aug, ₹3,000 from Sep).
     - `Employee PF`: Adjust employee deduction per month.
     - `Bonus / Incentive`: Input one-time bonuses in any month (e.g. ₹3,33,000 in Nov).
     - `Professional Tax (PT)`: Set per-month PT (default ₹200/mo, ₹300 in Feb).
   - Quick bulk action popovers: "Quick Fill Base CTC", "Apply Mid-Year Hike", "Apply PF Change".

2. **Section 192 Dynamic Month-by-Month Recalculation**:
   - Computes:
     $$\text{TDS}_{\text{month}} = \frac{\text{Projected Annual Tax} - \text{Cumulative TDS Deducted to Date}}{\text{Months Remaining in FY}}$$
   - Guarantees exact reconciliation down to the rupee in March true-up.

3. **Pure Monochrome / Black & White Professional Executive UI**:
   - Clean, minimalist aesthetic with zero rainbow colors.
   - High-contrast typography (`Inter` for UI, `JetBrains Mono` for financial figures).
   - Custom monochrome Plotly charts and dark executive card layouts.

4. **One-Time Bonuses with Dual Tax Treatments**:
   - **Mode A (Section 192 Spread)**: Incremental tax is spread across remaining months (Nov–Mar).
   - **Mode B (Upfront Bonus Tax)**: Incremental tax on bonus is deducted in the bonus month itself.

5. **Dual Interfaces**:
   - 🖥️ **Streamlit Web Dashboard**: Interactive sliders, Plotly cashflow charts, payslip inspector, and CSV export.
   - ⌨️ **Terminal / CLI**: Rich formatted console tables and summary cards for rapid command-line simulations.

---

## 🚀 Quick Start

### 1. Launch the Streamlit Web Dashboard

```bash
streamlit run app.py
```
Open [http://localhost:8501](http://localhost:8501) in your browser.

### 2. Run the Command-Line Interface (CLI)

Run default scenario (22 LPA + ₹3.33L Nov Bonus + 20% Jan Hike + ₹3k PF):
```bash
python3 cli.py
```

Run in upfront bonus tax mode:
```bash
python3 cli.py --bonus-mode upfront
```

Customize initial CTC or PF:
```bash
python3 cli.py --ctc 2500000 --pf-amount 3000 --bonus-mode spread
```

---

## 🧪 Running Unit Tests

Run the test suite with pytest:
```bash
PYTHONPATH=. pytest tests/ -v
```

---

## 📊 Project Structure

```
salary_calculator/
├── core/
│   ├── __init__.py
│   ├── tax_engine.py         # Slabs, 87A rebate & marginal relief, surcharge, cess
│   ├── salary_structure.py    # CTC breakdown: Basic, HRA, Special Allowance, EPF, PT
│   ├── payroll_simulator.py  # 12-month Section 192 simulation engine
│   └── report_exporter.py    # DataFrame conversion, single payslips & comparison
├── app.py                    # Streamlit Interactive Web Application
├── cli.py                    # Rich-powered Terminal CLI runner
├── tests/
│   ├── test_tax_engine.py    # Unit tests for tax engine & slabs
│   └── test_payroll_simulator.py # Tests for hikes, bonuses, and PF variations
└── README.md
```
