"""The IRC 743(b) basis adjustment and its allocation among assets under IRC 755.

Steps, following the regulations:

1. Buyer's outside basis: cash paid plus the buyer's share of partnership debt
   (IRC 742, 1012, 752(d)).
2. Partnership gross value from the price, with any excess over the listed assets
   treated as goodwill (residual method, Reg. 1.755-1(a)(4) and (a)(5)).
3. A hypothetical sale of every asset for fair market value (Reg. 1.743-1(d)(2)):
   the buyer's share of inside basis is previously taxed capital plus debt share.
4. The 743(b) adjustment is outside basis minus share of inside basis (Reg. 1.743-1(b)).
5. The adjustment is split between ordinary income property and capital gain
   property, then among the items in each class (Reg. 1.755-1(b)(2) and (b)(3)).
"""

from __future__ import annotations

from .depreciation import recovery_schedule
from .models import ASSET_TYPES, AllocationLine, Asset, Flag, Results, Sale

SUBSTANTIAL_LOSS = 250_000  # IRC 743(d)


def compute(assets: list[Asset], sale: Sale) -> Results:
    pct = sale.interest_sold
    if not 0 < pct <= 1:
        raise ValueError("interest_sold must be between 0 and 1")
    flags: list[Flag] = []
    debt = sale.partnership_liabilities

    # 1. Buyer's cost basis in the interest.
    outside_basis = sale.cash_price + sale.debt_share

    # 2. Gross value implied by the price, and residual goodwill.
    gross_value = sale.cash_price / pct + debt
    listed_fmv = sum(a.fair_market_value for a in assets)
    residual = gross_value - listed_fmv
    assets = list(assets)
    if residual > 0.5:
        goodwill = next((a for a in assets if a.asset_type == "section_197"), None)
        if goodwill:
            assets[assets.index(goodwill)] = Asset(
                goodwill.asset_id, goodwill.description, "section_197", goodwill.tax_basis,
                goodwill.fair_market_value + residual, goodwill.prior_depreciation,
                goodwill.recovery_years, goodwill.remaining_years,
            )
        else:
            assets.append(Asset("GW", "Goodwill (residual value from the price)", "section_197", 0.0, residual))
        flags.append(Flag("RESIDUAL_GOODWILL", "Price exceeds the listed asset values; the excess is goodwill "
                          "under the residual method (Reg. 1.755-1(a)(5))", residual))
    elif residual < -0.5:
        flags.append(Flag("PRICE_BELOW_ASSET_VALUES", "Price is below the listed asset values; the difference is "
                          "spread across each class in proportion to value (Reg. 1.755-1(b)(3))", residual))
        residual = 0.0
    else:
        residual = 0.0

    # 3. Hypothetical sale of all assets at fair market value.
    lines = _allocation_lines(assets, pct)
    share_of_gain = sum(line.share_of_gain for line in lines)
    total_basis = sum(a.tax_basis for a in assets)
    total_fmv = sum(a.fair_market_value for a in assets)
    cash_on_liquidation = pct * (total_fmv - debt)
    previously_taxed_capital = cash_on_liquidation - share_of_gain
    inside_basis_share = previously_taxed_capital + sale.debt_share

    # 4. The adjustment.
    adjustment = outside_basis - inside_basis_share

    # IRC 743(d): a substantial built-in loss makes the adjustment mandatory.
    partnership_loss = total_basis - total_fmv
    buyer_loss = -share_of_gain
    mandatory = partnership_loss > SUBSTANTIAL_LOSS or buyer_loss > SUBSTANTIAL_LOSS
    applies = sale.election_754 or mandatory
    if mandatory:
        flags.append(Flag("MANDATORY_743B", "Substantial built-in loss: the 743(b) adjustment is required even "
                          "without a 754 election (IRC 743(d))", max(partnership_loss, buyer_loss)))
    elif sale.election_754:
        flags.append(Flag("754_ELECTION", "754 election in effect: the adjustment applies (attach the election to "
                          "the timely filed return for the year of the sale if not already made, Reg. 1.754-1(b))",
                          adjustment))
    else:
        flags.append(Flag("NO_754_ELECTION", "No 754 election: the buyer gets no inside basis adjustment. The "
                          "partnership can still elect on its timely filed return for this year (Reg. 1.754-1(b))",
                          adjustment))

    # 5. Allocate under Reg. 1.755-1(b).
    ordinary_share = sum(l.share_of_gain for l in lines if l.asset_class == "ordinary")
    capital_class = adjustment - ordinary_share
    ordinary_class = ordinary_share
    capital_basis = pct * sum(l.basis for l in lines if l.asset_class == "capital")
    if capital_class < -capital_basis:
        excess = -capital_basis - capital_class
        capital_class += excess
        ordinary_class -= excess
        flags.append(Flag("CAPITAL_DECREASE_LIMITED", "Decrease to capital gain property exceeded its basis; the "
                          "excess reduces ordinary income property (Reg. 1.755-1(b)(2)(i))", excess))
    lines = (_allocate_class([l for l in lines if l.asset_class == "ordinary"], ordinary_class, pct, flags)
             + _allocate_class([l for l in lines if l.asset_class == "capital"], capital_class, pct, flags))

    by_asset: dict[str, float] = {}
    for line in lines:
        by_asset[line.asset_id] = by_asset.get(line.asset_id, 0.0) + line.adjustment
    if not applies:
        by_asset = {k: 0.0 for k in by_asset}

    depreciation = {
        a.asset_id: recovery_schedule(a, by_asset.get(a.asset_id, 0.0), sale.sale_date, sale.bonus_pct)
        for a in assets
    }
    depreciation = {k: v for k, v in depreciation.items() if v}

    if ordinary_share > 0.5:
        flags.append(Flag("751_EXCHANGE", "The sale includes 'hot assets' (receivables, inventory, depreciation "
                          "recapture): part of the seller's gain is ordinary (IRC 751(a)), and the partnership "
                          "files Form 8308", ordinary_share))
    if sale.sale_date.month >= 10 and any(a.recovery == "200DB-HY" for a in assets):
        flags.append(Flag("MID_QUARTER_CHECK", "Sale in the 4th quarter: test whether the mid-quarter convention "
                          "applies to the personal property step-up"))
    if not sale.election_754 and not mandatory and adjustment > 0:
        flags.append(Flag("ELECTION_OPPORTUNITY", "A 754 election would give the buyer this step-up", adjustment))

    seller = _seller(sale, lines, assets, outside_basis, pct) if sale.seller_outside_basis is not None else None

    return Results(
        sale=sale, assets=assets, gross_value=gross_value, residual_goodwill=residual,
        outside_basis=outside_basis, cash_on_liquidation=cash_on_liquidation, share_of_gain=share_of_gain,
        previously_taxed_capital=previously_taxed_capital, inside_basis_share=inside_basis_share,
        adjustment=adjustment, adjustment_applies=applies, mandatory=mandatory,
        ordinary_class=ordinary_class, capital_class=capital_class, lines=lines, by_asset=by_asset,
        depreciation=depreciation, seller=seller, flags=flags,
    )


def _allocation_lines(assets: list[Asset], pct: float) -> list[AllocationLine]:
    """Split each asset into Reg. 1.755-1 items: recapture is its own ordinary income item."""
    lines = []
    for a in assets:
        cls = ASSET_TYPES[a.asset_type]["class"]
        if cls is None:  # money can't take a basis adjustment
            continue
        recapture = a.recapture
        if recapture:
            lines.append(AllocationLine(a.asset_id, f"{a.description} - 1245 recapture", "ordinary",
                                        0.0, recapture, pct * recapture))
        lines.append(AllocationLine(a.asset_id, a.description, cls, a.tax_basis,
                                    a.fair_market_value - recapture, pct * (a.gain - recapture)))
    return lines


def _allocate_class(lines: list[AllocationLine], class_total: float, pct: float, flags: list[Flag]):
    """Reg. 1.755-1(b)(3): each item gets the buyer's share of its gain or loss, less a pro rata
    share (by fair market value) of any difference between the class total and those shares.
    A decrease can't take an item below zero; the excess moves to the other items by basis."""
    if not lines:
        return []
    difference = sum(l.share_of_gain for l in lines) - class_total
    class_fmv = sum(l.fmv for l in lines)
    amounts = [
        l.share_of_gain - (difference * l.fmv / class_fmv if class_fmv else difference / len(lines))
        for l in lines
    ]
    floors = [-pct * l.basis for l in lines]
    for _ in range(len(lines)):
        excess = sum(f - a for a, f in zip(amounts, floors) if a < f)
        if excess < 0.005:
            break
        amounts = [max(a, f) for a, f in zip(amounts, floors)]
        room = [a - f for a, f in zip(amounts, floors)]  # buyer's remaining basis in each item
        open_basis = sum(room)
        if open_basis <= 0:
            break
        amounts = [a - excess * r / open_basis for a, r in zip(amounts, room)]
        flags.append(Flag("ITEM_DECREASE_LIMITED", "A decrease would take an item below zero basis; the excess "
                          "was moved to other items in the class by relative basis", excess))
    return [AllocationLine(l.asset_id, l.description, l.asset_class, l.basis, l.fmv, l.share_of_gain, a)
            for l, a in zip(lines, amounts)]


def _seller(sale: Sale, lines, assets, outside_basis, pct) -> dict[str, float]:
    """Seller's gain and its character (IRC 741, 751(a), Reg. 1.1(h)-1 look-through)."""
    amount_realized = sale.cash_price + sale.debt_share
    gain = amount_realized - sale.seller_outside_basis
    ordinary = sum(l.share_of_gain for l in lines if l.asset_class == "ordinary")
    capital = gain - ordinary
    unrecaptured_1250 = sum(
        pct * max(0.0, min(a.gain, a.prior_depreciation))
        for a in assets if a.asset_type in ("residential_building", "nonresidential_building")
    )
    unrecaptured_1250 = max(0.0, min(unrecaptured_1250, capital))
    return {
        "cash_received": sale.cash_price,
        "debt_relief": sale.debt_share,
        "amount_realized": amount_realized,
        "outside_basis": sale.seller_outside_basis,
        "total_gain": gain,
        "ordinary_751": ordinary,
        "capital_gain": capital,
        "unrecaptured_1250": unrecaptured_1250,
        "other_long_term": capital - unrecaptured_1250,
    }
