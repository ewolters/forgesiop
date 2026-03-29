"""Bill of Materials — recursive tree traversal and explosion.

No external dependencies. Pure Python.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

from .types import BOMEntry


@dataclass
class BOMNode:
    """A node in the exploded BOM tree."""

    item_id: str
    quantity_per_parent: float
    scrap_factor: float
    level: int
    children: list[BOMNode]

    @property
    def quantity_with_scrap(self) -> float:
        return self.quantity_per_parent / (1 - self.scrap_factor) if self.scrap_factor < 1 else self.quantity_per_parent


class BOM:
    """Bill of materials manager.

    Build from a flat list of BOMEntry records. Explode to tree.
    Level-by-level explosion for MRP netting.
    """

    def __init__(self, entries: list[BOMEntry]):
        self._children: dict[str, list[BOMEntry]] = defaultdict(list)
        self._parents: dict[str, list[BOMEntry]] = defaultdict(list)
        for entry in entries:
            self._children[entry.parent_id].append(entry)
            self._parents[entry.child_id].append(entry)

    def get_children(self, item_id: str) -> list[BOMEntry]:
        """Direct children of an item."""
        return self._children.get(item_id, [])

    def get_parents(self, item_id: str) -> list[BOMEntry]:
        """Direct parents of an item (where-used)."""
        return self._parents.get(item_id, [])

    def explode(self, item_id: str, quantity: float = 1.0, level: int = 0, max_level: int = 20) -> BOMNode:
        """Recursively explode BOM from a top-level item.

        Returns a tree of BOMNode with quantities adjusted for scrap.
        """
        if level > max_level:
            return BOMNode(item_id=item_id, quantity_per_parent=quantity, scrap_factor=0, level=level, children=[])

        children = []
        for entry in self.get_children(item_id):
            child_qty = quantity * entry.quantity_per / (1 - entry.scrap_factor) if entry.scrap_factor < 1 else quantity * entry.quantity_per
            child_node = self.explode(entry.child_id, child_qty, level + 1, max_level)
            children.append(child_node)

        return BOMNode(
            item_id=item_id,
            quantity_per_parent=quantity,
            scrap_factor=0,
            level=level,
            children=children,
        )

    def low_level_codes(self) -> dict[str, int]:
        """Compute low-level codes for MRP sequencing.

        An item's low-level code is the deepest level at which it
        appears in ANY BOM. MRP processes items by low-level code
        (0 first, then 1, then 2...) to ensure parent demand is
        computed before child netting.
        """
        codes: dict[str, int] = {}

        def _traverse(item_id: str, level: int):
            if item_id in codes:
                codes[item_id] = max(codes[item_id], level)
            else:
                codes[item_id] = level
            for entry in self.get_children(item_id):
                _traverse(entry.child_id, level + 1)

        # Find top-level items (no parents)
        all_children = {e.child_id for entries in self._children.values() for e in entries}
        all_parents = set(self._children.keys())
        top_level = all_parents - all_children

        for item_id in top_level:
            _traverse(item_id, 0)

        return codes

    def indented_bom(self, item_id: str, quantity: float = 1.0) -> list[dict]:
        """Flat indented BOM list for display.

        Returns [{item_id, level, quantity, scrap_factor}]
        """
        result = []

        def _flatten(node: BOMNode):
            result.append({
                "item_id": node.item_id,
                "level": node.level,
                "quantity": node.quantity_per_parent,
                "scrap_factor": node.scrap_factor,
            })
            for child in node.children:
                _flatten(child)

        tree = self.explode(item_id, quantity)
        _flatten(tree)
        return result
