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
CONFIG_FILE="$CONFIG_DIR/config.ini"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

info() { echo -e "${BLUE}[INFO]${NC} $1"; }
success() { echo -e "${GREEN}[OK]${NC} $1"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
error() { echo -e "${RED}[ERROR]${NC} $1"; exit 1; }
prompt() { echo -en "${CYAN}$1${NC}"; }

# Read from terminal even when piped
read_input() {
    read "$@" </dev/tty
}

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

# Interactive AD Setup Wizard
setup_wizard() {
    echo ""
    echo -e "${BOLD}${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BOLD}${BLUE}║          Active Directory Configuration Wizard             ║${NC}"
    echo -e "${BOLD}${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    
    # Check if config already exists
    if [[ -f "$CONFIG_FILE" ]]; then
        echo -e "${YELLOW}Configuration file already exists at:${NC}"
        echo "  $CONFIG_FILE"
        echo ""
        prompt "Do you want to reconfigure? [y/N]: "
        read_input -r RECONFIGURE
        if [[ ! "$RECONFIGURE" =~ ^[Yy]$ ]]; then
            success "Keeping existing configuration"
            return
        fi
        # Backup existing config
        cp "$CONFIG_FILE" "$CONFIG_FILE.backup.$(date +%Y%m%d_%H%M%S)"
        info "Existing config backed up"
    fi
    
    mkdir -p "$CONFIG_DIR"
    
    # Initialize config file
    echo "# ADTUI Configuration" > "$CONFIG_FILE"
    echo "# Generated by setup wizard" >> "$CONFIG_FILE"
    echo "" >> "$CONFIG_FILE"
    echo "[ad_domains]" >> "$CONFIG_FILE"
    
    DOMAINS=""
    AD_COUNT=0
    
    while true; do
        ((AD_COUNT++))
        echo ""
        echo -e "${BOLD}--- Active Directory #$AD_COUNT ---${NC}"
        echo ""
        
        # Domain name (short name like CORP, DOMMAN)
        prompt "Domain short name (e.g., CORP, DOMMAN): "
        read_input -r DOMAIN_NAME
        DOMAIN_NAME=$(echo "$DOMAIN_NAME" | tr '[:lower:]' '[:upper:]')
        
        if [[ -z "$DOMAIN_NAME" ]]; then
            warn "Domain name cannot be empty"
            ((AD_COUNT--))
            continue
        fi
        
        # Server
        prompt "AD Server hostname (e.g., dc1.domain.com): "
        read_input -r AD_SERVER
        
        if [[ -z "$AD_SERVER" ]]; then
            warn "Server cannot be empty"
            ((AD_COUNT--))
            continue
        fi
        
        # Base DN - try to auto-detect from server name
        DEFAULT_BASE_DN=""
        if [[ "$AD_SERVER" == *.* ]]; then
            # Extract domain parts from server name
            DOMAIN_PARTS=$(echo "$AD_SERVER" | sed 's/^[^.]*\.//' | tr '.' '\n')
            for PART in $DOMAIN_PARTS; do
                if [[ -n "$DEFAULT_BASE_DN" ]]; then
                    DEFAULT_BASE_DN="$DEFAULT_BASE_DN,"
                fi
                DEFAULT_BASE_DN="${DEFAULT_BASE_DN}DC=$PART"
            done
        fi
        
        if [[ -n "$DEFAULT_BASE_DN" ]]; then
            prompt "Base DN [$DEFAULT_BASE_DN]: "
        else
            prompt "Base DN (e.g., DC=domain,DC=com): "
        fi
        read_input -r BASE_DN
        
        if [[ -z "$BASE_DN" ]]; then
            BASE_DN="$DEFAULT_BASE_DN"
        fi
        
        if [[ -z "$BASE_DN" ]]; then
            warn "Base DN cannot be empty"
            ((AD_COUNT--))
            continue
        fi
        
        # SSL
        prompt "Use SSL/TLS? [y/N]: "
        read_input -r USE_SSL
        if [[ "$USE_SSL" =~ ^[Yy]$ ]]; then
            USE_SSL="true"
        else
            USE_SSL="false"
        fi
        
        # Add to domains list
        if [[ -n "$DOMAINS" ]]; then
            DOMAINS="$DOMAINS, $DOMAIN_NAME"
        else
            DOMAINS="$DOMAIN_NAME"
        fi
        
        # Write AD section to config
        {
            echo ""
            echo "[ad_$DOMAIN_NAME]"
            echo "server = $AD_SERVER"
            echo "domain = $DOMAIN_NAME"
            echo "base_dn = $BASE_DN"
            echo "use_ssl = $USE_SSL"
            echo "max_retries = 5"
            echo "initial_retry_delay = 1.0"
            echo "max_retry_delay = 60.0"
            echo "health_check_interval = 30.0"
        } >> "$CONFIG_FILE"
        
        success "Added $DOMAIN_NAME configuration"
        
        # Ask for another AD
        echo ""
        prompt "Add another Active Directory? [y/N]: "
        read_input -r ADD_ANOTHER
        if [[ ! "$ADD_ANOTHER" =~ ^[Yy]$ ]]; then
            break
        fi
    done
    
    # Update domains list in config
    sed -i.tmp "s/\[ad_domains\]/[ad_domains]\ndomains = $DOMAINS/" "$CONFIG_FILE"
    rm -f "$CONFIG_FILE.tmp"
    
    # Also add legacy [ldap] section for first domain (backward compatibility)
    FIRST_DOMAIN=$(echo "$DOMAINS" | cut -d',' -f1 | tr -d ' ')
    
    # Extract first domain settings
    FIRST_SERVER=$(grep -A5 "\[ad_$FIRST_DOMAIN\]" "$CONFIG_FILE" | grep "server" | cut -d'=' -f2 | tr -d ' ')
    FIRST_BASE_DN=$(grep -A5 "\[ad_$FIRST_DOMAIN\]" "$CONFIG_FILE" | grep "base_dn" | cut -d'=' -f2 | tr -d ' ')
    FIRST_SSL=$(grep -A5 "\[ad_$FIRST_DOMAIN\]" "$CONFIG_FILE" | grep "use_ssl" | cut -d'=' -f2 | tr -d ' ')
    
    {
        echo ""
        echo "# Legacy single AD support (for backward compatibility)"
        echo "[ldap]"
        echo "server = $FIRST_SERVER"
        echo "domain = $FIRST_DOMAIN"
        echo "base_dn = $FIRST_BASE_DN"
        echo "use_ssl = $FIRST_SSL"
        echo "max_retries = 5"
        echo "initial_retry_delay = 1.0"
        echo "max_retry_delay = 60.0"
        echo "health_check_interval = 30.0"
    } >> "$CONFIG_FILE"
    
    echo ""
    success "Configuration saved to $CONFIG_FILE"
    
    if [[ $AD_COUNT -gt 1 ]]; then
        info "Configured $AD_COUNT Active Directory domains: $DOMAINS"
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
    
    echo "Your configuration is saved at:"
    echo -e "   ${BLUE}$CONFIG_FILE${NC}"
    echo ""
    echo "To edit your configuration later:"
    echo -e "   ${BLUE}nano $CONFIG_FILE${NC}"
    echo ""
    echo "To launch ADTUI:"
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

# Reconfigure function
reconfigure() {
    setup_wizard
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
    echo "  --reconfigure      Run the AD configuration wizard again"
    echo "  --help, -h         Show this help"
    echo ""
    echo "Examples:"
    echo "  Install:     curl -fsSL <url>/install.sh | bash"
    echo "  Update:      $0 --update"
    echo "  Reconfigure: $0 --reconfigure"
    echo "  Uninstall:   $0 --uninstall"
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
        --reconfigure)
            setup_wizard
            exit 0
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
    setup_wizard
    print_instructions
}

main "$@"
