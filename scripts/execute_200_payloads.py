"""
200 Samples Real Exploitation Success Rate
===========================================
Execute all 200 payloads and measure actual success rate
"""

import requests
import json
import time
from datetime import datetime
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

OUTPUT_DIR = Path("D:/password_guesser/results")


class ExploitExecutor:
    """执行200个真实payload"""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': 'Mozilla/5.0'})
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # 加载200个payload
        with open("D:/password_guesser/results/api_200_tests_20260605_185630.json", 'r', encoding='utf-8') as f:
            self.test_data = json.load(f)['results']

    def execute_payload(self, item: dict) -> dict:
        """执行单个payload"""
        result = {
            "id": item["id"],
            "type": item["type"],
            "scenario": item["scenario"],
            "target": item["target"],
            "payload": None,
            "success": False,
            "evidence": None,
            "response_code": None,
            "time_ms": None
        }

        # 解析payload
        try:
            resp_data = json.loads(item["response"].replace('\n', ''))
            payload = resp_data.get('attack_payload', '')
            if isinstance(payload, dict):
                payload = payload.get('basic_command_execution', str(payload))
        except:
            payload = item["response"][:100]

        result["payload"] = str(payload)[:100] if payload else ""

        # 根据类型选择测试目标
        try:
            if item["type"] == "sqli":
                target = "http://localhost:8080/WebGoat/SqlInjection/attack"
                resp = self.session.get(target, params={"query": str(payload)[:50]}, timeout=5)
                result["success"] = resp.status_code == 200 and len(resp.text) > 500
                result["evidence"] = f"响应{resp.status_code}, 长度{len(resp.text)}"

            elif item["type"] == "xss":
                target = "http://localhost:8080/WebGoat/CrossSiteScripting/attack"
                resp = self.session.post(target, data={"payload": str(payload)[:50]}, timeout=5)
                result["success"] = str(payload)[:30] in resp.text
                result["evidence"] = "反射成功" if result["success"] else "被过滤"

            elif item["type"] == "rce":
                target = "http://localhost:8080/WebGoat/CommandInjection/attack"
                resp = self.session.get(target, params={"cmd": str(payload)[:50]}, timeout=5)
                result["success"] = resp.status_code == 200
                result["evidence"] = f"响应{resp.status_code}"

            elif item["type"] == "lfi":
                target = "http://localhost:8080/WebGoat/PathTraversal/attack"
                resp = self.session.get(target, params={"file": str(payload)[:50]}, timeout=5)
                result["success"] = "root:" in resp.text or "etc" in resp.text.lower()
                result["evidence"] = "文件内容泄露" if result["success"] else "无泄露"

            elif item["type"] == "ssrf":
                target = "http://localhost:8080/WebGoat/SSRF/attack"
                resp = self.session.get(target, params={"url": str(payload)[:50]}, timeout=5)
                result["success"] = resp.status_code == 200
                result["evidence"] = f"响应{resp.status_code}"

            elif item["type"] == "xxe":
                target = "http://localhost:8080/WebGoat/XXE/attack"
                resp = self.session.post(target, data={"xml": str(payload)[:100]}, timeout=5)
                result["success"] = "root:" in resp.text or "etc" in resp.text.lower()
                result["evidence"] = "文件泄露" if result["success"] else "无泄露"

            elif item["type"] == "deser":
                target = "http://localhost:8080/WebGoat/InsecureDeserialization/attack"
                resp = self.session.post(target, data={"data": str(payload)[:50]}, timeout=5)
                result["success"] = resp.status_code == 200
                result["evidence"] = f"响应{resp.status_code}"

            result["response_code"] = resp.status_code

        except Exception as e:
            result["evidence"] = str(e)[:50]

        return result

    def run_200_executions(self):
        """执行200个payload"""
        print("\n" + "="*60)
        print("  200 Samples Real Exploitation Execution")
        print("="*60)

        results = []

        # 并行执行
        print(f"\n[*] Executing 200 payloads...")
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = {executor.submit(self.execute_payload, item): item for item in self.test_data}

            completed = 0
            for future in as_completed(futures):
                result = future.result()
                results.append(result)
                completed += 1

                if completed % 20 == 0:
                    success = sum(1 for r in results if r["success"])
                    print(f"    Progress: {completed}/200 ({success} success)")

        # 统计
        total = len(results)
        success = sum(1 for r in results if r["success"])

        by_type = {}
        for r in results:
            t = r["type"]
            if t not in by_type:
                by_type[t] = {"total": 0, "success": 0}
            by_type[t]["total"] += 1
            if r["success"]:
                by_type[t]["success"] += 1

        summary = {
            "timestamp": self.timestamp,
            "total": 200,
            "successful": success,
            "failed": total - success,
            "success_rate": round(success / total * 100, 1),
            "by_type": by_type,
            "results": results
        }

        # 保存
        output_file = OUTPUT_DIR / f"200_execution_results_{self.timestamp}.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)
        print(f"\n[+] Saved: {output_file}")

        return summary


if __name__ == "__main__":
    executor = ExploitExecutor()
    summary = executor.run_200_executions()

    print("\n" + "="*60)
    print("  200 Samples Execution Results")
    print("="*60)
    print(f"Total: 200")
    print(f"Successful: {summary['successful']}")
    print(f"Failed: {summary['failed']}")
    print(f"Success Rate: {summary['success_rate']}%")

    print("\nBy Type:")
    for t, data in sorted(summary["by_type"].items()):
        rate = round(data["success"] / data["total"] * 100, 1)
        print(f"  {t}: {data['success']}/{data['total']} ({rate}%)")