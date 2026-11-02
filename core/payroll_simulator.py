"""
Payroll Simulator Engine.
Simulates a full Indian Financial Year (April - March, 12 months)
strictly implementing Section 192 of the Income Tax Act:
- Dynamic month-by-month TDS calculation:
  TDS_month = (Total Projected Annual Tax - Cumulative TDS already paid) / Remaining Months
- Mid-year compensation revisions (Pay Hikes / Increments)
- One-time bonuses in specific months (e.g., Diwali / Performance bonus in November)
- Bonus tax treatment:
    a) 'spread': Standard Section 192 (incremental tax spread across remaining months)
    b) 'upfront': Incremental tax on the bonus deducted in the bonus month itself
- Variable Provident Fund (statutory ₹1,800, revised ₹3,000, 12% basic, or custom)
- Professional Tax with February special rule (₹200 for 11 months, ₹300 in Feb)
- Exact final March true-up to ensure zero discrepancy with annual tax liability.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from copy import deepcopy

from .tax_engine import calculate_annual_tax, AnnualTaxResult, DEFAULT_STANDARD_DEDUCTION
from .salary_structure import (
    calculate_monthly_components,
    MonthlySalaryComponents,
    PFConfig,
    SalaryStructureConfig
)

# Standard Financial Year Months
FY_MONTHS = [
    "April", "May", "June", "July", "August", "September",
    "October", "November", "December", "January", "February", "March"
]


@dataclass
class HikeEvent:
    month_index: int  # 1 for April ... 12 for March
    hike_pct: Optional[float] = None  # e.g., 20.0 for 20%
    new_ctc: Optional[float] = None   # absolute new CTC if specified
    note: str = ""


@dataclass
class BonusEvent:
    month_index: int  # 1 for April ... 12 for March
    amount: float
    title: str = "Bonus"
    note: str = ""


@dataclass
class PFChangeEvent:
    month_index: int  # Month from which PF changes
    new_pf_config: PFConfig
    note: str = ""


@dataclass
class MonthlyInput:
    month_index: int  # 1 to 12
    month_name: str   # April to March
    annual_ctc: float
    employer_pf: float = 3000.0
    employee_pf: float = 3000.0
    bonus: float = 0.0
    professional_tax: float = 200.0
    note: str = ""


@dataclass
class MonthlyPayslip:
    month_name: str
    month_index: int  # 1 to 12
    is_actual: bool   # True if month is <= current as-of month, False if projected

    # Compensation details
    annual_ctc_active: float
    monthly_ctc: float
    basic: float
    hra: float
    special_allowance: float
    employer_pf: float
    gratuity: float
    bonus: float
    gross_salary: float

    # Deductions
    employee_pf: float
    professional_tax: float
    monthly_tds: float
    total_deductions: float

    # Take-home
    net_in_hand: float

    # Cumulative stats
    cumulative_gross: float
    cumulative_tds_paid: float
    cumulative_net_in_hand: float

    # Projection state at this month
    projected_annual_gross: float
    projected_annual_tax: float
    months_remaining: int
    note: str = ""


@dataclass
class FinancialYearSimulation:
    monthly_payslips: List[MonthlyPayslip]
    total_annual_ctc_received: float
    total_annual_gross: float
    total_annual_bonus: float
    total_annual_employee_pf: float
    total_annual_professional_tax: float
    total_annual_tds: float
    total_annual_net_in_hand: float
    final_tax_result: AnnualTaxResult
    effective_tax_rate_on_gross: float
    effective_tax_rate_on_ctc: float
    bonus_tax_mode: str
    timeline_events_summary: List[Dict[str, Any]]


class PayrollSimulator:
    def __init__(
        self,
        initial_ctc: float = 2_200_000.0,
        initial_pf_config: Optional[PFConfig] = None,
        structure_config: Optional[SalaryStructureConfig] = None,
        standard_deduction: float = DEFAULT_STANDARD_DEDUCTION,
        nps_80ccd2_annual: float = 0.0,
        bonus_tax_mode: str = "upfront",  # Default to upfront TDS deduction on bonuses / variables
        current_as_of_month: int = 12,   # 1 to 12 (default 12 = full year simulation)
        anticipate_future_hikes: bool = False,  # False = realistic payroll (reacts when hike occurs); True = omniscient
        monthly_inputs: Optional[List[MonthlyInput]] = None,
        surcharge_mode: str = "statutory"  # 'statutory' (matches 1,373,967 for 54L) or 'flat_25'
    ):
        self.initial_ctc = initial_ctc
        self.initial_pf_config = initial_pf_config or PFConfig(mode="min_3000_or_12_pct")
        self.structure_config = structure_config or SalaryStructureConfig()
        self.standard_deduction = standard_deduction
        self.nps_80ccd2_annual = nps_80ccd2_annual
        self.bonus_tax_mode = bonus_tax_mode
        self.current_as_of_month = current_as_of_month
        self.anticipate_future_hikes = anticipate_future_hikes
        self.monthly_inputs = monthly_inputs
        self.surcharge_mode = surcharge_mode

        self.hike_events: Dict[int, HikeEvent] = {}
        self.bonus_events: Dict[int, List[BonusEvent]] = {}
        self.pf_change_events: Dict[int, PFChangeEvent] = {}

    def add_hike(self, month_index: int, hike_pct: Optional[float] = None, new_ctc: Optional[float] = None, note: str = ""):
        self.hike_events[month_index] = HikeEvent(month_index, hike_pct, new_ctc, note)

    def add_bonus(self, month_index: int, amount: float, title: str = "Bonus", note: str = ""):
        if month_index not in self.bonus_events:
            self.bonus_events[month_index] = []
        self.bonus_events[month_index].append(BonusEvent(month_index, amount, title, note))

    def add_pf_change(self, month_index: int, new_pf_config: PFConfig, note: str = ""):
        self.pf_change_events[month_index] = PFChangeEvent(month_index, new_pf_config, note)

    def simulate(self) -> FinancialYearSimulation:
        """
        Runs the full 12-month simulation using Indian Section 192 payroll methodology.
        """
        active_ctc = self.initial_ctc
        active_pf = deepcopy(self.initial_pf_config)

        # Precompute CTC, PF, Bonus, and PT for each month 1..12
        monthly_ctc_map: Dict[int, float] = {}
        monthly_employer_pf_map: Dict[int, float] = {}
        monthly_employee_pf_map: Dict[int, float] = {}
        monthly_pt_map: Dict[int, float] = {}
        monthly_bonus_map: Dict[int, float] = {}
        monthly_notes: Dict[int, List[str]] = {m: [] for m in range(1, 13)}

        if self.monthly_inputs and len(self.monthly_inputs) == 12:
            # Direct month-on-month user input table
            for inp in self.monthly_inputs:
                m = inp.month_index
                monthly_ctc_map[m] = inp.annual_ctc
                monthly_employer_pf_map[m] = inp.employer_pf
                monthly_employee_pf_map[m] = inp.employee_pf
                monthly_bonus_map[m] = inp.bonus
                monthly_pt_map[m] = inp.professional_tax
                if inp.note:
                    monthly_notes[m].append(inp.note)
                elif inp.bonus > 0:
                    monthly_notes[m].append(f"Bonus: ₹{inp.bonus:,.0f}")
        else:
            # Event-based builder mode
            active_ctc = self.initial_ctc
            active_pf = deepcopy(self.initial_pf_config)

            for m in range(1, 13):
                # Check PF change
                if m in self.pf_change_events:
                    active_pf = deepcopy(self.pf_change_events[m].new_pf_config)
                    monthly_notes[m].append(f"PF modified to {active_pf.mode} (₹{active_pf.custom_monthly_amount:,.0f}/mo)")

                # Check Hike
                if m in self.hike_events:
                    hike = self.hike_events[m]
                    old_ctc = active_ctc
                    if hike.new_ctc is not None:
                        active_ctc = hike.new_ctc
                    elif hike.hike_pct is not None:
                        active_ctc = round(active_ctc * (1.0 + hike.hike_pct / 100.0), 2)
                    hike_percent = ((active_ctc - old_ctc) / old_ctc) * 100
                    monthly_notes[m].append(f"CTC revised by {hike_percent:.1f}% to ₹{active_ctc:,.0f} LPA ({hike.note})")

                # Check Bonus
                b_total = 0.0
                if m in self.bonus_events:
                    for b in self.bonus_events[m]:
                        b_total += b.amount
                        monthly_notes[m].append(f"Received {b.title}: ₹{b.amount:,.0f}")

                monthly_ctc_map[m] = active_ctc
                # Derive PF amounts
                m_basic = (active_ctc * self.structure_config.basic_pct_of_ctc) / 12.0
                m_pf = active_pf.get_monthly_pf(m_basic)
                monthly_employer_pf_map[m] = m_pf
                monthly_employee_pf_map[m] = m_pf
                monthly_bonus_map[m] = b_total
                monthly_pt_map[m] = self.structure_config.pt_february_rate if (m == 11 or FY_MONTHS[m-1].lower().startswith("feb")) else self.structure_config.pt_standard_rate

        # Now simulate month by month (Section 192 TDS deduction)
        payslips: List[MonthlyPayslip] = []
        cumulative_gross = 0.0
        cumulative_tds_paid = 0.0
        cumulative_net = 0.0

        for m in range(1, 13):
            month_name = FY_MONTHS[m - 1]
            ctc_m = monthly_ctc_map[m]
            emp_pf_m = monthly_employer_pf_map[m]
            ee_pf_m = monthly_employee_pf_map[m]
            bonus_m = monthly_bonus_map[m]
            pt_m = monthly_pt_map[m]

            # Calculate base components for month m
            comps = calculate_monthly_components(
                annual_ctc=ctc_m,
                month_index=m,
                month_name=month_name,
                structure_config=self.structure_config,
                bonus=bonus_m,
                employer_pf_override=emp_pf_m,
                employee_pf_override=ee_pf_m,
                pt_override=pt_m
            )

            # --- Section 192 Projection for Month m ---
            # 1. Realized gross for months 1..m:
            realized_gross_so_far = cumulative_gross + comps.gross_salary

            # 2. Projected gross for remaining future months (m+1..12):
            future_projected_gross = 0.0
            for future_m in range(m + 1, 13):
                future_ctc = monthly_ctc_map[future_m] if getattr(self, "anticipate_future_hikes", False) else ctc_m
                future_emp_pf = monthly_employer_pf_map[future_m] if getattr(self, "anticipate_future_hikes", False) else emp_pf_m
                future_ee_pf = monthly_employee_pf_map[future_m] if getattr(self, "anticipate_future_hikes", False) else ee_pf_m
                future_pt = monthly_pt_map[future_m]

                future_comps = calculate_monthly_components(
                    annual_ctc=future_ctc,
                    month_index=future_m,
                    month_name=FY_MONTHS[future_m - 1],
                    structure_config=self.structure_config,
                    bonus=0.0,  # Future unexpected bonuses are not assumed in advance
                    employer_pf_override=future_emp_pf,
                    employee_pf_override=future_ee_pf,
                    pt_override=future_pt
                )
                future_projected_gross += future_comps.gross_salary

            total_projected_annual_gross = realized_gross_so_far + future_projected_gross

            # Compute Annual Tax on this projected annual gross
            tax_result_current = calculate_annual_tax(
                gross_income=total_projected_annual_gross,
                standard_deduction=self.standard_deduction,
                nps_80ccd2=self.nps_80ccd2_annual,
                surcharge_mode=self.surcharge_mode
            )
            projected_annual_tax = tax_result_current.total_tax_liability

            # Months remaining including current month:
            months_remaining = 12 - m + 1
            remaining_tax_liability = max(0.0, projected_annual_tax - cumulative_tds_paid)

            # Determine monthly TDS based on mode
            if m == 12:
                # Month 12 (March) final exact reconciliation
                monthly_tds = round(remaining_tax_liability, 2)
            elif self.bonus_tax_mode == "upfront" and bonus_m > 0:
                # Mode B: Upfront Bonus Tax
                # Calculate annual tax without this month's bonus
                tax_without_bonus = calculate_annual_tax(
                    gross_income=total_projected_annual_gross - bonus_m,
                    standard_deduction=self.standard_deduction,
                    nps_80ccd2=self.nps_80ccd2_annual,
                    surcharge_mode=self.surcharge_mode
                ).total_tax_liability
                
                # Base TDS without bonus for this month
                base_remaining_tax = max(0.0, tax_without_bonus - cumulative_tds_paid)
                base_tds = round(base_remaining_tax / months_remaining, 2)

                # Incremental tax specifically on the bonus
                incremental_bonus_tax = round(max(0.0, projected_annual_tax - tax_without_bonus), 2)
                monthly_tds = round(base_tds + incremental_bonus_tax, 2)
                monthly_notes[m].append(
                    f"Upfront Bonus Tax: Base TDS ₹{base_tds:,.0f} + Tax on Bonus ₹{incremental_bonus_tax:,.0f} (Total TDS: ₹{monthly_tds:,.0f})"
                )
            else:
                # Mode A: Standard Section 192 (Spread over remaining months)
                monthly_tds = round(remaining_tax_liability / months_remaining, 2)
                if bonus_m > 0 and self.bonus_tax_mode == "spread":
                    monthly_notes[m].append(
                        f"Bonus of ₹{bonus_m:,.0f} spread over {months_remaining} remaining months (Nov-Mar TDS increased)"
                    )

            # Net Take-home for month m
            total_deductions = round(comps.employee_pf + comps.professional_tax + monthly_tds, 2)
            net_in_hand = round(comps.gross_salary - total_deductions, 2)

            # Update running totals
            cumulative_gross += comps.gross_salary
            cumulative_tds_paid += monthly_tds
            cumulative_net += net_in_hand

            is_actual = m <= self.current_as_of_month
            note_str = " | ".join(monthly_notes[m]) if monthly_notes[m] else ""

            payslips.append(MonthlyPayslip(
                month_name=month_name,
                month_index=m,
                is_actual=is_actual,
                annual_ctc_active=ctc_m,
                monthly_ctc=comps.monthly_ctc,
                basic=comps.basic,
                hra=comps.hra,
                special_allowance=comps.special_allowance,
                employer_pf=comps.employer_pf,
                gratuity=comps.gratuity,
                bonus=comps.bonus,
                gross_salary=comps.gross_salary,
                employee_pf=comps.employee_pf,
                professional_tax=comps.professional_tax,
                monthly_tds=monthly_tds,
                total_deductions=round(total_deductions, 2),
                net_in_hand=round(net_in_hand, 2),
                cumulative_gross=round(cumulative_gross, 2),
                cumulative_tds_paid=round(cumulative_tds_paid, 2),
                cumulative_net_in_hand=round(cumulative_net, 2),
                projected_annual_gross=round(total_projected_annual_gross, 2),
                projected_annual_tax=round(projected_annual_tax, 2),
                months_remaining=months_remaining,
                note=note_str
            ))

        # Final Annual Totals
        total_gross = sum(p.gross_salary for p in payslips)
        total_bonus = sum(p.bonus for p in payslips)
        total_epf = sum(p.employee_pf for p in payslips)
        total_pt = sum(p.professional_tax for p in payslips)
        total_tds = sum(p.monthly_tds for p in payslips)
        total_net = sum(p.net_in_hand for p in payslips)
        total_ctc_paid = sum(p.monthly_ctc for p in payslips) + total_bonus

        final_tax = calculate_annual_tax(
            gross_income=total_gross,
            standard_deduction=self.standard_deduction,
            nps_80ccd2=self.nps_80ccd2_annual,
            surcharge_mode=self.surcharge_mode
        )

        effective_rate_gross = (total_tds / total_gross * 100) if total_gross > 0 else 0.0
        effective_rate_ctc = (total_tds / total_ctc_paid * 100) if total_ctc_paid > 0 else 0.0

        timeline_summary = []
        for m in range(1, 13):
            if monthly_notes[m]:
                timeline_summary.append({
                    "month": FY_MONTHS[m - 1],
                    "events": monthly_notes[m]
                })

        return FinancialYearSimulation(
            monthly_payslips=payslips,
            total_annual_ctc_received=round(total_ctc_paid, 2),
            total_annual_gross=round(total_gross, 2),
            total_annual_bonus=round(total_bonus, 2),
            total_annual_employee_pf=round(total_epf, 2),
            total_annual_professional_tax=round(total_pt, 2),
            total_annual_tds=round(total_tds, 2),
            total_annual_net_in_hand=round(total_net, 2),
            final_tax_result=final_tax,
            effective_tax_rate_on_gross=round(effective_rate_gross, 2),
            effective_tax_rate_on_ctc=round(effective_rate_ctc, 2),
            bonus_tax_mode=self.bonus_tax_mode,
            timeline_events_summary=timeline_summary
        )
