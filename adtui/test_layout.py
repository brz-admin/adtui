"""Simple test to verify basic layout works."""

from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Static, Footer, Input, Tree

class TestApp(App):
    """Test application with minimal layout."""
    
    CSS = """
    Screen {
        layout: grid;
        grid-size: 1 3;
        grid-rows: 1fr auto auto;
    }
    
    Horizontal {
        width: 100%;
        height: 100%;
        background: blue;
    }
    
    Vertical {
        height: 100%;
        border: solid green;
    }
    
    .left {
        width: 30%;
        background: red;
    }
    
    .right {
        width: 70%;
        background: yellow;
    }
    
    Static {
        height: 100%;
        content-align: center middle;
    }
    
    Tree {
        height: 100%;
    }
    """
    
    def compose(self) -> ComposeResult:
        """Compose the UI."""
        print("COMPOSE CALLED")
        with Horizontal():
            with Vertical(classes="left"):
                yield Static("LEFT PANE", id="left")
            with Vertical(classes="right"):
                yield Static("RIGHT PANE", id="right")
        yield Input(placeholder="Input here", id="test-input")
        yield Footer()
    
    def on_mount(self):
        """Handle mount."""
        print("ON_MOUNT CALLED")
        print("App is running!")

if __name__ == "__main__":
    print("Starting test app...")
    app = TestApp()
    app.run()
    print("App closed")
