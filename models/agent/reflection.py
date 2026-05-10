"""
Action Reflection & Self-Improvement

Analyzes executed actions for learning and adaptation.
"""

import logging
import json
import time
from dataclasses import dataclass, field
from typing import List, Dict, Optional

from models.agent.state import AttackAction, AttackState

logger = logging.getLogger(__name__)


@dataclass
class Reflection:
    """Result of reflecting on an action."""
    action_id: str
    success: bool
    analysis: str
    lessons: List[str] = field(default_factory=list)
    alternatives: List[str] = field(default_factory=list)
    next_steps: List[str] = field(default_factory=list)
    confidence: float = 0.5
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "action_id": self.action_id,
            "success": self.success,
            "analysis": self.analysis,
            "lessons": self.lessons,
            "alternatives": self.alternatives,
            "confidence": self.confidence,
        }


REFLECT_PROMPT = """你是一位经验丰富的渗透测试专家，请分析以下操作的结果并提供反思。

执行的操作:
- 类型: {action_type}
- 目标: {target}
- 工具: {tool}
- 命令: {command}

执行结果:
- 成功: {success}
- 输出摘要: {output_summary}
- 错误: {error}

当前攻击状态:
{state_summary}

请返回JSON:
{{
    "analysis": "操作结果分析",
    "success": true/false,
    "lessons": [
        "从这次操作中学到的经验教训"
    ],
    "alternatives": [
        "如果失败，可以尝试的替代方案"
    ],
    "next_steps": [
        "建议的下一步操作"
    ],
    "confidence": 0.0-1.0
}}

分析原则：
1. 识别成功或失败的根本原因
2. 提取可复用的经验
3. 提供具体的改进建议
4. 评估对整体攻击的影响
"""


class ActionReflector:
    """Reflects on action results for learning."""

    def __init__(self, llm_provider=None):
        self.llm = llm_provider
        self.reflections: List[Reflection] = []

    def reflect(self, action: AttackAction, result: dict, state: AttackState) -> Reflection:
        """Reflect on an executed action."""
        if self.llm:
            try:
                return self._reflect_with_llm(action, result, state)
            except Exception as e:
                logger.warning(f"LLM reflection failed: {e}")

        return self._rule_based_reflect(action, result)

    def _reflect_with_llm(self, action: AttackAction, result: dict, state: AttackState) -> Reflection:
        """Use LLM to reflect on action."""
        output_summary = result.get("stdout", "")[:500]
        if not output_summary:
            output_summary = result.get("interpretation", "") or "No output"

        prompt = REFLECT_PROMPT.format(
            action_type=action.type,
            target=action.target,
            tool=action.tool or "auto",
            command=action.params.get("command", action.type),
            success=action.status == "success",
            output_summary=output_summary,
            error=result.get("error", "None"),
            state_summary=state.get_state_for_llm()[:1500],
        )

        response = self.llm.call(
            [{"role": "user", "content": prompt}],
            use_json_mode=False,
            temperature=0.3,
        )

        content = response.content.strip()
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            content = content.split("```")[1].split("```")[0]

        data = json.loads(content.strip())

        reflection = Reflection(
            action_id=action.action_id,
            success=data.get("success", action.status == "success"),
            analysis=data.get("analysis", ""),
            lessons=data.get("lessons", []),
            alternatives=data.get("alternatives", []),
            next_steps=data.get("next_steps", []),
            confidence=data.get("confidence", 0.5),
        )

        self.reflections.append(reflection)
        return reflection

    def _rule_based_reflect(self, action: AttackAction, result: dict) -> Reflection:
        """Rule-based reflection fallback."""
        success = action.status == "success"
        lessons = []
        alternatives = []
        next_steps = []

        if not success:
            if "timeout" in str(result.get("error", "")).lower():
                lessons.append("操作超时，考虑增加超时时间或优化命令")
                alternatives.append("使用更快的扫描选项")
            elif "connection refused" in str(result.get("stderr", "")).lower():
                lessons.append("目标服务未运行或被防火墙阻断")
                alternatives.append("检查其他开放端口")
            elif "permission denied" in str(result.get("stderr", "")).lower():
                lessons.append("权限不足")
                alternatives.append("尝试权限提升后再执行")
            else:
                lessons.append("操作未成功完成")
                alternatives.append("尝试其他攻击向量")

            next_steps.append("分析失败原因并调整策略")
        else:
            lessons.append(f"操作成功完成: {action.type}")
            next_steps.append("继续下一阶段操作")

        reflection = Reflection(
            action_id=action.action_id,
            success=success,
            analysis=f"操作{'成功' if success else '失败'}",
            lessons=lessons,
            alternatives=alternatives,
            next_steps=next_steps,
            confidence=0.7 if success else 0.3,
        )

        self.reflections.append(reflection)
        return reflection

    def get_lessons_learned(self) -> List[str]:
        """Get all lessons from reflections."""
        all_lessons = []
        for r in self.reflections:
            all_lessons.extend(r.lessons)
        return list(set(all_lessons))

    def get_successful_patterns(self) -> List[dict]:
        """Get patterns from successful actions."""
        return [
            {
                "action_id": r.action_id,
                "analysis": r.analysis,
            }
            for r in self.reflections
            if r.success and r.confidence > 0.6
        ]

    def get_recent_reflections(self, n: int = 5) -> List[Reflection]:
        """Get the most recent reflections."""
        return self.reflections[-n:]
