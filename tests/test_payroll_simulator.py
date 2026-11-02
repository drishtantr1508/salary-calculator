import pytest
from core.payroll_simulator import PayrollSimulator
from core.salary_structure import PFConfig
from core.tax_engine import calculate_annual_tax


def test_user_scenario_spread_mode():
    """
    Scenario:
    - Initial CTC: 22 LPA (April to December)
    - Bonus: ₹3,33,000 in November (Month 8)
    - Hike: 20% in January (Month 10)
    - PF: ₹3,000 / month
    - Professional Tax: ₹200 / month, ₹300 in Feb (Month 11)
    - Mode: 'spread'
    """
    sim = PayrollSimulator(
        initial_ctc=2_200_000.0,
        initial_pf_config=PFConfig(mode="custom", custom_monthly_amount=3000.0),
        bonus_tax_mode="spread"
    )
    # Add bonus in November (Month 8)
    sim.add_bonus(month_index=8, amount=333_000.0, title="Annual Performance Bonus")

    # Add hike in January (Month 10)
    sim.add_hike(month_index=10, hike_pct=20.0, note="Annual Appraisal")

    res = sim.simulate()

    # 1. Check months count
    assert len(res.monthly_payslips) == 12

    # 2. Check April to October active CTC is 22 LPA
    for m in range(0, 7):
        p = res.monthly_payslips[m]
        assert p.annual_ctc_active == 2_200_000.0
        assert p.bonus == 0.0

    # 3. Check November has bonus
    nov = res.monthly_payslips[7]
    assert nov.month_name == "November"
    assert nov.bonus == 333_000.0
    # TDS in November should be higher than October because bonus increases annual liability
    oct_payslip = res.monthly_payslips[6]
    assert nov.monthly_tds > oct_payslip.monthly_tds

    # 4. Check January hike (22L * 1.2 = 26.4L)
    jan = res.monthly_payslips[9]
    assert jan.month_name == "January"
    assert jan.annual_ctc_active == 2_640_000.0
    assert jan.monthly_ctc > oct_payslip.monthly_ctc

    # 5. Check Professional Tax in February (Month 11) is 300, others 200
    feb = res.monthly_payslips[10]
    assert feb.month_name == "February"
    assert feb.professional_tax == 300.0
    assert oct_payslip.professional_tax == 200.0

    # 6. Total Annual TDS must match the final tax liability exactly to the rupee!
    total_tds = sum(p.monthly_tds for p in res.monthly_payslips)
    expected_final_tax = calculate_annual_tax(res.total_annual_gross).total_tax_liability
    assert abs(total_tds - expected_final_tax) <= 1.0


def test_user_scenario_upfront_mode():
    """
    Same scenario with upfront bonus tax:
    - November TDS bears the full incremental tax of the bonus.
    - December TDS should drop back to pre-bonus baseline!
    """
    sim = PayrollSimulator(
        initial_ctc=2_200_000.0,
        initial_pf_config=PFConfig(mode="custom", custom_monthly_amount=3000.0),
        bonus_tax_mode="upfront"
    )
    sim.add_bonus(month_index=8, amount=333_000.0, title="Annual Performance Bonus")
    sim.add_hike(month_index=10, hike_pct=20.0, note="Annual Appraisal")

    res = sim.simulate()

    oct_p = res.monthly_payslips[6]
    nov_p = res.monthly_payslips[7]
    dec_p = res.monthly_payslips[8]

    # November TDS should spike massively (base TDS + 30% slab on bonus + cess)
    assert nov_p.monthly_tds > oct_p.monthly_tds * 2

    # In December, TDS drops back down because the bonus tax was already deducted upfront in Nov
    assert dec_p.monthly_tds < nov_p.monthly_tds
    assert abs(dec_p.monthly_tds - oct_p.monthly_tds) <= 5.0

    # Exact annual reconciliation still holds!
    total_tds = sum(p.monthly_tds for p in res.monthly_payslips)
    expected_final_tax = calculate_annual_tax(res.total_annual_gross).total_tax_liability
    assert abs(total_tds - expected_final_tax) <= 1.0


def test_pf_change_mid_year():
    """
    Test switching PF from ₹1,800 to ₹3,000 from October (Month 7)
    """
    sim = PayrollSimulator(
        initial_ctc=2_200_000.0,
        initial_pf_config=PFConfig(mode="custom", custom_monthly_amount=1800.0),
        bonus_tax_mode="spread"
    )
    sim.add_pf_change(
        month_index=7,
        new_pf_config=PFConfig(mode="custom", custom_monthly_amount=3000.0),
        note="PF rule update"
    )
    res = sim.simulate()

    # April - September: PF = 1800
    for m in range(0, 6):
        assert res.monthly_payslips[m].employee_pf == 1800.0

    # October - March: PF = 3000
    for m in range(6, 12):
        assert res.monthly_payslips[m].employee_pf == 3000.0


def test_direct_monthly_inputs_table():
    from core.payroll_simulator import MonthlyInput, FY_MONTHS
    
    # Custom 12-month table
    inputs = []
    for idx, name in enumerate(FY_MONTHS, start=1):
        ctc = 2_640_000.0 if idx >= 10 else 2_200_000.0
        pf = 1800.0 if idx <= 5 else 3000.0
        bonus = 333_000.0 if idx == 8 else 0.0
        pt = 300.0 if idx == 11 else 200.0
        inputs.append(MonthlyInput(
            month_index=idx,
            month_name=name,
            annual_ctc=ctc,
            employer_pf=pf,
            employee_pf=pf,
            bonus=bonus,
            professional_tax=pt
        ))

    sim = PayrollSimulator(monthly_inputs=inputs, bonus_tax_mode="spread")
    res = sim.simulate()

    assert len(res.monthly_payslips) == 12
    # Verify PF values
    assert res.monthly_payslips[0].employee_pf == 1800.0
    assert res.monthly_payslips[4].employee_pf == 1800.0  # Aug
    assert res.monthly_payslips[5].employee_pf == 3000.0  # Sep
    # Verify Bonus
    assert res.monthly_payslips[7].bonus == 333_000.0    # Nov
    # Verify PT
    assert res.monthly_payslips[10].professional_tax == 300.0  # Feb
    # Verify Hike
    assert res.monthly_payslips[9].annual_ctc_active == 2_640_000.0  # Jan
    # Final exact tax true-up
    total_tds = sum(p.monthly_tds for p in res.monthly_payslips)
    expected_tax = calculate_annual_tax(res.total_annual_gross).total_tax_liability
    assert abs(total_tds - expected_tax) <= 1.0

