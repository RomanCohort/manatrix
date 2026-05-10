"""
Conversation Context & Agent Memory

Manages the conversation history for LLM context management
and persistent attack memory across sessions.
"""

import json
import time
import os
import logging
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class Message:
    """A message in the conversation."""
    role: str  # system, user, assistant
    content: str
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp,
        }

    def to_api_format(self) -> dict:
        """Format for LLM API call."""
        return {"role": self.role, "content": self.content}


class ConversationContext:
    """
    Manages conversation context for LLM interactions.

    Handles:
    - Message history with token estimation
    - System prompt management
    - Context window trimming
    """

    def __init__(self, system_prompt: str = "", max_context_messages: int = 50):
        self.messages: List[Message] = []
        self.system_prompt = system_prompt
        self.max_context_messages = max_context_messages

    def set_system_prompt(self, prompt: str) -> None:
        """Set the system prompt."""
        self.system_prompt = prompt

    def add_message(self, role: str, content: str, metadata: dict = None) -> None:
        """Add a message to the conversation."""
        self.messages.append(Message(
            role=role,
            content=content,
            metadata=metadata or {},
        ))
        # Trim if needed
        if len(self.messages) > self.max_context_messages * 2:
            self.messages = self.messages[-self.max_context_messages:]

    def get_messages_for_llm(self, max_messages: int = None) -> List[dict]:
        """Get messages formatted for LLM API call."""
        messages = []
        if self.system_prompt:
            messages.append({"role": "system", "content": self.system_prompt})

        count = max_messages or self.max_context_messages
        recent = self.messages[-count:]
        for msg in recent:
            messages.append(msg.to_api_format())

        return messages

    def get_recent_summary(self, n: int = 5) -> str:
        """Get a summary of recent messages."""
        recent = self.messages[-n:]
        lines = []
        for msg in recent:
            role_label = {"system": "系统", "user": "用户", "assistant": "助手"}.get(msg.role, msg.role)
            content = msg.content[:200]
            lines.append(f"[{role_label}]: {content}")
        return "\n".join(lines)

    def clear(self) -> None:
        """Clear conversation history."""
        self.messages.clear()

    def save(self, filepath: str) -> None:
        """Save conversation to file."""
        data = {
            "system_prompt": self.system_prompt,
            "messages": [m.to_dict() for m in self.messages],
        }
        Path(filepath).parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def load(self, filepath: str) -> None:
        """Load conversation from file."""
        if not os.path.exists(filepath):
            return
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        self.system_prompt = data.get("system_prompt", "")
        self.messages = [
            Message(role=m["role"], content=m["content"], timestamp=m.get("timestamp", 0))
            for m in data.get("messages", [])
        ]


class AgentMemory:
    """
    Persistent memory for the attack agent.

    Stores:
    - Attack patterns and results
    - Tool effectiveness ratings
    - Expert routing history
    - Lessons learned
    """

    def __init__(self, workspace_dir: str = None):
        self.workspace_dir = workspace_dir or str(Path.home() / ".manatrix" / "agent")
        os.makedirs(self.workspace_dir, exist_ok=True)

        # In-memory stores
        self.tool_results: Dict[str, List[dict]] = {}  # tool_name -> [results]
        self.expert_history: List[dict] = []
        self.lessons: List[str] = []
        self.patterns: Dict[str, Any] = {}

        # Load existing memory
        self._load()

    def record_tool_result(self, tool: str, action: str, success: bool, output_summary: str) -> None:
        """Record a tool execution result."""
        if tool not in self.tool_results:
            self.tool_results[tool] = []
        self.tool_results[tool].append({
            "action": action,
            "success": success,
            "summary": output_summary[:200],
            "timestamp": time.time(),
        })
        # Keep bounded
        if len(self.tool_results[tool]) > 100:
            self.tool_results[tool] = self.tool_results[tool][-100:]

    def record_expert_routing(self, expert_type: str, success: bool, context: str) -> None:
        """Record expert routing decision."""
        self.expert_history.append({
            "expert": expert_type,
            "success": success,
            "context": context[:200],
            "timestamp": time.time(),
        })
        if len(self.expert_history) > 200:
            self.expert_history = self.expert_history[-200:]

    def add_lesson(self, lesson: str) -> None:
        """Add a learned lesson."""
        if lesson not in self.lessons:
            self.lessons.append(lesson)
        if len(self.lessons) > 100:
            self.lessons = self.lessons[-100:]

    def get_tool_effectiveness(self, tool: str) -> float:
        """Get effectiveness rating for a tool (0-1)."""
        results = self.tool_results.get(tool, [])
        if not results:
            return 0.5
        successes = sum(1 for r in results if r["success"])
        return successes / len(results)

    def get_best_tools_for_action(self, action_type: str) -> List[str]:
        """Get most effective tools for an action type."""
        scored = []
        for tool, results in self.tool_results.items():
            relevant = [r for r in results if action_type in r["action"]]
            if relevant:
                success_rate = sum(1 for r in relevant if r["success"]) / len(relevant)
                scored.append((tool, success_rate))

        scored.sort(key=lambda x: x[1], reverse=True)
        return [tool for tool, _ in scored[:5]]

    def get_context_for_llm(self) -> str:
        """Format memory context for LLM."""
        lines = ["=== Agent Memory ==="]

        # Lessons
        if self.lessons:
            lines.append(f"Lessons learned ({len(self.lessons)}):")
            for lesson in self.lessons[-5:]:
                lines.append(f"  - {lesson}")

        # Tool effectiveness
        effective_tools = []
        for tool, results in self.tool_results.items():
            if results:
                rate = sum(1 for r in results if r["success"]) / len(results)
                effective_tools.append((tool, rate, len(results)))
        if effective_tools:
            effective_tools.sort(key=lambda x: x[1], reverse=True)
            lines.append("Tool effectiveness:")
            for tool, rate, count in effective_tools[:10]:
                lines.append(f"  - {tool}: {rate:.0%} ({count} uses)")

        return "\n".join(lines)

    def _load(self) -> None:
        """Load memory from disk."""
        mem_file = os.path.join(self.workspace_dir, "memory.json")
        if os.path.exists(mem_file):
            try:
                with open(mem_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                self.lessons = data.get("lessons", [])
                self.patterns = data.get("patterns", {})
            except Exception as e:
                logger.warning(f"Failed to load memory: {e}")

    def save(self) -> None:
        """Save memory to disk."""
        mem_file = os.path.join(self.workspace_dir, "memory.json")
        try:
            with open(mem_file, 'w', encoding='utf-8') as f:
                json.dump({
                    "lessons": self.lessons,
                    "patterns": self.patterns,
                }, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.warning(f"Failed to save memory: {e}")
