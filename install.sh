#!/bin/bash
# ADTUI Installer for Mac and Linux
# Usage: curl -fsSL https://raw.githubusercontent.com/brz-admin/adtui/main/install.sh | bash
#    or: curl -fsSL https://servgitea.domman.ad/ti2103/adtui/raw/branch/main/install.sh | bash

set -e

# Configuration
REPO_URL="https://github.com/brz-admin/adtui.git"
FALLBACK_REPO="https://servgitea.domman.ad/ti2103/adtui.git"
INSTALL_DIR="$HOME/.local/share/adtui"
BIN_DIR="$HOME/.local/bin"
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

# Create virtual environment and install ADTUI
install_adtui() {
    info "Creating virtual environment in $INSTALL_DIR..."
    
    # Create installation directory
    mkdir -p "$INSTALL_DIR"
    mkdir -p "$BIN_DIR"
    
    # Create virtual environment
    $PYTHON_CMD -m venv "$INSTALL_DIR/venv"
    
    # Activate and install
    source "$INSTALL_DIR/venv/bin/activate"
    
    info "Installing ADTUI..."
    
    # Upgrade pip first
    pip install --upgrade pip > /dev/null 2>&1
    
    # Try primary repo first
    if pip install "git+${REPO_URL}" 2>/dev/null; then
        success "ADTUI installed from primary repository"
    elif pip install "git+${FALLBACK_REPO}" 2>/dev/null; then
        success "ADTUI installed from fallback repository"
    else
        deactivate
        error "Failed to install ADTUI. Check your internet connection."
    fi
    
    deactivate
    
    # Create wrapper script in ~/.local/bin
    info "Creating adtui command..."
    cat > "$BIN_DIR/adtui" << 'EOF'
#!/bin/bash
source "$HOME/.local/share/adtui/venv/bin/activate"
python -m adtui "$@"
deactivate
EOF
    chmod +x "$BIN_DIR/adtui"
    
    success "ADTUI installed successfully"
}

# Setup PATH
setup_path() {
    info "Checking PATH..."
    
    # Check if BIN_DIR is in PATH
    if [[ ":$PATH:" == *":$BIN_DIR:"* ]]; then
        success "$BIN_DIR is already in PATH"
        return
    fi
    
    # Detect shell config file
    SHELL_NAME=$(basename "$SHELL")
    case "$SHELL_NAME" in
        zsh)  SHELL_RC="$HOME/.zshrc" ;;
        bash) 
            if [[ -f "$HOME/.bash_profile" ]]; then
                SHELL_RC="$HOME/.bash_profile"
            else
                SHELL_RC="$HOME/.bashrc"
            fi
            ;;
        *)    SHELL_RC="$HOME/.profile" ;;
    esac
    
    # Add to PATH if not already there
    if ! grep -q "$BIN_DIR" "$SHELL_RC" 2>/dev/null; then
        echo "" >> "$SHELL_RC"
        echo "# Added by ADTUI installer" >> "$SHELL_RC"
        echo "export PATH=\"\$PATH:$BIN_DIR\"" >> "$SHELL_RC"
        success "Added $BIN_DIR to PATH in $SHELL_RC"
        PATH_UPDATED=1
    else
        success "PATH already configured in $SHELL_RC"
    fi
    
    # Export for current session
    export PATH="$PATH:$BIN_DIR"
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
    
    if [[ -n "$PATH_UPDATED" ]]; then
        echo -e "${YELLOW}IMPORTANT: Run this command to update your PATH:${NC}"
        echo -e "   ${BLUE}source $SHELL_RC${NC}"
        echo ""
    fi
    
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
}

# Uninstall function
uninstall() {
    info "Uninstalling ADTUI..."
    
    # Remove virtual environment
    if [[ -d "$INSTALL_DIR" ]]; then
        rm -rf "$INSTALL_DIR"
        success "Removed $INSTALL_DIR"
    fi
    
    # Remove wrapper script
    if [[ -f "$BIN_DIR/adtui" ]]; then
        rm -f "$BIN_DIR/adtui"
        success "Removed $BIN_DIR/adtui"
    fi
    
    success "ADTUI uninstalled"
    echo ""
    echo "Configuration at $CONFIG_DIR was preserved."
    echo "Remove it manually if needed: rm -rf $CONFIG_DIR"
    exit 0
}

# Update function
update() {
    info "Updating ADTUI..."
    
    if [[ ! -d "$INSTALL_DIR/venv" ]]; then
        error "ADTUI is not installed. Run the installer without --update first."
    fi
    
    source "$INSTALL_DIR/venv/bin/activate"
    
    # Try primary repo first
    if pip install --upgrade "git+${REPO_URL}" 2>/dev/null; then
        success "ADTUI updated from primary repository"
    elif pip install --upgrade "git+${FALLBACK_REPO}" 2>/dev/null; then
        success "ADTUI updated from fallback repository"
    else
        deactivate
        error "Failed to update ADTUI. Check your internet connection."
    fi
    
    deactivate
    success "ADTUI updated successfully"
    exit 0
}

# Show help
show_help() {
    echo "ADTUI Installer"
    echo ""
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  --uninstall, -u    Remove ADTUI"
    echo "  --update           Update ADTUI to latest version"
    echo "  --help, -h         Show this help"
    echo ""
    echo "Examples:"
    echo "  Install:   curl -fsSL <url>/install.sh | bash"
    echo "  Update:    ~/.local/share/adtui/install.sh --update"
    echo "  Uninstall: ~/.local/share/adtui/install.sh --uninstall"
    exit 0
}

# Main
main() {
    echo ""
    echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║          ADTUI - Active Directory TUI Installer            ║${NC}"
    echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    
    # Parse arguments
    case "$1" in
        --uninstall|-u)
            detect_os
            uninstall
            ;;
        --update)
            detect_os
            check_python
            update
            ;;
        --help|-h)
            show_help
            ;;
        "")
            # Normal install
            ;;
        *)
            error "Unknown option: $1. Use --help for usage."
            ;;
    esac
    
    detect_os
    check_python
    install_adtui
    setup_path
    setup_config
    print_instructions
}

main "$@"
