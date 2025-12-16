#!/usr/bin/env python3
"""Build ADTUI for multiple platforms and create distributions."""

import subprocess
import sys
import os
from pathlib import Path


def run_command(cmd, cwd=None, check=True):
    """Run command and handle errors."""
    print(f"Running: {' '.join(cmd)}")
    try:
        result = subprocess.run(cmd, cwd=cwd, check=check, capture_output=False)
        return result
    except subprocess.CalledProcessError as e:
        print(f"Command failed: {e}")
        sys.exit(1)


def build_wheel():
    """Build Python wheel package."""
    print("📦 Building wheel package...")
    run_command(["python", "-m", "build", "--wheel"])
    print("✅ Wheel package built successfully")


def build_sdist():
    """Build source distribution."""
    print("📦 Building source distribution...")
    run_command(["python", "-m", "build", "--sdist"])
    print("✅ Source distribution built successfully")


def build_executable():
    """Build PyInstaller executable."""
    print("🔨 Building executable with PyInstaller...")
    run_command(["pyinstaller", "--clean", "scripts/pyinstaller.spec"])
    print("✅ Executable built successfully")


def clean():
    """Clean build artifacts."""
    print("🧹 Cleaning build artifacts...")

    # Remove build directories
    artifacts = [
        "build/",
        "dist/",
        "*.egg-info/",
        "adtui/__pycache__/",
        "adtui/*/__pycache__/",
        "__pycache__/",
    ]

    for artifact in artifacts:
        if "*" in artifact:
            run_command(
                [
                    "find",
                    ".",
                    "-name",
                    artifact.replace("*", "*"),
                    "-type",
                    "d",
                    "-exec",
                    "rm",
                    "-rf",
                    "{}",
                    "+",
                ],
                check=False,
            )
        else:
            run_command(["rm", "-rf", artifact], check=False)

    print("✅ Build artifacts cleaned")


def validate_package():
    """Validate the built package."""
    print("🔍 Validating package...")

    # Check if wheel exists
    wheel_files = list(Path("dist").glob("*.whl"))
    if not wheel_files:
        print("❌ No wheel file found in dist/")
        sys.exit(1)

    wheel_path = wheel_files[0]
    print(f"Found wheel: {wheel_path}")

    # Validate with twine
    run_command(["python", "-m", "twine", "check", str(wheel_path)])
    print("✅ Package validation passed")


def main():
    """Main build process."""
    import argparse

    parser = argparse.ArgumentParser(description="Build ADTUI packages")
    parser.add_argument("--clean", action="store_true", help="Clean build artifacts")
    parser.add_argument("--wheel", action="store_true", help="Build wheel package")
    parser.add_argument(
        "--sdist", action="store_true", help="Build source distribution"
    )
    parser.add_argument("--executable", action="store_true", help="Build executable")
    parser.add_argument("--all", action="store_true", help="Build all packages")
    parser.add_argument("--validate", action="store_true", help="Validate packages")

    args = parser.parse_args()

    # Change to repository root
    repo_root = Path(__file__).parent.parent
    os.chdir(repo_root)

    print(f"🚀 ADTUI Build Script")
    print(f"📍 Working directory: {repo_root}")
    print(f"🐍 Python version: {sys.version}")

    if args.clean:
        clean()
        return

    if not any([args.wheel, args.sdist, args.executable, args.all]):
        print("No target specified. Use --help for options.")
        return

    # Install build dependencies if needed
    print("📋 Installing build dependencies...")
    run_command(
        ["python", "-m", "pip", "install", "--upgrade", "build", "twine", "pyinstaller"]
    )

    if args.all:
        clean()
        build_wheel()
        build_sdist()
        build_executable()
    else:
        if args.wheel:
            build_wheel()
        if args.sdist:
            build_sdist()
        if args.executable:
            build_executable()

    if args.validate or args.all:
        validate_package()

    # List artifacts
    print("\n📋 Build artifacts:")
    if os.path.exists("dist"):
        for item in Path("dist").iterdir():
            size = item.stat().st_size if item.is_file() else "N/A"
            print(
                f"  - {item.name} ({size:,} bytes)"
                if isinstance(size, int)
                else f"  - {item.name}"
            )


if __name__ == "__main__":
    main()
