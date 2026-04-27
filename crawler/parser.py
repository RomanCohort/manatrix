"""
HTML Parser

Parse HTML content and extract structured information.
"""

import re
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Set, Tuple
from urllib.parse import urlparse


@dataclass
class FormData:
    """Extracted form information."""
    action: str
    method: str
    inputs: List[Dict[str, str]]
    has_file_upload: bool = False
    has_password: bool = False
    enctype: Optional[str] = None


@dataclass
class MetaInfo:
    """Extracted meta tag information."""
    title: Optional[str] = None
    description: Optional[str] = None
    keywords: List[str] = field(default_factory=list)
    generator: Optional[str] = None
    author: Optional[str] = None
    robots: Optional[str] = None
    viewport: Optional[str] = None
    charset: Optional[str] = None
    content_type: Optional[str] = None
    refresh: Optional[Tuple[int, Optional[str]]] = None  # (seconds, url)
    og_tags: Dict[str, str] = field(default_factory=dict)


@dataclass
class ScriptInfo:
    """Extracted script information."""
    src: Optional[str]
    content: Optional[str]
    script_type: Optional[str]
    is_inline: bool
    has_external_api: bool = False
    frameworks: List[str] = field(default_factory=list)


@dataclass
class ParsedPage:
    """Parsed HTML page with extracted information."""
    url: str
    title: Optional[str]
    meta: MetaInfo
    forms: List[FormData]
    scripts: List[ScriptInfo]
    stylesheets: List[str]
    images: List[Dict[str, str]]
    links: List[Dict[str, str]]  # internal links
    external_links: List[str]
    comments: List[str]
    emails: Set[str]
    phone_numbers: Set[str]
    api_endpoints: List[str]
    hidden_inputs: List[Dict[str, str]]
    cookies: List[Dict[str, str]]
    headers: Dict[str, str]


class HTMLParser:
    """Parse HTML content and extract reconnaissance data."""

    # Patterns for sensitive data extraction
    EMAIL_PATTERN = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    PHONE_PATTERN = r'(?:\+\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}'
    API_PATTERN = r'["\']/(api|v\d+|graphql|rest)[^"\']*["\']'

    # Patterns for API endpoints in JavaScript
    API_ENDPOINT_PATTERNS = [
        r'["\']/(api/v\d+/[\w/]+)["\']',
        r'["\']/(api/[\w/]+)["\']',
        r'["\']/(graphql)["\']',
        r'fetch\(["\']([^"\']+)["\']',
        r'axios\.[a-z]+\(["\']([^"\']+)["\']',
        r'\$\.ajax\([^)]*url:\s*["\']([^"\']+)["\']',
    ]

    # Framework detection patterns
    FRAMEWORK_SIGNATURES = {
        'react': [r'react\.min\.js', r'react-dom', r'__REACT_DEVTOOLS', r'data-reactroot'],
        'vue': [r'vue\.min\.js', r'vue-router', r'__VUE__', r'v-cloak'],
        'angular': [r'angular\.min\.js', r'ng-app', r'ng-controller', r'ng-repeat'],
        'jquery': [r'jquery', r'\$\(', r'jQuery'],
        'bootstrap': [r'bootstrap\.min', r'btn-', r'container-fluid', 'navbar-'],
        'tailwind': [r'tailwind', r'class="[^"]*\b(flex|grid|bg-|text-|p-|m-)\b'],
        'nextjs': [r'_next/static', r'__NEXT_DATA__', r'next/dist'],
        'nuxt': [r'__NUXT__', r'_nuxt/'],
        'svelte': [r'svelte', r'__svelte'],
        'ember': [r'ember\.min', r'Ember\.Application'],
        'backbone': [r'backbone\.min', r'Backbone\.Router'],
        'lodash': [r'lodash', r'_\.\w+'],
        'axios': [r'axios'],
        'webpack': [r'webpack', r'__webpack_require__'],
    }

    def __init__(self, url: str):
        """
        Initialize HTML parser.

        Args:
            url: URL of the page being parsed
        """
        self.url = url
        self.parsed_url = urlparse(url)

    def parse(self, html: str, headers: Optional[Dict[str, str]] = None) -> ParsedPage:
        """
        Parse HTML content.

        Args:
            html: HTML content
            headers: HTTP response headers

        Returns:
            ParsedPage with extracted information
        """
        meta = self._extract_meta(html)
        forms = self._extract_forms(html)
        scripts = self._extract_scripts(html)
        stylesheets = self._extract_stylesheets(html)
        images = self._extract_images(html)
        links = self._extract_links(html)
        external_links = self._extract_external_links(html)
        comments = self._extract_comments(html)
        emails = self._extract_emails(html)
        phone_numbers = self._extract_phones(html)
        api_endpoints = self._extract_api_endpoints(html)
        hidden_inputs = self._extract_hidden_inputs(html)
        cookies = self._parse_cookies(headers.get('set-cookie', '') if headers else '')

        return ParsedPage(
            url=self.url,
            title=meta.title,
            meta=meta,
            forms=forms,
            scripts=scripts,
            stylesheets=stylesheets,
            images=images,
            links=links,
            external_links=external_links,
            comments=comments,
            emails=emails,
            phone_numbers=phone_numbers,
            api_endpoints=api_endpoints,
            hidden_inputs=hidden_inputs,
            cookies=cookies,
            headers=headers or {}
        )

    def _extract_meta(self, html: str) -> MetaInfo:
        """Extract meta tag information."""
        meta = MetaInfo()

        # Title
        title_match = re.search(r'<title[^>]*>([^<]*)</title>', html, re.IGNORECASE)
        if title_match:
            meta.title = title_match.group(1).strip()

        # Meta tags
        meta_pattern = r'<meta[^>]+(?:name|property|http-equiv)=["\']([^"\']+)["\'][^>]*(?:content=["\']([^"\']*)["\'])?'

        for match in re.finditer(meta_pattern, html, re.IGNORECASE):
            name, content = match.groups()
            if not content:
                # Try alternate format
                content_match = re.search(r'content=["\']([^"\']*)["\']', match.group(0))
                content = content_match.group(1) if content_match else ''

            name = name.lower()
            content = content.strip() if content else ''

            if name == 'description':
                meta.description = content
            elif name == 'keywords':
                meta.keywords = [k.strip() for k in content.split(',')]
            elif name == 'generator':
                meta.generator = content
            elif name == 'author':
                meta.author = content
            elif name == 'robots':
                meta.robots = content
            elif name == 'viewport':
                meta.viewport = content
            elif name == 'charset':
                meta.charset = content
            elif name == 'content-type':
                meta.content_type = content
            elif name == 'refresh' and content:
                # Parse refresh: "5; url=/redirect"
                parts = content.split(';')
                try:
                    seconds = int(parts[0])
                    url = None
                    if len(parts) > 1:
                        url_match = re.search(r'url=(.+)', parts[1], re.IGNORECASE)
                        url = url_match.group(1).strip() if url_match else None
                    meta.refresh = (seconds, url)
                except ValueError:
                    pass
            elif name.startswith('og:'):
                meta.og_tags[name] = content

        # Charset from <meta charset="...">
        charset_match = re.search(r'<meta[^>]+charset=["\']([^"\']+)["\']', html, re.IGNORECASE)
        if charset_match:
            meta.charset = charset_match.group(1)

        return meta

    def _extract_forms(self, html: str) -> List[FormData]:
        """Extract form information."""
        forms = []

        # Find all form tags
        form_pattern = r'<form[^>]*>(.*?)</form>'
        for form_match in re.finditer(form_pattern, html, re.IGNORECASE | re.DOTALL):
            form_html = form_match.group(0)

            # Extract form attributes
            action = self._get_attr(form_html, 'action') or ''
            method = (self._get_attr(form_html, 'method') or 'GET').upper()
            enctype = self._get_attr(form_html, 'enctype')

            # Extract inputs
            inputs = []
            has_file_upload = False
            has_password = False

            input_pattern = r'<input[^>]*>'
            for input_match in re.finditer(input_pattern, form_html, re.IGNORECASE):
                input_html = input_match.group(0)
                input_type = self._get_attr(input_html, 'type') or 'text'
                input_name = self._get_attr(input_html, 'name') or ''
                input_value = self._get_attr(input_html, 'value') or ''
                input_id = self._get_attr(input_html, 'id') or ''

                if input_name:
                    inputs.append({
                        'type': input_type,
                        'name': input_name,
                        'value': input_value,
                        'id': input_id
                    })

                if input_type == 'file':
                    has_file_upload = True
                elif input_type == 'password':
                    has_password = True

            # Extract select and textarea
            select_pattern = r'<select[^>]*name=["\']([^"\']+)["\']'
            for match in re.finditer(select_pattern, form_html, re.IGNORECASE):
                inputs.append({'type': 'select', 'name': match.group(1)})

            textarea_pattern = r'<textarea[^>]*name=["\']([^"\']+)["\']'
            for match in re.finditer(textarea_pattern, form_html, re.IGNORECASE):
                inputs.append({'type': 'textarea', 'name': match.group(1)})

            forms.append(FormData(
                action=action,
                method=method,
                inputs=inputs,
                has_file_upload=has_file_upload,
                has_password=has_password,
                enctype=enctype
            ))

        return forms

    def _extract_scripts(self, html: str) -> List[ScriptInfo]:
        """Extract script information."""
        scripts = []

        # External scripts
        ext_pattern = r'<script[^>]*src=["\']([^"\']+)["\'][^>]*>'
        for match in re.finditer(ext_pattern, html, re.IGNORECASE):
            src = match.group(1)
            script_type = self._get_attr(match.group(0), 'type')

            # Detect frameworks from script src
            frameworks = []
            src_lower = src.lower()
            for fw, patterns in self.FRAMEWORK_SIGNATURES.items():
                if any(p in src_lower for p in patterns):
                    frameworks.append(fw)

            scripts.append(ScriptInfo(
                src=src,
                content=None,
                script_type=script_type,
                is_inline=False,
                frameworks=frameworks
            ))

        # Inline scripts
        inline_pattern = r'<script[^>]*>(.*?)</script>'
        for match in re.finditer(inline_pattern, html, re.IGNORECASE | re.DOTALL):
            content = match.group(1).strip()
            if not content:
                continue

            script_tag = match.group(0)
            script_type = self._get_attr(script_tag, 'type')

            # Detect frameworks from content
            frameworks = []
            content_lower = content.lower()
            for fw, patterns in self.FRAMEWORK_SIGNATURES.items():
                if any(re.search(p, content, re.IGNORECASE) for p in patterns):
                    frameworks.append(fw)

            # Check for API calls
            has_external_api = bool(re.search(r'(fetch|axios|XMLHttpRequest|\$\.ajax)', content))

            scripts.append(ScriptInfo(
                src=None,
                content=content[:1000] if len(content) > 1000 else content,  # Truncate
                script_type=script_type,
                is_inline=True,
                has_external_api=has_external_api,
                frameworks=frameworks
            ))

        return scripts

    def _extract_stylesheets(self, html: str) -> List[str]:
        """Extract stylesheet URLs."""
        stylesheets = []
        pattern = r'<link[^>]*rel=["\']?stylesheet["\']?[^>]*href=["\']([^"\']+)["\']'

        for match in re.finditer(pattern, html, re.IGNORECASE):
            stylesheets.append(match.group(1))

        return stylesheets

    def _extract_images(self, html: str) -> List[Dict[str, str]]:
        """Extract image information."""
        images = []
        pattern = r'<img[^>]*>'

        for match in re.finditer(pattern, html, re.IGNORECASE):
            img_html = match.group(0)
            src = self._get_attr(img_html, 'src') or ''
            alt = self._get_attr(img_html, 'alt') or ''

            if src:
                images.append({'src': src, 'alt': alt})

        return images

    def _extract_links(self, html: str) -> List[Dict[str, str]]:
        """Extract internal links."""
        links = []
        pattern = r'<a[^>]*href=["\']([^"\']+)["\'][^>]*>([^<]*)</a>'

        for match in re.finditer(pattern, html, re.IGNORECASE):
            href = match.group(1)
            text = match.group(2).strip()

            # Check if internal
            if href.startswith(('/', '#')) or self.parsed_url.netloc in href:
                links.append({'href': href, 'text': text})

        return links

    def _extract_external_links(self, html: str) -> List[str]:
        """Extract external links."""
        external = set()
        pattern = r'<a[^>]*href=["\']([^"\']+)["\']'

        for match in re.finditer(pattern, html, re.IGNORECASE):
            href = match.group(1)
            if href.startswith(('http://', 'https://')) and self.parsed_url.netloc not in href:
                external.add(href)

        return list(external)

    def _extract_comments(self, html: str) -> List[str]:
        """Extract HTML comments."""
        comments = []
        pattern = r'<!--(.*?)-->'

        for match in re.finditer(pattern, html, re.DOTALL):
            comment = match.group(1).strip()
            if comment and not comment.startswith(('[if', '<![endif')):
                comments.append(comment)

        return comments

    def _extract_emails(self, html: str) -> Set[str]:
        """Extract email addresses."""
        emails = set()
        for match in re.finditer(self.EMAIL_PATTERN, html):
            email = match.group(0)
            # Filter out common false positives
            if not any(x in email.lower() for x in ['example.com', 'test.com', 'domain.com']):
                emails.add(email)
        return emails

    def _extract_phones(self, html: str) -> Set[str]:
        """Extract phone numbers."""
        phones = set()
        for match in re.finditer(self.PHONE_PATTERN, html):
            phones.add(match.group(0))
        return phones

    def _extract_api_endpoints(self, html: str) -> List[str]:
        """Extract API endpoints from HTML and JavaScript."""
        endpoints = set()

        for pattern in self.API_ENDPOINT_PATTERNS:
            for match in re.finditer(pattern, html, re.IGNORECASE):
                endpoint = match.group(1)
                if endpoint.startswith('/'):
                    endpoints.add(endpoint)

        return list(endpoints)

    def _extract_hidden_inputs(self, html: str) -> List[Dict[str, str]]:
        """Extract hidden form inputs."""
        hidden = []
        pattern = r'<input[^>]*type=["\']hidden["\'][^>]*>'

        for match in re.finditer(pattern, html, re.IGNORECASE):
            input_html = match.group(0)
            name = self._get_attr(input_html, 'name') or ''
            value = self._get_attr(input_html, 'value') or ''
            if name:
                hidden.append({'name': name, 'value': value})

        return hidden

    def _parse_cookies(self, cookie_header: str) -> List[Dict[str, str]]:
        """Parse Set-Cookie header."""
        cookies = []
        if not cookie_header:
            return cookies

        for cookie in cookie_header.split(','):
            parts = cookie.split(';')
            if parts:
                name_value = parts[0].strip().split('=', 1)
                if len(name_value) == 2:
                    cookies.append({
                        'name': name_value[0],
                        'value': name_value[1],
                        'attributes': [p.strip() for p in parts[1:]]
                    })

        return cookies

    def _get_attr(self, tag: str, attr: str) -> Optional[str]:
        """Extract attribute value from HTML tag."""
        # Try quoted format
        pattern = rf'{attr}=["\']([^"\']*)["\']'
        match = re.search(pattern, tag, re.IGNORECASE)
        if match:
            return match.group(1)

        # Try unquoted format
        pattern = rf'{attr}=([^\s>]+)'
        match = re.search(pattern, tag, re.IGNORECASE)
        if match:
            return match.group(1)

        return None
