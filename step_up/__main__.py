"""Command line entry point: python -m step_up"""

from __future__ import annotations

import argparse
from pathlib import Path

from .adjustment import compute
from .excel_export import export
from .loader import load_inputs

ROOT = Path(__file__).resolve().parent.parent


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Compute a Section 743(b) step-up and allocate it under Section 755.")
    parser.add_argument("--data", default=ROOT / "sample_data", help="folder with assets.csv and sale.csv")
    parser.add_argument("--out", default=ROOT / "output" / "step_up_report.xlsx", help="Excel file to write")
    args = parser.parse_args(argv)

    assets, sale = load_inputs(args.data)
    r = compute(assets, sale)
    path = export(r, args.out)

    print(f"{sale.buyer} buys {sale.interest_sold:.0%} of {sale.partnership} on {sale.sale_date}")
    print(f"  Outside basis (cash + debt share)   {r.outside_basis:>14,.0f}")
    print(f"  Share of inside basis               {r.inside_basis_share:>14,.0f}")
    print(f"  743(b) adjustment                   {r.adjustment:>14,.0f}"
          + ("" if r.adjustment_applies else "   (not applied: no 754 election)"))
    print("Allocation under 755:")
    names = {a.asset_id: a.description for a in r.assets}
    for asset_id, amount in r.by_asset.items():
        if abs(amount) >= 0.5:
            print(f"  {names[asset_id]:<42}{amount:>14,.0f}")
    if r.years:
        print(f"Extra deductions in {sale.sale_date.year}: {r.deduction(sale.sale_date.year):,.0f}")
    print("Flags: " + ", ".join(f.code for f in r.flags))
    print(f"Excel report: {path}")


if __name__ == "__main__":
    main()
