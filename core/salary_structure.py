"""
CTC and Monthly Salary Structure Components Engine.
Handles Indian salary structuring:
- Basic Salary
- House Rent Allowance (HRA)
- Special Allowance / Other Allowances (balancing figure)
- Employer Provident Fund (EPF)
- Gratuity (optional component of CTC)
- Employee Deductions: Employee PF, Professional Tax (PT), etc.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class PFConfig:
    """
    Configuration for Provident Fund:
    - mode: 'min_3000_or_12_pct' (default: minimum of 3000 and 12% of monthly basic salary),
            'statutory' (₹1,800/mo), 'custom' (fixed amount, e.g. ₹3,000/mo),
            'actual_12_pct' (12% of Basic), or 'zero' (opted out).
    - custom_monthly_amount: Used when mode is 'custom'.
    """
    mode: str = "min_3000_or_12_pct"
    custom_monthly_amount: float = 3000.0

    def get_monthly_pf(self, monthly_basic: float) -> float:
        if self.mode == "min_3000_or_12_pct":
            twelve_pct = round(monthly_basic * 0.12, 2)
            return min(3000.0, twelve_pct)
        elif self.mode == "statutory":
            return 1800.0
        elif self.mode == "actual_12_pct":
            return round(monthly_basic * 0.12, 2)
        elif self.mode == "zero":
            return 0.0
        else:  # 'custom'
            return float(self.custom_monthly_amount)


@dataclass
class SalaryStructureConfig:
    basic_pct_of_ctc: float = 0.50  # 50% of CTC
    hra_pct_of_basic: float = 0.50  # 50% of Basic (or 40% for non-metro)
    include_gratuity: bool = False   # Many companies do not subtract gratuity from monthly gross unless specified
    gratuity_pct_of_basic: float = 0.0481  # 4.81% of Basic (15/26 days per year)
    pt_standard_rate: float = 200.0
    pt_february_rate: float = 300.0


@dataclass
class MonthlySalaryComponents:
    month_name: str
    month_index: int  # 1 for April ... 12 for March
    annual_ctc: float
    monthly_ctc: float
    basic: float
    hra: float
    special_allowance: float
    employer_pf: float
    gratuity: float
    gross_salary: float  # basic + hra + special_allowance (+ bonus if added)
    employee_pf: float
    professional_tax: float
    bonus: float = 0.0

    @property
    def total_statutory_deductions_excl_tds(self) -> float:
        return self.employee_pf + self.professional_tax


def calculate_monthly_components(
    annual_ctc: float,
    month_index: int,
    month_name: str,
    pf_config: Optional[PFConfig] = None,
    structure_config: Optional[SalaryStructureConfig] = None,
    bonus: float = 0.0,
    employer_pf_override: Optional[float] = None,
    employee_pf_override: Optional[float] = None,
    pt_override: Optional[float] = None
) -> MonthlySalaryComponents:
    """
    Calculates monthly CTC decomposition and gross salary for a given month.
    Allows exact direct overrides for employer_pf, employee_pf, and professional_tax.
    """
    if structure_config is None:
        structure_config = SalaryStructureConfig()

    monthly_ctc = annual_ctc / 12.0
    annual_basic = annual_ctc * structure_config.basic_pct_of_ctc
    monthly_basic = annual_basic / 12.0

    monthly_hra = monthly_basic * structure_config.hra_pct_of_basic

    if employer_pf_override is not None:
        monthly_employer_pf = float(employer_pf_override)
    elif pf_config is not None:
        monthly_employer_pf = pf_config.get_monthly_pf(monthly_basic)
    else:
        monthly_employer_pf = 3000.0

    monthly_gratuity = (monthly_basic * structure_config.gratuity_pct_of_basic) if structure_config.include_gratuity else 0.0

    # Special allowance is the balancing component to ensure sum equals monthly CTC
    monthly_special_allowance = monthly_ctc - (monthly_basic + monthly_hra + monthly_employer_pf + monthly_gratuity)
    if monthly_special_allowance < 0:
        # Edge case: If basic + hra + pf exceeds monthly CTC, adjust special allowance to 0
        monthly_special_allowance = 0.0

    # Base gross salary (without bonus)
    base_gross = monthly_basic + monthly_hra + monthly_special_allowance
    total_gross = base_gross + bonus

    # Deductions
    if employee_pf_override is not None:
        monthly_employee_pf = float(employee_pf_override)
    else:
        monthly_employee_pf = monthly_employer_pf  # Standard is matching employer contribution

    # Professional Tax: ₹200 for 11 months, ₹300 in February
    if pt_override is not None:
        monthly_pt = float(pt_override)
    elif month_index == 11 or month_name.lower().startswith("feb"):
        monthly_pt = structure_config.pt_february_rate
    else:
        monthly_pt = structure_config.pt_standard_rate

    return MonthlySalaryComponents(
        month_name=month_name,
        month_index=month_index,
        annual_ctc=annual_ctc,
        monthly_ctc=round(monthly_ctc, 2),
        basic=round(monthly_basic, 2),
        hra=round(monthly_hra, 2),
        special_allowance=round(monthly_special_allowance, 2),
        employer_pf=round(monthly_employer_pf, 2),
        gratuity=round(monthly_gratuity, 2),
        gross_salary=round(total_gross, 2),
        employee_pf=round(monthly_employee_pf, 2),
        professional_tax=round(monthly_pt, 2),
        bonus=round(bonus, 2)
    )
