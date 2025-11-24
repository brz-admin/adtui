"""Modal dialogs for ADTUI."""

from textual.screen import ModalScreen
from textual.app import ComposeResult
from textual.containers import Vertical, Horizontal, ScrollableContainer
from textual.widgets import Static, Button, Input, ListView, ListItem, Label


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


class EditUserDialog(ModalScreen):
    """Dialog to edit user attributes."""
    
    def __init__(self, dn: str, conn, user_details):
        super().__init__()
        self.dn = dn
        self.conn = conn
        self.user_details = user_details
    
    def compose(self) -> ComposeResult:
        cn = str(self.user_details.entry.cn.value) if self.user_details and hasattr(self.user_details.entry, 'cn') else "User"
        
        yield Vertical(
            Static(f"[bold cyan]Edit User: {cn}[/bold cyan]\n", id="question"),
            Input(placeholder="Display Name", id="displayName", value=str(self.user_details.entry.displayName.value) if hasattr(self.user_details.entry, 'displayName') else ""),
            Input(placeholder="Email", id="mail", value=str(self.user_details.entry.mail.value) if hasattr(self.user_details.entry, 'mail') else ""),
            Input(placeholder="Description", id="description", value=str(self.user_details.entry.description.value) if hasattr(self.user_details.entry, 'description') else ""),
            Horizontal(
                Button("Save", variant="success", id="save"),
                Button("Cancel", variant="primary", id="cancel"),
                id="dialog-buttons"
            ),
            id="dialog"
        )
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "save":
            try:
                changes = {}
                display_name = self.query_one("#displayName", Input).value
                mail = self.query_one("#mail", Input).value
                description = self.query_one("#description", Input).value
                
                from ldap3 import MODIFY_REPLACE
                
                if display_name:
                    self.conn.modify(self.dn, {'displayName': [(MODIFY_REPLACE, [display_name])]})
                if mail:
                    self.conn.modify(self.dn, {'mail': [(MODIFY_REPLACE, [mail])]})
                if description:
                    self.conn.modify(self.dn, {'description': [(MODIFY_REPLACE, [description])]})
                
                self.app.notify("User updated successfully", severity="information")
                self.dismiss(True)
            except Exception as e:
                self.app.notify(f"Error updating user: {e}", severity="error")
        else:
            self.dismiss(False)


class ManageGroupsDialog(ModalScreen):
    """Dialog to manage user's group memberships."""
    
    def __init__(self, dn: str, conn, user_details):
        super().__init__()
        self.dn = dn
        self.conn = conn
        self.user_details = user_details
    
    def compose(self) -> ComposeResult:
        cn = str(self.user_details.entry.cn.value) if self.user_details and hasattr(self.user_details.entry, 'cn') else "User"
        
        groups_list = ListView()
        if self.user_details and self.user_details.member_of:
            for group in self.user_details.member_of:
                groups_list.append(ListItem(Label(group['name'])))
        
        yield Vertical(
            Static(f"[bold cyan]Group Memberships: {cn}[/bold cyan]\n\nSelect a group and press Enter to remove\n", id="question"),
            ScrollableContainer(groups_list, id="groups-list"),
            Horizontal(
                Button("Close", variant="primary", id="close"),
                id="dialog-buttons"
            ),
            id="dialog"
        )
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss()


class ManageGroupMembersDialog(ModalScreen):
    """Dialog to manage group members."""
    
    def __init__(self, dn: str, conn, group_details):
        super().__init__()
        self.dn = dn
        self.conn = conn
        self.group_details = group_details
    
    def compose(self) -> ComposeResult:
        cn = str(self.group_details.entry.cn.value) if self.group_details and hasattr(self.group_details.entry, 'cn') else "Group"
        
        members_list = ListView()
        if self.group_details and self.group_details.members:
            for member in self.group_details.members:
                members_list.append(ListItem(Label(member['name'])))
        
        yield Vertical(
            Static(f"[bold cyan]Group Members: {cn}[/bold cyan]\n\nMembers ({len(self.group_details.members) if self.group_details else 0}):\n", id="question"),
            ScrollableContainer(members_list, id="members-list"),
            Horizontal(
                Button("Close", variant="primary", id="close"),
                id="dialog-buttons"
            ),
            id="dialog"
        )
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss()
