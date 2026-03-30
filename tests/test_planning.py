"""Tests for planning modules."""

from datetime import date, timedelta


from forgesiop.core.types import BOMEntry, InventoryPosition, Item
from forgesiop.planning.aggregate import chase_strategy, compare_strategies, level_strategy
from forgesiop.planning.atp import available_to_promise, capable_to_promise
from forgesiop.planning.capacity import identify_bottlenecks
from forgesiop.planning.ddmrp import BufferProfile, execution_alerts, net_flow_equation
from forgesiop.planning.mrp import run_mrp
from forgesiop.planning.siop import SIOPScenario, balance_scenario, compare_scenarios


class TestMRP:
    def test_simple_explosion(self):
        items = {
            "A": Item(id="A", name="Product A", lead_time_days=7),
            "B": Item(id="B", name="Component B", lead_time_days=14),
        }
        bom = [BOMEntry(parent_id="A", child_id="B", quantity_per=2)]
        mps = {"A": [(date.today() + timedelta(days=28), 100)]}
        inv = {"A": InventoryPosition(item_id="A", on_hand=0), "B": InventoryPosition(item_id="B", on_hand=50)}

        records = run_mrp(items, bom, mps, inv, start_date=date.today())
        assert "A" in records
        assert "B" in records

    def test_mrp_produces_records(self):
        items = {"A": Item(id="A", name="A", lead_time_days=7)}
        start = date.today()
        # Place demand in second week to ensure it lands in a period
        mps = {"A": [(start + timedelta(days=10), 50)]}
        inv = {"A": InventoryPosition(item_id="A", on_hand=0)}
        records = run_mrp(items, [], mps, inv, start_date=start)
        assert "A" in records
        # Should have net requirement somewhere
        assert any(nr > 0 for nr in records["A"].net_requirements)


class TestDDMRP:
    def test_buffer_profile(self):
        bp = BufferProfile(
            item_id="X",
            average_daily_usage=100,
            decoupled_lead_time_days=5,
            lead_time_factor=0.5,
            variability_factor=0.3,
        )
        assert bp.red_base == 250  # 100 * 5 * 0.5
        assert bp.red_safety == 75  # 250 * 0.3
        assert bp.red_zone == 325
        assert bp.yellow_zone == 500  # 100 * 5
        assert bp.top_of_green > bp.top_of_yellow > bp.top_of_red

    def test_net_flow_green(self):
        bp = BufferProfile(item_id="X", average_daily_usage=100, decoupled_lead_time_days=5)
        # TOG=1750. NFP = 1500 + 400 - 100 = 1800 > TOG → green
        result = net_flow_equation(bp, on_hand=1500, on_order=400, qualified_demand=100)
        assert result["zone"] == "green"
        assert result["recommended_order"] == 0

    def test_net_flow_red(self):
        bp = BufferProfile(item_id="X", average_daily_usage=100, decoupled_lead_time_days=5)
        result = net_flow_equation(bp, on_hand=50, on_order=0, qualified_demand=400)
        assert result["zone"] == "red"
        assert result["recommended_order"] > 0

    def test_execution_alerts(self):
        profiles = [
            BufferProfile(item_id="A", average_daily_usage=100, decoupled_lead_time_days=5),
            BufferProfile(item_id="B", average_daily_usage=50, decoupled_lead_time_days=3),
        ]
        positions = {
            "A": {"on_hand": 50, "on_order": 0, "qualified_demand": 400},
            "B": {"on_hand": 500, "on_order": 100, "qualified_demand": 50},
        }
        alerts = execution_alerts(profiles, positions)
        assert len(alerts) >= 1
        assert alerts[0]["item_id"] == "A"


class TestCapacity:
    def test_bottleneck_identification(self):
        from forgesiop.planning.capacity import CapacityResult

        results = [
            CapacityResult("WC1", date.today(), 40, 38, 0.95, True, 0),
            CapacityResult("WC2", date.today(), 40, 20, 0.50, False, 0),
        ]
        bottlenecks = identify_bottlenecks(results, threshold=0.85)
        assert len(bottlenecks) == 1
        assert bottlenecks[0]["work_center_id"] == "WC1"


class TestATP:
    def test_simple_atp(self):
        periods = [date.today() + timedelta(days=i * 7) for i in range(4)]
        mps = [(periods[0], 100), (periods[2], 100)]
        orders = [(periods[0], 30), (periods[1], 20)]

        results = available_to_promise(
            on_hand=50,
            master_schedule=mps,
            committed_orders=orders,
            planning_periods=periods,
        )
        assert len(results) == 4
        assert results[0].available > 0  # first period has on-hand + MPS - committed

    def test_ctp_capacity_limited(self):
        periods = [date.today() + timedelta(days=i * 7) for i in range(3)]
        atp = available_to_promise(50, [(periods[0], 200)], [], periods)
        capacity = {periods[0]: 40, periods[1]: 40, periods[2]: 40}

        ctp = capable_to_promise(atp, capacity, hours_per_unit=0.5)
        assert ctp[0]["capacity_limited"]
        assert ctp[0]["ctp"] <= 80  # 40 hours / 0.5 = 80 units max


class TestAggregate:
    def test_chase(self):
        demand = [100, 120, 80, 150, 110, 90]
        result = chase_strategy(demand)
        assert result.strategy == "chase"
        assert result.total_cost > 0
        assert all(inv == 0 for inv in result.inventory)

    def test_level(self):
        demand = [100, 120, 80, 150, 110, 90]
        result = level_strategy(demand)
        assert result.strategy == "level"
        assert result.total_cost > 0

    def test_compare(self):
        demand = [100, 120, 80, 150, 110, 90]
        results = compare_strategies(demand)
        assert len(results) == 2
        assert results[0].total_cost <= results[1].total_cost


class TestSIOP:
    def test_balance_scenario(self):
        periods = [date.today() + timedelta(days=i * 30) for i in range(6)]
        scenario = SIOPScenario(
            name="Base",
            periods=periods,
            demand=[100, 120, 110, 130, 100, 90],
            supply=[110, 110, 110, 110, 110, 110],
            opening_inventory=50,
        )
        result = balance_scenario(scenario)
        assert result["total_demand"] == 650
        assert result["total_supply"] == 660
        assert result["service_level"] > 0

    def test_compare_scenarios(self):
        periods = [date.today() + timedelta(days=i * 30) for i in range(4)]
        s1 = SIOPScenario("Conservative", periods, [100, 100, 100, 100], [120, 120, 120, 120], 0)
        s2 = SIOPScenario("Aggressive", periods, [100, 100, 100, 100], [90, 90, 90, 90], 0)
        result = compare_scenarios([s1, s2])
        assert result["recommended"] == "Conservative"

    def test_stockout_detection(self):
        periods = [date.today() + timedelta(days=i * 7) for i in range(4)]
        scenario = SIOPScenario("Shortage", periods, [100, 100, 100, 100], [50, 50, 50, 50], 0)
        assert len(scenario.stockout_periods) > 0
