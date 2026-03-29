"""Demand classification — ABC, XYZ, ABC-XYZ matrix."""

from __future__ import annotations


def abc_classification(
    items: list[dict],
    value_key: str = "annual_value",
    a_threshold: float = 0.80,
    b_threshold: float = 0.95,
) -> list[dict]:
    """ABC classification by cumulative value.

    Args:
        items: [{id, annual_value, ...}]
        a_threshold: cumulative % for A class (default 80%)
        b_threshold: cumulative % for A+B class (default 95%)

    Returns:
        items with 'abc_class' added, sorted by value descending.
    """
    sorted_items = sorted(items, key=lambda x: x.get(value_key, 0), reverse=True)
    total = sum(i.get(value_key, 0) for i in sorted_items)
    if total == 0:
        for item in sorted_items:
            item["abc_class"] = "C"
        return sorted_items

    cumulative = 0
    for item in sorted_items:
        cumulative += item.get(value_key, 0)
        pct = cumulative / total
        if pct <= a_threshold:
            item["abc_class"] = "A"
        elif pct <= b_threshold:
            item["abc_class"] = "B"
        else:
            item["abc_class"] = "C"

    return sorted_items


def xyz_classification(
    items: list[dict],
    cv_key: str = "cv",
    x_threshold: float = 0.5,
    y_threshold: float = 1.0,
) -> list[dict]:
    """XYZ classification by coefficient of variation.

    X = stable demand (CV < 0.5)
    Y = variable demand (0.5 <= CV < 1.0)
    Z = erratic demand (CV >= 1.0)
    """
    for item in items:
        cv = item.get(cv_key, 0)
        if cv < x_threshold:
            item["xyz_class"] = "X"
        elif cv < y_threshold:
            item["xyz_class"] = "Y"
        else:
            item["xyz_class"] = "Z"
    return items


def abc_xyz_matrix(items: list[dict]) -> dict[str, list[dict]]:
    """Combine ABC and XYZ into a 9-cell matrix.

    Returns: {"AX": [...], "AY": [...], ..., "CZ": [...]}
    """
    matrix = {}
    for item in items:
        abc = item.get("abc_class", "C")
        xyz = item.get("xyz_class", "Z")
        key = f"{abc}{xyz}"
        matrix.setdefault(key, []).append(item)
    return matrix
