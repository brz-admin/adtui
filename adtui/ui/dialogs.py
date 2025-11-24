"""Modal dialogs for ADTUI."""

from textual.screen import ModalScreen
from textual.app import ComposeResult
from textual.containers import Vertical, Horizontal, ScrollableContainer
from textual.widgets import Static, Button, Input, ListView, ListItem, Label
import unicodedata


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
        entry = self.user_details.entry
        
        yield Vertical(
            Static(f"[bold cyan]Edit User: {cn}[/bold cyan]\n", id="question"),
            ScrollableContainer(
                Input(placeholder="Display Name", id="displayName", value=str(entry.displayName.value) if hasattr(entry, 'displayName') else ""),
                Input(placeholder="Given Name (First Name)", id="givenName", value=str(entry.givenName.value) if hasattr(entry, 'givenName') else ""),
                Input(placeholder="Surname (Last Name)", id="sn", value=str(entry.sn.value) if hasattr(entry, 'sn') else ""),
                Input(placeholder="Email", id="mail", value=str(entry.mail.value) if hasattr(entry, 'mail') else ""),
                Input(placeholder="Telephone", id="telephoneNumber", value=str(entry.telephoneNumber.value) if hasattr(entry, 'telephoneNumber') else ""),
                Input(placeholder="Mobile", id="mobile", value=str(entry.mobile.value) if hasattr(entry, 'mobile') else ""),
                Input(placeholder="Office", id="physicalDeliveryOfficeName", value=str(entry.physicalDeliveryOfficeName.value) if hasattr(entry, 'physicalDeliveryOfficeName') else ""),
                Input(placeholder="Department", id="department", value=str(entry.department.value) if hasattr(entry, 'department') else ""),
                Input(placeholder="Title", id="title", value=str(entry.title.value) if hasattr(entry, 'title') else ""),
                Input(placeholder="Description", id="description", value=str(entry.description.value) if hasattr(entry, 'description') else ""),
                Input(placeholder="Profile Path", id="profilePath", value=str(entry.profilePath.value) if hasattr(entry, 'profilePath') else ""),
                Input(placeholder="Home Directory", id="homeDirectory", value=str(entry.homeDirectory.value) if hasattr(entry, 'homeDirectory') else ""),
            ),
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
                from ldap3 import MODIFY_REPLACE
                
                fields = ['displayName', 'givenName', 'sn', 'mail', 'telephoneNumber', 'mobile', 
                         'physicalDeliveryOfficeName', 'department', 'title', 'description', 
                         'profilePath', 'homeDirectory']
                
                for field in fields:
                    value = self.query_one(f"#{field}", Input).value.strip()
                    if value:  # Only update if not empty
                        self.conn.modify(self.dn, {field: [(MODIFY_REPLACE, [value])]})
                
                self.app.notify("User updated successfully", severity="information")
                self.dismiss(True)
            except Exception as e:
                self.app.notify(f"Error updating user: {e}", severity="error")
        else:
            self.dismiss(False)


class ManageGroupsDialog(ModalScreen):
    """Dialog to manage user's group memberships."""
    
    BINDINGS = [
        ("escape", "dismiss_dialog", "Close"),
        ("delete", "remove_group", "Remove"),
        ("a", "add_group", "Add Group"),
    ]
    
    def __init__(self, dn: str, conn, user_details):
        super().__init__()
        self.dn = dn
        self.conn = conn
        self.user_details = user_details
        self.groups_data = {}
    
    def compose(self) -> ComposeResult:
        cn = str(self.user_details.entry.cn.value) if self.user_details and hasattr(self.user_details.entry, 'cn') else "User"
        
        yield Vertical(
            Static(f"[bold cyan]Group Memberships: {cn}[/bold cyan]\n\nMember of {len(self.user_details.member_of) if self.user_details else 0} groups\n[dim]Delete: Remove | A: Add | Esc: Close[/dim]\n", id="question"),
            Input(placeholder="Search groups to add...", id="group-search"),
            ListView(id="groups-list"),
            Horizontal(
                Button("Add Group", variant="success", id="add"),
                Button("Remove", variant="error", id="remove"),
                Button("Close", variant="primary", id="close"),
                id="dialog-buttons"
            ),
            id="dialog"
        )
    
    def on_mount(self) -> None:
        """Populate the groups list after mounting."""
        groups_list = self.query_one("#groups-list", ListView)
        if self.user_details and self.user_details.member_of:
            for group in self.user_details.member_of:
                item = ListItem(Label(group['name']))
                self.groups_data[id(item)] = group
                groups_list.append(item)
        groups_list.focus()
    
    def action_dismiss_dialog(self) -> None:
        self.dismiss()
    
    def action_remove_group(self) -> None:
        """Remove selected group."""
        groups_list = self.query_one("#groups-list", ListView)
        if groups_list.highlighted_child:
            item = groups_list.highlighted_child
            group_data = self.groups_data.get(id(item))
            if group_data:
                try:
                    from ldap3 import MODIFY_DELETE
                    self.conn.modify(group_data['dn'], {'member': [(MODIFY_DELETE, [self.dn])]})
                    groups_list.remove_items([item])
                    del self.groups_data[id(item)]
                    self.app.notify(f"Removed from {group_data['name']}", severity="information")
                except Exception as e:
                    self.app.notify(f"Error removing from group: {e}", severity="error")
    
    def action_add_group(self) -> None:
        """Focus search input to add group."""
        self.query_one("#group-search", Input).focus()
    
    def on_input_changed(self, event: Input.Changed) -> None:
        """Search for groups as user types."""
        if event.input.id == "group-search":
            query = event.value.strip()
            if len(query) >= 2:
                self._search_groups(query)
            elif len(query) == 0:
                # Clear search results
                groups_list = self.query_one("#groups-list", ListView)
                groups_list.clear()
                # Repopulate with current memberships
                if self.user_details and self.user_details.member_of:
                    for group in self.user_details.member_of:
                        item = ListItem(Label(group['name']))
                        self.groups_data[id(item)] = group
                        groups_list.append(item)
    
    def _search_groups(self, query: str) -> None:
        """Search for groups matching query and show in list."""
        try:
            base_dn = ','.join(self.dn.split(',')[1:])  # Get base DN from user DN
            self.conn.search(
                base_dn,
                f'(&(objectClass=group)(cn=*{query}*))',
                attributes=['cn', 'distinguishedName'],
                size_limit=50
            )
            
            # Clear and show search results
            groups_list = self.query_one("#groups-list", ListView)
            groups_list.clear()
            self.groups_data.clear()
            
            if self.conn.entries:
                for entry in self.conn.entries:
                    group_name = str(entry.cn.value)
                    group_dn = entry.entry_dn
                    
                    # Mark if already a member
                    is_member = any(g['dn'] == group_dn for g in (self.user_details.member_of or []))
                    label_text = f"{group_name} [dim](member)[/dim]" if is_member else group_name
                    
                    item = ListItem(Label(label_text))
                    self.groups_data[id(item)] = {'name': group_name, 'dn': group_dn, 'is_member': is_member}
                    groups_list.append(item)
                
                self.app.notify(f"Found {len(self.conn.entries)} groups", severity="information")
            else:
                self.app.notify(f"No groups found matching '{query}'", severity="information")
        except Exception as e:
            self.app.notify(f"Search error: {e}", severity="error")
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "remove":
            self.action_remove_group()
        elif event.button.id == "add":
            # Add by search text
            search_input = self.query_one("#group-search", Input)
            query = search_input.value.strip()
            if query:
                self._add_group_by_name(query)
        else:
            self.dismiss()
    
    def on_list_view_selected(self, event: ListView.Selected) -> None:
        """Add to selected group from search results."""
        if event.list_view.id == "groups-list":
            item = event.item
            group_data = self.groups_data.get(id(item))
            if group_data and not group_data.get('is_member', False):
                self._add_to_group(group_data)
    
    def _add_group_by_name(self, group_name: str) -> None:
        """Add user to group by search then selection."""
        # Just trigger search, user selects from results
        self._search_groups(group_name)
    
    def _add_to_group(self, group_data: dict) -> None:
        """Add user to the specified group."""
        try:
            from ldap3 import MODIFY_ADD
            self.conn.modify(group_data['dn'], {'member': [(MODIFY_ADD, [self.dn])]})
            self.app.notify(f"Added to {group_data['name']}", severity="information")
            
            # Clear search and refresh
            self.query_one("#group-search", Input).value = ""
        except Exception as e:
            self.app.notify(f"Error adding to group: {e}", severity="error")


class ManageGroupMembersDialog(ModalScreen):
    """Dialog to manage group members."""
    
    BINDINGS = [
        ("escape", "dismiss_dialog", "Close"),
    ]
    
    def __init__(self, dn: str, conn, group_details):
        super().__init__()
        self.dn = dn
        self.conn = conn
        self.group_details = group_details
    
    def compose(self) -> ComposeResult:
        cn = str(self.group_details.entry.cn.value) if self.group_details and hasattr(self.group_details.entry, 'cn') else "Group"
        
        yield Vertical(
            Static(f"[bold cyan]Group Members: {cn}[/bold cyan]\n\nMembers ({len(self.group_details.members) if self.group_details else 0})\n[dim]Esc: Close[/dim]\n", id="question"),
            ListView(id="members-list"),
            Horizontal(
                Button("Close", variant="primary", id="close"),
                id="dialog-buttons"
            ),
            id="dialog"
        )
    
    def on_mount(self) -> None:
        """Populate the members list after mounting."""
        members_list = self.query_one("#members-list", ListView)
        if self.group_details and self.group_details.members:
            for member in self.group_details.members:
                members_list.append(ListItem(Label(member['name'])))
        members_list.focus()
    
    def action_dismiss_dialog(self) -> None:
        self.dismiss()
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss()


class EditAttributesDialog(ModalScreen):
    """Dialog to view and edit all LDAP attributes."""
    
    BINDINGS = [
        ("escape", "dismiss_dialog", "Close"),
    ]
    
    def __init__(self, dn: str, conn):
        super().__init__()
        self.dn = dn
        self.conn = conn
        self.attributes = {}
    
    def compose(self) -> ComposeResult:
        yield Vertical(
            Static(f"[bold cyan]All Attributes[/bold cyan]\n{self.dn}\n[dim]Select attribute and press Enter to edit | Esc: Close[/dim]\n", id="question"),
            ListView(id="attributes-list"),
            Horizontal(
                Button("Close", variant="primary", id="close"),
                id="dialog-buttons"
            ),
            id="dialog"
        )
    
    def on_mount(self) -> None:
        """Load and display all attributes."""
        try:
            self.conn.search(
                self.dn,
                '(objectClass=*)',
                search_scope='BASE',
                attributes=['*']
            )
            if self.conn.entries:
                entry = self.conn.entries[0]
                attrs_list = self.query_one("#attributes-list", ListView)
                
                for attr in sorted(entry.entry_attributes_as_dict.keys()):
                    values = entry.entry_attributes_as_dict[attr]
                    if isinstance(values, list):
                        value_str = ', '.join(str(v) for v in values[:3])
                        if len(values) > 3:
                            value_str += f" ... (+{len(values)-3} more)"
                    else:
                        value_str = str(values)
                    
                    # Truncate long values
                    if len(value_str) > 60:
                        value_str = value_str[:60] + "..."
                    
                    label = f"[bold]{attr}:[/bold] {value_str}"
                    item = ListItem(Label(label))
                    self.attributes[id(item)] = {'name': attr, 'values': values}
                    attrs_list.append(item)
                
                attrs_list.focus()
        except Exception as e:
            self.app.notify(f"Error loading attributes: {e}", severity="error")
    
    def action_dismiss_dialog(self) -> None:
        self.dismiss()
    
    def on_list_view_selected(self, event: ListView.Selected) -> None:
        """Edit selected attribute."""
        item = event.item
        attr_data = self.attributes.get(id(item))
        if attr_data:
            # Open edit dialog for this attribute
            self.app.push_screen(
                EditSingleAttributeDialog(self.dn, self.conn, attr_data['name'], attr_data['values']),
                self._refresh_after_edit
            )
    
    def _refresh_after_edit(self, result) -> None:
        """Refresh attributes list after editing."""
        if result:
            # Reload the attributes
            attrs_list = self.query_one("#attributes-list", ListView)
            attrs_list.clear()
            self.attributes.clear()
            self.on_mount()
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss()


class EditSingleAttributeDialog(ModalScreen):
    """Dialog to edit a single attribute."""
    
    def __init__(self, dn: str, conn, attr_name: str, current_values):
        super().__init__()
        self.dn = dn
        self.conn = conn
        self.attr_name = attr_name
        self.current_values = current_values
    
    def compose(self) -> ComposeResult:
        # Convert values to string
        if isinstance(self.current_values, list):
            value_str = '\n'.join(str(v) for v in self.current_values)
        else:
            value_str = str(self.current_values)
        
        yield Vertical(
            Static(f"[bold cyan]Edit Attribute: {self.attr_name}[/bold cyan]\n\n[dim]For multi-value: one per line[/dim]\n", id="question"),
            Input(placeholder="New value", id="attr-value", value=value_str),
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
                from ldap3 import MODIFY_REPLACE
                new_value = self.query_one("#attr-value", Input).value.strip()
                
                if new_value:
                    # Split by newlines for multi-value
                    values = [v.strip() for v in new_value.split('\n') if v.strip()]
                    self.conn.modify(self.dn, {self.attr_name: [(MODIFY_REPLACE, values)]})
                    self.app.notify(f"Updated {self.attr_name}", severity="information")
                    self.dismiss(True)
                else:
                    self.app.notify("Value cannot be empty", severity="warning")
            except Exception as e:
                self.app.notify(f"Error: {e}", severity="error")
        else:
            self.dismiss(False)


class SetPasswordDialog(ModalScreen):
    """Dialog to set user password."""
    
    def __init__(self, dn: str, conn):
        super().__init__()
        self.dn = dn
        self.conn = conn
    
    def compose(self) -> ComposeResult:
        cn = self.dn.split(',')[0].split('=')[1] if ',' in self.dn else self.dn
        yield Vertical(
            Static(f"[bold cyan]Set Password for: {cn}[/bold cyan]\n", id="question"),
            Static("New password:"),
            Input(placeholder="Enter new password", password=True, id="password1"),
            Static("\nConfirm password:"),
            Input(placeholder="Re-enter password", password=True, id="password2"),
            Static(""),  # Spacer
            Horizontal(
                Button("Set Password", variant="success", id="save"),
                Button("Cancel", variant="primary", id="cancel"),
                id="dialog-buttons"
            ),
            id="dialog",
            classes="password-dialog"
        )
    
    def on_mount(self) -> None:
        """Focus first password field."""
        self.query_one("#password1", Input).focus()
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "save":
            try:
                pwd1_input = self.query_one("#password1", Input)
                pwd2_input = self.query_one("#password2", Input)
                
                pwd1 = pwd1_input.value
                pwd2 = pwd2_input.value
                
                print(f"DEBUG: pwd1 length: {len(pwd1)}, pwd2 length: {len(pwd2)}")
                print(f"DEBUG: pwd1 repr: {repr(pwd1)}, pwd2 repr: {repr(pwd2)}")
                
                if len(pwd1) == 0 or len(pwd2) == 0:
                    self.app.notify("Password cannot be empty", severity="warning")
                    return
                
                if pwd1 != pwd2:
                    self.app.notify("Passwords do not match", severity="warning")
                    return
                
                if len(pwd1) < 8:
                    self.app.notify("Password must be at least 8 characters", severity="warning")
                    return
                
                # Set password using ldap3
                from ldap3 import MODIFY_REPLACE
                
                # Encode password for AD (must be in quotes and UTF-16-LE)
                password_value = f'"{pwd1}"'.encode('utf-16-le')
                
                result = self.conn.modify(self.dn, {'unicodePwd': [(MODIFY_REPLACE, [password_value])]})
                
                if result and self.conn.result['result'] == 0:
                    self.app.notify("Password updated successfully", severity="information")
                    self.dismiss(True)
                else:
                    error_msg = self.conn.result.get('message', 'Unknown error')
                    self.app.notify(f"Failed to set password: {error_msg}", severity="error")
            except Exception as e:
                self.app.notify(f"Error setting password: {e}", severity="error")
                import traceback
                traceback.print_exc()
        else:
            self.dismiss(False)
