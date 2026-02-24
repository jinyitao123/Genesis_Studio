<script setup lang="ts">
import { useAuthStore, useComplianceStore, useNotificationStore } from '@/stores';
import { useRealtimeNotifications } from '@/composables/useWebSocket';
import { computed } from 'vue';

const authStore = useAuthStore();
const complianceStore = useComplianceStore();
const notificationStore = useNotificationStore();

const complianceSubject = computed({
  get: () => complianceStore.currentSubject,
  set: (val: string) => { complianceStore.currentSubject = val; },
});
const complianceRecords = computed(() => complianceStore.complianceRecords);

const runCompliance = async (action: "export" | "delete") => {
  if (action === 'export') {
    await complianceStore.exportData(complianceStore.currentSubject);
  } else {
    await complianceStore.deleteData(complianceStore.currentSubject);
  }
};

const runServiceEndpoint = async (path: string, body: Record<string, unknown>) => {
  await authStore.ensureToken();
  const { apiPost } = await import("@/api/client");
  const result = await apiPost(path, body, authStore.token);
  await notificationStore.loadNotifications();
  return result;
};
</script>

<template>
  <div class="ops-view ops-stack">
    <article class="ops-card">
      <h3>合规</h3>
      <input v-model="complianceSubject" type="text" placeholder="主体 ID" />
      <div class="btn-row">
        <button type="button" @click="runCompliance('export')">导出</button>
        <button type="button" @click="runCompliance('delete')">删除</button>
        <button type="button" @click="complianceStore.loadRecords">刷新记录</button>
      </div>
      <pre>{{ JSON.stringify(complianceRecords.slice(0, 5), null, 2) }}</pre>
    </article>

    <article class="ops-card">
      <h3>服务适配</h3>
      <div class="btn-grid">
        <button type="button" @click="runServiceEndpoint('/api/command/services/ontology/validate', { schema_version: '3.0.0' })">
          本体验证
        </button>
        <button type="button" @click="runServiceEndpoint('/api/command/services/object/upsert', { object_id: 'entity-1', object_type: 'Drone' })">
          对象写入
        </button>
        <button type="button" @click="runServiceEndpoint('/api/command/services/link/connect', { source_id: 'entity-1', target_id: 'entity-2', link_type: 'ATTACKS' })">
          链接建立
        </button>
        <button type="button" @click="runServiceEndpoint('/api/command/services/time-travel/snapshot', { entity_id: 'entity-1', at_ts: new Date().toISOString() })">
          时间快照
        </button>
        <button type="button" @click="runServiceEndpoint('/api/command/services/search', { query: 'drone' })">
          检索
        </button>
        <button type="button" @click="runServiceEndpoint('/api/command/services/auth/issue-token', { subject: 'svc-user', role: 'Operator' })">
          签发令牌(管理员)
        </button>
        <button type="button" @click="runServiceEndpoint('/api/command/services/notification/publish', { channel: 'ops.alerts', message: 'MVP live notification' })">
          发布通知
        </button>
      </div>
    </article>
  </div>
</template>

<script lang="ts">
export default {
  name: 'OpsView'
};
</script>

<style scoped>
.ops-view {
  height: 100%;
  width: 100%;
}

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

.ops-card pre {
  margin: 0;
  max-height: 220px;
  overflow: auto;
  background: #fff;
  border: 1px solid #d6e6ee;
  border-radius: 8px;
  padding: 8px;
}
</style>
