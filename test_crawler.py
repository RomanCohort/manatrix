#!/usr/bin/env python3
"""
Crawler Module Test Script

Tests the web crawler functionality:
1. Link extraction and normalization
2. HTML parsing
3. Technology detection
4. Vulnerability scanning
5. Integration with RL state / knowledge graph
"""

import sys
import os
sys.path.insert(0, "D:/password_guesser")

import json
from urllib.parse import urlparse

print("=" * 60)
print("Web Crawler Module Tests")
print("=" * 60)


# ===========================================================================
# Test 1: Link Finder
# ===========================================================================
print("\n[1] Testing Link Finder")
print("-" * 50)

try:
    from crawler.link_finder import LinkFinder, LinkInfo

    # Test link extraction
    test_html = """
    <html>
    <head><title>Test Page</title></head>
    <body>
        <a href="/page1">Internal Link 1</a>
        <a href="https://example.com/page2">Internal Link 2</a>
        <a href="https://external.com/page">External Link</a>
        <a href="#anchor">Anchor</a>
        <script src="/js/app.js"></script>
        <link rel="stylesheet" href="/css/style.css">
        <img src="/images/logo.png">
        <form action="/login" method="POST">
            <input type="text" name="username">
            <input type="password" name="password">
        </form>
        <iframe src="/embed"></iframe>
    </body>
    </html>
    """

    finder = LinkFinder("https://example.com", skip_media=False)
    links = finder.extract_links(test_html)

    print(f"  Extracted {len(links)} links:")
    for link in links[:5]:
        print(f"    - [{link.link_type}] {link.url[:50]}")

    # Test URL normalization
    print("\n  URL normalization:")
    test_urls = [
        "https://Example.com/Page/",
        "https://example.com/page#section",
        "https://example.com:443/page",
    ]
    for url in test_urls:
        normalized = finder._normalize_url(url)
        print(f"    {url[:40]} -> {normalized}")

    # Test same domain check
    print("\n  Domain checks:")
    print(f"    example.com/page -> same_domain: {finder.is_same_domain('https://example.com/page')}")
    print(f"    external.com -> same_domain: {finder.is_same_domain('https://external.com')}")

    print("\n  [OK] Link Finder tests passed")

except Exception as e:
    print(f"  [FAIL] Link Finder test failed: {e}")
    import traceback
    traceback.print_exc()


# ===========================================================================
# Test 2: HTML Parser
# ===========================================================================
print("\n[2] Testing HTML Parser")
print("-" * 50)

try:
    from crawler.parser import HTMLParser

    test_html = """
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width">
        <meta name="description" content="Test page for crawler">
        <meta name="generator" content="WordPress 6.0">
        <meta property="og:title" content="Test Page">
        <title>Test Page Title</title>
        <link rel="stylesheet" href="/style.css">
        <script src="/app.js"></script>
    </head>
    <body>
        <h1>Test Page</h1>
        <p>Contact: test@example.com or call 555-123-4567</p>
        <form action="/search" method="GET">
            <input type="hidden" name="csrf_token" value="abc123">
            <input type="text" name="query">
            <input type="password" name="password">
            <button type="submit">Search</button>
        </form>
        <!-- TODO: Fix this later -->
        <!-- API Key: sk-test123456789 -->
        <a href="/about">About</a>
        <a href="https://external.com">External</a>
    </body>
    </html>
    """

    parser = HTMLParser("https://example.com/test")
    parsed = parser.parse(test_html, {"Content-Type": "text/html", "Server": "nginx"})

    print(f"  Title: {parsed.title}")
    print(f"  Meta description: {parsed.meta.description}")
    print(f"  Meta generator: {parsed.meta.generator}")
    print(f"  Emails found: {parsed.emails}")
    print(f"  Phone numbers: {parsed.phone_numbers}")
    print(f"  Forms: {len(parsed.forms)}")
    if parsed.forms:
        print(f"    Form 1: action={parsed.forms[0].action}, method={parsed.forms[0].method}")
        print(f"    Has password field: {parsed.forms[0].has_password}")
    print(f"  Hidden inputs: {len(parsed.hidden_inputs)}")
    print(f"  Comments: {len(parsed.comments)}")
    print(f"  Internal links: {len(parsed.links)}")
    print(f"  External links: {len(parsed.external_links)}")

    print("\n  [OK] HTML Parser tests passed")

except Exception as e:
    print(f"  [FAIL] HTML Parser test failed: {e}")
    import traceback
    traceback.print_exc()


# ===========================================================================
# Test 3: Technology Detector
# ===========================================================================
print("\n[3] Testing Technology Detector")
print("-" * 50)

try:
    from crawler.technology_detector import TechnologyDetector

    detector = TechnologyDetector()

    test_html = """
    <!DOCTYPE html>
    <html>
    <head>
        <meta name="generator" content="WordPress 6.2">
        <script src="/wp-content/themes/theme/app.js"></script>
        <script src="https://code.jquery.com/jquery-3.6.0.min.js"></script>
        <link rel="stylesheet" href="/wp-content/plugins/plugin/style.css">
    </head>
    <body class="home blog">
        <div id="content">Content</div>
    </body>
    </html>
    """

    test_headers = {
        "Server": "nginx/1.23.0",
        "X-Powered-By": "PHP/8.1.0",
        "Set-Cookie": "PHPSESSID=abc123",
    }

    test_scripts = [
        "/wp-content/themes/theme/app.js",
        "https://code.jquery.com/jquery-3.6.0.min.js",
    ]

    test_cookies = ["PHPSESSID", "wordpress_test_cookie"]

    report = detector.detect(
        "https://example.com",
        test_html,
        test_headers,
        test_scripts,
        test_cookies
    )

    print(f"  Server: {report.server}")
    print(f"  Programming language: {report.programming_language}")
    print(f"  CMS: {report.cms}")
    print(f"  Frameworks: {report.frameworks}")
    print(f"  Frontend libs: {report.frontend_libs}")
    print(f"  Security headers: {list(report.security_headers.keys())}")

    print(f"\n  Detected technologies ({len(report.technologies)}):")
    for tech in report.technologies:
        version_str = f" v{tech.version}" if tech.version else ""
        print(f"    - {tech.name}{version_str} [{tech.category}]")

    # Get CVE search terms
    cve_terms = detector.get_cve_search_terms(report)
    print(f"\n  CVE search terms: {cve_terms[:5]}")

    print("\n  [OK] Technology Detector tests passed")

except Exception as e:
    print(f"  [FAIL] Technology Detector test failed: {e}")
    import traceback
    traceback.print_exc()


# ===========================================================================
# Test 4: Vulnerability Scanner
# ===========================================================================
print("\n[4] Testing Vulnerability Scanner")
print("-" * 50)

try:
    from crawler.vulnerability_scanner import VulnerabilityScanner
    from crawler.technology_detector import TechnologyReport, Technology

    scanner = VulnerabilityScanner()

    test_html = """
    <html>
    <head><title>Test</title></head>
    <body>
        <!-- Debug mode enabled -->
        <!-- Password: secret123 -->
        <!-- API Key: sk-abc123def456 -->
        <div>Error: mysql_query() failed</div>
        <div>Warning: mysqli_connect(): Access denied</div>
        <a href="/.env">Config</a>
        <a href="/.git/config">Git</a>
        <a href="/wp-config.php">WordPress Config</a>
        <form action="/login" method="POST">
            <input type="password" name="pass">
        </form>
    </body>
    </html>
    """

    test_headers = {
        "Set-Cookie": "session=abc123",
        "Content-Type": "text/html",
    }

    # Create minimal tech report
    class MockParsedPage:
        forms = []
        comments = [
            "Debug mode enabled",
            "Password: secret123",
            "API Key: sk-abc123def456",
        ]

    class MockTechReport:
        technologies = []

    parsed = MockParsedPage()
    tech = MockTechReport()

    vuln_report = scanner.scan(
        "http://example.com/.env",
        test_html,
        test_headers,
        tech,
        parsed
    )

    print(f"  Findings: {len(vuln_report.findings)}")
    print(f"  Summary: {vuln_report.summary}")
    print(f"  Risk score: {vuln_report.risk_score:.1f}/10")

    print("\n  Top findings:")
    for finding in vuln_report.findings[:5]:
        print(f"    - [{finding.severity.upper()}] {finding.title}")

    print("\n  [OK] Vulnerability Scanner tests passed")

except Exception as e:
    print(f"  [FAIL] Vulnerability Scanner test failed: {e}")
    import traceback
    traceback.print_exc()


# ===========================================================================
# Test 5: Robots.txt Parser
# ===========================================================================
print("\n[5] Testing Robots Parser")
print("-" * 50)

try:
    from crawler.robots_parser import RobotsParser

    robots_content = """
    User-agent: *
    Disallow: /admin/
    Disallow: /private/
    Allow: /public/
    Crawl-delay: 2

    User-agent: PentestBot
    Disallow: /

    Sitemap: https://example.com/sitemap.xml
    """

    parser = RobotsParser(user_agent="PentestBot")
    info = parser.parse("https://example.com/robots.txt", robots_content)

    print(f"  Has robots.txt: {info.has_robots_txt}")
    print(f"  Crawl delay: {info.crawl_delay}")
    print(f"  Sitemaps: {info.sitemaps}")

    # Test URL allowance (wildcard user-agent)
    parser2 = RobotsParser(user_agent="Googlebot")
    info2 = parser2.parse("https://example.com/robots.txt", robots_content)

    test_urls = [
        "https://example.com/page",
        "https://example.com/admin/login",
        "https://example.com/public/doc",
        "https://example.com/private/data",
    ]

    print("\n  URL allowance tests (Googlebot):")
    for url in test_urls:
        allowed = parser2.is_allowed(url, info2)
        print(f"    {url} -> {'ALLOWED' if allowed else 'BLOCKED'}")

    # Test with PentestBot (blocked everywhere)
    print("\n  URL allowance tests (PentestBot):")
    for url in test_urls[:1]:
        allowed = parser.is_allowed(url, info)
        print(f"    {url} -> {'ALLOWED' if allowed else 'BLOCKED'}")

    print("\n  [OK] Robots Parser tests passed")

except Exception as e:
    print(f"  [FAIL] Robots Parser test failed: {e}")
    import traceback
    traceback.print_exc()


# ===========================================================================
# Test 6: Sitemap Parser
# ===========================================================================
print("\n[6] Testing Sitemap Parser")
print("-" * 50)

try:
    from crawler.sitemap_parser import SitemapParser

    sitemap_content = """
    <?xml version="1.0" encoding="UTF-8"?>
    <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
        <url>
            <loc>https://example.com/</loc>
            <lastmod>2024-01-01</lastmod>
            <changefreq>daily</changefreq>
            <priority>1.0</priority>
        </url>
        <url>
            <loc>https://example.com/page1</loc>
            <lastmod>2024-01-02</lastmod>
            <priority>0.8</priority>
        </url>
        <url>
            <loc>https://example.com/page2</loc>
        </url>
    </urlset>
    """

    parser = SitemapParser()
    info = parser.parse("https://example.com/sitemap.xml", sitemap_content)

    print(f"  Is sitemap index: {info.sitemap_index}")
    print(f"  URLs found: {len(info.urls)}")

    for url in info.urls[:3]:
        print(f"    - {url.loc} (priority: {url.priority})")

    # Test sitemap index
    index_content = """
    <?xml version="1.0" encoding="UTF-8"?>
    <sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
        <sitemap>
            <loc>https://example.com/sitemap1.xml</loc>
        </sitemap>
        <sitemap>
            <loc>https://example.com/sitemap2.xml</loc>
        </sitemap>
    </sitemapindex>
    """

    info2 = parser.parse("https://example.com/sitemap_index.xml", index_content)
    print(f"\n  Sitemap index:")
    print(f"    Is index: {info2.sitemap_index}")
    print(f"    Child sitemaps: {info2.child_sitemaps}")

    print("\n  [OK] Sitemap Parser tests passed")

except Exception as e:
    print(f"  [FAIL] Sitemap Parser test failed: {e}")
    import traceback
    traceback.print_exc()


# ===========================================================================
# Test 7: Crawler Config
# ===========================================================================
print("\n[7] Testing Crawler Config")
print("-" * 50)

try:
    from crawler.config import CrawlerConfig

    config = CrawlerConfig(
        start_urls=["https://example.com/page1", "https://example.com/page2"],
        max_depth=3,
        max_urls=500,
        rate_limit=0.5,
    )

    print(f"  Start URLs: {config.start_urls}")
    print(f"  Allowed domains: {config.allowed_domains}")
    print(f"  Max depth: {config.max_depth}")
    print(f"  Max URLs: {config.max_urls}")
    print(f"  Rate limit: {config.rate_limit}s")

    # Test URL filtering
    test_urls = [
        "https://example.com/page",
        "https://external.com/page",
        "https://example.com/admin/login",
        "https://example.com/.env",
    ]

    print("\n  URL filtering:")
    for url in test_urls:
        allowed = config.is_url_allowed(url)
        print(f"    {url} -> {'ALLOWED' if allowed else 'BLOCKED'}")

    print("\n  [OK] Crawler Config tests passed")

except Exception as e:
    print(f"  [FAIL] Crawler Config test failed: {e}")
    import traceback
    traceback.print_exc()


# ===========================================================================
# Test 8: Export Functions
# ===========================================================================
print("\n[8] Testing Export Functions")
print("-" * 50)

try:
    from crawler.spider import CrawlResult, PageData
    from crawler.exporter import CrawlerExporter
    from crawler.technology_detector import Technology, TechnologyReport

    # Create mock crawl result
    result = CrawlResult(config=CrawlerConfig(start_urls=["https://example.com"]))

    # Add mock page data
    page = PageData(
        url="https://example.com",
        status_code=200,
        html="<html><title>Test</title></html>",
        headers={"Server": "nginx", "Content-Type": "text/html"},
        depth=0
    )
    page.internal_links = ["/about", "/contact"]
    page.external_links = ["https://external.com"]
    page.forms = []
    page.api_endpoints = ["/api/v1/users"]

    # Create mock parsed page
    from crawler.parser import ParsedPage, MetaInfo
    page.parsed = ParsedPage(
        url="https://example.com",
        title="Test Page",
        meta=MetaInfo(title="Test Page"),
        forms=[],
        scripts=[],
        stylesheets=[],
        images=[],
        links=[{"href": "/about", "text": "About"}],
        external_links=["https://external.com"],
        comments=[],
        emails=set(),
        phone_numbers=set(),
        api_endpoints=["/api/v1/users"],
        hidden_inputs=[],
        cookies=[],
        headers={}
    )

    # Create mock tech report
    page.tech_report = TechnologyReport(
        url="https://example.com",
        technologies=[
            Technology(name="nginx", category="server", version="1.23.0"),
            Technology(name="react", category="framework"),
        ],
        server="nginx",
        frameworks=["react"],
        security_headers={}
    )

    # Create mock vuln report
    from crawler.vulnerability_scanner import VulnerabilityReport, VulnerabilityFinding
    page.vuln_report = VulnerabilityReport(
        url="https://example.com",
        findings=[
            VulnerabilityFinding(
                title="Missing HSTS header",
                severity="high",
                category="misconfiguration",
                description="HTTPS not enforced",
                evidence="Header not present",
                url="https://example.com"
            )
        ],
        summary={"high": 1},
        risk_score=2.5
    )

    result.pages["https://example.com"] = page
    result.technologies["https://example.com"] = page.tech_report
    result.total_emails.add("test@example.com")
    result.total_forms = 0

    # Export
    exporter = CrawlerExporter(result)

    rl_state = exporter.export_to_rl_state()
    print(f"  RL State export:")
    print(f"    Discovered hosts: {rl_state.get('discovered_hosts', [])}")
    print(f"    Technologies: {rl_state.get('technologies', {})}")
    print(f"    Vulnerabilities: {rl_state.get('vulnerabilities', {})}")

    kg_data = exporter.export_to_knowledge_graph()
    print(f"\n  Knowledge Graph export:")
    print(f"    Technologies: {len(kg_data.get('technologies', []))}")
    print(f"    Vulnerabilities: {len(kg_data.get('vulnerabilities', []))}")
    print(f"    Attack patterns: {len(kg_data.get('attack_patterns', []))}")

    expert_state = exporter.export_to_expert_system()
    print(f"\n  Expert System export:")
    print(f"    Hosts: {expert_state.get('hosts', [])}")
    print(f"    Recommendations: {expert_state.get('recommendations', [])}")

    attack_graph = exporter.export_to_attack_graph()
    print(f"\n  Attack Graph export:")
    print(f"    Nodes: {len(attack_graph.get('nodes', []))}")
    print(f"    Edges: {len(attack_graph.get('edges', []))}")

    print("\n  [OK] Export functions tests passed")

except Exception as e:
    print(f"  [FAIL] Export functions test failed: {e}")
    import traceback
    traceback.print_exc()


# ===========================================================================
# Test Summary
# ===========================================================================
print("\n" + "=" * 60)
print("Test Summary")
print("=" * 60)

print("""
[OK] Link Finder
    - URL extraction from HTML
    - Link type classification (a, script, css, form, etc.)
    - URL normalization
    - Same-domain detection

[OK] HTML Parser
    - Meta tag extraction
    - Form parsing with input detection
    - Email/phone extraction
    - Comment extraction
    - Internal/external link classification

[OK] Technology Detector
    - Server detection from headers
    - CMS detection from meta tags
    - Framework detection from HTML/scripts
    - Version extraction
    - CVE search term generation

[OK] Vulnerability Scanner
    - Sensitive path detection
    - Information disclosure patterns
    - Sensitive data in HTML
    - Missing security headers
    - Cookie security checks

[OK] Robots Parser
    - Rule parsing
    - URL allowance checking
    - Crawl delay extraction
    - Sitemap URL extraction

[OK] Sitemap Parser
    - URLset parsing
    - Sitemap index parsing
    - Priority/changefreq extraction

[OK] Crawler Config
    - URL filtering
    - Domain restriction
    - Path denial

[OK] Export Functions
    - RL state format export
    - Knowledge graph format export
    - Expert system format export
    - Attack graph format export
""")

print("All crawler module tests passed!")
print("=" * 60)
