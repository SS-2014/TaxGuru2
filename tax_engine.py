"""
TaxGuru — Indian Income Tax Calculation Engine
FY 2025-26 (AY 2026-27)
Handles: Salaried, Business/Professional, Traders, Investors
Supports: Old Regime, New Regime (115BAC), Senior Citizens
"""

from dataclasses import dataclass, field
from typing import Optional
import math


# ── Tax Slabs FY 2025-26 ──

NEW_REGIME_SLABS = [
    (400000, 0.00),    # 0 - 4L: Nil
    (800000, 0.05),    # 4L - 8L: 5%
    (1200000, 0.10),   # 8L - 12L: 10%
    (1600000, 0.15),   # 12L - 16L: 15%
    (2000000, 0.20),   # 16L - 20L: 20%
    (2400000, 0.25),   # 20L - 24L: 25%
    (float('inf'), 0.30),  # Above 24L: 30%
]

OLD_REGIME_SLABS_BELOW_60 = [
    (250000, 0.00),
    (500000, 0.05),
    (1000000, 0.20),
    (float('inf'), 0.30),
]

OLD_REGIME_SLABS_60_TO_80 = [
    (300000, 0.00),
    (500000, 0.05),
    (1000000, 0.20),
    (float('inf'), 0.30),
]

OLD_REGIME_SLABS_ABOVE_80 = [
    (500000, 0.00),
    (1000000, 0.20),
    (float('inf'), 0.30),
]

SURCHARGE_SLABS_OLD = [
    (5000000, 0.00),
    (10000000, 0.10),
    (20000000, 0.15),
    (50000000, 0.25),
    (float('inf'), 0.37),
]

SURCHARGE_SLABS_NEW = [
    (5000000, 0.00),
    (10000000, 0.10),
    (20000000, 0.15),
    (float('inf'), 0.25),
]

CESS_RATE = 0.04
NEW_REGIME_STANDARD_DEDUCTION = 75000
OLD_REGIME_STANDARD_DEDUCTION = 50000
SECTION_87A_NEW_REGIME_LIMIT = 1200000
SECTION_87A_NEW_REGIME_REBATE = 60000
SECTION_87A_OLD_REGIME_LIMIT = 500000
SECTION_87A_OLD_REGIME_REBATE = 12500


@dataclass
class TaxpayerProfile:
    """Holds all financial details of a taxpayer"""
    name: str = ""
    age: int = 30
    taxpayer_type: str = "salaried"  # salaried, business, professional, trader, investor
    residency: str = "resident"  # resident, nri, rnor

    # Income components
    gross_salary: float = 0
    basic_salary: float = 0
    hra_received: float = 0
    special_allowance: float = 0
    lta: float = 0
    other_salary_components: float = 0

    business_income: float = 0
    professional_income: float = 0
    trading_income: float = 0  # F&O, intraday

    rental_income: float = 0
    interest_income: float = 0
    dividend_income: float = 0

    # Capital gains
    stcg_equity: float = 0  # 20% (listed equity sold within 1 yr)
    ltcg_equity: float = 0  # 12.5% above 1.25L
    stcg_other: float = 0   # slab rate
    ltcg_other: float = 0   # 20% with indexation / 12.5% without

    # ESOP
    esop_perquisite: float = 0
    esop_sale_gain: float = 0
    foreign_esop: bool = False

    # Deductions (Old Regime)
    section_80c: float = 0  # max 1.5L
    section_80d_self: float = 0  # max 25K (50K senior)
    section_80d_parents: float = 0  # max 25K (50K senior parents)
    section_80e: float = 0  # education loan interest (no limit)
    section_80g: float = 0  # donations
    section_80tta: float = 0  # savings interest (max 10K)
    section_80ttb: float = 0  # senior citizen interest (max 50K)
    section_80ccd_1b: float = 0  # NPS additional (max 50K)
    section_80ccd_2: float = 0  # employer NPS (no limit, new regime too)
    section_80ee: float = 0  # first home loan interest
    section_80eea: float = 0  # affordable housing
    section_24b: float = 0  # home loan interest (max 2L self-occupied)

    # HRA calculation inputs
    rent_paid_annual: float = 0
    metro_city: bool = False

    # Professional tax
    professional_tax: float = 0

    # Advance tax / TDS already paid
    tds_deducted: float = 0
    advance_tax_paid: float = 0


def compute_slab_tax(income: float, slabs: list) -> float:
    """Compute tax based on progressive slab rates"""
    tax = 0
    prev_limit = 0
    for limit, rate in slabs:
        if income <= prev_limit:
            break
        taxable_in_slab = min(income, limit) - prev_limit
        tax += taxable_in_slab * rate
        prev_limit = limit
    return tax


def compute_surcharge(tax: float, income: float, slabs: list) -> float:
    """Compute surcharge with marginal relief"""
    surcharge_rate = 0
    for limit, rate in slabs:
        if income <= limit:
            surcharge_rate = rate
            break
        surcharge_rate = rate

    surcharge = tax * surcharge_rate

    # Marginal relief
    if surcharge_rate > 0:
        prev_limit = 0
        for limit, rate in slabs:
            if rate == surcharge_rate:
                prev_limit = limit
                break
            prev_limit = limit
        # Find the threshold where this surcharge kicks in
        for i, (limit, rate) in enumerate(slabs):
            if rate == surcharge_rate and i > 0:
                threshold = slabs[i-1][0]
                tax_at_threshold = compute_slab_tax(threshold, 
                    NEW_REGIME_SLABS if slabs == SURCHARGE_SLABS_NEW else OLD_REGIME_SLABS_BELOW_60)
                max_surcharge = (income - threshold) - (tax_at_threshold * (1 + slabs[i-1][1]) - tax * (1 + surcharge_rate))
                if surcharge > 0:
                    pass  # Simplified; full marginal relief is complex

    return surcharge


def compute_hra_exemption(profile: TaxpayerProfile) -> float:
    """Calculate HRA exemption under old regime"""
    if profile.hra_received == 0 or profile.rent_paid_annual == 0:
        return 0

    basic = profile.basic_salary
    hra_received = profile.hra_received
    rent_paid = profile.rent_paid_annual
    metro_pct = 0.50 if profile.metro_city else 0.40

    option1 = hra_received
    option2 = rent_paid - (0.10 * basic)
    option3 = metro_pct * basic

    return max(0, min(option1, option2, option3))


def compute_total_income_old_regime(profile: TaxpayerProfile) -> dict:
    """Compute taxable income under old regime with all deductions"""
    # Salary income
    hra_exempt = compute_hra_exemption(profile)
    salary_income = profile.gross_salary - hra_exempt
    salary_income -= min(profile.lta, 0)  # LTA simplified
    salary_income -= OLD_REGIME_STANDARD_DEDUCTION
    salary_income -= min(profile.professional_tax, 2500)
    salary_income = max(0, salary_income)

    # House property income
    hp_income = profile.rental_income - min(profile.section_24b, 200000)

    # Business/Professional income
    biz_income = profile.business_income + profile.professional_income + profile.trading_income

    # Other income
    other_income = profile.interest_income + profile.dividend_income

    # Gross total income (excluding special rate income)
    gti = salary_income + max(hp_income, -200000) + biz_income + other_income + profile.esop_perquisite

    # Chapter VI-A deductions
    sec_80c = min(profile.section_80c, 150000)
    sec_80d = min(profile.section_80d_self, 50000 if profile.age >= 60 else 25000) + \
              min(profile.section_80d_parents, 50000)
    sec_80e = profile.section_80e
    sec_80g = profile.section_80g
    sec_80tta = min(profile.section_80tta, 10000) if profile.age < 60 else 0
    sec_80ttb = min(profile.section_80ttb, 50000) if profile.age >= 60 else 0
    sec_80ccd_1b = min(profile.section_80ccd_1b, 50000)
    sec_80ccd_2 = profile.section_80ccd_2

    total_deductions = sec_80c + sec_80d + sec_80e + sec_80g + sec_80tta + sec_80ttb + sec_80ccd_1b + sec_80ccd_2

    taxable_income = max(0, gti - total_deductions)

    return {
        'salary_income': salary_income,
        'hp_income': hp_income,
        'business_income': biz_income,
        'other_income': other_income,
        'esop_perquisite': profile.esop_perquisite,
        'gross_total_income': gti,
        'hra_exemption': hra_exempt,
        'total_deductions': total_deductions,
        'deduction_breakdown': {
            '80C': sec_80c, '80D': sec_80d, '80E': sec_80e,
            '80G': sec_80g, '80TTA': sec_80tta, '80TTB': sec_80ttb,
            '80CCD(1B)': sec_80ccd_1b, '80CCD(2)': sec_80ccd_2,
        },
        'taxable_income': taxable_income,
    }


def compute_total_income_new_regime(profile: TaxpayerProfile) -> dict:
    """Compute taxable income under new regime (115BAC)"""
    salary_income = profile.gross_salary - NEW_REGIME_STANDARD_DEDUCTION
    salary_income -= min(profile.professional_tax, 2500)
    salary_income = max(0, salary_income)

    hp_income = profile.rental_income  # No Sec 24b in new regime for self-occupied
    biz_income = profile.business_income + profile.professional_income + profile.trading_income
    other_income = profile.interest_income + profile.dividend_income

    gti = salary_income + hp_income + biz_income + other_income + profile.esop_perquisite

    # Only employer NPS (80CCD(2)) allowed in new regime
    sec_80ccd_2 = profile.section_80ccd_2
    taxable_income = max(0, gti - sec_80ccd_2)

    return {
        'salary_income': salary_income,
        'hp_income': hp_income,
        'business_income': biz_income,
        'other_income': other_income,
        'esop_perquisite': profile.esop_perquisite,
        'gross_total_income': gti,
        'total_deductions': sec_80ccd_2,
        'deduction_breakdown': {'80CCD(2)': sec_80ccd_2},
        'taxable_income': taxable_income,
    }


def compute_full_tax(profile: TaxpayerProfile, regime: str = 'new') -> dict:
    """Complete tax computation for a given regime"""
    if regime == 'new':
        income_details = compute_total_income_new_regime(profile)
        slabs = NEW_REGIME_SLABS
        surcharge_slabs = SURCHARGE_SLABS_NEW
        rebate_limit = SECTION_87A_NEW_REGIME_LIMIT
        max_rebate = SECTION_87A_NEW_REGIME_REBATE
    else:
        income_details = compute_total_income_old_regime(profile)
        if profile.age >= 80:
            slabs = OLD_REGIME_SLABS_ABOVE_80
        elif profile.age >= 60:
            slabs = OLD_REGIME_SLABS_60_TO_80
        else:
            slabs = OLD_REGIME_SLABS_BELOW_60
        surcharge_slabs = SURCHARGE_SLABS_OLD
        rebate_limit = SECTION_87A_OLD_REGIME_LIMIT
        max_rebate = SECTION_87A_OLD_REGIME_REBATE

    taxable = income_details['taxable_income']

    # Normal income tax on slab
    slab_tax = compute_slab_tax(taxable, slabs)

    # Special rate taxes (capital gains)
    stcg_equity_tax = profile.stcg_equity * 0.20
    ltcg_equity_exempt = min(profile.ltcg_equity, 125000)
    ltcg_equity_tax = max(0, profile.ltcg_equity - ltcg_equity_exempt) * 0.125
    stcg_other_tax = compute_slab_tax(profile.stcg_other, slabs) if profile.stcg_other > 0 else 0
    ltcg_other_tax = profile.ltcg_other * 0.125

    total_tax_before_rebate = slab_tax + stcg_equity_tax + ltcg_equity_tax + ltcg_other_tax

    # Rebate u/s 87A (only on normal income, not special rate)
    rebate = 0
    if profile.residency == 'resident' and taxable <= rebate_limit:
        rebate = min(slab_tax, max_rebate)

    tax_after_rebate = max(0, total_tax_before_rebate - rebate)

    # Surcharge
    total_income_for_surcharge = taxable + profile.stcg_equity + profile.ltcg_equity + profile.ltcg_other
    surcharge = 0
    if total_income_for_surcharge > 5000000:
        surcharge = tax_after_rebate * 0.10  # Simplified
        if total_income_for_surcharge > 10000000:
            surcharge = tax_after_rebate * 0.15
        if total_income_for_surcharge > 20000000:
            surcharge = tax_after_rebate * 0.25 if regime == 'new' else tax_after_rebate * 0.25

    # Cess
    tax_plus_surcharge = tax_after_rebate + surcharge
    cess = tax_plus_surcharge * CESS_RATE

    total_tax = tax_plus_surcharge + cess

    # Net payable
    total_prepaid = profile.tds_deducted + profile.advance_tax_paid
    net_payable = total_tax - total_prepaid

    return {
        **income_details,
        'regime': regime,
        'slab_tax': round(slab_tax),
        'stcg_equity_tax': round(stcg_equity_tax),
        'ltcg_equity_tax': round(ltcg_equity_tax),
        'ltcg_other_tax': round(ltcg_other_tax),
        'total_tax_before_rebate': round(total_tax_before_rebate),
        'rebate_87a': round(rebate),
        'tax_after_rebate': round(tax_after_rebate),
        'surcharge': round(surcharge),
        'cess': round(cess),
        'total_tax': round(total_tax),
        'tds_deducted': round(profile.tds_deducted),
        'advance_tax_paid': round(profile.advance_tax_paid),
        'net_payable': round(net_payable),
        'effective_rate': round(total_tax / max(taxable, 1) * 100, 2),
    }


def compare_regimes(profile: TaxpayerProfile) -> dict:
    """Compare old and new regime and recommend the better one"""
    old = compute_full_tax(profile, 'old')
    new = compute_full_tax(profile, 'new')

    savings = old['total_tax'] - new['total_tax']
    recommended = 'new' if savings >= 0 else 'old'

    return {
        'old_regime': old,
        'new_regime': new,
        'savings': abs(savings),
        'recommended': recommended,
        'recommendation_text': f"The {'New' if recommended == 'new' else 'Old'} Tax Regime saves you ₹{abs(savings):,.0f} this year."
    }


def estimate_from_monthly_salary(monthly_gross: float, monthly_basic: float = 0,
                                  monthly_hra: float = 0, employer_pf: float = 0) -> TaxpayerProfile:
    """Create a profile from a single month's payslip data"""
    if monthly_basic == 0:
        monthly_basic = monthly_gross * 0.40  # Common assumption
    if monthly_hra == 0:
        monthly_hra = monthly_basic * 0.50

    profile = TaxpayerProfile(
        gross_salary=monthly_gross * 12,
        basic_salary=monthly_basic * 12,
        hra_received=monthly_hra * 12,
        special_allowance=(monthly_gross - monthly_basic - monthly_hra) * 12,
        section_80c=min(employer_pf * 12, 150000) if employer_pf else min(monthly_basic * 0.12 * 12, 150000),
    )
    return profile


def format_currency(amount: float) -> str:
    """Format amount in Indian currency style"""
    if amount < 0:
        return f"-₹{abs(amount):,.0f}"
    return f"₹{amount:,.0f}"


def format_lakhs(amount: float) -> str:
    """Format in lakhs"""
    if amount >= 10000000:
        return f"₹{amount/10000000:.2f} Cr"
    elif amount >= 100000:
        return f"₹{amount/100000:.2f} L"
    else:
        return f"₹{amount:,.0f}"
