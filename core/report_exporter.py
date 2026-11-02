"""
Report and Export Utilities for Salary Calculator.
Provides:
- Conversion to pandas DataFrames
- Payslip breakdown summaries
- CSV export
- HTML printable summary
- Comparison with naive / static flat calculators
"""

import pandas as pd
from typing import Dict, Any, List
from .payroll_simulator import FinancialYearSimulation, MonthlyPayslip


def simulation_to_dataframe(sim: FinancialYearSimulation) -> pd.DataFrame:
    """
    Converts monthly payslips to a clean pandas DataFrame.
    """
    data = []
    for p in sim.monthly_payslips:
        data.append({
            "Month": p.month_name,
            "Status": "Actual" if p.is_actual else "Projected",
            "Active CTC (LPA)": round(p.annual_ctc_active / 100_000, 2),
            "Monthly CTC": p.monthly_ctc,
            "Basic Pay": p.basic,
            "HRA": p.hra,
            "Special Allowance": p.special_allowance,
            "Bonus": p.bonus,
            "Gross Salary": p.gross_salary,
            "Employee PF": p.employee_pf,
            "Prof. Tax (PT)": p.professional_tax,
            "Monthly TDS": p.monthly_tds,
            "Total Deductions": p.total_deductions,
            "Net In-Hand": p.net_in_hand,
            "Cumulative Gross": p.cumulative_gross,
            "Cumulative TDS": p.cumulative_tds_paid,
            "Cumulative Net": p.cumulative_net_in_hand,
            "Months Left": p.months_remaining,
            "Notes": p.note
        })
    return pd.DataFrame(data)


def generate_payslip_card(p: MonthlyPayslip) -> Dict[str, Any]:
    """
    Formats a single month payslip into detailed earnings vs deductions dictionary.
    """
    earnings = [
        {"item": "Basic Salary", "amount": p.basic},
        {"item": "House Rent Allowance (HRA)", "amount": p.hra},
        {"item": "Special Allowance", "amount": p.special_allowance},
    ]
    if p.bonus > 0:
        earnings.append({"item": "Performance Bonus / Incentive", "amount": p.bonus})

    deductions = [
        {"item": "Employee Provident Fund (EPF)", "amount": p.employee_pf},
        {"item": "Professional Tax (PT)", "amount": p.professional_tax},
        {"item": "Tax Deducted at Source (TDS)", "amount": p.monthly_tds},
    ]

    return {
        "month": p.month_name,
        "is_actual": p.is_actual,
        "active_ctc": p.annual_ctc_active,
        "gross": p.gross_salary,
        "earnings": earnings,
        "deductions": deductions,
        "total_deductions": p.total_deductions,
        "net_pay": p.net_in_hand,
        "note": p.note
    }


def compare_with_naive_calculator(sim: FinancialYearSimulation) -> Dict[str, Any]:
    """
    Demonstrates why naive calculators fail in real Indian payroll:
    A naive website just takes Total Annual Tax and divides by 12 evenly.
    In reality, when bonus arrives in Nov and hike in Jan:
    - April to October TDS was based on initial 22L.
    - November TDS spikes due to bonus.
    - January TDS shifts due to hike.
    """
    total_tax = sim.total_annual_tds
    naive_monthly_tds = round(total_tax / 12, 2)

    diffs = []
    for p in sim.monthly_payslips:
        diff = p.monthly_tds - naive_monthly_tds
        diffs.append({
            "month": p.month_name,
            "actual_tds": p.monthly_tds,
            "naive_tds": naive_monthly_tds,
            "difference": diff,
            "actual_net": p.net_in_hand,
            "naive_net": round(p.gross_salary - p.employee_pf - p.professional_tax - naive_monthly_tds, 2)
        })

    return {
        "total_tax": total_tax,
        "naive_monthly_tds": naive_monthly_tds,
        "monthly_comparison": diffs
    }
