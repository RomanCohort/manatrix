"""
200 Sample API Testing - Real DeepSeek API Calls
=================================================
200 real penetration test scenarios with DeepSeek API
"""

import requests
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List

OUTPUT_DIR = Path("D:/password_guesser/results")
CONFIG_FILE = Path("D:/password_guesser/config.yaml")

# DeepSeek API配置
API_URL = "https://api.deepseek.com/v1/chat/completions"
API_KEY = None  # 从config.yaml读取


def load_api_key():
    """加载API密钥"""
    global API_KEY
    try:
        import yaml
        with open(CONFIG_FILE, 'r') as f:
            config = yaml.safe_load(f)
            API_KEY = config.get('llm', {}).get('api_key', '')
    except:
        # 尝试环境变量
        import os
        API_KEY = os.environ.get('DEEPSEEK_API_KEY', '')
    return API_KEY


# 200个真实渗透测试场景
PEN_TEST_SCENARIOS = [
    # SQL注入场景 (1-40)
    {"id": 1, "type": "sqli", "scenario": "MySQL UNION注入获取users表数据", "target": "MySQL"},
    {"id": 2, "type": "sqli", "scenario": "SQL Server报错注入提取密码", "target": "MSSQL"},
    {"id": 3, "type": "sqli", "scenario": "Oracle盲注获取管理员权限", "target": "Oracle"},
    {"id": 4, "type": "sqli", "scenario": "PostgreSQL堆叠查询执行系统命令", "target": "PostgreSQL"},
    {"id": 5, "type": "sqli", "scenario": "SQLite注入绕过登录验证", "target": "SQLite"},
    {"id": 6, "type": "sqli", "scenario": "时间盲注提取数据库版本", "target": "MySQL"},
    {"id": 7, "type": "sqli", "scenario": "布尔盲注枚举表名", "target": "MySQL"},
    {"id": 8, "type": "sqli", "scenario": "二阶SQL注入攻击用户表", "target": "MySQL"},
    {"id": 9, "type": "sqli", "scenario": "SQL注入绕过WAF过滤", "target": "MySQL"},
    {"id": 10, "type": "sqli", "scenario": "宽字节注入绕过转义", "target": "MySQL"},
    {"id": 11, "type": "sqli", "scenario": "HTTP头SQL注入攻击", "target": "MySQL"},
    {"id": 12, "type": "sqli", "scenario": "Cookie字段SQL注入", "target": "MySQL"},
    {"id": 13, "type": "sqli", "scenario": "JSON参数SQL注入提取数据", "target": "MySQL"},
    {"id": 14, "type": "sqli", "scenario": "XML参数SQL注入攻击", "target": "MySQL"},
    {"id": 15, "type": "sqli", "scenario": "存储过程SQL注入提权", "target": "MSSQL"},
    {"id": 16, "type": "sqli", "scenario": "LIMIT注入获取数据", "target": "MySQL"},
    {"id": 17, "type": "sqli", "scenario": "ORDER BY注入排序攻击", "target": "MySQL"},
    {"id": 18, "type": "sqli", "scenario": "GROUP BY注入分组攻击", "target": "MySQL"},
    {"id": 19, "type": "sqli", "scenario": "HAVING注入条件攻击", "target": "MySQL"},
    {"id": 20, "type": "sqli", "scenario": "INSERT注入插入恶意数据", "target": "MySQL"},
    {"id": 21, "type": "sqli", "scenario": "UPDATE注入修改管理员密码", "target": "MySQL"},
    {"id": 22, "type": "sqli", "scenario": "DELETE注入删除日志记录", "target": "MySQL"},
    {"id": 23, "type": "sqli", "scenario": "SQL注入读取文件内容", "target": "MySQL"},
    {"id": 24, "type": "sqli", "scenario": "SQL注入写入WebShell", "target": "MySQL"},
    {"id": 25, "type": "sqli", "scenario": "SQL注入执行系统命令", "target": "MSSQL"},
    {"id": 26, "type": "sqli", "scenario": "SQL注入注册表操作", "target": "MSSQL"},
    {"id": 27, "type": "sqli", "scenario": "SQL注入网络命令执行", "target": "MSSQL"},
    {"id": 28, "type": "sqli", "scenario": "SQL注入CLR程序集加载", "target": "MSSQL"},
    {"id": 29, "type": "sqli", "scenario": "SQL注入链接服务器攻击", "target": "MSSQL"},
    {"id": 30, "type": "sqli", "scenario": "SQL注入 xp_cmdshell 执行", "target": "MSSQL"},
    {"id": 31, "type": "sqli", "scenario": "SQL注入 sp_OACreate 执行", "target": "MSSQL"},
    {"id": 32, "type": "sqli", "scenario": "Oracle UTL_HTTP请求攻击", "target": "Oracle"},
    {"id": 33, "type": "sqli", "scenario": "Oracle Java存储过程执行", "target": "Oracle"},
    {"id": 34, "type": "sqli", "scenario": "PostgreSQL COPY命令攻击", "target": "PostgreSQL"},
    {"id": 35, "type": "sqli", "scenario": "PostgreSQL lo_import文件读取", "target": "PostgreSQL"},
    {"id": 36, "type": "sqli", "scenario": "MongoDB NoSQL注入攻击", "target": "MongoDB"},
    {"id": 37, "type": "sqli", "scenario": "Redis Lua脚本注入", "target": "Redis"},
    {"id": 38, "type": "sqli", "scenario": "Elasticsearch查询注入", "target": "ES"},
    {"id": 39, "type": "sqli", "scenario": "GraphQL注入攻击", "target": "GraphQL"},
    {"id": 40, "type": "sqli", "scenario": "LDAP注入绕过认证", "target": "LDAP"},

    # XSS场景 (41-70)
    {"id": 41, "type": "xss", "scenario": "反射型XSS窃取Cookie", "target": "Web"},
    {"id": 42, "type": "xss", "scenario": "存储型XSS钓鱼攻击", "target": "Web"},
    {"id": 43, "type": "xss", "scenario": "DOM型XSS劫持会话", "target": "Web"},
    {"id": 44, "type": "xss", "scenario": "XSS绕过HTML实体编码", "target": "Web"},
    {"id": 45, "type": "xss", "scenario": "XSS绕过JavaScript编码", "target": "Web"},
    {"id": 46, "type": "xss", "scenario": "XSS绕过URL编码", "target": "Web"},
    {"id": 47, "type": "xss", "scenario": "XSS绕过CSP策略", "target": "Web"},
    {"id": 48, "type": "xss", "scenario": "SVG XSS向量攻击", "target": "Web"},
    {"id": 49, "type": "xss", "scenario": "Math标签XSS攻击", "target": "Web"},
    {"id": 50, "type": "xss", "scenario": "Onmouseover事件XSS", "target": "Web"},
    {"id": 51, "type": "xss", "scenario": "Onerror事件XSS攻击", "target": "Web"},
    {"id": 52, "type": "xss", "scenario": "Onload事件XSS攻击", "target": "Web"},
    {"id": 53, "type": "xss", "scenario": "Javascript协议XSS", "target": "Web"},
    {"id": 54, "type": "xss", "scenario": "Data协议XSS攻击", "target": "Web"},
    {"id": 55, "type": "xss", "scenario": "VBScript协议XSS", "target": "Web"},
    {"id": 56, "type": "xss", "scenario": "表达式注入XSS攻击", "target": "Web"},
    {"id": 57, "type": "xss", "scenario": "Angular模板注入XSS", "target": "Angular"},
    {"id": 58, "type": "xss", "scenario": "Vue模板注入XSS", "target": "Vue"},
    {"id": 59, "type": "xss", "scenario": "React JSX注入攻击", "target": "React"},
    {"id": 60, "type": "xss", "scenario": "Markdown XSS攻击", "target": "Web"},
    {"id": 61, "type": "xss", "scenario": "BBCode XSS攻击", "target": "Web"},
    {"id": 62, "type": "xss", "scenario": "富文本编辑器XSS", "target": "Web"},
    {"id": 63, "type": "xss", "scenario": "PDF生成XSS攻击", "target": "Web"},
    {"id": 64, "type": "xss", "scenario": "邮件正文XSS攻击", "target": "Email"},
    {"id": 65, "type": "xss", "scenario": "即时消息XSS攻击", "target": "IM"},
    {"id": 66, "type": "xss", "scenario": "评论系统XSS攻击", "target": "Web"},
    {"id": 67, "type": "xss", "scenario": "搜索结果XSS攻击", "target": "Web"},
    {"id": 68, "type": "xss", "scenario": "错误页面XSS攻击", "target": "Web"},
    {"id": 69, "type": "xss", "scenario": "重定向页面XSS", "target": "Web"},
    {"id": 70, "type": "xss", "scenario": "Flash XSS攻击", "target": "Flash"},

    # 命令注入场景 (71-100)
    {"id": 71, "type": "rce", "scenario": "Linux命令注入执行whoami", "target": "Linux"},
    {"id": 72, "type": "rce", "scenario": "Linux命令注入读取/etc/passwd", "target": "Linux"},
    {"id": 73, "type": "rce", "scenario": "Linux命令注入反弹Shell", "target": "Linux"},
    {"id": 74, "type": "rce", "scenario": "Linux命令注入写入SSH公钥", "target": "Linux"},
    {"id": 75, "type": "rce", "scenario": "Linux命令注入下载恶意文件", "target": "Linux"},
    {"id": 76, "type": "rce", "scenario": "Linux命令注入修改文件权限", "target": "Linux"},
    {"id": 77, "type": "rce", "scenario": "Linux命令注入创建用户", "target": "Linux"},
    {"id": 78, "type": "rce", "scenario": "Linux命令注入修改密码", "target": "Linux"},
    {"id": 79, "type": "rce", "scenario": "Linux命令注入查看进程", "target": "Linux"},
    {"id": 80, "type": "rce", "scenario": "Linux命令注入查看网络", "target": "Linux"},
    {"id": 81, "type": "rce", "scenario": "Windows命令注入执行whoami", "target": "Windows"},
    {"id": 82, "type": "rce", "scenario": "Windows命令注入读取系统信息", "target": "Windows"},
    {"id": 83, "type": "rce", "scenario": "Windows命令注入添加用户", "target": "Windows"},
    {"id": 84, "type": "rce", "scenario": "Windows命令注入修改防火墙", "target": "Windows"},
    {"id": 85, "type": "rce", "scenario": "Windows命令注入注册表操作", "target": "Windows"},
    {"id": 86, "type": "rce", "scenario": "Windows命令注入计划任务", "target": "Windows"},
    {"id": 87, "type": "rce", "scenario": "Windows命令注入服务操作", "target": "Windows"},
    {"id": 88, "type": "rce", "scenario": "Windows命令注入网络共享", "target": "Windows"},
    {"id": 89, "type": "rce", "scenario": "PHP代码注入执行命令", "target": "PHP"},
    {"id": 90, "type": "rce", "scenario": "PHP eval函数注入", "target": "PHP"},
    {"id": 91, "type": "rce", "scenario": "PHP assert函数注入", "target": "PHP"},
    {"id": 92, "type": "rce", "scenario": "PHP preg_replace注入", "target": "PHP"},
    {"id": 93, "type": "rce", "scenario": "Python代码注入执行", "target": "Python"},
    {"id": 94, "type": "rce", "scenario": "Python os.system注入", "target": "Python"},
    {"id": 95, "type": "rce", "scenario": "Python subprocess注入", "target": "Python"},
    {"id": 96, "type": "rce", "scenario": "Java Runtime.exec注入", "target": "Java"},
    {"id": 97, "type": "rce", "scenario": "Node.js child_process注入", "target": "NodeJS"},
    {"id": 98, "type": "rce", "scenario": "Perl system函数注入", "target": "Perl"},
    {"id": 99, "type": "rce", "scenario": "Ruby eval注入执行", "target": "Ruby"},
    {"id": 100, "type": "rce", "scenario": "Go os/exec注入攻击", "target": "Go"},

    # 文件包含场景 (101-130)
    {"id": 101, "type": "lfi", "scenario": "本地文件包含读取/etc/passwd", "target": "Linux"},
    {"id": 102, "type": "lfi", "scenario": "本地文件包含读取日志文件", "target": "Linux"},
    {"id": 103, "type": "lfi", "scenario": "本地文件包含读取配置文件", "target": "Linux"},
    {"id": 104, "type": "lfi", "scenario": "本地文件包含读取源代码", "target": "Linux"},
    {"id": 105, "type": "lfi", "scenario": "本地文件包含绕过../过滤", "target": "Linux"},
    {"id": 106, "type": "lfi", "scenario": "本地文件包含双写绕过", "target": "Linux"},
    {"id": 107, "type": "lfi", "scenario": "本地文件包含URL编码绕过", "target": "Linux"},
    {"id": 108, "type": "lfi", "scenario": "本地文件包含空字节截断", "target": "Linux"},
    {"id": 109, "type": "lfi", "scenario": "本地文件包含PHP伪协议", "target": "PHP"},
    {"id": 110, "type": "lfi", "scenario": "PHP filter协议读取源码", "target": "PHP"},
    {"id": 111, "type": "lfi", "scenario": "PHP input协议执行代码", "target": "PHP"},
    {"id": 112, "type": "lfi", "scenario": "PHP data协议注入代码", "target": "PHP"},
    {"id": 113, "type": "lfi", "scenario": "远程文件包含获取WebShell", "target": "PHP"},
    {"id": 114, "type": "lfi", "scenario": "远程文件包含反弹Shell", "target": "PHP"},
    {"id": 115, "type": "lfi", "scenario": "日志文件包含注入代码", "target": "Linux"},
    {"id": 116, "type": "lfi", "scenario": "Session文件包含攻击", "target": "PHP"},
    {"id": 117, "type": "lfi", "scenario": "/proc/self/environ包含", "target": "Linux"},
    {"id": 118, "type": "lfi", "scenario": "/proc/self/fd包含", "target": "Linux"},
    {"id": 119, "type": "lfi", "scenario": "phar反序列化包含", "target": "PHP"},
    {"id": 120, "type": "lfi", "scenario": "zip协议包含攻击", "target": "PHP"},
    {"id": 121, "type": "lfi", "scenario": "Windows本地文件包含", "target": "Windows"},
    {"id": 122, "type": "lfi", "scenario": "Windows绝对路径包含", "target": "Windows"},
    {"id": 123, "type": "lfi", "scenario": "IIS短文件名包含", "target": "Windows"},
    {"id": 124, "type": "lfi", "scenario": "Apache日志包含攻击", "target": "Apache"},
    {"id": 125, "type": "lfi", "scenario": "Nginx日志包含攻击", "target": "Nginx"},
    {"id": 126, "type": "lfi", "scenario": "SSH日志包含攻击", "target": "Linux"},
    {"id": 127, "type": "lfi", "scenario": "邮件日志包含攻击", "target": "Linux"},
    {"id": 128, "type": "lfi", "scenario": "FTP日志包含攻击", "target": "Linux"},
    {"id": 129, "type": "lfi", "scenario": "JSP文件包含攻击", "target": "Java"},
    {"id": 130, "type": "lfi", "scenario": "ASP文件包含攻击", "target": "ASP"},

    # SSRF场景 (131-160)
    {"id": 131, "type": "ssrf", "scenario": "SSRF访问内部服务", "target": "Web"},
    {"id": 132, "type": "ssrf", "scenario": "SSRF探测内网端口", "target": "Web"},
    {"id": 133, "type": "ssrf", "scenario": "SSRF读取本地文件", "target": "Web"},
    {"id": 134, "type": "ssrf", "scenario": "SSRF攻击云服务元数据", "target": "Cloud"},
    {"id": 135, "type": "ssrf", "scenario": "SSRF攻击Redis服务", "target": "Redis"},
    {"id": 136, "type": "ssrf", "scenario": "SSRF攻击MySQL服务", "target": "MySQL"},
    {"id": 137, "type": "ssrf", "scenario": "SSRF攻击FastCGI服务", "target": "PHP"},
    {"id": 138, "type": "ssrf", "scenario": "SSRF gopher协议攻击", "target": "Web"},
    {"id": 139, "type": "ssrf", "scenario": "SSRF dict协议攻击", "target": "Web"},
    {"id": 140, "type": "ssrf", "scenario": "SSRF绕过IP限制", "target": "Web"},
    {"id": 141, "type": "ssrf", "scenario": "SSRF绕过域名限制", "target": "Web"},
    {"id": 142, "type": "ssrf", "scenario": "SSRF绕过协议限制", "target": "Web"},
    {"id": 143, "type": "ssrf", "scenario": "SSRF DNS重绑定攻击", "target": "Web"},
    {"id": 144, "type": "ssrf", "scenario": "SSRF 302重定向攻击", "target": "Web"},
    {"id": 145, "type": "ssrf", "scenario": "SSRF短链接绕过", "target": "Web"},
    {"id": 146, "type": "ssrf", "scenario": "SSRF十六进制编码绕过", "target": "Web"},
    {"id": 147, "type": "ssrf", "scenario": "SSRF八进制编码绕过", "target": "Web"},
    {"id": 148, "type": "ssrf", "scenario": "SSRF IPv6绕过攻击", "target": "Web"},
    {"id": 149, "type": "ssrf", "scenario": "AWS EC2元数据攻击", "target": "AWS"},
    {"id": 150, "type": "ssrf", "scenario": "GCP元数据攻击", "target": "GCP"},
    {"id": 151, "type": "ssrf", "scenario": "Azure元数据攻击", "target": "Azure"},
    {"id": 152, "type": "ssrf", "scenario": "阿里云元数据攻击", "target": "Aliyun"},
    {"id": 153, "type": "ssrf", "scenario": "腾讯云元数据攻击", "target": "Tencent"},
    {"id": 154, "type": "ssrf", "scenario": "Kubernetes API攻击", "target": "K8s"},
    {"id": 155, "type": "ssrf", "scenario": "Docker API攻击", "target": "Docker"},
    {"id": 156, "type": "ssrf", "scenario": "Elasticsearch攻击", "target": "ES"},
    {"id": 157, "type": "ssrf", "scenario": "Memcached攻击", "target": "Memcache"},
    {"id": 158, "type": "ssrf", "scenario": "内网Web应用攻击", "target": "Web"},
    {"id": 159, "type": "ssrf", "scenario": "SSRF盲注攻击", "target": "Web"},
    {"id": 160, "type": "ssrf", "scenario": "SSRF时间盲注攻击", "target": "Web"},

    # XXE场景 (161-180)
    {"id": 161, "type": "xxe", "scenario": "XXE读取/etc/passwd", "target": "Linux"},
    {"id": 162, "type": "xxe", "scenario": "XXE读取配置文件", "target": "Web"},
    {"id": 163, "type": "xxe", "scenario": "XXE读取源代码", "target": "Web"},
    {"id": 164, "type": "xxe", "scenario": "XXE SSRF攻击", "target": "Web"},
    {"id": 165, "type": "xxe", "scenario": "XXE拒绝服务攻击", "target": "Web"},
    {"id": 166, "type": "xxe", "scenario": "XXE外带数据攻击", "target": "Web"},
    {"id": 167, "type": "xxe", "scenario": "XXE参数实体攻击", "target": "Web"},
    {"id": 168, "type": "xxe", "scenario": "XXE盲注攻击", "target": "Web"},
    {"id": 169, "type": "xxe", "scenario": "XXE绕过过滤攻击", "target": "Web"},
    {"id": 170, "type": "xxe", "scenario": "XXE UTF-16编码绕过", "target": "Web"},
    {"id": 171, "type": "xxe", "scenario": "SOAP XXE攻击", "target": "SOAP"},
    {"id": 172, "type": "xxe", "scenario": "REST XXE攻击", "target": "REST"},
    {"id": 173, "type": "xxe", "scenario": "SVG文件XXE攻击", "target": "SVG"},
    {"id": 174, "type": "xxe", "scenario": "Office文档XXE攻击", "target": "Office"},
    {"id": 175, "type": "xxe", "scenario": "PDF文件XXE攻击", "target": "PDF"},
    {"id": 176, "type": "xxe", "scenario": "Excel XXE攻击", "target": "Excel"},
    {"id": 177, "type": "xxe", "scenario": "Word XXE攻击", "target": "Word"},
    {"id": 178, "type": "xxe", "scenario": "PPT XXE攻击", "target": "PPT"},
    {"id": 179, "type": "xxe", "scenario": "DTD文件XXE攻击", "target": "DTD"},
    {"id": 180, "type": "xxe", "scenario": "XLSX XXE攻击", "target": "XLSX"},

    # 反序列化场景 (181-200)
    {"id": 181, "type": "deser", "scenario": "Java反序列化命令执行", "target": "Java"},
    {"id": 182, "type": "deser", "scenario": "PHP反序列化攻击", "target": "PHP"},
    {"id": 183, "type": "deser", "scenario": "Python pickle反序列化", "target": "Python"},
    {"id": 184, "type": "deser", "scenario": "Ruby YAML反序列化", "target": "Ruby"},
    {"id": 185, "type": "deser", "scenario": "JSON反序列化攻击", "target": "Web"},
    {"id": 186, "type": "deser", "scenario": "XML反序列化攻击", "target": "Web"},
    {"id": 187, "type": "deser", "scenario": "Fastjson反序列化攻击", "target": "Java"},
    {"id": 188, "type": "deser", "scenario": "Jackson反序列化攻击", "target": "Java"},
    {"id": 189, "type": "deser", "scenario": "Apache Commons攻击", "target": "Java"},
    {"id": 190, "type": "deser", "scenario": "Spring反序列化攻击", "target": "Java"},
    {"id": 191, "type": "deser", "scenario": "WebLogic反序列化攻击", "target": "WebLogic"},
    {"id": 192, "type": "deser", "scenario": "JBoss反序列化攻击", "target": "JBoss"},
    {"id": 193, "type": "deser", "scenario": "WebSphere反序列化", "target": "WebSphere"},
    {"id": 194, "type": "deser", "scenario": "Shiro反序列化攻击", "target": "Shiro"},
    {"id": 195, "type": "deser", "scenario": "Laravel反序列化攻击", "target": "PHP"},
    {"id": 196, "type": "deser", "scenario": "Symfony反序列化攻击", "target": "PHP"},
    {"id": 197, "type": "deser", "scenario": "Django反序列化攻击", "target": "Python"},
    {"id": 198, "type": "deser", "scenario": "Flask反序列化攻击", "target": "Python"},
    {"id": 199, "type": "deser", "scenario": "Node.js反序列化攻击", "target": "NodeJS"},
    {"id": 200, "type": "deser", "scenario": "NET反序列化攻击", "target": "NET"},
]


def call_deepseek_api(scenario: dict) -> dict:
    """调用DeepSeek API"""
    if not API_KEY:
        return {"error": "API Key未配置"}

    prompt = f"""你是一个渗透测试专家。请分析以下漏洞场景并生成攻击payload：

漏洞类型: {scenario['type']}
场景描述: {scenario['scenario']}
目标环境: {scenario['target']}

请提供:
1. 攻击payload
2. 预期结果
3. 风险等级(高/中/低)

用JSON格式回复。"""

    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }

    data = {
        "model": "deepseek-chat",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7,
        "max_tokens": 500
    }

    try:
        resp = requests.post(API_URL, headers=headers, json=data, timeout=30)
        if resp.status_code == 200:
            result = resp.json()
            content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
            return {
                "success": True,
                "response": content,
                "tokens": result.get("usage", {}).get("total_tokens", 0)
            }
        else:
            return {"success": False, "error": f"API错误: {resp.status_code}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def run_200_api_tests():
    """运行200个API测试"""
    print("\n" + "="*60)
    print("  200 Sample API Testing (DeepSeek)")
    print("="*60)

    # 加载API Key
    load_api_key()
    if not API_KEY:
        print("[-] 错误: 请配置DeepSeek API Key")
        print("    方法1: 在config.yaml中设置 llm.api_key")
        print("    方法2: 设置环境变量 DEEPSEEK_API_KEY")
        return None

    print(f"[+] API Key已加载: {API_KEY[:10]}...")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results = []

    # 测试200个场景
    for i, scenario in enumerate(PEN_TEST_SCENARIOS, 1):
        print(f"\n[{i}/200] {scenario['type']}: {scenario['scenario'][:40]}...")

        api_result = call_deepseek_api(scenario)

        result = {
            "id": scenario["id"],
            "type": scenario["type"],
            "scenario": scenario["scenario"],
            "target": scenario["target"],
            "api_success": api_result.get("success", False),
            "response": api_result.get("response", "")[:200],
            "tokens": api_result.get("tokens", 0),
            "error": api_result.get("error", "")
        }

        results.append(result)

        # 显示进度
        if api_result.get("success"):
            print(f"    [OK] tokens: {api_result.get('tokens', 0)}")
        else:
            print(f"    [FAIL] {api_result.get('error', 'Unknown')}")

        # 避免请求过快
        time.sleep(0.5)

    # 统计
    success_count = sum(1 for r in results if r["api_success"])
    total_tokens = sum(r["tokens"] for r in results)

    by_type = {}
    for r in results:
        t = r["type"]
        if t not in by_type:
            by_type[t] = {"total": 0, "success": 0}
        by_type[t]["total"] += 1
        if r["api_success"]:
            by_type[t]["success"] += 1

    summary = {
        "timestamp": timestamp,
        "total_tests": 200,
        "successful": success_count,
        "failed": 200 - success_count,
        "success_rate": round(success_count / 200 * 100, 1),
        "total_tokens": total_tokens,
        "by_type": by_type,
        "results": results
    }

    # 保存
    output_file = OUTPUT_DIR / f"api_200_tests_{timestamp}.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    print(f"\n[+] 结果保存: {output_file}")

    return summary


if __name__ == "__main__":
    summary = run_200_api_tests()

    if summary:
        print("\n" + "="*60)
        print("  200 API Tests Complete")
        print("="*60)
        print(f"Total: 200")
        print(f"Successful: {summary['successful']}")
        print(f"Failed: {summary['failed']}")
        print(f"Success rate: {summary['success_rate']}%")
        print(f"Total tokens: {summary['total_tokens']}")

        print("\nBy Type:")
        for t, data in summary["by_type"].items():
            rate = round(data["success"] / data["total"] * 100, 1)
            print(f"  {t}: {data['success']}/{data['total']} ({rate}%)")