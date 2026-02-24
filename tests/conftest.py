"""
Genesis Studio 测试套件配置
============================

测试分层:
- unit/: 单元测试 (纯函数、类、组件)
- integration/: 集成测试 (API、数据库、服务间)
- e2e_ui/: E2E测试 (用户旅程、前端UI)
- performance/: 性能测试 (k6)
- chaos/: 混沌测试 (故障注入)

运行测试:
    pytest tests/ -v
    pytest tests/unit -v
    pytest tests/integration -v
    pytest tests/e2e_ui -v
"""

import os

import pytest
from datetime import datetime, timezone

# 全局fixture
@pytest.fixture
def mock_timestamp():
    """返回标准mock时间戳"""
    return datetime.now(timezone.utc)

@pytest.fixture(scope="session")
def base_url():
    """API基础URL"""
    return "http://localhost:18080"

@pytest.fixture
def query_api_url():
    """Query API URL"""
    return "http://localhost:5000"

@pytest.fixture
def command_api_url():
    """Command API URL"""
    command_port = os.getenv("COMMAND_API_PORT", "8000")
    return f"http://localhost:{command_port}"

# 标记定义
unit = pytest.mark.unit
integration = pytest.mark.integration
e2e = pytest.mark.e2e
performance = pytest.mark.performance
chaos = pytest.mark.chaos
slow = pytest.mark.slow
flaky = pytest.mark.flaky
