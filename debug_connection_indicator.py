#!/usr/bin/env python3

"""Debug script to test connection indicator visibility."""

import sys
sys.path.insert(0, '/home/ti2103@domman.ad/dev/adtui')

from textual.app import App, ComposeResult
from textual.widgets import Static, Footer, Input
from textual.containers import Horizontal, Vertical
from textual.css.query import NoMatches

class DebugConnectionIndicator(App):
    """Debug app to test connection indicator visibility."""
    
    CSS = """
    Screen {
        layout: vertical;
    }
    
    #connection-status {
        height: 1;
        padding: 0 1;
        background: $surface;
        border-bottom: heavy $background 80%;
        text-align: center;
        content-align: center middle;
        color: white;
        background: red;  # Make it very visible for debugging
    }
    
    Horizontal {
        layout: horizontal;
        height: 1fr;
    }
    
    Vertical {
        layout: vertical;
        height: 1fr;
    }
    
    #tree-area {
        height: 1fr;
        background: blue;
    }
    
    #details-area {
        height: 70%;
        background: green;
    }
    
    #search-results {
        height: 30%;
        background: yellow;
    }
    """
    
    def compose(self) -> ComposeResult:
        """Compose the debug UI layout."""
        print("DEBUG: Starting compose method")
        
        # Connection status widget at the top
        self.connection_status_widget = Static("🔴 DISCONNECTED - DEBUG", id="connection-status")
        print(f"DEBUG: Created connection status widget: {self.connection_status_widget}")
        yield self.connection_status_widget
        print("DEBUG: Yielded connection status widget")
        
        with Horizontal():
            print("DEBUG: Inside Horizontal container")
            with Vertical():
                yield Static("Tree Area", id="tree-area")
            with Vertical():
                yield Static("Details Area", id="details-area")
                yield Static("Search Results", id="search-results")
        
        yield Footer()
        yield Input(placeholder=": command/search", id="command-input")
        print("DEBUG: Finished compose method")
    
    def on_mount(self):
        """Handle mount event."""
        print("DEBUG: App mounted, checking widgets...")
        
        try:
            # Try to find the connection status widget
            connection_status = self.query_one("#connection-status", Static)
            print(f"DEBUG: Found connection status widget: {connection_status}")
            print(f"DEBUG: Widget ID: {connection_status.id}")
            print(f"DEBUG: Widget styles: {connection_status.styles}")
            print(f"DEBUG: Widget display: {connection_status.styles.display}")
            print(f"DEBUG: Widget text: '{connection_status.renderable}'")
            
            # Test updating the widget
            connection_status.update("🟢 CONNECTED - DEBUG")
            print("DEBUG: Updated connection status text")
            
        except NoMatches as e:
            print(f"DEBUG: ERROR - Connection status widget not found: {e}")
            
            # List all widgets to see what's available
            print("DEBUG: Available widgets:")
            for widget in self.query(Static):
                print(f"  - Static widget with ID: {widget.id}")
                
        except Exception as e:
            print(f"DEBUG: ERROR in on_mount: {e}")
            import traceback
            traceback.print_exc()
        
        # Check screen layout
        print(f"DEBUG: Screen layout: {self.screen.styles.layout}")
        print(f"DEBUG: Screen children: {len(list(self.screen.children))}")
        
        for i, child in enumerate(self.screen.children):
            print(f"DEBUG: Child {i}: {child} (ID: {getattr(child, 'id', 'None')})")

if __name__ == "__main__":
    print("DEBUG: Starting debug app...")
    
    try:
        app = DebugConnectionIndicator()
        print("DEBUG: App created, running...")
        app.run()
    except Exception as e:
        print(f"DEBUG: App failed: {e}")
        import traceback
        traceback.print_exc()