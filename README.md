# ADTUI - Active Directory Terminal User Interface

A powerful Terminal User Interface (TUI) for managing Active Directory, built with Python and Textual.

## Features

### Core Functionality

- 🔍 **Search** - Search by CN or sAMAccountName with vim-style `/` search
- 📁 **Tree Navigation** - Browse AD organizational structure with lazy loading
- 👤 **User Management** - View and manage user details, group memberships
- 👥 **Group Management** - Manage groups and their members
- 💻 **Computer Management** - View computer object details

### Advanced Features

- ✨ **Path Autocomplete** - Intelligent OU path completion for move operations
- 🔄 **Undo Support** - Undo recent create/move operations
- ♻️ **Recycle Bin** - View and restore deleted objects (requires AD Recycle Bin)
- ⚠️ **Expiry Alerts** - Automatic alerts for expiring passwords and accounts
- 🎯 **Vim-style Commands** - Familiar command interface

### Operations

- Create/Delete OUs
- Move objects between OUs
- Add/Remove users from groups
- Delete objects (with confirmation)
- Restore deleted objects

## Installation

### From Source

```bash
# Clone the repository
git clone git@servgitea.domman.ad:ti2103/adtui.git
cd adtui

# Install dependencies
pip install -r requirements.txt

# Install the package
pip install -e .
```

## Configuration

1. Copy the example config:

```bash
cp config.ini.example config.ini
```

2. Edit `config.ini` with your AD details:

```ini
[ldap]
server = your-dc.domain.com
domain = domain.com
base_dn = dc=domain,dc=com
use_ssl = false
```

## Usage

### Starting the Application

```bash
adtui
```

You'll be prompted for your AD username and password (credentials are NEVER stored).

### Commands

#### Search

```
/<query>          Search (vim-style)
:s <query>        Search by CN or sAMAccountName
```

#### Object Management

```
:d, :del          Delete selected object
:m <path>         Move to path (with autocomplete)
:move <path>      Same as :m
```

#### OU Management

```
:mkou <path>      Create new OU
:createou <path>  Same as :mkou
```

#### Recovery & History

```
:recycle, :rb     Show AD Recycle Bin
:restore <name>   Restore deleted object
:undo, :u         Undo last operation
```

#### Other

```
:help             Show help
```

### Keyboard Shortcuts

- `/` - Open search (vim-style)
- `:` - Enter command mode
- `r` - Refresh current OU
- `Esc` - Quit application

### Examples

**Search for a user:**

```
/john.doe
```

**Move a user:**

```
:m Users/IT/Developers
```

**Create an OU:**

```
:mkou Departments/Sales/Region1
```

**View deleted objects:**

```
:recycle
```

**Restore a deleted object:**

```
:restore john.doe
```

## Requirements

- Python 3.8+
- Access to Active Directory (read/write permissions as needed)
- Network connectivity to AD Domain Controller
- For Recycle Bin features: AD Recycle Bin must be enabled on the domain

### Python Dependencies

- `ldap3>=2.9.1` - LDAP operations
- `textual>=0.40.0` - Terminal UI framework

## Features by AD Object Type

### Users (👤)

- General info (name, email, profile path, etc.)
- Account status (disabled, locked, expiry)
- Password status and expiry warnings
- Group memberships
- Join/leave groups

### Groups (👥)

- Members list (name only)
- Member Of list
- Add/remove members
- Join/leave parent groups

### Computers (💻)

- Computer name
- Operating system
- DNS hostname

## Architecture

The application is built with a clean, modular architecture:

```
adtui/
├── adtui.py              # Main application
├── services/             # Business logic layer
│   ├── ldap_service.py   # All LDAP operations
│   ├── history_service.py # Undo/redo tracking
│   └── path_service.py   # DN/path conversions
├── commands/             # Command handling
│   └── command_handler.py # Command parsing & execution
├── ui/                   # UI components
│   └── dialogs.py        # Modal dialogs
├── widgets/              # Custom widgets
│   ├── details_pane.py   # Details routing
│   ├── user_details.py   # User view
│   └── group_details.py  # Group view
├── constants.py          # Constants & enums
├── adtree.py            # AD tree widget
└── styles.tcss          # UI styling
```

## Development

### Running from Source

```bash
python adtui.py
```

### Running Tests

```bash
pytest tests/
```

### Code Quality

```bash
# Type checking
mypy adtui/

# Linting
pylint adtui/

# Formatting
black adtui/
```

## Security Notes

- ⚠️ **Credentials**: Never hardcoded, always prompted securely
- ⚠️ **SSL**: Enable `use_ssl = true` in config for production
- ⚠️ **Permissions**: Requires appropriate AD permissions for operations
- ⚠️ **Audit**: All operations are tracked in AD audit logs

## Troubleshooting

### Connection Issues

- Verify DC hostname and network connectivity
- Check firewall rules (LDAP: 389, LDAPS: 636)
- Ensure correct domain name and base DN

### Permission Denied

- Verify your AD account has necessary permissions
- Some operations require elevated privileges

### Recycle Bin Not Working

- AD Recycle Bin must be enabled on the domain
- Requires appropriate permissions to view deleted objects

### To Enable AD Recycle Bin (Domain Admin)

```powershell
Enable-ADOptionalFeature -Identity 'Recycle Bin Feature' `
  -Scope ForestOrConfigurationSet `
  -Target 'yourdomain.com'
```

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add/update tests
5. Submit a pull request

## License

MIT License - see LICENSE file for details

## Changelog

### Version 2.0.0 (Current)

- 🎉 Complete refactoring with clean architecture
- ✨ New: Path autocomplete for move operations
- ✨ New: Account and password expiry alerts
- ✨ New: Undo support for operations
- ✨ New: AD Recycle Bin integration
- 🔧 Improved: Separation of concerns (services layer)
- 🔧 Improved: Command handler pattern
- 🔧 Improved: Type hints throughout
- 🔒 Fixed: Removed hardcoded credentials

### Version 1.0.0

- Initial release
- Basic AD browsing and search
- User/Group/Computer details
- Move and delete operations

## Support

For issues, questions, or contributions:

- Issues: https://servgitea.domman.ad/ti2103/adtui/issues

## Credits

Built with:

- [Textual](https://github.com/Textualize/textual) - Amazing TUI framework
- [ldap3](https://github.com/cannatag/ldap3) - Pure Python LDAP client
