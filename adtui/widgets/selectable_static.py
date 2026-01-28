"""Selectable static widget with mouse text selection and auto-copy to clipboard."""

import logging
import re
import subprocess
import sys
from typing import Optional, List, Tuple

from textual.widgets import Static
from textual.events import MouseDown, MouseUp, MouseMove
from rich.text import Text

logger = logging.getLogger(__name__)


class SelectableStatic(Static):
    """Static widget with mouse text selection and automatic clipboard copy."""

    DEFAULT_CSS = """
    SelectableStatic {
        overflow-y: auto;
        overflow-x: hidden;
    }
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.selection_start: Optional[Tuple[int, int]] = None
        self.selection_end: Optional[Tuple[int, int]] = None
        self.is_selecting: bool = False
        self._content_lines: List[str] = []
        self._last_selected_text: Optional[str] = None

    def _get_plain_text_lines(self) -> List[str]:
        """Extract plain text lines from the current renderable content."""
        try:
            renderable = self.renderable
            if renderable is None:
                return []

            # Convert renderable to plain text
            if isinstance(renderable, Text):
                plain = renderable.plain
            elif isinstance(renderable, str):
                # Strip Rich markup tags
                plain = re.sub(r'\[/?[^\]]+\]', '', renderable)
            else:
                plain = str(renderable)

            # Strip ANSI escape codes
            ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
            plain = ansi_escape.sub('', plain)

            return plain.split('\n')
        except Exception as e:
            logger.debug(f"Error getting plain text: {e}")
            return []

    def on_mouse_down(self, event: MouseDown) -> None:
        """Start text selection on mouse down."""
        if event.button == 1:  # Left mouse button
            self.is_selecting = True
            self.selection_start = (event.x, event.y + self.scroll_offset.y)
            self.selection_end = None
            self._content_lines = self._get_plain_text_lines()
            self.capture_mouse()

    def on_mouse_move(self, event: MouseMove) -> None:
        """Update selection during mouse drag."""
        if self.is_selecting:
            self.selection_end = (event.x, event.y + self.scroll_offset.y)

    def on_mouse_up(self, event: MouseUp) -> None:
        """Finalize selection and copy to clipboard on mouse up."""
        if not self.is_selecting:
            return

        self.is_selecting = False
        self.release_mouse()

        if self.selection_start is None:
            return

        self.selection_end = (event.x, event.y + self.scroll_offset.y)

        # Extract selected text
        selected_text = self._extract_selected_text()

        if selected_text and selected_text.strip():
            self._last_selected_text = selected_text
            self._copy_to_clipboard(selected_text)

        # Clear selection
        self.selection_start = None
        self.selection_end = None

    def _extract_selected_text(self) -> str:
        """Extract text between selection start and end positions."""
        if not self.selection_start or not self.selection_end:
            return ""

        if not self._content_lines:
            return ""

        start_x, start_y = self.selection_start
        end_x, end_y = self.selection_end

        # Ensure start is before end
        if start_y > end_y or (start_y == end_y and start_x > end_x):
            start_x, start_y, end_x, end_y = end_x, end_y, start_x, start_y

        # Clamp to valid range
        start_y = max(0, min(start_y, len(self._content_lines) - 1))
        end_y = max(0, min(end_y, len(self._content_lines) - 1))

        selected_lines = []

        for line_idx in range(start_y, end_y + 1):
            if line_idx >= len(self._content_lines):
                break

            line = self._content_lines[line_idx]

            if line_idx == start_y and line_idx == end_y:
                # Single line selection
                start_col = max(0, min(start_x, len(line)))
                end_col = max(0, min(end_x, len(line)))
                if start_col <= end_col:
                    selected_lines.append(line[start_col:end_col])
            elif line_idx == start_y:
                # First line of multi-line selection
                start_col = max(0, min(start_x, len(line)))
                selected_lines.append(line[start_col:])
            elif line_idx == end_y:
                # Last line of multi-line selection
                end_col = max(0, min(end_x, len(line)))
                selected_lines.append(line[:end_col])
            else:
                # Middle lines
                selected_lines.append(line)

        return '\n'.join(selected_lines)

    def _copy_to_clipboard(self, text: str) -> None:
        """Copy text to system clipboard with cross-platform support."""
        try:
            # Strip ANSI escape codes
            ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
            clean_text = ansi_escape.sub('', text)

            # Remove excessive whitespace but keep newlines
            clean_text = '\n'.join(
                line.strip() for line in clean_text.split('\n') if line.strip()
            )

            if not clean_text:
                return

            # Try different clipboard commands based on OS
            if sys.platform == 'linux':
                # Try wl-copy first (Wayland), then xclip (X11)
                for cmd in ['wl-copy', 'xclip -selection clipboard']:
                    try:
                        subprocess.run(
                            cmd,
                            input=clean_text,
                            text=True,
                            check=True,
                            shell=True,
                            capture_output=True,
                        )
                        self._notify_copy_success(clean_text)
                        return
                    except (subprocess.CalledProcessError, FileNotFoundError):
                        continue
                # Fallback to pbcopy if available
                try:
                    subprocess.run(['pbcopy'], input=clean_text, text=True, check=True)
                    self._notify_copy_success(clean_text)
                    return
                except (subprocess.CalledProcessError, FileNotFoundError):
                    pass
            elif sys.platform == 'darwin':
                subprocess.run(['pbcopy'], input=clean_text, text=True, check=True)
                self._notify_copy_success(clean_text)
                return
            elif sys.platform == 'win32':
                subprocess.run(
                    ['clip'], input=clean_text, text=True, check=True, shell=True
                )
                self._notify_copy_success(clean_text)
                return

            # Clipboard not available
            logger.debug("Clipboard not available")

        except Exception as e:
            logger.debug(f"Failed to copy to clipboard: {e}")

    def _notify_copy_success(self, text: str) -> None:
        """Show notification for successful copy."""
        try:
            display_text = text[:50] + '...' if len(text) > 50 else text
            # Replace newlines with spaces for display
            display_text = display_text.replace('\n', ' ')
            self.app.notify(f"Copied: {display_text}", severity="information", timeout=2)
        except Exception:
            pass  # Silently fail if notification fails

    def get_last_selected_text(self) -> Optional[str]:
        """Return the last selected text, if any."""
        return self._last_selected_text

    def clear_last_selected_text(self) -> None:
        """Clear the stored last selected text."""
        self._last_selected_text = None
