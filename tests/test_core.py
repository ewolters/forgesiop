"""Tests for ForgeSIOP core modules."""

import pytest

from forgesiop.core.bom import BOM
from forgesiop.core.types import BOMEntry, Item, SupplyRisk, ProcessCapability
from forgesiop.demand.forecasting import (
    croston_intermittent,
    holt_trend_corrected,
    simple_moving_average,
    single_exponential_smoothing,
    weighted_moving_average,
)
from forgesiop.inventory.eoq import economic_order_quantity, eoq_with_quantity_discount
from forgesiop.inventory.safety_stock import (
    demand_only_safety_stock,
    dynamic_safety_stock,
    safety_stock_with_supply_risk,
)
from forgesiop.probabilistic.yield_model import (
    required_input_quantity,
    yield_distribution,
    yield_from_cpk,
)


# =============================================================================
# BOM
# =============================================================================


class TestBOM:
    def test_explode_simple(self):
        entries = [
            BOMEntry(parent_id="A", child_id="B", quantity_per=2),
            BOMEntry(parent_id="A", child_id="C", quantity_per=1),
            BOMEntry(parent_id="B", child_id="D", quantity_per=3),
        ]
        bom = BOM(entries)
        tree = bom.explode("A", quantity=10)
        assert tree.item_id == "A"
        assert len(tree.children) == 2
        # B needs 20, D needs 60
        b_node = next(c for c in tree.children if c.item_id == "B")
        assert b_node.quantity_per_parent == 20
        d_node = b_node.children[0]
        assert d_node.item_id == "D"
        assert d_node.quantity_per_parent == 60

    def test_low_level_codes(self):
        entries = [
            BOMEntry(parent_id="A", child_id="B", quantity_per=1),
            BOMEntry(parent_id="A", child_id="C", quantity_per=1),
            BOMEntry(parent_id="B", child_id="C", quantity_per=1),  # C appears at level 1 AND 2
        ]
        bom = BOM(entries)
        codes = bom.low_level_codes()
        assert codes["A"] == 0
        assert codes["B"] == 1
        assert codes["C"] == 2  # deepest occurrence

    def test_scrap_factor(self):
        entries = [
            BOMEntry(parent_id="A", child_id="B", quantity_per=10, scrap_factor=0.1),
        ]
        bom = BOM(entries)
        tree = bom.explode("A", quantity=1)
        b = tree.children[0]
        # 10 / (1 - 0.1) = 11.11
        assert b.quantity_per_parent == pytest.approx(11.11, rel=0.01)


# =============================================================================
# Demand Forecasting
# =============================================================================


class TestForecasting:
    def test_sma(self):
        data = [100, 110, 120, 130, 140]
        assert simple_moving_average(data, 3) == pytest.approx(130.0)

    def test_wma(self):
        data = [100, 110, 120]
        result = weighted_moving_average(data, [1, 2, 3])
        assert result == pytest.approx(113.33, rel=0.01)

    def test_ses(self):
        data = [100, 110, 120, 130]
        smoothed = single_exponential_smoothing(data, alpha=0.5)
        assert len(smoothed) == 4
        assert smoothed[-1] > smoothed[0]

    def test_holt(self):
        data = [100, 110, 120, 130, 140]
        forecast = holt_trend_corrected(data, periods_ahead=1)
        assert forecast > 140  # upward trend should forecast above last value

    def test_croston_zero_demand(self):
        assert croston_intermittent([0, 0, 0, 0]) == 0.0

    def test_croston_intermittent(self):
        data = [0, 0, 5, 0, 0, 0, 3, 0, 4, 0]
        result = croston_intermittent(data)
        assert result > 0


# =============================================================================
# Inventory
# =============================================================================


class TestEOQ:
    def test_classic_eoq(self):
        q = economic_order_quantity(
            annual_demand=10000,
            ordering_cost=50,
            holding_cost_rate=0.25,
            unit_cost=10,
        )
        # sqrt(2 * 10000 * 50 / 2.5) = sqrt(400000) = 632.45
        assert q == pytest.approx(632.45, rel=0.01)

    def test_quantity_discount(self):
        result = eoq_with_quantity_discount(
            annual_demand=10000,
            ordering_cost=50,
            holding_cost_rate=0.25,
            price_breaks=[(1, 10.0), (500, 9.50), (1000, 9.00)],
        )
        assert result["quantity"] > 0
        assert result["total_cost"] > 0


class TestSafetyStock:
    def test_dynamic(self):
        ss = dynamic_safety_stock(
            demand_mean=200,
            demand_std=30,
            lead_time_mean=5,
            lead_time_std=1,
            service_level=0.95,
        )
        assert ss > 0
        assert ss < 500  # sanity check

    def test_demand_only(self):
        ss = demand_only_safety_stock(demand_std=30, lead_time=5, service_level=0.95)
        assert ss > 0

    def test_supply_risk_multiplier(self):
        base = dynamic_safety_stock(200, 30, 5, 1, 0.95)
        risky = safety_stock_with_supply_risk(200, 30, 5, 1, 0.95, supply_risk_factor=1.5)
        assert risky == pytest.approx(base * 1.5)

    def test_higher_service_level_more_stock(self):
        ss_90 = dynamic_safety_stock(200, 30, 5, 1, 0.90)
        ss_99 = dynamic_safety_stock(200, 30, 5, 1, 0.99)
        assert ss_99 > ss_90


# =============================================================================
# Probabilistic — Yield
# =============================================================================


class TestYieldModel:
    def test_cpk_1_yield(self):
        y = yield_from_cpk(1.0)
        assert y == pytest.approx(0.9973, abs=0.001)

    def test_cpk_1_33_yield(self):
        y = yield_from_cpk(1.33)
        assert y > 0.999

    def test_cpk_0_67_yield(self):
        y = yield_from_cpk(0.67)
        assert y < 0.99
        assert y > 0.9

    def test_cpk_0_yield(self):
        y = yield_from_cpk(0)
        assert y == 0.5

    def test_yield_distribution(self):
        dist = yield_distribution(cpk=1.0, cpk_std=0.1, n_samples=500)
        assert dist["mean"] > 0.99
        assert dist["std"] > 0
        assert dist["p5"] < dist["p95"]

    def test_required_input(self):
        qty = required_input_quantity(desired_output=100, cpk=1.0)
        assert qty > 100  # need more than desired due to yield loss
        assert qty < 110  # but not too much at Cpk=1.0

    def test_low_cpk_needs_more_input(self):
        qty_good = required_input_quantity(100, cpk=1.33)
        qty_bad = required_input_quantity(100, cpk=0.67)
        assert qty_bad > qty_good


# =============================================================================
# Data Types
# =============================================================================


class TestTypes:
    def test_supply_risk_factor(self):
        low = SupplyRisk(supplier_id="S1", risk_level="low")
        high = SupplyRisk(supplier_id="S2", risk_level="high")
        critical = SupplyRisk(supplier_id="S3", risk_level="critical")
        assert low.risk_factor == 1.0
        assert high.risk_factor == 1.5
        assert critical.risk_factor == 2.0

    def test_process_capability(self):
        pc = ProcessCapability(item_id="X", cpk=1.0, yield_rate=0.997)
        assert pc.expected_good_units == pytest.approx(99.7)

    def test_inventory_position(self):
        from forgesiop.core.types import InventoryPosition

        pos = InventoryPosition(item_id="W", on_hand=100, on_order=50, committed=30)
        assert pos.available == 120
