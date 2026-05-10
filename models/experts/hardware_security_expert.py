"""
Hardware Security Expert

Expert in hardware attacks including side-channel attacks, fault injection,
chip security, PCB reverse engineering, JTAG/SWD debugging, and physical
security testing.
"""

import logging
from typing import List, Dict, Optional

from models.experts.base import PenTestExpert, ExpertAdvice, ExpertType

logger = logging.getLogger(__name__)


class HardwareSecurityExpert(PenTestExpert):
    """Expert in hardware security testing and attacks."""

    # Comprehensive hardware security tools (100+)
    TOOLS = [
        # === Side-Channel Analysis ===
        # Power Analysis
        "chipwhisperer", "cw1173", "cw1180", "openadc", "勒克隆",
        "power_analysis", " DPA", "CPA", "correlation_power_analysis",
        # Electromagnetic Analysis
        "riscure_inspector", "riscure_hspider", "EM_probes", "EM_scanner",
        "presto", "newAE", "cw-lite", "cw-arm",
        # Timing Analysis
        "timing_attack", "cache_timing", "spectre_meltdown",
        # Acoustic Analysis
        "acoustic_capture", "phonons", "acoustic_microphone",
        # Optical / Fault Injection
        "laser_fault_injection", "EM_fault_injection", "voltage_glitch",
        "clock_glitch", "cold_boot_attack", "fault_injection",

        # === Chip Security ===
        # eFuse / Secure Boot
        "efuse_dump", "fuse_programming", "secure_boot_bypass",
        # TPM / HSM
        "tpmdump", "tpm2tools", "cryptosec", "softHSM", "pkcs11_tool",
        # Secure Element
        "javacard", "globalplatform", "pyapdu", "cardpeek",
        # eMMC / NAND
        "nand_reader", "flashrom", "rt809h", "ch341a", "rtDruid",
        # MCU Extraction
        " STM32_Programmer", "JLink", "CMSIS_DAP", "STLink", "EDB", "xds110",

        # === Debug Interfaces ===
        # JTAG / SWD
        "jtagulator", "openocd", "jlink_exe", "cmsis_dap", "FTDI_JTAG",
        "JTAGenum", "svf_player", "urjtag", "openjtag", "jtag_helpers",
        # UART / Serial
        "minicom", "screen", "picocom", "cutecom", "putty", "baudrate",
        "uart_to_serial", "usb_uart", "CP210x", "FT232", "PL2303",
        # SPI / I2C
        "flashrom", "beaglebone", "beagle_spi", "i2c_tools", "i2cdetect",
        "saleae_logic", "sigrok", "pulseview", "scoppy", "dslogic",
        # USB
        "usb_modeswitch", "usbtree", "lsusb", "usbip", "sniff_usb",
        "wireshark_usb", "usbguard", "libusb", "pyusb",

        # === Chip-Off & Deprocessing ===
        "microscope", "hot_air_station", "reflow_oven", "tormach",
        "probe_station", "FIB", "focused_ion_beam", "micromanipulator",
        "die_imaging", "delayer", "polisher", "acid_decapsulation",

        # === PCB Reverse Engineering ===
        "pcb_reverse", "diptrace", "eagle_pcb", "kicad", "fritzing",
        "openmv", " Gerber_viewer", "pcbimg", "pcbnew", "route", "traces",
        "via", "netlist_extraction", "pcb_etching", "copper_recovery",

        # === Bus / Protocol Analysis ===
        # CAN / Automotive
        "cansniffer", "candump", "can-utils", "icsim", "caringo",
        "isotp", "j1939", "uds_protocol", "canmatrix", "canoe", "canalyzer",
        "odx", "odx2csv", "opendigitaltwins", "canedge", "macchina",
        # USB Protocol
        "usb协议", "usb_protocol", "usb_driver", "usb_analysis",
        # Ethernet / SerDes
        "ethernet_tap", "SerDes", "SFP", "FPGA", "mipi", "CSI_DSI",
        # Industrial
        "modbus", "profibus", "hart_protocol", "foundation_fieldbus",
        "opc_ua", "scada_protocol", "plc_comm",

        # === RF / Wireless Hardware ===
        # SDR
        "hackrf_one", "bladeRF", "usrp", "rtlsdr", "airspy", "sdrsharp",
        "gnuradio", "grc", "gqrx", "kalibrate_rtl", "rtl_433", "rtl_power",
        # ZigBee
        "killerbee", "zigbee_sniffer", "at86rf", "zigd", "zbsdr",
        # Sub-GHz
        "rfcat", "rfidiot", "proxmark3", "proxmark3_iceman", "llrp",
        "gnuradio_rf", "rflayer",
        # Bluetooth / BLE
        "ubertooth", "btlejack", "gattacker", "bleah", "blue_hydra",
        "btproxy", "blesuite", "btcrack", "bluetooth_sniffer",

        # === RFID / NFC ===
        "proxmark3", "mfoc", "mfcuk", "nfc_mfclassic", "nfcpy",
        "libnfc", "pn532", "rfidiot", " chameleon", "hicom",
        "mfroware", "acr122", "ACR122U", "nfc_tools", "taginfo",

        # === Physical Security ===
        "lockpick", "raking", "spinning", "dimple", "decoders", "lishi",
        "bump_key", "snap_rakes", "electric_lock", "magnetic_lock_bypass",
        "shimming", "impressioning", "key_tracking", "covert_entry",
        "lock_bypass", "hinge_puller", "door_follower", "under_the_door",

        # === Cold Boot / Memory Attacks ===
        "ddr_tools", "inception", "passcape", "memdrip", "arsenic",
        "cold_boot_attack", "memory_imaging", "firewire_attack", "thunderbolt",

        # === Firmware Security (Hardware Context) ===
        "binwalk", "firmware_mod_kit", "固件提取", "固件分析", "固件修改",
        "uefi_extract", "uefi_pyramid", "chipsec", "uefitool", "ifrextract",

        # === Automotive Security ===
        "can_utils", "icsim", "canard", "canopen", "opendbc", "cantools",
        "canmatrix", "rvi", "doip", "enet", "ethernet automotive",
        # OBD-II
        "obd2_can", "torque_pro", "cabana", "logic_analyzer",

        # === Hardware Trojans ===
        "htdetect", "htinsertion", "malicious_circuit", "trojan_detection",
        "side_channel_trojan", "hardware_trojan_benchmark",

        # === Specialized Hardware Tools ===
        "chipcrow", "dangerousprototypes", "goodfet", "buspirate",
        "shikra", "hydra", "garderos", "tradewind", "minimax", "neural Networks",

        # === Password Extraction from Hardware ===
        "bios_pw", "cmos_pw", "eeprom_dump", " nvram_extract",
        "keeloq_decrypt", "rolling_code", "garage_sniff",
    ]

    SYSTEM_PROMPT = """你是一位资深的硬件安全测试与攻击专家。

专长领域：
1. 侧信道攻击 (Side-Channel Attacks)
   - 功耗分析 (Power Analysis): CPA, DPA, 时间相关功耗分析
   - 电磁分析 (EM Analysis): 电磁辐射采集与分析
   - 时序攻击 (Timing Attacks): Cache-timing, Spectre/Meltdown变体
   - 声学攻击 (Acoustic Attacks): 键盘声学分析

2. 故障注入 (Fault Injection)
   - 电压故障注入 (Voltage Glitching)
   - 时钟故障注入 (Clock Glitching)
   - 电磁故障注入 (EM Fault Injection)
   - 激光故障注入 (Laser Fault Injection)
   - 冷启动攻击 (Cold Boot Attacks)

3. 芯片安全测试
   - eFuse / 安全启动绕过
   - TPM / HSM 安全评估
   - 安全芯片攻击
   - MCU 固件提取与篡改
   - eMMC / NAND Flash 读取

4. 调试接口攻击
   - JTAG / SWD 调试接口利用
   - UART / 串口识别与利用
   - SPI / I2C 总线嗅探
   - USB 协议分析与攻击

5. PCB 逆向工程
   - 电路板成像与走线提取
   - 网表提取与原理图重建
   - 器件识别与功能分析
   - 隐藏电路/后门检测

6. 汽车/工控安全
   - CAN总线协议分析与攻击
   - OBD-II 诊断接口测试
   - UDS / DoIP 协议分析
   - PLC / SCADA 通信安全

7. RFID/NFC 安全
   - 低频/高频/超高频标签攻击
   - MIFARE Classic 破解
   - NFC 中间人攻击
   - 门禁系统绕过

8. 物理安全
   - 机械锁具开锁技术
   - 电子锁绕过
   - 门禁系统渗透
   - 物理入侵路径规划

工具集：
- ChipWhisperer: 侧信道功耗分析
- JTAGulator / OpenOCD: JTAG调试
- Flashrom: SPI Flash读取
- Saleae Logic: 协议分析
- Proxmark3: RFID/NFC攻击
- KillerBee: ZigBee安全
- Ubertooth: 蓝牙低功耗
- CAN-utils / ICSim: 汽车总线
- Binwalk: 固件提取
- Chipsec: UEFI安全

测试原则：
1. 先非侵入式侦察 (读取引脚、标记、接口)
2. 再半侵入式分析 (调试接口、芯片读取)
3. 最后侵入式攻击 (去封装、探针台、FIB)
4. 注意ESD防护和设备安全
"""

    def __init__(self, llm_provider=None, rag_retriever=None):
        super().__init__(
            expert_type=ExpertType.HARDWARE_SECURITY,
            llm_provider=llm_provider,
            rag_retriever=rag_retriever,
            tools=self.TOOLS,
        )

    def analyze(self, state: dict, context: dict = None) -> ExpertAdvice:
        """Analyze hardware security testing opportunities."""
        self.call_count += 1

        target = state.get("target", "")
        target_type = state.get("target_type", "")  # chip, pcb, rfid, automotive, lock, etc.
        interface = state.get("interface", "")  # jtag, uart, spi, can, etc.
        firmware = state.get("firmware", None)
        protocol = state.get("protocol", "")  # can, modbus, zigbee, etc.

        actions = []
        tools = []
        warnings = []
        reasoning = ""
        confidence = 0.5

        # Auto-detect target type
        hw_indicators = [
            "chip", "pcb", "mcu", "cpu", "soc", "fpga", "eeprom", "flash",
            "rfid", "nfc", "zigbee", "lock", "key", "card", "tag",
            "automotive", "car", "can", "obd", "plc", "scada", "modbus",
            "uart", "jtag", "swd", "spi", "i2c", "usb", "serial",
            "side_channel", "fault", "glitch", "em", "power", "timing",
            "decap", "chip-off", "probing", "pcb", "board", "circuit",
        ]
        is_hardware = any(ind in (target + target_type + interface + protocol).lower() for ind in hw_indicators)

        if not target_type:
            target_type = self._infer_target_type(target, interface, protocol)

        # === Side-Channel Attacks ===
        if any(k in target_type for k in ["side_channel", "crypto", "smartcard", "secure_element"]):
            actions.extend([
                {
                    "type": "power_analysis",
                    "tool": "chipwhisperer",
                    "params": {"operation": "trace_collection"},
                    "description": "采集功耗轨迹进行侧信道分析",
                },
                {
                    "type": "cpa_attack",
                    "tool": "chipwhisperer",
                    "params": {"method": "CPA", "target": "AES"},
                    "description": "相关功耗分析提取密钥",
                },
                {
                    "type": "em_analysis",
                    "tool": "EM_probes",
                    "params": {"frequency": "1MHz-1GHz"},
                    "description": "采集电磁辐射进行分析",
                },
                {
                    "type": "timing_analysis",
                    "tool": "timing_attack",
                    "description": "时序分析检测密钥操作差异",
                },
            ])
            tools.extend(["chipwhisperer", "openadc", "cw-lite"])
            reasoning = "目标疑似加密芯片/智能卡，执行侧信道攻击。"
            confidence = 0.8

        # === Chip / MCU Extraction ===
        elif any(k in target_type for k in ["chip", "mcu", "cpu", "soc", "fpga", "secure_boot", "efuse"]):
            if firmware:
                actions.extend([
                    {
                        "type": "read_flash",
                        "tool": "flashrom",
                        "params": {"interface": "programmer"},
                        "description": "尝试通过Flash读取固件",
                    },
                    {
                        "type": "debug_interface",
                        "tool": "openocd",
                        "params": {"interface": interface or "jtag"},
                        "description": "通过调试接口连接芯片",
                    },
                    {
                        "type": "efuse_dump",
                        "tool": "JLink",
                        "description": "提取eFuse安全熔丝状态",
                    },
                ])
                tools.extend(["flashrom", "openocd", "JLink"])
                reasoning = "发现芯片目标，进行固件提取。"
                confidence = 0.85
            else:
                actions.extend([
                    {
                        "type": "identify_chip",
                        "tool": "microscope",
                        "description": "识别芯片型号和封装",
                    },
                    {
                        "type": "debug_probe",
                        "tool": "JTAGulator",
                        "params": {"mode": "enumerate"},
                        "description": "枚举JTAG引脚配置",
                    },
                    {
                        "type": "serial_console",
                        "tool": "minicom",
                        "params": {"baudrate": 115200},
                        "description": "尝试连接UART串口控制台",
                    },
                ])
                tools.extend(["JTAGulator", "minicom", "openocd"])
                reasoning = "芯片目标已识别，进行调试接口探测。"
                confidence = 0.75

        # === Debug Interface (JTAG/UART/SPI/I2C) ===
        elif any(k in target_type for k in ["jtag", "uart", "spi", "i2c", "debug"]):
            actions.extend([
                {
                    "type": "jtag_enumerate",
                    "tool": "JTAGenum",
                    "description": "枚举JTAG指令和数据寄存器",
                },
                {
                    "type": "uart_identify",
                    "tool": "minicom",
                    "params": {"baudrate": "auto_detect"},
                    "description": "识别UART波特率并连接",
                },
                {
                    "type": "spi_sniff",
                    "tool": "flashrom",
                    "params": {"operation": "read"},
                    "description": "嗅探或读取SPI Flash",
                },
                {
                    "type": "i2c_scan",
                    "tool": "i2cdetect",
                    "description": "扫描I2C总线设备",
                },
            ])
            tools.extend(["JTAGenum", "openocd", "flashrom", "i2c_tools"])
            reasoning = f"检测到调试接口 {interface or target_type}，进行接口测试。"
            confidence = 0.8

        # === RFID / NFC ===
        elif any(k in target_type for k in ["rfid", "nfc", "card", "tag", "access_control"]):
            actions.extend([
                {
                    "type": "tag_read",
                    "tool": "proxmark3",
                    "params": {"mode": "hw tune"},
                    "description": "读取RFID/NFC标签信息",
                },
                {
                    "type": "tag_cloning",
                    "tool": "proxmark3",
                    "params": {"operation": "clone"},
                    "description": "克隆标签到空白卡",
                },
                {
                    "type": "mifare_crack",
                    "tool": "mfoc",
                    "params": {"nested_attack": True},
                    "description": "MIFARE ClassicNested攻击破解",
                },
                {
                    "type": "sniff_nfc",
                    "tool": "nfcpy",
                    "description": "嗅探NFC通信数据",
                },
            ])
            tools.extend(["proxmark3", "mfoc", "mfcuk", "nfcpy", "libnfc"])
            reasoning = "发现RFID/NFC目标，进行标签分析和克隆。"
            confidence = 0.8

        # === Automotive / CAN Bus ===
        elif any(k in target_type for k in ["automotive", "car", "can", "obd", "vehicle"]):
            actions.extend([
                {
                    "type": "can_discovery",
                    "tool": "cansniffer",
                    "params": {"interface": "socketcan"},
                    "description": "发现CAN总线上的通信帧",
                },
                {
                    "type": "can_replay",
                    "tool": "cansend",
                    "params": {"can_id": "spoof"},
                    "description": "重放/欺骗CAN消息",
                },
                {
                    "type": "obd_scan",
                    "tool": "can-utils",
                    "params": {"mode": "diagnostic"},
                    "description": "OBD-II诊断接口扫描",
                },
                {
                    "type": "can_injection",
                    "tool": "candump",
                    "params": {"fuzzing": True},
                    "description": "CAN总线模糊测试",
                },
            ])
            tools.extend(["cansniffer", "candump", "can-utils", "icsim"])
            reasoning = "发现汽车/工控目标，进行CAN总线分析。"
            confidence = 0.8

        # === ZigBee / Sub-GHz Wireless ===
        elif any(k in target_type for k in ["zigbee", "subghz", "wireless", "rf"]):
            actions.extend([
                {
                    "type": "rf_sniff",
                    "tool": "hackrf_one",
                    "params": {"frequency": "auto"},
                    "description": "捕获RF无线信号",
                },
                {
                    "type": "zigbee_capture",
                    "tool": "killerbee",
                    "params": {"channel": "auto"},
                    "description": "嗅探ZigBee通信",
                },
                {
                    "type": "replay_attack",
                    "tool": "rfcat",
                    "params": {"replay": True},
                    "description": "重放攻击无线信号",
                },
            ])
            tools.extend(["hackrf_one", "killerbee", "rfcat", "gnuradio"])
            reasoning = "发现无线硬件目标，进行RF信号分析。"
            confidence = 0.75

        # === Physical Security / Lock ===
        elif any(k in target_type for k in ["lock", "physical", "door", "access"]):
            actions.extend([
                {
                    "type": "lock_analysis",
                    "tool": "pick_kit",
                    "description": "分析锁具结构和安全等级",
                },
                {
                    "type": "lockpick",
                    "tool": "lockpick",
                    "params": {"technique": "raking"},
                    "description": "技术开锁",
                },
                {
                    "type": "key_impression",
                    "tool": "impressioning",
                    "description": "钥匙压印技术",
                },
                {
                    "type": "bypass_lock",
                    "tool": "bypass_tool",
                    "description": "锁具绕过技术",
                },
            ])
            reasoning = "发现物理安全目标，进行锁具测试。"
            confidence = 0.7

        # === PCB Reverse Engineering ===
        elif any(k in target_type for k in ["pcb", "board", "circuit", "hardware"]):
            actions.extend([
                {
                    "type": "pcb_image",
                    "tool": "microscope",
                    "params": {"magnification": "10x-100x"},
                    "description": "PCB成像采集走线",
                },
                {
                    "type": "netlist_extract",
                    "tool": "pcb_reverse",
                    "description": "提取网表重建原理图",
                },
                {
                    "type": "component_id",
                    "tool": "microscope",
                    "description": "识别主要器件型号",
                },
                {
                    "type": "signal_trace",
                    "tool": "saleae_logic",
                    "description": "跟踪关键信号路径",
                },
            ])
            tools.extend(["microscope", "saleae_logic", "kicad"])
            reasoning = "发现PCB目标，进行逆向工程分析。"
            confidence = 0.75

        # === Cold Boot / Memory Attacks ===
        elif any(k in target_type for k in ["memory", "cold_boot", "ram", "ddr"]):
            actions.extend([
                {
                    "type": "memory_dump",
                    "tool": "inception",
                    "params": {"interface": "firewire"},
                    "description": "通过FireWire提取内存",
                },
                {
                    "type": "cold_boot",
                    "tool": "cold_boot_attack",
                    "description": "执行冷启动攻击提取密钥",
                },
                {
                    "type": "bitstream",
                    "tool": "memdrip",
                    "description": "内存位镜像提取",
                },
            ])
            tools.extend(["inception", "memdrip", "ddr_tools"])
            reasoning = "目标涉及内存安全，执行冷启动攻击。"
            confidence = 0.7

        # === General Hardware Recon ===
        else:
            if is_hardware or target_type:
                # Generic hardware testing workflow
                actions.extend([
                    {
                        "type": "visual_inspection",
                        "tool": "microscope",
                        "description": "视觉检查识别芯片和接口",
                    },
                    {
                        "type": "interface_scan",
                        "tool": "JTAGulator",
                        "params": {"mode": "bitbang"},
                        "description": "扫描调试接口",
                    },
                    {
                        "type": "serial_probe",
                        "tool": "usb_uart",
                        "description": "探测UART串口",
                    },
                    {
                        "type": "datasheet_search",
                        "tool": "search",
                        "description": "搜索芯片数据手册",
                    },
                ])
                tools.extend(["JTAGulator", "minicom", "microscope"])
                reasoning = f"识别为硬件目标，进行基础侦察。检测到: {target_type or interface or protocol}"
                confidence = 0.65
            else:
                # Not clearly hardware - check for indicators
                actions.extend([
                    {
                        "type": "identify",
                        "tool": "file",
                        "params": {"target": target},
                        "description": "识别目标类型",
                    },
                ])
                reasoning = "目标类型不明确，建议进一步确认。"
                confidence = 0.4

        # Universal hardware warnings
        warnings.extend([
            "硬件测试可能造成设备永久性损坏",
            "请确保在授权范围内进行测试",
            "ESD防护措施必须到位",
            "部分攻击需要物理接触目标设备",
            "芯片去封装是不可逆操作",
        ])

        return ExpertAdvice(
            expert_type=self.expert_type,
            summary=f"硬件安全测试，推荐 {len(actions)} 个测试行动",
            recommended_actions=actions,
            tools_to_use=list(set(tools)),
            confidence=confidence,
            reasoning=reasoning,
            warnings=warnings,
        )

    def get_prompt_template(self) -> str:
        return self.SYSTEM_PROMPT

    def _get_techniques(self) -> List[str]:
        return [
            "T1200",  # Hardware Additions
            "T0855",  #江南书生
            "T0858",  #失能
            "T0861",  #利用
            "T0862",  #PLC
            "T0866",  #运营技术
            "T1552.001",  #未经许可的凭证
            "T0801",  #入侵
            "T0804",  #破坏
        ]

    def _get_required_inputs(self) -> List[str]:
        return ["target", "target_type"]

    def _get_outputs(self) -> List[str]:
        return [
            "firmware_dump",
            "key_extraction",
            "debug_access",
            "interface_pins",
            "protocol_analysis",
            "vulnerabilities",
        ]

    def _infer_target_type(self, target: str, interface: str, protocol: str) -> str:
        """Infer target type from context."""
        combined = (target + interface + protocol).lower()

        type_mapping = {
            "chip|mcu|cpu|soc|fpga|stm32|atmega|esp32|attiny": "chip",
            "jtag": "jtag",
            "uart|serial|console": "uart",
            "spi|flash": "spi",
            "i2c": "i2c",
            "rfid|nfc|mifare|proxmark|em41|em4": "rfid",
            "can|obd|automotive|car|vehicle": "automotive",
            "zigbee|zig": "zigbee",
            "lock|physical|door|key": "lock",
            "pcb|board|circuit": "pcb",
            "side.channel|cpa|dpa|power.analysis|em.": "side_channel",
            "fault|glitch|voltage|clock": "fault_injection",
            "cold.boot|memory|ram|ddr": "cold_boot",
        }

        for patterns, type_name in type_mapping.items():
            if any(p in combined for p in patterns.split("|")):
                return type_name

        return ""
