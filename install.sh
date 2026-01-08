#!/bin/bash
# ADTUI Installer for Mac and Linux
# Usage: curl -fsSL https://raw.githubusercontent.com/brz-admin/adtui/main/install.sh | bash
#    or: curl -fsSL https://servgitea.domman.ad/ti2103/adtui/raw/branch/main/install.sh | bash

set -e

# Configuration
REPO_URL="https://github.com/brz-admin/adtui.git"
FALLBACK_REPO="https://servgitea.domman.ad/ti2103/adtui.git"
CONFIG_DIR="$HOME/.config/adtui"
CONFIG_URL="https://raw.githubusercontent.com/brz-admin/adtui/main/config.ini.example"
FALLBACK_CONFIG_URL="https://servgitea.domman.ad/ti2103/adtui/raw/branch/main/config.ini.example"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

info() { echo -e "${BLUE}[INFO]${NC} $1"; }
success() { echo -e "${GREEN}[OK]${NC} $1"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
error() { echo -e "${RED}[ERROR]${NC} $1"; exit 1; }

# Detect OS
detect_os() {
    OS="$(uname -s)"
    case "$OS" in
        Linux*)  OS_TYPE="linux" ;;
        Darwin*) OS_TYPE="mac" ;;
        *)       error "Unsupported OS: $OS" ;;
    esac
    info "Detected OS: $OS_TYPE"
}

# Check Python 3
check_python() {
    info "Checking Python..."
    
    if command -v python3 &> /dev/null; then
        PYTHON_CMD="python3"
        PYTHON_VERSION=$($PYTHON_CMD --version 2>&1 | cut -d' ' -f2)
        success "Found Python $PYTHON_VERSION"
    elif command -v python &> /dev/null; then
        PYTHON_CMD="python"
        PYTHON_VERSION=$($PYTHON_CMD --version 2>&1 | cut -d' ' -f2)
        if [[ "$PYTHON_VERSION" == 2.* ]]; then
            error "Python 3 is required. Found Python $PYTHON_VERSION"
        fi
        success "Found Python $PYTHON_VERSION"
    else
        error "Python 3 is required but not found. Please install Python 3.8 or later."
    fi
}

# Check/install pip
check_pip() {
    info "Checking pip..."
    
    if $PYTHON_CMD -m pip --version &> /dev/null; then
        success "pip is available"
        PIP_CMD="$PYTHON_CMD -m pip"
    else
        warn "pip not found, installing..."
        curl -fsSL https://bootstrap.pypa.io/get-pip.py | $PYTHON_CMD
        PIP_CMD="$PYTHON_CMD -m pip"
        success "pip installed"
    fi
}

# Install ADTUI
install_adtui() {
    info "Installing ADTUI..."
    
    # Try primary repo first
    if $PIP_CMD install --user "git+${REPO_URL}" 2>/dev/null; then
        success "ADTUI installed from primary repository"
    elif $PIP_CMD install --user "git+${FALLBACK_REPO}" 2>/dev/null; then
        success "ADTUI installed from fallback repository"
    else
        error "Failed to install ADTUI. Check your internet connection."
    fi
}

# Setup PATH
setup_path() {
    info "Checking PATH..."
    
    # Determine user bin directory
    if [[ "$OS_TYPE" == "mac" ]]; then
        USER_BIN="$HOME/Library/Python/$(echo $PYTHON_VERSION | cut -d. -f1-2)/bin"
    else
        USER_BIN="$HOME/.local/bin"
    fi
    
    # Check if adtui is accessible
    if command -v adtui &> /dev/null; then
        success "adtui is in PATH"
        return
    fi
    
    # Check if it exists in user bin
    if [[ -f "$USER_BIN/adtui" ]]; then
        warn "$USER_BIN is not in your PATH"
        
        # Detect shell
        SHELL_NAME=$(basename "$SHELL")
        case "$SHELL_NAME" in
            zsh)  SHELL_RC="$HOME/.zshrc" ;;
            bash) SHELL_RC="$HOME/.bashrc" ;;
            *)    SHELL_RC="$HOME/.profile" ;;
        esac
        
        # Add to PATH
        if ! grep -q "$USER_BIN" "$SHELL_RC" 2>/dev/null; then
            echo "" >> "$SHELL_RC"
            echo "# Added by ADTUI installer" >> "$SHELL_RC"
            echo "export PATH=\"\$PATH:$USER_BIN\"" >> "$SHELL_RC"
            success "Added $USER_BIN to PATH in $SHELL_RC"
            warn "Run 'source $SHELL_RC' or restart your terminal to apply"
        fi
        
        # Export for current session
        export PATH="$PATH:$USER_BIN"
    fi
}

# Setup configuration
setup_config() {
    info "Setting up configuration..."
    
    mkdir -p "$CONFIG_DIR"
    
    if [[ -f "$CONFIG_DIR/config.ini" ]]; then
        success "Configuration already exists at $CONFIG_DIR/config.ini"
    else
        # Download config template
        if curl -fsSL "$CONFIG_URL" -o "$CONFIG_DIR/config.ini" 2>/dev/null; then
            success "Configuration template downloaded"
        elif curl -fsSL "$FALLBACK_CONFIG_URL" -o "$CONFIG_DIR/config.ini" 2>/dev/null; then
            success "Configuration template downloaded (fallback)"
        else
            warn "Could not download config template. Create $CONFIG_DIR/config.ini manually."
        fi
    fi
}

# Print final instructions
print_instructions() {
    echo ""
    echo -e "${GREEN}╔════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║          ADTUI Installation Complete!                      ║${NC}"
    echo -e "${GREEN}╚════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo "Next steps:"
    echo ""
    echo "1. Edit the configuration file with your AD server details:"
    echo -e "   ${BLUE}nano $CONFIG_DIR/config.ini${NC}"
    echo ""
    echo "2. Configure at minimum:"
    echo "   - server = your-ad-server.domain.com"
    echo "   - base_dn = DC=domain,DC=com"
    echo ""
    echo "3. Launch ADTUI:"
    echo -e "   ${BLUE}adtui${NC}"
    echo ""
    
    if [[ -n "$SHELL_RC" ]]; then
        echo -e "${YELLOW}Note: Run 'source $SHELL_RC' first if 'adtui' command is not found.${NC}"
        echo ""
    fi
}

# Uninstall function
uninstall() {
    info "Uninstalling ADTUI..."
    $PYTHON_CMD -m pip uninstall -y adtui 2>/dev/null || true
    success "ADTUI uninstalled"
    echo "Configuration at $CONFIG_DIR was preserved."
    echo "Remove it manually if needed: rm -rf $CONFIG_DIR"
    exit 0
}

# Main
main() {
    echo ""
    echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║          ADTUI - Active Directory TUI Installer            ║${NC}"
    echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    
    # Check for uninstall flag
    if [[ "$1" == "--uninstall" ]] || [[ "$1" == "-u" ]]; then
        detect_os
        check_python
        uninstall
    fi
    
    detect_os
    check_python
    check_pip
    install_adtui
    setup_path
    setup_config
    print_instructions
}

main "$@"
