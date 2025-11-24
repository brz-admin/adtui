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
        # Extract domain from base_dn for UPN generation
        self.domain = base_dn.replace('DC=', '').replace(',', '.')
    
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

    def check_samaccount_availability(self, samaccount: str, base_dn: str = "") -> Tuple[bool, str]:
        """Check if sAMAccountName is available.
        
        Args:
            samaccount: The sAMAccountName to check
            base_dn: Base DN to search in (optional)
            
        Returns:
            Tuple of (available: bool, message: str)
        """
        try:
            search_base = base_dn if base_dn else self.base_dn
            self.conn.search(
                search_base,
                f'(sAMAccountName={samaccount})',
                search_scope='SUBTREE',
                attributes=['sAMAccountName', 'distinguishedName']
            )
            
            if self.conn.entries:
                existing_dn = self.conn.entries[0].distinguishedName.value
                return False, f"sAMAccountName '{samaccount}' already exists: {existing_dn}"
            
            return True, "sAMAccountName is available"
            
        except Exception as e:
            return False, f"Error checking sAMAccountName availability: {e}"

    def generate_samaccount_name(self, full_name: str, base_dn: str = "") -> str:
        """Generate a unique sAMAccountName from full name.
        
        Args:
            full_name: Full name of the user
            base_dn: Base DN to check uniqueness in
            
        Returns:
            Unique sAMAccountName
        """
        import re
        
        # Split full name into parts
        name_parts = full_name.strip().split()
        if len(name_parts) == 0:
            return "user"
        
        # Generate base sAMAccountName
        if len(name_parts) == 1:
            base_sam = name_parts[0].lower()
        elif len(name_parts) == 2:
            first, last = name_parts
            base_sam = f"{first[0].lower()}{last.lower()}"
        else:
            first, last = name_parts[0], name_parts[-1]
            base_sam = f"{first[0].lower()}{last.lower()}"
        
        # Clean up special characters
        base_sam = re.sub(r'[^a-zA-Z0-9]', '', base_sam)
        
        # Check availability and add number if needed
        samaccount = base_sam
        counter = 1
        while True:
            available, _ = self.check_samaccount_availability(samaccount, base_dn if base_dn else "")
            if available:
                break
            samaccount = f"{base_sam}{counter}"
            counter += 1
            
        return samaccount

    def create_user(self, full_name: str, samaccount: str, password: str, ou_dn: str,
                   first_name: str = "", last_name: str = "", 
                   user_must_change_password: bool = True,
                   user_cannot_change_password: bool = False,
                   password_never_expires: bool = False,
                   account_disabled: bool = False,
                   account_expires: str = "") -> Tuple[bool, str, str]:
        """Create a new user account.
        
        Args:
            full_name: Full name (CN)
            samaccount: sAMAccountName
            password: Initial password
            ou_dn: Target OU DN
            first_name: Given name (optional)
            last_name: Surname (optional)
            user_must_change_password: User must change password at next logon
            user_cannot_change_password: User cannot change password
            password_never_expires: Password never expires
            account_disabled: Account is disabled
            account_expires: Account expiry date (optional)
            
        Returns:
            Tuple of (success: bool, message: str, user_dn: str)
        """
        try:
            # Validate required fields
            if not full_name.strip():
                return False, "Full name is required", ""
            if not samaccount.strip():
                return False, "User logon name is required", ""
            if not password.strip():
                return False, "Password is required", ""
            
            # Check sAMAccountName availability
            available, message = self.check_samaccount_availability(samaccount)
            if not available:
                return False, message, ""
            
            # Generate user DN
            user_dn = f"cn={full_name},{ou_dn}"
            
            # Calculate userAccountControl flags
            uac = 0x200  # NORMAL_ACCOUNT
            if account_disabled:
                uac |= 0x2  # ACCOUNTDISABLE
            if user_cannot_change_password:
                uac |= 0x40  # PASSWD_CANT_CHANGE
            if password_never_expires:
                uac |= 0x10000  # DONT_EXPIRE_PASSWORD
            if user_must_change_password:
                uac |= 0x200  # NORMAL_ACCOUNT (already set)
            
            # Prepare attributes
            attributes = {
                'objectClass': ['top', 'person', 'organizationalPerson', 'user'],
                'cn': full_name,
                'sAMAccountName': samaccount,
                'userAccountControl': str(uac),
                'unicodePwd': f'"{password}"'.encode('utf-16-le'),
                'userPrincipalName': f"{samaccount}@{self.domain}"
            }
            
            # Add optional attributes
            if first_name:
                attributes['givenName'] = first_name
            if last_name:
                attributes['sn'] = last_name
            
            # Handle account expiry
            if account_expires and account_expires.strip():
                try:
                    # Convert date to Windows FILETIME
                    expiry_date = datetime.strptime(account_expires, '%Y-%m-%d')
                    # Convert to FILETIME (100-nanosecond intervals since 1601-01-01)
                    filetime = (expiry_date - datetime(1601, 1, 1)).total_seconds() * 10000000
                    attributes['accountExpires'] = str(int(filetime))
                except ValueError:
                    return False, "Invalid account expiry date format. Use YYYY-MM-DD", ""
            
            # Create the user
            result = self.conn.add(user_dn, attributes=attributes)
            
            if not result:
                error_msg = self.conn.result.get('message', 'Unknown error')
                return False, f"Failed to create user: {error_msg}", ""
            
            # If user must change password at next logon, set pwdLastSet to 0
            if user_must_change_password:
                self.conn.modify(user_dn, {'pwdLastSet': [(MODIFY_REPLACE, ['0'])]})
            
            return True, f"Successfully created user: {full_name}", user_dn
            
        except Exception as e:
            return False, f"Error creating user: {e}", ""

    def copy_user(self, source_dn: str, new_full_name: str, new_samaccount: str, 
                 password: str, target_ou_dn: str, copy_groups: bool = False,
                 copy_manager: bool = False, copy_account_options: bool = False) -> Tuple[bool, str, str]:
        """Copy an existing user account.
        
        Args:
            source_dn: Source user DN
            new_full_name: New user's full name
            new_samaccount: New user's sAMAccountName
            password: New user's password
            target_ou_dn: Target OU DN
            copy_groups: Copy group memberships
            copy_manager: Copy manager relationship
            copy_account_options: Copy account options
            
        Returns:
            Tuple of (success: bool, message: str, new_user_dn: str)
        """
        try:
            # Get source user information
            self.conn.search(source_dn, '(objectClass=user)', search_scope='BASE',
                          attributes=['givenName', 'sn', 'description', 'department', 
                                   'company', 'title', 'manager', 'userAccountControl'])
            
            if not self.conn.entries:
                return False, "Source user not found", ""
            
            source_entry = self.conn.entries[0]
            
            # Extract source attributes
            first_name = str(source_entry.givenName.value) if hasattr(source_entry, 'givenName') else ""
            last_name = str(source_entry.sn.value) if hasattr(source_entry, 'sn') else ""
            
            # Determine account options from source if requested
            user_must_change_password = True  # Default for new users
            user_cannot_change_password = False
            password_never_expires = False
            account_disabled = False
            
            if copy_account_options and hasattr(source_entry, 'userAccountControl'):
                source_uac = int(source_entry.userAccountControl.value)
                user_cannot_change_password = (source_uac & 0x40) != 0
                password_never_expires = (source_uac & 0x10000) != 0
                account_disabled = (source_uac & 0x2) != 0
            
            # Create the new user
            success, message, new_user_dn = self.create_user(
                new_full_name, new_samaccount, password, target_ou_dn,
                first_name, last_name, user_must_change_password,
                user_cannot_change_password, password_never_expires, account_disabled
            )
            
            if not success:
                return False, message, ""
            
            # Copy group memberships if requested
            if copy_groups:
                try:
                    # Get source user's groups
                    self.conn.search(source_dn, '(objectClass=user)', search_scope='BASE',
                                  attributes=['memberOf'])
                    
                    if hasattr(source_entry, 'memberOf'):
                        groups_to_add = []
                        for group_dn in source_entry.memberOf.values:
                            # Try to add user to each group
                            try:
                                result = self.conn.modify(group_dn, {'member': [(MODIFY_ADD, [new_user_dn])]})
                                if result:
                                    groups_to_add.append(group_dn)
                            except:
                                continue  # Skip groups we can't add to
                        
                        if groups_to_add:
                            message += f" Copied to {len(groups_to_add)} groups."
                
                except Exception as e:
                    message += f" Warning: Could not copy group memberships: {e}"
            
            # Copy manager if requested
            if copy_manager and hasattr(source_entry, 'manager'):
                try:
                    manager_dn = str(source_entry.manager.value)
                    self.conn.modify(new_user_dn, {'manager': [(MODIFY_REPLACE, [manager_dn])]})
                    message += " Manager copied."
                except Exception as e:
                    message += f" Warning: Could not copy manager: {e}"
            
            return True, message, new_user_dn
            
        except Exception as e:
            return False, f"Error copying user: {e}", ""
