"""Configuration Service - Handles multi-AD configuration loading."""

import configparser
import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple


class ADConfig:
    """Represents a single AD configuration."""

    def __init__(
        self,
        domain: str,
        server: str,
        base_dn: str,
        use_ssl: bool = False,
        max_retries: int = 5,
        initial_retry_delay: float = 1.0,
        max_retry_delay: float = 60.0,
        health_check_interval: float = 30.0,
    ):
        self.domain = domain
        self.server = server
        self.base_dn = base_dn
        self.use_ssl = use_ssl
        self.max_retries = max_retries
        self.initial_retry_delay = initial_retry_delay
        self.max_retry_delay = max_retry_delay
        self.health_check_interval = health_check_interval

    def __str__(self) -> str:
        return f"{self.domain} ({self.server})"


def get_config_search_paths(config_file: str = "config.ini") -> List[str]:
    """Get list of configuration file search paths in priority order."""
    from .platform_service import PlatformService

    # Environment variable override
    if os.getenv("ADTUI_CONFIG"):
        env_config = os.getenv("ADTUI_CONFIG")
        if env_config and os.path.exists(env_config):
            return [env_config]

    # User-specific config directory (preferred)
    user_config_dir = PlatformService.get_config_dir()
    user_config = user_config_dir / config_file
    if user_config.exists():
        return [str(user_config)]

    # Legacy home directory location (Unix only)
    legacy_config = PlatformService.get_legacy_config_path(config_file)
    if legacy_config and legacy_config.exists():
        return [str(legacy_config)]

    # Current working directory (backward compatibility)
    cwd_config = Path.cwd() / config_file
    if cwd_config.exists():
        return [str(cwd_config)]

    # Return default paths for creation (in priority order)
    return [
        str(user_config_dir / config_file),  # Preferred location
        str(cwd_config),  # Fallback location
    ]


class ConfigService:
    """Service for loading and managing AD configurations."""

    def __init__(self, config_file: str = "config.ini"):
        # Search for existing config file
        search_paths = get_config_search_paths(config_file)

        # Find first existing config
        self.config_file = None
        for path in search_paths:
            if os.path.exists(path):
                self.config_file = path
                break

        # No existing config found, use preferred default location
        if self.config_file is None:
            self.config_file = search_paths[0]

        self.config = configparser.ConfigParser()
        self.ad_configs: Dict[str, ADConfig] = {}
        self._load_config()

    def _load_config(self) -> None:
        """Load configuration from file."""
        if not os.path.exists(self.config_file):
            # Provide helpful error message with creation guidance
            config_dir = os.path.dirname(self.config_file)
            config_name = os.path.basename(self.config_file)

            # Suggest creation command
            if config_dir.startswith(str(Path.home())):
                # Home directory config
                relative_config = self.config_file.replace(str(Path.home()), "~")
                print(f"Configuration file not found at: {relative_config}")
                print(f"Creating config directory: {config_dir}")
                os.makedirs(config_dir, exist_ok=True)
                print(f"Please copy config.ini.example to: {relative_config}")
                print(f"Example: cp config.ini.example {relative_config}")
            else:
                # Current working directory config
                print(
                    f"Configuration file '{config_name}' not found in current directory"
                )
                print(
                    "Please copy config.ini.example to config.ini in current directory"
                )
                print("Example: cp config.ini.example config.ini")

            raise FileNotFoundError(
                f"Configuration file '{self.config_file}' not found"
            )

        self.config.read(self.config_file)

        # Try to load multi-AD configuration first
        if self._has_multi_ad_config():
            self._load_multi_ad_config()
        else:
            # Fall back to legacy single AD configuration
            self._load_legacy_config()

    def _has_multi_ad_config(self) -> bool:
        """Check if config file has multi-AD configuration."""
        return "ad_domains" in self.config and "domains" in self.config["ad_domains"]

    def _load_multi_ad_config(self) -> None:
        """Load multi-AD configuration."""
        domains_str = self.config["ad_domains"]["domains"]
        domains = [d.strip() for d in domains_str.split(",") if d.strip()]

        for domain in domains:
            section_name = f"ad_{domain}"
            if section_name in self.config:
                ad_config = self.config[section_name]
                self.ad_configs[domain] = ADConfig(
                    domain=domain,
                    server=ad_config["server"],
                    base_dn=ad_config["base_dn"],
                    use_ssl=ad_config.getboolean("use_ssl", fallback=False),
                    max_retries=ad_config.getint("max_retries", fallback=5),
                    initial_retry_delay=ad_config.getfloat(
                        "initial_retry_delay", fallback=1.0
                    ),
                    max_retry_delay=ad_config.getfloat(
                        "max_retry_delay", fallback=60.0
                    ),
                    health_check_interval=ad_config.getfloat(
                        "health_check_interval", fallback=30.0
                    ),
                )

    def _load_legacy_config(self) -> None:
        """Load legacy single AD configuration."""
        if "ldap" in self.config:
            ldap_config = self.config["ldap"]
            domain = ldap_config.get("domain", "DEFAULT")
            self.ad_configs[domain] = ADConfig(
                domain=domain,
                server=ldap_config["server"],
                base_dn=ldap_config["base_dn"],
                use_ssl=ldap_config.getboolean("use_ssl", fallback=False),
                max_retries=ldap_config.getint("max_retries", fallback=5),
                initial_retry_delay=ldap_config.getfloat(
                    "initial_retry_delay", fallback=1.0
                ),
                max_retry_delay=ldap_config.getfloat("max_retry_delay", fallback=60.0),
                health_check_interval=ldap_config.getfloat(
                    "health_check_interval", fallback=30.0
                ),
            )

    def get_available_domains(self) -> List[str]:
        """Get list of available AD domains."""
        return list(self.ad_configs.keys())

    def get_config(self, domain: str) -> Optional[ADConfig]:
        """Get AD configuration for specified domain."""
        return self.ad_configs.get(domain)

    def has_multiple_domains(self) -> bool:
        """Check if multiple AD domains are configured."""
        return len(self.ad_configs) > 1

    def get_default_domain(self) -> Optional[str]:
        """Get default domain (first in list)."""
        domains = self.get_available_domains()
        return domains[0] if domains else None

    def validate_config(self) -> Tuple[bool, List[str]]:
        """Validate configuration and return any issues."""
        issues = []

        if not self.ad_configs:
            issues.append("No AD configurations found")
            return False, issues

        # Check each configuration
        for domain, config in self.ad_configs.items():
            if not config.server:
                issues.append(f"Domain {domain}: Missing server")
            if not config.base_dn:
                issues.append(f"Domain {domain}: Missing base_dn")

        return len(issues) == 0, issues

    def get_config_file_path(self) -> str:
        """Get the path to the currently loaded config file."""
        return self.config_file
