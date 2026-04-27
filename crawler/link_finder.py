"""
Link Finder

Extract URLs from HTML and JavaScript content.
"""

import re
from dataclasses import dataclass, field
from typing import List, Set, Optional
from urllib.parse import urljoin, urlparse, urlunparse


@dataclass
class LinkInfo:
    """Information about a discovered link."""
    url: str
    source_url: str
    link_type: str  # "a", "img", "script", "css", "form", "iframe", "meta", "other"
    rel: Optional[str] = None  # rel attribute for anchors
    text: Optional[str] = None  # anchor text
    method: str = "GET"  # HTTP method (GET, POST, etc.)
    data: Optional[dict] = None  # form data if applicable


class LinkFinder:
    """Extract and filter links from HTML/JS content."""

    # URL patterns commonly found in JavaScript
    JS_URL_PATTERNS = [
        r'["\']((?:https?:)?//[^"\']+)["\']',
        r'["\']((?:/\w+)+/?)["\']',
        r'["\'](\.\./[^"\']+)["\']',
        r'url\(["\']?([^)"\']+)["\']?\)',
        r'href\s*=\s*["\']([^"\']+)["\']',
        r'src\s*=\s*["\']([^"\']+)["\']',
        r'action\s*=\s*["\']([^"\']+)["\']',
    ]

    # File extensions to skip (media, binaries)
    SKIP_EXTENSIONS = {
        # Images
        '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.ico', '.svg', '.webp', '.tiff',
        # Video
        '.mp4', '.avi', '.mov', '.wmv', '.flv', '.mkv', '.webm', '.m4v',
        # Audio
        '.mp3', '.wav', '.ogg', '.flac', '.aac', '.m4a',
        # Documents (usually static)
        '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx',
        # Archives
        '.zip', '.rar', '.7z', '.tar', '.gz', '.bz2',
        # Fonts
        '.woff', '.woff2', '.ttf', '.eot', '.otf',
        # Binaries
        '.exe', '.dll', '.so', '.bin', '.iso',
    }

    def __init__(self, base_url: str, skip_media: bool = True, skip_binaries: bool = True):
        """
        Initialize link finder.

        Args:
            base_url: Base URL for resolving relative URLs
            skip_media: Skip image/video/audio files
            skip_binaries: Skip binary files
        """
        self.base_url = base_url
        self.parsed_base = urlparse(base_url)
        self.skip_media = skip_media
        self.skip_binaries = skip_binaries

    def extract_links(self, html: str, content_type: str = "text/html") -> List[LinkInfo]:
        """
        Extract links from HTML content.

        Args:
            html: HTML content
            content_type: Content type of the response

        Returns:
            List of LinkInfo objects
        """
        links = []

        if "html" in content_type.lower():
            links.extend(self._extract_html_links(html))
        elif "javascript" in content_type.lower():
            links.extend(self._extract_js_links(html))

        return self._filter_links(links)

    def _extract_html_links(self, html: str) -> List[LinkInfo]:
        """Extract links from HTML using regex patterns."""
        links = []

        # Pattern for anchor tags
        a_pattern = r'<a[^>]*href=["\']([^"\']+)["\'][^>]*(?:>([^<]*)</a>)?'
        for match in re.finditer(a_pattern, html, re.IGNORECASE):
            url, text = match.groups()
            rel = self._extract_attribute(match.group(0), 'rel')
            links.append(LinkInfo(
                url=url.strip(),
                source_url=self.base_url,
                link_type="a",
                rel=rel,
                text=text.strip() if text else None
            ))

        # Pattern for script tags
        script_pattern = r'<script[^>]*src=["\']([^"\']+)["\']'
        for match in re.finditer(script_pattern, html, re.IGNORECASE):
            links.append(LinkInfo(
                url=match.group(1).strip(),
                source_url=self.base_url,
                link_type="script"
            ))

        # Pattern for link tags (CSS, icons, etc.)
        link_pattern = r'<link[^>]*href=["\']([^"\']+)["\'][^>]*>'
        for match in re.finditer(link_pattern, html, re.IGNORECASE):
            rel = self._extract_attribute(match.group(0), 'rel')
            link_type = "css" if rel == "stylesheet" else "other"
            links.append(LinkInfo(
                url=match.group(1).strip(),
                source_url=self.base_url,
                link_type=link_type,
                rel=rel
            ))

        # Pattern for img tags
        img_pattern = r'<img[^>]*src=["\']([^"\']+)["\']'
        for match in re.finditer(img_pattern, html, re.IGNORECASE):
            links.append(LinkInfo(
                url=match.group(1).strip(),
                source_url=self.base_url,
                link_type="img"
            ))

        # Pattern for forms
        form_pattern = r'<form[^>]*action=["\']([^"\']*)["\'][^>]*(?:method=["\'](\w+)["\'])?'
        for match in re.finditer(form_pattern, html, re.IGNORECASE):
            url, method = match.groups()
            links.append(LinkInfo(
                url=url.strip() if url else self.base_url,
                source_url=self.base_url,
                link_type="form",
                method=method.upper() if method else "GET"
            ))

        # Pattern for iframes
        iframe_pattern = r'<iframe[^>]*src=["\']([^"\']+)["\']'
        for match in re.finditer(iframe_pattern, html, re.IGNORECASE):
            links.append(LinkInfo(
                url=match.group(1).strip(),
                source_url=self.base_url,
                link_type="iframe"
            ))

        # Pattern for meta refresh
        meta_pattern = r'<meta[^>]*http-equiv=["\']?refresh["\']?[^>]*content=["\']?[^"\']*url=([^"\';\s]+)'
        for match in re.finditer(meta_pattern, html, re.IGNORECASE):
            links.append(LinkInfo(
                url=match.group(1).strip(),
                source_url=self.base_url,
                link_type="meta"
            ))

        return links

    def _extract_js_links(self, js: str) -> List[LinkInfo]:
        """Extract URLs from JavaScript content."""
        links = []

        for pattern in self.JS_URL_PATTERNS:
            for match in re.finditer(pattern, js, re.IGNORECASE):
                url = match.group(1).strip()
                if url and not url.startswith(('data:', 'javascript:', '#')):
                    links.append(LinkInfo(
                        url=url,
                        source_url=self.base_url,
                        link_type="js_endpoint"
                    ))

        return links

    def _extract_attribute(self, tag: str, attr: str) -> Optional[str]:
        """Extract attribute value from HTML tag."""
        pattern = rf'{attr}=["\']([^"\']+)["\']'
        match = re.search(pattern, tag, re.IGNORECASE)
        return match.group(1) if match else None

    def _filter_links(self, links: List[LinkInfo]) -> List[LinkInfo]:
        """Filter and normalize links."""
        filtered = []
        seen_urls = set()

        for link in links:
            # Skip empty or javascript: URLs
            if not link.url or link.url.startswith(('javascript:', 'data:', '#')):
                continue

            # Normalize URL
            try:
                normalized = self._normalize_url(link.url)
            except Exception:
                continue

            # Skip already seen
            if normalized in seen_urls:
                continue
            seen_urls.add(normalized)

            # Update link URL
            link.url = normalized

            # Check extension filters
            if self._should_skip_url(normalized):
                continue

            filtered.append(link)

        return filtered

    def _normalize_url(self, url: str) -> str:
        """Normalize URL to absolute form."""
        # Handle protocol-relative URLs
        if url.startswith('//'):
            url = f"{self.parsed_base.scheme}:{url}"

        # Join with base URL for relative URLs
        if not url.startswith(('http://', 'https://')):
            url = urljoin(self.base_url, url)

        # Parse and clean
        parsed = urlparse(url)

        # Remove fragment
        parsed = parsed._replace(fragment='')

        # Normalize path (remove trailing slash except for root)
        path = parsed.path
        if path != '/' and path.endswith('/'):
            path = path[:-1]
        parsed = parsed._replace(path=path)

        return urlunparse(parsed)

    def _should_skip_url(self, url: str) -> bool:
        """Check if URL should be skipped based on extension."""
        if not (self.skip_media or self.skip_binaries):
            return False

        parsed = urlparse(url)
        path = parsed.path.lower()

        for ext in self.SKIP_EXTENSIONS:
            if path.endswith(ext):
                return True

        return False

    def get_domain(self, url: str) -> str:
        """Extract domain from URL."""
        parsed = urlparse(url)
        return parsed.netloc

    def is_same_domain(self, url: str) -> bool:
        """Check if URL is on the same domain as base URL."""
        return self.get_domain(url) == self.parsed_base.netloc

    def is_subdomain(self, url: str) -> bool:
        """Check if URL is a subdomain of the base URL's domain."""
        target_domain = self.get_domain(url)
        base_domain = self.parsed_base.netloc

        # Remove www prefix for comparison
        target_clean = target_domain.replace('www.', '')
        base_clean = base_domain.replace('www.', '')

        return target_clean.endswith('.' + base_clean) or target_clean == base_clean
