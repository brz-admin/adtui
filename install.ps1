#Requires -Version 5.1
<#
.SYNOPSIS
    ADTUI Installer for Windows
.DESCRIPTION
    Installs ADTUI (Active Directory Terminal UI) on Windows systems.
    Creates a virtual environment and installs the package from Git.
.PARAMETER Uninstall
    Remove ADTUI installation
.PARAMETER Update
    Update ADTUI to the latest version
.EXAMPLE
    .\install.ps1
    .\install.ps1 -Update
    .\install.ps1 -Uninstall
.NOTES
    One-liner: irm https://servgitea.domman.ad/ti2103/adtui/raw/branch/main/install.ps1 | iex
#>

[CmdletBinding()]
param(
    [switch]$Uninstall,
    [switch]$Update,
    [switch]$Help
)

# Configuration
$REPO_URL = "https://github.com/brz-admin/adtui.git"
$FALLBACK_REPO = "https://servgitea.domman.ad/ti2103/adtui.git"
$INSTALL_DIR = Join-Path $env:LOCALAPPDATA "adtui"
$VENV_DIR = Join-Path $INSTALL_DIR "venv"
$CONFIG_DIR = Join-Path $env:APPDATA "adtui"

# Colors for output
function Write-Info { param($Message) Write-Host "[INFO] " -ForegroundColor Cyan -NoNewline; Write-Host $Message }
function Write-Success { param($Message) Write-Host "[OK] " -ForegroundColor Green -NoNewline; Write-Host $Message }
function Write-Warn { param($Message) Write-Host "[WARN] " -ForegroundColor Yellow -NoNewline; Write-Host $Message }
function Write-Err { param($Message) Write-Host "[ERROR] " -ForegroundColor Red -NoNewline; Write-Host $Message; exit 1 }

function Show-Banner {
    Write-Host ""
    Write-Host "======================================" -ForegroundColor Cyan
    Write-Host "  ADTUI - Active Directory TUI" -ForegroundColor Cyan
    Write-Host "  Windows Installer" -ForegroundColor Cyan
    Write-Host "======================================" -ForegroundColor Cyan
    Write-Host ""
}

function Show-Help {
    Write-Host "ADTUI Installer for Windows"
    Write-Host ""
    Write-Host "Usage: .\install.ps1 [OPTIONS]"
    Write-Host ""
    Write-Host "Options:"
    Write-Host "  -Uninstall     Remove ADTUI"
    Write-Host "  -Update        Update ADTUI to latest version"
    Write-Host "  -Help          Show this help"
    Write-Host ""
    Write-Host "One-liner install:"
    Write-Host "  irm https://servgitea.domman.ad/ti2103/adtui/raw/branch/main/install.ps1 | iex"
    Write-Host ""
    exit 0
}

function Test-PythonInstalled {
    Write-Info "Checking Python..."

    # Try python command first
    try {
        $pythonVersion = & python --version 2>&1
        if ($pythonVersion -match "Python (\d+)\.(\d+)") {
            $major = [int]$Matches[1]
            $minor = [int]$Matches[2]
            if ($major -ge 3 -and $minor -ge 8) {
                Write-Success "Found $pythonVersion"
                return "python"
            }
        }
    } catch {}

    # Try python3 command
    try {
        $pythonVersion = & python3 --version 2>&1
        if ($pythonVersion -match "Python (\d+)\.(\d+)") {
            $major = [int]$Matches[1]
            $minor = [int]$Matches[2]
            if ($major -ge 3 -and $minor -ge 8) {
                Write-Success "Found $pythonVersion"
                return "python3"
            }
        }
    } catch {}

    # Try py launcher
    try {
        $pythonVersion = & py -3 --version 2>&1
        if ($pythonVersion -match "Python (\d+)\.(\d+)") {
            $major = [int]$Matches[1]
            $minor = [int]$Matches[2]
            if ($major -ge 3 -and $minor -ge 8) {
                Write-Success "Found $pythonVersion"
                return "py"
            }
        }
    } catch {}

    # Python not found, try to install
    Write-Warn "Python not found. Attempting to install..."

    # Try winget first
    try {
        $wingetCheck = & winget --version 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Info "Installing Python 3.14 via winget..."
            & winget install Python.Python.3.14 --silent --accept-package-agreements --accept-source-agreements

            if ($LASTEXITCODE -eq 0) {
                Write-Success "Python installed via winget"
                Restart-And-Continue
            }
        }
    } catch {}

    # Fallback: download from python.org
    Write-Info "Downloading Python from python.org..."
    $pythonUrl = "https://www.python.org/ftp/python/3.14.0/python-3.14.0-amd64.exe"
    $installerPath = "$env:TEMP\python-installer.exe"

    try {
        Invoke-WebRequest -Uri $pythonUrl -OutFile $installerPath -UseBasicParsing

        Write-Info "Installing Python (this may take a minute)..."
        Start-Process -FilePath $installerPath -ArgumentList "/quiet InstallAllUsers=0 PrependPath=1 Include_pip=1" -Wait

        Remove-Item $installerPath -Force -ErrorAction SilentlyContinue

        Write-Success "Python installed successfully"
        Restart-And-Continue
    } catch {
        Write-Err "Failed to install Python. Please install manually from https://python.org"
    }
}

function Restart-And-Continue {
    Write-Warn "Please restart your terminal and run this installer again."
    Write-Host ""
    Write-Host "After restarting, run:" -ForegroundColor Yellow
    Write-Host "  Invoke-Expression (Invoke-RestMethod https://raw.githubusercontent.com/brz-admin/adtui/main/install.ps1)" -ForegroundColor Cyan
    exit 0
}

function Install-ADTUI {
    param([string]$PythonCmd)

    Write-Info "Creating installation directory..."

    # Create directories
    if (-not (Test-Path $INSTALL_DIR)) {
        New-Item -ItemType Directory -Path $INSTALL_DIR -Force | Out-Null
    }

    Write-Info "Creating virtual environment..."

    # Create venv
    if ($PythonCmd -eq "py") {
        & py -3 -m venv $VENV_DIR
    } else {
        & $PythonCmd -m venv $VENV_DIR
    }

    if (-not $?) {
        Write-Err "Failed to create virtual environment"
    }

    # Paths
    $pipPath = Join-Path $VENV_DIR "Scripts\pip.exe"
    $pythonPath = Join-Path $VENV_DIR "Scripts\python.exe"

    Write-Info "Upgrading pip..."
    & $pipPath install --upgrade pip 2>&1 | Out-Null

    Write-Info "Installing ADTUI (this may take a minute)..."

    # Try primary repo
    $installed = $false
    $output = & $pipPath install "git+$REPO_URL" 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Success "ADTUI installed from primary repository"
        $installed = $true
    } else {
        Write-Warn "Primary repository failed, trying fallback..."
        # Try fallback repo
        $output = & $pipPath install "git+$FALLBACK_REPO" 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Success "ADTUI installed from fallback repository"
            $installed = $true
        }
    }

    if (-not $installed) {
        Write-Err "Failed to install ADTUI. Check your internet connection and that Git is installed."
    }

    # Create wrapper batch file
    $batchPath = Join-Path $INSTALL_DIR "adtui.cmd"
    $batchContent = "@echo off`r`n`"$pythonPath`" -m adtui %*"
    Set-Content -Path $batchPath -Value $batchContent -Encoding ASCII

    Write-Success "Created launcher at $batchPath"
}

function Add-ToPath {
    Write-Info "Checking PATH..."

    $userPath = [Environment]::GetEnvironmentVariable("PATH", "User")
    if ($userPath -notlike "*$INSTALL_DIR*") {
        Write-Info "Adding to user PATH..."
        $newPath = "$INSTALL_DIR;$userPath"
        [Environment]::SetEnvironmentVariable("PATH", $newPath, "User")
        $env:PATH = "$INSTALL_DIR;$env:PATH"
        Write-Success "Added to PATH"
        return $true
    } else {
        Write-Success "Already in PATH"
        return $false
    }
}

function Update-ADTUI {
    Write-Info "Updating ADTUI..."

    if (-not (Test-Path $VENV_DIR)) {
        Write-Err "ADTUI is not installed. Run the installer first."
    }

    $pipPath = Join-Path $VENV_DIR "Scripts\pip.exe"

    # Try primary repo
    $output = & $pipPath install --upgrade "git+$REPO_URL" 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Success "ADTUI updated from primary repository"
        exit 0
    }

    # Try fallback repo
    $output = & $pipPath install --upgrade "git+$FALLBACK_REPO" 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Success "ADTUI updated from fallback repository"
        exit 0
    }

    Write-Err "Failed to update ADTUI."
}

function Uninstall-ADTUI {
    Write-Info "Uninstalling ADTUI..."

    if (Test-Path $INSTALL_DIR) {
        Remove-Item -Path $INSTALL_DIR -Recurse -Force
        Write-Success "Removed $INSTALL_DIR"
    } else {
        Write-Warn "Installation directory not found"
    }

    # Remove from PATH
    $userPath = [Environment]::GetEnvironmentVariable("PATH", "User")
    if ($userPath -like "*$INSTALL_DIR*") {
        $pathParts = $userPath -split ";" | Where-Object { $_ -ne $INSTALL_DIR -and $_ -ne "" }
        $newPath = $pathParts -join ";"
        [Environment]::SetEnvironmentVariable("PATH", $newPath, "User")
        Write-Success "Removed from PATH"
    }

    Write-Success "ADTUI uninstalled"
    Write-Host ""
    Write-Host "Configuration at $CONFIG_DIR was preserved."
    Write-Host "Remove it manually if needed:"
    Write-Host "  Remove-Item -Recurse `"$CONFIG_DIR`"" -ForegroundColor Cyan
    exit 0
}

function Show-Instructions {
    param([bool]$PathUpdated)

    Write-Host ""
    Write-Host "======================================" -ForegroundColor Green
    Write-Host "  Installation Complete!" -ForegroundColor Green
    Write-Host "======================================" -ForegroundColor Green
    Write-Host ""

    if ($PathUpdated) {
        Write-Host "NOTE: PATH was updated. Either:" -ForegroundColor Yellow
        Write-Host "  1. Restart your terminal, OR"
        Write-Host "  2. Run: " -NoNewline
        Write-Host "`$env:PATH = [Environment]::GetEnvironmentVariable('PATH', 'User')" -ForegroundColor Cyan
        Write-Host ""
    }

    Write-Host "To start ADTUI:"
    Write-Host "  adtui" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "On first run, ADTUI will guide you through AD configuration."
    Write-Host ""
    Write-Host "Commands:"
    Write-Host "  adtui --version    Show version"
    Write-Host "  adtui --help       Show help"
    Write-Host ""
}

# Main
function Main {
    Show-Banner

    if ($Help) { Show-Help }
    if ($Uninstall) { Uninstall-ADTUI }
    if ($Update) { Update-ADTUI }

    # Check for Git (required for pip install from git)
    try {
        $gitVersion = & git --version 2>&1
        Write-Success "Found $gitVersion"
    } catch {
        Write-Err "Git is required but not found. Please install Git from https://git-scm.com"
    }

    $pythonCmd = Test-PythonInstalled
    Install-ADTUI -PythonCmd $pythonCmd
    $pathUpdated = Add-ToPath
    Show-Instructions -PathUpdated $pathUpdated
}

Main
