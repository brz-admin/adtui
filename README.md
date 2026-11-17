# ADTUI - Active Directory Terminal User Interface

A powerful Terminal User Interface (TUI) for managing Active Directory, built with Python and Textual.

**Current Version: 2.4.1**

## Features

### Core Functionality

- 🔍 **Search** - Search by CN or sAMAccountName with vim-style `/` search
- 📁 **Tree Navigation** - Browse AD organizational structure with lazy loading
- 👤 **User Management** - View and manage user details, group memberships, create/copy users, enable/disable accounts
- 👥 **Group Management** - Manage groups and their members
- 💻 **Computer Management** - View computer object details

### Advanced Features

- ✨ **Path Autocomplete** - Type any part of an OU name after `:m`, pick with ↑↓, `Tab` completes, `Enter` moves
- 🔀 **Several ADs at once** - `:connect` (or `+`) logs in to another AD (or the same one with another account); the trees stack on top of each other and every action uses the account of the tree you are working in
- 🔄 **Undo Support** - Undo recent create/move operations
- ♻️ **Recycle Bin** - View and restore deleted objects (requires AD Recycle Bin)
- ⚠️ **Expiry Alerts** - Automatic alerts for expiring passwords and accounts
- 🎯 **Vim-style Commands** - Familiar command interface

### Operations

- Create/Delete OUs
- Create/Copy user accounts
- Move objects between OUs
- Add/Remove users from groups
- Delete objects (with confirmation)
- Restore deleted objects
- Unlock user accounts
- Enable/disable user accounts

#### User Account State Management
- **Enable accounts**: `:enable` or `:en` commands
- **Disable accounts**: `:disable` or `:dis` commands  
- **Unlock accounts**: `:unlock` command (existing)
- **Status display**: Shows "Disabled: Yes/No" with color coding
- **Confirmation dialogs**: Red for disable, green for enable operations

## 🚀 Quick Install

### Linux/macOS
```bash
curl -fsSL https://raw.githubusercontent.com/brz-admin/adtui/refs/heads/main/install.sh | bash
```

### Windows (PowerShell)
```powershell
Invoke-Expression (Invoke-RestMethod https://raw.githubusercontent.com/brz-admin/adtui/refs/heads/main/install.ps1)
```

### Method 2: Python Package
```bash
pip install adtui
```

### Method 3: Download Executable (No Python Required)
```bash
# Linux/macOS
curl -L https://servgitea.domman.ad/ti2103/adtui/releases/latest/download/adtui -o adtui
chmod +x adtui
./adtui

# Windows
# Download adtui.exe from releases
```

### Method 4: Docker
```bash
docker run -it --rm adtui:latest
```

### Method 5: Web Server (Browser Access)

Run ADTUI as a web service accessible from any browser:

```bash
# Install with serve dependencies
pip install adtui[serve]

# Run the web server
textual serve --host 0.0.0.0 --port 8000 --url "http://YOUR_SERVER:8000" "python -m adtui.serve"
```

Or use Docker:

```bash
# Build the web server image
docker build -f Dockerfile.serve -t adtui-web .

# Run with your config
docker run -p 8000:8000 \
  -v /path/to/config.ini:/home/adtui/config.ini:ro \
  -e PUBLIC_URL=http://YOUR_SERVER:8000 \
  adtui-web
```

Or use docker-compose:

```bash
# Edit docker-compose.yml to set PUBLIC_URL
docker-compose up adtui-web
```

Then access via browser at `http://YOUR_SERVER:8000`

### Method 6: From Source (Development)
```bash
git clone https://github.com/brz-admin/adtui.git
cd adtui
pip install -e .
```

## Configuration

ADTUI will automatically search for configuration files in this order of priority:

1. **Environment Variable**: `ADTUI_CONFIG` (if set)
2. **User Config**: `~/.config/adtui/config.ini` (preferred)
3. **Legacy Config**: `~/.adtui_config.ini` 
4. **Current Directory**: `./config.ini` (fallback)

### Quick Setup

1. Create configuration directory:

```bash
mkdir -p ~/.config/adtui
```

2. Copy the example config:

```bash
cp config.ini.example ~/.config/adtui/config.ini
```

3. Edit `~/.config/adtui/config.ini` with your AD details:

```ini
[ldap]
server = your-dc.domain.com
domain = domain.com
base_dn = dc=domain,dc=com
use_ssl = false
```

### Alternative Setup (Current Directory)

If you prefer to keep config in the current directory:

```bash
cp config.ini.example config.ini
# Edit config.ini with your AD details
```

## Usage

### Starting the Application

```bash
adtui
```

You'll be prompted for your AD username and password (credentials are NEVER stored).

The app auto-updates on startup by default. Use `--no-auto-update` to skip this.

### Command Line Options

```bash
adtui --help              # Show help
adtui --version           # Show version
adtui --update            # Update to latest version and exit
adtui --check-update      # Check for updates without installing
adtui --no-auto-update    # Launch without auto-updating
```

### Commands

#### Search

```
/<query>          Search (vim-style)
:s <query>        Search by CN or sAMAccountName
```

#### Object Management

```
:d, :del          Delete selected object
:m <path>         Move to an OU (with autocomplete)
:move <path>      Same as :m
```

While typing a move path, matching OUs are listed under the input (the whole
domain is searched, so `:m help` finds `Departments/IT/Helpdesk`):

| Key | Action |
|-----|--------|
| `↑` / `↓` | Choose a suggestion |
| `Tab` | Complete the chosen suggestion (adds `/` to list its sub-OUs) |
| `Enter` | Move to the typed path, or to the chosen suggestion |
| `Esc` | Cancel |

#### Several ADs at once

```
:connect [domain]   Log in to another AD (also: + or :add)
:close, :cl         Disconnect the active AD only
:logout             Disconnect everything and return to login
```

Each connected AD gets its own tree, stacked one under another. `Tab` / mouse
move between them: the tree you are in is the one every command (search, move,
create, delete, undo...) is performed on, with the account you logged in with
for that AD. Selecting a tree of another AD clears the current selection, so an
object is never acted on with the wrong account.

#### OU Management

```
:mkou <path>      Create new OU
:createou <path>  Same as :mkou
```

#### User Management

```
:createuser [ou]  Create new user account (uses current OU if not specified)
:cu [ou]         Same as :createuser
:copyuser [source] [ou] Copy user account (uses current selection if not specified)
:copygroups <user> Add selected user to all groups of <user> (name or DN)
:cpg <user>      Same as :copygroups
:unlock           Unlock currently selected locked user account
:enable          Enable currently selected disabled user account
:en              Same as :enable
:disable         Disable currently selected enabled user account
:dis             Same as :disable
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
- `a` - Edit attributes of selected object
- `g` - Manage groups for selected user
- `p` - Set password for selected user
- `c` - Create new user account
- `C` - Copy selected user account
- `Esc` - Quit application

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

**Create a user:**

```
:createuser
:cu IT/Staff
```

**Copy a user:**

```
:C
:copyuser "CN=John Doe,OU=Users,DC=example,DC=com" IT/Staff
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
- `prompt_toolkit>=3.0.0` - Enhanced input handling

## Features by AD Object Type

### Users (👤)

- General info (name, email, profile path, etc.)
- Account status (disabled, locked, expiry)
- Password status and expiry warnings
- Group memberships
- Join/leave groups
- Create new user accounts
- Copy existing user accounts
- Set/change passwords
- Unlock locked accounts

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

### Version 2.4.1 (Current)
- ✨ New: Web server support via `textual serve` for browser-based access
- ✨ New: Auto-update on startup (disable with `--no-auto-update`)
- ✨ New: `--update` flag to update without launching the app
- ✨ New: Show built-in containers (Users, Computers, Builtin) in tree
- ✨ New: Dockerfile.serve and docker-compose web service
- 🔧 Fixed: Password expiry calculation for datetime objects
- 🔧 Fixed: 'y' key now copies selected text instead of always copying DN

### Version 2.0.0

- 🎉 Complete refactoring with clean architecture
- ✨ New: Path autocomplete for move operations
- ✨ New: Account and password expiry alerts
- ✨ New: Undo support for operations
- ✨ New: AD Recycle Bin integration
- ✨ New: Comprehensive user account creation and copy functionality
- 🔧 Improved: Separation of concerns (services layer)
- 🔧 Improved: Command handler pattern
- 🔧 Improved: Type hints throughout
- 🔒 Fixed: Removed hardcoded credentials
- 🔧 Improved: Error handling and user feedback

### Version 2.1.0
- ✨ New: Complete user account state management (enable/disable)
- 🎯 Added: `:disable` and `:dis` commands to disable enabled user accounts
- 🎯 Added: `ConfirmDisableDialog` with red styling and warning messages
- 🎯 Added: UAC flag manipulation for account disabling
- 🎯 Added: Complete symmetry between enable/disable operations
- 🔧 Fixed: Removed conflicting keyboard shortcuts in help text
- 🔧 Improved: Complete user management workflow with proper validation

- Initial release
- Basic AD browsing and search
- User/Group/Computer details
- Move and delete operations

## 🔧 Troubleshooting

### Installation Issues

**Error: `/usr/bin/python3: No module named pip`**
```bash
# Install pip first, then run installer
curl -fsSL https://bootstrap.pypa.io/get-pip.py | python3
./install.sh
```

**Curl 404 errors with git.brznet.fr**
```bash
# Use alternative servgitea URL
curl -fsSL https://servgitea.domman.ad/ti2103/adtui/raw/branch/main/install.sh | sh
```

**PATH not found after installation**
```bash
# Add to ~/.bashrc or ~/.zshrc
export PATH="$PATH:$HOME/.local/bin"
source ~/.bashrc  # or source ~/.zshrc
```

### Configuration Issues

**Credentials not accepted**
- Verify AD server and domain in config.ini
- Ensure user account has necessary permissions
- Check network connectivity to domain controller

**SSL connection issues**
- Set `use_ssl = true` in config.ini
- Verify SSL certificates on domain controller
- Test with `openssl s_client -connect dc.domain.com:636`

## Support

For issues, questions, or contributions:

- Issues: https://github.com/brz-admin/adtui/issues

## Credits

Built with:

- [Textual](https://github.com/Textualize/textual) - Amazing TUI framework
- [ldap3](https://github.com/cannatag/ldap3) - Pure Python LDAP client
