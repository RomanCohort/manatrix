"""
Shared Enums for the Manatrix project.

Centralized enum definitions to avoid circular dependencies between modules.
"""

from enum import Enum


class ExpertType(Enum):
    """Types of penetration testing experts."""
    RECONNAISSANCE = "reconnaissance"
    VULNERABILITY = "vulnerability"
    EXPLOITATION = "exploitation"
    POST_EXPLOITATION = "post_exploitation"
    CREDENTIAL = "credential"
    LATERAL_MOVEMENT = "lateral_movement"
    PRIVILEGE_ESCALATION = "privilege_escalation"
    PERSISTENCE = "persistence"
    EVASION = "evasion"
    # New experts for more hacking scenarios
    WEB_APPLICATION = "web_application"
    API_SECURITY = "api_security"
    ACTIVE_DIRECTORY = "active_directory"
    CLOUD_SECURITY = "cloud_security"
    IOT_SECURITY = "iot_security"
    MOBILE_SECURITY = "mobile_security"
    CRYPTO_ATTACK = "crypto_attack"
    NETWORK_TUNNEL = "network_tunnel"
    DATA_EXFILTRATION = "data_exfiltration"
    SOCIAL_ENGINEERING = "social_engineering"
    SUPPLY_CHAIN = "supply_chain"
    WIRELESS_SECURITY = "wireless_security"
    REVERSE_ENGINEERING = "reverse_engineering"
    HARDWARE_SECURITY = "hardware_security"