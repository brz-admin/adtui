"""Nouveautés (what's new) shown once after an update, in French.

The notes ship with the code, so they are available right after the update
without any network access. Add an entry to ``NOTES`` for every release that
has something users should know about.
"""

import logging
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# version -> list of short bullet points (French). Rich markup allowed.
NOTES: Dict[str, List[str]] = {
    "2.7.0": [
        "[bold]Plusieurs AD en même temps[/bold] : [cyan]:connect[/cyan] (ou la touche "
        "[cyan]+[/cyan]) ouvre une 2e connexion sans vous déconnecter. Les arbres "
        "s'empilent l'un sous l'autre.",
        "L'action est toujours faite avec le [bold]compte de l'arbre dans lequel vous "
        "êtes[/bold] ([cyan]Tab[/cyan] ou la souris pour changer d'arbre). Changer "
        "d'arbre efface la sélection, pour ne jamais agir sur le mauvais AD.",
        "[cyan]:close[/cyan] déconnecte seulement l'AD actif ; [cyan]:logout[/cyan] "
        "déconnecte tout.",
        "[bold]Déplacement (:m) plus simple[/bold] : tapez une partie du nom d'une OU "
        "(ex. [cyan]:m help[/cyan]), les OU correspondantes s'affichent. "
        "[cyan]↑↓[/cyan] choisir, [cyan]Tab[/cyan] compléter, [cyan]Entrée[/cyan] "
        "déplacer, [cyan]Échap[/cyan] annuler.",
        "Corrections : Tab ne fonctionnait pas dans l'autocomplétion, déplacement "
        "vers les conteneurs (ex. CN=Users), liste de suggestions qui restait affichée.",
    ],
}


def _parse(version: str) -> Tuple[int, ...]:
    version = version.split("-")[0].split("+")[0]
    parts = []
    for part in version.split(".")[:3]:
        try:
            parts.append(int(part))
        except ValueError:
            parts.append(0)
    while len(parts) < 3:
        parts.append(0)
    return tuple(parts)


def unseen_notes(
    current: str, last_seen: Optional[str], notes: Optional[Dict[str, List[str]]] = None
) -> List[Tuple[str, List[str]]]:
    """Notes for versions in ``(last_seen, current]``, newest first.

    With no ``last_seen`` (first launch of a release that has notes) only the
    current version's notes are returned.
    """
    notes = NOTES if notes is None else notes
    cur = _parse(current)
    if last_seen is None:
        return [(v, n) for v, n in notes.items() if _parse(v) == cur]
    seen = _parse(last_seen)
    found = [(v, n) for v, n in notes.items() if seen < _parse(v) <= cur]
    return sorted(found, key=lambda item: _parse(item[0]), reverse=True)


def format_notes(entries: List[Tuple[str, List[str]]]) -> str:
    """Rich markup text for the dialog."""
    blocks = []
    for version, items in entries:
        lines = [f"[bold cyan]Version {version}[/bold cyan]"]
        lines += [f"  • {item}" for item in items]
        blocks.append("\n".join(lines))
    return "\n\n".join(blocks)


class WhatsNewTracker:
    """Remembers the last version whose notes the user has seen."""

    def __init__(self, directory=None):
        from .platform_service import PlatformService

        base = directory or PlatformService.get_config_dir()
        self.file = base / "last_seen_version.txt"

    def load(self) -> Optional[str]:
        try:
            value = self.file.read_text().strip()
            return value or None
        except OSError:
            return None

    def save(self, version: str) -> None:
        try:
            self.file.parent.mkdir(parents=True, exist_ok=True)
            self.file.write_text(version)
        except OSError as e:
            logger.debug("Could not save last seen version: %s", e)
