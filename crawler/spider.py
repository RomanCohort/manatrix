"""
Core Spider

Async web crawler with depth control, rate limiting, and deduplication.
"""

import asyncio
import time
import logging
from dataclasses import dataclass, field
from typing import List, Dict, Set, Optional, Any, Callable
from urllib.parse import urlparse, urljoin
from collections import defaultdict

try:
    import httpx
except ImportError:
    httpx = None

from .config import CrawlerConfig
from .link_finder import LinkFinder, LinkInfo
from .parser import HTMLParser, ParsedPage
from .technology_detector import TechnologyDetector, TechnologyReport
from .vulnerability_scanner import VulnerabilityScanner, VulnerabilityReport
from .robots_parser import RobotsParser, RobotsInfo
from .sitemap_parser import SitemapParser, SitemapInfo

logger = logging.getLogger(__name__)


@dataclass
class PageData:
    """Data collected from a single crawled page."""
    url: str
    status_code: int
    content_type: Optional[str] = None
    html: Optional[str] = None
    headers: Dict[str, str] = field(default_factory=dict)
    response_time: float = 0.0
    redirect_url: Optional[str] = None
    depth: int = 0
    error: Optional[str] = None

    # Parsed data
    parsed: Optional[ParsedPage] = None
    tech_report: Optional[TechnologyReport] = None
    vuln_report: Optional[VulnerabilityReport] = None

    # Links
    internal_links: List[str] = field(default_factory=list)
    external_links: List[str] = field(default_factory=list)
    forms: List[Any] = field(default_factory=list)
    api_endpoints: List[str] = field(default_factory=list)


@dataclass
class CrawlResult:
    """Complete crawl results."""
    config: CrawlerConfig
    pages: Dict[str, PageData] = field(default_factory=dict)
    start_time: float = 0.0
    end_time: float = 0.0
    urls_crawled: int = 0
    urls_failed: int = 0
    total_links: int = 0
    total_forms: int = 0
    total_emails: Set[str] = field(default_factory=set)
    total_phone_numbers: Set[str] = field(default_factory=set)
    technologies: Dict[str, TechnologyReport] = field(default_factory=dict)
    vulnerabilities: List[Any] = field(default_factory=list)
    sitemap_urls: List[str] = field(default_factory=list)

    @property
    def duration(self) -> float:
        """Total crawl duration in seconds."""
        return self.end_time - self.start_time

    def get_all_urls(self) -> List[str]:
        """Get all discovered URLs."""
        return list(self.pages.keys())

    def get_successful_urls(self) -> List[str]:
        """Get URLs that were successfully crawled."""
        return [url for url, page in self.pages.items()
                if page.status_code and 200 <= page.status_code < 400]

    def get_failed_urls(self) -> List[str]:
        """Get URLs that failed."""
        return [url for url, page in self.pages.items()
                if page.error or (page.status_code and page.status_code >= 400)]

    def get_all_forms(self) -> List[tuple]:
        """Get all discovered forms with their URLs."""
        forms = []
        for url, page in self.pages.items():
            if page.parsed and page.parsed.forms:
                for form in page.parsed.forms:
                    forms.append((url, form))
        return forms

    def get_all_technologies(self) -> Dict[str, List[str]]:
        """Get all detected technologies organized by category."""
        techs = defaultdict(set)
        for url, report in self.technologies.items():
            for tech in report.technologies:
                techs[tech.category].add(tech.name)
        return {k: list(v) for k, v in techs.items()}

    def get_all_vulnerabilities(self) -> List[tuple]:
        """Get all vulnerability findings with their URLs."""
        findings = []
        for url, page in self.pages.items():
            if page.vuln_report:
                for finding in page.vuln_report.findings:
                    findings.append((url, finding))
        return findings

    def to_dict(self) -> dict:
        """Convert results to dictionary for export."""
        return {
            "urls_crawled": self.urls_crawled,
            "urls_failed": self.urls_failed,
            "duration": round(self.duration, 2),
            "total_links": self.total_links,
            "total_forms": self.total_forms,
            "emails": list(self.total_emails),
            "technologies": {
                url: [t.name for t in report.technologies]
                for url, report in self.technologies.items()
            },
            "vulnerabilities": [
                {"url": url, "title": f.title, "severity": f.severity}
                for url, page in self.pages.items()
                if page.vuln_report
                for f in page.vuln_report.findings
            ],
            "pages": {
                url: {
                    "status": page.status_code,
                    "title": page.parsed.title if page.parsed else None,
                    "links": len(page.internal_links),
                    "forms": len(page.forms),
                }
                for url, page in self.pages.items()
            }
        }


class CoreSpider:
    """
    Async web crawler for penetration testing reconnaissance.

    Features:
    - Depth-controlled crawling
    - Rate limiting and request throttling
    - robots.txt and sitemap.xml parsing
    - Technology fingerprinting
    - Vulnerability scanning
    - PII and credential detection
    """

    def __init__(self, config: CrawlerConfig):
        """
        Initialize spider.

        Args:
            config: Crawler configuration
        """
        if httpx is None:
            raise ImportError("httpx is required for crawling: pip install httpx")

        self.config = config
        self.result = CrawlResult(config=config)

        # Internal state
        self._visited: Set[str] = set()
        self._queue: asyncio.Queue = None
        self._robots_parser = RobotsParser()
        self._sitemap_parser = SitemapParser()
        self._tech_detector = TechnologyDetector()
        self._vuln_scanner = VulnerabilityScanner()
        self._html_parser = HTMLParser  # Class reference, instantiated per URL

        # Callbacks
        self._on_page_crawled: Optional[Callable] = None
        self._on_error: Optional[Callable] = None

        # Semaphore for concurrent requests
        self._semaphore = asyncio.Semaphore(config.max_concurrent)

    def on_page_crawled(self, callback: Callable):
        """Register callback for when a page is crawled."""
        self._on_page_crawled = callback

    def on_error(self, callback: Callable):
        """Register callback for errors."""
        self._on_error = callback

    async def crawl(self) -> CrawlResult:
        """
        Start the crawl.

        Returns:
            CrawlResult with all discovered information
        """
        self.result = CrawlResult(config=self.config)
        self.result.start_time = time.time()
        self._visited = set()
        self._queue = asyncio.Queue()

        # Initialize queue with start URLs
        for url in self.config.start_urls:
            await self._queue.put((url, 0))  # (url, depth)

        # Fetch robots.txt and sitemap for each domain
        domains = set()
        for url in self.config.start_urls:
            parsed = urlparse(url)
            if parsed.netloc:
                domains.add(parsed.netloc)

        async with httpx.AsyncClient(
            timeout=httpx.Timeout(self.config.timeout),
            follow_redirects=self.config.follow_redirects,
            max_redirects=self.config.max_redirects,
            verify=self.config.verify_ssl,
            headers={"User-Agent": self.config.user_agent},
            proxy=self.config.proxy_url,
        ) as client:
            self._client = client

            # Pre-crawl: robots.txt and sitemap
            if self.config.respect_robots:
                await self._fetch_robots_txt(domains)

            if self.config.use_sitemap:
                await self._fetch_sitemaps(domains)

            # Main crawl loop
            workers = []
            for _ in range(self.config.max_concurrent):
                workers.append(asyncio.create_task(self._worker()))

            # Wait for all workers to finish
            await asyncio.gather(*workers)

        self.result.end_time = time.time()
        self._client = None

        return self.result

    async def _worker(self):
        """Worker coroutine for processing URLs from queue."""
        while True:
            try:
                # Get URL with timeout
                url, depth = await asyncio.wait_for(
                    self._queue.get(), timeout=30.0
                )
            except asyncio.TimeoutError:
                break

            try:
                await self._process_url(url, depth)
            except Exception as e:
                logger.error(f"Error processing {url}: {e}")
                if self._on_error:
                    self._on_error(url, e)
            finally:
                self._queue.task_done()

    async def _process_url(self, url: str, depth: int):
        """Process a single URL."""
        # Check limits
        if len(self._visited) >= self.config.max_urls:
            return

        if depth > self.config.max_depth:
            return

        # Normalize and check visited
        normalized = self._normalize_url(url)
        if normalized in self._visited:
            return

        # Check if URL is allowed
        if not self.config.is_url_allowed(normalized):
            return

        # Check robots.txt
        if self.config.respect_robots:
            parsed = urlparse(normalized)
            if not self._robots_parser.is_allowed(normalized):
                logger.info(f"Blocked by robots.txt: {normalized}")
                return

        # Rate limiting
        await self._rate_limit()

        # Mark as visited
        self._visited.add(normalized)

        # Fetch page
        page_data = await self._fetch_page(normalized, depth)

        if page_data and page_data.html:
            # Parse HTML
            parser = self._html_parser(normalized)
            page_data.parsed = parser.parse(page_data.html, page_data.headers)

            # Detect technologies
            scripts = [s.src for s in page_data.parsed.scripts if s.src]
            cookies = [c['name'] for c in page_data.parsed.cookies]
            page_data.tech_report = self._tech_detector.detect(
                normalized, page_data.html, page_data.headers, scripts, cookies
            )

            # Scan vulnerabilities
            page_data.vuln_report = self._vuln_scanner.scan(
                normalized, page_data.html, page_data.headers,
                page_data.tech_report, page_data.parsed
            )

            # Extract links
            link_finder = LinkFinder(normalized)
            links = link_finder.extract_links(page_data.html, page_data.content_type or "text/html")

            for link in links:
                if link_finder.is_same_domain(link.url):
                    page_data.internal_links.append(link.url)
                else:
                    page_data.external_links.append(link.url)

            # Extract forms and APIs
            page_data.forms = page_data.parsed.forms
            page_data.api_endpoints = page_data.parsed.api_endpoints

            # Update result
            self.result.total_emails.update(page_data.parsed.emails)
            self.result.total_phone_numbers.update(page_data.parsed.phone_numbers)
            self.result.total_forms += len(page_data.parsed.forms)
            self.result.total_links += len(page_data.internal_links)
            self.result.technologies[normalized] = page_data.tech_report
            self.result.vulnerabilities.extend(
                page_data.vuln_report.findings if page_data.vuln_report else []
            )

            # Queue internal links
            if depth < self.config.max_depth:
                for link_url in page_data.internal_links:
                    link_normalized = self._normalize_url(link_url)
                    if link_normalized not in self._visited:
                        await self._queue.put((link_normalized, depth + 1))

        # Store page data
        self.result.pages[normalized] = page_data
        if page_data.error:
            self.result.urls_failed += 1
        else:
            self.result.urls_crawled += 1

        # Callback
        if self._on_page_crawled:
            self._on_page_crawled(normalized, page_data)

    async def _fetch_page(self, url: str, depth: int) -> Optional[PageData]:
        """Fetch a single page."""
        page = PageData(url=url, depth=depth)

        try:
            start = time.time()
            response = await self._client.get(url)
            page.response_time = time.time() - start
            page.status_code = response.status_code
            page.headers = dict(response.headers)
            page.content_type = response.headers.get('content-type', '')

            # Only store HTML content
            if 'html' in page.content_type or 'xml' in page.content_type:
                page.html = response.text
            elif 'json' in page.content_type:
                page.html = response.text  # Store JSON for API endpoint discovery

        except httpx.TimeoutException as e:
            page.error = f"Timeout: {e}"
        except httpx.ConnectError as e:
            page.error = f"Connection error: {e}"
        except httpx.TooManyRedirects:
            page.error = "Too many redirects"
        except Exception as e:
            page.error = f"Error: {e}"

        return page

    async def _fetch_robots_txt(self, domains: Set[str]):
        """Fetch and parse robots.txt for each domain."""
        for domain in domains:
            robots_url = f"https://{domain}/robots.txt"

            try:
                response = await self._client.get(robots_url)
                if response.status_code == 200:
                    self._robots_parser.parse(robots_url, response.text)
                    logger.info(f"Parsed robots.txt for {domain}")
            except Exception as e:
                logger.debug(f"No robots.txt for {domain}: {e}")

    async def _fetch_sitemaps(self, domains: Set[str]):
        """Fetch and parse sitemaps."""
        for domain in domains:
            sitemaps = self._robots_parser.get_sitemaps(domain)

            if not sitemaps:
                # Try common sitemap locations
                for path in ['/sitemap.xml', '/sitemap_index.xml', '/sitemap-index.xml']:
                    sitemaps.append(f"https://{domain}{path}")

            for sitemap_url in sitemaps:
                try:
                    response = await self._client.get(sitemap_url)
                    if response.status_code == 200:
                        info = self._sitemap_parser.parse(sitemap_url, response.text)

                        if info.sitemap_index:
                            # Fetch child sitemaps
                            for child_url in info.child_sitemaps[:10]:  # Limit
                                try:
                                    child_resp = await self._client.get(child_url)
                                    if child_resp.status_code == 200:
                                        child_info = self._sitemap_parser.parse(child_url, child_resp.text)
                                        self.result.sitemap_urls.extend(
                                            [u.loc for u in child_info.urls[:100]]
                                        )
                                except Exception:
                                    pass
                        else:
                            self.result.sitemap_urls.extend(
                                [u.loc for u in info.urls[:100]]
                            )

                        # Add sitemap URLs to queue
                        for url in self.result.sitemap_urls:
                            if url not in self._visited:
                                await self._queue.put((url, 0))

                except Exception as e:
                    logger.debug(f"Error fetching sitemap {sitemap_url}: {e}")

    async def _rate_limit(self):
        """Apply rate limiting between requests."""
        if self.config.rate_limit > 0:
            await asyncio.sleep(self.config.rate_limit)

    def _normalize_url(self, url: str) -> str:
        """Normalize URL for deduplication."""
        parsed = urlparse(url)

        # Remove fragment
        parsed = parsed._replace(fragment='')

        # Normalize path
        path = parsed.path or '/'
        if path != '/' and path.endswith('/'):
            path = path[:-1]
        parsed = parsed._replace(path=path)

        # Lowercase scheme and netloc
        parsed = parsed._replace(
            scheme=parsed.scheme.lower(),
            netloc=parsed.netloc.lower()
        )

        return parsed.geturl()
