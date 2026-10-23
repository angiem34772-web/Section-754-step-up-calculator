"""Read and validate the CSV inputs."""

from __future__ import annotations

import csv
from datetime import date
from pathlib import Path

from .models import Asset, Sale


def _num(value: str | None, default=None):
    value = (value or "").strip()
    return float(value.replace(",", "")) if value else default


def load_assets(path: str | Path) -> list[Asset]:
    with open(path, newline="") as f:
        assets = [
            Asset(
                asset_id=row["asset_id"].strip(),
                description=row["description"].strip(),
                asset_type=row["asset_type"].strip(),
                tax_basis=_num(row["tax_basis"], 0.0),
                fair_market_value=_num(row["fair_market_value"], 0.0),
                prior_depreciation=_num(row.get("prior_depreciation"), 0.0),
                recovery_years=_num(row.get("recovery_years")),
                remaining_years=_num(row.get("remaining_years")),
            )
            for row in csv.DictReader(f)
        ]
    ids = [a.asset_id for a in assets]
    if len(ids) != len(set(ids)):
        raise ValueError("asset_id values must be unique")
    return assets


def load_sale(path: str | Path) -> Sale:
    with open(path, newline="") as f:
        rows = list(csv.DictReader(f))
    if len(rows) != 1:
        raise ValueError("sale.csv should have exactly one sale")
    row = rows[0]
    return Sale(
        partnership=row["partnership"].strip(),
        seller=row["seller"].strip(),
        buyer=row["buyer"].strip(),
        sale_date=date.fromisoformat(row["sale_date"].strip()),
        interest_sold=_num(row["interest_sold"]),
        cash_price=_num(row["cash_price"]),
        partnership_liabilities=_num(row["partnership_liabilities"], 0.0),
        liability_share=_num(row.get("liability_share")),
        seller_outside_basis=_num(row.get("seller_outside_basis")),
        election_754=(row.get("election_754") or "yes").strip().lower() in ("yes", "y", "true", "1"),
        bonus_pct=_num(row.get("bonus_pct"), 0.0),
        tax_rate=_num(row.get("tax_rate"), 0.37),
    )


def load_inputs(folder: str | Path) -> tuple[list[Asset], Sale]:
    folder = Path(folder)
    return load_assets(folder / "assets.csv"), load_sale(folder / "sale.csv")
