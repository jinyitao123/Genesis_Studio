<script setup lang="ts">
import { ref, computed } from 'vue';

interface ValidationResult {
  tier: 'L1' | 'L2' | 'L3' | 'L4';
  name: string;
  passed: boolean;
  message: string;
  details?: Record<string, unknown>;
}

interface ValidationReport {
  timestamp: string;
  duration: number;
  overall: 'passed' | 'failed' | 'warning';
  results: ValidationResult[];
}

const props = defineProps<{
  modelValue: boolean;
}>();

const emit = defineEmits<{
  (e: 'update:modelValue', value: boolean): void;
  (e: 'validate'): void;
}>();

const isValidating = ref(false);
const validationReport = ref<ValidationReport | null>(null);
const selectedTier = ref<'all' | 'L1' | 'L2' | 'L3' | 'L4'>('all');

// Mock validation results
const mockValidation = (): ValidationReport => {
  const results: ValidationResult[] = [
    { tier: 'L1', name: 'Schema Valid', passed: true, message: '所有 OTD 定义符合 Pydantic v2 Schema' },
    { tier: 'L1', name: 'Required Fields', passed: true, message: '所有必需字段已定义' },
    { tier: 'L1', name: 'Type Constraints', passed: true, message: '属性类型约束验证通过' },
    { tier: 'L2', name: 'Topology Check', passed: true, message: '无孤立节点检测通过' },
    { tier: 'L2', name: 'Cyclic Dependencies', passed: true, message: '无循环依赖' },
    { tier: 'L2', name: 'Cardinality Constraints', passed: false, message: '链接基数约束违规', details: { link: 'COMMANDS', max_fan_out: 15, limit: 12 } },
    { tier: 'L3', name: 'Cypher Safety', passed: true, message: '无禁止的 Cypher 操作' },
    { tier: 'L3', name: 'Action Parameters', passed: true, message: '动作参数定义完整' },
    { tier: 'L3', name: 'Pre-conditions', passed: true, message: '前置条件语法正确' },
    { tier: 'L4', name: 'Permission Check', passed: true, message: '用户权限验证通过' },
  ];

  const failedCount = results.filter(r => !r.passed).length;
  
  return {
    timestamp: new Date().toLocaleString('zh-CN'),
    duration: Math.floor(Math.random() * 500) + 200,
    overall: failedCount > 0 ? 'warning' : 'passed',
    results,
  };
};

const filteredResults = computed(() => {
  if (!validationReport.value) return [];
  if (selectedTier.value === 'all') return validationReport.value.results;
  return validationReport.value.results.filter(r => r.tier === selectedTier.value);
});

const passedCount = computed(() => validationReport.value?.results.filter(r => r.passed).length || 0);
const failedCount = computed(() => validationReport.value?.results.filter(r => !r.passed).length || 0);

async function runValidation() {
  isValidating.value = true;
  
  // Simulate validation delay
  await new Promise(resolve => setTimeout(resolve, 1500));
  
  validationReport.value = mockValidation();
  isValidating.value = false;
  emit('validate');
}

function close() {
  emit('update:modelValue', false);
}

function getTierColor(tier: string): string {
  switch (tier) {
    case 'L1': return '#3b82f6';
    case 'L2': return '#8b5cf6';
    case 'L3': return '#f59e0b';
    case 'L4': return '#10b981';
    default: return '#6b7280';
  }
}

function getTierLabel(tier: string): string {
  switch (tier) {
    case 'L1': return 'Schema';
    case 'L2': return 'Topology';
    case 'L3': return 'Logic';
    case 'L4': return 'Permission';
    default: return tier;
  }
}
</script>

<template>
  <Teleport to="body">
    <Transition name="fade">
      <div v-if="modelValue" class="validation-overlay" @click.self="close">
        <div class="validation-console">
          <header class="console-header">
            <h2>验证控制台</h2>
            <button class="close-btn" @click="close">✕</button>
          </header>
          
          <div class="console-body">
            <div class="validation-actions">
              <button 
                class="validate-btn" 
                :disabled="isValidating"
                @click="runValidation"
              >
                <span v-if="isValidating" class="spinner"></span>
                <span v-else>▶️</span>
                {{ isValidating ? '验证中...' : '运行验证' }}
              </button>
              
              <div v-if="validationReport" class="summary">
                <span class="summary-item success">✅ 通过: {{ passedCount }}</span>
                <span class="summary-item warning">⚠️ 失败: {{ failedCount }}</span>
                <span class="summary-item time">⏱️ {{ validationReport.duration }}ms</span>
              </div>
            </div>
            
            <div v-if="validationReport" class="tier-filters">
              <button 
                class="filter-btn"
                :class="{ active: selectedTier === 'all' }"
                @click="selectedTier = 'all'"
              >
                全部 ({{ validationReport.results.length }})
              </button>
              <button 
                v-for="tier in ['L1', 'L2', 'L3', 'L4']" 
                :key="tier"
                class="filter-btn"
                :class="{ active: selectedTier === tier }"
                :style="{ borderColor: getTierColor(tier) }"
                @click="selectedTier = tier as any"
              >
                {{ getTierLabel(tier) }} ({{ validationReport.results.filter(r => r.tier === tier).length }})
              </button>
            </div>
            
            <div v-if="validationReport" class="results-list">
              <TransitionGroup name="list">
                <div 
                  v-for="result in filteredResults" 
                  :key="result.name"
                  class="result-item"
                  :class="{ failed: !result.passed }"
                >
                  <div class="result-status">
                    <span v-if="result.passed" class="status-icon success">✅</span>
                    <span v-else class="status-icon failed">❌</span>
                    <span 
                      class="tier-badge"
                      :style="{ backgroundColor: getTierColor(result.tier) }"
                    >
                      {{ result.tier }}
                    </span>
                  </div>
                  <div class="result-content">
                    <div class="result-name">{{ result.name }}</div>
                    <div class="result-message">{{ result.message }}</div>
                    <div v-if="result.details" class="result-details">
                      <pre>{{ JSON.stringify(result.details, null, 2) }}</pre>
                    </div>
                  </div>
                </div>
              </TransitionGroup>
            </div>
            
            <div v-else class="empty-state">
              <div class="empty-icon">🔍</div>
              <p>点击"运行验证"开始验证</p>
              <div class="validation-tiers">
                <div class="tier-info">
                  <span class="tier-badge" style="background: #3b82f6">L1 Schema</span>
                  <span>Pydantic Schema 验证</span>
                </div>
                <div class="tier-info">
                  <span class="tier-badge" style="background: #8b5cf6">L2 Topology</span>
                  <span>NetworkX 拓扑验证</span>
                </div>
                <div class="tier-info">
                  <span class="tier-badge" style="background: #f59e0b">L3 Logic</span>
                  <span>AST 沙箱逻辑验证</span>
                </div>
                <div class="tier-info">
                  <span class="tier-badge" style="background: #10b981">L4 Permission</span>
                  <span>权限与安全验证</span>
                </div>
              </div>
            </div>
          </div>
          
          <footer v-if="validationReport" class="console-footer">
            <span>验证时间: {{ validationReport.timestamp }}</span>
            <button class="export-btn" @click="() => {}">导出报告</button>
          </footer>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script lang="ts">
export default {
  name: 'ValidationConsole'
};
</script>

<style scoped>
.validation-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 9999;
}

.validation-console {
  width: 700px;
  max-width: 95vw;
  max-height: 90vh;
  background: #fff;
  border-radius: 12px;
  display: flex;
  flex-direction: column;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
}

.console-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
  background: linear-gradient(135deg, #1f2937, #374151);
  color: #fff;
  border-radius: 12px 12px 0 0;
}

.console-header h2 {
  margin: 0;
  font-size: 18px;
}

.close-btn {
  width: 32px;
  height: 32px;
  border: none;
  background: rgba(255, 255, 255, 0.1);
  color: #fff;
  border-radius: 8px;
  cursor: pointer;
}

.close-btn:hover {
  background: rgba(255, 255, 255, 0.2);
}

.console-body {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
}

.validation-actions {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 20px;
}

.validate-btn {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 24px;
  border: none;
  background: linear-gradient(135deg, #1f2937, #374151);
  color: #fff;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}

.validate-btn:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
}

.validate-btn:disabled {
  opacity: 0.7;
  cursor: not-allowed;
}

.spinner {
  width: 16px;
  height: 16px;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-top-color: #fff;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.summary {
  display: flex;
  gap: 16px;
}

.summary-item {
  font-size: 13px;
  color: #6b7280;
}

.summary-item.success {
  color: #10b981;
}

.summary-item.warning {
  color: #f59e0b;
}

.tier-filters {
  display: flex;
  gap: 8px;
  margin-bottom: 16px;
  flex-wrap: wrap;
}

.filter-btn {
  padding: 6px 12px;
  border: 1px solid #e5e7eb;
  background: #fff;
  border-radius: 20px;
  font-size: 12px;
  cursor: pointer;
  transition: all 0.2s;
}

.filter-btn:hover {
  background: #f9fafb;
}

.filter-btn.active {
  background: #1f2937;
  color: #fff;
  border-color: #1f2937;
}

.results-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.result-item {
  display: flex;
  gap: 12px;
  padding: 12px 16px;
  background: #f9fafb;
  border-radius: 8px;
  border-left: 3px solid #10b981;
}

.result-item.failed {
  background: #fef3c7;
  border-left-color: #f59e0b;
}

.result-status {
  display: flex;
  align-items: center;
  gap: 8px;
}

.status-icon {
  font-size: 16px;
}

.tier-badge {
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 600;
  color: #fff;
}

.result-content {
  flex: 1;
}

.result-name {
  font-weight: 600;
  font-size: 14px;
  color: #1f2937;
  margin-bottom: 4px;
}

.result-message {
  font-size: 13px;
  color: #6b7280;
}

.result-details {
  margin-top: 8px;
}

.result-details pre {
  margin: 0;
  padding: 8px;
  background: rgba(0, 0, 0, 0.05);
  border-radius: 4px;
  font-size: 12px;
  overflow-x: auto;
}

.empty-state {
  text-align: center;
  padding: 40px;
}

.empty-icon {
  font-size: 48px;
  margin-bottom: 16px;
}

.empty-state p {
  color: #6b7280;
  margin-bottom: 24px;
}

.validation-tiers {
  display: flex;
  justify-content: center;
  gap: 16px;
  flex-wrap: wrap;
}

.tier-info {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  color: #6b7280;
}

.console-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 20px;
  background: #f9fafb;
  border-radius: 0 0 12px 12px;
  font-size: 12px;
  color: #6b7280;
}

.export-btn {
  padding: 8px 16px;
  border: 1px solid #e5e7eb;
  background: #fff;
  border-radius: 6px;
  font-size: 12px;
  cursor: pointer;
}

.export-btn:hover {
  background: #f9fafb;
}

.list-enter-active,
.list-leave-active {
  transition: all 0.3s ease;
}

.list-enter-from,
.list-leave-to {
  opacity: 0;
  transform: translateX(-20px);
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
