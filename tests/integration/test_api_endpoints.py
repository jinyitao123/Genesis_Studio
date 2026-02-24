"""
集成测试 - API 端点测试
=======================

测试范围:
- Command API 端点 (FastAPI)
- Query API 端点 (Flask)
- gRPC 服务
- WebSocket

运行方式:
    pytest tests/integration/test_api_endpoints.py -v
"""

import pytest
import requests
from uuid import uuid4

class TestCommandAPIHealth:
    """Command API 健康检查"""

    @pytest.mark.integration
    def test_command_api_health(self, command_api_url):
        """测试Command API健康端点"""
        response = requests.get(f"{command_api_url}/health", timeout=5)
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["service"] == "command-api"

    @pytest.mark.integration
    def test_command_api_metrics(self, command_api_url):
        """测试Command API指标端点"""
        response = requests.get(f"{command_api_url}/metrics", timeout=5)
        
        # Prometheus指标格式
        assert response.status_code == 200
        assert "http_request" in response.text or "python" in response.text


class TestQueryAPIHealth:
    """Query API 健康检查"""

    @pytest.mark.integration
    def test_query_api_health(self, query_api_url):
        """测试Query API健康端点"""
        response = requests.get(f"{query_api_url}/api/health", timeout=5)
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"

    @pytest.mark.integration
    def test_query_api_dependency_health(self, query_api_url):
        """测试Query API依赖健康检查"""
        response = requests.get(f"{query_api_url}/api/health/dependencies", timeout=5)
        
        assert response.status_code == 200
        data = response.json()
        assert "dependencies" in data or "docker" in data


class TestAuthenticationFlow:
    """认证流程集成测试"""

    @pytest.mark.integration
    def test_login_success(self, command_api_url):
        """测试登录成功"""
        payload = {
            "username": "designer",
            "password": "designer"
        }
        
        response = requests.post(
            f"{command_api_url}/api/auth/token",
            json=payload,
            timeout=5
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "token_type" in data
        assert data["token_type"] == "bearer"

    @pytest.mark.integration
    def test_login_invalid_credentials(self, command_api_url):
        """测试登录失败 - 无效凭证"""
        payload = {
            "username": "invalid",
            "password": "wrong"
        }
        
        response = requests.post(
            f"{command_api_url}/api/auth/token",
            json=payload,
            timeout=5
        )
        
        assert response.status_code == 401

    @pytest.mark.integration
    def test_access_protected_endpoint(self, command_api_url):
        """测试访问受保护端点"""
        # 1. 登录获取token
        login_resp = requests.post(
            f"{command_api_url}/api/auth/token",
            json={"username": "designer", "password": "designer"},
            timeout=5
        )
        token = login_resp.json()["access_token"]
        
        # 2. 使用token访问受保护端点
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(
            f"{command_api_url}/api/command/proposals",
            headers=headers,
            timeout=5
        )
        
        assert response.status_code == 200


class TestObjectTypeCRUD:
    """Object Type CRUD 集成测试"""

    @pytest.mark.integration
    def test_create_object_type(self, command_api_url):
        """测试创建Object Type"""
        # 获取token
        login_resp = requests.post(
            f"{command_api_url}/api/auth/token",
            json={"username": "designer", "password": "designer"},
            timeout=5
        )
        token = login_resp.json()["access_token"]
        
        # 创建OTD
        type_uri = f"com.genesis.integration.test.Unit{uuid4().hex[:8]}"
        payload = {
            "type_uri": type_uri,
            "display_name": "Integration Test Unit",
            "parent_type": None,
            "tags": ["integration", "test"],
            "properties": {
                "test_field": {"type": "string", "storage": "static"}
            }
        }
        
        response = requests.post(
            f"{command_api_url}/api/command/object-types",
            json=payload,
            headers={"Authorization": f"Bearer {token}"},
            timeout=5
        )
        
        assert response.status_code in [200, 201]

    @pytest.mark.integration
    def test_list_object_types(self, query_api_url):
        """测试列出Object Types"""
        response = requests.get(
            f"{query_api_url}/api/query/object-types",
            timeout=5
        )
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)


class TestActionDispatch:
    """Action Dispatch 集成测试"""

    @pytest.mark.integration
    def test_dispatch_action_dry_run(self, command_api_url):
        """测试Action Dry Run"""
        login_resp = requests.post(
            f"{command_api_url}/api/auth/token",
            json={"username": "designer", "password": "designer"},
            timeout=5
        )
        token = login_resp.json()["access_token"]
        
        payload = {
            "action_id": "ACT_TEST_ACTION",
            "source_id": "entity-1",
            "target_id": "entity-2",
            "payload": {"test": True},
            "dry_run": True
        }
        
        response = requests.post(
            f"{command_api_url}/api/command/dispatch",
            json=payload,
            headers={"Authorization": f"Bearer {token}"},
            timeout=5
        )
        
        # Dry run应该返回预估结果
        assert response.status_code in [200, 202]

    @pytest.mark.integration
    def test_get_transactions(self, query_api_url):
        """测试获取Transactions"""
        response = requests.get(
            f"{query_api_url}/api/query/transactions",
            timeout=5
        )
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)


class TestTransactionLineage:
    """Transaction Lineage 集成测试"""

    @pytest.mark.integration
    def test_get_transaction_lineage(self, query_api_url):
        """测试获取Transaction Lineage"""
        # 先获取transactions
        tx_resp = requests.get(
            f"{query_api_url}/api/query/transactions",
            timeout=5
        )
        
        if tx_resp.status_code == 200:
            transactions = tx_resp.json()
            if transactions:
                txn_id = transactions[0]["txn_id"]
                
                # 获取lineage
                response = requests.get(
                    f"{query_api_url}/api/query/transactions/lineage/{txn_id}",
                    timeout=5
                )
                
                assert response.status_code == 200
                data = response.json()
                assert "transaction" in data

    @pytest.mark.integration
    def test_get_lineage_aggregate(self, query_api_url):
        """测试获取Lineage Aggregate"""
        tx_resp = requests.get(
            f"{query_api_url}/api/query/transactions",
            timeout=5
        )
        
        if tx_resp.status_code == 200:
            transactions = tx_resp.json()
            if transactions:
                txn_id = transactions[0]["txn_id"]
                
                response = requests.get(
                    f"{query_api_url}/api/query/transactions/lineage/{txn_id}/aggregate",
                    timeout=5
                )
                
                assert response.status_code == 200
                data = response.json()
                assert "lineage" in data
                assert "bus_events" in data


class TestCopilotAPI:
    """Copilot API 集成测试"""

    @pytest.mark.integration
    def test_copilot_route(self, command_api_url):
        """测试Copilot路由"""
        login_resp = requests.post(
            f"{command_api_url}/api/auth/token",
            json={"username": "designer", "password": "designer"},
            timeout=5
        )
        token = login_resp.json()["access_token"]
        
        payload = {
            "intent": "create_unit",
            "prompt": "创建一个测试单位",
            "context": {}
        }
        
        response = requests.post(
            f"{command_api_url}/api/copilot/route",
            json=payload,
            headers={"Authorization": f"Bearer {token}"},
            timeout=5
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "agent" in data
        assert "confidence" in data


class TestABACSecureEndpoints:
    """ABAC 安全端点集成测试"""

    @pytest.mark.integration
    def test_secure_transactions_viewer(self, query_api_url, command_api_url):
        """测试Viewer角色访问安全Transactions"""
        # Viewer登录
        login_resp = requests.post(
            f"{command_api_url}/api/auth/token",
            json={"username": "viewer", "password": "viewer"},
            timeout=5
        )
        token = login_resp.json()["access_token"]
        
        # 访问安全端点
        response = requests.get(
            f"{query_api_url}/api/query/transactions/secure",
            headers={"Authorization": f"Bearer {token}"},
            timeout=5
        )
        
        assert response.status_code == 200
        data = response.json()
        # Viewer应该看到过滤后的字段
        if data:
            assert "actor" not in data[0] or "gates" not in data[0]

    @pytest.mark.integration
    def test_secure_transactions_unauthorized(self, query_api_url):
        """测试未授权访问安全端点"""
        response = requests.get(
            f"{query_api_url}/api/query/transactions/secure",
            timeout=5
        )
        
        assert response.status_code == 401


class TestProjectionAPI:
    """Projection API 集成测试"""

    @pytest.mark.integration
    def test_get_latest_projection(self, query_api_url):
        """测试获取最新Projection"""
        response = requests.get(
            f"{query_api_url}/api/query/projections/latest",
            timeout=5
        )
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)
        if data:
            assert "projection_id" in data

    @pytest.mark.integration
    def test_get_projection_lag(self, query_api_url):
        """测试获取Projection Lag"""
        response = requests.get(
            f"{query_api_url}/api/query/projections/lag",
            timeout=5
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "lag" in data
        assert "stream_event_count" in data
