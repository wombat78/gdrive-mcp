from __future__ import annotations
from typing import Callable, Iterable


class OutOfScopeError(Exception):
    """Raised when a target file/folder is outside the allowed folders."""


class ScopeGuard:
    def __init__(self, allowed: Iterable[str], get_parents: Callable[[str], list[str]]):
        self._allowed = set(allowed)
        self._get_parents = get_parents

    def _is_in_scope(self, file_id: str) -> bool:
        # BFS up the parent chain; cap depth to avoid cycles/runaways.
        seen: set[str] = set()
        frontier = [file_id]
        for _ in range(50):
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
