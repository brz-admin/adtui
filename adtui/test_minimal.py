"""Minimal test to debug layout issue."""

from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Static, Footer, Input, Tree

class MinimalADTUI(App):
    """Minimal version of ADTUI to test layout."""
    
    CSS = """
    Screen {
        layout: grid;
        grid-size: 1 3;
        grid-rows: 1fr auto auto;
    }

    Horizontal {
        width: 100%;
        height: 100%;
        row-span: 1;
        background: blue;
    }

    Horizontal > Vertical:first-child {
        width: 30%;
        height: 100%;
        border-right: heavy green;
        background: red;
    }

    Horizontal > Vertical:last-child {
        width: 70%;
        height: 100%;
        background: yellow;
    }

    Tree {
        height: 100%;
    }

    #details-pane {
        height: 70%;
        border: solid white;
        padding: 1;
    }

    #search-results-pane {
        height: 30%;
        border: solid white;
        display: none;
    }

    #command-input {
        height: 3;
        row-span: 1;
    }

    Footer {
        height: auto;
        row-span: 1;
    }
    """
    
    def __init__(self):
        super().__init__()
        print("MinimalADTUI __init__ called")
        
        # Initialize widgets before compose (like your app does)
        self.adtree = Tree("Test Tree")
        self.details = Static("Details Pane Content Here", id="details-pane")
        self.search_pane = Static("Search Results", id="search-results-pane")
    
    def compose(self) -> ComposeResult:
        """Compose the UI layout."""
        print("compose() called")
        with Horizontal():
            with Vertical():
                print("Yielding tree")
                yield self.adtree
            with Vertical():
                print("Yielding details and search")
                yield self.details
                yield self.search_pane
        print("Yielding input and footer")
        yield Input(placeholder=": command/search", id="command-input")
        yield Footer()
    
    def on_mount(self):
        """Handle mount event."""
        print("on_mount() called")
        
        # Add nodes to tree after mount
        self.adtree.root.add("Item 1")
        self.adtree.root.add("Item 2")
        self.adtree.root.add("Item 3")
        
        print(f"Tree root has {len(self.adtree.root.children)} children")
        
        cmd_input = self.query_one("#command-input", Input)
        cmd_input.visible = False
        print("on_mount() complete")

if __name__ == "__main__":
    print("Starting minimal test app...")
    app = MinimalADTUI()
    app.run()
    print("App closed")
