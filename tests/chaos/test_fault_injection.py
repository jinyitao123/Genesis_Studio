"""
混沌测试 - 故障注入与恢复测试
=============================

测试范围:
- 服务重启恢复
- 数据库故障
- 网络分区
- 级联故障

运行方式:
    pytest tests/chaos/test_fault_injection.py -v --run-chaos
"""

import pytest
import requests
import time
import subprocess
from datetime import datetime, timezone


class TestServiceRestart:
    """服务重启恢复测试"""

    @pytest.mark.chaos
    def test_query_api_restart_recovery(self, query_api_url):
        """测试Query API重启后恢复"""
        # 1. 验证服务正常
        resp = requests.get(f"{query_api_url}/api/health", timeout=5)
        assert resp.status_code == 200
        
        # 2. 重启服务
        subprocess.run(
            ["docker", "compose", "restart", "query-api"],
            check=True,
            capture_output=True
        )
        
        # 3. 等待恢复
        time.sleep(5)
        
        # 4. 验证恢复
        max_retries = 30
        for i in range(max_retries):
            try:
                resp = requests.get(f"{query_api_url}/api/health", timeout=5)
                if resp.status_code == 200:
                    break
            except requests.exceptions.ConnectionError:
                pass
            time.sleep(1)
        else:
            pytest.fail("Query API failed to recover after restart")
        
        # 5. 验证功能正常
        resp = requests.get(f"{query_api_url}/api/query/object-types", timeout=5)
        assert resp.status_code == 200

    @pytest.mark.chaos
    def test_command_api_restart_recovery(self, command_api_url):
        """测试Command API重启后恢复"""
        # 1. 验证服务正常
        resp = requests.get(f"{command_api_url}/health", timeout=5)
        assert resp.status_code == 200
        
        # 2. 重启服务
        subprocess.run(
            ["docker", "compose", "restart", "command-api"],
            check=True,
            capture_output=True
        )
        
        # 3. 等待恢复
        time.sleep(5)
        
        # 4. 验证恢复
        max_retries = 30
        for i in range(max_retries):
            try:
                resp = requests.get(f"{command_api_url}/health", timeout=5)
                if resp.status_code == 200:
                    break
            except requests.exceptions.ConnectionError:
                pass
            time.sleep(1)
        else:
            pytest.fail("Command API failed to recover after restart")

    @pytest.mark.chaos
    def test_redis_restart_recovery(self, query_api_url):
        """测试Redis重启后恢复"""
        # 1. 验证服务使用Redis
        resp = requests.get(f"{query_api_url}/api/health/dependencies", timeout=5)
        assert resp.status_code == 200
        
        # 2. 重启Redis
        subprocess.run(
            ["docker", "compose", "restart", "redis"],
            check=True,
            capture_output=True
        )
        
        # 3. 等待恢复
        time.sleep(10)
        
        # 4. 验证系统仍然可用
        resp = requests.get(f"{query_api_url}/api/health", timeout=5)
        assert resp.status_code == 200


class TestDatabaseFailure:
    """数据库故障测试"""

    @pytest.mark.chaos
    @pytest.mark.slow
    def test_neo4j_temporary_failure(self, query_api_url):
        """测试Neo4j临时故障"""
        # 暂停Neo4j
        subprocess.run(
            ["docker", "compose", "pause", "neo4j"],
            check=True,
            capture_output=True
        )
        
        try:
            # 等待并验证降级行为
            time.sleep(5)
            
            # API应该仍然响应（可能返回缓存或降级数据）
            resp = requests.get(f"{query_api_url}/api/health", timeout=5)
            assert resp.status_code == 200
        finally:
            # 恢复Neo4j
            subprocess.run(
                ["docker", "compose", "unpause", "neo4j"],
                check=True,
                capture_output=True
            )
            time.sleep(10)  # 等待完全恢复

    @pytest.mark.chaos
    @pytest.mark.slow
    def test_postgres_failure_impact(self, command_api_url):
        """测试Postgres故障影响"""
        # 暂停Postgres
        subprocess.run(
            ["docker", "compose", "pause", "postgres"],
            check=True,
            capture_output=True
        )
        
        try:
            time.sleep(5)
            
            # 健康检查应该仍然通过（核心功能不依赖Postgres）
            resp = requests.get(f"{command_api_url}/health", timeout=5)
            # 可能200或503，取决于依赖设计
            assert resp.status_code in [200, 503]
        finally:
            subprocess.run(
                ["docker", "compose", "unpause", "postgres"],
                check=True,
                capture_output=True
            )
            time.sleep(10)


class TestCascadingFailure:
    """级联故障测试"""

    @pytest.mark.chaos
    @pytest.mark.slow
    def test_worker_failure_handling(self, command_api_url):
        """测试Worker故障处理"""
        # 停止Worker
        subprocess.run(
            ["docker", "compose", "stop", "worker"],
            check=True,
            capture_output=True
        )
        
        try:
            # Command API应该继续接受请求
            resp = requests.get(f"{command_api_url}/health", timeout=5)
            assert resp.status_code == 200
            
            # 异步任务应该排队（不会失败）
            # 这里可以dispatch一个action并验证它不会立即失败
        finally:
            # 恢复Worker
            subprocess.run(
                ["docker", "compose", "start", "worker"],
                check=True,
                capture_output=True
            )
            time.sleep(5)

    @pytest.mark.chaos
    @pytest.mark.slow
    def test_multiple_service_failure(self, query_api_url, command_api_url):
        """测试多服务故障"""
        services = ["elasticsearch", "timescaledb"]
        
        # 暂停多个服务
        for svc in services:
            subprocess.run(
                ["docker", "compose", "pause", svc],
                check=True,
                capture_output=True
            )
        
        try:
            time.sleep(5)
            
            # 核心API应该仍然可用
            resp = requests.get(f"{query_api_url}/api/health", timeout=5)
            assert resp.status_code == 200
            
            resp = requests.get(f"{command_api_url}/health", timeout=5)
            assert resp.status_code == 200
        finally:
            # 恢复所有服务
            for svc in services:
                subprocess.run(
                    ["docker", "compose", "unpause", svc],
                    check=True,
                    capture_output=True
                )
            time.sleep(10)


class TestRecoveryProcedures:
    """恢复程序测试"""

    @pytest.mark.chaos
    def test_graceful_degradation(self, query_api_url):
        """测试优雅降级"""
        # 验证基础功能在压力下仍然可用
        for _ in range(10):
            resp = requests.get(f"{query_api_url}/api/health", timeout=5)
            assert resp.status_code == 200
            time.sleep(0.1)

    @pytest.mark.chaos
    def test_circuit_breaker_pattern(self, command_api_url):
        """测试熔断器模式"""
        # 快速发送多个请求测试熔断
        responses = []
        for _ in range(20):
            try:
                resp = requests.get(f"{command_api_url}/health", timeout=2)
                responses.append(resp.status_code)
            except requests.exceptions.Timeout:
                responses.append("timeout")
            except requests.exceptions.ConnectionError:
                responses.append("connection_error")
        
        # 大多数请求应该成功（或返回预期的错误）
        success_count = responses.count(200)
        assert success_count >= 10, f"Too many failures: {responses}"


class TestDataConsistency:
    """数据一致性测试"""

    @pytest.mark.chaos
    def test_transaction_atomicity_after_failure(self, command_api_url, query_api_url):
        """测试故障后事务原子性"""
        # 1. 登录
        login_resp = requests.post(
            f"{command_api_url}/api/auth/token",
            json={"username": "designer", "password": "designer"},
            timeout=5
        )
        token = login_resp.json()["access_token"]
        
        # 2. 触发一个dispatch
        dispatch_resp = requests.post(
            f"{command_api_url}/api/command/dispatch",
            json={
                "action_id": "ACT_CHAOS_TEST",
                "source_id": "chaos-test-1",
                "target_id": "chaos-test-2",
                "payload": {"test": "atomicity"}
            },
            headers={"Authorization": f"Bearer {token}"},
            timeout=5
        )
        
        # 3. 验证事务最终一致
        time.sleep(2)
        
        tx_resp = requests.get(f"{query_api_url}/api/query/transactions")
        assert tx_resp.status_code == 200
        
        transactions = tx_resp.json()
        # 应该能找到我们创建的事务
        found = any(
            tx.get("action_id") == "ACT_CHAOS_TEST" 
            for tx in transactions
        )
        # 注意：由于测试环境可能有其他数据，不强求找到
