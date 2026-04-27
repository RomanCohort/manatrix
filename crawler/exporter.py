"""
Exporter

Export crawl results to various system components:
- RL agent state
- Knowledge graph
- Expert system
- Attack graph
"""

import logging
from typing import Dict, List, Optional, Any, Set
from urllib.parse import urlparse

from .spider import CrawlResult, PageData

logger = logging.getLogger(__name__)


class CrawlerExporter:
    """Export crawl results to different formats and systems."""

    def __init__(self, result: CrawlResult):
        """
        Initialize exporter with crawl results.

        Args:
            result: Crawl results to export
        """
        self.result = result

    def export_all(self) -> Dict[str, Any]:
        """Export all data in a unified format."""
        return {
            "rl_state": self.export_to_rl_state(),
            "knowledge_graph": self.export_to_knowledge_graph(),
            "expert_system": self.export_to_expert_system(),
            "attack_graph": self.export_to_attack_graph(),
        }

    def export_to_rl_state(self) -> Dict[str, Any]:
        """
        Export to RL agent state format.

        Returns a dict compatible with PenTestState.from_dict().
        Maps to: rl_agent/state.py PenTestState fields
        """
        state = {
            "discovered_hosts": set(),
            "open_ports": {},
            "services": {},
            "vulnerabilities": {},
            "credentials": {},
            "technologies": {},
            "urls": set(),
            "emails": list(self.result.total_emails),
            "phone_numbers": list(self.result.total_phone_numbers),
            "forms": [],
            "api_endpoints": set(),
            "attack_surface": {},
        }

        for url, page in self.result.pages.items():
            parsed = urlparse(url)
            host = parsed.netloc

            if host:
                state["discovered_hosts"].add(host)
                state["urls"].add(url)

                # Ports from scheme
                port = parsed.port
                if not port:
                    port = 443 if parsed.scheme == 'https' else 80

                if host not in state["open_ports"]:
                    state["open_ports"][host] = []
                if port not in state["open_ports"][host]:
                    state["open_ports"][host].append(port)

                # Services
                if host not in state["services"]:
                    state["services"][host] = {}

                service = "https" if parsed.scheme == 'https' else "http"
                state["services"][host][port] = f"{service} (web)"

                # Technologies
                if page.tech_report:
                    techs = [t.name for t in page.tech_report.technologies]
                    if techs:
                        state["technologies"][host] = techs

                    # Server info
                    if page.tech_report.server:
                        state["services"][host][port] = f"{service} ({page.tech_report.server})"

                # Vulnerabilities
                if page.vuln_report and page.vuln_report.findings:
                    high_vulns = [
                        f.title for f in page.vuln_report.findings
                        if f.severity in ('critical', 'high')
                    ]
                    if high_vulns:
                        if host not in state["vulnerabilities"]:
                            state["vulnerabilities"][host] = []
                        state["vulnerabilities"][host].extend(high_vulns)

                # Forms
                if page.parsed and page.parsed.forms:
                    for form in page.parsed.forms:
                        state["forms"].append({
                            "url": url,
                            "action": form.action,
                            "method": form.method,
                            "inputs": [i.get("name", "") for i in form.inputs],
                            "has_password": form.has_password,
                            "has_file_upload": form.has_file_upload,
                        })

                # API endpoints
                if page.api_endpoints:
                    state["api_endpoints"].update(page.api_endpoints)

                # Attack surface
                if host not in state["attack_surface"]:
                    state["attack_surface"][host] = {
                        "web_ports": [],
                        "tech_stack": [],
                        "cms": None,
                        "has_forms": False,
                        "has_api": False,
                        "security_headers": {},
                    }

                surface = state["attack_surface"][host]
                surface["web_ports"].append(port)
                if page.tech_report:
                    surface["tech_stack"] = list(set(
                        surface["tech_stack"] + page.tech_report.frameworks
                    ))
                    surface["cms"] = page.tech_report.cms
                    surface["security_headers"] = page.tech_report.security_headers
                if page.parsed and page.parsed.forms:
                    surface["has_forms"] = True
                if page.api_endpoints:
                    surface["has_api"] = True

        # Convert sets to lists for JSON serialization
        state["discovered_hosts"] = list(state["discovered_hosts"])
        state["urls"] = list(state["urls"])
        state["api_endpoints"] = list(state["api_endpoints"])

        return state

    def export_to_knowledge_graph(self) -> Dict[str, Any]:
        """
        Export to knowledge graph format.

        Returns structured data for CVE/ATT&CK database enrichment.
        Maps to: knowledge_graph/ modules
        """
        kg_data = {
            "technologies": [],
            "vulnerabilities": [],
            "attack_patterns": [],
            "cpe_list": [],
        }

        seen_techs = set()

        for url, report in self.result.technologies.items():
            for tech in report.technologies:
                tech_key = f"{tech.name}:{tech.version}"
                if tech_key in seen_techs:
                    continue
                seen_techs.add(tech_key)

                tech_entry = {
                    "name": tech.name,
                    "category": tech.category,
                    "version": tech.version,
                    "cpe": tech.cpe,
                    "evidence": tech.evidence,
                    "confidence": tech.confidence,
                    "source_url": url,
                }
                kg_data["technologies"].append(tech_entry)

                if tech.cpe:
                    kg_data["cpe_list"].append(tech.cpe)

        # Vulnerabilities
        for url, page in self.result.pages.items():
            if page.vuln_report:
                for finding in page.vuln_report.findings:
                    vuln_entry = {
                        "title": finding.title,
                        "severity": finding.severity,
                        "category": finding.category,
                        "description": finding.description,
                        "url": url,
                        "remediation": finding.remediation,
                        "cve": finding.cve,
                    }
                    kg_data["vulnerabilities"].append(vuln_entry)

                    # Map to ATT&CK patterns
                    attack_pattern = self._map_to_attack_pattern(finding)
                    if attack_pattern:
                        kg_data["attack_patterns"].append(attack_pattern)

        return kg_data

    def export_to_expert_system(self) -> Dict[str, Any]:
        """
        Export to expert system format.

        Returns state dict for ReconnaissanceExpert.analyze().
        Maps to: models/experts/reconnaissance_expert.py
        """
        # Build a state dict compatible with expert system
        expert_state = {
            "hosts": [],
            "services": {},
            "ports": {},
            "technologies": {},
            "vulnerabilities": {},
            "urls": [],
            "emails": list(self.result.total_emails),
            "attack_surface": {},
            "recommendations": [],
        }

        # Hosts
        hosts = set()
        for url in self.result.pages:
            parsed = urlparse(url)
            if parsed.netloc:
                hosts.add(parsed.netloc)

        expert_state["hosts"] = list(hosts)

        # Services and ports
        for host in hosts:
            expert_state["services"][host] = {}
            expert_state["ports"][host] = []

            for url, page in self.result.pages.items():
                parsed_url = urlparse(url)
                if parsed_url.netloc != host:
                    continue

                port = parsed_url.port or (443 if parsed_url.scheme == 'https' else 80)
                if port not in expert_state["ports"][host]:
                    expert_state["ports"][host].append(port)

                service_name = "https" if parsed_url.scheme == 'https' else "http"
                if page.tech_report and page.tech_report.server:
                    service_name += f" ({page.tech_report.server})"

                expert_state["services"][host][port] = service_name

        # Technologies
        for url, report in self.result.technologies.items():
            parsed_url = urlparse(url)
            host = parsed_url.netloc
            if host:
                expert_state["technologies"][host] = [
                    {"name": t.name, "version": t.version, "category": t.category}
                    for t in report.technologies
                ]

        # Vulnerabilities
        for url, page in self.result.pages.items():
            parsed_url = urlparse(url)
            host = parsed_url.netloc
            if page.vuln_report and page.vuln_report.findings:
                expert_state["vulnerabilities"][host] = [
                    {"title": f.title, "severity": f.severity, "category": f.category}
                    for f in page.vuln_report.findings
                    if f.severity in ('critical', 'high', 'medium')
                ]

        # URLs
        expert_state["urls"] = self.result.get_all_urls()

        # Generate recommendations
        expert_state["recommendations"] = self._generate_recommendations()

        return expert_state

    def export_to_attack_graph(self) -> Dict[str, Any]:
        """
        Export to attack graph format.

        Returns nodes and edges for AttackGraph.
        Maps to: attack_graph/graph.py
        """
        graph = {
            "nodes": [],
            "edges": [],
        }

        # Add host nodes
        hosts = set()
        for url in self.result.pages:
            parsed = urlparse(url)
            if parsed.netloc:
                hosts.add(parsed.netloc)

        for host in hosts:
            node = {
                "id": f"host:{host}",
                "type": "host",
                "label": host,
                "properties": {
                    "web_ports": [],
                    "technologies": [],
                    "vulnerabilities": [],
                }
            }

            for url, page in self.result.pages.items():
                parsed = urlparse(url)
                if parsed.netloc != host:
                    continue

                port = parsed.port or (443 if parsed.scheme == 'https' else 80)
                if port not in node["properties"]["web_ports"]:
                    node["properties"]["web_ports"].append(port)

                if page.tech_report:
                    node["properties"]["technologies"] = list(set(
                        node["properties"]["technologies"] +
                        [t.name for t in page.tech_report.technologies]
                    ))

                if page.vuln_report:
                    node["properties"]["vulnerabilities"] = list(set(
                        node["properties"]["vulnerabilities"] +
                        [f.title for f in page.vuln_report.findings
                         if f.severity in ('critical', 'high')]
                    ))

            graph["nodes"].append(node)

        # Add service nodes and edges
        for host in hosts:
            for url, page in self.result.pages.items():
                parsed = urlparse(url)
                if parsed.netloc != host:
                    continue

                port = parsed.port or (443 if parsed.scheme == 'https' else 80)
                service_id = f"service:{host}:{port}"

                service_node = {
                    "id": service_id,
                    "type": "service",
                    "label": f"HTTP/HTTPS:{port}",
                    "properties": {
                        "protocol": "https" if parsed.scheme == 'https' else "http",
                        "port": port,
                        "url": url,
                    }
                }

                if page.tech_report and page.tech_report.server:
                    service_node["properties"]["server"] = page.tech_report.server

                graph["nodes"].append(service_node)

                # Edge: host -> service
                graph["edges"].append({
                    "source": f"host:{host}",
                    "target": service_id,
                    "type": "runs_service"
                })

                # Add vulnerability nodes
                if page.vuln_report:
                    for finding in page.vuln_report.findings:
                        if finding.severity in ('critical', 'high'):
                            vuln_id = f"vuln:{host}:{port}:{finding.title[:30]}"

                            graph["nodes"].append({
                                "id": vuln_id,
                                "type": "vulnerability",
                                "label": finding.title,
                                "properties": {
                                    "severity": finding.severity,
                                    "category": finding.category,
                                    "description": finding.description,
                                }
                            })

                            graph["edges"].append({
                                "source": service_id,
                                "target": vuln_id,
                                "type": "has_vulnerability"
                            })

        return graph

    def _map_to_attack_pattern(self, finding) -> Optional[Dict]:
        """Map vulnerability finding to MITRE ATT&CK pattern."""
        category_map = {
            "exposure": {"tactic": "Initial Access", "technique": "T1190", "name": "Exploit Public-Facing Application"},
            "disclosure": {"tactic": "Discovery", "technique": "T1082", "name": "System Information Discovery"},
            "sensitive": {"tactic": "Credential Access", "technique": "T1552", "name": "Unsecured Credentials"},
            "misconfiguration": {"tactic": "Initial Access", "technique": "T1190", "name": "Exploit Public-Facing Application"},
        }

        if finding.category in category_map:
            pattern = category_map[finding.category]
            return {
                "technique_id": pattern["technique"],
                "technique_name": pattern["name"],
                "tactic": pattern["tactic"],
                "evidence": finding.title,
                "severity": finding.severity,
            }

        return None

    def _generate_recommendations(self) -> List[str]:
        """Generate actionable recommendations based on findings."""
        recommendations = []

        # Check for critical/high vulnerabilities
        critical_vulns = []
        for url, page in self.result.pages.items():
            if page.vuln_report:
                for finding in page.vuln_report.findings:
                    if finding.severity in ('critical', 'high'):
                        critical_vulns.append((url, finding))

        if critical_vulns:
            recommendations.append(
                f"Found {len(critical_vulns)} critical/high vulnerabilities - "
                "prioritize exploitation of exposed credentials and config files"
            )

        # Check for forms (potential injection points)
        forms = self.result.get_all_forms()
        if forms:
            recommendations.append(
                f"Discovered {len(forms)} forms - test for SQL injection, XSS, and CSRF"
            )

        # Check for CMS
        for url, report in self.result.technologies.items():
            if report.cms:
                recommendations.append(
                    f"CMS detected: {report.cms} - check for known CMS vulnerabilities"
                )

        # Check for outdated tech
        for url, report in self.result.technologies.items():
            for tech in report.technologies:
                if tech.version:
                    recommendations.append(
                        f"Technology with version detected: {tech.name} {tech.version} "
                        "- check for known CVEs"
                    )

        # Check for missing security headers
        missing_headers = set()
        for url, report in self.result.technologies.items():
            for header in ['strict-transport-security', 'content-security-policy', 'x-frame-options']:
                if header not in report.security_headers:
                    missing_headers.add(header)

        if missing_headers:
            recommendations.append(
                f"Missing security headers: {', '.join(missing_headers)} - "
                "may indicate weaker security posture"
            )

        return recommendations


# Convenience functions
def export_to_rl_state(result: CrawlResult) -> Dict[str, Any]:
    """Export crawl results to RL state format."""
    return CrawlerExporter(result).export_to_rl_state()


def export_to_knowledge_graph(result: CrawlResult) -> Dict[str, Any]:
    """Export crawl results to knowledge graph format."""
    return CrawlerExporter(result).export_to_knowledge_graph()


def export_to_expert_system(result: CrawlResult) -> Dict[str, Any]:
    """Export crawl results to expert system format."""
    return CrawlerExporter(result).export_to_expert_system()


def export_to_attack_graph(result: CrawlResult) -> Dict[str, Any]:
    """Export crawl results to attack graph format."""
    return CrawlerExporter(result).export_to_attack_graph()
