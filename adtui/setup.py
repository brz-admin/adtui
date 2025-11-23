"""Setup script for ADTUI - Active Directory Terminal UI."""

from setuptools import setup, find_packages
import os

# Read the README file
with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

# Read requirements
with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="adtui",
    version="2.0.0",
    author="Your Name",
    author_email="your.email@example.com",
    description="Active Directory Terminal User Interface - A TUI for managing Active Directory",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/adtui",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: System Administrators",
        "Topic :: System :: Systems Administration :: Authentication/Directory",
        "Topic :: System :: Systems Administration :: Authentication/Directory :: LDAP",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Environment :: Console",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.8",
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "adtui=adtui:main",
        ],
    },
    include_package_data=True,
    package_data={
        "adtui": [
            "styles.tcss",
            "config.ini.example",
            "*.md",
        ],
    },
    zip_safe=False,
)
