import configparser
import os
from ldap3 import Server, Connection, ALL
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Tree, Static, Input, Footer, ListView, ListItem, Label
from textual.binding import Binding
import getpass
from functools import lru_cache

from adtree import ADTree

# Load configuration
config = configparser.ConfigParser()
config.read('config.ini')

# Configuration
LDAP_SERVER = config['ldap']['server']
DOMAIN = config['ldap']['domain']
BASE_DN = config['ldap']['base_dn']
USE_SSL = config.getboolean('ldap', 'use_ssl', fallback=False)
LAST_USER_FILE = 'last_user.txt'

last_user = ''
if os.path.exists(LAST_USER_FILE):
    with open(LAST_USER_FILE, 'r') as f:
        last_user = f.read().strip()

def get_ldap_connection(username, password):
    """Create and return an Active Directory connection using simple bind."""
    bind_dn = f"{username}@{DOMAIN}"
    port = 636 if USE_SSL else 389
    server = Server(LDAP_SERVER, port=port, use_ssl=USE_SSL, get_info=ALL)
    try:
        return Connection(server, user=bind_dn, password=password, auto_bind=True)
    except Exception as e:
        print(f"Failed to connect: {e}")
        raise

@lru_cache(maxsize=100)
def get_object_details(conn, dn):
    """Get detailed attributes for an object (cached)."""
    return
    try:
        conn.search(dn, '(objectClass=*)', attributes=['*'])
        if conn.entries:
            return conn.entries[0]
    except Exception as e:
        print(f"Error getting details for {dn}: {e}")
    return None

class DetailsPane(Static):
    def update_content(self, item_label, dn=None, conn=None):
        """Display details for the selected object."""
        self.update("Detail pane")
        if not item_label:
            self.update("Select an item to view details.")
            return
        if not dn or not conn:
            self.update(f"Details for: {item_label}\n\n[Select an object to view details]")
            return
        entry = get_object_details(conn, dn)
        if not entry:
            self.update(f"Details for: {item_label}\n\n[Could not load details]")
            return
        details = f"Details for: {item_label}\n\n"
        try:
            if hasattr(entry, 'entry_attributes'):
                for attr, values in entry.entry_attributes.items():
                    if attr != 'objectClass':
                        details += f"{attr}: {', '.join(str(v) for v in values)}\n"
            elif hasattr(entry, 'attributes'):
                for attr in entry.attributes:
                    if attr != 'objectClass':
                        values = entry[attr].value
                        if values:
                            details += f"{attr}: {', '.join(str(v) for v in values)}\n"
            else:
                details += "[Basic details only]\n"
                details += f"DN: {dn}\n"
        except Exception as e:
            details += f"Error getting details: {e}\n"
        self.update(details)

class SearchResultsPane(ListView):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.conn = None

    def populate(self, results, conn=None):
        self.clear()
        self.conn = conn
        for result in results:
            item = ListItem(Label(result["label"]))
            item.text = result["label"]
            item.data = result['dn']
            self.append(item)


class ADTUI(App):
    CSS = """
    Screen {
        layout: grid;
        grid-columns: 1fr 1fr 1fr;
        grid-rows: 1fr 3;
    }
    Horizontal {
        width: 100%;
    }
    Horizontal > Vertical:first-child {
        width: 30%;
        border-right: heavy $background 80%;
    }
    Horizontal > Vertical:last-child {
        width: 70%;
        height: 100%;
        layout: vertical;
    }
    
    #details-pane {
        height: 70%;
        border-bottom: heavy $background 80%;
    }
    Input {
        dock: bottom;
        height: 3;
    }
    #search-results-pane {
        height: 30%;
    }
    """
    BINDINGS = [
        Binding("escape", "quit", "Quit", show=True),
        Binding(":", "command_mode", "Command", show=True),
        Binding("r", "refresh_ou", "Refresh OU", show=True),
        Binding("s", "search", "Search", show=True),
        Binding("t", "test_search", "test", show=True),
    ]

    def action_test_search(self):
        """Populate test search results."""
        self.populate_test_search_results()

    def __init__(self, username, password):
        super().__init__()
        self.conn = get_ldap_connection(username, password)
        self.adtree = ADTree(self.conn, BASE_DN)
        self.details = DetailsPane(id="details-pane")
        self.search_results_pane = SearchResultsPane(id="search-results-pane")
        self.command_mode = False
        self.base_dn = BASE_DN

    def compose(self) -> ComposeResult:
        with Horizontal():
            with Vertical():
                yield self.adtree
            with Vertical():
                yield self.details
                yield self.search_results_pane
        yield Input(placeholder=": command/search", id="command-input")
        yield Footer()

    def on_mount(self):
        self.query_one("#command-input", Input).visible = False

    def action_command_mode(self):
        self.command_mode = True
        cmd_input = self.query_one("#command-input", Input)
        cmd_input.value = ":"
        cmd_input.visible = True
        cmd_input.focus()

    def action_refresh_ou(self):
        """Refresh the currently selected OU."""
        self.adtree.refresh_current_ou()

    def action_search(self):
        """Open search input."""
        self.action_command_mode()
        cmd_input = self.query_one("#command-input", Input)
        cmd_input.placeholder = "Search..."
        cmd_input.value = "s "

    def on_tree_node_selected(self, event: Tree.NodeSelected):
        """Show details when an object is selected."""
        node = event.node
        self.details.update_content(node.label, node.data, self.conn)

    def on_list_view_highlighted(self, event: ListView.Highlighted):
        """Show details when a search result is selected."""
        if event.list_view.id == "search-results-pane":
            item = event.item
            self.details.update_content(item.text, item.data, self.conn)

    def on_input_submitted(self, event: Input.Submitted):
        """Handle command/search input."""
        if self.command_mode:
            cmd = event.value.strip()
            if cmd.startswith("s "):
                query = cmd[2:]
                self.search_ad(query)
            self.query_one("#command-input", Input).visible = False
            self.command_mode = False

    def search_ad(self, query):
        """Search Active Directory."""
        try:
            self.conn.search(
                self.base_dn,
                f'(|(cn=*{query}*)(objectClass=user)(objectClass=computer)(objectClass=group))',
                attributes=['cn', 'objectClass']
            )
            results = []
            for entry in self.conn.entries:
                cn = str(entry['cn']) if 'cn' in entry else "Unknown"
                obj_classes = [str(cls).lower() for cls in entry['objectClass']]
                if 'user' in obj_classes and 'computer' not in obj_classes:
                    label = f"👤 {cn}"
                elif 'computer' in obj_classes:
                    label = f"💻 {cn}"
                elif 'group' in obj_classes:
                    label = f"👥 {cn}"
                else:
                    label = f"📄 {cn}"
                results.append({'label': label, 'dn': entry.entry_dn})
            self.search_results_pane.populate(results)
            self.search_results_pane.styles.display = "block"
        except Exception as e:
            print(f"Error searching AD: {e}")

    def populate_test_search_results(self):
        """Populate the search results pane with test data."""
        test_results = [
            {"label": "👤 Test User 1", "dn": "cn=Test User 1,ou=Users,dc=example,dc=com"},
            {"label": "💻 Test Computer 1", "dn": "cn=Test Computer 1,ou=Computers,dc=example,dc=com"},
            {"label": "👥 Test Group 1", "dn": "cn=Test Group 1,ou=Groups,dc=example,dc=com"},
        ]
        self.search_results_pane.populate(test_results)

if __name__ == "__main__":
    print(f"Active Directory TUI - Domain: {DOMAIN}")
    username = "REDACTED_USERNAME"  # input(f"Username [{last_user}]: ") or last_user
    password = "REDACTED_PASSWORD" #getpass.getpass("Password: ")
    with open(LAST_USER_FILE, 'w') as f:
        f.write(username)
    try:
        app = ADTUI(username, password)
        app.run()
    except Exception as e:
        print(f"Failed to connect: {e}")

