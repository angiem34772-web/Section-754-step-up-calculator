"""Tests for the 743(b) step-up. Expected amounts come from the hand calculation in
docs/hand_calculation.md, and the depreciation rates from IRS Pub. 946 tables."""

from dataclasses import replace
from datetime import date
from pathlib import Path

import pytest

from step_up.adjustment import _allocate_class, compute
from step_up.depreciation import amortize_197, macrs_declining_balance, straight_line_mid_month
from step_up.excel_export import export
from step_up.loader import load_inputs
from step_up.models import AllocationLine, Asset, Sale

ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="module")
def sample():
    assets, sale = load_inputs(ROOT / "sample_data")
    return compute(assets, sale)


def codes(results):
    return {f.code for f in results.flags}


# ---------- The sample sale, line by line against the hand calculation ----------

def test_outside_basis_is_cash_plus_debt_share(sample):
    assert sample.outside_basis == pytest.approx(1_850_000 + 2_000_000)


def test_gross_value_and_residual_goodwill(sample):
    assert sample.gross_value == pytest.approx(38_500_000)
    assert sample.residual_goodwill == pytest.approx(600_000)
    assert "RESIDUAL_GOODWILL" in codes(sample)


def test_inside_basis_from_hypothetical_sale(sample):
    assert sample.cash_on_liquidation == pytest.approx(1_850_000)
    assert sample.share_of_gain == pytest.approx(1_235_000)
    assert sample.previously_taxed_capital == pytest.approx(615_000)
    assert sample.inside_basis_share == pytest.approx(2_615_000)


def test_743b_adjustment(sample):
    assert sample.adjustment == pytest.approx(1_235_000)
    assert sample.adjustment_applies and not sample.mandatory


def test_755_class_split(sample):
    assert sample.ordinary_class == pytest.approx(40_000)
    assert sample.capital_class == pytest.approx(1_195_000)


def test_755_allocation_by_asset(sample):
    expected = {"AR": 0, "FFE": 40_000, "LAND": 350_000, "BLDG": 800_000, "COOP": -15_000, "GW": 60_000}
    assert sample.by_asset == pytest.approx(expected)
    assert sum(sample.by_asset.values()) == pytest.approx(sample.adjustment)


def test_depreciation_of_the_step_up(sample):
    bldg, ffe, gw = (sample.depreciation[k] for k in ("BLDG", "FFE", "GW"))
    assert bldg[2026] == pytest.approx(13_333.33, abs=0.01)  # 800,000 / 27.5 x 5.5/12
    assert bldg[2027] == pytest.approx(29_090.91, abs=0.01)
    assert sum(bldg.values()) == pytest.approx(800_000)
    assert [round(ffe[y]) for y in range(2026, 2032)] == [8_000, 12_800, 7_680, 4_608, 4_608, 2_304]
    assert gw[2026] == pytest.approx(2_000) and gw[2027] == pytest.approx(4_000)
    assert sample.deduction(2026) == pytest.approx(23_333.33, abs=0.01)
    assert "LAND" not in sample.depreciation and "COOP" not in sample.depreciation


def test_seller_gain_and_character(sample):
    s = sample.seller
    assert s["amount_realized"] == pytest.approx(3_850_000)
    assert s["total_gain"] == pytest.approx(1_150_000)
    assert s["ordinary_751"] == pytest.approx(40_000)
    assert s["unrecaptured_1250"] == pytest.approx(800_000)
    assert s["other_long_term"] == pytest.approx(310_000)
    assert "751_EXCHANGE" in codes(sample)


def test_excel_report_builds(sample, tmp_path):
    path = export(sample, tmp_path / "report.xlsx")
    from openpyxl import load_workbook
    wb = load_workbook(path)
    assert wb.sheetnames == ["Summary", "743(b) Calculation", "Hypothetical Sale", "755 Allocation",
                             "Depreciation Schedule", "Seller Gain", "Inputs"]


# ---------- Depreciation methods against IRS Pub. 946 tables ----------

@pytest.mark.parametrize("years, factor, table", [
    (5, 2.0, [20.00, 32.00, 19.20, 11.52, 11.52, 5.76]),
    (7, 2.0, [14.29, 24.49, 17.49, 12.49, 8.93, 8.92, 8.93, 4.46]),
    (15, 1.5, [5.00, 9.50, 8.55, 7.70, 6.93, 6.23, 5.90, 5.90, 5.91, 5.90, 5.91, 5.90, 5.91, 5.90, 5.91, 2.95]),
])
def test_macrs_matches_table_a1(years, factor, table):
    schedule = macrs_declining_balance(10_000, years, 2026, factor)
    assert [round(v / 100, 2) for v in schedule.values()] == pytest.approx(table, abs=0.011)
    assert sum(schedule.values()) == pytest.approx(10_000)


def test_residential_mid_month_matches_table():
    schedule = straight_line_mid_month(100_000, 27.5, date(2026, 1, 15))
    assert schedule[2026] / 1000 == pytest.approx(3.485, abs=0.001)  # January column of Table A-6
    assert schedule[2027] / 1000 == pytest.approx(3.636, abs=0.001)
    assert sum(schedule.values()) == pytest.approx(100_000)


def test_197_amortization_starts_month_acquired():
    schedule = amortize_197(180_000, date(2026, 10, 1))
    assert schedule[2026] == pytest.approx(3_000)  # Oct-Dec = 3 months x 1,000
    assert schedule[2041] == pytest.approx(9_000)
    assert sum(schedule.values()) == pytest.approx(180_000)


def test_bonus_depreciation_on_personal_property(sample):
    assets, sale = load_inputs(ROOT / "sample_data")
    r = compute(assets, replace(sale, bonus_pct=1.0))
    assert r.depreciation["FFE"] == {2026: pytest.approx(40_000)}
    assert r.depreciation["BLDG"][2026] == pytest.approx(13_333.33, abs=0.01)  # real property: no bonus


# ---------- Elections and special rules ----------

def test_no_election_means_no_adjustment():
    assets, sale = load_inputs(ROOT / "sample_data")
    r = compute(assets, replace(sale, election_754=False))
    assert r.adjustment == pytest.approx(1_235_000)  # what the buyer is missing out on
    assert not r.adjustment_applies
    assert all(v == 0 for v in r.by_asset.values()) and r.depreciation == {}
    assert {"NO_754_ELECTION", "ELECTION_OPPORTUNITY"} <= codes(r)


def test_substantial_built_in_loss_is_mandatory():
    assets = [Asset("L", "Land", "land", 1_000_000, 600_000)]
    sale = Sale("P", "S", "B", date(2026, 7, 1), 0.5, 300_000, 0, election_754=False)
    r = compute(assets, sale)
    assert r.mandatory and r.adjustment_applies
    assert r.adjustment == pytest.approx(-200_000)
    assert r.by_asset["L"] == pytest.approx(-200_000)
    assert "MANDATORY_743B" in codes(r)


def test_price_below_asset_values_spreads_difference_by_value():
    assets = [Asset("A", "Asset A", "land", 100, 300), Asset("B", "Asset B", "capital_asset", 200, 100)]
    r = compute(assets, Sale("P", "S", "B", date(2026, 7, 1), 0.5, 150, 0))
    # Shares of gain: A +100 x 50% = 50, B -100 x 50% = -50. Adjustment = 150 - 150 = 0.
    # Difference of 50 is taken back 300/400 from A and 100/400 from B.
    assert r.adjustment == pytest.approx(0)
    assert r.by_asset == pytest.approx({"A": 62.5, "B": -62.5})
    assert "PRICE_BELOW_ASSET_VALUES" in codes(r)


def test_item_decrease_cannot_go_below_zero():
    lines = [AllocationLine("A", "A", "capital", 10, 900, 0), AllocationLine("B", "B", "capital", 1_000, 100, 0)]
    flags = []
    out = _allocate_class(lines, -500, 1.0, flags)
    # Pro rata by value would give A -450, but A only has 10 of basis: the other 440 moves to B.
    assert [l.adjustment for l in out] == pytest.approx([-10, -490])
    assert flags[0].code == "ITEM_DECREASE_LIMITED"


def test_step_down_on_building_spread_over_remaining_life():
    assets = [Asset("BL", "Building", "residential_building", 1_000_000, 800_000, 500_000, 27.5, 10)]
    r = compute(assets, Sale("P", "S", "B", date(2026, 7, 1), 1.0, 800_000, 0))
    assert r.by_asset["BL"] == pytest.approx(-200_000)
    assert r.depreciation["BL"] == {y: pytest.approx(-20_000) for y in range(2026, 2036)}
