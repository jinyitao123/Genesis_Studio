<script setup lang="ts">
import { computed, ref } from "vue";

type ProposalStatus = "draft" | "applied" | "rejected" | "rolled_back";

type Proposal = {
  proposal_id: string;
  title: string;
  intent: string;
  status: ProposalStatus;
  created_at: string;
  updated_at: string;
  code_changes?: CodeChange[];
  impact_analysis?: ImpactItem[];
  rollback_plan?: string[];
};

type CodeChange = {
  file: string;
  type: "add" | "remove" | "modify";
  line_start: number;
  line_end: number;
  old_code?: string;
  new_code?: string;
  description: string;
};

type ImpactItem = {
  type: "entity" | "relationship" | "action" | "query";
  name: string;
  impact: "high" | "medium" | "low";
  description: string;
  affected_count?: number;
};

const props = defineProps<{
  proposal: Proposal;
  busy: boolean;
}>();

const emit = defineEmits<{
  (event: "apply", proposalId: string): void;
  (event: "reject", proposalId: string): void;
  (event: "rollback", proposalId: string): void;
  (event: "preview", proposalId: string): void;
}>();

const activeTab = ref<"overview" | "diff" | "impact">("overview");
const expandedFiles = ref<Set<string>>(new Set());

const applyProposal = () => emit("apply", props.proposal.proposal_id);
const rejectProposal = () => emit("reject", props.proposal.proposal_id);
const rollbackProposal = () => emit("rollback", props.proposal.proposal_id);
const previewProposal = () => emit("preview", props.proposal.proposal_id);

const statusLabel: Record<ProposalStatus, string> = {
  draft: "草稿",
  applied: "已应用",
  rejected: "已拒绝",
  rolled_back: "已回滚",
};

const statusClass: Record<ProposalStatus, string> = {
  draft: "status-draft",
  applied: "status-applied",
  rejected: "status-rejected",
  rolled_back: "status-rolled-back",
};

const codeChanges = computed<CodeChange[]>(() => {
  return props.proposal.code_changes || [
    {
      file: "ontology/types/drone.json",
      type: "modify",
      line_start: 15,
      line_end: 28,
      old_code: `  "max_speed": 100,\n  "armor": 50,`,
      new_code: `  "max_speed": 120,\n  "armor": 65,\n  "stealth_mode": true,`,
      description: "增强无人机属性并添加隐身模式",
    },
    {
      file: "actions/attack.yaml",
      type: "add",
      line_start: 45,
      line_end: 52,
      new_code: `  stealth_bonus:\n    condition: source.stealth_mode == true\n    effect: damage * 1.5\n    duration: 10s`,
      description: "添加隐身攻击加成",
    },
  ];
});

const impactItems = computed<ImpactItem[]>(() => {
  return props.proposal.impact_analysis || [
    {
      type: "entity",
      name: "Drone",
      impact: "high",
      description: "将修改 1,247 个无人机实体的属性",
      affected_count: 1247,
    },
    {
      type: "action",
      name: "ACT_ATTACK",
      impact: "medium",
      description: "攻击动作逻辑变更，影响所有战斗计算",
      affected_count: 5234,
    },
  ];
});

const rollbackPlan = computed<string[]>(() => {
  return props.proposal.rollback_plan || [
    "1. 备份当前 Drone 类型定义到 rollback/drone_backup.json",
    "2. 恢复原始 max_speed 和 armor 值",
    "3. 删除 stealth_mode 属性",
    "4. 移除 attack.yaml 中的 stealth_bonus 逻辑",
    "5. 重新计算所有受影响的实体",
  ];
});

const totalAffected = computed(() => {
  return impactItems.value.reduce((sum, item) => sum + (item.affected_count || 0), 0);
});

const highImpactCount = computed(() => {
  return impactItems.value.filter((item) => item.impact === "high").length;
});

const toggleFile = (file: string) => {
  if (expandedFiles.value.has(file)) {
    expandedFiles.value.delete(file);
  } else {
    expandedFiles.value.add(file);
  }
};

const getChangeIcon = (type: string) => {
  switch (type) {
    case "add": return "+";
    case "remove": return "−";
    case "modify": return "○";
    default: return "•";
  }
};

const getImpactClass = (impact: string) => {
  switch (impact) {
    case "high": return "impact-high";
    case "medium": return "impact-medium";
    case "low": return "impact-low";
    default: return "";
  }
};

const getImpactLabel = (impact: string) => {
  switch (impact) {
    case "high": return "高";
    case "medium": return "中";
    case "low": return "低";
    default: return "未知";
  }
};

const getTypeLabel = (type: string) => {
  switch (type) {
    case "entity": return "实体";
    case "relationship": return "关系";
    case "action": return "动作";
    case "query": return "查询";
    default: return type;
  }
};
</script>

<template>
  <article class="proposal-card">
    <header class="proposal-header">
      <div class="title-section">
        <h3>{{ proposal.title }}</h3>
        <span class="status" :class="statusClass[proposal.status]">
          {{ statusLabel[proposal.status] }}
        </span>
      </div>
      <div class="meta-badges">
        <span class="badge" v-if="totalAffected > 0">
          影响 {{ totalAffected.toLocaleString() }} 个对象
        </span>
        <span class="badge warning" v-if="highImpactCount > 0">
          {{ highImpactCount }} 个高风险变更
        </span>
      </div>
    </header>

    <p class="intent">{{ proposal.intent }}</p>

    <div class="meta">
      <span>编号: {{ proposal.proposal_id }}</span>
      <span>创建: {{ new Date(proposal.created_at).toLocaleString('zh-CN') }}</span>
      <span>更新: {{ new Date(proposal.updated_at).toLocaleString('zh-CN') }}</span>
    </div>

    <!-- Tab Navigation -->
    <nav class="tab-nav">
      <button type="button" :class="{ active: activeTab === 'overview' }" @click="activeTab = 'overview'">
        概览
      </button>
      <button type="button" :class="{ active: activeTab === 'diff' }" @click="activeTab = 'diff'">
        代码差异 ({{ codeChanges.length }})
      </button>
      <button type="button" :class="{ active: activeTab === 'impact' }" @click="activeTab = 'impact'">
        影响分析
      </button>
    </nav>

    <!-- Overview Tab -->
    <section v-if="activeTab === 'overview'" class="tab-content">
      <div class="summary-stats">
        <div class="stat-item">
          <span class="stat-value">{{ codeChanges.length }}</span>
          <span class="stat-label">文件变更</span>
        </div>
        <div class="stat-item">
          <span class="stat-value">{{ impactItems.length }}</span>
          <span class="stat-label">受影响组件</span>
        </div>
        <div class="stat-item">
          <span class="stat-value">{{ rollbackPlan.length }}</span>
          <span class="stat-label">回滚步骤</span>
        </div>
      </div>

      <div class="change-preview">
        <h4>主要变更</h4>
        <ul class="change-list">
          <li v-for="(change, index) in codeChanges.slice(0, 3)" :key="index">
            <span class="change-icon" :class="`type-${change.type}`">{{ getChangeIcon(change.type) }}</span>
            <span class="change-file">{{ change.file }}</span>
            <span class="change-desc">{{ change.description }}</span>
          </li>
        </ul>
      </div>

      <div class="impact-preview">
        <h4>影响摘要</h4>
        <div class="impact-bars">
          <div v-for="item in impactItems.slice(0, 3)" :key="item.name" class="impact-bar-item">
            <div class="impact-info">
              <span class="impact-name">{{ item.name }}</span>
              <span class="impact-type">{{ getTypeLabel(item.type) }}</span>
            </div>
            <div class="impact-meter">
              <div class="impact-fill" :class="getImpactClass(item.impact)" 
                   :style="{ width: item.impact === 'high' ? '100%' : item.impact === 'medium' ? '60%' : '30%' }" />
            </div>
            <span class="impact-badge" :class="getImpactClass(item.impact)">{{ getImpactLabel(item.impact) }}</span>
          </div>
        </div>
      </div>
    </section>

    <!-- Diff Tab -->
    <section v-else-if="activeTab === 'diff'" class="tab-content">
      <div class="diff-list">
        <div v-for="(change, index) in codeChanges" :key="index" class="diff-item">
          <div class="diff-header" @click="toggleFile(change.file)">
            <span class="diff-toggle">{{ expandedFiles.has(change.file) ? '▼' : '▶' }}</span>
            <span class="diff-type" :class="`type-${change.type}`">
              {{ getChangeIcon(change.type) }} {{ change.type.toUpperCase() }}
            </span>
            <span class="diff-file">{{ change.file }}</span>
            <span class="diff-lines">行 {{ change.line_start }}-{{ change.line_end }}</span>
          </div>
          
          <div v-if="expandedFiles.has(change.file)" class="diff-content">
            <p class="diff-description">{{ change.description }}</p>
            <div v-if="change.old_code" class="code-block removed">
              <div class="code-header">删除</div>
              <pre>{{ change.old_code }}</pre>
            </div>
            <div v-if="change.new_code" class="code-block added">
              <div class="code-header">新增</div>
              <pre>{{ change.new_code }}</pre>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- Impact Tab -->
    <section v-else-if="activeTab === 'impact'" class="tab-content">
      <div class="impact-summary">
        <h4>影响范围</h4>
        <div class="impact-grid">
          <div v-for="item in impactItems" :key="item.name" class="impact-card" :class="getImpactClass(item.impact)">
            <div class="impact-card-header">
              <span class="impact-type-badge">{{ getTypeLabel(item.type) }}</span>
              <span class="impact-level">{{ getImpactLabel(item.impact) }}风险</span>
            </div>
            <h5 class="impact-card-name">{{ item.name }}</h5>
            <p class="impact-card-desc">{{ item.description }}</p>
            <div v-if="item.affected_count" class="impact-card-count">影响 {{ item.affected_count.toLocaleString() }} 个对象</div>
          </div>
        </div>
      </div>

      <div class="rollback-section">
        <h4>回滚计划</h4>
        <ol class="rollback-list">
          <li v-for="(step, index) in rollbackPlan" :key="index">{{ step }}</li>
        </ol>
      </div>
    </section>

    <footer class="actions">
      <button type="button" class="btn-preview" @click="previewProposal" :disabled="busy">预览</button>
      <button type="button" class="btn-apply" @click="applyProposal" :disabled="busy || proposal.status !== 'draft'">应用</button>
      <button type="button" class="btn-reject" @click="rejectProposal" :disabled="busy || proposal.status !== 'draft'">拒绝</button>
      <button type="button" class="btn-rollback" @click="rollbackProposal" :disabled="busy || proposal.status !== 'applied'">回滚</button>
    </footer>
  </article>
</template>

<style scoped>
.proposal-card {
  border: 1px solid #ccd9e3;
  border-radius: 12px;
  padding: 16px;
  background: #ffffff;
  display: grid;
  gap: 12px;
}

.proposal-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
  flex-wrap: wrap;
}

.title-section {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.proposal-header h3 {
  margin: 0;
  font-size: 16px;
  color: #0f2f41;
}

.status {
  text-transform: uppercase;
  font-size: 11px;
  padding: 3px 10px;
  border-radius: 999px;
  font-weight: 700;
}

.status-draft { background: #e9f4fa; color: #0d6c8d; }
.status-applied { background: #d1fae5; color: #065f46; }
.status-rejected { background: #fee2e2; color: #991b1b; }
.status-rolled-back { background: #f3f4f6; color: #4b5563; }

.meta-badges {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}

.badge {
  font-size: 11px;
  padding: 3px 8px;
  background: #e9f4fa;
  color: #0d6c8d;
  border-radius: 999px;
}

.badge.warning {
  background: #fef3c7;
  color: #92400e;
}

.intent {
  margin: 0;
  color: #2f4858;
  font-size: 14px;
  line-height: 1.5;
}

.meta {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  font-size: 12px;
  color: #5d7280;
}

/* Tab Navigation */
.tab-nav {
  display: flex;
  gap: 4px;
  border-bottom: 1px solid #e5e7eb;
  margin: 8px 0;
}

.tab-nav button {
  border: none;
  background: transparent;
  color: #6b7280;
  padding: 8px 16px;
  cursor: pointer;
  font-size: 13px;
  border-bottom: 2px solid transparent;
  margin-bottom: -1px;
}

.tab-nav button.active {
  color: #0d6c8d;
  border-bottom-color: #0d6c8d;
  font-weight: 600;
}

.tab-content {
  min-height: 200px;
}

/* Overview Tab */
.summary-stats {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
  margin-bottom: 16px;
}

.stat-item {
  text-align: center;
  padding: 12px;
  background: #f8fbfd;
  border-radius: 8px;
}

.stat-value {
  display: block;
  font-size: 24px;
  font-weight: 700;
  color: #0d6c8d;
}

.stat-label {
  font-size: 12px;
  color: #6b7280;
}

.change-preview h4, .impact-preview h4 {
  margin: 0 0 10px;
  font-size: 14px;
  color: #1f2937;
}

.change-list {
  list-style: none;
  margin: 0;
  padding: 0;
}

.change-list li {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 0;
  border-bottom: 1px solid #f3f4f6;
}

.change-icon {
  width: 20px;
  height: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 4px;
  font-size: 14px;
  font-weight: 700;
}

.change-icon.type-add { background: #d1fae5; color: #065f46; }
.change-icon.type-remove { background: #fee2e2; color: #991b1b; }
.change-icon.type-modify { background: #fef3c7; color: #92400e; }

.change-file {
  font-family: monospace;
  font-size: 12px;
  color: #374151;
  background: #f3f4f6;
  padding: 2px 6px;
  border-radius: 4px;
}

.change-desc {
  flex: 1;
  font-size: 13px;
  color: #6b7280;
}

/* Impact Bars */
.impact-bars {
  display: grid;
  gap: 10px;
}

.impact-bar-item {
  display: grid;
  grid-template-columns: 1fr 100px 40px;
  align-items: center;
  gap: 10px;
}

.impact-info {
  display: flex;
  align-items: center;
  gap: 8px;
}

.impact-name {
  font-weight: 600;
  color: #1f2937;
}

.impact-type {
  font-size: 11px;
  color: #6b7280;
  background: #f3f4f6;
  padding: 2px 6px;
  border-radius: 4px;
}

.impact-meter {
  height: 8px;
  background: #e5e7eb;
  border-radius: 4px;
  overflow: hidden;
}

.impact-fill {
  height: 100%;
  border-radius: 4px;
  transition: width 0.3s;
}

.impact-fill.impact-high { background: #ef4444; }
.impact-fill.impact-medium { background: #f59e0b; }
.impact-fill.impact-low { background: #10b981; }

.impact-badge {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 4px;
  text-align: center;
}

.impact-badge.impact-high { background: #fee2e2; color: #991b1b; }
.impact-badge.impact-medium { background: #fef3c7; color: #92400e; }
.impact-badge.impact-low { background: #d1fae5; color: #065f46; }

/* Diff Tab */
.diff-list {
  display: grid;
  gap: 10px;
}

.diff-item {
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  overflow: hidden;
}

.diff-header {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  background: #f9fafb;
  cursor: pointer;
  user-select: none;
}

.diff-header:hover {
  background: #f3f4f6;
}

.diff-toggle {
  color: #6b7280;
  font-size: 10px;
}

.diff-type {
  font-size: 11px;
  font-weight: 700;
  padding: 2px 6px;
  border-radius: 4px;
}

.diff-type.type-add { background: #d1fae5; color: #065f46; }
.diff-type.type-remove { background: #fee2e2; color: #991b1b; }
.diff-type.type-modify { background: #fef3c7; color: #92400e; }

.diff-file {
  flex: 1;
  font-family: monospace;
  font-size: 13px;
  color: #374151;
}

.diff-lines {
  font-size: 11px;
  color: #9ca3af;
}

.diff-content {
  padding: 12px;
  background: #fff;
  border-top: 1px solid #e5e7eb;
}

.diff-description {
  margin: 0 0 12px;
  font-size: 13px;
  color: #4b5563;
  padding: 8px;
  background: #f9fafb;
  border-radius: 6px;
}

.code-block {
  margin-bottom: 10px;
  border-radius: 6px;
  overflow: hidden;
}

.code-block .code-header {
  font-size: 11px;
  padding: 4px 10px;
  font-weight: 600;
}

.code-block pre {
  margin: 0;
  padding: 10px;
  font-size: 12px;
  font-family: 'Monaco', 'Consolas', monospace;
  overflow-x: auto;
  line-height: 1.5;
}

.code-block.removed {
  border: 1px solid #fecaca;
}

.code-block.removed .code-header {
  background: #fee2e2;
  color: #991b1b;
}

.code-block.removed pre {
  background: #fef2f2;
  color: #7f1d1d;
}

.code-block.added {
  border: 1px solid #a7f3d0;
}

.code-block.added .code-header {
  background: #d1fae5;
  color: #065f46;
}

.code-block.added pre {
  background: #ecfdf5;
  color: #064e3b;
}

/* Impact Tab */
.impact-summary h4, .rollback-section h4 {
  margin: 0 0 12px;
  font-size: 14px;
  color: #1f2937;
}

.impact-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 10px;
}

.impact-card {
  padding: 12px;
  border-radius: 8px;
  border: 1px solid #e5e7eb;
}

.impact-card.impact-high { border-color: #fecaca; background: #fef2f2; }
.impact-card.impact-medium { border-color: #fde68a; background: #fffbeb; }
.impact-card.impact-low { border-color: #a7f3d0; background: #ecfdf5; }

.impact-card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.impact-type-badge {
  font-size: 10px;
  padding: 2px 6px;
  background: rgba(255, 255, 255, 0.8);
  border-radius: 4px;
  color: #6b7280;
}

.impact-level {
  font-size: 11px;
  font-weight: 600;
}

.impact-card.impact-high .impact-level { color: #991b1b; }
.impact-card.impact-medium .impact-level { color: #92400e; }
.impact-card.impact-low .impact-level { color: #065f46; }

.impact-card-name {
  margin: 0 0 6px;
  font-size: 14px;
  color: #1f2937;
}

.impact-card-desc {
  margin: 0 0 8px;
  font-size: 12px;
  color: #4b5563;
  line-height: 1.4;
}

.impact-card-count {
  font-size: 11px;
  color: #6b7280;
  font-weight: 600;
}

/* Rollback Section */
.rollback-section {
  border-top: 1px solid #e5e7eb;
  padding-top: 16px;
  margin-top: 16px;
}

.rollback-list {
  margin: 0;
  padding-left: 20px;
  font-size: 12px;
  color: #4b5563;
}

.rollback-list li {
  margin-bottom: 6px;
  line-height: 1.5;
}

/* Actions */
.actions {
  display: flex;
  gap: 8px;
  padding-top: 12px;
  border-top: 1px solid #e5e7eb;
}

.actions button {
  padding: 8px 16px;
  border-radius: 6px;
  cursor: pointer;
  font-size: 13px;
  font-weight: 500;
  transition: all 0.2s;
}

.btn-preview {
  border: 1px solid #d1d5db;
  background: #fff;
  color: #374151;
}

.btn-apply {
  border: 1px solid #0d6c8d;
  background: #0d6c8d;
  color: #fff;
}

.btn-reject {
  border: 1px solid #dc2626;
  background: #fff;
  color: #dc2626;
}

.btn-rollback {
  border: 1px solid #6b7280;
  background: #f3f4f6;
  color: #4b5563;
}

.actions button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
</style>
