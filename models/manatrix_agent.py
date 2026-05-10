"""
ManatrixAgent - Autonomous Attack Agent

Claude Code-style autonomous penetration testing agent.
Give it a brief, and it plans and executes the entire attack.

Usage:
    from models.manatrix_agent import ManatrixAgent
    from models.llm_provider import LLMConfig

    config = LLMConfig(provider="deepseek", api_key="sk-xxx")
    agent = ManatrixAgent(config)

    # Run autonomous attack
    result = agent.run("攻击 192.168.1.0/24，目标是获取域管理员权限")

    # Or stream results via callback
    agent.run(brief, on_update=print)
"""

import logging
import time
import json
import uuid
from typing import Callable, Optional, List, Dict, Any
from dataclasses import dataclass, field

from models.llm_provider import LLMConfig, get_provider, BaseLLMProvider
from models.agent.brief_parser import BriefParser, AttackObjectives
from models.agent.planner import AttackPlanner, AttackPlan, AttackPhase, AttackStep
from models.agent.executor import AgentToolExecutor, ExecutionResult
from models.agent.state import AttackState, AttackAction, Phase, Host
from models.agent.memory import ConversationContext, AgentMemory
from models.agent.reflection import ActionReflector, Reflection
from models.expert_router import create_default_router, ExpertRouter

logger = logging.getLogger(__name__)


@dataclass
class AttackResult:
    """Final result of an autonomous attack."""
    session_id: str
    brief: str
    success: bool
    duration: float
    phases_completed: int
    total_actions: int
    hosts_discovered: int
    vulns_found: int
    creds_obtained: int
    shells_obtained: int
    compromised_hosts: List[str]
    state: AttackState = None
    plan: AttackPlan = None
    reflections: List[Reflection] = field(default_factory=list)
    report: str = ""

    def to_dict(self) -> dict:
        return {
            "session_id": self.session_id,
            "success": self.success,
            "duration": self.duration,
            "phases_completed": self.phases_completed,
            "total_actions": self.total_actions,
            "hosts_discovered": self.hosts_discovered,
            "vulns_found": self.vulns_found,
            "creds_obtained": self.creds_obtained,
            "shells_obtained": self.shells_obtained,
            "compromised_hosts": self.compromised_hosts,
            "report": self.report,
        }


# System prompt for the agent
AGENT_SYSTEM_PROMPT = """你是 ManatrixAgent，一个自主渗透测试AI代理。

你的工作方式类似于 Claude Code：
1. 用户给你一个攻击简报（目标、范围、目标）
2. 你制定详细的攻击计划
3. 你逐步执行计划中的每个操作
4. 你分析每个操作的结果并调整策略
5. 你持续执行直到达成目标或穷尽所有选项

你拥有 18 个专业领域的专家可以咨询：
- 侦察、漏洞分析、漏洞利用、后渗透、凭据攻击、横向移动
- Web应用、API安全、Active Directory、云安全
- IoT安全、移动安全、密码学攻击、网络隧道
- 数据窃取、社会工程、供应链安全、无线安全

攻击原则：
1. 遵守授权范围
2. 从被动到主动
3. 每步操作后有反思和调整
4. 保持操作隐蔽性
5. 记录所有操作和结果
"""


class ManatrixAgent:
    """
    Autonomous attack agent - Claude Code style.

    Give it a briefing, and it autonomously plans and executes
    the entire penetration test.
    """

    def __init__(
        self,
        llm_config: LLMConfig = None,
        llm_provider: BaseLLMProvider = None,
        workspace_dir: str = None,
        timeout: int = 120,
        max_steps: int = 50,
        sandbox: bool = False,
    ):
        # LLM setup
        if llm_provider:
            self.llm = llm_provider
        elif llm_config:
            self.llm = get_provider(llm_config)
        else:
            self.llm = None

        # Components
        self.brief_parser = BriefParser(self.llm)
        self.planner = AttackPlanner(self.llm)
        self.executor = AgentToolExecutor(self.llm, timeout=timeout, sandbox=sandbox)
        self.reflector = ActionReflector(self.llm)
        self.memory = AgentMemory(workspace_dir)

        # Expert router
        self.router: Optional[ExpertRouter] = None
        if self.llm:
            try:
                self.router = create_default_router(self.llm)
            except Exception as e:
                logger.warning(f"Expert router initialization failed: {e}")

        # Conversation
        self.context = ConversationContext(system_prompt=AGENT_SYSTEM_PROMPT)

        # Config
        self.max_steps = max_steps
        self.timeout = timeout
        self.sandbox = sandbox

        # State
        self.state: Optional[AttackState] = None
        self.plan: Optional[AttackPlan] = None

    def run(
        self,
        brief: str,
        on_update: Callable[[str, dict], None] = None,
        on_action: Callable[[AttackAction, ExecutionResult], None] = None,
        dry_run: bool = False,
    ) -> AttackResult:
        """
        Run an autonomous attack from a briefing.

        Args:
            brief: Natural language attack briefing
            on_update: Callback for progress updates (message, data)
            on_action: Callback for each action execution
            dry_run: If True, only plan without executing

        Returns:
            AttackResult with full results
        """
        start_time = time.time()
        session_id = str(uuid.uuid4())[:8]

        self._emit(on_update, "status", {
            "session_id": session_id,
            "phase": "initializing",
            "message": "Starting ManatrixAgent...",
        })

        # Initialize state
        self.state = AttackState(session_id=session_id, phase=Phase.PLANNING)
        self.context.clear()

        try:
            # === Phase 1: Parse Brief ===
            self._emit(on_update, "status", {"phase": "parsing", "message": "Parsing brief..."})
            objectives = self.brief_parser.parse(brief)
            self.state.objectives = objectives.objectives
            self.state.targets = objectives.targets
            self.state.scope = objectives.scope.value

            self.context.add_message("user", f"攻击简报:\n{brief}")
            self.context.add_message("assistant",
                f"已解析目标: {', '.join(objectives.targets)}\n"
                f"攻击类型: {objectives.attack_type.value}\n"
                f"具体目标: {', '.join(objectives.objectives)}")

            self._emit(on_update, "parsed", objectives.to_dict())

            # === Phase 2: Create Plan ===
            self._emit(on_update, "status", {"phase": "planning", "message": "Creating attack plan..."})
            self.plan = self.planner.create_plan(objectives, self.state)

            self.context.add_message("assistant",
                f"攻击计划已制定: {len(self.plan.phases)} 个阶段\n"
                + "\n".join(f"  {i+1}. {p.name} ({len(p.steps)} 步)" for i, p in enumerate(self.plan.phases)))

            self._emit(on_update, "plan", self.plan.to_dict())

            if dry_run:
                return self._build_result(start_time, brief, "Dry run - plan only")

            # === Phase 3: Execute Plan ===
            step_count = 0
            while step_count < self.max_steps:
                # Get next action
                action_step = self.plan.get_next_action()

                if action_step is None:
                    # Try to advance phase
                    if not self.plan.advance_phase():
                        # All phases complete
                        break
                    self.state.phase = self.plan.get_current_phase().phase_type
                    self._emit(on_update, "phase_change", {
                        "phase": self.state.phase.value,
                        "message": f"Entering phase: {self.plan.get_current_phase().name}",
                    })
                    continue

                # Mark step as running
                action_step.completed = True  # Mark as processed

                # Create attack action
                action = AttackAction(
                    type=action_step.type,
                    target=action_step.target,
                    tool=action_step.tool,
                    params=action_step.params,
                    phase=self.state.phase,
                )

                self._emit(on_update, "action_start", {
                    "action_id": action.action_id,
                    "type": action.type,
                    "target": action.target,
                    "tool": action.tool,
                })

                # === Execute ===
                self.state.phase = action_step.phase_type if hasattr(action_step, 'phase_type') else self.state.phase
                result = self.executor.execute(action, self.state)

                # Update action
                action.status = "success" if result.success else "failure"
                action.output = result.stdout[:500] if result.stdout else ""
                action.error = result.error
                action.completed_at = time.time()

                self.state.add_action(action)
                self.state.elapsed_time = time.time() - start_time
                step_count += 1

                # Callback
                if on_action:
                    on_action(action, result)

                self._emit(on_update, "action_result", {
                    "action_id": action.action_id,
                    "type": action.type,
                    "target": action.target,
                    "success": result.success,
                    "duration": result.duration,
                    "interpretation": result.interpretation[:200] if result.interpretation else "",
                    "parsed": result.parsed,
                })

                # === Reflect ===
                reflection = self.reflector.reflect(
                    action,
                    {"stdout": result.stdout, "error": result.error, "interpretation": result.interpretation},
                    self.state,
                )

                # Record lessons
                for lesson in reflection.lessons:
                    self.memory.add_lesson(lesson)

                self._emit(on_update, "reflection", {
                    "action_id": action.action_id,
                    "success": reflection.success,
                    "analysis": reflection.analysis,
                    "lessons": reflection.lessons,
                    "next_steps": reflection.next_steps,
                })

                # === Adapt Plan ===
                if not result.success and reflection.alternatives:
                    self._adapt_plan(action_step, reflection, result)

                # Adapt plan every 5 steps
                if step_count % 5 == 0 and self.llm:
                    self.plan = self.planner.adapt_plan(self.plan, self.state)

                # Record in memory
                self.memory.record_tool_result(
                    action.tool or action.type,
                    action.type,
                    result.success,
                    result.interpretation or result.stdout[:200],
                )

            # === Phase 4: Complete ===
            self.state.phase = Phase.COMPLETE
            self.state.elapsed_time = time.time() - start_time

            # Generate report
            report = self._generate_report()

            self._emit(on_update, "complete", {
                "phase": "complete",
                "duration": self.state.elapsed_time,
                "hosts": len(self.state.hosts),
                "vulns": len(self.state.vulns),
                "creds": len(self.state.creds),
                "shells": len(self.state.shells),
                "actions": len(self.state.actions),
            })

            result = self._build_result(start_time, brief, report)
            result.report = report
            return result

        except KeyboardInterrupt:
            self.state.phase = Phase.FAILED
            self._emit(on_update, "interrupted", {"message": "Attack interrupted by user"})
            return self._build_result(start_time, brief, "Interrupted by user")

        except Exception as e:
            logger.error(f"Agent error: {e}", exc_info=True)
            self.state.phase = Phase.FAILED
            self._emit(on_update, "error", {"message": str(e)})
            return self._build_result(start_time, brief, f"Error: {e}")

    def _adapt_plan(self, step: AttackStep, reflection: Reflection, result: ExecutionResult) -> None:
        """Adapt the plan based on reflection."""
        current_phase = self.plan.get_current_phase()
        if not current_phase:
            return

        # Add alternative steps
        for i, alt in enumerate(reflection.alternatives[:3]):
            new_step = AttackStep(
                step_id=f"adapt_{int(time.time())}_{i}",
                type=step.type,
                target=step.target,
                tool=step.fallback if step.fallback else step.tool,
                params=step.params,
                description=f"Adapted: {alt}",
                priority=2,
            )
            current_phase.steps.append(new_step)

    def _generate_report(self) -> str:
        """Generate final attack report."""
        lines = [
            f"=== Manatrix Agent Attack Report ===",
            f"Session: {self.state.session_id}",
            f"Duration: {self.state.elapsed_time:.1f}s",
            f"",
            f"--- Summary ---",
            f"Hosts discovered: {len(self.state.hosts)}",
            f"Vulnerabilities found: {len(self.state.vulns)}",
            f"Credentials obtained: {len(self.state.creds)}",
            f"Shells obtained: {len(self.state.shells)}",
            f"Compromised hosts: {len(self.state.get_compromised_hosts())}",
            f"Total actions: {len(self.state.actions)}",
            f"",
        ]

        # Hosts detail
        if self.state.hosts:
            lines.append("--- Hosts ---")
            for ip, host in self.state.hosts.items():
                status = "[COMPROMISED]" if host.compromised else ""
                services = ", ".join([f"{p}/{s}" for p, s in host.services.items()])
                lines.append(f"  {ip} {status}: {services}")

        # Vulns detail
        critical = [v for v in self.state.vulns if v.severity in ("critical", "high")]
        if critical:
            lines.append(f"\n--- Critical/High Vulnerabilities ---")
            for v in critical:
                lines.append(f"  {v.cve_id} @ {v.host}:{v.port} ({v.severity})")

        # Credentials
        if self.state.creds:
            lines.append(f"\n--- Credentials ---")
            for c in self.state.creds:
                lines.append(f"  {c.username}@{c.source} ({c.privilege})")

        # Lessons
        lessons = self.reflector.get_lessons_learned()
        if lessons:
            lines.append(f"\n--- Lessons Learned ---")
            for lesson in lessons[:10]:
                lines.append(f"  - {lesson}")

        return "\n".join(lines)

    def _build_result(self, start_time: float, brief: str, report: str = "") -> AttackResult:
        """Build the final AttackResult."""
        duration = time.time() - start_time

        return AttackResult(
            session_id=self.state.session_id if self.state else "unknown",
            brief=brief,
            success=len(self.state.get_compromised_hosts()) > 0 if self.state else False,
            duration=duration,
            phases_completed=sum(1 for p in self.plan.phases if p.completed) if self.plan else 0,
            total_actions=len(self.state.actions) if self.state else 0,
            hosts_discovered=len(self.state.hosts) if self.state else 0,
            vulns_found=len(self.state.vulns) if self.state else 0,
            creds_obtained=len(self.state.creds) if self.state else 0,
            shells_obtained=len(self.state.shells) if self.state else 0,
            compromised_hosts=self.state.get_compromised_hosts() if self.state else [],
            state=self.state,
            plan=self.plan,
            reflections=self.reflector.reflections,
            report=report,
        )

    def _emit(self, callback: Callable, event_type: str, data: dict) -> None:
        """Emit an event to the callback."""
        if callback:
            try:
                callback(event_type, data)
            except Exception as e:
                logger.warning(f"Callback error: {e}")

    def get_status(self) -> dict:
        """Get current agent status."""
        if not self.state:
            return {"status": "idle"}

        return {
            "status": "running" if self.state.phase != Phase.COMPLETE else "complete",
            "session_id": self.state.session_id,
            "phase": self.state.phase.value,
            "elapsed_time": self.state.elapsed_time,
            "hosts": len(self.state.hosts),
            "actions": len(self.state.actions),
        }
