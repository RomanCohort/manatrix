"""
Sitemap Parser

Parse XML sitemaps for URL discovery.
"""

import re
from dataclasses import dataclass, field
from typing import List, Optional
from urllib.parse import urlparse, urljoin


@dataclass
class SitemapURL:
    """A URL from a sitemap."""
    loc: str
    lastmod: Optional[str] = None
    changefreq: Optional[str] = None
    priority: Optional[float] = None


@dataclass
class SitemapInfo:
    """Parsed sitemap information."""
    url: str
    urls: List[SitemapURL]
    sitemap_index: bool = False
    child_sitemaps: List[str] = field(default_factory=list)


class SitemapParser:
    """Parse XML sitemaps."""

    def parse(self, sitemap_url: str, content: str) -> SitemapInfo:
        """
        Parse sitemap XML content.

        Args:
            sitemap_url: URL of the sitemap
            content: XML content

        Returns:
            SitemapInfo with parsed URLs
        """
        content = content.strip()

        # Check if it's a sitemap index
        if '<sitemapindex' in content:
            return self._parse_index(sitemap_url, content)

        return self._parse_urlset(sitemap_url, content)

    def _parse_urlset(self, sitemap_url: str, content: str) -> SitemapInfo:
        """Parse a regular sitemap (urlset)."""
        urls = []

        # Extract URL entries
        url_pattern = r'<url>(.*?)</url>'
        for match in re.finditer(url_pattern, content, re.DOTALL):
            url_block = match.group(1)

            loc = self._extract_tag(url_block, 'loc')
            lastmod = self._extract_tag(url_block, 'lastmod')
            changefreq = self._extract_tag(url_block, 'changefreq')
            priority_str = self._extract_tag(url_block, 'priority')

            priority = None
            if priority_str:
                try:
                    priority = float(priority_str)
                except ValueError:
                    pass

            if loc:
                # Resolve relative URLs
                if not loc.startswith(('http://', 'https://')):
                    loc = urljoin(sitemap_url, loc)
                urls.append(SitemapURL(
                    loc=loc,
                    lastmod=lastmod,
                    changefreq=changefreq,
                    priority=priority
                ))

        return SitemapInfo(
            url=sitemap_url,
            urls=urls
        )

    def _parse_index(self, sitemap_url: str, content: str) -> SitemapInfo:
        """Parse a sitemap index."""
        child_sitemaps = []

        sitemap_pattern = r'<sitemap>(.*?)</sitemap>'
        for match in re.finditer(sitemap_pattern, content, re.DOTALL):
            block = match.group(1)
            loc = self._extract_tag(block, 'loc')

            if loc:
                if not loc.startswith(('http://', 'https://')):
                    loc = urljoin(sitemap_url, loc)
                child_sitemaps.append(loc)

        return SitemapInfo(
            url=sitemap_url,
            urls=[],
            sitemap_index=True,
            child_sitemaps=child_sitemaps
        )

    def _extract_tag(self, block: str, tag: str) -> Optional[str]:
        """Extract text content from XML tag."""
        # Handle namespace prefixes
        pattern = rf'(?:\w+:)?{tag}>(.*?)<(?:/\w+:)?{tag}'
        match = re.search(pattern, block, re.DOTALL)
        if match:
            return match.group(1).strip()

        # Simple pattern without namespace
        pattern = rf'<{tag}[^>]*>(.*?)</{tag}>'
        match = re.search(pattern, block, re.DOTALL)
        if match:
            return match.group(1).strip()

        return None
