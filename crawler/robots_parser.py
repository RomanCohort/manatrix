"""
Robots.txt Parser

Parse robots.txt to determine allowed/disallowed paths.
"""

import re
from dataclasses import dataclass, field
from typing import List, Dict, Set, Optional
from urllib.parse import urlparse, urljoin


@dataclass
class RobotsRule:
    """A single robots.txt rule."""
    path: str
    is_allowed: bool


@dataclass
class RobotsInfo:
    """Parsed robots.txt information."""
    url: str
    user_agent_rules: Dict[str, List[RobotsRule]]  # user-agent -> rules
    sitemaps: List[str]
    crawl_delay: Optional[float] = None
    has_robots_txt: bool = False
    raw_content: Optional[str] = None


class RobotsParser:
    """Parse and query robots.txt files."""

    def __init__(self, user_agent: str = "PentestBot"):
        """
        Initialize robots parser.

        Args:
            user_agent: User agent string for rule matching
        """
        self.user_agent = user_agent.lower()
        self.robots_cache: Dict[str, RobotsInfo] = {}

    def parse(self, robots_url: str, content: str) -> RobotsInfo:
        """
        Parse robots.txt content.

        Args:
            robots_url: URL of the robots.txt file
            content: Raw robots.txt content

        Returns:
            RobotsInfo with parsed rules
        """
        rules: Dict[str, List[RobotsRule]] = {}
        sitemaps = []
        crawl_delay = None
        current_agents = ["*"]

        for line in content.splitlines():
            line = line.strip()

            # Skip empty lines and comments
            if not line or line.startswith('#'):
                continue

            # Split directive
            if ':' not in line:
                continue

            directive, _, value = line.partition(':')
            directive = directive.strip().lower()
            value = value.strip()

            if not value:
                continue

            # Handle directives
            if directive == 'user-agent':
                current_agents = [value.lower()]

            elif directive == 'disallow':
                for agent in current_agents:
                    if agent not in rules:
                        rules[agent] = []
                    rules[agent].append(RobotsRule(
                        path=value,
                        is_allowed=False
                    ))

            elif directive == 'allow':
                for agent in current_agents:
                    if agent not in rules:
                        rules[agent] = []
                    rules[agent].append(RobotsRule(
                        path=value,
                        is_allowed=True
                    ))

            elif directive == 'crawl-delay':
                try:
                    crawl_delay = float(value)
                except ValueError:
                    pass

            elif directive == 'sitemap':
                # Resolve relative URLs
                if not value.startswith(('http://', 'https://')):
                    value = urljoin(robots_url, value)
                sitemaps.append(value)

        info = RobotsInfo(
            url=robots_url,
            user_agent_rules=rules,
            sitemaps=sitemaps,
            crawl_delay=crawl_delay,
            has_robots_txt=True,
            raw_content=content
        )

        # Cache
        parsed = urlparse(robots_url)
        domain = parsed.netloc
        self.robots_cache[domain] = info

        return info

    def is_allowed(self, url: str, robots_info: Optional[RobotsInfo] = None) -> bool:
        """
        Check if URL is allowed by robots.txt.

        Args:
            url: URL to check
            robots_info: Pre-parsed robots info (uses cache if None)

        Returns:
            True if URL is allowed
        """
        parsed = urlparse(url)
        domain = parsed.netloc
        path = parsed.path or '/'

        # Get robots info
        if robots_info is None:
            robots_info = self.robots_cache.get(domain)

        if not robots_info or not robots_info.has_robots_txt:
            # No robots.txt = everything allowed
            return True

        # Check specific user-agent rules first, then wildcard
        rules = []
        if self.user_agent in robots_info.user_agent_rules:
            rules = robots_info.user_agent_rules[self.user_agent]
        elif '*' in robots_info.user_agent_rules:
            rules = robots_info.user_agent_rules['*']

        if not rules:
            return True

        # Find the most specific matching rule
        best_match = None
        best_match_length = -1

        for rule in rules:
            if self._path_matches(path, rule.path):
                if len(rule.path) > best_match_length:
                    best_match = rule
                    best_match_length = len(rule.path)

        if best_match is None:
            return True

        return best_match.is_allowed

    def _path_matches(self, path: str, pattern: str) -> bool:
        """
        Check if path matches robots.txt pattern.

        Supports basic wildcards (*) and end-of-path ($).
        """
        if pattern == '/':
            return True

        # Convert robots.txt pattern to regex
        regex_pattern = pattern

        # Escape special regex chars (except * and $)
        for char in ['.?', '(', ')', '[', ']', '{', '}', '+', '|', '^']:
            regex_pattern = regex_pattern.replace(char, '\\' + char)

        # Handle wildcards
        regex_pattern = regex_pattern.replace('*', '.*')

        # Handle end-of-path marker
        if regex_pattern.endswith('$'):
            regex_pattern = regex_pattern[:-1] + '$'
        else:
            regex_pattern = regex_pattern + '.*'

        try:
            return bool(re.match(regex_pattern, path))
        except re.error:
            return path.startswith(pattern)

    def get_sitemaps(self, domain: str) -> List[str]:
        """Get sitemap URLs for a domain."""
        info = self.robots_cache.get(domain)
        return info.sitemaps if info else []

    def get_crawl_delay(self, domain: str) -> Optional[float]:
        """Get crawl delay for a domain."""
        info = self.robots_cache.get(domain)
        return info.crawl_delay if info else None
