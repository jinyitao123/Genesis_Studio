<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from "vue";
import { apiGet, apiPost } from "./api/client";
import ActionFormBuilder from "./components/ActionFormBuilder.vue";
import GraphVisualizer from "./components/GraphVisualizer.vue";
import InspectorPanel from "./components/InspectorPanel.vue";
import LineageGraph from "./components/LineageGraph.vue";
import LogicComposer from "./components/LogicComposer.vue";
import ProposalCard from "./components/ProposalCard.vue";
import StudioTabBar from "./components/StudioTabBar.vue";
import TimelineController from "./components/TimelineController.vue";

type TabId = "graph" | "timeline" | "logic" | "lineage" | "inspector" | "proposals" | "ops";

type HealthPayload = {
  status: string;
  service: string;
};

type EventPayload = {
  event_id: string;
  action_id: string;
  created_at: string;
  source_id?: string | null;
  target_id?: string | null;
  payload?: Record<string, unknown>;
};

type ObjectTypePayload = {
  type_uri: string;
  display_name: string;
};

type ProposalStatus = "draft" | "applied" | "rejected" | "rolled_back";

type ProposalPayload = {
  proposal_id: string;
  title: string;
  intent: string;
  status: ProposalStatus;
  created_at: string;
  updated_at: string;
};

type TransactionPayload = {
  txn_id: string;
  action_id: string;
  status: string;
  event_id: string | null;
};

type ActionField = {
  name: string;
  label: string;
  input: "text" | "number" | "select";
  required?: boolean;
  options?: string[];
  defaultValue?: string;
};

type DispatchDryRunResponse = {
  allowed: boolean;
  txn_preview_id: string;
  estimated_effects: string[];
  gates: { tier: string; passed: boolean; detail: string }[];
};

type LineageAggregate = {
  lineage: {
    transaction: Record<string, unknown>;
    primary_event: Record<string, unknown> | null;
    compensation_event: Record<string, unknown> | null;
  };
  bus_events: Record<string, unknown>[];
};

type CopilotRouteResponse = {
  agent: string;
  confidence: number;
  guardrail: {
    allowed: boolean;
    reasons: string[];
    sanitized_prompt: string;
  };
  plan: string[];
};

type ComplianceRecord = {
  action: string;
  subject_id: string;
  actor: string;
  recorded_at: string;
};

type ServiceAdapterResponse = {
  operation: string;
  status: string;
  service: string;
  result: unknown;
};

type NotificationPayload = {
  event_type?: string;
  created_at?: string;
  service?: string;
  correlation_id?: string;
};

const tabs: { id: TabId; label: string }[] = [
  { id: "graph", label: "图谱" },
  { id: "timeline", label: "时间线" },
  { id: "logic", label: "逻辑" },
  { id: "lineage", label: "追溯" },
  { id: "inspector", label: "检查器" },
  { id: "proposals", label: "提案" },
  { id: "ops", label: "运维" },
];

const actionSchema = ref<ActionField[]>([
  {
    name: "action_id",
    label: "动作 ID",
    input: "select",
    required: true,
    options: ["ACT_SELF_DESTRUCT", "ACT_MOVE", "ACT_REPAIR"],
    defaultValue: "ACT_SELF_DESTRUCT",
  },
  { name: "source_id", label: "源实体", input: "text", required: true, defaultValue: "entity-1" },
  { name: "target_id", label: "目标实体", input: "text", required: true, defaultValue: "entity-2" },
  { name: "damage", label: "伤害值", input: "number", required: true, defaultValue: "50" },
]);

const activeTab = ref<TabId>("graph");
const queryHealth = ref<HealthPayload | null>(null);
const commandHealth = ref<HealthPayload | null>(null);
const projection = ref<Record<string, unknown> | null>(null);
const projectionLag = ref<Record<string, unknown> | null>(null);
const objectTypes = ref<ObjectTypePayload[]>([]);
const events = ref<EventPayload[]>([]);
const transactions = ref<TransactionPayload[]>([]);
const proposals = ref<ProposalPayload[]>([]);
const lineageAggregate = ref<LineageAggregate | null>(null);
const selectedLineageTxn = ref<string>("");
const selectedTick = ref<number>(0);
const dryRun = ref<DispatchDryRunResponse | null>(null);
const copilotIntent = ref<string>("优化本体模式迁移");
const copilotPrompt = ref<string>("给出一个安全的模式迁移执行计划");
const copilotResult = ref<CopilotRouteResponse | null>(null);
const complianceSubject = ref<string>("user-123");
const complianceRecords = ref<ComplianceRecord[]>([]);
const serviceResult = ref<ServiceAdapterResponse | null>(null);
const notifications = ref<NotificationPayload[]>([]);
const token = ref<string>("");
const busy = ref<boolean>(false);
const error = ref<string>("");
let notificationPolling: number | undefined;

const latestEvents = computed(() => events.value.slice(0, 1000));
const timelineCursorEvent = computed(() => {
  if (latestEvents.value.length === 0) {
    return null;
  }
  const clamped = Math.min(selectedTick.value, latestEvents.value.length - 1);
  return latestEvents.value[clamped];
});

const inspectorPayload = computed<Record<string, unknown>>(() => ({
  projection_lag: projectionLag.value?.lag ?? null,
  stream_event_count: projectionLag.value?.stream_event_count ?? null,
  projected_event_count: projectionLag.value?.projected_event_count ?? null,
  cursor_event: timelineCursorEvent.value,
  dry_run: dryRun.value,
  selected_lineage_txn: selectedLineageTxn.value || null,
  compliance_records: complianceRecords.value.length,
  notifications: notifications.value.length,
}));

const loadToken = async () => {
  const payload = await apiPost<{ access_token: string }>("/api/auth/token", {
    username: "designer",
    password: "designer",
  });
  token.value = payload.access_token;
};

const ensureToken = async () => {
  if (!token.value) {
    await loadToken();
  }
};

const loadProposals = async () => {
  await ensureToken();
  proposals.value = await apiGet<ProposalPayload[]>("/api/command/proposals", token.value);
};

const loadLineage = async (txnId: string) => {
  selectedLineageTxn.value = txnId;
  lineageAggregate.value = await apiGet<LineageAggregate>(`/api/query/transactions/lineage/${txnId}/aggregate`);
};

const loadNotifications = async () => {
  await ensureToken();
  notifications.value = await apiGet<NotificationPayload[]>("/api/query/notifications/secure?limit=30", token.value);
};

const loadComplianceRecords = async () => {
  await ensureToken();
  complianceRecords.value = await apiGet<ComplianceRecord[]>("/api/compliance/records", token.value);
};

const performProposalAction = async (proposalId: string, action: "apply" | "reject" | "rollback") => {
  try {
    busy.value = true;
    await ensureToken();
    await apiPost<{ proposal_id: string; status: string }>(
      `/api/command/proposals/${proposalId}/${action}`,
      {},
      token.value,
    );
    await loadProposals();
    await loadNotifications();
  } catch (exc) {
    error.value = exc instanceof Error ? exc.message : "提案操作失败";
  } finally {
    busy.value = false;
  }
};

const submitDraftAction = async (values: Record<string, string>) => {
  try {
    await ensureToken();
    dryRun.value = await apiPost<DispatchDryRunResponse>(
      "/api/command/dispatch/dry-run",
      {
        action_id: values.action_id,
        source_id: values.source_id,
        target_id: values.target_id,
        payload: {
          damage: Number(values.damage),
        },
      },
      token.value,
    );
  } catch (exc) {
    error.value = exc instanceof Error ? exc.message : "动作预演失败";
  }
};

const runCopilot = async () => {
  try {
    await ensureToken();
    copilotResult.value = await apiPost<CopilotRouteResponse>(
      "/api/copilot/route",
      {
        intent: copilotIntent.value,
        prompt: copilotPrompt.value,
        context: { domain: "mvp-ops" },
      },
      token.value,
    );
  } catch (exc) {
    error.value = exc instanceof Error ? exc.message : "Copilot 调用失败";
  }
};

const runCompliance = async (action: "export" | "delete") => {
  try {
    await ensureToken();
    await apiPost(`/api/compliance/${action}`, { subject_id: complianceSubject.value }, token.value);
    await loadComplianceRecords();
  } catch (exc) {
    error.value = exc instanceof Error ? exc.message : `合规${action}操作失败`;
  }
};

const runServiceEndpoint = async (path: string, body: Record<string, unknown>) => {
  try {
    await ensureToken();
    serviceResult.value = await apiPost<ServiceAdapterResponse>(path, body, token.value);
    await loadNotifications();
  } catch (exc) {
    error.value = exc instanceof Error ? exc.message : `服务接口调用失败: ${path}`;
  }
};

const startNotificationPolling = () => {
  if (notificationPolling !== undefined) {
    clearInterval(notificationPolling);
  }
  notificationPolling = window.setInterval(async () => {
    try {
      await loadNotifications();
    } catch {
      return;
    }
  }, 3000);
};

onMounted(async () => {
  try {
    const [qh, ch, proj, lag, objects, evts, txns] = await Promise.all([
      apiGet<HealthPayload>("/api/health"),
      apiGet<HealthPayload>("/health"),
      apiGet<Record<string, unknown>>("/api/query/projections/latest"),
      apiGet<Record<string, unknown>>("/api/query/projections/lag"),
      apiGet<ObjectTypePayload[]>("/api/query/object-types"),
      apiGet<EventPayload[]>("/api/query/events"),
      apiGet<TransactionPayload[]>("/api/query/transactions"),
    ]);

    queryHealth.value = qh;
    commandHealth.value = ch;
    projection.value = proj;
    projectionLag.value = lag;
    objectTypes.value = objects;
    events.value = evts;
    transactions.value = txns;

    if (latestEvents.value.length > 0) {
      selectedTick.value = latestEvents.value.length - 1;
    }

    if (txns.length > 0) {
      await loadLineage(txns[0].txn_id);
    }

    await loadProposals();
    await loadComplianceRecords();
    await loadNotifications();
    startNotificationPolling();
  } catch (exc) {
    error.value = exc instanceof Error ? exc.message : "未知错误";
  }
});

onBeforeUnmount(() => {
  if (notificationPolling !== undefined) {
    clearInterval(notificationPolling);
  }
});
</script>

<template>
  <div class="studio-root">
    <header class="topbar">
      <div>
        <h1>Genesis Studio</h1>
        <p>P4 交互工作台</p>
      </div>
      <div class="health-badges">
        <span v-if="queryHealth">Q: {{ queryHealth.status }}</span>
        <span v-if="commandHealth">C: {{ commandHealth.status }}</span>
      </div>
    </header>

    <section class="workspace">
      <aside class="left-panel panel">
        <h2>本体浏览器</h2>
        <ul>
          <li v-for="item in objectTypes" :key="item.type_uri">
            {{ item.display_name }}
          </li>
        </ul>
      </aside>

      <main class="center-panel panel">
        <StudioTabBar v-model="activeTab" :tabs="tabs" />

        <section v-if="activeTab === 'graph'" class="tab-content">
          <GraphVisualizer
            :projection-id="String(projection?.projection_id ?? '无')"
            :object-types="objectTypes"
            :events="latestEvents"
          />
        </section>

        <section v-else-if="activeTab === 'timeline'" class="tab-content">
          <TimelineController v-model="selectedTick" :events="latestEvents" />
        </section>

        <section v-else-if="activeTab === 'logic'" class="tab-content logic-stack">
          <LogicComposer />
          <ActionFormBuilder :fields="actionSchema" @submit="submitDraftAction" />
          <div v-if="dryRun" class="dry-run-box">
            <p><strong>预演:</strong> {{ dryRun.allowed ? "允许" : "阻止" }} / {{ dryRun.txn_preview_id }}</p>
            <ul>
              <li v-for="gate in dryRun.gates" :key="gate.tier">
                {{ gate.tier }} · {{ gate.passed ? "通过" : "失败" }} · {{ gate.detail }}
              </li>
            </ul>
          </div>
        </section>

        <section v-else-if="activeTab === 'lineage'" class="tab-content lineage-stack">
          <div class="txn-strip" v-if="transactions.length > 0">
            <button
              v-for="txn in transactions"
              :key="txn.txn_id"
              type="button"
              class="txn-btn"
              :class="{ active: selectedLineageTxn === txn.txn_id }"
              @click="loadLineage(txn.txn_id)"
            >
              {{ txn.action_id }} · {{ txn.status }}
            </button>
          </div>
          <LineageGraph :aggregate="lineageAggregate" />
        </section>

        <section v-else-if="activeTab === 'inspector'" class="tab-content">
          <InspectorPanel :payload="inspectorPayload" />
        </section>

        <section v-else-if="activeTab === 'proposals'" class="tab-content proposals-grid">
          <ProposalCard
            v-for="proposal in proposals"
            :key="proposal.proposal_id"
            :proposal="proposal"
            :busy="busy"
            @apply="(id) => performProposalAction(id, 'apply')"
            @reject="(id) => performProposalAction(id, 'reject')"
            @rollback="(id) => performProposalAction(id, 'rollback')"
          />
        </section>

        <section v-else class="tab-content ops-stack">
          <article class="ops-card">
            <h3>Copilot 路由</h3>
            <input v-model="copilotIntent" type="text" placeholder="意图" />
            <textarea v-model="copilotPrompt" rows="3" placeholder="提示词" />
            <button type="button" @click="runCopilot">运行 Copilot</button>
            <pre v-if="copilotResult">{{ JSON.stringify(copilotResult, null, 2) }}</pre>
          </article>

          <article class="ops-card">
            <h3>合规</h3>
            <input v-model="complianceSubject" type="text" placeholder="主体 ID" />
            <div class="btn-row">
              <button type="button" @click="runCompliance('export')">导出</button>
              <button type="button" @click="runCompliance('delete')">删除</button>
              <button type="button" @click="loadComplianceRecords">刷新记录</button>
            </div>
            <pre>{{ JSON.stringify(complianceRecords.slice(0, 5), null, 2) }}</pre>
          </article>

          <article class="ops-card">
            <h3>服务适配</h3>
            <div class="btn-grid">
              <button
                type="button"
                @click="runServiceEndpoint('/api/command/services/ontology/validate', { schema_version: '3.0.0' })"
              >
                本体验证
              </button>
              <button
                type="button"
                @click="runServiceEndpoint('/api/command/services/object/upsert', { object_id: 'entity-1', object_type: 'Drone' })"
              >
                对象写入
              </button>
              <button
                type="button"
                @click="runServiceEndpoint('/api/command/services/link/connect', { source_id: 'entity-1', target_id: 'entity-2', link_type: 'ATTACKS' })"
              >
                链接建立
              </button>
              <button
                type="button"
                @click="runServiceEndpoint('/api/command/services/time-travel/snapshot', { entity_id: 'entity-1', at_ts: new Date().toISOString() })"
              >
                时间快照
              </button>
              <button
                type="button"
                @click="runServiceEndpoint('/api/command/services/search', { query: 'drone' })"
              >
                检索
              </button>
              <button
                type="button"
                @click="runServiceEndpoint('/api/command/services/auth/issue-token', { subject: 'svc-user', role: 'Operator' })"
              >
                签发令牌(管理员)
              </button>
              <button
                type="button"
                @click="runServiceEndpoint('/api/command/services/notification/publish', { channel: 'ops.alerts', message: 'MVP live notification' })"
              >
                发布通知
              </button>
            </div>
            <pre v-if="serviceResult">{{ JSON.stringify(serviceResult, null, 2) }}</pre>
          </article>
        </section>
      </main>

      <aside class="right-panel panel">
        <h2>实时事件流</h2>
        <p>当前 Tick: {{ selectedTick + 1 }}</p>
        <p>投影延迟: {{ projectionLag?.lag ?? "无" }}</p>
        <p>流事件数: {{ projectionLag?.stream_event_count ?? "无" }}</p>
        <p>事务数: {{ transactions.length }}</p>
        <ul class="notification-list">
          <li v-for="item in notifications.slice(0, 8)" :key="`${item.event_type}:${item.created_at}`">
            <strong>{{ item.event_type ?? "事件" }}</strong>
            <small>{{ item.created_at ?? "" }}</small>
          </li>
        </ul>
      </aside>
    </section>

    <footer class="footer">
      <span v-if="error">{{ error }}</span>
      <span v-else>就绪</span>
    </footer>
  </div>
</template>

<style scoped>
.studio-root {
  min-height: 100vh;
  display: grid;
  grid-template-rows: 88px 1fr 48px;
  background: linear-gradient(140deg, #f3faf8 0%, #eff6fb 45%, #f8f4ee 100%);
  color: #153244;
  font-family: "Space Grotesk", "Manrope", "Segoe UI";
}

.topbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 18px;
  background: linear-gradient(120deg, #0f4d66, #1f7a63);
  color: #fff;
}

.topbar h1 {
  margin: 0;
  font-size: 22px;
}

.topbar p {
  margin: 2px 0 0;
  opacity: 0.9;
}

.health-badges {
  display: flex;
  gap: 8px;
}

.health-badges span {
  border: 1px solid rgba(255, 255, 255, 0.5);
  border-radius: 999px;
  padding: 4px 10px;
  font-weight: 700;
}

.workspace {
  display: grid;
  grid-template-columns: 260px 1fr 280px;
  gap: 12px;
  padding: 14px;
}

.panel {
  background: rgba(255, 255, 255, 0.92);
  border: 1px solid #cde0e8;
  border-radius: 12px;
  padding: 12px;
  overflow: auto;
}

.tab-content {
  margin-top: 14px;
}

.logic-stack,
.lineage-stack,
.proposals-grid,
.ops-stack {
  display: grid;
  gap: 10px;
}

.ops-card {
  border: 1px solid #cde0e8;
  border-radius: 10px;
  padding: 10px;
  background: #f8fbfd;
  display: grid;
  gap: 8px;
}

.ops-card h3 {
  margin: 0;
}

.ops-card input,
.ops-card textarea {
  width: 100%;
  border: 1px solid #c5d9e4;
  border-radius: 8px;
  padding: 6px 8px;
  font: inherit;
}

.btn-row,
.btn-grid {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

button {
  border: 1px solid #7fa6bf;
  background: #f4fafc;
  color: #15425a;
  padding: 6px 10px;
  border-radius: 8px;
  cursor: pointer;
}

.ops-card pre {
  margin: 0;
  max-height: 220px;
  overflow: auto;
  background: #fff;
  border: 1px solid #d6e6ee;
  border-radius: 8px;
  padding: 8px;
}

.txn-strip {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.txn-btn {
  border: 1px solid #7fa6bf;
  background: #f4fafc;
  color: #15425a;
  padding: 6px 10px;
  border-radius: 8px;
  cursor: pointer;
}

.txn-btn.active {
  background: linear-gradient(120deg, #0d6c8d, #2a8e72);
  color: #fff;
  border-color: #0d6c8d;
}

.dry-run-box {
  border: 1px solid #cde0e8;
  border-radius: 10px;
  padding: 10px;
  background: #f8fbfd;
}

.dry-run-box p {
  margin: 0 0 6px;
}

.dry-run-box ul {
  margin: 0;
  padding-left: 18px;
}

.notification-list {
  list-style: none;
  margin: 8px 0 0;
  padding: 0;
  display: grid;
  gap: 8px;
}

.notification-list li {
  border: 1px solid #d4e4ec;
  border-radius: 8px;
  padding: 8px;
  background: #f8fbfd;
  display: grid;
  gap: 2px;
}

.notification-list small {
  color: #537081;
}

.footer {
  display: flex;
  align-items: center;
  padding: 0 14px;
  background: #1f2937;
  color: #f9fafb;
}

@media (max-width: 1100px) {
  .workspace {
    grid-template-columns: 1fr;
  }
}
</style>
