<script setup lang="ts">
import { computed, ref, onBeforeUnmount, onMounted } from "vue";
import { useRouter, useRoute } from "vue-router";
import { useAuthStore, useHealthStore, useOntologyStore, useEventStore } from "@/stores";
import { useGraphStore, useStudioStore, useProposalStore, useCopilotStore } from "@/stores";
import { useNotificationStore, useLineageStore, useComplianceStore } from "@/stores";
import { useRealtimeNotifications } from "./composables/useWebSocket";
import type { TabId } from "@/types";
import StudioTabBar from "./components/StudioTabBar.vue";
import ContextSwitcher from "./components/ContextSwitcher.vue";
import DirtyStateIndicator from "./components/DirtyStateIndicator.vue";
import CommandPalette from "./components/CommandPalette.vue";

// Router
const router = useRouter();
const route = useRoute();

// Stores
const authStore = useAuthStore();
const healthStore = useHealthStore();
const ontologyStore = useOntologyStore();
const eventStore = useEventStore();
const graphStore = useGraphStore();
const studioStore = useStudioStore();
const proposalStore = useProposalStore();
const copilotStore = useCopilotStore();
const notificationStore = useNotificationStore();
const lineageStore = useLineageStore();
const complianceStore = useComplianceStore();

const tabs: { id: TabId; label: string; route: string }[] = [
  { id: "graph", label: "图谱", route: "/graph" },
  { id: "timeline", label: "时间线", route: "/timeline" },
  { id: "logic", label: "逻辑", route: "/logic" },
  { id: "lineage", label: "追溯", route: "/lineage" },
  { id: "inspector", label: "检查器", route: "/inspector" },
  { id: "proposals", label: "提案", route: "/proposals" },
  { id: "copilot", label: "AI助手", route: "/copilot" },
  { id: "ops", label: "运维", route: "/ops" },
  { id: "geomap", label: "地图", route: "/geomap" },
  { id: "dashboard", label: "仪表盘", route: "/dashboard" },
];

// WebSocket for real-time notifications
const {
  state: wsState,
  messages: wsMessages,
  unreadCount,
  connect: connectWebSocket,
  disconnect: disconnectWebSocket,
} = useRealtimeNotifications(computed(() => authStore.token));

// Computed - sync with router
const activeTabId = computed({
  get: () => {
    const matched = tabs.find(t => t.route === route.path);
    return (matched?.id || 'graph') as TabId;
  },
  set: (tabId: TabId) => {
    const tab = tabs.find(t => t.id === tabId);
    if (tab) {
      router.push(tab.route);
    }
  },
});

const selectedTick = computed({
  get: () => studioStore.selectedTick,
  set: (val: number) => studioStore.setSelectedTick(val),
});

const objectTypes = computed(() => ontologyStore.objectTypes);
const latestEvents = computed(() => (Array.isArray(eventStore.events) ? eventStore.events : []).slice(0, 1000));
const transactions = computed(() => (Array.isArray(eventStore.transactions) ? eventStore.transactions : []));
const polledNotifications = computed(() =>
  Array.isArray(notificationStore.notifications) ? notificationStore.notifications : [],
);
const realtimeMessages = computed(() => (Array.isArray(wsMessages.value) ? wsMessages.value : []));
const busy = computed(() => proposalStore.loading || copilotStore.loading || studioStore.busy);
const error = computed(() => {
  const errors = [
    healthStore.error,
    ontologyStore.error,
    eventStore.error,
    graphStore.error,
    proposalStore.error,
    copilotStore.error,
    notificationStore.error,
    lineageStore.error,
    complianceStore.error,
  ].filter(Boolean);
  return errors[0] || null;
});

// Command Palette state
const showCommandPalette = ref(false);

function handleKeyboardShortcuts(e: KeyboardEvent) {
  if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
    e.preventDefault();
    showCommandPalette.value = true;
  }
}

// Lifecycle
onMounted(async () => {
  document.addEventListener('keydown', handleKeyboardShortcuts);
  
  await authStore.init();
  
  await Promise.all([
    healthStore.loadAll(),
    ontologyStore.loadObjectTypes(),
    eventStore.loadAll(),
    graphStore.loadGraphSnapshot(),
    proposalStore.loadProposals(),
    complianceStore.loadRecords(),
    notificationStore.loadNotifications(),
    lineageStore.loadLineage(transactions.value[0]?.txn_id || ""),
  ]);
  
  if (latestEvents.value.length > 0) {
    studioStore.setSelectedTick(latestEvents.value.length - 1);
  }
  
  notificationStore.startPolling(3000);
  connectWebSocket();
});

onBeforeUnmount(() => {
  document.removeEventListener('keydown', handleKeyboardShortcuts);
  notificationStore.stopPolling();
  disconnectWebSocket();
});
</script>

<template>
  <div class="studio-root">
    <header class="topbar">
      <div class="topbar-left">
        <h1>Genesis Studio</h1>
        <ContextSwitcher />
      </div>
      <div class="topbar-center">
        <p>P4 交互工作台</p>
      </div>
      <div class="health-badges">
        <span v-if="healthStore.queryHealth">Q: {{ healthStore.queryHealth.status }}</span>
        <span v-if="healthStore.commandHealth">C: {{ healthStore.commandHealth.status }}</span>
      </div>
      <DirtyStateIndicator />
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
        <StudioTabBar v-model="activeTabId" :tabs="tabs" />
        
        <div class="tab-content">
          <router-view v-slot="{ Component }">
            <keep-alive include="GraphView,TimelineView,LogicView">
              <component :is="Component" />
            </keep-alive>
          </router-view>
        </div>
      </main>

      <aside class="right-panel panel">
        <h2>实时事件流</h2>
        <div class="ws-status" :class="{ connected: wsState.connected }">
          <span class="ws-indicator"></span>
          {{ wsState.connected ? '实时连接' : '轮询模式' }}
          <span v-if="unreadCount > 0" class="unread-badge">{{ unreadCount }}</span>
        </div>
        <p>当前 Tick: {{ selectedTick + 1 }}</p>
        <p>事务数: {{ transactions.length }}</p>
        <p>事件数: {{ latestEvents.length }}</p>
        <ul class="notification-list">
          <li v-for="item in realtimeMessages.slice(0, 8)" :key="item.id" class="ws-notification">
            <strong>{{ item.event_type ?? "事件" }}</strong>
            <small>{{ item.created_at ?? "" }}</small>
          </li>
          <li v-for="item in polledNotifications.slice(0, 8)" :key="`poll-${item.event_type}:${item.created_at}`">
            <strong>{{ item.event_type ?? "事件" }}</strong>
            <small>{{ item.created_at ?? "" }}</small>
          </li>
        </ul>
      </aside>
    </section>

    <CommandPalette v-model="showCommandPalette" />

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

.topbar-left {
  display: flex;
  align-items: center;
  gap: 16px;
}

.topbar-center {
  flex: 1;
  text-align: center;
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

.ws-status {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: #dc2626;
  margin-bottom: 8px;
}

.ws-status.connected {
  color: #16a34a;
}

.ws-indicator {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #dc2626;
}

.ws-status.connected .ws-indicator {
  background: #16a34a;
}

.unread-badge {
  background: #dc2626;
  color: #fff;
  font-size: 10px;
  padding: 2px 6px;
  border-radius: 999px;
  margin-left: auto;
}

.ws-notification {
  border-left: 3px solid #2a8e72 !important;
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
