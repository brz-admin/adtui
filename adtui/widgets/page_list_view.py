"""ListView subclass where PageUp/PageDown move the selection.

By default, ListView only binds up/down: PageUp/PageDown fall through to
ScrollView and scroll the viewport without moving the highlight. Pressing an
arrow key afterwards then snaps the view back to the old selection. This
subclass moves the highlight with the page keys instead.
"""

from textual.binding import Binding
from textual.widgets import ListView


class PageListView(ListView):
    """ListView that moves the selection on PageUp/PageDown."""

    BINDINGS = ListView.BINDINGS + [
        Binding("pagedown", "cursor_page_down", "Page Down", show=False),
        Binding("pageup", "cursor_page_up", "Page Up", show=False),
    ]

    def _page_size(self) -> int:
        """Number of visible items to move per page (at least 1)."""
        height = self.scrollable_content_region.height
        return max(1, height - 1)

    def _move_index(self, delta: int) -> None:
        """Move the highlight by delta items, clamped to the list bounds.

        Assigning self.index also scrolls the new item into view, so the
        selection and the viewport stay in sync.
        """
        if not self._nodes:
            return
        current = self.index if self.index is not None else 0
        self.index = min(max(current + delta, 0), len(self._nodes) - 1)

    def action_cursor_page_down(self) -> None:
        """Highlight the item one page below the current selection."""
        self._move_index(self._page_size())

    def action_cursor_page_up(self) -> None:
        """Highlight the item one page above the current selection."""
        self._move_index(-self._page_size())
