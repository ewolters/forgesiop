"""Tests for production and lean modules."""

from forgesiop.production.takt import takt_time, line_balance
from forgesiop.production.oee import oee
from forgesiop.production.kanban import kanban_quantity, epei, pitch
from forgesiop.production.flow import littles_law, throughput_rate, bottleneck_analysis, value_ratio
from forgesiop.production.cost import cost_of_quality, cost_accounting, payback_period
from forgesiop.lean.smed import classify_elements, smed_reduction
from forgesiop.lean.changeover import changeover_matrix
from forgesiop.lean.family import process_flow_analysis, product_family_analysis


class TestTakt:
    def test_basic(self):
        r = takt_time(480, 240)  # 8 hrs, 240 units
        assert abs(r.takt_minutes - 2.0) < 0.01
        assert abs(r.takt_seconds - 120) < 1

    def test_with_breaks(self):
        r = takt_time(480, 240, breaks_minutes=30)
        assert r.takt_minutes < 2.0  # less time available

    def test_line_balance(self):
        stations = [
            {"name": "Cut", "cycle_time": 45},
            {"name": "Weld", "cycle_time": 55},
            {"name": "Paint", "cycle_time": 40},
        ]
        r = line_balance(stations, takt_seconds=60)
        assert r.bottleneck == "Weld"
        assert r.staff >= 2


class TestOEE:
    def test_perfect(self):
        r = oee(480, 0, 1, 480, 0)
        assert abs(r.oee - 1.0) < 0.01

    def test_typical(self):
        r = oee(480, 48, 1, 400, 20)
        assert 0 < r.oee < 1
        assert r.availability < 1
        assert r.quality < 1

    def test_teep(self):
        r = oee(480, 0, 1, 480, 0, loading_pct=80)
        assert abs(r.teep - 0.8) < 0.01


class TestKanban:
    def test_basic(self):
        r = kanban_quantity(100, 3, safety_factor=0.1, container_size=50)
        assert r.n_cards >= 7  # (100*3*1.1)/50 = 6.6 → 7

    def test_epei(self):
        e = epei(30, 480, 5, target_pct=10)
        assert e > 0

    def test_pitch(self):
        p = pitch(60, 10)
        assert p == 600


class TestFlow:
    def test_littles_law_solve_wip(self):
        r = littles_law(throughput=10, lead_time=5)
        assert abs(r.wip - 50) < 0.01

    def test_littles_law_solve_throughput(self):
        r = littles_law(wip=50, lead_time=5)
        assert abs(r.throughput - 10) < 0.01

    def test_throughput(self):
        t = throughput_rate(100, 3600)
        assert abs(t - 100) < 0.01

    def test_bottleneck(self):
        stations = [
            {"name": "A", "cycle_time": 30},
            {"name": "B", "cycle_time": 60},
            {"name": "C", "cycle_time": 45},
        ]
        r = bottleneck_analysis(stations)
        assert r.constraint == "B"
        assert abs(r.system_throughput - 60) < 1  # 3600/60

    def test_value_ratio(self):
        vr = value_ratio(10, 100)
        assert abs(vr - 10) < 0.01


class TestCost:
    def test_coq(self):
        r = cost_of_quality(100, 200, 300, 400, revenue=10000)
        assert r.total_coq == 1000
        assert abs(r.coq_revenue_pct - 10) < 0.01

    def test_cost_accounting(self):
        r = cost_accounting(worker_count=10, labor_cost_per_hour=25, hours_worked=8,
                            material_cost=500, units_produced=100)
        assert r.total > 0
        assert r.cost_per_unit > 0

    def test_payback(self):
        assert payback_period(100000, 50000) == 2.0


class TestSMED:
    def test_classify(self):
        elements = [
            {"name": "Detach mold", "time_minutes": 10, "type": "internal"},
            {"name": "Preheat mold", "time_minutes": 15, "type": "external"},
            {"name": "Align fixture", "time_minutes": 5, "type": "internal"},
        ]
        r = classify_elements(elements)
        assert r.internal_time == 15
        assert r.external_time == 15
        assert r.total_time == 30

    def test_reduction(self):
        current = [
            {"name": "A", "time_minutes": 20, "type": "internal"},
            {"name": "B", "time_minutes": 10, "type": "internal"},
        ]
        proposed = [
            {"name": "A", "time_minutes": 15, "type": "internal"},  # reduced
            {"name": "B", "time_minutes": 10, "type": "external"},  # externalized
        ]
        r = smed_reduction(current, proposed)
        assert r["time_saved_minutes"] == 5  # 30 → 25
        assert r["proposed_internal"] == 15  # only A is internal now


class TestChangeover:
    def test_basic(self):
        products = ["A", "B", "C"]
        matrix = {
            "A": {"B": 10, "C": 20},
            "B": {"A": 15, "C": 5},
            "C": {"A": 25, "B": 8},
        }
        r = changeover_matrix(products, matrix)
        assert len(r.optimal_sequence) == 3
        assert r.total_changeover > 0


class TestPFA:
    def test_flow_analysis(self):
        steps = [
            {"name": "Cut", "category": "P", "time_minutes": 5, "distance_meters": 0},
            {"name": "Move to weld", "category": "T", "time_minutes": 2, "distance_meters": 20},
            {"name": "Weld", "category": "P", "time_minutes": 8, "distance_meters": 0},
            {"name": "Inspect", "category": "I", "time_minutes": 3, "distance_meters": 0},
            {"name": "Store", "category": "S-B", "time_minutes": 60, "distance_meters": 0},
        ]
        r = process_flow_analysis(steps)
        assert r.process_time == 13  # Cut + Weld
        assert r.process_ratio < 20  # VA is small fraction

    def test_family_analysis(self):
        products = {
            "Widget A": ["cut", "drill", "paint"],
            "Widget B": ["cut", "drill", "plate"],
            "Gear X": ["forge", "machine", "heat_treat"],
        }
        families = product_family_analysis(products)
        assert len(families) >= 2  # widgets together, gear separate
