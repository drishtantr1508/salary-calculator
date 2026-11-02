"""
Interactive CLI for Indian Salary & TDS Calculator (New Tax Regime).
Provides Rich formatted console output with month-by-month payroll simulation.
"""

import argparse
import sys
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text

from core.payroll_simulator import PayrollSimulator, FY_MONTHS
from core.salary_structure import PFConfig, SalaryStructureConfig


def parse_arguments():
    parser = argparse.ArgumentParser(description="Indian Salary & TDS Calculator (New Tax Regime - Sec 192)")
    parser.add_argument("--ctc", type=float, default=2_200_000.0, help="Initial Annual CTC in INR (e.g. 2200000 for 22 LPA)")
    parser.add_argument("--bonus-mode", choices=["spread", "upfront"], default="spread",
                        help="TDS treatment for bonus: 'spread' across remaining months, or 'upfront' in bonus month")
    parser.add_argument("--pf-amount", type=float, default=3000.0, help="Monthly PF deduction in INR (e.g. 1800 or 3000)")
    parser.add_argument("--pf-mode", choices=["custom", "statutory", "actual_12_pct", "zero"], default="custom",
                        help="PF calculation mode")
    parser.add_argument("--preset", choices=["user_scenario", "flat_22L", "custom"], default="user_scenario",
                        help="Pre-configured scenario")
    return parser.parse_args()


def main():
    console = Console()
    args = parse_arguments()

    console.print(Panel.fit(
        "[bold white]INDIAN SALARY & TDS SIMULATOR (NEW TAX REGIME)[/bold white]\n"
        "[dim]Section 192 Dynamic Month-by-Month Payroll Simulator (Budget 2024 Slabs)[/dim]",
        border_style="white"
    ))

    pf_cfg = PFConfig(mode=args.pf_mode, custom_monthly_amount=args.pf_amount)
    sim = PayrollSimulator(
        initial_ctc=args.ctc,
        initial_pf_config=pf_cfg,
        bonus_tax_mode=args.bonus_mode
    )

    if args.preset == "user_scenario":
        console.print("[dim]Scenario: 22 LPA Baseline | ₹3.33L Nov Bonus | 20% Jan Hike | ₹3k PF | Sec 192 Recalculation[/dim]\n")
        sim.add_bonus(month_index=8, amount=333_000.0, title="Annual Bonus")
        sim.add_hike(month_index=10, hike_pct=20.0, note="Appraisal Hike")

    res = sim.simulate()

    # Build Monochrome Monthly Table
    table = Table(title="Financial Year Month-by-Month Payslip Breakdown (April to March)", border_style="dim", show_header=True)
    table.add_column("Month", style="bold white", justify="left")
    table.add_column("CTC (LPA)", justify="right")
    table.add_column("Gross Pay (₹)", justify="right")
    table.add_column("Bonus (₹)", justify="right")
    table.add_column("EPF (₹)", justify="right")
    table.add_column("Prof Tax (₹)", justify="right")
    table.add_column("TDS (₹)", justify="right", style="bold white")
    table.add_column("Net In-Hand (₹)", justify="right", style="bold white")
    table.add_column("Notes / Events", justify="left", style="dim")

    for p in res.monthly_payslips:
        table.add_row(
            p.month_name,
            f"{p.annual_ctc_active / 100_000:.2f}L",
            f"{p.gross_salary:,.0f}",
            f"{p.bonus:,.0f}" if p.bonus > 0 else "-",
            f"{p.employee_pf:,.0f}",
            f"{p.professional_tax:,.0f}",
            f"{p.monthly_tds:,.0f}",
            f"{p.net_in_hand:,.0f}",
            p.note
        )

    console.print(table)

    # Annual Summary Panel
    summary_text = Text()
    summary_text.append(f"• Total CTC Earned:        ₹{res.total_annual_ctc_received:,.2f}\n", style="bold white")
    summary_text.append(f"• Total Gross Salary:      ₹{res.total_annual_gross:,.2f}\n", style="bold white")
    summary_text.append(f"• Total Bonus Included:    ₹{res.total_annual_bonus:,.2f}\n", style="white")
    summary_text.append(f"• Standard Deduction:      ₹{res.final_tax_result.standard_deduction:,.2f}\n", style="dim")
    summary_text.append(f"• Taxable Income:          ₹{res.final_tax_result.taxable_income:,.2f}\n", style="white")
    summary_text.append(f"• Total TDS Paid for Year: ₹{res.total_annual_tds:,.2f}\n", style="bold white")
    summary_text.append(f"• Total In-Hand Received:  ₹{res.total_annual_net_in_hand:,.2f}\n", style="bold white")
    summary_text.append(f"• Effective Tax Rate:      {res.effective_tax_rate_on_gross:.2f}% (on Gross) | {res.effective_tax_rate_on_ctc:.2f}% (on CTC)\n", style="white")
    summary_text.append(f"• Bonus Tax Mode:          {res.bonus_tax_mode.upper()} (Sec 192)\n", style="dim")

    console.print(Panel(summary_text, title="ANNUAL TAX & COMPENSATION SUMMARY", border_style="white"))


if __name__ == "__main__":
    main()
