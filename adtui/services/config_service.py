"""Configuration Service - Handles multi-AD configuration loading."""

import configparser
import os
from typing import Dict, List, Optional, Tuple


class ADConfig:
    """Represents a single AD configuration."""
    
    def __init__(self, domain: str, server: str, base_dn: str, use_ssl: bool = False):
        self.domain = domain
        self.server = server
        self.base_dn = base_dn
        self.use_ssl = use_ssl
    
    def __str__(self) -> str:
        return f"{self.domain} ({self.server})"


class ConfigService:
    """Service for loading and managing AD configurations."""
    
    def __init__(self, config_file: str = "config.ini"):
        self.config_file = config_file
        self.config = configparser.ConfigParser()
        self.ad_configs: Dict[str, ADConfig] = {}
        self._load_config()
    
    def _load_config(self) -> None:
        """Load configuration from file."""
        if not os.path.exists(self.config_file):
            raise FileNotFoundError(f"Configuration file '{self.config_file}' not found")
        
        self.config.read(self.config_file)
        
        # Try to load multi-AD configuration first
        if self._has_multi_ad_config():
            self._load_multi_ad_config()
        else:
            # Fall back to legacy single AD configuration
            self._load_legacy_config()
    
    def _has_multi_ad_config(self) -> bool:
        """Check if config file has multi-AD configuration."""
        return 'ad_domains' in self.config and 'domains' in self.config['ad_domains']
    
    def _load_multi_ad_config(self) -> None:
        """Load multi-AD configuration."""
        domains_str = self.config['ad_domains']['domains']
        domains = [d.strip() for d in domains_str.split(',') if d.strip()]
        
        for domain in domains:
            section_name = f'ad_{domain}'
            if section_name in self.config:
                ad_config = self.config[section_name]
                self.ad_configs[domain] = ADConfig(
                    domain=domain,
                    server=ad_config['server'],
                    base_dn=ad_config['base_dn'],
                    use_ssl=ad_config.getboolean('use_ssl', fallback=False)
                )
    
    def _load_legacy_config(self) -> None:
        """Load legacy single AD configuration."""
        if 'ldap' in self.config:
            ldap_config = self.config['ldap']
            domain = ldap_config.get('domain', 'DEFAULT')
            self.ad_configs[domain] = ADConfig(
                domain=domain,
                server=ldap_config['server'],
                base_dn=ldap_config['base_dn'],
                use_ssl=ldap_config.getboolean('use_ssl', fallback=False)
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
        """Get the default domain (first in list)."""
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