"""Calibration adapter for ForgeSIOP.

Golden reference cases for supply chain computations:
- EOQ (known formula sqrt(2DS/H))
- Safety stock (z * sqrt(LT * σ_d² + d² * σ_LT²))
- Forecasting (SMA, SES known outputs)
- Reorder point (d * LT + SS)
- Newsvendor base stock (critical ratio → z-score)
- DDMRP buffer sizing (red/yellow/green zones)
"""

from __future__ import annotations

import math


# Golden reference cases — known correct answers
GOLDEN_CASES = [
    # --- EOQ ---
    {
        "case_id": "CAL-SIOP-001",
        "description": "Classic EOQ: D=10000, S=50, H=25% of $10 → sqrt(2*10000*50/2.5) = 632.46",
        "test": "eoq",
        "input": {
            "annual_demand": 10000,
            "ordering_cost": 50,
            "holding_cost_rate": 0.25,
            "unit_cost": 10,
        },
        "expected": {"eoq": 632.46, "tolerance": 0.01},
    },
    {
        "case_id": "CAL-SIOP-002",
        "description": "EOQ total cost at optimal Q",
        "test": "eoq_total_cost",
        "input": {
            "annual_demand": 10000,
            "ordering_cost": 50,
            "holding_cost_rate": 0.25,
            "unit_cost": 10,
        },
        "expected": {"total_cost_lt": 101582},  # purchasing + ordering + holding
    },
    # --- Safety stock ---
    {
        "case_id": "CAL-SIOP-003",
        "description": "Safety stock: demand-only, σ_d=20, LT=4, 95% → 1.645*20*sqrt(4) = 65.8",
        "test": "safety_stock_demand_only",
        "input": {"demand_std": 20, "lead_time": 4, "service_level": 0.95},
        "expected": {"safety_stock": 65.8, "tolerance": 0.1},
    },
    {
        "case_id": "CAL-SIOP-004",
        "description": "Dynamic safety stock: d=100, σ_d=20, LT=4, σ_LT=1, 95%",
        "test": "safety_stock_dynamic",
        "input": {
            "demand_mean": 100,
            "demand_std": 20,
            "lead_time_mean": 4,
            "lead_time_std": 1,
            "service_level": 0.95,
        },
        "expected": {"safety_stock": 177.16, "tolerance": 0.5},
    },
    # --- Forecasting ---
    {
        "case_id": "CAL-SIOP-005",
        "description": "SMA(3) of [10, 20, 30, 40, 50] → (30+40+50)/3 = 40.0",
        "test": "forecast_sma",
        "input": {"data": [10, 20, 30, 40, 50], "periods": 3},
        "expected": {"forecast": 40.0},
    },
    {
        "case_id": "CAL-SIOP-006",
        "description": "SES α=0.5 on [100, 110, 120, 130] — last smoothed value",
        "test": "forecast_ses",
        "input": {"data": [100, 110, 120, 130], "alpha": 0.5},
        "expected": {"last_value": 121.25, "tolerance": 0.01},
    },
    # --- Reorder point ---
    {
        "case_id": "CAL-SIOP-007",
        "description": "Reorder point: d=100/wk, LT=3wk, SS=150 → 100*3+150 = 450",
        "test": "reorder_point",
        "input": {"demand_mean": 100, "lead_time_mean": 3, "safety_stock": 150},
        "expected": {"rop": 450.0},
    },
    # --- Newsvendor ---
    {
        "case_id": "CAL-SIOP-008",
        "description": "Newsvendor: Cu=9, Co=1, CR=0.9 → z≈1.282",
        "test": "newsvendor",
        "input": {
            "demand_mean": 500,
            "demand_std": 100,
            "lead_time": 1,
            "holding_cost": 1,
            "stockout_cost": 9,
        },
        "expected": {"critical_ratio": 0.9, "base_stock_gt": 600},
    },
    # --- DDMRP buffer ---
    {
        "case_id": "CAL-SIOP-009",
        "description": "DDMRP buffer: ADU=50, DLT=10, LTF=0.5, VF=0.5 → red_base=250",
        "test": "ddmrp_buffer",
        "input": {
            "item_id": "PART-A",
            "average_daily_usage": 50,
            "decoupled_lead_time_days": 10,
            "lead_time_factor": 0.5,
            "variability_factor": 0.5,
        },
        "expected": {
            "red_base": 250.0,
            "red_safety": 125.0,
            "red_zone": 375.0,
            "green_zone": 250.0,
        },
    },
    # --- Holt trend ---
    {
        "case_id": "CAL-SIOP-010",
        "description": "Holt trend forecast on linear data [100,110,120,130,140] → ~150",
        "test": "forecast_holt",
        "input": {"data": [100, 110, 120, 130, 140], "alpha": 0.5, "beta": 0.3, "periods_ahead": 1},
        "expected": {"forecast_gt": 145, "forecast_lt": 155},
    },
]


def calibrate():
    """Run all golden reference cases. Standalone entry point."""
    from .inventory.eoq import economic_order_quantity, eoq_total_cost
    from .inventory.safety_stock import demand_only_safety_stock, dynamic_safety_stock
    from .inventory.reorder import reorder_point
    from .inventory.multi_echelon import base_stock_newsvendor
    from .demand.forecasting import (
        simple_moving_average,
        single_exponential_smoothing,
        holt_trend_corrected,
    )
    from .planning.ddmrp import BufferProfile

    results = []
    for case in GOLDEN_CASES:
        case_id = case["case_id"]
        test = case["test"]
        inp = case["input"]
        exp = case["expected"]

        try:
            if test == "eoq":
                actual = economic_order_quantity(**inp)
                tol = exp.get("tolerance", 0.01)
                passed = abs(actual - exp["eoq"]) < tol * exp["eoq"]
                results.append({"case_id": case_id, "passed": passed, "actual": round(actual, 2), "expected": exp["eoq"]})

            elif test == "eoq_total_cost":
                q = economic_order_quantity(**inp)
                total = eoq_total_cost(inp["annual_demand"], q, inp["ordering_cost"], inp["holding_cost_rate"], inp["unit_cost"])
                passed = total < exp["total_cost_lt"]
                results.append({"case_id": case_id, "passed": passed, "actual": round(total, 2)})

            elif test == "safety_stock_demand_only":
                actual = demand_only_safety_stock(inp["demand_std"], inp["lead_time"], inp["service_level"])
                tol = exp.get("tolerance", 0.1)
                passed = abs(actual - exp["safety_stock"]) < tol * 10
                results.append({"case_id": case_id, "passed": passed, "actual": round(actual, 2), "expected": exp["safety_stock"]})

            elif test == "safety_stock_dynamic":
                actual = dynamic_safety_stock(**inp)
                tol = exp.get("tolerance", 0.5)
                passed = abs(actual - exp["safety_stock"]) < tol * 10
                results.append({"case_id": case_id, "passed": passed, "actual": round(actual, 2), "expected": exp["safety_stock"]})

            elif test == "forecast_sma":
                actual = simple_moving_average(inp["data"], inp["periods"])
                passed = abs(actual - exp["forecast"]) < 0.01
                results.append({"case_id": case_id, "passed": passed, "actual": actual, "expected": exp["forecast"]})

            elif test == "forecast_ses":
                series = single_exponential_smoothing(inp["data"], inp["alpha"])
                actual = series[-1]
                tol = exp.get("tolerance", 0.01)
                passed = abs(actual - exp["last_value"]) < tol * 10
                results.append({"case_id": case_id, "passed": passed, "actual": round(actual, 4), "expected": exp["last_value"]})

            elif test == "reorder_point":
                actual = reorder_point(inp["demand_mean"], inp["lead_time_mean"], inp["safety_stock"])
                passed = abs(actual - exp["rop"]) < 0.01
                results.append({"case_id": case_id, "passed": passed, "actual": actual, "expected": exp["rop"]})

            elif test == "newsvendor":
                result = base_stock_newsvendor(**inp)
                cr_ok = abs(result["critical_ratio"] - exp["critical_ratio"]) < 0.01
                bs_ok = result["base_stock_level"] > exp["base_stock_gt"]
                passed = cr_ok and bs_ok
                results.append({"case_id": case_id, "passed": passed, "actual": result})

            elif test == "ddmrp_buffer":
                bp = BufferProfile(**inp)
                checks = {
                    "red_base": abs(bp.red_base - exp["red_base"]) < 0.1,
                    "red_safety": abs(bp.red_safety - exp["red_safety"]) < 0.1,
                    "red_zone": abs(bp.red_zone - exp["red_zone"]) < 0.1,
                    "green_zone": abs(bp.green_zone - exp["green_zone"]) < 0.1,
                }
                passed = all(checks.values())
                results.append({"case_id": case_id, "passed": passed, "actual": {k: getattr(bp, k) for k in exp}})

            elif test == "forecast_holt":
                actual = holt_trend_corrected(inp["data"], inp["alpha"], inp["beta"], inp["periods_ahead"])
                passed = exp["forecast_gt"] < actual < exp["forecast_lt"]
                results.append({"case_id": case_id, "passed": passed, "actual": round(actual, 2)})

        except Exception as e:
            results.append({"case_id": case_id, "passed": False, "error": str(e)})

    passed = sum(1 for r in results if r["passed"])
    return {
        "package": "forgesiop",
        "total": len(results),
        "passed": passed,
        "failed": len(results) - passed,
        "results": results,
        "is_calibrated": passed == len(results),
    }


def _run_case(case_id: str, test: str, inp: dict) -> dict:
    """Run a single golden case and return a flat dict with expectation-matching keys."""
    from .inventory.eoq import economic_order_quantity, eoq_total_cost
    from .inventory.safety_stock import demand_only_safety_stock, dynamic_safety_stock
    from .inventory.reorder import reorder_point
    from .inventory.multi_echelon import base_stock_newsvendor
    from .demand.forecasting import (
        simple_moving_average,
        single_exponential_smoothing,
        holt_trend_corrected,
    )
    from .planning.ddmrp import BufferProfile

    if test == "eoq":
        return {"eoq": economic_order_quantity(**inp)}

    elif test == "eoq_total_cost":
        q = economic_order_quantity(**inp)
        total = eoq_total_cost(inp["annual_demand"], q, inp["ordering_cost"], inp["holding_cost_rate"], inp["unit_cost"])
        return {"total_cost": total}

    elif test == "safety_stock_demand_only":
        return {"safety_stock": float(demand_only_safety_stock(inp["demand_std"], inp["lead_time"], inp["service_level"]))}

    elif test == "safety_stock_dynamic":
        return {"safety_stock": float(dynamic_safety_stock(**inp))}

    elif test == "forecast_sma":
        return {"forecast": simple_moving_average(inp["data"], inp["periods"])}

    elif test == "forecast_ses":
        series = single_exponential_smoothing(inp["data"], inp["alpha"])
        return {"last_value": series[-1]}

    elif test == "reorder_point":
        return {"rop": reorder_point(inp["demand_mean"], inp["lead_time_mean"], inp["safety_stock"])}

    elif test == "newsvendor":
        result = base_stock_newsvendor(**inp)
        return {
            "critical_ratio": result["critical_ratio"],
            "base_stock": float(result["base_stock_level"]),
        }

    elif test == "ddmrp_buffer":
        bp = BufferProfile(**inp)
        return {
            "red_base": bp.red_base,
            "red_safety": bp.red_safety,
            "red_zone": bp.red_zone,
            "green_zone": bp.green_zone,
        }

    elif test == "forecast_holt":
        return {"forecast": holt_trend_corrected(inp["data"], inp["alpha"], inp["beta"], inp["periods_ahead"])}

    raise ValueError(f"Unknown test: {test}")


def get_calibration_adapter():
    """ForgeCal adapter protocol."""
    try:
        from forgecal.core import CalibrationAdapter, CalibrationCase, Expectation
    except ImportError:
        return None

    cases = []
    for gc in GOLDEN_CASES:
        expectations = []
        case_tolerance = gc["expected"].get("tolerance", 0.01)
        for key, val in gc["expected"].items():
            if key == "tolerance":
                continue
            if key.endswith("_gt"):
                expectations.append(Expectation(key=key.replace("_gt", ""), expected=val, comparison="greater_than"))
            elif key.endswith("_lt"):
                expectations.append(Expectation(key=key.replace("_lt", ""), expected=val, comparison="less_than"))
            else:
                expectations.append(Expectation(key=key, expected=val, tolerance=case_tolerance, comparison="abs_within"))
        cases.append(CalibrationCase(
            case_id=gc["case_id"],
            package="forgesiop",
            category="supply_chain",
            analysis_type="siop",
            analysis_id=gc["test"],
            config=gc["input"],
            data={},
            expectations=expectations,
            description=gc["description"],
        ))

    def _run(case):
        gc = next(g for g in GOLDEN_CASES if g["case_id"] == case.case_id)
        return _run_case(case.case_id, gc["test"], gc["input"])

    from forgesiop import __version__
    return CalibrationAdapter(package="forgesiop", version=__version__, cases=cases, runner=_run)
