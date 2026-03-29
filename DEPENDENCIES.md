# ForgeSIOP Dependency Map

Every external dependency documented with: what it provides, why we use it, what breaks without it, and how to absorb it if we need to go fully standalone.

## Core Dependencies (always installed)

### scipy (>=1.10)
- **Provides:** `scipy.optimize.linprog` (LP solver for aggregate planning), `scipy.stats` (distribution fitting, CDF/PPF for safety stock), `scipy.special` (beta/gamma functions for Bayesian inventory models)
- **Used by:** `planning/aggregate.py`, `inventory/safety_stock.py`, `probabilistic/monte_carlo.py`, `probabilistic/yield_model.py`
- **If removed:** Aggregate planning LP fails. Safety stock z-score lookup fails. Monte Carlo distribution sampling falls back to Python random (less accurate tails).
- **Absorb path:**
  - LP solver: implement revised simplex (~200 lines) or use `linprog` from a vendored copy
  - Distribution functions: `statistics.NormalDist` covers normal. For others, vendor the specific CDF/PPF formulas (~50 lines per distribution)
  - Alternative: install just `scipy` core without optional deps (~15MB)
- **License:** BSD-3-Clause
- **Absorb risk:** LOW — well-understood algorithms, clean licenses

### numpy (>=1.24)
- **Provides:** Array operations, vectorized math, random sampling
- **Used by:** Everything. Array operations are pervasive.
- **If removed:** Rewrite all array ops with Python lists and `math` stdlib. ~2x slower for small arrays, ~100x slower for large ones.
- **Absorb path:** For small-scale (< 1000 items): replace with `statistics` stdlib + list comprehensions. For large-scale: keep numpy, it's essential.
- **License:** BSD-3-Clause
- **Absorb risk:** HIGH — removing numpy is painful. Don't do it unless forced.
- **Note:** scipy requires numpy, so if scipy is installed, numpy is already present.

## Optional Dependencies

### statsmodels (>=0.14) — `pip install forgesiop[forecast]`
- **Provides:** `ExponentialSmoothing` (Holt-Winters), `seasonal_decompose`, ARIMA, STL decomposition
- **Used by:** `demand/forecasting.py` (advanced methods), `demand/seasonality.py`
- **If removed:** Advanced forecasting falls back to our pure-Python implementations (SMA, WMA, SES, Holt trend-corrected). Holt-Winters and ARIMA unavailable.
- **Absorb path:**
  - Holt-Winters: ~120 lines of Python (triple exponential smoothing with additive/multiplicative seasonality)
  - Seasonal decomposition: ~80 lines (moving average + ratio-to-moving-average)
  - ARIMA: complex (~500+ lines). Consider dropping or deferring.
  - STL: complex. Use simple decomposition instead.
- **License:** BSD-3-Clause
- **Absorb risk:** MEDIUM — Holt-Winters is worth absorbing. ARIMA is expensive.

### stockpyl (>=1.0) — `pip install forgesiop[meio]`
- **Provides:** Multi-echelon inventory optimization (GSM, SSM algorithms), newsvendor problem, Wagner-Whitin
- **Used by:** `inventory/multi_echelon.py`
- **If removed:** Multi-echelon optimization unavailable. Single-echelon still works (our own EOQ, safety stock, reorder policies).
- **Absorb path:**
  - Newsvendor: ~30 lines (critical ratio → optimal order quantity)
  - Wagner-Whitin: ~100 lines (dynamic programming lot sizing)
  - GSM/SSM: ~300-500 lines per algorithm. Academic but well-documented in Snyder's book.
  - stockpyl is MIT licensed — can legally copy algorithms with attribution
- **Source:** https://github.com/LarrySnyder/stockpyl
- **License:** MIT
- **Absorb risk:** LOW — MIT license allows copying. Algorithms are published in textbooks.

## What We Write Ourselves (no dependency)

These are forgesiop-native with zero external dependency beyond numpy:

| Module | Key functions | Why not a dependency |
|--------|-------------|---------------------|
| `demand/forecasting.py` | SMA, WMA, SES, Holt (trend-corrected) | Simple enough. 4 methods, ~150 lines total. |
| `demand/classification.py` | ABC analysis, XYZ analysis, ABC-XYZ matrix | Sorting + thresholds. ~80 lines. |
| `demand/sensing.py` | Short-horizon signal adjustment | Weighted average of forecast + recent actuals. ~40 lines. |
| `inventory/eoq.py` | EOQ, EOQ with discounts, EOQ with constraints | Closed-form formulas. ~100 lines. |
| `inventory/safety_stock.py` | Dynamic safety stock (demand var + LT var) | Formulas with scipy.stats for z-score. ~80 lines. |
| `inventory/reorder.py` | ROP, (s,S), (s,Q) policies | Policy evaluation with demand distribution. ~120 lines. |
| `inventory/metrics.py` | Turns, DOS, fill rate, GMROI | Simple calculations. ~60 lines. |
| `planning/mrp.py` | Time-phased MRP explosion | BOM traversal + netting + lot sizing + offsetting. ~200 lines. |
| `planning/ddmrp.py` | Buffer sizing, net flow equation, execution alerts | DDMRP logic from Demand Driven Institute spec. ~250 lines. |
| `planning/capacity.py` | RCCP, finite loading, bottleneck ID | Load accumulation + constraint checking. ~150 lines. |
| `planning/aggregate.py` | Chase/level/mixed, LP formulation | Needs scipy.optimize.linprog for LP. ~200 lines. |
| `planning/atp.py` | Available-to-promise | Running balance of uncommitted inventory. ~80 lines. |
| `planning/ctp.py` | Capable-to-promise | ATP + capacity check + capability check. ~120 lines. |
| `planning/siop.py` | Demand/supply balancing, scenario comparison | Horizon-based planning with constraint propagation. ~300 lines. |
| `probabilistic/monte_carlo.py` | Plan-level Monte Carlo simulation | Sample from distributions, propagate through BOM/routing. ~200 lines. |
| `probabilistic/yield_model.py` | Yield from Cpk/Ppk distribution | Normal CDF computation from capability indices. ~60 lines. |
| `probabilistic/risk_scoring.py` | Supply risk from quality metrics | Weighted scoring from claim data, quality scores. ~80 lines. |
| `probabilistic/scenario.py` | What-if engine with distribution parameters | Run plan N times with perturbed inputs. ~100 lines. |
| `core/bom.py` | Bill of materials tree traversal | Recursive BOM with level-by-level explosion. ~100 lines. |
| `core/calendar.py` | Production calendar, shifts, holidays | Workday counting + shift mapping. ~80 lines. |

## Absorption Strategy

If we ever need to go fully standalone (zero pip dependencies beyond stdlib):

1. **Keep numpy** — the cost of removing it is too high, and it's BSD licensed.
2. **Absorb scipy.stats** — vendor the 5 distributions we actually use (normal, poisson, binomial, beta, gamma). ~200 lines.
3. **Absorb scipy.optimize.linprog** — vendor a revised simplex. ~200 lines. Or switch aggregate planning to heuristic (chase/level are formula-based, don't need LP).
4. **Absorb Holt-Winters from statsmodels** — ~120 lines. Drop ARIMA.
5. **Absorb newsvendor + Wagner-Whitin from stockpyl** — ~130 lines combined. MIT licensed.

Total absorption effort: ~800 lines of Python to be fully dependency-free (except numpy). One week of work.

## License Summary

| Dependency | License | Commercial use | Absorb legal risk |
|-----------|---------|---------------|-------------------|
| numpy | BSD-3 | Yes | None |
| scipy | BSD-3 | Yes | None |
| statsmodels | BSD-3 | Yes | None |
| stockpyl | MIT | Yes | None — attribution required |

All dependencies are permissively licensed. No GPL, no AGPL, no copyleft risk.
