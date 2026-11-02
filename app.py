"""
Indian Salary & TDS Calculator (New Tax Regime - Budget 2024).
Minimalist Executive Edition.
Features:
- High-contrast pinned columns (Month, Annual CTC, Net In-Hand) without dull gray styling.
- Cleaned up UI: removed redundant gray subtexts, captions, and personal calculation references.
- Clean PF options without hardcoded personal figures.
- Short month names (Apr, May, Jun, etc.) across the entire UI.
- Direct editable grid with instant recalculation.
- Crash-proof mode switching for multiple hikes and bonuses.
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go

from core.payroll_simulator import PayrollSimulator, MonthlyInput
from core.tax_engine import calculate_annual_tax, DEFAULT_STANDARD_DEDUCTION
from core.report_exporter import simulation_to_dataframe, compare_with_naive_calculator

SHORT_MONTHS = ["Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec", "Jan", "Feb", "Mar"]
BOLD_MONTHS = ["𝗔𝗽𝗿", "𝗠𝗮𝘆", "𝗝𝘂𝗻", "𝗝𝘂𝗹", "𝗔𝘂𝗴", "𝗦𝗲𝗽", "𝗢𝗰𝘁", "𝗡𝗼𝘃", "𝗗𝗲𝗰", "𝗝𝗮𝗻", "𝗙𝗲𝗯", "𝗠𝗮𝗿"]
BOLD_DIGITS = {'0':'𝟬','1':'𝟭','2':'𝟮','3':'𝟯','4':'𝟰','5':'𝟱','6':'𝟲','7':'𝟳','8':'𝟴','9':'𝟵'}
NORM_DIGITS = {v: k for k, v in BOLD_DIGITS.items()}

def to_bold_inr(val: float) -> str:
    s = f"₹{round(val):,}"
    return "".join(BOLD_DIGITS.get(c, c) for c in s)

def parse_bold_val(v) -> float:
    if isinstance(v, (int, float)):
        return float(v)
    clean = "".join(NORM_DIGITS.get(c, c) for c in str(v).replace("₹", "").replace(",", "").strip())
    try:
        return float(clean)
    except Exception:
        return 0.0

st.set_page_config(
    page_title="Salary & TDS Simulator | Indian New Tax Regime",
    page_icon="▪",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Minimalist Monochrome Styling (Clean White Background, High-Contrast Black & Sharp Borders)
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600;700&display=swap');

    html, body, [class*="css"] {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }
    
    .mono-num {
        font-family: 'JetBrains Mono', monospace;
    }

    .block-container {
        padding-top: 1.2rem;
        padding-bottom: 2.5rem;
        max-width: 1400px;
    }

    /* Minimal Header */
    .app-header {
        border-bottom: 1px solid #e5e7eb;
        padding-bottom: 0.6rem;
        margin-bottom: 1rem;
    }
    .app-title {
        font-size: 1.4rem;
        font-weight: 700;
        letter-spacing: -0.02em;
        color: #111827;
        margin: 0;
    }
    .app-sub {
        font-size: 0.8rem;
        color: #6b7280;
        margin-top: 2px;
    }

    /* Clean Minimalist KPI Card */
    .bw-kpi-card {
        background-color: #ffffff;
        border: 1px solid #e5e7eb;
        border-radius: 4px;
        padding: 12px 14px;
        margin-bottom: 0.8rem;
        box-shadow: 0 1px 2px rgba(0,0,0,0.02);
    }
    .bw-kpi-label {
        font-size: 0.7rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        color: #4b5563;
    }
    .bw-kpi-val {
        font-family: 'JetBrains Mono', monospace;
        font-size: 1.4rem;
        font-weight: 700;
        color: #111827;
        margin-top: 2px;
        letter-spacing: -0.02em;
    }

    /* Compact Real CTC Reality Check Box */
    .real-ctc-card {
        background: #f9fafb;
        border: 1px solid #e5e7eb;
        border-left: 3px solid #111827;
        padding: 10px 12px;
        border-radius: 3px;
        font-size: 0.77rem;
        color: #374151;
        line-height: 1.5;
        margin-top: 10px;
        margin-bottom: 10px;
    }

    /* Zero Tax Banner */
    .zero-tax-banner {
        border: 1px solid #111827;
        background: #f9fafb;
        padding: 10px 14px;
        border-radius: 3px;
        margin-bottom: 1rem;
        font-size: 0.82rem;
        color: #111827;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }

    /* High-contrast Tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        border-bottom: 2px solid #e5e7eb;
        background-color: transparent;
    }
    .stTabs [data-baseweb="tab"] {
        background-color: transparent;
        border: none;
        border-bottom: 2px solid transparent;
        color: #4b5563 !important;
        font-weight: 500;
        font-size: 0.85rem;
        padding: 8px 16px;
    }
    .stTabs [aria-selected="true"] {
        color: #000000 !important;
        border-bottom: 2px solid #000000 !important;
        background-color: transparent !important;
        font-weight: 700 !important;
    }
    .stTabs [data-baseweb="tab"]:hover {
        color: #000000 !important;
    }

    /* Table & Editor Styling: Solid black high-contrast presence */
    div[data-testid="stDataEditor"] {
        border: 1px solid #111827 !important;
        border-radius: 4px !important;
        font-size: 0.95rem !important;
        --gdg-text-dark: #000000 !important;
        --gdg-text-medium: #000000 !important;
        --gdg-text-light: #111827 !important;
        --gdg-text-header: #000000 !important;
        --gdg-text-group-header: #000000 !important;
        --gdg-bg-header: #f9fafb !important;
        --gdg-header-font-style: 700 13px Inter, sans-serif !important;
    }

    /* High-Visibility Solid Filled Primary Buttons */
    button[kind="primary"], div.stButton > button[kind="primary"], button[data-testid="baseButton-primary"] {
        background-color: #111827 !important;
        color: #ffffff !important;
        border: 1.5px solid #111827 !important;
        font-weight: 600 !important;
        border-radius: 5px !important;
        padding: 0.55rem 1rem !important;
        box-shadow: 0 1px 3px rgba(0,0,0,0.14) !important;
        letter-spacing: -0.01em !important;
        transition: all 0.15s ease !important;
    }
    button[kind="primary"]:hover, div.stButton > button[kind="primary"]:hover, button[data-testid="baseButton-primary"]:hover {
        background-color: #000000 !important;
        color: #ffffff !important;
        border-color: #000000 !important;
        box-shadow: 0 3px 8px rgba(0,0,0,0.24) !important;
        transform: translateY(-1px);
    }
    button[kind="primary"] p, div.stButton > button[kind="primary"] p, button[data-testid="baseButton-primary"] p {
        color: #ffffff !important;
        font-weight: 600 !important;
    }

    /* Solid Filled Style for Advanced Tax & TDS Settings */
    div[data-testid="stExpander"] {
        border: 1.5px solid #111827 !important;
        border-radius: 5px !important;
        overflow: hidden !important;
        margin-top: 14px !important;
        background: #ffffff !important;
    }
    div[data-testid="stExpander"] details summary {
        background-color: #111827 !important;
        color: #ffffff !important;
        font-weight: 600 !important;
        padding: 10px 14px !important;
        border-radius: 0px !important;
        transition: background-color 0.15s ease !important;
    }
    div[data-testid="stExpander"] details summary:hover {
        background-color: #000000 !important;
    }
    div[data-testid="stExpander"] details summary svg {
        fill: #ffffff !important;
        color: #ffffff !important;
    }
    div[data-testid="stExpander"] details summary p,
    div[data-testid="stExpander"] details summary span {
        color: #ffffff !important;
        font-weight: 600 !important;
    }
</style>
""", unsafe_allow_html=True)


# Helper: Generate monthly input table from base parameters, hikes, and bonuses
def generate_monthly_inputs(
    base_ctc: float,
    pf_mode: str,
    custom_pf: float,
    hikes: list,
    bonuses: list
) -> pd.DataFrame:
    hikes_sorted = sorted(hikes, key=lambda x: x.get("month", 1))
    current_ctc = float(base_ctc)
    rows = []

    for m in range(1, 13):
        notes = []

        # Apply any hikes effective at month m
        for h in hikes_sorted:
            if h.get("month") == m:
                mode = h.get("mode", "pct")
                val = float(h.get("value", 0.0))
                if mode == "pct":
                    current_ctc = round(current_ctc * (1.0 + val / 100.0), 2)
                    notes.append(f"Hike (+{val:.1f}%)")
                else:  # absolute
                    current_ctc = val
                    notes.append(f"CTC ₹{val/100000:.2f}L")

        # Calculate bonuses disbursed at month m
        b_sum = 0.0
        for b in bonuses:
            if b.get("month") == m:
                mode = b.get("mode", "absolute")
                val = float(b.get("value", 0.0))
                if mode == "absolute":
                    b_amt = val
                else:  # pct of CTC
                    b_amt = round(current_ctc * (val / 100.0), 2)
                b_sum += b_amt
                notes.append(f"Bonus ₹{b_amt:,.0f}")

        # Compute PF
        m_basic = (current_ctc * 0.50) / 12.0
        if pf_mode == "1800":
            pf_val = 1800.0
        elif pf_mode == "3000":
            pf_val = 3000.0
        elif pf_mode == "12_pct":
            pf_val = round(m_basic * 0.12, 2)
        elif pf_mode == "custom":
            pf_val = float(custom_pf)
        else:  # min_3000_or_12
            pf_val = min(3000.0, round(m_basic * 0.12, 2))

        pt_val = 300.0 if m == 11 else 200.0
        if m == 11 and not notes:
            notes.append("Feb PT ₹300")

        rows.append({
            "Month Index": m,
            "Month": SHORT_MONTHS[m - 1],
            "Annual CTC (₹)": float(current_ctc),
            "PF Contribution (₹)": float(pf_val),
            "Bonus (₹)": float(b_sum),
            "Prof. Tax (₹)": float(pt_val),
            "Notes": " | ".join(notes)
        })

    return pd.DataFrame(rows)


# Initialize Session State
if "base_ctc_input" not in st.session_state:
    st.session_state.base_ctc_input = 15.0  # Default 15 Lakhs CTC

if "pf_selection" not in st.session_state:
    st.session_state.pf_selection = "min_3000_or_12"

if "custom_pf_val" not in st.session_state:
    st.session_state.custom_pf_val = 3000.0

if "hikes_list" not in st.session_state:
    st.session_state.hikes_list = []

if "bonuses_list" not in st.session_state:
    st.session_state.bonuses_list = []

if "bonus_tax_mode" not in st.session_state:
    st.session_state.bonus_tax_mode = "upfront"

if "surcharge_mode" not in st.session_state:
    st.session_state.surcharge_mode = "statutory"

if "table_inputs" not in st.session_state:
    st.session_state.table_inputs = generate_monthly_inputs(
        base_ctc=1_500_000.0,
        pf_mode="min_3000_or_12",
        custom_pf=3000.0,
        hikes=[],
        bonuses=[]
    )


# ==================== APP HEADER ====================
st.markdown("""
<div class="app-header">
    <div class="app-title">INDIAN SALARY & TDS SIMULATOR</div>
    <div class="app-sub">Indian New Tax Regime • Budget 2024</div>
</div>
""", unsafe_allow_html=True)


# ==================== MAIN DESKTOP SIDE-BY-SIDE LAYOUT ====================
col_left, col_right = st.columns([3.8, 8.2], gap="medium")

# ----------------- LEFT PANEL: INPUTS & REVISION BUILDER -----------------
with col_left:
    st.markdown("#### Compensation Setup")

    # 1. Base CTC
    ctc_in = st.number_input(
        "Annual Base CTC (in Lakhs ₹)",
        min_value=1.0,
        max_value=300.0,
        value=float(st.session_state.base_ctc_input),
        step=0.5,
        help="Your recurring annual salary package (excluding unvested ESOPs and bonuses)."
    )

    # 2. Provident Fund (PF) Option
    pf_options = {
        "min_3000_or_12": "min(₹3,000, 12% Basic) — Default",
        "1800": "₹1,800 / month",
        "3000": "₹3,000 / month",
        "12_pct": "12% of Monthly Basic",
        "custom": "Custom Monthly Amount"
    }
    pf_keys = list(pf_options.keys())
    pf_idx = pf_keys.index(st.session_state.pf_selection) if st.session_state.pf_selection in pf_keys else 0

    selected_pf_key = st.selectbox(
        "Provident Fund (PF) Preset",
        options=pf_keys,
        index=pf_idx,
        format_func=lambda k: pf_options[k],
        help="Sets matching Employer PF and Employee PF deductions across all months."
    )

    custom_pf_val = 3000.0
    if selected_pf_key == "custom":
        custom_pf_val = st.number_input(
            "Custom Monthly PF (₹)",
            min_value=0.0,
            max_value=100000.0,
            value=float(st.session_state.custom_pf_val),
            step=100.0
        )

    st.markdown("---")

    # 3. Multiple Appraisals / Hikes Builder
    col_h_head, col_h_add = st.columns([3, 1.5])
    with col_h_head:
        st.markdown("**Appraisals / Hikes**")
    with col_h_add:
        if st.button("➕ Add Hike", key="add_hike_btn", use_container_width=True):
            st.session_state.hikes_list.append({
                "mode": "pct",
                "pct_val": 10.0,
                "abs_val": 2000000.0,
                "value": 10.0,
                "month": 10
            })
            st.rerun()

    if not st.session_state.hikes_list:
        st.caption("No hikes added.")
    else:
        hikes_to_remove = []
        for i, h in enumerate(st.session_state.hikes_list):
            c1, c2, c3, c4 = st.columns([1.3, 1.6, 1.6, 0.6])
            with c1:
                cur_mode = h.get("mode", "pct")
                h["mode"] = st.selectbox(
                    f"Mode #{i+1}",
                    options=["pct", "absolute"],
                    format_func=lambda x: "%" if x == "pct" else "₹ New CTC",
                    index=0 if cur_mode == "pct" else 1,
                    key=f"hike_mode_select_{i}",
                    label_visibility="collapsed"
                )
            with c2:
                if h["mode"] == "pct":
                    safe_val = min(200.0, max(0.5, float(h.get("pct_val", 10.0))))
                    val = st.number_input(
                        f"Hike % #{i+1}",
                        min_value=0.5,
                        max_value=200.0,
                        value=safe_val,
                        step=1.0,
                        key=f"hike_pct_input_{i}",
                        label_visibility="collapsed"
                    )
                    h["pct_val"] = val
                    h["value"] = val
                else:
                    safe_val = min(50000000.0, max(100000.0, float(h.get("abs_val", 2500000.0))))
                    val = st.number_input(
                        f"New CTC #{i+1}",
                        min_value=100000.0,
                        max_value=50000000.0,
                        value=safe_val,
                        step=50000.0,
                        key=f"hike_abs_input_{i}",
                        label_visibility="collapsed"
                    )
                    h["abs_val"] = val
                    h["value"] = val
            with c3:
                h["month"] = st.selectbox(
                    f"Month #{i+1}",
                    options=list(range(1, 13)),
                    format_func=lambda m: SHORT_MONTHS[m - 1],
                    index=int(h.get("month", 10) - 1),
                    key=f"hike_month_{i}",
                    label_visibility="collapsed"
                )
            with c4:
                if st.button("✖", key=f"del_hike_{i}", help="Remove hike"):
                    hikes_to_remove.append(i)

        if hikes_to_remove:
            for idx in sorted(hikes_to_remove, reverse=True):
                st.session_state.hikes_list.pop(idx)
            st.rerun()

    st.markdown("---")

    # 4. Multiple Bonuses Builder
    col_b_head, col_b_add = st.columns([3, 1.5])
    with col_b_head:
        st.markdown("**Bonuses / Variables**")
    with col_b_add:
        if st.button("➕ Add Bonus", key="add_bonus_btn", use_container_width=True):
            st.session_state.bonuses_list.append({
                "mode": "absolute",
                "abs_val": 100000.0,
                "pct_val": 10.0,
                "value": 100000.0,
                "month": 8
            })
            st.rerun()

    if not st.session_state.bonuses_list:
        st.caption("No bonuses added.")
    else:
        bonuses_to_remove = []
        for i, b in enumerate(st.session_state.bonuses_list):
            c1, c2, c3, c4 = st.columns([1.3, 1.6, 1.6, 0.6])
            with c1:
                cur_mode = b.get("mode", "absolute")
                b["mode"] = st.selectbox(
                    f"Bonus Mode #{i+1}",
                    options=["absolute", "pct"],
                    format_func=lambda x: "₹ Amount" if x == "absolute" else "% of CTC",
                    index=0 if cur_mode == "absolute" else 1,
                    key=f"bonus_mode_select_{i}",
                    label_visibility="collapsed"
                )
            with c2:
                if b["mode"] == "absolute":
                    safe_val = min(50000000.0, max(0.0, float(b.get("abs_val", 100000.0))))
                    val = st.number_input(
                        f"Bonus ₹ #{i+1}",
                        min_value=0.0,
                        max_value=50000000.0,
                        value=safe_val,
                        step=10000.0,
                        key=f"bonus_abs_input_{i}",
                        label_visibility="collapsed"
                    )
                    b["abs_val"] = val
                    b["value"] = val
                else:
                    safe_val = min(100.0, max(0.5, float(b.get("pct_val", 10.0))))
                    val = st.number_input(
                        f"Bonus % #{i+1}",
                        min_value=0.5,
                        max_value=100.0,
                        value=safe_val,
                        step=1.0,
                        key=f"bonus_pct_input_{i}",
                        label_visibility="collapsed"
                    )
                    b["pct_val"] = val
                    b["value"] = val
            with c3:
                b["month"] = st.selectbox(
                    f"Bonus Month #{i+1}",
                    options=list(range(1, 13)),
                    format_func=lambda m: SHORT_MONTHS[m - 1],
                    index=int(b.get("month", 8) - 1),
                    key=f"bonus_month_{i}",
                    label_visibility="collapsed"
                )
            with c4:
                if st.button("✖", key=f"del_bonus_{i}", help="Remove bonus"):
                    bonuses_to_remove.append(i)

        if bonuses_to_remove:
            for idx in sorted(bonuses_to_remove, reverse=True):
                st.session_state.bonuses_list.pop(idx)
            st.rerun()

    st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)

    # Apply configuration to Monthly Table
    if st.button("Apply Config to Monthly Table →", type="primary", use_container_width=True):
        st.session_state.base_ctc_input = ctc_in
        st.session_state.pf_selection = selected_pf_key
        st.session_state.custom_pf_val = custom_pf_val
        st.session_state.table_inputs = generate_monthly_inputs(
            base_ctc=ctc_in * 100_000.0,
            pf_mode=selected_pf_key,
            custom_pf=custom_pf_val,
            hikes=st.session_state.hikes_list,
            bonuses=st.session_state.bonuses_list
        )
        st.rerun()

    # Reality Check Callout
    st.markdown("""
    <div class="real-ctc-card">
        <div style="font-weight: 700; color: #111827; margin-bottom: 4px;">💡 REALITY OF YOUR CTC</div>
        Advertised compensation packages often include inflated multi-year figures:<br>
        <span style="font-family: 'JetBrains Mono', monospace; font-size: 0.74rem; color: #111827;">
            e.g. ₹13L Base + ₹2L Bonus + ₹5L ESOPs over 4 yrs = "20 LPA CTC"
        </span><br>
        • <b>Real Salary CTC is only ₹13 LPA</b>: Only this draws monthly salary.<br>
        • <b>Employer PF</b>: Deducted from CTC to determine Gross Salary.<br>
        • <b>TDS</b>: Taxed under Sec 192 after ₹75k Standard Deduction.<br>
        • <b>Bonuses</b>: One-time in joining or retention month.<br>
        • <b>ESOPs</b>: Vest over 4 years and do not fund monthly cashflow.
    </div>
    """, unsafe_allow_html=True)

    # Advanced Tax Settings
    with st.expander("⚙️ Advanced Tax & TDS Settings", expanded=False):
        std_deduction = st.number_input(
            "Standard Deduction (₹)",
            min_value=0.0,
            max_value=150000.0,
            value=float(DEFAULT_STANDARD_DEDUCTION),
            step=5000.0,
            help="Default ₹75,000 under Budget 2024."
        )

        nps_80ccd2 = st.number_input(
            "Employer NPS 80CCD(2) Annual (₹)",
            min_value=0.0,
            max_value=500000.0,
            value=0.0,
            step=10000.0,
            help="Exempt up to 14% of Basic pay under New Regime."
        )

        surcharge_mode = st.radio(
            "Surcharge Mode (> 50L)",
            options=["statutory", "flat_25"],
            index=0,
            format_func=lambda x: "Statutory with Marginal Relief" if x == "statutory" else "Flat 25%",
            help="Applies statutory marginal relief at ₹50 Lakhs threshold."
        )
        st.session_state.surcharge_mode = surcharge_mode

        bonus_tax_mode = st.radio(
            "Bonus TDS Mode",
            options=["upfront", "spread"],
            index=0,
            format_func=lambda x: "Upfront TDS in Bonus Month (Default)" if x == "upfront" else "Spread over remaining FY months",
            help="Upfront mode withholds bonus tax immediately so later months return to baseline take-home."
        )
        st.session_state.bonus_tax_mode = bonus_tax_mode

        st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)
        if st.button("Apply Advanced Tax Settings →", key="apply_adv_tax_btn", type="primary", use_container_width=True):
            st.rerun()


# ----------------- SIMULATION CALCULATION -----------------
current_inputs = []
for _, row in st.session_state.table_inputs.iterrows():
    current_inputs.append(MonthlyInput(
        month_index=int(row["Month Index"]),
        month_name=str(row["Month"]),
        annual_ctc=float(row["Annual CTC (₹)"]),
        employer_pf=float(row["PF Contribution (₹)"]),
        employee_pf=float(row["PF Contribution (₹)"]),
        bonus=float(row["Bonus (₹)"]),
        professional_tax=float(row["Prof. Tax (₹)"]),
        note=str(row["Notes"]) if pd.notna(row["Notes"]) else ""
    ))

simulator = PayrollSimulator(
    monthly_inputs=current_inputs,
    standard_deduction=std_deduction if 'std_deduction' in locals() else DEFAULT_STANDARD_DEDUCTION,
    nps_80ccd2_annual=nps_80ccd2 if 'nps_80ccd2' in locals() else 0.0,
    bonus_tax_mode=st.session_state.bonus_tax_mode,
    surcharge_mode=st.session_state.surcharge_mode
)
sim_result = simulator.simulate()


# Modal Dialog for Zero Tax
@st.dialog("🎉 HURRAY & CONGRATULATIONS!")
def render_zero_tax_popup(taxable_inc: float, gross_inc: float, std_ded: float):
    st.markdown(f"""
    <div style="font-family: 'Inter', sans-serif;">
        <h3 style="color: #111827; margin-top: 0; font-size: 1.25rem;">🏆 ZERO INCOME TAX PAYABLE!</h3>
        <p style="color: #4b5563; font-size: 0.88rem; line-height: 1.5;">
            Under the <b>New Tax Regime (Section 115BAC / Budget 2024)</b>, taxable income up to <b>₹12,00,000</b> receives a <b>100% Tax Rebate under Section 87A</b>.
        </p>
        <div style="background: #f9fafb; border: 1px solid #e5e7eb; padding: 12px 16px; border-radius: 4px; margin: 12px 0; font-family: 'JetBrains Mono', monospace; font-size: 0.85rem; color: #111827;">
            <div>• Annual Gross Salary: <b>₹{gross_inc:,.0f}</b></div>
            <div>• Standard Deduction: <b>₹{std_ded:,.0f}</b></div>
            <div>• Net Taxable Income: <b>₹{taxable_inc:,.0f}</b> (≤ ₹12,00,000)</div>
            <div style="color: #111827; font-weight: 700; margin-top: 6px; font-size: 0.95rem;">• Total Annual TDS: ₹0.00</div>
        </div>
        <p style="color: #6b7280; font-size: 0.8rem;">
            Every single rupee of your gross salary is credited directly to your bank account (less statutory PF & PT).
        </p>
    </div>
    """, unsafe_allow_html=True)
    if st.button("Proceed to View My Payslip Schedule →", use_container_width=True):
        st.session_state.zero_tax_dialog_shown = True
        st.rerun()


# ----------------- RIGHT PANEL: KPIS & MERGED EDITABLE PAYSLIP TABLE -----------------
with col_right:
    # 1. Zero Tax Celebration
    if sim_result.total_annual_tds == 0:
        st.balloons()
        if not st.session_state.get("zero_tax_dialog_shown", False):
            st.session_state.zero_tax_dialog_shown = True
            render_zero_tax_popup(
                taxable_inc=sim_result.final_tax_result.taxable_income,
                gross_inc=sim_result.total_annual_gross,
                std_ded=DEFAULT_STANDARD_DEDUCTION
            )
        st.markdown("""
        <div class="zero-tax-banner">
            <span>🎉 <b>HURRAY! YOUR ANNUAL INCOME TAX IS ₹0</b> — 100% Section 87A Rebate on taxable income up to ₹12 Lakhs (Gross up to ₹12.75L).</span>
            <span style="font-family: 'JetBrains Mono', monospace; font-size: 1rem; font-weight: 700;">TDS: ₹0</span>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.session_state.zero_tax_dialog_shown = False

    # 2. KPI Metrics Cards (Clean, sleek, no grey subtext clutter)
    k1, k2, k3, k4 = st.columns(4)
    with k1:
        st.markdown(f"""
        <div class="bw-kpi-card">
            <div class="bw-kpi-label">Annual Gross</div>
            <div class="bw-kpi-val">₹{sim_result.total_annual_gross:,.0f}</div>
        </div>
        """, unsafe_allow_html=True)

    with k2:
        st.markdown(f"""
        <div class="bw-kpi-card">
            <div class="bw-kpi-label">Annual Tax (TDS)</div>
            <div class="bw-kpi-val">₹{sim_result.total_annual_tds:,.0f}</div>
        </div>
        """, unsafe_allow_html=True)

    with k3:
        st.markdown(f"""
        <div class="bw-kpi-card">
            <div class="bw-kpi-label">Annual Net In-Hand</div>
            <div class="bw-kpi-val">₹{sim_result.total_annual_net_in_hand:,.0f}</div>
        </div>
        """, unsafe_allow_html=True)

    with k4:
        apr_inhand = round(sim_result.monthly_payslips[0].net_in_hand)
        st.markdown(f"""
        <div class="bw-kpi-card">
            <div class="bw-kpi-label">Monthly In-Hand (Apr)</div>
            <div class="bw-kpi-val">₹{apr_inhand:,.0f}</div>
        </div>
        """, unsafe_allow_html=True)

    # 3. MERGED EDITABLE MONTHLY PAYSLIP BREAKDOWN TABLE
    col_t_title, col_t_actions = st.columns([2.5, 2])
    with col_t_title:
        st.markdown("##### Monthly Payslip Breakdown")
    with col_t_actions:
        col_btn_recalc, col_btn_csv = st.columns([1.5, 1])
        with col_btn_recalc:
            recalc_clicked = st.button("🔄 Recalculate", use_container_width=True)
        with col_btn_csv:
            csv_data = simulation_to_dataframe(sim_result).to_csv(index=False).encode('utf-8')
            st.download_button("CSV", data=csv_data, file_name="monthly_payslips.csv", mime="text/csv", use_container_width=True)

    # High-contrast upfront ordering: Month, Annual CTC, and Net In-Hand (Bold Core Columns)
    editor_rows = []
    for i, p in enumerate(sim_result.monthly_payslips):
        inp_row = st.session_state.table_inputs.iloc[i]
        editor_rows.append({
            "Month Index": p.month_index,
            "Month": BOLD_MONTHS[p.month_index - 1],
            "Annual CTC (₹)": to_bold_inr(float(inp_row["Annual CTC (₹)"])),
            "Net In-Hand (₹)": to_bold_inr(round(p.net_in_hand)),
            "PF (₹)": float(inp_row["PF Contribution (₹)"]),
            "Bonus (₹)": float(inp_row["Bonus (₹)"]),
            "Gross Salary (₹)": round(p.gross_salary),
            "Prof. Tax (PT)": round(p.professional_tax),
            "Monthly TDS (₹)": round(p.monthly_tds),
            "Total Deductions (₹)": round(p.total_deductions),
            "Notes": str(inp_row["Notes"]) if pd.notna(inp_row["Notes"]) else ""
        })

    merged_df = pd.DataFrame(editor_rows)

    # High-contrast upfront ordering: Month, Annual CTC, and Net In-Hand
    edited_merged_df = st.data_editor(
        merged_df,
        column_config={
            "Month Index": None,  # Hide
            "Month": st.column_config.TextColumn(
                "𝗠𝗼𝗻𝘁𝗵",
                width="small",
                pinned=True
            ),
            "Annual CTC (₹)": st.column_config.TextColumn(
                "𝗔𝗻𝗻𝘂𝗮𝗹 𝗖𝗧𝗖 (₹)",
                pinned=True,
                help="Editable Annual CTC for this month"
            ),
            "Net In-Hand (₹)": st.column_config.TextColumn(
                "𝗡𝗲𝘁 𝗜𝗻-𝗛𝗮𝗻𝗱 (₹)",
                pinned=True,
                disabled=True,
                help="Calculated net monthly take-home"
            ),
            "PF (₹)": st.column_config.NumberColumn(
                "PF (₹)",
                min_value=0.0,
                step=100.0,
                format="₹%d"
            ),
            "Bonus (₹)": st.column_config.NumberColumn(
                "Bonus (₹)",
                min_value=0.0,
                step=10000.0,
                format="₹%d"
            ),
            "Gross Salary (₹)": st.column_config.NumberColumn(
                "Gross Salary (₹)",
                format="₹%d"
            ),
            "Prof. Tax (PT)": st.column_config.NumberColumn(
                "Prof. Tax (PT)",
                format="₹%d"
            ),
            "Monthly TDS (₹)": st.column_config.NumberColumn(
                "Monthly TDS (₹)",
                format="₹%d"
            ),
            "Total Deductions (₹)": st.column_config.NumberColumn(
                "Total Deductions (₹)",
                format="₹%d"
            ),
            "Notes": st.column_config.TextColumn(
                "Notes"
            )
        },
        use_container_width=True,
        hide_index=True,
        num_rows="fixed"
    )

    # Check if user made direct edits to CTC, PF, Bonus, or Notes
    inputs_changed = False
    for i in range(12):
        old_ctc = float(st.session_state.table_inputs.at[i, "Annual CTC (₹)"])
        new_ctc = parse_bold_val(edited_merged_df.at[i, "Annual CTC (₹)"])
        old_pf = float(st.session_state.table_inputs.at[i, "PF Contribution (₹)"])
        new_pf = float(edited_merged_df.at[i, "PF (₹)"])
        old_bonus = float(st.session_state.table_inputs.at[i, "Bonus (₹)"])
        new_bonus = float(edited_merged_df.at[i, "Bonus (₹)"])
        old_notes = str(st.session_state.table_inputs.at[i, "Notes"])
        new_notes = str(edited_merged_df.at[i, "Notes"])

        if (abs(old_ctc - new_ctc) > 0.01) or (abs(old_pf - new_pf) > 0.01) or (abs(old_bonus - new_bonus) > 0.01) or (old_notes != new_notes):
            inputs_changed = True
            st.session_state.table_inputs.at[i, "Annual CTC (₹)"] = new_ctc
            st.session_state.table_inputs.at[i, "PF Contribution (₹)"] = new_pf
            st.session_state.table_inputs.at[i, "Bonus (₹)"] = new_bonus
            st.session_state.table_inputs.at[i, "Notes"] = new_notes

    if inputs_changed or recalc_clicked:
        st.rerun()


# ==================== LOWER SECTION: TABS FOR DEEP-DIVE ====================
st.markdown("<hr style='border: none; border-bottom: 1px solid #e5e7eb; margin: 1.5rem 0;'>", unsafe_allow_html=True)

t1, t2, t3 = st.tabs([
    "📈 MINIMALIST TRAJECTORY CHART",
    "📑 SINGLE MONTH PAYSLIP INSPECTOR",
    "⚖️ SECTION 192 VS NAIVE /12 COMPARISON"
])

# --- TAB 1: MINIMALIST CHART (STRICTLY LIGHT BACKGROUND) ---
with t1:
    st.markdown("##### Minimal Cashflow Trajectory (Monthly)")

    months = [SHORT_MONTHS[p.month_index - 1] for p in sim_result.monthly_payslips]
    net_vals = [p.net_in_hand for p in sim_result.monthly_payslips]
    tds_vals = [p.monthly_tds for p in sim_result.monthly_payslips]
    gross_vals = [p.gross_salary for p in sim_result.monthly_payslips]

    fig_min = go.Figure()

    # Net In-Hand (Crisp Pure Black Line with markers)
    fig_min.add_trace(go.Scatter(
        x=months,
        y=net_vals,
        name="Net In-Hand",
        mode="lines+markers",
        line=dict(color="#000000", width=2.5),
        marker=dict(size=6, color="#000000")
    ))

    # Gross Salary (Neutral Dark Slate Dashed Line)
    fig_min.add_trace(go.Scatter(
        x=months,
        y=gross_vals,
        name="Gross Salary",
        mode="lines",
        line=dict(color="#4b5563", width=1.5, dash="dash")
    ))

    # Monthly TDS (Subtle Muted Gray Dotted Line)
    fig_min.add_trace(go.Scatter(
        x=months,
        y=tds_vals,
        name="Monthly TDS",
        mode="lines",
        line=dict(color="#9ca3af", width=1.5, dash="dot")
    ))

    # Light background layout
    fig_min.update_layout(
        paper_bgcolor="#ffffff",
        plot_bgcolor="#ffffff",
        xaxis=dict(
            showgrid=True,
            gridcolor="#f3f4f6",
            gridwidth=1,
            color="#374151",
            tickfont=dict(size=11, color="#374151")
        ),
        yaxis=dict(
            showgrid=True,
            gridcolor="#f3f4f6",
            gridwidth=1,
            color="#374151",
            tickfont=dict(size=11, color="#374151")
        ),
        legend=dict(
            font=dict(color="#111827", size=11),
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        ),
        margin=dict(l=40, r=20, t=30, b=40),
        hovermode="x unified",
        height=360
    )
    st.plotly_chart(fig_min, use_container_width=True)


# --- TAB 2: BUG-FREE PAYSLIP INSPECTOR ---
with t2:
    st.markdown("##### Single Month Payslip Card")
    inspect_month = st.selectbox("Select Month to Inspect", options=SHORT_MONTHS, index=0)
    m_idx = SHORT_MONTHS.index(inspect_month) + 1
    selected_p = sim_result.monthly_payslips[m_idx - 1]

    col_pi1, col_pi2 = st.columns([1.5, 1.2], gap="large")

    with col_pi1:
        st.markdown(f"#### 📄 PAYSLIP: {SHORT_MONTHS[selected_p.month_index - 1].upper()}")
        st.caption(f"Active CTC: ₹{selected_p.annual_ctc_active:,.0f} ({selected_p.annual_ctc_active/100000:.2f} LPA) • Status: {'Bonus Disbursed' if selected_p.bonus > 0 else 'Regular'}")

        c_earn, c_ded = st.columns(2)
        with c_earn:
            st.markdown("**EARNINGS**")
            st.write(f"• Basic Pay: **₹{selected_p.basic:,.2f}**")
            st.write(f"• HRA: **₹{selected_p.hra:,.2f}**")
            st.write(f"• Special Allowance: **₹{selected_p.special_allowance:,.2f}**")
            if selected_p.bonus > 0:
                st.write(f"• Bonus / Variable: **₹{selected_p.bonus:,.2f}**")
            st.markdown(f"**Gross Salary: ₹{selected_p.gross_salary:,.2f}**")

        with c_ded:
            st.markdown("**DEDUCTIONS**")
            st.write(f"• Employee PF: **₹{selected_p.employee_pf:,.2f}**")
            st.write(f"• Professional Tax: **₹{selected_p.professional_tax:,.2f}**")
            st.write(f"• Monthly TDS: **₹{selected_p.monthly_tds:,.2f}**")
            st.markdown(f"**Total Deductions: ₹{selected_p.total_deductions:,.2f}**")

        st.markdown("---")
        st.metric(
            label="NET TAKE-HOME",
            value=f"₹{selected_p.net_in_hand:,.2f}"
        )

    with col_pi2:
        st.markdown("#### ⚖️ TDS STATUS")
        st.write(f"• **Months Remaining in FY:** {selected_p.months_remaining}")
        st.write(f"• **Projected Annual Gross:** ₹{selected_p.projected_annual_gross:,.0f}")
        st.write(f"• **Projected Annual Tax:** ₹{selected_p.projected_annual_tax:,.0f}")
        st.write(f"• **Cumulative TDS Paid Prior:** ₹{selected_p.cumulative_tds_paid - selected_p.monthly_tds:,.0f}")
        st.write(f"• **Calculated Month TDS:** ₹{selected_p.monthly_tds:,.0f}")


# --- TAB 3: DYNAMIC VS NAIVE ---
with t3:
    st.markdown("##### Dynamic Section 192 vs. Naive Flat (/12) Calculators")

    comp = compare_with_naive_calculator(sim_result)
    comp_df = pd.DataFrame(comp["monthly_comparison"])
    comp_display = comp_df.rename(columns={
        "month": "Month",
        "actual_tds": "Actual Sec 192 TDS (₹)",
        "naive_tds": "Naive Flat TDS (₹)",
        "difference": "Variance / Gap (₹)",
        "actual_net": "Actual In-Hand (₹)",
        "naive_net": "Naive In-Hand (₹)"
    })
    for col in ["Actual Sec 192 TDS (₹)", "Naive Flat TDS (₹)", "Variance / Gap (₹)", "Actual In-Hand (₹)", "Naive In-Hand (₹)"]:
        comp_display[col] = comp_display[col].apply(lambda x: f"₹{round(x):,.0f}")

    st.dataframe(
        comp_display,
        use_container_width=True,
        hide_index=True
    )
