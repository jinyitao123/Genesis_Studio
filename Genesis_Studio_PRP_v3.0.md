# Genesis Studio — 产品参考计划 (Product Reference Plan)

**版本：** v3.0 (Enterprise Studio Edition — Enhanced Ontology + Event Sourcing)

**架构范式：** 模型驱动架构 (MDA) + 对象中心本体论 (Object-Centric Ontology) + CQRS/Event Sourcing

**日期：** 2026-02-11

**状态：** 已实施 / 激活 (Implemented / Active)

**分类：** 内部机密 (Internal Confidential)

---

## 修订历史

| 版本 | 日期 | 变更摘要 | 作者 |
|------|------|---------|------|
| v1.0 | 2025-08-15 | 初始版本，基础仿真编辑器概念 | 架构组 |
| v2.0 | 2025-11-20 | 引入 Palantir Ontology 设计理念 | 架构组 |
| v2.1 | 2026-02-10 | 增强本体层，完善前后端详细设计 | 架构组 |
| v3.0 | 2026-02-11 | 全面增强：CQRS/ES、零信任安全、可观测性、部署策略、测试体系、性能基准、容灾方案 | 架构组 |

---

## 1. 执行摘要 (Executive Summary)

**Genesis Studio** 是一个企业级的、基于本体的仿真世界构建平台。它超越传统代码编辑器，升级为可视化集成开发环境 (IDE)，弥合人类设计意图与复杂仿真内核之间的鸿沟。

本平台利用**动态本体层 (DOL)** 技术，允许设计师通过定义对象、链接和动力学来构建高保真数字孪生世界。系统核心采用 **Git-Ops** 工作流与**事件溯源 (Event Sourcing)** 架构，确保所有逻辑变更、模型迭代和数据注入具备完全的可追溯性、版本控制能力和热重载能力。

### 1.1 核心能力矩阵

| 能力域 | 能力描述 | 技术支撑 | 业务价值 |
|--------|---------|---------|---------|
| 语义本体建模 | 数据视为具有继承性、多态性和时间维度的对象 | Neo4j + Pydantic OTD Schema | 消除数据孤岛，统一语义理解 |
| 动态链接系统 | 链接作为一等公民，拥有独立属性和生命周期钩子 | Neo4j Edge Reification + Redis TTL | 复杂关系动态演化建模 |
| 全链路审计 | 所有状态变更通过封装的 Action 执行 | Event Sourcing + Immutable Log | 完全可回溯的写回机制 |
| 时序回溯 | 原生支持时序属性与时间旅行 | TimescaleDB + Delta Snapshot | 历史重放与根因分析 |
| 智能辅助设计 | AI Copilot 代理路由系统 | LangChain + RAG + Multi-Agent | 降低建模门槛，加速迭代 |
| 零停机热更新 | 蓝绿切换运行时配置迁移 | Git-Ops + Blue-Green Deploy | 设计变更即时生效 |
| 零信任安全 | RBAC + ABAC 混合模型 | OAuth 2.0 + mTLS + Vault | 细粒度权限控制到字段级 |
| 全栈可观测 | 分布式链路追踪与统一遥测 | OpenTelemetry + Grafana Stack | 全链路性能可视化 |

### 1.2 v3.0 与 v2.1 关键差异

| 维度 | v2.1 | v3.0 (本版本) | 改进说明 |
|------|------|--------------|---------|
| 架构范式 | MDA + Ontology | MDA + Ontology + Event Sourcing + CQRS | 命令查询分离与事件溯源 |
| 安全模型 | 基础权限检查 | RBAC + ABAC + 零信任 | 字段级权限控制 |
| 可观测性 | 基础日志 | OpenTelemetry + 分布式追踪 | 全链路性能可视化 |
| 数据管道 | 语义映射通道 | 增强 ETL + CDC + Schema Evolution | 在线 Schema 演化 |
| 部署模式 | 未定义 | K8s + Helm + Istio | 生产级容器编排 |
| 测试策略 | 未定义 | 金字塔 + 契约测试 + 混沌工程 | 全面质量保障 |
| 容灾 | 未定义 | 多区域主备, RPO<1min, RTO<5min | 企业级业务连续性 |
| 性能 | 未定义 | 全场景 SLA + 性能预算 | 可量化性能保障 |
| 本体演化 | 静态 Schema | Schema Versioning + Online Migration | 无损在线演进 |
| AI 安全 | 无防护 | Guardrails + AST 沙箱 + 审批门 | AI 内容安全可控 |

---

## 2. 架构概览 (Architecture Overview)

Genesis Studio 充当 PIM (平台无关模型) 的托管者，将其编译为 PSM (平台特定模型) 注入运行时内核。v3.0 引入 CQRS + Event Sourcing，读写路径彻底解耦。

### 2.1 MDA 增强分层模型

| 层级 | Genesis 概念 | 描述 | v3.0 增强 |
|------|-------------|------|----------|
| **CIM** (计算无关) | 领域概念 | 纯业务领域模型 | 领域事件词汇表 |
| **PIM** (平台无关) | 动态本体层 (DOL) | 核心资产：OTD、LTD、Action Sets | Schema 版本化 + Migration |
| **PSM** (平台特定) | 内核运行时 | 执行工件：Python/Neo4j/TimescaleDB | CQRS 读写分离 |
| **ISM** (基础设施) | 部署拓扑 | 容器编排与服务网格 | K8s + Istio + GitOps CD |

### 2.2 CQRS + Event Sourcing 架构

```
┌─────────────────────────────────────────────────────────┐
│               API Gateway (Kong/Envoy)                   │
│            Rate Limiting · Auth · Routing                │
├────────────────────┬────────────────────────────────────┤
│  Command Side      │       Query Side                    │
│  (Write Path)      │       (Read Path)                   │
│                    │                                     │
│ ┌────────────────┐ │ ┌──────────────────────────────┐   │
│ │ActionDispatcher│ │ │ ObjectService (Read Replica)  │   │
│ │  (FastAPI)     │ │ │ SearchService                │   │
│ └──────┬─────────┘ │ │ TimeTravelService (Read)      │   │
│        │           │ └────────────┬─────────────────┘   │
│        ▼           │              │                      │
│ ┌────────────────┐ │ ┌────────────▼────────────────┐   │
│ │ Event Store    │─┼─│ Read Model Projections      │   │
│ │ (Append-Only)  │ │ │ (Neo4j · ES · TSDB)         │   │
│ └────────────────┘ │ └─────────────────────────────┘   │
└────────────────────┴────────────────────────────────────┘
```

核心原则：Command 通过 ActionDispatcher 进入 Event Store，产生不可变 Domain Event。Projector 异步消费事件流写入读模型。Query 直接从读模型获取数据。

### 2.3 技术栈全景

#### 前端 (表示层)

| 类别 | 技术 | 用途 |
|------|------|------|
| 框架 | Vue 3 (Composition API) + TypeScript 5.x + Vite 5.x | 企业级组件架构 |
| 状态 | Pinia + RxJS | Draft State + Reactive WebSocket |
| 图谱 | Cytoscape.js + WebGL Overlay | 大规模拓扑渲染 (10k+) |
| 逻辑编排 | Vue Flow | 节点式规则链设计 |
| 仪表盘 | ECharts 5.x / D3.js v7 | 时序可视化 |
| 编辑器 | Monaco Editor | JSON/Cypher/Python |
| 样式 | Tailwind CSS 3.x + Headless UI | 无障碍响应式 |
| 地理 | Mapbox GL / Cesium | GIS + 3D 地球 |
| 构建 | Vite Module Federation + Service Worker | 微前端 + 离线缓存 |

#### 后端 (逻辑层)

| 类别 | 技术 | 用途 |
|------|------|------|
| API 网关 | Kong / Envoy | 限流·认证·路由·灰度 |
| 命令服务 | FastAPI (Python 3.11+) | 异步高并发 Action |
| 查询服务 | Flask (蓝图) | 读优化端点 |
| 验证 | Pydantic v2 + Cerberus | Schema 强制 + 自定义规则 |
| 版本控制 | GitPython | Git 存储后端 |
| 消息 | Redis Streams / Kafka | 异步事件解耦 |
| 任务 | Celery + APScheduler | 异步 + 定时 |
| 通信 | REST · WebSocket · gRPC | 多协议 |
| AI | LangChain + LlamaIndex | LLM 编排与 RAG |

#### 持久化 (数据层)

| 类别 | 技术 | 用途 |
|------|------|------|
| Schema 存储 | 文件系统 (Git) | **单一真理来源** |
| 事件存储 | EventStoreDB / Kafka + PostgreSQL | 不可变事件流 |
| 图数据库 | Neo4j 5.x | 拓扑关系计算 |
| 时序 | TimescaleDB 2.x / InfluxDB 3.x | 属性历史 + 传感器 |
| 搜索 | Elasticsearch 8.x | 全文 + 地理空间 |
| 向量 | Milvus / Chroma | AI 语义检索 |
| 缓存 | Redis 7.x | 热数据 + 锁 + Pub/Sub |
| 关系 | PostgreSQL 16 | 用户/权限/审计 |

#### 基础设施

| 类别 | 技术 | 用途 |
|------|------|------|
| 编排 | Kubernetes 1.28+ / Helm | 声明式部署 |
| 网格 | Istio 1.20+ | mTLS·流量·熔断 |
| CI/CD | GitLab CI / ArgoCD | GitOps 持续部署 |
| 观测 | OpenTelemetry + Grafana + Loki + Tempo | Metrics·Logs·Traces |
| 密钥 | HashiCorp Vault | 动态轮转 |
| 对象 | MinIO / S3 | 大型二进制资产 |

---

## 3. 动态本体层设计 (DOL)

构建**全语义、时空感知、高性能**的对象网格。v3.0 引入 Schema 版本化和在线迁移。

### 3.1 对象类型定义 (OTD)

#### 3.1.1 元数据与继承

- **URI 命名空间:** `com.{domain}.{subdomain}.{Entity}` 反向域名格式
- **深度继承:** Prototype Chain 机制。子类型继承所有属性/动作/资产，可覆盖默认值但不能改变类型 (Liskov)
- **接口 (v3.0):** 多接口实现 (`IMovable`, `IDamageable`)，定义属性契约和必须实现的 Action
- **密封类型 (v3.0):** `sealed: true` 禁止继承，保护核心系统类型
- **抽象类型:** `abstract: true` 不能直接实例化

#### 3.1.2 完整 OTD Schema

```json
{
  "type_uri": "com.genesis.mil.unit.Tank",
  "schema_version": "3.0.1",
  "display_name": "Main Battle Tank",
  "parent_type": "com.genesis.mil.unit.Vehicle",
  "implements": ["IMovable", "IDamageable", "IDetectable"],
  "sealed": false, "abstract": false,
  "icon": {
    "default": "assets/icons/tank_green.svg",
    "condition": "status == 'Destroyed' ? 'wreck.svg' : 'default'"
  },
  "3d_model": {
    "default": "assets/models/m1a2.glb",
    "lod_levels": { "high": "m1a2_high.glb", "medium": "m1a2_med.glb", "low": "m1a2_low.glb" }
  },
  "tags": ["military", "ground", "armored"],
  "access_control": { "read": ["*"], "write": ["admin", "designer"], "delete": ["admin"] },
  "properties": { "...见 3.1.3..." },
  "bound_actions": ["ACT_FIRE", "ACT_MOVE", "ACT_REPAIR"],
  "lifecycle_hooks": { "on_spawn": "scripts/tank_init.py", "on_destroy": "scripts/tank_cleanup.py" }
}
```

#### 3.1.3 属性系统

| 类别 | 存储 | 特征 | 典型应用 | 一致性 |
|------|------|------|---------|--------|
| **Static** | Neo4j | 读多写少，索引 | UUID, MaxAmmo | 强一致 |
| **Time-Series** | TimescaleDB | 追加写，按 Tick | Speed, Fuel, GPS | 最终一致 (1-tick) |
| **Computed** | Redis Cache | 运行时求值 | DangerLevel, ETA | Cache TTL |
| **Soft-Link** | ES / H3 | 动态聚合 | NearbyEnemies | 最终一致 (CDC) |
| **Derived** (v3.0) | Materialized View | 预聚合刷新 | TeamStrength | 定期快照 |

**静态属性规范：** 支持 Validators (regex/range/enum/custom)、索引 (index/fulltext/composite)、不可变 (immutable)、动态默认值 (`$uuid4()`, `$now()`)。

**时序属性规范：** 双时间戳 (tick + wall_clock)、插值策略 (linear/previous/zero/spline)、采样优化 (sample_rate + change_threshold)、分级保留 (raw 7d → downsampled 90d → archive 365d)。

**计算属性规范：** RestrictedPython 沙箱或 Cypher 片段、自动依赖 DAG 追踪、三层缓存 (L1 进程 → L2 Redis → L3 重算)。

**软链接属性 (核心创新)：** 不是物理边而是预定义搜索查询模板。查询类型：geo_spatial / full_text / graph_pattern / hybrid。运行时实时执行返回排序对象列表。

```json
{
  "nearby_enemies": {
    "type": "soft_link",
    "query_type": "geo_spatial",
    "params": {
      "center": "this.location", "radius": "500m",
      "filter": "target.faction != this.faction AND target.status != 'Destroyed'",
      "sort_by": "distance ASC", "limit": 20
    },
    "cache_ttl_seconds": 2
  }
}
```

**派生属性 (v3.0)：** 预聚合视图。刷新策略：periodic / on_change / manual。

### 3.2 链接类型定义 (LTD)

链接作为独立 Schema 的一等公民实体。

#### 3.2.1 链接元模型

```json
{
  "link_type_uri": "com.genesis.mil.rel.COMMANDS",
  "display_name": "指挥关系",
  "source_type_constraint": "Officer",
  "target_type_constraint": "Unit.*",
  "directionality": "directed",
  "cardinality": { "type": "one_to_many", "max_fan_out": 12 },
  "properties": {
    "authority_level": { "type": "integer", "storage": "static" },
    "trust_level": { "type": "float", "storage": "time_series", "interpolation": "linear" }
  },
  "lifecycle": {
    "on_create": "hooks/cmd_established.py",
    "on_destroy": "hooks/cmd_dissolved.py",
    "transient": false
  }
}
```

#### 3.2.2 Cardinality 约束

| 类型 | 语义 | 示例 | 违约行为 |
|------|------|------|---------|
| ONE_TO_ONE | 唯一绑定 | Driver DRIVES Tank | 409 Conflict |
| ONE_TO_MANY | A 连多个 B | Commander CONTROLS Squad | max_fan_out 限制 |
| MANY_TO_MANY | 任意对任意 | Soldier PARTICIPATES_IN Battle | 无约束 |
| ZERO_OR_ONE | 可选连接 | Unit OCCUPIES Building | 允许空 |

#### 3.2.3 生命周期钩子

| 钩子 | 时机 | 用途 | 执行模式 |
|------|------|------|---------|
| on_create | 建立时 | 通知/初始化 | 同步 |
| on_update | 属性变更 | 关联重算 | 异步 |
| on_destroy | 断开时 | 孤立状态计算 | 同步 |
| on_expire | TTL 到期 | 瞬时关系消散 | 异步 |

### 3.3 语义映射通道

#### 3.3.1 数据接入

- **Schema Registry:** 外部到内部映射文件，版本化管理
- **智能映射:** 嵌入向量自动建议 (如 `curr_spd` → `current_speed`)
- **实体解析:** Composite Key 去重 + 合并策略 (Update/Discard/Merge)

#### 3.3.2 Schema Evolution (v3.0)

| 变更类型 | 兼容性 | 迁移策略 |
|---------|--------|---------|
| 新增可选属性 | 向后兼容 | 自动迁移 |
| 新增默认值属性 | 向后兼容 | 自动填充 |
| 重命名属性 | 破坏性 | 别名映射 + 后台重写 |
| 删除属性 | 破坏性 | Migration Plan + 人工审批 |
| 修改类型 | 破坏性 | 转换函数 + 人工审批 |

迁移模式：Lazy Migration (首次访问) / Batch Background / Dual-Write (过渡期)。

---

## 4. 规则模型与动作集 (Rule Model & Action Sets)

核心原则：**Write-back 机制**。任何状态改变必须通过可审计、可回滚、可权限控制的 Action 完成。

### 4.1 Action 定义

```json
{
  "action_id": "ACT_TRANSFER_RESOURCE",
  "version": "1.2.0",
  "display_name": "物资转移",
  "category": "logistics",
  "permissions": ["LOGISTICS_WRITE"],
  "rate_limit": { "max_calls": 10, "window_seconds": 60 },
  "timeout_ms": 5000,
  "retry_policy": { "max_retries": 3, "backoff": "exponential" },
  "parameters": [
    { "name": "source_id", "type": "entity_ref", "constraints": {"type": "Storage"} },
    { "name": "target_id", "type": "entity_ref", "constraints": {"type": "Unit"} },
    { "name": "amount", "type": "integer", "constraints": {"min": 1, "max": 1000} }
  ],
  "pre_conditions": [
    { "name": "Check Distance", "tier": "L2", "expression": "geo.distance(source, target) < 50.0" },
    { "name": "Check Inventory", "tier": "L2", "expression": "source.inventory >= amount" }
  ],
  "effects": [
    { "type": "modify_property", "target": "source_id", "property": "inventory", "value_expression": "source.inventory - amount" },
    { "type": "modify_property", "target": "target_id", "property": "inventory", "value_expression": "target.inventory + amount" },
    { "type": "emit_event", "event_type": "ResourceTransferred" },
    { "type": "create_audit_log", "message": "{{user}} transferred {{amount}} to {{target}}" }
  ],
  "post_assertions": [
    { "expression": "source.inventory >= 0", "action_on_fail": "rollback" }
  ],
  "compensation": { "strategy": "reverse_effects", "timeout_ms": 5000 }
}
```

#### 逻辑门分层

| 层级 | 类型 | 执行位置 |
|------|------|---------|
| L0 | 参数格式校验 | 前端 + Gateway |
| L1 | 无状态校验 | ActionDispatcher (内存) |
| L2 | 有状态校验 | → Neo4j |
| L3 | 权限校验 | → AuthService |
| L4 | 后置断言 | Commit 前 |

#### 事务语义与 Saga 补偿

副作用原子事务。v3.0 引入 Saga Pattern 跨服务补偿：Effect1(成功) → Effect2(成功) → Effect3(失败) → Compensate 2 → Compensate 1 → Return Error。

### 4.2 行为与感知

- **L1 意图解析 (Synapser):** Transformer 意图分类 + 槽位填充。置信度 < 0.85 请求确认。
- **L2 实体消歧:** 视锥体/鼠标位置推断 UUID。多维权重 (视觉+语义+空间)。歧义时弹出选择器。
- **L3 事务执行器:** Redis Queue → Logic Gates → Atomic Commit (Neo4j + TSDB + EventStore) → WebSocket Broadcast。乐观锁 + 审计日志 + DLQ。

---

## 5. 前端架构 (Vue 3 Studio IDE)

全息控制台：高响应、上下文感知、10k+ 节点渲染、时间回溯集成。v3.0 引入插件架构和微前端。

### 5.1 布局 (Holy Grail)

```
┌──────────────────────────────────────────────────────────┐
│ [Draft/Sim] │ ◁◁ ▶ ▷▷ ──●──── Tick:10450 │ Git Ops    │
├──────┬───────────────────────────────────────┬───────────┤
│ Onto │         Center Stage (Tabs)           │ Inspector │
│ logy │ ┌Ontology┬Instance┬Logic┬GeoMap┬Data┐│ (Context) │
│ Expl │ │ Graph  │ Graph  │Canvas│View │Dash││           │
│ orer │ │        │        │     │     │    ││           │
├──────┴─┴────────┴────────┴─────┴─────┴────┴┴───────────┤
│ 💬 Copilot │ ⚠️ Validation │ 📡 Telemetry │ Audit Logs │
└──────────────────────────────────────────────────────────┘
```

**顶栏：** Context Switcher (Draft/Sim) + Timeline Scrubber (Play/Pause/Tick Slider/Speed/Keyframes) + GitOps Console (Branch/Commit/Hot Reload)

**左栏：** Schema 树 + Assets 浏览 + Blueprints 模板。Drag-and-Drop 创建实例。Smart Filter 过滤。

**中央：** Ontology Graph (语义缩放) | Instance Graph (WebGL + LOD) | Logic Canvas (Vue Flow + 断点调试) | Geo Map (Mapbox/Cesium) | Data Dashboard (ECharts)

**右栏：** 上下文感知 Inspector — 选中不同元素显示不同内容（OTD 表单 / Live Metrics + Action Trigger / Link 属性 / Git Diff）

**底栏：** Copilot Chat (Apply to Canvas) + Validation Console + System Telemetry + Audit Log Stream

### 5.2 关键组件

**GraphVisualizer.vue:** Cytoscape.js + WebGL。LOD 三级 (< 20% 粒子 / 20-80% 图标+名称 / > 80% 完整属性)。力导向布局。性能预算 10k 节点 60fps。虚拟视口。

**TimelineController.vue:** TickBuffer 环形缓冲 (1000 Ticks Delta)。客户端预测渲染。Ghosting 重影。Keyframe 标记。Shift+拖动精细模式。

**ActionFormBuilder.vue:** Schema → UI 自动映射 (integer→number, entity_ref→SearchableDropdown, coordinate→PointPicker, enum→Select)。300ms 防抖实时验证。

**LineageGraph.vue:** DAG 因果链展示。Action→Effect→StateChange 追溯。

**LogicComposer.vue:** Trigger/Gate/Effect/Aggregator 节点类型。类型兼容连线 + 颜色编码。断点调试 + 单步执行。

### 5.3 微交互

Toast 反馈 (Success/Error/Warning) · 快捷键 (Ctrl+S/Enter/Space/Cmd+K/Z/Y) · 骨架屏 · Smart Snapping · Undo/Redo (50步) · Dirty State 指示 · 引用高亮 · 拖拽预览

---

## 6. 原子后端服务 (Atomic Backend Services)

DDD 微服务。gRPC 内部通信 + Redis Streams/Kafka 异步解耦。v3.0 加入 API Gateway + Service Mesh + 分布式追踪。

### 6.1 服务全景

| 服务 | 别名 | 职责 | 主技术栈 | 存储 |
|------|------|------|---------|------|
| OntologyService | Architect | Schema 生命周期 | GitPython·Pydantic·FastAPI | Git |
| ObjectService | Entity Manager | 实例生命周期 | Neo4j Driver·Redis | Neo4j |
| LinkService | Topology Manager | 链接管理·拓扑计算 | NetworkX·Neo4j | Neo4j |
| TimeTravelService | Historian | 时序读写黑匣子 | TimescaleDB·Pandas | TSDB |
| SearchService | Navigator | 模糊匹配·地理空间 | ES·Uber H3 | ES |
| ActionDispatcher | Executive | **核心写入口** | Redis Lock·Celery | Redis+EventStore |
| CopilotService | Brain | AI LLM 代理 | LangChain·Milvus | Vector DB |
| AuthService (v3.0) | Guardian | 认证/授权/审计 | OAuth2·RBAC/ABAC | PostgreSQL |
| NotificationSvc (v3.0) | Herald | 事件广播·WebSocket | Socket.IO·Redis | Redis |

### 6.2 服务详述

**OntologyService:** 唯一直写 Git。Schema Registry (Cache-Aside) + 循环依赖检测 (DFS) + Git 事务包装 + Schema 版本管理。API: load_effective_schema / validate_mutation / commit_workspace / diff_workspace / generate_migration_plan。

**ObjectService:** 聚合根。多态解析 (递归子类型查找) + 数据水合 (Neo4j 静态 + TSDB 动态 → UnifiedObjectDTO) + 批量水合优化。API: spawn_entity / destroy_entity / query_by_pattern / batch_hydrate。

**LinkService:** 链接实化 (屏蔽中间节点细节) + TTL 管理 + NetworkX 图论算法。API: forge_connection / sever_connection / get_topology / find_shortest_path / compute_centrality。

**TimeTravelService:** Tick 对齐 + 回放插值 + 遥测压缩 (保留策略 7d/90d/365d)。API: record_telemetry (批量 Buffer 100ms flush) / get_world_snapshot / get_property_history / compare_snapshots。

**SearchService:** 软链接计算引擎 + 全文检索 (多字段权重) + CDC 同步 (<500ms lag)。API: fuzzy_search / geo_spatial_query / reindex_ontology / suggest_completions。

**ActionDispatcher:** 乐观锁 + 增强两阶段提交 (Prepare → Commit → Post-Assert → Broadcast，失败则 Rollback + Saga Compensate)。API: dispatch_action / dry_run / revert_transaction。

**CopilotService:** RAG Pipeline + 技能路由 (OAA/LSA/WFA/DAA/DBA) + Guardrails (AST 沙箱)。API: transpile_intent / generate_proposal / explain_lineage。

**AuthService (v3.0):** OAuth 2.0/OIDC + JWT (Access 15min + Refresh 7d) + RBAC (Admin/Designer/Operator/Viewer) + ABAC 字段级权限 + 审计日志。

### 6.3 数据流示例 ("Unit A Attack Unit B")

```
T1  Frontend: POST /dispatch {action: ATTACK, src: A, target: B}
T2  Gateway: JWT 验证 + Rate Limit → Forward
T3  Dispatcher: Redis Lock [A, B]
T4  Dispatcher → ObjectService: get_state([A, B])
T5  ObjectService → Neo4j + TSDB: 水合 A, B
T6  Dispatcher: Pre-conditions:
      L1: A.ammo > 0 ✓
      L2: distance(A,B) < A.range (→ SearchService) ✓
      L3: user has COMBAT_WRITE (→ AuthService) ✓
T7  Dispatcher: Calculate: B.hp -= A.damage, A.ammo -= 1
T8  Atomic Commit:
      → TSDB: record(B, hp, 50, tick)
      → TSDB: record(A, ammo, 39, tick)
      → LinkService: forge(A, B, ENGAGING, transient, ttl=3s)
      → EventStore: append(AttackExecuted)
T9  Post-Assert: B.hp >= 0 ✓
T10 Release Locks → WebSocket broadcast → Frontend animate
```

---

## 7. 开发流程 (Git-Ops Lifecycle)

设计理念：将软件工程的严谨性封装在直观图形界面之下，实现隐形 DevOps。采用影子分支 (Shadow Branch) 策略。

### 7.1 工作流阶段

**7.1.1 草稿 (Draft):** IndexedDB (L1) + Session (L2) 缓存，不写 Git。脏状态黄色角标。WebSocket 多用户锁定。30s 自动保存。

**7.1.2 验证 (Validate):** L1 Schema (Pydantic) → L2 Topology (NetworkX) → L3 Logic Safety (AST 沙箱)。

**7.1.3 提交 (Commit):** Visual Graph Diff (绿=新增/红=删除/对比卡片=修改)。原子写入 Git。CI/CD Webhook。

**7.1.4 热重载 (Hot Reload) — 零停机状态迁移

- **蓝绿切换 (Blue-Green Switch):** 仿真内核在内存中加载新的本体定义 (Green)，校验通过后原子性地切换流量指针。旧定义 (Blue) 保留作为即时回滚备份。
- **状态迁移 (State Migration):** 如果旧实例的属性在新本体中被删除，系统根据配置策略处理：
  - `preserve_as_deprecated`: 保留为废弃字段（标记但不删除）。
  - `discard_with_backup`: 丢弃但备份到归档存储。
  - `transform`: 执行迁移转换函数。
- **UI 反馈:** 界面顶部出现 "Applying Configuration..." 进度条。完成后显示 "World Updated (v2.1.5)" Toast 提示，同时显示迁移摘要（受影响实体数量、跳过数量）。

### 7.2 分支策略 (Branching Strategy) — v3.0 新增

| 分支 | 用途 | 保护规则 | 合并策略 |
|------|------|---------|---------|
| `main` | 生产级本体定义 | 受保护，仅 Merge Request 合入 | Squash Merge |
| `develop` | 集成分支 | 半保护，CI 通过方可合入 | Merge Commit |
| `feature/*` | 单个设计任务 | 无保护，个人分支 | Squash into develop |
| `hotfix/*` | 紧急修复 | 受保护，需 Admin 审批 | Cherry-pick to main |
| `release/*` | 发布准备 | 受保护，冻结新功能 | Merge to main + tag |

- **合并前检查:** 自动化 Schema 兼容性检查 + Validation L1-L3 全通过 + 至少 1 人 Code Review。
- **冲突解决:** 当两个 feature 分支修改同一 OTD 时，系统提供 3-way Visual Merge 工具（Base / Theirs / Mine），可视化合并冲突。

---

## 8. AI Copilot 集成 (Forge Copilot)

**设计理念：** AI 不是一个简单的聊天机器人，而是一个**"代理路由系统 (Agent Router System)"**。它具备对当前编辑器上下文（选中的节点、当前图结构、仿真运行状态）的完全感知能力。

### 8.1 Agent 集群架构

| Agent | 别名 | 职责 | 输入示例 | 输出 |
|-------|------|------|---------|------|
| Ontology Architect | OAA | 生成静态结构 (Object/Link Types) | "创建中世纪守卫，可巡逻和攻击" | Guard OTD + PATROLS LTD |
| Logic Synapser | LSA | 编写 Cypher/Python 逻辑规则 | "血量低于20%时逃跑" | ACT_FLEE Action 定义 |
| World Filler | WFA | 批量生成实例 Seed Data | "随机位置生成50个平民" | Cypher `UNWIND...CREATE` |
| Data Analyst | DAA | 分析仿真数据趋势 (v3.0) | "分析过去1000 tick战损比" | ECharts 配置 + 洞察报告 |
| Debug Assistant | DBA | 诊断运行时异常 (v3.0) | "为什么 Unit_42 无法移动" | 血缘追溯 + 根因分析 |

### 8.2 上下文注入机制 (Context Injection)

每次请求都会动态构建 Prompt：

```
┌─────────────────────────────────────────────────────┐
│                    Assembled Prompt                   │
├─────────────────────────────────────────────────────┤
│  System Prompt:                                      │
│    - MDA 架构原则                                     │
│    - Cypher 语法规范                                  │
│    - 项目特定约束                                     │
├─────────────────────────────────────────────────────┤
│  Project Context (RAG):                              │
│    - Current Selection: 画布选中节点 JSON             │
│    - Relevant Schema: 向量检索 Top-5 相关 OTD         │
│    - Session History: 最近 10 轮对话                   │
│    - Sim State: 当前 Tick、运行状态、最近告警          │
├─────────────────────────────────────────────────────┤
│  User Query: "给坦克添加一个开火动作"                  │
└─────────────────────────────────────────────────────┘
```

### 8.3 交互模式：Proposal Card

AI **绝不直接修改本体**，而是生成**"变更建议卡 (Proposal Card)"**：

1. **用户提问:** "给坦克添加一个开火动作。"
2. **AI 思考:** 分析上下文 → 选择 Logic Synapser Agent → 生成 JSON 格式 Action 定义。
3. **UI 呈现:** 聊天窗口弹出 Proposal Card：
   - 标题: "即将创建 Action: `ACT_FIRE`"
   - 代码预览: 生成的 Cypher/JSON 逻辑
   - 影响分析: "将绑定到 Tank 及其所有子类型 (3 个)"
   - 操作按钮: `[Diff View]` `[Apply]` `[Refine]` `[Reject]`
4. **应用:** 用户点击 `Apply`，变更合并到当前 Draft 状态，画布自动聚焦到新生成的节点。

### 8.4 安全防护 (Guardrails) — v3.0 新增

| 防护层 | 机制 | 描述 |
|--------|------|------|
| Schema 合规 | Pydantic 验证 | AI 生成的 OTD/LTD 必须通过完整 Schema 验证才能出现在 Proposal Card |
| Cypher 沙箱 | AST 静态分析 | 禁止 `DELETE *`, `DETACH DELETE` (无条件), `DROP`, `CALL apoc.*` |
| 生成限制 | Token 限制 + 输出过滤 | 单次生成不超过 500 行；过滤可能的 Prompt Injection |
| 人工审批门 | 权限配置 | 涉及权限变更、全局配置修改的 Proposal 强制要求 Admin 审批 |
| 回滚保障 | Transaction ID | 所有 Apply 的 Proposal 记录 `txn_id`，支持一键回滚到应用前状态 |

---

## 9. 用户旅程与交互设计 (User Journey & UX)

**角色:** Alex, 资深仿真架构师。
**任务:** 为一款科幻仿真创建一个新的单位 "Drone (无人机)"，并定义其"自爆"逻辑。

### 阶段 1: 启动与上下文 (Setup)

- **交互:** Alex 打开 Genesis Studio，选择 "SciFi_Project_v1"。
- **界面状态:**
  - 左侧 Ontology Explorer 树状列出 `Unit`, `Building`, `Terrain`。
  - 中间是空旷的 Graph Canvas，显示已有的类型继承关系图。
  - 底部 Status Bar: `Git: main (Clean) | Tick: 0 | FPS: 60 | Latency: 12ms`。
  - 右上角显示 Alex 的头像和角色 `Designer`。

### 阶段 2: AI 辅助生成本体 (AI-Assisted Creation)

- **交互:** Alex 按下快捷键 `Cmd+K` 唤起 Copilot Command Palette。
- **输入:** "创建一个 Drone 单位，它是空中单位，拥有电池电量属性，且极其脆弱。"
- **系统响应:**
  - Copilot 分析意图 → 路由到 `Ontology Architect Agent (OAA)`。
  - OAA 通过 RAG 检索到项目中已有 `AirUnit` 基类。
  - 弹出 **Proposal Card:**
    - **ObjectType:** `Drone` (`com.genesis.scifi.unit.Drone`)
    - **Parent:** `AirUnit` (AI 推断继承关系)
    - **Implements:** `IMovable`, `IDamageable`, `IDetectable`
    - **Properties:** `battery_level (float, time_series, default=1.0)`, `durability (int, static, default=10)`, `explosion_radius (float, static, default=10.0)`
    - **Bound Actions:** `ACT_MOVE` (继承), `ACT_SELF_DESTRUCT` (待定义)
  - Alex 审阅后点击 **[Apply]**。
- **视觉反馈:** 画布中心自动出现一个新的蓝色节点 `Drone`，通过虚线继承边连接到 `AirUnit`。右侧 Inspector 自动展开 Drone 的属性页。画布执行 fit-to-content 动画。

### 阶段 3: 可视化微调 (Visual Refinement)

- **交互:** Alex 觉得 `durability` 默认值太高，改为 5。
- **操作:** 在右侧 Inspector 中点击 `durability` 字段，将 `10` 改为 `5`。
- **即时反馈:**
  - 字段背景短暂闪烁黄色（表示已修改）。
  - 左侧资源树中 `Drone` 出现黄色圆点 (Dirty State)。
  - 画布上 `Drone` 节点右上角出现微小 "●" 标记。
  - Pending Changes Panel: `Modified: Drone.durability (10 → 5)`。
- **额外操作:** Alex 为 Drone 上传自定义图标 `drone_blue.svg`，在 Inspector 的 Icon 区域拖入文件。

### 阶段 4: 定义复杂逻辑 (Logic Orchestration)

- **交互:** Alex 右键点击 `Drone` 节点 → 选择 `Add Action`。
- **界面:** 视图切换到 **Logic Composer** (节点式逻辑编辑器)。一个空白的逻辑画布出现，左侧显示可用节点类型库。
- **AI 辅助:** Alex 在侧边栏 Copilot 输入: "当电池低于 5% 且周围 10 米内有敌人时，触发自爆，对范围内敌人造成 50 点伤害，自身被销毁。"
- **系统响应:**
  - Copilot 路由到 `Logic Synapser Agent (LSA)`。
  - LSA 生成完整的 Action 定义，包含:
    - **Pre-conditions:** `battery_level < 0.05 AND nearby_enemies(10m).count > 0`
    - **Effects:** `foreach enemy in range: enemy.hp -= 50; destroy self`
  - 生成 Cypher 逻辑:
    ```cypher
    MATCH (s:Drone) WHERE s.battery_level < 0.05
    MATCH (enemy:Unit)
      WHERE point.distance(s.location, enemy.location) < 10
      AND enemy.faction <> s.faction
    SET enemy.hp = enemy.hp - 50
    DETACH DELETE s
    ```
  - Logic Composer 自动填充节点链:
    `[Trigger: On Tick]` → `[Gate: battery < 5%]` → `[Gate: enemies nearby]` → `[Effect: Damage enemies]` → `[Effect: Destroy self]`

- **人工校验:** Alex 发现 AI 忘记在销毁前记录爆炸事件。他手动从节点库拖入一个 `Emit Event` 节点，连接在 `Destroy self` 之前，配置事件类型为 `DroneExploded`。

### 阶段 5: 验证与提交 (Validate & Commit)

- **验证交互:** Alex 点击顶部栏 [Validate] 按钮。
  - Loading 动画 (0.5s)。
  - Validation Report 弹出:
    - `✅ L1 Schema: All 2 new definitions valid`
    - `✅ L2 Topology: No orphan nodes, no cyclic dependencies`
    - `✅ L3 Logic: Cypher statements safe (no prohibited operations)`
    - `⚠️ Warning: ACT_SELF_DESTRUCT has no rate_limit configured (recommended)`
  - [Commit] 按钮变为高亮可点击。

- **提交交互:** 点击 [Commit]。
  - 弹出 Visual Diff 模态框:
    - 左侧: 原图 (无 Drone)
    - 右侧: 新增 `Drone` 节点 (绿色高亮) + `ACT_SELF_DESTRUCT` 逻辑 (绿色高亮)
    - 变更摘要: `+1 ObjectType, +1 Action, +3 Properties`
  - Message 输入: "Feature: Added Drone unit with self-destruct logic"
  - 点击 [Push to Git]。
- **反馈:** 底部状态栏滚动: `Serializing... → Git Add... → Git Commit... → Git Push Success ✓`。所有黄色脏状态标记消失。Status Bar 更新为 `Git: main (Clean)`。

### 阶段 6: 运行时测试 (Runtime Simulation)

- **热载:** Alex 点击右上角 [Hot Reload] (火焰图标)。
  - 进度条: "Applying Configuration..." (0.3s)
  - Toast: "World Updated (v1.3.0) — 1 new type, 1 new action loaded"
- **切换:** 点击 Context Switcher 切换到 **Sim Mode**。背景色渐变为深绿。
- **实例化:** 在 Sim View 中点击 "Spawn Entity" → 选择 `Drone` → 在地图上点击放置位置。
- **测试:** Alex 在 Inspector 中手动将 Drone 的 `battery_level` 调整为 `0.04` (低于 5%)。在附近放置一个敌方单位。
- **观察结果:**
  - 下一个 Tick 执行时，`ACT_SELF_DESTRUCT` 自动触发。
  - 画布上 Drone 图标变为爆炸动画，随后消失。
  - 附近敌方单位 HP 从 100 降到 50。
  - Inspector 显示完整事务链路: `[Tick: 1] → [Gate: battery=0.04 < 0.05 ✓] → [Gate: enemies=1 > 0 ✓] → [Effect: enemy.hp 100→50] → [Effect: drone destroyed]`
  - Audit Log: `{txn: TXN_001, action: ACT_SELF_DESTRUCT, user: system, tick: 1, duration: 2ms}`
- **结论:** 测试通过。Alex 对结果满意，切换回 Draft Mode 继续下一项工作。

---

## 10. 安全架构与合规 (Security & Compliance) [v3.0 新增]

Genesis Studio 作为企业级仿真平台，必须满足严格的安全和数据治理要求。

### 10.1 零信任安全模型 (Zero Trust)

| 层级 | 机制 | 实现 |
|------|------|------|
| 身份认证 | 所有请求必须携带有效 JWT | OAuth 2.0 / OIDC + SSO 集成 |
| 服务间认证 | mTLS (双向 TLS) | Istio 自动注入 Sidecar |
| 最小权限 | 每个账号仅授予必需权限 | RBAC + ABAC 策略引擎 |
| 网络分段 | 服务间通信白名单 | K8s NetworkPolicy |
| 数据加密 | 传输加密 + 静态加密 | TLS 1.3 + AES-256-GCM |
| 密钥管理 | 动态密钥轮转 | HashiCorp Vault |

### 10.2 权限模型

| 角色 | Schema 读 | Schema 写 | Instance 读 | Instance 写 | Action 执行 | Admin |
|------|-----------|-----------|-------------|-------------|------------|-------|
| Admin | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Designer | ✅ | ✅ | ✅ | ✅ (受限) | ✅ | ❌ |
| Operator | ✅ | ❌ | ✅ | ✅ | ✅ | ❌ |
| Viewer | ✅ | ❌ | ✅ | ❌ | ❌ | ❌ |
| API Client | 受限 | ❌ | 受限 | ❌ | 受限 | ❌ |

**ABAC 增强:** 支持字段级权限控制。例如 Designer 可编辑 OTD 属性定义，但不能修改 `access_control` 字段。支持对象和属性标记安全级别 (`PUBLIC` / `INTERNAL` / `CONFIDENTIAL` / `SECRET`)，视图自动过滤不可见内容。

### 10.3 审计与合规

- **不可篡改审计日志:** 所有写操作生成带数字签名的审计记录，存储于独立的 Append-Only 数据库。支持导出为 SIEM 兼容格式。
- **数据保留策略:**
  - 审计日志: 7 年
  - 时序原始数据: 30 天
  - 时序降采样: 1 年
  - 时序归档: 5 年
- **GDPR 支持:** 数据导出 (Right to Portability), 数据删除 (Right to Erasure), 处理记录 (Records of Processing)。
- **SOC 2 合规:** 访问控制、变更管理、系统监控三大领域全覆盖。

---

## 11. 可观测性与运维 (Observability & Operations) [v3.0 新增]

### 11.1 三支柱可观测性 (Three Pillars)

| 支柱 | 技术 | 数据源 | 用途 |
|------|------|--------|------|
| **Metrics** | Prometheus + Grafana | OpenTelemetry SDK | SLA 监控、容量规划、告警 |
| **Logs** | Loki + Grafana | 结构化 JSON 日志 | 问题诊断、审计追溯 |
| **Traces** | Tempo + Grafana | OpenTelemetry Traces | 分布式链路追踪、瓶颈定位 |

### 11.2 关键指标 (Key Metrics)

| 指标类别 | 指标名称 | SLA 目标 | 告警阈值 |
|---------|---------|---------|---------|
| 可用性 | API 成功率 (非 5xx) | ≥ 99.9% | < 99.5% |
| 延迟 | Action Dispatch P99 | ≤ 200ms | > 500ms |
| 延迟 | Graph Query P99 | ≤ 100ms | > 300ms |
| 延迟 | WebSocket Push Latency P99 | ≤ 50ms | > 150ms |
| 吞吐 | Action Throughput | ≥ 1,000 ops/s | < 500 ops/s |
| 吞吐 | Telemetry Write Rate | ≥ 50,000 points/s | < 20,000 points/s |
| 资源 | CPU Utilization (per service) | ≤ 70% | > 85% |
| 资源 | Memory Utilization | ≤ 75% | > 90% |
| 前端 | Canvas FPS | ≥ 30fps (10k nodes) | < 20fps |
| 前端 | Time to Interactive (TTI) | ≤ 3s | > 5s |

### 11.3 告警策略

- **P1 (Critical):** 服务不可用、数据丢失风险 → 即时通知 (PagerDuty + 电话)，15min 响应。
- **P2 (High):** SLA 降级、性能显著下降 → 即时通知 (Slack + Email)，1h 响应。
- **P3 (Medium):** 非关键指标异常、警告趋势 → Slack 通知，4h 响应。
- **P4 (Low):** 信息性告警、容量规划预警 → 日报汇总。

### 11.4 运维 Runbook

| 场景 | 检测方式 | 自动修复 | 手动介入 |
|------|---------|---------|---------|
| Neo4j 连接池耗尽 | 连接数 > 90% 容量 | 自动扩容连接池 | 排查慢查询 |
| TimescaleDB 写入积压 | 队列深度 > 10k | 自动触发批量 flush | 扩容写入节点 |
| Redis 内存不足 | 内存 > 90% | 自动 LRU 淘汰 | 扩容或清理冷数据 |
| ES 索引延迟 | CDC lag > 5s | 自动重启 CDC connector | 检查 ES 集群健康 |
| WebSocket 断连风暴 | 断连率 > 10%/min | 自动重连 + 指数退避 | 检查网络/证书 |

---

## 12. 部署架构与容灾 (Deployment & Disaster Recovery) [v3.0 新增]

### 12.1 Kubernetes 部署拓扑

```
┌─────────────── K8s Cluster (Production) ──────────────────┐
│                                                            │
│  ┌─ Namespace: genesis-gateway ─┐                         │
│  │  Kong Ingress (2 replicas)    │                         │
│  └──────────────┬────────────────┘                         │
│                 │                                          │
│  ┌─ Namespace: genesis-services ────────────────────────┐  │
│  │                                                       │  │
│  │  ActionDispatcher (3 pods, HPA: 3-10)                │  │
│  │  ObjectService    (3 pods, HPA: 3-8)                 │  │
│  │  OntologyService  (2 pods, HPA: 2-4)                 │  │
│  │  LinkService      (2 pods, HPA: 2-6)                 │  │
│  │  TimeTravelService(3 pods, HPA: 3-10)                │  │
│  │  SearchService    (2 pods, HPA: 2-6)                 │  │
│  │  CopilotService   (2 pods, HPA: 2-4)                │  │
│  │  AuthService      (2 pods, HPA: 2-4)                 │  │
│  │  NotificationSvc  (2 pods, HPA: 2-4)                 │  │
│  │                                                       │  │
│  │  Istio Sidecar: mTLS + Traffic Management            │  │
│  └───────────────────────────────────────────────────────┘  │
│                                                            │
│  ┌─ Namespace: genesis-data ─────────────────────────────┐  │
│  │  Neo4j Cluster     (3 nodes, Causal Cluster)          │  │
│  │  TimescaleDB       (Primary + 2 Replicas)             │  │
│  │  Elasticsearch     (3 nodes, Cross-cluster)           │  │
│  │  Redis Sentinel    (3 nodes, HA)                      │  │
│  │  PostgreSQL        (Primary + Standby, Patroni)       │  │
│  │  Kafka             (3 brokers, Strimzi Operator)      │  │
│  └───────────────────────────────────────────────────────┘  │
│                                                            │
│  ┌─ Namespace: genesis-observability ────────────────────┐  │
│  │  Grafana · Prometheus · Loki · Tempo · AlertManager   │  │
│  └───────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────┘
```

### 12.2 伸缩策略

| 服务 | 伸缩维度 | 触发条件 | Min/Max Pods |
|------|---------|---------|-------------|
| ActionDispatcher | CPU + Queue Depth | CPU > 70% 或 Queue > 1000 | 3 / 10 |
| ObjectService | CPU + Request Rate | CPU > 65% 或 RPS > 500 | 3 / 8 |
| TimeTravelService | CPU + Write Rate | CPU > 70% 或 Writes > 10k/s | 3 / 10 |
| SearchService | CPU + Query Latency | CPU > 60% 或 P99 > 200ms | 2 / 6 |
| CopilotService | GPU Memory + Queue | GPU > 80% 或 Queue > 50 | 2 / 4 |

### 12.3 容灾与备份

| 维度 | 指标 | 策略 |
|------|------|------|
| **RPO** (恢复点目标) | < 1 分钟 | Event Store 同步复制 + WAL 归档 |
| **RTO** (恢复时间目标) | < 5 分钟 | Standby 集群自动 Failover |
| **备份频率** | 每 6 小时全量 + 实时增量 | pg_basebackup + WAL shipping |
| **备份存储** | 跨区域对象存储 | S3 Cross-Region Replication |
| **备份验证** | 每周自动恢复测试 | CI Pipeline + 数据完整性校验 |

**灾难恢复流程:**

1. **Detection (< 30s):** 健康检查探针检测到主集群不可用。
2. **Failover (< 2min):** DNS 切换到备用集群。Kafka 消费者重新平衡。
3. **Recovery (< 5min):** 备用集群升级为主集群。验证数据一致性。
4. **Post-mortem:** 24h 内完成根因分析和改进措施。

---

## 13. 性能工程与基准 (Performance Engineering) [v3.0 新增]

### 13.1 性能预算 (Performance Budget)

| 场景 | 规模 | 延迟目标 (P99) | 吞吐目标 |
|------|------|---------------|---------|
| 单个 Action 执行 | — | ≤ 200ms | 1,000 ops/s |
| 图查询 (2-hop) | 10k 节点 | ≤ 100ms | 500 qps |
| 图查询 (4-hop) | 10k 节点 | ≤ 500ms | 100 qps |
| 时序写入 (单点) | — | ≤ 5ms | 50,000 points/s |
| 时序读取 (1h窗口) | 100k points | ≤ 200ms | 200 qps |
| 全文搜索 | 100k 文档 | ≤ 50ms | 300 qps |
| 地理空间查询 | 10k 实体 | ≤ 30ms | 500 qps |
| Canvas 渲染 (10k 节点) | 10k nodes + 50k edges | ≤ 16ms/frame | 60 fps |
| Hot Reload | 100 OTD changes | ≤ 2s | — |
| Copilot Response | — | ≤ 5s (首 token) | — |

### 13.2 性能优化策略

| 优化维度 | 策略 | 预期收益 |
|---------|------|---------|
| 图查询 | Cypher 查询计划缓存 + Parameterized Query | 查询延迟 -40% |
| 数据水合 | 批量查询 + Pipeline (避免 N+1) | 水合延迟 -60% |
| 时序写入 | 客户端批量 Buffer (100ms flush) | 写入吞吐 +300% |
| 搜索索引 | 预计算 + Warm Cache | 搜索延迟 -50% |
| 前端渲染 | WebGL + Virtual Viewport + LOD | 10k 节点 60fps |
| 缓存 | 多级缓存 (L1 进程 → L2 Redis → L3 数据库) | 缓存命中率 > 90% |
| 序列化 | Protobuf (gRPC) 替代 JSON (内部通信) | 序列化成本 -70% |

### 13.3 负载测试计划

- **工具:** k6 (API 负载) + Playwright (E2E 前端) + Custom Tick Simulator (仿真负载)
- **场景:**
  - **Baseline:** 10 并发用户，1,000 实体，正常操作混合
  - **Peak:** 50 并发用户，10,000 实体，密集 Action 执行
  - **Stress:** 持续增加负载直到服务降级，确定极限容量
  - **Soak:** 中等负载持续运行 24h，检测内存泄漏和性能退化
- **频率:** 每次主要版本发布前 + 每月定期回归

---

## 14. 测试策略 (Testing Strategy) [v3.0 新增]

### 14.1 测试金字塔

```
              ┌──────────┐
              │  E2E     │  5%   Playwright + Cypress
              │  Tests   │       用户旅程端到端验证
              ├──────────┤
              │Integration│ 20%  Testcontainers
              │  Tests   │       服务集成 + 数据流验证
              ├──────────┤
              │  Unit    │ 75%  Pytest + Vitest
              │  Tests   │       函数/组件级别验证
              └──────────┘
```

### 14.2 测试类型矩阵

| 测试类型 | 工具 | 覆盖范围 | 频率 |
|---------|------|---------|------|
| 单元测试 | Pytest (后端) + Vitest (前端) | 函数、类、组件 | 每次 Commit |
| 集成测试 | Testcontainers (Neo4j, Redis, TimescaleDB) | 服务间交互、数据流 | 每次 PR |
| 契约测试 | Pact | 服务间 API 契约 | 每次 PR |
| E2E 测试 | Playwright | 关键用户旅程 | 每日 + PR |
| 性能测试 | k6 + Custom Simulator | 延迟、吞吐、资源 | 每周 + 发布前 |
| 安全测试 | OWASP ZAP + Trivy | 漏洞扫描、依赖审计 | 每日 |
| 混沌工程 | Chaos Mesh (K8s) | 故障注入、容错验证 | 每月 |
| Schema 兼容性 | Custom Validator | OTD/LTD 向后兼容 | 每次 Schema 变更 |

### 14.3 质量门禁 (Quality Gates)

| 门禁 | 指标 | 阈值 | 阶段 |
|------|------|------|------|
| 单元测试覆盖率 | Line Coverage | ≥ 80% | PR Merge |
| 集成测试通过率 | Pass Rate | 100% | PR Merge |
| 安全漏洞 | Critical/High CVE | 0 | Release |
| 性能回归 | P99 Latency Delta | ≤ +10% | Release |
| API 契约 | Breaking Changes | 0 (without version bump) | PR Merge |

---

## 15. 演进路线图 (Evolution Roadmap)

### 15.1 短期 (v3.1 — Q2 2026)

| 特性 | 描述 | 优先级 |
|------|------|--------|
| 多人实时协作 | Google Docs 式的实时协同编辑 (CRDT/OT) | P0 |
| 插件市场 | 第三方 OTD/Action 包发布与安装 | P1 |
| 移动端 Viewer | 只读移动端查看器 (PWA) | P1 |
| 国际化 (i18n) | 中/英/日三语支持 | P2 |

### 15.2 中期 (v3.5 — Q4 2026)

| 特性 | 描述 | 优先级 |
|------|------|--------|
| 3D 仿真视图 | Three.js / Cesium 集成的 3D 实体渲染 | P0 |
| 联邦本体 | 跨项目/跨组织的本体引用与共享 | P1 |
| 自动化测试生成 | AI 自动生成 Action 的测试用例 | P1 |
| 数据沙箱 | 从生产克隆数据到隔离环境进行实验 | P2 |

### 15.3 长期 (v4.0 — 2027)

| 特性 | 描述 | 优先级 |
|------|------|--------|
| 分布式仿真 | 跨多个 K8s 集群的大规模分布式仿真 | P0 |
| 数字孪生市场 | 可交易的数字孪生模型市场 | P1 |
| AR/VR 编辑器 | XR 设备上的空间化本体编辑 | P2 |
| 自主智能体 | 基于强化学习的自主决策 Agent | P2 |

---

## 附录 A: 术语表 (Glossary)

| 术语 | 全称 | 定义 |
|------|------|------|
| OTD | Object Type Definition | 对象类型定义，描述实体的结构和行为 |
| LTD | Link Type Definition | 链接类型定义，描述实体间关系的结构 |
| DOL | Dynamic Ontology Layer | 动态本体层，系统核心数据模型层 |
| MDA | Model-Driven Architecture | 模型驱动架构 |
| CQRS | Command Query Responsibility Segregation | 命令查询职责分离 |
| PIM | Platform-Independent Model | 平台无关模型 |
| PSM | Platform-Specific Model | 平台特定模型 |
| CIM | Computation-Independent Model | 计算无关模型 |
| CDC | Change Data Capture | 变更数据捕获 |
| LOD | Level of Detail | 细节层次 |
| HPA | Horizontal Pod Autoscaler | 水平 Pod 自动伸缩 |
| RPO | Recovery Point Objective | 恢复点目标 |
| RTO | Recovery Time Objective | 恢复时间目标 |
| Tick | Simulation Tick | 仿真步进时间单位 |
| DLQ | Dead Letter Queue | 死信队列 |

## 附录 B: 接口 (Interface) 契约示例

```json
{
  "interface_uri": "com.genesis.core.IMovable",
  "required_properties": [
    { "name": "location", "type": "coordinate" },
    { "name": "current_speed", "type": "float", "storage": "time_series" },
    { "name": "max_speed", "type": "float", "storage": "static" }
  ],
  "required_actions": ["ACT_MOVE", "ACT_STOP"],
  "description": "可移动实体的标准接口契约"
}
```

```json
{
  "interface_uri": "com.genesis.core.IDamageable",
  "required_properties": [
    { "name": "hp", "type": "integer", "storage": "time_series" },
    { "name": "max_hp", "type": "integer", "storage": "static" },
    { "name": "armor_level", "type": "float", "storage": "static" }
  ],
  "required_actions": ["ACT_TAKE_DAMAGE", "ACT_REPAIR"],
  "description": "可受损实体的标准接口契约"
}
```

---

*文档结束 — Genesis Studio PRP v3.0*
*本文档为 Genesis Studio 产品的权威架构参考。所有实现必须以本文档为准。*
*如有疑问请联系架构组。*