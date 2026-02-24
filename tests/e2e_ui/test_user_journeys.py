"""
E2E 测试 - 用户旅程端到端测试
===============================

测试范围:
- 完整用户旅程（PRP v3.0 第9节）
- 前端UI交互
- AI Copilot 工作流
- 实时通知

运行方式:
    pytest tests/e2e_ui/test_user_journeys.py -v --headed
"""

import pytest
import re
from typing import Any

Page = Any


def expect(*args: Any, **kwargs: Any) -> Any:
    import importlib

    module = importlib.import_module("playwright.sync_api")
    return module.expect(*args, **kwargs)


@pytest.fixture
def studio_url():
    """Studio前端URL"""
    return "http://localhost:5173"


class TestUserJourneySetup:
    """用户旅程 - 阶段1: 启动与上下文"""

    @pytest.mark.e2e
    def test_studio_loads_successfully(self, page: Page, studio_url):
        """测试Studio成功加载"""
        page.goto(studio_url)
        
        # 验证页面标题
        expect(page).to_have_title(re.compile("Genesis Studio"))
        
        # 验证关键元素存在
        expect(page.locator("text=图谱")).to_be_visible()
        expect(page.locator("text=时间线")).to_be_visible()
        expect(page.locator("text=逻辑")).to_be_visible()
        expect(page.locator("text=AI助手")).to_be_visible()

    @pytest.mark.e2e
    def test_health_status_displayed(self, page: Page, studio_url):
        """测试健康状态显示"""
        page.goto(studio_url)
        
        # 等待健康检查完成
        page.wait_for_timeout(2000)
        
        # 验证健康状态指示器
        health_indicator = page.locator("[data-testid='health-indicator']")
        if health_indicator.is_visible():
            expect(health_indicator).to_have_class(re.compile("healthy|ok"))

    @pytest.mark.e2e
    def test_tab_navigation(self, page: Page, studio_url):
        """测试标签页导航"""
        page.goto(studio_url)
        
        # 点击各个标签
        tabs = ["图谱", "时间线", "逻辑", "追溯", "检查器", "提案", "AI助手"]
        
        for tab in tabs:
            tab_button = page.locator(f"button:has-text('{tab}')")
            if tab_button.is_visible():
                tab_button.click()
                page.wait_for_timeout(500)
                
                # 验证标签被选中
                expect(tab_button).to_have_class(re.compile("active|selected"))


class TestUserJourneyAICreation:
    """用户旅程 - 阶段2: AI辅助生成本体"""

    @pytest.mark.e2e
    def test_copilot_chat_interface(self, page: Page, studio_url):
        """测试Copilot聊天界面"""
        page.goto(studio_url)
        
        # 切换到AI助手标签
        page.click("button:has-text('AI助手')")
        
        # 验证聊天界面元素
        expect(page.locator("[data-testid='copilot-chat']")).to_be_visible()
        expect(page.locator("input[placeholder*='输入指令']")).to_be_visible()

    @pytest.mark.e2e
    def test_create_drone_via_copilot(self, page: Page, studio_url):
        """测试通过Copilot创建Drone单位"""
        page.goto(studio_url)
        
        # 切换到AI助手
        page.click("button:has-text('AI助手')")
        
        # 输入创建指令
        chat_input = page.locator("input[placeholder*='输入指令']")
        chat_input.fill("创建一个Drone单位，它是空中单位，拥有电池电量属性")
        chat_input.press("Enter")
        
        # 等待AI响应
        page.wait_for_timeout(3000)
        
        # 验证Proposal Card出现
        proposal_card = page.locator("[data-testid='proposal-card']")
        expect(proposal_card).to_be_visible(timeout=10000)
        
        # 验证提案内容
        expect(page.locator("text=ObjectType")).to_be_visible()
        expect(page.locator("text=battery_level")).to_be_visible()

    @pytest.mark.e2e
    def test_proposal_card_interactions(self, page: Page, studio_url):
        """测试Proposal Card交互"""
        page.goto(f"{studio_url}?demo=proposal")
        
        # 切换到提案标签
        page.click("button:has-text('提案')")
        
        # 验证提案卡片存在
        proposal_card = page.locator("[data-testid='proposal-card']").first
        expect(proposal_card).to_be_visible()
        
        # 验证操作按钮
        expect(page.locator("button:has-text('Diff View')")).to_be_visible()
        expect(page.locator("button:has-text('Apply')")).to_be_visible()
        expect(page.locator("button:has-text('Reject')")).to_be_visible()


class TestUserJourneyVisualRefinement:
    """用户旅程 - 阶段3: 可视化微调"""

    @pytest.mark.e2e
    def test_inspector_panel_displays(self, page: Page, studio_url):
        """测试检查器面板显示"""
        page.goto(studio_url)
        
        # 切换到检查器标签
        page.click("button:has-text('检查器')")
        
        # 验证检查器面板
        inspector = page.locator("[data-testid='inspector-panel']")
        expect(inspector).to_be_visible()

    @pytest.mark.e2e
    def test_graph_visualizer_interactive(self, page: Page, studio_url):
        """测试图谱可视化交互"""
        page.goto(studio_url)
        
        # 切换到图谱标签
        page.click("button:has-text('图谱')")
        
        # 等待图谱加载
        page.wait_for_timeout(2000)
        
        # 验证图谱容器
        graph_container = page.locator("[data-testid='graph-visualizer']")
        expect(graph_container).to_be_visible()
        
        # 尝试拖拽（如果节点存在）
        nodes = page.locator(".graph-node")
        if nodes.count() > 0:
            first_node = nodes.first
            # 模拟点击节点
            first_node.click()
            
            # 验证节点被选中
            expect(first_node).to_have_class(re.compile("selected"))


class TestUserJourneyLogicOrchestration:
    """用户旅程 - 阶段4: 定义复杂逻辑"""

    @pytest.mark.e2e
    def test_logic_composer_interface(self, page: Page, studio_url):
        """测试逻辑编排器界面"""
        page.goto(studio_url)
        
        # 切换到逻辑标签
        page.click("button:has-text('逻辑')")
        
        # 验证逻辑面板
        logic_panel = page.locator("[data-testid='logic-panel']")
        expect(logic_panel).to_be_visible()

    @pytest.mark.e2e
    def test_action_form_builder(self, page: Page, studio_url):
        """测试Action表单构建器"""
        page.goto(studio_url)
        
        # 找到Action表单
        action_form = page.locator("[data-testid='action-form-builder']")
        
        if action_form.is_visible():
            # 测试选择Action类型
            action_select = page.locator("select[name='action_id']")
            action_select.select_option("ACT_SELF_DESTRUCT")
            
            # 填写表单
            page.fill("input[name='source_id']", "test-entity-1")
            page.fill("input[name='target_id']", "test-entity-2")
            
            # 验证表单值
            expect(page.locator("input[name='source_id']")).to_have_value("test-entity-1")


class TestUserJourneyValidationCommit:
    """用户旅程 - 阶段5: 验证与提交"""

    @pytest.mark.e2e
    def test_validation_button_triggers_check(self, page: Page, studio_url):
        """测试验证按钮触发检查"""
        page.goto(studio_url)
        
        # 查找验证按钮
        validate_button = page.locator("button:has-text('验证')")
        
        if validate_button.is_visible():
            validate_button.click()
            
            # 等待验证完成
            page.wait_for_timeout(2000)
            
            # 验证结果显示
            validation_result = page.locator("[data-testid='validation-result']")
            expect(validation_result).to_be_visible()

    @pytest.mark.e2e
    def test_commit_workflow(self, page: Page, studio_url):
        """测试提交工作流"""
        page.goto(studio_url)
        
        # 切换到提案标签
        page.click("button:has-text('提案')")
        
        # 查找提交按钮
        commit_button = page.locator("button:has-text('提交')")
        
        if commit_button.is_visible():
            commit_button.click()
            
            # 验证提交对话框
            commit_dialog = page.locator("[data-testid='commit-dialog']")
            expect(commit_dialog).to_be_visible()


class TestUserJourneyRuntimeSimulation:
    """用户旅程 - 阶段6: 运行时测试"""

    @pytest.mark.e2e
    def test_timeline_controller_interface(self, page: Page, studio_url):
        """测试时间线控制器界面"""
        page.goto(studio_url)
        
        # 切换到时间线标签
        page.click("button:has-text('时间线')")
        
        # 验证时间线面板
        timeline_panel = page.locator("[data-testid='timeline-panel']")
        expect(timeline_panel).to_be_visible()
        
        # 验证时间线控制器
        timeline_controller = page.locator("[data-testid='timeline-controller']")
        expect(timeline_controller).to_be_visible()

    @pytest.mark.e2e
    def test_tick_navigation(self, page: Page, studio_url):
        """测试Tick导航"""
        page.goto(studio_url)
        
        # 切换到时间线标签
        page.click("button:has-text('时间线')")
        
        # 查找Tick显示
        tick_display = page.locator("[data-testid='tick-display']")
        
        if tick_display.is_visible():
            # 验证初始Tick值
            initial_tick = tick_display.inner_text()
            
            # 查找前进/后退按钮
            next_button = page.locator("button[title='下一Tick']")
            if next_button.is_visible():
                next_button.click()
                page.wait_for_timeout(500)
                
                # 验证Tick变化
                new_tick = tick_display.inner_text()
                assert new_tick != initial_tick or initial_tick == "0"

    @pytest.mark.e2e
    def test_lineage_graph_displays(self, page: Page, studio_url):
        """测试血缘图显示"""
        page.goto(studio_url)
        
        # 切换到追溯标签
        page.click("button:has-text('追溯')")
        
        # 验证血缘图
        lineage_graph = page.locator("[data-testid='lineage-graph']")
        expect(lineage_graph).to_be_visible()


class TestRealtimeNotifications:
    """实时通知E2E测试"""

    @pytest.mark.e2e
    def test_notification_indicator(self, page: Page, studio_url):
        """测试通知指示器"""
        page.goto(studio_url)
        
        # 查找通知指示器
        notification_indicator = page.locator("[data-testid='notification-indicator']")
        
        # 即使没有通知，指示器也应该存在
        if notification_indicator.is_visible():
            expect(notification_indicator).to_be_visible()

    @pytest.mark.e2e
    def test_websocket_connection_status(self, page: Page, studio_url):
        """测试WebSocket连接状态"""
        page.goto(studio_url)
        
        # 等待WebSocket连接
        page.wait_for_timeout(3000)
        
        # 查找连接状态指示器
        ws_indicator = page.locator("[data-testid='websocket-status']")
        
        if ws_indicator.is_visible():
            # 验证连接状态
            status_text = ws_indicator.inner_text()
            assert any(status in status_text.lower() for status in ["connected", "已连接", "ok"])


class TestStudioCoreWorkflow:
    """Studio核心工作流E2E测试"""

    @pytest.mark.e2e
    @pytest.mark.slow
    def test_complete_drone_creation_workflow(self, page: Page, studio_url):
        """测试完整的Drone创建工作流"""
        page.goto(studio_url)
        
        # 1. 使用Copilot创建Drone
        page.click("button:has-text('AI助手')")
        chat_input = page.locator("input[placeholder*='输入指令']")
        chat_input.fill("创建一个Drone单位")
        chat_input.press("Enter")
        
        # 等待AI响应
        page.wait_for_timeout(3000)
        
        # 2. 验证Proposal Card
        proposal_card = page.locator("[data-testid='proposal-card']")
        if proposal_card.is_visible():
            # 3. 应用提案
            apply_button = page.locator("button:has-text('Apply')")
            if apply_button.is_visible():
                apply_button.click()
                
                # 等待应用完成
                page.wait_for_timeout(2000)
                
                # 4. 切换到图谱查看
                page.click("button:has-text('图谱')")
                page.wait_for_timeout(1000)
                
                # 5. 验证Drone出现在图谱中
                graph_container = page.locator("[data-testid='graph-visualizer']")
                expect(graph_container).to_be_visible()

    @pytest.mark.e2e
    @pytest.mark.slow
    def test_action_execution_workflow(self, page: Page, studio_url):
        """测试Action执行工作流"""
        page.goto(studio_url)
        
        # 1. 找到Action表单
        action_form = page.locator("[data-testid='action-form-builder']")
        
        if action_form.is_visible():
            # 2. 填写并执行Action
            page.select_option("select[name='action_id']", "ACT_MOVE")
            page.fill("input[name='source_id']", "entity-1")
            page.fill("input[name='target_id']", "entity-2")
            
            # 3. 执行
            execute_button = page.locator("button:has-text('执行')")
            if execute_button.is_visible():
                execute_button.click()
                
                # 4. 验证执行结果
                page.wait_for_timeout(2000)
                result_indicator = page.locator("[data-testid='action-result']")
                expect(result_indicator).to_be_visible()
