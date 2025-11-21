from setuptools import setup, find_packages

setup(
    name="ad_tui",
    version="0.1",
    packages=find_packages(),
    install_requires=["ldap3", "textual", "prompt_toolkit"],
    entry_points={"console_scripts": ["ad-tui=ad_tui.app:main"]},
)

