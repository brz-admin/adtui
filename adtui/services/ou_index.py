"""OU index - in-memory list of every OU/container of a domain.

Used by the ``:move`` path autocomplete: the whole OU tree is fetched once (in
the background) and then filtered locally, so suggestions appear instantly while
typing instead of costing an LDAP round trip per keystroke.
"""

import re
import threading
import time
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional

from ldap3.utils.dn import parse_dn

_ESCAPE_HEX = re.compile(r"\\([0-9a-fA-F]{2})")
_ESCAPE_CHAR = re.compile(r"\\(.)")


def _unescape(value: str) -> str:
    """Undo RFC 4514 escaping of an RDN value (``Smith\\, John`` -> ``Smith, John``)."""
    value = _ESCAPE_HEX.sub(lambda m: chr(int(m.group(1), 16)), value)
    return _ESCAPE_CHAR.sub(r"\1", value)


def dn_to_display_path(dn: str, base_dn: str) -> str:
    """Convert a DN to a ``Parent/Child`` path relative to ``base_dn``.

    Unlike PathService.dn_to_path this keeps ``CN=`` components, so containers
    such as ``CN=Users`` are part of the path.
    """
    try:
        parts = parse_dn(dn, escape=False)
        base_parts = parse_dn(base_dn, escape=False)
    except Exception:
        return ""
    depth = len(parts) - len(base_parts)
    if depth <= 0:
        return ""
    names = [_unescape(p[1]) for p in parts[:depth]]
    names.reverse()
    return "/".join(names)


@dataclass(frozen=True)
class OUEntry:
    """One OU or container of the directory."""

    dn: str
    path: str  # relative to the base DN, e.g. "Departments/IT"

    @property
    def name(self) -> str:
        return self.path.rsplit("/", 1)[-1]

    @property
    def depth(self) -> int:
        return self.path.count("/") + 1

    @property
    def parent_path(self) -> str:
        return self.path.rsplit("/", 1)[0] if "/" in self.path else ""


class OUIndex:
    """Thread-safe, lazily loaded index of a domain's OUs and containers."""

    TTL_SECONDS = 300
    RETRY_SECONDS = 30

    def __init__(self, base_dn: str):
        self.base_dn = base_dn
        self.last_error: Optional[str] = None
        self._failed_at: Optional[float] = None
        self._invalidated = False
        self._entries: List[OUEntry] = []
        self._by_path: Dict[str, OUEntry] = {}
        self._loaded_at: Optional[float] = None
        self._lock = threading.Lock()
        self._loading = False

    # ------------------------------------------------------------------ state

    @property
    def is_loaded(self) -> bool:
        return self._loaded_at is not None

    @property
    def is_loading(self) -> bool:
        return self._loading

    @property
    def is_stale(self) -> bool:
        return (
            self._loaded_at is None
            or self._invalidated
            or time.monotonic() - self._loaded_at > self.TTL_SECONDS
        )

    def invalidate(self) -> None:
        """Mark the index as out of date (e.g. after creating/moving an OU).

        The old content stays usable until the refreshed one arrives.
        """
        self._invalidated = True

    # ---------------------------------------------------------------- loading

    def set_entries(self, dns: List[str]) -> None:
        """Replace the index content from a list of DNs."""
        entries = []
        for dn in dns:
            path = dn_to_display_path(dn, self.base_dn)
            if path:
                entries.append(OUEntry(dn=dn, path=path))
        entries.sort(key=lambda e: e.path.lower())
        with self._lock:
            self._entries = entries
            self._by_path = {e.path.lower(): e for e in entries}
            self._loaded_at = time.monotonic()
            self._invalidated = False
            self._failed_at = None

    def load(self, fetch_dns: Callable[[], List[str]]) -> bool:
        """Fetch and index all OUs. Returns False if a load is already running.

        Errors are kept in ``last_error`` (and retried after RETRY_SECONDS)
        instead of being raised, since this runs in a background thread.
        """
        with self._lock:
            if self._loading:
                return False
            self._loading = True
        try:
            self.set_entries(fetch_dns())
            self.last_error = None
        except Exception as e:
            self.last_error = str(e) or e.__class__.__name__
            self._failed_at = time.monotonic()
        finally:
            self._loading = False
        return True

    @property
    def needs_load(self) -> bool:
        """True when a (re)load should be started now."""
        if self._loading or not self.is_stale:
            return False
        if self._failed_at is not None:
            return time.monotonic() - self._failed_at > self.RETRY_SECONDS
        return True

    # ---------------------------------------------------------------- lookups

    @staticmethod
    def normalize(path: str) -> str:
        """Normalise user typed path: trim, unify separators, drop empty parts."""
        parts = [p.strip() for p in path.replace("\\", "/").split("/")]
        return "/".join(p for p in parts if p)

    def find(self, path: str) -> Optional[OUEntry]:
        """Exact (case-insensitive) lookup of ``path``."""
        return self._by_path.get(self.normalize(path).lower())

    def children(self, parent_path: str) -> List[OUEntry]:
        """Direct children of ``parent_path`` ("" = top level)."""
        parent = self.normalize(parent_path).lower()
        with self._lock:
            return [e for e in self._entries if e.parent_path.lower() == parent]

    def search(self, query: str, limit: int = 50) -> List[OUEntry]:
        """Suggestions for what the user typed after ``:move``.

        * empty query             -> top-level OUs
        * ``A/B/`` (trailing /)   -> children of A/B
        * anything else           -> OUs whose path contains the text, best first:
          path starts with it, then name starts with the last segment, then
          substring, then all words present (any order).
        """
        raw = query.replace("\\", "/")
        if not raw.strip():
            return self.children("")[:limit]
        if raw.rstrip().endswith("/"):
            if self.find(raw) is not None:
                return self.children(raw)[:limit]
            # "dep/": not an existing OU, treat as a partial name

        norm = self.normalize(raw).lower()
        last = norm.rsplit("/", 1)[-1]
        words = [w for w in norm.replace("/", " ").split() if w]

        scored = []
        with self._lock:
            entries = list(self._entries)
        for entry in entries:
            low = entry.path.lower()
            if low.startswith(norm):
                score = 0
            elif entry.name.lower().startswith(last) and norm in low:
                score = 1
            elif entry.name.lower().startswith(last) and "/" not in norm:
                score = 1
            elif norm in low:
                score = 2
            elif words and all(w in low for w in words):
                score = 3
            else:
                continue
            scored.append((score, entry.depth, low, entry))

        scored.sort(key=lambda t: t[:3])
        return [t[3] for t in scored[:limit]]
