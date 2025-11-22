"""Modal dialogs for ADTUI."""

from textual.screen import ModalScreen
from textual.app import ComposeResult
from textual.containers import Vertical, Horizontal
from textual.widgets import Static, Button, Input


class BaseConfirmDialog(ModalScreen[bool]):
    """Base class for confirmation dialogs."""
    
    def __init__(self, title: str, message: str, confirm_text: str, confirm_variant: str = "primary"):
        super().__init__()
        self.title = title
        self.message = message
        self.confirm_text = confirm_text
        self.confirm_variant = confirm_variant
    
    def compose(self) -> ComposeResult:
        yield Vertical(
            Static(f"{self.title}\n\n{self.message}", id="question"),
            Horizontal(
                Button(self.confirm_text, variant=self.confirm_variant, id="confirm"),
                Button("Cancel", variant="primary", id="cancel"),
                id="dialog-buttons"
            ),
            id="dialog"
        )
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss(event.button.id == "confirm")


class ConfirmDeleteDialog(BaseConfirmDialog):
    """Dialog to confirm object deletion."""
    
    def __init__(self, label: str, dn: str):
        super().__init__(
            title="[bold red]Confirm Deletion[/bold red]",
            message=f"Are you sure you want to delete:\n\n{label}\n\nDN: {dn}\n\nThis action cannot be undone!",
            confirm_text="Delete",
            confirm_variant="error"
        )


class ConfirmMoveDialog(BaseConfirmDialog):
    """Dialog to confirm object move."""
    
    def __init__(self, label: str, from_dn: str, to_dn: str):
        super().__init__(
            title="[bold yellow]Confirm Move[/bold yellow]",
            message=f"Move object:\n{label}\n\nFrom: {from_dn}\n\nTo: {to_dn}\n\nConfirm?",
            confirm_text="Move",
            confirm_variant="success"
        )


class ConfirmRestoreDialog(BaseConfirmDialog):
    """Dialog to confirm object restoration."""
    
    def __init__(self, name: str, dn: str):
        super().__init__(
            title="[bold cyan]Restore Deleted Object[/bold cyan]",
            message=f"Restore: {name}\n\nDN: {dn}\n\nConfirm?",
            confirm_text="Restore",
            confirm_variant="success"
        )


class ConfirmUndoDialog(BaseConfirmDialog):
    """Dialog to confirm undo operation."""
    
    def __init__(self, message: str):
        super().__init__(
            title="[bold yellow]Undo Last Operation[/bold yellow]",
            message=f"{message}\n\nConfirm?",
            confirm_text="Undo",
            confirm_variant="warning"
        )


class CreateOUDialog(ModalScreen):
    """Dialog to create a new OU."""
    
    def __init__(self, path: str):
        super().__init__()
        self.path = path
    
    def compose(self) -> ComposeResult:
        yield Vertical(
            Static(f"[bold green]Create New OU[/bold green]\n\nPath: {self.path}\n", id="question"),
            Input(placeholder="Description (optional)", id="ou-description"),
            Horizontal(
                Button("Create", variant="success", id="create"),
                Button("Cancel", variant="primary", id="cancel"),
                id="dialog-buttons"
            ),
            id="dialog"
        )
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "create":
            description_input = self.query_one("#ou-description", Input)
            self.dismiss((self.path, description_input.value))
        else:
            self.dismiss(None)
