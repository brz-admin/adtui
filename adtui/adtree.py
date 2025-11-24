# ad_tree.py
from textual.widgets import Tree
from ldap3 import Connection
from functools import lru_cache
import threading

class ADTree(Tree):
    def __init__(self, conn, base_dn):
        super().__init__("AD Tree")
        self.conn = conn
        self.base_dn = base_dn
        self.loaded_ous = set()  # Track which OUs have been populated
        self.ou_cache = {}      # Cache for OU contents
        self.build_tree()

    def build_tree(self):
        """Build the complete tree structure with direct children only."""
        try:
            # Start with the base DN as root
            root_node = self.root.add(f"📁 {self.base_dn}", expand=True)
            self._build_direct_children(root_node, self.base_dn)
        except Exception as e:
            print(f"Error building tree: {e}")

    def _build_direct_children(self, parent_node, parent_dn):
        """Build only the direct children of an OU."""
        try:
            # Search for direct child OUs only
            self.conn.search(parent_dn, '(objectClass=organizationalUnit)',
                           attributes=['ou', 'distinguishedName'],
                           search_scope='LEVEL',
                           size_limit=1000)

            # Sort OUs alphabetically
            ous = sorted(self.conn.entries, key=lambda x: str(x['ou']).lower())

            for ou in ous:
                ou_dn = ou.entry_dn
                if self._is_direct_child(ou_dn, parent_dn):
                    ou_name = str(ou['ou']) if 'ou' in ou else "Unknown OU"
                    ou_node = parent_node.add(f"📁 {ou_name}", expand=False)
                    ou_node.data = ou_dn

        except Exception as e:
            print(f"Error building children for {parent_dn}: {e}")

    def _is_direct_child(self, child_dn, parent_dn):
        """Check if child_dn is a direct child of parent_dn."""
        child_components = child_dn.split(',')
        if len(child_components) <= 1:
            return False
        return ','.join(child_components[1:]) == parent_dn

    def on_tree_node_expanded(self, event):
        """Load OU contents when expanded."""
        node = event.node
        if node.data and node.data not in self.loaded_ous:
            self.loaded_ous.add(node.data)
            # Use a thread to prevent UI freezing
            threading.Thread(target=self.populate_ou, args=(node, node.data)).start()

    def ensure_node_loaded(self, node):
        """Ensure a node's contents are loaded synchronously."""
        if node.data and node.data not in self.loaded_ous:
            self.loaded_ous.add(node.data)
            self.populate_ou_sync(node, node.data)

    def populate_ou(self, parent_node, ou_dn, synchronous=False):
        """Populate an OU with its contents."""
        try:
            # Check cache first
            if ou_dn in self.ou_cache:
                self._populate_from_cache(parent_node, ou_dn)
                return

            # First add direct child OUs
            self._build_direct_children(parent_node, ou_dn)

            # Search for non-OU objects with a more specific filter
            self.conn.search(ou_dn,
                           '(&(objectClass=*)(!(objectClass=organizationalUnit))(objectCategory=*))',
                           search_scope='LEVEL',
                           attributes=['cn', 'objectClass', 'userAccountControl'],
                           size_limit=1000)

            objects = []
            for entry in self.conn.entries:
                if self._is_direct_child(entry.entry_dn, ou_dn):
                    objects.append(entry)

            # Cache the results
            self.ou_cache[ou_dn] = objects

            # Add objects to the tree
            for entry in objects:
                cn = str(entry['cn']) if 'cn' in entry else "Unknown"
                obj_classes = [str(cls).lower() for cls in entry['objectClass']]
                entry_dn = entry.entry_dn
                
                if 'user' in obj_classes and 'computer' not in obj_classes:
                    uac = int(entry['userAccountControl'].value)
                    is_disabled = (uac & 2) == 2

                    if is_disabled:
                        node = parent_node.add_leaf(f"[dim]👤 {cn}[/]")
                    else:
                        node = parent_node.add_leaf(f"👤 {cn}")
                    node.data = entry_dn
                elif 'computer' in obj_classes:
                    node = parent_node.add_leaf(f"💻 {cn}")
                    node.data = entry_dn
                elif 'group' in obj_classes:
                    node = parent_node.add_leaf(f"👥 {cn}")
                    node.data = entry_dn

        except Exception as e:
            print(f"Error populating OU {ou_dn}: {e}")

    def populate_ou_sync(self, parent_node, ou_dn):
        """Synchronously populate an OU for navigation purposes."""
        self.populate_ou(parent_node, ou_dn, synchronous=True)

    def _populate_from_cache(self, parent_node, ou_dn):
        """Populate from cached results."""
        try:
            # First add direct child OUs
            self._build_direct_children(parent_node, ou_dn)

            # Add objects from cache
            for entry in self.ou_cache[ou_dn]:
                cn = str(entry['cn']) if 'cn' in entry else "Unknown"
                obj_classes = [str(cls).lower() for cls in entry['objectClass']]
                entry_dn = entry.entry_dn

                if 'user' in obj_classes and 'computer' not in obj_classes:
                    node = parent_node.add_leaf(f"👤 {cn}")
                    node.data = entry_dn
                elif 'computer' in obj_classes:
                    node = parent_node.add_leaf(f"💻 {cn}")
                    node.data = entry_dn
                elif 'group' in obj_classes:
                    node = parent_node.add_leaf(f"👥 {cn}")
                    node.data = entry_dn

        except Exception as e:
            print(f"Error populating from cache for {ou_dn}: {e}")

    def refresh_current_ou(self):
        """Refresh the currently selected OU."""
        if self.cursor_node and self.cursor_node.data:
            # Clear cache for this OU
            ou_dn = self.cursor_node.data
            if ou_dn in self.ou_cache:
                del self.ou_cache[ou_dn]
            if ou_dn in self.loaded_ous:
                self.loaded_ous.remove(ou_dn)
            
            # Clear and repopulate
            self.cursor_node.remove_children()
            self.populate_ou(self.cursor_node, ou_dn)
        else:
            print("OU not loaded yet, expand it first to load it")
