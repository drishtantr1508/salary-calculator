"""
Indian Income Tax Engine (New Tax Regime - Section 115BAC)
Supports FY 2024-25 and FY 2025-26 rules:
- Standard Deduction: ₹75,000 (Budget 2024 revised)
- Tax Slabs:
    0 - 3,00,000: Nil
    3,00,001 - 7,00,000: 5%
    7,00,001 - 10,00,000: 10%
    10,00,001 - 12,00,000: 15%
    12,00,001 - 15,00,000: 20%
    Above 15,00,000: 30%
- Section 87A Rebate:
    Rebate up to ₹25,000 for taxable income <= ₹7,00,000 (tax becomes ₹0 up to ₹7.75L gross).
    Marginal relief under proviso to section 87A:
    If taxable income slightly exceeds ₹7,00,000, tax liability shall not exceed (Taxable Income - ₹7,00,000).
- Surcharge (with marginal relief):
    > ₹50 Lakhs to ₹1 Crore: 10%
    > ₹1 Crore to ₹2 Crore: 15%
    > ₹2 Crore: 25%
- Health & Education Cess: 4% on (Tax + Surcharge)
- Section 80CCD(2): Employer contribution to NPS (up to 14% of Basic)
"""

from dataclasses import dataclass
from typing import List, Tuple, Dict, Any
import math


@dataclass
class TaxSlab:
    lower_limit: float
    upper_limit: float
    rate: float


# Actual Slabs:
# 0 - 4 Lakh: 0%
# 4 - 8 Lakh: 5% (₹20,000)
# 8 - 12 Lakh: 10% (₹40,000)
# 12 - 16 Lakh: 15% (₹60,000)
# 16 - 20 Lakh: 20% (₹80,000)
# 20 - 24 Lakh: 25% (₹100,000)
# 24 Lakh + : 30%
DEFAULT_NEW_REGIME_SLABS: List[TaxSlab] = [
    TaxSlab(0, 400_000, 0.0),
    TaxSlab(400_000, 800_000, 0.05),
    TaxSlab(800_000, 1_200_000, 0.10),
    TaxSlab(1_200_000, 1_600_000, 0.15),
    TaxSlab(1_600_000, 2_000_000, 0.20),
    TaxSlab(2_000_000, 2_400_000, 0.25),
    TaxSlab(2_400_000, float("inf"), 0.30),
]

DEFAULT_STANDARD_DEDUCTION: float = 75_000.0
CESS_RATE: float = 0.04


def compute_base_slab_tax(taxable_income: float, slabs: List[TaxSlab] = None) -> Tuple[float, List[Dict[str, Any]]]:
    """
    Computes base tax across the progressive slabs and returns total base tax
    along with breakdown per slab.
    """
    if slabs is None:
        slabs = DEFAULT_NEW_REGIME_SLABS

    if taxable_income <= 0:
        return 0.0, []

    total_base_tax = 0.0
    breakdown = []

    for slab in slabs:
        if taxable_income > slab.lower_limit:
            taxable_in_slab = min(taxable_income, slab.upper_limit) - slab.lower_limit
            tax_for_slab = taxable_in_slab * slab.rate
            total_base_tax += tax_for_slab
            breakdown.append({
                "slab": f"₹{slab.lower_limit:,.0f} - {'Above' if math.isinf(slab.upper_limit) else f'₹{slab.upper_limit:,.0f}'}",
                "rate_pct": slab.rate * 100,
                "taxable_amount": taxable_in_slab,
                "tax": tax_for_slab
            })
        else:
            break

    return total_base_tax, breakdown


def compute_87a_rebate(
    taxable_income: float,
    base_tax: float,
    rebate_limit: float = 1_200_000.0
) -> Tuple[float, float, str]:
    """
    Calculates Section 87A rebate and marginal relief:
    - If taxable income <= rebate_limit (₹12,00,000), 100% full tax rebate applies (up to ₹60,000).
      Zero tax on taxable income up to ₹12 Lakhs (Gross up to ₹12.75 Lakhs with standard deduction).
    - If taxable income slightly exceeds rebate_limit:
      Marginal relief applies: Tax payable cannot exceed (Taxable Income - rebate_limit).
      Ensures a person earning e.g. 12.76L does not take home less than someone earning 12.75L.
    Returns: (rebate_amount, tax_after_rebate, note)
    """
    if taxable_income <= rebate_limit:
        rebate = base_tax
        return rebate, 0.0, f"Full 87A Rebate (Zero Tax up to ₹{rebate_limit/100_000:.0f}L Taxable)"

    # Marginal Relief for taxable income slightly above rebate_limit (e.g. ₹12.01L to ~₹12.70L)
    excess_income = taxable_income - rebate_limit
    if base_tax > excess_income:
        marginal_relief = base_tax - excess_income
        tax_after_relief = excess_income
        return marginal_relief, tax_after_relief, f"Section 87A Marginal Relief of ₹{marginal_relief:,.0f} (Tax capped to excess over ₹{rebate_limit/100_000:.0f}L)"

    return 0.0, base_tax, "No 87A Rebate applicable"


def compute_surcharge_with_marginal_relief(
    taxable_income: float,
    tax_after_rebate: float,
    surcharge_mode: str = "statutory"
) -> Tuple[float, float]:
    """
    Calculates Surcharge under New Regime:
    - Mode 'statutory' (standard Indian tax rules, matching user's spreadsheet total 1,373,967 for 54.034L):
      > 50L to 1Cr: 10%
      > 1Cr to 2Cr: 15%
      > 2Cr: 25%
    - Mode 'flat_25' (applies 25% surcharge / extra levy on tax when taxable income > 50L)
    Applies marginal relief so tax + surcharge does not exceed tax at threshold + (income - threshold).
    """
    if taxable_income <= 5_000_000:
        return 0.0, 0.0

    threshold = 5_000_000.0
    if surcharge_mode == "flat_25":
        rate = 0.25
    else:
        if taxable_income <= 10_000_000:
            rate = 0.10
        elif taxable_income <= 20_000_000:
            rate = 0.15
            threshold = 10_000_000.0
        else:
            rate = 0.25
            threshold = 20_000_000.0

    raw_surcharge = tax_after_rebate * rate

    # Marginal relief check
    tax_at_threshold, _ = compute_base_slab_tax(threshold)
    _, tax_at_threshold_after_rebate, _ = compute_87a_rebate(threshold, tax_at_threshold)
    
    # Surcharge at threshold
    surcharge_at_threshold = 0.0
    if surcharge_mode != "flat_25":
        if threshold == 10_000_000.0:
            surcharge_at_threshold = tax_at_threshold_after_rebate * 0.10
        elif threshold == 20_000_000.0:
            surcharge_at_threshold = tax_at_threshold_after_rebate * 0.15

    max_allowed_tax_and_surcharge = (tax_at_threshold_after_rebate + surcharge_at_threshold) + (taxable_income - threshold)
    current_tax_and_surcharge = tax_after_rebate + raw_surcharge

    if current_tax_and_surcharge > max_allowed_tax_and_surcharge:
        surcharge = max(0.0, max_allowed_tax_and_surcharge - tax_after_rebate)
    else:
        surcharge = raw_surcharge

    return surcharge, rate


@dataclass
class AnnualTaxResult:
    gross_income: float
    standard_deduction: float
    nps_80ccd2_deduction: float
    taxable_income: float
    base_tax: float
    rebate_87a: float
    tax_after_rebate: float
    surcharge: float
    surcharge_rate: float
    cess: float
    total_tax_liability: float
    effective_tax_rate: float
    slab_breakdown: List[Dict[str, Any]]
    note_87a: str


def calculate_annual_tax(
    gross_income: float,
    standard_deduction: float = DEFAULT_STANDARD_DEDUCTION,
    nps_80ccd2: float = 0.0,
    slabs: List[TaxSlab] = None,
    surcharge_mode: str = "statutory",
    rebate_limit: float = 1_200_000.0
) -> AnnualTaxResult:
    """
    Computes total annual tax liability under the New Tax Regime.
    """
    if slabs is None:
        slabs = DEFAULT_NEW_REGIME_SLABS

    # Deductions allowed under New Regime
    total_deductions = standard_deduction + nps_80ccd2
    taxable_income = max(0.0, gross_income - total_deductions)

    # Base tax
    base_tax, breakdown = compute_base_slab_tax(taxable_income, slabs)

    # Section 87A rebate & marginal relief (full zero tax up to ₹12L taxable / ₹12.75L gross)
    rebate_87a, tax_after_rebate, note_87a = compute_87a_rebate(taxable_income, base_tax, rebate_limit=rebate_limit)

    # Surcharge with marginal relief at ₹50 Lakhs
    surcharge, surcharge_rate = compute_surcharge_with_marginal_relief(taxable_income, tax_after_rebate, surcharge_mode=surcharge_mode)

    # Health & Education Cess (4%)
    cess = round((tax_after_rebate + surcharge) * CESS_RATE, 2)

    total_tax = round(tax_after_rebate + surcharge + cess)
    effective_rate = (total_tax / gross_income * 100) if gross_income > 0 else 0.0

    return AnnualTaxResult(
        gross_income=gross_income,
        standard_deduction=standard_deduction,
        nps_80ccd2_deduction=nps_80ccd2,
        taxable_income=taxable_income,
        base_tax=base_tax,
        rebate_87a=rebate_87a,
        tax_after_rebate=tax_after_rebate,
        surcharge=surcharge,
        surcharge_rate=surcharge_rate,
        cess=cess,
        total_tax_liability=total_tax,
        effective_tax_rate=effective_rate,
        slab_breakdown=breakdown,
        note_87a=note_87a
    )
