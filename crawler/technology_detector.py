"""
Technology Detector

Fingerprint web technologies, frameworks, and libraries.
"""

import re
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Set
from urllib.parse import urlparse


@dataclass
class Technology:
    """Detected technology."""
    name: str
    category: str  # "framework", "cms", "library", "server", "analytics", etc.
    version: Optional[str] = None
    cpe: Optional[str] = None  # CPE identifier for CVE lookup
    confidence: float = 1.0
    evidence: List[str] = field(default_factory=list)
    cve_prefixes: List[str] = field(default_factory=list)


@dataclass
class TechnologyReport:
    """Complete technology detection report."""
    url: str
    technologies: List[Technology]
    server: Optional[str] = None
    programming_language: Optional[str] = None
    frameworks: List[str] = field(default_factory=list)
    cms: Optional[str] = None
    frontend_libs: List[str] = field(default_factory=list)
    backend_libs: List[str] = field(default_factory=list)
    analytics: List[str] = field(default_factory=list)
    security_headers: Dict[str, str] = field(default_factory=dict)


class TechnologyDetector:
    """Detect web technologies from HTML, headers, and scripts."""

    # Technology signatures database
    SIGNATURES = {
        # Web Servers
        "nginx": {
            "headers": {"server": r"nginx(?:/([\d.]+))?"},
            "category": "server",
            "cpe": "cpe:/a:nginx:nginx",
            "cve_prefix": "nginx"
        },
        "apache": {
            "headers": {"server": r"Apache(?:/([\d.]+))?"},
            "category": "server",
            "cpe": "cpe:/a:apache:http_server",
            "cve_prefix": "apache"
        },
        "iis": {
            "headers": {"server": r"Microsoft-IIS(?:/([\d.]+))?"},
            "category": "server",
            "cpe": "cpe:/a:microsoft:iis",
            "cve_prefix": "iis"
        },
        "cloudflare": {
            "headers": {"server": r"cloudflare", "cf-ray": r".*"},
            "category": "cdn",
            "cve_prefix": "cloudflare"
        },

        # Programming Languages (detected via headers/cookies)
        "php": {
            "headers": {"set-cookie": r"PHPSESSID", "x-powered-by": r"PHP(?:/([\d.]+))?"},
            "category": "language",
            "cpe": "cpe:/a:php:php",
            "cve_prefix": "php"
        },
        "asp.net": {
            "headers": {"x-aspnet-version": r"([\d.]+)", "set-cookie": r"ASP\.NET"},
            "category": "framework",
            "cpe": "cpe:/a:microsoft:asp.net",
            "cve_prefix": "asp.net"
        },
        "java": {
            "headers": {"set-cookie": r"JSESSIONID"},
            "category": "language",
            "cve_prefix": "java"
        },
        "node.js": {
            "headers": {"x-powered-by": r"Express"},
            "html": ["node_modules", "package.json"],
            "category": "runtime",
            "cve_prefix": "node.js"
        },
        "python": {
            "cookies": ["csrftoken"],  # Django
            "category": "language",
            "cve_prefix": "python"
        },

        # Frontend Frameworks
        "react": {
            "html": ["react", "react-dom", "data-reactroot", "__REACT_DEVTOOLS"],
            "scripts": [r"react(?:\.min)?\.js", r"react-dom(?:\.min)?\.js"],
            "category": "framework",
            "cve_prefix": "react"
        },
        "vue.js": {
            "html": ["vue", "__VUE__", "v-cloak", "v-if", "v-for"],
            "scripts": [r"vue(?:\.min)?\.js"],
            "category": "framework",
            "cve_prefix": "vue.js"
        },
        "angular": {
            "html": ["ng-app", "ng-controller", "ng-repeat", "angular"],
            "scripts": [r"angular(?:\.min)?\.js"],
            "category": "framework",
            "cpe": "cpe:/a:angularjs:angular.js",
            "cve_prefix": "angular"
        },
        "svelte": {
            "html": ["__svelte", "svelte"],
            "category": "framework",
            "cve_prefix": "svelte"
        },
        "jquery": {
            "scripts": [r"jquery(?:-[\d.]+)?(?:\.min)?\.js"],
            "html": ["jquery"],
            "category": "library",
            "cve_prefix": "jquery"
        },
        "bootstrap": {
            "html": ["bootstrap", "btn-", "container-fluid", "navbar-"],
            "scripts": [r"bootstrap(?:\.min)?\.js"],
            "css": [r"bootstrap(?:\.min)?\.css"],
            "category": "library",
            "cve_prefix": "bootstrap"
        },
        "tailwindcss": {
            "html": [r'class="[^"]*\b(flex|grid|bg-|text-|p-|m-|w-|h-)\b'],
            "category": "library",
            "cve_prefix": "tailwind"
        },

        # Meta Frameworks
        "next.js": {
            "html": ["_next/static", "__NEXT_DATA__", "next/dist"],
            "category": "framework",
            "cpe": "cpe:/a:vercel:next.js",
            "cve_prefix": "next.js"
        },
        "nuxt.js": {
            "html": ["__NUXT__", "_nuxt/"],
            "category": "framework",
            "cve_prefix": "nuxt"
        },
        "gatsby": {
            "html": ["gatsby", "gatsby-image"],
            "category": "framework",
            "cve_prefix": "gatsby"
        },

        # Backend Frameworks
        "django": {
            "html": ["csrfmiddlewaretoken", "django"],
            "cookies": ["csrftoken", "sessionid"],
            "category": "framework",
            "cpe": "cpe:/a:djangoproject:django",
            "cve_prefix": "django"
        },
        "flask": {
            "cookies": ["session"],
            "category": "framework",
            "cve_prefix": "flask"
        },
        "ruby on rails": {
            "headers": {"x-runtime": r".*", "x-powered-by": r"Phusion Passenger"},
            "cookies": ["_session_id"],
            "html": ["rails", "csrf-token"],
            "category": "framework",
            "cpe": "cpe:/a:rubyonrails:ruby_on_rails",
            "cve_prefix": "rails"
        },
        "spring": {
            "html": ["spring", "springframework"],
            "headers": {"set-cookie": r"JSESSIONID"},
            "category": "framework",
            "cpe": "cpe:/a:springsource:spring_framework",
            "cve_prefix": "spring"
        },
        "laravel": {
            "cookies": ["laravel_session", "XSRF-TOKEN"],
            "html": ["laravel"],
            "category": "framework",
            "cpe": "cpe:/a:laravel:laravel",
            "cve_prefix": "laravel"
        },
        "express": {
            "headers": {"x-powered-by": r"Express"},
            "category": "framework",
            "cve_prefix": "express"
        },

        # CMS
        "wordpress": {
            "html": ["wp-content", "wp-includes", "wp-json", "wordpress"],
            "meta": {"generator": r"WordPress(?:\s+([\d.]+))?"},
            "category": "cms",
            "cpe": "cpe:/a:wordpress:wordpress",
            "cve_prefix": "wordpress"
        },
        "drupal": {
            "html": ["drupal", "sites/default/files"],
            "meta": {"generator": r"Drupal\s+([\d.]+)"},
            "headers": {"x-drupal-cache": r".*"},
            "category": "cms",
            "cpe": "cpe:/a:drupal:drupal",
            "cve_prefix": "drupal"
        },
        "joomla": {
            "html": ["joomla", "/administrator/"],
            "meta": {"generator": r"Joomla(?:!)?(?:\s+([\d.]+))?"},
            "category": "cms",
            "cpe": r"cpe:/a:joomla:joomla!",
            "cve_prefix": "joomla"
        },
        "magento": {
            "html": ["magento", "/mage/"],
            "category": "cms",
            "cpe": "cpe:/a:magento:magento",
            "cve_prefix": "magento"
        },
        "shopify": {
            "html": ["shopify", "cdn.shopify.com"],
            "headers": {"x-shopify": r".*"},
            "category": "cms",
            "cve_prefix": "shopify"
        },

        # Analytics & Tracking
        "google-analytics": {
            "html": ["google-analytics.com", "gtag", r"ga\("],
            "category": "analytics"
        },
        "google-tag-manager": {
            "html": ["googletagmanager.com", "GTM-"],
            "category": "analytics"
        },
        "facebook-pixel": {
            "html": ["connect.facebook.net", r"fbq\("],
            "category": "analytics"
        },
        "hotjar": {
            "html": ["hotjar.com", r"hj\("],
            "category": "analytics"
        },

        # Security
        "cloudflare": {
            "headers": {"cf-ray": r".*", "cf-cache-status": r".*"},
            "category": "security"
        },
        "akamai": {
            "headers": {"x-akamai-transformed": r".*"},
            "category": "cdn"
        },
        "incapsula": {
            "headers": {"x-cdn": r"Incapsula"},
            "cookies": ["incap_ses_", "visid_incap_"],
            "category": "security"
        },

        # Databases (detected via error messages)
        "mysql": {
            "html": [r"mysql_fetch", r"mysql_query", r"MySQLSyntaxErrorException"],
            "category": "database",
            "cve_prefix": "mysql"
        },
        "postgresql": {
            "html": [r"pg_query", r"PostgreSQL.*ERROR", r"pg_connect"],
            "category": "database",
            "cve_prefix": "postgresql"
        },
        "mongodb": {
            "html": [r"MongoDB", r"mongoClient", r"ObjectId\("],
            "category": "database",
            "cve_prefix": "mongodb"
        },
        "redis": {
            "html": [r"Redis", r"redis-cli"],
            "category": "database",
            "cve_prefix": "redis"
        },

        # Build Tools
        "webpack": {
            "html": ["webpack", "__webpack_require__", "webpackJsonp"],
            "category": "build",
            "cve_prefix": "webpack"
        },
        "vite": {
            "html": ["vite", "/vite/"],
            "category": "build",
            "cve_prefix": "vite"
        },
    }

    def __init__(self):
        """Initialize technology detector."""
        self.detected: Dict[str, Technology] = {}

    def detect(self, url: str, html: str, headers: Dict[str, str],
               scripts: List[str] = None, cookies: List[str] = None) -> TechnologyReport:
        """
        Detect technologies from page content.

        Args:
            url: Page URL
            html: HTML content
            headers: HTTP response headers
            scripts: List of script URLs
            cookies: List of cookie names

        Returns:
            TechnologyReport with detected technologies
        """
        self.detected = {}
        scripts = scripts or []
        cookies = cookies or []

        # Normalize headers to lowercase
        headers_lower = {k.lower(): v for k, v in headers.items()}

        # Check each technology signature
        for tech_name, signatures in self.SIGNATURES.items():
            self._check_technology(tech_name, signatures, html, headers_lower, scripts, cookies)

        # Build report
        return self._build_report(url, headers_lower)

    def _check_technology(self, tech_name: str, signatures: dict,
                          html: str, headers: dict,
                          scripts: List[str], cookies: List[str]):
        """Check for a specific technology."""
        evidence = []
        version = None

        # Check headers
        if "headers" in signatures:
            for header, pattern in signatures["headers"].items():
                header_lower = header.lower()
                if header_lower in headers:
                    match = re.search(pattern, headers[header_lower], re.IGNORECASE)
                    if match:
                        evidence.append(f"Header: {header}")
                        if match.groups():
                            version = match.group(1)

        # Check HTML patterns
        if "html" in signatures:
            for pattern in signatures["html"]:
                if isinstance(pattern, str):
                    if pattern.lower() in html.lower():
                        evidence.append(f"HTML pattern: {pattern[:30]}")
                else:  # regex
                    if re.search(pattern, html, re.IGNORECASE):
                        evidence.append(f"HTML regex match")

        # Check meta tags
        if "meta" in signatures:
            for meta_name, pattern in signatures["meta"].items():
                meta_pattern = rf'<meta[^>]+name=["\']?{meta_name}["\']?[^>]+content=["\']([^"\']+)["\']'
                match = re.search(meta_pattern, html, re.IGNORECASE)
                if match:
                    content = match.group(1)
                    if re.search(pattern, content, re.IGNORECASE):
                        evidence.append(f"Meta: {meta_name}")
                        version_match = re.search(pattern, content)
                        if version_match and version_match.groups():
                            version = version_match.group(1)

        # Check scripts
        if "scripts" in signatures:
            for pattern in signatures["scripts"]:
                for script in scripts:
                    if re.search(pattern, script, re.IGNORECASE):
                        evidence.append(f"Script: {script[:50]}")

        # Check cookies
        if "cookies" in signatures:
            for pattern in signatures["cookies"]:
                if isinstance(pattern, str):
                    if pattern in cookies:
                        evidence.append(f"Cookie: {pattern}")
                else:  # regex
                    for cookie in cookies:
                        if re.search(pattern, cookie, re.IGNORECASE):
                            evidence.append(f"Cookie: {cookie}")

        # If evidence found, add to detected
        if evidence:
            category = signatures.get("category", "unknown")
            cpe = signatures.get("cpe")
            cve_prefix = signatures.get("cve_prefix", [])

            # Build CPE with version
            if cpe and version:
                cpe = f"{cpe}:{version}"

            self.detected[tech_name] = Technology(
                name=tech_name,
                category=category,
                version=version,
                cpe=cpe,
                confidence=min(1.0, len(evidence) * 0.3 + 0.4),
                evidence=evidence,
                cve_prefixes=[cve_prefix] if isinstance(cve_prefix, str) else cve_prefix
            )

    def _build_report(self, url: str, headers: dict) -> TechnologyReport:
        """Build final report from detected technologies."""
        techs = list(self.detected.values())

        # Categorize
        frameworks = [t.name for t in techs if t.category == "framework"]
        cms = next((t.name for t in techs if t.category == "cms"), None)
        frontend_libs = [t.name for t in techs if t.category in ("library", "analytics")]
        backend_libs = [t.name for t in techs if t.category in ("framework", "database")]
        analytics = [t.name for t in techs if t.category == "analytics"]
        server = next((t.name for t in techs if t.category == "server"), None)
        language = next((t.name for t in techs if t.category == "language"), None)

        # Check security headers
        security_headers = {}
        security_header_names = [
            "strict-transport-security",
            "content-security-policy",
            "x-frame-options",
            "x-xss-protection",
            "x-content-type-options",
            "referrer-policy",
            "permissions-policy",
        ]
        for header in security_header_names:
            if header in headers:
                security_headers[header] = headers[header]

        return TechnologyReport(
            url=url,
            technologies=techs,
            server=server,
            programming_language=language,
            frameworks=frameworks,
            cms=cms,
            frontend_libs=frontend_libs,
            backend_libs=backend_libs,
            analytics=analytics,
            security_headers=security_headers
        )

    def get_cve_search_terms(self, report: TechnologyReport) -> List[str]:
        """
        Get CVE search terms from detected technologies.

        Args:
            report: Technology detection report

        Returns:
            List of search terms for CVE lookup
        """
        terms = []
        for tech in report.technologies:
            if tech.cve_prefixes:
                terms.extend(tech.cve_prefixes)
            if tech.cpe:
                terms.append(tech.cpe)
            if tech.version:
                terms.append(f"{tech.name} {tech.version}")

        return list(set(terms))
