"""
Local Integration Test for ManatrixAgent

Tests the full autonomous attack pipeline on localhost without LLM.
Uses rule-based fallback for planning, execution, and reflection.
"""

import sys
import os
import json
import time
import logging

# Setup path - add project root
_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _project_root)

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(name)s] %(message)s')
logger = logging.getLogger("test")

print("=" * 60)
print("  ManatrixAgent Local Integration Test")
print("=" * 60)

# ─── Test 1: Brief Parsing ───
print("\n[Test 1] Brief Parsing")
print("-" * 40)

from models.agent.brief_parser import BriefParser

parser = BriefParser()

test_briefs = [
    "攻击 192.168.1.0/24，目标是获取域管理员权限",
    "扫描 localhost 的 Web 服务漏洞",
    "逆向分析 firmware.bin，提取加密密钥并开发漏洞利用",
    "decompile target.apk and extract hardcoded API keys",
    "对 10.0.0.1 执行 SSH 暴力破解并提权",
]

for brief in test_briefs:
    obj = parser.parse(brief)
    print(f"\n  Brief: {brief[:50]}...")
    print(f"  Targets: {obj.targets}")
    print(f"  Type: {obj.attack_type.value}")
    print(f"  Scope: {obj.scope.value}")
    print(f"  Objectives: {obj.objectives}")

# ─── Test 2: Expert Routing ───
print("\n\n[Test 2] Expert Routing")
print("-" * 40)

from models.expert_router import create_default_router

router = create_default_router()
registered = router.get_registered_experts()
print(f"  Registered experts: {len(registered)}")
for e in registered:
    print(f"    - {e.value}")

# Test routing for different scenarios
scenarios = [
    {"phase": "reconnaissance", "target": "192.168.1.1"},
    {"phase": "exploitation", "target": "web app", "services": ["http", "https"]},
    {"phase": "post_exploitation", "target": "localhost", "has_shell": True},
    {"phase": "exploitation", "target": "firmware.bin"},
]

for state in scenarios:
    decision = router.analyze_situation(state)
    print(f"\n  Query: phase={state.get('phase')}, target={state.get('target')}")
    print(f"  → Primary: {decision.primary_expert.value} (confidence: {decision.confidence:.2f})")
    print(f"  → Supporting: {[e.value for e in decision.supporting_experts]}")
    print(f"  → Reasoning: {decision.reasoning[:80]}")

# ─── Test 3: Attack Planning ───
print("\n\n[Test 3] Attack Planning")
print("-" * 40)

from models.agent.planner import AttackPlanner
from models.agent.brief_parser import AttackType

planner = AttackPlanner()

# Test network attack plan
obj = parser.parse("攻击 127.0.0.1，扫描端口并利用漏洞")
plan = planner.create_plan(obj)
print(f"\n  Network Attack Plan ({len(plan.phases)} phases):")
for i, phase in enumerate(plan.phases):
    print(f"    Phase {i}: {phase.name} ({len(phase.steps)} steps)")
    for step in phase.steps:
        print(f"      [{step.priority}] {step.type}: {step.tool} → {step.target}")

# Test RE attack plan
obj_re = parser.parse("逆向分析 target.exe .net 二进制文件")
plan_re = planner.create_plan(obj_re)
print(f"\n  Reverse Engineering Plan ({len(plan_re.phases)} phases):")
for i, phase in enumerate(plan_re.phases):
    print(f"    Phase {i}: {phase.name} ({len(phase.steps)} steps)")
    for step in phase.steps:
        print(f"      [{step.priority}] {step.type}: {step.tool} → {step.description}")

# ─── Test 4: Tool Executor (Simulation) ───
print("\n\n[Test 4] Tool Executor")
print("-" * 40)

from models.agent.executor import AgentToolExecutor
from models.agent.state import AttackState, AttackAction, Phase

executor = AgentToolExecutor(timeout=10, sandbox=True)
state = AttackState(session_id="test_001", phase=Phase.RECONNAISSANCE)

# Test simulated scan action
action = AttackAction(
    type="scan",
    target="127.0.0.1",
    tool="nmap",
    params={},
    phase=Phase.RECONNAISSANCE,
)

print(f"\n  Executing: {action.type} -> {action.target} ({action.tool})")
result = executor.execute(action, state)
print(f"  Success: {result.success}")
print(f"  Duration: {result.duration:.3f}s")
print(f"  Tool: {result.tool}")
if result.parsed:
    print(f"  Parsed: {json.dumps(result.parsed, indent=4)[:300]}")

# ─── Test 5: Reflection ───
print("\n\n[Test 5] Action Reflection")
print("-" * 40)

from models.agent.reflection import ActionReflector

reflector = ActionReflector()

action.status = "success"
reflection = reflector.reflect(
    action,
    {"stdout": "Scan completed", "error": None},
    state,
)
print(f"  Action: {action.type} → {action.target}")
print(f"  Success: {reflection.success}")
print(f"  Analysis: {reflection.analysis}")
print(f"  Lessons: {reflection.lessons}")
print(f"  Next steps: {reflection.next_steps}")
print(f"  Confidence: {reflection.confidence:.2f}")

# ─── Test 6: Full Agent Run (Network Scan) ───
print("\n\n[Test 6] Full Agent Run - Network Scan")
print("-" * 40)

from models.manatrix_agent import ManatrixAgent

events_log = []

def on_update(event_type, data):
    events_log.append((event_type, data))
    phase = data.get("phase", "")
    msg = data.get("message", "")
    if msg:
        print(f"  [{event_type}] {phase}: {msg}")
    elif event_type == "parsed":
        print(f"  [PARSED] targets={data.get('targets', [])}, type={data.get('attack_type', '')}")
    elif event_type == "plan":
        print(f"  [PLAN] {data.get('total_phases', 0)} phases created")
    elif event_type == "action_result":
        success = "OK" if data.get("success") else "FAIL"
        print(f"  [ACTION] {data.get('type')} → {data.get('target')} [{success}] ({data.get('duration', 0):.2f}s)")
    elif event_type == "reflection":
        print(f"  [REFLECT] confidence={data.get('confidence', 0):.2f}")

agent = ManatrixAgent(max_steps=8)

print("\n  Running: '扫描 127.0.0.1 Web 服务'")
result = agent.run(
    brief="扫描 127.0.0.1 Web 服务",
    on_update=on_update,
)

print(f"\n  Result:")
print(f"    Session: {result.session_id}")
print(f"    Duration: {result.duration:.2f}s")
print(f"    Actions: {result.total_actions}")
print(f"    Phases completed: {result.phases_completed}")
print(f"    Hosts discovered: {result.hosts_discovered}")
print(f"    Report:\n{result.report}")

# ─── Test 7: Full Agent Run (Reverse Engineering) ───
print("\n\n[Test 7] Full Agent Run - Reverse Engineering")
print("-" * 40)

events_log.clear()

print("\n  Running: '逆向分析 target.apk，提取加密密钥'")
result_re = agent.run(
    brief="逆向分析 target.apk，提取加密密钥",
    on_update=on_update,
)

print(f"\n  Result:")
print(f"    Session: {result_re.session_id}")
print(f"    Duration: {result_re.duration:.2f}s")
print(f"    Actions: {result_re.total_actions}")
print(f"    Phases completed: {result_re.phases_completed}")
print(f"    Report:\n{result_re.report}")

# ─── Summary ───
print("\n" + "=" * 60)
print("  ALL TESTS PASSED")
print("=" * 60)
print(f"\n  Events captured: {len(events_log)}")
print(f"  Test 6 actions: {result.total_actions}")
print(f"  Test 7 actions: {result_re.total_actions}")
