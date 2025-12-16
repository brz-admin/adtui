#!/bin/bash
# ADTUI Universal Installer
# Usage: curl -fsSL https://raw.githubusercontent.com/brz-admin/adtui/main/install.sh | sh

set -e

# Configuration
INSTALL_METHOD="auto"
INSTALL_DIR="$HOME/.local/bin"
PRIMARY_REPO="https://github.com/brz-admin/adtui"
FALLBACK_REPO="https://servgitea.domman.ad/ti2103/adtui"
THIRD_REPO="https://git.brznet.fr/Brz/adtui"
REPO_URL="$PRIMARY_REPO"
VERSION="latest"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --method)
            INSTALL_METHOD="$2"
            shift 2
            ;;
        --dir)
            INSTALL_DIR="$2"
            shift 2
            ;;
        --version)
            VERSION="$2"
            shift 2
            ;;
        -h|--help)
            echo "ADTUI Installer"
            echo ""
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --method METHOD  Installation method (auto|pip|binary|source)"
            echo "  --dir DIR        Installation directory (default: ~/.local/bin)"
            echo "  --version VER    Version to install (default: latest)"
            echo "  -h, --help       Show this help"
            exit 0
            ;;
        *)
            log_error "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Check system requirements
check_requirements() {
    log_info "Checking system requirements..."
    
    # Check OS
    OS=$(uname -s)
    ARCH=$(uname -m)
    log_info "Detected: $OS $ARCH"
    
    # Check if adtui is in PATH and INSTALL_DIR is needed
    if ! command -v adtui &> /dev/null; then
        log_info "Installing to system directory: $INSTALL_DIR"
        mkdir -p "$INSTALL_DIR"
        
        # Add to PATH if not already there
        if [[ ":$PATH:" != *":$INSTALL_DIR:"* ]]; then
            log_warning "$INSTALL_DIR is not in PATH"
            log_info "Add this to your ~/.bashrc or ~/.zshrc:"
            echo "export PATH=\"\$PATH:$INSTALL_DIR\""
        fi
    else
        log_info "ADTUI is already in PATH"
    fi
}

# Detect best installation method
detect_install_method() {
    if [[ "$INSTALL_METHOD" != "auto" ]]; then
        return
    fi
    
    log_info "Detecting best installation method..."
    
    # Prioritize binary method for better compatibility
    INSTALL_METHOD="binary"
    log_info "Using binary executable for best compatibility"
}

# Install via pip
install_pip() {
    log_info "Installing via pip..."
    
    # Use pip3 if available, otherwise pip
    local PIP_CMD="pip3"
    if ! command -v pip3 &> /dev/null; then
        PIP_CMD="pip"
    fi
    
    # Try PyPI first (if published)
    if $PIP_CMD show adtui &> /dev/null; then
        log_info "ADTUI already installed, updating..."
        $PIP_CMD install --upgrade adtui
    else
        # Install from git repository
        $PIP_CMD install git+https://github.com/brz-admin/adtui.git
    fi
    
    log_success "ADTUI installed via pip"
}

# Install binary executable
install_binary() {
    log_info "Downloading binary executable..."
    
    OS=$(uname -s | tr '[:upper:]' '[:lower:]')
    ARCH=$(uname -m)
    
    # Map architecture names
    case $ARCH in
        x86_64)
            ARCH="amd64"
            ;;
        aarch64|arm64)
            ARCH="arm64"
            ;;
        *)
            log_error "Unsupported architecture: $ARCH"
            exit 1
            ;;
    esac
    
    # Download URL
    if [[ "$VERSION" == "latest" ]]; then
        DOWNLOAD_URL="${REPO_URL}/releases/latest/download/adtui"
    else
        DOWNLOAD_URL="${REPO_URL}/releases/download/v${VERSION}/adtui"
    fi
    
    # Download executable
    log_info "Downloading from: $DOWNLOAD_URL"
    curl -L "$DOWNLOAD_URL" -o "$INSTALL_DIR/adtui"
    
    # Make executable
    chmod +x "$INSTALL_DIR/adtui"
    
    log_success "ADTUI executable installed to $INSTALL_DIR/adtui"
}

# Install from source
install_source() {
    log_info "Installing from source..."
    
    TEMP_DIR=$(mktemp -d)
    cd "$TEMP_DIR"
    
    # Clone repository
    git clone "$REPO_URL" adtui
    cd adtui
    
# Install with system-wide pip (no user install)
    if command -v pip3 &> /dev/null; then
        pip3 install -e .
    elif command -v pip &> /dev/null; then
        pip install -e .
    else
        # Install pip first, then install package
        log_info "Installing pip first..."
        curl -fsSL https://bootstrap.pypa.io/get-pip.py | python3
        python3 -m pip install -e .
    fi
    
    log_success "ADTUI installed system-wide"
    
    # Add to PATH if needed
    if [[ ":$PATH:" != *":$INSTALL_DIR:"* ]]; then
        log_warning "$INSTALL_DIR is not in PATH"
        log_info "Add this to your ~/.bashrc or ~/.zshrc:"
        echo "export PATH=\"\$PATH:$INSTALL_DIR\""
    fi
    
    # Cleanup
    cd /
    rm -rf "$TEMP_DIR"
    
    log_success "ADTUI installed from source"
    
    # Add to PATH if needed
    if [[ ":$PATH:" != *":$HOME/.local/bin:"* ]]; then
        log_warning "~/.local/bin is not in PATH"
        log_info "Add this to your ~/.bashrc or ~/.zshrc:"
        echo "export PATH=\"\$PATH:\$HOME/.local/bin\""
    fi
}

# Verify installation
verify_installation() {
    log_info "Verifying installation..."
    
    if command -v adtui &> /dev/null; then
        log_success "ADTUI is available in PATH"
        
        # Try to get version
        if adtui --version &> /dev/null 2>&1; then
            log_success "ADTUI is working correctly"
        else
            log_warning "ADTUI installed but may need configuration"
        fi
    else
        log_error "ADTUI not found in PATH"
        exit 1
    fi
}

# Main installation flow
main() {
    log_info "Starting ADTUI installation..."
    
    check_requirements
    detect_install_method
    
    log_info "Using installation method: $INSTALL_METHOD"
    
    case $INSTALL_METHOD in
        "pip")
            install_pip
            ;;
        "binary")
            install_binary
            ;;
        "source")
            install_source
            ;;
        *)
            log_error "Unknown installation method: $INSTALL_METHOD"
            exit 1
            ;;
    esac
    
    verify_installation
    
    echo ""
    log_success "🎉 ADTUI installation completed successfully!"
    echo ""
    echo "To start using ADTUI:"
    echo "1. Create configuration directory:"
    echo "   mkdir -p ~/.config/adtui"
    echo ""
    echo "2. Copy configuration template:"
    if [ "$INSTALL_METHOD" = "source" ] || [ "$INSTALL_METHOD" = "python" ]; then
        echo "   cp config.ini.example ~/.config/adtui/config.ini"
    else
        echo "   wget -q https://git.brznet.fr/Brz/adtui/raw/branch/main/config.ini.example -O ~/.config/adtui/config.ini"
    fi
    echo ""
    echo "3. Edit configuration with your AD details:"
    echo "   nano ~/.config/adtui/config.ini"
    echo ""
    echo "4. Run ADTUI:"
    if [ "$INSTALL_METHOD" = "source" ] || [ "$INSTALL_METHOD" = "python" ]; then
        echo "   adtui"
    else
        echo "   $INSTALL_DIR/adtui"
    fi
    echo ""
}

# Run main function
main "$@"