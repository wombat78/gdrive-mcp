from __future__ import annotations
from typing import Callable, Iterable

_MAX_ANCESTRY_HOPS = 100


class OutOfScopeError(Exception):
    """Raised when a target file/folder is outside the allowed folders."""


class ScopeGuard:
    def __init__(
        self,
        allowed_folder_ids: Iterable[str],
        allowed_drive_ids: Iterable[str],
        get_parents: Callable[[str], list[str]],
        get_drive_id: Callable[[str], str | None],
    ):
        self._allowed_folders = set(allowed_folder_ids)
        self._allowed_drives = set(allowed_drive_ids)
        self._get_parents = get_parents
        self._get_drive_id = get_drive_id

    @property
    def allowed_ids(self) -> frozenset[str]:
        """Public read-only view of the allowed folder IDs."""
        return frozenset(self._allowed_folders)

    @property
    def allowed_drive_ids(self) -> frozenset[str]:
        """Public read-only view of the allowed drive IDs."""
        return frozenset(self._allowed_drives)

    def _is_in_scope(self, file_id: str) -> bool:
        # Check driveId rule first: item's drive must be in the trusted set,
        # and the trusted set must be non-empty (fail-closed: empty set never matches).
        drive_id = self._get_drive_id(file_id)
        # `and self._allowed_drives` is an explicit empty-set/None fail-closed guard: an empty allowed-drives set must never match, even if drive_id happens to be falsy/None.
        if drive_id in self._allowed_drives and self._allowed_drives:
            return True

        # Iterative DFS up the parent chain; cap depth to avoid cycles/runaways.
        # The seen-check happens BEFORE fetching parents so each node's parents
        # are fetched at most once.
        seen: set[str] = set()
        frontier = [file_id]
        for _ in range(_MAX_ANCESTRY_HOPS):
            if not frontier:
                break
            node = frontier.pop()
            if node in self._allowed_folders:
                return True
            if node in seen:
                continue
            seen.add(node)
            frontier.extend(self._get_parents(node))
        return False

    def assert_in_scope(self, file_id: str) -> None:
        if not self._is_in_scope(file_id):
            raise OutOfScopeError(
                f"'{file_id}' is not within the allowed folders {sorted(self._allowed_folders)}"
            )

    # Creation target: the destination folder must itself be in scope.
    assert_folder_allowed = assert_in_scope
