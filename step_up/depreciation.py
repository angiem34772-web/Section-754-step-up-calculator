"""Cost recovery for a 743(b) adjustment.

Under Reg. 1.743-1(j)(4)(i)(B), an increase in the basis of recovery property is
treated as newly purchased property placed in service on the date of the transfer,
so it starts a fresh recovery period. A decrease is taken into account over the
property's remaining recovery period (Reg. 1.743-1(j)(4)(ii)).
"""

from __future__ import annotations

from datetime import date


def macrs_declining_balance(amount: float, years: int, start_year: int, factor: float = 2.0) -> dict[int, float]:
    """MACRS declining balance with a switch to straight line, half-year convention.

    Reproduces IRS Pub. 946 Table A-1 (200% for 3/5/7/10-year property, 150% for 15/20-year).
    """
    schedule: dict[int, float] = {}
    remaining = amount
    rate = factor / years
    for t in range(years + 1):
        if t == years:
            deduction = remaining
        else:
            fraction = 0.5 if t == 0 else 1.0
            declining = remaining * rate * fraction
            remaining_period = years - t + (0.5 if t > 0 else 0.0)
            straight_line = remaining / remaining_period * fraction
            deduction = max(declining, straight_line)
        schedule[start_year + t] = deduction
        remaining -= deduction
    return schedule


def straight_line_mid_month(amount: float, years: float, placed_in_service: date) -> dict[int, float]:
    """Straight line, mid-month convention (residential 27.5-year and nonresidential 39-year)."""
    annual = amount / years
    schedule: dict[int, float] = {}
    remaining = amount
    year = placed_in_service.year
    first = annual * (12 - placed_in_service.month + 0.5) / 12
    while remaining > 0.005:
        deduction = min(first if year == placed_in_service.year else annual, remaining)
        schedule[year] = deduction
        remaining -= deduction
        year += 1
    return schedule


def amortize_197(amount: float, acquired: date, years: int = 15) -> dict[int, float]:
    """Ratable monthly amortization over 15 years, starting the month acquired (IRC 197(a))."""
    monthly = amount / (years * 12)
    schedule: dict[int, float] = {}
    months_left = years * 12
    year, months = acquired.year, 12 - acquired.month + 1
    while months_left > 0:
        months = min(months, months_left)
        schedule[year] = monthly * months
        months_left -= months
        year, months = year + 1, 12
    return schedule


def step_down(amount: float, remaining_years: float, start_year: int) -> dict[int, float]:
    """Spread a negative adjustment evenly over the remaining recovery period (simplified)."""
    whole = int(remaining_years)
    pieces = [amount / remaining_years] * whole
    if remaining_years > whole:
        pieces.append(amount - sum(pieces))
    return {start_year + i: piece for i, piece in enumerate(pieces)}


def recovery_schedule(asset, adjustment: float, transfer: date, bonus_pct: float = 0.0) -> dict[int, float]:
    """Deductions by tax year for one asset's share of the 743(b) adjustment."""
    if not asset.recovery or abs(adjustment) < 0.005:
        return {}
    if adjustment < 0:
        remaining = asset.remaining_years or asset.years
        return step_down(adjustment, remaining, transfer.year)
    if asset.recovery == "SL-MM":
        return straight_line_mid_month(adjustment, asset.years, transfer)
    if asset.recovery == "SL-197":
        return amortize_197(adjustment, transfer, int(asset.years))
    # MACRS personal property; bonus (IRC 168(k)) applies to recovery periods of 20 years or less.
    bonus = adjustment * bonus_pct
    factor = 1.5 if asset.years >= 15 else 2.0
    schedule = macrs_declining_balance(adjustment - bonus, int(asset.years), transfer.year, factor)
    schedule[transfer.year] += bonus
    return {year: amount for year, amount in schedule.items() if abs(amount) >= 0.005}
