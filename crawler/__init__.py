"""
Web Crawler Module

Async web crawler for penetration testing reconnaissance.
Discovers web targets, technologies, and vulnerabilities.
"""

from .spider import CoreSpider, CrawlResult, PageData
from .config import CrawlerConfig
from .exporter import (
    export_to_rl_state,
    export_to_knowledge_graph,
    export_to_expert_system,
    export_to_attack_graph,
    CrawlerExporter
)

__all__ = [
    "CoreSpider",
    "CrawlResult",
    "PageData",
    "CrawlerConfig",
    "CrawlerExporter",
    "export_to_rl_state",
    "export_to_knowledge_graph",
    "export_to_expert_system",
    "export_to_attack_graph",
]