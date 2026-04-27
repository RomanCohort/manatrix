"""
Crawler Configuration

Dataclasses and settings for the web crawler.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Set
from urllib.parse import urlparse


@dataclass
class CrawlerConfig:
    """Configuration for the web crawler."""

    # Target specification
    start_urls: List[str] = field(default_factory=list)

    # Crawling limits
    max_depth: int = 2
    max_urls: int = 1000
    max_per_page: int = 100

    # Respect robots.txt and sitemap
    respect_robots: bool = True
    use_sitemap: bool = True

    # Rate limiting
    rate_limit: float = 1.0  # seconds between requests
    max_concurrent: int = 5

    # HTTP settings
    user_agent: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 PentestBot/1.0"
    timeout: float = 10.0
    follow_redirects: bool = True
    max_redirects: int = 5

    # Domain filtering
    allowed_domains: List[str] = field(default_factory=list)
    denied_domains: List[str] = field(default_factory=list)
    deny_paths: List[str] = field(default_factory=lambda: [
        "/admin", "/administrator", "/login", "/wp-admin",
        "/.git", "/.svn", "/.env", "/config", "/backup",
        "/debug", "/phpinfo", "/server-status",
        "/phpmyadmin", "/wp-content/uploads",
    ])

    # Content filtering
    allowed_content_types: List[str] = field(default_factory=lambda: [
        "text/html", "application/xhtml+xml",
        "application/xml", "text/xml",
    ])
    skip_media: bool = True
    skip_binaries: bool = True

    # Export settings
    export_to_state: bool = True
    export_to_kg: bool = True
    export_to_expert: bool = True

    # Proxy support
    proxy_url: Optional[str] = None

    # SSL settings
    verify_ssl: bool = True

    def __post_init__(self):
        """Validate and normalize configuration."""
        # Parse allowed/denied domains from start URLs if not specified
        if not self.allowed_domains and self.start_urls:
            domains = set()
            for url in self.start_urls:
                parsed = urlparse(url)
                if parsed.netloc:
                    domains.add(parsed.netloc)
            self.allowed_domains = list(domains)

    def is_url_allowed(self, url: str) -> bool:
        """Check if URL is within allowed scope."""
        parsed = urlparse(url)

        # Check domain restrictions
        if self.denied_domains:
            for denied in self.denied_domains:
                if denied in parsed.netloc:
                    return False

        if self.allowed_domains:
            domain_allowed = False
            for allowed in self.allowed_domains:
                if allowed in parsed.netloc:
                    domain_allowed = True
                    break
            if not domain_allowed:
                return False

        # Check path restrictions
        for denied_path in self.deny_paths:
            if denied_path.lower() in parsed.path.lower():
                return False

        return True

    def to_dict(self) -> dict:
        """Convert config to dictionary for serialization."""
        return {
            "start_urls": self.start_urls,
            "max_depth": self.max_depth,
            "max_urls": self.max_urls,
            "respect_robots": self.respect_robots,
            "rate_limit": self.rate_limit,
            "user_agent": self.user_agent,
            "timeout": self.timeout,
            "allowed_domains": self.allowed_domains,
            "deny_paths": self.deny_paths,
        }