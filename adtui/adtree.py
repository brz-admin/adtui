# ad_tree.py
from textual.widgets import Tree
from ldap3 import Connection
from functools import lru_cache
import threading
from typing import Optional
from services.connection_manager import ConnectionManager

class ADTree(Tree):
    def __init__(self, connection_manager: Optional[ConnectionManager], base_dn: str):
        super().__init__("AD Tree")
        self.connection_manager = connection_manager
        self.base_dn = base_dn
        self.loaded_ous = set()  # Track which OUs have been populated
        self.ou_cache = {}      # Cache for OU contents
        self.build_tree()

    def build_tree(self):
        """Build complete tree structure with direct children only."""
        if self.connection_manager is None:
            return
        try:
            # Clear existing tree nodes
            self.root.remove_children()
            
            # Start with base DN as root
            root_node = self.root.add(f"📁 {self.base_dn}", expand=True)
            self._build_direct_children(root_node, self.base_dn)
            
            # Ensure tree root is expanded to show base DN node
            self.root.expand()
        except Exception as e:
            print(f"Error building tree: {e}")
            import traceback
            traceback.print_exc()
    
    def load_root(self):
        """Load root of tree (alias for build_tree)."""
        self.build_tree()

    def _build_direct_children(self, parent_node, parent_dn):
        """Build only the direct children of an OU."""
        try:
            def search_op(conn: Connection):
                # Search for direct child OUs only
                conn.search(parent_dn, '(objectClass=organizationalUnit)',
                           attributes=['ou', 'distinguishedName'],
                           search_scope='LEVEL',
                           size_limit=1000)

                # Sort OUs alphabetically
                ous = sorted(conn.entries, key=lambda x: str(x['ou']).lower())

                for ou in ous:
                    ou_dn = ou.entry_dn
                    if self._is_direct_child(ou_dn, parent_dn):
                        ou_name = str(ou['ou']) if 'ou' in ou else "Unknown OU"
                        ou_node = parent_node.add(f"📁 {ou_name}", expand=False)
                        ou_node.data = ou_dn
            
            if self.connection_manager:
                self.connection_manager.execute_with_retry(search_op)
            else:
                return

        except Exception as e:
            print(f"Error building children for {parent_dn}: {e}")
            import traceback
            traceback.print_exc()

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

            def populate_op(conn: Connection):
                # Clear existing children before populating
                parent_node.remove_children()

                # First add direct child OUs
                self._build_direct_children(parent_node, ou_dn)

                # Search for non-OU objects with a more specific filter
                conn.search(ou_dn,
                           '(&(objectClass=*)(!(objectClass=organizationalUnit))(objectCategory=*))',
                           search_scope='LEVEL',
                           attributes=['cn', 'objectClass', 'userAccountControl'],
                           size_limit=1000)

                objects = []
                for entry in conn.entries:
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
            
            if self.connection_manager:
                self.connection_manager.execute_with_retry(populate_op)
            else:
                return

        except Exception as e:
            print(f"Error populating OU {ou_dn}: {e}")

    def populate_ou_sync(self, parent_node, ou_dn):
        """Synchronously populate an OU for navigation purposes."""
        self.populate_ou(parent_node, ou_dn, synchronous=True)

    def _populate_from_cache(self, parent_node, ou_dn):
        """Populate from cached results."""
        try:
            # Clear existing children before populating
            parent_node.remove_children()

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

    def _populate_ou_fresh(self, parent_node, ou_dn):
        """Populate an OU with fresh data (bypassing cache)."""
        try:
            def fresh_populate_op(conn: Connection):
                # Clear existing children before populating
                parent_node.remove_children()

                # First add direct child OUs
                self._build_direct_children(parent_node, ou_dn)

                # Search for non-OU objects with a more specific filter
                conn.search(ou_dn,
                           '(&(objectClass=*)(!(objectClass=organizationalUnit))(objectCategory=*))',
                           search_scope='LEVEL',
                           attributes=['cn', 'objectClass', 'userAccountControl'],
                           size_limit=1000)

                objects = []
                for entry in conn.entries:
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
            
            if self.connection_manager:
                self.connection_manager.execute_with_retry(fresh_populate_op)
            else:
                return

        except Exception as e:
            print(f"Error populating OU {ou_dn}: {e}")

    def refresh_current_ou(self):
        """Refresh currently selected OU."""
        if self.connection_manager is None:
            return
        if self.cursor_node and self.cursor_node.data:
            # Clear cache for this OU
            ou_dn = self.cursor_node.data
            if ou_dn in self.ou_cache:
                del self.ou_cache[ou_dn]
            if ou_dn in self.loaded_ous:
                self.loaded_ous.remove(ou_dn)
            
            # Clear and repopulate with fresh data
            self.cursor_node.remove_children()
            self._populate_ou_fresh(self.cursor_node, ou_dn)
        else:
            print("OU not loaded yet, expand it first to load it")
    
    def refresh_ou_by_dn(self, ou_dn: str):
        """Refresh a specific OU by finding its node in the tree."""
        if self.connection_manager is None:
            return
        
        # Find the node with this DN
        target_node = self._find_node_by_dn(self.root, ou_dn)
        if target_node:
            # Clear cache for this OU
            if ou_dn in self.ou_cache:
                del self.ou_cache[ou_dn]
            if ou_dn in self.loaded_ous:
                self.loaded_ous.remove(ou_dn)
            
            # Clear and repopulate with fresh data
            target_node.remove_children()
            self._populate_ou_fresh(target_node, ou_dn)
            
            # Expand the node to show refreshed content
            target_node.expand()
        else:
            print(f"Could not find OU node for DN: {ou_dn}")
    
    def _find_node_by_dn(self, node, target_dn: str):
        """Recursively find a tree node by its DN."""
        if hasattr(node, 'data') and node.data == target_dn:
            return node
        
        # Search children
        if hasattr(node, 'children'):
            for child in node.children:
                result = self._find_node_by_dn(child, target_dn)
                if result:
                    return result
        
        return None
