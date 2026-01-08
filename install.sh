#!/bin/bash
# ADTUI Installer for Mac and Linux
# Usage: curl -fsSL https://raw.githubusercontent.com/brz-admin/adtui/main/install.sh | bash

set -e

# Configuration
REPO_URL="https://github.com/brz-admin/adtui.git"
FALLBACK_REPO="https://servgitea.domman.ad/ti2103/adtui.git"
INSTALL_DIR="$HOME/.local/share/adtui"
BIN_DIR="$HOME/.local/bin"

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
    
    mkdir -p "$INSTALL_DIR"
    mkdir -p "$BIN_DIR"
    
    $PYTHON_CMD -m venv "$INSTALL_DIR/venv"
    
    source "$INSTALL_DIR/venv/bin/activate"
    
    info "Installing ADTUI..."
    
    pip install --upgrade pip > /dev/null 2>&1
    
    if pip install "git+${REPO_URL}" 2>/dev/null; then
        success "ADTUI installed from primary repository"
    elif pip install "git+${FALLBACK_REPO}" 2>/dev/null; then
        success "ADTUI installed from fallback repository"
    else
        deactivate
        error "Failed to install ADTUI. Check your internet connection."
    fi
    
    deactivate
    
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
    
    if [[ ":$PATH:" == *":$BIN_DIR:"* ]]; then
        success "$BIN_DIR is already in PATH"
        return
    fi
    
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
    
    if ! grep -q "$BIN_DIR" "$SHELL_RC" 2>/dev/null; then
        echo "" >> "$SHELL_RC"
        echo "# Added by ADTUI installer" >> "$SHELL_RC"
        echo "export PATH=\"\$PATH:$BIN_DIR\"" >> "$SHELL_RC"
        success "Added $BIN_DIR to PATH in $SHELL_RC"
        PATH_UPDATED=1
    else
        success "PATH already configured in $SHELL_RC"
    fi
    
    export PATH="$PATH:$BIN_DIR"
}

# Print final instructions
print_instructions() {
    echo ""
    echo -e "${GREEN}╔════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║          ADTUI Installation Complete!                      ║${NC}"
    echo -e "${GREEN}╚════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    
    if [[ -n "$PATH_UPDATED" ]]; then
        echo -e "${YELLOW}Run this command to update your PATH:${NC}"
        echo -e "   ${BLUE}source $SHELL_RC${NC}"
        echo ""
    fi
    
    echo "To start ADTUI:"
    echo -e "   ${BLUE}adtui${NC}"
    echo ""
    echo "On first run, ADTUI will guide you through the AD configuration."
    echo ""
}

# Uninstall function
uninstall() {
    info "Uninstalling ADTUI..."
    
    if [[ -d "$INSTALL_DIR" ]]; then
        rm -rf "$INSTALL_DIR"
        success "Removed $INSTALL_DIR"
    fi
    
    if [[ -f "$BIN_DIR/adtui" ]]; then
        rm -f "$BIN_DIR/adtui"
        success "Removed $BIN_DIR/adtui"
    fi
    
    success "ADTUI uninstalled"
    echo ""
    echo "Configuration at ~/.config/adtui was preserved."
    echo "Remove it manually if needed: rm -rf ~/.config/adtui"
    exit 0
}

# Update function
update() {
    info "Updating ADTUI..."
    
    if [[ ! -d "$INSTALL_DIR/venv" ]]; then
        error "ADTUI is not installed. Run the installer first."
    fi
    
    source "$INSTALL_DIR/venv/bin/activate"
    
    if pip install --upgrade "git+${REPO_URL}" 2>/dev/null; then
        success "ADTUI updated from primary repository"
    elif pip install --upgrade "git+${FALLBACK_REPO}" 2>/dev/null; then
        success "ADTUI updated from fallback repository"
    else
        deactivate
        error "Failed to update ADTUI."
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
    exit 0
}

# Main
main() {
    echo ""
    echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║          ADTUI - Active Directory TUI Installer            ║${NC}"
    echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    
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
            ;;
        *)
            error "Unknown option: $1. Use --help for usage."
            ;;
    esac
    
    detect_os
    check_python
    install_adtui
    setup_path
    print_instructions
}

main "$@"
