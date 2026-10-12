# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.5.5] - 2026-10-12

### 🐛 Fixed
- PageUp/PageDown in list panes (search results, groups, members, attributes,
  domains) now move the selection instead of only scrolling the viewport, so
  arrow keys no longer snap the view back to the previously selected item

## [2.5.4] - 2026-10-12

### ✨ Features
- Display the user logon name (userPrincipalName / UPN) in the user details pane
- Edit the logon name (UPN) with a dedicated dialog mirroring the ADUC "Account" tab:
  logon name field plus a @suffix selector loaded from the domain (default domain
  and forest UPN suffixes)
- New `l` shortcut and `:l, :upn` command to edit the UPN of the selected user
- Duplicate UPN check before saving (AD rejects duplicates forest-wide)

## [2.1.0] - 2024-12-16

### 🎉 Packaging & Distribution
- Complete packaging refactor for PyPI distribution
- Universal one-liner installer script
- Standalone executable support (Linux/macOS)
- Docker container support with docker-compose
- Automated CI/CD pipeline with releases
- Multi-platform build infrastructure
- Support for both Gitea and remote repositories

### ✨ Features
- Complete user account state management (enable/disable)
- Path autocomplete for move operations
- Account and password expiry alerts
- Undo support for recent operations
- AD Recycle Bin integration

### 🔧 Technical Improvements
- Modern packaging with pyproject.toml (removed setup.py)
- Clean service layer architecture
- Improved error handling and user feedback
- Removed hardcoded credentials
- Enhanced security and configuration management
- Proper package entry points and module imports
- Fixed package structure for proper distribution

### 🚀 Installation Methods
- Universal one-liner: `curl -fsSL https://git.brznet.fr/brz/adtui/raw/branch/main/install.sh | sh`
- Python package: `pip install adtui`
- Binary executable: Download from releases
- Docker: `docker run -it --rm adtui:latest`
- Source: `pip install git+https://git.brznet.fr/brz/adtui.git`

## [2.0.0] - Previous Version

### ✨ Major Features
- Complete refactored architecture
- Service layer for clean separation of concerns
- Command handler pattern
- Path autocomplete for move operations
- Account and password expiry alerts
- Undo support for operations
- AD Recycle Bin integration

### 🔧 Improvements
- Separation of concerns (services layer)
- Command handler pattern
- Type hints throughout
- Fixed: Removed hardcoded credentials
- Improved error handling and user feedback

### 📦 Features
- Search by CN or sAMAccountName with vim-style interface
- Browse AD organizational structure with lazy loading
- Create/copy user accounts with smart defaults
- Manage user details, group memberships, and passwords
- Create/delete OUs and move objects
- Undo support for recent operations
- AD Recycle Bin integration
- Account and password expiry alerts

## [1.0.0] - Initial Release

### 🎯 Core Features
- Basic AD browsing and search
- User/Group/Computer details
- Move and delete operations
- Vim-style commands interface