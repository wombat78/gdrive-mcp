from __future__ import annotations
from typing import Callable, Iterable

_MAX_ANCESTRY_HOPS = 100


class OutOfScopeError(Exception):
    """Raised when a target file/folder is outside the allowed folders."""


class ScopeGuard:
    def __init__(self, allowed: Iterable[str], get_parents: Callable[[str], list[str]]):
        self._allowed = set(allowed)
        self._get_parents = get_parents

    @property
    def allowed_ids(self) -> frozenset[str]:
        """Public read-only view of the allowed folder IDs."""
        return frozenset(self._allowed)

    def _is_in_scope(self, file_id: str) -> bool:
        # Iterative DFS up the parent chain; cap depth to avoid cycles/runaways.
        # The seen-check happens BEFORE fetching parents so each node's parents
        # are fetched at most once.
        seen: set[str] = set()
        frontier = [file_id]
        for _ in range(_MAX_ANCESTRY_HOPS):
            if not frontier:
                break
            node = frontier.pop()
            if node in self._allowed:
                return True
            if node in seen:
                continue
            seen.add(node)
            frontier.extend(self._get_parents(node))
        return False

    def assert_in_scope(self, file_id: str) -> None:
        if not self._is_in_scope(file_id):
            raise OutOfScopeError(
                f"'{file_id}' is not within the allowed folders {sorted(self._allowed)}"
            )

    # Creation target: the destination folder must itself be in scope.
    assert_folder_allowed = assert_in_scope
