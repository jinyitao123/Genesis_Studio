<script setup lang="ts">
import { ref, computed, onMounted } from 'vue';
import type { InspectorFieldSchema } from '@/types';
import { apiGet } from '@/api/client';

const props = defineProps<{
  field: InspectorFieldSchema;
  modelValue: unknown;
  error?: string;
}>();

const emit = defineEmits<{
  (event: 'update:model-value', value: Array<{ timestamp: string; value: unknown }>): void;
}>();

const isExpanded = ref(false);
const isLoading = ref(false);
const historyData = ref<Array<{ timestamp: string; value: unknown }>>([]);
const maxDisplayPoints = 5;

// Load time series history - mock for demo
async function loadHistory() {
  isLoading.value = true;
  try {
    // In production:
    // const history = await apiGet<Array<{ timestamp: string; value: unknown }>>(
    //   `/api/query/property-history?property=${props.field.name}`
    // );
    
    // Mock data
    historyData.value = [
      { timestamp: new Date(Date.now() - 60000).toISOString(), value: Math.random() * 100 },
      { timestamp: new Date(Date.now() - 30000).toISOString(), value: Math.random() * 100 },
      { timestamp: new Date(Date.now()).toISOString(), value: props.modelValue },
    ];
  } catch {
    historyData.value = [];
  } finally {
    isLoading.value = false;
  }
}

onMounted(() => {
  if (isExpanded.value) {
    loadHistory();
  }
});

function toggleExpand() {
  isExpanded.value = !isExpanded.value;
  if (isExpanded.value && historyData.value.length === 0) {
    loadHistory();
  }
}

const displayHistory = computed(() => {
  return historyData.value.slice(-maxDisplayPoints);
});

function formatTimestamp(ts: string) {
  const date = new Date(ts);
  return date.toLocaleTimeString();
}
</script>

<template>
  <div class="timeseries-field" :class="{ 'has-error': error, 'is-expanded': isExpanded }">
    <div class="current-value">
      <span class="value-display">{{ modelValue ?? '-' }}</span>
      <button type="button" class="expand-btn" @click="toggleExpand">
        {{ isExpanded ? '收起' : '历史' }}
      </button>
    </div>
    
    <div v-if="isExpanded" class="history-panel">
      <div v-if="isLoading" class="loading">加载中...</div>
      <div v-else-if="historyData.length > 0" class="history-list">
        <div 
          v-for="(point, index) in displayHistory" 
          :key="index"
          class="history-item"
        >
          <span class="history-time">{{ formatTimestamp(point.timestamp) }}</span>
          <span class="history-value">{{ point.value }}</span>
        </div>
      </div>
      <div v-else class="no-data">暂无历史数据</div>
    </div>
    
    <span v-if="error" class="field-error">{{ error }}</span>
  </div>
</template>

<style scoped>
.timeseries-field {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.current-value {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 6px 10px;
  background: #f9fafb;
  border: 1px solid #e5e7eb;
  border-radius: 6px;
}

.value-display {
  font-size: 13px;
  font-family: 'Monaco', 'Consolas', monospace;
  color: #374151;
}

.expand-btn {
  background: none;
  border: 1px solid #d1d5db;
  border-radius: 4px;
  padding: 4px 8px;
  font-size: 11px;
  color: #6b7280;
  cursor: pointer;
}

.expand-btn:hover {
  background: #f3f4f6;
}

.history-panel {
  margin-top: 8px;
  padding: 8px;
  background: #f9fafb;
  border-radius: 6px;
}

.loading {
  text-align: center;
  color: #9ca3af;
  font-size: 12px;
}

.no-data {
  text-align: center;
  color: #9ca3af;
  font-size: 12px;
}

.history-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.history-item {
  display: flex;
  justify-content: space-between;
  font-size: 11px;
  padding: 4px 0;
  border-bottom: 1px solid #e5e7eb;
}

.history-item:last-child {
  border-bottom: none;
}

.history-time {
  color: #9ca3af;
}

.history-value {
  font-family: 'Monaco', 'Consolas', monospace;
  color: #374151;
}

.timeseries-field.has-error .current-value {
  border-color: #dc2626;
}

.field-error {
  color: #dc2626;
  font-size: 11px;
}
</style>
