"""
Agent Module for Manatrix Autonomous Attack System
"""

# Use lazy imports to avoid circular import:
# models/agent/__init__.py -> models.manatrix_agent -> models.agent.brief_parser -> models.agent
def __getattr__(name):
    if name == "ManatrixAgent":
        from models.manatrix_agent import ManatrixAgent
        return ManatrixAgent
    if name == "BriefParser":
        from models.agent.brief_parser import BriefParser
        return BriefParser
    if name == "AttackObjectives":
        from models.agent.brief_parser import AttackObjectives
        return AttackObjectives
    if name == "ScopeType":
        from models.agent.brief_parser import ScopeType
        return ScopeType
    if name == "AttackType":
        from models.agent.brief_parser import AttackType
        return AttackType
    if name == "AttackPlanner":
        from models.agent.planner import AttackPlanner
        return AttackPlanner
    if name == "AttackPlan":
        from models.agent.planner import AttackPlan
        return AttackPlan
    if name == "AttackPhase":
        from models.agent.planner import AttackPhase
        return AttackPhase
    if name == "AttackState":
        from models.agent.state import AttackState
        return AttackState
    if name == "Host":
        from models.agent.state import Host
        return Host
    if name == "Vulnerability":
        from models.agent.state import Vulnerability
        return Vulnerability
    if name == "Credential":
        from models.agent.state import Credential
        return Credential
    if name == "ConversationContext":
        from models.agent.memory import ConversationContext
        return ConversationContext
    if name == "Message":
        from models.agent.memory import Message
        return Message
    if name == "AgentMemory":
        from models.agent.memory import AgentMemory
        return AgentMemory
    if name == "AgentToolExecutor":
        from models.agent.executor import AgentToolExecutor
        return AgentToolExecutor
    if name == "ActionReflector":
        from models.agent.reflection import ActionReflector
        return ActionReflector
    raise AttributeError(f"module 'models.agent' has no attribute '{name}'")


__all__ = [
    "ManatrixAgent",
    "BriefParser",
    "AttackObjectives",
    "ScopeType",
    "AttackType",
    "AttackPlanner",
    "AttackPlan",
    "AttackPhase",
    "AttackState",
    "Host",
    "Vulnerability",
    "Credential",
    "ConversationContext",
    "Message",
    "AgentMemory",
    "AgentToolExecutor",
    "ActionReflector",
]
