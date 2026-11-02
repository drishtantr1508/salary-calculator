import pytest
from core.tax_engine import (
    calculate_annual_tax,
    compute_base_slab_tax,
    compute_87a_rebate,
    compute_surcharge_with_marginal_relief
)
from core.payroll_simulator import PayrollSimulator, MonthlyInput, FY_MONTHS


def test_12L_full_rebate_and_12_75L_gross():
    """
    Gross income of 12.75 Lakhs with 75k standard deduction leaves 12.00 Lakhs taxable.
    Full rebate applies up to 12 Lakhs taxable income -> Tax is ZERO!
    """
    res = calculate_annual_tax(gross_income=1_275_000.0)
    assert res.standard_deduction == 75_000.0
    assert res.taxable_income == 1_200_000.0
    assert res.base_tax == 60_000.0
    assert res.rebate_87a == 60_000.0
    assert res.tax_after_rebate == 0.0
    assert res.total_tax_liability == 0.0


def test_12_76L_gross_marginal_relief():
    """
    Person earning 12.76 Lakhs gross:
    Taxable income = 12,76,000 - 75,000 = 12,01,000.
    Excess over 12 Lakhs is 1,000.
    Marginal relief caps tax to excess income (1,000).
    Total tax = 1,000 + 4% cess (40) = 1,040.
    Guarantees person earning 12.76L does not take home less than person earning 12.75L!
    """
    res = calculate_annual_tax(gross_income=1_276_000.0)
    assert res.taxable_income == 1_201_000.0
    assert res.tax_after_rebate == 1_000.0
    assert res.cess == 40.0
    assert res.total_tax_liability == 1_040.0


def test_50L_marginal_relief_on_surcharge():
    """
    Person earning 50,00,001 (50 Lakh and 1 rupee taxable):
    Base tax at 50 Lakh is 10,80,000.
    Without marginal relief, a 10% surcharge would be 1,08,000 on 1 extra rupee.
    With marginal relief, tax + surcharge cannot exceed:
    (Tax at 50L) + (Income - 50L) = 10,80,000 + 1 = 10,80,001.
    Surcharge is capped at 0.70 rupee.
    """
    taxable = 5_000_001.0
    base_tax, _ = compute_base_slab_tax(taxable)
    surcharge, rate = compute_surcharge_with_marginal_relief(taxable, base_tax)
    assert rate == 0.10
    assert round(base_tax + surcharge) == 1_080_001.0


def test_user_screenshot_54L_calculation():
    """
    Validates user's spreadsheet screenshot:
    Taxable Income = 54,03,400
    Base Tax = 1,201,020
    Surcharge (10%) + Cess (4%) = 13,73,967
    """
    base_tax, _ = compute_base_slab_tax(5_403_400.0)
    assert base_tax == 1_201_020.0

    res = calculate_annual_tax(gross_income=5_403_400.0 + 75_000.0, surcharge_mode="statutory")
    assert res.taxable_income == 5_403_400.0
    assert res.base_tax == 1_201_020.0
    assert res.total_tax_liability == 1_373_967.0


def test_user_22lpa_exact_inhand():
    """
    Validates user's reported figure:
    For 22 LPA at 1,800 PF deduction:
    Monthly In-Hand = 159,960!
    """
    inputs = [
        MonthlyInput(
            month_index=m,
            month_name=name,
            annual_ctc=2_200_000.0,
            employer_pf=1800.0,
            employee_pf=1800.0,
            bonus=0.0,
            professional_tax=200.0
        ) for m, name in enumerate(FY_MONTHS, start=1)
    ]
    sim = PayrollSimulator(monthly_inputs=inputs)
    res = sim.simulate()

    apr_slip = res.monthly_payslips[0]
    assert abs(apr_slip.net_in_hand - 159960) <= 1.0
