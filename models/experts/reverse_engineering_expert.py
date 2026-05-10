"""
Reverse Engineering & Decompilation Attack Expert

Expert in binary reverse engineering, decompilation, malware analysis,
firmware extraction, patch diffing, and exploit development from RE.
Covers x86/x64/ARM/MIPS architectures and Windows/Linux/macOS/Android/iOS platforms.
"""

import logging
from typing import List, Dict, Optional

from models.experts.base import PenTestExpert, ExpertAdvice, ExpertType

logger = logging.getLogger(__name__)


class ReverseEngineeringExpert(PenTestExpert):
    """Expert in reverse engineering and decompilation attacks."""

    TOOLS = [
        # Disassemblers & Decompilers
        "ghidra", "ida_pro", "radare2", "rizin", "cutter", "binary_ninja",
        "hopper", "retdec", "snowman",
        # Android/iOS RE
        "jadx", "apktool", "dex2jar", "smali", "frida", "objection",
        "classdump", "dsdump", "clutch", "bfinject",
        # .NET/Java RE
        "dnspy", "ilspy", "dotpeek", "reflexil", "mono_decompile",
        "procyon", "cfr", "fernflower",
        # Binary Analysis
        "strings", "file", "objdump", "readelf", "nm", "ltrace", "strace",
        "binwalk", "firmware-mod-kit", "blobtools",
        # Debugging
        "gdb", "gdb-multiarch", "pwndbg", "gef", "peda", "x64dbg", "windbg",
        "lldb", "r2pipe",
        # Fuzzing & Crash Analysis
        "afl", "afl-plus-plus", "libfuzzer", "honggfuzz", "sydr",
        "crashwalk", "exploitable",
        # Patch Diffing & BinDiff
        "bindiff", "diaphora", "cobalt_strike_srdi",
        # Shellcode & ROP
        "pwntools", "ropgadget", "ropper", "rp++", "shellnoob",
        "msfvenom", "veil",
        # Crypto RE
        "findcrypt", "signsrch", "klee", "angr", "z3", "smt_solver",
        # Memory Forensics
        "volatility", "rekall", "memdump", "gdb-pt-dump",
    ]

    SYSTEM_PROMPT = """你是一位资深的逆向工程与反编译攻击专家。

专长领域：
- 二进制程序逆向分析（x86/x64/ARM/MIPS架构）
- 反编译与源码恢复（C/C++、.NET、Java、Android APK）
- 固件提取与分析（路由器、IoT设备、嵌入式系统）
- 漏洞挖掘（栈溢出、堆溢出、格式化字符串、UAF、竞态条件）
- Exploit开发（ROP链构造、Shellcode编写、堆利用）
- 加密算法识别与绕过（对称/非对称加密、自定义混淆）
- 补丁对比与1-Day分析
- 反调试/反虚拟机检测绕过
- 混淆代码分析与去混淆
- 内存取证与运行时分析

工具集：

【反汇编与反编译】
- ghidra: NSA开源反编译器，支持多架构，含脚本/扩展生态
- ida_pro: 业界标准反汇编器，支持FLIRT签名、Hex-Rays反编译
- radare2/rizin: 开源逆向框架， Cutter图形界面
- binary_ninja: 现代化二进制分析平台，API丰富
- retdec: RetDec开源反编译器（基于LLVM）
- hopper: macOS/Linux反汇编器

【Android逆向】
- jadx: Dex到Java反编译器，Android RE标配
- apktool: APK解包/重打包工具
- dex2jar: Dex转Jar工具
- smali: Dalvik字节码汇编/反汇编
- frida: 动态插桩工具，运行时Hook
- objection: 基于Frida的运行时探索工具包

【.NET/Java逆向】
- dnspy: .NET调试器+反编译器，可修改IL代码
- ilspy: 开源.NET反编译器
- reflexil: .NET程序集编辑器
- procyon/cfr/fernflower: Java反编译器

【二进制静态分析】
- strings: 提取可读字符串
- file: 识别文件类型
- objdump/readelf/nm: ELF分析工具
- binwalk: 固件分析与提取
- ltrace/strace: 库调用/系统调用追踪

【调试器】
- gdb/pwndbg/gef/peda: Linux调试增强工具链
- x64dbg/windbg: Windows调试器
- lldb: macOS/LLVM调试器

【Fuzzing】
- afl/afl-plus-plus: 美国模糊_loop模糊测试
- libfuzzer/honggfuzz: 覆盖率引导Fuzzing
- sydr: 符号执行辅助Fuzzing

【Exploit开发】
- pwntools: CTF/Exploit开发框架
- ropgadget/ropper: ROP Gadgets搜索
- angr/z3: 符号执行与约束求解
- msfvenom: Shellcode生成器

【补丁对比】
- bindiff: IDA插件，二进制Diff
- diaphora: 开源函数级Diff工具

攻击原则：
1. 先静态分析再动态调试
2. 识别程序保护机制（NX/ASLR/Canary/PIE/RELRO）
3. 定位关键函数和加密算法
4. 寻找输入验证漏洞
5. 构造精确的Exploit
6. 验证漏洞可利用性
"""

    def __init__(self, llm_provider=None, rag_retriever=None):
        super().__init__(
            expert_type=ExpertType.REVERSE_ENGINEERING,
            llm_provider=llm_provider,
            rag_retriever=rag_retriever,
            tools=self.TOOLS,
        )

    def get_prompt_template(self) -> str:
        return self.SYSTEM_PROMPT

    def _get_techniques(self) -> List[str]:
        return [
            "T1589",  # Gather Victim Network Information
            "T1059",  # Command and Scripting Interpreter
            "T1027",  # Obfuscated Files or Information
            "T1140",  # Deobfuscate/Decode Files or Information
            "T1036",  # Masquerading
            "T1027.007",  # Dynamic API Resolution
            "T1027.009",  # Embedded Payloads
            "T1055",  # Process Injection
            "T1574",  # Hijack Execution Flow
            "T1562",  # Impair Defenses
            "T1014",  # Rootkit
            "T1218",  # System Binary Proxy Execution
            "T1127",  # Trusted Developer Utilities Proxy Execution
            "T1554",  # Compromise Client Software Binary
            "T1195",  # Supply Chain Compromise
        ]

    def _get_required_inputs(self) -> List[str]:
        return [
            "target_binary", "binary_path", "architecture",
            "file_type", "platform", "protections",
            "entry_point", "strings_output",
        ]

    def _get_outputs(self) -> List[str]:
        return [
            "decompiled_code", "vulnerability_report", "exploit_script",
            "function_map", "crypto_algorithm", "memory_layout",
            "rop_chain", "shellcode", "patch_diff",
        ]

    def analyze(self, state: dict, context: dict = None) -> ExpertAdvice:
        """Analyze a reverse engineering scenario."""
        # Rule-based quick analysis
        tools = []
        actions = []
        warnings = []
        cves = []

        # Determine what type of RE based on context
        target = state.get("target", "") if state else ""
        target_lower = (target or "").lower()
        services = state.get("services", []) if state else []
        services_str = " ".join(str(s) for s in services).lower()

        context_info = context or {}
        file_info = context_info.get("file_type", "").lower()
        binary_path = context_info.get("binary_path", "")

        # Scenario detection and tool selection
        if any(ext in target_lower for ext in [".apk", "android"]):
            tools = ["jadx", "apktool", "dex2jar", "frida", "objection"]
            actions = [
                {"action": "decompile_apk", "tool": "jadx",
                 "command": f"jadx -d output {target}",
                 "description": "使用jadx反编译APK文件"},
                {"action": "unpack_apk", "tool": "apktool",
                 "command": f"apktool d {target} -o unpacked",
                 "description": "使用apktool解包APK资源"},
                {"action": "runtime_hook", "tool": "frida",
                 "command": f"frida -U -f com.target.app -l hook.js",
                 "description": "使用Frida进行运行时Hook"},
            ]
            warnings.append("注意Androidmanifest.xml中的危险权限声明")

        elif any(ext in target_lower for ext in [".dll", ".exe"]) or ".net" in services_str:
            tools = ["dnspy", "ilspy", "dotpeek", "reflexil"]
            actions = [
                {"action": "decompile_dotnet", "tool": "dnspy",
                 "command": f"dnspy {target}",
                 "description": "使用dnSpy反编译.NET程序集"},
                {"action": "analyze_il", "tool": "ilspy",
                 "command": f"ilspycmd {target}",
                 "description": "使用ILSpy反编译为C#代码"},
            ]
            warnings.append("检查是否使用了混淆工具(ConfuserEx, dotfuscator等)")

        elif any(ext in target_lower for ext in [".jar", ".class"]) or "java" in services_str:
            tools = ["procyon", "cfr", "fernflower", "jadx"]
            actions = [
                {"action": "decompile_java", "tool": "cfr",
                 "command": f"java -jar cfr.jar {target} --outputdir output",
                 "description": "使用CFR反编译Java类文件"},
                {"action": "analyze_jar", "tool": "procyon",
                 "command": f"java -jar procyon.jar {target}",
                 "description": "使用Procyon反编译JAR"},
            ]

        elif any(ext in target_lower for ext in [".bin", ".fw", ".img", ".firmware"]):
            tools = ["binwalk", "firmware-mod-kit", "ghidra", "radare2"]
            actions = [
                {"action": "extract_firmware", "tool": "binwalk",
                 "command": f"binwalk -e {target}",
                 "description": "使用binwalk提取固件文件系统"},
                {"action": "analyze_firmware", "tool": "ghidra",
                 "command": f"analyzeHeadless /tmp/project Firmware -import {target}",
                 "description": "使用Ghidra分析固件二进制"},
            ]
            warnings.append("检查固件是否加密或使用自定义压缩")

        elif any(kw in target_lower for kw in ["elf", "linux", "binary", "executable"]):
            tools = ["ghidra", "gdb", "pwndbg", "pwntools", "radare2", "ropgadget", "checksec"]
            actions = [
                {"action": "check_protections", "tool": "checksec",
                 "command": f"checksec --file={target}",
                 "description": "检查二进制保护机制(NX/ASLR/Canary/PIE)"},
                {"action": "static_analysis", "tool": "ghidra",
                 "command": f"analyzeHeadless /tmp/project Target -import {target}",
                 "description": "使用Ghidra进行静态分析"},
                {"action": "find_gadgets", "tool": "ropgadget",
                 "command": f"ROPgadget --binary {target}",
                 "description": "搜索ROP Gadgets"},
                {"action": "dynamic_debug", "tool": "gdb",
                 "command": f"gdb ./{target}",
                 "description": "使用GDB动态调试"},
            ]

        else:
            # Generic binary analysis
            tools = ["ghidra", "radare2", "strings", "binwalk", "gdb", "file"]
            actions = [
                {"action": "identify_file", "tool": "file",
                 "command": f"file {target}",
                 "description": "识别文件类型"},
                {"action": "extract_strings", "tool": "strings",
                 "command": f"strings -a {target} | head -100",
                 "description": "提取可读字符串"},
                {"action": "analyze_binary", "tool": "ghidra",
                 "command": f"analyzeHeadless /tmp/project Target -import {target}",
                 "description": "使用Ghidra进行深度分析"},
                {"action": "r2_analysis", "tool": "radare2",
                 "command": f"r2 -A {target}",
                 "description": "使用radare2分析二进制"},
            ]

        # Add common RE steps
        actions.extend([
            {"action": "find_crypto", "tool": "findcrypt",
             "description": "识别加密算法（AES/DES/RSA等常量）"},
            {"action": "anti_debug_check", "tool": "generic",
             "description": "检测反调试机制并制定绕过策略"},
        ])

        # Build LLM analysis if available
        if self.llm:
            try:
                return self._llm_analyze(state, context, tools, actions)
            except Exception as e:
                logger.warning(f"LLM analysis failed, using rule-based: {e}")

        return ExpertAdvice(
            expert_type=ExpertType.REVERSE_ENGINEERING,
            summary=f"逆向分析目标: {target or 'unknown binary'}",
            recommended_actions=actions[:6],
            tools_to_use=tools[:6],
            confidence=0.6,
            reasoning="基于目标类型选择反编译和分析工具",
            warnings=warnings,
            relevant_techniques=self._get_techniques()[:5],
        )

    def _llm_analyze(self, state: dict, context: dict, tools: list, actions: list) -> ExpertAdvice:
        """Use LLM for deeper analysis."""
        prompt = self._build_analysis_prompt(state, context)
        prompt += """

请分析以上渗透测试场景，提供逆向工程建议。返回JSON格式:
{
    "summary": "分析总结",
    "recommended_actions": [
        {"action": "操作名称", "tool": "工具", "command": "命令", "description": "说明"}
    ],
    "tools_to_use": ["推荐工具列表"],
    "confidence": 0.0-1.0,
    "reasoning": "分析推理过程",
    "warnings": ["注意事项"],
    "vulnerabilities": ["可能的漏洞"],
    "anti_debug": ["反调试机制"],
    "crypto_identified": ["识别到的加密算法"],
    "exploit_strategy": "漏洞利用策略"
}
"""
        response = self.llm.call(
            [{"role": "user", "content": prompt}],
            use_json_mode=False,
            temperature=0.3,
        )

        content = response.content.strip()
        import json

        # Try to parse JSON from response
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            content = content.split("```")[1].split("```")[0]

        try:
            data = json.loads(content.strip())
        except json.JSONDecodeError:
            data = {
                "summary": content[:200],
                "recommended_actions": actions[:4],
                "tools_to_use": tools[:4],
                "confidence": 0.5,
                "reasoning": "基于规则的分析",
                "warnings": [],
            }

        return ExpertAdvice(
            expert_type=ExpertType.REVERSE_ENGINEERING,
            summary=data.get("summary", "逆向工程分析"),
            recommended_actions=data.get("recommended_actions", actions[:6]),
            tools_to_use=data.get("tools_to_use", tools[:6]),
            confidence=data.get("confidence", 0.6),
            reasoning=data.get("reasoning", ""),
            warnings=data.get("warnings", []),
            relevant_techniques=self._get_techniques()[:5],
        )
