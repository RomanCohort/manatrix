"""
Multi-Expert System for Penetration Testing

This module provides specialized experts for different penetration testing domains.
Each expert can analyze situations and provide actionable advice.
"""

from models.experts.base import PenTestExpert, ExpertAdvice, ExpertType
from models.experts.vulnerability_expert import VulnerabilityExpert
from models.experts.exploitation_expert import ExploitationExpert
from models.experts.post_exploitation_expert import PostExploitationExpert
from models.experts.credential_expert import CredentialExpert
from models.experts.lateral_movement_expert import LateralMovementExpert
from models.experts.reconnaissance_expert import ReconnaissanceExpert
# New experts for expanded hacking scenarios
from models.experts.web_application_expert import WebApplicationExpert
from models.experts.api_security_expert import APISecurityExpert
from models.experts.active_directory_expert import ActiveDirectoryExpert
from models.experts.cloud_security_expert import CloudSecurityExpert
from models.experts.iot_security_expert import IoTIoTSecurityExpert
from models.experts.mobile_security_expert import MobileSecurityExpert
from models.experts.crypto_attack_expert import CryptoAttackExpert
from models.experts.network_tunnel_expert import NetworkTunnelExpert
from models.experts.data_exfiltration_expert import DataExfiltrationExpert
from models.experts.social_engineering_expert import SocialEngineeringExpert
from models.experts.supply_chain_expert import SupplyChainExpert
from models.experts.wireless_security_expert import WirelessSecurityExpert
from models.experts.reverse_engineering_expert import ReverseEngineeringExpert
from models.experts.hardware_security_expert import HardwareSecurityExpert

__all__ = [
    "PenTestExpert",
    "ExpertAdvice",
    "ExpertType",
    # Core experts
    "ReconnaissanceExpert",
    "VulnerabilityExpert",
    "ExploitationExpert",
    "PostExploitationExpert",
    "CredentialExpert",
    "LateralMovementExpert",
    # Expanded experts
    "WebApplicationExpert",
    "APISecurityExpert",
    "ActiveDirectoryExpert",
    "CloudSecurityExpert",
    "IoTIoTSecurityExpert",
    "MobileSecurityExpert",
    "CryptoAttackExpert",
    "NetworkTunnelExpert",
    "DataExfiltrationExpert",
    "SocialEngineeringExpert",
    "SupplyChainExpert",
    "WirelessSecurityExpert",
    "ReverseEngineeringExpert",
    "HardwareSecurityExpert",
]
