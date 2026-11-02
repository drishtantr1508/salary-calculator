"""
Indian Salary & TDS Calculator Engine (New Tax Regime).
"""

from .tax_engine import (
    calculate_annual_tax,
    AnnualTaxResult,
    TaxSlab,
    DEFAULT_NEW_REGIME_SLABS,
    DEFAULT_STANDARD_DEDUCTION
)
from .salary_structure import (
    calculate_monthly_components,
    MonthlySalaryComponents,
    PFConfig,
    SalaryStructureConfig
)
from .payroll_simulator import (
    PayrollSimulator,
    FinancialYearSimulation,
    MonthlyPayslip,
    MonthlyInput,
    HikeEvent,
    BonusEvent,
    PFChangeEvent,
    FY_MONTHS
)
from .report_exporter import (
    simulation_to_dataframe,
    generate_payslip_card,
    compare_with_naive_calculator
)

__all__ = [
    "calculate_annual_tax",
    "AnnualTaxResult",
    "TaxSlab",
    "DEFAULT_NEW_REGIME_SLABS",
    "DEFAULT_STANDARD_DEDUCTION",
    "calculate_monthly_components",
    "MonthlySalaryComponents",
    "PFConfig",
    "SalaryStructureConfig",
    "PayrollSimulator",
    "FinancialYearSimulation",
    "MonthlyPayslip",
    "HikeEvent",
    "BonusEvent",
    "PFChangeEvent",
    "FY_MONTHS",
    "simulation_to_dataframe",
    "generate_payslip_card",
    "compare_with_naive_calculator"
]
