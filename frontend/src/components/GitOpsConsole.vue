<script setup lang="ts">
import { ref, computed, onMounted } from 'vue';
import { useStudioStore } from '@/stores';

interface GitCommit {
  hash: string;
  message: string;
  author: string;
  timestamp: string;
  branch: string;
}

interface GitBranch {
  name: string;
  isCurrent: boolean;
  isProtected: boolean;
}

interface PendingChange {
  type: 'add' | 'modify' | 'delete';
  path: string;
  status: 'staged' | 'unstaged';
}

const props = defineProps<{
  modelValue: boolean;
}>();

const emit = defineEmits<{
  (e: 'update:modelValue', value: boolean): void;
  (e: 'hotReload'): void;
}>();

const studioStore = useStudioStore();

// Tab state
const activeTab = ref<'changes' | 'commits' | 'push'>('changes');

// Mock data
const currentBranch = ref('main');
const branches = ref<GitBranch[]>([
  { name: 'main', isCurrent: true, isProtected: true },
  { name: 'develop', isCurrent: false, isProtected: false },
  { name: 'feature/drone-unit', isCurrent: false, isProtected: false },
  { name: 'hotfix/security-patch', isCurrent: false, isProtected: true },
]);

const commits = ref<GitCommit[]>([
  { hash: 'a1b2c3d', message: 'feat: Add Drone unit with self-destruct logic', author: 'Alex', timestamp: '2026-02-12 10:30', branch: 'feature/drone-unit' },
  { hash: 'e4f5g6h', message: 'fix: Resolve circular dependency in LinkService', author: 'Alex', timestamp: '2026-02-11 16:45', branch: 'develop' },
  { hash: 'i7j8k9l', message: 'chore: Update dependencies', author: 'CI', timestamp: '2026-02-11 08:00', branch: 'main' },
  { hash: 'm0n1o2p', message: 'feat: Implement GraphVisualizer with Cytoscape', author: 'Alex', timestamp: '2026-02-10 14:20', branch: 'develop' },
]);

const pendingChanges = ref<PendingChange[]>([
  { type: 'modify', path: 'domains/mil/units/Drone.yaml', status: 'staged' },
  { type: 'add', path: 'domains/mil/actions/ACT_SELF_DESTRUCT.yaml', status: 'staged' },
  { type: 'modify', path: 'domains/mil/schemas/Tank.yaml', status: 'unstaged' },
  { type: 'delete', path: 'domains/mil/temp/TempUnit.yaml', status: 'unstaged' },
]);

const commitMessage = ref('');
const pushMessage = ref('');

// Computed
const stagedChanges = computed(() => pendingChanges.value.filter(c => c.status === 'staged'));
const unstagedChanges = computed(() => pendingChanges.value.filter(c => c.status === 'unstaged'));
const hasStagedChanges = computed(() => stagedChanges.value.length > 0);
const canCommit = computed(() => commitMessage.value.trim().length > 0);

// Actions
function switchBranch(branch: GitBranch) {
  if (branch.isProtected && branch.name !== 'main') {
    alert('受保护分支，需要管理员权限');
    return;
  }
  currentBranch.value = branch.name;
}

function stageChange(change: PendingChange) {
  change.status = 'staged';
}

function unstageChange(change: PendingChange) {
  change.status = 'unstaged';
}

function stageAll() {
  pendingChanges.value.forEach(c => c.status = 'staged');
}

function unstageAll() {
  pendingChanges.value.forEach(c => c.status = 'unstaged');
}

async function commit() {
  if (!canCommit.value) return;
  
  // Mock commit
  const newCommit: GitCommit = {
    hash: Math.random().toString(36).substring(2, 8),
    message: commitMessage.value,
    author: 'Alex',
    timestamp: new Date().toLocaleString('zh-CN'),
    branch: currentBranch.value,
  };
  
  commits.value.unshift(newCommit);
  pendingChanges.value = [];
  commitMessage.value = '';
  studioStore.clearAllDirty();
}

async function push() {
  // Mock push
  alert(`推送到 ${currentBranch.value} 完成`);
}

async function pull() {
  // Mock pull
  alert('拉取完成');
}

async function triggerHotReload() {
  emit('hotReload');
  emit('update:modelValue', false);
}

function close() {
  emit('update:modelValue', false);
}

function getChangeIcon(type: PendingChange['type']): string {
  switch (type) {
    case 'add': return '➕';
    case 'modify': return '✏️';
    case 'delete': return '🗑️';
  }
}

function formatHash(hash: string): string {
  return hash.substring(0, 7);
}
</script>

<template>
  <Teleport to="body">
    <Transition name="slide">
      <div v-if="modelValue" class="gitops-overlay" @click.self="close">
        <div class="gitops-console">
          <header class="console-header">
            <h2>GitOps 控制台</h2>
            <button class="close-btn" @click="close">✕</button>
          </header>
          
          <div class="console-tabs">
            <button 
              class="tab" 
              :class="{ active: activeTab === 'changes' }"
              @click="activeTab = 'changes'"
            >
              变更
            </button>
            <button 
              class="tab" 
              :class="{ active: activeTab === 'commits' }"
              @click="activeTab = 'commits'"
            >
              提交
            </button>
            <button 
              class="tab" 
              :class="{ active: activeTab === 'push' }"
              @click="activeTab = 'push'"
            >
              推送
            </button>
          </div>
          
          <div class="console-content">
            <!-- Changes Tab -->
            <div v-if="activeTab === 'changes'" class="changes-tab">
              <div class="branch-selector">
                <label>当前分支:</label>
                <select :value="currentBranch" @change="(e) => switchBranch(branches.find(b => b.name === (e.target as HTMLSelectElement).value)!)">
                  <option v-for="branch in branches" :key="branch.name" :value="branch.name">
                    {{ branch.name }}{{ branch.isProtected ? ' 🔒' : '' }}
                  </option>
                </select>
              </div>
              
              <div class="changes-section">
                <div class="section-header">
                  <span>已暂存 ({{ stagedChanges.length }})</span>
                  <button class="text-btn" @click="unstageAll">全部取消暂存</button>
                </div>
                <ul class="changes-list">
                  <li v-for="change in stagedChanges" :key="change.path" class="change-item staged">
                    <span class="change-icon">{{ getChangeIcon(change.type) }}</span>
                    <span class="change-path">{{ change.path }}</span>
                    <button class="icon-btn" @click="unstageChange(change)" title="取消暂存">↩️</button>
                  </li>
                </ul>
              </div>
              
              <div class="changes-section">
                <div class="section-header">
                  <span>未暂存 ({{ unstagedChanges.length }})</span>
                  <button class="text-btn" @click="stageAll">全部暂存</button>
                </div>
                <ul class="changes-list">
                  <li v-for="change in unstagedChanges" :key="change.path" class="change-item unstaged">
                    <span class="change-icon">{{ getChangeIcon(change.type) }}</span>
                    <span class="change-path">{{ change.path }}</span>
                    <button class="icon-btn" @click="stageChange(change)" title="暂存">↪️</button>
                  </li>
                </ul>
              </div>
              
              <div class="commit-section">
                <textarea 
                  v-model="commitMessage" 
                  placeholder="提交消息..."
                  rows="3"
                ></textarea>
                <button class="commit-btn" :disabled="!canCommit" @click="commit">
                  提交变更
                </button>
              </div>
            </div>
            
            <!-- Commits Tab -->
            <div v-if="activeTab === 'commits'" class="commits-tab">
              <div class="commits-list">
                <div v-for="commit in commits" :key="commit.hash" class="commit-item">
                  <div class="commit-hash">{{ formatHash(commit.hash) }}</div>
                  <div class="commit-info">
                    <div class="commit-message">{{ commit.message }}</div>
                    <div class="commit-meta">
                      <span>{{ commit.author }}</span>
                      <span>•</span>
                      <span>{{ commit.timestamp }}</span>
                      <span class="commit-branch" :class="{ current: commit.branch === currentBranch }">
                        {{ commit.branch }}
                      </span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
            
            <!-- Push Tab -->
            <div v-if="activeTab === 'push'" class="push-tab">
              <div class="push-actions">
                <div class="action-card">
                  <h3>📤 推送</h3>
                  <p>将本地提交推送到远程仓库</p>
                  <button class="action-btn primary" @click="push">推送到 {{ currentBranch }}</button>
                </div>
                
                <div class="action-card">
                  <h3>📥 拉取</h3>
                  <p>从远程仓库获取最新变更</p>
                  <button class="action-btn" @click="pull">拉取并合并</button>
                </div>
                
                <div class="action-card hot-reload">
                  <h3>🔥 热重载</h3>
                  <p>应用配置变更，无需重启服务</p>
                  <button class="action-btn reload" @click="triggerHotReload">
                    执行热重载
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script lang="ts">
export default {
  name: 'GitOpsConsole'
};
</script>

<style scoped>
.gitops-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  justify-content: flex-end;
  z-index: 9998;
}

.gitops-console {
  width: 500px;
  max-width: 100vw;
  height: 100%;
  background: #fff;
  display: flex;
  flex-direction: column;
  box-shadow: -10px 0 40px rgba(0, 0, 0, 0.2);
}

.console-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
  background: linear-gradient(135deg, #1f2937, #374151);
  color: #fff;
}

.console-header h2 {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
}

.close-btn {
  width: 32px;
  height: 32px;
  border: none;
  background: rgba(255, 255, 255, 0.1);
  color: #fff;
  border-radius: 8px;
  cursor: pointer;
  font-size: 16px;
}

.close-btn:hover {
  background: rgba(255, 255, 255, 0.2);
}

.console-tabs {
  display: flex;
  border-bottom: 1px solid #e5e7eb;
}

.tab {
  flex: 1;
  padding: 12px;
  border: none;
  background: transparent;
  font-size: 14px;
  color: #6b7280;
  cursor: pointer;
  transition: all 0.2s;
}

.tab:hover {
  color: #374151;
  background: #f9fafb;
}

.tab.active {
  color: #1f2937;
  border-bottom: 2px solid #1f2937;
  font-weight: 600;
}

.console-content {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
}

.changes-section {
  margin-bottom: 16px;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
  font-size: 13px;
  font-weight: 600;
  color: #374151;
}

.text-btn {
  border: none;
  background: transparent;
  color: #6b7280;
  font-size: 12px;
  cursor: pointer;
}

.text-btn:hover {
  color: #1f2937;
}

.changes-list {
  list-style: none;
  margin: 0;
  padding: 0;
}

.change-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  border-radius: 6px;
  margin-bottom: 4px;
}

.change-item.staged {
  background: #d1fae5;
}

.change-item.unstaged {
  background: #fef3c7;
}

.change-icon {
  font-size: 14px;
}

.change-path {
  flex: 1;
  font-size: 13px;
  font-family: monospace;
}

.icon-btn {
  padding: 4px;
  border: none;
  background: transparent;
  cursor: pointer;
  opacity: 0.6;
}

.icon-btn:hover {
  opacity: 1;
}

.commit-section {
  margin-top: 16px;
}

.commit-section textarea {
  width: 100%;
  padding: 12px;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  font-family: inherit;
  font-size: 14px;
  resize: vertical;
}

.commit-btn {
  width: 100%;
  margin-top: 8px;
  padding: 12px;
  border: none;
  background: linear-gradient(135deg, #1f2937, #374151);
  color: #fff;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
}

.commit-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.commits-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.commit-item {
  display: flex;
  gap: 12px;
  padding: 12px;
  background: #f9fafb;
  border-radius: 8px;
}

.commit-hash {
  font-family: monospace;
  font-size: 12px;
  color: #6b7280;
  padding: 4px 8px;
  background: #e5e7eb;
  border-radius: 4px;
}

.commit-info {
  flex: 1;
}

.commit-message {
  font-size: 14px;
  font-weight: 500;
  margin-bottom: 4px;
}

.commit-meta {
  display: flex;
  gap: 8px;
  font-size: 12px;
  color: #6b7280;
}

.commit-branch {
  padding: 2px 6px;
  background: #e5e7eb;
  border-radius: 4px;
}

.commit-branch.current {
  background: #dbeafe;
  color: #1e40af;
}

.push-actions {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.action-card {
  padding: 20px;
  border: 1px solid #e5e7eb;
  border-radius: 12px;
}

.action-card h3 {
  margin: 0 0 8px;
  font-size: 16px;
}

.action-card p {
  margin: 0 0 12px;
  font-size: 13px;
  color: #6b7280;
}

.action-btn {
  width: 100%;
  padding: 12px;
  border: 1px solid #e5e7eb;
  background: #fff;
  border-radius: 8px;
  font-size: 14px;
  cursor: pointer;
  transition: all 0.2s;
}

.action-btn:hover {
  background: #f9fafb;
  border-color: #d1d5db;
}

.action-btn.primary {
  background: #1f2937;
  color: #fff;
  border: none;
}

.action-btn.primary:hover {
  background: #374151;
}

.action-btn.reload {
  background: linear-gradient(135deg, #f59e0b, #d97706);
  color: #fff;
  border: none;
}

.action-btn.reload:hover {
  background: linear-gradient(135deg, #d97706, #b45309);
}

.branch-selector {
  margin-bottom: 16px;
}

.branch-selector label {
  display: block;
  font-size: 12px;
  color: #6b7280;
  margin-bottom: 4px;
}

.branch-selector select {
  width: 100%;
  padding: 10px;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  font-size: 14px;
}

.slide-enter-active,
.slide-leave-active {
  transition: transform 0.3s ease;
}

.slide-enter-from,
.slide-leave-to {
  transform: translateX(100%);
}
</style>
