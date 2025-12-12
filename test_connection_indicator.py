#!/usr/bin/env python3

"""Test script to verify connection indicator visibility."""

import sys
import os

# Add the adtui directory to Python path
sys.path.insert(0, '/home/ti2103@domman.ad/dev/adtui')

from textual.app import App, ComposeResult
from textual.widgets import Static, Footer, Input
from textual.containers import Horizontal, Vertical

class TestConnectionIndicator(App):
    """Test app to verify connection indicator layout."""
    
    CSS_PATH = "adtui/styles.tcss"
    
    def compose(self) -> ComposeResult:
        """Compose the test UI layout."""
        # Connection status widget at the top
        self.connection_status_widget = Static("🔴 Disconnected", id="connection-status")
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
        # Test that connection status widget exists and is visible
        connection_status = self.query_one("#connection-status", Static)
        print(f"Connection status widget found: {connection_status}")
        print(f"Connection status text: {str(connection_status)}")
        print(f"Connection status styles: {connection_status.styles}")
        
        # Test layout structure
        print("\nLayout structure:")
        print(f"Screen children: {list(self.screen.children)}")
        
        # Update connection status to test visibility
        connection_status.update("🟢 Connected")
        print(f"Updated connection status text: {str(connection_status)}")

if __name__ == "__main__":
    app = TestConnectionIndicator()
    
    # Run in headless mode for testing
    try:
        app.run(headless=True)
        print("\nTest completed successfully!")
    except Exception as e:
        print(f"Test failed: {e}")
        import traceback
        traceback.print_exc()