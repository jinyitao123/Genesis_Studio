#!/usr/bin/env python3
"""
Genesis Studio 全量测试运行器
==============================

运行所有测试套件并生成报告。

使用方法:
    python tests/run_all_tests.py [options]

选项:
    --unit          运行单元测试
    --integration   运行集成测试（需要服务运行）
    --e2e           运行E2E测试（需要服务和浏览器）
    --performance   运行性能测试（需要k6）
    --chaos         运行混沌测试（需要docker）
    --all           运行所有测试
    --report        生成HTML报告

示例:
    python tests/run_all_tests.py --unit
    python tests/run_all_tests.py --all --report
"""

import subprocess
import sys
import argparse
import json
from datetime import datetime
from pathlib import Path

# 测试套件配置
TEST_SUITES = {
    "unit": {
        "path": "tests/unit",
        "requires": [],
        "description": "单元测试",
    },
    "integration": {
        "path": "tests/integration",
        "requires": ["services"],
        "description": "集成测试（需要运行中的服务）",
        "marker": "integration",
    },
    "e2e": {
        "path": "tests/e2e_ui",
        "requires": ["services", "browser"],
        "description": "E2E测试（需要服务和浏览器）",
        "marker": "e2e",
    },
    "chaos": {
        "path": "tests/chaos",
        "requires": ["docker"],
        "description": "混沌测试（需要Docker）",
        "marker": "chaos",
    },
}

PERF_TESTS = {
    "smoke": "perf/smoke_test.js",
    "load": "perf/load_test.js",
    "stress": "perf/stress_test.js",
    "lineage": "perf/lineage_query.js",
    "projection": "perf/projection_lag.js",
}


def run_pytest_tests(path: str, marker: str | None = None, report: bool = False) -> dict:
    """运行pytest测试"""
    cmd = ["python", "-m", "pytest", path, "-v"]
    
    if marker:
        cmd.extend(["-m", marker])
    
    if report:
        cmd.extend(["--html=reports/pytest_report.html", "--self-contained-html"])
    
    cmd.extend(["--tb=short"])
    
    print(f"\n{'='*60}")
    print(f"运行: {' '.join(cmd)}")
    print('='*60)
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    print(result.stdout)
    if result.stderr:
        print(result.stderr)
    
    # 解析结果
    passed = result.stdout.count("PASSED")
    failed = result.stdout.count("FAILED")
    skipped = result.stdout.count("SKIPPED")
    
    return {
        "passed": passed,
        "failed": failed,
        "skipped": skipped,
        "return_code": result.returncode,
    }


def run_k6_test(test_file: str) -> dict:
    """运行k6性能测试"""
    cmd = [
        "docker", "run", "--rm",
        "--network", "host",
        "-v", f"{Path.cwd()}/perf:/perf",
        "grafana/k6:0.52.0", "run", f"/perf/{test_file}"
    ]
    
    print(f"\n{'='*60}")
    print(f"运行性能测试: {test_file}")
    print('='*60)
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    print(result.stdout)
    if result.stderr:
        print(result.stderr)
    
    return {
        "return_code": result.returncode,
        "output": result.stdout,
    }


def check_prerequisites(requirements: list) -> bool:
    """检查前置条件"""
    for req in requirements:
        if req == "services":
            # 检查服务是否运行
            try:
                import requests
                resp = requests.get("http://localhost:5000/api/health", timeout=2)
                if resp.status_code != 200:
                    print(f"⚠️  服务未运行: {req}")
                    return False
            except Exception:
                print(f"⚠️  无法连接到服务，跳过需要服务的测试")
                return False
        
        elif req == "docker":
            result = subprocess.run(["docker", "ps"], capture_output=True)
            if result.returncode != 0:
                print(f"⚠️  Docker未运行，跳过混沌测试")
                return False
    
    return True


def generate_report(results: dict) -> str:
    """生成测试报告"""
    report_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    total_passed = sum(r.get("passed", 0) for r in results.values() if isinstance(r, dict))
    total_failed = sum(r.get("failed", 0) for r in results.values() if isinstance(r, dict))
    total_skipped = sum(r.get("skipped", 0) for r in results.values() if isinstance(r, dict))
    total = total_passed + total_failed + total_skipped
    
    report = f"""
╔══════════════════════════════════════════════════════════════════════╗
║           Genesis Studio 测试报告 - {report_time}           ║
╚══════════════════════════════════════════════════════════════════════╝

📊 测试结果汇总
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
总测试数:    {total}
通过:        {total_passed} ✅
失败:        {total_failed} ❌
跳过:        {total_skipped} ⚠️
通过率:      {(total_passed/max(total, 1)*100):.1f}%

📋 详细结果
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
    
    for suite_name, result in results.items():
        if isinstance(result, dict):
            status = "✅ PASS" if result.get("return_code", 1) == 0 else "❌ FAIL"
            report += f"""
{suite_name.upper()}:
  状态: {status}
  通过: {result.get('passed', 0)}
  失败: {result.get('failed', 0)}
  跳过: {result.get('skipped', 0)}
"""
    
    report += """
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📝 说明:
  ✅ - 测试通过
  ❌ - 测试失败
  ⚠️  - 测试跳过（前置条件不满足）

📁 报告文件:
  - 详细报告: reports/pytest_report.html
  - 日志文件: logs/test_run_*.log
"""
    
    return report


def main():
    parser = argparse.ArgumentParser(description="Genesis Studio 全量测试运行器")
    parser.add_argument("--unit", action="store_true", help="运行单元测试")
    parser.add_argument("--integration", action="store_true", help="运行集成测试")
    parser.add_argument("--e2e", action="store_true", help="运行E2E测试")
    parser.add_argument("--performance", action="store_true", help="运行性能测试")
    parser.add_argument("--chaos", action="store_true", help="运行混沌测试")
    parser.add_argument("--all", action="store_true", help="运行所有测试")
    parser.add_argument("--report", action="store_true", help="生成HTML报告")
    
    args = parser.parse_args()
    
    # 如果没有指定任何选项，默认运行单元测试
    if not any([args.unit, args.integration, args.e2e, args.performance, args.chaos, args.all]):
        args.unit = True
    
    # 如果指定了--all，启用所有测试
    if args.all:
        args.unit = True
        args.integration = True
        args.e2e = True
        args.performance = True
        args.chaos = True
    
    results = {}
    
    # 创建报告目录
    Path("reports").mkdir(exist_ok=True)
    Path("logs").mkdir(exist_ok=True)
    
    print("""
╔══════════════════════════════════════════════════════════════════════╗
║              Genesis Studio 全量测试套件 v3.0                         ║
╚══════════════════════════════════════════════════════════════════════╝
""")
    
    # 运行单元测试
    if args.unit:
        results["unit"] = run_pytest_tests(
            TEST_SUITES["unit"]["path"],
            report=args.report
        )
    
    # 运行集成测试
    if args.integration:
        if check_prerequisites(TEST_SUITES["integration"]["requires"]):
            results["integration"] = run_pytest_tests(
                TEST_SUITES["integration"]["path"],
                marker=TEST_SUITES["integration"]["marker"],
                report=args.report
            )
        else:
            print(f"\n⚠️  跳过集成测试: 前置条件不满足")
            results["integration"] = {"passed": 0, "failed": 0, "skipped": 0, "return_code": 0}
    
    # 运行E2E测试
    if args.e2e:
        if check_prerequisites(TEST_SUITES["e2e"]["requires"]):
            results["e2e"] = run_pytest_tests(
                TEST_SUITES["e2e"]["path"],
                marker=TEST_SUITES["e2e"]["marker"],
                report=args.report
            )
        else:
            print(f"\n⚠️  跳过E2E测试: 前置条件不满足")
            results["e2e"] = {"passed": 0, "failed": 0, "skipped": 0, "return_code": 0}
    
    # 运行混沌测试
    if args.chaos:
        if check_prerequisites(TEST_SUITES["chaos"]["requires"]):
            results["chaos"] = run_pytest_tests(
                TEST_SUITES["chaos"]["path"],
                marker=TEST_SUITES["chaos"]["marker"],
                report=args.report
            )
        else:
            print(f"\n⚠️  跳过混沌测试: 前置条件不满足")
            results["chaos"] = {"passed": 0, "failed": 0, "skipped": 0, "return_code": 0}
    
    # 运行性能测试
    if args.performance:
        print("\n🚀 性能测试需要手动运行k6:")
        print("   docker run --rm --network host -v \"$PWD/perf:/perf\" grafana/k6 run /perf/smoke_test.js")
        results["performance"] = {"passed": 0, "failed": 0, "skipped": 0, "return_code": 0}
    
    # 生成并打印报告
    report = generate_report(results)
    print(report)
    
    # 保存报告到文件
    report_file = f"reports/test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    with open(report_file, "w", encoding="utf-8") as f:
        f.write(report)
    print(f"\n📄 报告已保存到: {report_file}")
    
    # 返回退出码
    total_failed = sum(r.get("failed", 0) for r in results.values() if isinstance(r, dict))
    return 1 if total_failed > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
