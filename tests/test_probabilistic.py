"""Tests for probabilistic modules."""

import pytest

from forgesiop.probabilistic.monte_carlo import simulate_production, simulate_supply_chain
from forgesiop.probabilistic.risk_scoring import compute_risk_level, risk_adjusted_lead_time
from forgesiop.probabilistic.scenario import ScenarioInput, run_scenario


class TestMonteCarlo:
    def test_simulate_production(self):
        result = simulate_production(
            planned_quantity=1000,
            yield_mean=0.95,
            yield_std=0.02,
            demand_mean=900,
            demand_std=50,
            lead_time_mean=5,
            lead_time_std=1,
            n_iterations=1000,
        )
        assert "good_output" in result
        assert "ending_inventory" in result
        assert "service_level" in result
        assert result["good_output"].mean > 900

    def test_supply_chain_simulation(self):
        stages = [
            {"name": "Raw", "input_qty": 1000, "yield_mean": 0.98, "yield_std": 0.01},
            {"name": "Machine", "input_qty": 1000, "yield_mean": 0.95, "yield_std": 0.02},
            {"name": "Assembly", "input_qty": 1000, "yield_mean": 0.99, "yield_std": 0.005},
        ]
        result = simulate_supply_chain(stages, n_iterations=500)
        assert result["final_output"].mean < 1000  # yield losses
        assert result["final_output"].mean > 800  # but not catastrophic


class TestRiskScoring:
    def test_low_risk(self):
        risk = compute_risk_level(quality_score=0.9, open_claims=0, lead_time_reliability=0.95)
        assert risk.risk_level == "low"
        assert risk.risk_factor == 1.0

    def test_high_risk(self):
        risk = compute_risk_level(quality_score=0.3, open_claims=3, lead_time_reliability=0.6)
        assert risk.risk_level in ("high", "critical")
        assert risk.risk_factor > 1.0

    def test_risk_adjusted_lead_time(self):
        risk = compute_risk_level(quality_score=0.3, open_claims=3, lead_time_reliability=0.5)
        base_lt, base_std = 10.0, 2.0
        adj_lt, adj_std = risk_adjusted_lead_time(base_lt, base_std, risk)
        assert adj_lt > base_lt
        assert adj_std > base_std


class TestScenario:
    def test_basic_scenario(self):
        inputs = [
            ScenarioInput("demand", 1000, 800, 1200),
            ScenarioInput("yield", 0.95, 0.90, 0.99),
            ScenarioInput("price", 10, 8, 12),
        ]

        def model(params):
            revenue = params["demand"] * params["yield"] * params["price"]
            return {"revenue": revenue}

        result = run_scenario(inputs, model, n_iterations=500)
        assert result.base_case["revenue"] == pytest.approx(9500, rel=0.01)
        assert result.output_distributions["revenue"]["mean"] > 0
        assert len(result.sensitivity) == 3
        assert result.sensitivity[0]["rank"] == 1  # most impactful input


class TestDemandExtended:
    def test_abc_classification(self):
        from forgesiop.demand.classification import abc_classification

        items = [
            {"id": "A", "annual_value": 50000},
            {"id": "B", "annual_value": 30000},
            {"id": "C", "annual_value": 5000},
            {"id": "D", "annual_value": 3000},
            {"id": "E", "annual_value": 2000},
        ]
        result = abc_classification(items)
        assert result[0]["abc_class"] == "A"
        assert any(i["abc_class"] == "C" for i in result)

    def test_seasonal_indices(self):
        from forgesiop.demand.seasonality import seasonal_indices

        # Quarterly data with clear seasonality
        data = [100, 80, 120, 110] * 3  # 3 years
        indices = seasonal_indices(data, period=4)
        assert len(indices) == 4
        assert sum(indices) == pytest.approx(4.0, rel=0.1)  # should sum to period

    def test_demand_sensing(self):
        from forgesiop.demand.sensing import demand_sensing

        forecast = [100, 100, 100, 100, 100, 100]
        actuals = [110, 115, 120]  # trending up
        adjusted = demand_sensing(forecast, actuals, alpha=0.6, horizon=4)
        assert adjusted[0] > forecast[0]  # near-term adjusted up
        assert adjusted[5] == forecast[5]  # beyond horizon unchanged


class TestInventoryExtended:
    def test_reorder_policies(self):
        from forgesiop.inventory.reorder import continuous_review_sQ, periodic_review_sS

        sq = continuous_review_sQ(200, 30, 5, 1, order_quantity=500, service_level=0.95)
        assert sq["reorder_point_s"] > 0
        assert sq["policy"] == "(s, Q)"

        ss = periodic_review_sS(200, 30, 7, 5, 1, service_level=0.95)
        assert ss["order_up_to_S"] > 0
        assert ss["policy"] == "(s, S)"

    def test_inventory_metrics(self):
        from forgesiop.inventory.metrics import days_of_supply, fill_rate, gmroi, inventory_turns

        assert inventory_turns(1000000, 200000) == pytest.approx(5.0)
        assert days_of_supply(500, 100) == pytest.approx(5.0)
        assert fill_rate(95, 100) == pytest.approx(0.95)
        assert gmroi(300000, 200000) == pytest.approx(1.5)

    def test_multi_echelon(self):
        from forgesiop.inventory.multi_echelon import base_stock_newsvendor

        result = base_stock_newsvendor(
            demand_mean=100, demand_std=20, lead_time=5,
            holding_cost=2, stockout_cost=20,
        )
        assert result["base_stock_level"] > 0
        assert result["safety_stock"] > 0


class TestCalendar:
    def test_workdays(self):
        from datetime import date

        from forgesiop.core.calendar import add_workdays, workdays_between

        mon = date(2026, 3, 30)  # Monday
        fri = date(2026, 4, 3)  # Friday
        assert workdays_between(mon, fri) == 4

        result = add_workdays(mon, 5)
        assert result.weekday() < 5  # should be a weekday
