"""Data structures for the partnership balance sheet, the sale, and the results."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

# How each kind of asset is treated. "class" is the Reg. 1.755-1(a) class for the
# asset's own gain; Section 1245 recapture is split out as ordinary income property.
ASSET_TYPES = {
    "cash": {"class": None, "recovery": None},
    "receivable": {"class": "ordinary", "recovery": None},
    "inventory": {"class": "ordinary", "recovery": None},
    "land": {"class": "capital", "recovery": None},
    "residential_building": {"class": "capital", "recovery": "SL-MM"},
    "nonresidential_building": {"class": "capital", "recovery": "SL-MM"},
    "personal_property": {"class": "capital", "recovery": "200DB-HY"},
    "capital_asset": {"class": "capital", "recovery": None},
    "section_197": {"class": "capital", "recovery": "SL-197"},
}

DEFAULT_RECOVERY_YEARS = {
    "residential_building": 27.5,
    "nonresidential_building": 39,
    "personal_property": 7,
    "section_197": 15,
}


@dataclass(frozen=True)
class Asset:
    """One line of the partnership's tax balance sheet on the sale date."""

    asset_id: str
    description: str
    asset_type: str  # a key of ASSET_TYPES
    tax_basis: float  # partnership's adjusted (common) basis
    fair_market_value: float
    prior_depreciation: float = 0.0  # depreciation/amortization taken to date (recapture and 1250 tests)
    recovery_years: float | None = None  # MACRS recovery period for a new step-up
    remaining_years: float | None = None  # remaining recovery period, used for a step-down

    def __post_init__(self):
        if self.asset_type not in ASSET_TYPES:
            raise ValueError(f"{self.asset_id}: unknown asset_type {self.asset_type!r}")

    @property
    def gain(self) -> float:
        return self.fair_market_value - self.tax_basis

    @property
    def recapture(self) -> float:
        """Section 1245 ordinary recapture built into the asset (zero for real property)."""
        if self.asset_type not in ("personal_property", "section_197"):
            return 0.0
        return max(0.0, min(self.gain, self.prior_depreciation))

    @property
    def recovery(self) -> str | None:
        return ASSET_TYPES[self.asset_type]["recovery"]

    @property
    def years(self) -> float | None:
        return self.recovery_years or DEFAULT_RECOVERY_YEARS.get(self.asset_type)


@dataclass(frozen=True)
class Sale:
    """A purchase of an existing partner's interest by a new partner (IRC 743)."""

    partnership: str
    seller: str
    buyer: str
    sale_date: date
    interest_sold: float  # e.g. 0.10 for a 10% interest
    cash_price: float
    partnership_liabilities: float  # total partnership debt
    liability_share: float | None = None  # buyer's IRC 752 share; defaults to interest_sold
    seller_outside_basis: float | None = None
    election_754: bool = True
    bonus_pct: float = 0.0  # IRC 168(k) bonus on eligible step-up; 0 if not claimed
    tax_rate: float = 0.37  # buyer's marginal rate, for the illustrative benefit only

    @property
    def debt_share(self) -> float:
        share = self.interest_sold if self.liability_share is None else self.liability_share
        return share * self.partnership_liabilities


@dataclass(frozen=True)
class AllocationLine:
    """One Reg. 1.755-1 'item': an asset, or the recapture piece of an asset."""

    asset_id: str
    description: str
    asset_class: str  # "ordinary" or "capital"
    basis: float  # partnership basis in the item
    fmv: float
    share_of_gain: float  # buyer's share of gain/(loss) in the hypothetical sale
    adjustment: float = 0.0


@dataclass(frozen=True)
class Flag:
    code: str
    message: str
    amount: float | None = None


@dataclass
class Results:
    sale: Sale
    assets: list[Asset]
    gross_value: float
    residual_goodwill: float
    outside_basis: float
    cash_on_liquidation: float
    share_of_gain: float
    previously_taxed_capital: float
    inside_basis_share: float
    adjustment: float
    adjustment_applies: bool
    mandatory: bool
    ordinary_class: float
    capital_class: float
    lines: list[AllocationLine]
    by_asset: dict[str, float]
    depreciation: dict[str, dict[int, float]]  # asset_id -> year -> deduction
    seller: dict[str, float] | None
    flags: list[Flag] = field(default_factory=list)

    @property
    def years(self) -> list[int]:
        return sorted({y for sched in self.depreciation.values() for y in sched})

    def deduction(self, year: int) -> float:
        return sum(sched.get(year, 0.0) for sched in self.depreciation.values())
