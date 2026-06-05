"""
Bugku Platform Batch Testing
============================
Real batch testing on Bugku platform (bugku.com)
Requires: Bugku account and login session
"""

import requests
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple

OUTPUT_DIR = Path("D:/password_guesser/results")


class BugkuBatchTester:
    """Bugku平台批量测试器"""

    BASE_URL = "https://ctf.bugku.com"

    # Bugku常见Web题目（可实际测试）
    WEB_CHALLENGES = {
        "sqli": {
            "name": "SQL注入",
            "endpoint": "/challenges/detail?id=Sql_injection",
            "type": "Web",
            "difficulty": "easy"
        },
        "xss": {
            "name": "XSS",
            "endpoint": "/challenges/detail?id=XSS",
            "type": "Web",
            "difficulty": "easy"
        },
        "file_include": {
            "name": "文件包含",
            "endpoint": "/challenges/detail?id=File_Include",
            "type": "Web",
            "difficulty": "medium"
        },
        "upload": {
            "name": "文件上传",
            "endpoint": "/challenges/detail?id=Upload",
            "type": "Web",
            "difficulty": "medium"
        },
        "csrf": {
            "name": "CSRF",
            "endpoint": "/challenges/detail?id=CSRF",
            "type": "Web",
            "difficulty": "easy"
        },
        "ssrf": {
            "name": "SSRF",
            "endpoint": "/challenges/detail?id=SSRF",
            "type": "Web",
            "difficulty": "medium"
        },
        "ssti": {
            "name": "SSTI",
            "endpoint": "/challenges/detail?id=SSTI",
            "type": "Web",
            "difficulty": "hard"
        },
        "serialize": {
            "name": "反序列化",
            "endpoint": "/challenges/detail?id=Serialize",
            "type": "Web",
            "difficulty": "hard"
        }
    }

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json, text/html, */*',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8'
        })
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.results = []

    def check_platform_access(self) -> bool:
        """检查Bugku平台是否可访问"""
        try:
            resp = self.session.get(self.BASE_URL, timeout=10)
            if resp.status_code == 200:
                print("[+] Bugku平台可访问")
                return True
        except Exception as e:
            print(f"[-] Bugku平台访问失败: {e}")
        return False

    def get_challenge_list(self) -> List[Dict]:
        """获取题目列表（真实API调用）"""
        print("\n[*] 获取Bugku题目列表...")

        try:
            # Bugku题目API
            api_url = f"{self.BASE_URL}/api/challenges"
            resp = self.session.get(api_url, timeout=10)

            if resp.status_code == 200:
                data = resp.json()
                print(f"[+] 获取到 {len(data.get('data', []))} 个题目")
                return data.get('data', [])
            else:
                print(f"[-] API返回: {resp.status_code}")
        except Exception as e:
            print(f"[-] 获取题目列表失败: {e}")

        return []

    def test_challenge_access(self, challenge_id: str) -> Dict:
        """测试题目访问（真实HTTP请求）"""
        result = {
            "challenge_id": challenge_id,
            "timestamp": datetime.now().isoformat(),
            "accessible": False,
            "response_code": None,
            "response_time_ms": None
        }

        try:
            url = f"{self.BASE_URL}/challenges/detail?id={challenge_id}"
            start = time.time()
            resp = self.session.get(url, timeout=10)
            elapsed = (time.time() - start) * 1000

            result["accessible"] = resp.status_code == 200
            result["response_code"] = resp.status_code
            result["response_time_ms"] = round(elapsed, 2)
            result["content_length"] = len(resp.content)

        except Exception as e:
            result["error"] = str(e)

        return result

    def batch_test_challenges(self, challenge_ids: List[str]) -> List[Dict]:
        """批量测试题目（真实测试）"""
        print(f"\n[*] 批量测试 {len(challenge_ids)} 个题目...")

        results = []
        for i, cid in enumerate(challenge_ids, 1):
            print(f"    [{i}/{len(challenge_ids)}] 测试 {cid}...", end=" ")
            result = self.test_challenge_access(cid)
            results.append(result)
            status = "OK" if result["accessible"] else "FAIL"
            print(f"{status} ({result['response_time_ms']}ms)")
            time.sleep(0.5)  # 避免请求过快

        return results

    def get_user_stats(self) -> Dict:
        """获取用户统计（需要登录）"""
        print("\n[*] 获取用户统计...")

        try:
            api_url = f"{self.BASE_URL}/api/user/stats"
            resp = self.session.get(api_url, timeout=10)

            if resp.status_code == 200:
                return resp.json()
        except:
            pass

        return {"note": "需要登录后获取用户统计"}

    def run_full_batch_test(self) -> Dict:
        """运行完整批量测试"""
        print("\n" + "=" * 60)
        print("  Bugku Platform Batch Testing (Real)")
        print("=" * 60)

        # 检查平台访问
        if not self.check_platform_access():
            return {"error": "Bugku平台无法访问"}

        # 获取题目列表
        challenges = self.get_challenge_list()

        # 获取题目ID列表
        challenge_ids = []
        if challenges:
            challenge_ids = [c.get('id') for c in challenges if c.get('id')][:20]
        else:
            # 使用预设题目
            challenge_ids = list(self.WEB_CHALLENGES.keys())

        print(f"\n[*] 准备测试 {len(challenge_ids)} 个题目")

        # 批量测试
        test_results = self.batch_test_challenges(challenge_ids)

        # 统计
        accessible_count = sum(1 for r in test_results if r.get("accessible"))
        avg_response_time = sum(r.get("response_time_ms", 0) for r in test_results) / len(test_results) if test_results else 0

        summary = {
            "timestamp": self.timestamp,
            "platform": "Bugku",
            "platform_url": self.BASE_URL,
            "total_challenges_tested": len(test_results),
            "accessible_challenges": accessible_count,
            "access_rate": round(accessible_count / len(test_results) * 100, 1) if test_results else 0,
            "avg_response_time_ms": round(avg_response_time, 2),
            "test_results": test_results,
            "challenges_available": len(challenges)
        }

        # 保存结果
        output_file = OUTPUT_DIR / f"bugku_batch_test_{self.timestamp}.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)
        print(f"\n[+] 结果已保存: {output_file}")

        # 生成报告
        report_file = OUTPUT_DIR / f"bugku_batch_test_report_{self.timestamp}.md"
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write("# Bugku Platform Batch Test Report\n\n")
            f.write(f"**Date**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write("## Summary\n\n")
            f.write(f"- Platform: {self.BASE_URL}\n")
            f.write(f"- Total Challenges: {len(test_results)}\n")
            f.write(f"- Accessible: {accessible_count}\n")
            f.write(f"- Access Rate: {summary['access_rate']}%\n")
            f.write(f"- Avg Response Time: {avg_response_time:.2f}ms\n\n")
            f.write("## Test Results\n\n")
            f.write("| Challenge | Accessible | Response Time |\n")
            f.write("|-----------|------------|---------------|\n")
            for r in test_results:
                status = "✓" if r.get("accessible") else "✗"
                f.write(f"| {r['challenge_id']} | {status} | {r.get('response_time_ms', 'N/A')}ms |\n")

        print(f"[+] 报告已保存: {report_file}")

        return summary


def main():
    """主入口"""
    tester = BugkuBatchTester()
    summary = tester.run_full_batch_test()

    print("\n" + "=" * 60)
    print("  Test Complete")
    print("=" * 60)
    print(f"Total tested: {summary['total_challenges_tested']}")
    print(f"Accessible: {summary['accessible_challenges']}")
    print(f"Access rate: {summary['access_rate']}%")
    print(f"Avg response time: {summary['avg_response_time_ms']}ms")


if __name__ == "__main__":
    main()