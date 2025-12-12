#!/usr/bin/env python3

"""Final test to confirm connection indicator is visible."""

import sys
sys.path.insert(0, '/home/ti2103@domman.ad/dev/adtui')

from textual.app import App, ComposeResult
from textual.widgets import Static, Footer, Input
from textual.containers import Horizontal, Vertical

class FinalTestApp(App):
    """Final test app with the corrected CSS."""
    
    CSS_PATH = "adtui/styles.tcss"
    
    def compose(self) -> ComposeResult:
        """Compose the final test UI."""
        # Connection status widget at the top (should now be visible with height: 3)
        self.connection_status_widget = Static("🔴 DISCONNECTED - FINAL TEST", id="connection-status")
        yield self.connection_status_widget
        
        with Horizontal():
            with Vertical():
                yield Static("Tree Area", id="tree-area")
            with Vertical():
                yield Static("Details Area", id="details-area")
                yield Static("Search Results", id="search-results")
        
        yield Footer()
        yield Input(placeholder=": command/search", id="command-input")
    
    def on_mount(self):
        """Handle mount event."""
        # Update connection status to test visibility
        self.connection_status_widget.update("🟢 CONNECTED - FINAL TEST")

if __name__ == "__main__":
    try:
        app = FinalTestApp()
        app.run()
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()