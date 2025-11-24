"""LDAP Service - Handles all Active Directory operations."""

from typing import List, Dict, Optional, Tuple
from ldap3 import Connection, MODIFY_DELETE, MODIFY_REPLACE, MODIFY_ADD
from datetime import datetime
import sys
import os

# Add parent directory to path to import constants
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from constants import ObjectIcon, ObjectType, SearchScope, LDAPControl


class LDAPService:
    """Handles all LDAP/Active Directory operations."""
    
    def __init__(self, connection: Connection, base_dn: str):
        """Initialize LDAP service.
        
        Args:
            connection: Active LDAP connection
            base_dn: Base Distinguished Name for the domain
        """
        self.conn = connection
        self.base_dn = base_dn
    
    def search_objects(self, query: str, object_types: Optional[List[str]] = None) -> List[Dict]:
        """Search for AD objects by cn or sAMAccountName.
        
        Args:
            query: Search query string
            object_types: List of object types to search for (user, computer, group)
            
        Returns:
            List of dictionaries containing label and dn
        """
        if object_types is None:
            object_types = ['user', 'computer', 'group']
        
        # Build object class filter
        if len(object_types) == 1:
            obj_filter = f'(objectClass={object_types[0]})'
        else:
            obj_filter = '(|' + ''.join([f'(objectClass={obj})' for obj in object_types]) + ')'
        
        ldap_filter = f'(&(|(cn=*{query}*)(sAMAccountName=*{query}*)){obj_filter})'
        
        try:
            self.conn.search(
                self.base_dn,
                ldap_filter,
                attributes=['cn', 'objectClass', 'sAMAccountName'],
                size_limit=1000
            )
            
            results = []
            for entry in self.conn.entries:
                cn = str(entry['cn']) if 'cn' in entry else "Unknown"
                obj_classes = [str(cls).lower() for cls in entry['objectClass']]
                
                icon = self._get_object_icon(obj_classes)
                label = f"{icon} {cn}"
                
                results.append({
                    'label': label,
                    'dn': entry.entry_dn,
                    'cn': cn,
                    'object_classes': obj_classes
                })
            
            return results
        except Exception as e:
            raise Exception(f"Search failed: {e}")
    
    def create_ou(self, ou_name: str, parent_dn: str, description: str = "") -> Tuple[bool, str]:
        """Create a new Organizational Unit.
        
        Args:
            ou_name: Name of the OU
            parent_dn: Parent DN where OU will be created
            description: Optional description
            
        Returns:
            Tuple of (success: bool, message: str)
        """
        try:
            ou_dn = f"ou={ou_name},{parent_dn}"
            
            attributes = {
                'objectClass': ['top', 'organizationalUnit'],
                'ou': ou_name
            }
            
            if description:
                attributes['description'] = description
            
            result = self.conn.add(ou_dn, attributes=attributes)
            
            if result:
                return True, f"Successfully created OU: {ou_name}"
            else:
                error_msg = self.conn.result.get('message', 'Unknown error')
                return False, f"Failed to create OU: {error_msg}"
        except Exception as e:
            return False, f"Error creating OU: {e}"
    
    def delete_object(self, dn: str) -> Tuple[bool, str]:
        """Delete an AD object.
        
        Args:
            dn: Distinguished Name of object to delete
            
        Returns:
            Tuple of (success: bool, message: str)
        """
        try:
            result = self.conn.delete(dn)
            
            if result:
                return True, "Successfully deleted object. Use :recycle to restore if needed."
            else:
                error_msg = self.conn.result.get('message', 'Unknown error')
                return False, f"Failed to delete: {error_msg}"
        except Exception as e:
            return False, f"Error deleting object: {e}"
    
    def move_object(self, dn: str, target_ou: str) -> Tuple[bool, str, Optional[str]]:
        """Move an AD object to a different OU.
        
        Args:
            dn: Current Distinguished Name
            target_ou: Target OU Distinguished Name
            
        Returns:
            Tuple of (success: bool, message: str, new_dn: Optional[str])
        """
        try:
            # Extract the RDN
            rdn = dn.split(',')[0]
            
            # Perform the move
            result = self.conn.modify_dn(dn, rdn, new_superior=target_ou)
            
            if result:
                new_dn = f"{rdn},{target_ou}"
                return True, f"Successfully moved object to {target_ou}", new_dn
            else:
                error_msg = self.conn.result.get('message', 'Unknown error')
                return False, f"Failed to move: {error_msg}", None
        except Exception as e:
            return False, f"Error moving object: {e}", None
    
    def validate_ou_exists(self, ou_dn: str) -> bool:
        """Check if an OU exists.
        
        Args:
            ou_dn: OU Distinguished Name
            
        Returns:
            True if OU exists, False otherwise
        """
        try:
            self.conn.search(
                ou_dn,
                '(objectClass=organizationalUnit)',
                search_scope='BASE',
                attributes=['ou']
            )
            return len(self.conn.entries) > 0
        except:
            return False
    
    def search_ous(self, base_dn: str, prefix: str = "", limit: int = 50) -> List[Dict]:
        """Search for OUs at a specific level.
        
        Args:
            base_dn: Base DN to search from
            prefix: Optional prefix filter
            limit: Maximum results
            
        Returns:
            List of OU dictionaries
        """
        try:
            self.conn.search(
                base_dn,
                '(objectClass=organizationalUnit)',
                search_scope='LEVEL',
                attributes=['ou'],
                size_limit=limit
            )
            
            ous = []
            for entry in self.conn.entries:
                ou_name = str(entry.ou.value) if hasattr(entry, 'ou') else None
                if ou_name:
                    if not prefix or ou_name.lower().startswith(prefix.lower()):
                        ous.append({
                            'name': ou_name,
                            'dn': entry.entry_dn
                        })
            
            return ous
        except Exception as e:
            return []
    
    def get_deleted_objects(self) -> List[Dict]:
        """Get objects from AD Recycle Bin.
        
        Returns:
            List of deleted object dictionaries
        """
        try:
            deleted_objects_dn = f"CN=Deleted Objects,{self.base_dn}"
            
            self.conn.search(
                deleted_objects_dn,
                '(isDeleted=TRUE)',
                search_scope='SUBTREE',
                attributes=['cn', 'objectClass', 'whenChanged', 'isDeleted'],
                controls=[(LDAPControl.SHOW_DELETED_OBJECTS, True, None)]
            )
            
            results = []
            for entry in self.conn.entries:
                cn = str(entry.cn.value) if hasattr(entry, 'cn') else "Unknown"
                obj_classes = [str(cls).lower() for cls in entry.objectClass] if hasattr(entry, 'objectClass') else []
                when_deleted = str(entry.whenChanged.value) if hasattr(entry, 'whenChanged') else "Unknown"
                
                icon = self._get_object_icon(obj_classes)
                
                results.append({
                    'label': f"{icon} [Deleted] {cn} ({when_deleted})",
                    'dn': entry.entry_dn,
                    'cn': cn
                })
            
            return results
        except Exception as e:
            raise Exception(f"Error accessing Recycle Bin: {e}. Ensure AD Recycle Bin is enabled.")
    
    def search_deleted_object(self, cn: str) -> Optional[Dict]:
        """Search for a specific deleted object.
        
        Args:
            cn: Common name to search for
            
        Returns:
            Dictionary with object info or None
        """
        try:
            deleted_objects_dn = f"CN=Deleted Objects,{self.base_dn}"
            
            self.conn.search(
                deleted_objects_dn,
                f'(&(isDeleted=TRUE)(cn={cn}*))',
                search_scope='SUBTREE',
                attributes=['*'],
                controls=[(LDAPControl.SHOW_DELETED_OBJECTS, True, None)]
            )
            
            if self.conn.entries:
                if len(self.conn.entries) > 1:
                    return {'error': 'multiple', 'count': len(self.conn.entries)}
                
                entry = self.conn.entries[0]
                return {
                    'dn': entry.entry_dn,
                    'cn': cn
                }
            
            return None
        except Exception as e:
            raise Exception(f"Error searching for deleted object: {e}")
    
    def restore_object(self, deleted_dn: str) -> Tuple[bool, str]:
        """Restore a deleted object from Recycle Bin.
        
        Args:
            deleted_dn: DN of deleted object
            
        Returns:
            Tuple of (success: bool, message: str)
        """
        try:
            result = self.conn.modify(deleted_dn, {
                'isDeleted': [(MODIFY_DELETE, [])],
                'distinguishedName': [(MODIFY_REPLACE, [deleted_dn.replace('\\0ADEL:', '')])]
            })
            
            if result:
                return True, "Successfully restored object"
            else:
                return False, "Restore failed. Use PowerShell: Restore-ADObject cmdlet for complex restores."
        except Exception as e:
            return False, f"Error restoring object: {e}. Use PowerShell Restore-ADObject cmdlet."
    
    def modify_attribute(self, dn: str, attribute: str, value: str) -> Tuple[bool, str]:
        """Modify an attribute on an AD object.
        
        Args:
            dn: Object DN
            attribute: Attribute name
            value: New value
            
        Returns:
            Tuple of (success: bool, message: str)
        """
        try:
            self.conn.modify(dn, {attribute: [(MODIFY_REPLACE, [value])]})
            if self.conn.result['result'] == 0:
                return True, f"Successfully updated {attribute}"
            else:
                return False, f"Failed to update {attribute}: {self.conn.result['message']}"
        except Exception as e:
            return False, f"Error updating {attribute}: {e}"
    
    def add_to_group(self, user_dn: str, group_dn: str) -> Tuple[bool, str]:
        """Add a user to a group.
        
        Args:
            user_dn: User Distinguished Name
            group_dn: Group Distinguished Name
            
        Returns:
            Tuple of (success: bool, message: str)
        """
        try:
            self.conn.modify(group_dn, {'member': [(MODIFY_ADD, [user_dn])]})
            if self.conn.result['result'] == 0:
                return True, "Successfully joined group"
            else:
                return False, f"Failed to join group: {self.conn.result['message']}"
        except Exception as e:
            return False, f"Error joining group: {e}"
    
    def remove_from_group(self, user_dn: str, group_dn: str) -> Tuple[bool, str]:
        """Remove a user from a group.
        
        Args:
            user_dn: User Distinguished Name
            group_dn: Group Distinguished Name
            
        Returns:
            Tuple of (success: bool, message: str)
        """
        try:
            self.conn.modify(group_dn, {'member': [(MODIFY_DELETE, [user_dn])]})
            if self.conn.result['result'] == 0:
                return True, "Successfully left group"
            else:
                return False, f"Failed to leave group: {self.conn.result['message']}"
        except Exception as e:
            return False, f"Error leaving group: {e}"
    
    def _get_object_icon(self, object_classes: List[str]) -> str:
        """Get icon for object based on object classes.
        
        Args:
            object_classes: List of objectClass values
            
        Returns:
            Icon string
        """
        if 'user' in object_classes and 'computer' not in object_classes:
            return ObjectIcon.USER.value
        elif 'computer' in object_classes:
            return ObjectIcon.COMPUTER.value
        elif 'group' in object_classes:
            return ObjectIcon.GROUP.value
        elif 'organizationalunit' in object_classes:
            return ObjectIcon.OU.value
        else:
            return ObjectIcon.GENERIC.value

    def unlock_user_account(self, user_dn: str) -> Tuple[bool, str]:
        """Unlock a locked user account.
        
        Args:
            user_dn: User Distinguished Name
            
        Returns:
            Tuple of (success: bool, message: str)
        """
        try:
            # Get current lockoutTime to check if account is actually locked
            self.conn.search(
                user_dn,
                '(objectClass=user)',
                search_scope='BASE',
                attributes=['lockoutTime', 'badPwdCount']
            )
            
            if not self.conn.entries:
                return False, "User not found"
                
            entry = self.conn.entries[0]
            
            # Check if account is actually locked
            lockout_time = 0
            if hasattr(entry, 'lockoutTime') and entry.lockoutTime.value:
                lockout_time = int(entry.lockoutTime.value)
            
            # 0 means not locked
            if lockout_time == 0:
                return False, "Account is not currently locked"
            
            # Unlock by clearing lockoutTime and resetting badPwdCount
            changes = {
                'lockoutTime': [(MODIFY_REPLACE, ['0'])],
                'badPwdCount': [(MODIFY_REPLACE, ['0'])]
            }
            
            self.conn.modify(user_dn, changes)
            
            if self.conn.result['result'] == 0:
                return True, "Successfully unlocked user account"
            else:
                return False, f"Failed to unlock account: {self.conn.result['message']}"
                
        except Exception as e:
            return False, f"Error unlocking account: {e}"
