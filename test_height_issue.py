#!/usr/bin/env python3

"""Test to check if height: 1 is the issue."""

import sys
sys.path.insert(0, '/home/ti2103@domman.ad/dev/adtui')

from textual.app import App, ComposeResult
from textual.widgets import Static, Footer, Input
from textual.containers import Horizontal, Vertical

class TestHeightApp(App):
    """Test app to check height issues."""
    
    CSS = """
    Screen {
        layout: vertical;
    }
    
    #connection-status {
        height: 1;
        padding: 0 1;
        background: red;
        border-bottom: heavy black;
        text-align: center;
        content-align: center middle;
        color: white;
    }
    
    #connection-status-tall {
        height: 3;
        padding: 0 1;
        background: blue;
        border-bottom: heavy black;
        text-align: center;
        content-align: center middle;
        color: white;
    }
    
    Horizontal {
        layout: horizontal;
        height: 1fr;
    }
    """
    
    def compose(self) -> ComposeResult:
        """Compose the test UI."""
        # Test with height: 1 (original)
        yield Static("HEIGHT 1 - Should be visible", id="connection-status")
        
        # Test with height: 3 (taller)
        yield Static("HEIGHT 3 - Should be visible", id="connection-status-tall")
        
        with Horizontal():
            yield Static("Left Content", id="left")
            yield Static("Right Content", id="right")
        
        yield Footer()

if __name__ == "__main__":
    try:
        app = TestHeightApp()
        app.run()
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()