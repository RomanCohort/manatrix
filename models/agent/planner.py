"""
Attack Planner

Uses LLM to generate phased attack plans from objectives.
Similar to Claude Code's task planning loop.
"""

import logging
import json
import time
from dataclasses import dataclass, field
from typing import List, Dict, Optional

from models.agent.brief_parser import AttackObjectives
from models.agent.state import Phase, AttackState

logger = logging.getLogger(__name__)


@dataclass
class AttackStep:
    """A single step in an attack phase."""
    step_id: str
    type: str                  # scan, exploit, brute, enum, move, dump, exfil
    target: str                # IP, URL, service
    tool: Optional[str]        # suggested tool
    params: Dict = field(default_factory=dict)
    description: str = ""
    expected_result: str = ""
    fallback: Optional[str] = None
    priority: int = 1          # 1=high, 2=medium, 3=low
    completed: bool = False

    def to_dict(self) -> dict:
        return {
            "step_id": self.step_id,
            "type": self.type,
            "target": self.target,
            "tool": self.tool,
            "params": self.params,
            "description": self.description,
            "priority": self.priority,
            "completed": self.completed,
        }


@dataclass
class AttackPhase:
    """A phase in the attack plan."""
    phase_id: int
    name: str
    objective: str
    steps: List[AttackStep] = field(default_factory=list)
    phase_type: Phase = Phase.RECONNAISSANCE
    success_criteria: str = ""
    fallback_strategy: str = ""
    completed: bool = False

    def get_next_step(self) -> Optional[AttackStep]:
        """Get the next uncompleted step."""
        pending = [s for s in self.steps if not s.completed]
        if not pending:
            return None
        # Sort by priority
        pending.sort(key=lambda s: s.priority)
        return pending[0]


@dataclass
class AttackPlan:
    """Complete attack plan."""
    plan_id: str
    objective_summary: str
    phases: List[AttackPhase] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    current_phase_idx: int = 0

    def get_current_phase(self) -> Optional[AttackPhase]:
        """Get the current active phase."""
        if 0 <= self.current_phase_idx < len(self.phases):
            return self.phases[self.current_phase_idx]
        return None

    def advance_phase(self) -> bool:
        """Move to the next phase."""
        if self.current_phase_idx < len(self.phases) - 1:
            self.phases[self.current_phase_idx].completed = True
            self.current_phase_idx += 1
            return True
        return False

    def get_next_action(self) -> Optional[AttackStep]:
        """Get the next action to execute."""
        phase = self.get_current_phase()
        if phase:
            return phase.get_next_step()
        return None

    def to_dict(self) -> dict:
        return {
            "plan_id": self.plan_id,
            "objective_summary": self.objective_summary,
            "total_phases": len(self.phases),
            "current_phase": self.current_phase_idx,
            "phases": [
                {
                    "name": p.name,
                    "objective": p.objective,
                    "steps": len(p.steps),
                    "completed": p.completed,
                }
                for p in self.phases
            ],
        }


PLAN_GENERATION_PROMPT = """你是一位资深的渗透测试策略专家。请根据以下信息制定攻击计划。

攻击目标: {targets}
攻击类型: {attack_type}
具体目标: {objectives}
约束条件: {constraints}
当前已知信息: {known_info}

请制定一个分阶段的攻击计划，返回JSON格式:
{{
    "phases": [
        {{
            "name": "阶段名称",
            "objective": "阶段目标",
            "phase_type": "reconnaissance/vulnerability_scan/exploitation/post_exploitation/lateral_movement/data_exfiltration",
            "success_criteria": "成功标准",
            "fallback_strategy": "备用策略",
            "steps": [
                {{
                    "step_id": "step_1",
                    "type": "scan/exploit/brute/enum/move/dump/exfil",
                    "target": "目标",
                    "tool": "推荐工具",
                    "params": {{"key": "value"}},
                    "description": "步骤描述",
                    "expected_result": "预期结果",
                    "fallback": "备用方案",
                    "priority": 1
                }}
            ]
        }}
    ]
}}

计划原则：
1. 每个阶段目标明确可验证
2. 步骤从被动到主动
3. 每个步骤有备用方案
4. 优先利用已知漏洞
5. 考虑规避检测
6. 合理安排攻击顺序
"""

ADAPT_PLAN_PROMPT = """根据最新攻击结果，调整后续计划。

当前状态:
{state_summary}

最近执行的操作:
{recent_actions}

请分析当前状态并调整后续计划，返回JSON:
{{
    "analysis": "当前情况分析",
    "should_change_phase": true/false,
    "new_steps": [
        {{
            "step_id": "adapt_step_X",
            "type": "...",
            "target": "...",
            "tool": "...",
            "params": {{}},
            "description": "...",
            "priority": 1
        }}
    ],
    "skip_steps": ["应跳过的步骤ID"],
    "lessons": "经验教训"
}}
"""


class AttackPlanner:
    """Generates and adapts attack plans using LLM."""

    def __init__(self, llm_provider=None):
        self.llm = llm_provider

    def create_plan(self, objectives: AttackObjectives, state: AttackState = None) -> AttackPlan:
        """Generate an attack plan from objectives."""
        plan_id = f"plan_{int(time.time())}"

        if self.llm:
            try:
                return self._create_plan_with_llm(objectives, state, plan_id)
            except Exception as e:
                logger.warning(f"LLM planning failed, using rule-based: {e}")

        return self._create_rule_based_plan(objectives, plan_id)

    def adapt_plan(self, plan: AttackPlan, state: AttackState) -> AttackPlan:
        """Adapt the plan based on current state and results."""
        if not self.llm:
            return plan

        try:
            return self._adapt_plan_with_llm(plan, state)
        except Exception as e:
            logger.warning(f"Plan adaptation failed: {e}")
            return plan

    def _create_plan_with_llm(self, objectives: AttackObjectives, state: AttackState, plan_id: str) -> AttackPlan:
        """Use LLM to generate attack plan."""
        known_info = ""
        if state:
            known_info = state.get_state_for_llm()

        prompt = PLAN_GENERATION_PROMPT.format(
            targets=", ".join(objectives.targets) if objectives.targets else "待定",
            attack_type=objectives.attack_type.value,
            objectives=", ".join(objectives.objectives) if objectives.objectives else "全面渗透",
            constraints=", ".join(objectives.constraints) if objectives.constraints else "无特殊限制",
            known_info=known_info or "无已知信息",
        )

        response = self.llm.call(
            [{"role": "user", "content": prompt}],
            use_json_mode=False,
        )

        content = response.content.strip()
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            content = content.split("```")[1].split("```")[0]

        data = json.loads(content.strip())
        return self._parse_plan(data, objectives, plan_id)

    def _parse_plan(self, data: dict, objectives: AttackObjectives, plan_id: str) -> AttackPlan:
        """Parse LLM response into AttackPlan."""
        phases = []
        for i, phase_data in enumerate(data.get("phases", [])):
            phase_type_str = phase_data.get("phase_type", "reconnaissance")
            try:
                phase_type = Phase(phase_type_str)
            except ValueError:
                phase_type = Phase.RECONNAISSANCE

            steps = []
            for step_data in phase_data.get("steps", []):
                steps.append(AttackStep(
                    step_id=step_data.get("step_id", f"step_{i}_{len(steps)}"),
                    type=step_data.get("type", "scan"),
                    target=step_data.get("target", ""),
                    tool=step_data.get("tool"),
                    params=step_data.get("params", {}),
                    description=step_data.get("description", ""),
                    expected_result=step_data.get("expected_result", ""),
                    fallback=step_data.get("fallback"),
                    priority=step_data.get("priority", 2),
                ))

            phases.append(AttackPhase(
                phase_id=i,
                name=phase_data.get("name", f"Phase {i+1}"),
                objective=phase_data.get("objective", ""),
                steps=steps,
                phase_type=phase_type,
                success_criteria=phase_data.get("success_criteria", ""),
                fallback_strategy=phase_data.get("fallback_strategy", ""),
            ))

        return AttackPlan(
            plan_id=plan_id,
            objective_summary=", ".join(objectives.objectives) if objectives.objectives else "Full penetration test",
            phases=phases,
        )

    def _create_rule_based_plan(self, objectives: AttackObjectives, plan_id: str) -> AttackPlan:
        """Rule-based plan generation fallback."""
        targets = objectives.targets or ["TARGET"]

        # Check if this is a reverse engineering attack
        if objectives.attack_type.value == "reverse_engineering":
            return self._create_re_plan(objectives, targets, plan_id)

        # Check if this is a hardware attack
        if objectives.attack_type.value == "hardware":
            return self._create_hw_plan(objectives, targets, plan_id)

        phases = [
            AttackPhase(
                phase_id=0,
                name="侦察阶段",
                objective="发现目标网络拓扑和开放服务",
                phase_type=Phase.RECONNAISSANCE,
                steps=[
                    AttackStep("recon_1", "scan", targets[0], "nmap",
                              {"scan_type": "service_version"}, "端口和服务扫描", "开放端口列表", priority=1),
                    AttackStep("recon_2", "scan", targets[0], "nuclei",
                              {"templates": "vulnerabilities"}, "漏洞扫描", "CVE列表", priority=2),
                ],
                success_criteria="发现至少一个开放服务",
                fallback_strategy="扩大扫描范围",
            ),
            AttackPhase(
                phase_id=1,
                name="漏洞利用阶段",
                objective="利用发现的漏洞获取初始访问",
                phase_type=Phase.EXPLOITATION,
                steps=[
                    AttackStep("exploit_1", "exploit", targets[0], "metasploit",
                              {}, "尝试利用高危漏洞", "获取shell", priority=1),
                    AttackStep("exploit_2", "brute", targets[0], "hydra",
                              {"service": "ssh"}, "SSH暴力破解", "获取凭据",
                              fallback="尝试其他服务", priority=2),
                ],
                success_criteria="获取至少一个shell",
                fallback_strategy="尝试其他攻击向量",
            ),
            AttackPhase(
                phase_id=2,
                name="后渗透阶段",
                objective="权限提升和凭据收集",
                phase_type=Phase.POST_EXPLOITATION,
                steps=[
                    AttackStep("post_1", "enum", targets[0], "linpeas",
                              {}, "权限提升检查", "提权向量", priority=1),
                    AttackStep("post_2", "dump", targets[0], "mimikatz",
                              {}, "凭据转储", "获取凭据", priority=2),
                ],
                success_criteria="获取管理员权限",
                fallback_strategy="尝试其他提权方法",
            ),
            AttackPhase(
                phase_id=3,
                name="横向移动阶段",
                objective="扩展到其他主机",
                phase_type=Phase.LATERAL_MOVEMENT,
                steps=[
                    AttackStep("lateral_1", "move", "internal", "crackmapexec",
                              {}, "使用获取的凭据扫描内网", "发现可达主机", priority=1),
                ],
                success_criteria="攻陷多台主机",
                fallback_strategy="建立隧道继续渗透",
            ),
        ]

        return AttackPlan(
            plan_id=plan_id,
            objective_summary=", ".join(objectives.objectives) or "Full penetration test",
            phases=phases,
        )

    def _create_hw_plan(self, objectives: AttackObjectives, targets: List[str], plan_id: str) -> AttackPlan:
        """Create a hardware security attack plan."""
        target = targets[0] if targets else "TARGET"
        target_lower = target.lower()

        # Detect hardware sub-type
        hw_keywords = {
            "side_channel": ["侧信道", "side channel", "功耗", "power", "cpa", "dpa", "em", "电磁"],
            "fault_injection": ["故障注入", "fault", "glitch", "电压", "时钟"],
            "jtag_debug": ["jtag", "swd", "调试口", "debug"],
            "uart_serial": ["uart", "serial", "串口", "console"],
            "rfid_nfc": ["rfid", "nfc", "mifare", "proxmark", "门禁"],
            "automotive": ["can", "obd", "汽车", "automotive", "车载"],
            "pcb_reverse": ["pcb", "电路板", "board", "走线"],
            "chip_extraction": ["芯片", "chip", "mcu", "提取", "flash"],
        }

        hw_type = "general"
        objectives_text = " ".join(objectives.objectives).lower() + " " + target_lower
        for htype, keywords in hw_keywords.items():
            if any(k in objectives_text for k in keywords):
                hw_type = htype
                break

        phases = []

        # Phase 0: Hardware Reconnaissance
        phases.append(AttackPhase(
            phase_id=0,
            name="硬件侦察与接口识别",
            objective="识别目标硬件接口、芯片型号和攻击面",
            phase_type=Phase.RECONNAISSANCE,
            steps=[
                AttackStep("hw_recon_1", "scan", target, "microscope",
                          {}, "视觉检查识别芯片型号和封装", "芯片型号/封装类型", priority=1),
                AttackStep("hw_recon_2", "scan", target, "JTAGulator",
                          {"mode": "enumerate"}, "枚举JTAG/SWD调试引脚", "调试接口配置", priority=1),
                AttackStep("hw_recon_3", "scan", target, "minicom",
                          {"baudrate": "auto"}, "扫描UART串口控制台", "波特率/Shell访问", priority=1),
                AttackStep("hw_recon_4", "scan", target, "flashrom",
                          {"operation": "detect"}, "检测SPI Flash芯片", "Flash型号/容量", priority=2),
            ],
            success_criteria="识别至少一个可用硬件接口",
            fallback_strategy="尝试非侵入式分析或PCB走线追踪",
        ))

        # Phase 1: Interface Access & Firmware Extraction
        if hw_type in ("jtag_debug", "chip_extraction", "general"):
            phases.append(AttackPhase(
                phase_id=1,
                name="接口访问与固件提取",
                objective="通过调试接口获取芯片访问权限并提取固件",
                phase_type=Phase.EXPLOITATION,
                steps=[
                    AttackStep("hw_access_1", "enum", target, "openocd",
                              {"interface": "jtag"}, "通过JTAG连接芯片", "调试连接", priority=1),
                    AttackStep("hw_access_2", "enum", target, "flashrom",
                              {"operation": "read"}, "读取SPI Flash固件", "固件镜像", priority=1),
                    AttackStep("hw_access_3", "scan", target, "binwalk",
                              {"extract": True}, "提取固件文件系统", "文件系统/配置文件", priority=2),
                    AttackStep("hw_access_4", "scan", target, "strings",
                              {}, "提取固件中的敏感字符串", "默认密码/API密钥", priority=2),
                ],
                success_criteria="成功提取固件或获取调试访问",
                fallback_strategy="尝试chip-off或直接eMMC读取",
            ))

        # Phase 1b: Side-Channel Attack (for crypto targets)
        elif hw_type == "side_channel":
            phases.append(AttackPhase(
                phase_id=1,
                name="侧信道分析攻击",
                objective="通过功耗/电磁/时序侧信道提取密钥",
                phase_type=Phase.EXPLOITATION,
                steps=[
                    AttackStep("hw_sca_1", "analyze", target, "chipwhisperer",
                              {"operation": "trace_collection"}, "采集功耗轨迹", "功耗Trace数据", priority=1),
                    AttackStep("hw_sca_2", "analyze", target, "chipwhisperer",
                              {"method": "CPA", "target": "AES"}, "相关功耗分析(CPA)", "AES密钥候选", priority=1),
                    AttackStep("hw_sca_3", "analyze", target, "EM_probes",
                              {"frequency": "1MHz-1GHz"}, "电磁辐射分析", "EM轨迹数据", priority=2),
                    AttackStep("hw_sca_4", "analyze", target, "timing_attack",
                              {}, "时序差异分析", "密钥操作时间差异", priority=2),
                ],
                success_criteria="提取出完整密钥",
                fallback_strategy="切换攻击算法或尝试故障注入",
            ))

        # Phase 1c: Fault Injection
        elif hw_type == "fault_injection":
            phases.append(AttackPhase(
                phase_id=1,
                name="故障注入攻击",
                objective="通过电压/时钟/EM故障注入绕过安全机制",
                phase_type=Phase.EXPLOITATION,
                steps=[
                    AttackStep("hw_fi_1", "analyze", target, "voltage_glitch",
                              {"voltage_drop": "0.5V", "timing": "precise"}, "电压故障注入", "安全检查绕过", priority=1),
                    AttackStep("hw_fi_2", "analyze", target, "clock_glitch",
                              {"frequency": "skip"}, "时钟故障注入", "指令跳过", priority=1),
                    AttackStep("hw_fi_3", "analyze", target, "EM_fault_injection",
                              {}, "电磁故障注入", "寄存器翻转", priority=2),
                ],
                success_criteria="绕过安全检查或触发异常行为",
                fallback_strategy="调整故障参数或换用激光故障注入",
            ))

        # Phase 1d: RFID/NFC Attack
        elif hw_type == "rfid_nfc":
            phases.append(AttackPhase(
                phase_id=1,
                name="RFID/NFC攻击",
                objective="分析、破解和克隆RFID/NFC标签",
                phase_type=Phase.EXPLOITATION,
                steps=[
                    AttackStep("hw_rfid_1", "scan", target, "proxmark3",
                              {"mode": "hw tune"}, "读取RFID标签信息", "标签类型/UID", priority=1),
                    AttackStep("hw_rfid_2", "brute", target, "mfoc",
                              {"nested_attack": True}, "MIFARE Classic Nested攻击", "密钥A/B", priority=1),
                    AttackStep("hw_rfid_3", "brute", target, "mfcuk",
                              {}, "MIFARE Darkside攻击", "未知密钥", priority=2),
                    AttackStep("hw_rfid_4", "exploit", target, "proxmark3",
                              {"operation": "clone"}, "克隆标签到空白卡", "克隆卡", priority=1),
                ],
                success_criteria="获取标签密钥并成功克隆",
                fallback_strategy="尝试中继攻击或逻辑分析",
            ))

        # Phase 1e: Automotive / CAN Bus Attack
        elif hw_type == "automotive":
            phases.append(AttackPhase(
                phase_id=1,
                name="汽车总线攻击",
                objective="分析CAN总线协议并注入消息",
                phase_type=Phase.EXPLOITATION,
                steps=[
                    AttackStep("hw_auto_1", "scan", target, "cansniffer",
                              {"interface": "socketcan"}, "嗅探CAN总线通信", "CAN帧数据库", priority=1),
                    AttackStep("hw_auto_2", "scan", target, "candump",
                              {}, "记录CAN流量", "完整CAN日志", priority=1),
                    AttackStep("hw_auto_3", "analyze", target, "canmatrix",
                              {}, "解析CAN信号定义", "信号物理值映射", priority=2),
                    AttackStep("hw_auto_4", "exploit", target, "cansend",
                              {"fuzzing": True}, "CAN消息注入/模糊测试", "异常ECU响应", priority=1),
                ],
                success_criteria="识别关键ECU控制信号",
                fallback_strategy="尝试OBD-II诊断接口攻击",
            ))

        # Phase 2: Hardware Vulnerability Exploitation
        if not phases or len(phases) < 2:
            phases.append(AttackPhase(
                phase_id=max(p.phase_id for p in phases) + 1 if phases else 1,
                name="硬件漏洞利用",
                objective="利用发现的硬件漏洞实现攻击目标",
                phase_type=Phase.POST_EXPLOITATION,
                steps=[
                    AttackStep("hw_exploit_1", "analyze", target, "openocd",
                              {"operation": "halt"}, "暂停MCU执行获取完全控制", "MCU控制权", priority=1),
                    AttackStep("hw_exploit_2", "dump", target, "openocd",
                              {"operation": "dump"}, "转储MCU Flash内容", "完整固件", priority=1),
                    AttackStep("hw_exploit_3", "analyze", target, "ghidra",
                              {}, "逆向分析提取的固件", "漏洞/后门", priority=2),
                ],
                success_criteria="获取固件或实现物理访问绕过",
                fallback_strategy="考虑侵入式攻击(chip-off/FIB)",
            ))

        return AttackPlan(
            plan_id=plan_id,
            objective_summary=", ".join(objectives.objectives) or "Hardware security assessment",
            phases=phases,
        )

    def _create_re_plan(self, objectives: AttackObjectives, targets: List[str], plan_id: str) -> AttackPlan:
        """Create a reverse engineering attack plan."""
        target = targets[0]
        target_lower = target.lower()

        phases = []

        # Phase 0: File Identification & Strings Extraction
        phases.append(AttackPhase(
            phase_id=0,
            name="文件识别与信息提取",
            objective="识别目标文件类型、架构和保护机制",
            phase_type=Phase.RECONNAISSANCE,
            steps=[
                AttackStep("re_file_1", "scan", target, "file",
                          {}, "识别文件类型和架构", "文件格式信息", priority=1),
                AttackStep("re_file_2", "scan", target, "strings",
                          {}, "提取可读字符串", "URL、IP、加密常量", priority=1),
                AttackStep("re_file_3", "scan", target, "checksec",
                          {}, "检查二进制保护机制", "NX/ASLR/Canary/PIE状态", priority=1),
                AttackStep("re_file_4", "scan", target, "binwalk",
                          {}, "扫描嵌入文件和签名", "嵌入的文件系统/证书", priority=2),
            ],
            success_criteria="确认文件类型和保护机制",
            fallback_strategy="尝试多种文件分析工具",
        ))

        # Phase 1: Static Analysis & Decompilation
        # Choose tool based on target type
        decompile_tool = "ghidra"
        decompile_desc = "使用Ghidra反编译二进制"
        decompile_cmd = "analyzeHeadless"
        if target_lower.endswith(".apk"):
            decompile_tool = "jadx"
            decompile_desc = "使用jadx反编译APK"
        elif target_lower.endswith((".dll", ".exe")):
            decompile_tool = "dnspy"
            decompile_desc = "使用dnSpy反编译.NET程序集"
        elif target_lower.endswith((".jar", ".class")):
            decompile_tool = "cfr"
            decompile_desc = "使用CFR反编译Java"
        elif target_lower.endswith((".bin", ".fw", ".img")):
            decompile_tool = "binwalk"
            decompile_desc = "提取固件文件系统"

        phases.append(AttackPhase(
            phase_id=1,
            name="静态分析与反编译",
            objective="反编译目标，恢复源码并分析程序逻辑",
            phase_type=Phase.EXPLOITATION,
            steps=[
                AttackStep("re_static_1", "decompile", target, decompile_tool,
                          {"output_dir": "decompiled"}, decompile_desc, "反编译源码", priority=1),
                AttackStep("re_static_2", "disassemble", target, "radare2",
                          {}, "控制流分析", "函数调用图", priority=2),
                AttackStep("re_static_3", "analyze", target, "ghidra",
                          {}, "交叉引用分析", "关键数据引用", priority=2),
                AttackStep("re_static_4", "scan", target, "strings",
                          {}, "搜索加密常量和硬编码凭据", "AES S-Box/MD5常量", priority=2),
            ],
            success_criteria="获取关键函数和逻辑的理解",
            fallback_strategy="使用替代反编译器或手动汇编分析",
        ))

        # Phase 2: Dynamic Analysis & Debugging
        phases.append(AttackPhase(
            phase_id=2,
            name="动态分析与调试",
            objective="运行时行为分析和漏洞验证",
            phase_type=Phase.POST_EXPLOITATION,
            steps=[
                AttackStep("re_dynamic_1", "analyze", target, "gdb",
                          {"commands": "info functions; checksec"}, "调试运行，分析内存布局", "内存映射", priority=1),
                AttackStep("re_dynamic_2", "analyze", target, "frida",
                          {"package": "target", "script": "trace.js"}, "运行时函数Hook和参数追踪", "函数参数/返回值", priority=1),
                AttackStep("re_dynamic_3", "fuzz", target, "afl",
                          {"input": "seeds", "output": "fuzz_out"}, "模糊测试发现崩溃", "崩溃样本", priority=2,
                          fallback="尝试libfuzzer"),
            ],
            success_criteria="发现程序崩溃点或关键逻辑",
            fallback_strategy="增加Fuzzing时间或切换Fuzzer",
        ))

        # Phase 3: Vulnerability Analysis & Exploit Development
        phases.append(AttackPhase(
            phase_id=3,
            name="漏洞利用开发",
            objective="构造Exploit实现代码执行",
            phase_type=Phase.LATERAL_MOVEMENT,
            steps=[
                AttackStep("re_exploit_1", "reverse", target, "ropgadget",
                          {}, "搜索ROP Gadgets", "可用Gadgets列表", priority=1),
                AttackStep("re_exploit_2", "reverse", target, "pwntools",
                          {"script": "exploit.py"}, "开发Exploit脚本", "Exploit POC",
                          fallback="使用msfvenom生成shellcode", priority=1),
                AttackStep("re_exploit_3", "reverse", target, "angr",
                          {}, "符号执行求解路径约束", "到达目标函数的输入",
                          fallback="手动构造输入", priority=2),
            ],
            success_criteria="成功执行任意代码",
            fallback_strategy="尝试其他漏洞类型或1-Day利用",
        ))

        return AttackPlan(
            plan_id=plan_id,
            objective_summary=", ".join(objectives.objectives) or "Reverse engineering analysis",
            phases=phases,
        )

    def _adapt_plan_with_llm(self, plan: AttackPlan, state: AttackState) -> AttackPlan:
        """Adapt plan based on current state."""
        recent = state.actions[-5:] if state.actions else []
        recent_str = "\n".join([
            f"  - {a.type} -> {a.target} ({a.status}): {a.result or 'N/A'}"
            for a in recent
        ])

        prompt = ADAPT_PLAN_PROMPT.format(
            state_summary=state.get_state_for_llm(),
            recent_actions=recent_str or "No actions yet",
        )

        response = self.llm.call(
            [{"role": "user", "content": prompt}],
            use_json_mode=False,
        )

        content = response.content.strip()
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            content = content.split("```")[1].split("```")[0]

        data = json.loads(content.strip())

        # Apply adaptations
        current_phase = plan.get_current_phase()
        if current_phase:
            # Skip steps
            for step_id in data.get("skip_steps", []):
                for step in current_phase.steps:
                    if step.step_id == step_id:
                        step.completed = True

            # Add new steps
            for step_data in data.get("new_steps", []):
                current_phase.steps.append(AttackStep(
                    step_id=step_data.get("step_id", f"adapt_{int(time.time())}"),
                    type=step_data.get("type", "scan"),
                    target=step_data.get("target", ""),
                    tool=step_data.get("tool"),
                    params=step_data.get("params", {}),
                    description=step_data.get("description", ""),
                    priority=step_data.get("priority", 2),
                ))

            # Advance phase if needed
            if data.get("should_change_phase", False):
                plan.advance_phase()

        return plan
